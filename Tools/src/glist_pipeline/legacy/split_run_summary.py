from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SplitRunSummary:
    """Track artifacts created during current split run only."""

    audio_clips: int = 0
    subtitle_files: int = 0

    def record_audio_success(self) -> None:
        self.audio_clips += 1

    def record_subtitle_success(self) -> None:
        self.subtitle_files += 1

    def completion_line(self) -> str:
        return (
            f"  ALL DONE - {self.audio_clips} audio clips + "
            f"{self.subtitle_files} subtitle files"
        )
