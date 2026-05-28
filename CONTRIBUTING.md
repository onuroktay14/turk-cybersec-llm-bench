# Contributing to cybersec-llm-bench

Thanks for thinking about contributing. The benchmark grows in value with
every additional model, prompt variant, and well-labeled alert.

## Quick dev setup

```bash
git clone https://github.com/<your-fork>/cybersec-llm-bench
cd cybersec-llm-bench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Lint + test
ruff check src tests
pytest -v
```

You don't need Ollama running for the unit tests — the network layer is
mocked out of the way. You only need Ollama when running the actual
benchmark or smoke-testing the CLI/UI end-to-end.

## How to add a model

Edit `config.toml` (your local one — `config.example.toml` is shipped):

```toml
[[models]]
id           = "my_cyber_llm"
display_name = "My Cyber LLM (Q4_K_M)"
ollama_tag   = "hf.co/<org>/<repo>:Q4_K_M"
notes        = "Short note: base model, size, language focus"
```

Then pull it on the Ollama host:

```bash
ollama pull hf.co/<org>/<repo>:Q4_K_M
```

If you think a model deserves a permanent slot in `config.example.toml`,
open a PR. Criteria:

- Public Hugging Face / Ollama Hub availability (no closed weights).
- Either security-focused fine-tune, or a strong general model frequently
  used as a baseline for cyber tasks.
- License compatible with users running it commercially.

## How to add a prompt template

1. Place a new file in `prompts/` (e.g. `prompts/triage_v2_en.md`).
2. Use `{alert_json}` as the placeholder where the alert JSON should land.
3. Keep the same Markdown output schema (`### Verdict`, `### Confidence`,
   `### MITRE ATT&CK`, etc.) so the extractor still works. If you change
   the schema, update `src/cybersec_llm_bench/extract.py` and its tests.

## How to add an alert

Drop a new `.json` file in `alerts/`. Required fields:

```json
{
  "alert_id": "evt-YYYY-NNNN",
  "timestamp": "ISO-8601",
  "source": "siem-or-sensor-name",
  "expected_verdict": "TP | FP | BENIGN | SUSPICIOUS",
  "expected_confidence": "LOW | MEDIUM | HIGH",
  "expected_techniques": ["T1234"],
  "rule": { "id": "...", "name": "...", "mitre": ["..."] }
}
```

The `expected_*` fields are the ground-truth labels used to grade models
later. Pick scenarios that stress real triage decisions — clearly malicious
TPs, plausible-looking FPs (legit admin work that scares an analyst), edge
cases, novel TTPs, etc.

Anonymize anything that could identify a real organization, person, or
incident. Use generic hostnames (`WS-FIN-04`), placeholder domains
(`corp.example.local`), and made-up IPs in private RFC1918 ranges.

Add a test entry in `tests/test_runner.py::test_sample_alerts_are_valid_json`
runs against every alert in the folder automatically — no per-alert test
needed.

## How to extend the extractor

Add a new field (e.g. `severity`) to `src/cybersec_llm_bench/extract.py`:

```python
_SEVERITY_RE = re.compile(r"###\s*Severity\s*\n+\s*([^\n]+)", re.IGNORECASE)

def extract_severity(text: str) -> str | None:
    ...
```

Then:

1. Expose it in `src/cybersec_llm_bench/__init__.py`.
2. Add it to `RunResult` in `runner.py`.
3. Add a column to the schema in `storage.py` and to the inserts.
4. Display it in `app.py` and `cli.py`.
5. Add tests in `tests/test_extract.py`.

## Code style

- Ruff handles lint + import sort. Run `ruff check src tests` and
  `ruff format src tests` before submitting.
- Type-annotate new public APIs. Avoid `Any` when a concrete type fits.
- Tests are required for new logic (extractor rules, storage paths,
  config parsing). UI changes don't need tests.

## Commit messages

Plain imperative subject, body if needed:

```
add foundation-sec-8b to default config

Default config now includes FoundationAI's Foundation-Sec-8B alongside
Titus and Qwen3.6, giving a third public cyber-LLM baseline.
```

## Reporting bugs

Open an issue with: the model tag that misbehaved, the alert JSON, the
prompt template, the (full) response, and what you expected. The more we
can reproduce, the faster it gets fixed.
