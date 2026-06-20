from __future__ import annotations

import argparse
from pathlib import Path

from .apply_boundary_suggestions import apply_boundary_suggestions


def main() -> int:
    parser = argparse.ArgumentParser(prog="glist-apply-boundaries")
    parser.add_argument("markdown_path")
    parser.add_argument("--evidence", default="Outputs/review_logs/boundary_suggestions.jsonl")
    parser.add_argument("--apply-uncertain", action="store_true")
    parser.add_argument("--headings", default="")
    args = parser.parse_args()

    headings = {h.strip() for h in args.headings.split(",") if h.strip()}

    return apply_boundary_suggestions(
        Path(args.markdown_path),
        evidence_path=Path(args.evidence),
        apply_uncertain=args.apply_uncertain,
        apply_headings=headings,
    )


if __name__ == "__main__":
    raise SystemExit(main())
