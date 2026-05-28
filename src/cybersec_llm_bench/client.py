"""Ollama HTTP client — thin wrapper around /api/generate."""
from __future__ import annotations

import time
from typing import Any

import httpx


class OllamaClient:
    """Synchronous Ollama client that surfaces native timing fields."""

    def __init__(self, base_url: str, timeout: float = 600.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        num_ctx: int = 8192,
        keep_alive: str = "5m",
    ) -> dict[str, Any]:
        """Call /api/generate and return a normalized result dict.

        Timing fields are converted from nanoseconds to milliseconds.
        `tokens_per_second` is computed from `eval_count / eval_duration`.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
            "keep_alive": keep_alive,
        }
        t0 = time.perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
        wall_ms = (time.perf_counter() - t0) * 1000

        eval_count = data.get("eval_count", 0) or 0
        eval_dur_ns = data.get("eval_duration", 0) or 0
        tps = (eval_count / (eval_dur_ns / 1e9)) if eval_dur_ns > 0 else 0.0

        return {
            "response": data.get("response", ""),
            "prompt_tokens": data.get("prompt_eval_count", 0) or 0,
            "completion_tokens": eval_count,
            "total_duration_ms": (data.get("total_duration", 0) or 0) / 1e6,
            "load_duration_ms": (data.get("load_duration", 0) or 0) / 1e6,
            "prompt_eval_duration_ms": (data.get("prompt_eval_duration", 0) or 0) / 1e6,
            "eval_duration_ms": eval_dur_ns / 1e6,
            "tokens_per_second": tps,
            "wall_clock_ms": wall_ms,
        }

    def unload(self, model: str) -> None:
        """Force-unload a model from VRAM via keep_alive=0."""
        try:
            with httpx.Client(timeout=30.0) as client:
                client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": model, "keep_alive": 0, "prompt": ""},
                )
        except Exception:
            pass

    def list_models(self) -> list[str]:
        """List models currently available on this Ollama instance."""
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{self.base_url}/api/tags")
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
