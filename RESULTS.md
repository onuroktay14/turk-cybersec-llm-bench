# Benchmark Results

**Tested by Onur OKTAY - Senior Cyber Security Expert**
**Run date:** 2026-05-28
**Hardware:** NVIDIA Tesla V100-SXM2-32GB
**Runtime:** Ollama 0.20.4
**Prompt:** `prompts/triage_v1_tr.md` generic Turkish SOC triage, identical for every model
**Sampling:** temperature 0.0, num_ctx 8192, sequential model unload
**Dataset:** 5 labeled SOC alerts (`alerts/*.json`); ground truth in each file's `expected_verdict`

All models run **bare** — no system prompt, no per-model tuning. Each model
receives only the shared triage prompt, so differences reflect the model
itself, not the harness or any product-specific scaffolding.

## Models

| ID | Model | Base | Size | Source |
|----|-------|------|------|--------|
| `seneca` | Seneca-Cybersecurity-LLM Q4_K_M | Llama-3 8B | 4.9 GB | `AlicanKiraz0/Seneca-Cybersecurity-LLM-Q4_K_M-GGUF` |
| `titus` | Titus-CybersecurityLLM v1.0 Q4_0 | Qwen3.6-35B-A3B | 19 GB | `AlicanKiraz0/Titus-CybersecurityLLM-v1.0-Q4_0-GGUF` |
| `qwen36_base` | Qwen3.6-35B-A3B (control) | — | 23 GB | `qwen3.6:35b-a3b` |

`qwen36_base` is the vanilla base model that Titus is fine-tuned from, included
as a control to isolate the fine-tune's contribution from the base capability.

## Summary

| Model | Verdict accuracy | Avg tokens/s | Avg wall (s) | Errors |
|-------|:---:|:---:|:---:|:---:|
| `qwen36_base` | **5/5** | 64.1 | 68.6 | 0 |
| `seneca` | 4/5 | 113.0 | 10.7 | 0 |
| `titus` | 0/5 | — | — | 5 |

## Verdict matrix

| Alert | Expected | `seneca` | `qwen36_base` | `titus` |
|-------|:---:|:---:|:---:|:---:|
| Suspicious LSASS access | TP | TP ✓ | TP ✓ | ERROR |
| Periodic C2 beacon | TP | TP ✓ | TP ✓ | ERROR |
| Kerberoasting burst | TP | TP ✓ | TP ✓ | ERROR |
| DNS tunneling | SUSPICIOUS | SUSPICIOUS ✓ | SUSPICIOUS ✓ | ERROR |
| Scheduled PowerShell | FP | undecided ✗ | FP ✓ | ERROR |

## Key findings

### 1. Qwen3.6-35B-A3B (control) is the accuracy leader — but slow

5/5 correct verdicts, clean MITRE mapping (e.g. only `T1558.003` on the
Kerberoasting case, no spurious techniques), and the deepest context-aware
reasoning across the set. The trade-off is latency: ~60-83 s per alert with
long outputs (2,800-4,300 completion tokens).

### 2. Seneca (8B) is fast but shallow

~6-8× faster in wall-clock (7-13 s, ~113 t/s) but pays for it on quality:

- **MITRE hallucinations** — on the Kerberoasting case it invented unrelated
  `T1001.001` and `T1012`; on the DNS-exfil case it mislabeled `T1048.003` as
  "Remote File Monitoring" (the technique is *Exfiltration Over Alternative
  Protocol*, sub-technique DNS).
- **Prompt echoing** — on the LSASS case it repeated part of the prompt
  instructions back instead of answering cleanly.
- **Indecision on the FP** — see finding 3.

### 3. The FP case is the real maturity test

`powershell_scheduled_fp` looks alarming on the surface (encoded PowerShell,
`-ExecutionPolicy Bypass`) but is contextually benign: ScheduledTask parent,
valid Microsoft signature, approved change ticket `CHG-2025-1142`, weekly
recurring pattern. **Qwen3.6 read the context and returned a confident FP**,
even proposing an allowlist policy. **Seneca was undecided** — it emitted
"True Positive | False Positive" and "LOW | HIGH" without committing to either.
This is the sharpest divider between a small/older model and a large/newer one:
the ability to weigh the context underneath the alarm rather than reacting to
surface indicators.

### 4. Titus v1.0 Q4_0 GGUF fails to load (broken quantization)

Titus returned HTTP 500 on every alert. Root cause from the Ollama runner log:

```
architecture=qwen35moe  file_type=Q4_0  name="Titus CybersecurityLLM v1.0"  num_tensors=733
llm load error: failed to initialize model: qwen3next: layer 40 missing attn_qkv/attn_gate projections
```

For comparison, the vanilla Qwen3.6-35B-A3B in the **same runtime** loads with
`num_tensors=1194`. The Titus GGUF ships only **733 tensors** — the attention
projection tensors (`attn_qkv` / `attn_gate`) for a subset of layers are absent
from the file. This is a GGUF-conversion defect specific to Qwen3.6-35B-A3B's
hybrid attention architecture (interleaved Gated DeltaNet + Gated Attention
layers), not an Ollama or parameter problem — the same runtime runs the base
model flawlessly.

**Implication:** Titus's underlying capability is likely strong — the base it
is fine-tuned from scored 5/5 here — but the published Q4_0 GGUF is unusable on
current Ollama. A re-conversion (or a `Q4_K_M` build) from the merged weights
is required to evaluate Titus on its merits.

## Reproduce

```bash
pip install -e .
cp config.example.toml config.toml      # set base_url and model tags
for a in alerts/*.json; do
  cybersec-llm-bench --alert "$a" --prompt prompts/triage_v1_tr.md
done
```

## Caveats

- Single run per (alert, model) at temperature 0; no variance/repeatability
  analysis yet.
- 5 alerts is a smoke-sized set — results are directional, not statistically
  conclusive.
- Reasoning-quality is described qualitatively above; only verdict accuracy is
  quantified as the headline metric.
- Seneca is a Llama-3 8B base while Qwen3.6 is 35B-A3B — the parameter-count
  asymmetry is large, so "Seneca vs Qwen3.6" is not apples-to-apples on size.
  The fair size-matched comparison (Seneca vs a correctly-packaged Titus) is
  blocked until a working Titus GGUF exists.
