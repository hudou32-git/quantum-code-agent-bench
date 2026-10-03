"""Ablation episode controller: one (task, arm) -> logged episode row.

Differences from frozen ctrl_iso_loop (all by design, freeze plan v3 §3-10):
- toolset per arm; Submit is terminal and returns no result;
- gateway-filtered Shell (B: none; C: inspect-only);
- budgets frozen in arms.FROZEN_BUDGETS, action-opportunity based;
- R: on official Eval mismatch, wipe conversation (keep jail), rebuild with
  original task + latest Eval feedback only;
- primary outcome terminal_candidate_pass: offline grade of the last
  successful Write after the agent has stopped acting.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from exp.common.grader_qhe import run_candidate
from exp import config
from exp.common.cases import load_case
from exp.common.canary import scan_text
from exp.eqpa.jail import ensure_jail
from exp.eqpa.tools import run_eval, run_shell, run_write
from exp.common.baseline.prompts import feedback_user, spec_user
from exp.eqpa.config import EQPA_SYSTEM
from exp.eqpa.isoabl import gateway
from exp.eqpa.isoabl.arms import ARM_TOOLS, FROZEN_BUDGETS, manifest_block, workspace_block
from exp.common.parse import extract_module_v2 as extract_module


def _safe_obs(text: str) -> str:
    if scan_text(text):
        return "REPL blocked: sealed pattern in output"
    return text


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _grade_offline(case: dict[str, Any], code: str) -> dict[str, Any]:
    """Terminal grade, fully offline: no episode workspace access of any kind."""
    return run_candidate(
        code=code or "",
        test=case["test"],
        entry=case["entry_point"],
        prompt=case["prompt"],
        timeout=60.0,
        case_id=str(case.get("case_id") or ""),
    )


def run_ablation_episode(
    case_id: str,
    arm: str,
    client,
    *,
    tag: str,
    block_id: str | None = None,
    arm_order: int | None = None,
) -> dict[str, Any]:
    t_start = time.time()
    case = load_case(case_id)
    entry_point = case.get("entry_point") or ""
    session = ensure_jail(case_id, tag=f"{tag}/{arm}", prompt=case.get("prompt") or "")

    system_prompt = EQPA_SYSTEM
    user0 = spec_user(
        case["prompt"],
        workspace_block(case_id=case_id, arm=arm) + "\n\n" + manifest_block(arm),
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user0},
    ]

    llm_calls = 0
    inspect_calls = 0
    write_calls = 0
    eval_calls = 0
    blocked_attempts = 0
    completion_tokens = 0
    context_resets = 0
    submitted = False
    forced_submit = False
    last_code = ""
    last_write_name: str | None = None
    first_write_step = first_inspect_step = first_eval_step = submit_step = None
    first_error_sig: str | None = None
    shell_audit: list[dict[str, Any]] = []
    steps = 0
    termination = "budget_model_calls"
    eval_history: list[dict[str, Any]] = []
    saw_pass_on_terminal = False

    def _budget_left() -> bool:
        nonlocal termination
        if llm_calls >= int(FROZEN_BUDGETS["max_model_calls"]):
            termination = "budget_model_calls"
            return False
        if completion_tokens >= int(FROZEN_BUDGETS["max_generated_tokens"]):
            termination = "budget_generated_tokens"
            return False
        if time.time() - t_start >= float(FROZEN_BUDGETS["episode_wallclock_limit"]):
            termination = "budget_wallclock"
            return False
        return True

    while _budget_left():
        steps += 1
        res = client.chat_messages(messages, tools=ARM_TOOLS[arm])
        llm_calls += 1
        u = res.usage or {}
        completion_tokens += int(u.get("completion_tokens") or 0)
        messages.append(res.assistant_message or {"role": "assistant", "content": res.content})
        calls = list(res.tool_calls or [])

        if not calls:
            code = extract_module(res.content)
            if code.strip() and write_calls < int(FROZEN_BUDGETS["max_write_calls"]):
                wr = run_write(path="attempt_1.py", contents=code, session=session)
                write_calls += 1
                if first_write_step is None:
                    first_write_step = steps
                if wr.get("ok"):
                    last_code = code
                    last_write_name = "attempt_1.py"
                messages.append(
                    {
                        "role": "user",
                        "content": "Code captured via Write. Continue with the available tools "
                        "(see capability manifest), then Submit when done.",
                    }
                )
            else:
                messages.append(
                    {
                        "role": "user",
                        "content": "Use the tools described in the capability manifest, then Submit when done.",
                    }
                )
            continue

        for call in calls:
            name = call.get("name") or ""
            args = call.get("arguments") or {}
            cid = call.get("id") or ""
            if name == "Shell":
                cmd = str(args.get("command") or "")
                sh = gateway.gateway_shell(
                    cmd, arm=arm, entry_point=entry_point, run_shell_fn=run_shell, session=session
                )
                if sh.get("capability_block"):
                    blocked_attempts += 1
                elif inspect_calls >= int(FROZEN_BUDGETS["max_inspect_calls"]):
                    blocked_attempts += 1
                    sh = {
                        "ok": False,
                        "blocked": True,
                        "kind": "shell",
                        "text": "Inspect budget for this episode is used "
                        f"({FROZEN_BUDGETS['max_inspect_calls']}/{FROZEN_BUDGETS['max_inspect_calls']}).",
                    }
                else:
                    inspect_calls += 1
                    if first_inspect_step is None:
                        first_inspect_step = steps
                shell_audit.append(
                    {
                        "step": steps,
                        "cmd": cmd[:300],
                        "class": gateway.classify_shell_use(cmd),
                        "blocked": bool(sh.get("capability_block")),
                        "reason": sh.get("block_reason") or "",
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
                continue
            if name == "Write":
                if write_calls >= int(FROZEN_BUDGETS["max_write_calls"]):
                    blocked_attempts += 1
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": cid,
                            "name": "Write",
                            "content": "Write budget for this episode is used "
                            f"({FROZEN_BUDGETS['max_write_calls']}/{FROZEN_BUDGETS['max_write_calls']}). "
                            "Submit the latest written candidate when ready.",
                        }
                    )
                    continue
                wr = run_write(
                    path=str(args.get("path") or ""),
                    contents=str(args.get("contents") or ""),
                    session=session,
                )
                write_calls += 1
                if first_write_step is None:
                    first_write_step = steps
                if wr.get("ok"):
                    last_code = str(args.get("contents") or "")
                    last_write_name = wr.get("path")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": cid,
                        "name": "Write",
                        "content": _safe_obs(wr.get("text") or ""),
                    }
                )
                continue
            if name == "Eval":
                if arm == "C":
                    blocked_attempts += 1
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": cid,
                            "name": "Eval",
                            "content": "Eval is disabled in this episode (EVAL=0).",
                        }
                    )
                    continue
                if eval_calls >= int(FROZEN_BUDGETS["max_eval_calls"]):
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": cid,
                            "name": "Eval",
                            "content": "Eval budget for this episode is used "
                            f"({FROZEN_BUDGETS['max_eval_calls']}/{FROZEN_BUDGETS['max_eval_calls']}). "
                            "Refine with Write if needed, then Submit.",
                        }
                    )
                    continue

                def _grade_fn(code: str) -> dict[str, Any]:
                    return _grade_offline(case, code)

                ev = run_eval(session=session, k=None, grade_fn=_grade_fn)
                eval_calls += 1
                if first_eval_step is None:
                    first_eval_step = steps
                obs = _safe_obs(ev.get("text") or "")
                err = ev.get("error") or ""
                if first_error_sig is None and not ev.get("passed"):
                    first_error_sig = (err or obs)[:200]
                eval_history.append(
                    {
                        "step": steps,
                        "passed": bool(ev.get("passed")),
                        "error": (err or "")[:300],
                        "code_sha": _sha(ev.get("code") or ""),
                    }
                )
                if ev.get("passed") and _sha(ev.get("code") or "") == _sha(last_code):
                    saw_pass_on_terminal = True
                messages.append(
                    {"role": "tool", "tool_call_id": cid, "name": "Eval", "content": obs}
                )
                if not ev.get("passed") and arm == "R":
                    # Restart: wipe conversation, keep jail + latest feedback only.
                    pre_sha = _sha(ev.get("code") or last_code)
                    context_resets += 1
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": user0
                            + "\n\nLatest evaluation feedback (your previous attempt, "
                            + f"all earlier context was cleared):\n"
                            + feedback_user(error=err or "(no message)", attempt=eval_calls),
                        },
                    ]
                    shell_audit.append(
                        {"step": steps, "event": "context_reset", "pre_candidate_sha": pre_sha}
                    )
                continue
            if name == "Submit":
                submitted = True
                submit_step = steps
                termination = "agent_submit"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": cid,
                        "name": "Submit",
                        "content": "Episode finalized. No result is returned.",
                    }
                )
                break
            blocked_attempts += 1
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": cid,
                    "content": gateway.blocked_tool_reply(name, arm),
                }
            )
        if submitted:
            break

    # --- terminal outcome: offline grade of last successful Write ---
    terminal_pass = False
    terminal_rescore_used = not saw_pass_on_terminal
    terminal_error = ""
    if last_write_name:
        if not submitted:
            forced_submit = True
        exe = _grade_offline(case, last_code)
        terminal_pass = bool(exe.get("passed"))
        terminal_error = str(exe.get("error_message") or "")[:500]
    else:
        termination = "no_write_nosubmit"

    row: dict[str, Any] = {
        "case_id": case_id,
        "arm": arm,
        "block_id": block_id,
        "arm_order_in_block": arm_order,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model_identifier": getattr(client, "model", ""),
        "budget": FROZEN_BUDGETS,
        "capability_manifest": manifest_block(arm),
        "prompt_sha": _sha(system_prompt + user0),
        "llm_calls": llm_calls,
        "inspect_calls": inspect_calls,
        "write_calls": write_calls,
        "eval_calls": eval_calls,
        "blocked_capability_attempt_count": blocked_attempts,
        "completion_tokens": completion_tokens,
        "context_reset_count": context_resets,
        "first_write_step": first_write_step,
        "first_inspect_step": first_inspect_step,
        "first_eval_step": first_eval_step,
        "submit_step": submit_step,
        "steps": steps,
        "agent_submitted": submitted,
        "forced_submit": forced_submit,
        "NoSubmit": int(not submitted and not forced_submit),
        "terminal_candidate_pass": terminal_pass,
        "terminal_error": terminal_error,
        "terminal_rescore_used": terminal_rescore_used,
        "termination_reason": termination,
        "first_error_signature": first_error_sig,
        "eval_history": eval_history[:8],
        "last_code_sha": _sha(last_code),
        "parsed_code_chars": len(last_code or ""),
        "shell_audit": shell_audit[:120],
        "wallclock_s": round(time.time() - t_start, 1),
        "entry_point": entry_point,
        "jail": str(session.host_dir),
        "canary_hits": 0,
    }
    return row
