from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

MARKER_RE = re.compile(r"\bteil\s+(eins|zwei|drei|vier|f(?:u|ü)nf|sechs|sieben|acht|neun|zehn|\d+)\b", re.IGNORECASE)
END_RE = re.compile(r"\bende\s+des\s+teil\s+(eins|zwei|drei|vier|f(?:u|ü)nf|sechs|sieben|acht|neun|zehn|\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TranscriptProfile:
    marker_capable: bool
    classic_capable: bool
    reason: str


def detect_transcript_profile(transcript_path: Path) -> TranscriptProfile:
    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    texts: list[str] = []
    word_count = 0
    for seg in segments:
        for w in seg.get("words", []):
            if w.get("type") == "word":
                texts.append(str(w.get("text", "")))
                word_count += 1
    joined = " ".join(texts)
    marker_hits = len(MARKER_RE.findall(joined))
    end_hits = len(END_RE.findall(joined))
    marker_capable = marker_hits > 0 and end_hits > 0
    classic_capable = word_count > 0
    reason = f"marker_hits={marker_hits}, end_hits={end_hits}, words={word_count}"
    return TranscriptProfile(marker_capable=marker_capable, classic_capable=classic_capable, reason=reason)


def route_mode(requested_mode: str, profile: TranscriptProfile) -> str:
    if requested_mode == "marker":
        if not profile.marker_capable:
            raise ValueError("marker_mode_unavailable_for_transcript")
        return "marker"
    if requested_mode == "classic":
        return "classic"
    # hitl super-mode
    if profile.marker_capable:
        return "marker"
    if profile.classic_capable:
        return "semantic"
    raise ValueError("no_routable_pipeline_for_transcript")


def append_router_run_record(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
