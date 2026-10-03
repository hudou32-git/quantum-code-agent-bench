"""G2 probe (e7 generation_guard, 2026-09-20): live streaming transport check.

One real call through make_official_client (guard=enforce, stream=True):
verifies SSE assembly, real-vs-estimated usage, finish_reason propagation and
that a normal (non-degenerate) generation passes through untouched.

Run: python3 -m exp.common.probe_stream
"""

from __future__ import annotations

import json

TASK = (
    "Write a Python function `bell_state_qc()` that builds and returns a "
    "2-qubit QuantumCircuit preparing the Bell state |00> + |11> with H on "
    "q0 then CX(0,1). Return one ```python fenced block."
)


def main() -> int:
    from exp.common.llm import make_official_client, official_chat_url, official_model

    print(f"endpoint={official_chat_url()} model={official_model()}", flush=True)
    c = make_official_client(max_tokens=40960, temperature=0.6)
    res = c.chat_messages([{"role": "user", "content": TASK}], tools=None)
    report = {
        "transport": res.raw.get("transport"),
        "finish_reason": res.finish_reason,
        "usage": res.usage,
        "completion_tokens_estimated": res.completion_tokens_estimated,
        "content_chars": len(res.content or ""),
        "has_fence": (res.content or "").count("```") >= 2,
        "reasoning_chars": len(res.reasoning_content or ""),
        "wall_time": round(res.wall_time, 2),
        "repeat_guard": res.repeat_guard,
        "n_calls": c.n_calls,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    ok = (
        report["transport"] == "stream"
        and report["finish_reason"] == "stop"
        and report["completion_tokens_estimated"] is False
        and report["has_fence"]
        and report["reasoning_chars"] == 0
        and report["n_calls"] == 1
    )
    print("PROBE STREAM OK" if ok else "PROBE STREAM INCONCLUSIVE — inspect before arms", flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
