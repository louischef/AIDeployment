"""Step 1 -- Extract: articles.json -> data/interim/corpus.jsonl.

Parses the raw JSON export, isolates the text field of each article (tolerant
to a handful of common field-naming conventions, see schemas.RawArticle),
applies minimal whitespace/control-character cleanup, and writes one JSON
object per line -- articles are never concatenated into a single text blob.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from osint_ner.schemas import Article, RawArticle

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"[ \t ]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Minimal, non-destructive cleanup: normalise unicode, strip control
    characters, collapse runs of spaces/tabs and excessive blank lines.

    Deliberately does NOT lowercase, strip punctuation, or remove stopwords --
    the NER model needs the original casing and punctuation to find entity
    boundaries.
    """
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if ch == "\n" or ch.isprintable())
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def normalise_date(value: str | int | None) -> str | None:
    """Normalise a raw date to an ISO 8601 date string.

    Accepts either an already-formatted string or a Unix timestamp (seconds
    since epoch) -- the real TASS export uses the latter.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    return value


def normalise_url(value: str | None) -> str | None:
    """The real TASS export stores `link` as a site-relative path; make it a full URL."""
    if value and value.startswith("/"):
        return f"https://tass.com{value}"
    return value


def load_raw_articles(input_path: Path) -> list[dict]:
    with open(input_path, encoding="utf-8") as fh:
        payload = json.load(fh)

    if isinstance(payload, dict):
        # Tolerate a top-level wrapper such as {"articles": [...]}.
        for key in ("articles", "data", "items", "results"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
        raise ValueError(
            f"{input_path} is a JSON object without a recognisable list field "
            f"(looked for 'articles'/'data'/'items'/'results'); top-level keys: "
            f"{sorted(payload.keys())}"
        )
    if isinstance(payload, list):
        return payload
    raise ValueError(
        f"{input_path} must contain a JSON array or object, got {type(payload).__name__}"
    )


def parse_article(raw: dict, index: int) -> Article | None:
    try:
        parsed = RawArticle.model_validate(raw)
    except ValidationError as exc:
        logger.warning(
            "Skipping record #%d: %s. Available keys were: %s",
            index,
            exc.errors()[0].get("msg", exc),
            sorted(raw.keys()) if isinstance(raw, dict) else type(raw).__name__,
        )
        return None

    cleaned = clean_text(parsed.text)
    if not cleaned:
        logger.warning("Skipping record #%d: text is empty after cleaning", index)
        return None

    article_id = str(parsed.id) if parsed.id is not None else f"article-{index:06d}"
    return Article(
        id=article_id,
        url=normalise_url(parsed.url),
        title=parsed.title,
        date=normalise_date(parsed.date),
        text=cleaned,
    )


def extract(input_path: Path, output_path: Path) -> int:
    """Run the full extraction step. Returns the number of articles written."""
    raw_records = load_raw_articles(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for index, raw in enumerate(raw_records):
            article = parse_article(raw, index)
            if article is None:
                continue
            out.write(article.model_dump_json())
            out.write("\n")
            written += 1

    logger.info("Extracted %d/%d articles -> %s", written, len(raw_records), output_path)
    return written


def iter_corpus(corpus_path: Path):
    """Yield Article objects from an existing corpus.jsonl."""
    with open(corpus_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield Article.model_validate_json(line)
