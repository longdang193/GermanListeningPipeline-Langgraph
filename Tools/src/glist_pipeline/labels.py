import tomllib
from pathlib import Path


class TaxonomyError(ValueError):
    """Raised when label taxonomy is invalid."""


def load_taxonomy(path: Path) -> set[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    labels = data.get("labels", [])
    ids = {item.get("id", "").strip() for item in labels if isinstance(item, dict)}
    ids.discard("")
    if not ids:
        raise TaxonomyError("No label IDs found in taxonomy file")
    return ids


def validate_final_labels(final_labels: list[str], allowed_ids: set[str]) -> None:
    invalid = [x for x in final_labels if x not in allowed_ids]
    if invalid:
        raise TaxonomyError(f"Unknown label IDs: {invalid}")
