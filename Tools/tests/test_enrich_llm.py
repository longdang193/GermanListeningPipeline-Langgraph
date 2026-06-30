from pathlib import Path

import glist_pipeline.enrich_llm as enrich_llm
from glist_pipeline.enrich_llm import _fetch_valid_payload, _keywords_match_source
from glist_pipeline.glossary_policy import (
    extract_note_keywords,
    gloss_is_conservative,
    keywords_have_conservative_glosses,
    load_content_policy,
    load_glossary_policy,
    sanitize_gloss,
    sanitize_short_fragment_translation,
    translation_is_conservative,
)

GLOSSARY_POLICY = load_glossary_policy()
CONTENT_POLICY = load_content_policy()


def test_keywords_match_source_requires_exact_source_term() -> None:
    german_sentences = [
        "Das wirklich Verrueckte daran ist, dass es damals schon Kakerlaken gab.",
        "Mistvieh.",
    ]
    keywords = [{"term": "Mistvieh", "gloss": "vermin"}]
    assert _keywords_match_source(keywords, german_sentences) is True


def test_keywords_reject_embellished_glosses() -> None:
    assert gloss_is_conservative(
        "damn pest / bloody vermin (colloquial insult)",
        GLOSSARY_POLICY,
    ) is False


def test_keywords_accept_short_neutral_glosses() -> None:
    keywords = [{"term": "Mistvieh", "gloss": "vermin"}]
    assert keywords_have_conservative_glosses(keywords, GLOSSARY_POLICY) is True


def test_keywords_reject_non_neutral_gloss_bundle() -> None:
    keywords = [{"term": "Mistvieh", "gloss": "damn pest / bloody vermin"}]
    assert keywords_have_conservative_glosses(keywords, GLOSSARY_POLICY) is False


def test_keywords_reject_intensifier_only_glosses() -> None:
    keywords = [{"term": "Mistvieh", "gloss": "damn pest"}]
    assert keywords_have_conservative_glosses(keywords, GLOSSARY_POLICY) is False


def test_keywords_reject_intensifier_variants() -> None:
    keywords = [{"term": "Mistvieh", "gloss": "damned pest"}]
    assert keywords_have_conservative_glosses(keywords, GLOSSARY_POLICY) is False


def test_sanitize_gloss_removes_embellishment() -> None:
    assert sanitize_gloss(
        "damn pest / bloody vermin (colloquial insult)",
        GLOSSARY_POLICY,
    ) == "pest"


def test_extract_note_keywords_reads_note_contract() -> None:
    note = (
        "<b>Key Words and Phrases</b><br>"
        "• <b>Mistvieh</b> — pest<br>"
        "• <b>Kakerlaken</b> — cockroaches<br>"
        "<br><b>Grammar to Remember</b><br>"
        "• <b>x</b> — y"
    )
    assert extract_note_keywords(note) == [
        {"term": "Mistvieh", "gloss": "pest"},
        {"term": "Kakerlaken", "gloss": "cockroaches"},
    ]


def test_short_fragment_translation_is_neutralized_by_shared_policy() -> None:
    assert (
        sanitize_short_fragment_translation(
            "Mistvieh.",
            "Damn critter.",
            CONTENT_POLICY.translation,
        )
        == "Critter."
    )


def test_short_fragment_translation_policy_rejects_intensified_translation() -> None:
    assert (
        translation_is_conservative(
            "Mistvieh.",
            "Damn critter.",
            CONTENT_POLICY.translation,
        )
        is False
    )


def test_fetch_valid_payload_retries_after_parse_failure(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_call(_german_sentences: list[str], _glossary_policy: object) -> dict:
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("bad json")
        return {
            "translations": ["vermin"],
            "keywords": [
                {"term": "Mistvieh", "gloss": "vermin"},
                {"term": "Mistvieh", "gloss": "pest"},
                {"term": "Mistvieh", "gloss": "creep"},
                {"term": "Mistvieh", "gloss": "brute"},
                {"term": "Mistvieh", "gloss": "nuisance"},
            ],
            "grammar": [
                {"point": "x", "explanation": "x"},
                {"point": "y", "explanation": "y"},
                {"point": "z", "explanation": "z"},
            ],
        }

    monkeypatch.setattr(enrich_llm, "_call_openai", fake_call)
    payload = _fetch_valid_payload(["Mistvieh"], CONTENT_POLICY)
    assert payload["translations"] == ["Vermin"]
    assert calls["count"] == 2


def test_fetch_valid_payload_repairs_keyword_drift_with_source_repair_lane(monkeypatch) -> None:
    def fake_call(_german_sentences: list[str], _glossary_policy: object) -> dict:
        return {
            "translations": ["We were in good spirits."],
            "keywords": [
                {"term": "gute Dinge", "gloss": "good spirits"},
                {"term": "volle Kraft", "gloss": "full blast"},
                {"term": "Schule", "gloss": "school"},
                {"term": "Maltesisch", "gloss": "Maltese"},
                {"term": "Kinder", "gloss": "children"},
            ],
            "grammar": [
                {"point": "x", "explanation": "x"},
                {"point": "y", "explanation": "y"},
                {"point": "z", "explanation": "z"},
            ],
        }

    monkeypatch.setattr(enrich_llm, "_call_openai", fake_call)
    monkeypatch.setattr(
        enrich_llm,
        "_call_keyword_repair_openai",
        lambda german_sentences, candidate_terms, glossary_policy: [
            {"term": "Grundschule", "gloss": "primary school"},
            {"term": "Maltesisch", "gloss": "Maltese"},
            {"term": "Stufe", "gloss": "level"},
            {"term": "Dinge", "gloss": "spirits"},
            {"term": "höchster", "gloss": "highest"},
        ],
    )
    payload = _fetch_valid_payload(
        ["Ich war ganz guter Dinge und die Grundschule hatte Maltesisch auf höchster Stufe."],
        CONTENT_POLICY,
    )
    assert len(payload["keywords"]) == 5
    assert _keywords_match_source(
        payload["keywords"],
        ["Ich war ganz guter Dinge und die Grundschule hatte Maltesisch auf höchster Stufe."],
    ) is True
    assert keywords_have_conservative_glosses(payload["keywords"], GLOSSARY_POLICY) is True


def test_run_shared_postprocess_prints_progress(monkeypatch, tmp_path, capsys) -> None:
    from glist_pipeline import cli

    md_path = tmp_path / "Listening-generated.md"
    md_path.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(cli, "enrich_file_in_place", lambda _path: 0)
    monkeypatch.setattr(cli, "BANNED", [])

    assert cli._run_shared_postprocess(md_path) == 0
    out = capsys.readouterr().out
    assert "Enrichment started..." in out
    assert "LLM translations and notes may take a while." in out
    assert "Postprocess: enriching Listening-generated.md..." in out
    assert "Enrichment complete. Running placeholder check..." in out
