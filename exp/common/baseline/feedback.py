"""Execution-feedback builder shared by the loop-family arms.

v7 protocol (user directive, 2026-09-21): the feedback template is aligned
byte-for-byte with the official QuanBench+ feedback loop (source repo
<本地 QuanBench+ 源仓库>, feedback_loop/feedback_prompt.py::
format_execution_feedback), so our EF rounds and the official FB baseline
differ only in the error gate (official KL grading here vs the official
in-process trial), not in prompt wording. This supersedes both the v4/v5/v6
typed templates (compile/runtime/assert/KL framing) and the interim
bare-error design. classify_feedback_kind survives only as trace metadata
(shots[].feedback_kind) and never reaches the model.
"""

from __future__ import annotations

ERROR_CLIP = 2000

COMPILE_TYPES = frozenset(
    {"SyntaxError", "IndentationError", "TabError", "MissingEntryPoint"}
)
ASSERT_TYPES = frozenset({"AssertionError"})


def classify_feedback_kind(*, error_type: str, error_message: str = "") -> str:
    """Failure-class label for trace records only (never model-visible text)."""
    et = (error_type or "").strip()
    if et in COMPILE_TYPES:
        return "compile"
    if et in ASSERT_TYPES:
        return "assert"
    msg = (error_message or "").lstrip()
    if msg.startswith("SyntaxError") or "invalid syntax" in msg.lower():
        return "compile"
    if msg.startswith("AssertionError"):
        return "assert"
    return "runtime"


def feedback_for(
    *,
    error: str,
    attempt: int,
    max_attempts: int,
    code_snippet: str | None = None,
    max_code_chars: int = 6000,
) -> str:
    """Official QuanBench+ feedback template (verbatim port)."""
    snippet = (code_snippet or "").strip()
    if len(snippet) > max_code_chars:
        snippet = snippet[: max_code_chars - 40] + "\n# ... [truncated]"

    parts = [
        f"The code you submitted failed on attempt {attempt} of {max_attempts}.",
        "",
        "Error from execution / transpilation:",
        error.strip() or "(no message)",
        "",
        "Fix the implementation and respond with corrected Python code only "
        "(same format as the original task: complete function, imports if needed).",
    ]
    if snippet:
        parts.extend(
            [
                "",
                "Your previous code (for reference):",
                "```python",
                snippet,
                "```",
            ]
        )
    return "\n".join(parts)
