"""Streamlit UI for cybersec-llm-bench.

Run from the repo root after `pip install -e .`:

    streamlit run app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from cybersec_llm_bench import (
    BenchConfig,
    OllamaClient,
    list_runs,
    run_alert,
    save_runs,
    update_score,
)

st.set_page_config(page_title="cybersec-llm-bench", layout="wide")
st.title("cybersec-llm-bench")
st.caption("Head-to-head benchmark for cybersecurity LLMs · Ollama-backed")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Configuration")
    config_path = st.text_input("Config file", "config.toml")
    try:
        cfg = BenchConfig.load(config_path)
    except Exception as e:
        st.error(f"Config error: {e}")
        st.info("Copy `config.example.toml` to `config.toml` and edit.")
        st.stop()

    st.code(cfg.ollama_base_url, language="text")

    selected_ids = st.multiselect(
        "Models to compare",
        [m.id for m in cfg.models],
        default=[m.id for m in cfg.models],
    )
    selected_models = [m for m in cfg.models if m.id in selected_ids]

    temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.1)
    num_ctx = st.select_slider(
        "Context size", options=[2048, 4096, 8192, 16384, 32768], value=8192
    )
    sequential_unload = st.checkbox(
        "Unload model between calls",
        value=True,
        help="Required when total model footprint exceeds available VRAM.",
    )

    st.divider()
    st.caption(
        "Tip: do one warm-up run per model before measuring latency. "
        "First call always pays the cold-load cost."
    )

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_run, tab_history = st.tabs(["Run Comparison", "History & Stats"])

with tab_run:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Alert")
        sample_alert = Path("alerts/lsass_dump_tp.json")
        alert_text = st.text_area(
            "Alert JSON",
            sample_alert.read_text(encoding="utf-8") if sample_alert.exists() else "{}",
            height=380,
            key="alert_input",
        )

    with c2:
        st.subheader("Prompt Template")
        sample_prompt = Path("prompts/triage_v1_tr.md")
        prompt_text = st.text_area(
            "Markdown prompt — use {alert_json} placeholder",
            sample_prompt.read_text(encoding="utf-8") if sample_prompt.exists() else "",
            height=380,
            key="prompt_input",
        )

    if st.button(
        "Run Comparison", type="primary",
        disabled=not selected_models, use_container_width=True,
    ):
        try:
            alert_obj = json.loads(alert_text)
        except json.JSONDecodeError as e:
            st.error(f"Invalid alert JSON: {e}")
            st.stop()
        client = OllamaClient(cfg.ollama_base_url)
        with st.spinner(f"Running on {len(selected_models)} model(s)…"):
            results = run_alert(
                client, selected_models, alert_obj, prompt_text,
                sequential_unload=sequential_unload,
                temperature=temperature,
                num_ctx=num_ctx,
            )
        save_runs(results, alert_obj, prompt_text)
        st.session_state["last_results"] = results
        st.success(f"Done — {len(results)} run(s) saved")

    if "last_results" in st.session_state:
        results = st.session_state["last_results"]

        st.subheader("Metrics")
        df = pd.DataFrame([
            {
                "Model": r.model_id,
                "Verdict": r.verdict or "—",
                "Conf": r.confidence or "—",
                "MITRE": ", ".join(r.techniques) or "—",
                "In tok": r.prompt_tokens,
                "Out tok": r.completion_tokens,
                "t/s": round(r.tokens_per_second, 1),
                "Eval (ms)": round(r.eval_duration_ms),
                "Load (ms)": round(r.load_duration_ms),
                "Wall (ms)": round(r.wall_clock_ms),
                "Error": r.error or "",
            }
            for r in results
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Responses")
        cols = st.columns(len(results))
        for col, r in zip(cols, results):
            with col:
                st.markdown(f"#### {r.model_id}")
                st.caption(r.model_tag)
                if r.error:
                    st.error(r.error)
                else:
                    st.markdown(r.response)

with tab_history:
    runs = list_runs()
    if not runs:
        st.info("No runs yet. Go to the Run Comparison tab.")
    else:
        df = pd.DataFrame(runs)

        st.subheader(f"Per-model aggregate ({len(df)} total rows)")
        agg = df.groupby("model_id").agg(
            runs=("id", "count"),
            avg_tps=("tokens_per_second", "mean"),
            avg_eval_ms=("eval_duration_ms", "mean"),
            avg_wall_ms=("wall_clock_ms", "mean"),
            avg_score=("manual_score", "mean"),
            verdict_acc=("manual_verdict_correct", "mean"),
        ).round(2)
        st.dataframe(agg, use_container_width=True)

        st.divider()
        st.subheader("Latest run group — score it")
        latest_run_id = df["run_id"].iloc[0]
        latest = df[df["run_id"] == latest_run_id]
        st.caption(
            f"run_id: `{latest_run_id}`  ·  alert: `{latest['alert_id'].iloc[0]}`"
        )

        for _, row in latest.iterrows():
            verdict_disp = row["verdict"] or "—"
            with st.expander(
                f"{row['model_id']}  —  verdict: {verdict_disp}  "
                f"·  t/s: {row['tokens_per_second']:.1f}"
            ):
                st.markdown(row["response"][:6000])
                a, b, c = st.columns([1, 1, 2])
                with a:
                    score = st.slider(
                        "Quality 1–5", 1, 5,
                        int(row["manual_score"]) if row["manual_score"] else 3,
                        key=f"score_{row['id']}",
                    )
                with b:
                    mvc = row["manual_verdict_correct"]
                    default_idx = 0 if mvc is None else (1 if mvc == 1 else 2)
                    correct = st.radio(
                        "Verdict correct?",
                        ["unset", "yes", "no"],
                        index=default_idx,
                        key=f"correct_{row['id']}",
                    )
                with c:
                    notes = st.text_area(
                        "Notes", row["manual_notes"] or "",
                        key=f"notes_{row['id']}", height=80,
                    )
                if st.button("Save score", key=f"save_{row['id']}"):
                    update_score(
                        int(row["id"]),
                        score=score,
                        verdict_correct=(
                            1 if correct == "yes"
                            else 0 if correct == "no"
                            else None
                        ),
                        notes=notes,
                    )
                    st.success("Saved")
                    st.rerun()

        st.divider()
        st.subheader("Raw runs (latest 50)")
        show_cols = [
            "created_at", "model_id", "alert_id", "verdict", "confidence",
            "tokens_per_second", "eval_duration_ms", "wall_clock_ms",
            "manual_score", "manual_verdict_correct",
        ]
        st.dataframe(
            df[show_cols].head(50),
            use_container_width=True, hide_index=True,
        )
