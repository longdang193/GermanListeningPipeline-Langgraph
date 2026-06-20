#!/usr/bin/env python3
"""Compatibility wrapper; delegates to glist_pipeline package."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_SRC = REPO_ROOT / "Tools" / "src"
if str(TOOLS_SRC) not in sys.path:
    sys.path.insert(0, str(TOOLS_SRC))

from glist_pipeline.legacy_runner import run_legacy

if __name__ == "__main__":
    raise SystemExit(run_legacy("split_and_subtitle_4.py", sys.argv[1:]))
