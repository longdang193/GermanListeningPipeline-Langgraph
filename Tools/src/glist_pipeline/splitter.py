from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .blocks import Block
from .srt import extract_sentences, generate_srt


def heading_to_filename(index: int, heading: str, mode: str) -> str:
    if mode == "classic":
        normalized = heading.replace("—", "").replace("&", "and")
        normalized = re.sub(r"Teil\s+", "Teil", normalized)
        normalized = re.sub(r"Aufgabe\s+", "Aufgabe", normalized)
        normalized = re.sub(r"Q\s*&?\s*A\s*", "QandA", normalized)
        normalized = re.sub(r"\s+", "_", normalized.strip())
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        return f"{index + 1:02d}_{normalized}"
    compact = heading.replace(" ", "")
    compact = compact.replace("##", "").replace("—", "")
    compact = compact.replace("Teil", "Teil")
    compact = re.sub(r"[^A-Za-z0-9._-]", "", compact)
    return f"{index + 1:02d}_{compact}"


def split_audio(source: Path, output: Path, start: float, end: float) -> bool:
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source),
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def split_blocks(blocks: list[Block], audio_source: Path, out_dir: Path, mode: str) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for i, block in enumerate(blocks):
        fields = block.fields
        start = float(fields.get("de_1_start", "0") or 0)
        end = float(fields.get("de_1_end", "0") or 0)
        if end <= start:
            errors.append(f"Block {i+1}: invalid timestamps")
            continue
        base = heading_to_filename(i, block.heading, mode)
        mp3_out = out_dir / f"{base}.mp3"
        if not split_audio(audio_source, mp3_out, start, end):
            errors.append(f"Block {i+1}: ffmpeg failed")
            continue
        sentences = extract_sentences(fields.get("de_1", ""))
        srt_text = generate_srt(sentences, block_start=start)
        (out_dir / f"{base}.srt").write_text(srt_text, encoding="utf-8")
    return errors
