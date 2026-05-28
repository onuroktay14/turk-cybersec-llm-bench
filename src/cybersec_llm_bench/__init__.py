"""cybersec-llm-bench: head-to-head benchmark for cybersecurity LLMs.

Public API:
    OllamaClient, BenchConfig, ModelConfig,
    run_alert, render_prompt, RunResult,
    extract_verdict, extract_confidence, extract_techniques,
    save_runs, list_runs, update_score
"""
from __future__ import annotations

from .client import OllamaClient
from .config import BenchConfig, ModelConfig
from .extract import extract_confidence, extract_techniques, extract_verdict
from .runner import RunResult, render_prompt, run_alert
from .storage import list_runs, save_runs, update_score

__version__ = "0.1.0"

__all__ = [
    "BenchConfig",
    "ModelConfig",
    "OllamaClient",
    "RunResult",
    "__version__",
    "extract_confidence",
    "extract_techniques",
    "extract_verdict",
    "list_runs",
    "render_prompt",
    "run_alert",
    "save_runs",
    "update_score",
]
