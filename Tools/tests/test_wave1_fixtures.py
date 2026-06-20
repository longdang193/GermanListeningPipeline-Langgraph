import json
from pathlib import Path


def test_fixture_manifest_loads() -> None:
    root = Path(__file__).parent / "fixtures"
    data = json.loads((root / "fixture_manifest.json").read_text(encoding="utf-8"))
    assert data["classic_expected"]["teil1_headings"] == 5
    assert data["audio_selection"]["expected_latest"] == "sample_new.mp3"


def test_sample_transcript_has_segments() -> None:
    root = Path(__file__).parent / "fixtures"
    transcript = json.loads((root / "sample_transcript.json").read_text(encoding="utf-8"))
    assert "segments" in transcript
    assert len(transcript["segments"]) >= 2
    first_word = transcript["segments"][0]["words"][0]
    assert {"word", "start", "end"}.issubset(first_word.keys())


def test_latest_audio_selection_fixture() -> None:
    root = Path(__file__).parent / "fixtures" / "audio_mtime"
    files = sorted(root.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    assert files
    assert files[0].name == "sample_new.mp3"
