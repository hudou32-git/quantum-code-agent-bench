"""Evidence-Efficient EQPA (Batch-EQPA) arm config.

Batch-EQPA keeps EQPA's model/protocol/official budget/grader/sandbox byte-for-
byte and changes ONE thing: the free-form per-command Shell tool is replaced by
BatchProbe — the agent submits up to MAX_QUERIES_PER_BATCH commands in a single
tool round and receives structured, clipped evidence back. Phases 2/3 add an
error→evidence-plan hint (--planning) and a same-error replanning notice
(--progress); both are feature-flagged OFF by default so the Phase-1 variant is
batch-only.

This module never mutates exp/eqpa/ or any historical tag. New tags are
e7_evidence_eqpa* only.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from exp import config

ARM_NAME = "EVIDENCE_EQPA"
TAG_PREFIX = "e7_evidence_eqpa"

EQPA_DEV_CASES = config.BASELINE_DEV_CASES

# ---- protocol pins (identical to e4_eqpa_40960) ----
MAX_LLM_PER_SHOT = 16
MAX_OFFICIAL = 3

# ---- batch knobs (the treatment) ----
MAX_QUERIES_PER_BATCH = 5
PROBE_TIMEOUT_S = 8.0
PROBE_MAX_CHARS = 900
MAX_PROBES_PER_SHOT = 12

# ---- feature flags (set by run.py from CLI; default Phase-1 batch-only) ----
PLANNING_ENABLED = False
PROGRESS_ENABLED = False


def set_modes(planning: bool, progress: bool) -> None:
    global PLANNING_ENABLED, PROGRESS_ENABLED
    PLANNING_ENABLED = bool(planning)
    PROGRESS_ENABLED = bool(progress)


def variant_suffix() -> str:
    s = ""
    if PLANNING_ENABLED:
        s += "_plan"
    if PROGRESS_ENABLED:
        s += "_prog"
    return s


BATCH_SYSTEM = (
    "You solve one Qiskit programming task against the live interpreter. "
    "Hidden tests are not provided. The host benchmark repository is not visible. "
    "Use BatchProbe to inspect installed Qiskit: it runs a small batch of shell "
    "commands in the isolated environment in ONE round and returns structured, "
    "clipped evidence per command. Group related inspections into a single "
    "BatchProbe call (API signatures, versions, object construction, and small "
    "behavioral experiments belong together); do not spend one call per fact. "
    "Label each query with its kind: api, behavior, runtime, or env. "
    "Scratch files belong in /tmp. /workspace is read-only. "
    "Submit with Write using the exact filename attempt_1.py, attempt_2.py, or attempt_3.py, "
    "then call Eval() to run official tests. Do not try to read dataset, sealed, or grader files."
)

BATCH_TOOL = {
    "type": "function",
    "function": {
        "name": "BatchProbe",
        "description": (
            "Run a batch of up to 5 shell commands in the isolated evaluation "
            "environment in ONE round. Returns structured evidence per command "
            "(index, kind, ok, clipped output). cwd is /workspace (read-only); "
            "scratch files go in /tmp; Python and Qiskit are available. Label "
            "each query's kind: api (signatures/attributes/versions), behavior "
            "(small circuit/state/distribution experiments), runtime (minimal "
            "repros), or env (paths, env facts)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": ["api", "behavior", "runtime", "env"],
                                "description": "What kind of evidence this query collects.",
                            },
                            "query": {
                                "type": "string",
                                "description": "One shell command to execute.",
                            },
                        },
                        "required": ["query"],
                    },
                    "description": "Up to 5 queries, executed in order in one round.",
                }
            },
            "required": ["queries"],
        },
    },
}


def default_tag(*, bench: str = "qhe", dev: bool = False, cohort: bool = False) -> str:
    bench = (bench or "qhe").strip().lower()
    tag = TAG_PREFIX
    if cohort:
        tag += "_cohort"
    if bench == "qbplus":
        tag += "_qbplus"
    if dev and not tag.endswith("_dev"):
        tag += "_dev"
    return tag + variant_suffix()


def refuse_foreign_tag(tag: str) -> None:
    t = (tag or "").strip()
    if not t.startswith(TAG_PREFIX):
        raise ValueError(
            f"REFUSE: evidence_eqpa writes only {TAG_PREFIX}* tags, got {t!r}. "
            "Historical e4_* results are frozen and untouchable."
        )


def batch_frozen_constants() -> dict:
    return {
        "arm": ARM_NAME,
        "max_llm_per_shot": MAX_LLM_PER_SHOT,
        "max_official": MAX_OFFICIAL,
        "max_queries_per_batch": MAX_QUERIES_PER_BATCH,
        "probe_timeout_s": PROBE_TIMEOUT_S,
        "probe_max_chars": PROBE_MAX_CHARS,
        "max_probes_per_shot": MAX_PROBES_PER_SHOT,
        "planning_enabled": PLANNING_ENABLED,
        "progress_enabled": PROGRESS_ENABLED,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
    }


def config_hashes() -> dict:
    here = Path(__file__).resolve().parent
    out = {}
    for name in ("prompts.py", "tools.py", "loop.py", "config.py"):
        p = here / name
        if p.is_file():
            out[name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out
