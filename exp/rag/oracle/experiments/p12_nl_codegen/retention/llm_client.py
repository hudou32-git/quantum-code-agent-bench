"""Retention-aware DeepSeek client: same payload semantics as call_deepseek_detailed, with attempt logs.

Does NOT change temperature/model/max_tokens/disable_thinking. Logs each HTTP attempt.
Inner empty-response retry still mutates messages the same way as oracle_mvp.repair.prompt.call_deepseek_detailed
to preserve existing retry semantics.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from oracle_mvp.repair.prompt import DeepSeekResponse, extract_reasoning_fields, load_deepseek_env

from experiments.p12_nl_codegen.config import DISABLE_THINKING, MAX_TOKENS, MODEL, TEMPERATURE
from experiments.p12_nl_codegen.retention.ids import make_attempt_id
from experiments.p12_nl_codegen.retention.recorder import RetentionRecorder
from experiments.p12_nl_codegen.retention.store import utc_now


def classify_infra_error(exc: BaseException, *, http_status: Optional[int] = None) -> str:
    msg = str(exc).lower()
    if http_status == 429 or "429" in msg or "rate" in msg:
        return "RATE_LIMIT"
    if http_status and 500 <= http_status <= 599:
        return "SERVER_ERROR"
    if http_status and 400 <= http_status <= 499:
        return "CLIENT_ERROR"
    if "timeout" in msg:
        return "NETWORK_TIMEOUT"
    if "connection" in msg:
        return "CONNECTION_ERROR"
    if "empty response" in msg:
        return "EMPTY_RESPONSE"
    return "INVALID_API_RESPONSE"


def call_llm_logged(
    prompt: str,
    *,
    system: str,
    recorder: RetentionRecorder,
    completion_id: str,
    task_id: str,
    arm: str,
    round_idx: int,
    max_infra_retries: int = 3,
    infra_retry_delay_s: float = 60.0,
    short_retries: int = 4,
) -> Dict[str, Any]:
    """Return dict compatible with runner._llm plus attempt logging."""
    api_key, base_url, env_model = load_deepseek_env()
    use_model = MODEL or env_model
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    def _post(messages, *, disable_thinking_flag: bool, max_tokens_n: int) -> DeepSeekResponse:
        payload: dict = {
            "model": use_model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": max_tokens_n,
        }
        if disable_thinking_flag:
            payload["thinking"] = {"type": "disabled"}
        resp = requests.post(url, json=payload, headers=headers, timeout=180.0)
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") in {None, "text", "output_text"}:
                    parts.append(str(block.get("text") or block.get("content") or ""))
                elif isinstance(block, str):
                    parts.append(block)
            content = "\n".join(p for p in parts if p)
        content = str(content).strip()
        reasoning = extract_reasoning_fields(msg)
        finish = data["choices"][0].get("finish_reason")
        usage = data.get("usage")
        if content or reasoning:
            return DeepSeekResponse(
                content=content,
                reasoning_content=reasoning,
                thinking_disabled=disable_thinking_flag,
                finish_reason=finish,
                usage=usage,
                raw_message=msg,
            )
        raise RuntimeError(f"empty response (finish={finish}, usage={usage})")

    system_msg = system
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]
    t0 = time.time()
    attempt_index = 0
    last_err = None
    last_type = None
    infra_round = 0

    while infra_round < max_infra_retries:
        for _short in range(short_retries):
            attempt_index += 1
            attempt_id = make_attempt_id(completion_id, attempt_index)
            started = utc_now()
            http_status = None
            try:
                # Preserve original retry-message mutation semantics of call_deepseek_detailed
                resp = _post(messages, disable_thinking_flag=DISABLE_THINKING, max_tokens_n=MAX_TOKENS)
                finished = utc_now()
                recorder.log_attempt(
                    {
                        "protocol_id": "P12_NL_LOCAL_HARD_v1",
                        "block": recorder.block,
                        "completion_id": completion_id,
                        "attempt_id": attempt_id,
                        "attempt_index": attempt_index,
                        "task_id": task_id,
                        "arm": arm,
                        "round": round_idx,
                        "request_started_at_utc": started,
                        "request_finished_at_utc": finished,
                        "latency_seconds": round(time.time() - t0, 4),
                        "http_status": 200,
                        "error_type": None,
                        "error_message": None,
                        "retry_delay_seconds": 0.0,
                        "success": True,
                    }
                )
                return {
                    "ok": True,
                    "raw": resp.content or "",
                    "finish_reason": resp.finish_reason,
                    "usage": resp.usage if isinstance(resp.usage, dict) else {},
                    "latency_s": time.time() - t0,
                    "infra_failure": False,
                    "infra_status": "OK",
                    "request_id": attempt_id,
                    "attempts": attempt_index,
                    "model_returned": use_model,
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001
                finished = utc_now()
                if isinstance(exc, requests.HTTPError) and exc.response is not None:
                    http_status = int(exc.response.status_code)
                et = classify_infra_error(exc, http_status=http_status)
                last_err = str(exc)
                last_type = et
                delay = min(1.0 * (2**(_short)), 30.0)
                recorder.log_attempt(
                    {
                        "protocol_id": "P12_NL_LOCAL_HARD_v1",
                        "block": recorder.block,
                        "completion_id": completion_id,
                        "attempt_id": attempt_id,
                        "attempt_index": attempt_index,
                        "task_id": task_id,
                        "arm": arm,
                        "round": round_idx,
                        "request_started_at_utc": started,
                        "request_finished_at_utc": finished,
                        "latency_seconds": round(time.time() - t0, 4),
                        "http_status": http_status,
                        "error_type": et,
                        "error_message": last_err[:500],
                        "retry_delay_seconds": delay,
                        "success": False,
                    }
                )
                # Same mutation as call_deepseek_detailed on invalid reply
                messages = [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            "Your previous reply was invalid. "
                            "Reply with ONLY:\n```python\n"
                            "from qiskit import QuantumCircuit\n"
                            "def build_circuit():\n"
                            "    ...\n```"
                        ),
                    },
                ]
                time.sleep(delay)
        infra_round += 1
        if infra_round < max_infra_retries:
            time.sleep(infra_retry_delay_s)

    recorder.log_attempt(
        {
            "protocol_id": "P12_NL_LOCAL_HARD_v1",
            "block": recorder.block,
            "completion_id": completion_id,
            "attempt_id": make_attempt_id(completion_id, attempt_index + 1),
            "attempt_index": attempt_index + 1,
            "task_id": task_id,
            "arm": arm,
            "round": round_idx,
            "request_started_at_utc": utc_now(),
            "request_finished_at_utc": utc_now(),
            "latency_seconds": round(time.time() - t0, 4),
            "http_status": None,
            "error_type": "PERMANENT_INFRA_FAILURE",
            "error_message": (last_err or "")[:500],
            "retry_delay_seconds": 0.0,
            "success": False,
        }
    )
    return {
        "ok": False,
        "raw": "",
        "finish_reason": None,
        "usage": {},
        "latency_s": time.time() - t0,
        "infra_failure": True,
        "infra_status": "INFRA_FAILURE_PERMANENT",
        "request_id": make_attempt_id(completion_id, max(1, attempt_index)),
        "attempts": attempt_index,
        "model_returned": use_model,
        "error": f"api:{last_type}:{last_err}",
    }
