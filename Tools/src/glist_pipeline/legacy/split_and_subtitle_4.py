#!/usr/bin/env python3
"""
split_and_subtitle_4.py — Split marker-based merged audio and generate SRT subtitles from Listening_2 blocks.

Usage:
    python split_and_subtitle_4.py <path-to-generated-file.md>

Outputs are written to Outputs/Youtube/ (relative to the repo root).
"""

import re
import subprocess
import sys
from pathlib import Path

from glist_pipeline.legacy.split_run_summary import SplitRunSummary


def parse_blocks_with_headings(content: str) -> list[dict]:
    """Extract SSTART...EEND blocks together with the preceding ## heading."""
    heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    block_pattern = re.compile(r"(?ms)^(?:SSTART|START)\s*$\n(.*?)\n^(?:EEND|END)\s*$")

    headings = [(m.start(), m.group(1).strip()) for m in heading_pattern.finditer(content)]
    blocks_raw = [(m.start(), m.group(1).strip()) for m in block_pattern.finditer(content)]

    results: list[dict] = []
    for b_pos, b_text in blocks_raw:
        heading = "Unknown"
        for h_pos, h_text in reversed(headings):
            if h_pos < b_pos:
                heading = h_text
                break

        fields: dict[str, str] = {}
        for line in b_text.split("\n"):
            match = re.match(
                r"^(de_1|en_1|note_1|de_1_audio|de_1_wave|de_1_start|de_1_end):\s*(.*)",
                line,
            )
            if match:
                fields[match.group(1)] = match.group(2).strip()

        results.append({"heading": heading, "fields": fields})
    return results


def heading_to_filename(index: int, heading: str) -> str:
    """Convert a heading like 'Teil 1' or 'Teil 1.2' into '01_Teil1' or '02_Teil1.2'."""
    heading = heading.replace("—", " ")
    heading = re.sub(r"\s+", " ", heading.strip())
    match = re.fullmatch(r"Teil\s+([\d.]+)", heading)
    if match:
        return f"{index + 1:02d}_Teil{match.group(1)}"

    compact = re.sub(r"\s+", "_", heading).strip("_")
    return f"{index + 1:02d}_{compact}"


SPAN_TS = re.compile(r'<span\s+data-start="([\d.]+)"\s+data-end="([\d.]+)">(.*?)</span>')
TAG_RE = re.compile(r"<[^>]+>")


def extract_sentences(de_1: str) -> list[dict]:
    """Split de_1 by <br>, extract plain text and start/end times per sentence."""
    parts = re.split(r"\s*<br>\s*", de_1.strip())
    sentences: list[dict] = []
    for part in parts:
        spans = SPAN_TS.findall(part)
        if not spans:
            continue
        start = float(spans[0][0])
        end = float(spans[-1][1])
        text = TAG_RE.sub("", part).strip()
        sentences.append({"start": start, "end": end, "text": text})
    return sentences


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(sentences: list[dict], block_start: float) -> str:
    """Build SRT content with timestamps relative to block_start."""
    lines: list[str] = []
    for i, sent in enumerate(sentences, 1):
        rel_start = max(0.0, sent["start"] - block_start)
        rel_end = max(0.0, sent["end"] - block_start)
        lines.append(str(i))
        lines.append(f"{format_srt_time(rel_start)} --> {format_srt_time(rel_end)}")
        lines.append(sent["text"])
        lines.append("")
    return "\n".join(lines)


def split_audio(source: Path, output: Path, start: float, end: float) -> bool:
    """Use ffmpeg to extract a segment from source audio."""
    duration = end - start
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python split_and_subtitle_4.py <path-to-generated-file.md>")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"ERROR: File not found: {md_path}")
        sys.exit(1)

    repo_root = md_path.parent.parent
    content = md_path.read_text(encoding="utf-8")
    blocks = parse_blocks_with_headings(content)

    if not blocks:
        print("ERROR: No SSTART...EEND blocks found.")
        sys.exit(1)

    wave_field = blocks[0]["fields"].get("de_1_wave", "")
    if not wave_field:
        print("ERROR: de_1_wave is empty in the first block.")
        sys.exit(1)

    audio_source = repo_root / "Audios" / wave_field
    if not audio_source.exists():
        print(f"ERROR: Audio file not found: {audio_source}")
        sys.exit(1)

    out_dir = repo_root / "Outputs" / "Youtube"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("  Marker-Based Audio Splitter & Subtitle Generator")
    print(f"  Blocks: {len(blocks)}  |  Audio: {audio_source.name}")
    print(f"  Output: {out_dir}")
    print(f"{'=' * 60}\n")

    errors: list[str] = []
    summary = SplitRunSummary()
    for i, block in enumerate(blocks):
        fields = block["fields"]
        heading = block["heading"]
        basename = heading_to_filename(i, heading)

        start_str = fields.get("de_1_start", "")
        end_str = fields.get("de_1_end", "")
        de_1 = fields.get("de_1", "")

        if not start_str or not end_str:
            errors.append(f"Block {i + 1} ({heading}): missing de_1_start or de_1_end")
            continue

        start = float(start_str)
        end = float(end_str)

        mp3_out = out_dir / f"{basename}.mp3"
        print(f"  [{i + 1:2d}/{len(blocks)}] {basename}")
        print(f"         Audio: {start:.3f}s -> {end:.3f}s  ({end - start:.1f}s)")

        if not split_audio(audio_source, mp3_out, start, end):
            errors.append(f"Block {i + 1} ({heading}): ffmpeg failed")
            print("         FAIL audio split")
        else:
            summary.record_audio_success()
            print(f"         OK {mp3_out.name}")

        sentences = extract_sentences(de_1)
        if sentences:
            srt_content = generate_srt(sentences, block_start=start)
            srt_out = out_dir / f"{basename}.srt"
            srt_out.write_text(srt_content, encoding="utf-8")
            summary.record_subtitle_success()
            print(f"         OK {srt_out.name}  ({len(sentences)} entries)")
        else:
            errors.append(f"Block {i + 1} ({heading}): no sentences extracted for SRT")
            print("         FAIL SRT generation")

        print()

    print(f"{'=' * 60}")
    if errors:
        print(f"  Completed with {len(errors)} error(s):")
        for error in errors:
            print(f"    - {error}")
    else:
        print(summary.completion_line())
    print(f"{'=' * 60}\n")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
