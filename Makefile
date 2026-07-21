.PHONY: install download-model extract annotate review split train-config train infer analyze \
        es-index es-ingest pipeline test lint format clean

PYTHON ?= python

install:
	$(PYTHON) -m pip install -e ".[dev]"

download-model:
	$(PYTHON) -m spacy download en_core_web_sm

extract:
	$(PYTHON) -m osint_ner extract

annotate:
	$(PYTHON) -m osint_ner annotate

review:
	$(PYTHON) -m osint_ner review

split:
	$(PYTHON) -m osint_ner split

train-config:
	$(PYTHON) -m osint_ner train-config

# Step 3c is a direct spaCy CLI call by design -- see train_config.py docstring.
train:
	$(PYTHON) -m spacy train configs/config.cfg \
		--output ./output \
		--paths.train ./data/annotations/train.spacy \
		--paths.dev ./data/annotations/dev.spacy

infer:
	$(PYTHON) -m osint_ner infer

analyze:
	$(PYTHON) -m osint_ner analyze

es-index:
	$(PYTHON) -m osint_ner es-index

es-ingest:
	$(PYTHON) -m osint_ner es-ingest

# Runs extract -> annotate -> split -> train-config -> infer -> analyze in order.
# Does NOT run `train` (a real training run is a deliberate, longer step you
# trigger yourself once the annotations have been human-reviewed) or the
# es-* targets (they need real Elastic Cloud credentials in .env).
pipeline: extract annotate split train-config infer analyze

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff format .

clean:
	rm -rf data/interim/* data/annotations/* data/processed/* output
