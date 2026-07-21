"""Pydantic models used across pipeline stages.

Keeping these in one module means every stage (extract -> annotate -> infer ->
ingest) agrees on field names without importing each other's internals.
"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, Field, field_validator


class RawArticle(BaseModel):
    """One record as it might appear in the source `articles.json`.

    Real-world TASS exports vary in field naming, so each field accepts a
    handful of common aliases. If none match, pydantic raises a validation
    error that names the missing field -- see extract.py for how that error
    is surfaced with the actual keys found in the record.
    """

    model_config = {"populate_by_name": True}

    id: str | int | None = Field(
        default=None, validation_alias=AliasChoices("id", "article_id", "uid", "_id")
    )
    text: str = Field(
        validation_alias=AliasChoices("text", "body", "content", "full_text", "article_text")
    )
    title: str | None = Field(default=None, validation_alias=AliasChoices("title", "headline"))
    # The real TASS export encodes `date` as a Unix timestamp (int), not a
    # string -- both are accepted here; extract.py normalises to an ISO date.
    date: str | int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "date", "published_at", "pubDate", "publish_date", "timestamp"
        ),
    )
    url: str | None = Field(
        default=None, validation_alias=AliasChoices("url", "link", "source_url")
    )

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("article text is empty after stripping")
        return v


class Article(BaseModel):
    """Cleaned, per-article record written to data/interim/corpus.jsonl."""

    id: str
    url: str | None = None
    title: str | None = None
    date: str | None = None
    text: str


class EntitySpan(BaseModel):
    start: int
    end: int
    label: str
    text: str


class EntityDoc(BaseModel):
    """One article enriched with extracted entities, ready for Elasticsearch."""

    id: str
    url: str | None = None
    title: str | None = None
    date: str | None = None
    text: str
    entities: list[EntitySpan]
    weapons: list[str] = Field(default_factory=list)
    mil_units: list[str] = Field(default_factory=list)
    mil_orgs: list[str] = Field(default_factory=list)
