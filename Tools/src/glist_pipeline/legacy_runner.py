from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

from .runtime_paths import get_repo_root

REPO_ROOT = get_repo_root()
LEGACY_DIR = REPO_ROOT / "Tools" / "src" / "glist_pipeline" / "legacy"


def _run_legacy_in_process(module_name: str, argv: list[str]) -> int:
    old_argv = sys.argv[:]
    try:
        sys.argv = [module_name, *argv]
        runpy.run_module(module_name, run_name="__main__")
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
    module_name = f"glist_pipeline.legacy.{Path(script_name).stem}"

    # Exe-safe path: avoid recursive invocation of frozen CLI binary.
    if getattr(sys, "frozen", False):
        return _run_legacy_in_process(module_name, argv)

    # Default path for source/python execution.
    script = LEGACY_DIR / script_name
    cmd = [sys.executable, str(script), *argv]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode
