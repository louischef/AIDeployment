"""Human validation of annotations.json (slide 24, step C -- OBLIGATOIRE).

Run interactively: `python -m osint_ner review --sample 20`. For each sampled
article, prints the text with entity spans highlighted and labelled, then
asks the reviewer to accept, reject, or leave a free-text note. Decisions are
appended to review_log.json so the review is auditable.

This is a lightweight substitute for a full annotation UI (Label Studio,
Doccano, Prodigy -- see README for that alternative) that is enough to catch
systematic labelling or boundary errors within the time budget of a TP.
"""

from __future__ import annotations

import json
import random
from pathlib import Path


def render_highlighted(text: str, entities: list[tuple[int, int, str]]) -> str:
    """Render `text` with each span wrapped as `[span|LABEL]` for terminal review."""
    ordered = sorted(entities, key=lambda e: e[0])
    pieces = []
    cursor = 0
    for start, end, label in ordered:
        if start < cursor:
            continue  # defensive: ignore malformed overlapping spans rather than crash
        pieces.append(text[cursor:start])
        pieces.append(f"[{text[start:end]}|{label}]")
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def load_annotations(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sample_records(records: list[dict], sample_size: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    if sample_size >= len(records):
        return list(records)
    return rng.sample(records, sample_size)


def run_review(
    annotations_path: Path,
    review_log_path: Path,
    sample_size: int = 20,
    seed: int = 13,
) -> None:
    """Interactive review loop. Requires a human at the keyboard -- not covered by pytest."""
    records = load_annotations(annotations_path)
    sampled = sample_records(records, sample_size, seed)

    decisions: list[dict] = []
    if review_log_path.exists():
        decisions = json.loads(review_log_path.read_text(encoding="utf-8"))
    reviewed_ids = {d["id"] for d in decisions}

    print(f"Reviewing {len(sampled)} of {len(records)} pre-annotated articles.")
    print("For each: [a]ccept, [r]eject, or type a free-text note, then Enter. Ctrl+C to stop.\n")

    for record in sampled:
        if record["id"] in reviewed_ids:
            continue
        print("-" * 80)
        print(f"id: {record['id']}")
        print(render_highlighted(record["text"], [tuple(e) for e in record["entities"]]))
        try:
            decision = input("\ndecision> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopping review; progress saved.")
            break
        decisions.append({"id": record["id"], "decision": decision or "accept"})
        review_log_path.parent.mkdir(parents=True, exist_ok=True)
        review_log_path.write_text(
            json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    accepted = sum(1 for d in decisions if d["decision"].lower().startswith("a"))
    print(f"\n{accepted}/{len(decisions)} decisions recorded as accepted -> {review_log_path}")
