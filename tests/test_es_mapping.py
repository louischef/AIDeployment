from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = REPO_ROOT / "elastic" / "index_mapping.json"
NDJSON_PATH = REPO_ROOT / "elastic" / "kibana_saved_objects.ndjson"

EXPECTED_FIELDS = {
    "id",
    "url",
    "title",
    "date",
    "date_raw",
    "text",
    "weapons",
    "mil_units",
    "mil_orgs",
    "source_name",
    "source_bias",
}


def test_index_mapping_is_valid_and_covers_expected_fields():
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    properties = mapping["mappings"]["properties"]

    assert EXPECTED_FIELDS <= properties.keys()
    assert properties["date"]["type"] == "date"
    for field in ("weapons", "mil_units", "mil_orgs"):
        assert properties[field]["type"] == "keyword"


def test_kibana_ndjson_is_well_formed():
    lines = [line for line in NDJSON_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, "expected at least one saved object"

    objects = [json.loads(line) for line in lines]
    ids = {obj["id"] for obj in objects}
    assert "tass-war-entities-index-pattern" in ids

    for obj in objects:
        assert {"id", "type", "attributes", "references"} <= obj.keys()
        if obj["type"] == "visualization":
            assert any(ref["id"] == "tass-war-entities-index-pattern" for ref in obj["references"])
            # visState is itself a JSON-encoded string -- make sure it actually parses.
            json.loads(obj["attributes"]["visState"])
