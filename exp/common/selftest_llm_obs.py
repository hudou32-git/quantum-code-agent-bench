"""Offline selftest for the Phase-0 LLM observability layer (no network).

Run: python3 -m exp.common.selftest_llm_obs

Verifies: record schema (nine required fields + extras), behavior equivalence
(observed vs unobserved client return identical results), call_id scoping
(run-level, per-episode reset, per-worker thread episodes), error records
(exception recorded then re-raised unchanged), no-op without activation,
estimated-usage passthrough, totals/describe, and recorder replacement.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Hermetic env BEFORE exp.common.llm import (load_dotenv uses override=False,
# so these defaults win only when .env lacks the variable).
os.environ.setdefault("DEEPSEEK_API_KEY", "selftest-key")
os.environ.setdefault("DEEPSEEK_API_URL", "https://selftest.invalid/v1")
os.environ.setdefault("DEEPSEEK_MODEL", "selftest-model")

from exp.common import llm_obs  # noqa: E402
from exp.common.llm import DeepSeekClient, LLMResult  # noqa: E402

CHECKS = {"n": 0, "fail": 0}


def check(name: str, cond: bool) -> None:
    CHECKS["n"] += 1
    if cond:
        print(f"  ok  {name}")
    else:
        CHECKS["fail"] += 1
        print(f"  FAIL {name}")


def canned_payload(content: str = "ok", pt: int = 11, ct: int = 7) -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
        "model": "selftest-model",
    }


def make_client(system: str = "sys") -> DeepSeekClient:
    return DeepSeekClient(temperature=0.6, max_tokens=512, system=system, max_retries=2)


def read_lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="llm_obs_selftest_"))

    # ── 1. no-op without activation ──
    llm_obs.deactivate()
    c0 = make_client()
    check("no-activation: observer is None", c0.observer is None)
    c0._post_messages = lambda *a, **k: canned_payload()  # type: ignore[method-assign]
    r0 = c0.chat("hello")
    check("no-activation: chat still works", r0.content == "ok")

    # ── 2. schema + equivalence with observer active ──
    rec_path = tmp / "run1" / "llm_calls.jsonl"
    rec = llm_obs.activate(rec_path, runner="selftest", tag="t1", arm="EQPA")
    check("activation: current_recorder set", llm_obs.current_recorder() is rec)
    c1 = make_client()
    check("activation: client auto-attached", c1.observer is rec)
    c1._post_messages = lambda *a, **k: canned_payload(pt=11, ct=7)  # type: ignore[method-assign]
    r1 = c1.chat_with_system("sys", "hello")
    lines = read_lines(rec_path)
    check("one record per logical call", len(lines) == 1)
    rec1 = lines[0]
    for field in llm_obs.REQUIRED_FIELDS:
        check(f"schema: required field present: {field}", field in rec1)
    check("schema: call_id == 1", rec1["call_id"] == 1)
    check("schema: input_tokens == 11", rec1["input_tokens"] == 11)
    check("schema: output_tokens == 7", rec1["output_tokens"] == 7)
    check("schema: total_tokens == 18", rec1["total_tokens"] == 18)
    check("schema: temperature == 0.6", rec1["temperature"] == 0.6)
    check("schema: latency >= 0", rec1["latency_seconds"] >= 0.0)
    check("schema: timestamps ISO", rec1["timestamp_start"].startswith("20") and rec1["timestamp_end"].startswith("20"))
    check("schema: transport non_stream", rec1["transport"] == "non_stream")
    check("schema: context carries runner/tag/arm", rec1["context"].get("runner") == "selftest" and rec1["context"].get("tag") == "t1")

    # behavior equivalence: same call without observer returns identical result
    c2 = make_client()
    c2._post_messages = c1._post_messages  # type: ignore[method-assign]
    r2 = c2.chat_with_system("sys", "hello")
    same = (
        r1.content == r2.content
        and r1.finish_reason == r2.finish_reason
        and r1.usage == r2.usage
        and r1.model == r2.model
        and r1.tool_calls == r2.tool_calls
        and r1.reasoning_content == r2.reasoning_content
    )
    check("behavior equivalence: observed vs unobserved identical result", same)

    # ── 3. call_id monotonic + per-episode reset ──
    # NOTE: the equivalence call above (c2, also auto-attached to the same run
    # recorder) is recorded too — run-level ids are monotonic across clients.
    c1.chat("second")
    c1.chat("third")
    lines = read_lines(rec_path)
    check("call_id monotonic across clients", [x["call_id"] for x in lines] == [1, 2, 3, 4])
    rec.set_episode("task-42", case_id="42")
    c1.chat("ep2")
    rec.set_episode("task-43", case_id="43")
    c1.chat("ep3")
    lines = read_lines(rec_path)
    check("call_id resets per episode", [x["call_id"] for x in lines[-2:]] == [1, 1])
    check("episode id in context", lines[-2]["context"].get("episode_id") == "task-42" and lines[-1]["context"].get("episode_id") == "task-43")
    rec.clear_episode()

    # ── 4. thread episodes: independent counters per worker ──
    def worker(tag_name: str, n: int) -> None:
        rec.set_thread_episode(tag_name)
        for _ in range(n):
            c1.chat("threaded")

    threads = [threading.Thread(target=worker, args=(f"w{i}", 5)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    lines = read_lines(rec_path)
    tail = lines[-20:]
    per_worker: dict = {}
    ok_ids = True
    for x in tail:
        ep = x["context"].get("episode_id")
        per_worker.setdefault(ep, []).append(x["call_id"])
    for ep, ids in per_worker.items():
        if ids != list(range(1, 6)):
            ok_ids = False
    check("thread episodes: 4 workers x 5 calls, ids 1..5 each", len(per_worker) == 4 and ok_ids)

    # ── 5. error record: exception recorded, then re-raised unchanged ──
    err_path = tmp / "run2" / "llm_calls.jsonl"
    llm_obs.activate(err_path, runner="selftest", tag="t2")
    c3 = make_client()

    def boom(*a, **k):
        raise RuntimeError("HTTP 500: boom")

    c3._post_messages = boom  # type: ignore[method-assign]
    raised = None
    try:
        c3.chat("will fail")
    except RuntimeError as exc:
        raised = exc
    check("error: exception re-raised unchanged", raised is not None and "boom" in str(raised))
    lines = read_lines(err_path)
    check("error: one error record", len(lines) == 1 and lines[0]["error"] is not None and "RuntimeError" in lines[0]["error"])
    check("error: zero tokens on failed call", lines[0]["total_tokens"] == 0)

    # ── 6. estimated-usage passthrough (direct recorder.observe) ──
    # NOTE: section 5's re-activation closed run1's recorder (fail-safe by
    # design), so re-activate on the same path — append, new obs_session.
    rec = llm_obs.activate(rec_path, runner="selftest", tag="t1", arm="EQPA")
    res = LLMResult(
        content="x", model="selftest-model", finish_reason="stop",
        usage={}, wall_time=0.5, raw={"transport": "stream"},
        completion_tokens_estimated=True,
    )
    rec.observe(c1, res, __import__("time").time())
    last = read_lines(rec_path)[-1]
    check("estimated flag passthrough", last["tokens_estimated"] is True and last["usage_present"] is False)
    check("stream transport detected", last["transport"] == "stream")

    # fail-safe contract: an observer-internal error never raises into the run
    rec.close()
    failsafe_ok = True
    try:
        rec.observe(c1, res, __import__("time").time())
    except Exception:  # noqa: BLE001
        failsafe_ok = False
    check("fail-safe: observe on closed recorder never raises", failsafe_ok and rec._broken)

    # ── 7. totals + describe (fresh session: only the section-6 call) ──
    d = rec.describe()
    check("totals: n_calls matches this session", d["totals"]["n_calls"] == 1)
    check("describe: context + schema_version", d["context"].get("runner") == "selftest" and d["schema_version"] == 1)

    # ── 8. re-activation closes and replaces the previous recorder ──
    old = llm_obs.current_recorder()
    llm_obs.activate(tmp / "run3" / "llm_calls.jsonl", runner="selftest", tag="t3")
    check("re-activation: new recorder installed", llm_obs.current_recorder() is not old)
    llm_obs.deactivate()
    check("deactivation: recorder cleared", llm_obs.current_recorder() is None)

    # ── 9. episode ledger + run-level cost summary (increment 2) ──
    rec2 = llm_obs.activate(tmp / "run4" / "llm_calls.jsonl", runner="selftest", tag="t4")
    c4 = make_client()
    c4._post_messages = lambda *a, **k: canned_payload(pt=100, ct=50)  # type: ignore[method-assign]
    with rec2.episode_context(method="EQPA", task_id="03", bench="qbplus", replicate=1) as ep:
        c4.chat("a")
        c4.chat("b")
        ep.record_outcome(success=True, iterations=2, quantum_executions=None)
    with rec2.episode_context(method="EQPA", task_id="05", bench="qbplus", replicate=1) as ep:
        c4.chat("c")
        ep.record_outcome(success=False, iterations=1, quantum_executions=None)
    raised = False
    try:
        with rec2.episode_context(method="EQPA", task_id="07", bench="qbplus", replicate=2):
            raise RuntimeError("worker died")
    except RuntimeError:
        raised = True
    check("episode: exception propagates after ledgering", raised)
    ledger = read_lines(tmp / "run4" / "episode_ledger.jsonl")
    check("ledger: three episode lines", len(ledger) == 3)
    e1 = ledger[0]
    check("ledger: identifiers preserved", e1["method"] == "EQPA" and e1["task_id"] == "03" and e1["replicate"] == 1 and e1["bench"] == "qbplus")
    check("ledger: episode cost aggregated", e1["cost"]["llm_calls"] == 2 and e1["cost"]["input_tokens"] == 200 and e1["cost"]["total_tokens"] == 300)
    check("ledger: outcome recorded", e1["outcome"].get("success") is True and e1["outcome"].get("iterations") == 2)
    check("ledger: quantum_executions carried (None = offline extraction)", e1["outcome"].get("quantum_executions", "missing") is None)
    check("ledger: exception episode marked", ledger[2]["completed_normally"] is False and "worker died" in (ledger[2]["outcome"].get("exception") or ""))
    cs = rec2.write_cost_summary()
    check("cost summary: returned", cs is not None)
    check("cost summary: episodes == 3", cs["episodes"] == 3)
    check("cost summary: success_rate == 1/3", cs["success_rate"] == round(1 / 3, 4))
    check("cost summary: mean_llm_calls == 1.0", cs["mean_llm_calls_per_episode"] == 1.0)
    check("cost summary: cost_measurement embedded (GATE 4 identity block)",
          cs["cost_measurement"]["latency"]["include"] == ["llm_api_call"]
          and cs["cost_measurement"]["replicate"]["policy"]["external_control"] is True)
    check("cost summary: file written", (tmp / "run4" / "cost_summary.json").is_file())
    calls = read_lines(tmp / "run4" / "llm_calls.jsonl")
    check("calls: episode context on every call record", all(x["context"].get("episode_id") for x in calls))
    check("calls: task_id per episode", calls[0]["context"]["task_id"] == "03" and calls[2]["context"]["task_id"] == "05")
    llm_obs.deactivate()

    print(f"\n{CHECKS['n'] - CHECKS['fail']}/{CHECKS['n']} checks passed")
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
