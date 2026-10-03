"""Capability gateway for the ISO mechanism ablation.

Information-level enforcement (freeze plan §4/§7):
- B (INSPECT=0): no Shell tool at all; attempts to call it get a blocked reply.
- C (EVAL=0): Shell stays available for Inspect-class observations, but any
  command whose returned observation could contain *candidate correctness
  information* is blocked before execution:
    * executing/importing the attempt files (attempt_*.py);
    * test runners (pytest / unittest);
    * inline python probes referencing the task entry point.
  Static reads (cat/head/ls/grep of files) remain legal Inspect.
- Write is ACK-only upstream (run_write already returns only "wrote <name>").
- Submit is terminal: returns no result.

Residual, documented: C cannot be made perfectly blind to inline code the model
duplicates under a renamed function inside `python -c`. All C-arm Shell
commands and outputs are logged for post-hoc audit; the deterministic rules
above are what the smoke test enforces.
"""

from __future__ import annotations

import re
from typing import Any

_ATTEMPT_RE = re.compile(r"attempt[_\- ]?[0-9_]|attempt\.py", re.IGNORECASE)
_EXEC_RE = re.compile(r"(^|[;&|\s])(python3?|pypy)\b|(^|[;&|\s])(pytest|unittest|nose|tox)\b", re.IGNORECASE)
_RUNNER_RE = re.compile(r"pytest|unittest|nose[0-9]?|tox|run_candidate|grade_qbplus", re.IGNORECASE)

C_BLOCK_MSG = (
    "Shell blocked: this command could produce a candidate-correctness observation, "
    "which is disabled in this episode (EVAL=0). Inspect-style queries about the "
    "environment (versions, symbols, signatures, static files) remain available."
)


def _references(s: str, needle: str | None) -> bool:
    return bool(needle) and needle in s


def c_arm_command_allowed(command: str, entry_point: str | None) -> tuple[bool, str]:
    """Deterministic pre-execution filter for arm C. Returns (allowed, reason)."""
    low = command or ""
    if _ATTEMPT_RE.search(low) and (_EXEC_RE.search(low) or _RUNNER_RE.search(low)):
        return False, "executes/imports an attempt file"
    if _RUNNER_RE.search(low):
        return False, "test-runner style command"
    if _EXEC_RE.search(low) and _references(low, entry_point or ""):
        return False, "inline python references the task entry point"
    return True, ""


def classify_shell_use(command: str) -> str:
    """Coarse label for process logging (read/inspect vs exec)."""
    if _EXEC_RE.search(command or ""):
        return "exec"
    return "read"


def blocked_tool_reply(name: str, arm: str) -> str:
    return (
        f"Tool {name} is not available in this episode "
        f"(see capability manifest)."
    )


def gateway_shell(
    command: str,
    *,
    arm: str,
    entry_point: str | None,
    run_shell_fn,
    session,
) -> dict[str, Any]:
    """Route a Shell call through the arm policy.

    run_shell_fn(command, session=...) is exp.eqpa.tools.run_shell.
    """
    if arm == "B":
        return {
            "ok": False,
            "blocked": True,
            "kind": "shell",
            "capability_block": True,
            "text": "Shell is disabled in this episode (INSPECT=0).",
        }
    if arm == "C":
        allowed, reason = c_arm_command_allowed(command, entry_point)
        if not allowed:
            return {
                "ok": False,
                "blocked": True,
                "kind": "shell",
                "capability_block": True,
                "block_reason": reason,
                "text": C_BLOCK_MSG,
            }
    return run_shell_fn(command, session=session)
