from __future__ import annotations

from osint_ner.es_ingest import _normalise_date, _to_action
from osint_ner.schemas import EntityDoc


def test_normalise_date_handles_iso_and_common_formats():
    assert _normalise_date("2024-02-11") == "2024-02-11"
    assert _normalise_date("11.02.2024") == "2024-02-11"
    assert _normalise_date(None) is None
    assert _normalise_date("not a date") is None


def test_to_action_groups_entities_and_tags_source():
    doc = EntityDoc(
        id="a1",
        url="http://x",
        title="T",
        date="2024-02-11",
        text="t",
        entities=[],
        weapons=["Kalibr"],
        mil_units=["brigade"],
        mil_orgs=[],
    )

    action = _to_action(doc, index="my-index")

    assert action["_index"] == "my-index"
    assert action["_id"] == "a1"
    assert action["_source"]["weapons"] == ["Kalibr"]
    assert action["_source"]["date"] == "2024-02-11"
    assert action["_source"]["date_raw"] == "2024-02-11"
    assert action["_source"]["source_name"] == "TASS"
