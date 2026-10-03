"""Blind QB+ eval: pass/fail + error only. Spawned by grader_qbplus.grade_qbplus.

Run: QHE_PYTHON exp/common/eval_qbplus.py --task-id 01 --completion ... --out ...
Needs the submit root on PYTHONPATH (set by the caller) for `exp` imports.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from exp.common.grader_qbplus import get_task, normalize_framework  # noqa: E402
from exp.common.grading import grade_official  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Blind QB+ eval: pass/fail + error only")
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--framework", default="qiskit")
    ap.add_argument("--completion", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    fw = normalize_framework(args.framework)
    task = get_task(args.task_id, fw)
    code = args.completion.read_text(encoding="utf-8")
    # grade_official dispatches on task.framework (qiskit worker / cirq worker).
    gr = grade_official(task, code)
    err = ""
    if not gr.passed:
        err = gr.public_feedback()
    result = {
        "task_id": str(task.problem_id),
        "framework": fw,
        "passed": bool(gr.passed),
        "error": err,
        "error_type": gr.error_type or "",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if gr.passed:
        print(f"{task.problem_id}: PASS")
    else:
        print(f"{task.problem_id}: FAIL")
        print(err[:4000])
    return 0 if gr.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
