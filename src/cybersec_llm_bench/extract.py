"""Structured extraction from Markdown-formatted LLM responses."""
from __future__ import annotations

import re

VERDICT_LABELS = ("TP", "FP", "BENIGN", "SUSPICIOUS")
CONFIDENCE_LABELS = ("HIGH", "MEDIUM", "LOW")

_MITRE_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")


def _extract_labeled(text: str, word: str, labels: tuple[str, ...]) -> str | None:
    head = r"(?:#{1,6}|\*\*)?\s*" + word + r"\s*(?:\*\*)?\s*:?[ \t]*"
    candidates: list[str] = []
    m = re.search(head + r"([^\n]*)", text, re.IGNORECASE)
    if m and m.group(1).strip():
        candidates.append(m.group(1))
    m2 = re.search(head + r"\n+\s*([^\n]+)", text, re.IGNORECASE)
    if m2:
        candidates.append(m2.group(1))
    for c in candidates:
        cu = c.strip().upper()
        for label in labels:
            if label in cu:
                return label
    return None


def extract_verdict(text: str) -> str | None:
    return _extract_labeled(text, "Verdict", VERDICT_LABELS)


def extract_confidence(text: str) -> str | None:
    return _extract_labeled(text, "Confidence", CONFIDENCE_LABELS)


def extract_techniques(text: str) -> list[str]:
    return sorted(set(_MITRE_RE.findall(text)))
