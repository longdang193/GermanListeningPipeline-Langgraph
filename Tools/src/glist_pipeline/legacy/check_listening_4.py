#!/usr/bin/env python3
"""
check_listening_4.py — Validate a marker-based Listening_2 output file against Requirement B1-4-2.

Usage:
    python check_listening_4.py <path-to-generated-file.md>
"""

import re
import sys
from pathlib import Path


MARKER_PATTERNS = [
    r"\bTeil\s+eins\b",
    r"\bTeil\s+zwei\b",
    r"\bTeil\s+drei\b",
    r"\bTeil\s+vier\b",
    r"\bTeil\s+f(?:u|ü)nf\b",
    r"\bTeil\s+sechs\b",
    r"\bTeil\s+sieben\b",
    r"\bTeil\s+acht\b",
    r"\bTeil\s+neun\b",
    r"\bTeil\s+zehn\b",
    r"\bEnde\s+des\s+Teil\s+eins\b",
    r"\bEnde\s+des\s+Teil\s+zwei\b",
    r"\bEnde\s+des\s+Teil\s+drei\b",
    r"\bEnde\s+des\s+Teil\s+vier\b",
    r"\bEnde\s+des\s+Teil\s+f(?:u|ü)nf\b",
    r"\bEnde\s+des\s+Teil\s+sechs\b",
    r"\bEnde\s+des\s+Teil\s+sieben\b",
    r"\bEnde\s+des\s+Teil\s+acht\b",
    r"\bEnde\s+des\s+Teil\s+neun\b",
    r"\bEnde\s+des\s+Teil\s+zehn\b",
    r"\bTeil\s+\d+\b",
    r"\bEnde\s+des\s+Teil\s+\d+\b",
]

INTRO_PATTERNS = [
    r"^Beratungsgespr[aä]ch,\s*Teil\s+(?:eins|zwei|drei|vier|f(?:u|ü)nf|\d+)[.!?]?$",
    r"^H[öo]rtexte\s+zum\s+Kursbuch\b",
    r"^H[öo]ren\s+Sie\b",
    r"^Lesen\s+Sie\b",
    r"^Sie\s+h[öo]ren\b",
    r"^Dazu\s+sollen\s+Sie\b",
    r"^Markieren\s+Sie\b",
]


def parse_blocks_with_headings(content: str) -> list[dict]:
    """Extract all SSTART...EEND blocks together with their preceding ## heading."""
    heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    block_pattern = re.compile(
        r"(?ms)^(?:SSTART|START)\s*$\n(.*?)\n^(?:EEND|END)\s*$")

    headings = [(m.start(), m.group(1).strip())
                for m in heading_pattern.finditer(content)]
    blocks_raw = [(m.start(), m.group(1).strip())
                  for m in block_pattern.finditer(content)]

    results = []
    for block_pos, block_text in blocks_raw:
        heading = "Unknown"
        for heading_pos, heading_text in reversed(headings):
            if heading_pos < block_pos:
                heading = heading_text
                break

        lines = block_text.split("\n")
        fields: dict[str, str] = {}
        for line in lines:
            match = re.match(
                r"^(de_1|en_1|note_1|de_1_audio|de_1_wave|de_1_start|de_1_end):\s*(.*)",
                line,
            )
            if match:
                fields[match.group(1)] = match.group(2).strip()

        results.append({
            "heading": heading,
            "raw": block_text,
            "has_header": any(line.strip() == "Listening_2" for line in lines),
            "fields": fields,
        })
    return results


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def split_lines(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*<br>\s*", value.strip()) if part.strip()]


def check_structure(content: str, blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.1 — Block structure."""
    errors = []

    if "TARGET DECK: TEST" not in content.split("```")[0]:
        errors.append(
            "Missing 'TARGET DECK: TEST' at top of file (outside code fences)")

    teil_headings = re.findall(r"(?m)^##\s+Teil\s+([\d.]+)\s*$", content)
    if not teil_headings:
        errors.append(
            "Expected at least 1 heading in the format '## Teil X' or '## Teil X.Y'")

    if len(blocks) != len(teil_headings):
        errors.append(
            f"Block count mismatch: found {len(blocks)} blocks, expected {len(teil_headings)} based on headings"
        )

    # Validate heading sequence: base Teil numbers must be sequential,
    # sub-block numbers (X.Y) must be sequential within each Teil
    if teil_headings:
        prev_base = 0
        prev_sub = 0
        for h in teil_headings:
            if "." in h:
                base, sub = h.split(".", 1)
                base, sub = int(base), int(sub)
                if base < prev_base:
                    errors.append(
                        f"Teil headings out of order: Teil {h} after Teil {prev_base}")
                    break
                if base == prev_base and sub != prev_sub + 1:
                    errors.append(
                        f"Sub-block numbering not sequential: Teil {h}")
                    break
                prev_base, prev_sub = base, sub
            else:
                base = int(h)
                if base != prev_base + 1 and not (base == prev_base and prev_sub > 0):
                    if prev_sub == 0 and base != prev_base + 1:
                        errors.append(
                            f"Teil headings should be sequential, found Teil {h} after Teil {prev_base}"
                        )
                        break
                prev_base = base
                prev_sub = 0

    for i, block in enumerate(blocks):
        if not block["has_header"]:
            errors.append(
                f"Block {i + 1}: missing 'Listening_2' note-type header")
        if not re.fullmatch(r"Teil\s+\d+(?:\.\d+)?", block["heading"]):
            errors.append(
                f"Block {i + 1}: heading must be '## Teil X' or '## Teil X.Y', got '{block['heading']}'"
            )

    return len(errors) == 0, errors


def check_field_completeness(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.2 — Field completeness."""
    errors = []
    required_nonempty = [
        "de_1",
        "en_1",
        "note_1",
        "de_1_audio",
        "de_1_wave",
        "de_1_start",
        "de_1_end",
    ]
    audio_pattern = re.compile(r"^\[sound:(.+\.mp3)\]$")

    for i, block in enumerate(blocks):
        for field in required_nonempty:
            value = block["fields"].get(field)
            if value is None:
                errors.append(f"Block {i + 1}: field '{field}' is missing")
            elif value == "":
                errors.append(f"Block {i + 1}: field '{field}' is empty")

        audio_val = block["fields"].get("de_1_audio", "")
        wave_val = block["fields"].get("de_1_wave", "")
        if audio_val:
            match = audio_pattern.match(audio_val)
            if not match:
                errors.append(
                    f"Block {i + 1}: de_1_audio format invalid — expected '[sound:filename.mp3]', got '{audio_val[:60]}'"
                )
            elif wave_val and match.group(1) != wave_val:
                errors.append(
                    f"Block {i + 1}: de_1_audio filename '{match.group(1)}' != de_1_wave '{wave_val}'"
                )
        if wave_val and not wave_val.endswith(".mp3"):
            errors.append(
                f"Block {i + 1}: de_1_wave should be a plain .mp3 filename, got '{wave_val[:60]}'"
            )

    return len(errors) == 0, errors


def check_html_format(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.3 — HTML format validation."""
    errors = []
    span_pattern = re.compile(
        r'<span\s+data-start="[\d.]+"\s+data-end="[\d.]+">')
    bold_pattern = re.compile(r"<b>.+?</b>\s*—")

    for i, block in enumerate(blocks):
        de_1 = block["fields"].get("de_1", "")
        en_1 = block["fields"].get("en_1", "")
        note_1 = block["fields"].get("note_1", "")

        if not span_pattern.search(de_1):
            errors.append(
                f"Block {i + 1}: de_1 has no <span data-start data-end> tags")
        if not bold_pattern.search(en_1):
            errors.append(
                f"Block {i + 1}: en_1 has no '<b>...</b> —' translation pattern"
            )
        if "<b>Key Words and Phrases</b>" not in note_1:
            errors.append(
                f"Block {i + 1}: note_1 missing '<b>Key Words and Phrases</b>'")
        if "<b>Grammar to Remember</b>" not in note_1:
            errors.append(
                f"Block {i + 1}: note_1 missing '<b>Grammar to Remember</b>'")

    return len(errors) == 0, errors


def check_content_minimums(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.4 — Content minimums."""
    errors = []
    for i, block in enumerate(blocks):
        note_1 = block["fields"].get("note_1", "")
        parts = note_1.split("<b>Grammar to Remember</b>")
        kw_section = parts[0] if len(parts) >= 1 else ""
        gr_section = parts[1] if len(parts) >= 2 else ""
        kw_count = kw_section.count("•")
        gr_count = gr_section.count("•")

        if kw_count < 5:
            errors.append(
                f"Block {i + 1} ({block['heading']}): Key Words has {kw_count} items, need ≥5"
            )
        if gr_count < 3:
            errors.append(
                f"Block {i + 1} ({block['heading']}): Grammar has {gr_count} items, need ≥3"
            )

    return len(errors) == 0, errors


def check_timestamps(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.5 — Timestamp validation."""
    errors = []
    span_ts_pattern = re.compile(
        r'<span\s+data-start="([\d.]+)"\s+data-end="([\d.]+)">')

    for i, block in enumerate(blocks):
        start_str = block["fields"].get("de_1_start", "")
        end_str = block["fields"].get("de_1_end", "")
        de_1 = block["fields"].get("de_1", "")

        try:
            block_start = float(start_str)
        except ValueError:
            errors.append(
                f"Block {i + 1}: de_1_start '{start_str}' is not a valid number")
            continue

        try:
            block_end = float(end_str)
        except ValueError:
            errors.append(
                f"Block {i + 1}: de_1_end '{end_str}' is not a valid number")
            continue

        if block_start >= block_end:
            errors.append(
                f"Block {i + 1}: de_1_start ({block_start}) >= de_1_end ({block_end})"
            )

        spans = span_ts_pattern.findall(de_1)
        if not spans:
            continue

        for j, (start, end) in enumerate(spans):
            try:
                float(start)
                float(end)
            except ValueError:
                errors.append(
                    f"Block {i + 1}: span {j + 1} has invalid timestamp(s): start={start}, end={end}"
                )

        first_start = float(spans[0][0])
        last_end = float(spans[-1][1])
        if abs(first_start - block_start) > 0.01:
            errors.append(
                f"Block {i + 1}: first span data-start ({first_start}) != de_1_start ({block_start})"
            )
        if abs(last_end - block_end) > 0.01:
            errors.append(
                f"Block {i + 1}: last span data-end ({last_end}) != de_1_end ({block_end})"
            )

    return len(errors) == 0, errors


def check_translation_consistency(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.6 — Sentence-by-sentence translation consistency."""
    errors = []
    missing_line_break_after_sentence = re.compile(
        r'<span\s+data-start="[\d.]+"\s+data-end="[\d.]+">[^<]*[.!?]["\')”]?</span>\s+(?=<span\s+data-start=)'
    )

    for i, block in enumerate(blocks):
        de_1 = block["fields"].get("de_1", "")
        en_1 = block["fields"].get("en_1", "")
        if not de_1 or not en_1:
            continue

        if missing_line_break_after_sentence.search(de_1):
            errors.append(
                f"Block {i + 1}: de_1 is not sentence-per-line (missing <br> after sentence-ending span)"
            )

        de_sentences = de_1.count("<br>") + 1
        en_sentences = en_1.count("<br>") + 1
        if de_sentences != en_sentences:
            errors.append(
                f"Block {i + 1}: de_1 has {de_sentences} sentence(s) but en_1 has {en_sentences} translation(s)"
            )

    return len(errors) == 0, errors


def check_marker_exclusion(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.7 — Marker exclusion check."""
    errors = []
    marker_regexes = [re.compile(pattern, re.IGNORECASE)
                      for pattern in MARKER_PATTERNS]

    for i, block in enumerate(blocks):
        de_plain = strip_html(block["fields"].get("de_1", ""))
        en_plain = strip_html(block["fields"].get("en_1", ""))
        combined = f"{de_plain}\n{en_plain}"

        for regex in marker_regexes:
            match = regex.search(combined)
            if match:
                errors.append(
                    f"Block {i + 1} ({block['heading']}): contains marker text '{match.group(0)}'"
                )
                break

    return len(errors) == 0, errors


def check_instruction_exclusion(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.8 — Instruction exclusion check."""
    errors = []
    intro_regexes = [re.compile(pattern, re.IGNORECASE)
                     for pattern in INTRO_PATTERNS]

    for i, block in enumerate(blocks):
        de_lines = [strip_html(line) for line in split_lines(
            block["fields"].get("de_1", ""))]
        if not de_lines:
            continue

        for line in de_lines:
            for regex in intro_regexes:
                if regex.search(line):
                    errors.append(
                        f"Block {i + 1} ({block['heading']}): contains likely intro/setup text '{line}'"
                    )
                    break
            else:
                continue
            break

    return len(errors) == 0, errors


MAX_BLOCK_DURATION = 60.0  # seconds
MIN_FRAGMENT_DURATION = 2.5  # seconds
MAX_FRAGMENT_WORDS = 3


def check_block_duration(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-4-2.9 — Block duration check (≤ 60 seconds) and short-fragment detection."""
    errors = []
    span_pattern = re.compile(
        r'<span\s+data-start="[\d.]+"\s+data-end="[\d.]+">[^<]+</span>')
    for i, block in enumerate(blocks):
        start = block["fields"].get("de_1_start", "")
        end = block["fields"].get("de_1_end", "")
        de_1 = block["fields"].get("de_1", "")
        if not start or not end:
            continue
        try:
            duration = float(end) - float(start)
        except ValueError:
            continue
        if duration > MAX_BLOCK_DURATION:
            errors.append(
                f"Block {i + 1} ({block['heading']}): duration {duration:.1f}s exceeds "
                f"maximum {MAX_BLOCK_DURATION:.0f}s — split into sub-blocks"
            )

        # Flag likely accidental micro-cuts like a one-word fragment (e.g., "Danke.").
        word_count = len(span_pattern.findall(de_1))
        if duration < MIN_FRAGMENT_DURATION and word_count <= MAX_FRAGMENT_WORDS:
            errors.append(
                f"Block {i + 1} ({block['heading']}): suspicious short fragment "
                f"({duration:.3f}s, {word_count} word(s)) — likely a bad cut"
            )
    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_listening_4.py <path-to-generated-file.md>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    content = filepath.read_text(encoding="utf-8")
    blocks = parse_blocks_with_headings(content)

    checks = [
        ("B1-4-2.1 Block Structure", check_structure, (content, blocks)),
        ("B1-4-2.2 Field Completeness", check_field_completeness, (blocks,)),
        ("B1-4-2.3 HTML Format", check_html_format, (blocks,)),
        ("B1-4-2.4 Content Minimums", check_content_minimums, (blocks,)),
        ("B1-4-2.5 Timestamp Validation", check_timestamps, (blocks,)),
        ("B1-4-2.6 Translation Consistency",
         check_translation_consistency, (blocks,)),
        ("B1-4-2.7 Marker Exclusion", check_marker_exclusion, (blocks,)),
        ("B1-4-2.8 Instruction Exclusion", check_instruction_exclusion, (blocks,)),
        ("B1-4-2.9 Block Duration", check_block_duration, (blocks,)),
    ]

    all_pass = True
    print(f"\n{'=' * 60}")
    print(f"  Marker-Based Listening_2 Validation — {filepath.name}")
    print(f"  Blocks found: {len(blocks)}")
    print(f"{'=' * 60}\n")

    for name, fn, args in checks:
        passed, errors = fn(*args)
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if errors:
            for error in errors:
                print(f"    - {error}")
        if not passed:
            all_pass = False
        print()

    print(f"{'=' * 60}")
    if all_pass:
        print("  ALL CHECKS PASSED")
    else:
        print("  SOME CHECKS FAILED")
    print(f"{'=' * 60}\n")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
