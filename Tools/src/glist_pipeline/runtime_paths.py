from __future__ import annotations

import sys
from pathlib import Path


def _looks_like_repo_root(path: Path) -> bool:
    return (
        (path / "configs").exists()
        and (path / "Outputs").exists()
        and (path / "Transcripts").exists()
    )


def get_repo_root() -> Path:
    candidates: list[Path] = [Path.cwd()]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass))

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent)

    candidates.append(Path(__file__).resolve().parents[3])

    for candidate in candidates:
        if _looks_like_repo_root(candidate):
            return candidate

    return Path(__file__).resolve().parents[3]
