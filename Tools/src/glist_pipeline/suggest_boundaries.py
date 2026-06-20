from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .blocks import Block
from .markdown import parse_markdown

MAX_BLOCK_SECONDS = 60.0
TARGET_BLOCK_SECONDS = 45.0
MIN_TARGET_SECONDS = 30.0
MIN_NATURAL_SHORT_SECONDS = 25.0

SPAN_RE = re.compile(r'<span\s+data-start="([\d.]+)"\s+data-end="([\d.]+)">([^<]*)</span>')


@dataclass
class SentenceRow:
    text: str
    start: float
    end: float


def _split_sentences_from_de1(de_1: str) -> list[SentenceRow]:
    lines = [line.strip() for line in re.split(r"\s*<br>\s*", de_1.strip()) if line.strip()]
    out: list[SentenceRow] = []
    for line in lines:
        spans = SPAN_RE.findall(line)
        if not spans:
            continue
        start = float(spans[0][0])
        end = float(spans[-1][1])
        text = " ".join(token.strip() for _, _, token in spans).strip()
        out.append(SentenceRow(text=text, start=start, end=end))
    return out


def _candidate_boundaries(sentences: list[SentenceRow]) -> list[dict]:
    if len(sentences) < 2:
        return []
    region_start = sentences[0].start
    region_end = sentences[-1].end
    total = region_end - region_start

    cands: list[dict] = []
    for i in range(1, len(sentences)):
        left_end = sentences[i - 1].end
        right_start = sentences[i].start
        left = left_end - region_start
        right = region_end - right_start
        max_side = max(left, right)
        min_side = min(left, right)
        hard_valid = max_side <= MAX_BLOCK_SECONDS and min_side >= MIN_NATURAL_SHORT_SECONDS
        target_fit = 1.0 - min(abs(left - TARGET_BLOCK_SECONDS), abs(right - TARGET_BLOCK_SECONDS)) / TARGET_BLOCK_SECONDS
        target_fit = max(0.0, min(1.0, target_fit))
        cands.append(
            {
                "index": i,
                "left_seconds": round(left, 3),
                "right_seconds": round(right, 3),
                "hard_valid": hard_valid,
                "target_fit": round(target_fit, 3),
                "max_side_seconds": round(max_side, 3),
                "min_side_seconds": round(min_side, 3),
                "gap_seconds": round(max(0.0, right_start - left_end), 3),
                "left_tail": sentences[i - 1].text[-140:],
                "right_head": sentences[i].text[:140],
            }
        )

    if total <= MAX_BLOCK_SECONDS:
        return cands

    good = [c for c in cands if c["hard_valid"]]
    if good:
        return good
    return cands


def _choose_boundary_with_llm(candidates: list[dict], block_heading: str, total_seconds: float) -> dict:
    if not candidates:
        return {
            "selected_index": None,
            "confidence": 1.0,
            "reason": "single-sentence or no candidate",
            "method": "rule_fallback",
        }

    prompt = {
        "task": "Choose best split boundary for listening block",
        "contract": {
            "max_block_seconds": MAX_BLOCK_SECONDS,
            "target_window_seconds": [MIN_TARGET_SECONDS, MAX_BLOCK_SECONDS],
            "sweet_spot_seconds": TARGET_BLOCK_SECONDS,
            "natural_short_allowed_seconds": MIN_NATURAL_SHORT_SECONDS,
            "must_cut_on_sentence_boundary": True,
        },
        "block": {"heading": block_heading, "duration_seconds": round(total_seconds, 3)},
        "candidates": candidates,
        "output": {
            "selected_index": "int|null",
            "confidence": "float_0_1",
            "reason": "string_short",
        },
        "rule": "Return valid JSON only. No markdown.",
    }

    try:
        from openai import OpenAI  # type: ignore[import-not-found]

        client = OpenAI()
        model = __import__("os").environ.get("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.responses.create(
            model=model,
            input=[{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
        )
        text = getattr(resp, "output_text", "").strip()
        payload = json.loads(text)
        idx = payload.get("selected_index")
        conf = float(payload.get("confidence", 0.0))
        reason = str(payload.get("reason", ""))
        return {
            "selected_index": idx,
            "confidence": max(0.0, min(1.0, conf)),
            "reason": reason[:400],
            "method": "llm",
        }
    except Exception:
        # deterministic fallback if LLM unavailable/noisy
        best = sorted(candidates, key=lambda c: (not c["hard_valid"], -c["target_fit"], c["max_side_seconds"]))[0]
        return {
            "selected_index": best["index"],
            "confidence": 0.5,
            "reason": "fallback by hard_valid + target_fit",
            "method": "rule_fallback",
        }


def _record_for_block(block: Block) -> dict:
    heading = block.heading
    sentences = _split_sentences_from_de1(block.fields.get("de_1", ""))
    if not sentences:
        return {"heading": heading, "status": "no_sentences"}

    total = sentences[-1].end - sentences[0].start
    cands = _candidate_boundaries(sentences)
    selected = _choose_boundary_with_llm(cands, heading, total)

    violates_max = total > MAX_BLOCK_SECONDS
    selected_row = next((c for c in cands if c.get("index") == selected.get("selected_index")), None)
    uncertain = selected.get("confidence", 0.0) < 0.65

    return {
        "heading": heading,
        "duration_seconds": round(total, 3),
        "sentence_count": len(sentences),
        "violates_max": violates_max,
        "candidate_count": len(cands),
        "selected": selected,
        "selected_candidate": selected_row,
        "uncertain": uncertain,
    }


def suggest_boundaries(md_path: Path, *, evidence_path: Path | None = None) -> int:
    doc = parse_markdown(md_path.read_text(encoding="utf-8"))
    evidence_path = evidence_path or (md_path.parent / "review_logs" / "boundary_suggestions.jsonl")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [_record_for_block(block) for block in doc.blocks]
    with evidence_path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    violating = [r for r in rows if r.get("violates_max")]
    if violating:
        # fail fast: boundary contract broken before downstream steps
        names = ", ".join(r.get("heading", "?") for r in violating[:8])
        raise RuntimeError(f"boundary contract violation: >60s blocks present ({names})")

    print(f"Boundary suggestions written: {evidence_path}")
    uncertain_count = sum(1 for r in rows if r.get("uncertain"))
    print(f"Boundary suggestions summary: blocks={len(rows)}, uncertain={uncertain_count}")
    return 0
