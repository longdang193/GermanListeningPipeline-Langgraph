from pathlib import Path

from glist_pipeline.cli import _detect_blocks_mode, _repair_console_path, _split_mode_for_blocks_mode


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


def test_detect_blocks_mode_returns_semantic_for_abschnitt_blocks(tmp_path: Path) -> None:
    md = tmp_path / "semantic.md"
    md.write_text("TARGET DECK: TEST\n\n## Abschnitt 1 — Januar\n```\nListening_2\n```\n", encoding="utf-8")

    assert _detect_blocks_mode(md) == "semantic"


def test_detect_blocks_mode_returns_classic_for_telc_blocks(tmp_path: Path) -> None:
    md = tmp_path / "classic.md"
    md.write_text("## Teil 2 — Q&A 46\nAufgabe 56\nListening_2\n", encoding="utf-8")

    assert _detect_blocks_mode(md) == "classic"


def test_split_mode_for_semantic_blocks_uses_marker_splitter() -> None:
    assert _split_mode_for_blocks_mode("semantic") == "marker"
