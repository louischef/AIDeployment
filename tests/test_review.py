from __future__ import annotations

from osint_ner.review import render_highlighted, sample_records


def _span(text: str, substring: str, label: str) -> tuple[int, int, str]:
    start = text.index(substring)
    return (start, start + len(substring), label)


def test_render_highlighted_wraps_spans_with_label():
    text = "Kalibr missiles hit the brigade."
    entities = [_span(text, "Kalibr", "WEAPON"), _span(text, "brigade", "MIL_UNIT")]

    rendered = render_highlighted(text, entities)

    assert rendered == "[Kalibr|WEAPON] missiles hit the [brigade|MIL_UNIT]."


def test_render_highlighted_ignores_overlapping_span():
    text = "Kalibr missile"
    entities = [(0, 6, "WEAPON"), (2, 8, "WEAPON")]  # second overlaps the first

    rendered = render_highlighted(text, entities)

    assert rendered == "[Kalibr|WEAPON] missile"


def test_sample_records_is_deterministic_for_a_seed():
    records = [{"id": i} for i in range(20)]

    sample_a = sample_records(records, sample_size=5, seed=7)
    sample_b = sample_records(records, sample_size=5, seed=7)

    assert sample_a == sample_b
    assert len(sample_a) == 5


def test_sample_records_returns_everything_if_sample_size_exceeds_length():
    records = [{"id": i} for i in range(3)]

    assert sample_records(records, sample_size=10, seed=1) == records
