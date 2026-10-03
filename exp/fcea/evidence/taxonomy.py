"""FCEA evidence taxonomy: category definitions and output classification.

Category rules are the ones frozen by the RQ2 analysis
(analysis/rq2_evidence_utility/analyze.py) so that "actual evidence type" of a
probe is scored with the same classifier that produced the utility prior.
BatchProbe query kinds (api/env/runtime/behavior) map to categories as the
*requested* type; the output classifier supplies the *actual* type.
"""
from __future__ import annotations

import re

CATEGORIES = ("E1", "E2", "E3", "E4")

CATEGORY_NAMES = {
    "E1": "Environment Evidence (API signatures, attributes, versions, imports, source)",
    "E2": "Execution Evidence (running candidate/minimal repro, tracebacks, timeouts)",
    "E3": "Behavioral Evidence (self-designed experiments: statevector, counts, toy circuits)",
    "E4": "Context Evidence (re-reading files, prior code, task text)",
}

# BatchProbe kind label (model-facing) -> utility category
KIND_TO_CATEGORY = {
    "api": "E1",
    "env": "E1",
    "runtime": "E2",
    "behavior": "E3",
}

# ---- output classifier (ported from analysis/rq2_evidence_utility/analyze.py) ----
_E2_TRACEBACK = "Traceback (most recent call last)"
_E1_SIG_RE = re.compile(r"\([^)]*\)\s*->\s*|Signature\(|Help on |^\s*def \w+\(", re.M)
_E1_VERSION_RE = re.compile(r"^\s*\d+\.\d+(?:\.\d+)?\s*$")
_E1_SOURCE_RE = re.compile(r"raise \w+|return [^\n]+|@\w+|import \w+", re.M)
_E3_SIM_RE = re.compile(
    r"Statevector\(|DensityMatrix\(|Operator\(|Probability|probabilit|counts|"
    r"\{'[01]+' ?:|\[\['[01]+'|┌|q_0|amplitude|\[0\.\d+[\d\s.,e+\-]*\]|"
    r"\[\[\d+\.?\+?0?\.?j|SparsePauliOp\(|PrimitiveResult\(|SamplerPubResult|BitArray\(|DataBin\(", re.I)
_E1_CTOR_SIG_RE = re.compile(r"^\((?:self\b|[a-z_]+: )", re.M)
_E1_TYPE_RE = re.compile(r"<class 'qiskit")
_E1_DIR_RE = re.compile(r"^\['[A-Za-z_][A-Za-z0-9_]*'(?:, ?'[A-Za-z_][A-Za-z0-9_]*')+,?\]?\s*$", re.M)
_E1_PATH_RE = re.compile(r"site-packages|/opt/qhe/lib")
_E2_STATUS_RE = re.compile(r"^\s*(status: (timeout|error|nonzero)|stderr:)", re.M | re.I)
_E2_RAISED_ERR_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_.]*(?:Error|Mismatch)\b[^\n]*$", re.M)
_E1_IMPORT_ERR_RE = re.compile(r"ModuleNotFoundError|ImportError|cannot import name")
_E4_FILE_RE = re.compile(r"attempt_\d+\.py|^prompt\.txt$|\.py\s*$|^total \d+", re.M)
_E4_PROMPT_ECHO_RE = re.compile(
    r"You must implement|Your task|function named|implement a function|given tolerance", re.I)


def classify_evidence_output(text: str) -> tuple[str, float]:
    """Classify one probe output into a category. Returns (category, confidence)."""
    t = text or ""
    if _E2_TRACEBACK in t:
        return "E2", 0.95
    if _E1_IMPORT_ERR_RE.search(t):
        return "E1", 0.85
    if _E2_STATUS_RE.search(t):
        return "E2", 0.6
    signals = 0
    if _E1_SIG_RE.search(t) or _E1_CTOR_SIG_RE.search(t) or _E1_TYPE_RE.search(t) or _E1_DIR_RE.search(t):
        signals += 1
    if _E1_VERSION_RE.match(t.strip()):
        signals += 1
    if _E1_PATH_RE.search(t):
        signals += 1
    if _E1_SOURCE_RE.search(t) and len(t) > 120 and not _E2_RAISED_ERR_RE.search(t):
        signals += 1
    if signals:
        return "E1", 0.75 if signals == 1 else 0.85
    if _E3_SIM_RE.search(t):
        return "E3", 0.75
    if _E2_RAISED_ERR_RE.search(t):
        return "E2", 0.6
    if _E4_FILE_RE.search(t) or _E4_PROMPT_ECHO_RE.search(t):
        return "E4", 0.65
    return "Unknown", 0.3
