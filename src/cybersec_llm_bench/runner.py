"""Run an alert through one or more models and collect timed results."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from .client import OllamaClient
from .config import ModelConfig
from .extract import extract_confidence, extract_techniques, extract_verdict


@dataclass
class RunResult:
    """Single (alert, model) evaluation result."""

    run_id: str
    alert_id: str
    model_id: str
    model_tag: str
    response: str
    prompt_tokens: int
    completion_tokens: int
    total_duration_ms: float
    load_duration_ms: float
    eval_duration_ms: float
    tokens_per_second: float
    wall_clock_ms: float
    verdict: str | None
    confidence: str | None
    techniques: list[str]
    error: str | None = None


def render_prompt(template: str, alert: dict[str, Any]) -> str:
    """Substitute {alert_json} placeholder with pretty-printed alert JSON."""
    payload = json.dumps(alert, indent=2, ensure_ascii=False)
    return template.replace("{alert_json}", payload)


def run_alert(
    client: OllamaClient,
    models: list[ModelConfig],
    alert: dict[str, Any],
    prompt_template: str,
    *,
    sequential_unload: bool = True,
    temperature: float = 0.0,
    num_ctx: int = 8192,
) -> list[RunResult]:
    """Run `alert` against every model in `models`, sequentially.

    Parameters
    ----------
    sequential_unload
        If True (default), each model is evicted from VRAM after its call
        via `keep_alive=0`. Required when total model footprint exceeds
        available GPU memory. Set to False on rigs with comfortable VRAM.
    temperature
        Sampling temperature. Default 0.0 for reproducible benchmark runs.
    num_ctx
        Context window size. Larger = more VRAM. 8192 is a safe default for
        typical SOC alerts.
    """
    rendered = render_prompt(prompt_template, alert)
    run_id = str(uuid.uuid4())
    alert_id = str(alert.get("alert_id", "unknown"))
    keep_alive = "0" if sequential_unload else "5m"
    results: list[RunResult] = []

    for cfg in models:
        try:
            out = client.generate(
                cfg.ollama_tag,
                rendered,
                temperature=temperature,
                num_ctx=num_ctx,
                keep_alive=keep_alive,
            )
            results.append(RunResult(
                run_id=run_id,
                alert_id=alert_id,
                model_id=cfg.id,
                model_tag=cfg.ollama_tag,
                response=out["response"],
                prompt_tokens=out["prompt_tokens"],
                completion_tokens=out["completion_tokens"],
                total_duration_ms=out["total_duration_ms"],
                load_duration_ms=out["load_duration_ms"],
                eval_duration_ms=out["eval_duration_ms"],
                tokens_per_second=out["tokens_per_second"],
                wall_clock_ms=out["wall_clock_ms"],
                verdict=extract_verdict(out["response"]),
                confidence=extract_confidence(out["response"]),
                techniques=extract_techniques(out["response"]),
            ))
        except Exception as e:
            results.append(RunResult(
                run_id=run_id, alert_id=alert_id,
                model_id=cfg.id, model_tag=cfg.ollama_tag,
                response="",
                prompt_tokens=0, completion_tokens=0,
                total_duration_ms=0.0, load_duration_ms=0.0,
                eval_duration_ms=0.0,
                tokens_per_second=0.0, wall_clock_ms=0.0,
                verdict=None, confidence=None, techniques=[],
                error=f"{type(e).__name__}: {e}",
            ))
    return results
