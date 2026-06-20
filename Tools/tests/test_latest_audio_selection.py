from pathlib import Path

from glist_pipeline.parser import latest_audio


def test_latest_audio_selection() -> None:
    audio_dir = Path(__file__).parent / "fixtures" / "audio_mtime"
    file = latest_audio(audio_dir)
    assert file.name == "sample_new.mp3"
