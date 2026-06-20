#!/usr/bin/env python3
"""Compatibility wrapper that re-exports canonical marker generator."""

import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_SRC = REPO_ROOT / "Tools" / "src"
if str(TOOLS_SRC) not in sys.path:
    sys.path.insert(0, str(TOOLS_SRC))

_MODULE = import_module("glist_pipeline.legacy.generate_listening_4")

for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)

if __name__ == "__main__":
    raise SystemExit(_MODULE.main())
