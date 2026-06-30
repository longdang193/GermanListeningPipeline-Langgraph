from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .runtime_paths import get_config_dir


@dataclass(frozen=True)
class GlossaryPolicy:
    max_gloss_words: int
    forbidden_punctuation: tuple[str, ...]
    forbidden_prefixes: tuple[str, ...]
    banned_exact_glosses: tuple[str, ...]


@dataclass(frozen=True)
class TranslationPolicy:
    neutralize_short_fragments_max_source_words: int
    forbidden_prefixes: tuple[str, ...]


@dataclass(frozen=True)
class ContentPolicy:
    glossary: GlossaryPolicy
    translation: TranslationPolicy


def default_policy_path() -> Path:
    return get_config_dir() / "policy.toml"


def _normalize_gloss_value(gloss: str) -> str:
    return " ".join(gloss.split()).casefold()


def load_content_policy(path: Path | None = None) -> ContentPolicy:
    policy_path = path or default_policy_path()
    data = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    glossary = data.get("glossary", {})
    translation = data.get("translation", {})
    if not isinstance(glossary, dict):
        raise ValueError("Invalid glossary policy configuration")
    if not isinstance(translation, dict):
        raise ValueError("Invalid translation policy configuration")

    max_gloss_words = int(glossary.get("max_gloss_words", 5))
    forbidden_punctuation = tuple(str(x) for x in glossary.get("forbidden_punctuation", []))
    forbidden_prefixes = tuple(str(x).casefold() for x in glossary.get("forbidden_prefixes", []))
    banned_exact_glosses = tuple(
        _normalize_gloss_value(str(x))
        for x in glossary.get("banned_exact_glosses", [])
    )
    neutralize_short_fragments_max_source_words = int(
        translation.get("neutralize_short_fragments_max_source_words", 2)
    )
    if max_gloss_words <= 0:
        raise ValueError("glossary.max_gloss_words must be positive")
    if neutralize_short_fragments_max_source_words <= 0:
        raise ValueError("translation.neutralize_short_fragments_max_source_words must be positive")
    return ContentPolicy(
        glossary=GlossaryPolicy(
            max_gloss_words=max_gloss_words,
            forbidden_punctuation=forbidden_punctuation,
            forbidden_prefixes=forbidden_prefixes,
            banned_exact_glosses=banned_exact_glosses,
        ),
        translation=TranslationPolicy(
            neutralize_short_fragments_max_source_words=neutralize_short_fragments_max_source_words,
            forbidden_prefixes=forbidden_prefixes,
        ),
    )


def load_glossary_policy(path: Path | None = None) -> GlossaryPolicy:
    return load_content_policy(path).glossary


def load_translation_policy(path: Path | None = None) -> TranslationPolicy:
    return load_content_policy(path).translation


def gloss_is_conservative(gloss: str, policy: GlossaryPolicy) -> bool:
    normalized_gloss = " ".join(gloss.split())
    if not normalized_gloss:
        return False
    if any(token in normalized_gloss for token in policy.forbidden_punctuation):
        return False
    if any(
        word.casefold().startswith(policy.forbidden_prefixes)
        for word in normalized_gloss.split()
    ):
        return False
    if _normalize_gloss_value(normalized_gloss) in policy.banned_exact_glosses:
        return False
    if len(normalized_gloss.split()) > policy.max_gloss_words:
        return False
    return True


def sanitize_gloss(gloss: str, policy: GlossaryPolicy) -> str:
    sanitized = gloss.strip()
    for token in policy.forbidden_punctuation:
        if token in sanitized:
            sanitized = sanitized.split(token, 1)[0].strip()

    kept_words = [
        word
        for word in sanitized.split()
        if not word.casefold().startswith(policy.forbidden_prefixes)
    ]
    sanitized = " ".join(kept_words)
    if _normalize_gloss_value(sanitized) in policy.banned_exact_glosses:
        return ""
    if len(sanitized.split()) > policy.max_gloss_words:
        return ""
    return sanitized


def sanitize_keywords(
    keywords: list[dict[str, str | object]],
    policy: GlossaryPolicy,
) -> list[dict[str, str]]:
    sanitized_keywords: list[dict[str, str]] = []
    for item in keywords:
        sanitized_keywords.append(
            {
                "term": str(item.get("term", "")).strip(),
                "gloss": sanitize_gloss(str(item.get("gloss", "")).strip(), policy),
            }
        )
    return sanitized_keywords


def keywords_have_conservative_glosses(
    keywords: list[dict[str, str | object]],
    policy: GlossaryPolicy,
) -> bool:
    for item in keywords:
        gloss = str(item.get("gloss", "")).strip()
        if not gloss_is_conservative(gloss, policy):
            return False
    return True


KEYWORD_LINE_RE = re.compile(r"• <b>(.*?)</b> — (.*?)(?:<br>|$)")


def extract_note_keywords(note_1: str) -> list[dict[str, str]]:
    keyword_section = note_1.split("<br><b>Grammar to Remember</b>", 1)[0]
    keywords: list[dict[str, str]] = []
    for term, gloss in KEYWORD_LINE_RE.findall(keyword_section):
        keywords.append({"term": term.strip(), "gloss": gloss.strip()})
    return keywords


def contains_forbidden_prefix(text: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    words = re.findall(r"\b[\w'-]+\b", text.casefold())
    return any(word.startswith(forbidden_prefixes) for word in words)


def _capitalise_first_alpha(text: str) -> str:
    for idx, char in enumerate(text):
        if char.isalpha():
            return text[:idx] + char.upper() + text[idx + 1 :]
    return text


def sanitize_short_fragment_translation(
    german_sentence: str,
    english_sentence: str,
    policy: TranslationPolicy,
) -> str:
    german_word_count = len(re.findall(r"\b[\w'-]+\b", german_sentence, flags=re.UNICODE))
    if german_word_count > policy.neutralize_short_fragments_max_source_words:
        return english_sentence.strip()

    tokens = english_sentence.strip().split()
    filtered_tokens = [
        token
        for token in tokens
        if not re.sub(r"^[^\w]+|[^\w]+$", "", token).casefold().startswith(policy.forbidden_prefixes)
    ]
    sanitized = " ".join(filtered_tokens).strip()
    sanitized = re.sub(r"\s+([,.;:!?])", r"\1", sanitized)
    return _capitalise_first_alpha(sanitized)


def translation_is_conservative(
    german_sentence: str,
    english_sentence: str,
    policy: TranslationPolicy,
) -> bool:
    german_word_count = len(re.findall(r"\b[\w'-]+\b", german_sentence, flags=re.UNICODE))
    if german_word_count > policy.neutralize_short_fragments_max_source_words:
        return True
    return not contains_forbidden_prefix(english_sentence, policy.forbidden_prefixes)
