"""Evidence-EQPA prompts: workspace block, evidence-plan templates (Phase 2),
and the same-error replanning notice (Phase 3).

The plan is a PROBE-MENU suggestion injected once after the first official Eval
failure. It never changes tool availability. Templates are selected from the
failure text by regex (framework / semantic / runtime / unknown); the mapping
reuses the known mini/classify.py simplification (all TypeErrors -> api menu).
"""

from __future__ import annotations

import re

def workspace_block(*, case_id: str) -> str:
    return (
        "Workspace:\n"
        f"- task_id: {case_id}\n"
        "- visible files: /workspace/prompt.txt, /workspace/attempt_k.py (read-only)\n"
        "- inspect: BatchProbe runs a batch of shell commands in the isolated "
        "environment (python and Qiskit are on PATH) and returns structured evidence\n"
        "- scratch: /tmp\n"
        "- submit: Write with path exactly attempt_1.py (or attempt_2.py / attempt_3.py), then Eval()\n"
        "- Eval() grades the last successful Write and returns {passed, error}"
    )

API_PLAN = (
    "Evidence plan (api/ENV need): the failure looks framework-related "
    "(TypeError/ImportError/AttributeError). In ONE BatchProbe round collect: "
    "(1) inspect.signature of the symbol named in the error; "
    "(2) dir() of its module to find the current name; "
    "(3) qiskit.__version__; "
    "(4) a minimal construction test with the corrected arguments. "
    "Skip broad exploratory experiments until the interface facts are in hand."
)

SEMANTIC_PLAN = (
    "Evidence plan (semantic/behavior need): the failure is behavioral "
    "(AssertionError/KL mismatch). In ONE BatchProbe round: "
    "(1) build a minimal version of your circuit; "
    "(2) print its measurement distribution (and/or Statevector) for a small case; "
    "(3) check the qubit->classical mapping and whether measurement is required at all; "
    "(4) compare against what the task text asks for, step by step. "
    "Additional API lookups are fine only when a specific signature question arises."
)

RUNTIME_PLAN = (
    "Evidence plan (runtime need): the failure is an execution/value error. "
    "In ONE BatchProbe round: (1) build a minimal reproduction of the failing "
    "line; (2) print the types/shapes/values of the involved variables; "
    "(3) check index/order assumptions (little-endian ordering, register vs int)."
)

UNCERTAIN_PLAN = (
    "Evidence plan (uncertain): the feedback does not indicate a clear "
    "information need. Run ONE small BatchProbe round of discriminative checks: "
    "(1) qiskit version; (2) existence/signature of the entry-point symbols you "
    "use; (3) the smallest runnable fragment of your current solution. Then "
    "re-assess whether the need is api or behavioral before writing."
)


def plan_from_error(error_text: str) -> str:
    m = (error_text or "").strip()
    low = m.lower()
    if m.startswith("no official submit"):
        return (
            "Evidence plan (no submit happened): the previous attempt produced no "
            "candidate. Write attempt_k.py now; if information is missing, one "
            "small BatchProbe round first, then Write."
        )
    if re.search(r"AssertionError|KLMismatch|failed the hidden benchmark tests|does NOT match", m, re.I):
        return SEMANTIC_PLAN
    if re.search(r"TypeError|ImportError|ModuleNotFoundError|AttributeError|CircuitError|QiskitError|"
                 r"unexpected keyword argument|positional argument|NameError|has no attribute|"
                 r"backend or session must be specified", m, re.I):
        return API_PLAN
    if re.search(r"ValueError|KeyError|IndexError|timed? ?out|MemoryError|Killed|RecursionError", m, re.I):
        return RUNTIME_PLAN
    return UNCERTAIN_PLAN


REPLAN_NOTICE = (
    "The previous evidence round did NOT change the failure: the official error "
    "is identical to the previous one. The current probe strategy is not "
    "producing new information. Do NOT resubmit the same candidate. Switch "
    "evidence strategy in your next BatchProbe: if you were inspecting API "
    "facts, run a behavioral experiment instead (minimal circuit, distribution, "
    "truth table); if you were running behavior experiments, check the concrete "
    "API signatures you rely on. State in one line why the new direction should "
    "change the failure mode."
)

PROBE_BUDGET_NOTICE = (
    "Probe budget for this attempt is used ({n} queries across {rounds} batch "
    "rounds). Write attempt_k.py (exact filename attempt_1.py / attempt_2.py / "
    "attempt_3.py) and call Eval()."
)
