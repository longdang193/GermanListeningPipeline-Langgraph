from __future__ import annotations

import json
from pathlib import Path


def load_transcript(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_transcript(transcripts_dir: Path) -> Path:
    files = sorted(transcripts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No transcript found in {transcripts_dir}")
    return files[-1]


def latest_audio(audios_dir: Path) -> Path:
    files = sorted(audios_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No .mp3 found in {audios_dir}")
    return files[-1]
