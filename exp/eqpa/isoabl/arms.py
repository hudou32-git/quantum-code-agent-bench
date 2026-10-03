"""Arm definitions for the ISO mechanism ablation (freeze plan v3).

Arms: A full / B -Inspect / C -Eval / R Restart(-stateful).
Budget table is FROZEN (e4_isoabl_freeze_plan.md §9-10); identical across arms.
"""

from __future__ import annotations

from typing import Any

FROZEN_BUDGETS: dict[str, Any] = {
    "max_controller_steps": 120,   # non-binding; max_model_calls is the binding cap
    "max_model_calls": 36,         # failing-task p50 24-35, p90 48 (locked traces)
    "max_generated_tokens": 150_000,
    "max_write_calls": 6,
    "max_inspect_calls": 32,       # 0 for B
    "max_eval_calls": 3,           # 0 for C; standard ISO controller protocol
    "episode_wallclock_limit": 1800,
    "forced_submit_at_budget": True,
}

ARM_NAMES = ("A", "B", "C", "R")

MANIFEST_LINE = {
    "A": "INSPECT=1 EVAL=1 WRITE=1 SUBMIT=1",
    "B": "INSPECT=0 EVAL=1 WRITE=1 SUBMIT=1",
    "C": "INSPECT=1 EVAL=0 WRITE=1 SUBMIT=1",
    "R": "INSPECT=1 EVAL=1 WRITE=1 SUBMIT=1",
}

CONSTRAINT_SENTENCE = (
    "Only use capabilities explicitly enabled in the capability manifest. "
    "Disabled capabilities are unavailable in this episode."
)

SHELL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Shell",
        "description": (
            "Run one shell command in the isolated environment and return stdout/stderr. "
            "cwd is /workspace (read-only). Scratch files go in /tmp. "
            "Python and Qiskit are available. Do not expect host repository paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "The shell command to execute."}},
            "required": ["command"],
        },
    },
}

WRITE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Write",
        "description": (
            "Write one complete Python module as this task's solution. "
            "path must be exactly attempt_1.py, attempt_2.py, or attempt_3.py."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Exact filename: attempt_1.py, attempt_2.py, or attempt_3.py."},
                "contents": {"type": "string", "description": "Full module text. No markdown fences."},
            },
            "required": ["path", "contents"],
        },
    },
}

EVAL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Eval",
        "description": (
            "Run the task evaluation on the latest successful Write. "
            "Returns {passed, error}. Counts against the eval budget."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

SUBMIT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Submit",
        "description": (
            "Finalize the latest successful Write as your solution and end this episode. "
            "No result is returned. Call Submit when you believe your solution is complete."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

ARM_TOOLS: dict[str, list[dict[str, Any]]] = {
    "A": [SHELL_TOOL, WRITE_TOOL, EVAL_TOOL, SUBMIT_TOOL],
    "B": [WRITE_TOOL, EVAL_TOOL, SUBMIT_TOOL],
    "C": [SHELL_TOOL, WRITE_TOOL, SUBMIT_TOOL],
    "R": [SHELL_TOOL, WRITE_TOOL, EVAL_TOOL, SUBMIT_TOOL],
}


def manifest_block(arm: str) -> str:
    return f"Capability manifest: {MANIFEST_LINE[arm]}\n{CONSTRAINT_SENTENCE}"


def workspace_block(*, case_id: str, arm: str) -> str:
    lines = [
        "Workspace:",
        f"- task_id: {case_id}",
        "- visible files: /workspace/prompt.txt (read-only)",
        "- scratch: /tmp",
        f"- capabilities enabled: {MANIFEST_LINE[arm]}",
    ]
    if arm in {"A", "C", "R"}:
        lines.append("- inspect: Shell in the isolated environment (python and Qiskit are on PATH)")
    lines.append("- write: Write with path exactly attempt_1.py (or attempt_2.py / attempt_3.py)")
    if arm in {"A", "B", "R"}:
        lines.append("- eval: Eval() grades the last successful Write and returns {passed, error}")
    lines.append("- submit: Submit() finalizes the latest successful Write and ends the episode")
    return "\n".join(lines)
