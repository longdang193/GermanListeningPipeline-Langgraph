import json
from pathlib import Path

import glist_pipeline.semantic_generate as semantic_generate
from glist_pipeline import cli
from glist_pipeline.mode_router import TranscriptProfile


def test_generate_semantic_uses_explicit_paths(monkeypatch, tmp_path, capsys) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Hallo.", "start": 0.0, "end": 1.0}
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "Listening-generated.md"

    monkeypatch.setattr(semantic_generate, "OUTPUT", out)

    def fail_latest_transcript():
        raise AssertionError("latest_transcript should not be used")

    def fail_latest_audio():
        raise AssertionError("latest_audio_name should not be used")

    monkeypatch.setattr(semantic_generate, "latest_transcript", fail_latest_transcript)
    monkeypatch.setattr(semantic_generate, "latest_audio_name", fail_latest_audio)

    assert semantic_generate.generate_semantic(
        transcript_path=transcript,
        audio_name="chosen.mp3",
    ) == 0

    rendered = out.read_text(encoding="utf-8")
    assert "[sound:chosen.mp3]" in rendered
    assert "de_1_wave: chosen.mp3" in rendered
    out_text = capsys.readouterr().out
    assert f"Semantic source transcript: {transcript}" in out_text
    assert "Semantic source audio: chosen.mp3" in out_text
    assert "Semantic split summary:" in out_text
    assert "target~45s" in out_text
    assert "≈" not in out_text
    assert "sentences=1" in out_text

def test_generate_semantic_filters_instruction_scaffold(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Zertifikat", "start": 0.0, "end": 0.2},
                            {"type": "word", "text": "B1.", "start": 0.2, "end": 0.4},
                            {"type": "word", "text": "Sie", "start": 1.0, "end": 1.1},
                            {"type": "word", "text": "hören", "start": 1.1, "end": 1.3},
                            {"type": "word", "text": "nun", "start": 1.3, "end": 1.4},
                            {"type": "word", "text": "fünf", "start": 1.4, "end": 1.6},
                            {"type": "word", "text": "kurze", "start": 1.6, "end": 1.8},
                            {"type": "word", "text": "Texte.", "start": 1.8, "end": 2.0},
                            {"type": "word", "text": "Hallo", "start": 3.0, "end": 3.2},
                            {"type": "word", "text": "Jan,", "start": 3.2, "end": 3.4},
                            {"type": "word", "text": "hier", "start": 3.4, "end": 3.6},
                            {"type": "word", "text": "ist", "start": 3.6, "end": 3.8},
                            {"type": "word", "text": "Frank.", "start": 3.8, "end": 4.0},
                            {"type": "word", "text": "Achtung,", "start": 5.0, "end": 5.2},
                            {"type": "word", "text": "Autofahrer...", "start": 5.2, "end": 5.5}
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "Listening-generated.md"
    monkeypatch.setattr(semantic_generate, "OUTPUT", out)

    assert semantic_generate.generate_semantic(transcript_path=transcript, audio_name="chosen.mp3") == 0

    rendered = out.read_text(encoding="utf-8")
    assert "Zertifikat" not in rendered
    assert "Sie hören nun fünf kurze Texte." not in rendered
    assert "Hallo Jan, hier ist Frank." in rendered
    assert "Achtung, Autofahrer..." in rendered


def _write_semantic_block(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "TARGET DECK: TEST",
                "",
                "## Abschnitt 1 — Hallo Jan",
                "```",
                "SSTART",
                "",
                "Listening_2",
                "",
                "de_1: <span data-start=\"0.0\" data-end=\"0.5\">Hallo.</span>",
                "en_1: <b>Hallo.</b> — TODO: add English translation.",
                "note_1: <b>Key Words and Phrases</b><br>• <b>TODO_TERM_1</b> — Add glossary note.<br><br><b>Grammar to Remember</b><br>• <b>TODO_GRAMMAR_1</b> — Add grammar explanation.",
                "de_1_audio: [sound:chosen.mp3]",
                "de_1_wave: chosen.mp3",
                "de_1_start: 0.0",
                "de_1_end: 0.5",
                "EEND",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_hitl_semantic_promotes_draft_to_final(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    audio = tmp_path / "chosen.mp3"
    transcript.write_text("{}", encoding="utf-8")
    audio.write_text("x", encoding="utf-8")
    draft = tmp_path / "Listening-generated.draft.md"
    final = tmp_path / "Listening-generated.md"

    monkeypatch.setattr(cli, "OUTPUT_MD", final)
    monkeypatch.setattr(cli, "SEMANTIC_DRAFT_MD", draft)
    monkeypatch.setattr(cli, "load_taxonomy", lambda _p: ["topic_daily_life"])
    monkeypatch.setattr(cli, "detect_transcript_profile", lambda _p: TranscriptProfile(marker_capable=False, classic_capable=True, reason="no markers"))
    monkeypatch.setattr(cli, "append_router_run_record", lambda *_a, **_k: None)
    monkeypatch.setattr(cli, "append_review_log", lambda *_a, **_k: None)
    monkeypatch.setattr("builtins.input", lambda _p: "1")
    monkeypatch.setattr(cli, "_set_latest", lambda _p: None)
    monkeypatch.setattr(
        cli,
        "enrich_file_in_place",
        lambda path: path.write_text(
            path.read_text(encoding="utf-8")
            .replace("TODO: add English translation.", "Hello.")
            .replace("TODO_TERM_1", "Hallo")
            .replace("Add glossary note.", "hello")
            .replace("TODO_GRAMMAR_1", "Greeting")
            .replace("Add grammar explanation.", "Simple greeting."),
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(cli, "generate_semantic", lambda **_k: (_write_semantic_block(draft), 0)[1])

    assert cli._run_action_create_blocks(transcript, audio, "hitl") == 0
    assert draft.exists()
    assert final.exists()
    assert "TODO:" not in draft.read_text(encoding="utf-8")
    assert draft.read_text(encoding="utf-8") == final.read_text(encoding="utf-8")


def test_hitl_semantic_failure_keeps_old_final(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    audio = tmp_path / "chosen.mp3"
    transcript.write_text("{}", encoding="utf-8")
    audio.write_text("x", encoding="utf-8")
    draft = tmp_path / "Listening-generated.draft.md"
    final = tmp_path / "Listening-generated.md"
    final.write_text("old final", encoding="utf-8")

    monkeypatch.setattr(cli, "OUTPUT_MD", final)
    monkeypatch.setattr(cli, "SEMANTIC_DRAFT_MD", draft)
    monkeypatch.setattr(cli, "load_taxonomy", lambda _p: ["topic_daily_life"])
    monkeypatch.setattr(cli, "detect_transcript_profile", lambda _p: TranscriptProfile(marker_capable=False, classic_capable=True, reason="no markers"))
    monkeypatch.setattr(cli, "append_router_run_record", lambda *_a, **_k: None)
    monkeypatch.setattr(cli, "append_review_log", lambda *_a, **_k: None)
    monkeypatch.setattr("builtins.input", lambda _p: "1")
    monkeypatch.setattr(cli, "_set_latest", lambda _p: None)
    monkeypatch.setattr(cli, "generate_semantic", lambda **_k: (_write_semantic_block(draft), 0)[1])
    monkeypatch.setattr(cli, "enrich_file_in_place", lambda _path: 0)

    assert cli._run_action_create_blocks(transcript, audio, "hitl") == 2
    assert draft.exists()
    assert final.read_text(encoding="utf-8") == "old final"


