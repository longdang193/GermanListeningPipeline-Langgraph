from pathlib import Path

import pytest

from glist_pipeline.cli import _prompt_mode, _route_label, _route_reason
from glist_pipeline.mode_router import TranscriptProfile, route_mode


def test_agent_suggestions_routes_marker_when_marker_capable() -> None:
    profile = TranscriptProfile(marker_capable=True, classic_capable=True, reason="ok")
    assert route_mode("hitl", profile) == "marker"


def test_agent_suggestions_routes_semantic_when_non_marker() -> None:
    profile = TranscriptProfile(marker_capable=False, classic_capable=True, reason="no markers")
    assert route_mode("hitl", profile) == "semantic"


def test_marker_mode_fails_typed_on_non_marker() -> None:
    profile = TranscriptProfile(marker_capable=False, classic_capable=True, reason="no markers")
    with pytest.raises(ValueError, match="marker_mode_unavailable_for_transcript"):
        route_mode("marker", profile)


def test_prompt_mode_accepts_numeric_shortcuts(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "3")
    assert _prompt_mode() == "hitl"


def test_prompt_mode_accepts_short_alias(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "telc")
    assert _prompt_mode() == "classic"


def test_prompt_mode_prints_guided_review_label(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "guided review")
    assert _prompt_mode() == "hitl"
    out = capsys.readouterr().out
    assert "Choose block generation mode:" in out
    assert "3) Guided review" in out


def test_route_reason_for_semantic_fallback() -> None:
    assert _route_label("semantic") == "semantic fallback"
    assert _route_reason("hitl", "semantic", "ignored") == (
        "transcript has no marker anchors, so app uses timing/sentence-based splitting."
    )


def test_prompt_mode_accepts_agentic_alias(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "agentic")
    assert _prompt_mode() == "hitl"
