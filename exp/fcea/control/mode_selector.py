"""Repair Mode Selector: deterministic mapping (RCI, state, branch state) ->
RepairMode. The mode — not the LLM — decides WHAT the next attempt is for;
the LLM only decides HOW to execute it.

Priority (rq4_deurc_design.md §modes): TERMINATE > ESCAPE > FOCUS > SEARCH.

  TERMINATE  utility_drop >= threshold AND no_progress >= threshold
             (exploration utility exhausted; mirrors the frozen H2 FINALIZE
             trigger: drop >= 0.046, no_progress >= 2)
  ESCAPE     an evidence branch is ESCAPE-worthy: family failures >= threshold
             with non-increasing information gain (task-32 oscillation: the
             error text changes but the family keeps failing — the branch
             state does not reset, unlike the DEU-v2 same_error counter)
  FOCUS      evidence sufficient: best-family Q >= threshold AND enough
             evidence samples collected this episode
  SEARCH     default

All thresholds are config values (frozen in exp/fcea/config.py).
"""
from __future__ import annotations

SEARCH = "SEARCH"
FOCUS = "FOCUS"
ESCAPE = "ESCAPE"
TERMINATE = "TERMINATE"
MODES = (SEARCH, FOCUS, ESCAPE, TERMINATE)

# what the LLM may execute per mode (allowed_actions in the control log;
# the runtime removes BatchProbe from the tool list for FOCUS/TERMINATE)
ALLOWED_ACTIONS = {
    SEARCH: ("BatchProbe", "Write", "Eval"),
    FOCUS: ("Write", "Eval"),
    ESCAPE: ("BatchProbe", "Write", "Eval"),
    TERMINATE: ("Write", "Eval"),
}

# context policy key per mode (context_gate.py implements the assembly)
CONTEXT_POLICY = {
    SEARCH: "full",
    FOCUS: "focused",
    ESCAPE: "escaped",
    TERMINATE: "final",
}

DEFAULT_CONSTANTS = {
    "terminate_no_progress_threshold": 2,
    "terminate_utility_drop_threshold": 0.046,   # frozen H2 median nonzero |dQ|
    "focus_utility_threshold": 0.30,
    "focus_min_evidence": 4,
    # RQ-fix F2 (variant deurq_fix): FOCUS additionally requires that at least
    # one E3 (behavioral-experiment) probe was collected this episode — on
    # KL-graded tasks "enough evidence" is a coverage criterion (distribution
    # checks), not a count. Default False keeps every existing variant
    # byte-identical.
    "focus_requires_e3": False,
    # escape_family_failures lives in evidence_gate.DEFAULT_CONSTANTS (single
    # source; the escape-worthy predicate is a branch-state property)
}


def select_mode(*, no_progress_count, utility_drop, escape_worthy_family,
                best_q, evidence_samples, focus_e3_ready: bool = False,
                contract_coverage: bool | None = None,
                no_improvement_count: int = 0,
                escape_allowed: bool = True,
                constants: dict | None = None) -> dict:
    c = dict(DEFAULT_CONSTANTS)
    if constants:
        c.update(constants)
    # deurq_fsm G1: convergence signal. no_progress_count means "exact
    # repeat failure"; TERMINATE needs "no confirmed improvement for N
    # boundaries". Under fsm_g1_terminate the stall signal is the max of
    # both; the counter itself is maintained by the controller from the
    # progress_score series (spec 修订 5 — controller-side memory, loops
    # untouched). Legacy (flag off) byte-identical: no_progress only.
    stall = (max(int(no_progress_count), int(no_improvement_count))
             if c.get("fsm_g1_terminate", False) else int(no_progress_count))
    if (stall >= c["terminate_no_progress_threshold"]
            and float(utility_drop) >= c["terminate_utility_drop_threshold"]):
        mode = TERMINATE
        reason = ("no_progress={np} >= {t} and utility_drop={d} >= {dt}".format(
            np=no_progress_count, t=c["terminate_no_progress_threshold"],
            d=round(float(utility_drop), 4), dt=c["terminate_utility_drop_threshold"]))
        if c.get("fsm_g1_terminate", False) and \
                int(no_improvement_count) > int(no_progress_count):
            reason += (" [fsm_g1: stall=no_improvement={ni} >= {t}]".format(
                ni=no_improvement_count, t=c["terminate_no_progress_threshold"]))
    elif escape_allowed and escape_worthy_family is not None:
        mode = ESCAPE
        reason = ("family {f} failed {n} times with non-increasing information "
                  "gain".format(f=escape_worthy_family["family"],
                                n=escape_worthy_family["failures"]))
    elif (best_q is not None
          and float(best_q) >= c["focus_utility_threshold"]
          and int(evidence_samples) >= c["focus_min_evidence"]
          and (not c.get("focus_requires_e3", False) or focus_e3_ready)
          and not (c.get("mech_focus_coverage", False)
                   and contract_coverage is False)):
        mode = FOCUS
        reason = ("best-family Q={q} >= {t} and evidence_samples={n} >= {m}"
                  "{e3}".format(
                      q=round(float(best_q), 4), t=c["focus_utility_threshold"],
                      n=evidence_samples, m=c["focus_min_evidence"],
                      e3=" and E3 sampled" if c.get("focus_requires_e3", False) else ""))
    elif c.get("mech_focus_coverage", False) and contract_coverage is False:
        # MECH-1 D-F: the utility/count focus gates held, but the failing
        # API's resolved contract is not in the coverage ledger — "evidence
        # sufficient" is not satisfied. SEARCH keeps BatchProbe available so
        # the contract can be probed (model-initiated or the D1 auto probe).
        mode = SEARCH
        reason = "mech: focus gate held but failing-API contract uncovered"
    else:
        mode = SEARCH
        reason = "no gate condition met"
    return {"mode": mode, "reason": reason}
