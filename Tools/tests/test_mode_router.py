from pathlib import Path

import pytest

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
