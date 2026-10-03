"""DEU-RC RepairController: orchestrates RCI -> mode selection -> evidence
gate -> context policy at every failure boundary, and emits the per-decision
control record (JSON-serializable) plus the mode directive message.

The controller decides the repair MODE; the LLM executes it. All inputs are
fields that already exist in the DEU-v2 trace (state manager + EMA updater);
no new oracle, no LLM in the controller, deterministic everywhere.

Ablation flags (Phase-2 preparation; frozen defaults True):
  enable_mode_controller  False -> mode forced to SEARCH every boundary
                          (equivalence arm: plain DEU-v2 behavior)
  enable_evidence_gate    False -> no family is ever blocked (probe filter
                          no-ops)
  enable_context_gate     False -> full history every attempt (assemble
                          no-ops)
Ablation arms: full / w/o context / w/o evidence gate / action-only
(mode directive + prompt constraints only: evidence_gate=False,
context_gate=False). See rq4_deurc_design.md §ablations.
"""
from __future__ import annotations

import time

from exp.fcea.control import context_gate
from exp.fcea.control.control_index import DEFAULT_CONSTANTS as _RCI_C
from exp.fcea.control.control_index import compute_rci
from exp.fcea.control.evidence_gate import (
    BLOCKED, DEGRADED, EvidenceBranchState, FAMILY_KINDS, PROBEABLE,
)
from exp.fcea.control.evidence_gate import DEFAULT_CONSTANTS as _EVIDENCE_C
from exp.fcea.control.evidence_gate_soft import (
    DEFAULT_CONSTANTS as _SOFTFOCUS_C, SOFT_FOCUS_TEXT, focus_withdraws_tool,
    preferred_family,
)
from exp.fcea.control.mode_selector import (
    ALLOWED_ACTIONS, CONTEXT_POLICY, ESCAPE, FOCUS, SEARCH, TERMINATE,
)
from exp.fcea.control.mode_selector import DEFAULT_CONSTANTS as _MODE_C
from exp.fcea.control.mode_selector import select_mode
from exp.fcea.control.mode_selector_noescape import select_mode_noescape
from exp.fcea.utility.commitment_state import CommitmentState, fsm_active

DEFAULT_CONSTANTS = {
    **_RCI_C,
    **_MODE_C,
    **_EVIDENCE_C,
    **context_gate.DEFAULT_CONSTANTS,
    "enable_mode_controller": True,
    "enable_evidence_gate": True,
    "enable_context_gate": True,
    # Phase 2.2 ESCAPE ablation (variant deurc_noescape): when False, an
    # ESCAPE selection is replaced by the no-escape fallback (FOCUS if the
    # focus gate holds, else SEARCH); original_mode/escape_blocked record
    # what the frozen rule would have done
    "enable_escape_mode": True,
    # Phase 2.2 FOCUS ablation (variant deurc_softfocus): when False, FOCUS
    # no longer withdraws BatchProbe — soft prioritization instead (preferred
    # family = utility argmax, others selectable with a priority penalty)
    "focus_hard_restriction": True,
    # RQ3 Phase B (variant d3 = full − C1): state inputs blinded — failure
    # attribution / branch updates skipped (branches frozen ACTIVE), stagnation
    # counters forced 0, progress/novelty forced neutral, ESCAPE unreachable.
    # Utility inputs (Q, utility_drop) still consumed as passed. Default False
    # keeps every existing variant byte-identical.
    "state_blind": False,
}

HEADER = "[Repair controller — mode directive]"
FOOTER = ("The controller selects the repair mode; you execute it. How to "
          "execute the mode remains yours.")

_CONSTRAINTS_TEXT = {
    SEARCH: "No additional restriction this attempt.",
    FOCUS: ("Evidence collection is disabled this attempt. Work with the "
            "evidence you have: generate or improve the patch and validate it."),
    ESCAPE: ("The blocked evidence path failed repeatedly and must not be "
             "continued. Use only the allowed evidence kinds or change repair "
             "strategy; repeating the failed direction is not acceptable."),
    TERMINATE: ("Probing and evidence acquisition are disabled for the rest "
                "of this episode. Prepare your best current solution and "
                "submit it for evaluation."),
}

# MECH-1 mech_directive_v2 (protocol docs/实验MECH-1_协议.md): the legacy
# wording conflates "do not repeat the failed call" with "do not gather
# contract evidence about it" — the second part is what starved QHE ENV
# repairs (31/34 episodes FOCUS-banned; directive is what the model reads).
_MECH_DIRECTIVE_V2 = {
    FOCUS: ("Open-ended exploration is disabled this attempt: do not start "
            "new broad evidence sweeps. If a contract probe for the failing "
            "API is attached below, use it; improve the patch and validate."),
    ESCAPE: ("Do not resubmit previously failed calls or constructions. "
             "Collecting contract evidence about the failing API (e.g. the "
             "attached probe, or ApiProbe) is allowed; otherwise change the "
             "repair direction."),
}


class RepairController:
    """One instance per episode; updated only at failure boundaries."""

    def __init__(self, constants: dict | None = None):
        self.c = dict(DEFAULT_CONSTANTS)
        if constants:
            self.c.update(constants)
        self.branches = EvidenceBranchState(self.c)
        self.control_log: list[dict] = []
        self.current_mode = SEARCH
        self.last_decision: dict | None = None
        # deurq_fsm (v1.1): commitment bookkeeping + derived convergence
        # memory. The counter is maintained HERE from the progress_score
        # series passed at each boundary (spec 修订 5) — no loop changes.
        # Both stay inert unless an fsm_* flag is on.
        self.commitment = CommitmentState()
        self.no_improvement_count = 0

    # ---- deurq_fsm helpers -----------------------------------------------
    def _fsm_guards(self) -> dict:
        return {"G1": bool(self.c.get("fsm_g1_terminate")),
                "G2": bool(self.c.get("fsm_g2_chain")),
                "G3": bool(self.c.get("fsm_g3_evidence_guard")),
                "G4": bool(self.c.get("fsm_g4_hysteresis")),
                "G5": bool(self.c.get("fsm_g5_best_q"))}

    def _fsm_on(self) -> bool:
        return any(self._fsm_guards().values())

    # ---- runtime queries -------------------------------------------------
    def allowed_families(self) -> list[str]:
        if not self.c.get("enable_evidence_gate", True):
            return list(PROBEABLE)
        return self.branches.allowed_families()

    def probe_withdrawn(self) -> bool:
        """TERMINATE always withdraws BatchProbe; FOCUS withdraws it only
        under the frozen hard policy (soft FOCUS keeps it available)."""
        if not self.c.get("enable_mode_controller", True):
            return False
        return focus_withdraws_tool(self.current_mode, self.c)

    # ---- boundary decision ------------------------------------------------
    def on_boundary(self, *, step, boundary_kind, task_id,
                    no_progress_count, same_error_count, code_changed,
                    progress_score, novelty_mean_now, novelty_mean_prev,
                    family_novelty_now, family_novelty_prev,
                    utility_drop, Q, evidence_used, evidence_samples,
                    error_message, ts=None,
                    mech_contract_coverage: bool | None = None) -> dict:
        state_blind = bool(self.c.get("state_blind", False))
        if state_blind:
            # D3 (full − C1): the state path is dead. No failure attribution,
            # no stagnation, no saturation — every state-triggered rule
            # becomes unreachable; only utility-driven selection remains.
            no_progress_count = 0
            same_error_count = 0
            progress_score = 0
            novelty_mean_now = None
            novelty_mean_prev = None
            family_novelty_now = {}
            family_novelty_prev = {}

        # deurq_fsm: commitment bookkeeping + G1 convergence memory. The
        # counter advances on every boundary without a confirmed improvement
        # (progress_score != +1, including SUBMISSION_MISSING per spec 修订 3)
        # and resets on +1. Maintained only under fsm_g1_terminate so legacy
        # episodes keep identical object state.
        fsm = self._fsm_guards()
        if fsm["G2"] or fsm["G3"]:
            self.commitment.on_boundary(boundary_kind)
        if fsm["G1"]:
            if int(progress_score) == 1:
                self.no_improvement_count = 0
            else:
                self.no_improvement_count += 1

        # 1) evidence branch update (failure attribution by dominant family)
        self.branches.set_q_values(Q or {})
        fam = EvidenceBranchState.dominant_family(evidence_used)
        if state_blind:
            branch_rec = None          # branches frozen ACTIVE; nothing updated
            recovered = []
        elif boundary_kind == "nosubmit" and fsm["G3"]:
            # deurq_fsm G3: a SUBMISSION_MISSING boundary is a commitment
            # failure, not evidence-path failure — no family attribution, no
            # failures increment, no signature into the pool (G2/G3 pair,
            # spec §5). Decision inputs (RCI, mode selection) are unaffected.
            branch_rec = None
            recovered = []
        else:
            branch_rec = self.branches.on_failure(
                evidence_used=evidence_used, error_message=error_message,
                family_novelty_now=(family_novelty_now or {}).get(fam),
                family_novelty_prev=(family_novelty_prev or {}).get(fam))
            recovered = self.branches.on_recovery_evidence(error_message or "")

        # 2) RCI
        rci_rec = compute_rci(
            Q=Q or {}, progress_score=progress_score,
            novelty_mean=novelty_mean_now,
            no_progress_count=no_progress_count,
            same_error_count=same_error_count, utility_drop=utility_drop,
            constants=self.c)

        # 3) mode selection (deterministic, priority TERMINATE>ESCAPE>FOCUS>SEARCH)
        mode_ctrl_on = self.c.get("enable_mode_controller", True)
        sel_kwargs = dict(
            no_progress_count=no_progress_count, utility_drop=utility_drop,
            escape_worthy_family=(None if state_blind else
                                  self.branches.escape_worthy()
                                  if self.c.get("enable_evidence_gate", True)
                                  else None),
            best_q=self.branches.best_q(),
            evidence_samples=evidence_samples,
            # RQ-fix F2: E3 coverage flag for the FOCUS gate (consumed only
            # when focus_requires_e3 is on, i.e. variant deurq_fix)
            focus_e3_ready=bool((evidence_used or {}).get("E3", 0) >= 1),
            # MECH-1 D-F: failing-API contract coverage from the episode
            # ledger (consumed only when mech_focus_coverage is on, i.e.
            # variants mech1_rep/mech1_full; None keeps legacy behavior)
            contract_coverage=mech_contract_coverage)
        prev_mode = self.current_mode
        sel = select_mode(**sel_kwargs, no_improvement_count=self.no_improvement_count,
                          constants=self.c)
        original_mode = sel["mode"]
        escape_blocked = False
        # deurq_fsm G4: FOCUS hysteresis (spec 修订 1, fall-through). A FOCUS
        # decision owns at least one full attempt: an immediate ESCAPE at the
        # next boundary is suppressed and priority evaluation continues
        # WITHOUT the escape branch (temporal stability, not mode lock —
        # TERMINATE stays reachable above it, and after any non-FOCUS
        # boundary ESCAPE is selectable again).
        hysteresis_blocked = False
        if fsm["G4"] and prev_mode == FOCUS and sel["mode"] == ESCAPE:
            sel = select_mode(**sel_kwargs, no_improvement_count=self.no_improvement_count,
                              escape_allowed=False, constants=self.c)
            original_mode = "ESCAPE"
            hysteresis_blocked = True
        if not self.c.get("enable_escape_mode", True) and sel["mode"] == ESCAPE:
            sel = select_mode_noescape(**sel_kwargs, constants=self.c)
            original_mode = "ESCAPE"
            escape_blocked = bool(sel.get("escape_blocked"))
        mode = sel["mode"] if mode_ctrl_on else SEARCH
        self.current_mode = mode

        # 4) evidence gate constraints
        blocked = self.branches.blocked_families() \
            if self.c.get("enable_evidence_gate", True) else []
        allowed = [f for f in PROBEABLE if f not in blocked]

        # 5) context policy (applied by the caller via context_gate.assemble)
        context_policy = CONTEXT_POLICY[mode] \
            if self.c.get("enable_context_gate", True) else "disabled"

        # 6) directive message
        message = None
        focus_evidence = None
        if mode != SEARCH and mode_ctrl_on:
            if mode == FOCUS and not self.c.get("focus_hard_restriction", True):
                # soft FOCUS: no family removal — preferred family + penalty
                pf = preferred_family(Q or {})
                body = SOFT_FOCUS_TEXT.format(fam=pf or "none")
                penalized = [f for f in PROBEABLE if f != pf]
                focus_evidence = {
                    "before_evidence": {f: int((evidence_used or {}).get(f, 0))
                                        for f in PROBEABLE},
                    "preferred_family": pf,
                    "hard_removed_evidence": penalized,
                    "soft_penalty_evidence": penalized,
                    "selected_evidence": pf,
                    "hard_restriction": False,
                }
            else:
                body = _CONSTRAINTS_TEXT[mode]
            # MECH-1 mech_directive_v2: FOCUS/ESCAPE wording must not forbid
            # collecting contract evidence about the failing API (protocol
            # docs/实验MECH-1_协议.md; analysis 2026-09-30 §2.6)
            if self.c.get("mech_directive_v2", False) and mode in (FOCUS, ESCAPE):
                body = _MECH_DIRECTIVE_V2[mode]
            message = "\n".join([
                HEADER,
                "Current Repair Mode: %s" % mode,
                "Controller Constraints: %s" % body,
                "Allowed Evidence: %s" % (", ".join(allowed) or "none"),
                "Forbidden Evidence: %s" % (", ".join(blocked) or "none"),
                "RCI: {r} (utility {utility}, progress {progress}, "
                "novelty {novelty}, stagnation {stagnation}, "
                "utility_drop {utility_drop})".format(
                    r=rci_rec["rci"], **rci_rec["components"]),
                FOOTER,
            ])

        record = {
            "step": step,
            "task_id": task_id,
            "boundary_kind": boundary_kind,
            "ts": ts if ts is not None else None,
            "q_values": {k: round(float(v), 4) for k, v in (Q or {}).items()},
            "utility_delta": round(float(utility_drop), 4),
            "progress": int(progress_score),
            "novelty": (round(float(novelty_mean_now), 4)
                        if novelty_mean_now is not None else None),
            "same_error_count": int(same_error_count),
            "rci": rci_rec["rci"],
            "rci_components": rci_rec["components"],
            "repair_mode": mode,
            "original_mode": original_mode,
            "selected_mode": mode,
            "escape_blocked": escape_blocked,
            "mode_reason": sel["reason"],
            "mode_changed": mode != prev_mode,
            "prev_mode": prev_mode,
            **({"mech_contract_coverage": mech_contract_coverage}
               if mech_contract_coverage is not None else {}),
            "allowed_actions": (
                ["BatchProbe"] + list(ALLOWED_ACTIONS[mode])
                if (mode == FOCUS
                    and not self.c.get("focus_hard_restriction", True))
                else list(ALLOWED_ACTIONS[mode])),
            "focus_evidence": focus_evidence,
            "allowed_evidence": allowed,
            "blocked_evidence": blocked,
            "blocked_branches": [f for f in blocked],
            "context_policy": context_policy,
            "branches": branch_rec,
            "recovered_to_recoverable": recovered,
            "message_sent": message is not None,
            "message_text": message,
            "ablation_flags": {
                "enable_mode_controller": mode_ctrl_on,
                "enable_evidence_gate": self.c.get("enable_evidence_gate", True),
                "enable_context_gate": self.c.get("enable_context_gate", True),
                "state_blind": state_blind,
            },
        }
        if self._fsm_on():
            record["fsm"] = {
                "guards": fsm_active() or [g for g, on in fsm.items() if on],
                "no_improvement_count": self.no_improvement_count,
                "hysteresis_blocked": hysteresis_blocked,
                "branch_attribution": (None if (boundary_kind == "nosubmit" and fsm["G3"])
                                       else (branch_rec or {}).get("family") if branch_rec else None),
                "commitment": self.commitment.snapshot(),
            }
        self.control_log.append(record)
        self.last_decision = record
        return record

    # ---- context assembly (delegates to the gate) -------------------------
    def assemble_context(self, messages: list[dict]) -> tuple[list[dict], dict]:
        if not self.c.get("enable_context_gate", True):
            return messages, {"context_policy": "disabled", "turns_before": 0,
                              "turns_kept": 0, "chars_before": 0,
                              "chars_after": 0, "reduction_ratio": 0.0}
        return context_gate.assemble(self.current_mode, messages,
                                     constants=self.c)

    def snapshot(self) -> dict:
        return {"current_mode": self.current_mode,
                "branches": self.branches.snapshot(),
                "decisions": len(self.control_log)}
