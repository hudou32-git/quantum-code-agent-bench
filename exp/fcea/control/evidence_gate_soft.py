"""Soft-FOCUS evidence policy (Phase 2.2 Experiment 2, variant deurc_softfocus).

SINGLE override, per the ablation freeze rules: only the FOCUS evidence
restriction changes. Hard FOCUS (frozen deurc) withdraws BatchProbe for the
whole attempt — no new evidence acquisition at all. Soft FOCUS keeps every
evidence family selectable and instead marks the best-utility family as
PREFERRED with a priority penalty on the others (prompt-level soft
prioritization; the branch-state hard blocking from ESCAPE-layer BLOCKED
statuses is unaffected).

  preferred_family(Q)   argmax utility over probeable families
  focus_withdraws_tool  TERMINATE always withdraws BatchProbe; FOCUS only
                        under the frozen hard policy
  SOFT_FOCUS_TEXT       the soft directive body

RCI, mode selection, ESCAPE/TERMINATE logic, context gate, thresholds: all
frozen and untouched.
"""
from __future__ import annotations

PROBEABLE = ("E1", "E2", "E3")

DEFAULT_CONSTANTS = {
    # frozen deurc default; deurc_softfocus runs with False
    "focus_hard_restriction": True,
}


def preferred_family(Q: dict) -> str | None:
    cands = {f: float(Q[f]) for f in PROBEABLE
             if f in Q and Q[f] is not None}
    return max(cands, key=cands.get) if cands else None


def focus_withdraws_tool(mode: str, constants: dict | None = None) -> bool:
    c = dict(DEFAULT_CONSTANTS)
    if constants:
        c.update(constants)
    if mode == "TERMINATE":
        return True
    if mode == "FOCUS":
        return bool(c.get("focus_hard_restriction", True))
    return False


SOFT_FOCUS_TEXT = ("Preferred evidence family this attempt: {fam}. Focus on "
                   "it first; other families remain selectable at lower "
                   "priority when you have a concrete reason.")
