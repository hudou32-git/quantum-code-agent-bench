"""EQPA arm: Shell + Write + Eval. Same inner loop as E3 CTRL, OS-sandboxed Shell."""

from __future__ import annotations

from typing import Any

from exp.common.grader_qhe import run_candidate
from exp import config
from exp.eqpa.config import ARM_NAME, EQPA_DEV_CASES, EQPA_TAG, eqpa_system
from exp.common.cases import load_case
from exp.common.canary import scan_text
from exp.eqpa.jail import ensure_jail
from exp.eqpa.tools import (
    EQPA_TOOLS,
    run_eval,
    run_shell,
    run_write,
    workspace_block,
)
from exp.common.baseline.prompts import feedback_user, spec_user
from exp.common.parse import extract_module_v2 as extract_module
from exp.common.grader_qbplus import grade_qbplus, load_qbplus_case

MAX_SHELL_PER_SHOT = 8
MAX_LLM_PER_SHOT = 16
MAX_OFFICIAL = 3


def _grade(case: dict[str, Any], code: str, *, bench: str = "qhe", dest=None, k: int = 1, case_id: str = "", framework: str = "qiskit") -> dict[str, Any]:
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


def run_eqpa(case_id: str, client, *, tag: str | None = None, bench: str = "qhe", framework: str = "qiskit") -> dict[str, Any]:
    tag = tag or EQPA_TAG
    case = load_qbplus_case(case_id, framework=framework) if bench == "qbplus" else load_case(case_id)
    session = ensure_jail(case_id, tag=tag, prompt=case.get("prompt") or "")
    user0 = spec_user(case["prompt"], workspace_block(case_id=case_id))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": eqpa_system(framework)},
        {"role": "user", "content": user0},
    ]
    tool_log: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    # e7 plan P0-1: per-LLM-call audit log (finish_reason = max_tokens cutoff
    # signal) + usage totals — frozen EQPA rows carried neither (P0 gap).
    call_log: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    official = 0
    llm_calls = 0
    shell_calls = 0
    write_calls = 0
    eval_calls = 0
    fallback = False
    last_code = ""
    last_exe: dict[str, Any] = {
        "passed": False,
        "error_message": "no official submit",
        "error_type": "",
    }

    def grade_fn(code: str) -> dict[str, Any]:
        k = official + 1
        return _grade(case, code, bench=bench, dest=session.host_dir, k=k, case_id=case_id, framework=framework)

    while official < MAX_OFFICIAL:
        shells_this = 0
        llm_this = 0
        reminded = False
        shot_done = False
        while not shot_done and llm_this < MAX_LLM_PER_SHOT:
            res = client.chat_messages(messages, tools=EQPA_TOOLS)
            llm_calls += 1
            llm_this += 1
            u = res.usage or {}
            pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
            prompt_tokens += pt
            completion_tokens += ct
            # generation_guard detect-only (e7 2026-09-20): record the post-hoc
            # degenerate-repeat flag; never aborts, never retries, no verdict
            # change — the turn flows through the agent loop exactly as before.
            call_log.append({"i": llm_calls, "finish_reason": res.finish_reason or "",
                             "prompt_tokens": pt, "completion_tokens": ct,
                             "completion_tokens_estimated": bool(getattr(res, "completion_tokens_estimated", False)),
                             "degenerate_repeat": bool(getattr(res, "repeat_guard", None) and res.repeat_guard.get("fired"))})
            # e7 P0-7: a length-cut turn with no tool calls cannot advance the
            # episode — resample once. Tool-call turns cut mid-args are left to
            # the agent loop to recover from (server-parsed args may survive).
            if (res.finish_reason or "") == "length" and not res.tool_calls:
                call_log[-1]["length_cut_no_tool"] = True
                res = client.chat_messages(messages, tools=EQPA_TOOLS)
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
                    tool_log.append({"name": "Write", "fallback": True, **{x: wr[x] for x in wr if x != "contents"}})
                    ev = run_eval(session=session, k=k, grade_fn=grade_fn)
                    eval_calls += 1
                    official += 1
                    last_code = ev.get("code") or code
                    last_exe = {
                        "passed": bool(ev.get("passed")),
                        "error_message": ev.get("error") or "",
                        "error_type": "",
                    }
                    tool_log.append(
                        {
                            "name": "Eval",
                            "fallback": True,
                            "official_eval": True,
                            "passed": last_exe["passed"],
                            "text": (ev.get("text") or "")[:1500],
                        }
                    )
                    shots.append(_shot_row(k, last_exe, last_code))
                    shot_done = True
                    if last_exe.get("passed"):
                        break
                    messages.append(
                        {
                            "role": "user",
                            "content": feedback_user(
                                error=last_exe.get("error_message") or "",
                                attempt=official,
                            ),
                        }
                    )
                    continue
                if not reminded and shells_this >= 2:
                    reminded = True
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Use Shell to inspect, Write attempt_k.py "
                                "(exact filename attempt_1.py / attempt_2.py / attempt_3.py), then Eval()."
                            ),
                        }
                    )
                    continue
                if llm_this >= MAX_LLM_PER_SHOT:
                    break
                continue
            for call in calls:
                name = call.get("name") or ""
                args = call.get("arguments") or {}
                cid = call.get("id") or ""
                if name == "Write":
                    wr = run_write(
                        path=str(args.get("path") or ""),
                        contents=str(args.get("contents") or ""),
                        session=session,
                    )
                    write_calls += 1
                    tool_log.append({"name": "Write", **{x: wr[x] for x in wr if x != "contents"}})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": cid,
                            "name": "Write",
                            "content": _safe_obs(wr.get("text") or ""),
                        }
                    )
                    continue
                if name == "Shell":
                    sh = run_shell(str(args.get("command") or ""), session=session)
                    shells_this += 1
                    shell_calls += 1
                    tool_log.append(
                        {
                            "name": "Shell",
                            "kind": sh.get("kind"),
                            "blocked": sh.get("blocked"),
                            "sandboxed": True,
                            "text": (sh.get("text") or "")[:1500],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": cid,
                            "name": "Shell",
                            "content": _safe_obs(sh.get("text") or ""),
                        }
                    )
                    if shells_this >= MAX_SHELL_PER_SHOT and not reminded:
                        reminded = True
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Shell inspect budget for this attempt is used. "
                                    "Write attempt_k.py and call Eval()."
                                ),
                            }
                        )
                    continue
                if name == "Eval":
                    raw_k = args.get("k")
                    k_arg = int(raw_k) if raw_k not in (None, "") else None
                    ev = run_eval(session=session, k=k_arg, grade_fn=grade_fn)
                    eval_calls += 1
                    tool_log.append(
                        {
                            "name": "Eval",
                            "official_eval": bool(ev.get("official_eval")),
                            "passed": ev.get("passed"),
                            "text": (ev.get("text") or "")[:1500],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": cid,
                            "name": "Eval",
                            "content": _safe_obs(ev.get("text") or ""),
                        }
                    )
                    if not ev.get("official_eval"):
                        continue
                    official += 1
                    last_code = ev.get("code") or last_code
                    last_exe = {
                        "passed": bool(ev.get("passed")),
                        "error_message": ev.get("error") or "",
                        "error_type": "",
                    }
                    shots.append(_shot_row(official, last_exe, last_code))
                    shot_done = True
                    if last_exe.get("passed"):
                        break
                    messages.append(
                        {
                            "role": "user",
                            "content": feedback_user(
                                error=last_exe.get("error_message") or "",
                                attempt=official,
                            ),
                        }
                    )
                    break
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": cid,
                        "content": f"unknown tool {name}",
                    }
                )
            if last_exe.get("passed"):
                break
        if last_exe.get("passed"):
            break
        if not shot_done:
            official += 1
            last_exe = {
                "passed": False,
                "error_message": "no official submit this attempt",
                "error_type": "NoSubmit",
            }
            shots.append(_shot_row(official, last_exe, last_code))
            if official < MAX_OFFICIAL:
                messages.append(
                    {
                        "role": "user",
                        "content": feedback_user(
                            error=last_exe["error_message"],
                            attempt=official,
                        ),
                    }
                )

    passed = bool(last_exe.get("passed"))
    blob = "\n".join(
        [
            last_code or "",
            last_exe.get("error_message") or "",
            *(str(t.get("text") or "") for t in tool_log),
        ]
    )
    return {
        "case_id": case_id,
        "arm": ARM_NAME,
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
        "entry_point": case.get("entry_point"),
        "shots": shots,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "llm_call_log": call_log,
        "tool_log": tool_log[:80],
        "n_messages": len(messages),
        "had_tools": True,
        "tool_names": ["Shell", "Write", "Eval"],
        "split": "dev" if case_id in EQPA_DEV_CASES else "eval",
        "canary_hits": len(scan_text(blob)),
        "jail": str(session.host_dir),
    }


def _safe_obs(text: str) -> str:
    if scan_text(text):
        return "REPL blocked: sealed pattern in output"
    return text


def _shot_row(k: int, exe: dict[str, Any], code: str) -> dict[str, Any]:
    return {
        "k": k,
        "passed": bool(exe.get("passed")),
        "error_message": (exe.get("error_message") or "")[:2000],
        "code_chars": len(code or ""),
        # P0-2: keep the exact graded submission text per attempt
        "code": code or "",
    }
