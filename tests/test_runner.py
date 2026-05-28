"""Tests for prompt rendering and config loading."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cybersec_llm_bench.config import BenchConfig
from cybersec_llm_bench.runner import render_prompt


def test_render_prompt_substitutes_alert_json() -> None:
    template = "## Alert\n```json\n{alert_json}\n```\nAnalyze."
    alert = {"alert_id": "abc", "rule": {"name": "test"}}
    rendered = render_prompt(template, alert)
    assert "{alert_json}" not in rendered
    assert '"alert_id"' in rendered
    assert '"abc"' in rendered


def test_render_prompt_pretty_prints() -> None:
    rendered = render_prompt("{alert_json}", {"a": 1, "b": 2})
    # indent=2 produces newlines between keys
    assert "\n" in rendered


def test_render_prompt_handles_non_ascii() -> None:
    rendered = render_prompt("{alert_json}", {"user": "şükrü"})
    # ensure_ascii=False → original characters preserved
    assert "şükrü" in rendered


def test_render_prompt_no_placeholder_unchanged() -> None:
    rendered = render_prompt("static template", {"x": 1})
    assert rendered == "static template"


def test_config_load_valid(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[ollama]\nbase_url = "http://localhost:11434"\n\n'
        '[[models]]\nid = "a"\ndisplay_name = "A"\nollama_tag = "a:latest"\n'
    )
    cfg = BenchConfig.load(cfg_path)
    assert cfg.ollama_base_url == "http://localhost:11434"
    assert len(cfg.models) == 1
    assert cfg.models[0].id == "a"


def test_config_missing_models_raises(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('[ollama]\nbase_url = "http://x"\n')
    with pytest.raises(ValueError, match="no \\[\\[models\\]\\]"):
        BenchConfig.load(cfg_path)


def test_config_missing_ollama_raises(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[[models]]\nid = "a"\ndisplay_name = "A"\nollama_tag = "a"\n'
    )
    with pytest.raises(ValueError, match="\\[ollama\\]"):
        BenchConfig.load(cfg_path)


def test_sample_alerts_are_valid_json() -> None:
    """Smoke test: every shipped alert parses and has the expected keys."""
    alerts_dir = Path(__file__).parent.parent / "alerts"
    if not alerts_dir.exists():
        pytest.skip("alerts directory not present")
    files = list(alerts_dir.glob("*.json"))
    assert files, "no sample alerts found"
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        assert "alert_id" in data, f"{f.name} missing alert_id"
        assert "rule" in data, f"{f.name} missing rule"
        assert "expected_verdict" in data, f"{f.name} missing expected_verdict"
