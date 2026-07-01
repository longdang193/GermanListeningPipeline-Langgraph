from pathlib import Path
from types import SimpleNamespace

from glist_pipeline import cli
from glist_pipeline import legacy_runner


def test_run_menu_stays_open_after_action(monkeypatch, capsys) -> None:
    answers = iter(["1", "3"])
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


def test_run_legacy_uses_static_entrypoint_when_frozen(monkeypatch) -> None:
    seen: dict[str, list[str]] = {}

    def fake_main() -> None:
        seen["argv"] = legacy_runner.sys.argv[:]

    monkeypatch.setattr(legacy_runner.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        legacy_runner,
        "_load_legacy_entrypoint",
        lambda _name: SimpleNamespace(main=fake_main),
    )

    assert legacy_runner.run_legacy("split_and_subtitle_4.py", ["out.md"]) == 0
    assert seen["argv"] == ["split_and_subtitle_4.py", "out.md"]
