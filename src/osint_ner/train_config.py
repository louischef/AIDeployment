"""Step 3b -- generate configs/config.cfg via spaCy's own CLI, then source
en_core_web_sm into the NER component (slide 26) so training starts from the
pretrained model instead of an empty NER head.

Actual training (step 3c) is deliberately NOT wrapped in Python -- it is a
direct `python -m spacy train` call (see Makefile / README), matching the
TP's literal commands instead of reinventing spaCy's own trainer/CLI.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

from osint_ner.config import BASE_MODEL

logger = logging.getLogger(__name__)

# Matches the whole `[components.ner]` block: its header line plus every
# following line up to (but not including) the next `[section]` header.
_NER_SECTION_RE = re.compile(r"^\[components\.ner\]\n(?:(?!^\[).*\n?)*", re.MULTILINE)


def generate_config(output_path: Path, lang: str = "en", pipeline: str = "ner") -> Path:
    """Run `spacy init config` and source en_core_web_sm into [components.ner]."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "spacy",
            "init",
            "config",
            str(output_path),
            "--lang",
            lang,
            "--pipeline",
            pipeline,
            "--force",
        ],
        check=True,
    )

    config_text = output_path.read_text(encoding="utf-8")
    if not _NER_SECTION_RE.search(config_text):
        raise RuntimeError(f"Could not find a [components.ner] section in generated {output_path}")

    patched = _NER_SECTION_RE.sub(
        f'[components.ner]\nsource = "{BASE_MODEL}"\n\n', config_text, count=1
    )
    output_path.write_text(patched, encoding="utf-8")

    logger.info("Wrote %s with [components.ner] sourced from %s", output_path, BASE_MODEL)
    return output_path
