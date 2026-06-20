from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
import json

from .labels import validate_final_labels
from .models import LabelDecision, LabelSuggestion


class DecisionAction(StrEnum):
    ACCEPT = "accept"
    REGENERATE = "regenerate"
    DISCARD = "discard"
    MANUAL_SELECT = "manual_select"


class HitlEngine:
    def __init__(self, allowed_ids: set[str], max_regenerations: int = 2) -> None:
        self.allowed_ids = allowed_ids
        self.max_regenerations = max_regenerations

    def decide(
        self,
        block_id: str,
        action: DecisionAction,
        suggestions: list[LabelSuggestion],
        manual_labels: list[str] | None = None,
        regenerate_count: int = 0,
    ) -> LabelDecision:
        if action is DecisionAction.ACCEPT:
            if not suggestions:
                raise ValueError("Cannot accept without suggestions")
            final = [suggestions[0].label_id]
            validate_final_labels(final, self.allowed_ids)
            return LabelDecision(block_id=block_id, action=action, source="human", final_labels=final)

        if action is DecisionAction.REGENERATE:
            if regenerate_count >= self.max_regenerations:
                raise ValueError("Regenerate attempt limit reached")
            return LabelDecision(
                block_id=block_id,
                action=action,
                source="human",
                final_labels=[],
                regenerate_count=regenerate_count + 1,
            )

        if action is DecisionAction.DISCARD:
            return LabelDecision(block_id=block_id, action=action, source="human", final_labels=[])

        if action is DecisionAction.MANUAL_SELECT:
            final = manual_labels or []
            if not final:
                raise ValueError("Manual select needs at least one label")
            validate_final_labels(final, self.allowed_ids)
            return LabelDecision(block_id=block_id, action=action, source="human", final_labels=final)

        raise ValueError(f"Unsupported action: {action}")


def append_review_log(path: Path, decision: LabelDecision) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "label_decision",
        "decision": asdict(decision),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
