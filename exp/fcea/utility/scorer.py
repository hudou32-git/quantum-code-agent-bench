"""FCEA failure-context scorer.

Classifies the OBSERVED failure feedback into a utility-prior context
(Framework / Semantic / Runtime / NoSubmit / Other). Rules are the ones frozen
by the RQ2 analysis (analysis/rq2_evidence_utility/analyze.py::classify_failure)
so runtime routing matches the prior's construction.

This is an observation label only. The field name in traces is
`failure_context` — never `root_cause`: an AssertionError means the observed
failure is semantic-style, NOT that the underlying bug is algorithmic.
"""
from __future__ import annotations

import re

CONTEXTS = ("Framework", "Semantic", "Runtime", "NoSubmit", "Other")

_NO_SUBMIT_RE = re.compile(r"no official submit", re.I)

_FRAMEWORK_PATTERNS = [
    (r"ModuleNotFoundError|ImportError|cannot import name", 0.9),
    (r"unexpected keyword argument|missing \d+ required positional|takes? \d+ (?:positional )?arguments? but", 0.95),
    (r"AttributeError|has no attribute|has no member", 0.9),
    (r"\bTypeError\b", 0.85),
]
_SEMANTIC_PATTERNS = [
    (r"KLMismatch|KL divergence|KL=", 0.98),
    (r"\bAssertionError\b|\bassert\b", 0.85),
    (r"distribution .*(?:match|incorrect|expected)|incorrect output", 0.7),
]
_RUNTIME_PATTERNS = [
    (r"Execution timeout|Timed?\s*out|timeout expired", 0.95),
    (r"QiskitError|CircuitError|ValueError|KeyError|NameError|IndexError|ZeroDivisionError|RuntimeError|MemoryError|FileNotFoundError", 0.8),
]

_EXC_TYPE_MAP = {
    "AssertionError": "Semantic",
    "KLMismatch": "Semantic",
    "TypeError": "Framework",
    "AttributeError": "Framework",
    "ImportError": "Framework",
    "ModuleNotFoundError": "Framework",
    "ValueError": "Runtime",
    "QiskitError": "Runtime",
    "CircuitError": "Runtime",
    "KeyError": "Runtime",
    "NameError": "Runtime",
    "IndexError": "Runtime",
    "ZeroDivisionError": "Runtime",
    "RuntimeError": "Runtime",
    "MemoryError": "Runtime",
    "FileNotFoundError": "Runtime",
}


def classify_failure(message: str) -> dict:
    """Return {failure_context, confidence}. Observation label, not root cause."""
    m = (message or "").strip()
    if not m:
        return {"failure_context": "Other", "confidence": 0.2}
    if _NO_SUBMIT_RE.search(m):
        return {"failure_context": "NoSubmit", "confidence": 1.0}
    exc = None
    for line in reversed([l for l in m.splitlines() if l.strip()][-4:]):
        mm = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*(?:Error|Mismatch)\b", line)
        if mm:
            exc = mm.group(1).split(".")[-1]
            break
    if exc == "Timeout":
        exc = "Runtime"
    if exc == "Execution":  # "Execution timeout (120.0s)"
        return {"failure_context": "Runtime", "confidence": 0.95}
    if exc in _EXC_TYPE_MAP:
        return {"failure_context": _EXC_TYPE_MAP[exc], "confidence": 0.95}
    for pat, conf in _SEMANTIC_PATTERNS:
        if re.search(pat, m, re.I):
            return {"failure_context": "Semantic", "confidence": conf}
    for pat, conf in _FRAMEWORK_PATTERNS:
        if re.search(pat, m, re.I):
            return {"failure_context": "Framework", "confidence": conf}
    for pat, conf in _RUNTIME_PATTERNS:
        if re.search(pat, m, re.I):
            return {"failure_context": "Runtime", "confidence": conf}
    return {"failure_context": "Other", "confidence": 0.2}
