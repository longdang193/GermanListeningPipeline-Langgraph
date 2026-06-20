from glist_pipeline.legacy.split_run_summary import SplitRunSummary


def test_completion_line_uses_current_run_counts_only() -> None:
    summary = SplitRunSummary()
    summary.record_audio_success()
    summary.record_audio_success()
    summary.record_subtitle_success()

    assert summary.completion_line() == "  ALL DONE - 2 audio clips + 1 subtitle files"


def test_completion_line_starts_from_zero() -> None:
    summary = SplitRunSummary()

    assert summary.completion_line() == "  ALL DONE - 0 audio clips + 0 subtitle files"
