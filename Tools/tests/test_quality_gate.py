from pathlib import Path

from glist_pipeline.quality_gate import find_quality_issues


def test_quality_gate_flags_non_conservative_keyword_gloss(tmp_path: Path) -> None:
    md_path = tmp_path / "sample.md"
    md_path.write_text(
        "\n".join(
            [
                "TARGET DECK: TEST",
                "",
                "## Abschnitt 1",
                "```",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span>Text.</span>",
                "en_1: <b>Text.</b> — Text.",
                (
                    "note_1: <b>Key Words and Phrases</b><br>"
                    "• <b>Mistvieh</b> — damn pest<br>"
                    "<br><b>Grammar to Remember</b><br>"
                    "• <b>x</b> — y"
                ),
                "de_1_audio: [sound:x.mp3]",
                "de_1_wave: x.mp3",
                "de_1_start: 0",
                "de_1_end: 1",
                "EEND",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    issues = find_quality_issues(md_path)
    assert ("block_1_keyword_gloss_policy", "Abschnitt 1") in issues


def test_quality_gate_flags_non_conservative_short_fragment_translation(tmp_path: Path) -> None:
    md_path = tmp_path / "sample_translation.md"
    md_path.write_text(
        "\n".join(
            [
                "TARGET DECK: TEST",
                "",
                "## Abschnitt 1",
                "```",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span>Mistvieh.</span>",
                "en_1: <b>Mistvieh.</b> — Damn critter.",
                (
                    "note_1: <b>Key Words and Phrases</b><br>"
                    "• <b>Mistvieh</b> — pest<br>"
                    "<br><b>Grammar to Remember</b><br>"
                    "• <b>x</b> — y"
                ),
                "de_1_audio: [sound:x.mp3]",
                "de_1_wave: x.mp3",
                "de_1_start: 0",
                "de_1_end: 1",
                "EEND",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    issues = find_quality_issues(md_path)
    assert ("block_1_translation_policy", "Abschnitt 1") in issues
