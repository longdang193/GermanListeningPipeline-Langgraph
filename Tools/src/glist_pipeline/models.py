from dataclasses import dataclass, field
from typing import Literal


DecisionSource = Literal["human", "system"]
DecisionType = Literal["accept", "regenerate", "discard", "manual_select"]


@dataclass(frozen=True)
class LabelSuggestion:
    label_id: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class LabelDecision:
    block_id: str
    action: DecisionType
    source: DecisionSource
    final_labels: list[str] = field(default_factory=list)
    regenerate_count: int = 0
