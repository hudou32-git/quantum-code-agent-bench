"""Baseline arms engine: adaptive EF loop, or v6 pass@k independent sampling.

- loop arm: optional feedback rounds (generate -> official eval -> official
  QuanBench+ feedback template: attempt framing + error + repair instruction
  + code echo -> full rewrite), MAX_OFFICIAL=3.
- passk arms (oneshot/cot/qscot/rag): PASS_K independent samples per problem,
  a fresh conversation per sample, no feedback between samples; the problem
  passes if any sample passes (pass@k, user directive 2026-09-17).
No tools anywhere."""

from __future__ import annotations

from typing import Any, Callable

from exp.common.baseline.config import (
    DECODING_TEMPERATURE,
    FIRST_SHOT_OF,
    MAX_OFFICIAL,
    MODEL,
    MODEL_FAMILY,
    PASSK_ARMS,
    PASS_K,
    SINGLE_TURN,
    default_tag,
    normalize_arm,
    normalize_bench,
    refuse_locked_tag,
)
from exp.common.baseline.feedback import ERROR_CLIP, classify_feedback_kind, feedback_for
from exp.common.baseline.prompts import first_user
from exp.common.cases import load_base_case
from exp.common.canary import scan_text
from exp.common.grader_qhe import run_candidate
from exp.common.grader_qbplus import arm_dest, grade_qbplus
from exp.common.parse import extract_module_v2, extraction_status


def _grade_case(case, code, *, bench, results_root, tag, k, case_id=""):
    b = normalize_bench(bench)
    if b == "qbplus":
        dest = arm_dest(tag, str(case.get("case_id") or ""), results_root=results_root)
        return grade_qbplus(case, code, dest=dest, k=k)
    return run_candidate(
        code=code or "",
        test=case.get("test") or "",
        entry=case.get("entry_point") or "",
        prompt=case.get("prompt") or "",
        timeout=60.0,
        case_id=str(case_id),
    )


def _clip_messages(messages: list[dict[str, str]], n: int = 8) -> list[dict[str, str]]:
    out = []
    for m in messages[:n]:
        out.append({"role": m["role"], "content": (m.get("content") or "")[:4000]})
    return out


def run_base_task(
    case_id: str,
    client,
    *,
    arm: str,
    bench: str = "qhe",
    tag: str | None = None,
    results_root=None,
    retrieve_fn: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]] | None = None,
    pass_k: int | None = None,
) -> dict[str, Any]:
    a = normalize_arm(arm)
    b = normalize_bench(bench)
    # pass@k sampling mode: the four single-turn arms default to PASS_K
    # independent samples; the loop arm stays adaptive-feedback (pass_k=1
    # here means "use the arm's native schedule", not "one sample total").
    sampling = (a in PASSK_ARMS) and (PASS_K if pass_k is None else int(pass_k)) > 1
    n_samples = (PASS_K if pass_k is None else int(pass_k)) if a in PASSK_ARMS else 1
    tag = tag or default_tag(a, bench=b, pass_k=n_samples if a in PASSK_ARMS else None)
    refuse_locked_tag(tag)
    if results_root is None:
        from exp.config import arm_results

        results_root = arm_results(a)
    case = load_base_case(case_id, bench=b)
    rag_meta: dict[str, Any] = {}
    rag_block = ""
    # rag-flavored first shots (rag, loop_rag): retrieve once per problem and
    # inject into the first shot only — feedback rounds never re-retrieve.
    if a == "rag" or a == "loop_rag":
        if retrieve_fn is None:
            from exp.rag.retrieve import retrieve_docs

            retrieve_fn = retrieve_docs
        rag_block, rag_meta = retrieve_fn(case)
    user = first_user(a, case, rag_block=rag_block)
    # v5/v6 protocol: no system message; the five arms run bare.
    base_user = [{"role": "user", "content": user}]
    messages: list[dict[str, str]] = list(base_user)
    cap = n_samples if sampling else (1 if a in SINGLE_TURN else MAX_OFFICIAL)
    shots: list[dict[str, Any]] = []
    last_code = ""
    last_exe: dict[str, Any] = {
        "passed": False,
        "error_message": "no official submit",
        "error_type": "",
    }
    llm_calls = 0
    prompt_tokens = 0
    completion_tokens = 0

    for k in range(1, cap + 1):
        # pass@k: every sample starts from the bare user turn — samples are
        # independent draws, never conditioned on earlier failures.
        call_messages = list(base_user) if sampling else messages
        res = client.chat_messages(call_messages, tools=None)
        llm_calls += 1
        usage = res.usage or {}
        prompt_tokens += int(usage.get("prompt_tokens") or 0)
        completion_tokens += int(usage.get("completion_tokens") or 0)
        assistant = res.content or ""
        # e7 P0-7 (2026-09-20): a length-cut draw whose final code fence never
        # closed (odd fence count → cut mid-block) or that carries no code at
        # all is a degenerate sampling loop (~1-2% of draws at any budget) —
        # resample ONCE, keep both calls on the trace. A length cut AFTER a
        # closed code block is graded as-is (extractor ignores post-fence
        # noise). Frozen as protocol field `length_retry` = 1.
        length_retry = None
        if (res.finish_reason or "") == "length" and (
            assistant.count("```") % 2 == 1 or not extract_module_v2(assistant)
        ):
            length_retry = {
                "first_finish_reason": "length",
                "first_completion_tokens": int(usage.get("completion_tokens") or 0),
            }
            res = client.chat_messages(call_messages, tools=None)
            llm_calls += 1
            usage = res.usage or {}
            prompt_tokens += int(usage.get("prompt_tokens") or 0)
            completion_tokens += int(usage.get("completion_tokens") or 0)
            assistant = res.content or ""
            length_retry["retry_finish_reason"] = res.finish_reason or ""
            length_retry["retry_completion_tokens"] = int(usage.get("completion_tokens") or 0)
        if sampling:
            messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})
        code = extract_module_v2(assistant)
        last_code = code
        last_extraction = extraction_status(assistant)
        last_exe = _grade_case(case, code, bench=b, results_root=results_root, tag=tag, k=k, case_id=case_id)
        kind = ""
        if not last_exe.get("passed"):
            kind = classify_feedback_kind(
                error_type=last_exe.get("error_type") or "",
                error_message=last_exe.get("error_message") or "",
            )
            if b == "qbplus" and (last_exe.get("error_type") or "") == "KLMismatch":
                kind = "assert"
        shot = {
            "k": k,
            "passed": bool(last_exe.get("passed")),
            "error_type": last_exe.get("error_type") or "",
            "error_message": (last_exe.get("error_message") or "")[:ERROR_CLIP],
            "feedback_kind": kind,
            "code_chars": len(code or ""),
            # per-call history (user directive 2026-09-20): every LLM call's
            # full prompt, raw model output, and extracted code — makes future
            # regrades/extraction audits exact (frozen rows predate this).
            "prompt": call_messages[-1].get("content") or "",
            "raw_output": assistant,
            "code": code,
            **last_extraction,
            # e7 plan P0-1: finish_reason persisted per call — "length" here is
            # the max_tokens cutoff signal (completion_tokens==cap corroborates).
            # generation_guard: finish_reason=="client_repeat_stop" is the
            # execution-level early abort — NOT an API length cut (so the
            # frozen P0-7 length_retry rule can never fire on it).
            "finish_reason": res.finish_reason or "",
            "length_retry": length_retry,
            "completion_tokens_estimated": bool(getattr(res, "completion_tokens_estimated", False)),
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            **({"repeat_guard": res.repeat_guard} if getattr(res, "repeat_guard", None) else {}),
        }
        shots.append(shot)
        if sampling:
            # independent resampling: never feed errors back between samples
            continue
        if last_exe.get("passed"):
            break
        if k >= cap:
            break
        fb = feedback_for(
            error=last_exe.get("error_message") or "",
            attempt=k,
            max_attempts=cap,
            code_snippet=last_code,
        )
        shots[-1]["feedback_sent"] = fb
        messages.append({"role": "user", "content": fb})

    if sampling:
        passed = any(s["passed"] for s in shots)
    else:
        passed = bool(last_exe.get("passed"))
    blob = "\n".join(
        [last_code, last_exe.get("error_message") or ""]
        + [m.get("content") or "" for m in messages]
    )
    canary = scan_text(blob)
    row = {
        "case_id": case_id,
        "arm": a.upper(),
        "tag": tag,
        "benchmark": b,
        "passed": passed,
        "pass_fail": "PASS" if passed else "FAIL",
        "error_message": last_exe.get("error_message") or "",
        "error_type": last_exe.get("error_type") or "",
        "parsed_code": last_code,
        **last_extraction,
        "llm_calls": llm_calls,
        "official_submits": len(shots),
        "official_attempts": len(shots),
        "eval_completed": len(shots),
        "sampling_mode": "independent_passk" if sampling else "adaptive_feedback",
        "pass_k": n_samples if sampling else 1,
        "first_shot_prompt": (
            FIRST_SHOT_OF.get(a)
            or ("base" if a in {"oneshot", "loop"} else a)
        ),
        "n_samples_passed": sum(1 for s in shots if s["passed"]) if sampling else int(passed),
        "decoding_temperature": float(getattr(client, "temperature", DECODING_TEMPERATURE)),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "entry_point": case.get("entry_point"),
        "shots": shots,
        "had_tools": False,
        "max_attempts": 1 if sampling else cap,
        "canary_hits": len(canary),
        "messages_head": _clip_messages(messages),
        "model": MODEL,
        "model_family": MODEL_FAMILY,
    }
    if rag_meta:
        row["rag"] = rag_meta
    return row
