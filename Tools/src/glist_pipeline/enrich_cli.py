from __future__ import annotations

import sys
from pathlib import Path

from .enrich_llm import enrich_file_in_place


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m glist_pipeline.enrich_cli <path-to-listening-md>")
        return 1
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Missing file: {path}")
        return 1
    return enrich_file_in_place(path)


if __name__ == "__main__":
    raise SystemExit(main())
