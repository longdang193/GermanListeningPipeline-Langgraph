from __future__ import annotations

from pathlib import Path

from ..legacy_runner import run_legacy


def generate() -> int:
    return run_legacy("generate_listening_2.py")


def validate() -> int:
    return run_legacy("check_listening_2.py", ["Outputs/Listening-generated.md"])


def split(blocks_path: str | Path = "Outputs/Listening-generated.md") -> int:
    return run_legacy("split_and_subtitle.py", [str(blocks_path)])

