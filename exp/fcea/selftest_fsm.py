"""deurq_fsm v1.1 selftest — stub-driven, zero LLM / zero network.

Verifies, in order:
  A. legacy identity: registry empty + no fsm_* flags -> every touched
     component behaves exactly as before (byte-identical freeze guarantee)
  B. registry: enable_from_constants reads the DEURQ_FSM_* flag names
  C. G2: Technical Error Chain Integrity + Invariants A/B on the state
     manager; legacy nosubmit behavior unchanged when the guard is off
  D. G1: controller-side no_improvement_count + TERMINATE reachability
  E. G3: nosubmit boundaries no longer touch the evidence branch FSM
  F. G4: FOCUS hysteresis suppresses the immediate ESCAPE (fall-through)
  G. G5: best_q excludes BLOCKED families only
  H. CommitmentState transitions

Run: python3 -m exp.fcea.selftest_fsm
"""
from __future__ import annotations

from exp.fcea import config as fcfg
from exp.fcea.control.controller import RepairController
from exp.fcea.control.evidence_gate import (BLOCKED, DEGRADED,
                                            EvidenceBranchState)
from exp.fcea.control.mode_selector import select_mode
from exp.fcea.utility import commitment_state as fsm_mod
from exp.fcea.utility.commitment_state import CommitmentState, fsm_enabled
from exp.fcea.utility.state import DynamicEvidenceStateManager

_PASS = 0


def check(name: str, cond: bool) -> None:
    global _PASS
    if not cond:
        raise AssertionError(f"deurq_fsm selftest FAILED: {name}")
    _PASS += 1
    print(f"  ok  {name}")


def boundary_kwargs(**over):
    kw = dict(step=1, boundary_kind="error", task_id="T",
              no_progress_count=0, same_error_count=0, code_changed=False,
              progress_score=0, novelty_mean_now=None, novelty_mean_prev=None,
              family_novelty_now=None, family_novelty_prev=None,
              utility_drop=0.0, Q={}, evidence_used={}, evidence_samples=0,
              error_message="ValueError: x", ts=None)
    kw.update(over)
    return kw


# ---------------------------------------------------------------- A: legacy
def test_legacy_identity() -> None:
    print("A. legacy identity (no flags, empty registry)")
    sel = select_mode(no_progress_count=1, utility_drop=0.5,
                      escape_worthy_family=None, best_q=0.5,
                      evidence_samples=4)
    check("legacy TERMINATE still needs no_progress>=2 (1 -> not TERMINATE)",
          sel["mode"] != "TERMINATE")
    sel = select_mode(no_progress_count=2, utility_drop=0.5,
                      escape_worthy_family=None, best_q=0.5,
                      evidence_samples=4)
    check("legacy TERMINATE fires at no_progress>=2", sel["mode"] == "TERMINATE")
    sel = select_mode(no_progress_count=0, utility_drop=0.0,
                      escape_worthy_family={"family": "E1", "failures": 2},
                      best_q=0.1, evidence_samples=0)
    check("legacy ESCAPE fires when escape-worthy", sel["mode"] == "ESCAPE")

    st = EvidenceBranchState({"fsm_g5_best_q": False})
    for _ in range(3):
        st.on_failure(evidence_used={"E1": 1}, error_message="ValueError: a",
                      family_novelty_now=None, family_novelty_prev=None)
    st.set_q_values({"E1": 0.9, "E2": 0.1})
    check("legacy best_q includes the BLOCKED family",
          st.best_q() == 0.9 and st.branches["E1"]["status"] == BLOCKED)

    m = DynamicEvidenceStateManager()
    m.on_eval_result(shot=1, passed=False, error_message="KL=0.5",
                     code="def f(): pass")
    rec = m.on_eval_result(shot=2, passed=False,
                           error_message="no official submit this attempt",
                           code="def f(): pass", nosubmit=True)
    check("legacy nosubmit overwrites current_error (pre-G2 behavior)",
          "no official submit" in m.current_error)
    check("legacy nosubmit transition forced 'same'",
          rec["error_transition"] == "same" and m.error_transition == "same")
    check("legacy nosubmit increments same_error_count",
          m.same_error_count == 1)

    c = RepairController({})
    c.on_boundary(**boundary_kwargs(boundary_kind="nosubmit",
                                    evidence_used={"E2": 5},
                                    error_message="no official submit"))
    check("legacy nosubmit still attributes a branch failure",
          c.branches.branches["E2"]["failures"] == 1)
    check("legacy control_log carries no fsm block",
          all("fsm" not in r for r in c.control_log))


# -------------------------------------------------------------- B: registry
def test_registry() -> None:
    print("B. guard registry")
    fsm_mod.fsm_disable_all()
    active = fsm_mod.fsm_enable_from_constants(fcfg.DEURQ_FSM_CONSTANTS)
    check("full constants enable G1-G5", active == ["G1", "G2", "G3", "G4", "G5"])
    check("fsm_enabled('G2') true after enable", fsm_enabled("G2"))
    fsm_mod.fsm_disable_all()
    active = fsm_mod.fsm_enable_from_constants(fcfg.DEURQ_FSM_G2G3_CONSTANTS)
    check("G2G3 arm enables exactly G2+G3", active == ["G2", "G3"])
    fsm_mod.fsm_disable_all()
    active = fsm_mod.fsm_enable_from_constants(fcfg.DEURQ_FSM_G1_CONSTANTS)
    check("G1 arm enables exactly G1", active == ["G1"])
    fsm_mod.fsm_disable_all()
    check("disable_all clears", fsm_mod.fsm_active() == [])


# --------------------------------------------------------------------- C: G2
def test_g2() -> None:
    print("C. G2 technical error chain integrity")
    fsm_mod.fsm_disable_all()
    fsm_mod.fsm_enable(["G2"])

    m = DynamicEvidenceStateManager()
    m.on_eval_result(shot=1, passed=False, error_message="KL=0.5",
                     code="def f(): pass")
    ns = m.on_eval_result(shot=2, passed=False,
                          error_message="no official submit this attempt",
                          code="def f(): pass", nosubmit=True)
    check("G2 nosubmit preserves current_error (chain integrity)",
          m.current_error == "KL=0.5")
    check("G2 nosubmit record is boundary_type=nosubmit / commitment",
          ns["boundary_type"] == "nosubmit" and ns["commitment_failure"] is True
          and ns["technical_failure"] is False)
    check("Invariant A: record progress_score=0", ns["progress_score"] == 0)
    check("Invariant B: stagnation counters untouched at nosubmit",
          m.no_progress_count == 0 and m.same_error_count == 0)
    check("G2 derived caches legacy-neutral (same / 0) for the frozen C2",
          m.error_transition == "same" and m.last_progress_score == 0)
    after = m.on_eval_result(shot=3, passed=False, error_message="KL=0.30",
                             code="def g(): pass")
    check("next technical failure compares against the last TECHNICAL one "
          "(numeric improved, not unclear-via-pseudo)",
          after["error_transition"] == "improved")
    check("code-change comparison chain intact",
          after["code_changed"] is True and after["progress_score"] == 1)

    # legacy path (guard off) reproduces the polluted behavior for contrast
    fsm_mod.fsm_disable_all()
    m2 = DynamicEvidenceStateManager()
    m2.on_eval_result(shot=1, passed=False, error_message="KL=0.5",
                      code="def f(): pass")
    m2.on_eval_result(shot=2, passed=False,
                      error_message="no official submit this attempt",
                      code="def f(): pass", nosubmit=True)
    after2 = m2.on_eval_result(shot=3, passed=False, error_message="KL=0.30",
                               code="def g(): pass")
    check("legacy same sequence degrades to unclear (documents the bug)",
          after2["error_transition"] == "unclear")


# --------------------------------------------------------------------- D: G1
def test_g1() -> None:
    print("D. G1 convergence signal")
    fsm_mod.fsm_disable_all()
    c = RepairController({"fsm_g1_terminate": True})
    c.on_boundary(**boundary_kwargs(step=1, utility_drop=0.10))
    check("G1 counter advances on non-improving boundary",
          c.no_improvement_count == 1)
    c.on_boundary(**boundary_kwargs(step=2, utility_drop=0.10))
    check("G1 TERMINATE reachable at the 2nd unimproved boundary "
          "(0/93 -> >0)", c.current_mode == "TERMINATE")
    rec = c.control_log[-1]
    check("fsm block logged with counter + guard",
          rec["fsm"]["no_improvement_count"] == 2 and "G1" in rec["fsm"]["guards"])
    c.on_boundary(**boundary_kwargs(step=3, utility_drop=0.10, progress_score=1))
    check("confirmed improvement resets the counter",
          c.no_improvement_count == 0)
    check("nosubmit boundary counts as no-improvement (dual track)",
          (c.on_boundary(**boundary_kwargs(step=4, boundary_kind="nosubmit",
                                           utility_drop=0.0)),
           c.no_improvement_count == 1)[1])

    c2 = RepairController({})
    c2.on_boundary(**boundary_kwargs(step=1, utility_drop=0.10))
    c2.on_boundary(**boundary_kwargs(step=2, utility_drop=0.10))
    check("legacy controller never TERMINATEs on this sequence",
          c2.current_mode != "TERMINATE")


# --------------------------------------------------------------------- E: G3
def test_g3() -> None:
    print("E. G3 evidence attribution guard")
    fsm_mod.fsm_disable_all()
    fsm_mod.fsm_enable(["G3"])
    c = RepairController({"fsm_g3_evidence_guard": True})
    c.on_boundary(**boundary_kwargs(boundary_kind="nosubmit",
                                    evidence_used={"E2": 5},
                                    error_message="no official submit"))
    check("G3: nosubmit does not attribute a branch failure",
          c.branches.branches["E2"]["failures"] == 0)
    check("G3: technical failure boundaries still attribute",
          (c.on_boundary(**boundary_kwargs(evidence_used={"E2": 5},
                                           error_message="ValueError: y")),
           c.branches.branches["E2"]["failures"] == 1)[1])
    check("G3: nosubmit still records commitment state",
          c.commitment.state == CommitmentState.NORMAL
          and c.commitment.events == 1)
    check("G3 record carries exempt attribution",
          c.control_log[0]["fsm"]["branch_attribution"] is None)


# --------------------------------------------------------------------- F: G4
def test_g4() -> None:
    print("F. G4 FOCUS hysteresis (fall-through)")
    fsm_mod.fsm_disable_all()

    def drive(c: RepairController):
        # b1: FOCUS gate holds (Q=0.5 >= 0.3, samples 4)
        c.on_boundary(**boundary_kwargs(step=1, Q={"E1": 0.5},
                                        evidence_samples=4, utility_drop=0.0))
        # b2/b3: E1-family technical failures -> DEGRADED at 2 -> ESCAPE-worthy
        c.on_boundary(**boundary_kwargs(step=2, Q={"E1": 0.5},
                                        evidence_samples=6,
                                        evidence_used={"E1": 3},
                                        error_message="ValueError: q1"))
        c.on_boundary(**boundary_kwargs(step=3, Q={"E1": 0.5},
                                        evidence_samples=8,
                                        evidence_used={"E1": 3},
                                        error_message="ValueError: q2"))

    c = RepairController({"fsm_g4_hysteresis": True})
    drive(c)
    rec = c.control_log[-1]
    check("G4 suppresses the immediate FOCUS->ESCAPE flip",
          rec["original_mode"] == "ESCAPE" and rec["selected_mode"] == "FOCUS"
          and rec["fsm"]["hysteresis_blocked"] is True)
    check("G4 fall-through keeps FOCUS when the focus gate holds",
          c.current_mode == "FOCUS")

    c2 = RepairController({})
    drive(c2)
    check("legacy controller does flip FOCUS->ESCAPE (documents the bug)",
          c2.control_log[-1]["selected_mode"] == "ESCAPE")


# --------------------------------------------------------------------- G: G5
def test_g5() -> None:
    print("G. G5 blocked-branch exclusion")
    fsm_mod.fsm_disable_all()
    st = EvidenceBranchState({"fsm_g5_best_q": True})
    for _ in range(3):
        st.on_failure(evidence_used={"E1": 1}, error_message="ValueError: a",
                      family_novelty_now=None, family_novelty_prev=None)
    st.set_q_values({"E1": 0.9, "E2": 0.1})
    check("G5: BLOCKED family excluded from best_q",
          st.best_q() == 0.1 and st.branches["E1"]["status"] == BLOCKED)
    st2 = EvidenceBranchState({"fsm_g5_best_q": True})
    for _ in range(2):
        st2.on_failure(evidence_used={"E1": 1}, error_message="ValueError: a",
                       family_novelty_now=None, family_novelty_prev=None)
    st2.set_q_values({"E1": 0.9})
    check("G5: DEGRADED stays eligible",
          st2.best_q() == 0.9 and st2.branches["E1"]["status"] == DEGRADED)


# --------------------------------------------------------------------- H: CS
def test_commitment_state() -> None:
    print("H. CommitmentState transitions")
    cs = CommitmentState()
    check("initial NORMAL", cs.state == CommitmentState.NORMAL)
    cs.on_boundary("nosubmit")
    check("nosubmit -> SUBMISSION_MISSING",
          cs.state == CommitmentState.SUBMISSION_MISSING and cs.events == 1)
    cs.on_boundary("error")
    check("technical boundary -> NORMAL",
          cs.state == CommitmentState.NORMAL and cs.events == 1)


def main() -> None:
    # parent/identity sanity: existing variant constants untouched
    check("DEURQ_FIX_CONSTANTS unchanged (parent declaration)",
          fcfg.DEURQ_FIX_CONSTANTS["focus_min_evidence"] == 8
          and fcfg.DEURQ_FIX_CONSTANTS["focus_requires_e3"] is True
          and fcfg.DEURQ_FIX_CONSTANTS["kl_neutral_attribution"] is True
          and "fsm_g1_terminate" not in fcfg.DEURQ_FIX_CONSTANTS)
    check("full fsm constants extend the parent",
          all(fcfg.DEURQ_FSM_CONSTANTS[k] is True
              for k in ("fsm_g1_terminate", "fsm_g2_chain",
                        "fsm_g3_evidence_guard", "fsm_g4_hysteresis",
                        "fsm_g5_best_q")))
    test_legacy_identity()
    test_registry()
    test_g2()
    test_g1()
    test_g3()
    test_g4()
    test_g5()
    test_commitment_state()
    print(f"\ndeurq_fsm selftest: {_PASS} checks passed")


if __name__ == "__main__":
    main()
