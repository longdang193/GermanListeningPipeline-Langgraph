from pathlib import Path

from glist_pipeline.apply_boundary_suggestions import apply_boundary_suggestions
from glist_pipeline.markdown import parse_markdown


def _mk_sentence(start: float, end: float, token: str) -> str:
    return f'<span data-start="{start}" data-end="{end}">{token}.</span>'


def _mk_block(heading: str, de_lines: list[str], en_lines: list[str], start: float, end: float) -> str:
    return "\n".join(
        [
            f"## {heading}",
            "```",
            "SSTART",
            "",
            "Listening_2",
            "",
            f"de_1: {'<br>'.join(de_lines)}",
            f"en_1: {'<br>'.join(en_lines)}",
            "note_1: <b>Key Words and Phrases</b><br>• <b>x</b> — y<br>• <b>x</b> — y<br>• <b>x</b> — y<br>• <b>x</b> — y<br>• <b>x</b> — y<br><br><b>Grammar to Remember</b><br>• <b>a</b> — b<br>• <b>a</b> — b<br>• <b>a</b> — b",
            "de_1_audio: [sound:L8-merged.mp3]",
            "de_1_wave: L8-merged.mp3",
            f"de_1_start: {start}",
            f"de_1_end: {end}",
            "EEND",
            "```",
            "",
        ]
    )


def test_apply_splits_selected_heading_and_preserves_translation_count(tmp_path: Path) -> None:
    md = tmp_path / "Listening-generated.md"
    evidence = tmp_path / "boundary_suggestions.jsonl"

    de_lines = [_mk_sentence(0.0, 16.0, "A"), _mk_sentence(16.1, 33.0, "B"), _mk_sentence(33.1, 66.5, "C")]
    en_lines = ["<b>A.</b> — A", "<b>B.</b> — B", "<b>C.</b> — C"]
    md.write_text("TARGET DECK: TEST\n\n" + _mk_block("Teil 1", de_lines, en_lines, 0.0, 66.5), encoding="utf-8")

    evidence.write_text(
        '{"heading":"Teil 1","duration_seconds":66.5,"selected":{"selected_index":2,"confidence":0.9,"reason":"split"},"uncertain":false}\n',
        encoding="utf-8",
    )

    rc = apply_boundary_suggestions(md, evidence_path=evidence)
    assert rc == 0

    doc = parse_markdown(md.read_text(encoding="utf-8"))
    assert len(doc.blocks) == 2
    assert [b.heading for b in doc.blocks] == ["Teil 1.1", "Teil 1.2"]
    assert doc.blocks[0].fields["en_1"].count("<br>") + 1 == doc.blocks[0].fields["de_1"].count("<br>") + 1
    assert doc.blocks[1].fields["en_1"].count("<br>") + 1 == doc.blocks[1].fields["de_1"].count("<br>") + 1


def test_noop_when_no_eligible_blocks(tmp_path: Path) -> None:
    md = tmp_path / "Listening-generated.md"
    evidence = tmp_path / "boundary_suggestions.jsonl"

    de_lines = [_mk_sentence(0.0, 8.0, "A"), _mk_sentence(8.1, 18.0, "B")]
    en_lines = ["<b>A.</b> — A", "<b>B.</b> — B"]
    original = "TARGET DECK: TEST\n\n" + _mk_block("Teil 2", de_lines, en_lines, 0.0, 18.0)
    md.write_text(original, encoding="utf-8")

    evidence.write_text(
        '{"heading":"Teil 2","duration_seconds":18.0,"selected":{"selected_index":1,"confidence":0.4,"reason":"uncertain"},"uncertain":true}\n',
        encoding="utf-8",
    )

    rc = apply_boundary_suggestions(md, evidence_path=evidence)
    assert rc == 0
    assert md.read_text(encoding="utf-8") == original
