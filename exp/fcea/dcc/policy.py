"""DCC policy: the frozen depth-conditioned commitment schedule.

Protocol source: user-specified arm spec (2026-09-29), grounded in the Stage 0
F1 census (docs/analysis/stage0_f1_control_census_20260929.md §5.1: step1
conservative optimal 43-71% vs interventions 12-47%; step2 converge optimal
FOCUS 58-60% vs ESCAPE 19-29%).

The ONLY decision variable is failure_depth (the official-attempt counter at
the failure boundary). Forbidden by spec: error_transition, utility,
evidence_value, belief, taxonomy, root cause, RCI, learned models, dynamic
thresholds, remaining-slot arithmetic in state judgment. This module is a pure
function of an integer.

    depth == 1  -> SEARCH   (keep exploring;  tools: BatchProbe+Write+Eval;
                             constraint: none)
    depth == 2  -> FOCUS    (converge;       tools: Write+Eval;
                             constraint: tool_withdrawn)
    depth >= 3  -> COMMIT   (final attempt;  tools: Write+Eval;
                             constraint: tool_withdrawn)

Deterministic: identical inputs give byte-identical outputs.
"""
from __future__ import annotations

SEARCH = "SEARCH"
FOCUS = "FOCUS"
COMMIT = "COMMIT"

ALL_TOOLS = ("BatchProbe", "Write", "Eval")
CONVERGE_TOOLS = ("Write", "Eval")

_HEADER = "[Depth-conditioned controller — commitment directive]"
_FOOTER = ("The controller sets the commitment level for the next attempt; "
           "how to execute it remains yours.")

_L1_TEXT = {
    SEARCH: ("Continue diagnosing. Keep gathering the evidence you need "
             "(BatchProbe stays available), then write and validate your "
             "candidate."),
    FOCUS: ("Stop exploring new directions. Work from the evidence you "
            "already have: produce the candidate fix now and validate it. "
            "No further evidence collection this attempt."),
    COMMIT: ("Final official attempt. No further exploration: prepare your "
             "best current fix and submit it for evaluation."),
}


def select(depth: int) -> dict:
    """Frozen mapping depth -> commitment. Pure; no other input exists."""
    d = int(depth)
    if d <= 1:
        action = SEARCH
    elif d == 2:
        action = FOCUS
    else:
        action = COMMIT
    tools = ALL_TOOLS if action == SEARCH else CONVERGE_TOOLS
    return {
        "failure_depth": d,
        "action": action,
        "allowed_tools": list(tools),
        "constraint_applied": "none" if action == SEARCH else "tool_withdrawn",
        "l1_text": "\n".join([_HEADER,
                              "Current commitment level: %s" % action,
                              _L1_TEXT[action],
                              _FOOTER]),
        "reason": "failure_depth=%d" % d,
    }
