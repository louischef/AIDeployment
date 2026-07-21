"""Step 5 -- create the Elasticsearch index (idempotent) and bulk-ingest entities.jsonl.

Requires ES_CLOUD_ID + ES_API_KEY (or ES_URL) in the environment / .env --
see .env.example. Every indexed document carries `source_name`/`source_bias`
so the OSINT provenance caveat from slide 6 ("we never extract the truth,
only what a source claims") stays attached to the data in Kibana, not just
in the report's prose.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from osint_ner.config import ES_API_KEY, ES_CLOUD_ID, ES_URL, SOURCE_BIAS, SOURCE_NAME
from osint_ner.schemas import EntityDoc

logger = logging.getLogger(__name__)

_DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y", "%B %d, %Y", "%d %B %Y")


def _normalise_date(raw: str | None) -> str | None:
    """Best-effort parse of a handful of common date formats to ISO 8601 (date only).

    Returns None (rather than raising) on anything unrecognised -- the raw
    string is always preserved separately in `date_raw` so no information is
    silently lost, but a bad date must not abort the whole ingest run.
    """
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    logger.warning("Could not parse date %r; keeping it in date_raw only", raw)
    return None


def get_client() -> Elasticsearch:
    if ES_CLOUD_ID and ES_API_KEY:
        return Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)
    if ES_URL:
        return Elasticsearch(ES_URL, api_key=ES_API_KEY) if ES_API_KEY else Elasticsearch(ES_URL)
    raise RuntimeError(
        "No Elasticsearch connection configured: set ES_CLOUD_ID + ES_API_KEY, or ES_URL, "
        "in your .env (see .env.example)."
    )


def ensure_index(client: Elasticsearch, index: str, mapping_path: Path) -> bool:
    """Create `index` from mapping_path if it doesn't already exist. Returns True if created."""
    if client.indices.exists(index=index):
        logger.info("Index %s already exists; leaving its mapping untouched", index)
        return False
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    client.indices.create(index=index, **mapping)
    logger.info("Created index %s from %s", index, mapping_path)
    return True


def _to_action(doc: EntityDoc, index: str) -> dict:
    return {
        "_index": index,
        "_id": doc.id,
        "_source": {
            "id": doc.id,
            "url": doc.url,
            "title": doc.title,
            "date": _normalise_date(doc.date),
            "date_raw": doc.date,
            "text": doc.text,
            "weapons": doc.weapons,
            "mil_units": doc.mil_units,
            "mil_orgs": doc.mil_orgs,
            "source_name": SOURCE_NAME,
            "source_bias": SOURCE_BIAS,
        },
    }


def ingest(client: Elasticsearch, index: str, entities_path: Path) -> int:
    """Bulk-index every EntityDoc in entities.jsonl. Returns the number of documents indexed."""
    with open(entities_path, encoding="utf-8") as fh:
        docs = [EntityDoc.model_validate_json(line) for line in fh if line.strip()]

    actions = (_to_action(doc, index) for doc in docs)
    success, errors = bulk(client, actions, raise_on_error=False)
    if errors:
        logger.warning(
            "%d document(s) failed to index (showing up to 3): %s", len(errors), errors[:3]
        )
    logger.info("Indexed %d/%d documents into %s", success, len(docs), index)
    return success
