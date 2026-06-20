from pathlib import Path

import pytest

from glist_pipeline.labels import TaxonomyError, load_taxonomy, validate_final_labels


def test_taxonomy_loads_ids() -> None:
    labels_path = Path(__file__).resolve().parents[2] / "configs" / "labels.toml"
    ids = load_taxonomy(labels_path)
    assert "topic_daily_life" in ids


def test_reject_unknown_final_labels() -> None:
    labels_path = Path(__file__).resolve().parents[2] / "configs" / "labels.toml"
    ids = load_taxonomy(labels_path)
    with pytest.raises(TaxonomyError):
        validate_final_labels(["bad_id"], ids)
