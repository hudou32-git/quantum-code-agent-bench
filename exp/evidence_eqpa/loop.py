"""Evidence-EQPA episode loop.

Mirror of exp.eqpa.loop (protocol parity: LLM/official budgets, per-call audit
log, P0-7 length-cut resample, Write/Eval semantics, fallback submit, NoSubmit
penalty, canary gating, pass-stop) with ONE substitution: free-form per-command
Shell is replaced by BatchProbe (batched, structured, clipped evidence). On top,
two feature-flagged harness hints may be enabled by the runner:
  - planning (--planning): after a failed official Eval, inject an evidence-plan
    suggestion derived from the failure text (probe-menu only; no tool gating);
  - progress (--progress): when the official error repeats verbatim (normalized),
    inject a switch-strategy notice (re-diagnosis, never a stop).
"""

from __future__ import annotations

import re
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
from exp.evidence_eqpa import config as bcfg
from exp.evidence_eqpa.prompts import (
    PROBE_BUDGET_NOTICE,
    REPLAN_NOTICE,
    plan_from_error,
    workspace_block,
)
from exp.evidence_eqpa.tools import EVIDENCE_TOOLS, run_batch_probe

MAX_LLM_PER_SHOT = bcfg.MAX_LLM_PER_SHOT
MAX_OFFICIAL = bcfg.MAX_OFFICIAL


def _norm_err(msg: str) -> str:
    t = (msg or "").strip()
    t = re.sub(r"/[\w./+-]+", " <P> ", t)
    t = re.sub(r"0x[0-9a-fA-F]+", " <A> ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()[:200]


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


def run_evidence_eqpa(case_id: str, client, *, tag: str | None = None, bench: str = "qhe") -> dict[str, Any]:
    tag = tag or bcfg.default_tag(bench=bench)
    bcfg.refuse_foreign_tag(tag)
    case = load_qbplus_case(case_id) if bench == "qbplus" else load_case(case_id)
    session = ensure_jail(case_id, tag=tag, prompt=case.get("prompt") or "")
    user0 = spec_user(case["prompt"], workspace_block(case_id=case_id))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": bcfg.BATCH_SYSTEM},
        {"role": "user", "content": user0},
    ]
    tool_log: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    call_log: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    official = 0
    llm_calls = 0
    write_calls = 0
    eval_calls = 0
    fallback = False
    # ---- batch interaction accounting ----
    probe_rounds = 0
    probe_queries = 0
    batch_sizes: list[int] = []
    evidence_chars = 0
    plan_injections = 0
    replan_injections = 0
    prev_failed_error = ""
    last_code = ""
    last_exe: dict[str, Any] = {"passed": False, "error_message": "no official submit", "error_type": ""}

    def grade_fn(code: str) -> dict[str, Any]:
        k = official + 1
        return _grade(case, code, bench=bench, dest=session.host_dir, k=k, case_id=case_id)

    while official < MAX_OFFICIAL:
        rounds_this = 0
        probes_this = 0
        llm_this = 0
        reminded = False
        planned_this = False
        replanned_this = False
        shot_done = False
        while not shot_done and llm_this < MAX_LLM_PER_SHOT:
            res = client.chat_messages(messages, tools=EVIDENCE_TOOLS)
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
                res = client.chat_messages(messages, tools=EVIDENCE_TOOLS)
                llm_calls += 1
                llm_this += 1
                u = res.usage or {}
                pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
                prompt_tokens += pt
                completion_tokens += ct
                call_log.append({"i": llm_calls, "finish_reason": res.finish_reason or "",
                                 "prompt_tokens": pt, "completion_tokens": ct,
                                 "length_retry": True})
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
                    shot_done = True
                    if last_exe.get("passed"):
                        break
                    messages.append({"role": "user", "content": feedback_user(
                        error=last_exe.get("error_message") or "", attempt=official)})
                    continue
                if not reminded and rounds_this >= 2:
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
                if name == "BatchProbe":
                    pr = run_batch_probe(args.get("queries"), session=session)
                    n_run = int(pr.get("n_run") or 0)
                    probe_rounds += 1
                    rounds_this += 1
                    probe_queries += n_run
                    probes_this += n_run
                    batch_sizes.append(n_run)
                    for e in pr.get("evidence") or []:
                        evidence_chars += len(e.get("output") or "")
                    tool_log.append({"name": "BatchProbe", "round": probe_rounds,
                                     "n_run": n_run, "n_requested": pr.get("n_requested"),
                                     "blocked": bool(pr.get("blocked")),
                                     "sandboxed": True,
                                     "text": (pr.get("text") or "")[:1500]})
                    messages.append({"role": "tool", "tool_call_id": cid, "name": "BatchProbe",
                                     "content": _safe_obs(pr.get("text") or "")})
                    if probes_this >= bcfg.MAX_PROBES_PER_SHOT and not reminded:
                        reminded = True
                        messages.append({"role": "user", "content": PROBE_BUDGET_NOTICE.format(
                            n=probes_this, rounds=rounds_this)})
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
                    shot_done = True
                    if last_exe.get("passed"):
                        break
                    cur_err = last_exe.get("error_message") or ""
                    if bcfg.PLANNING_ENABLED and not planned_this:
                        planned_this = True
                        plan_injections += 1
                        messages.append({"role": "user", "content": plan_from_error(cur_err)})
                    if (bcfg.PROGRESS_ENABLED and prev_failed_error
                            and _norm_err(cur_err) == _norm_err(prev_failed_error)
                            and not replanned_this):
                        replanned_this = True
                        replan_injections += 1
                        messages.append({"role": "user", "content": REPLAN_NOTICE})
                    prev_failed_error = cur_err
                    messages.append({"role": "user", "content": feedback_user(
                        error=cur_err, attempt=official)})
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
            if official < MAX_OFFICIAL:
                messages.append({"role": "user", "content": feedback_user(
                    error=last_exe["error_message"], attempt=official)})

    passed = bool(last_exe.get("passed"))
    blob = "\n".join([last_code or "", last_exe.get("error_message") or "",
                      *(str(t.get("text") or "") for t in tool_log)])
    avg_batch = round(probe_queries / probe_rounds, 2) if probe_rounds else 0.0
    return {
        "case_id": case_id,
        "arm": bcfg.ARM_NAME,
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
        # ---- interaction-efficiency fields (new in this branch) ----
        "tool_rounds": probe_rounds,
        "probe_queries": probe_queries,
        "batch_sizes": batch_sizes,
        "avg_batch": avg_batch,
        "evidence_chars": evidence_chars,
        "plan_injections": plan_injections,
        "replan_injections": replan_injections,
        "planning_enabled": bcfg.PLANNING_ENABLED,
        "progress_enabled": bcfg.PROGRESS_ENABLED,
        "entry_point": case.get("entry_point"),
        "shots": shots,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "llm_call_log": call_log,
        "tool_log": tool_log[:120],
        "n_messages": len(messages),
        "had_tools": True,
        "tool_names": ["BatchProbe", "Write", "Eval"],
        "split": "dev" if case_id in bcfg.EQPA_DEV_CASES else "eval",
        "canary_hits": len(scan_text(blob)),
        "jail": str(session.host_dir),
        "model": config.MODEL,
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
