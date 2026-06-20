from __future__ import annotations

import argparse
from pathlib import Path

from .suggest_boundaries import suggest_boundaries


def main() -> int:
    parser = argparse.ArgumentParser(prog="glist-suggest-boundaries")
    parser.add_argument("markdown_path")
    parser.add_argument("--evidence", default="Outputs/review_logs/boundary_suggestions.jsonl")
    args = parser.parse_args()

    md_path = Path(args.markdown_path)
    evidence = Path(args.evidence)
    return suggest_boundaries(md_path, evidence_path=evidence)


if __name__ == "__main__":
    raise SystemExit(main())
