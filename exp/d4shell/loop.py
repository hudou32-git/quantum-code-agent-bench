"""D4 (full − C0) episode loop: DEU-RQ's decision stack over free-form Shell.

Mirror of exp.fcea.loop (deurc_noctx path) with ONE structural difference:
the BatchProbe substrate is replaced by the EQPA free-form Shell — exactly the
C0 removal. Everything above the substrate is the same machinery, imported
unchanged from exp.fcea:

  C1  DynamicEvidenceStateManager   (error-state tracking)
  C2  frozen prior Q0 + DynamicUtilityUpdater (EMA Q(e, s_t))
  C3  RepairController (exp.fcea.config.DEURC_NOCTX constants)

Interface adaptations are D4-1..D4-6 (see config.py); the loop implements
them at the shell-execution site, the tool list, and the system prompt only.
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
from exp.fcea.control.controller import RepairController
from exp.fcea.evidence.taxonomy import classify_evidence_output
from exp.fcea.evidence.planner import utility_notice
from exp.fcea.tracing import trace as ftrace
from exp.fcea.utility import prior as uprior
from exp.fcea.utility.scorer import classify_failure
from exp.fcea.utility.state import DynamicEvidenceStateManager
from exp.fcea.utility.updater import DynamicUtilityUpdater
from exp.d4shell import config as dcfg

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


def run_d4(case_id: str, client, *, tag: str | None = None, bench: str = "qbplus") -> dict[str, Any]:
    tag = tag or dcfg.default_tag(bench=bench)
    dcfg.refuse_foreign_tag(tag)
    case = load_qbplus_case(case_id) if bench == "qbplus" else load_case(case_id)
    session = ensure_jail(case_id, tag=tag, prompt=case.get("prompt") or "")
    user0 = spec_user(case["prompt"], workspace_block(case_id=case_id))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": dcfg.D4_SYSTEM},
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
    # C1 + C2: the full DEU machinery, unchanged from the fcea deurc path
    deu_state = DynamicEvidenceStateManager(fcfg.DEU_CONSTANTS)
    deu_updater = DynamicUtilityUpdater(uprior.global_q0(), fcfg.DEU_CONSTANTS)
    deu_trace: list[dict] = []
    consec_zero_nov = 0
    # C3: the full controller on the deurc_noctx constants (context gate OFF)
    controller = RepairController(dcfg.D4_CONTROLLER_CONSTANTS)
    rc_blocked_note = 0

    def record_deu_step(passed: bool, error_message: str, code: str,
                        *, nosubmit: bool = False) -> None:
        nonlocal consec_zero_nov
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
        if not nosubmit and ctx != "Other":
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
        if not deu_trace:
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

    def _episode_tools() -> list[dict]:
        # D4-3: mirror the frozen deurc withdrawal semantics — the tool stays
        # in the list and refusal happens at execution (the frozen fcea
        # tools-list filter is a no-op because BATCH_TOOL carries no top-level
        # "name" field; discovered in the 2026-09-25 audit and deliberately
        # NOT "fixed" — identity preservation). The commitment effect is the
        # same: after FOCUS/TERMINATE, Shell calls get the controller refusal
        # message and never execute.
        return [SHELL_TOOL, WRITE_TOOL, EVAL_TOOL]

    while official < MAX_OFFICIAL:
        shells_this = 0
        llm_this = 0
        reminded = False
        shot_done = False
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
                             "degenerate_repeat": bool(getattr(res, "repeat_guard", None) and res.repeat_guard.get("fired"))})
            if (res.finish_reason or "") == "length" and not res.tool_calls:
                call_log[-1]["length_cut_no_tool"] = True
                res = client.chat_messages(messages, tools=_episode_tools())
                llm_calls += 1
                llm_this += 1
                u = res.usage or {}
                pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
                prompt_tokens += pt
                completion_tokens += ct
                call_log.append({"i": llm_calls, "finish_reason": res.finish_reason or "",
                                 "prompt_tokens": pt, "completion_tokens": ct,
                                 "length_retry": True})
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
                    tool_log.append({"name": "Write", "fallback": True,
                                     **{x: wr[x] for x in wr if x != "contents"}})
                    ev = run_eval(session=session, k=k, grade_fn=grade_fn)
                    eval_calls += 1
                    official += 1
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
                if not reminded and shells_this >= 2 and not controller.probe_withdrawn():
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
                    if controller.probe_withdrawn():
                        rc_blocked_note += 1
                        messages.append({"role": "tool", "tool_call_id": cid,
                                         "name": "Shell",
                                         "content": "Shell is disabled by the repair "
                                         "controller (mode=%s). Proceed without new evidence."
                                         % controller.current_mode})
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
                        # (no requested-kind channel on free-form commands)
                        out = sh.get("text") or ""
                        cat, _conf = classify_evidence_output(out)
                        evidence_chars += len(out)
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
        "variant": "d4_shell",
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
           "deu_state_final": deu_state.snapshot(),
           "deu_marginal_utility_final": dict(deu_updater.Q)},
        **{"control_log": controller.control_log,
           "control_state_final": controller.snapshot()},
        "controller_shell_withdrawn_final": controller.probe_withdrawn(),
        "controller_shell_refusals": rc_blocked_note,
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
