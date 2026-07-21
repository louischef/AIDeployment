"""Step 3a -- split annotations.json into train/dev and convert to .spacy DocBins.

Uses `spacy.blank("en")` rather than en_core_web_sm: only the tokenizer is
needed to resolve character offsets to token-aligned spans, and English's
tokenizer rules are identical between the blank pipeline and en_core_web_sm,
so this avoids requiring the full model just to build training data.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

import spacy
from spacy.language import Language
from spacy.tokens import DocBin
from spacy.util import filter_spans

from osint_ner.config import TRAIN_DEV_SPLIT_SEED, TRAIN_FRACTION

logger = logging.getLogger(__name__)

TrainingPair = tuple[str, dict]


def load_training_pairs(annotations_path: Path) -> list[TrainingPair]:
    """Load annotations.json and return the exact spaCy tuple format (slide 23)."""
    records = json.loads(annotations_path.read_text(encoding="utf-8"))
    return [
        (record["text"], {"entities": [tuple(e) for e in record["entities"]]}) for record in records
    ]


def split_train_dev(
    pairs: list[TrainingPair],
    train_fraction: float = TRAIN_FRACTION,
    seed: int = TRAIN_DEV_SPLIT_SEED,
) -> tuple[list[TrainingPair], list[TrainingPair]]:
    """Seeded shuffle + split so the split is reproducible across runs."""
    shuffled = list(pairs)
    random.Random(seed).shuffle(shuffled)
    split_at = round(len(shuffled) * train_fraction)
    return shuffled[:split_at], shuffled[split_at:]


def to_docbin(pairs: list[TrainingPair], nlp: Language) -> DocBin:
    doc_bin = DocBin()
    dropped = 0
    for text, annot in pairs:
        doc = nlp.make_doc(text)
        spans = []
        for start, end, label in annot["entities"]:
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is None:
                dropped += 1
                logger.warning(
                    "Dropping misaligned span (%d, %d, %s) in text starting %r",
                    start,
                    end,
                    label,
                    text[:60],
                )
                continue
            spans.append(span)
        doc.ents = filter_spans(spans)
        doc_bin.add(doc)
    if dropped:
        logger.warning("Dropped %d misaligned span(s) while building DocBin", dropped)
    return doc_bin


def convert(
    annotations_path: Path,
    train_out: Path,
    dev_out: Path,
    train_fraction: float = TRAIN_FRACTION,
    seed: int = TRAIN_DEV_SPLIT_SEED,
) -> tuple[int, int]:
    """Full step 3a: load annotations, split, convert, write train.spacy + dev.spacy."""
    pairs = load_training_pairs(annotations_path)
    if not pairs:
        raise ValueError(f"{annotations_path} contains no annotated records")

    train_pairs, dev_pairs = split_train_dev(pairs, train_fraction, seed)

    nlp = spacy.blank("en")
    train_out.parent.mkdir(parents=True, exist_ok=True)
    dev_out.parent.mkdir(parents=True, exist_ok=True)
    to_docbin(train_pairs, nlp).to_disk(train_out)
    to_docbin(dev_pairs, nlp).to_disk(dev_out)

    logger.info(
        "Split %d records -> train=%d dev=%d -> %s / %s",
        len(pairs),
        len(train_pairs),
        len(dev_pairs),
        train_out,
        dev_out,
    )
    return len(train_pairs), len(dev_pairs)
