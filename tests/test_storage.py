"""Tests for the SQLite storage layer."""
from __future__ import annotations

from pathlib import Path

import pytest

from cybersec_llm_bench.runner import RunResult
from cybersec_llm_bench.storage import list_runs, save_runs, update_score


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_runs.db"


def _make_result(model_id: str = "seneca", verdict: str = "TP") -> RunResult:
    return RunResult(
        run_id="test-run-1",
        alert_id="evt-test-001",
        model_id=model_id,
        model_tag=f"{model_id}:latest",
        response=f"### Verdict\n{verdict}\n",
        prompt_tokens=512,
        completion_tokens=180,
        total_duration_ms=4200.0,
        load_duration_ms=1100.0,
        eval_duration_ms=2900.0,
        tokens_per_second=62.1,
        wall_clock_ms=4250.0,
        verdict=verdict,
        confidence="HIGH",
        techniques=["T1003.001", "T1059"],
    )


def test_save_and_list_runs(tmp_db: Path) -> None:
    alert = {"alert_id": "evt-test-001", "rule": {"name": "test"}}
    save_runs([_make_result()], alert, "prompt text", db_path=tmp_db)

    rows = list_runs(db_path=tmp_db)
    assert len(rows) == 1
    assert rows[0]["model_id"] == "seneca"
    assert rows[0]["verdict"] == "TP"
    assert rows[0]["tokens_per_second"] == pytest.approx(62.1)
    assert '"T1003.001"' in rows[0]["techniques"]


def test_list_runs_missing_db_returns_empty(tmp_path: Path) -> None:
    assert list_runs(db_path=tmp_path / "does-not-exist.db") == []


def test_multiple_models_one_alert(tmp_db: Path) -> None:
    alert = {"alert_id": "evt-test-002"}
    results = [
        _make_result(model_id="seneca", verdict="TP"),
        _make_result(model_id="titus_q4_0", verdict="FP"),
    ]
    save_runs(results, alert, "prompt", db_path=tmp_db)

    rows = list_runs(db_path=tmp_db)
    assert len(rows) == 2
    by_model = {r["model_id"]: r for r in rows}
    assert by_model["seneca"]["verdict"] == "TP"
    assert by_model["titus_q4_0"]["verdict"] == "FP"


def test_update_score(tmp_db: Path) -> None:
    save_runs([_make_result()], {"alert_id": "x"}, "p", db_path=tmp_db)
    row_id = list_runs(db_path=tmp_db)[0]["id"]

    update_score(row_id, score=5, verdict_correct=1,
                 notes="Caught Mimikatz pattern", db_path=tmp_db)

    row = list_runs(db_path=tmp_db)[0]
    assert row["manual_score"] == 5
    assert row["manual_verdict_correct"] == 1
    assert "Mimikatz" in row["manual_notes"]


def test_update_score_partial(tmp_db: Path) -> None:
    """Partial updates should only touch the fields provided."""
    save_runs([_make_result()], {"alert_id": "x"}, "p", db_path=tmp_db)
    row_id = list_runs(db_path=tmp_db)[0]["id"]

    update_score(row_id, score=3, db_path=tmp_db)
    update_score(row_id, notes="Reviewed", db_path=tmp_db)

    row = list_runs(db_path=tmp_db)[0]
    assert row["manual_score"] == 3
    assert row["manual_notes"] == "Reviewed"
    assert row["manual_verdict_correct"] is None
