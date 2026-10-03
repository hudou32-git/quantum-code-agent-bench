"""FCEA episode loop.

Mirror of exp.evidence_eqpa.loop (protocol parity: LLM/official budgets,
per-call audit log, length-cut resample, Write/Eval semantics, fallback submit,
NoSubmit penalty, canary gating, pass-stop, BatchProbe substitution) with ONE
addition: after a failed official Eval the frozen utility prior is injected as
a soft evidence-priority notice.
  variant "global" — same pooled tiers after every failure (V2)
  variant "fcond"  — tiers conditioned on the classified failure context (V3)
NoSubmit failures receive NO notice (phase-1 design). There is no progress /
stagnation / dynamic-updating module in phase 1.
"""
from __future__ import annotations

import time
from typing import Any

from exp import config
from exp.common.baseline.prompts import feedback_user, spec_user
from exp.common.canary import scan_text
from exp.common.cases import load_case
from exp.common.grader_qbplus import grade_qbplus, load_qbplus_case
from exp.common.grader_qhe import run_candidate
from exp.common.parse import extract_module_v2 as extract_module
from exp.eqpa.jail import ensure_jail
from exp.eqpa.tools import run_eval, run_write
from exp.evidence_eqpa.prompts import PROBE_BUDGET_NOTICE, workspace_block
from exp.fcea import config as fcfg
from exp.fcea.control.mech_flags import flags_for_variant
from exp.fcea.control.mech_ledger import MechLedger, api_tokens_from_error
from exp.fcea.control import preflight as mech_preflight
from exp.fcea.control import execution_guard as _execg
from exp.fcea.utility.commitment_state import (fsm_disable_all,
                                               fsm_enable_from_constants)
from exp.fcea.control import rq4b as rqb
from exp.fcea.control import acceptance as accept_mod
from exp.fcea.control import trace_probe as mech_trace
from exp.fcea.evidence import contract_probe as mech_cprobe
from exp.fcea.evidence import env_probe as mech_envprobe
from exp.fcea.evidence.batch_probe import run_fcea_batch_probe
from exp.fcea.evidence.planner import (
    classify_adoption,
    deu_kind,
    marginal_notice,
    utility_notice,
)
from exp.fcea.evidence.taxonomy import KIND_TO_CATEGORY, classify_evidence_output
from exp.fcea.action_selector import ActionSelector, RandomActionSelector, action_message
from exp.fcea.adapter import ActionAdapter
from exp.fcea.control.controller import RepairController
from exp.fcea.dcc import DCCController
from exp.fcea.tracing import trace as ftrace
from exp.fcea.utility import prior as uprior
from exp.fcea.utility.noise import NoiseUtilitySource, d2_noise_seed
from exp.fcea.utility.scorer import classify_failure
from exp.fcea.utility.state import DynamicEvidenceStateManager
from exp.fcea.utility.updater import DynamicUtilityUpdater

MAX_LLM_PER_SHOT = fcfg.MAX_LLM_PER_SHOT
MAX_OFFICIAL = fcfg.MAX_OFFICIAL


def _grade(case: dict[str, Any], code: str, *, bench: str = "qhe", dest=None, k: int = 1,
           case_id: str = "", framework: str = "qiskit") -> dict[str, Any]:
    if bench == "qbplus":
        return grade_qbplus(case, code, dest=dest, k=k, framework=framework)
    return run_candidate(
        code=code or "",
        test=case["test"],
        entry=case["entry_point"],
        prompt=case["prompt"],
        timeout=60.0,
        case_id=str(case_id),
    )


def run_fcea(case_id: str, client, *, tag: str | None = None, bench: str = "qhe",
             framework: str = "qiskit") -> dict[str, Any]:
    tag = tag or fcfg.default_tag(bench=bench)
    fcfg.refuse_foreign_tag(tag)
    variant = fcfg.VARIANT
    # wall-clock audit anchors (P0-1 drift sensitivity; v4.1 cost telemetry)
    _started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # deurq_fsm G2 registry: set per-episode from the variant so a later arm
    # in the SAME process cannot inherit an earlier arm's global state
    # (explicit else-disable; audit P1 fix — no more one-arm-one-process
    # fragility).
    if variant == "deurq_base":
        fsm_enable_from_constants(fcfg.DEURQ_BASE_CONSTANTS)
    elif variant in ("deurq_baseenv", "deurq_baseenv_v2", "deurq_final"):
        fsm_enable_from_constants(fcfg.DEURQ_BASEENV_CONSTANTS)
    else:
        fsm_disable_all()
    # MECH-1 (docs/实验MECH-1_协议.md): all flags default False — non-mech
    # variants get the all-False map and every hook below is a no-op.
    MECH = flags_for_variant(variant)
    case = (load_qbplus_case(case_id, framework=framework) if bench == "qbplus"
            else load_case(case_id))
    session = ensure_jail(case_id, tag=tag, prompt=case.get("prompt") or "")
    user0 = spec_user(case["prompt"], workspace_block(case_id=case_id))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": fcfg.FCEA_SYSTEM},
        {"role": "user", "content": user0},
    ]
    # MECH-1 E: fixed environment probe before the first LLM call (harness-
    # initiated; system prompt untouched; result travels as its own message)
    if MECH.get("mech_env_probe"):
        _env = mech_envprobe.run_env_probe(session=session)
        messages.append({"role": "user",
                         "content": mech_envprobe.env_probe_block(_env)})
    # MECH-1 C/D-F/D1 shared per-episode ledger
    mledger = (MechLedger()
               if (MECH.get("mech_failure_ledger")
                   or MECH.get("mech_focus_coverage")
                   or MECH.get("mech_auto_contract_probe")) else None)
    mech_auto_probes = 0
    preflight_rejects = 0
    preflight_rejects_this_shot = 0
    # rq4b (PROTOCOL v2.1): A|trace gate (deurc_trace) / B restart-replan
    # state (deurc_restart|deurc_replan). Default-off: every other variant
    # leaves these None and all hooks below are no-ops.
    # A16 (PROTOCOL_rq4b_A16.md): deurc_trace_v2 swaps in the v2 gate — same
    # v1 accounting, plus the harness-owned armed state (L1 boundary auto
    # probe + L2 Eval tri-state interception; L3 model channel unchanged).
    # E4 (deurq_final, 2026-10-01 freeze): the same frozen probe machinery
    # behind the E4 armed lifecycle (acceptance.Z4Gate) + acceptance gate.
    trace_v2 = variant in ("deurc_trace_v2", "deurq_final", "deurq_final_noz2")
    z4_active = variant in ("deurq_final", "deurq_final_noz2")
    trace_gate = (accept_mod.Z4Gate() if z4_active
                  else rqb.TraceGateV2() if trace_v2
                  else rqb.TraceGate() if variant == "deurc_trace" else None)
    # E3-new / E4 acceptance pipeline (docs/E3_E4_ACCEPTANCE_PIPELINE.md):
    # gate-bound salvage + fallback coverage + revision provenance. Default
    # off — every legacy variant keeps accept=None and byte-identical paths.
    _accept_c = (fcfg.DEURQ_BASEENV_V2_CONSTANTS if variant == "deurq_baseenv_v2"
                 else fcfg.DEURQ_FINAL_CONSTANTS if variant == "deurq_final"
                 else fcfg.DEURQ_FINAL_NOZ2_CONSTANTS if variant == "deurq_final_noz2"
                 else {})
    z3_gate_salvage = bool(_accept_c.get("z3_gate_salvage"))
    z3_fallback_gate = bool(_accept_c.get("z3_fallback_gate"))
    z4_defer_when_z3 = bool(_accept_c.get("z4_arm_defer_when_z3"))
    accept = (accept_mod.AcceptanceGate()
              if (z3_gate_salvage or z3_fallback_gate or z4_active) else None)
    replan_state = (rqb.ReplanState(fcfg.RQB_RESTART_CONSTANTS["rq4b_replan_kind"]
                                    if variant == "deurc_restart"
                                    else fcfg.RQB_REPLAN_CONSTANTS["rq4b_replan_kind"])
                    if variant in ("deurc_restart", "deurc_replan") else None)
    replan_shot_active = False
    _trace_tool: dict | None = None
    if trace_gate is not None:
        import copy as _copy
        _trace_tool = _copy.deepcopy(fcfg.FCEA_TOOL)
        _kind_prop = (_trace_tool["function"]["parameters"]["properties"]
                      ["queries"]["items"]["properties"]["kind"])
        _kind_prop["enum"] = list(_kind_prop["enum"]) + [rqb.TRACE_KIND]
        _kind_prop["description"] = (_kind_prop["description"]
                                     + ' Use "trace" for probes that call your '
                                     'entry function and print the checked '
                                     'quantity vs the value your current '
                                     'implementation produces.')
    _kind_map = ({**KIND_TO_CATEGORY, rqb.TRACE_KIND: rqb.TRACE_KIND_CATEGORY}
                 if trace_gate is not None else KIND_TO_CATEGORY)
    tool_log: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    call_log: list[dict[str, Any]] = []
    etrace = ftrace.new_episode_trace()
    prompt_tokens = 0
    completion_tokens = 0
    official = 0
    llm_calls = 0
    write_calls = 0
    eval_calls = 0
    fallback = False
    probe_rounds = 0
    probe_queries = 0
    batch_sizes: list[int] = []
    evidence_chars = 0
    priority_injections = 0
    last_code = ""
    # DEU-v2 Phase 1: passive state tracking (no update, no guidance); the
    # manager exists only for variant == "deu", so V2/V3 rows stay identical
    # (d2_clean included: the C2 machinery still computes for trace reference
    # only — every consumption point receives the noise surrogate instead).
    # dcc included (2026-09-29 fix): the DCC controller ignores every state
    # field, but the boundary plumbing (deu_trace records) is what carries the
    # controller's on_boundary call — without a state manager the controller
    # never fires (found in the 13:48 live audit; see dcc_postmortem)
    deu_state = (DynamicEvidenceStateManager(fcfg.DEU_CONSTANTS)
                 if fcfg.VARIANT in ("deu", "deu3", "deuact", "deurand", "deurc",
                                     "deurc_noescape", "deurc_softfocus",
                                     "deurc_jointrelax", "deurc_noctx",
                                     "deurc_noctx_joint", "d2_clean", "dcc",
                                     "deurq_fix", "mech1_prev", "mech1_rep",
                                     "mech1_full", "deurc_trace",
                                     "deurc_restart", "deurc_replan",
                                     "deurc_trace_v2", "deurq_base",
                                     "deurq_baseenv", "deurq_baseenv_v2",
                                     "deurq_final")
                 else None)
    deu_trace: list[dict] = []
    deu_updater = (DynamicUtilityUpdater(uprior.global_q0(), fcfg.DEU_CONSTANTS)
                   if deu_state is not None else None)
    consec_zero_nov = 0
    pending_adoption: dict | None = None
    adoption_log: list[dict] = []
    # DEU-v3 PoC: identical DEU machinery + an action adapter that may inject
    # short action-level guidance at every failure boundary (incl. NoSubmit)
    adapter = ActionAdapter(fcfg.DEU3_CONSTANTS) if fcfg.VARIANT == "deu3" else None
    adapter_log: list[dict] = []
    # DEU-v3-ACT (+ random ablation): rule-based Action Selector as a real
    # decision layer; actions are committed on the next attempt
    selector = (ActionSelector(fcfg.DEUACT_CONSTANTS) if fcfg.VARIANT == "deuact"
                else RandomActionSelector(fcfg.DEUACT_CONSTANTS)
                if fcfg.VARIANT == "deurand" else None)
    action_log: list[dict] = []
    action_finalize = False        # BatchProbe withdrawn once FINALIZE fires
    action_focus = None            # SWITCH_EVIDENCE family for the next attempt
    # DEU-RC: repair-control layer (RCI -> mode -> evidence/context gates);
    # restricts the decision space for the NEXT attempt, reversible per mode
    deurc_variants = ("deurc", "deurc_noescape", "deurc_softfocus",
                      "deurc_jointrelax", "deurc_noctx", "deurc_noctx_joint",
                      "d2_clean", "d3", "deurq_fix", "deurq_base", "deurq_baseenv",
                      "deurq_baseenv_v2", "deurq_final",
                      "deurq_baseenv_noz2", "deurq_final_noz2",
                      "mech1_prev", "mech1_rep", "mech1_full",
                      "deurc_trace", "deurc_restart", "deurc_replan",
                      "deurc_trace_v2")
    deurc_constants = {"deurc": fcfg.DEURC_CONSTANTS,
                       "deurc_noescape": fcfg.DEURC_NOESCAPE_CONSTANTS,
                       "deurc_softfocus": fcfg.DEURC_SOFTFOCUS_CONSTANTS,
                       "deurc_jointrelax": fcfg.DEURC_JOINTRELAX_CONSTANTS,
                       "deurc_noctx": fcfg.DEURC_NOCTX_CONSTANTS,
                       "deurq_base": fcfg.DEURQ_BASE_CONSTANTS,
                       "deurq_z1": fcfg.DEURQ_Z1_CONSTANTS,
                       "deurq_baseenv": fcfg.DEURQ_BASEENV_CONSTANTS,
                       "deurq_baseenv_v2": fcfg.DEURQ_BASEENV_V2_CONSTANTS,
                       "deurq_final": fcfg.DEURQ_FINAL_CONSTANTS,
                       "deurq_baseenv_noz2": fcfg.DEURQ_BASEENV_NOZ2_CONSTANTS,
                       "deurq_final_noz2": fcfg.DEURQ_FINAL_NOZ2_CONSTANTS,
                       "deurc_noctx_joint": fcfg.DEURC_NOCTX_JOINT_CONSTANTS,
                       "d2_clean": fcfg.D2_CLEAN_CONSTANTS,
                       "d3": fcfg.D3_CONSTANTS,
                       "deurq_fix": fcfg.DEURQ_FIX_CONSTANTS,
                       "mech1_prev": fcfg.MECH1_PREV_CONSTANTS,
                       "mech1_rep": fcfg.MECH1_REP_CONSTANTS,
                       "mech1_full": fcfg.MECH1_FULL_CONSTANTS,
                       "deurc_trace": fcfg.RQB_TRACE_CONSTANTS,
                       "deurc_restart": fcfg.RQB_RESTART_CONSTANTS,
                       "deurc_replan": fcfg.RQB_REPLAN_CONSTANTS,
                       "deurc_trace_v2": fcfg.RQB_TRACE_V2_CONSTANTS}
    controller = (DCCController(fcfg.DCC_CONSTANTS)
                  if fcfg.VARIANT == "dcc" else
                  RepairController(deurc_constants[fcfg.VARIANT])
                  if fcfg.VARIANT in deurc_variants else None)
    # deurq_base execution guards (exp.fcea.control.execution_guard):
    # default-off flags resolved from the same variant constants dict; every
    # legacy variant reads all-False here and behaves byte-identically.
    _exec_c = deurc_constants.get(fcfg.VARIANT) or {}
    exec_retry_corrective = bool(_exec_c.get("exec_retry_corrective"))
    exec_fuse = _execg.LengthFuse(_exec_c.get("exec_length_fuse_cap")
                                  if exec_retry_corrective else 0)
    exec_artifact_gate = bool(_exec_c.get("exec_artifact_gate"))
    exec_slot_salvage = bool(_exec_c.get("exec_slot_salvage"))
    # C7: execution-layer probe budget for the experiment ladder arms. Legacy
    # variants keep the reminder-only semantics (flag absent -> False).
    exec_probe_budget = bool(_exec_c.get("exec_probe_budget"))
    # P2-1 negative control hook: an override cap (e.g. 0) turns the probe
    # interface into an always-refused shell of itself (E1-null, preregistered
    # deferred arm). None keeps the protocol cap MAX_PROBES_PER_SHOT.
    exec_probe_budget_cap = _exec_c.get("exec_probe_budget_cap")
    probe_budget_cap = (fcfg.MAX_PROBES_PER_SHOT if exec_probe_budget_cap is None
                        else max(0, int(exec_probe_budget_cap)))
    probe_budget_refusals = 0
    fuse_directed_shot = False       # one hard directive per shot after the fuse blows
    retry_corrected = 0
    fuse_blown_shots = 0
    artifact_gate_rejects = 0
    slot_salvages = 0
    graded_attempts: set[str] = set()
    # RQ3 Phase B episode-level plumbing:
    #   d2_clean — seeded noise surrogate replacing the utility input;
    #   d3       — utility pinned to the frozen prior Q0 (no EMA updates) and
    #              a minimal evidence ledger (counts only; no error state).
    d2_noise: NoiseUtilitySource | None = None
    d2_noise_log: list[dict] = []
    d3_ledger: dict[str, int] = {}
    q_pinned: dict[str, float] | None = None
    if fcfg.VARIANT == "d2_clean":
        d2_noise = NoiseUtilitySource(seed=d2_noise_seed(tag=tag, case_id=case_id),
                                      constants=fcfg.D2_NOISE_CONSTANTS)
    if fcfg.VARIANT == "d3":
        q_pinned = uprior.global_q0()
    rc_blocked = 0                 # BatchProbe queries dropped by the gate
    deu_updater = (DynamicUtilityUpdater(uprior.global_q0(), fcfg.DEU_CONSTANTS)
                   if deu_state is not None else None)

    def record_deu_step(passed: bool, error_message: str, code: str,
                        *, nosubmit: bool = False) -> None:
        """Phase-2/3: close the repair step — state record + EMA utility update
        + adoption backfill (logging only; guidance is the Phase-3 notice)."""
        nonlocal consec_zero_nov, pending_adoption
        if deu_state is None:
            return
        step_rec = deu_state.on_eval_result(shot=official, passed=passed,
                                            error_message=error_message, code=code,
                                            nosubmit=nosubmit)
        if deu_updater is not None:
            upd = deu_updater.update_step(
                progress_score=deu_state.last_progress_score,
                step_state_change=bool(step_rec["code_changed"])
                or deu_state.error_transition != "same",
                category_novelties=deu_state.category_novelties(official),
                no_progress_count=deu_state.no_progress_count)
            for k in ("marginal_utility_before", "reward", "outcome_novelty",
                      "marginal_utility_after"):
                step_rec[k] = upd[k]
            step_rec["progress"] = {1: "improved", 0: "no_change",
                                    -1: "worse"}[deu_state.last_progress_score]
            novs = upd["outcome_novelty"]
            if novs and all(v == 0 for v in novs.values()):
                consec_zero_nov += 1
            elif novs:
                consec_zero_nov = 0
        if pending_adoption is not None:
            new_cats = sorted({h["category"] for h in deu_state.evidence_history
                               if h.get("shot", 0) > pending_adoption["injected_at_step"]
                               and h.get("category")})
            adoption_log.append({
                **pending_adoption, "categories_after": new_cats,
                "evaluated_at_step": official,
                **classify_adoption(pending_adoption["categories_before"], new_cats,
                                    step_rec["code_changed"], step_rec["passed"]),
            })
            pending_adoption = None
        deu_trace.append(step_rec)
        deu_state.on_code_submitted(code)
    last_exe: dict[str, Any] = {"passed": False, "error_message": "no official submit", "error_type": ""}

    def grade_fn(code: str) -> dict[str, Any]:
        k = official + 1
        return _grade(case, code, bench=bench, dest=session.host_dir, k=k,
                      case_id=case_id, framework=framework)

    def _attempt_text(name: str) -> str:
        """Sandbox-side contents of a written attempt (revision identity
        input; empty on any read failure -> hash of "", never matches a
        real revision, so provenance marking degrades to no-mark)."""
        try:
            from pathlib import Path as _P
            return _P(session.attempt_path(name)).read_text(encoding="utf-8")
        except (OSError, AttributeError):
            return ""

    def inject_priority(error_message: str) -> None:
        nonlocal priority_injections, consec_zero_nov, pending_adoption
        if fcfg.VARIANT == "deurq_fix":
            # RQ-fix F1: the evidence-priority notice carries the
            # QHE-misaligned prior tiers (E1 HIGH) — the fix arm deletes the
            # channel entirely instead of randomizing it (delta vs d2_clean).
            return
        cls = classify_failure(error_message)
        ctx = cls["failure_context"]
        nosubmit = ctx == "NoSubmit"
        injected = False
        trace_tiers = None
        trace_recommended = None
        # deurq_z1 (E1): the evidence-priority notice belongs to the Z2
        # decision stack — E0/E1 run without it (audit C2). Surgical gate:
        # only this new variant skips injection; the failure event is still
        # recorded below for traces. Every legacy variant is untouched.
        # D-ladder (2026-10-03): deurq_baseenv_noz2 / deurq_final_noz2 remove
        # Z2 by construction, so they sit on the same side of this gate.
        if (not nosubmit and ctx != "Other"
                and fcfg.VARIANT not in ("deurq_z1", "deurq_baseenv_noz2",
                                         "deurq_final_noz2")):
            if fcfg.VARIANT == "d2_clean":
                # D2 clean: the notice channel is a C2 consumption point too —
                # the frozen-prior tiers are replaced by the matched-form noise
                # assignment (byte-identical template, random tiers).
                notice = d2_noise.notice()
            elif fcfg.VARIANT in ("deu", "deu3"):
                # Phase 3: marginal-utility soft guidance (adaptive within the
                # episode; saturation warning when the repair state stalls)
                kind = deu_kind(deu_state.no_progress_count, consec_zero_nov)
                notice = marginal_notice(
                    kind=kind, Q=deu_updater.Q,
                    state_hint={"no_progress_count": deu_state.no_progress_count,
                                "same_error_count": deu_state.same_error_count,
                                "consecutive_uninformative_probes": consec_zero_nov})
                if deu_trace:
                    deu_trace[-1]["guidance_kind"] = kind
                pending_adoption = {
                    "guidance": kind, "injected_at_step": official,
                    "categories_before": sorted({h["category"] for h in
                                                 deu_state.evidence_history
                                                 if h.get("shot") == official
                                                 and h.get("category")}),
                }
            else:
                notice = utility_notice(variant=variant, failure_context=ctx,
                                        confidence=cls["confidence"])
            messages.append({"role": "user", "content": notice})
            priority_injections += 1
            injected = True
        # trace provenance: d2_clean records the noise tiers it actually served
        # (only when injected); every other variant keeps the historical
        # expression byte-for-byte (real tiers when not nosubmit, else None).
        if fcfg.VARIANT == "d2_clean":
            if injected:
                trace_tiers = dict(d2_noise.tiers)
                trace_recommended = list(d2_noise.recommended)
        else:
            trace_tiers = uprior.tiers_for(variant, ctx) if not nosubmit else None
            trace_recommended = uprior.recommended_for(variant, ctx) if not nosubmit else None
        ftrace.record_failure(
            etrace, shot=official, error_message=error_message,
            failure_context=ctx, confidence=cls["confidence"], nosubmit=nosubmit,
            utility_prior=trace_tiers,
            recommended=trace_recommended,
            injected=injected)

    def run_adapter(boundary_kind: str) -> None:
        """DEU-v3 PoC: evaluate the action adapter at a failure boundary.
        Reads only fields already recorded in deu_trace; logs an event even
        when nothing fires (near-miss diagnostics for the coverage analysis)."""
        if adapter is None or not deu_trace:
            return
        cur = deu_trace[-1]
        prev = deu_trace[-2] if len(deu_trace) >= 2 else None
        novs = cur.get("outcome_novelty") or {}
        nov_now = (sum(novs.values()) / len(novs)) if novs else None
        pnovs = (prev or {}).get("outcome_novelty") or {}
        nov_prev = (sum(pnovs.values()) / len(pnovs)) if pnovs else None
        b, a = cur.get("marginal_utility_before"), cur.get("marginal_utility_after")
        drop = max((abs(float(a[c]) - float(b[c])) for c in b if c in a), default=0.0) \
            if (b and a) else 0.0
        msg, event = adapter.on_boundary(
            step=official, boundary_kind=boundary_kind, task_id=case_id,
            error_transition=cur.get("error_transition"),
            error_message=cur.get("error_after") or "",
            no_progress_count=int(cur.get("no_progress_count") or 0),
            same_error_count=int(cur.get("same_error_count") or 0),
            code_changed=bool(cur.get("code_changed")),
            novelty_mean_now=nov_now, novelty_mean_prev=nov_prev,
            utility_drop=drop,
            attempts_left=max(MAX_OFFICIAL - (official + 1), 0))
        adapter_log.append(event)
        if msg and official < MAX_OFFICIAL:
            messages.append({"role": "user", "content": msg})

    def mech_boundary_extra(error_message: str) -> str:
        """MECH-1 C + D1: ledger failure record + feedback extras. Returns
        "" when the mech flags are off (byte-identical legacy feedback)."""
        nonlocal mech_auto_probes
        if mledger is None:
            return ""
        mledger.record_failure(error_message, last_code)
        parts: list[str] = []
        if MECH.get("mech_failure_ledger"):
            block = mledger.failure_block()
            if block:
                parts.append(block)
        if MECH.get("mech_auto_contract_probe"):
            cap = fcfg.MECH1_AUTO_MAX_PER_EPISODE
            per_b = fcfg.MECH1_AUTO_MAX_PER_BOUNDARY
            unresolved: list[str] = []
            while mech_auto_probes < cap and per_b > 0:
                uncovered = sorted(mledger.uncovered_targets(error_message))
                if not uncovered:
                    break
                progressed = False
                for tok in uncovered:
                    tried = False
                    for cand in mech_cprobe.resolve_targets(tok):
                        if cand in mledger.contracts:
                            continue
                        res = mech_cprobe.run_api_probe(cand, session=session)
                        mledger.record_contract(cand, res)
                        mech_auto_probes += 1
                        per_b -= 1
                        tried = True
                        progressed = True
                        _txt = res.get("text") or ""
                        if res.get("ok") and "RESOLVE_ERR" not in _txt \
                                and '"error"' not in _txt:
                            parts.append(mech_cprobe.auto_probe_block(res))
                        else:
                            unresolved.append(cand)
                        if per_b <= 0 or mech_auto_probes >= cap:
                            break
                    if tried:
                        # token-level coverage: every frozen candidate has
                        # been attempted (resolved or not) — do not retry
                        mledger.record_contract(
                            tok, {"ok": False, "output": "resolution attempted"})
                    if per_b <= 0 or mech_auto_probes >= cap:
                        break
                if not progressed:
                    break
            if unresolved:
                parts.append("[auto contract probe] not found in the frozen "
                             "candidate modules: " + ", ".join(unresolved[:3]))
        if MECH.get("mech_failure_ledger"):
            note = mledger.coverage_note()
            if note:
                parts.append(note)
        return ("\n" + "\n".join(parts)) if parts else ""

    def rq4b_boundary_extra(error_message: str, attempt_name: str | None) -> str:
        """A16 L1 (PROTOCOL_rq4b_A16.md §3): failure-boundary auto trace
        probe. At every informative-assertion trigger boundary the harness
        executes the just-evaluated attempt's entry with the frozen dummy
        ladder and appends the frozen evidence block to the failure
        feedback. Returns "" when not v2 / not a trigger / undeliverable
        (byte-identical legacy feedback for every other variant).
        E4 (z4_arm_defer_when_z3): arm-now/probe-later — when a Z3 contract
        gap co-triggers at the same boundary, the expectation is armed
        silently and the L1 probe is DEFERRED to a later boundary (Z3 owns
        the frame; the expectation is not lost)."""
        if trace_gate is None or not trace_v2:
            return ""
        if rqb.informative_signature(error_message) is None:
            return ""
        fname = attempt_name or f"attempt_{official}.py"
        if fname not in getattr(session, "written", set()):
            return ""
        if z4_active and z4_defer_when_z3 and mledger is not None \
                and MECH.get("mech_auto_contract_probe") \
                and mledger.uncovered_targets(error_message):
            trace_gate.arm_silent(error_message)
            trace_gate.defer_l1()
            return ""
        if z4_active and getattr(trace_gate, "pending_l1", False):
            trace_gate.resume_l1()
        _pr = mech_trace.run_trace_probe(
            fname, entry=str(case.get("entry_point") or ""), session=session)
        trace_gate.boundary_probes += 1
        _blk = rqb.l1_block(rqb.TraceGateV2.body_of(error_message), _pr)
        if _blk:
            trace_gate.blocks_delivered += 1
            return "\n" + _blk
        return ""

    def run_selector(boundary_kind: str) -> None:
        """DEU-v3-ACT: rule-based action selection at a failure boundary.
        The action is committed on the next attempt (message + mechanical
        constraint); the decision is logged even when CONTINUE."""
        nonlocal action_finalize, action_focus
        if selector is None or not deu_trace:
            return
        cur = deu_trace[-1]
        prev = deu_trace[-2] if len(deu_trace) >= 2 else None
        novs = cur.get("outcome_novelty") or {}
        nov_now = (sum(novs.values()) / len(novs)) if novs else None
        pnovs = (prev or {}).get("outcome_novelty") or {}
        nov_prev = (sum(pnovs.values()) / len(pnovs)) if pnovs else None
        b, a = cur.get("marginal_utility_before"), cur.get("marginal_utility_after")
        drop = max((abs(float(a[c]) - float(b[c])) for c in b if c in a), default=0.0) \
            if (b and a) else 0.0
        used = cur.get("evidence_used") or {}
        probeable = [(k, v) for k, v in used.items() if k in ("E1", "E2", "E3")]
        cur_fam = max(probeable, key=lambda kv: kv[1])[0] if probeable else None
        decision = selector.select(
            no_progress_count=int(cur.get("no_progress_count") or 0),
            same_error_count=int(cur.get("same_error_count") or 0),
            code_changed=bool(cur.get("code_changed")),
            novelty_mean_now=nov_now, novelty_mean_prev=nov_prev,
            utility_drop=drop,
            Q=dict(deu_updater.Q) if deu_updater is not None else {},
            current_family=cur_fam)
        msg = action_message(decision)
        action_focus = decision["focus_family"] if decision["action"] == "SWITCH_EVIDENCE" else None
        if decision["action"] == "FINALIZE":
            action_finalize = True   # persists to episode end
        action_log.append({
            "step_id": official, "task_id": case_id, "boundary_kind": boundary_kind,
            "action": decision["action"], "reason": decision["reason"],
            "focus_family": decision.get("focus_family"), "current_family": cur_fam,
            "trigger_signal": {
                "no_progress_count": int(cur.get("no_progress_count") or 0),
                "same_error_count": int(cur.get("same_error_count") or 0),
                "code_changed": bool(cur.get("code_changed")),
                "novelty_mean_now": nov_now, "novelty_mean_prev": nov_prev,
                "utility_drop": drop,
            },
            "utility_state": {"Q": {k: round(float(v), 4) for k, v in
                                    (deu_updater.Q.items() if deu_updater is not None else [])}},
            "message_sent": msg is not None,
            "delivered_next_attempt": official < MAX_OFFICIAL,
        })
        if msg and official < MAX_OFFICIAL:
            messages.append({"role": "user", "content": msg})

    def ensure_boundary_entry(error_message: str) -> None:
        """D3 only: no state manager exists, but the controller still needs a
        boundary record — build one from neutral (state-blind) inputs plus the
        evidence ledger. The controller's state_blind flag enforces blindness
        independently of what is passed here."""
        if fcfg.VARIANT != "d3":
            return
        deu_trace.append({
            "step": official, "boundary_kind_d3": True,
            "error_after": (error_message or "")[:400],
            "no_progress_count": 0, "same_error_count": 0,
            "code_changed": False, "progress_score": 0,
            "outcome_novelty": {}, "marginal_utility_before": None,
            "marginal_utility_after": None,
            "evidence_used": dict(d3_ledger)})

    def run_controller(boundary_kind: str) -> None:
        """DEU-RC: control-state decision at a failure boundary. Updates the
        evidence branch states, computes the RCI, selects the repair mode,
        prunes the message history per the mode's context policy, and appends
        the mode directive. Logged even when the mode stays SEARCH."""
        if controller is None or not deu_trace:
            return
        cur = deu_trace[-1]
        prev = deu_trace[-2] if len(deu_trace) >= 2 else None
        novs = cur.get("outcome_novelty") or {}
        nov_now = (sum(novs.values()) / len(novs)) if novs else None
        pnovs = (prev or {}).get("outcome_novelty") or {}
        nov_prev = (sum(pnovs.values()) / len(pnovs)) if pnovs else None
        b, a = cur.get("marginal_utility_before"), cur.get("marginal_utility_after")
        drop = max((abs(float(a[c]) - float(b[c])) for c in b if c in a), default=0.0) \
            if (b and a) else 0.0
        # RQ3 Phase B: the utility input is sourced per variant. d2_clean
        # substitutes the seeded noise surrogate at this single chokepoint —
        # everything downstream (branch Q states, RCI utility components and
        # the directive text that displays them, TERMINATE/FOCUS gates) then
        # consumes noise without any controller change. d3 passes the pinned
        # frozen prior with drop ≡ 0 (no EMA updates exist).
        if d2_noise is not None:
            q_noise, drop_noise = d2_noise.draw()
            d2_noise_log.append({"step": official, "boundary_kind": boundary_kind,
                                 "q_noise": q_noise,
                                 "utility_drop_noise": drop_noise})
            Q_boundary, drop_boundary = q_noise, drop_noise
        elif fcfg.VARIANT == "deurq_fix":
            # RQ-fix F1: state-only utility channel — uniform pinned Q, zero
            # drop; nothing downstream receives prior- or EMA-derived utility.
            Q_boundary = {"E1": 0.5, "E2": 0.5, "E3": 0.5, "E4": 0.5}
            drop_boundary = 0.0
        elif q_pinned is not None:
            Q_boundary, drop_boundary = dict(q_pinned), 0.0
        else:
            Q_boundary = dict(deu_updater.Q) if deu_updater is not None else {}
            drop_boundary = drop
        # MECH-1 D-F: is the failing API's resolved contract in the ledger?
        # None (flags off / no ledger) keeps legacy byte-identical behavior.
        mech_cov = None
        if mledger is not None and MECH.get("mech_focus_coverage"):
            mech_cov = mledger.contract_covered(
                api_tokens_from_error(cur.get("error_after") or ""))
        rec = controller.on_boundary(
            step=official, boundary_kind=boundary_kind, task_id=case_id,
            no_progress_count=int(cur.get("no_progress_count") or 0),
            same_error_count=int(cur.get("same_error_count") or 0),
            code_changed=bool(cur.get("code_changed")),
            progress_score=int(cur.get("progress_score") or 0),
            novelty_mean_now=nov_now, novelty_mean_prev=nov_prev,
            family_novelty_now=dict(novs), family_novelty_prev=dict(pnovs),
            utility_drop=drop_boundary,
            Q=Q_boundary,
            evidence_used=cur.get("evidence_used") or {},
            evidence_samples=sum((cur.get("evidence_used") or {}).values()),
            error_message=cur.get("error_after") or "", ts=time.time(),
            mech_contract_coverage=mech_cov)
        # mode-based context assembly BEFORE the directive so the directive
        # and the failure feedback always survive the prune
        new_msgs, ctx_stats = controller.assemble_context(messages)
        messages[:] = new_msgs
        rec["context_stats"] = ctx_stats
        msg = rec["message_text"]
        if msg and official < MAX_OFFICIAL:
            messages.append({"role": "user", "content": msg})

    def _episode_tools() -> list[dict]:
        if replan_shot_active:
            # rq4b B: the forced shot runs tools-unbound (schema carries no
            # tools -> the model can only answer in text; the no-tool-call
            # fallback path then writes + evals attempt_3.py automatically)
            return []
        tools = _evidence_tools()
        if MECH.get("mech_api_probe_tool"):
            # MECH-1 A: ApiProbe surface (additive; withdrawn never — its
            # purpose is exactly the FOCUS/TERMINATE-starved repair turns)
            tools = tools + [mech_cprobe.API_PROBE_TOOL]
        if _trace_tool is not None:
            # rq4b A: BatchProbe schema gains the "trace" kind (this variant
            # only; every other variant keeps the frozen schema bytes)
            tools = [(_trace_tool if (isinstance(t, dict)
                     and t.get("function", {}).get("name") == "BatchProbe") else t)
                     for t in tools]
        if action_finalize or (controller is not None and controller.probe_withdrawn()):
            # FINALIZE (DEU-ACT, persistent) and FOCUS/TERMINATE (DEU-RC,
            # mode-scoped) both disable new evidence collection
            return [t for t in tools if (t.get("name") if isinstance(t, dict) else None) != "BatchProbe"]
        return tools

    while official < MAX_OFFICIAL:
        if replan_state is not None and replan_state.pending:
            # rq4b B context surgery: [system, original spec, frozen injection]
            messages[:] = replan_state.surgery(fcfg.FCEA_SYSTEM, user0)
            replan_shot_active = True
        rounds_this = 0
        probes_this = 0
        llm_this = 0
        reminded = False
        shot_done = False
        preflight_rejects_this_shot = 0
        fuse_directed_shot = False
        if trace_gate is not None and trace_v2:
            trace_gate.new_shot()
        while not shot_done and llm_this < MAX_LLM_PER_SHOT:
            res = client.chat_messages(messages, tools=_episode_tools())
            llm_calls += 1
            llm_this += 1
            u = res.usage or {}
            pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
            prompt_tokens += pt
            completion_tokens += ct
            call_log.append({"i": llm_calls, "finish_reason": res.finish_reason or "",
                             "prompt_tokens": pt, "completion_tokens": ct,
                             "completion_tokens_estimated": bool(getattr(res, "completion_tokens_estimated", False)),
                             "degenerate_repeat": bool(getattr(res, "repeat_guard", None) and res.repeat_guard.get("fired")),
                             "duration_ms": round(1000 * float(getattr(res, "wall_time", 0) or 0), 1)})
            if (res.finish_reason or "") == "length" and not res.tool_calls:
                call_log[-1]["length_cut_no_tool"] = True
                # deurq_base: corrective retry changes the sampling condition
                # BEFORE the resample; once the episode fuse blows, no further
                # resample is paid and the shot gets one hard submit directive
                # (exp/fcea/control/execution_guard.py).
                _resample = True
                if exec_retry_corrective:
                    if exec_fuse.on_cut() == "retry":
                        retry_corrected += 1
                        messages.append({"role": "user",
                                         "content": _execg.CORRECTIVE_TEXT})
                    else:
                        _resample = False
                        if not fuse_directed_shot:
                            fuse_directed_shot = True
                            fuse_blown_shots += 1
                            messages.append({"role": "user",
                                             "content": _execg.FUSE_TEXT})
                if _resample:
                    res = client.chat_messages(messages, tools=_episode_tools())
                    llm_calls += 1
                    llm_this += 1
                    u = res.usage or {}
                    pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
                    prompt_tokens += pt
                    completion_tokens += ct
                    call_log.append({"i": llm_calls, "finish_reason": res.finish_reason or "",
                                     "prompt_tokens": pt, "completion_tokens": ct,
                                     "duration_ms": round(1000 * float(getattr(res, "wall_time", 0) or 0), 1),
                                     "length_retry": True,
                                     **({"corrected_retry": True}
                                        if exec_retry_corrective else {})})
            if deu_state is not None:
                deu_state.on_shot_state(llm_this, MAX_LLM_PER_SHOT)
            messages.append(res.assistant_message or {"role": "assistant", "content": res.content})
            calls = list(res.tool_calls or [])
            if not calls:
                if exec_artifact_gate and (res.finish_reason or "") == "length":
                    # deurq_base: a truncated draw may not enter the fallback
                    # submit path — its extracted residue burned an official
                    # slot with a NameError-class残码 (qbplus/26 case).
                    artifact_gate_rejects += 1
                    messages.append({"role": "user", "content": _execg.GATE_TEXT})
                    if llm_this >= MAX_LLM_PER_SHOT:
                        break
                    continue
                code = extract_module(res.content)
                if code.strip():
                    fallback = True
                    k = official + 1
                    wr = run_write(path=f"attempt_{k}.py", contents=code, session=session)
                    write_calls += 1
                    tool_log.append({"name": "Write", "fallback": True,
                                     **{x: wr[x] for x in wr if x != "contents"}})
                    _fb_rem = None
                    if trace_gate is not None:
                        _fb_rem = trace_gate.on_write()
                    # E3-new/E4 submission-path coverage (frozen R2): the
                    # fallback candidate passes the Z3 preflight before the
                    # official grade. A gate failure rejects NON-officially
                    # (slot NOT consumed, feedback returned) and the revision
                    # is marked ineligible for salvage until modified. The
                    # per-shot reject cap bounds the loop; past the cap the
                    # gate fails open (Z0 semantics: the slot grades).
                    if (z3_fallback_gate and accept is not None
                            and MECH.get("mech_preflight")
                            and preflight_rejects_this_shot
                            < fcfg.MECH1_PREFLIGHT_REJECT_CAP_PER_SHOT):
                        _pf = mech_preflight.run_preflight(f"attempt_{k}.py",
                                                           session=session)
                        if _pf.get("outcome") == "failed":
                            accept.mark_rejected(accept_mod.revision_hash(code), "z3")
                            preflight_rejects += 1
                            preflight_rejects_this_shot += 1
                            tool_log.append({"name": "Preflight",
                                             "fallback_rejected": True,
                                             "attempt_file": f"attempt_{k}.py",
                                             "text": (_pf.get("tb") or _pf.get("error") or "")[:400]})
                            messages.append({"role": "user", "content":
                                             mech_preflight.preflight_feedback_block(_pf)})
                            continue
                    # E4 submission-path coverage: the fallback candidate also
                    # passes the Z4 L2 probe when an expectation is armed
                    # (frozen pipeline; Z3-first — reached only when Z3 did
                    # not reject). failed -> NON-official rejection; other
                    # outcomes fail open into the official grade.
                    if (z4_active and accept is not None
                            and trace_gate.armed_sig is not None
                            and trace_gate.l2_rejects_this_shot
                            < rqb.TRACE_REJECT_CAP_PER_SHOT):
                        _tr = mech_trace.run_trace_probe(
                            f"attempt_{k}.py",
                            entry=str(case.get("entry_point") or ""),
                            session=session)
                        trace_gate.l2_probes += 1
                        _exp = rqb.parse_expected_number(trace_gate.last_body)
                        _outcome, _z4r = mech_trace.classify_probe(
                            _tr, _exp, body=trace_gate.last_body)
                        trace_gate.on_l2_outcome(_outcome)
                        if _outcome == "failed":
                            accept.mark_rejected(
                                accept_mod.revision_hash(
                                    _attempt_text(f"attempt_{k}.py")), "z4")
                            tool_log.append({"name": "TraceGate",
                                             "fallback_rejected": True,
                                             "attempt_file": f"attempt_{k}.py",
                                             "reason": _z4r})
                            messages.append({"role": "user", "content": _safe_obs(
                                rqb.l2_reject_block(
                                    trace_gate.last_body, _tr, _exp,
                                    rqb.probe_numeric_value(
                                        _tr.get("artifact") if isinstance(
                                            _tr.get("artifact"), dict) else None)))})
                            continue
                        tool_log.append({"name": "TraceGate", "rejected_eval": False,
                                         "fallback": True, "outcome": _outcome,
                                         "attempt_file": f"attempt_{k}.py"})
                    ev = run_eval(session=session, k=k, grade_fn=grade_fn)
                    eval_calls += 1
                    official += 1
                    if exec_slot_salvage and ev.get("path"):
                        graded_attempts.add(ev["path"])
                    last_code = ev.get("code") or code
                    last_exe = {"passed": bool(ev.get("passed")),
                                "error_message": ev.get("error") or "",
                                "error_type": ""}
                    tool_log.append({"name": "Eval", "fallback": True, "official_eval": True,
                                     "passed": last_exe["passed"],
                                     "text": (ev.get("text") or "")[:1500]})
                    shots.append(_shot_row(k, last_exe, last_code))
                    record_deu_step(bool(last_exe["passed"]),
                                    last_exe["error_message"] or "", last_code)
                    shot_done = True
                    if last_exe.get("passed"):
                        if z4_active:
                            # frozen R6 extension (fallback path symmetry)
                            trace_gate.discharge("official")
                        break
                    inject_priority(last_exe.get("error_message") or "")
                    _fb = feedback_user(
                        error=last_exe.get("error_message") or "", attempt=official) \
                        + mech_boundary_extra(last_exe.get("error_message") or "") \
                        + rq4b_boundary_extra(last_exe.get("error_message") or "",
                                              ev.get("path"))
                    if _fb_rem:
                        _fb = _fb + "\n" + _fb_rem
                    messages.append({"role": "user", "content": _fb})
                    if trace_gate is not None:
                        _tc = trace_gate.on_failure(last_exe.get("error_message") or "")
                        if _tc:
                            messages.append({"role": "user", "content": _tc})
                    if replan_state is not None:
                        _em = last_exe.get("error_message") or ""
                        replan_state.on_official_failure(_em)
                        if rqb.kl_raw_of(_em) is not None:
                            replan_state.on_shot2_boundary(official)
                    continue
                if not reminded and rounds_this >= 2 and not action_finalize \
                        and not replan_shot_active \
                        and not (controller is not None and controller.probe_withdrawn()):
                    reminded = True
                    messages.append({"role": "user", "content": (
                        "Use BatchProbe to inspect, Write attempt_k.py "
                        "(exact filename attempt_1.py / attempt_2.py / attempt_3.py), then Eval().")})
                    continue
                if llm_this >= MAX_LLM_PER_SHOT:
                    break
                continue
            for call in calls:
                name = call.get("name") or ""
                args = call.get("arguments") or {}
                cid = call.get("id") or ""
                if name == "ApiProbe":
                    # MECH-1 A: resolved-contract probe (read-only
                    # introspection; frozen script; probe caps + canary).
                    _target = str(args.get("target") or "")
                    _res = mech_cprobe.run_api_probe(_target, session=session)
                    if mledger is not None and _res.get("ok"):
                        mledger.record_contract(_target, _res)
                    tool_log.append({"name": "ApiProbe", "target": _target,
                                     "ok": bool(_res.get("ok")),
                                     "text": (_res.get("text") or "")[:400]})
                    messages.append({"role": "tool", "tool_call_id": cid,
                                     "name": "ApiProbe",
                                     "content": _safe_obs((_res.get("text") or "")[:900])})
                    continue
                if name == "BatchProbe":
                    if controller is not None and controller.probe_withdrawn():
                        # tool was withdrawn for this mode; never execute
                        messages.append({"role": "tool", "tool_call_id": cid,
                                         "name": "BatchProbe",
                                         "content": "BatchProbe is disabled by the repair "
                                         "controller (mode=%s). Proceed without new evidence."
                                         % controller.current_mode})
                        continue
                    if exec_probe_budget and probes_this >= probe_budget_cap:
                        # C7 (execution hard budget): the per-shot probe budget
                        # is ENFORCED here for the experiment ladder arms — the
                        # real batch backend is not called again this shot.
                        # Legacy variants keep the reminder-only path below.
                        probe_budget_refusals += 1
                        tool_log.append({"name": "BatchProbe", "blocked": True,
                                         "budget": True})
                        messages.append({"role": "tool", "tool_call_id": cid,
                                         "name": "BatchProbe",
                                         "content": _execg.PROBE_BUDGET_REFUSAL.format(
                                             used=probes_this,
                                             cap=probe_budget_cap,
                                             k=official + 1)})
                        continue
                    queries = args.get("queries")
                    focus_dropped = 0
                    rc_blocked = 0
                    if action_focus and isinstance(queries, list):
                        kept = []
                        for q in queries:
                            if (isinstance(q, dict)
                                    and _kind_map.get(q.get("kind")) == action_focus):
                                kept.append(q)
                            else:
                                focus_dropped += 1
                        queries = kept
                    if controller is not None and isinstance(queries, list):
                        # evidence gate: blocked families' kinds are not executed
                        allowed = set(controller.allowed_families())
                        kept = []
                        for q in queries:
                            if (isinstance(q, dict)
                                    and _kind_map.get(q.get("kind")) in allowed):
                                kept.append(q)
                            else:
                                rc_blocked += 1
                        queries = kept
                    pr = run_fcea_batch_probe(queries, session=session)
                    if trace_gate is not None:
                        # rq4b A: a round containing an executed kind="trace"
                        # query discharges the armed obligation (soft gate)
                        trace_gate.on_probe_round(
                            [q.get("kind") for q in (queries or [])
                             if isinstance(q, dict)])
                    if controller is not None and rc_blocked:
                        pr["text"] = (pr.get("text") or "") + (
                            "\n[repair controller: %d query(ies) on blocked evidence kinds not executed]"
                            % rc_blocked)
                    if action_focus and isinstance(args.get("queries"), list):
                        pr["text"] = (pr.get("text") or "") + (
                            "\n[evidence focus %s active: %d non-conforming query(ies) not executed]"
                            % (action_focus, focus_dropped))
                    n_run = int(pr.get("n_run") or 0)
                    probe_rounds += 1
                    rounds_this += 1
                    probe_queries += n_run
                    probes_this += n_run
                    batch_sizes.append(n_run)
                    for e in pr.get("evidence") or []:
                        evidence_chars += len(e.get("output") or "")
                    # MECH-1 D-F: a BatchProbe whose query mentions a ledger
                    # token counts as covering it (model-initiated contract
                    # probing; audit rule frozen 2026-09-30)
                    if mledger is not None:
                        for e in pr.get("evidence") or []:
                            _q = str(e.get("query") or "")
                            if not _q:
                                continue
                            for _tok in api_tokens_from_error(_q):
                                mledger.record_contract(_tok, {"ok": True, "output": ""})
                    if deu_state is not None:
                        deu_state.on_probes(official + 1, [
                            {"category": classify_evidence_output(e.get("output") or "")[0],
                             "output": e.get("output") or ""} for e in pr.get("evidence") or []])
                    if fcfg.VARIANT == "d3":
                        # state layer off: keep only the evidence account
                        # (counts per classified category) — the FOCUS gate's
                        # evidence_samples input. No novelty, no error state.
                        for e in pr.get("evidence") or []:
                            cat = classify_evidence_output(e.get("output") or "")[0]
                            d3_ledger[cat] = d3_ledger.get(cat, 0) + 1
                    ftrace.record_probes(etrace, round_no=probe_rounds, shot=official + 1,
                                         evidence=pr.get("evidence") or [],
                                         rejected=pr.get("rejected") or [],
                                         classify_output=classify_evidence_output)
                    tool_log.append({"name": "BatchProbe", "round": probe_rounds,
                                     "n_run": n_run, "n_requested": pr.get("n_requested"),
                                     "blocked": bool(pr.get("blocked")),
                                     "sandboxed": True,
                                     "text": (pr.get("text") or "")[:1500]})
                    messages.append({"role": "tool", "tool_call_id": cid, "name": "BatchProbe",
                                     "content": _safe_obs(pr.get("text") or "")})
                    if probes_this >= fcfg.MAX_PROBES_PER_SHOT and not reminded:
                        reminded = True
                        messages.append({"role": "user", "content": PROBE_BUDGET_NOTICE.format(
                            n=probes_this, rounds=rounds_this)})
                    continue
                if name == "Write":
                    wr = run_write(path=str(args.get("path") or ""),
                                   contents=str(args.get("contents") or ""), session=session)
                    write_calls += 1
                    tool_log.append({"name": "Write", **{x: wr[x] for x in wr if x != "contents"}})
                    _wtxt = _safe_obs(wr.get("text") or "")
                    if mledger is not None and MECH.get("mech_failure_ledger") \
                            and wr.get("ok", True):
                        _note = mledger.revert_note(str(args.get("contents") or ""))
                        if _note:
                            _wtxt = _wtxt + "\n" + _note
                    if trace_gate is not None:
                        # rq4b A soft gate: Write while armed-and-undischarged
                        # -> violation + verbatim contract re-injection
                        _rem = trace_gate.on_write()
                        if _rem:
                            _wtxt = _wtxt + "\n" + _rem
                    messages.append({"role": "tool", "tool_call_id": cid, "name": "Write",
                                     "content": _wtxt})
                    continue
                if name == "Eval":
                    raw_k = args.get("k")
                    k_arg = int(raw_k) if raw_k not in (None, "") else None
                    # MECH-1 B: L1 preflight before the official Eval. A
                    # preflight that itself cannot produce a verdict
                    # (indeterminate) FAILS OPEN — the official Eval proceeds.
                    # Genuine failures are rejected non-officially, at most
                    # MECH1_PREFLIGHT_REJECT_CAP_PER_SHOT per shot (then the
                    # gate degrades to pass-through for the rest of the shot).
                    if MECH.get("mech_preflight"):
                        _pf_name = (f"attempt_{k_arg}.py" if k_arg is not None
                                    else getattr(session, "last_write_name", None))
                        if (_pf_name and _pf_name in getattr(session, "written", set())
                                and preflight_rejects_this_shot
                                < fcfg.MECH1_PREFLIGHT_REJECT_CAP_PER_SHOT):
                            _pf = mech_preflight.run_preflight(_pf_name, session=session)
                            if _pf.get("outcome") == "failed":
                                preflight_rejects += 1
                                preflight_rejects_this_shot += 1
                                if accept is not None:
                                    accept.mark_rejected(
                                        accept_mod.revision_hash(
                                            _attempt_text(_pf_name)), "z3")
                                tool_log.append({"name": "Preflight", "rejected_eval": True,
                                                 "attempt_file": _pf_name,
                                                 "text": (_pf.get("tb") or _pf.get("error") or "")[:400]})
                                messages.append({"role": "tool", "tool_call_id": cid,
                                                 "name": "Eval",
                                                 "content": mech_preflight.preflight_feedback_block(_pf)})
                                continue
                            if _pf.get("outcome") == "indeterminate":
                                tool_log.append({"name": "Preflight", "rejected_eval": False,
                                                 "attempt_file": _pf_name,
                                                 "text": (_pf.get("error") or "indeterminate")[:200]})
                    # A16 L2: armed official Eval runs the trace probe first.
                    # failed (entry crash / parseable mismatch) -> non-official
                    # rejection, probe evidence as the Eval tool result (the
                    # attempt is NOT consumed), at most TRACE_REJECT_CAP_PER_SHOT
                    # per shot; indeterminate and passed -> FAIL-OPEN pass-through.
                    if trace_v2 and trace_gate.armed \
                            and trace_gate.l2_rejects_this_shot < rqb.TRACE_REJECT_CAP_PER_SHOT:
                        _tr_name = (f"attempt_{k_arg}.py" if k_arg is not None
                                    else getattr(session, "last_write_name", None))
                        if _tr_name and _tr_name in getattr(session, "written", set()):
                            _tr = mech_trace.run_trace_probe(
                                _tr_name, entry=str(case.get("entry_point") or ""),
                                session=session)
                            trace_gate.l2_probes += 1
                            _exp = rqb.parse_expected_number(trace_gate.last_body)
                            _outcome, _reason = mech_trace.classify_probe(
                                _tr, _exp, body=trace_gate.last_body)
                            if _outcome == "failed":
                                trace_gate.l2_rejects += 1
                                trace_gate.l2_rejects_this_shot += 1
                                tool_log.append({"name": "TraceGate", "rejected_eval": True,
                                                 "attempt_file": _tr_name,
                                                 "reason": _reason,
                                                 "phase": _tr.get("phase"),
                                                 "artifact": _tr.get("artifact")})
                                messages.append({"role": "tool", "tool_call_id": cid,
                                                 "name": "Eval",
                                                 "content": _safe_obs(rqb.l2_reject_block(
                                                     trace_gate.last_body, _tr, _exp,
                                                     rqb.probe_numeric_value(
                                                         _tr.get("artifact") if isinstance(
                                                             _tr.get("artifact"), dict) else None)))})
                                if z4_active and accept is not None:
                                    accept.mark_rejected(
                                        accept_mod.revision_hash(
                                            _attempt_text(_tr_name)), "z4")
                                continue
                            trace_gate.l2_indeterminate += (_outcome == "indeterminate")
                            trace_gate.l2_passthrough += (_outcome == "passed")
                            if z4_active:
                                # frozen E4 discharge rule: a "passed" L2
                                # verdict satisfies the armed expectation
                                if _outcome == "passed":
                                    trace_gate.discharge("l2")
                            tool_log.append({"name": "TraceGate", "rejected_eval": False,
                                             "outcome": _outcome, "attempt_file": _tr_name,
                                             "reason": _reason})
                    ev = run_eval(session=session, k=k_arg, grade_fn=grade_fn)
                    eval_calls += 1
                    tool_log.append({"name": "Eval", "official_eval": bool(ev.get("official_eval")),
                                     "passed": ev.get("passed"),
                                     "text": (ev.get("text") or "")[:1500]})
                    messages.append({"role": "tool", "tool_call_id": cid, "name": "Eval",
                                     "content": _safe_obs(ev.get("text") or "")})
                    if not ev.get("official_eval"):
                        continue
                    official += 1
                    if exec_slot_salvage and ev.get("path"):
                        graded_attempts.add(ev["path"])
                    last_code = ev.get("code") or last_code
                    last_exe = {"passed": bool(ev.get("passed")),
                                "error_message": ev.get("error") or "",
                                "error_type": ""}
                    shots.append(_shot_row(official, last_exe, last_code))
                    record_deu_step(bool(last_exe["passed"]),
                                    last_exe["error_message"] or "", last_code)
                    shot_done = True
                    if last_exe.get("passed"):
                        if z4_active:
                            # frozen R6 extension: the official PASS of the
                            # revised candidate satisfies the expectation
                            trace_gate.discharge("official")
                        break
                    ensure_boundary_entry(last_exe.get("error_message") or "")
                    run_adapter("error")
                    run_selector("error")
                    run_controller("error")
                    inject_priority(last_exe.get("error_message") or "")
                    messages.append({"role": "user", "content": feedback_user(
                        error=last_exe.get("error_message") or "", attempt=official)
                        + mech_boundary_extra(last_exe.get("error_message") or "")
                        + rq4b_boundary_extra(last_exe.get("error_message") or "",
                                              ev.get("path"))})
                    if trace_gate is not None:
                        _tc = trace_gate.on_failure(last_exe.get("error_message") or "")
                        if _tc:
                            messages.append({"role": "user", "content": _tc})
                    if replan_state is not None:
                        _em = last_exe.get("error_message") or ""
                        replan_state.on_official_failure(_em)
                        if rqb.kl_raw_of(_em) is not None:
                            replan_state.on_shot2_boundary(official)
                    break
                messages.append({"role": "tool", "tool_call_id": cid,
                                 "content": f"unknown tool {name}"})
            if last_exe.get("passed"):
                break
        if last_exe.get("passed"):
            break
        if not shot_done:
            # deurq_base slot salvage: the attempt slot burns regardless
            # (official += 1), so a written-but-never-graded candidate is
            # officially graded instead of recorded as NoSubmit. The MECH
            # preflight is deliberately bypassed here (FAIL-OPEN: the slot
            # is consumed either way, so the official grade is strictly
            # more information than a rejection).
            # E3-new/E4 (frozen R2, docs/E3_E4_ACCEPTANCE_PIPELINE.md): the
            # salvage candidate passes the acceptance pipeline — the legacy
            # FAIL-OPEN bypass is SUPERSEDED on these arms only (legacy
            # variants keep the semantics above, byte-identical). A gate
            # rejection here consumes the slot as NoSubmit; a revision
            # already rejected by an active gate is ineligible (R3) until
            # its contents change.
            _salvage = None
            if exec_slot_salvage:
                _cand = getattr(session, "last_write_name", None)
                if (_cand and _cand in getattr(session, "written", set())
                        and _cand not in graded_attempts):
                    _salvage = _cand
            if _salvage and z3_gate_salvage and accept is not None:
                _c_hash = accept_mod.revision_hash(_attempt_text(_salvage))
                _pf_failed = False
                _z4_rejected = False
                if MECH.get("mech_preflight") and _c_hash:
                    _pf = mech_preflight.run_preflight(_salvage, session=session)
                    if _pf.get("outcome") == "failed":
                        _pf_failed = True
                if (z4_active and not _pf_failed
                        and trace_gate.armed_sig is not None
                        and trace_gate.l2_rejects_this_shot
                        < rqb.TRACE_REJECT_CAP_PER_SHOT):
                    # Z4 L2 at the final boundary (E4 only): the armed
                    # expectation is checked before the slot is spent;
                    # rejections are counted separately for the audit.
                    _tr = mech_trace.run_trace_probe(
                        _salvage, entry=str(case.get("entry_point") or ""),
                        session=session)
                    trace_gate.l2_probes += 1
                    _exp = rqb.parse_expected_number(trace_gate.last_body)
                    _outcome, _z4r = mech_trace.classify_probe(
                        _tr, _exp, body=trace_gate.last_body)
                    trace_gate.on_l2_outcome(_outcome)
                    if _outcome == "failed":
                        _z4_rejected = True
                        accept.z4_final_boundary_rejects += 1
                        tool_log.append({"name": "TraceGate", "final_boundary": True,
                                         "rejected_salvage": True,
                                         "attempt_file": _salvage, "reason": _z4r})
                _proceed, _ns_reason = accept_mod.salvage_decision(
                    accept, _c_hash,
                    preflight_failed=_pf_failed, z4_rejected=_z4_rejected)
                if not _proceed:
                    if _ns_reason not in ("revision_rejected_by_z3",
                                          "revision_rejected_by_z4"):
                        accept.mark_rejected(_c_hash,
                                             "z3" if _pf_failed else "z4")
                    accept.block_salvage(_ns_reason)
                    # frozen R2: the slot is consumed, recorded as NoSubmit
                    official += 1
                    last_exe = {"passed": False,
                                "error_message": "no official submit this attempt",
                                "error_type": "NoSubmit"}
                    shots.append(_shot_row(official, last_exe, last_code))
                    record_deu_step(False, last_exe["error_message"], last_code,
                                    nosubmit=True)
                    tool_log.append({"name": "GateSalvage", "blocked": True,
                                     "reason": _ns_reason,
                                     "attempt_file": _salvage})
                    ensure_boundary_entry(last_exe["error_message"])
                    run_adapter("nosubmit")
                    run_selector("nosubmit")
                    run_controller("nosubmit")
                    inject_priority(last_exe["error_message"])
                    if official < MAX_OFFICIAL:
                        messages.append({"role": "user", "content": feedback_user(
                            error=last_exe["error_message"], attempt=official)})
                    continue
            if _salvage:
                slot_salvages += 1
                ev = run_eval(session=session, k=None, grade_fn=grade_fn)
                eval_calls += 1
                official += 1
                if ev.get("path"):
                    graded_attempts.add(ev["path"])
                last_code = ev.get("code") or last_code
                last_exe = {"passed": bool(ev.get("passed")),
                            "error_message": ev.get("error") or "",
                            "error_type": ""}
                shots.append(_shot_row(official, last_exe, last_code))
                record_deu_step(bool(last_exe["passed"]),
                                last_exe["error_message"] or "", last_code)
                tool_log.append({"name": "Eval", "official_eval": True,
                                 "slot_salvage": True,
                                 "passed": last_exe["passed"],
                                 "text": (ev.get("text") or "")[:1500]})
                shot_done = True
                if last_exe.get("passed"):
                    break
                ensure_boundary_entry(last_exe["error_message"])
                run_adapter("error")
                run_selector("error")
                run_controller("error")
                inject_priority(last_exe["error_message"])
                if official < MAX_OFFICIAL:
                    messages.append({"role": "user", "content": feedback_user(
                        error=last_exe["error_message"], attempt=official)
                        + mech_boundary_extra(last_exe["error_message"])})
                continue
            official += 1
            last_exe = {"passed": False, "error_message": "no official submit this attempt",
                        "error_type": "NoSubmit"}
            shots.append(_shot_row(official, last_exe, last_code))
            record_deu_step(False, last_exe["error_message"], last_code, nosubmit=True)
            ensure_boundary_entry(last_exe["error_message"])
            run_adapter("nosubmit")
            run_selector("nosubmit")
            run_controller("nosubmit")
            inject_priority(last_exe["error_message"])  # records nosubmit, injects nothing
            if official < MAX_OFFICIAL:
                messages.append({"role": "user", "content": feedback_user(
                    error=last_exe["error_message"], attempt=official)
                    + mech_boundary_extra(last_exe["error_message"])})

    passed = bool(last_exe.get("passed"))
    blob = "\n".join([last_code or "", last_exe.get("error_message") or "",
                      *(str(t.get("text") or "") for t in tool_log)])
    avg_batch = round(probe_queries / probe_rounds, 2) if probe_rounds else 0.0
    return {
        "case_id": case_id,
        "arm": fcfg.ARM_NAME,
        "variant": variant,
        "passed": passed,
        "pass_fail": "PASS" if passed else "FAIL",
        "error_message": last_exe.get("error_message") or "",
        "error_type": last_exe.get("error_type") or "",
        "parsed_code": last_code,
        "llm_calls": llm_calls,
        "write_calls": write_calls,
        "eval_calls": eval_calls,
        "official_submits": official,
        "fallback": fallback,
        "tool_rounds": probe_rounds,
        "probe_queries": probe_queries,
        "batch_sizes": batch_sizes,
        "avg_batch": avg_batch,
        "evidence_chars": evidence_chars,
        "priority_injections": priority_injections,
        "length_cuts": exec_fuse.cuts,
        "retry_corrected": retry_corrected,
        "fuse_blown_shots": fuse_blown_shots,
        "artifact_gate_rejects": artifact_gate_rejects,
        "slot_salvages": slot_salvages,
        "probe_budget_refusals": probe_budget_refusals,
        "probe_log": etrace["probe_log"],
        "failure_events": etrace["failure_events"],
        "actual_probe_count": probe_queries,
        # MECH-1 additive episode fields (absent flags -> zero/empty; keys are
        # additive so legacy trace consumers are unaffected)
        "mech_flags": {k: bool(v) for k, v in MECH.items() if v},
        "preflight_rejects": preflight_rejects,
        "mech_auto_probes": mech_auto_probes,
        "mech_contracts": dict(mledger.contracts) if mledger is not None else {},
        **({"rq4b_trace": trace_gate.stats(),
            "rq4b_trace_armed_final": list(trace_gate.armed)}
           if trace_gate is not None else {}),
        # E3-new / E4 acceptance pipeline telemetry (additive; frozen field
        # names, docs/E3_E4_ACCEPTANCE_PIPELINE.md §trace):
        **({"gate_rejected_before_salvage": accept.gate_rejected_before_salvage,
            "nosubmit_reason": accept.last_nosubmit_reason,
            "acceptance": {**accept.stats(),
                           "z3_gate_salvage": z3_gate_salvage,
                           "z3_fallback_gate": z3_fallback_gate,
                           "z4_active": z4_active}}
           if accept is not None else {}),
        **({"z4_armed": trace_gate.armed_sig is not None,
            "z4_signature_id": trace_gate.armed_sig,
            "z4_probe_sent": trace_gate.l2_probes + trace_gate.boundary_probes,
            "z4_revision": trace_gate.writes_while_armed,
            "z4_discharged": trace_gate.l2_discharges + trace_gate.l3_discharges}
           if z4_active else {}),
        **({"rq4b_replan": replan_state.stats()}
           if replan_state is not None else {}),
        **({"deu_trace": deu_trace,
            "deu_state_final": deu_state.snapshot(),
            "deu_marginal_utility_final": dict(deu_updater.Q),
            "adoption_log": adoption_log}
           if deu_state is not None else {}),
        **({"adapter_log": adapter_log} if adapter is not None else {}),
        **({"action_log": action_log} if selector is not None else {}),
        **({"control_log": controller.control_log,
            "control_state_final": controller.snapshot()}
           if controller is not None else {}),
        **({"d2_noise": {"seed": d2_noise.seed,
                         "seed_rule": "sha256('d2|<tag>|<case_id>')[:6]",
                         "tiers": d2_noise.tiers,
                         "recommended": d2_noise.recommended,
                         "q_anchor": d2_noise.q_anchor,
                         "draws": d2_noise_log}}
           if d2_noise is not None else {}),
        **({"d3_ledger_final": dict(d3_ledger),
            "utility_pinned_q0": dict(q_pinned or {}),
            "state_blind": True}
           if fcfg.VARIANT == "d3" else {}),
        **({"dcc_trace_schema": 1,
            "dcc_state": controller.dcc_state_final(),
            "decision_trace": controller.decision_trace}
           if fcfg.VARIANT == "dcc" and controller is not None else {}),
        "entry_point": case.get("entry_point"),
        "shots": shots,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "llm_call_log": call_log,
        "tool_log": tool_log[:120],
        "n_messages": len(messages),
        "had_tools": True,
        "tool_names": ["BatchProbe", "Write", "Eval"],
        "split": "dev" if case_id in fcfg.EQPA_DEV_CASES else "eval",
        "canary_hits": len(scan_text(blob)),
        "jail": str(session.host_dir),
        "model": config.MODEL,
        "started_utc": _started_utc,
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prior_sha256": uprior.prior_sha256(),
    }


def _evidence_tools() -> list[dict]:
    from exp.eqpa.tools import EVAL_TOOL, WRITE_TOOL
    return [fcfg.FCEA_TOOL, WRITE_TOOL, EVAL_TOOL]


def _safe_obs(text: str) -> str:
    if scan_text(text):
        return "REPL blocked: sealed pattern in output"
    return text


def _shot_row(k: int, exe: dict[str, Any], code: str) -> dict[str, Any]:
    return {"k": k,
            "passed": bool(exe.get("passed")),
            "error_message": (exe.get("error_message") or "")[:2000],
            "code_chars": len(code or ""),
            "code": code or ""}
