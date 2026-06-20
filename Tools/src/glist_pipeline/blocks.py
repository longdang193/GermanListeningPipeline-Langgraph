from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Block:
    heading: str
    fields: dict[str, str]


@dataclass
class ParsedDocument:
    blocks: list[Block]
    metadata: dict[str, Any]
