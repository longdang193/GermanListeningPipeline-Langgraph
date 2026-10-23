from pathlib import Path
from types import SimpleNamespace

from glist_pipeline import cli
from glist_pipeline import legacy_runner


def test_run_menu_stays_open_after_action(monkeypatch, capsys) -> None:
    answers = iter(["1", "4"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    calls = {"count": 0}

    def fake_action() -> int:
        calls["count"] += 1
        return 0

    monkeypatch.setattr(cli, "run_menu_action_1", fake_action)

    assert cli.run_menu() == 0
    assert calls["count"] == 1
    out = capsys.readouterr().out
    assert "Action complete. Choose next action or exit." in out
    assert out.count("German_Listening MVP") == 2
    assert "3) MERGE AUDIOS" in out
    assert "O) OPEN OUTPUTS" in out
    assert "4) EXIT" in out


def test_menu_action_1_reports_generation_errors_without_raising(monkeypatch, capsys) -> None:
    answers = iter(["transcript.json", "audio.ogg", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(
        cli,
        "_run_action_create_blocks",
        lambda *_args: (_ for _ in ()).throw(IndexError("invalid transcript layout")),
    )

    assert cli.run_menu_action_1() == 1
    assert "Action failed: invalid transcript layout" in capsys.readouterr().out


def test_run_menu_opens_outputs_folder(monkeypatch) -> None:
    answers = iter(["O", "4"])
    opened: list[Path] = []
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(cli.os, "startfile", opened.append)

    assert cli.run_menu() == 0
    assert opened == [cli.REPO_ROOT / "Outputs"]


def test_action_2_routes_semantic_blocks_to_classic_split(monkeypatch, tmp_path, capsys) -> None:
    md_path = tmp_path / "Listening-generated.draft.md"
    md_path.write_text("## Abschnitt 1 — Foo\n", encoding="utf-8")
    chosen: list[tuple[str, Path]] = []

    def fake_mode_impl(mode: str):
        return SimpleNamespace(split=lambda path: chosen.append((mode, path)) or 0)

    monkeypatch.setattr(cli, "_mode_impl", fake_mode_impl)
    monkeypatch.setattr(cli, "_ensure_blocks_audio_available", lambda _path: 0)

    assert cli._run_action_create_audios_from_blocks(md_path) == 0
    assert chosen == [("classic", md_path)]
    out = capsys.readouterr().out
    assert "Detected blocks mode: semantic" in out
    assert "Using deterministic splitter: classic" in out


def test_ensure_repo_audio_copies_external_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    source = tmp_path / "Downloads" / "lesson.mp3"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"mp3")

    target = cli._ensure_repo_audio(source)

    assert target == tmp_path / "Audios" / "lesson.mp3"
    assert target.read_bytes() == b"mp3"


def test_ensure_repo_audio_converts_non_mp3_input(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    source = tmp_path / "Downloads" / "lesson.ogg"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"ogg")
    seen: list[list[str]] = []

    def fake_run_ffmpeg(args: list[str]) -> None:
        seen.append(args)
        Path(args[-1]).write_bytes(b"mp3")

    monkeypatch.setattr(cli.merge_audio_lib, "run_ffmpeg", fake_run_ffmpeg)

    target = cli._ensure_repo_audio(source)

    assert target == tmp_path / "Audios" / "lesson.mp3"
    assert target.read_bytes() == b"mp3"
    assert seen == [[
        "-y",
        "-i",
        str(source),
        "-vn",
        "-codec:a",
        "libmp3lame",
        str(target),
    ]]


def test_create_blocks_stages_selected_transcript_and_audio_for_legacy_generator(
    monkeypatch, tmp_path
) -> None:
    transcript = tmp_path / "Downloads" / "selected.json"
    audio = tmp_path / "Downloads" / "selected.ogg"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text('{"segments": []}', encoding="utf-8")
    audio.write_bytes(b"ogg")
    output = tmp_path / "Outputs" / "Listening-generated.md"
    seen: dict[str, Path] = {}

    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cli, "OUTPUT_MD", output)
    monkeypatch.setattr(cli, "SEMANTIC_DRAFT_MD", output)
    monkeypatch.setattr(cli, "detect_transcript_profile", lambda _path: SimpleNamespace(
        marker_capable=False,
        classic_capable=True,
        reason="fixture",
    ))
    monkeypatch.setattr(cli, "route_mode", lambda _mode, _profile: "classic")
    def fake_generate() -> int:
        seen.update({
            "transcript": tmp_path / "Transcripts" / "selected.json",
            "audio": tmp_path / "Audios" / "selected.mp3",
        })
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("TARGET DECK: TEST\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli.classic, "generate", fake_generate)
    monkeypatch.setattr(cli, "_run_shared_postprocess", lambda _path: 0)
    monkeypatch.setattr(cli, "append_router_run_record", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_set_latest", lambda _path: None)
    monkeypatch.setattr(
        cli.merge_audio_lib,
        "run_ffmpeg",
        lambda args: Path(args[-1]).write_bytes(b"mp3"),
    )

    assert cli._run_action_create_blocks(transcript, audio, "classic") == 0
    assert seen["transcript"].exists()
    assert seen["audio"].exists()
    assert seen["transcript"].read_text(encoding="utf-8") == transcript.read_text(encoding="utf-8")


def test_run_legacy_uses_static_entrypoint_when_frozen(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_main() -> None:
        seen["argv"] = legacy_runner.sys.argv[:]
        seen["cwd"] = Path.cwd()

    caller_cwd = Path.cwd().parent
    monkeypatch.setattr(legacy_runner.sys, "frozen", True, raising=False)
    monkeypatch.chdir(caller_cwd)
    monkeypatch.setattr(
        legacy_runner,
        "_load_legacy_entrypoint",
        lambda _name: SimpleNamespace(main=fake_main),
    )

    assert legacy_runner.run_legacy("split_and_subtitle_4.py", ["out.md"]) == 0
    assert seen["argv"] == ["split_and_subtitle_4.py", "out.md"]
    assert seen["cwd"] == legacy_runner.REPO_ROOT
    assert Path.cwd() == caller_cwd


def test_menu_action_3_dispatches_to_merge_engine(monkeypatch, capsys) -> None:
    answers = iter(["Audios/Merge", "2", "Outputs/Merge/out.mp3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    seen: dict[str, object] = {}

    def fake_merge_audio(**kwargs):
        seen.update(kwargs)
        return Path("Outputs/Merge/out.mp3")

    monkeypatch.setattr(cli.merge_audio_lib, "merge_audio", fake_merge_audio)

    assert cli.run_menu_action_3() == 0
    assert seen["markers"] == "without"
    assert seen["prompt_mode"] == "generated"
    out = capsys.readouterr().out
    assert "Merged file created at:" in out


def test_build_parser_accepts_merge_command() -> None:
    parser = cli.build_parser()

    args = parser.parse_args([
        "merge",
        "--input-dir",
        "Audios/Merge",
        "--output-file",
        "Outputs/Merge/out.mp3",
        "--markers",
        "without",
    ])

    assert args.command == "merge"
    assert args.markers == "without"
    assert args.func is cli.cmd_merge


def test_cmd_merge_rejects_prompt_mode_without_markers(capsys) -> None:
    args = SimpleNamespace(
        markers="without",
        prompt_mode="recorded",
        prompt_dir="Audios/MergePrompts",
        voice_name="",
        list_voices=False,
    )

    assert cli.cmd_merge(args) == 2
    assert "--prompt-mode is only valid with --markers with" in capsys.readouterr().out


def test_cmd_merge_dispatches_to_shared_engine(monkeypatch, capsys) -> None:
    args = SimpleNamespace(
        markers="with",
        prompt_mode="generated",
        prompt_dir="",
        voice_name="",
        input_dir="Audios/Merge",
        output_file="Outputs/Merge/out.mp3",
        bitrate_kbps=192,
        keep_temp_files=False,
        list_voices=False,
    )
    seen: dict[str, object] = {}

    def fake_merge_audio_from_args(passed_args):
        seen["args"] = passed_args
        return Path("Outputs/Merge/out.mp3")

    monkeypatch.setattr(cli.merge_audio_lib, "merge_audio_from_args", fake_merge_audio_from_args)

    assert cli.cmd_merge(args) == 0
    assert seen["args"] is args
    assert "Merged file created at:" in capsys.readouterr().out
