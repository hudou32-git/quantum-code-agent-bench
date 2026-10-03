"""P12-NL: Existing techniques on NL→code (local_hard by default).

Override dataset with:
  export ORACLE_QHE_SPLIT=local|local_hard
  # or
  export ORACLE_QHE_DATASET=/abs/path/to/dataset.json
"""

from __future__ import annotations

import os
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent
ORACLE_ROOT = PKG_ROOT.parents[1]  # exp/rag/oracle
REPO_ROOT = ORACLE_ROOT.parents[2]  # submit/
QHE_ROOT = REPO_ROOT / "bench" / "qhe"

_SPLIT = (os.environ.get("ORACLE_QHE_SPLIT") or "local_hard").strip().lower()
_DATASET_OVERRIDE = (os.environ.get("ORACLE_QHE_DATASET") or "").strip()
if _DATASET_OVERRIDE:
    DATASET = Path(_DATASET_OVERRIDE)
elif _SPLIT in {"local", "qhe_local"}:
    DATASET = QHE_ROOT / "dataset" / "dataset_qiskit_test_human_eval_local.json"
elif _SPLIT in {"local_hard", "qhe_local_hard", "hard"}:
    DATASET = QHE_ROOT / "dataset" / "dataset_qiskit_test_human_eval_local_hard.json"
else:
    raise ValueError(f"Unknown ORACLE_QHE_SPLIT={_SPLIT!r}; use local or local_hard")
QHE_SPLIT = "local" if "local_hard" not in DATASET.name else "local_hard"
EVAL_SCRIPT = QHE_ROOT / "eval" / "evaluate_completions.py"
QHE_PYTHON = Path("/root/anaconda3/envs/qhe/bin/python")
ENV_FILE = REPO_ROOT / ".env"
RAG_KB = ORACLE_ROOT.parents[1] / "rag" / "kb" / "rag_kb"  # exp/rag/kb/rag_kb

RUNS = PKG_ROOT / "runs"
RESULTS = PKG_ROOT / "results"
REPORTS = PKG_ROOT / "reports"
MANIFESTS = PKG_ROOT / "manifests"

EXPERIMENT_ID = "P12_NL"
PROTOCOL_ID = "P12_NL_LOCAL_HARD_v1"

def _dotenv_model() -> str:
    """DEEPSEEK_MODEL from process env, else submit-root .env; no hardcoded id."""
    v = (os.environ.get("DEEPSEEK_MODEL") or "").strip()
    if v:
        return v
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("DEEPSEEK_MODEL=") or s.startswith("DEEPSEEK_MODEL ="):
                return s.split("=", 1)[1].strip().strip("'\"")
    return ""


MODEL = _dotenv_model()
TEMPERATURE = 0.0
MAX_TOKENS = 4096
DISABLE_THINKING = True

RAG_TOP_K = 3
RAG_CONTEXT_MAX_CHARS = 3600
RAG_SNIPPET_CHARS = 900
SHUFFLED_RAG_SEED = 20261201

# Default non-formal backend: "ragflow" (single-dataset) or "local" (TF-IDF).
# Formal RAG arms (G3/G4/E2/E3/I2/I3) ALWAYS use RAGFlow SEPARATE via
# matched(..., formal_rag=True) — env cannot force them onto local KB.
# Override non-formal path with ORACLE_RAG_BACKEND. RAGFlow uses RAGFLOW_* from .env.
RAG_BACKEND = "ragflow"

# Formal RAG technical-route arms: forced RAGFLOW_MULTI_DATASET_SEPARATE.
FORMAL_RAG_ARMS = (
    "G3_RAG",
    "G4_RAG_PLAN",
    "G4_RAG_QSCOT_FS",
    "E2_RAG_EF",
    "E3_RAG_PLAN_EF",
    "E_RAG_QSCOT_EF",
    "I2_RAG_EF_B3",
    "I3_RAG_PLAN_EF_B3",
)

# Shuffled-context control only (local doc pool). Not a formal RAG route.
SHUFFLED_CONTROL_ARM = "C1_SHUFFLED_RAG"

SEPARATE_RUNTIME_CFG = PKG_ROOT / "config" / "RAGFLOW_SEPARATE_RUNTIME.json"

DEFAULT_MAX_CONCURRENT = 128
LLM_MAX_CONCURRENT = 128
EVAL_MAX_CONCURRENT = 24
SMOKE_N_TASKS = 5
SMOKE_MAX_CONCURRENT = 8  # smoke: keep low; full run uses 128
EVAL_WORKERS = 24

LLM_MAX_RETRIES = 4
LLM_RETRY_BASE_S = 1.0
MAX_INFRA_RETRIES = 3
INFRA_RETRY_DELAY_S = 60.0
MAX_TOTAL_CALLS_DEFAULT = 4000
TOKEN_BUDGET_DEFAULT = 8_000_000  # soft budget across B0; checkpoint tracks usage
CHECKPOINT_EVERY = 20
MAX_ROUNDS = 3  # Success@3 ceiling (round1 + up to 2 revisions)

# Cross-task / temporal leakage
CROSS_TASK_SIM_THRESHOLD = 0.85
TEMPORAL_LEAKAGE_EXCLUDE = True

SINGLE_TURN_ARMS = (
    "G0_RAW",
    "G1_CONTRACT",
    "G2_PLAN",
    "G3_RAG",
    "G4_RAG_PLAN",
    "C1_SHUFFLED_RAG",
    "C2_CHECKLIST",
)

# Feedback ablation: Round1 frozen identical G1; revise only G1 failures.
ITER_ARMS = (
    "I0_EF_B3",
    "I1_PLAN_EF_B3",
    "I2_RAG_EF_B3",
    "I3_RAG_PLAN_EF_B3",
)

# End-to-end: continue from each parent arm's own Round-1 candidates.
E_ARMS = (
    "E0_EF",
    "E1_PLAN_EF",
    "E2_RAG_EF",
    "E3_RAG_PLAN_EF",
)

E_PARENT = {
    "E0_EF": "G1_CONTRACT",
    "E1_PLAN_EF": "G2_PLAN",
    "E2_RAG_EF": "G3_RAG",
    "E3_RAG_PLAN_EF": "G4_RAG_PLAN",
    # FSE2027 confirmatory: EF on Q-SCoT / RAG+Q-SCoT parents (not in default B0E E_ARMS)
    "E_QSCOT_EF": "G2_QSCOT_FS",
    "E_RAG_QSCOT_EF": "G4_RAG_QSCOT_FS",
}

I_PARENT = {a: "G1_CONTRACT" for a in ITER_ARMS}

PRIMARY_BASELINE = "G1_CONTRACT"

# Feedback uses the SAME public tests as final grading (declared oracle).
FEEDBACK_ORACLE_MODE = "TEST_ORACLE_GUIDED_GENERATION"
FEEDBACK_VISIBLE_FIELDS = (
    "exception_type",
    "exception_message",
    "overall_pass_fail",
)
FEEDBACK_NOT_VISIBLE_FIELDS = (
    "hidden_assert_source",  # N/A: no separate hidden suite in this protocol
    "expected_vs_actual_structured",  # only if present inside exception message
    "full_traceback_unlimited",
)
