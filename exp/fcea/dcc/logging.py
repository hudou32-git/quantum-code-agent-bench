"""DCC trace record builders (additive keys only).

Row-level additions (never overwriting an existing key):
    dcc_trace_schema: 1
    dcc_state:        episode-final {failure_depth, selected_commitment,
                                     constraint_applied}
    decision_trace:   per-boundary records per the arm spec §7
"""
from __future__ import annotations

DCC_TRACE_SCHEMA = 1


def decision_record(*, episode_id, step, decision, allowed_tools_before,
                    boundary_kind=None):
    """One control-boundary record. `decision` is policy.select(depth)."""
    return {
        "episode_id": episode_id,
        "step": int(step),
        "boundary_kind": boundary_kind,
        "failure_depth": decision["failure_depth"],
        "selected_action": decision["action"],
        "constraint_applied": decision["constraint_applied"],
        "allowed_tools_before": list(allowed_tools_before),
        "allowed_tools_after": list(decision["allowed_tools"]),
        "reason": decision["reason"],
    }


def final_state(decisions: list[dict]) -> dict:
    if not decisions:
        return {"failure_depth": 0, "selected_commitment": None,
                "constraint_applied": "none"}
    last = decisions[-1]
    return {
        "failure_depth": last["failure_depth"],
        "selected_commitment": last["selected_action"],
        "constraint_applied": last["constraint_applied"],
    }


def message_text(decision: dict) -> str:
    return decision["l1_text"]
