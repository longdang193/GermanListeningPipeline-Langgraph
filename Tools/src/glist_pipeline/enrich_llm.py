from __future__ import annotations

import json
import re
from pathlib import Path
from .blocks import Block
from .glossary_policy import (
    ContentPolicy,
    extract_note_keywords,
    GlossaryPolicy,
    keywords_have_conservative_glosses,
    load_content_policy,
    sanitize_keywords,
    sanitize_short_fragment_translation,
    translation_is_conservative,
)
from .markdown import parse_markdown, render_document

TODO_PATTERNS = (
    "TODO: add English translation.",
    "TODO_TERM_",
    "TODO_GRAMMAR_",
)
MAX_ENRICH_ATTEMPTS = 3
CONTENT_POLICY = load_content_policy()

SYSTEM_PROMPT = (
    "You are preparing high-quality German listening-study material for B1 learners. "
    "Write natural, learner-friendly English. Do not translate word-for-word when the result sounds odd. "
    "Preserve tone, idioms, humor, and implied meaning. "
    "For keywords, prefer useful vocabulary or set phrases that appear in the block. "
    "For grammar notes, explain one concrete grammar or usage pattern from the block in clear teaching language. "
    "Return only valid JSON."
)


def _extract_german_sentences_from_en1(en_1: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\s*<br>\s*", en_1.strip()) if p.strip()]
    out: list[str] = []
    for p in parts:
        m = re.match(r"^<b>(.*?)</b>\s*—\s*", p)
        if m:
            out.append(m.group(1).strip())
    return out


def _needs_enrichment(block: Block) -> bool:
    e = block.fields.get("en_1", "")
    n = block.fields.get("note_1", "")
    return any(tok in e for tok in TODO_PATTERNS) or any(tok in n for tok in TODO_PATTERNS)


def _render_en1(german_sentences: list[str], english_sentences: list[str]) -> str:
    lines: list[str] = []
    for de, en in zip(german_sentences, english_sentences):
        lines.append(f"<b>{de}</b> — {en}")
    return "<br>".join(lines)


def _render_note(keywords: list[dict], grammar: list[dict]) -> str:
    kw_lines = ["<b>Key Words and Phrases</b><br>"]
    for item in keywords:
        kw_lines.append(f"• <b>{item['term']}</b> — {item['gloss']}<br>")

    gr_lines = ["<br><b>Grammar to Remember</b><br>"]
    for item in grammar:
        gr_lines.append(f"• <b>{item['point']}</b> — {item['explanation']}<br>")

    return "".join(kw_lines + gr_lines).rstrip("<br>")


def _extract_translation_pairs(en_1: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for part in re.split(r"\s*<br>\s*", en_1.strip()):
        match = re.match(r"^<b>(.*?)</b>\s*—\s*(.*)$", part.strip())
        if match:
            pairs.append((match.group(1).strip(), match.group(2).strip()))
    return pairs


def _apply_content_policy_to_block(block: Block, content_policy: ContentPolicy) -> bool:
    changed = False

    translation_pairs = _extract_translation_pairs(block.fields.get("en_1", ""))
    if translation_pairs:
        german_sentences = [de for de, _ in translation_pairs]
        sanitized_translations = [
            sanitize_short_fragment_translation(de, en, content_policy.translation)
            for de, en in translation_pairs
        ]
        sanitized_en_1 = _render_en1(german_sentences, sanitized_translations)
        if sanitized_en_1 != block.fields.get("en_1", ""):
            block.fields["en_1"] = sanitized_en_1
            changed = True

    note_1 = block.fields.get("note_1", "")
    if note_1:
        keywords = extract_note_keywords(note_1)
        if keywords:
            sanitized_keywords = sanitize_keywords(keywords, content_policy.glossary)
            if sanitized_keywords != keywords:
                grammar_part = note_1.split("<br><b>Grammar to Remember</b><br>", 1)
                if len(grammar_part) == 2:
                    grammar_html = grammar_part[1]
                    block.fields["note_1"] = _render_note(
                        sanitized_keywords,
                        _extract_grammar_items(grammar_html),
                    )
                    changed = True

    return changed


def _extract_grammar_items(grammar_html: str) -> list[dict[str, str]]:
    grammar_items: list[dict[str, str]] = []
    for point, explanation in re.findall(r"• <b>(.*?)</b> — (.*?)(?:<br>|$)", grammar_html):
        grammar_items.append({"point": point.strip(), "explanation": explanation.strip()})
    return grammar_items


def _normalize_for_match(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _build_keyword_fallback(german_sentences: list[str]) -> list[dict[str, str]]:
    from .legacy.generate_listening_4 import LOW_VALUE_TOKENS, STOPWORDS, keyword_gloss, normalize_token

    stats: dict[str, dict[str, int | str]] = {}
    ordered_norms: list[str] = []
    for sentence in german_sentences:
        tokens = re.findall(r"\b[\wÄÖÜäöüß'-]+\b", sentence, flags=re.UNICODE)
        for index, token in enumerate(tokens):
            norm = normalize_token(token)
            if not norm or norm.isdigit():
                continue
            if len(norm) < 4:
                continue
            if norm in STOPWORDS or norm in LOW_VALUE_TOKENS:
                continue
            if norm not in stats:
                stats[norm] = {
                    "display": token,
                    "count": 0,
                    "non_start": 0,
                    "capitalized": 0,
                }
                ordered_norms.append(norm)
            stats[norm]["count"] += 1
            if index > 0:
                stats[norm]["non_start"] += 1
            if token[:1].isupper():
                stats[norm]["capitalized"] += 1

    ranked: list[tuple[int, int, str, str]] = []
    for norm in ordered_norms:
        info = stats[norm]
        score = 0
        if int(info["non_start"]) > 0:
            score += 3
        if int(info["capitalized"]) > 0:
            score += 2
        if int(info["count"]) > 1:
            score += 1
        ranked.append((score, int(info["count"]), norm, str(info["display"])))

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    chosen = [(item[3], item[2]) for item in ranked[:5]]

    def _compact_gloss(norm: str) -> str:
        gloss = keyword_gloss(norm)
        if len(gloss.split()) <= CONTENT_POLICY.glossary.max_gloss_words:
            return gloss
        return "context term"

    return [
        {"term": display, "gloss": _compact_gloss(norm)}
        for display, norm in chosen[:5]
    ]


def _keywords_match_source(keywords: list[dict], german_sentences: list[str]) -> bool:
    source = _normalize_for_match(" ".join(german_sentences))
    if not source:
        return False

    for item in keywords:
        term = str(item.get("term", "")).strip()
        if not term:
            return False
        normalized_term = _normalize_for_match(term)
        if not normalized_term:
            return False
        if normalized_term not in source:
            return False
    return True



def _build_translation_fallback(german_sentences: list[str]) -> list[str]:
    return [f"TODO: add English translation. ({sentence})" for sentence in german_sentences]

def _parse_json_payload(text: str) -> dict:
    text = text.strip()
    if not text:
        raise RuntimeError("LLM returned empty response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    obj = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if obj:
        return json.loads(obj.group(0))

    raise RuntimeError("LLM response did not contain valid JSON payload")


def _extract_responses_text(resp: object) -> str:
    output = getattr(resp, "output", None)
    if output:
        chunks: list[str] = []
        for item in output:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)

    try:
        text = getattr(resp, "output_text", "")
    except TypeError:
        text = ""
    return text or ""


def _call_chat_completions(client: object, model: str, prompt_text: str) -> str:
    resp = client.chat.completions.create(  # type: ignore[attr-defined]
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        response_format={"type": "json_object"},
    )
    return ((resp.choices[0].message.content or "") if resp.choices else "").strip()


def _call_openai(german_sentences: list[str], glossary_policy: GlossaryPolicy) -> dict:
    from openai import OpenAI  # type: ignore[import-not-found]

    client = OpenAI()
    prompt = {
        "task": "Translate and enrich German listening block",
        "requirements": {
            "translation": (
                "Return one natural English translation per German sentence in the same order. "
                "Use idiomatic English. Avoid stiff literal renderings. "
                "If a line is colloquial, abrupt, funny, or fragmentary, keep that effect in English."
            ),
            "keywords": (
                "Return exactly 5 keyword objects: term + gloss. "
                "Prefer high-value vocabulary, fixed expressions, or culturally useful words from the block. "
                "Each keyword term must be copied exactly from the German block text, not invented or normalized. "
                "Each gloss must be one short neutral dictionary-style meaning in plain English, "
                f"max {glossary_policy.max_gloss_words} words. "
                "No slash-separated alternatives, no commas, no parentheses, no usage labels, no dramatic embellishment, "
                "and no added intensifiers like 'damn' or 'bloody'."
            ),
            "grammar": (
                "Return exactly 3 grammar objects: point + explanation. "
                "Each point must be grounded in a real phrase from the block and explained for B1 learners."
            ),
            "format": "Return only valid JSON object. No markdown, no commentary.",
        },
        "quality_examples": {
            "good": [
                {
                    "german": "Aber mir kommt das einfach nicht richtig vor.",
                    "english": "It just doesn't feel right to me.",
                },
                {
                    "german": "Mach mal halblang hier.",
                    "english": "Take it easy.",
                },
            ],
            "avoid": [
                {
                    "german": "Das ist eine wunderbare Laune des Wetters.",
                    "bad_english": "That is a wonderful mood of the weather.",
                    "better_english": "That's just one of the weather's little moods.",
                }
            ],
        },
        "german_sentences": german_sentences,
        "output_json_schema": {
            "translations": ["string"],
            "keywords": [{"term": "string", "gloss": "string"}],
            "grammar": [{"point": "string", "explanation": "string"}],
        },
    }
    prompt_text = json.dumps(prompt, ensure_ascii=False)

    model = __import__("os").environ.get("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=[{"role": "user", "content": prompt_text}],
    )

    text = _extract_responses_text(resp)
    if not text:
        text = _call_chat_completions(client, model, prompt_text)
    return _parse_json_payload(text)


def _fetch_valid_payload(german_sentences: list[str], content_policy: ContentPolicy) -> dict:
    last_error: RuntimeError | None = None
    for attempt in range(1, MAX_ENRICH_ATTEMPTS + 1):
        try:
            payload = _call_openai(german_sentences, content_policy.glossary)
        except Exception as exc:
            last_error = RuntimeError(
                "LLM output could not be parsed "
                f"(attempt {attempt}/{MAX_ENRICH_ATTEMPTS}: {exc})"
            )
            continue

        raw_translations = payload.get("translations", [])
        translations = [
            sanitize_short_fragment_translation(de, en, content_policy.translation)
            for de, en in zip(german_sentences, raw_translations)
        ]
        payload["translations"] = translations
        keywords = sanitize_keywords(payload.get("keywords", []), content_policy.glossary)
        payload["keywords"] = keywords
        grammar = payload.get("grammar", [])
        keywords_ok = _keywords_match_source(keywords, german_sentences)
        glosses_ok = keywords_have_conservative_glosses(keywords, content_policy.glossary)
        translations_ok = (
            len(raw_translations) == len(german_sentences)
            and all(
                translation_is_conservative(de, en, content_policy.translation)
                for de, en in zip(german_sentences, translations)
            )
        )

        if (
            len(translations) == len(german_sentences)
            and len(keywords) == 5
            and len(grammar) == 3
            and keywords_ok
            and glosses_ok
            and translations_ok
        ):
            return payload

        if (
            len(translations) == len(german_sentences)
            and len(grammar) == 3
            and translations_ok
            and not keywords_ok
        ):
            fallback_keywords = sanitize_keywords(
                _build_keyword_fallback(german_sentences),
                content_policy.glossary,
            )
            if (
                len(fallback_keywords) == 5
                and _keywords_match_source(fallback_keywords, german_sentences)
                and keywords_have_conservative_glosses(
                    fallback_keywords,
                    content_policy.glossary,
                )
            ):
                payload["keywords"] = fallback_keywords
                return payload

        if (
            len(keywords) == 5
            and len(grammar) == 3
            and keywords_ok
            and glosses_ok
            and not translations_ok
        ):
            fallback_translations = [
                sanitize_short_fragment_translation(de, en, content_policy.translation)
                for de, en in zip(german_sentences, _build_translation_fallback(german_sentences))
            ]
            if all(
                translation_is_conservative(de, en, content_policy.translation)
                for de, en in zip(german_sentences, fallback_translations)
            ):
                payload["translations"] = fallback_translations
                return payload

        last_error = RuntimeError(
            "LLM output shape mismatch "
            f"(attempt {attempt}/{MAX_ENRICH_ATTEMPTS}, "
            f"translations={len(translations)}/{len(german_sentences)}, "
            f"keywords={len(keywords)}/5, grammar={len(grammar)}/3, "
            f"keywords_match_source={keywords_ok}, glosses_conservative={glosses_ok}, "
            f"translations_conservative={translations_ok})"
        )

    raise last_error or RuntimeError("LLM enrichment failed unexpectedly")


def enrich_file_in_place(md_path: Path) -> int:
    doc = parse_markdown(md_path.read_text(encoding="utf-8"))
    changed = False

    for block in doc.blocks:
        changed = _apply_content_policy_to_block(block, CONTENT_POLICY) or changed
        if not _needs_enrichment(block):
            continue

        german = _extract_german_sentences_from_en1(block.fields.get("en_1", ""))
        if not german:
            continue

        payload = _fetch_valid_payload(german, CONTENT_POLICY)
        translations = payload.get("translations", [])
        keywords = payload.get("keywords", [])
        grammar = payload.get("grammar", [])

        block.fields["en_1"] = _render_en1(german, translations)
        block.fields["note_1"] = _render_note(keywords, grammar)
        changed = True

    if changed:
        md_path.write_text(render_document(doc.blocks), encoding="utf-8")
    return 0
