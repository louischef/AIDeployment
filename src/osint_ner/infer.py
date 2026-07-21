"""Step 4 -- run the fine-tuned model over the corpus and write entities.jsonl.

Each output line is one `schemas.EntityDoc`: the article plus its extracted
entities, both as a detailed span list and grouped by label (weapons /
mil_units / mil_orgs) -- the grouped form is what es_ingest.py indexes.
"""

from __future__ import annotations

import logging
from pathlib import Path

import spacy
from tqdm import tqdm

from osint_ner.extract import iter_corpus
from osint_ner.schemas import EntityDoc, EntitySpan

logger = logging.getLogger(__name__)

_LABEL_TO_FIELD = {"WEAPON": "weapons", "MIL_UNIT": "mil_units", "MIL_ORG": "mil_orgs"}


def infer(corpus_path: Path, model_dir: Path, output_path: Path, batch_size: int = 32) -> int:
    nlp = spacy.load(model_dir)
    articles = list(iter_corpus(corpus_path))
    texts = [article.text for article in articles]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(output_path, "w", encoding="utf-8") as out:
        docs = nlp.pipe(texts, batch_size=batch_size)
        pairs = zip(articles, docs, strict=True)
        for article, doc in tqdm(pairs, total=len(texts), desc="infer"):
            entities = [
                EntitySpan(start=e.start_char, end=e.end_char, label=e.label_, text=e.text)
                for e in doc.ents
            ]
            grouped: dict[str, list[str]] = {"weapons": [], "mil_units": [], "mil_orgs": []}
            for entity in entities:
                field = _LABEL_TO_FIELD.get(entity.label)
                if field:
                    grouped[field].append(entity.text)

            entity_doc = EntityDoc(
                id=article.id,
                url=article.url,
                title=article.title,
                date=article.date,
                text=article.text,
                entities=entities,
                **grouped,
            )
            out.write(entity_doc.model_dump_json())
            out.write("\n")
            written += 1

    logger.info("Inferred entities for %d articles -> %s", written, output_path)
    return written
