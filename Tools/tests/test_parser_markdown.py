from pathlib import Path

from glist_pipeline.markdown import parse_markdown


def test_parse_markdown_reads_blocks() -> None:
    md_path = Path(__file__).resolve().parents[2] / "Outputs" / "Listening-generated.md"
    doc = parse_markdown(md_path.read_text(encoding="utf-8"))
    assert doc.metadata["has_target_deck"] is True
    assert len(doc.blocks) > 0
    first = doc.blocks[0]
    assert "de_1_start" in first.fields
    assert "de_1_end" in first.fields
