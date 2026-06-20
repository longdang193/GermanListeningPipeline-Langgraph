#!/usr/bin/env python3
"""
check_listening_2.py — Validate a Listening_2 output file against Requirement B1-3-2.

Usage:
    python check_listening_2.py <path-to-generated-file.md>
"""

import re
import sys
from pathlib import Path

def _safe_symbol(unicode_symbol: str, ascii_symbol: str) -> str:
    """Return unicode symbol only when console encoding supports it."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        unicode_symbol.encode(encoding)
        return unicode_symbol
    except UnicodeEncodeError:
        return ascii_symbol


PASS_ICON = _safe_symbol("✅", "PASS")
FAIL_ICON = _safe_symbol("❌", "FAIL")
WARN_ICON = _safe_symbol("⚠", "WARN")
DONE_ICON = _safe_symbol("🎉", "OK")
STOP_ICON = _safe_symbol("⛔", "ERROR")


def parse_blocks(content: str) -> list[dict]:
    """Extract all SSTART...EEND (or legacy START...END) blocks from the markdown content."""
    # Remove code fences wrapping
    raw = content
    blocks = []
    pattern = re.compile(
        r"(?ms)^(?:SSTART|START)\s*$\n(.*?)\n^(?:EEND|END)\s*$")
    for m in pattern.finditer(raw):
        block_text = m.group(1).strip()
        block = {"raw": block_text, "fields": {}}
        # Check for note-type header
        lines = block_text.split("\n")
        block["has_header"] = any(
            line.strip() == "Listening_2" for line in lines)
        # Parse fields (key: value on single lines)
        for line in lines:
            match = re.match(
                r"^(de_1|en_1|note_1|de_1_audio|de_1_wave|de_1_start|de_1_end):\s*(.*)", line)
            if match:
                block["fields"][match.group(1)] = match.group(2).strip()
        blocks.append(block)
    return blocks


def check_structure(content: str, blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-3-2.1 — Block structure."""
    errors = []
    # TARGET DECK check
    if "TARGET DECK: TEST" not in content.split("```")[0]:
        errors.append(
            "Missing 'TARGET DECK: TEST' at top of file (outside code fences)")
    # Heading counts: Teil 1 fixed (41-45), Teil 2 dynamic (Q&A), Teil 3 fixed (56-60)
    teil1_headings = re.findall(
        r"(?m)^##\s+Teil\s+1\s+—\s+Aufgabe\s+(41|42|43|44|45)\s*$", content)
    teil2_headings = re.findall(
        r"(?m)^##\s+Teil\s+2\s+—\s+Q&A\s+\d+\s*$", content)
    teil3_headings = re.findall(
        r"(?m)^##\s+Teil\s+3\s+—\s+Aufgabe\s+(56|57|58|59|60)\s*$", content)

    if len(teil1_headings) != 5:
        errors.append(
            f"Expected 5 Teil 1 headings (Aufgabe 41-45), found {len(teil1_headings)}")
    if len(teil3_headings) != 5:
        errors.append(
            f"Expected 5 Teil 3 headings (Aufgabe 56-60), found {len(teil3_headings)}")
    if len(teil2_headings) < 1:
        errors.append(
            "Expected at least 1 Teil 2 Q&A heading (## Teil 2 — Q&A NN)")

    expected_blocks = len(teil1_headings) + \
        len(teil2_headings) + len(teil3_headings)
    if len(blocks) != expected_blocks:
        errors.append(
            f"Block count mismatch: found {len(blocks)} blocks, expected {expected_blocks} based on headings (5+N+5)")
    # Listening_2 header
    for i, b in enumerate(blocks):
        if not b["has_header"]:
            errors.append(
                f"Block {i+1}: missing 'Listening_2' note-type header")
    return len(errors) == 0, errors


def check_field_completeness(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-3-2.2 — Field completeness."""
    errors = []
    required_nonempty = ["de_1", "en_1", "note_1", "de_1_audio", "de_1_wave",
                         "de_1_start", "de_1_end"]
    audio_pattern = re.compile(r"^\[sound:(.+\.mp3)\]$")
    for i, b in enumerate(blocks):
        for field in required_nonempty:
            val = b["fields"].get(field)
            if val is None:
                errors.append(f"Block {i+1}: field '{field}' is missing")
            elif val == "":
                errors.append(f"Block {i+1}: field '{field}' is empty")
        # Audio format checks
        audio_val = b["fields"].get("de_1_audio", "")
        wave_val = b["fields"].get("de_1_wave", "")
        if audio_val:
            m = audio_pattern.match(audio_val)
            if not m:
                errors.append(
                    f"Block {i+1}: de_1_audio format invalid — expected '[sound:filename.mp3]', got '{audio_val[:60]}'")
            else:
                # Consistency: filename inside [sound:...] must match de_1_wave
                inner_filename = m.group(1)
                if wave_val and inner_filename != wave_val:
                    errors.append(
                        f"Block {i+1}: de_1_audio filename '{inner_filename}' != de_1_wave '{wave_val}'")
        if wave_val and not wave_val.endswith(".mp3"):
            errors.append(
                f"Block {i+1}: de_1_wave should be a plain .mp3 filename, got '{wave_val[:60]}'")
    return len(errors) == 0, errors


def check_html_format(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-3-2.3 — HTML format validation."""
    errors = []
    span_pattern = re.compile(
        r'<span\s+data-start="[\d.]+" data-end="[\d.]+">')
    bold_pattern = re.compile(r"<b>.+?</b>\s*—")
    for i, b in enumerate(blocks):
        de_1 = b["fields"].get("de_1", "")
        en_1 = b["fields"].get("en_1", "")
        note_1 = b["fields"].get("note_1", "")
        # de_1: must have <span> tags
        if not span_pattern.search(de_1):
            errors.append(
                f"Block {i+1}: de_1 has no <span data-start data-end> tags")
        # en_1: must have <b>...</b> — pattern
        if not bold_pattern.search(en_1):
            errors.append(
                f"Block {i+1}: en_1 has no '<b>...</b> —' translation pattern")
        # note_1: must have both sections
        if "<b>Key Words and Phrases</b>" not in note_1:
            errors.append(
                f"Block {i+1}: note_1 missing '<b>Key Words and Phrases</b>'")
        if "<b>Grammar to Remember</b>" not in note_1:
            errors.append(
                f"Block {i+1}: note_1 missing '<b>Grammar to Remember</b>'")
    return len(errors) == 0, errors


def check_content_minimums(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-3-2.4 — Content minimums."""
    errors = []
    teil2_count = max(0, len(blocks) - 10)
    for i, b in enumerate(blocks):
        note_1 = b["fields"].get("note_1", "")
        # Determine block type: blocks 0-4 = Teil 1, blocks 5..(4+N) = Teil 2, last 5 = Teil 3
        if i < 5:
            label = f"Teil 1 Aufgabe {41 + i}"
        elif i < 5 + teil2_count:
            label = f"Teil 2 Q&A {i - 4}"
        else:
            label = f"Teil 3 Aufgabe {56 + (i - (5 + teil2_count))}"
            min_kw, min_gr = 5, 3

        min_kw, min_gr = 5, 3

        # Split at Grammar section
        parts = note_1.split("<b>Grammar to Remember</b>")
        kw_section = parts[0] if len(parts) >= 1 else ""
        gr_section = parts[1] if len(parts) >= 2 else ""

        kw_count = kw_section.count("•")
        gr_count = gr_section.count("•")

        if kw_count < min_kw:
            errors.append(
                f"Block {i+1} ({label}): Key Words has {kw_count} items, need ≥{min_kw}")
        if gr_count < min_gr:
            errors.append(
                f"Block {i+1} ({label}): Grammar has {gr_count} items, need ≥{min_gr}")
    return len(errors) == 0, errors


def check_timestamps(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-3-2.5 — Timestamp validation."""
    errors = []
    span_ts_pattern = re.compile(
        r'<span\s+data-start="([\d.]+)"\s+data-end="([\d.]+)">')
    for i, b in enumerate(blocks):
        start_str = b["fields"].get("de_1_start", "")
        end_str = b["fields"].get("de_1_end", "")
        de_1 = b["fields"].get("de_1", "")

        # Validate de_1_start and de_1_end are numbers
        try:
            block_start = float(start_str)
        except ValueError:
            errors.append(
                f"Block {i+1}: de_1_start '{start_str}' is not a valid number")
            continue
        try:
            block_end = float(end_str)
        except ValueError:
            errors.append(
                f"Block {i+1}: de_1_end '{end_str}' is not a valid number")
            continue

        # start < end
        if block_start >= block_end:
            errors.append(
                f"Block {i+1}: de_1_start ({block_start}) >= de_1_end ({block_end})")

        # Validate span timestamps
        spans = span_ts_pattern.findall(de_1)
        if not spans:
            continue
        for j, (s, e) in enumerate(spans):
            try:
                float(s)
                float(e)
            except ValueError:
                errors.append(
                    f"Block {i+1}: span {j+1} has invalid timestamp(s): start={s}, end={e}")

        # First span data-start should match de_1_start
        first_start = float(spans[0][0])
        if abs(first_start - block_start) > 0.01:
            errors.append(
                f"Block {i+1}: first span data-start ({first_start}) != de_1_start ({block_start})"
            )
        # Last span data-end should match de_1_end
        last_end = float(spans[-1][1])
        if abs(last_end - block_end) > 0.01:
            errors.append(
                f"Block {i+1}: last span data-end ({last_end}) != de_1_end ({block_end})"
            )
    return len(errors) == 0, errors


def check_translation_consistency(blocks: list[dict]) -> tuple[bool, list[str]]:
    """B1-3-2.6 — Sentence-by-sentence translation consistency."""
    errors = []

    def strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()

    def split_lines(value: str) -> list[str]:
        return [part.strip() for part in re.split(r"\s*<br>\s*", value.strip()) if part.strip()]

    def extract_terminal_punct(text: str) -> str:
        # Ignore trailing quotes/brackets when checking sentence-final punctuation.
        cleaned = text.strip()
        cleaned = re.sub(r"[\s\"'”’)\]]+$", "", cleaned)
        m = re.search(r"([.!?])$", cleaned)
        return m.group(1) if m else ""

    def extract_numeric_signals(text: str, lang: str) -> list[str]:
        # Keep this intentionally light and stable: digits + strong number-word cues.
        tokens = []
        low = text.lower()

        digit_tokens = re.findall(r"\d+(?:[.,:]\d+)*", low)
        tokens.extend(digit_tokens)

        word_tokens = re.findall(r"[a-zA-Z\u00c0-\u017f]+", low)
        if lang == "de":
            de_num_re = re.compile(
                r"^(null|zwei|drei|vier|f(?:u|ü)nf|sechs|sieben|acht|neun|"
                r"zehn|elf|zw(?:o|ö)lf|zwanzig|drei(?:ss|ß)ig|vierzig|f(?:u|ü)nfzig|sechzig|"
                r"siebzig|achtzig|neunzig|hundert|tausend|million(?:en)?|"
                r"(?:zwei|drei|vier|f(?:u|ü)nf|sechs|sieben|acht|neun|zehn|elf|zw(?:o|ö)lf)mal|"
                r".*hundert.*|.*tausend.*)$"
            )
            word_hits = []
            for w in word_tokens:
                if de_num_re.match(w):
                    word_hits.append(w)
        else:
            en_num_re = re.compile(
                r"^(zero|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
                r"thirty|forty|fifty|sixty|seventy|eighty|ninety|twice|thrice|"
                r"hundred|thousand|million|"
                r".*hundred.*|.*thousand.*)$"
            )
            word_hits = []
            for w in word_tokens:
                if en_num_re.match(w):
                    word_hits.append(w)

        # Only count word-numbers as strong signals if there is enough evidence.
        if len(word_hits) >= 2 or any(("hundert" in w or "thousand" in w or "tausend" in w) for w in word_hits):
            tokens.extend(word_hits)
        return tokens

    missing_line_break_after_sentence = re.compile(
        r'<span\s+data-start="[\d.]+"\s+data-end="[\d.]+">([^<]*[.!?])</span>\s+(?=<span\s+data-start=)'
    )
    _ABBR_SET = {"Dr", "Mr", "Mrs", "Ms", "Prof", "Nr", "St", "Str", "ca", "bzw", "usw", "etc", "z", "d", "u"}
    for i, b in enumerate(blocks):
        de_1 = b["fields"].get("de_1", "")
        en_1 = b["fields"].get("en_1", "")
        if not de_1 or not en_1:
            continue

        # Enforce sentence-per-line by requiring <br> whenever a sentence-ending span
        # is followed by another span — but skip abbreviations and ordinal numbers.
        for m in missing_line_break_after_sentence.finditer(de_1):
            span_text = m.group(1).rstrip()
            bare = span_text.rstrip('.!?"' + "'" + ')')
            if bare in _ABBR_SET:
                continue  # Abbreviation, not a sentence boundary
            if bare.isdigit() and span_text.endswith("."):
                continue  # Ordinal number
            errors.append(
                f"Block {i+1}: de_1 is not sentence-per-line (missing <br> after sentence-ending span)"
            )
            break  # One error per block is enough

        de_breaks = de_1.count("<br>")
        de_sentences = de_breaks + 1
        en_sentences = en_1.count("<br>") + 1
        if de_sentences != en_sentences:
            errors.append(
                f"Block {i+1}: de_1 has {de_sentences} sentence(s) but en_1 has {en_sentences} translation(s)"
            )

        # Pair-level checks for drift prevention.
        de_lines = split_lines(de_1)
        en_lines = split_lines(en_1)
        pair_count = min(len(de_lines), len(en_lines))
        for j in range(pair_count):
            de_plain = strip_html(de_lines[j])

            en_match = re.match(r"^<b>(.*?)</b>\s*—\s*(.*)$", en_lines[j])
            en_trans = en_match.group(2).strip(
            ) if en_match else strip_html(en_lines[j])

            # 1) Punctuation parity (stable signal for sentence boundary drift).
            de_p = extract_terminal_punct(de_plain)
            en_p = extract_terminal_punct(en_trans)
            if de_p == "?" and en_p != "?":
                errors.append(
                    f"Block {i+1}, pair {j+1}: punctuation mismatch (DE ends with '?', EN ends with '{en_p or 'none'}')"
                )
            elif de_p == "!" and en_p != "!":
                errors.append(
                    f"Block {i+1}, pair {j+1}: punctuation mismatch (DE ends with '{de_p}', EN ends with '{en_p or 'none'}')"
                )
            elif de_p == "." and en_trans.rstrip().endswith(","):
                errors.append(
                    f"Block {i+1}, pair {j+1}: punctuation mismatch (DE ends with '.', EN ends with trailing comma)"
                )

            # 2) Content match: bold DE text in en_1 must match de_1 plain text.
            if en_match:
                en_bold_de = en_match.group(1).strip()

                # Canonical numeric parity checks DE source vs DE echo.
                # Do not block on EN translation style (digits vs words).
                de_nums = extract_numeric_signals(de_plain, "de")
                echo_nums = extract_numeric_signals(en_bold_de, "de")
                if de_nums and not echo_nums:
                    errors.append(
                        f"Block {i+1}, pair {j+1}: de_1 has number-like tokens {de_nums[:4]} but en_1 bold DE has none"
                    )
                if echo_nums and not de_nums:
                    errors.append(
                        f"Block {i+1}, pair {j+1}: en_1 bold DE has number-like tokens {echo_nums[:4]} but de_1 has none"
                    )
                # and strip ordinal periods (build_spans may remove them from de_1).
                ordinal_period_re = re.compile(r'(\d+)\.')
                de_norm = ordinal_period_re.sub(r'\1', " ".join(de_plain.split()))
                en_bold_norm = ordinal_period_re.sub(r'\1', " ".join(en_bold_de.split()))
                if de_norm != en_bold_norm:
                    # Show a short snippet to help locate the mismatch.
                    de_snip = de_norm[:60] + ("..." if len(de_norm) > 60 else "")
                    en_snip = en_bold_norm[:60] + ("..." if len(en_bold_norm) > 60 else "")
                    errors.append(
                        f"Block {i+1}, pair {j+1}: de_1 text does not match en_1 bold DE text\n"
                        f"        de_1: \"{de_snip}\"\n"
                        f"        en_1: \"{en_snip}\""
                    )
    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_listening_2.py <path-to-generated-file.md>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    content = filepath.read_text(encoding="utf-8")
    blocks = parse_blocks(content)

    checks = [
        ("B1-3-2.1 Block Structure", check_structure, (content, blocks)),
        ("B1-3-2.2 Field Completeness", check_field_completeness, (blocks,)),
        ("B1-3-2.3 HTML Format", check_html_format, (blocks,)),
        ("B1-3-2.4 Content Minimums", check_content_minimums, (blocks,)),
        ("B1-3-2.5 Timestamp Validation", check_timestamps, (blocks,)),
        ("B1-3-2.6 Translation Consistency",
         check_translation_consistency, (blocks,)),
    ]

    all_pass = True
    print(f"\n{'='*60}")
    print(f"  Listening_2 Validation — {filepath.name}")
    print(f"  Blocks found: {len(blocks)}")
    print(f"{'='*60}\n")

    for name, fn, args in checks:
        passed, errors = fn(*args)
        status = f"{PASS_ICON} PASS" if passed else f"{FAIL_ICON} FAIL"
        print(f"  {name}: {status}")
        if errors:
            for e in errors:
                print(f"    {WARN_ICON}  {e}")
        if not passed:
            all_pass = False
        print()

    print(f"{'='*60}")
    if all_pass:
        print(f"  {DONE_ICON} ALL CHECKS PASSED")
    else:
        print(f"  {STOP_ICON} SOME CHECKS FAILED - review errors above")
    print(f"{'='*60}\n")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()

