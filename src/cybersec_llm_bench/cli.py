"""Command-line interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .client import OllamaClient
from .config import BenchConfig
from .runner import RunResult, run_alert
from .storage import save_runs


def _print_result(r: RunResult) -> None:
    bar = "━" * 8
    print(f"\n{bar} {r.model_id}  ({r.model_tag}) {bar}")
    if r.error:
        print(f"  ERROR: {r.error}")
        return
    print(f"  verdict={r.verdict}  confidence={r.confidence}  "
          f"techniques={r.techniques or '—'}")
    print(f"  tokens: in={r.prompt_tokens}  out={r.completion_tokens}  "
          f"t/s={r.tokens_per_second:.1f}")
    print(f"  timing: wall={r.wall_clock_ms:.0f}ms  "
          f"load={r.load_duration_ms:.0f}ms  "
          f"eval={r.eval_duration_ms:.0f}ms")
    print()
    print(r.response)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cybersec-llm-bench",
        description="Benchmark cybersecurity LLMs on SOC alerts via Ollama.",
    )
    p.add_argument("--alert", required=True, help="Path to alert JSON file")
    p.add_argument("--prompt", default="prompts/triage_v1_tr.md",
                   help="Path to Markdown prompt template")
    p.add_argument("--config", default="config.toml",
                   help="Path to TOML config file")
    p.add_argument("--no-save", action="store_true",
                   help="Don't persist results to SQLite")
    p.add_argument("--keep-loaded", action="store_true",
                   help="Don't unload models between calls (faster re-runs, more VRAM)")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--num-ctx", type=int, default=8192)
    p.add_argument("--db", default="results/runs.db",
                   help="SQLite database path")
    args = p.parse_args(argv)

    try:
        cfg = BenchConfig.load(args.config)
    except FileNotFoundError:
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        print("hint: copy config.example.toml to config.toml and edit",
              file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: failed to load config: {e}", file=sys.stderr)
        return 2

    try:
        alert = json.loads(Path(args.alert).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: alert file not found: {args.alert}", file=sys.stderr)
        return 2

    try:
        template = Path(args.prompt).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"error: prompt file not found: {args.prompt}", file=sys.stderr)
        return 2

    client = OllamaClient(cfg.ollama_base_url)
    print(f"→ alert={alert.get('alert_id')} models={len(cfg.models)} "
          f"ollama={cfg.ollama_base_url} "
          f"sequential_unload={not args.keep_loaded}")

    results = run_alert(
        client, cfg.models, alert, template,
        sequential_unload=not args.keep_loaded,
        temperature=args.temperature,
        num_ctx=args.num_ctx,
    )
    for r in results:
        _print_result(r)

    if not args.no_save:
        save_runs(results, alert, template, db_path=args.db)
        print(f"\n✓ saved {len(results)} run(s) to {args.db}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
