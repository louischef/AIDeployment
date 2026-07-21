"""Lightweight analysis over entities.jsonl: top-N entities per label and a
mentions-over-time count. Feeds the "analyse des metriques" required in the
report (slide 21). This is a fast sanity check runnable without a cluster --
it does not replace the Kibana dashboards built in step 5.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from osint_ner.schemas import EntityDoc

_FIELD_TO_LABEL = (("weapons", "WEAPON"), ("mil_units", "MIL_UNIT"), ("mil_orgs", "MIL_ORG"))


def load_entity_docs(path: Path) -> list[EntityDoc]:
    docs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(EntityDoc.model_validate_json(line))
    return docs


def top_entities(docs: list[EntityDoc], field: str, top_n: int = 10) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for doc in docs:
        counter.update(getattr(doc, field))
    return counter.most_common(top_n)


def mentions_by_date(docs: list[EntityDoc], field: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for doc in docs:
        if doc.date:
            counts[doc.date] += len(getattr(doc, field))
    return dict(sorted(counts.items()))


def print_report(docs: list[EntityDoc], top_n: int = 10) -> None:
    print(f"{len(docs)} article(s) analysed\n")
    for field, label in _FIELD_TO_LABEL:
        print(f"Top {top_n} {label}:")
        entries = top_entities(docs, field, top_n)
        if not entries:
            print("  (none found)")
        for term, count in entries:
            print(f"  {count:>4}  {term}")
        print()
