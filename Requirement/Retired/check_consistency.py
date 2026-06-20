#!/usr/bin/env python3
"""
Character Count Consistency Check for German Listening Files
Requirement B1-2
"""

import re
from pathlib import Path


def remove_punctuation_and_clean(text):
    """
    Remove punctuation, timestamps, and clean text while keeping spaces between words.
    """
    # Remove timestamps (patterns like 0:02, 10:45, 1:23:45, etc.)
    text = re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', '', text)

    # Remove punctuation: . , ; : ! ? " ' ( ) [ ] { } … - – —
    punctuation = r'[.,;:!?\"\'\(\)\[\]\{\}…\-–—]'
    text = re.sub(punctuation, '', text)

    # Remove leading/trailing spaces
    text = text.strip()

    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)

    return text


def count_breakdown_characters(file_path):
    """
    Count characters in all <sentence_DE_...> inside Breakdown sections.
    Returns T1, T2, T3 and TOTAL_BREAKDOWN.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into blocks (START...END)
    blocks = re.findall(r'START(.*?)END', content, re.DOTALL)

    teil_counts = {'1': 0, '2': 0, '3': 0}

    for block in blocks:
        # Identify which Teil this block belongs to
        title_match = re.search(
            r'Title:\s*\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-(\d+)', block)
        if not title_match:
            continue

        teil_number = title_match.group(1)

        # Find all Breakdown sections in this block
        breakdown_sections = re.findall(
            r'## Breakdown(.*?)(?=##|\d{2}_|END|$)', block, re.DOTALL)

        for breakdown in breakdown_sections:
            # Find all German sentences: * "<sentence_DE>" = <translation>
            sentences = re.findall(r'\*\s*"([^"]+)"\s*=', breakdown)

            for sentence in sentences:
                cleaned = remove_punctuation_and_clean(sentence)
                char_count = len(cleaned)
                if teil_number in teil_counts:
                    teil_counts[teil_number] += char_count

    T1 = teil_counts['1']
    T2 = teil_counts['2']
    T3 = teil_counts['3']

    # TOTAL_BREAKDOWN = T1 + 2 × (T2 + T3)
    TOTAL_BREAKDOWN = T1 + 2 * (T2 + T3)

    return T1, T2, T3, TOTAL_BREAKDOWN


def count_transcript_characters(file_path):
    """
    Count characters in the raw transcript file.
    Returns TOTAL_TRANSCRIPT.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the TRANSCRIPT section
    transcript_match = re.search(
        r'## TRANSCRIPT\s*```(.*?)```', content, re.DOTALL)

    if not transcript_match:
        print("Warning: Could not find TRANSCRIPT section")
        return 0

    transcript_text = transcript_match.group(1)

    total_chars = 0

    # Process each line
    for line in transcript_text.split('\n'):
        cleaned = remove_punctuation_and_clean(line)
        total_chars += len(cleaned)

    return total_chars


def calculate_iou(total_breakdown, total_transcript):
    """
    Calculate Intersection over Union (IoU).
    """
    if max(total_breakdown, total_transcript) == 0:
        return 0.0

    iou = min(total_breakdown, total_transcript) / \
        max(total_breakdown, total_transcript)
    return iou


def main():
    # File paths
    base_path = Path(__file__).parent
    generated_file = base_path / "Listening-generated.md"
    transcript_file = base_path / "Transcripts" / "German_Listening_Transcript.md"

    print("=" * 70)
    print("Character Count Consistency Check (Requirement B1-2)")
    print("=" * 70)
    print()

    # B1-2.1: Count breakdown characters
    print("B1-2.1 — Counting characters in Breakdown sections...")
    T1, T2, T3, TOTAL_BREAKDOWN = count_breakdown_characters(generated_file)

    print(f"  Teil 1 (T1): {T1:,} characters")
    print(f"  Teil 2 (T2): {T2:,} characters")
    print(f"  Teil 3 (T3): {T3:,} characters")
    print(f"  Formula: TOTAL_BREAKDOWN = T1 + 2 × (T2 + T3)")
    print(f"  Formula: TOTAL_BREAKDOWN = {T1:,} + 2 × ({T2:,} + {T3:,})")
    print(f"  TOTAL_BREAKDOWN = {TOTAL_BREAKDOWN:,} characters")
    print()

    # B1-2.2: Count transcript characters
    print("B1-2.2 — Counting characters in raw transcript...")
    TOTAL_TRANSCRIPT = count_transcript_characters(transcript_file)
    print(f"  TOTAL_TRANSCRIPT = {TOTAL_TRANSCRIPT:,} characters")
    print()

    # B1-2.3: Calculate IoU
    print("B1-2.3 — Intersection-over-Union (IoU) Validation...")
    iou = calculate_iou(TOTAL_BREAKDOWN, TOTAL_TRANSCRIPT)
    print(
        f"  IoU = min({TOTAL_BREAKDOWN:,}, {TOTAL_TRANSCRIPT:,}) / max({TOTAL_BREAKDOWN:,}, {TOTAL_TRANSCRIPT:,})")
    print(
        f"  IoU = {min(TOTAL_BREAKDOWN, TOTAL_TRANSCRIPT):,} / {max(TOTAL_BREAKDOWN, TOTAL_TRANSCRIPT):,}")
    print(f"  IoU = {iou:.4f} ({iou*100:.2f}%)")
    print()

    # Validation
    print("=" * 70)
    if iou < 0.76:
        print("❌ FAILED: Intersection over Union < 76%. Check the generated file again!")
    else:
        print(f"✅ PASSED: IoU = {iou*100:.2f}% (≥ 76%)")
        print("The file passes the consistency check.")
    print("=" * 70)


if __name__ == "__main__":
    main()
