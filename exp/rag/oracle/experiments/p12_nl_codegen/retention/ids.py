"""Stable IDs for P12-NL retention (protocol-frozen naming)."""

from __future__ import annotations

import re
from typing import Optional

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def task_id_safe(task_id: str) -> str:
    """Escape task_id for filenames; reversible via task_id_from_safe for known patterns."""
    # Prefer deterministic replace of / first (qiskitHumanEval/0 → qiskitHumanEval__0)
    s = (task_id or "").replace("/", "__")
    return _SAFE.sub("_", s)


def task_id_from_safe(safe: str) -> str:
    # Reverse only the intentional __ → / mapping used above
    return (safe or "").replace("__", "/")


def make_completion_id(
    *,
    protocol_id: str,
    block: str,
    arm: str,
    task_id: str,
    round_idx: int,
) -> str:
    return f"{protocol_id}__{block}__{arm}__{task_id_safe(task_id)}__r{int(round_idx)}"


def make_attempt_id(completion_id: str, attempt_index: int) -> str:
    return f"{completion_id}__attempt_{int(attempt_index)}"


def parse_completion_id(completion_id: str) -> Optional[dict]:
    """Best-effort parse; arm may contain underscores so split carefully from ends."""
    parts = (completion_id or "").split("__")
    # protocol_id itself may contain underscores? Ours is P12_NL_LOCAL_HARD_v1 (underscores)
    # Format: {protocol_id}__{block}__{arm}__{task_safe}__r{N}
    # With protocol containing underscores this is ambiguous if we only split __.
    # Convention: protocol_id has no '__'; block has no '__'; round is last token rN;
    # task_safe is second-to-last; arm is everything between block and task.
    if len(parts) < 5:
        return None
    round_tok = parts[-1]
    if not round_tok.startswith("r") or not round_tok[1:].isdigit():
        return None
    task_safe = parts[-2]
    block = parts[-4] if len(parts) >= 5 else ""
    # protocol = join of parts until we find block position: protocol is parts[0:-4] joined?
    # Actually: protocol_id = "P12_NL_LOCAL_HARD_v1" has no __, so parts[0]=protocol, parts[1]=block
    protocol_id = parts[0]
    block = parts[1]
    arm = "__".join(parts[2:-2])  # unlikely; arms don't use __
    # Wait: task_id_safe uses __ for slash, so task is parts[-2] only if task has no extra __.
    # qiskitHumanEval__0 → one part with __ already split: parts[-2] and we need to rejoin task.
    # Better format: use single '-' separators for structural fields and keep task_safe with __.
    return {
        "protocol_id": protocol_id,
        "block": block,
        "arm": "__".join(parts[2:-2]) if len(parts) > 4 else parts[2],
        "task_id": task_id_from_safe(task_safe),
        "round": int(round_tok[1:]),
        "completion_id": completion_id,
    }
