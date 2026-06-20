#!/usr/bin/env python3
"""
generate_listening_4.py — Generate marker-based Listening_2 output from transcript JSON.

This version builds blocks automatically from marker phrases in the transcript:
- opening marker: "Teil N"
- closing marker: "Ende des Teil N"

Usage:
    python Requirement/generate_listening_4.py
"""

import html
import json
import re
from pathlib import Path

OUTPUT = Path(r"Outputs\Listening-generated.md")
MAX_BLOCK_SECONDS = 60.0
TARGET_BLOCK_SECONDS = 45.0
MIN_BLOCK_SECONDS = 25.0
MIN_FRAGMENT_DURATION = 2.5
MAX_FRAGMENT_WORDS = 3

NUMBER_WORDS = {
    "ein": 1,
    "eins": 1,
    "eine": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "funf": 5,
    "fuenf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
}

INTRO_PATTERNS = [
    re.compile(
        r"^Beratungsgesprach,\s*Teil\s+(?:eins|zwei|drei|vier|funf|fuenf|\d+)[.!?]?$", re.IGNORECASE),
    re.compile(r"^hoertexte\s+zum\s+kursbuch\b", re.IGNORECASE),
    re.compile(r"^Horen\s+Sie\b", re.IGNORECASE),
    re.compile(r"^Lesen\s+Sie\b", re.IGNORECASE),
    re.compile(r"^Sie\s+horen\b", re.IGNORECASE),
    re.compile(r"^Dazu\s+sollen\s+Sie\b", re.IGNORECASE),
    re.compile(r"^Markieren\s+Sie\b", re.IGNORECASE),
]

MARKER_TEXT_PATTERN = re.compile(
    r"\b(?:ende\s+des\s+)?teil\s+(eins|zwei|drei|vier|funf|fuenf|sechs|sieben|acht|neun|zehn|\d+)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "einem", "einen",
    "und", "oder", "aber", "doch", "nur", "auch", "nicht", "kein", "keine", "ist", "sind",
    "war", "waren", "hat", "haben", "ich", "du", "er", "sie", "wir", "ihr", "man", "es",
    "mit", "von", "auf", "im", "in", "an", "am", "zum", "zur", "fur", "dass", "wenn",
    "dann", "noch", "mal", "ja", "so", "zu", "bei", "wie", "was", "wo", "wer", "wann",
    "ihnen", "ihm", "ihn", "ihr", "ihre", "ihren", "ihrem", "ihrer", "ihres",
    "uns", "unser", "unsere", "unseren", "unserem", "unserer", "unseres",
    "mein", "meine", "meinen", "meinem", "meiner", "meines",
    "dein", "deine", "deinen", "deinem", "deiner", "deines",
    "sein", "seine", "seinen", "seinem", "seiner", "seines",
    "dies", "diese", "dieser", "dieses", "jen", "jene", "jener", "jenes",
    "etwas", "alles", "nichts", "manche", "viele", "alle",
}

LOW_VALUE_TOKENS = {
    "hallo", "guten", "tag", "abend", "bitte", "danke", "wiedersehen", "wiederhoren",
    "herr", "frau", "herein", "ja", "nein", "okay", "gut", "ach", "hm", "aha",
}

GLOSS_MAP = {
    "angebot": "quote / offer",
    "angebote": "quotes / offers",
    "rechnung": "invoice / bill",
    "rechnungen": "invoices / bills",
    "beratung": "consultation / advice",
    "beratungsgespraech": "consultation conversation",
    "anderungswuensche": "change requests",
    "katalog": "catalogue",
    "katalogseite": "catalogue page",
    "modell": "model",
    "modellreihe": "model series",
    "waschbecken": "washbasin",
    "dusche": "shower",
    "badewanne": "bathtub",
    "armaturen": "fittings / taps",
    "baustelle": "construction site",
    "firma": "company",
    "jahrestagung": "annual conference",
    "spiegel": "mirror",
    "termin": "appointment / deadline",
    "arbeit": "work",
    "arbeiten": "works / tasks",
    "mail": "email",
    "adresse": "address",
    "problem": "problem",
    "probleme": "problems",
    "frage": "question",
    "fragen": "questions",
    "aufgabe": "task",
    "aufgaben": "tasks",
    "beispiel": "example",
    "besprechung": "meeting / discussion",
    "aktennotiz": "case/file note",
    "aktennotizen": "case/file notes",
    "moment": "moment",
    "gespraech": "conversation",
    "gespraeche": "conversations",
}

TOKEN_EDGE_RE = re.compile(
    r"^[^A-Za-z0-9\u00c0-\u017f]+|[^A-Za-z0-9\u00c0-\u017f]+$")


def latest_transcript() -> Path:
    files = sorted(Path("Transcripts").glob("*.json"),
                   key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError("No transcript JSON found in Transcripts/")
    return files[-1]


def latest_audio_name() -> str:
    files = sorted(Path("Audios").glob("*.mp3"),
                   key=lambda p: p.stat().st_mtime)
    if not files:
        return "Lektion-7.mp3"
    return files[-1].name


def normalize_token(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    text = (
        text.replace("a", "a")
        .replace("o", "o")
        .replace("u", "u")
        .replace("ss", "ss")
        .replace("ue", "ue")
        .replace("oe", "oe")
        .replace("ae", "ae")
    )
    # Also normalize umlauts if they are present.
    text = (
        text.replace("\u00e4", "ae")
        .replace("\u00f6", "oe")
        .replace("\u00fc", "ue")
        .replace("\u00df", "ss")
    )
    return text


def token_to_number(token: str):
    t = normalize_token(token)
    if not t:
        return None
    if t.isdigit():
        return int(t)
    return NUMBER_WORDS.get(t)


def flatten_words(segments):
    words = []
    for segment in segments:
        for word in segment.get("words", []):
            if word.get("type") != "word":
                continue
            words.append({
                "text": word.get("text", ""),
                "start": float(word.get("start", 0.0)),
                "end": float(word.get("end", 0.0)),
            })
    return words


def detect_marker_regions(words):
    starts = {}
    ends = {}
    n = len(words)

    i = 0
    while i < n:
        t0 = normalize_token(words[i]["text"])

        # Ende des Teil N
        if i + 3 < n:
            t1 = normalize_token(words[i + 1]["text"])
            t2 = normalize_token(words[i + 2]["text"])
            n4 = token_to_number(words[i + 3]["text"])
            if t0 == "ende" and t1 == "des" and t2 == "teil" and n4 is not None:
                ends.setdefault(n4, []).append({
                    "word_index": i,
                    "start_time": words[i]["start"],
                    "end_time": words[i + 3]["end"],
                })
                i += 4
                continue

        # Teil N (but not the Teil in "Ende des Teil N")
        if i + 1 < n and t0 == "teil":
            prev1 = normalize_token(words[i - 1]["text"]) if i - 1 >= 0 else ""
            prev2 = normalize_token(words[i - 2]["text"]) if i - 2 >= 0 else ""
            n2 = token_to_number(words[i + 1]["text"])
            if n2 is not None and not (prev1 == "des" and prev2 == "ende"):
                starts.setdefault(n2, []).append({
                    "word_index": i,
                    "start_time": words[i]["start"],
                    "end_time": words[i + 1]["end"],
                })
                i += 2
                continue

        i += 1

    regions = []
    for teil_num, start_events in starts.items():
        end_events = ends.get(teil_num, [])
        used = set()
        for start in start_events:
            found = None
            for idx, end in enumerate(end_events):
                if idx in used:
                    continue
                if end["word_index"] > start["word_index"]:
                    found = (idx, end)
                    break
            if not found:
                continue
            idx, end = found
            used.add(idx)
            region_start = start["end_time"]
            region_end = end["start_time"]
            if region_end > region_start:
                regions.append((teil_num, region_start, region_end))

    regions.sort(key=lambda x: x[0])
    return regions


def collect_region_words(words, start_time: float, end_time: float):
    out = []
    for word in words:
        mid = (word["start"] + word["end"]) / 2.0
        if start_time <= mid <= end_time:
            out.append(word)
    return out


def words_to_sentences(words_list):
    """Group words into sentence lists by punctuation."""
    month_names = {
        "januar", "februar", "maerz", "marz", "april", "mai", "juni", "juli",
        "august", "september", "oktober", "november", "dezember",
    }
    date_continuations = {"bis", "und", "oder", "ab", "vom", "zum"}

    sentences = []
    current = []
    for idx, word in enumerate(words_list):
        current.append(word)
        text = word["text"].rstrip()
        if not text:
            continue
        if text[-1] not in ".!?" or text.endswith("..."):
            continue

        bare = text.rstrip(".!?")
        if bare.isdigit() and idx + 1 < len(words_list):
            next_text = normalize_token(words_list[idx + 1]["text"])
            if next_text in month_names or next_text in date_continuations:
                continue

        sentences.append(current)
        current = []

    if current:
        sentences.append(current)

    return sentences


def sentence_plain_text(sentence_words):
    return " ".join(w["text"] for w in sentence_words).strip()


def is_non_content_sentence(sentence_words) -> bool:
    text = sentence_plain_text(sentence_words)
    text_norm = normalize_token(text)

    if MARKER_TEXT_PATTERN.search(text_norm):
        return True

    for pattern in INTRO_PATTERNS:
        if pattern.search(text_norm):
            return True

    return False


def drop_non_content_prefix(sentences):
    while sentences:
        if is_non_content_sentence(sentences[0]):
            sentences.pop(0)
            continue
        break

    return sentences


def build_spans(sentence_words):
    parts = []
    for word in sentence_words:
        parts.append(
            f'<span data-start="{word["start"]}" data-end="{word["end"]}">{html.escape(word["text"])}</span>'
        )
    return " ".join(parts)


def split_into_blocks(sentences):
    blocks = []
    current = []

    for sentence in sentences:
        if not current:
            current = [sentence]
            continue

        current_start = current[0][0]["start"]
        current_end = current[-1][-1]["end"]
        next_end = sentence[-1]["end"]

        current_duration = current_end - current_start
        next_duration = next_end - current_start

        if next_duration > MAX_BLOCK_SECONDS and current_duration >= MIN_BLOCK_SECONDS:
            blocks.append(current)
            current = [sentence]
            continue

        # Prefer splitting around target duration at a sentence boundary.
        if current_duration >= TARGET_BLOCK_SECONDS and next_duration > TARGET_BLOCK_SECONDS + 8:
            blocks.append(current)
            current = [sentence]
            continue

        current.append(sentence)

    if current:
        blocks.append(current)

    return merge_short_fragment_blocks(blocks)


def block_duration(block):
    return block[-1][-1]["end"] - block[0][0]["start"]


def block_word_count(block):
    return sum(len(sentence) for sentence in block)


def is_short_fragment_block(block):
    return block_duration(block) < MIN_FRAGMENT_DURATION and block_word_count(block) <= MAX_FRAGMENT_WORDS


def merge_short_fragment_blocks(blocks):
    if not blocks:
        return blocks

    merged = []
    index = 0
    while index < len(blocks):
        block = blocks[index]

        if is_short_fragment_block(block):
            # Prefer merging tiny fragments into the previous block if we can stay within MAX_BLOCK_SECONDS.
            if merged and block_duration(merged[-1]) + block_duration(block) <= MAX_BLOCK_SECONDS:
                merged[-1].extend(block)
                index += 1
                continue

            # Otherwise, try merging into the next block.
            if index + 1 < len(blocks):
                next_block = blocks[index + 1]
                combined_duration = next_block[-1][-1]["end"] - \
                    block[0][0]["start"]
                if combined_duration <= MAX_BLOCK_SECONDS:
                    blocks[index + 1] = block + next_block
                    index += 1
                    continue

        merged.append(block)
        index += 1

    return merged


def detect_person_names(block_sentences):
    names = set()
    title_pattern = re.compile(
        r"\b(?:Herr|Frau)\s+([A-Z][A-Za-z\u00c0-\u017f-]+)")
    for sentence in block_sentences:
        text = sentence_plain_text(sentence)
        for match in title_pattern.finditer(text):
            names.add(normalize_token(match.group(1)))
    return names


def choose_keywords(block_sentences):
    person_names = detect_person_names(block_sentences)
    stats = {}

    for sentence in block_sentences:
        for index, word in enumerate(sentence):
            token = TOKEN_EDGE_RE.sub("", word["text"].strip())
            norm = normalize_token(token)
            if not norm:
                continue
            if len(norm) < 4:
                continue
            if norm in STOPWORDS or norm in LOW_VALUE_TOKENS:
                continue
            if norm in person_names:
                continue
            if norm.isdigit():
                continue

            if norm not in stats:
                stats[norm] = {
                    "display": token,
                    "count": 0,
                    "non_start": 0,
                    "capitalized": 0,
                }

            stats[norm]["count"] += 1
            if index > 0:
                stats[norm]["non_start"] += 1
            if token[:1].isupper():
                stats[norm]["capitalized"] += 1

    ranked = []
    for norm, info in stats.items():
        score = 0
        if info["non_start"] > 0:
            score += 3
        if info["capitalized"] > 0:
            score += 2
        if info["count"] > 1:
            score += 1
        if norm in GLOSS_MAP:
            score += 2
        ranked.append((score, info["count"], norm, info["display"]))

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    selected = [(item[3], item[2]) for item in ranked[:5]]

    fallback_terms = [
        ("Gesprach", "gespraech"),
        ("Arbeit", "arbeit"),
        ("Termin", "termin"),
        ("Angebot", "angebot"),
        ("Rechnung", "rechnung"),
    ]
    used_norms = {norm for _, norm in selected}
    for display, norm in fallback_terms:
        if len(selected) >= 5:
            break
        if norm in used_norms:
            continue
        selected.append((display, norm))
        used_norms.add(norm)

    return selected


def keyword_gloss(norm: str):
    if norm in GLOSS_MAP:
        return GLOSS_MAP[norm]

    variants = [norm]
    for suffix in ("en", "ern", "er", "e", "n", "s"):
        if norm.endswith(suffix) and len(norm) > len(suffix) + 2:
            variants.append(norm[: -len(suffix)])

    for variant in variants:
        if variant in GLOSS_MAP:
            return GLOSS_MAP[variant]

    if norm.endswith("ung"):
        return "noun (often an action/process)"
    if norm.endswith("keit") or norm.endswith("heit"):
        return "abstract noun"
    if norm.endswith("lich") or norm.endswith("ig"):
        return "adjective form"
    if norm.endswith("en"):
        return "verb form in context"
    return "context term used in the dialogue"


def build_grammar_points(block_sentences):
    block_text = " ".join(sentence_plain_text(sentence)
                          for sentence in block_sentences)
    norm = normalize_token(block_text)
    points = []

    if "wenn" in norm:
        points.append((
            "wenn-clause",
            "Use when + verb-final clause to describe condition or time.",
        ))
    if "dass" in norm:
        points.append((
            "dass-clause",
            "In subordinate clauses with dass, the conjugated verb moves to the end.",
        ))
    if "?" in block_text:
        points.append((
            "Question structure",
            "Yes/no questions place the finite verb before the subject.",
        ))
    if "werden" in norm or "wurde" in norm or "wurden" in norm:
        points.append((
            "Passive forms",
            "werden + Partizip II is used to focus on process/result.",
        ))

    defaults = [
        ("Word order", "Main clauses keep verb in position two."),
        ("Modal particles", "ja, doch, mal add tone and speaker attitude."),
        ("Tense consistency", "Keep tense changes clear across the dialogue."),
    ]

    seen = set()
    final_points = []
    for title, desc in points + defaults:
        key = normalize_token(title)
        if key in seen:
            continue
        seen.add(key)
        final_points.append((title, desc))
        if len(final_points) == 3:
            break

    return final_points


def build_note_placeholder():
    """
    Intentionally returns placeholders only.
    Meaningful note content must be authored by a human/LLM pass, not generated by code.
    """
    return (
        "<b>Key Words and Phrases</b><br>"
        "• <b>TODO_TERM_1</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_2</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_3</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_4</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_5</b> — Add glossary note.<br>"
        "<br>"
        "<b>Grammar to Remember</b><br>"
        "• <b>TODO_GRAMMAR_1</b> — Add grammar explanation.<br>"
        "• <b>TODO_GRAMMAR_2</b> — Add grammar explanation.<br>"
        "• <b>TODO_GRAMMAR_3</b> — Add grammar explanation."
    )


def build_translation_placeholders(block_sentences):
    """
    Intentionally returns placeholders only.
    Natural sentence translations must be authored by a human/LLM pass.
    """
    lines = []
    for sentence in block_sentences:
        german = sentence_plain_text(sentence)
        lines.append(
            f"<b>{html.escape(german)}</b> — TODO: add English translation.")
    return "<br>".join(lines)


def main():
    transcript_path = latest_transcript()
    audio_name = latest_audio_name()

    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    words = flatten_words(segments)
    regions = detect_marker_regions(words)

    if not regions:
        raise RuntimeError(
            "No marker regions detected (Teil N ... Ende des Teil N)")

    output_lines = ["TARGET DECK: TEST", ""]

    block_total = 0
    for teil_num, region_start, region_end in regions:
        region_words = collect_region_words(words, region_start, region_end)
        if not region_words:
            continue

        sentences = words_to_sentences(region_words)
        sentences = drop_non_content_prefix(sentences)
        sentences = [
            sentence for sentence in sentences if not is_non_content_sentence(sentence)]
        if not sentences:
            continue

        blocks = split_into_blocks(sentences)

        for block_index, block_sentences in enumerate(blocks, start=1):
            block_total += 1
            is_split = len(blocks) > 1
            heading = f"Teil {teil_num}.{block_index}" if is_split else f"Teil {teil_num}"

            de_lines = [build_spans(sentence) for sentence in block_sentences]
            de_1 = "<br>".join(de_lines)
            en_1 = build_translation_placeholders(block_sentences)
            note_1 = build_note_placeholder()

            block_start = block_sentences[0][0]["start"]
            block_end = block_sentences[-1][-1]["end"]
            duration = block_end - block_start

            output_lines.append(f"## {heading}")
            output_lines.append("")
            output_lines.append("```")
            output_lines.append("SSTART")
            output_lines.append("")
            output_lines.append("Listening_2")
            output_lines.append("")
            output_lines.append(f"de_1: {de_1}")
            output_lines.append(f"en_1: {en_1}")
            output_lines.append(f"note_1: {note_1}")
            output_lines.append(f"de_1_audio: [sound:{audio_name}]")
            output_lines.append(f"de_1_wave: {audio_name}")
            output_lines.append(f"de_1_start: {block_start}")
            output_lines.append(f"de_1_end: {block_end}")
            output_lines.append("EEND")
            output_lines.append("```")
            output_lines.append("")

            print(f"  {heading}: {len(block_sentences)} sents, {duration:.1f}s")

    OUTPUT.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"\nGenerated {OUTPUT} from {transcript_path.name}")
    print(f"Total blocks: {block_total}")


if __name__ == "__main__":
    main()
