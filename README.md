# OSINT NER — TASS "War" articles

Pipeline for the *IA appliquée au renseignement OSINT* TP: turn a corpus of
TASS "War" section articles into a queryable, dashboarded set of military
entities (`WEAPON`, `MIL_UNIT`, `MIL_ORG`), using a spaCy model fine-tuned on
top of `en_core_web_sm`.

```
articles.json --extract--> corpus.jsonl --annotate--> annotations.json
    --split--> train.spacy/dev.spacy --spacy train--> model-best
    --infer--> entities.jsonl --es-ingest--> Elasticsearch --> Kibana dashboards
```

Every stage above is both a CLI subcommand (`python -m osint_ner <stage>`)
and a plain, independently testable function — see `src/osint_ner/`.

## OSINT framing (read this first)

TASS is a Russian state-affiliated outlet. This pipeline extracts **what the
source claims**, not verified fact — every ingested document is tagged with
`source_name`/`source_bias` (see `src/osint_ner/config.py`) precisely so that
caveat travels into Kibana and into any analysis built on top of it, rather
than living only as a disclaimer in a report. Treat every count and trend
this pipeline produces as "mentions in TASS reporting", not as ground truth
about the battlefield.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
```

Copy `.env.example` to `.env` and fill in your Elastic Cloud credentials
before running the `es-index` / `es-ingest` steps (step 5).

## Data

Drop the real TASS export under `data/raw/` (gitignored — see `.gitignore`,
so a 40+ MB export never ends up in git). The loader
(`osint_ner/schemas.py::RawArticle`) tolerates a few common field names so
you likely don't need to reshape anything:

| Concept | Accepted keys |
|---|---|
| id | `id`, `article_id`, `uid`, `_id` |
| text | `text`, `body`, `content`, `full_text`, `article_text` |
| title | `title`, `headline` |
| date | `date`, `published_at`, `pubDate`, `publish_date`, `timestamp` — string or Unix timestamp (int), both accepted |
| url | `url`, `link`, `source_url` — a site-relative path (`/defense/123`) is expanded to a full `tass.com` URL |

If a record matches none of these, extraction logs a warning naming the
keys it actually saw instead of silently dropping or misreading data.

The corpus this repo was actually developed and validated against is
`data/raw/data_set.json` — 21,742 TASS articles, `date` as a Unix timestamp,
`link` as a site-relative path (both handled by the normalisation above).
Run it with `python -m osint_ner extract --input data/raw/data_set.json`
(21,676/21,742 records pass extraction; the rest are missing a text field
entirely or are blank after cleaning — extraction logs exactly which and
why). Pre-annotating that full corpus (`osint_ner annotate`) takes roughly
10-15 minutes on a single CPU core; `extract`, `split`, and `train-config`
are all under a few seconds.

A small synthetic corpus also lives at `examples/sample_articles.json` so
the whole pipeline is runnable end-to-end in seconds — that's what the test
suite runs against.

## Running the pipeline

Either the Makefile or the CLI works; the Makefile just wraps the CLI (no
`make` requirement on Windows):

```bash
python -m osint_ner extract   --input examples/sample_articles.json
python -m osint_ner annotate
python -m osint_ner review --sample 20      # human validation -- see below
python -m osint_ner split
python -m osint_ner train-config
python -m spacy train configs/config.cfg --output ./output \
    --paths.train ./data/annotations/train.spacy --paths.dev ./data/annotations/dev.spacy
python -m osint_ner infer
python -m osint_ner analyze
```

or, equivalently: `make extract annotate split train-config train infer analyze`.

### Step 2 — why rule-based pre-annotation instead of an LLM

The TP's suggested workflow (slide 24) is to have an LLM generate a first
annotation pass. No LLM API key is available in this environment, so
pre-annotation instead reuses `en_core_web_sm` — the same base model step 3
fine-tunes:

- A `PhraseMatcher` + `Matcher` layer (`src/osint_ner/annotate.py`) tags
  `WEAPON` / `MIL_UNIT` / `MIL_ORG` from curated gazetteers
  (`src/osint_ner/gazetteers/*.txt`) plus a regex pattern for numbered
  formations ("58th Army", "3rd Motor Rifle Brigade").
- `en_core_web_sm`'s own generic `ORG` predictions are kept as extra
  `MIL_ORG` candidates when their text contains a military cue word
  (`mil_orgs.txt`), filling gaps the gazetteer alone would miss.
- Gazetteer/regex spans always win on overlap.

This preserves the TP's "pre-annotate automatically, then validate by hand"
workflow without a paid API. **Extend the gazetteers** as you review the
real corpus — consistency matters more than exhaustiveness (slide 16).

### Step 2c — human validation (OBLIGATOIRE)

`python -m osint_ner review --sample 20` samples N pre-annotated articles,
prints them with spans highlighted as `[text|LABEL]`, and asks you to
accept/reject/note each one; decisions land in
`data/annotations/review_log.json`. This is a lightweight stand-in for a
full annotation UI — if you'd rather use one, Label Studio / Doccano /
Prodigy all accept the same `(text, {"entities": [...]})` records.

### Step 3 — training

`osint_ner train-config` generates `configs/config.cfg` via spaCy's own
`init config` CLI and then sources `en_core_web_sm` into `[components.ner]`
(slide 26), so training starts from the pretrained model instead of an
empty NER head. The actual `spacy train` call is intentionally a direct CLI
invocation (see above / Makefile), not wrapped in Python — that mirrors the
TP's own commands and avoids re-implementing spaCy's trainer.

A model trained only on `examples/sample_articles.json` (5 articles) is a
wiring smoke test, not a usable model — real quality depends on annotating
the full TASS corpus. One concrete thing this smoke test already surfaces
(slide 28's "que constatez-vous ?"): because `source = "en_core_web_sm"`
brings over *all* of the base model's original labels (`ORDINAL`, `GPE`,
`CARDINAL`, ...), a severely undertrained run still predicts those old
labels alongside — or instead of — the new ones on inference. It takes more
steps/data than this toy run for the fine-tuned weights to fully displace
the source model's original behaviour; don't be surprised to see legacy
labels in `entities.jsonl` until the model has trained properly on the full
corpus.

### Step 5 — Elasticsearch & Kibana

```bash
python -m osint_ner es-index     # idempotent: creates the index once from elastic/index_mapping.json
python -m osint_ner es-ingest    # bulk-indexes data/processed/entities.jsonl
```

1. Create a 14-day trial cluster at <https://cloud.elastic.co/>.
2. Put its Cloud ID + an API key in `.env` (see `.env.example`).
3. Run `es-index` then `es-ingest`.
4. In Kibana, **Stack Management → Saved Objects → Import**
   `elastic/kibana_saved_objects.ndjson`. It defines the `tass_war_entities`
   index pattern and four classic visualizations (top `WEAPON` / `MIL_UNIT`
   / `MIL_ORG` terms, mentions-over-time date histogram) matching slide 31.

   This NDJSON was hand-authored against the classic Kibana visualization
   schema and could not be tested against a live cluster in this
   environment — if an object fails to import, the `visState`/aggregation
   definitions inside each line are plain enough to recreate the same panel
   manually in a couple of clicks (Visualize → the field/agg named in that
   object's `attributes`). Co-occurrence and period-filter panels mentioned
   on slide 31 depend on your actual field values and are best built ad hoc
   in Kibana once real data is loaded.

## Tests & CI

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

`pytest` runs against `examples/sample_articles.json` and `en_core_web_sm`
only — no live Elasticsearch and no real training run in CI (a `slow`
marker exists for anyone who wants to exercise a tiny real `spacy train`
locally). GitHub Actions (`.github/workflows/ci.yml`) runs the same checks
on every push/PR.

## What still needs a human

This repo is runnable end-to-end against the sample data. Finishing the
graded deliverable (slide 21) still requires you to, in order:

1. Drop the real `articles.json` in `data/raw/` and re-run the pipeline.
2. Actually review a sample with `osint_ner review` and extend the
   gazetteers based on what you see.
3. Run a real `spacy train` on the full annotated corpus.
4. Deploy an Elastic Cloud trial cluster, ingest, import the dashboards,
   and take real screenshots.
5. Fill in `report/NOTE_TEMPLATE.md` (metric analysis + intelligence note)
   with real numbers from your run, then paste it into the school's PDF
   template together with the screenshots and this repo's GitHub link.

Nothing in this repo fabricates screenshots, dashboard numbers, or the
graded template — those have to come from your own run.
