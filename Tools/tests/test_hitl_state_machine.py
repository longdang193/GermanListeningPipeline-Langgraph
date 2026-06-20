from pathlib import Path

import pytest

from glist_pipeline.hitl import DecisionAction, HitlEngine
from glist_pipeline.labels import TaxonomyError, load_taxonomy
from glist_pipeline.models import LabelSuggestion


def _engine() -> HitlEngine:
    allowed = load_taxonomy(Path(__file__).resolve().parents[2] / "configs" / "labels.toml")
    return HitlEngine(allowed_ids=allowed, max_regenerations=2)


def test_accept_uses_top_suggestion() -> None:
    engine = _engine()
    decision = engine.decide(
        block_id="teil-1",
        action=DecisionAction.ACCEPT,
        suggestions=[LabelSuggestion("topic_daily_life", 0.9, "fit")],
    )
    assert decision.final_labels == ["topic_daily_life"]


def test_regenerate_limit_enforced() -> None:
    engine = _engine()
    with pytest.raises(ValueError):
        engine.decide(
            block_id="teil-1",
            action=DecisionAction.REGENERATE,
            suggestions=[LabelSuggestion("topic_daily_life", 0.9, "fit")],
            regenerate_count=2,
        )


def test_manual_select_requires_taxonomy_id() -> None:
    engine = _engine()
    with pytest.raises(TaxonomyError):
        engine.decide(
            block_id="teil-1",
            action=DecisionAction.MANUAL_SELECT,
            suggestions=[],
            manual_labels=["unknown_label"],
        )
