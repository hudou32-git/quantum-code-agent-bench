"""DCC RepairController replacement: depth-conditioned commitment controller.

Loop-compatible duck-typed replacement for RepairController on the unchanged
deurc-noctx stack (identical constants; the decision layer is swapped the same
way d2_clean/d3 swap inputs). Interface consumed by exp/fcea/loop.py:
    on_boundary(**kwargs) -> record with "message_text"
    probe_withdrawn() / current_mode / allowed_families()
    assemble_context(messages) -> (messages, stats)   [noctx: passthrough]
    control_log / snapshot()

Every state/utility/evidence kwarg passed by the loop is ACCEPTED AND IGNORED:
failure_depth (the official-attempt counter at the boundary) is the only
decision input, per the arm spec. The selftest asserts this explicitly
(state-perturbation invariance).
"""
from __future__ import annotations

from exp.fcea.control.evidence_gate import PROBEABLE
from exp.fcea.dcc import logging as dlog
from exp.fcea.dcc import policy

DEFAULT_CONSTANTS = {
    # Intentionally minimal: no thresholds exist. Kept as a dict for
    # manifest/config symmetry with the other variant constant blocks.
    "policy": "depth_conditioned_commitment_v1",
}


class DCCController:
    """One instance per episode; updated only at failure boundaries."""

    def __init__(self, constants: dict | None = None):
        self.c = dict(DEFAULT_CONSTANTS)
        if constants:
            self.c.update(constants)
        self.current_mode = policy.SEARCH
        self.control_log: list[dict] = []
        self.decision_trace: list[dict] = []
        self.last_decision: dict | None = None

    # ---- runtime queries (loop interface) --------------------------------
    def allowed_families(self) -> list[str]:
        return list(PROBEABLE)          # DCC never gates evidence families

    def probe_withdrawn(self) -> bool:
        return self.last_decision is not None \
            and self.last_decision["constraint_applied"] == "tool_withdrawn"

    # ---- boundary decision -------------------------------------------------
    def on_boundary(self, *, step, task_id=None, boundary_kind=None,
                    allowed_tools_before=None, ts=None, **_ignored_state) -> dict:
        """`step` is the official counter at the failure boundary ==
        failure_depth. All other kwargs (state, utility, novelty, evidence,
        error text) are deliberately ignored."""
        decision = policy.select(step)
        self.current_mode = decision["action"]
        self.last_decision = decision
        rec = dlog.decision_record(
            episode_id=task_id, step=step, decision=decision,
            allowed_tools_before=allowed_tools_before or policy.ALL_TOOLS,
            boundary_kind=boundary_kind)
        rec["ts"] = ts
        rec["message_sent"] = True
        rec["message_text"] = dlog.message_text(decision)
        # compatibility aliases so generic control_log tooling keeps working
        rec["repair_mode"] = decision["action"]
        rec["selected_mode"] = decision["action"]
        rec["mode_changed"] = True  # vs SEARCH init; logged, never consumed
        self.control_log.append(rec)
        self.decision_trace.append(rec)
        return rec

    # ---- context assembly (noctx passthrough) ------------------------------
    def assemble_context(self, messages: list[dict]) -> tuple[list[dict], dict]:
        return messages, {"context_policy": "disabled", "turns_before": 0,
                          "turns_kept": 0, "chars_before": 0, "chars_after": 0,
                          "reduction_ratio": 0.0}

    # ---- episode-final state -----------------------------------------------
    def dcc_state_final(self) -> dict:
        return dlog.final_state(self.decision_trace)

    def snapshot(self) -> dict:
        st = self.dcc_state_final()
        return {"current_mode": self.current_mode,
                "dcc_decisions": len(self.decision_trace),
                **st}
