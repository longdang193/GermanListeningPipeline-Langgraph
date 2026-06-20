from __future__ import annotations

import re

SPAN_TS = re.compile(r'<span\s+data-start="([\d.]+)"\s+data-end="([\d.]+)">(.*?)</span>')
TAG_RE = re.compile(r"<[^>]+>")


def extract_sentences(de_1: str) -> list[dict]:
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
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(sentences: list[dict], block_start: float) -> str:
    lines: list[str] = []
    for i, sent in enumerate(sentences, 1):
        rel_start = max(0.0, sent["start"] - block_start)
        rel_end = max(0.0, sent["end"] - block_start)
        lines.append(str(i))
        lines.append(f"{format_srt_time(rel_start)} --> {format_srt_time(rel_end)}")
        lines.append(sent["text"])
        lines.append("")
    return "\n".join(lines)
