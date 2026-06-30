from __future__ import annotations

import json
import re
from pathlib import Path

from .blocks import Block
from .glossary_policy import (
    ContentPolicy,
    GlossaryPolicy,
    extract_note_keywords,
    keywords_have_conservative_glosses,
    load_content_policy,
    sanitize_keywords,
    sanitize_short_fragment_translation,
    translation_is_conservative,
)
from .llm_provider import get_openai_model_name, supports_responses_api
from .markdown import parse_markdown, render_document

TODO_PATTERNS = (
    "TODO: add English translation.",
    "TODO_TERM_",
    "TODO_GRAMMAR_",
)
MAX_ENRICH_ATTEMPTS = 3
KEYWORD_REPAIR_CANDIDATE_LIMIT = 12
CONTENT_POLICY = load_content_policy()

SYSTEM_PROMPT = (
    "You are preparing high-quality German listening-study material for B1 learners. "
    "Write natural, learner-friendly English. Do not translate word-for-word when the result sounds odd. "
    "Preserve tone, idioms, humor, and implied meaning. "
    "For keywords, prefer useful vocabulary or set phrases that appear in the block. "
    "For grammar notes, explain one concrete grammar or usage pattern from the block in clear teaching language. "
    "Return only valid JSON."
)

KEYWORD_REPAIR_SYSTEM_PROMPT = (
    "You repair keyword glosses for German listening-study material. "
    "Stay fully source-grounded. Use only candidate terms provided by user. "
    "Write short neutral glossary meanings in plain English. "
    "Return only valid JSON."
)


def _extract_german_sentences_from_en1(en_1: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\s*<br>\s*", en_1.strip()) if part.strip()]
    out: list[str] = []
    for part in parts:
        match = re.match(r"^<b>(.*?)</b>\s*—\s*", part)
        if match:
            out.append(match.group(1).strip())
    return out


def _needs_enrichment(block: Block) -> bool:
    en_1 = block.fields.get("en_1", "")
    note_1 = block.fields.get("note_1", "")
    if any(token in en_1 for token in TODO_PATTERNS) or any(token in note_1 for token in TODO_PATTERNS):
        return True

    translation_pairs = _extract_translation_pairs(en_1)
    if any(
        not translation_is_conservative(german_sentence, english_sentence, CONTENT_POLICY.translation)
        for german_sentence, english_sentence in translation_pairs
    ):
        return True

    keywords = extract_note_keywords(note_1)
    if keywords and not keywords_have_conservative_glosses(keywords, CONTENT_POLICY.glossary):
        return True

    return False


def _render_en1(german_sentences: list[str], english_sentences: list[str]) -> str:
    lines: list[str] = []
    for german_sentence, english_sentence in zip(german_sentences, english_sentences):
        lines.append(f"<b>{german_sentence}</b> — {english_sentence}")
    return "<br>".join(lines)


def _render_note(keywords: list[dict], grammar: list[dict]) -> str:
    keyword_lines = ["<b>Key Words and Phrases</b><br>"]
    for item in keywords:
        keyword_lines.append(f"• <b>{item['term']}</b> — {item['gloss']}<br>")

    grammar_lines = ["<br><b>Grammar to Remember</b><br>"]
    for item in grammar:
        grammar_lines.append(f"• <b>{item['point']}</b> — {item['explanation']}<br>")

    return "".join(keyword_lines + grammar_lines).rstrip("<br>")


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
        german_sentences = [german_sentence for german_sentence, _ in translation_pairs]
        sanitized_translations = [
            sanitize_short_fragment_translation(german_sentence, english_sentence, content_policy.translation)
            for german_sentence, english_sentence in translation_pairs
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
    normalized = text.casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def _rank_keyword_candidates(german_sentences: list[str]) -> list[tuple[str, str]]:
    from .legacy.generate_listening_4 import (
        GLOSS_MAP,
        LOW_VALUE_TOKENS,
        STOPWORDS,
        normalize_token,
    )

    stats: dict[str, dict[str, int | str]] = {}
    ordered_norms: list[str] = []
    for sentence in german_sentences:
        tokens = re.findall(r"\b[\wÄÖÜäöüß'-]+\b", sentence, flags=re.UNICODE)
        for index, token in enumerate(tokens):
            normalized = normalize_token(token)
            if not normalized or normalized.isdigit() or len(normalized) < 4:
                continue
            if normalized in STOPWORDS or normalized in LOW_VALUE_TOKENS:
                continue
            if normalized not in stats:
                stats[normalized] = {
                    "display": token,
                    "count": 0,
                    "non_start": 0,
                    "capitalized": 0,
                }
                ordered_norms.append(normalized)
            stats[normalized]["count"] += 1
            if index > 0:
                stats[normalized]["non_start"] += 1
            if token[:1].isupper():
                stats[normalized]["capitalized"] += 1

    ranked: list[tuple[int, int, str, str]] = []
    for normalized in ordered_norms:
        info = stats[normalized]
        score = 0
        if int(info["non_start"]) > 0:
            score += 3
        if int(info["capitalized"]) > 0:
            score += 2
        if int(info["count"]) > 1:
            score += 1
        if normalized in GLOSS_MAP:
            score += 2
        ranked.append((score, int(info["count"]), normalized, str(info["display"])))

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [(display, normalized) for _, _, normalized, display in ranked]


def _build_keyword_fallback(
    german_sentences: list[str],
    glossary_policy: GlossaryPolicy | None = None,
) -> list[dict[str, str]]:
    from .legacy.generate_listening_4 import keyword_gloss

    active_policy = glossary_policy or CONTENT_POLICY.glossary
    fallback_keywords: list[dict[str, str]] = []
    for display, normalized in _rank_keyword_candidates(german_sentences):
        gloss = keyword_gloss(normalized)
        sanitized = sanitize_keywords(
            [{"term": display, "gloss": gloss}],
            active_policy,
        )
        if not sanitized:
            continue
        keyword = sanitized[0]
        if not keyword["gloss"]:
            continue
        if not keywords_have_conservative_glosses([keyword], active_policy):
            continue
        fallback_keywords.append(keyword)
        if len(fallback_keywords) == 5:
            break
    return fallback_keywords


def _keywords_match_source(keywords: list[dict], german_sentences: list[str]) -> bool:
    source = _normalize_for_match(" ".join(german_sentences))
    if not source:
        return False

    for item in keywords:
        term = str(item.get("term", "")).strip()
        if not term:
            return False
        normalized_term = _normalize_for_match(term)
        if not normalized_term or normalized_term not in source:
            return False
    return True


def _keywords_are_valid(
    keywords: list[dict[str, str]],
    german_sentences: list[str],
    glossary_policy: GlossaryPolicy,
) -> bool:
    return (
        len(keywords) == 5
        and _keywords_match_source(keywords, german_sentences)
        and keywords_have_conservative_glosses(keywords, glossary_policy)
    )


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


def _call_chat_completions(
    client: object,
    model: str,
    prompt_text: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    resp = client.chat.completions.create(  # type: ignore[attr-defined]
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_text},
        ],
        response_format={"type": "json_object"},
    )
    return ((resp.choices[0].message.content or "") if resp.choices else "").strip()


def _call_openai_json(client: object, model: str, prompt_text: str, system_prompt: str) -> dict:
    last_responses_error: Exception | None = None
    if supports_responses_api():
        try:
            resp = client.responses.create(
                model=model,
                instructions=system_prompt,
                input=[{"role": "user", "content": prompt_text}],
            )
            text = _extract_responses_text(resp)
            if text:
                return _parse_json_payload(text)
        except Exception as exc:
            last_responses_error = exc

    try:
        text = _call_chat_completions(client, model, prompt_text, system_prompt)
        return _parse_json_payload(text)
    except Exception:
        if last_responses_error is not None:
            raise last_responses_error
        raise


def _call_openai(german_sentences: list[str], glossary_policy: GlossaryPolicy) -> dict:
    from openai import OpenAI  # type: ignore[import-not-found]

    prompt = {
        "task": "Translate and enrich German listening block",
        "requirements": {
            "translation": (
                "Return one natural English translation per German sentence in same order. "
                "Use idiomatic English. Avoid stiff literal renderings. "
                "If line is colloquial, abrupt, funny, or fragmentary, keep that effect in English."
            ),
            "keywords": (
                "Return exactly 5 keyword objects: term + gloss. "
                "Prefer high-value vocabulary, fixed expressions, or culturally useful words from block. "
                "Each keyword term must be copied exactly from German block text, not invented or normalized. "
                "Each gloss must be one short neutral dictionary-style meaning in plain English, "
                f"max {glossary_policy.max_gloss_words} words. "
                "No slash-separated alternatives, no commas, no parentheses, no usage labels, no dramatic embellishment, "
                "no added intensifiers like 'damn' or 'bloody', and no generic labels like 'context term' or 'verb form in context'."
            ),
            "grammar": (
                "Return exactly 3 grammar objects: point + explanation. "
                "Each point must be grounded in real phrase from block and explained for B1 learners."
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
    client = OpenAI()
    model = get_openai_model_name()
    return _call_openai_json(client, model, json.dumps(prompt, ensure_ascii=False), SYSTEM_PROMPT)


def _call_keyword_repair_openai(
    german_sentences: list[str],
    candidate_terms: list[str],
    glossary_policy: GlossaryPolicy,
) -> list[dict[str, str]]:
    from openai import OpenAI  # type: ignore[import-not-found]

    prompt = {
        "task": "Repair keyword selection for German listening block",
        "requirements": {
            "keywords": (
                "Return exactly 5 keyword objects: term + gloss. "
                "Each term must be copied exactly from candidate_terms list. "
                "Do not invent, normalize, merge, or paraphrase German terms. "
                "Each gloss must be one short neutral dictionary-style meaning in plain English, "
                f"max {glossary_policy.max_gloss_words} words. "
                "No slash-separated alternatives, no commas, no parentheses, no usage labels, no dramatic embellishment, "
                "no added intensifiers like 'damn' or 'bloody', and no generic labels like 'context term' or 'verb form in context'."
            ),
            "selection": (
                "Prefer terms most useful for comprehension of this block. "
                "Avoid names or trivial words unless they matter for meaning."
            ),
            "format": "Return only valid JSON object with keywords field.",
        },
        "german_sentences": german_sentences,
        "candidate_terms": candidate_terms,
        "output_json_schema": {
            "keywords": [{"term": "string", "gloss": "string"}],
        },
    }
    client = OpenAI()
    model = get_openai_model_name()
    payload = _call_openai_json(
        client,
        model,
        json.dumps(prompt, ensure_ascii=False),
        KEYWORD_REPAIR_SYSTEM_PROMPT,
    )
    repaired = sanitize_keywords(payload.get("keywords", []), glossary_policy)
    return [
        {"term": item["term"], "gloss": item["gloss"]}
        for item in repaired
    ]


def _repair_keywords_with_llm(
    german_sentences: list[str],
    glossary_policy: GlossaryPolicy,
) -> list[dict[str, str]]:
    candidate_terms = [
        display
        for display, _ in _rank_keyword_candidates(german_sentences)[:KEYWORD_REPAIR_CANDIDATE_LIMIT]
    ]
    if len(candidate_terms) < 5:
        return []

    try:
        repaired_keywords = _call_keyword_repair_openai(
            german_sentences,
            candidate_terms,
            glossary_policy,
        )
    except Exception:
        return []

    if _keywords_are_valid(repaired_keywords, german_sentences, glossary_policy):
        return repaired_keywords
    return []


def _resolve_keyword_drift(
    german_sentences: list[str],
    glossary_policy: GlossaryPolicy,
) -> list[dict[str, str]]:
    repaired_keywords = _repair_keywords_with_llm(german_sentences, glossary_policy)
    if repaired_keywords:
        return repaired_keywords

    fallback_keywords = _build_keyword_fallback(german_sentences, glossary_policy)
    if _keywords_are_valid(fallback_keywords, german_sentences, glossary_policy):
        return fallback_keywords
    return []


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
            sanitize_short_fragment_translation(german_sentence, english_sentence, content_policy.translation)
            for german_sentence, english_sentence in zip(german_sentences, raw_translations)
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
                translation_is_conservative(german_sentence, english_sentence, content_policy.translation)
                for german_sentence, english_sentence in zip(german_sentences, translations)
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
            and (not keywords_ok or not glosses_ok)
        ):
            repaired_keywords = _resolve_keyword_drift(german_sentences, content_policy.glossary)
            if repaired_keywords:
                payload["keywords"] = repaired_keywords
                return payload

        if (
            len(keywords) == 5
            and len(grammar) == 3
            and keywords_ok
            and glosses_ok
            and not translations_ok
        ):
            fallback_translations = [
                sanitize_short_fragment_translation(german_sentence, english_sentence, content_policy.translation)
                for german_sentence, english_sentence in zip(
                    german_sentences,
                    _build_translation_fallback(german_sentences),
                )
            ]
            if all(
                translation_is_conservative(german_sentence, english_sentence, content_policy.translation)
                for german_sentence, english_sentence in zip(german_sentences, fallback_translations)
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

        german_sentences = _extract_german_sentences_from_en1(block.fields.get("en_1", ""))
        if not german_sentences:
            continue

        payload = _fetch_valid_payload(german_sentences, CONTENT_POLICY)
        translations = payload.get("translations", [])
        keywords = payload.get("keywords", [])
        grammar = payload.get("grammar", [])

        block.fields["en_1"] = _render_en1(german_sentences, translations)
        block.fields["note_1"] = _render_note(keywords, grammar)
        changed = True

    if changed:
        md_path.write_text(render_document(doc.blocks), encoding="utf-8")
    return 0
