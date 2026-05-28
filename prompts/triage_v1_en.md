# SOC Alert Triage — cybersec-llm-bench v1 (EN)

You are a Tier-2 SOC analyst. Review the SIEM alert below and **strictly follow the output format below**.

## Alert
```json
{alert_json}
```

## Output Format — Use these Markdown headers exactly

### Verdict
Single line. One of: `TP` | `FP` | `BENIGN` | `SUSPICIOUS`

### Confidence
Single line. One of: `LOW` | `MEDIUM` | `HIGH`

### Reasoning
2–4 sentences. Which indicators (process tree, command line, target process, access mask, parent–child relationship, network destination, etc.) support the verdict? Avoid generic statements — reference concrete fields from the alert.

### MITRE ATT&CK
Comma-separated technique IDs in `T1234` or `T1234.001` format. List all relevant ones. Write `N/A` if not applicable.

### Recommended Actions
1–3 concrete, actionable items. Avoid generic advice — specify host isolation, EDR auto-block, threat hunt query, IR escalation, etc.

### IOCs
JSON object: `{"ips": [...], "hashes": [...], "domains": [...], "users": [...]}`. Use `[]` for empty arrays; omit keys with no relevant values.

---

**Rules:**
- Do not deviate from the format. Each header must appear exactly as shown (`### Verdict`, `### Confidence`, etc.).
- Do not hallucinate in Reasoning — only reference fields present in the alert payload.
- If you don't know something, say so. Do not invent details.
