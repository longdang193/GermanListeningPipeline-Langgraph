from glist_pipeline.enrich_llm import _fetch_valid_payload
from glist_pipeline.glossary_policy import load_content_policy


def test_fetch_valid_payload_uses_translation_fallback_when_translation_count_mismatches(monkeypatch):
    payload = {
        "translations": ["first only"],
        "keywords": [
            {"term": "Hallo", "gloss": "hello"},
            {"term": "Welt", "gloss": "world"},
            {"term": "guten", "gloss": "good"},
            {"term": "Tag", "gloss": "day"},
            {"term": "heute", "gloss": "today"},
        ],
        "grammar": [
            {"topic": "A", "explanation": "a"},
            {"topic": "B", "explanation": "b"},
            {"topic": "C", "explanation": "c"},
        ],
    }

    monkeypatch.setattr('glist_pipeline.enrich_llm._call_openai', lambda german_sentences, glossary_policy: payload)

    content_policy = load_content_policy()
    german_sentences = ["Hallo Welt guten Tag heute", "Noch ein Satz heute"]
    result = _fetch_valid_payload(german_sentences, content_policy)

    assert result["translations"] == [
        "TODO: add English translation. (Hallo Welt guten Tag heute)",
        "TODO: add English translation. (Noch ein Satz heute)",
    ]
