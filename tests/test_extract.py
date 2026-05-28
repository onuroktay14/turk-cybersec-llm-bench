"""Tests for response extraction."""
from __future__ import annotations

import pytest

from cybersec_llm_bench.extract import (
    extract_confidence,
    extract_techniques,
    extract_verdict,
)

# ---- Verdict ----

@pytest.mark.parametrize("text, expected", [
    ("### Verdict\nTP\n\n### Confidence\nHIGH", "TP"),
    ("### Verdict\nFP\n", "FP"),
    ("### Verdict\nBENIGN\n", "BENIGN"),
    ("### Verdict\nSUSPICIOUS - needs review\n", "SUSPICIOUS"),
    ("### verdict\ntp - looks like Mimikatz\n", "TP"),  # case-insensitive
    ("blah blah\n\n### Verdict\n   FP   \n", "FP"),     # leading whitespace
    ("no verdict header here", None),
    ("", None),
])
def test_extract_verdict(text: str, expected: str | None) -> None:
    assert extract_verdict(text) == expected


# ---- Confidence ----

@pytest.mark.parametrize("text, expected", [
    ("### Confidence\nHIGH\n", "HIGH"),
    ("### Confidence\nmedium\n", "MEDIUM"),
    ("### Confidence\nlow because limited telemetry\n", "LOW"),
    ("### Confidence\nVERY HIGH\n", "HIGH"),  # contains 'HIGH'
    ("no confidence", None),
])
def test_extract_confidence(text: str, expected: str | None) -> None:
    assert extract_confidence(text) == expected


# ---- MITRE techniques ----

def test_extract_techniques_basic() -> None:
    text = "### MITRE ATT&CK\nT1003.001, T1059, T1218.011"
    assert extract_techniques(text) == ["T1003.001", "T1059", "T1218.011"]


def test_extract_techniques_dedup_and_sort() -> None:
    text = "T1059 and also T1003.001, and T1059 again"
    assert extract_techniques(text) == ["T1003.001", "T1059"]


def test_extract_techniques_embedded_in_prose() -> None:
    text = "This matches T1110.003 password spraying and partially T1078.004 cloud accounts."
    assert extract_techniques(text) == ["T1078.004", "T1110.003"]


def test_extract_techniques_no_false_positives() -> None:
    # T123 is too short; T12345 too long; t1059 lowercase not matched
    text = "T123 T12345 t1059 nothing here"
    assert extract_techniques(text) == []


def test_extract_techniques_empty() -> None:
    assert extract_techniques("") == []
