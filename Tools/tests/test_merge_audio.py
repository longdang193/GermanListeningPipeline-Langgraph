from pathlib import Path

import pytest

from glist_pipeline import merge_audio


def test_collect_source_files_filters_and_sorts_windows_logically(tmp_path: Path) -> None:
    if merge_audio._STRCMP_LOGICAL is None:
        pytest.skip("Windows logical sort is only available on Windows.")

    input_dir = tmp_path / "Audios" / "Merge"
    input_dir.mkdir(parents=True)
    (input_dir / "Gregs Tagebuch - Kapitel 10.mp3").write_bytes(b"mp3")
    (input_dir / "Gregs Tagebuch - Kapitel 3.mp3").write_bytes(b"mp3")
    (input_dir / "Gregs Tagebuch - Kapitel 26.mp3").write_bytes(b"mp3")
    (input_dir / "notes.txt").write_text("ignore", encoding="utf-8")

    files = merge_audio.collect_source_files(input_dir)

    assert [path.name for path in files] == [
        "Gregs Tagebuch - Kapitel 3.mp3",
        "Gregs Tagebuch - Kapitel 10.mp3",
        "Gregs Tagebuch - Kapitel 26.mp3",
    ]


def test_sort_audio_files_falls_back_to_plain_name_sort(monkeypatch, tmp_path: Path) -> None:
    files = [
        tmp_path / "Gregs Tagebuch - Kapitel 10.mp3",
        tmp_path / "Gregs Tagebuch - Kapitel 3.mp3",
        tmp_path / "Gregs Tagebuch - Kapitel 26.mp3",
    ]

    monkeypatch.setattr(merge_audio, "_STRCMP_LOGICAL", None)

    ordered = merge_audio.sort_audio_files(files)

    assert [path.name for path in ordered] == [
        "Gregs Tagebuch - Kapitel 10.mp3",
        "Gregs Tagebuch - Kapitel 26.mp3",
        "Gregs Tagebuch - Kapitel 3.mp3",
    ]


def test_collect_source_files_fails_on_empty_dir(tmp_path: Path) -> None:
    input_dir = tmp_path / "Audios" / "Merge"
    input_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="No audio files found"):
        merge_audio.collect_source_files(input_dir)


def test_build_merge_plan_preserves_input_order_without_markers(tmp_path: Path) -> None:
    sources = [tmp_path / "b.mp3", tmp_path / "a.mp3"]
    for path in sources:
        path.write_bytes(b"x")

    plan = merge_audio.build_merge_plan(sources, markers="without")

    assert [(item.kind, item.part_number, item.text) for item in plan] == [
        ("source", 1, None),
        ("source", 2, None),
    ]
    assert [item.source_path.name for item in plan] == ["b.mp3", "a.mp3"]


def test_build_merge_plan_with_markers_preserves_input_order(tmp_path: Path) -> None:
    sources = [tmp_path / "b.mp3", tmp_path / "a.mp3"]
    for path in sources:
        path.write_bytes(b"x")

    plan = merge_audio.build_merge_plan(sources, markers="with")

    assert [(item.kind, item.part_number, item.text) for item in plan] == [
        ("prompt_intro", 1, "Teil 1"),
        ("source", 1, None),
        ("prompt_outro", 1, "Ende des Teil 1"),
        ("prompt_intro", 2, "Teil 2"),
        ("source", 2, None),
        ("prompt_outro", 2, "Ende des Teil 2"),
    ]
    assert [item.source_path.name for item in plan if item.kind == "source"] == ["b.mp3", "a.mp3"]


def test_resolve_recorded_prompt_clip_requires_expected_name(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    with pytest.raises(FileNotFoundError, match=r"teil_1\.mp3"):
        merge_audio.resolve_recorded_prompt_clip(prompt_dir, 1, "prompt_intro")


def test_select_sapi_voice_rejects_missing_requested_voice() -> None:
    voices = ["Microsoft David Desktop", "Microsoft Zira Desktop"]

    with pytest.raises(ValueError, match="Available voices"):
        merge_audio.select_sapi_voice(voices, requested_voice_name="Hedda")


def test_select_sapi_voice_requires_german_voice_when_unset() -> None:
    voices = ["Microsoft David Desktop", "Microsoft Zira Desktop"]

    with pytest.raises(ValueError, match="No German SAPI voice"):
        merge_audio.select_sapi_voice(voices, requested_voice_name="")


def test_generate_prompt_wav_interpolates_powershell_inputs(monkeypatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs):
        commands.append(command)
        return type("Result", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(merge_audio.subprocess, "run", fake_run)

    target = tmp_path / "prompt.wav"
    merge_audio.generate_prompt_wav(target, "Teil 1", "")

    script = commands[0][-1]
    assert "$requested = '';" in script
    assert "$spoken = 'Teil 1';" in script
    assert f"$target = '{target}';" in script
    assert "{requested}" not in script


def test_write_concat_manifest_preserves_order_and_escaping(tmp_path: Path) -> None:
    stage_dir = tmp_path / "_merge_stage"
    stage_dir.mkdir()
    first = stage_dir / "o'clock.mp3"
    second = stage_dir / "plain.mp3"
    first.write_bytes(b"x")
    second.write_bytes(b"y")

    manifest = merge_audio.write_concat_manifest(stage_dir, [first, second])

    assert manifest.read_text(encoding="ascii").splitlines() == [
        "file '{}'".format(str(first).replace("'", "''")),
        "file '{}'".format(str(second).replace("'", "''")),
    ]


def test_merge_audio_calls_ffmpeg_with_overwrite_and_cleans_stage(monkeypatch, tmp_path: Path) -> None:
    input_dir = tmp_path / "Audios" / "Merge"
    input_dir.mkdir(parents=True)
    source = input_dir / "b.mp3"
    source.write_bytes(b"src")
    output_file = tmp_path / "Outputs" / "Merge" / "merged.mp3"

    seen = {"convert": [], "ffmpeg": None, "stage_dir": None}

    monkeypatch.setattr(merge_audio, "assert_ffmpeg_available", lambda: None)

    def fake_stage_source(item, stage_dir: Path, bitrate_kbps: int, **_kwargs) -> Path:
        seen["stage_dir"] = stage_dir
        staged = stage_dir / f"{item.kind}_{item.part_number:02d}.mp3"
        staged.write_bytes(b"stage")
        seen["convert"].append((item.kind, item.part_number, bitrate_kbps, staged.name))
        return staged

    monkeypatch.setattr(merge_audio, "stage_segment", fake_stage_source)

    def fake_run_ffmpeg(args: list[str]) -> None:
        seen["ffmpeg"] = args
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(b"merged")

    monkeypatch.setattr(merge_audio, "run_ffmpeg", fake_run_ffmpeg)

    result = merge_audio.merge_audio(
        input_dir=input_dir,
        output_file=output_file,
        markers="without",
    )

    assert result == output_file
    assert seen["convert"] == [("source", 1, 192, "source_01.mp3")]
    assert seen["ffmpeg"] is not None
    assert seen["ffmpeg"][:6] == ["-y", "-f", "concat", "-safe", "0", "-i"]
    assert seen["ffmpeg"][-3:] == ["-c", "copy", str(output_file)]
    assert output_file.exists()
    assert seen["stage_dir"] is not None
    assert not seen["stage_dir"].exists()


def test_merge_audio_keeps_stage_when_requested(monkeypatch, tmp_path: Path) -> None:
    input_dir = tmp_path / "Audios" / "Merge"
    input_dir.mkdir(parents=True)
    source = input_dir / "a.mp3"
    source.write_bytes(b"src")
    output_file = tmp_path / "Outputs" / "Merge" / "merged.mp3"
    stage_root: list[Path] = []

    monkeypatch.setattr(merge_audio, "assert_ffmpeg_available", lambda: None)

    def fake_stage(item, stage_dir: Path, bitrate_kbps: int, **_kwargs) -> Path:
        stage_root[:] = [stage_dir]
        staged = stage_dir / "source_01.mp3"
        staged.write_bytes(b"x")
        return staged

    monkeypatch.setattr(merge_audio, "stage_segment", fake_stage)
    monkeypatch.setattr(merge_audio, "run_ffmpeg", lambda _args: output_file.parent.mkdir(parents=True, exist_ok=True) or output_file.write_bytes(b"merged"))

    merge_audio.merge_audio(
        input_dir=input_dir,
        output_file=output_file,
        markers="without",
        keep_temp_files=True,
    )

    assert stage_root
    assert stage_root[0].exists()


def test_wrapper_script_delegates_to_python_cli_contract() -> None:
    script = Path(__file__).resolve().parents[2] / "Requirement" / "merge_audio_with_markers.ps1"
    text = script.read_text(encoding="utf-8")

    assert "glist_pipeline.cli" in text or "-m glist_pipeline.cli" in text
    assert "merge" in text
    assert "--markers" in text
