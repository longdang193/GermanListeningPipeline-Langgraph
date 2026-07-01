from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .runtime_paths import get_repo_root

REPO_ROOT = get_repo_root()
LEGACY_DIR = REPO_ROOT / "Tools" / "src" / "glist_pipeline" / "legacy"


def _load_legacy_entrypoint(script_name: str):
    if script_name == "generate_listening_2.py":
        from .legacy import generate_listening_2 as module
        return module
    if script_name == "check_listening_2.py":
        from .legacy import check_listening_2 as module
        return module
    if script_name == "split_and_subtitle.py":
        from .legacy import split_and_subtitle as module
        return module
    if script_name == "generate_listening_4.py":
        from .legacy import generate_listening_4 as module
        return module
    if script_name == "check_listening_4.py":
        from .legacy import check_listening_4 as module
        return module
    if script_name == "split_and_subtitle_4.py":
        from .legacy import split_and_subtitle_4 as module
        return module
    raise ValueError(f"Unknown legacy script: {script_name}")


def _run_legacy_in_process(script_name: str, argv: list[str]) -> int:
    module = _load_legacy_entrypoint(script_name)
    old_argv = sys.argv[:]
    try:
        sys.argv = [script_name, *argv]
        module.main()
        return 0
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            return code
        return 1 if code else 0
    finally:
        sys.argv = old_argv


def run_legacy(script_name: str, argv: list[str] | None = None) -> int:
    argv = argv or []

    if getattr(sys, "frozen", False):
        return _run_legacy_in_process(script_name, argv)

    script = LEGACY_DIR / script_name
    cmd = [sys.executable, str(script), *argv]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode
