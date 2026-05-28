# cybersec-llm-bench

> Head-to-head benchmark for cybersecurity LLMs on SOC alerts, via Ollama.

[![CI](https://github.com/onuroktay14/turk-cybersec-llm-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/onuroktay14/turk-cybersec-llm-bench/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A small framework for running the **same SOC alert** through **multiple
cybersecurity-focused LLMs**, extracting structured triage output
(verdict, confidence, MITRE ATT&CK techniques), and scoring the results
side by side. Built around Ollama so any GGUF-compatible model works.

The default config ships with two cyber-focused Turkish-first models —
**Seneca** and **Titus v1.0** — plus an optional vanilla **Qwen3.6-35B-A3B**
control to isolate fine-tune contribution. Add any other model with a
three-line TOML entry.

---

## Why this exists

Choosing a backbone LLM for SOC triage is hard. Marketing numbers don't
tell you whether a model nails a `TP / HIGH` verdict on a real LSASS dump,
correctly flags a scheduled-task PowerShell as `FP`, or maps a Kerberoasting
burst to `T1558.003`. Latency claims don't account for cold-load time on
your actual GPU.

This benchmark answers those questions in a few minutes per alert, with
reproducible numbers you can put in a decision doc.

---

## Quick start

```bash
git clone https://github.com/onuroktay14/turk-cybersec-llm-bench
cd cybersec-llm-bench
pip install -e .

# Configure
cp config.example.toml config.toml
$EDITOR config.toml   # set base_url, pick your models

# Pull models on the Ollama host
ollama pull hf.co/AlicanKiraz0/Titus-CybersecurityLLM-v1.0-Q4_0-GGUF:Q4_0
ollama pull qwen3.6:35b-a3b   # optional control

# Run
cybersec-llm-bench --alert alerts/lsass_dump_tp.json
streamlit run app.py
```

---

## Features

- **Ollama-backed** — works with any model you can `ollama pull` (GGUF,
  Hugging Face Hub, custom builds).
- **Structured extraction** — Markdown-aware regex pulls
  `### Verdict`, `### Confidence`, and `T####` techniques out of each
  response.
- **Native timings** — surfaces Ollama's own `load_duration`,
  `eval_duration`, and computes tokens/sec separately so cold-load doesn't
  pollute steady-state numbers.
- **VRAM-aware sequencing** — `keep_alive=0` between calls so big models
  unload before the next one loads. Disable for snappy reruns when VRAM
  is comfortable.
- **SQLite history** — every run is persisted; manual scores layered on
  top; per-model aggregates over time.
- **Streamlit UI** — side-by-side responses, metrics table, manual scoring.
- **CLI** — same logic, scriptable for batch jobs.
- **5 labeled sample alerts** — LSASS dump (TP), legit scheduled
  PowerShell (FP), Cobalt Strike beacon (TP), Kerberoasting (TP), DNS
  tunnel (SUSPICIOUS).

---

## Default model lineup

| ID            | Model                                          | Size      | Source              | Notes                       |
|---------------|------------------------------------------------|-----------|---------------------|-----------------------------|
| `titus_q4_0`  | Titus v1.0 Q4_0 GGUF                           | ~19.7 GB  | Hugging Face        | Qwen3.6-35B-A3B + cyber LoRA |
| `seneca`      | Seneca q4_k_m                                  | ~4.7 GB   | Custom / private    | **You need your own GGUF**   |
| `qwen36_base` | Qwen3.6-35B-A3B (control, commented out)       | ~19.5 GB  | Ollama Hub          | Vanilla base for control     |

**Seneca is not on a public registry.** It's a Turkish-first cyber LLM
maintained outside this project. If you don't have it, either remove the
block from `config.toml` or swap in any other GGUF you have access to
(Foundation-Sec-8B, WhiteRabbitNeo, your own merge, etc.).

The Qwen3.6 control is the most important addition for anyone evaluating
Titus seriously — Titus = `Qwen3.6-35B-A3B + LoRA`. Without the vanilla
base in the comparison, you can't tell whether wins come from the fine-tune
or just from the larger base.

---

## Architecture

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Alert JSON   │───▶│ Prompt Template  │───▶│ Rendered Prompt  │
└──────────────┘    │ (Markdown + ph)  │    └────────┬─────────┘
                    └──────────────────┘             │
                                                     ▼
                                          ┌─────────────────────┐
                                          │  OllamaClient       │
                                          │  /api/generate × N  │
                                          └─────────┬───────────┘
                                                    │ per-model
                                                    ▼
                                          ┌─────────────────────┐
                                          │ Markdown extractor  │
                                          │ verdict / conf /    │
                                          │ MITRE techniques    │
                                          └─────────┬───────────┘
                                                    ▼
                                          ┌─────────────────────┐
                                          │ SQLite history      │
                                          │ + manual scoring    │
                                          └─────────────────────┘
```

---

## Sample CLI output

```
→ alert=evt-2026-0001 models=2 ollama=http://localhost:11434 sequential_unload=True

━━━━━━━━ titus_q4_0  (hf.co/AlicanKiraz0/Titus-CybersecurityLLM-v1.0-Q4_0-GGUF:Q4_0) ━━━━━━━━
  verdict=TP  confidence=HIGH  techniques=['T1003.001', 'T1055']
  tokens: in=687  out=312  t/s=41.2
  timing: wall=18420ms  load=11200ms  eval=7100ms

### Verdict
TP

### Confidence
HIGH

### Reasoning
rundll32.exe + comsvcs.dll MiniDump + lsass.exe (PID 716) target with
GrantedAccess 0x1410 is a classic LSASS credential-dump pattern...

━━━━━━━━ seneca  (seneca-cybersecurity:q4_k_m) ━━━━━━━━
  verdict=TP  confidence=HIGH  techniques=['T1003.001']
  tokens: in=687  out=204  t/s=89.4
  timing: wall=3850ms  load=1200ms  eval=2280ms
...

✓ saved 2 run(s) to results/runs.db
```

---

## Project layout

```
cybersec-llm-bench/
├── src/cybersec_llm_bench/
│   ├── __init__.py     # public API
│   ├── client.py       # OllamaClient
│   ├── config.py       # BenchConfig, ModelConfig
│   ├── extract.py      # verdict / confidence / MITRE extractors
│   ├── runner.py       # run_alert, RunResult, render_prompt
│   ├── storage.py      # SQLite persistence
│   └── cli.py          # cybersec-llm-bench CLI
├── app.py              # Streamlit UI
├── prompts/
│   ├── triage_v1_tr.md
│   └── triage_v1_en.md
├── alerts/             # labeled sample alerts (ground truth in JSON)
├── tests/              # pytest suite
├── pyproject.toml
├── config.example.toml
└── README.md
```

---

## VRAM guidance

| GPU         | Comfortable footprint | Notes                                           |
|-------------|-----------------------|-------------------------------------------------|
| 24 GB       | ≤ 20 GB single model  | Run Titus solo or with `sequential_unload`.    |
| 32 GB       | Titus + ~8B model     | Sequential unload still recommended under load. |
| 48 GB+      | Multiple co-resident  | Disable `sequential_unload` for faster reruns.  |

The first call to each model includes the cold-load cost. For real warm
latency, fire one throwaway request per model, then measure.

---

## Roadmap

- [ ] Batch mode (`--batch alerts/*.json` for overnight grading)
- [ ] LLM-as-judge auto-grader (pre-score with a stronger model before
  human review)
- [ ] Cold/warm latency split tracked separately in storage
- [ ] `nvidia-smi` sampling during eval for peak-VRAM measurement
- [ ] Prompt-injection regression set with expected refusal/`BENIGN`
- [ ] Concurrency stress (N parallel requests per model)
- [ ] Export to CSV / JSON for downstream analysis
- [ ] More public cyber LLMs in default config (Foundation-Sec-8B,
  WhiteRabbitNeo, ZySec-7B)

See [CONTRIBUTING.md](CONTRIBUTING.md) to send a PR for any of these.

---

## License

[Apache 2.0](LICENSE). Compatible with the licenses of the cyber LLMs
this benchmark commonly targets (Titus, Qwen3.6, Foundation-Sec).

This is not affiliated with the developers of Seneca, Titus, Qwen, or
any other model evaluated here. Trademarks belong to their respective
owners.
