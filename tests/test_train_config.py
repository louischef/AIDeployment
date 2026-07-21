from __future__ import annotations

from osint_ner.train_config import generate_config


def test_generate_config_sources_en_core_web_sm(tmp_path):
    output = tmp_path / "config.cfg"

    generate_config(output)

    text = output.read_text(encoding="utf-8")
    assert '[components.ner]\nsource = "en_core_web_sm"' in text
    # the default (un-sourced) architecture keys should be gone from that section
    ner_section = text.split("[components.ner]")[1].split("\n[")[0]
    assert "factory" not in ner_section
