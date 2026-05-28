"""SQLite persistence for bench runs and manual scores."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .runner import RunResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    alert_id TEXT,
    alert_json TEXT,
    prompt_template TEXT,
    model_id TEXT,
    model_tag TEXT,
    response TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_duration_ms REAL,
    load_duration_ms REAL,
    eval_duration_ms REAL,
    tokens_per_second REAL,
    wall_clock_ms REAL,
    verdict TEXT,
    confidence TEXT,
    techniques TEXT,
    error TEXT,
    manual_score INTEGER,
    manual_verdict_correct INTEGER,
    manual_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_alert_id ON runs(alert_id);
CREATE INDEX IF NOT EXISTS idx_runs_model_id ON runs(model_id);
"""

DEFAULT_DB = "results/runs.db"


@contextmanager
def db_conn(path: str | Path = DEFAULT_DB):
    """Yield a SQLite connection with the schema applied. Auto-commits."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_runs(
    results: list[RunResult],
    alert: dict[str, Any],
    prompt_template: str,
    db_path: str | Path = DEFAULT_DB,
) -> None:
    with db_conn(db_path) as conn:
        for r in results:
            conn.execute(
                """INSERT INTO runs (
                    run_id, alert_id, alert_json, prompt_template,
                    model_id, model_tag, response,
                    prompt_tokens, completion_tokens,
                    total_duration_ms, load_duration_ms, eval_duration_ms,
                    tokens_per_second, wall_clock_ms,
                    verdict, confidence, techniques, error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    r.run_id, r.alert_id,
                    json.dumps(alert, ensure_ascii=False),
                    prompt_template,
                    r.model_id, r.model_tag, r.response,
                    r.prompt_tokens, r.completion_tokens,
                    r.total_duration_ms, r.load_duration_ms, r.eval_duration_ms,
                    r.tokens_per_second, r.wall_clock_ms,
                    r.verdict, r.confidence, json.dumps(r.techniques), r.error,
                ),
            )


def update_score(
    row_id: int,
    *,
    score: int | None = None,
    verdict_correct: int | None = None,
    notes: str | None = None,
    db_path: str | Path = DEFAULT_DB,
) -> None:
    fields: list[str] = []
    values: list[Any] = []
    if score is not None:
        fields.append("manual_score = ?")
        values.append(score)
    if verdict_correct is not None:
        fields.append("manual_verdict_correct = ?")
        values.append(verdict_correct)
    if notes is not None:
        fields.append("manual_notes = ?")
        values.append(notes)
    if not fields:
        return
    values.append(row_id)
    with db_conn(db_path) as conn:
        conn.execute(
            f"UPDATE runs SET {', '.join(fields)} WHERE id = ?",
            values,
        )


def list_runs(db_path: str | Path = DEFAULT_DB, limit: int = 500) -> list[dict]:
    if not Path(db_path).exists():
        return []
    with db_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
