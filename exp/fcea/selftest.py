"""FCEA (Static-EQPA) selftest — no LLM, no sandbox, no benchmark cases.

Validates: tag discipline, failure-context scoring, frozen prior loading and
variant tiers, notice construction (soft guidance, non-root-cause wording),
evidence taxonomy classification, BatchProbe query normalization, trace
records, and protocol-pin parity with the frozen Batch-EQPA branch.
"""
from __future__ import annotations

import json

from exp.fcea import config as fcfg
from exp.fcea.control import context_gate
from exp.fcea.control.context_gate import segment_turns
from exp.fcea.control.control_index import compute_rci
from exp.fcea.control.controller import RepairController
from exp.fcea.control.evidence_gate import (
    ACTIVE, BLOCKED, EvidenceBranchState, RECOVERABLE, error_signature,
)
from exp.fcea.control.mode_selector import (
    ESCAPE, FOCUS, SEARCH, TERMINATE, select_mode,
)
from exp.fcea.control.mode_selector_noescape import select_mode_noescape
from exp.fcea.evidence import planner
from exp.fcea.evidence.batch_probe import _normalize_queries
from exp.fcea.evidence.taxonomy import KIND_TO_CATEGORY, classify_evidence_output
from exp.fcea.tracing import trace as ftrace
from exp.fcea.utility import prior as uprior
from exp.fcea.utility.scorer import classify_failure

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))


def main() -> int:
    # ---- tag discipline ----
    for bad in ("e4_eqpa", "e7_evidence_eqpa", "e7_evidence_eqpa_qbplus", "rq3_x"):
        try:
            fcfg.refuse_foreign_tag(bad)
            check(f"tag_refuse_{bad}", False, "no exception")
        except ValueError:
            check(f"tag_refuse_{bad}", True)
    fcfg.set_variant("global")
    check("tag_default_global", fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_global")
    fcfg.set_variant("fcond")
    check("tag_default_fcond", fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_fcond")

    # ---- failure context scorer ----
    cases = [
        ("TypeError: SamplerV2.__init__() got an unexpected keyword argument 'x'", "Framework"),
        ("AttributeError: 'X' object has no attribute 'y'", "Framework"),
        ("ModuleNotFoundError: No module named 'qiskit.extensions'", "Framework"),
        ("AssertionError: 1 != 2", "Semantic"),
        ("KLMismatch: KL=27.631 threshold=0.05", "Semantic"),
        ("ValueError: bad shape", "Runtime"),
        ("QiskitError: invalid param", "Runtime"),
        ("Execution timeout (120.0s)", "Runtime"),
        ("no official submit this attempt", "NoSubmit"),
        ("", "Other"),
    ]
    for msg, want in cases:
        got = classify_failure(msg)["failure_context"]
        check(f"scorer_{want}<-{msg[:24]!r}", got == want, f"got {got}")

    # ---- frozen prior ----
    check("prior_loads", bool(uprior.provenance()["generated_at_utc"]))
    g = uprior.tiers_for("global", "Semantic")
    check("prior_global_any_context", g == uprior.tiers_for("global", "Framework"),
          "V2 ignores context")
    fw = uprior.tiers_for("fcond", "Framework")
    rt = uprior.tiers_for("fcond", "Runtime")
    check("prior_fcond_framework_E2_high", fw.get("E2") == "HIGH")
    check("prior_fcond_runtime_E2_low", rt.get("E2") == "LOW")
    check("prior_fcond_differentiates", fw != rt)
    check("prior_nosubmit_not_routed", uprior.tiers_for("fcond", "NoSubmit") == {})
    check("prior_qhe_only_provenance", "qbplus" not in json.dumps(
        uprior.provenance()["source_dataset"]).lower())

    # ---- planner notice ----
    notice = planner.utility_notice(variant="fcond", failure_context="Semantic", confidence=0.95)
    payload = json.loads(notice.split("```json")[1].split("```")[0])
    check("notice_json_parses", payload["failure_context"] == "Semantic")
    check("notice_soft_guidance", "prefer evidence categories with higher estimated utility"
          in notice.lower())
    check("notice_non_root_cause", "not a claim about the underlying root cause" in notice)
    hi = {p["type"] for p in payload["evidence_priority"] if p["tier"] == "HIGH"}
    check("notice_recommended_matches_high", set(payload["recommended_evidence_types"]) == hi)
    notice_g = planner.utility_notice(variant="global", failure_context="Semantic", confidence=0.95)
    pg = json.loads(notice_g.split("```json")[1].split("```")[0])
    pf = json.loads(planner.utility_notice(variant="fcond", failure_context="Framework",
                                           confidence=0.9).split("```json")[1].split("```")[0])
    check("notice_global_vs_fcond_differ", pg["evidence_priority"] != pf["evidence_priority"])
    check("notice_global_context_is_global", pg["failure_context"] == "global")

    # ---- taxonomy ----
    check("kind_map", (KIND_TO_CATEGORY["api"], KIND_TO_CATEGORY["env"],
                       KIND_TO_CATEGORY["runtime"], KIND_TO_CATEGORY["behavior"]) == ("E1", "E1", "E2", "E3"))
    e2, c2 = classify_evidence_output("Traceback (most recent call last):\n  File 'x'\nValueError: boom")
    check("classify_traceback_E2", e2 == "E2" and c2 >= 0.9)
    e1, _ = classify_evidence_output("(self, *, default_shots: 'int' = 1024, options: 'dict | None' = None)")
    check("classify_ctor_sig_E1", e1 == "E1")
    e3, _ = classify_evidence_output("{'00': 552, '01': 472}")
    check("classify_counts_E3", e3 == "E3")
    eu, cu = classify_evidence_output("")
    check("classify_empty_unknown", eu == "Unknown" and cu <= 0.3)

    # ---- probe normalization (reused from frozen branch) ----
    acc, rej = _normalize_queries([
        "print(1)", {"kind": "api", "query": "print(2)"}, "print(1)",
        {"kind": "bogus", "query": "print(3)"}, "", "print(4)", "print(5)", "print(6)",
    ])
    check("normalize_cap5", len(acc) == 5)
    check("normalize_dedup", any(r.get("reason") == "duplicate query (already in this batch)" for r in rej))
    check("normalize_kind_cleared", all(a["kind"] in ("", "api", "behavior", "runtime", "env") for a in acc))
    check("normalize_empty_rejected", any("empty query" in r.get("reason", "") for r in rej))

    # ---- trace records ----
    tr = ftrace.new_episode_trace()
    ftrace.record_probes(tr, round_no=1, shot=2,
                         evidence=[{"kind": "behavior", "query": "python -c 'print(1)'",
                                    "ok": True, "status": "ok", "output": "{'00': 5}"}],
                         rejected=[{"i": 2, "reason": "empty query"}],
                         classify_output=classify_evidence_output)
    p0 = tr["probe_log"][0]
    check("trace_probe_query_kept", p0["probe_query"] == "python -c 'print(1)'")
    check("trace_requested_category", p0["requested_evidence_type"] == "E3")
    check("trace_actual_category", p0["actual_evidence_type"] == "E3")
    ftrace.record_failure(tr, shot=2, error_message="no official submit this attempt",
                          failure_context="NoSubmit", confidence=1.0, nosubmit=True,
                          utility_prior=None, recommended=None, injected=False)
    fe = tr["failure_events"][0]
    check("trace_nosubmit_recorded", fe["nosubmit"] and not fe["priority_injected"])
    check("trace_no_root_cause_field", "root_cause" not in json.dumps(tr))

    # ---- protocol pins identical to frozen Batch-EQPA branch ----
    from exp.evidence_eqpa import config as bcfg
    check("pin_llm_budget", fcfg.MAX_LLM_PER_SHOT == bcfg.MAX_LLM_PER_SHOT == 16)
    check("pin_official", fcfg.MAX_OFFICIAL == bcfg.MAX_OFFICIAL == 3)
    check("pin_batch_knobs", (fcfg.MAX_QUERIES_PER_BATCH, fcfg.PROBE_TIMEOUT_S,
                              fcfg.PROBE_MAX_CHARS, fcfg.MAX_PROBES_PER_SHOT) ==
          (bcfg.MAX_QUERIES_PER_BATCH, bcfg.PROBE_TIMEOUT_S, bcfg.PROBE_MAX_CHARS,
           bcfg.MAX_PROBES_PER_SHOT))
    check("pin_system_soft_guidance", "soft guidance" in fcfg.FCEA_SYSTEM)
    check("pin_system_root_cause_disclaimer", "not a root-cause claim" in fcfg.FCEA_SYSTEM)
    check("pin_tool_schema_shared", fcfg.FCEA_TOOL is bcfg.BATCH_TOOL)

    # ---- DEU-v2 Phase 2: EMA marginal utility update ----
    from exp.fcea.utility.updater import DynamicUtilityUpdater, q0_from_prior
    from exp.fcea.utility.state import DynamicEvidenceStateManager
    fake_prior = {"global": {"cells": {e: {"U_recovery": v} for e, v in
                                         (("E1", 0.4386), ("E2", 0.3571),
                                          ("E3", 0.3469), ("E4", 0.0909))}}}
    q0 = q0_from_prior(fake_prior)
    check("deu_q0_from_prior", q0 == {"E1": 0.4386, "E2": 0.3571, "E3": 0.3469, "E4": 0.0909})
    check("deu_q0_live_prior", abs(uprior.global_q0()["E1"] - 0.4386) < 1e-3)
    up = DynamicUtilityUpdater(q0, fcfg.DEU_CONSTANTS)
    rec = up.update_step(progress_score=1, step_state_change=True,
                         category_novelties={"E1": [1, 1]}, no_progress_count=0)
    # R = 0.5*1 + 0.5*1 = 1 ; Q(E1) = 0.7*0.4386 + 0.3*1 = 0.60702
    check("deu_ema_positive", rec["marginal_utility_after"]["E1"] == 0.607
          and rec["reward"] == 1.0 and rec["outcome_novelty"]["E1"] == 1.0)
    rec = up.update_step(progress_score=-1, step_state_change=False,
                         category_novelties={"E2": [1]}, no_progress_count=0)
    # outcome novelty gated to 0 by state_change=False; R = -0.5
    # Q(E2) = 0.7*0.3571 + 0.3*(-0.5) = 0.09997
    check("deu_ema_negative_gated", rec["outcome_novelty"]["E2"] == 0.0
          and rec["marginal_utility_after"]["E2"] == 0.1)
    rec = up.update_step(progress_score=0, step_state_change=True,
                         category_novelties={"E3": [0, 1]}, no_progress_count=2)
    # R = 0.5*0 + 0.5*0.5 = 0.25 ; Q(E3) = 0.7*0.3469 + 0.3*0.25 = 0.31783
    # then decay x0.8 (no_progress=2): 0.254264 -> 0.2543
    check("deu_ema_neutral_then_decay", rec["marginal_utility_after"]["E3"] == 0.2543,
          f"got {rec['marginal_utility_after'].get('E3')}")
    up.Q["E4"] = 0.06
    up.update_step(progress_score=0, step_state_change=False,
                   category_novelties={}, no_progress_count=5)
    check("deu_decay_floor", up.Q["E4"] == 0.05, f"got {up.Q['E4']}")

    # same-code KL worsening must stay neutral (noise, task 31 symmetric case)
    st2 = DynamicEvidenceStateManager()
    st2.on_eval_result(shot=1, passed=False,
                       error_message="KLMismatch: KL=25.0 threshold=0.05", code="def a():\n    return 1\n")
    st2.on_code_submitted("def a():\n    return 1\n")
    st2.on_eval_result(shot=2, passed=False,
                       error_message="KLMismatch: KL=30.0 threshold=0.05", code="def a():\n    return 1\n")
    check("deu_same_code_worse_neutral", st2.last_progress_score == 0,
          f"got {st2.last_progress_score}")

    # ---- DEU-v2 Phase 3: soft guidance ----
    check("deu_kind_routine", planner.deu_kind(0, 0) == "routine"
          and planner.deu_kind(1, 1) == "routine")
    check("deu_kind_saturation", planner.deu_kind(2, 0) == "saturation_warning"
          and planner.deu_kind(0, 2) == "saturation_warning")
    n_sat = planner.marginal_notice(kind="saturation_warning",
                                    Q={"E1": 0.47, "E2": 0.325, "E3": 0.347, "E4": 0.091},
                                    state_hint={"no_progress_count": 2,
                                                "consecutive_uninformative_probes": 2})
    check("deu_saturation_text", "limited state change" in n_sat
          and "reassessing current strategy" in n_sat)
    check("deu_notice_json", "marginal_utility" in json.loads(
        n_sat.split("```json")[1].split("```")[0]))
    check("deu_notice_soft_line", "prefer evidence categories with higher estimated utility"
          in n_sat.lower())
    check("deu_notice_non_root_cause", "not a claim about the underlying root cause" in n_sat)
    low = n_sat.lower()
    check("deu_notice_no_directive", all(d not in low for d in planner.FORBIDDEN_DIRECTIVES))
    n_r = planner.marginal_notice(kind="routine", Q={"E1": 0.44, "E2": 0.35},
                                  state_hint={"no_progress_count": 0})
    check("deu_routine_no_saturation", "limited state change" not in n_r)
    ad = planner.classify_adoption(["E1", "E3"], ["E1", "E3"], code_changed=False)
    check("deu_adoption_not_followed", ad["followed"] is False and ad["switched_category"] is False)
    ad = planner.classify_adoption(["E1"], ["E1", "E2"], code_changed=True, next_passed=True)
    check("deu_adoption_followed", ad["followed"] is True and ad["switched_category"] is True)

    # ---- DEU-v2 Phase 1: state tracking ----
    from exp.fcea.utility.state import (DynamicEvidenceStateManager, norm_err,
                                        output_novelty, numeric_signal, code_change_ratio)
    fcfg.set_variant("deu")
    check("tag_deu_variant", fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_deu")
    st = DynamicEvidenceStateManager()
    st.on_eval_result(shot=1, passed=False,
                      error_message="KLMismatch: KL=26.245 threshold=0.05", code="def a():\n    return 1\n")
    st.on_code_submitted("def a():\n    return 1\n")
    r2 = st.on_eval_result(shot=2, passed=False,
                           error_message="KLMismatch: KL=26.2448 threshold=0.05",
                           code="def a():\n    return 1 \n")  # whitespace-only change
    check("deu_same_error_same_code", st.error_transition == "same"
          and r2["code_changed"] is False and st.no_progress_count == 1)
    check("deu_task31_noise_not_progress", st.last_progress_score == 0,
          "same-code KL flip must not count as progress")
    r3 = st.on_eval_result(shot=3, passed=False,
                           error_message="KLMismatch: KL=12.8 threshold=0.05",
                           code="def a():\n    return 42\n")
    check("deu_kl_improved_with_code_change", st.error_transition == "improved"
          and st.last_progress_score == 1 and r3["code_changed"] is True
          and st.no_progress_count == 0)
    r4 = st.on_eval_result(shot=4, passed=False,
                           error_message="KLMismatch: KL=25.0 threshold=0.05",
                           code="def b():\n    return 7\n")
    check("deu_kl_worse_minus1", st.last_progress_score == -1 and st.error_transition == "worse")
    r5 = st.on_eval_result(shot=5, passed=False,
                           error_message="AssertionError: x != y", code="def c():\n    pass\n")
    check("deu_unclear_zero", st.last_progress_score == 0 and st.error_transition == "unclear")
    st.on_eval_result(shot=6, passed=False, error_message="no official submit this attempt",
                      code="def c():\n    pass\n", nosubmit=True)
    check("deu_nosubmit_recorded", st.submission_status["nosubmit_events"] == 1
          and st.error_transition == "same")
    check("deu_pressures", st.on_shot_state(10, 16)["submit_pressure"] == 0.625
          and st.on_shot_state(5, 16)["submit_pressure_high"] is False)
    snap = st.snapshot()
    check("deu_snapshot_fields", all(k in snap for k in (
        "current_error", "previous_error", "error_transition", "code_hash",
        "previous_code_hash", "code_change_ratio", "evidence_history",
        "evidence_novelty_history", "no_progress_count", "same_error_count",
        "submission_status")))

    nov = []
    seen: set = set()
    nov.append(output_novelty("", seen))
    nov.append(output_novelty("stderr: Traceback (most recent call last):", seen))
    nov.append(output_novelty("{'00': 552, '01': 472}", seen))
    nov.append(output_novelty("{'00': 552, '01': 472}", seen))  # duplicate
    nov.append(output_novelty("{'01': 1024}", seen))
    check("deu_output_novelty_sequence", nov == [0, 0, 1, 0, 1], f"got {nov}")
    check("deu_numeric_signal", numeric_signal("KLMismatch: KL=27.631 threshold=0.05") == 27.631)
    check("deu_norm_err_stable", norm_err("KL=1.0 at /a/b/c.py") == norm_err("KL=1.0 at /x/y.py"))
    check("deu_code_ratio_threshold", code_change_ratio("abcdefg", "abcdefg") == 1.0)

    # V2/V3 regression guard: variants untouched by Phase 1
    check("v2_tiers_intact", uprior.tiers_for("global", "Semantic") ==
          {"E1": "HIGH", "E2": "MEDIUM", "E3": "MEDIUM", "E4": "LOW"})
    fcfg.set_variant("fcond")
    check("variant_restore", fcfg.VARIANT == "fcond")

    # ---- DEU-v3 Action Adapter (PoC): pure logic, no LLM ----
    from exp.fcea.adapter import ActionAdapter, STRATEGY_SWITCH_TEXT, STOP_EXPLORE_TEXT
    fcfg.set_variant("deu3")
    check("tag_deu3_variant", fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_deu3")
    check("deu3_threshold_defaults", fcfg.DEU3_CONSTANTS["strategy_same_error_threshold"] == 2
          and fcfg.DEU3_CONSTANTS["stop_no_progress_threshold"] == 2
          and abs(fcfg.DEU3_CONSTANTS["utility_drop_threshold"] - 0.046) < 1e-9)
    ad = ActionAdapter()
    common = dict(step=2, boundary_kind="error", task_id="03",
                  error_transition="same", error_message="no official submit this attempt",
                  code_changed=False, attempts_left=1)
    # Action 1: strategy switch on same-error stagnation with low novelty
    msg, ev = ad.on_boundary(**common, same_error_count=2, no_progress_count=0,
                             novelty_mean_now=0.0, novelty_mean_prev=0.4, utility_drop=0.0)
    check("adapter_strategy_switch", msg is not None and STRATEGY_SWITCH_TEXT in msg
          and ev["action_type"] == ["strategy_switch"], f"types={ev['action_type']}")
    check("adapter_event_schema", all(k in ev for k in (
        "step_id", "task_id", "action_type", "trigger_signal", "utility_state",
        "error_state", "message_sent")), "missing event fields")
    # Action 2: explore/stop on no-progress with a large utility drop
    msg2, ev2 = ad.on_boundary(**common, same_error_count=0, no_progress_count=2,
                               novelty_mean_now=0.5, novelty_mean_prev=0.5,
                               utility_drop=0.096)
    check("adapter_explore_stop", msg2 is not None and STOP_EXPLORE_TEXT in msg2
          and ev2["action_type"] == ["explore_stop"], f"types={ev2['action_type']}")
    # no trigger: healthy state (progress made, novelty present, small drop)
    msg3, ev3 = ad.on_boundary(**common, same_error_count=0, no_progress_count=0,
                               novelty_mean_now=0.6, novelty_mean_prev=0.4,
                               utility_drop=0.01)
    check("adapter_no_trigger_healthy", msg3 is None and ev3["action_type"] == []
          and ev3["message_sent"] is False)
    # stop-pressure requires the utility drop, not just no-progress
    msg4, _ = ad.on_boundary(**common, same_error_count=0, no_progress_count=2,
                             novelty_mean_now=0.0, novelty_mean_prev=0.0,
                             utility_drop=0.0)
    check("adapter_stop_needs_utility_drop", msg4 is None)
    # strategy-switch fires on the NoSubmit boundary too (the PoC's reach point)
    msg5, ev5 = ad.on_boundary(**{**common, "boundary_kind": "nosubmit"},
                               same_error_count=2, no_progress_count=2,
                               novelty_mean_now=0.0, novelty_mean_prev=0.0,
                               utility_drop=0.12)
    check("adapter_nosubmit_reach", msg5 is not None
          and ev5["boundary_kind"] == "nosubmit"
          and sorted(ev5["action_type"]) == ["explore_stop", "strategy_switch"])
    # both thresholds configurable
    ad2 = ActionAdapter({"strategy_same_error_threshold": 5, "stop_no_progress_threshold": 3})
    msg6, _ = ad2.on_boundary(**common, same_error_count=2, no_progress_count=2,
                              novelty_mean_now=0.0, novelty_mean_prev=0.0,
                              utility_drop=0.12)
    check("adapter_thresholds_configurable", msg6 is None)
    fcfg.set_variant("fcond")

    # ---- DEU-v3-ACT Action Selector (rule-based) + random ablation ----
    from exp.fcea.action_selector import (ActionSelector, RandomActionSelector,
                                          action_message, ACTIONS)
    fcfg.set_variant("deuact")
    check("tag_deuact_variant", fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_deuact")
    sel = ActionSelector()
    base = dict(code_changed=False)
    Q = {"E1": 0.457, "E2": 0.266, "E3": 0.393, "E4": 0.091}
    # task-03 phenotype: no_progress=2 + large utility drop -> FINALIZE (precedence)
    d1 = sel.select(no_progress_count=2, same_error_count=2, novelty_mean_now=0.0,
                    novelty_mean_prev=0.0, utility_drop=0.107, Q=Q,
                    current_family="E2", **base)
    check("act_task03_finalize", d1["action"] == "FINALIZE", d1["reason"])
    check("act_finalize_message", action_message(d1) is not None
          and "No additional probing" in action_message(d1))
    # task-32 phenotype (step 2): counters reset, but utility gap -> SWITCH_EVIDENCE
    # (rule: switch TO the argmax family when the current family lags by > delta)
    d2 = sel.select(no_progress_count=0, same_error_count=0, novelty_mean_now=0.0833,
                    novelty_mean_prev=0.91667, utility_drop=0.0963, Q=Q,
                    current_family="E2", **base)
    check("act_task32_switch_evidence", d2["action"] == "SWITCH_EVIDENCE"
          and d2["focus_family"] == "E1", d2["reason"])
    check("act_switch_message", "E1" in (action_message(d2) or "")
          and "api" in (action_message(d2) or ""))
    # SWITCH_STRATEGY: same-error stagnation with falling novelty, no drop gate
    d3 = sel.select(no_progress_count=0, same_error_count=2, novelty_mean_now=0.05,
                    novelty_mean_prev=0.4, utility_drop=0.0, Q=Q,
                    current_family="E3", **base)
    check("act_switch_strategy", d3["action"] == "SWITCH_STRATEGY", d3["reason"])
    # CONTINUE when the current family IS the argmax (never switch away from best)
    d4 = sel.select(no_progress_count=0, same_error_count=0, novelty_mean_now=0.6,
                    novelty_mean_prev=0.4, utility_drop=0.0, Q=Q,
                    current_family="E1", **base)
    check("act_continue_at_argmax", d4["action"] == "CONTINUE"
          and action_message(d4) is None)
    # a lagging family on a healthy step still switches (rule is utility-gated,
    # not stagnation-gated)
    d4b = sel.select(no_progress_count=0, same_error_count=0, novelty_mean_now=0.6,
                     novelty_mean_prev=0.4, utility_drop=0.0, Q=Q,
                     current_family="E3", **base)
    check("act_switch_on_utility_gap", d4b["action"] == "SWITCH_EVIDENCE"
          and d4b["focus_family"] == "E1", d4b["reason"])
    # no probes -> no current family -> cannot SWITCH_EVIDENCE
    d5 = sel.select(no_progress_count=0, same_error_count=0, novelty_mean_now=None,
                    novelty_mean_prev=None, utility_drop=0.0, Q=Q,
                    current_family=None, **base)
    check("act_no_family_continue", d5["action"] == "CONTINUE")
    # finalization needs the utility drop, not just no-progress
    d6 = sel.select(no_progress_count=2, same_error_count=0, novelty_mean_now=0.0,
                    novelty_mean_prev=0.0, utility_drop=0.0, Q=Q,
                    current_family="E2", **base)
    check("act_finalize_needs_drop", d6["action"] != "FINALIZE")
    # random ablation: seeded determinism + valid action + no utility sensitivity
    rs = RandomActionSelector()
    seq1 = [rs.select(**base)["action"] for _ in range(12)]
    rs2 = RandomActionSelector()
    seq2 = [rs2.select(**base)["action"] for _ in range(12)]
    check("act_random_seeded", seq1 == seq2
          and all(a in ACTIONS for a in seq1) and len(set(seq1)) > 1)
    # repetition runs: seed override changes the random stream, None keeps the
    # frozen 20260923, and the override does not touch the rule selector
    eff = fcfg.set_action_seed(20260924)
    rs3 = RandomActionSelector(fcfg.DEUACT_CONSTANTS)
    seq3 = [rs3.select(**base)["action"] for _ in range(12)]
    check("act_seed_override", eff == 20260924 and seq1 != seq3)
    eff2 = fcfg.set_action_seed(None)
    rs4 = RandomActionSelector(fcfg.DEUACT_CONSTANTS)
    seq4 = [rs4.select(**base)["action"] for _ in range(12)]
    check("act_seed_default_kept", eff2 == 20260923 and seq4 == seq1)

    # ---- DEU-RC: RCI computation ----
    rci = compute_rci(Q={"E1": 0.5, "E2": 0.3, "E3": 0.4}, progress_score=1,
                      novelty_mean=0.5, no_progress_count=0, same_error_count=0,
                      utility_drop=0.0)
    check("rc_rci_computation", abs(rci["rci"] - (
        0.40 * 0.4 + 0.20 * 1.0 + 0.15 * 0.5)) < 1e-6
        and set(rci["components"]) == {"utility", "progress", "novelty",
                                       "stagnation", "utility_drop"},
        str(rci))
    rci_hi = compute_rci(Q={"E1": 2.0, "E2": 2.0, "E3": 2.0}, progress_score=1,
                         novelty_mean=2.0, no_progress_count=99,
                         same_error_count=99, utility_drop=99.0)
    check("rc_rci_bounded", 0.0 <= rci_hi["rci"] <= 1.0
        and rci_hi["components"]["stagnation"] == 1.0
        and rci_hi["components"]["utility_drop"] == 1.0, str(rci_hi))

    # ---- DEU-RC: mode priority TERMINATE > ESCAPE > FOCUS > SEARCH ----
    branches = EvidenceBranchState(dict(fcfg.DEURC_CONSTANTS))
    mk = lambda fam, fails, status: {"family": fam, "failures": fails,
                                     "status": status}
    sel = select_mode(no_progress_count=2, utility_drop=0.05,
                      escape_worthy_family=mk("E2", 3, BLOCKED),
                      best_q=0.9, evidence_samples=9,
                      constants=fcfg.DEURC_CONSTANTS)
    check("rc_mode_terminate_first", sel["mode"] == TERMINATE, sel["reason"])
    sel = select_mode(no_progress_count=0, utility_drop=0.0,
                      escape_worthy_family=mk("E2", 3, BLOCKED),
                      best_q=0.9, evidence_samples=9,
                      constants=fcfg.DEURC_CONSTANTS)
    check("rc_mode_escape_over_focus", sel["mode"] == ESCAPE, sel["reason"])
    sel = select_mode(no_progress_count=0, utility_drop=0.0,
                      escape_worthy_family=None, best_q=0.5,
                      evidence_samples=6, constants=fcfg.DEURC_CONSTANTS)
    check("rc_mode_focus", sel["mode"] == FOCUS, sel["reason"])
    sel = select_mode(no_progress_count=0, utility_drop=0.0,
                      escape_worthy_family=None, best_q=0.1,
                      evidence_samples=1, constants=fcfg.DEURC_CONSTANTS)
    check("rc_mode_search_default", sel["mode"] == SEARCH, sel["reason"])

    # ---- DEU-RC: error signatures (task 32 oscillation: KL / ValueError / KL) ----
    kl1 = error_signature("KL = 0.31234, target 0.1")
    kl2 = error_signature("KL = 0.29876, target 0.1")
    ve = error_signature("ValueError: bad shape")
    check("rc_signature_kl_drift_same", kl1 == kl2 and kl1 != ve, f"{kl1}|{kl2}|{ve}")

    # ---- DEU-RC: branch blocking + reversibility ----
    br = EvidenceBranchState(dict(fcfg.DEURC_CONSTANTS))
    for msg in ("KL = 0.31", "ValueError: bad", "KL = 0.29"):
        rec = br.on_failure(evidence_used={"E2": 4}, error_message=msg,
                            family_novelty_now=0.0, family_novelty_prev=0.2)
    e2 = br.branches["E2"]
    check("rc_branch_oscillation_accumulates", e2["failures"] == 3
        and e2["status"] == BLOCKED and e2["seen_signatures"][0] == e2["seen_signatures"][2],
        json.dumps(rec))
    check("rc_branch_blocked_excluded", "E2" in br.blocked_families()
        and br.allowed_families() == ["E1", "E3"]
        and br.escape_worthy()["family"] == "E2")
    # controller order: failure update first (its recovery scan only promotes
    # families ALREADY in RECOVERABLE), then the recovery scan
    # (BLOCKED -> RECOVERABLE on a new signature); the NEXT boundary's
    # failure update then promotes RECOVERABLE -> ACTIVE
    rec = br.on_failure(evidence_used={"E1": 2}, error_message="TypeError: new path",
                        family_novelty_now=None, family_novelty_prev=None)
    moved = br.on_recovery_evidence("TypeError: new path")
    check("rc_branch_recoverable_on_new_signature",
        moved == ["E2"] and br.branches["E2"]["status"] == RECOVERABLE,
        json.dumps(rec))
    rec = br.on_failure(evidence_used={"E1": 1}, error_message="KeyError: other new",
                        family_novelty_now=None, family_novelty_prev=None)
    check("rc_branch_recoverable_to_active",
        br.branches["E2"]["status"] == ACTIVE, json.dumps(rec))

    # ---- DEU-RC: context gate (turn-atomic pruning) ----
    ev_turns: list[dict] = []
    for i in range(5):
        ev_turns += [
            {"role": "assistant", "content": "th%d" % i,
             "tool_calls": [{"id": str(i)}]},
            {"role": "tool", "tool_call_id": str(i), "name": "BatchProbe",
             "content": "ev%d" % i}]
    msgs = ([{"role": "system", "content": "sys"},
             {"role": "user", "content": "task"}]
            + ev_turns
            + [{"role": "assistant", "content": "write", "tool_calls": [{"id": "w"}]},
               {"role": "tool", "tool_call_id": "w", "name": "Write", "content": "ok"},
               {"role": "user", "content": "feedback"}])
    seg = segment_turns(msgs)
    check("rc_context_segmentation", len(seg["header"]) == 2
        and [t["kind"] for t in seg["turns"]] == ["evidence"] * 5 + ["patch", "notice"])
    kept, stats = context_gate.assemble(FOCUS, msgs, constants=fcfg.DEURC_CONSTANTS)
    tools_kept = [m.get("name") for m in kept if m.get("role") == "tool"]
    check("rc_context_focus_keeps_newest_evidence",
        tools_kept == ["BatchProbe", "BatchProbe", "Write"]
        and stats["turns_kept"] < stats["turns_before"] and stats["reduction_ratio"] > 0,
        json.dumps(stats))
    for m in kept:
        if m.get("role") == "tool":
            prev = kept[kept.index(m) - 1]
            check("rc_context_tool_paired", prev.get("role") == "assistant")
            break
    kept_esc, _ = context_gate.assemble(ESCAPE, msgs)
    check("rc_context_escape_drops_evidence",
        not any(m.get("name") == "BatchProbe" for m in kept_esc)
        and any(m.get("role") == "user" for m in kept_esc))
    kept_fin, _ = context_gate.assemble(TERMINATE, msgs)
    check("rc_context_final_keeps_best_candidate",
        any(m.get("name") == "Write" for m in kept_fin)
        and not any(m.get("name") == "BatchProbe" for m in kept_fin))
    kept_full, _ = context_gate.assemble(SEARCH, msgs)
    check("rc_context_search_full", kept_full == msgs)

    # ---- DEU-RC: controller end-to-end + record serialization + ablations ----
    ctrl = RepairController(fcfg.DEURC_CONSTANTS)
    recs = []
    for i, (np_c, drop, nov) in enumerate([(0, 0.0, 0.5), (1, 0.02, 0.2),
                                           (2, 0.06, 0.0)]):
        recs.append(ctrl.on_boundary(
            step=i + 1, boundary_kind="error", task_id="t",
            no_progress_count=np_c, same_error_count=np_c, code_changed=False,
            progress_score=0, novelty_mean_now=nov, novelty_mean_prev=0.5,
            family_novelty_now={"E2": nov}, family_novelty_prev={"E2": 0.5},
            utility_drop=drop, Q={"E1": 0.4, "E2": 0.3, "E3": 0.35},
            evidence_used={"E2": 3}, evidence_samples=6,
            error_message="KL = 0.3%d" % i, ts=None))
    check("rc_controller_mode_sequence",
          [r["repair_mode"] for r in recs] == [FOCUS, ESCAPE, TERMINATE]
          and all(isinstance(r["rci"], float) for r in recs)
          and recs[-1]["allowed_actions"] == ["Write", "Eval"]
          and ctrl.probe_withdrawn(),
          json.dumps([r["repair_mode"] for r in recs]))
    try:
        json.dumps(recs)
        check("rc_record_serializable", True)
    except (TypeError, ValueError) as exc:
        check("rc_record_serializable", False, str(exc))
    check("rc_controller_log_appended", len(ctrl.control_log) == 3)

    ab = RepairController({**fcfg.DEURC_CONSTANTS,
                           "enable_mode_controller": False,
                           "enable_evidence_gate": False,
                           "enable_context_gate": False})
    ra = ab.on_boundary(step=1, boundary_kind="error", task_id="t",
                        no_progress_count=3, same_error_count=3, code_changed=False,
                        progress_score=0, novelty_mean_now=0.0,
                        novelty_mean_prev=0.0, family_novelty_now={"E2": 0.0},
                        family_novelty_prev={"E2": 0.0}, utility_drop=0.5,
                        Q={"E2": 0.1}, evidence_used={"E2": 3},
                        evidence_samples=9, error_message="x", ts=None)
    check("rc_ablation_mode_off", ra["repair_mode"] == SEARCH
        and ra["message_sent"] is False and not ab.probe_withdrawn())
    check("rc_ablation_gates_off", ra["blocked_evidence"] == []
        and ra["context_policy"] == "disabled")

    # ---- DEU-RC Phase 2.2: ESCAPE ablation (deurc_noescape) ----
    esc_kwargs = dict(no_progress_count=0, utility_drop=0.0,
                      escape_worthy_family={"family": "E2", "failures": 3,
                                            "status": BLOCKED},
                      best_q=0.5, evidence_samples=6)
    sel = select_mode_noescape(**esc_kwargs, constants=fcfg.DEURC_CONSTANTS)
    check("rc_noescape_escape_to_focus", sel["mode"] == FOCUS
        and sel["original_mode"] == "ESCAPE" and sel["escape_blocked"] is True,
        json.dumps(sel))
    sel = select_mode_noescape(no_progress_count=0, utility_drop=0.0,
                               escape_worthy_family={"family": "E2",
                                                     "failures": 3,
                                                     "status": BLOCKED},
                               best_q=0.1, evidence_samples=1,
                               constants=fcfg.DEURC_CONSTANTS)
    check("rc_noescape_escape_to_search", sel["mode"] == SEARCH
        and sel["escape_blocked"] is True, json.dumps(sel))
    sel = select_mode_noescape(no_progress_count=2, utility_drop=0.05,
                               escape_worthy_family=None, best_q=0.9,
                               evidence_samples=6,
                               constants=fcfg.DEURC_CONSTANTS)
    check("rc_noescape_terminate_kept", sel["mode"] == TERMINATE
        and sel["escape_blocked"] is False)

    ne = RepairController({**fcfg.DEURC_CONSTANTS, "enable_escape_mode": False})
    bkw = dict(boundary_kind="error", task_id="t", code_changed=False,
               progress_score=0, novelty_mean_now=0.2, novelty_mean_prev=0.5,
               family_novelty_now={"E2": 0.2}, family_novelty_prev={"E2": 0.5},
               utility_drop=0.02, Q={"E1": 0.4, "E2": 0.3, "E3": 0.35},
               evidence_used={"E2": 3}, evidence_samples=6,
               error_message="KL = 0.31", ts=None)
    ne.on_boundary(step=1, no_progress_count=1, same_error_count=1, **bkw)
    rn = ne.on_boundary(step=2, no_progress_count=1, same_error_count=2, **bkw)
    check("rc_noescape_controller_blocks_escape",
        rn["repair_mode"] == FOCUS and rn["original_mode"] == "ESCAPE"
        and rn["escape_blocked"] is True and rn["same_error_count"] == 2
        and "selected_mode" in rn, json.dumps({k: rn[k] for k in
            ("repair_mode", "original_mode", "escape_blocked")}))
    # frozen deurc flag: identical boundary still yields ESCAPE
    rc = RepairController(fcfg.DEURC_CONSTANTS)
    rc.on_boundary(step=1, no_progress_count=1, same_error_count=1, **bkw)
    rr = rc.on_boundary(step=2, no_progress_count=1, same_error_count=2, **bkw)
    check("rc_noescape_flag_default_keeps_escape",
        rr["repair_mode"] == ESCAPE and rr["original_mode"] == "ESCAPE"
        and rr["escape_blocked"] is False)

    # ---- DEU-RC Phase 2.2 Exp2: soft FOCUS ----
    sf = RepairController({**fcfg.DEURC_CONSTANTS, "focus_hard_restriction": False})
    sf.on_boundary(step=1, boundary_kind="error", task_id="t",
                   no_progress_count=1, same_error_count=1, code_changed=False,
                   progress_score=0, novelty_mean_now=0.0, novelty_mean_prev=0.2,
                   family_novelty_now={"E2": 0.0}, family_novelty_prev={"E2": 0.2},
                   utility_drop=0.01, Q={"E1": 0.5, "E2": 0.3, "E3": 0.4},
                   evidence_used={"E2": 3}, evidence_samples=6,
                   error_message="ValueError: x", ts=None)
    rsf = sf.on_boundary(step=2, boundary_kind="error", task_id="t",
                         no_progress_count=2, same_error_count=2,
                         code_changed=False, progress_score=0,
                         novelty_mean_now=0.3, novelty_mean_prev=0.2,
                         family_novelty_now={"E2": 0.3},
                         family_novelty_prev={"E2": 0.2}, utility_drop=0.02,
                         Q={"E1": 0.5, "E2": 0.3, "E3": 0.4},
                         evidence_used={"E2": 5}, evidence_samples=9,
                         error_message="ValueError: y", ts=None)
    check("rc_softfocus_focus_probe_available",
        rsf["repair_mode"] == FOCUS and not sf.probe_withdrawn()
        and "BatchProbe" in rsf["allowed_actions"],
        json.dumps(rsf["allowed_actions"]))
    fe = rsf.get("focus_evidence") or {}
    check("rc_softfocus_focus_evidence_log",
        fe.get("preferred_family") == "E1"
        and fe.get("hard_removed_evidence") == ["E2", "E3"]
        and fe.get("soft_penalty_evidence") == ["E2", "E3"]
        and fe.get("selected_evidence") == "E1"
        and fe.get("hard_restriction") is False
        and fe.get("before_evidence", {}).get("E2") == 5, json.dumps(fe))
    check("rc_softfocus_directive_soft",
        "Preferred evidence family" in (rsf.get("message_text") or ""))
    # hard policy (frozen deurc): FOCUS still withdraws the tool
    hard = RepairController(fcfg.DEURC_CONSTANTS)
    hard.current_mode = FOCUS
    check("rc_softhocus_hard_default_withdraws", hard.probe_withdrawn() is True)
    # TERMINATE withdrawal regardless of policy
    sf.current_mode = TERMINATE
    check("rc_softfocus_terminate_still_withdraws",
        sf.probe_withdrawn() is True)

    # ---- DEU-RC Phase 2.2 joint relaxation (both flags) ----
    jr = RepairController(fcfg.DEURC_JOINTRELAX_CONSTANTS)
    jr.on_boundary(step=1, no_progress_count=1, same_error_count=1, **bkw)
    rj = jr.on_boundary(step=2, no_progress_count=1, same_error_count=2, **bkw)
    check("rc_jointrelax_escape_blocked_focus_soft",
        rj["repair_mode"] == FOCUS and rj["original_mode"] == "ESCAPE"
        and rj["escape_blocked"] is True and not jr.probe_withdrawn()
        and "BatchProbe" in rj["allowed_actions"]
        and (rj.get("focus_evidence") or {}).get("hard_restriction") is False,
        json.dumps({k: rj[k] for k in ("repair_mode", "original_mode",
                                       "escape_blocked")}))
    # joint + escape impossible + hard task => SEARCH, no withdrawal
    jr2 = RepairController(fcfg.DEURC_JOINTRELAX_CONSTANTS)
    rj2 = jr2.on_boundary(step=1, boundary_kind="error", task_id="t",
                          no_progress_count=0, same_error_count=0,
                          code_changed=False, progress_score=0,
                          novelty_mean_now=0.1, novelty_mean_prev=0.1,
                          family_novelty_now={"E2": 0.1},
                          family_novelty_prev={"E2": 0.1}, utility_drop=0.0,
                          Q={"E1": 0.1, "E2": 0.1, "E3": 0.1},
                          evidence_used={"E2": 1}, evidence_samples=1,
                          error_message="ValueError: z", ts=None)
    check("rc_jointrelax_search_default",
        rj2["repair_mode"] == SEARCH and not jr2.probe_withdrawn())

    # ---- DEU-RC Phase 2.2 context preservation (noctx) ----
    nctx = RepairController(fcfg.DEURC_NOCTX_CONSTANTS)
    nctx.current_mode = ESCAPE           # worst-case pruning policy
    msgs = [{"role": "system", "content": "s"}]
    msgs += [{"role": "user", "content": "u%d" % i} for i in range(6)]
    kept, stats = nctx.assemble_context(msgs)
    check("rc_noctx_context_preserved", kept == msgs
        and stats["context_policy"] == "disabled"
        and stats["reduction_ratio"] == 0.0)
    rnctx = nctx.on_boundary(step=1, boundary_kind="nosubmit", task_id="t",
                             no_progress_count=2, same_error_count=2,
                             code_changed=False, progress_score=0,
                             novelty_mean_now=0.0, novelty_mean_prev=0.1,
                             family_novelty_now={}, family_novelty_prev={},
                             utility_drop=0.06, Q={"E1": 0.4, "E2": 0.3},
                             evidence_used={}, evidence_samples=0,
                             error_message="no official submit", ts=None)
    check("rc_noctx_decision_still_active",
        rnctx["repair_mode"] == TERMINATE
        and rnctx["context_policy"] == "disabled"
        and nctx.probe_withdrawn() is True)

    # ---- DEU-RC Phase 2.2 interaction test (noctx + joint relaxation) ----
    nj = RepairController(fcfg.DEURC_NOCTX_JOINT_CONSTANTS)
    bkw2 = dict(boundary_kind="error", task_id="t", code_changed=False,
                progress_score=0, novelty_mean_now=0.2, novelty_mean_prev=0.5,
                family_novelty_now={"E2": 0.2}, family_novelty_prev={"E2": 0.5},
                utility_drop=0.02, Q={"E1": 0.4, "E2": 0.3, "E3": 0.35},
                evidence_used={"E2": 3}, evidence_samples=6,
                error_message="KL = 0.31", ts=None)
    nj.on_boundary(step=1, no_progress_count=1, same_error_count=1, **bkw2)
    rnj = nj.on_boundary(step=2, no_progress_count=1, same_error_count=2, **bkw2)
    msgs = [{"role": "system", "content": "s"}]
    msgs += [{"role": "user", "content": "m%d" % i} for i in range(5)]
    kept, kstats = nj.assemble_context(msgs)
    check("rc_noctxjoint_escape_blocked_soft_focus_full_context",
        rnj["repair_mode"] == FOCUS and rnj["original_mode"] == "ESCAPE"
        and rnj["escape_blocked"] is True
        and not nj.probe_withdrawn()
        and "BatchProbe" in rnj["allowed_actions"]
        and kept == msgs and kstats["context_policy"] == "disabled"
        and kstats["reduction_ratio"] == 0.0,
        json.dumps({k: rnj[k] for k in ("repair_mode", "original_mode",
                                        "escape_blocked")}))

    fcfg.set_variant("fcond")

    # ---- RQ3 Phase B: D2 clean (full − C2) noise surrogate ----
    from exp.fcea.utility.noise import (NoiseUtilitySource, d2_noise_seed,
                                        tiers_from_ranking, TIER_MULTISET)
    check("d2_variant_registered", "d2_clean" in fcfg.VARIANTS
          and "d3" in fcfg.VARIANTS)
    fcfg.set_variant("d2_clean")
    check("tag_d2_variant", fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_d2_clean")
    # controller byte-identical to the full stack: the substitution is upstream
    check("d2_controller_constants_identical",
          fcfg.D2_CLEAN_CONSTANTS == fcfg.DEURC_NOCTX_CONSTANTS)
    # seed: reproducible from (tag, case_id); distinct across tasks/replicates
    s1 = d2_noise_seed(tag="rq4_fcea_qbplus_d2_clean", case_id="03")
    s2 = d2_noise_seed(tag="rq4_fcea_qbplus_d2_clean", case_id="03")
    s3 = d2_noise_seed(tag="rq4_fcea_qbplus_d2_clean", case_id="07")
    s4 = d2_noise_seed(tag="rq4_fcea_qbplus_d2_clean_rep2", case_id="03")
    check("d2_seed_deterministic", s1 == s2 and s1 != s3 and s1 != s4)
    n1 = NoiseUtilitySource(seed=s1)
    n2 = NoiseUtilitySource(seed=s1)
    d1a, dr1a = n1.draw()
    d1b, dr1b = n2.draw()
    check("d2_noise_seeded_stream", d1a == d1b and dr1a == dr1b)
    # matched form: same support as the real clipped EMA Q
    check("d2_noise_support", all(0.05 <= v <= 1.0 for v in d1a.values())
          and set(d1a) == {"E1", "E2", "E3", "E4"})
    for _ in range(20):
        q_t, drop_t = n1.draw()
        check_ok = all(0.05 <= v <= 1.0 for v in q_t.values()) and 0.0 <= drop_t <= 0.95
        if not check_ok:
            check("d2_noise_walk_form", False, f"q={q_t} drop={drop_t}")
            break
    else:
        check("d2_noise_walk_form", True)
    # first drop is measured against the anchor (the Q0 role)
    n3 = NoiseUtilitySource(seed=s3)
    q1, drop1 = n3.draw()
    want_drop = round(max(abs(q1[e] - n3.q_anchor[e]) for e in q1), 4)
    check("d2_first_drop_vs_anchor", drop1 == want_drop, f"{drop1} vs {want_drop}")
    # notice tiers: frozen multiset, assigned by anchor ranking
    check("d2_tier_multiset", sorted(n1.tiers.values()) == sorted(TIER_MULTISET))
    check("d2_tiers_by_rank",
          tiers_from_ranking({"E1": 0.9, "E2": 0.8, "E3": 0.5, "E4": 0.1})
          == {"E1": "HIGH", "E2": "MEDIUM", "E3": "MEDIUM", "E4": "LOW"})
    check("d2_recommended_is_high", n1.recommended ==
          sorted([e for e, t in n1.tiers.items() if t == "HIGH"]))
    # notice: byte-identical template to the real global notice, noise tiers
    real_notice = planner.utility_notice(variant="global", failure_context="Semantic",
                                         confidence=0.95)
    noise_notice = n1.notice()
    check("d2_notice_same_template",
          real_notice.split("```json")[0] == noise_notice.split("```json")[0]
          and real_notice.split("```")[2] == noise_notice.split("```")[2])
    npl = json.loads(noise_notice.split("```json")[1].split("```")[0])
    check("d2_notice_payload", npl["evidence_priority"] and
          {p["type"]: p["tier"] for p in npl["evidence_priority"]} == n1.tiers
          and sorted(npl["recommended_evidence_types"]) == n1.recommended)
    # override path leaves the frozen-prior path untouched
    check("d2_notice_override_local",
          json.loads(real_notice.split("```json")[1].split("```")[0])["evidence_priority"]
          != npl["evidence_priority"])
    fcfg.set_variant("fcond")

    # ---- RQ3 Phase B: D3 (full − C1) state blindness ----
    fcfg.set_variant("d3")
    check("tag_d3_variant", fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_d3")
    check("d3_constants_noctx_base",
          fcfg.D3_CONSTANTS["enable_context_gate"] is False
          and fcfg.D3_CONSTANTS["state_blind"] is True)
    q0 = uprior.global_q0()
    check("d3_pinned_prior_live", abs(q0["E1"] - 0.4386) < 1e-3 and "E4" in q0)
    check("d3_notice_channel_unchanged",
          uprior.tiers_for("d3", "Semantic") == uprior.tiers_for("deurc_noctx", "Semantic"))
    blind = RepairController(fcfg.D3_CONSTANTS)
    bkw_d3 = dict(boundary_kind="error", task_id="t", code_changed=False,
                  progress_score=0, novelty_mean_now=0.0, novelty_mean_prev=0.5,
                  family_novelty_now={"E2": 0.0}, family_novelty_prev={"E2": 0.5},
                  Q=q0, evidence_used={"E2": 6}, evidence_samples=9,
                  error_message="KL = 0.31", ts=None)
    # repeated failures on one family: full DEU-RC would ESCAPE here (state
    # branch gate) — blind D3 must stay inside {SEARCH, FOCUS}
    r_b1 = blind.on_boundary(step=1, no_progress_count=2, same_error_count=2,
                             utility_drop=0.0, **bkw_d3)
    r_b2 = blind.on_boundary(step=2, no_progress_count=3, same_error_count=3,
                             utility_drop=0.0, **bkw_d3)
    r_b3 = blind.on_boundary(step=3, no_progress_count=9, same_error_count=9,
                             utility_drop=0.99, **bkw_d3)
    check("d3_state_gates_unreachable",
          all(r["repair_mode"] in (SEARCH, FOCUS) for r in (r_b1, r_b2, r_b3))
          and r_b3["repair_mode"] != TERMINATE,
          json.dumps([r["repair_mode"] for r in (r_b1, r_b2, r_b3)]))
    check("d3_branches_frozen_active",
          blind.branches.blocked_families() == []
          and all(b["status"] == ACTIVE and b["failures"] == 0
                  for b in blind.branches.snapshot().values()))
    check("d3_blind_flag_logged",
          all(r["ablation_flags"]["state_blind"] is True
              for r in (r_b1, r_b2, r_b3)))
    check("d3_blind_components",
          r_b3["rci_components"]["stagnation"] == 0.0
          and r_b3["same_error_count"] == 0
          and r_b3["q_values"] == {k: round(v, 4) for k, v in q0.items()},
          json.dumps(r_b3["rci_components"]))
    # FOCUS stays reachable through the pinned utility alone
    r_f = blind.on_boundary(step=4, no_progress_count=0, same_error_count=0,
                            utility_drop=0.0, **bkw_d3)
    check("d3_focus_utility_only", r_f["repair_mode"] == FOCUS,
          r_f["mode_reason"])
    # contrast: the same inputs WITHOUT state_blind keep the frozen behavior
    sighted = RepairController(fcfg.DEURC_NOCTX_CONSTANTS)
    rs1 = sighted.on_boundary(step=1, no_progress_count=0, same_error_count=2,
                              utility_drop=0.0, **bkw_d3)
    rs2 = sighted.on_boundary(step=2, no_progress_count=0, same_error_count=3,
                              utility_drop=0.0, **bkw_d3)
    check("d3_contrast_sighted_escapes",
          rs2["repair_mode"] == ESCAPE,
          json.dumps([rs1["repair_mode"], rs2["repair_mode"]]))
    # RCI blind display: utility from pinned Q0, progress neutral, drop 0
    rci_blind = compute_rci(Q=q0, progress_score=0, novelty_mean=None,
                            no_progress_count=0, same_error_count=0,
                            utility_drop=0.0)
    check("d3_rci_blind_shape", rci_blind["components"]["progress"] == 0.5
          and rci_blind["components"]["novelty"] == 0.0
          and rci_blind["components"]["utility_drop"] == 0.0)
    fcfg.set_variant("fcond")

    # ---- Phase C prerequisite: framework parameterization (e9 pattern) ----
    check("fw_system_qiskit_byte_identical", fcfg.fcea_system("qiskit") == fcfg.FCEA_SYSTEM)
    sys_pl = fcfg.fcea_system("pennylane")
    sys_cq = fcfg.fcea_system("cirq")
    check("fw_system_swap_both_occurrences",
          sys_pl.count("PennyLane") == 2 and "Qiskit" not in sys_pl
          and sys_cq.count("Cirq") == 2 and "Qiskit" not in sys_cq)
    check("fw_system_otherwise_identical",
          fcfg.FCEA_SYSTEM.replace("Qiskit", "PennyLane") == sys_pl)
    check("fw_notice_guidance_kept", "prefer evidence categories with higher estimated utility"
          in sys_pl and "not a root-cause claim" in sys_pl)
    check("fw_tag_qiskit_layout_unchanged",
          fcfg.default_tag(bench="qbplus") == "rq4_fcea_qbplus_fcond")
    check("fw_tag_pennylane_suffix",
          fcfg.default_tag(bench="qbplus", framework="pennylane")
          == "rq4_fcea_qbplus_pennylane_fcond")
    check("fw_tag_cirq_suffix",
          fcfg.default_tag(bench="qbplus", framework="cirq", dev=True)
          == "rq4_fcea_qbplus_cirq_dev_fcond")

    ok = sum(1 for _, p, _ in RESULTS if p)
    for name, passed, detail in RESULTS:
        print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))
    print(f"\nselftest: {ok} pass / {len(RESULTS) - ok} fail")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
