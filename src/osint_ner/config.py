"""Central paths, constants, and environment loading for the pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
ANNOTATIONS_DIR = DATA_DIR / "annotations"
PROCESSED_DIR = DATA_DIR / "processed"

GAZETTEERS_DIR = Path(__file__).resolve().parent / "gazetteers"
CONFIGS_DIR = ROOT_DIR / "configs"
ELASTIC_DIR = ROOT_DIR / "elastic"

RAW_ARTICLES_PATH = RAW_DIR / "articles.json"
CORPUS_PATH = INTERIM_DIR / "corpus.jsonl"
ANNOTATIONS_PATH = ANNOTATIONS_DIR / "annotations.json"
REVIEW_LOG_PATH = ANNOTATIONS_DIR / "review_log.json"
TRAIN_SPACY_PATH = ANNOTATIONS_DIR / "train.spacy"
DEV_SPACY_PATH = ANNOTATIONS_DIR / "dev.spacy"
ENTITIES_PATH = PROCESSED_DIR / "entities.jsonl"

MODEL_BEST_DIR = ROOT_DIR / "output" / "model-best"
BASE_MODEL = "en_core_web_sm"

# Our custom NER schema (slide 15). Keep this list as the single source of truth:
# gazetteers, training config, and Elasticsearch mapping all key off these labels.
ENTITY_LABELS = ("WEAPON", "MIL_UNIT", "MIL_ORG")

TRAIN_DEV_SPLIT_SEED = 13
TRAIN_FRACTION = 0.8

ES_CLOUD_ID = os.getenv("ES_CLOUD_ID") or None
ES_API_KEY = os.getenv("ES_API_KEY") or None
ES_URL = os.getenv("ES_URL") or None
ES_INDEX = os.getenv("ES_INDEX", "tass_war_entities")

# TASS is a Russian state media outlet (see slide 6): every ingested document
# carries this provenance/bias marker so it survives into Kibana, not just the report.
SOURCE_NAME = "TASS"
SOURCE_BIAS = "state-affiliated (Russia) — reports the source's claims, not verified fact"
