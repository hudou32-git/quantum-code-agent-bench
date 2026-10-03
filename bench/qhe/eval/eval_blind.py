#!/usr/bin/env python3
"""Blind grader: loads sealed test/entry_point; prints ONLY pass/fail + error.

Solvers must NOT read outputs/agent_blind_solve_local_hard/sealed/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from evaluate_completions import (  # noqa: E402
    TASK_EXECUTION_TIMEOUT_OVERRIDES,
    _build_execution_code,
    _run_problem_subprocess,
)

SEALED = HERE.parent / "sealed" / "problems_full.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Blind eval: feedback is pass/fail + error only")
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--completion", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    sealed = {p["task_id"]: p for p in json.loads(SEALED.read_text(encoding="utf-8"))}
    if args.task_id not in sealed:
        print(f"unknown task_id: {args.task_id}", file=sys.stderr)
        return 2
    full = sealed[args.task_id]
    completion = args.completion.read_text(encoding="utf-8")

    # Hard local_hard: full-program completions; do not prepend prompt.
    problem = {
        "prompt": full["prompt"],
        "test": full["test"],
        "entry_point": full["entry_point"],
    }
    code = _build_execution_code(problem, completion, exclude_prompt=True)
    timeout = TASK_EXECUTION_TIMEOUT_OVERRIDES.get(args.task_id, 60)
    ok, err = _run_problem_subprocess(
        code, str(full["entry_point"]), timeout_seconds=timeout
    )

    # Feedback contract: ONLY these fields (no test/entry_point/canonical/difficulty).
    result = {
        "task_id": args.task_id,
        "passed": bool(ok),
        "error": (err or "") if not ok else "",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Human-readable one-liner (still no sealed fields)
    if ok:
        print(f"{args.task_id}: PASS")
    else:
        print(f"{args.task_id}: FAIL")
        print(result["error"][:4000])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
