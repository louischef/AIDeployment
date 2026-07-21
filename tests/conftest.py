from __future__ import annotations

from pathlib import Path

import pytest
import spacy

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ARTICLES_PATH = REPO_ROOT / "examples" / "sample_articles.json"


@pytest.fixture(scope="session")
def en_core_web_sm():
    """Loaded once per test session -- annotate.py's Preannotator accepts an
    injected nlp so tests don't pay the model-loading cost repeatedly."""
    return spacy.load("en_core_web_sm")


@pytest.fixture
def sample_articles_path() -> Path:
    return SAMPLE_ARTICLES_PATH
