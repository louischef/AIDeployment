from __future__ import annotations

from osint_ner.analyze import mentions_by_date, top_entities
from osint_ner.schemas import EntityDoc


def _doc(id_: str, date: str, weapons: list[str]) -> EntityDoc:
    return EntityDoc(id=id_, date=date, text="x", entities=[], weapons=weapons)


def test_top_entities_counts_across_documents():
    docs = [
        _doc("1", "2024-01-01", ["Kalibr", "Kalibr"]),
        _doc("2", "2024-01-02", ["Iskander"]),
    ]

    assert top_entities(docs, "weapons", top_n=2) == [("Kalibr", 2), ("Iskander", 1)]


def test_mentions_by_date_sums_per_day_and_sorts_chronologically():
    docs = [
        _doc("1", "2024-01-02", ["Kalibr"]),
        _doc("2", "2024-01-01", ["Iskander", "Kalibr"]),
    ]

    assert mentions_by_date(docs, "weapons") == {"2024-01-01": 2, "2024-01-02": 1}
