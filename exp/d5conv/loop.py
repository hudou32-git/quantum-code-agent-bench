"""D5 (d5conv) episode loop: d4shell + A1 + A2 + B1 + B2.

Mirror of exp.d4shell.loop with exactly the four frozen deviations
(docs/protocols/d5conv_design_20261001.md):

  D5-1 (A1)  Shell hard budget      — execution-layer refusal past
             MAX_SHELL_PER_SHOT executed shells in the shot.
  D5-2 (A2)  Deadline ladder        — escalation message before call 13,
             Shell removed from the tools list from call 15 while the shot
             has no official eval (invariant I-1: after llm_this>=14 the
             only executable tools are Write and Eval).
  D5-3 (B1)  Corrective retry       — directive injected before the single
             length resample; truncated messages are discarded.
  D5-4 (B2)  Fallback artifact gate — extracted fallback code passes the
             frozen preflight before consuming an official attempt.

Everything else — C1/C2/C3 DEU machinery, prompts, budgets, controller,
termination, NoSubmit accounting — is line-identical to d4shell.
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
from exp.eqpa.tools import (EVAL_TOOL, SHELL_TOOL, WRITE_TOOL,
                            run_eval, run_shell, run_write, workspace_block)
from exp.fcea import config as fcfg
from exp.fcea.control import preflight as mech_preflight
from exp.fcea.control import execution_guard as _execg
from exp.fcea.control.controller import RepairController
from exp.fcea.evidence.taxonomy import classify_evidence_output
from exp.fcea.evidence.planner import utility_notice
from exp.fcea.tracing import trace as ftrace
from exp.fcea.utility import prior as uprior
from exp.fcea.utility.scorer import classify_failure
from exp.fcea.utility.state import DynamicEvidenceStateManager
from exp.fcea.utility.updater import DynamicUtilityUpdater
from exp.d5conv import config as dcfg

MAX_LLM_PER_SHOT = dcfg.MAX_LLM_PER_SHOT
MAX_OFFICIAL = dcfg.MAX_OFFICIAL
MAX_SHELL_PER_SHOT = dcfg.MAX_SHELL_PER_SHOT


def _grade(case: dict[str, Any], code: str, *, bench: str = "qhe", dest=None, k: int = 1,
           case_id: str = "") -> dict[str, Any]:
    if bench == "qbplus":
        return grade_qbplus(case, code, dest=dest, k=k)
    return run_candidate(
        code=code or "",
        test=case["test"],
        entry=case["entry_point"],
        prompt=case["prompt"],
        timeout=60.0,
        case_id=str(case_id),
    )


def run_d5(case_id: str, client, *, tag: str | None = None, bench: str = "qbplus") -> dict[str, Any]:
    tag = tag or dcfg.default_tag(bench=bench)
    dcfg.refuse_foreign_tag(tag)
    # wall-clock audit anchors (P0-1 drift sensitivity; v4.1 cost telemetry)
    _started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    case = load_qbplus_case(case_id) if bench == "qbplus" else load_case(case_id)
    session = ensure_jail(case_id, tag=tag, prompt=case.get("prompt") or "")
    user0 = spec_user(case["prompt"], workspace_block(case_id=case_id))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": dcfg.D5_SYSTEM},
        {"role": "user", "content": user0},
    ]
    tool_log: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    call_log: list[dict[str, Any]] = []
    etrace = ftrace.new_episode_trace()
    prompt_tokens = 0
    completion_tokens = 0
    official = 0
    llm_calls = 0
    shell_calls = 0
    write_calls = 0
    eval_calls = 0
    fallback = False
    evidence_chars = 0
    priority_injections = 0
    shell_rounds = 0
    last_code = ""
    last_exe: dict[str, Any] = {"passed": False, "error_message": "no official submit",
                                "error_type": ""}
    # C1 + C2: the full DEU machinery, unchanged from the fcea deurc path.
    # E0 (CONTROLLER_OFF): the whole Z2 stack is absent — no C1/C2 bookkeeping
    # (matching the fcea-side deurq_z1, where deu_state is None), no C3.
    _e0 = dcfg.CONTROLLER_OFF
    deu_state = None if _e0 else DynamicEvidenceStateManager(fcfg.DEU_CONSTANTS)
    deu_updater = (None if _e0
                   else DynamicUtilityUpdater(uprior.global_q0(), fcfg.DEU_CONSTANTS))
    deu_trace: list[dict] = []
    consec_zero_nov = 0
    # C3: the full controller on the deurc_noctx constants (context gate OFF)
    controller = None if _e0 else RepairController(dcfg.D4_CONTROLLER_CONSTANTS)
    rc_blocked_note = 0
    # D5 attribution counters (design doc §7)
    shell_budget_refusals = 0
    shell_deadline_refusals = 0
    escalate_injections = 0
    narrowed_shots = 0
    retry_corrected = 0
    artifact_gate_rejects = 0
    # E0 additions (fcea execution_guard parity): episode length fuse + slot
    # salvage; graded_attempts dedupes salvage against already-graded files.
    exec_fuse = _execg.LengthFuse(dcfg.LENGTH_FUSE_CAP or 0)
    fuse_directed_shot = False
    fuse_blown_shots = 0
    slot_salvages = 0
    graded_attempts: set[str] = set()

    def record_deu_step(passed: bool, error_message: str, code: str,
                        *, nosubmit: bool = False) -> None:
        nonlocal consec_zero_nov
        if deu_state is None:
            return
        step_rec = deu_state.on_eval_result(shot=official, passed=passed,
                                            error_message=error_message, code=code,
                                            nosubmit=nosubmit)
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
        deu_trace.append(step_rec)
        deu_state.on_code_submitted(code)

    def grade_fn(code: str) -> dict[str, Any]:
        k = official + 1
        return _grade(case, code, bench=bench, dest=session.host_dir, k=k, case_id=case_id)

    def inject_priority(error_message: str) -> None:
        nonlocal priority_injections
        cls = classify_failure(error_message)
        ctx = cls["failure_context"]
        nosubmit = ctx == "NoSubmit"
        injected = False
        # E0 (CONTROLLER_OFF): the evidence-priority notice is part of the Z2
        # decision stack — not injected. The failure event is still recorded.
        if (not nosubmit and ctx != "Other" and controller is not None):
            notice = utility_notice(variant="deurc_noctx", failure_context=ctx,
                                    confidence=cls["confidence"])
            messages.append({"role": "user", "content": notice})
            priority_injections += 1
            injected = True
        ftrace.record_failure(
            etrace, shot=official, error_message=error_message,
            failure_context=ctx, confidence=cls["confidence"], nosubmit=nosubmit,
            utility_prior=uprior.tiers_for("deurc_noctx", ctx) if not nosubmit else None,
            recommended=uprior.recommended_for("deurc_noctx", ctx) if not nosubmit else None,
            injected=injected)

    def run_controller(boundary_kind: str) -> None:
        """C3 boundary decision — identical to the fcea deurc path (real Q)."""
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
        rec = controller.on_boundary(
            step=official, boundary_kind=boundary_kind, task_id=case_id,
            no_progress_count=int(cur.get("no_progress_count") or 0),
            same_error_count=int(cur.get("same_error_count") or 0),
            code_changed=bool(cur.get("code_changed")),
            progress_score=int(cur.get("progress_score") or 0),
            novelty_mean_now=nov_now, novelty_mean_prev=nov_prev,
            family_novelty_now=dict(novs), family_novelty_prev=dict(pnovs),
            utility_drop=drop,
            Q=dict(deu_updater.Q),
            evidence_used=cur.get("evidence_used") or {},
            evidence_samples=sum((cur.get("evidence_used") or {}).values()),
            error_message=cur.get("error_after") or "", ts=time.time())
        new_msgs, ctx_stats = controller.assemble_context(messages)
        messages[:] = new_msgs
        rec["context_stats"] = ctx_stats
        msg = rec["message_text"]
        if msg and official < MAX_OFFICIAL:
            messages.append({"role": "user", "content": msg})

    def _episode_tools(narrowed: bool = False) -> list[dict]:
        # D4-3 base semantics kept (tool list flat, controller withdrawal at
        # execution); D5-2 adds the deadline narrowing on top: a WORKING
        # filter on function.name (the frozen fcea/d4shell filter checked a
        # non-existent top-level "name" key and was a no-op).
        tools = [SHELL_TOOL, WRITE_TOOL, EVAL_TOOL]
        if narrowed:
            tools = [t for t in tools
                     if t.get("function", {}).get("name") != "Shell"]
        return tools

    while official < MAX_OFFICIAL:
        shells_this = 0
        llm_this = 0
        reminded = False
        shot_done = False
        # D5-2 per-shot ladder state
        escalated = False
        narrowed = False
        writes_this_ok = 0
        file_gate_rejected = False
        fuse_directed_shot = False
        while not shot_done and llm_this < MAX_LLM_PER_SHOT:
            # D5-2 (A2): deadline ladder, evaluated pre-call (llm_this = calls
            # already consumed; the call about to be made is llm_this + 1).
            # E0 (CONVERT_LADDER_OFF): the ladder has no fcea-side counterpart,
            # so it is disabled for the ladder arms (audit C1 symmetry).
            if not shot_done and not dcfg.CONVERT_LADDER_OFF:
                if (dcfg.CONVERT_ESCALATE_AT is not None
                        and llm_this >= dcfg.CONVERT_ESCALATE_AT and not escalated):
                    escalated = True
                    escalate_injections += 1
                    messages.append({"role": "user", "content": dcfg.A2_S1.format(
                        k=official + 1, left=MAX_LLM_PER_SHOT - llm_this)})
                if (dcfg.CONVERT_NARROW_AT is not None
                        and llm_this >= dcfg.CONVERT_NARROW_AT and not narrowed):
                    narrowed = True
                    narrowed_shots += 1
                    if file_gate_rejected:
                        s2 = dcfg.A2_S2_FIX.format(k=official + 1)
                    elif writes_this_ok > 0:
                        s2 = dcfg.A2_S2_EVAL.format(k=official + 1)
                    else:
                        s2 = dcfg.A2_S2_WRITE.format(k=official + 1)
                    messages.append({"role": "user", "content": s2})
            res = client.chat_messages(messages, tools=_episode_tools(narrowed))
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
                # D5-3 (B1): corrective directive BEFORE the resample; the
                # truncated assistant message stays discarded (never
                # appended, its tokens never re-sent).
                # E0 fuse (LENGTH_FUSE_CAP, fcea execution_guard parity): once
                # the episode cap is blown, no further resample is paid and
                # the shot gets one hard submit directive. Legacy (cap None)
                # keeps the unconditional-resample behavior byte-identical.
                _resample = True
                if (dcfg.LENGTH_FUSE_CAP is not None
                        and exec_fuse.on_cut() != "retry"):
                    _resample = False
                    if not fuse_directed_shot:
                        fuse_directed_shot = True
                        fuse_blown_shots += 1
                        messages.append({"role": "user",
                                         "content": _execg.FUSE_TEXT})
                elif dcfg.RETRY_CORRECTIVE:
                    messages.append({"role": "user", "content": dcfg.B1_CORRECTIVE.format(
                        k=official + 1)})
                if _resample:
                    res = client.chat_messages(messages, tools=_episode_tools(narrowed))
                    llm_calls += 1
                    llm_this += 1
                    u = res.usage or {}
                    pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
                    prompt_tokens += pt
                    completion_tokens += ct
                    retry_entry = {"i": llm_calls, "finish_reason": res.finish_reason or "",
                                   "prompt_tokens": pt, "completion_tokens": ct,
                                   "duration_ms": round(1000 * float(getattr(res, "wall_time", 0) or 0), 1),
                                   "length_retry": True}
                    if dcfg.RETRY_CORRECTIVE:
                        retry_entry["corrected_retry"] = True
                        retry_corrected += 1
                    call_log.append(retry_entry)
                    if (dcfg.RETRY_CORRECTIVE
                            and (res.finish_reason or "") == "length" and not res.tool_calls):
                        # double cut: no further resample; discard the truncated
                        # retry too — nothing from it may reach the fallback path.
                        continue
            if deu_state is not None:
                deu_state.on_shot_state(llm_this, MAX_LLM_PER_SHOT)
            messages.append(res.assistant_message or {"role": "assistant", "content": res.content})
            calls = list(res.tool_calls or [])
            if not calls:
                code = extract_module(res.content)
                if code.strip():
                    fallback = True
                    k = official + 1
                    wr = run_write(path=f"attempt_{k}.py", contents=code, session=session)
                    write_calls += 1
                    if wr.get("ok"):
                        writes_this_ok += 1
                        file_gate_rejected = False
                    tool_log.append({"name": "Write", "fallback": True,
                                     **{x: wr[x] for x in wr if x != "contents"}})
                    if dcfg.FALLBACK_ARTIFACT_GATE and wr.get("ok"):
                        # D5-4 (B2): the extracted artifact must survive the
                        # frozen preflight (compile+exec) before it may
                        # consume an official attempt. indeterminate FAILS
                        # OPEN — the official Eval proceeds.
                        _pf = mech_preflight.run_preflight(f"attempt_{k}.py",
                                                           session=session)
                        if _pf.get("outcome") == "failed":
                            artifact_gate_rejects += 1
                            file_gate_rejected = True
                            tb = (_pf.get("tb") or _pf.get("error") or "")[-400:]
                            tool_log.append({"name": "ArtifactGate", "rejected": True,
                                             "attempt_file": f"attempt_{k}.py",
                                             "text": tb})
                            messages.append({"role": "user", "content": dcfg.B2_REJECT.format(
                                k=k, tb=tb)})
                            continue
                    ev = run_eval(session=session, k=k, grade_fn=grade_fn)
                    eval_calls += 1
                    official += 1
                    if dcfg.SLOT_SALVAGE and ev.get("path"):
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
                        break
                    inject_priority(last_exe.get("error_message") or "")
                    messages.append({"role": "user", "content": feedback_user(
                        error=last_exe.get("error_message") or "", attempt=official)})
                    continue
                if (not reminded and shells_this >= 2
                        and (controller is None or not controller.probe_withdrawn())):
                    reminded = True
                    messages.append({"role": "user", "content": (
                        "Use Shell to inspect, Write attempt_k.py "
                        "(exact filename attempt_1.py / attempt_2.py / attempt_3.py), then Eval().")})
                    continue
                if llm_this >= MAX_LLM_PER_SHOT:
                    break
                continue
            for call in calls:
                name = call.get("name") or ""
                args = call.get("arguments") or {}
                cid = call.get("id") or ""
                if name == "Shell":
                    if controller is not None and controller.probe_withdrawn():
                        rc_blocked_note += 1
                        messages.append({"role": "tool", "tool_call_id": cid,
                                         "name": "Shell",
                                         "content": "Shell is disabled by the repair "
                                         "controller (mode=%s). Proceed without new evidence."
                                         % controller.current_mode})
                        continue
                    if narrowed:
                        # D5-2: the model emitted a Shell call although it is
                        # no longer in the tools list (deadline refusal)
                        shell_deadline_refusals += 1
                        tool_log.append({"name": "Shell", "blocked": True,
                                         "deadline": True})
                        messages.append({"role": "tool", "tool_call_id": cid,
                                         "name": "Shell",
                                         "content": dcfg.A2_DEADLINE_REFUSAL})
                        continue
                    if dcfg.SHELL_BUDGET_HARD and shells_this >= MAX_SHELL_PER_SHOT:
                        # D5-1 (A1): execution-layer hard budget
                        shell_budget_refusals += 1
                        tool_log.append({"name": "Shell", "blocked": True,
                                         "budget": True})
                        messages.append({"role": "tool", "tool_call_id": cid,
                                         "name": "Shell",
                                         "content": dcfg.A1_REFUSAL.format(
                                             used=MAX_SHELL_PER_SHOT,
                                             cap=MAX_SHELL_PER_SHOT,
                                             k=official + 1)})
                        continue
                    sh = run_shell(str(args.get("command") or ""), session=session)
                    shells_this += 1
                    shell_calls += 1
                    shell_rounds += 1
                    tool_log.append({"name": "Shell", "kind": sh.get("kind"),
                                     "blocked": sh.get("blocked"),
                                     "sandboxed": True,
                                     "text": (sh.get("text") or "")[:1500]})
                    messages.append({"role": "tool", "tool_call_id": cid, "name": "Shell",
                                     "content": _safe_obs(sh.get("text") or "")})
                    if not sh.get("blocked"):
                        # D4-1: family attribution by output classification
                        out = sh.get("text") or ""
                        cat, _conf = classify_evidence_output(out)
                        evidence_chars += len(out)
                        if deu_state is not None:
                            deu_state.on_probes(official + 1,
                                                [{"category": cat, "output": out}])
                        ftrace.record_probes(etrace, round_no=shell_rounds,
                                             shot=official + 1,
                                             evidence=[{"kind": "", "query": str(args.get("command") or ""),
                                                        "ok": bool(sh.get("ok")),
                                                        "status": "ok" if sh.get("ok") else (sh.get("reason") or "nonzero exit"),
                                                        "output": out}],
                                             rejected=[],
                                             classify_output=classify_evidence_output)
                    if shells_this >= MAX_SHELL_PER_SHOT and not reminded:
                        reminded = True
                        messages.append({"role": "user", "content": (
                            "Shell inspect budget for this attempt is used. "
                            "Write attempt_k.py and call Eval().")})
                    continue
                if name == "Write":
                    wr = run_write(path=str(args.get("path") or ""),
                                   contents=str(args.get("contents") or ""), session=session)
                    write_calls += 1
                    if wr.get("ok"):
                        writes_this_ok += 1
                        file_gate_rejected = False
                    tool_log.append({"name": "Write", **{x: wr[x] for x in wr if x != "contents"}})
                    messages.append({"role": "tool", "tool_call_id": cid, "name": "Write",
                                     "content": _safe_obs(wr.get("text") or "")})
                    continue
                if name == "Eval":
                    raw_k = args.get("k")
                    k_arg = int(raw_k) if raw_k not in (None, "") else None
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
                    if dcfg.SLOT_SALVAGE and ev.get("path"):
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
                        break
                    run_controller("error")
                    inject_priority(last_exe.get("error_message") or "")
                    messages.append({"role": "user", "content": feedback_user(
                        error=last_exe.get("error_message") or "", attempt=official)})
                    break
                messages.append({"role": "tool", "tool_call_id": cid,
                                 "content": f"unknown tool {name}"})
            if last_exe.get("passed"):
                break
        if last_exe.get("passed"):
            break
        if not shot_done:
            # E0 slot salvage (fcea execution_guard parity): the attempt slot
            # burns either way, so a written-but-never-graded candidate is
            # officially graded instead of recorded as NoSubmit.
            _salvage = None
            if dcfg.SLOT_SALVAGE:
                _cand = getattr(session, "last_write_name", None)
                if (_cand and _cand in getattr(session, "written", set())
                        and _cand not in graded_attempts):
                    _salvage = _cand
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
                run_controller("error")
                inject_priority(last_exe["error_message"] or "")
                if official < MAX_OFFICIAL:
                    messages.append({"role": "user", "content": feedback_user(
                        error=last_exe["error_message"] or "", attempt=official)})
                continue
            official += 1
            last_exe = {"passed": False, "error_message": "no official submit this attempt",
                        "error_type": "NoSubmit"}
            shots.append(_shot_row(official, last_exe, last_code))
            record_deu_step(False, last_exe["error_message"], last_code, nosubmit=True)
            run_controller("nosubmit")
            inject_priority(last_exe["error_message"])  # records nosubmit, injects nothing
            if official < MAX_OFFICIAL:
                messages.append({"role": "user", "content": feedback_user(
                    error=last_exe["error_message"], attempt=official)})

    passed = bool(last_exe.get("passed"))
    blob = "\n".join([last_code or "", last_exe.get("error_message") or "",
                      *(str(t.get("text") or "") for t in tool_log)])
    return {
        "case_id": case_id,
        "arm": dcfg.ARM_NAME,
        "variant": "react_e0" if _e0 else "d5_conv",
        "passed": passed,
        "pass_fail": "PASS" if passed else "FAIL",
        "error_message": last_exe.get("error_message") or "",
        "error_type": last_exe.get("error_type") or "",
        "parsed_code": last_code,
        "llm_calls": llm_calls,
        "shell_calls": shell_calls,
        "write_calls": write_calls,
        "eval_calls": eval_calls,
        "official_submits": official,
        "fallback": fallback,
        "shell_rounds": shell_rounds,
        "evidence_chars": evidence_chars,
        "priority_injections": priority_injections,
        "probe_log": etrace["probe_log"],
        "failure_events": etrace["failure_events"],
        **{"deu_trace": deu_trace,
           "deu_state_final": deu_state.snapshot() if deu_state is not None else None,
           "deu_marginal_utility_final": dict(deu_updater.Q) if deu_updater is not None else {}},
        **{"control_log": controller.control_log if controller is not None else [],
           "control_state_final": controller.snapshot() if controller is not None else None},
        "controller_shell_withdrawn_final": (controller.probe_withdrawn()
                                             if controller is not None else None),
        "controller_shell_refusals": rc_blocked_note,
        # D5 attribution counters (design doc §7)
        "shell_budget_refusals": shell_budget_refusals,
        "shell_deadline_refusals": shell_deadline_refusals,
        "escalate_injections": escalate_injections,
        "narrowed_shots": narrowed_shots,
        "retry_corrected": retry_corrected,
        "artifact_gate_rejects": artifact_gate_rejects,
        # E0 additions (fcea execution_guard parity)
        "length_cuts": exec_fuse.cuts,
        "fuse_blown_shots": fuse_blown_shots,
        "slot_salvages": slot_salvages,
        "entry_point": case.get("entry_point"),
        "shots": shots,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "llm_call_log": call_log,
        "tool_log": tool_log[:120],
        "n_messages": len(messages),
        "had_tools": True,
        "tool_names": ["Shell", "Write", "Eval"],
        "split": "dev" if case_id in dcfg.EQPA_DEV_CASES else "eval",
        "canary_hits": len(scan_text(blob)),
        "jail": str(session.host_dir),
        "model": config.MODEL,
        "started_utc": _started_utc,
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prior_sha256": uprior.prior_sha256(),
    }


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
