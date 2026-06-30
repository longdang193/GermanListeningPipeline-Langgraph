import json

import glist_pipeline.semantic_generate as semantic_generate


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
