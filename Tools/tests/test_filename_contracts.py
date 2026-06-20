import re

from glist_pipeline.splitter import heading_to_filename


def test_classic_filename_contract() -> None:
    name = heading_to_filename(0, "Teil 1 — Aufgabe 41", mode="classic")
    assert re.match(r"^01_Teil1_Aufgabe41$", name)


def test_classic_qanda_contract() -> None:
    name = heading_to_filename(5, "Teil 2 — Q&A 1", mode="classic")
    assert re.match(r"^06_Teil2_QandA_1$", name)


def test_marker_filename_contract() -> None:
    name = heading_to_filename(2, "Teil 1.3", mode="marker")
    assert re.match(r"^03_Teil1.3$", name)
