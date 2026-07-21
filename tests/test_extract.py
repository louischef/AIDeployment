from __future__ import annotations

import json

from osint_ner.extract import clean_text, extract, normalise_date, normalise_url, parse_article


def test_clean_text_collapses_whitespace_but_keeps_paragraphs():
    dirty = "  hello   world  \n\n\n\nfoo  "
    assert clean_text(dirty) == "hello world\n\nfoo"


def test_parse_article_accepts_common_field_aliases():
    raw = {
        "id": 1,
        "body": "Some article text.",
        "headline": "A title",
        "pubDate": "2024-01-01",
        "link": "http://example.com/1",
    }
    article = parse_article(raw, index=0)
    assert article is not None
    assert article.id == "1"
    assert article.text == "Some article text."
    assert article.title == "A title"
    assert article.date == "2024-01-01"
    assert article.url == "http://example.com/1"


def test_parse_article_skips_record_with_no_text_field():
    assert parse_article({"id": 1, "title": "no text here"}, index=0) is None


def test_parse_article_skips_blank_text():
    assert parse_article({"id": 1, "text": "   "}, index=0) is None


def test_parse_article_normalises_unix_timestamp_and_relative_link():
    # This mirrors the real TASS export's shape: `date` as a Unix timestamp,
    # `link` as a site-relative path.
    raw = {"id": 2035207, "text": "Some text.", "date": 1761470423, "link": "/defense/2035207"}

    article = parse_article(raw, index=0)

    assert article is not None
    assert article.date == "2025-10-26"
    assert article.url == "https://tass.com/defense/2035207"


def test_normalise_date_passes_through_strings_and_converts_timestamps():
    assert normalise_date("2024-01-01") == "2024-01-01"
    assert normalise_date(1761470423) == "2025-10-26"
    assert normalise_date(None) is None


def test_normalise_url_only_prefixes_relative_paths():
    assert normalise_url("/defense/2035207") == "https://tass.com/defense/2035207"
    assert normalise_url("https://tass.com/x") == "https://tass.com/x"
    assert normalise_url(None) is None


def test_extract_end_to_end_on_sample_corpus(tmp_path, sample_articles_path):
    output = tmp_path / "corpus.jsonl"
    count = extract(sample_articles_path, output)

    assert count == 5
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5

    first = json.loads(lines[0])
    assert first["id"] == "tass-001"
    assert first["text"] == first["text"].strip()
    assert "58th Army" in first["text"]
