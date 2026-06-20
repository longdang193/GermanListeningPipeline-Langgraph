from __future__ import annotations

import re
import sys
from pathlib import Path

from .glossary_policy import (
    extract_note_keywords,
    keywords_have_conservative_glosses,
    load_content_policy,
    translation_is_conservative,
)
from .markdown import parse_markdown

BANNED = [
    r"TODO: add English translation\.",
    r"TODO_TERM_\d+",
    r"TODO_GRAMMAR_\d+",
    r"Add glossary note\.",
    r"Add grammar explanation\.",
]
CONTENT_POLICY = load_content_policy()


def _extract_translation_pairs(en_1: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for part in re.split(r"\s*<br>\s*", en_1.strip()):
        match = re.match(r"^<b>(.*?)</b>\s*—\s*(.*)$", part.strip())
        if match:
            pairs.append((match.group(1).strip(), match.group(2).strip()))
    return pairs


def find_quality_issues(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    hits: list[tuple[str, str]] = []
    for pat in BANNED:
        m = re.search(pat, text)
        if m:
            hits.append((pat, m.group(0)))

    doc = parse_markdown(text)
    for idx, block in enumerate(doc.blocks, start=1):
        en_1 = block.fields.get("en_1", "")
        for german_sentence, english_sentence in _extract_translation_pairs(en_1):
            if not translation_is_conservative(
                german_sentence,
                english_sentence,
                CONTENT_POLICY.translation,
            ):
                hits.append((f"block_{idx}_translation_policy", block.heading))
                break

        note_1 = block.fields.get("note_1", "")
        keywords = extract_note_keywords(note_1)
        if keywords and not keywords_have_conservative_glosses(keywords, CONTENT_POLICY.glossary):
            hits.append((f"block_{idx}_keyword_gloss_policy", block.heading))
    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m glist_pipeline.quality_gate <path-to-listening-md>")
        return 1
    path = Path(sys.argv[1])
    hits = find_quality_issues(path)

    if hits:
        print("Quality gate failed")
        for pat, val in hits:
            print(f" - {pat}: {val}")
        return 2

    print("Quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
