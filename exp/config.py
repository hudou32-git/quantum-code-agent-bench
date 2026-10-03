"""Central paths and protocol constants. Everything resolves from this file."""

from __future__ import annotations

import os
from pathlib import Path

PKG = Path(__file__).resolve().parent  # submit/exp
ROOT = PKG.parent  # submit/

# ── .env ──
ENV_FILE = ROOT / ".env"


def _dotenv_get(key: str) -> str:
    """Process env first, then the submit-root .env (same precedence as override=False)."""
    v = (os.getenv(key) or "").strip()
    if v:
        return v
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith(f"{key}=") or s.startswith(f"{key} ="):
                return s.split("=", 1)[1].strip().strip("'\"")
    return ""


# ── LLM identity: read from .env, never hardcoded (user directive, 2026-09-16) ──
MODEL = _dotenv_get("DEEPSEEK_MODEL")
if not MODEL:
    raise RuntimeError("DEEPSEEK_MODEL missing: set it in submit/.env")
# v6 protocol window (user directive, 2026-09-17): decoding temperature 0.6
# package-wide — baseline arms, loop and EQPA all decode at this value.
# Historical T=0 rows (v5 and earlier) are frozen under their own tags; do not mix.
TEMPERATURE = 0.6
# Output budget (user directive, 2026-09-18): raised 4096 -> 40960 so naturally
# long generations finish instead of being cut at finish_reason=length (~1-3% of
# shots at 4096). thinking stays disabled package-wide (README discipline 10) —
# if it were ever enabled, reasoning would consume this budget first.
# Historical rows ran at 4096: a protocol dimension, never mix budgets in one tag.
MAX_TOKENS = 40960

# ── generation_guard (user resolution, 2026-09-20) ──
# EXECUTION-LEVEL EARLY ABORT, not a decoding-strategy change: detect the
# degenerate block-repetition loop (exp/common/repeat_guard.py, rep-v1), abort
# the stream early, record evidence. It does NOT retry, resample, or extend any
# sampling budget; a guard-stopped text flows into extraction/grading exactly
# as an uncut draw would and is failed by the scorer per existing rules.
# finish_reason "client_repeat_stop" != "length", so the frozen P0-7
# length_retry rule can never fire on a guard stop. Official path
# (make_official_client) enforces on tools=None text calls; direct
# DeepSeekClient construction (EQPA) runs detect-only — never aborts.
GENERATION_GUARD = {
    "enabled": True,
    "detector": "rep-v1",
    "mode_official": "enforce",  # stream + early abort on text calls
    "mode_direct": "detect",     # post-hoc flag only (EQPA), never aborts
}
LLM_TIMEOUT = 600.0
LLM_CONCURRENCY_LIMIT = 128
JOB_WORKERS = 64
JOB_WORKERS_MAX = 128

# ── QHE benchmark (bench/qhe) ──
QHE_ROOT = ROOT / "bench" / "qhe"
QHE_DATASET_DIR = QHE_ROOT / "dataset"
QHE_SEALED_DIR = QHE_ROOT / "sealed"
QHE_EVAL_DIR = QHE_ROOT / "eval"
EVAL_BLIND = QHE_EVAL_DIR / "eval_blind.py"

# ── QB+ benchmark (bench/qbplus) ──
QBPLUS_ROOT = ROOT / "bench" / "qbplus"
QBPLUS_DATASET_DIR = QBPLUS_ROOT / "dataset"
QBPLUS_PROBLEMS = QBPLUS_DATASET_DIR / "sealed" / "problems_full.json"
# e8: cirq suite migrated alongside qiskit (task ids identical, 42/42)
QBPLUS_PROBLEMS_CIRQ = QBPLUS_DATASET_DIR / "sealed" / "problems_cirq_full.json"
# e9: pennylane suite migrated alongside qiskit/cirq (task ids identical, 42/42)
QBPLUS_PROBLEMS_PENNYLANE = QBPLUS_DATASET_DIR / "sealed" / "problems_pennylane_full.json"
QBPLUS_CANONICAL = QBPLUS_ROOT / "canonical_solutions.json"
EVAL_QBPLUS = PKG / "common" / "eval_qbplus.py"

# ── grader runtimes ──
# QHE main-table grading (and EQPA Shell sandbox source env): system python3.8
# with qiskit 1.2.4. QB+ grading spawns this interpreter explicitly.
QHE_PYTHON = Path("/root/anaconda3/envs/qhe/bin/python")
QHE_ENV = Path("/root/anaconda3/envs/qhe")

# ── QB+ official grading constants (from the original quanbench-plus pin) ──
QBPLUS_SHOTS = 10000      # raised from the official 1000: canonical_output is a
                          # 1000-shot empirical table and 1000-shot KL has a noise
                          # floor above the 0.05 threshold for wide outputs (04/08)
GRADE_TIMEOUT = 90.0
KL_THRESHOLD = 0.05

# ── baseline decoding / dev split ──
BASELINE_DEV_CASES = (
    "qiskitHumanEval/15",
    "qiskitHumanEval/21",
    "qiskitHumanEval/30",
    "qiskitHumanEval/104",
    "qiskitHumanEval/121",
)
QBPLUS_SMOKE_CASES = ("01", "16", "37")

# ── EQPA runtime state (rebuilt on first run; never versioned) ──
EQPA_RUNTIME = PKG / "eqpa" / "runtime"
EQPA_JAIL_ROOT = EQPA_RUNTIME / "jail"
EQPA_CANARY_STATE = EQPA_RUNTIME / "canaries.json"
EQPA_OVERLAY_ROOT = EQPA_RUNTIME / "python_overlay"

# EQPA Shell sandbox budget
REPL_TIMEOUT = 12.0
REPL_MAX_BYTES = 4000


def arm_results(arm: str) -> Path:
    """Per-arm results directory: exp/<arm>/results."""
    return PKG / arm / "results"
