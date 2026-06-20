from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .blocks import Block
from .markdown import parse_markdown, render_document

SPAN_RE = re.compile(r'<span\s+data-start="([\d.]+)"\s+data-end="([\d.]+)">([^<]*)</span>')
HEADING_RE = re.compile(r"^Teil\s+(\d+)(?:\.(\d+))?$")


@dataclass
class Row:
    heading: str
    duration_seconds: float
    selected_index: int | None
    confidence: float
    uncertain: bool


def _split_br(value: str) -> list[str]:
    return [x.strip() for x in re.split(r"\s*<br>\s*", value.strip()) if x.strip()]


def _duration_from_de_line(line: str) -> tuple[float, float]:
    spans = SPAN_RE.findall(line)
    if not spans:
        raise RuntimeError("de_1 sentence line missing span timestamps")
    return float(spans[0][0]), float(spans[-1][1])


def load_latest_suggestions(path: Path) -> dict[str, Row]:
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest: dict[str, Row] = {}
    for r in rows:
        heading = str(r.get("heading", ""))
        selected = r.get("selected") or {}
        latest[heading] = Row(
            heading=heading,
            duration_seconds=float(r.get("duration_seconds", 0.0)),
            selected_index=selected.get("selected_index"),
            confidence=float(selected.get("confidence", 0.0)),
            uncertain=bool(r.get("uncertain", False)),
        )
    return latest


def _split_block(block: Block, cut_index: int) -> tuple[Block, Block]:
    de_lines = _split_br(block.fields.get("de_1", ""))
    en_lines = _split_br(block.fields.get("en_1", ""))
    if len(de_lines) != len(en_lines):
        raise RuntimeError(f"translation mismatch in {block.heading}: de={len(de_lines)} en={len(en_lines)}")
    if cut_index <= 0 or cut_index >= len(de_lines):
        raise RuntimeError(f"invalid cut index {cut_index} for {block.heading} with {len(de_lines)} lines")

    left_de = de_lines[:cut_index]
    right_de = de_lines[cut_index:]
    left_en = en_lines[:cut_index]
    right_en = en_lines[cut_index:]

    l_start, _ = _duration_from_de_line(left_de[0])
    _, l_end = _duration_from_de_line(left_de[-1])
    r_start, _ = _duration_from_de_line(right_de[0])
    _, r_end = _duration_from_de_line(right_de[-1])

    common = {
        "note_1": block.fields.get("note_1", ""),
        "de_1_audio": block.fields.get("de_1_audio", ""),
        "de_1_wave": block.fields.get("de_1_wave", ""),
    }

    left = Block(
        heading=block.heading,
        fields={
            **common,
            "de_1": "<br>".join(left_de),
            "en_1": "<br>".join(left_en),
            "de_1_start": str(l_start),
            "de_1_end": str(l_end),
        },
    )
    right = Block(
        heading=block.heading,
        fields={
            **common,
            "de_1": "<br>".join(right_de),
            "en_1": "<br>".join(right_en),
            "de_1_start": str(r_start),
            "de_1_end": str(r_end),
        },
    )
    return left, right


def _renumber_marker_headings(blocks: list[Block]) -> list[Block]:
    indices_by_base: dict[int, list[int]] = {}
    for idx, block in enumerate(blocks):
        m = HEADING_RE.match(block.heading)
        if not m:
            continue
        base = int(m.group(1))
        indices_by_base.setdefault(base, []).append(idx)

    for base, indices in indices_by_base.items():
        if len(indices) == 1:
            blocks[indices[0]].heading = f"Teil {base}"
            continue
        for sub_idx, i in enumerate(indices, start=1):
            blocks[i].heading = f"Teil {base}.{sub_idx}"

    return blocks


def apply_boundary_suggestions(
    md_path: Path,
    *,
    evidence_path: Path | None = None,
    apply_uncertain: bool = False,
    apply_headings: set[str] | None = None,
) -> int:
    evidence_path = evidence_path or (md_path.parent / "review_logs" / "boundary_suggestions.jsonl")
    suggestions = load_latest_suggestions(evidence_path)
    apply_headings = apply_headings or set()

    doc = parse_markdown(md_path.read_text(encoding="utf-8"))
    out_blocks: list[Block] = []
    applied = 0

    for block in doc.blocks:
        row = suggestions.get(block.heading)
        if not row or row.selected_index is None:
            out_blocks.append(block)
            continue

        need_split = row.duration_seconds > 60.0
        selected_manual = block.heading in apply_headings
        selected_uncertain = apply_uncertain and row.uncertain

        if not (need_split or selected_uncertain or selected_manual):
            out_blocks.append(block)
            continue

        left, right = _split_block(block, int(row.selected_index))
        out_blocks.extend([left, right])
        applied += 1

    if applied == 0:
        print("Boundary apply: no block changed")
        return 0

    out_blocks = _renumber_marker_headings(out_blocks)
    md_path.write_text(render_document(out_blocks), encoding="utf-8")
    print(f"Boundary apply: split applied to {applied} block(s)")
    return 0
