from __future__ import annotations

import os


def get_openai_model_name(default: str = "gpt-4o-mini") -> str:
    raw_model = os.environ.get("OPENAI_MODEL", default).strip() or default
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip().casefold()
    if "deepseek.com" in base_url and raw_model.startswith("ds/"):
        return raw_model.split("/", 1)[1]
    return raw_model


def supports_responses_api() -> bool:
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip().casefold()
    return "deepseek.com" not in base_url
