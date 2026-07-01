from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

from .runtime_paths import get_repo_root

REPO_ROOT = get_repo_root()
OUTPUT_FINAL = REPO_ROOT / "Outputs" / "Listening-generated.md"
OUTPUT_DRAFT = REPO_ROOT / "Outputs" / "Listening-generated.draft.md"
OUTPUT = OUTPUT_FINAL
TARGET_BLOCK_SECONDS = 45.0
MAX_BLOCK_SECONDS = 60.0
MIN_BLOCK_SECONDS = 30.0
HARD_SPLIT_GAP_SECONDS = 20.0
STRONG_ITEM_SPLIT_MIN_SECONDS = 20.0
ABBREVIATIONS = {"Dr", "Mr", "Mrs", "Ms", "Prof", "Nr", "St", "Str", "ca", "bzw", "usw", "etc", "z", "d", "u"}
MONTH_NAMES = {"Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"}
DATE_CONTINUATIONS = {"bis", "und", "oder", "ab", "vom", "zum"}
INSTRUCTION_PATTERNS = (
    r"^zertifikat b1\b",
    r"^zertifikat b eins\b",
    r"^modul horen\b",
    r"^horen teil\b",
    r"^sie horen nun\b",
    r"^sie horen jeden text\b",
    r"^sie horen jetzt den text noch einmal\b",
    r"^sie horen den text noch einmal\b",
    r"^sie horen (den text|das gesprach|die diskussion) einmal\b",
    r"^sie horen (den text|das gesprach|die diskussion) zweimal\b",
    r"^sie horen den wetterbericht im radio\b",
    r"^nun horen sie den text noch einmal\b",
    r"^dazu losen sie (funf|sieben|acht) aufgaben\b",
    r"^ordnen sie die aussagen zu\b",
    r"^wer sagt was\b",
    r"^zu jedem text\b",
    r"^wahlen sie\b",
    r"^lesen sie\b",
    r"^dazu haben sie\b",
    r"^sie horen eine\b",
)
REPLAY_MARKERS = {
    "sie horen jetzt den text noch einmal",
    "sie horen den text noch einmal",
    "nun horen sie den text noch einmal",
}
STRONG_ITEM_START_PATTERNS = (
    r"^hallo\b",
    r"^achtung autofahrer\b",
    r"^gleis\b",
    r"^eine wichtige information\b",
    r"^der wetterbericht\b",
)
IMPLICIT_REPLAY_GAP_SECONDS = 5.0
IMPLICIT_REPLAY_MATCH_LENGTH = 2


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
    for index, w in enumerate(words):
        cur.append(w)
        t = str(w.get("text", "")).rstrip()
        if t and t[-1] in ".!?" and not t.endswith("..."):
            bare = t.rstrip(".!?")
            if bare in ABBREVIATIONS:
                continue
            if bare.isdigit() and index + 1 < len(words):
                next_text = str(words[index + 1].get("text", "")).rstrip(".,;:!?")
                if next_text in MONTH_NAMES or next_text.lower() in DATE_CONTINUATIONS:
                    continue
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
        next_start = sent[0]["start"]
        next_end = sent[-1]["end"]

        cur_d = cur_end - start
        next_d = next_end - start

        if next_start - cur_end >= HARD_SPLIT_GAP_SECONDS and _is_strong_item_start(sentence_plain(sent)):
            blocks.append(cur)
            cur = [sent]
            continue

        if _is_strong_item_start(sentence_plain(sent)) and cur_d >= STRONG_ITEM_SPLIT_MIN_SECONDS:
            blocks.append(cur)
            cur = [sent]
            continue

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

def normalize_sentence_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text

def sentence_compare_key(text: str) -> str:
    text = normalize_sentence_text(text)
    text = re.sub(r"[^\w\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def is_instruction_sentence(text: str) -> bool:
    normalized = normalize_sentence_text(text)
    return any(re.match(pattern, normalized) for pattern in INSTRUCTION_PATTERNS)

def _lookahead_matches_seen(sentences: list[list[dict]], index: int, seen_order: list[str], offset: int = 1) -> bool:
    if len(seen_order) < IMPLICIT_REPLAY_MATCH_LENGTH:
        return False
    if index + offset + IMPLICIT_REPLAY_MATCH_LENGTH - 1 >= len(sentences):
        return False
    lookahead = [
        sentence_compare_key(sentence_plain(sentences[index + offset + delta]))
        for delta in range(IMPLICIT_REPLAY_MATCH_LENGTH)
    ]
    for start in range(len(seen_order) - IMPLICIT_REPLAY_MATCH_LENGTH + 1):
        if seen_order[start:start + IMPLICIT_REPLAY_MATCH_LENGTH] == lookahead:
            return True
    return False

def _starts_implicit_replay(sentences: list[list[dict]], index: int, seen_order: list[str]) -> bool:
    if index <= 0:
        return False
    gap = float(sentences[index][0]["start"]) - float(sentences[index - 1][-1]["end"])
    if gap < IMPLICIT_REPLAY_GAP_SECONDS:
        return False
    return _lookahead_matches_seen(sentences, index, seen_order)

def _prepare_sentences(words: list[dict]) -> list[list[dict]]:
    sentences = words_to_sentences(words)
    if not sentences:
        sentences = [words]

    cleaned: list[list[dict]] = []
    seen: set[str] = set()
    seen_order: list[str] = []
    replay_window = False
    for index, sentence in enumerate(sentences):
        plain = sentence_plain(sentence)
        normalized = normalize_sentence_text(plain)
        compare_key = sentence_compare_key(plain)
        if compare_key in REPLAY_MARKERS:
            replay_window = True
            continue
        if is_instruction_sentence(plain):
            continue
        if not replay_window and _starts_implicit_replay(sentences, index, seen_order):
            replay_window = True
            continue
        if replay_window and compare_key not in seen and _lookahead_matches_seen(sentences, index, seen_order):
            continue
        if replay_window and compare_key in seen:
            continue
        replay_window = False
        cleaned.append(sentence)
        if compare_key:
            seen.add(compare_key)
            seen_order.append(compare_key)
    return cleaned or sentences

def _is_strong_item_start(text: str) -> bool:
    compare_key = sentence_compare_key(text)
    return any(re.match(pattern, compare_key) for pattern in STRONG_ITEM_START_PATTERNS)


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


def generate_semantic(
    transcript_path: Path | None = None,
    audio_name: str | None = None,
    output_path: Path | None = None,
) -> int:
    tp = transcript_path or latest_transcript()
    audio = audio_name or latest_audio_name()
    print(f"Semantic source transcript: {tp}")
    print(f"Semantic source audio: {audio}")
    data = json.loads(tp.read_text(encoding="utf-8"))
    words = flatten_words(data.get("segments", []))
    if not words:
        raise RuntimeError("Transcript has no words")

    sentences = _prepare_sentences(words)

    blocks = split_into_blocks(sentences)
    block_durations = [round(block[-1][-1]["end"] - block[0][0]["start"], 2) for block in blocks]
    print(
        "Semantic split summary: "
        f"sentences={len(sentences)} blocks={len(blocks)} "
        f"target~{TARGET_BLOCK_SECONDS:.0f}s min={MIN_BLOCK_SECONDS:.0f}s max={MAX_BLOCK_SECONDS:.0f}s"
    )
    if block_durations:
        print(f"Block durations: {block_durations[:8]}{'...' if len(block_durations) > 8 else ''}")

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

    target = output_path or OUTPUT
    target.write_text("\n".join(out), encoding="utf-8")
    print(f"Generated {target} from {tp.name} (semantic fallback)")
    print(f"Total blocks: {len(blocks)}")
    return 0
