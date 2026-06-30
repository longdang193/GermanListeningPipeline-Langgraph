import sys
import types

import glist_pipeline.enrich_llm as enrich_llm
from glist_pipeline.enrich_llm import (
    _build_keyword_fallback,
    _call_openai,
    _fetch_valid_payload,
    _repair_keywords_with_llm,
    _needs_enrichment,
)
from glist_pipeline.glossary_policy import (
    keywords_have_conservative_glosses,
    load_content_policy,
)


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

    monkeypatch.setattr(enrich_llm, "_call_openai", lambda german_sentences, glossary_policy: payload)

    content_policy = load_content_policy()
    german_sentences = ["Hallo Welt guten Tag heute", "Noch ein Satz heute"]
    result = _fetch_valid_payload(german_sentences, content_policy)

    assert result["translations"] == [
        "TODO: add English translation. (Hallo Welt guten Tag heute)",
        "TODO: add English translation. (Noch ein Satz heute)",
    ]


def test_call_openai_falls_back_to_chat_completions_when_responses_api_missing(monkeypatch):
    class FakeResponses:
        def create(self, **kwargs):
            raise RuntimeError("Error code: 404")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeChatCompletions:
        def create(self, **kwargs):
            payload = '{"translations": ["Hello there."], "keywords": [{"term": "Hallo", "gloss": "hello"}, {"term": "da", "gloss": "there"}, {"term": "guten", "gloss": "good"}, {"term": "Tag", "gloss": "day"}, {"term": "heute", "gloss": "today"}], "grammar": [{"point": "A", "explanation": "a"}, {"point": "B", "explanation": "b"}, {"point": "C", "explanation": "c"}]}'
            return types.SimpleNamespace(choices=[FakeChoice(payload)])

    class FakeOpenAI:
        def __init__(self):
            self.responses = FakeResponses()
            self.chat = types.SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    content_policy = load_content_policy()
    payload = _call_openai(["Hallo da guten Tag heute"], content_policy.glossary)

    assert payload["translations"] == ["Hello there."]
    assert len(payload["keywords"]) == 5
    assert len(payload["grammar"]) == 3


def test_get_openai_model_name_normalizes_deepseek_alias(monkeypatch):
    from glist_pipeline.llm_provider import get_openai_model_name

    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("OPENAI_MODEL", "ds/deepseek-v4-flash")

    assert get_openai_model_name() == "deepseek-v4-flash"


def test_call_openai_uses_normalized_deepseek_model_for_chat_fallback(monkeypatch):
    seen = {}

    class FakeResponses:
        def create(self, **kwargs):
            raise AssertionError("responses api should be skipped for deepseek")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeChatCompletions:
        def create(self, **kwargs):
            seen["model"] = kwargs.get("model")
            payload = '{"translations": ["Hello there."], "keywords": [{"term": "Hallo", "gloss": "hello"}, {"term": "da", "gloss": "there"}, {"term": "guten", "gloss": "good"}, {"term": "Tag", "gloss": "day"}, {"term": "heute", "gloss": "today"}], "grammar": [{"point": "A", "explanation": "a"}, {"point": "B", "explanation": "b"}, {"point": "C", "explanation": "c"}]}'
            return types.SimpleNamespace(choices=[FakeChoice(payload)])

    class FakeOpenAI:
        def __init__(self):
            self.responses = FakeResponses()
            self.chat = types.SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("OPENAI_MODEL", "ds/deepseek-v4-flash")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    content_policy = load_content_policy()
    payload = _call_openai(["Hallo da guten Tag heute"], content_policy.glossary)

    assert seen["model"] == "deepseek-v4-flash"
    assert payload["translations"] == ["Hello there."]


def test_keyword_fallback_filters_generic_gloss_family():
    content_policy = load_content_policy()
    keywords = _build_keyword_fallback(
        [
            "Ein paar hundert Millionen Jahre lang waren sie die größten.",
            "Das wirklich Verrückte daran ist, dass es damals schon Kakerlaken gab.",
            "Heute habe ich sogar ein echt wichtiges Projekt vergessen: Meine Präsentation für die internationale Schaubühne.",
        ],
        content_policy.glossary,
    )

    assert all(keyword["gloss"] for keyword in keywords)
    assert keywords_have_conservative_glosses(keywords, content_policy.glossary)
    assert all(keyword["gloss"] != "context term" for keyword in keywords)
    assert all(keyword["gloss"] != "verb form in context" for keyword in keywords)


def test_keyword_repair_uses_source_grounded_candidates(monkeypatch):
    content_policy = load_content_policy()

    monkeypatch.setattr(
        enrich_llm,
        "_call_keyword_repair_openai",
        lambda german_sentences, candidate_terms, glossary_policy: [
            {"term": "Kakerlaken", "gloss": "cockroaches"},
            {"term": "Jahre", "gloss": "years"},
            {"term": "Projekt", "gloss": "project"},
            {"term": "Präsentation", "gloss": "presentation"},
            {"term": "Schaubühne", "gloss": "stage show"},
        ],
    )

    keywords = _repair_keywords_with_llm(
        [
            "Ein paar hundert Millionen Jahre lang waren sie die größten.",
            "Das wirklich Verrückte daran ist, dass es damals schon Kakerlaken gab.",
            "Heute habe ich sogar ein echt wichtiges Projekt vergessen: Meine Präsentation für die internationale Schaubühne.",
        ],
        content_policy.glossary,
    )

    assert len(keywords) == 5
    assert keywords_have_conservative_glosses(keywords, content_policy.glossary)


def test_fetch_valid_payload_repairs_generic_keyword_glosses(monkeypatch):
    content_policy = load_content_policy()

    monkeypatch.setattr(
        enrich_llm,
        "_call_openai",
        lambda german_sentences, glossary_policy: {
            "translations": ["I forgot an important project today."],
            "keywords": [
                {"term": "Projekt", "gloss": "context term"},
                {"term": "Präsentation", "gloss": "verb form in context"},
                {"term": "Schaubühne", "gloss": "abstract noun"},
                {"term": "heute", "gloss": "today"},
                {"term": "wichtiges", "gloss": "important"},
            ],
            "grammar": [
                {"point": "x", "explanation": "x"},
                {"point": "y", "explanation": "y"},
                {"point": "z", "explanation": "z"},
            ],
        },
    )
    monkeypatch.setattr(
        enrich_llm,
        "_resolve_keyword_drift",
        lambda german_sentences, glossary_policy: [
            {"term": "Projekt", "gloss": "project"},
            {"term": "Präsentation", "gloss": "presentation"},
            {"term": "Schaubühne", "gloss": "stage show"},
            {"term": "heute", "gloss": "today"},
            {"term": "wichtiges", "gloss": "important"},
        ],
    )

    payload = _fetch_valid_payload(
        ["Heute habe ich sogar ein echt wichtiges Projekt vergessen: Meine Präsentation für die internationale Schaubühne."],
        content_policy,
    )

    assert [item["gloss"] for item in payload["keywords"]] == [
        "project",
        "presentation",
        "stage show",
        "today",
        "important",
    ]


def test_needs_enrichment_detects_generic_keyword_glosses():
    from glist_pipeline.blocks import Block

    block = Block(
        heading="Abschnitt 1",
        fields={
            "en_1": "<b>Film.</b> — Film.",
            "note_1": (
                "<b>Key Words and Phrases</b><br>"
                "• <b>Film</b> — context term<br>"
                "<br><b>Grammar to Remember</b><br>"
                "• <b>x</b> — y"
            ),
        },
    )

    assert _needs_enrichment(block) is True
