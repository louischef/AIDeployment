"""Unified CLI: `python -m osint_ner <subcommand> [options]`.

Every pipeline stage is a plain, independently testable function in its own
module; this file only wires argparse onto those functions so the whole
pipeline runs identically from PowerShell or bash, with no dependency on
`make` (the Makefile is a convenience wrapper around these same commands).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from osint_ner import config


def _cmd_extract(args: argparse.Namespace) -> None:
    from osint_ner.extract import extract

    extract(Path(args.input), Path(args.output))


def _cmd_annotate(args: argparse.Namespace) -> None:
    from osint_ner.annotate import annotate

    annotate(Path(args.corpus), Path(args.output))


def _cmd_review(args: argparse.Namespace) -> None:
    from osint_ner.review import run_review

    run_review(Path(args.annotations), Path(args.log), sample_size=args.sample, seed=args.seed)


def _cmd_split(args: argparse.Namespace) -> None:
    from osint_ner.spacy_convert import convert

    convert(
        Path(args.annotations),
        Path(args.train_out),
        Path(args.dev_out),
        train_fraction=args.train_fraction,
        seed=args.seed,
    )


def _cmd_train_config(args: argparse.Namespace) -> None:
    from osint_ner.train_config import generate_config

    generate_config(Path(args.output))


def _cmd_infer(args: argparse.Namespace) -> None:
    from osint_ner.infer import infer

    infer(Path(args.corpus), Path(args.model), Path(args.output), batch_size=args.batch_size)


def _cmd_analyze(args: argparse.Namespace) -> None:
    from osint_ner.analyze import load_entity_docs, print_report

    print_report(load_entity_docs(Path(args.entities)), top_n=args.top)


def _cmd_es_index(args: argparse.Namespace) -> None:
    from osint_ner.es_ingest import ensure_index, get_client

    ensure_index(get_client(), args.index, Path(args.mapping))


def _cmd_es_ingest(args: argparse.Namespace) -> None:
    from osint_ner.es_ingest import get_client, ingest

    ingest(get_client(), args.index, Path(args.entities))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="osint_ner", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("extract", help="Step 1: articles.json -> corpus.jsonl")
    p.add_argument("--input", default=str(config.RAW_ARTICLES_PATH))
    p.add_argument("--output", default=str(config.CORPUS_PATH))
    p.set_defaults(func=_cmd_extract)

    p = sub.add_parser("annotate", help="Step 2: corpus.jsonl -> annotations.json (pre-annotation)")
    p.add_argument("--corpus", default=str(config.CORPUS_PATH))
    p.add_argument("--output", default=str(config.ANNOTATIONS_PATH))
    p.set_defaults(func=_cmd_annotate)

    p = sub.add_parser("review", help="Step 2c: interactive human validation of annotations.json")
    p.add_argument("--annotations", default=str(config.ANNOTATIONS_PATH))
    p.add_argument("--log", default=str(config.REVIEW_LOG_PATH))
    p.add_argument("--sample", type=int, default=20)
    p.add_argument("--seed", type=int, default=config.TRAIN_DEV_SPLIT_SEED)
    p.set_defaults(func=_cmd_review)

    p = sub.add_parser("split", help="Step 3a: annotations.json -> train.spacy + dev.spacy")
    p.add_argument("--annotations", default=str(config.ANNOTATIONS_PATH))
    p.add_argument("--train-out", default=str(config.TRAIN_SPACY_PATH))
    p.add_argument("--dev-out", default=str(config.DEV_SPACY_PATH))
    p.add_argument("--train-fraction", type=float, default=config.TRAIN_FRACTION)
    p.add_argument("--seed", type=int, default=config.TRAIN_DEV_SPLIT_SEED)
    p.set_defaults(func=_cmd_split)

    p = sub.add_parser(
        "train-config", help="Step 3b: generate configs/config.cfg sourced from en_core_web_sm"
    )
    p.add_argument("--output", default=str(config.CONFIGS_DIR / "config.cfg"))
    p.set_defaults(func=_cmd_train_config)

    p = sub.add_parser("infer", help="Step 4: run output/model-best over corpus.jsonl")
    p.add_argument("--corpus", default=str(config.CORPUS_PATH))
    p.add_argument("--model", default=str(config.MODEL_BEST_DIR))
    p.add_argument("--output", default=str(config.ENTITIES_PATH))
    p.add_argument("--batch-size", type=int, default=32)
    p.set_defaults(func=_cmd_infer)

    p = sub.add_parser("analyze", help="Print top entities per label and a quick sanity report")
    p.add_argument("--entities", default=str(config.ENTITIES_PATH))
    p.add_argument("--top", type=int, default=10)
    p.set_defaults(func=_cmd_analyze)

    p = sub.add_parser(
        "es-index", help="Step 5: create the Elasticsearch index from elastic/index_mapping.json"
    )
    p.add_argument("--index", default=config.ES_INDEX)
    p.add_argument("--mapping", default=str(config.ELASTIC_DIR / "index_mapping.json"))
    p.set_defaults(func=_cmd_es_index)

    p = sub.add_parser("es-ingest", help="Step 5: bulk-index entities.jsonl into Elasticsearch")
    p.add_argument("--index", default=config.ES_INDEX)
    p.add_argument("--entities", default=str(config.ENTITIES_PATH))
    p.set_defaults(func=_cmd_es_ingest)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
