from __future__ import annotations

import html
import json
import re
from pathlib import Path

from .runtime_paths import get_repo_root

REPO_ROOT = get_repo_root()
OUTPUT = REPO_ROOT / "Outputs" / "Listening-generated.md"
TARGET_BLOCK_SECONDS = 45.0
MAX_BLOCK_SECONDS = 60.0
MIN_BLOCK_SECONDS = 30.0


def latest_transcript() -> Path:
    files = sorted((REPO_ROOT / "Transcripts").glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError("No transcript JSON found in Transcripts/")
    return files[-1]


def latest_audio_name() -> str:
    files = sorted((REPO_ROOT / "Audios").glob("*.mp3"), key=lambda p: p.stat().st_mtime)
    if not files:
        return "Lektion-7.mp3"
    return files[-1].name


def flatten_words(segments: list[dict]) -> list[dict]:
    words: list[dict] = []
    for seg in segments:
        for w in seg.get("words", []):
            if w.get("type") != "word":
                continue
            words.append({"text": w.get("text", ""), "start": float(w.get("start", 0.0)), "end": float(w.get("end", 0.0))})
    return words


def words_to_sentences(words: list[dict]) -> list[list[dict]]:
    sentences: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        cur.append(w)
        t = str(w.get("text", "")).rstrip()
        if t and t[-1] in ".!?" and not t.endswith("..."):
            sentences.append(cur)
            cur = []
    if cur:
        sentences.append(cur)
    return sentences


def split_into_blocks(sentences: list[list[dict]]) -> list[list[list[dict]]]:
    blocks: list[list[list[dict]]] = []
    cur: list[list[dict]] = []

    for sent in sentences:
        if not cur:
            cur = [sent]
            continue

        start = cur[0][0]["start"]
        cur_end = cur[-1][-1]["end"]
        next_end = sent[-1]["end"]

        cur_d = cur_end - start
        next_d = next_end - start

        if next_d > MAX_BLOCK_SECONDS and cur_d >= MIN_BLOCK_SECONDS:
            blocks.append(cur)
            cur = [sent]
            continue

        if cur_d >= TARGET_BLOCK_SECONDS and next_d > TARGET_BLOCK_SECONDS + 8:
            blocks.append(cur)
            cur = [sent]
            continue

        cur.append(sent)

    if cur:
        blocks.append(cur)
    return blocks


def spans(sentence: list[dict]) -> str:
    return " ".join(
        f'<span data-start="{w["start"]}" data-end="{w["end"]}">{html.escape(str(w["text"]))}</span>'
        for w in sentence
    )


def sentence_plain(sentence: list[dict]) -> str:
    return " ".join(str(w["text"]) for w in sentence).strip()


def _topic_from_block(block: list[list[dict]]) -> str:
    first = sentence_plain(block[0]) if block else ""
    tokens = [re.sub(r"[^\wäöüÄÖÜß-]", "", t) for t in first.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return "Inhalt"
    topic = " ".join(tokens[:6])
    return topic[:56].strip()


def placeholder_en(block: list[list[dict]]) -> str:
    return "<br>".join(f"<b>{html.escape(sentence_plain(s))}</b> — TODO: add English translation." for s in block)


def placeholder_note() -> str:
    return (
        "<b>Key Words and Phrases</b><br>"
        "• <b>TODO_TERM_1</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_2</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_3</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_4</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_5</b> — Add glossary note.<br><br>"
        "<b>Grammar to Remember</b><br>"
        "• <b>TODO_GRAMMAR_1</b> — Add grammar explanation.<br>"
        "• <b>TODO_GRAMMAR_2</b> — Add grammar explanation.<br>"
        "• <b>TODO_GRAMMAR_3</b> — Add grammar explanation."
    )


def generate_semantic() -> int:
    tp = latest_transcript()
    audio = latest_audio_name()
    data = json.loads(tp.read_text(encoding="utf-8"))
    words = flatten_words(data.get("segments", []))
    if not words:
        raise RuntimeError("Transcript has no words")

    sentences = words_to_sentences(words)
    if not sentences:
        sentences = [words]

    blocks = split_into_blocks(sentences)

    out = ["TARGET DECK: TEST", ""]
    for i, block in enumerate(blocks, start=1):
        topic = _topic_from_block(block)
        heading = f"Abschnitt {i} — {topic}"
        de_1 = "<br>".join(spans(s) for s in block)
        en_1 = placeholder_en(block)
        note_1 = placeholder_note()
        start = block[0][0]["start"]
        end = block[-1][-1]["end"]

        out.extend([
            f"## {heading}",
            "```",
            "SSTART",
            "",
            "Listening_2",
            "",
            f"de_1: {de_1}",
            f"en_1: {en_1}",
            f"note_1: {note_1}",
            f"de_1_audio: [sound:{audio}]",
            f"de_1_wave: {audio}",
            f"de_1_start: {start}",
            f"de_1_end: {end}",
            "EEND",
            "```",
            "",
        ])

    OUTPUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Generated {OUTPUT} from {tp.name} (semantic fallback)")
    print(f"Total blocks: {len(blocks)}")
    return 0
