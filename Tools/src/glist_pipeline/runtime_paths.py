from __future__ import annotations

import sys
from pathlib import Path


def _looks_like_workspace_root(path: Path) -> bool:
    return (
        (path / "configs").exists()
        and (path / "Outputs").exists()
        and (path / "Transcripts").exists()
    )


def _iter_unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def _workspace_candidates() -> list[Path]:
    candidates: list[Path] = [Path.cwd()]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.extend([Path(meipass), Path(meipass).parent])

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([exe_dir, exe_dir.parent])
    else:
        candidates.append(Path(__file__).resolve().parents[3])

    return _iter_unique(candidates)


def get_workspace_root() -> Path:
    for candidate in _workspace_candidates():
        if _looks_like_workspace_root(candidate):
            return candidate

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent

    return Path(__file__).resolve().parents[3]


def get_config_dir() -> Path:
    workspace_root = get_workspace_root()
    workspace_config = workspace_root / "configs"
    if workspace_config.exists():
        return workspace_config

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled_config = Path(meipass).resolve() / "configs"
        if bundled_config.exists():
            return bundled_config

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir / "configs", exe_dir.parent / "configs"):
            if candidate.exists():
                return candidate

    return Path(__file__).resolve().parents[3] / "configs"


def get_repo_root() -> Path:
    return get_workspace_root()

