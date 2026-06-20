from pathlib import Path

from glist_pipeline.cli import _repair_console_path


def test_repair_console_path_recovers_utf8_mojibake(tmp_path: Path) -> None:
    target = tmp_path / "PRÜFUNG.txt"
    target.write_text("ok", encoding="utf-8")

    mojibake = str(target).replace("Ü", "Ãœ")

    repaired = _repair_console_path(mojibake)

    assert repaired == target
    assert repaired.exists()


def test_repair_console_path_keeps_original_when_no_match(tmp_path: Path) -> None:
    raw = str(tmp_path / "does-not-exist-Ãœ.txt")

    repaired = _repair_console_path(raw)

    assert repaired == Path(raw)
