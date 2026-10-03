"""Baseline prompt texts. No system message: the arms run bare.

The output contract (one ```python fence) lives in the user text so
exp.common.parse keeps working.
"""

from __future__ import annotations

from typing import Any

from exp.common.baseline.config import FIRST_SHOT_OF

ZS_INSTRUCTION = """Let's think step by step.
Then write one complete runnable Python program.
"""

FENCE_TAIL = (
    "\n\nReturn one ```python fenced block with the complete Python module. "
    "No hidden tests are provided."
)

RAG_INSTRUCTION = (
    "You may use the retrieved Qiskit knowledge excerpts if they match the "
    "current public specification. They are not task solutions. Prefer the "
    "live task over stale API text."
)


def spec_user(prompt: str, extra: str = "") -> str:
    parts = [
        "Public specification:",
        (prompt or "").strip(),
        "",
        "Write a complete Python module that implements the required entry point.",
        "Return one ```python fenced block. No hidden tests are provided.",
    ]
    if extra.strip():
        parts.extend(["", extra.strip()])
    return "\n".join(parts)


def feedback_user(*, error: str, attempt: int, max_attempts: int = 3) -> str:
    return (
        f"Your solution failed the benchmark tests (attempt {attempt}/{max_attempts}).\n\n"
        f"Error:\n{(error or '').strip() or '(no message)'}\n\n"
        "Provide a corrected answer in the same format as the original instructions "
        "(typically only the function body with proper indentation, no markdown unless asked)."
    )


def first_user(arm: str, case: dict[str, Any], *, rag_block: str = "") -> str:
    a = (arm or "").strip().lower()
    prompt = case.get("prompt") or ""
    # loop_X arms: the first shot must be byte-identical to arm X's first
    # shot — the delegation below is what guarantees that by construction.
    if a in FIRST_SHOT_OF:
        return first_user(FIRST_SHOT_OF[a], case, rag_block=rag_block)
    if a in {"zeroshot", "loop"}:
        return spec_user(prompt)
    if a == "cot":
        return spec_user(prompt) + "\n\n" + ZS_INSTRUCTION.strip() + FENCE_TAIL
    if a == "qscot":
        from exp.qscot.prompt import build_qscot_prompt

        return build_qscot_prompt(case).rstrip() + FENCE_TAIL
    if a == "rag":
        block = (rag_block or "").strip() or (
            "<retrieved_knowledge>\n(no documents injected)\n</retrieved_knowledge>"
        )
        extra = RAG_INSTRUCTION + "\n\n" + block
        return spec_user(prompt, extra)
    raise ValueError(a)
