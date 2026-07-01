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


def test_generate_semantic_filters_spoken_b_eins_intro(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Zertifikat", "start": 0.0, "end": 0.2},
                            {"type": "word", "text": "B", "start": 0.2, "end": 0.3},
                            {"type": "word", "text": "eins,", "start": 0.3, "end": 0.5},
                            {"type": "word", "text": "Modul", "start": 0.5, "end": 0.7},
                            {"type": "word", "text": "Hören,", "start": 0.7, "end": 0.9},
                            {"type": "word", "text": "Modelsatz.", "start": 0.9, "end": 1.1},
                            {"type": "word", "text": "Hallo", "start": 2.0, "end": 2.2},
                            {"type": "word", "text": "Jan,", "start": 2.2, "end": 2.4},
                            {"type": "word", "text": "hier", "start": 2.4, "end": 2.6},
                            {"type": "word", "text": "ist", "start": 2.6, "end": 2.8},
                            {"type": "word", "text": "Frank.", "start": 2.8, "end": 3.0}
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
    assert "Zertifikat B eins, Modul Hören, Modelsatz." not in rendered
    assert "Hallo Jan, hier ist Frank." in rendered

def test_generate_semantic_filters_repeat_marker(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Hallo.", "start": 0.0, "end": 0.4},
                            {"type": "word", "text": "Sie", "start": 1.0, "end": 1.1},
                            {"type": "word", "text": "hören", "start": 1.1, "end": 1.2},
                            {"type": "word", "text": "jetzt", "start": 1.2, "end": 1.3},
                            {"type": "word", "text": "den", "start": 1.3, "end": 1.4},
                            {"type": "word", "text": "Text", "start": 1.4, "end": 1.5},
                            {"type": "word", "text": "noch", "start": 1.5, "end": 1.6},
                            {"type": "word", "text": "einmal.", "start": 1.6, "end": 1.7},
                            {"type": "word", "text": "Tschüss.", "start": 2.0, "end": 2.4}
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
    assert "Sie hören jetzt den Text noch einmal." not in rendered
    assert "Tschüss." in rendered


def test_generate_semantic_filters_single_play_instruction_pair(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Sie", "start": 0.0, "end": 0.1},
                            {"type": "word", "text": "hören", "start": 0.1, "end": 0.2},
                            {"type": "word", "text": "den", "start": 0.2, "end": 0.3},
                            {"type": "word", "text": "Text", "start": 0.3, "end": 0.4},
                            {"type": "word", "text": "einmal.", "start": 0.4, "end": 0.5},
                            {"type": "word", "text": "Dazu", "start": 0.6, "end": 0.7},
                            {"type": "word", "text": "lösen", "start": 0.7, "end": 0.8},
                            {"type": "word", "text": "Sie", "start": 0.8, "end": 0.9},
                            {"type": "word", "text": "fünf", "start": 0.9, "end": 1.0},
                            {"type": "word", "text": "Aufgaben.", "start": 1.0, "end": 1.1},
                            {"type": "word", "text": "Sie", "start": 2.0, "end": 2.1},
                            {"type": "word", "text": "nehmen", "start": 2.1, "end": 2.2},
                            {"type": "word", "text": "teil.", "start": 2.2, "end": 2.3}
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
    assert "Sie hören den Text einmal." not in rendered
    assert "Dazu lösen Sie fünf Aufgaben." not in rendered
    assert "Sie nehmen teil." in rendered


def test_generate_semantic_filters_conversation_instruction_pair(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Sie", "start": 0.0, "end": 0.1},
                            {"type": "word", "text": "hören", "start": 0.1, "end": 0.2},
                            {"type": "word", "text": "das", "start": 0.2, "end": 0.3},
                            {"type": "word", "text": "Gespräch", "start": 0.3, "end": 0.4},
                            {"type": "word", "text": "einmal.", "start": 0.4, "end": 0.5},
                            {"type": "word", "text": "Dazu", "start": 0.6, "end": 0.7},
                            {"type": "word", "text": "lösen", "start": 0.7, "end": 0.8},
                            {"type": "word", "text": "Sie", "start": 0.8, "end": 0.9},
                            {"type": "word", "text": "sieben", "start": 0.9, "end": 1.0},
                            {"type": "word", "text": "Aufgaben.", "start": 1.0, "end": 1.1},
                            {"type": "word", "text": "Sie", "start": 2.0, "end": 2.1},
                            {"type": "word", "text": "sind", "start": 2.1, "end": 2.2},
                            {"type": "word", "text": "da.", "start": 2.2, "end": 2.3}
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
    assert "Sie hören das Gespräch einmal." not in rendered
    assert "Dazu lösen Sie sieben Aufgaben." not in rendered
    assert "Sie sind da." in rendered


def test_generate_semantic_filters_discussion_instruction_group(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Sie", "start": 0.0, "end": 0.1},
                            {"type": "word", "text": "hören", "start": 0.1, "end": 0.2},
                            {"type": "word", "text": "die", "start": 0.2, "end": 0.3},
                            {"type": "word", "text": "Diskussion", "start": 0.3, "end": 0.4},
                            {"type": "word", "text": "zweimal.", "start": 0.4, "end": 0.5},
                            {"type": "word", "text": "Dazu", "start": 0.6, "end": 0.7},
                            {"type": "word", "text": "lösen", "start": 0.7, "end": 0.8},
                            {"type": "word", "text": "Sie", "start": 0.8, "end": 0.9},
                            {"type": "word", "text": "acht", "start": 0.9, "end": 1.0},
                            {"type": "word", "text": "Aufgaben.", "start": 1.0, "end": 1.1},
                            {"type": "word", "text": "Ordnen", "start": 1.2, "end": 1.3},
                            {"type": "word", "text": "Sie", "start": 1.3, "end": 1.4},
                            {"type": "word", "text": "die", "start": 1.4, "end": 1.5},
                            {"type": "word", "text": "Aussagen", "start": 1.5, "end": 1.6},
                            {"type": "word", "text": "zu.", "start": 1.6, "end": 1.7},
                            {"type": "word", "text": "Wer", "start": 1.8, "end": 1.9},
                            {"type": "word", "text": "sagt", "start": 1.9, "end": 2.0},
                            {"type": "word", "text": "was?", "start": 2.0, "end": 2.1},
                            {"type": "word", "text": "Der", "start": 3.0, "end": 3.1},
                            {"type": "word", "text": "Moderator", "start": 3.1, "end": 3.2},
                            {"type": "word", "text": "spricht.", "start": 3.2, "end": 3.3}
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
    assert "Sie hören die Diskussion zweimal." not in rendered
    assert "Dazu lösen Sie acht Aufgaben." not in rendered
    assert "Ordnen Sie die Aussagen zu." not in rendered
    assert "Wer sagt was?" not in rendered
    assert "Der Moderator spricht." in rendered

def test_generate_semantic_filters_weather_report_listener_prompt(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Sie", "start": 0.0, "end": 0.1},
                            {"type": "word", "text": "hören", "start": 0.1, "end": 0.2},
                            {"type": "word", "text": "den", "start": 0.2, "end": 0.3},
                            {"type": "word", "text": "Wetterbericht", "start": 0.3, "end": 0.4},
                            {"type": "word", "text": "im", "start": 0.4, "end": 0.5},
                            {"type": "word", "text": "Radio.", "start": 0.5, "end": 0.6},
                            {"type": "word", "text": "Der", "start": 1.0, "end": 1.1},
                            {"type": "word", "text": "Wetterbericht.", "start": 1.1, "end": 1.2},
                            {"type": "word", "text": "Und", "start": 2.0, "end": 2.1},
                            {"type": "word", "text": "hier", "start": 2.1, "end": 2.2},
                            {"type": "word", "text": "noch", "start": 2.2, "end": 2.3},
                            {"type": "word", "text": "die", "start": 2.3, "end": 2.4},
                            {"type": "word", "text": "aktuellen", "start": 2.4, "end": 2.5},
                            {"type": "word", "text": "Wetteraussichten.", "start": 2.5, "end": 2.7}
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
    assert "Sie hören den Wetterbericht im Radio." not in rendered
    assert "Der Wetterbericht." in rendered
    assert "Und hier noch die aktuellen Wetteraussichten." in rendered

def test_words_to_sentences_keeps_dr_becker_together() -> None:
    words = [
        {"text": "Hallo", "start": 0.0, "end": 0.1},
        {"text": "Frau", "start": 0.1, "end": 0.2},
        {"text": "Stein,", "start": 0.2, "end": 0.3},
        {"text": "hier", "start": 0.3, "end": 0.4},
        {"text": "ist", "start": 0.4, "end": 0.5},
        {"text": "die", "start": 0.5, "end": 0.6},
        {"text": "Praxis", "start": 0.6, "end": 0.7},
        {"text": "Dr.", "start": 0.7, "end": 0.8},
        {"text": "Becker.", "start": 0.8, "end": 0.9},
    ]

    sentences = semantic_generate.words_to_sentences(words)

    assert len(sentences) == 1
    assert semantic_generate.sentence_plain(sentences[0]) == "Hallo Frau Stein, hier ist die Praxis Dr. Becker."

def test_generate_semantic_removes_replayed_second_pass(monkeypatch, tmp_path) -> None:
    transcript = tmp_path / "selected.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "words": [
                            {"type": "word", "text": "Hallo", "start": 0.0, "end": 0.2},
                            {"type": "word", "text": "Jan,", "start": 0.2, "end": 0.4},
                            {"type": "word", "text": "hier", "start": 0.4, "end": 0.6},
                            {"type": "word", "text": "ist", "start": 0.6, "end": 0.8},
                            {"type": "word", "text": "Frank.", "start": 0.8, "end": 1.0},
                            {"type": "word", "text": "Wir", "start": 10.0, "end": 10.2},
                            {"type": "word", "text": "fahren", "start": 10.2, "end": 10.4},
                            {"type": "word", "text": "im", "start": 10.4, "end": 10.6},
                            {"type": "word", "text": "Sommer.", "start": 10.6, "end": 11.0},
                            {"type": "word", "text": "Tschüss.", "start": 34.5, "end": 35.0},
                            {"type": "word", "text": "Sie", "start": 40.0, "end": 40.1},
                            {"type": "word", "text": "hören", "start": 40.1, "end": 40.2},
                            {"type": "word", "text": "jetzt", "start": 40.2, "end": 40.3},
                            {"type": "word", "text": "den", "start": 40.3, "end": 40.4},
                            {"type": "word", "text": "Text", "start": 40.4, "end": 40.5},
                            {"type": "word", "text": "noch", "start": 40.5, "end": 40.6},
                            {"type": "word", "text": "einmal.", "start": 40.6, "end": 41.0},
                            {"type": "word", "text": "Hallo", "start": 50.0, "end": 50.2},
                            {"type": "word", "text": "Jan,", "start": 50.2, "end": 50.4},
                            {"type": "word", "text": "hier", "start": 50.4, "end": 50.6},
                            {"type": "word", "text": "ist", "start": 50.6, "end": 50.8},
                            {"type": "word", "text": "Frank.", "start": 50.8, "end": 51.0},
                            {"type": "word", "text": "Wir", "start": 60.0, "end": 60.2},
                            {"type": "word", "text": "fahren", "start": 60.2, "end": 60.4},
                            {"type": "word", "text": "im", "start": 60.4, "end": 60.6},
                            {"type": "word", "text": "Sommer.", "start": 60.6, "end": 61.0},
                            {"type": "word", "text": "Tschüss.", "start": 84.5, "end": 85.0},
                            {"type": "word", "text": "Hallo", "start": 100.0, "end": 100.2},
                            {"type": "word", "text": "Frau", "start": 100.2, "end": 100.4},
                            {"type": "word", "text": "Stein,", "start": 100.4, "end": 100.6},
                            {"type": "word", "text": "hier", "start": 100.6, "end": 100.8},
                            {"type": "word", "text": "ist", "start": 100.8, "end": 101.0},
                            {"type": "word", "text": "die", "start": 101.0, "end": 101.2},
                            {"type": "word", "text": "Praxis", "start": 101.2, "end": 101.4},
                            {"type": "word", "text": "Dr.", "start": 101.4, "end": 101.6},
                            {"type": "word", "text": "Becker.", "start": 101.6, "end": 102.0},
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
    assert rendered.count("Hallo Jan, hier ist Frank.") == 1
    assert "Hallo Frau Stein, hier ist die Praxis Dr. Becker." in rendered
    assert rendered.count("## Abschnitt") == 2

def test_prepare_sentences_drops_gap_triggered_replay_cluster() -> None:
    words = [
        {"text": "A.", "start": 0.0, "end": 1.0},
        {"text": "B.", "start": 2.0, "end": 3.0},
        {"text": "C.", "start": 4.0, "end": 5.0},
        {"text": "D.", "start": 6.0, "end": 7.0},
        {"text": "Intro.", "start": 18.0, "end": 19.0},
        {"text": "B.", "start": 20.0, "end": 21.0},
        {"text": "C.", "start": 22.0, "end": 23.0},
        {"text": "D.", "start": 24.0, "end": 25.0},
        {"text": "Neu.", "start": 26.0, "end": 27.0},
    ]

    sentences = semantic_generate._prepare_sentences(words)
    plain = [semantic_generate.sentence_plain(sentence) for sentence in sentences]

    assert plain == ["A.", "B.", "C.", "D.", "Neu."]

def test_prepare_sentences_drops_replay_teaser_before_duplicate_run() -> None:
    words = [
        {"text": "A.", "start": 0.0, "end": 1.0},
        {"text": "B.", "start": 2.0, "end": 3.0},
        {"text": "C.", "start": 4.0, "end": 5.0},
        {"text": "Sie", "start": 10.0, "end": 10.1},
        {"text": "hören", "start": 10.1, "end": 10.2},
        {"text": "jetzt", "start": 10.2, "end": 10.3},
        {"text": "den", "start": 10.3, "end": 10.4},
        {"text": "Text", "start": 10.4, "end": 10.5},
        {"text": "noch", "start": 10.5, "end": 10.6},
        {"text": "einmal.", "start": 10.6, "end": 11.0},
        {"text": "Intro.", "start": 12.0, "end": 13.0},
        {"text": "B.", "start": 14.0, "end": 15.0},
        {"text": "C.", "start": 16.0, "end": 17.0},
        {"text": "Neu.", "start": 18.0, "end": 19.0},
    ]

    sentences = semantic_generate._prepare_sentences(words)
    plain = [semantic_generate.sentence_plain(sentence) for sentence in sentences]

    assert plain == ["A.", "B.", "C.", "Neu."]

def test_prepare_sentences_drops_replay_with_punctuation_only_drift() -> None:
    words = [
        {"text": "Radio", "start": 0.0, "end": 0.1},
        {"text": "Liberty,", "start": 0.1, "end": 0.2},
        {"text": "alle", "start": 0.2, "end": 0.3},
        {"text": "fünfzehn", "start": 0.3, "end": 0.4},
        {"text": "Minuten.", "start": 0.4, "end": 0.5},
        {"text": "Sie", "start": 1.0, "end": 1.1},
        {"text": "hören", "start": 1.1, "end": 1.2},
        {"text": "jetzt", "start": 1.2, "end": 1.3},
        {"text": "den", "start": 1.3, "end": 1.4},
        {"text": "Text", "start": 1.4, "end": 1.5},
        {"text": "noch", "start": 1.5, "end": 1.6},
        {"text": "einmal.", "start": 1.6, "end": 1.7},
        {"text": "Radio", "start": 2.0, "end": 2.1},
        {"text": "Liberty", "start": 2.1, "end": 2.2},
        {"text": "alle", "start": 2.2, "end": 2.3},
        {"text": "fünfzehn", "start": 2.3, "end": 2.4},
        {"text": "Minuten.", "start": 2.4, "end": 2.5},
        {"text": "Neu.", "start": 3.0, "end": 3.1},
    ]

    sentences = semantic_generate._prepare_sentences(words)
    plain = [semantic_generate.sentence_plain(sentence) for sentence in sentences]

    assert plain == ["Radio Liberty, alle fünfzehn Minuten.", "Neu."]

def test_split_into_blocks_splits_on_large_gap_before_item_start() -> None:
    sentences = [
        [{"text": "A.", "start": 0.0, "end": 25.0}],
        [{"text": "Gleis", "start": 50.0, "end": 50.2}, {"text": "dreizehn.", "start": 50.2, "end": 60.0}],
        [{"text": "Weiter.", "start": 60.5, "end": 70.0}],
    ]

    blocks = semantic_generate.split_into_blocks(sentences)

    assert len(blocks) == 2
    assert semantic_generate.sentence_plain(blocks[0][0]) == "A."
    assert semantic_generate.sentence_plain(blocks[1][0]) == "Gleis dreizehn."

def test_split_into_blocks_splits_before_strong_opener() -> None:
    sentences = [
        [{"text": "Gleis", "start": 0.0, "end": 0.2}, {"text": "dreizehn.", "start": 0.2, "end": 10.0}],
        [{"text": "Erste", "start": 10.5, "end": 10.7}, {"text": "Klasse.", "start": 10.7, "end": 22.0}],
        [{"text": "Eine", "start": 23.0, "end": 23.2}, {"text": "wichtige", "start": 23.2, "end": 23.5}, {"text": "Information.", "start": 23.5, "end": 27.0}],
    ]

    blocks = semantic_generate.split_into_blocks(sentences)

    assert len(blocks) == 2
    assert semantic_generate.sentence_plain(blocks[1][0]) == "Eine wichtige Information."


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


