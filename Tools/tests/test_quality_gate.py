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


def test_quality_gate_flags_generic_keyword_gloss_family(tmp_path: Path) -> None:
    md_path = tmp_path / "sample_generic.md"
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
                    "• <b>Film</b> — context term<br>"
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

def test_quality_gate_flags_two_sentence_adjacent_overlap(tmp_path: Path) -> None:
    md_path = tmp_path / "overlap.md"
    md_path.write_text(
        "\n".join(
            [
                "TARGET DECK: TEST",
                "",
                "## Abschnitt 1",
                "`",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span data-start=\"0\" data-end=\"1\">A.</span><br><span data-start=\"1\" data-end=\"2\">B.</span><br><span data-start=\"2\" data-end=\"3\">C.</span>",
                "en_1: <b>A.</b> — A.<br><b>B.</b> — B.<br><b>C.</b> — C.",
                "note_1: <b>Key Words and Phrases</b><br>• <b>a</b> — a<br><br><b>Grammar to Remember</b><br>• <b>x</b> — y",
                "de_1_audio: [sound:x.mp3]",
                "de_1_wave: x.mp3",
                "de_1_start: 0",
                "de_1_end: 3",
                "EEND",
                "`",
                "",
                "## Abschnitt 2",
                "`",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span data-start=\"3\" data-end=\"4\">B.</span><br><span data-start=\"4\" data-end=\"5\">C.</span><br><span data-start=\"5\" data-end=\"6\">D.</span>",
                "en_1: <b>B.</b> — B.<br><b>C.</b> — C.<br><b>D.</b> — D.",
                "note_1: <b>Key Words and Phrases</b><br>• <b>b</b> — b<br><br><b>Grammar to Remember</b><br>• <b>x</b> — y",
                "de_1_audio: [sound:x.mp3]",
                "de_1_wave: x.mp3",
                "de_1_start: 3",
                "de_1_end: 6",
                "EEND",
                "`",
            ]
        ),
        encoding="utf-8",
    )

    issues = find_quality_issues(md_path)
    assert ("block_2_adjacent_overlap", "Abschnitt 2") in issues

def test_quality_gate_allows_one_sentence_adjacent_overlap(tmp_path: Path) -> None:
    md_path = tmp_path / "light_overlap.md"
    md_path.write_text(
        "\n".join(
            [
                "TARGET DECK: TEST",
                "",
                "## Abschnitt 1",
                "`",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span data-start=\"0\" data-end=\"1\">A.</span><br><span data-start=\"1\" data-end=\"2\">B.</span>",
                "en_1: <b>A.</b> — A.<br><b>B.</b> — B.",
                "note_1: <b>Key Words and Phrases</b><br>• <b>a</b> — a<br><br><b>Grammar to Remember</b><br>• <b>x</b> — y",
                "de_1_audio: [sound:x.mp3]",
                "de_1_wave: x.mp3",
                "de_1_start: 0",
                "de_1_end: 2",
                "EEND",
                "`",
                "",
                "## Abschnitt 2",
                "`",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span data-start=\"2\" data-end=\"3\">B.</span><br><span data-start=\"3\" data-end=\"4\">C.</span>",
                "en_1: <b>B.</b> — B.<br><b>C.</b> — C.",
                "note_1: <b>Key Words and Phrases</b><br>• <b>b</b> — b<br><br><b>Grammar to Remember</b><br>• <b>x</b> — y",
                "de_1_audio: [sound:x.mp3]",
                "de_1_wave: x.mp3",
                "de_1_start: 2",
                "de_1_end: 4",
                "EEND",
                "`",
            ]
        ),
        encoding="utf-8",
    )

    issues = find_quality_issues(md_path)
    assert ("block_2_adjacent_overlap", "Abschnitt 2") not in issues

def test_quality_gate_allows_weather_report_title(tmp_path: Path) -> None:
    md_path = tmp_path / "weather_title.md"
    md_path.write_text(
        "\n".join(
            [
                "TARGET DECK: TEST",
                "",
                "## Abschnitt 1",
                "`",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span data-start=\"0\" data-end=\"1\">Der</span> <span data-start=\"1\" data-end=\"2\">Wetterbericht.</span>",
                "en_1: <b>Der Wetterbericht.</b> — The weather report.",
                "note_1: <b>Key Words and Phrases</b><br>• <b>Wetterbericht</b> — weather report<br><br><b>Grammar to Remember</b><br>• <b>x</b> — y",
                "de_1_audio: [sound:x.mp3]",
                "de_1_wave: x.mp3",
                "de_1_start: 0",
                "de_1_end: 2",
                "EEND",
                "`",
            ]
        ),
        encoding="utf-8",
    )

    issues = find_quality_issues(md_path)
    assert not any(code == "block_1_adjacent_overlap" for code, _ in issues)
