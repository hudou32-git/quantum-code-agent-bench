"""EQPA (formerly CTRL-ISO) arm config: budgets, prompts, tags, runtime paths."""

from __future__ import annotations

from exp import config

# Arm identity. Historical rows (e4_iso*) used the name CTRL-ISO; new runs
# record arm="EQPA" under e4_eqpa* tags.
ARM_NAME = "EQPA"
EQPA_TAG = "e4_eqpa"
EQPA_DEV_TAG = "e4_eqpa_dev"
EQPA_QBPLUS_TAG = "e4_eqpa_qbplus"

EQPA_DEV_CASES = config.BASELINE_DEV_CASES

MAX_SHELL_PER_SHOT = 8
MAX_LLM_PER_SHOT = 16
MAX_OFFICIAL = 3

EQPA_SYSTEM = (
    "You solve one Qiskit programming task against the live interpreter. "
    "Hidden tests are not provided. The host benchmark repository is not visible. "
    "Use Shell to inspect installed Qiskit (python, importlib, inspect, ls). "
    "Scratch files belong in /tmp. /workspace is read-only. "
    "Submit with Write using the exact filename attempt_1.py, attempt_2.py, or attempt_3.py, "
    "then call Eval() to run official tests. Do not try to read dataset, sealed, or grader files."
)


def eqpa_system(framework: str = "qiskit") -> str:
    """Framework-parametrized system prompt. qiskit returns EQPA_SYSTEM
    byte-identical; the cirq/pennylane variants swap only the framework facts
    (same sentence structure, budgets, and submission contract — e8/e9 P0-E)."""
    fw = (framework or "qiskit").strip().lower()
    if fw == "qiskit":
        return EQPA_SYSTEM
    name = {"cirq": "Cirq", "pennylane": "PennyLane"}.get(fw, fw.capitalize())
    return (
        f"You solve one {name} programming task against the live interpreter. "
        "Hidden tests are not provided. The host benchmark repository is not visible. "
        f"Use Shell to inspect installed {name} (python, importlib, inspect, ls). "
        "Scratch files belong in /tmp. /workspace is read-only. "
        "Submit with Write using the exact filename attempt_1.py, attempt_2.py, or attempt_3.py, "
        "then call Eval() to run official tests. Do not try to read dataset, sealed, or grader files."
    )


# Sealed-pattern substrings that must never reach the model.
FORBIDDEN_SEALED_SUBSTR = (
    "sealed",
    "canonical_solution",
    "canonical_output",
    "canonical_results",
    "get_canonical_results",
    "problems_full",
    "problems_cirq",
    "problems_pennylane",
    "G1_CONTRACT",
    "check(",
    "dataset_qiskit_test",
)
