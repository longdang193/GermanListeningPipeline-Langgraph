from __future__ import annotations

import re
from .blocks import Block, ParsedDocument

BLOCK_RE = re.compile(r"(?ms)^(?:SSTART|START)\s*$\n(.*?)\n^(?:EEND|END)\s*$")
HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
FIELD_RE = re.compile(r"^(de_1|en_1|note_1|de_1_audio|de_1_wave|de_1_start|de_1_end):\s*(.*)$")


def parse_markdown(content: str) -> ParsedDocument:
    headings = [(m.start(), m.group(1).strip()) for m in HEADING_RE.finditer(content)]
    blocks: list[Block] = []
    for m in BLOCK_RE.finditer(content):
        body = m.group(1).strip()
        pos = m.start()
        heading = "Unknown"
        for h_pos, h_text in reversed(headings):
            if h_pos < pos:
                heading = h_text
                break
        fields: dict[str, str] = {}
        for line in body.splitlines():
            field_match = FIELD_RE.match(line)
            if field_match:
                fields[field_match.group(1)] = field_match.group(2).strip()
        blocks.append(Block(heading=heading, fields=fields))
    meta = {"has_target_deck": "TARGET DECK: TEST" in content.split("```")[0]}
    return ParsedDocument(blocks=blocks, metadata=meta)


def render_block(heading: str, fields: dict[str, str]) -> str:
    lines = [
        f"## {heading}",
        "```",
        "SSTART",
        "",
        "Listening_2",
        "",
    ]
    for key in ("de_1", "en_1", "note_1", "de_1_audio", "de_1_wave", "de_1_start", "de_1_end"):
        lines.append(f"{key}: {fields.get(key, '')}")
    lines.extend(["EEND", "```", ""])
    return "\n".join(lines)


def render_document(blocks: list[Block]) -> str:
    out = ["TARGET DECK: TEST", ""]
    for block in blocks:
        out.append(render_block(block.heading, block.fields))
    return "\n".join(out).rstrip() + "\n"
