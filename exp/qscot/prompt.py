"""Q-SCoT few-shot prompt (P21 demos, QSCOT_DEMOS_V1). No RAG on this path."""

from __future__ import annotations

from typing import Any

from exp.qscot.demos import get_demos

GENERATION_CONTRACT = """Generation contract (fixed):
1. Implement exactly the required function name and arguments from the task.
2. Return one complete runnable Python module (necessary imports + full function).
3. Do not output markdown fences unless wrapping the whole program once.
4. Do not output explanations, analysis prose, or multiple alternative solutions.
5. Do not hard-code answers for individual test inputs.
6. Prefer a minimal correct implementation.
"""

QSCOT_FS_PREAMBLE = """Before writing the target code, follow the Quantum Structured
Chain-of-Thought (Q-SCoT) pattern demonstrated below.

A Q-SCoT contains:

1. Input / Output
2. Quantum Semantics
3. Program Structure using only the necessary:
   - Sequence
   - Branch
   - Loop

The examples below demonstrate how quantum-program semantics
should be mapped into program structure before code generation.
"""


def _format_demo(demo: dict, index: int) -> str:
    return (
        f"=== Demonstration {index} ===\n\n"
        f"Requirement:\n{demo['requirement'].strip()}\n\n"
        f"Q-SCoT:\n{demo['qscot'].strip()}\n\n"
        f"Code:\n```python\n{demo['code'].strip()}\n```\n"
    )


def build_qscot_prompt(case: dict[str, Any], *, retrieved_block: str = "") -> str:
    parts = [GENERATION_CONTRACT + "\n", QSCOT_FS_PREAMBLE + "\n"]
    for i, d in enumerate(get_demos(), 1):
        parts.append(_format_demo(d, i) + "\n")
    if retrieved_block.strip():
        parts.append(retrieved_block.strip() + "\n\n")
    parts.append("=== Target Task ===\n\n")
    parts.append(f"Requirement:\n{(case.get('prompt') or '').strip()}\n\n")
    parts.append(f"Required entrypoint name: `{case.get('entry_point')}`\n\n")
    parts.append(
        "First construct a concise Q-SCoT for the target task following "
        "the demonstrated pattern.\n\n"
        "Then write one complete runnable Python program satisfying "
        "the Generation Contract.\n\n"
        "Q-SCoT:\n"
    )
    return "".join(parts)
