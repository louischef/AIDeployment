"""Step 2 -- Annotate: pre-annotate the corpus with our 3-label schema.

No LLM API key is available in this environment. Per an explicit decision,
pre-annotation is done with `en_core_web_sm` instead -- the same base model
that step 3 reuses for transfer learning:

- A rule-based layer (spaCy `PhraseMatcher` over curated gazetteers + a
  `Matcher` regex pattern for numbered formations, e.g. "58th Army") tags
  WEAPON / MIL_UNIT / MIL_ORG spans that the generic model has no notion of.
- `en_core_web_sm`'s own NER pass supplies extra MIL_ORG candidates by
  keeping only its generic ORG entities whose text contains a military cue
  word from mil_orgs.txt (e.g. "Ministry of Defence", "General Staff").
- Rule-based spans always win on overlap; ORG-derived spans only fill gaps.

This keeps the TP's "automatic pre-annotation, then mandatory human review"
workflow (slide 24) intact -- see review.py for the review step -- without
depending on a paid external API.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Iterator
from pathlib import Path

import spacy
from spacy.language import Language
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Span
from spacy.util import filter_spans
from tqdm import tqdm

from osint_ner.config import BASE_MODEL, GAZETTEERS_DIR
from osint_ner.extract import iter_corpus

logger = logging.getLogger(__name__)

# All the matching below only needs tokenization + NER (for the generic-ORG
# fallback) -- not the tagger/parser/lemmatizer. Disabling them roughly
# doubles throughput, which matters once the corpus reaches thousands of
# articles. If a caller injects their own `nlp` (e.g. a full pipeline in
# tests), it is used as-is -- disabling only affects our own default load.
_UNUSED_COMPONENTS = ("tagger", "parser", "lemmatizer", "attribute_ruler")

_ORDINAL_REGEX = r"^\d+(st|nd|rd|th)$"
# A capitalised word (title-case "Vostok", or an all-caps acronym like "TKO")
# or a bare hyphen connector -- covers hyphenated proper names tokenized as
# separate pieces, e.g. "Vostok-Akhmat" -> ["Vostok", "-", "Akhmat"].
_CAP_OR_HYPHEN_REGEX = r"^(-|[A-Z][A-Za-z]*)$"


def _load_terms(filename: str) -> list[str]:
    path = GAZETTEERS_DIR / filename
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


class Preannotator:
    """Gazetteer + regex rules layered on top of en_core_web_sm."""

    def __init__(self, nlp: Language | None = None) -> None:
        self.nlp = nlp or spacy.load(BASE_MODEL, disable=_UNUSED_COMPONENTS)
        self._mil_org_cues = [t.lower() for t in _load_terms("mil_orgs.txt")]

        # Matched case-insensitively on raw token text (LOWER), not LEMMA: lemmatizing
        # a short out-of-context gazetteer phrase is unreliable for proper nouns (e.g.
        # "Bradley" alone tags as a common noun with lemma "bradley", but "Bradley" in
        # a real sentence tags as a proper noun with lemma "Bradley" -- the mismatch
        # silently drops the match). Plural/singular variants are listed explicitly in
        # the gazetteer files instead, keeping matching fully deterministic.
        self._phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self._phrase_matcher.add(
            "WEAPON", [self.nlp.make_doc(t) for t in _load_terms("weapons.txt")]
        )
        self._phrase_matcher.add(
            "MIL_UNIT", [self.nlp.make_doc(t) for t in _load_terms("mil_units.txt")]
        )
        self._phrase_matcher.add(
            "MIL_ORG", [self.nlp.make_doc(t) for t in _load_terms("mil_orgs.txt")]
        )

        unit_nouns = [t for t in _load_terms("mil_units.txt") if " " not in t]
        self._unit_matcher = Matcher(self.nlp.vocab)
        # e.g. "58th Army", "3rd Motor Rifle Brigade", "24th separate Mechanized Brigade".
        # Intervening tokens are matched on shape (IS_ALPHA), not POS, and bounded to at
        # most 3 -- this stays deterministic (no dependency on the statistical tagger)
        # and avoids the pattern running away across a whole sentence.
        self._unit_matcher.add(
            "NUMBERED_UNIT",
            [
                [
                    {"TEXT": {"REGEX": _ORDINAL_REGEX}},
                    {"IS_ALPHA": True, "OP": "?"},
                    {"IS_ALPHA": True, "OP": "?"},
                    {"IS_ALPHA": True, "OP": "?"},
                    {"LOWER": {"IN": unit_nouns}},
                ]
            ],
        )
        # e.g. "Vostok-Akhmat Battalion", "Kalashnikov Company", "Triada-TKO Company":
        # units named after a person/place/codename rather than a number. Bounded to
        # at most 4 leading capitalised/hyphen tokens for the same reason as above.
        # IS_STOP: False excludes a merely sentence-initial capital ("The brigade...")
        # from being mistaken for part of a proper name.
        cap_token = {"TEXT": {"REGEX": _CAP_OR_HYPHEN_REGEX}, "IS_STOP": False}
        self._unit_matcher.add(
            "NAMED_UNIT",
            [
                [
                    cap_token,
                    {**cap_token, "OP": "?"},
                    {**cap_token, "OP": "?"},
                    {**cap_token, "OP": "?"},
                    {"LOWER": {"IN": unit_nouns}},
                ]
            ],
        )

    def _looks_military(self, text: str) -> bool:
        lowered = text.lower()
        return any(cue in lowered for cue in self._mil_org_cues)

    @staticmethod
    def _overlaps_any(span: Span, others: list[Span]) -> bool:
        return any(span.start < o.end and span.end > o.start for o in others)

    def _spans_for_doc(self, doc: Doc) -> list[tuple[int, int, str]]:
        rule_spans: list[Span] = [
            Span(doc, start, end, label=self.nlp.vocab.strings[match_id])
            for match_id, start, end in self._phrase_matcher(doc)
        ]
        rule_spans += [
            Span(doc, start, end, label="MIL_UNIT") for _, start, end in self._unit_matcher(doc)
        ]
        rule_spans = filter_spans(rule_spans)

        org_spans = [
            Span(doc, ent.start, ent.end, label="MIL_ORG")
            for ent in doc.ents
            if ent.label_ == "ORG"
            and self._looks_military(ent.text)
            and not self._overlaps_any(ent, rule_spans)
        ]

        final_spans = filter_spans(rule_spans + org_spans)
        return [(span.start_char, span.end_char, span.label_) for span in final_spans]

    def annotate_text(self, text: str) -> list[tuple[int, int, str]]:
        """Return non-overlapping (start_char, end_char, label) spans for one article."""
        return self._spans_for_doc(self.nlp(text))

    def annotate_texts(
        self, texts: Iterable[str], batch_size: int = 64
    ) -> Iterator[list[tuple[int, int, str]]]:
        """Batched equivalent of annotate_text -- use for anything beyond a handful of
        articles, since `nlp.pipe` amortises per-call overhead across the batch."""
        for doc in self.nlp.pipe(texts, batch_size=batch_size):
            yield self._spans_for_doc(doc)


def annotate(corpus_path: Path, output_path: Path, preannotator: Preannotator | None = None) -> int:
    """Pre-annotate every article in corpus.jsonl, writing annotations.json.

    Each record is `{"id", "text", "entities": [[start, end, label], ...]}`.
    The `id` is kept for traceability during human review; spacy_convert.py
    strips it back down to the exact `(text, {"entities": [...]})` tuple
    format shown on slide 23 when building the training DocBin.
    """
    preannotator = preannotator or Preannotator()
    articles = list(iter_corpus(corpus_path))
    texts = [article.text for article in articles]

    records = []
    entity_lists = preannotator.annotate_texts(texts)
    for article, entities in tqdm(
        zip(articles, entity_lists, strict=True), total=len(articles), desc="annotate"
    ):
        records.append({"id": article.id, "text": article.text, "entities": entities})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)

    total_entities = sum(len(r["entities"]) for r in records)
    logger.info(
        "Pre-annotated %d articles (%d entity spans) -> %s",
        len(records),
        total_entities,
        output_path,
    )
    return len(records)
