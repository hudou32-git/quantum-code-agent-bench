"""Optional retention hooks used by runner when recorder is provided (B0 path).

Does not alter prompt text, RAG selection, or grading semantics.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from experiments.p12_nl_codegen.prompts import SYSTEM
from experiments.p12_nl_codegen.retention.hashutil import sha256_text
from experiments.p12_nl_codegen.retention.llm_client import call_llm_logged
from experiments.p12_nl_codegen.retention.recorder import RetentionRecorder
from experiments.p12_nl_codegen.extract import extract_program


def retained_llm_call(
    *,
    recorder: RetentionRecorder,
    completion_id: str,
    prompt: str,
    task_id: str,
    arm: str,
    round_idx: int,
    max_infra_retries: int = 3,
    infra_retry_delay_s: float = 60.0,
) -> Dict[str, Any]:
    lr = call_llm_logged(
        prompt,
        system=SYSTEM,
        recorder=recorder,
        completion_id=completion_id,
        task_id=task_id,
        arm=arm,
        round_idx=round_idx,
        max_infra_retries=max_infra_retries,
        infra_retry_delay_s=infra_retry_delay_s,
    )
    code, status = extract_program(lr.get("raw") or "")
    lr["code"] = code
    lr["extraction_status"] = status if not lr.get("infra_failure") else lr.get("extraction_status") or "API_FAIL"
    lr["ok"] = bool(code) and not lr.get("infra_failure")
    return lr


def persist_generation_artifacts(
    *,
    recorder: RetentionRecorder,
    completion_id: str,
    prompt: str,
    lr: Dict[str, Any],
    task: dict,
    arm: str,
    round_idx: int,
    retrieval_diag: Optional[dict] = None,
    retrieved_ids: Optional[list] = None,
    parent_completion_id: Optional[str] = None,
    parent_code_hash: Optional[str] = None,
    feedback_hash: Optional[str] = None,
    feedback_text: Optional[str] = None,
) -> Dict[str, Any]:
    paths = {}
    paths.update(
        recorder.save_prompt(
            completion_id=completion_id,
            rendered_prompt=prompt,
            meta={
                "task_id": task["task_id"],
                "arm": arm,
                "round": round_idx,
                "parent_completion_id": parent_completion_id,
                "parent_code_hash": parent_code_hash,
                "feedback_hash": feedback_hash,
                "system_prompt": SYSTEM,
                "system_prompt_hash": sha256_text(SYSTEM),
            },
        )
    )
    paths.update(
        recorder.save_response(
            completion_id=completion_id,
            raw_text=lr.get("raw") or "",
            meta={
                "model_requested": "deepseek-v4-flash",
                "model_returned": lr.get("model_returned"),
                "request_id": lr.get("request_id"),
                "latency_seconds": lr.get("latency_s"),
                "finish_reason": lr.get("finish_reason"),
                "prompt_tokens": (lr.get("usage") or {}).get("prompt_tokens"),
                "completion_tokens": (lr.get("usage") or {}).get("completion_tokens"),
                "total_tokens": (lr.get("usage") or {}).get("total_tokens"),
                "retry_count": lr.get("attempts"),
            },
        )
    )
    paths.update(
        recorder.save_code(
            completion_id=completion_id,
            code=lr.get("code") or "",
            meta={
                "extractor_version": "extract_program",
                "extraction_method": lr.get("extraction_status"),
                "extraction_status": "SUCCESS" if lr.get("code") else "EMPTY",
                "raw_response_hash": paths.get("raw_response_hash"),
                "finish_reason": lr.get("finish_reason"),
            },
        )
    )
    if retrieval_diag:
        paths["retrieval_path"] = recorder.save_retrieval(
            completion_id=completion_id,
            payload={
                **{k: retrieval_diag.get(k) for k in retrieval_diag},
                "selected_chunk_ids": retrieved_ids or retrieval_diag.get("selected_chunk_ids") or [],
            },
        )
    if feedback_text is not None:
        paths.update(
            recorder.save_feedback(
                completion_id=completion_id,
                feedback_text=feedback_text,
                meta={
                    "parent_completion_id": parent_completion_id,
                    "parent_code_hash": parent_code_hash,
                    "feedback_mode": "TEST_ORACLE_GUIDED_GENERATION",
                    "feedback_source": "evaluate_completions",
                },
            )
        )
    return paths
