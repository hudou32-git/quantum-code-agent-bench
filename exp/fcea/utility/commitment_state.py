"""deurq_fsm: CommitmentState + process-scoped guard registry (v1.1).

Two things live here.

1. CommitmentState — the C1-domain sibling of the technical error FSM
   (spec §3.2). A boundary is either a TECHNICAL FAILURE (the graded code
   raised/missed) or a COMMITMENT FAILURE (the attempt closed with no
   official submission). SUBMISSION_MISSING is not an error: it never
   enters error_transition, evidence failure attribution, or the signature
   pool (G2/G3); it feeds only commitment bookkeeping and controller-side
   stagnation pressure (spec 修订 3, dual-track).

2. The guard registry. G2 acts inside DynamicEvidenceStateManager, which
   both loops construct with the shared frozen ``fcfg.DEU_CONSTANTS`` —
   the loop files are outside the deurq_fsm modification boundary, so
   there is no per-instance channel for the flag. The runner therefore
   opts in once via :func:`fsm_enable_from_constants` before episode
   construction. The registry defaults to EMPTY: every pre-existing
   variant is byte-identical. Controller-side guards (G1/G3/G4/G5) do not
   use the registry — they flow through the per-episode constants dict.

This module is a leaf: it imports nothing from the package, so utility
(state.py) and control (controller.py) can both import it without cycles
and without inverting the control->utility layering.
"""
from __future__ import annotations

GUARDS = ("G1", "G2", "G3", "G4", "G5")

# constants flag name -> guard id (single source for enable_from_constants
# and for the controller-side reads of the same flags)
FLAG_TO_GUARD = {
    "fsm_g1_terminate": "G1",
    "fsm_g2_chain": "G2",
    "fsm_g3_evidence_guard": "G3",
    "fsm_g4_hysteresis": "G4",
    "fsm_g5_best_q": "G5",
}
GUARD_TO_FLAG = {g: f for f, g in FLAG_TO_GUARD.items()}

_ENABLED: set[str] = set()


def fsm_enable(guards) -> list[str]:
    for g in guards:
        if g in GUARDS:
            _ENABLED.add(g)
    return fsm_active()


def fsm_disable_all() -> None:
    _ENABLED.clear()


def fsm_enabled(guard: str) -> bool:
    return guard in _ENABLED


def fsm_active() -> list[str]:
    return sorted(_ENABLED)


def fsm_enable_from_constants(constants: dict | None) -> list[str]:
    """Enable every guard whose flag is set in a DEURQ_FSM_* constants dict.

    Called once by the runner (composition point); idempotent. G2 lives only
    in the registry (see module docstring); G1/G3/G4/G5 are read per-episode
    from the same flags via constants — enabling both keeps one switch panel.
    """
    if constants:
        fsm_enable(g for flag, g in FLAG_TO_GUARD.items() if constants.get(flag))
    return fsm_active()


class CommitmentState:
    """Per-episode commitment bookkeeping; updated at every failure boundary."""

    NORMAL = "NORMAL"
    SUBMISSION_MISSING = "SUBMISSION_MISSING"

    def __init__(self):
        self.state = self.NORMAL
        self.events = 0

    def on_boundary(self, boundary_kind: str) -> str:
        if boundary_kind == "nosubmit":
            self.state = self.SUBMISSION_MISSING
            self.events += 1
        else:
            self.state = self.NORMAL
        return self.state

    def snapshot(self) -> dict:
        return {"state": self.state, "events": self.events}
