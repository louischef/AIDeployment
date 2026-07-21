from __future__ import annotations

import json

import spacy
from spacy.tokens import DocBin

from osint_ner.spacy_convert import convert, split_train_dev, to_docbin


def _span(text: str, substring: str, label: str) -> tuple[int, int, str]:
    start = text.index(substring)
    return (start, start + len(substring), label)


def test_split_train_dev_is_deterministic_for_a_given_seed():
    pairs = [(f"text {i}", {"entities": []}) for i in range(10)]

    train_a, dev_a = split_train_dev(pairs, train_fraction=0.8, seed=42)
    train_b, dev_b = split_train_dev(pairs, train_fraction=0.8, seed=42)

    assert train_a == train_b
    assert dev_a == dev_b
    assert len(train_a) == 8
    assert len(dev_a) == 2


def test_to_docbin_sets_aligned_entities():
    nlp = spacy.blank("en")
    text = "Kalibr missiles hit the brigade."
    entities = [_span(text, "Kalibr", "WEAPON"), _span(text, "brigade", "MIL_UNIT")]

    doc_bin = to_docbin([(text, {"entities": entities})], nlp)
    docs = list(doc_bin.get_docs(nlp.vocab))

    assert len(docs) == 1
    labels = {(ent.text, ent.label_) for ent in docs[0].ents}
    assert labels == {("Kalibr", "WEAPON"), ("brigade", "MIL_UNIT")}


def test_to_docbin_drops_misaligned_span_instead_of_raising():
    nlp = spacy.blank("en")
    text = "Kalibr missiles hit the brigade."
    # (2, 6) slices "libr" out of the "Kalibr" token -- not a token boundary.
    pairs = [(text, {"entities": [(2, 6, "WEAPON")]})]

    doc_bin = to_docbin(pairs, nlp)
    docs = list(doc_bin.get_docs(nlp.vocab))

    assert len(docs) == 1
    assert docs[0].ents == ()


def test_convert_end_to_end(tmp_path):
    annotations = [
        {"id": f"a{i}", "text": f"Kalibr missile {i}.", "entities": [[0, 6, "WEAPON"]]}
        for i in range(10)
    ]
    annotations_path = tmp_path / "annotations.json"
    annotations_path.write_text(json.dumps(annotations), encoding="utf-8")

    train_out = tmp_path / "train.spacy"
    dev_out = tmp_path / "dev.spacy"
    train_count, dev_count = convert(
        annotations_path, train_out, dev_out, train_fraction=0.8, seed=1
    )

    assert (train_count, dev_count) == (8, 2)
    assert train_out.exists()
    assert dev_out.exists()

    nlp = spacy.blank("en")
    train_docs = list(DocBin().from_disk(train_out).get_docs(nlp.vocab))
    assert len(train_docs) == 8
