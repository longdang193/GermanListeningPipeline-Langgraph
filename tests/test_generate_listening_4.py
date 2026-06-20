import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "Requirement" / "generate_listening_4.py"
spec = importlib.util.spec_from_file_location("generate_listening_4", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_translation_placeholder_is_honest_todo_marker():
    output = module.build_translation_placeholders([[{"text": "Hallo", "start": 0.0, "end": 0.5}]])
    assert "LLM translation pending" not in output
    assert "TODO" in output
