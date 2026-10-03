"""max_tokens budget probe (e7 plan P0-6 / Phase-1 gate, 2026-09-20).

Two calls to the configured .env channel, same long-output task:
  A) max_tokens=4096  -> expected finish_reason=length (cap enforced & hit)
  B) max_tokens=40960 -> expected the sample finishes naturally (finish_reason=stop)
                           or, at minimum, generates well past 4096 tokens.

Confirms the channel accepts and enforces the 40960 pin before any arm runs.
Usage: python3 -m exp.common.probe_budget   (2 LLM calls, ~1-2 min)
"""

from __future__ import annotations

import json
import sys

from exp.common.llm import DeepSeekClient, official_chat_url, official_model

LONG_TASK = (
    "Write a single Python module containing a list variable named FACTS with "
    "60 entries. Each entry is a dict with keys: topic, note, example_code. "
    "topic: a quantum computing concept; note: a 3-4 sentence explanation; "
    "example_code: a 8-15 line qiskit snippet as a string. Do not stop early; "
    "keep writing until all 60 entries are complete."
)


def _probe(max_tokens: int) -> dict:
    c = DeepSeekClient(temperature=0.6, max_tokens=max_tokens, disable_thinking=True,
                       send_thinking=True, max_retries=2, system="")
    res = c.chat(LONG_TASK)
    u = res.usage or {}
    return {
        "max_tokens_sent": max_tokens,
        "finish_reason": res.finish_reason or "",
        "prompt_tokens": int(u.get("prompt_tokens") or 0),
        "completion_tokens": int(u.get("completion_tokens") or 0),
        "content_chars": len(res.content or ""),
        "reasoning_chars": len(res.reasoning_content or ""),
    }


def main() -> int:
    print(f"endpoint={official_chat_url()} model={official_model()}", flush=True)
    out = {"endpoint": official_chat_url(), "model": official_model(), "probes": []}
    for mt in (4096, 40960):
        print(f"probe max_tokens={mt} ...", flush=True)
        try:
            r = _probe(mt)
        except Exception as exc:  # noqa: BLE001
            print(f"PROBE FAILED at max_tokens={mt}: {type(exc).__name__}: {exc}", flush=True)
            return 1
        out["probes"].append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)

    a, b = out["probes"]
    out["verdict"] = {
        "cap_4096_enforced": a["finish_reason"] == "length"
        or a["completion_tokens"] >= 4096,
        "budget_40960_passes_long_task": (
            b["completion_tokens"] > a["completion_tokens"]
            and b["finish_reason"] != "length"
        ) or b["completion_tokens"] > 5000,
        "thinking_off": b["reasoning_chars"] == 0,
    }
    print(json.dumps(out["verdict"], ensure_ascii=False, indent=2), flush=True)
    ok = out["verdict"]["budget_40960_passes_long_task"] and out["verdict"]["thinking_off"]
    print("PROBE OK" if ok else "PROBE INCONCLUSIVE — inspect before running arms",
          flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
