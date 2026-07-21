from __future__ import annotations

from itertools import pairwise

from osint_ner.annotate import Preannotator


def _spans_by_text(entities, text):
    return {text[start:end]: label for start, end, label in entities}


def test_weapon_and_bare_unit_gazetteer(en_core_web_sm):
    # This is the exact example from the TP slides (slide 8 / 23).
    pre = Preannotator(nlp=en_core_web_sm)
    text = "The brigade fired Kalibr missiles near Kharkiv."

    spans = _spans_by_text(pre.annotate_text(text), text)

    assert spans.get("brigade") == "MIL_UNIT"
    assert spans.get("Kalibr") == "WEAPON"


def test_numbered_unit_pattern(en_core_web_sm):
    pre = Preannotator(nlp=en_core_web_sm)
    text = "The 58th Army and the 3rd Motor Rifle Brigade advanced together."

    spans = _spans_by_text(pre.annotate_text(text), text)

    assert spans.get("58th Army") == "MIL_UNIT"
    assert spans.get("3rd Motor Rifle Brigade") == "MIL_UNIT"


def test_mil_org_gazetteer(en_core_web_sm):
    pre = Preannotator(nlp=en_core_web_sm)
    text = "The Ministry of Defence confirmed the strike near the border."

    spans = _spans_by_text(pre.annotate_text(text), text)

    assert spans.get("Ministry of Defence") == "MIL_ORG"


def test_offsets_are_valid_non_empty_slices(en_core_web_sm):
    pre = Preannotator(nlp=en_core_web_sm)
    text = "Lancet drones and Iskander missiles struck the 24th Mechanized Brigade."

    entities = pre.annotate_text(text)

    assert entities, "expected at least one entity span"
    for start, end, label in entities:
        assert 0 <= start < end <= len(text)
        assert text[start:end].strip() != ""
        assert label in {"WEAPON", "MIL_UNIT", "MIL_ORG"}


def test_spans_never_overlap(en_core_web_sm):
    pre = Preannotator(nlp=en_core_web_sm)
    text = (
        "Kalibr missiles and Iskander missiles hit the base of the "
        "3rd Motor Rifle Brigade near the Ministry of Defence compound."
    )

    entities = sorted(pre.annotate_text(text))

    for (_, end, _), (next_start, _, _) in pairwise(entities):
        assert end <= next_start


def test_looks_military_cue_matching(en_core_web_sm):
    pre = Preannotator(nlp=en_core_web_sm)

    assert pre._looks_military("Russian Ministry of Defence")
    assert not pre._looks_military("Acme Trading Corp")


def test_non_military_org_is_not_tagged(en_core_web_sm):
    pre = Preannotator(nlp=en_core_web_sm)
    text = "Acme Trading Corp, a logistics contractor, was not involved."

    spans = _spans_by_text(pre.annotate_text(text), text)

    assert "Acme Trading Corp" not in spans
