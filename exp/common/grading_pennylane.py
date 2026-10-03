"""Official QuanBench+ pennylane grader in a spawn worker.

Pennylane-side counterpart of grading_cirq.py's cirq worker. Semantics are
frozen to the upstream quanbench-plus pennylane pipeline (snapshot
bench/qbplus/dataset/eval_pennylane/): the completion returns a qml.sample()
numpy array (1000 shots declared inside the model code's device spec);
get_probs_pennylane reproduces the upstream three-branch sample->probability
contract verbatim (2-D bit rows -> first-wire-MSB decimal counts; 1-D
int/bool -> binary [P(<=0), P(>0)]; 1-D float -> upstream TypeError); KL vs
canonical_output with the shared threshold. The qiskit and cirq paths are
untouched.
"""

from __future__ import annotations

import multiprocessing as mp
import traceback
from typing import Any, Optional

from exp.common.grading import GradeResult, _kl
from exp import config


def _worker_pennylane(
    code: str,
    entry: str,
    tid: str,
    expected,
    shots: int,
    q: mp.Queue,
) -> None:
    try:
        import sys
        import io

        sys.path.insert(0, str(config.QBPLUS_ROOT))
        from utils.get_canonical_results_pennylane import (  # type: ignore
            GLOBAL_INPUTS,
            get_probs_pennylane,
        )
        from utils.get_kl_div import get_kl_div  # type: ignore

        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        key = str(tid).zfill(2) if str(tid).isdigit() else str(tid)
        info: dict[str, Any] = {
            "passed": False,
            "error_type": "",
            "feedback": "",
            "output_type": "ndarray",
            "kl": None,
            "kl_reversed": None,
            "top_counts": [],
            "n_qubits": None,
            "n_clbits": None,
            "has_measure": None,
        }
        try:
            probs = get_probs_pennylane(key, code, entry, int(shots), GLOBAL_INPUTS)
        except Exception as exc:
            # Upstream contract: errors from get_handler or the get_probs
            # branches (incl. the 1-D float TypeError) fail the attempt.
            info["output_type"] = ""
            info["error_type"] = type(exc).__name__
            info["feedback"] = str(exc)
            q.put(info)
            return

        n = len(expected) if isinstance(expected, list) else 0
        if n <= 0:
            info["error_type"] = "GradeError"
            info["feedback"] = "missing canonical_output"
            q.put(info)
            return
        if len(probs) != n:
            # Upstream get_pennylane_results.main wording, verbatim.
            info["error_type"] = "ShapeMismatch"
            info["feedback"] = (
                f"shape mismatch: model_probs len {len(probs)}, "
                f"canonical_probs len {n}"
            )
            q.put(info)
            return
        ranked = sorted(enumerate(probs.tolist()), key=lambda kv: -kv[1])[:5]
        info["top_counts"] = [(str(i), float(p)) for i, p in ranked]
        kl, ok = get_kl_div(probs=probs, expected_probs=expected)
        info["kl"] = float(kl)
        info["kl_reversed"] = _kl(probs[::-1], expected)
        if ok:
            info["passed"] = True
            q.put(info)
            return
        info["error_type"] = "KLMismatch"
        info["feedback"] = f"KL={float(kl):.6g} threshold={config.KL_THRESHOLD}"
        q.put(info)
    except Exception as exc:
        q.put(
            {
                "passed": False,
                "error_type": type(exc).__name__,
                "feedback": f"{exc}\n{traceback.format_exc()[-400:]}",
            }
        )


def grade_official_pennylane(
    task,
    code: str,
    timeout: Optional[float] = None,
    shots: Optional[int] = None,
) -> GradeResult:
    import time

    t0 = time.perf_counter()
    ctx = mp.get_context("spawn")
    q: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(
        target=_worker_pennylane,
        args=(
            code,
            task.entry_point,
            task.problem_id,
            task.canonical_output,
            config.QBPLUS_SHOTS if shots is None else int(shots),
            q,
        ),
    )
    proc.start()
    proc.join(timeout or config.GRADE_TIMEOUT)
    wall = time.perf_counter() - t0
    if proc.is_alive():
        proc.terminate()
        proc.join(10)
        return GradeResult(
            passed=False,
            feedback=f"Execution timeout ({timeout or config.GRADE_TIMEOUT}s)",
            error_type="Timeout",
            wall_time=wall,
        )
    try:
        item = q.get_nowait()
    except Exception:
        return GradeResult(
            passed=False,
            feedback="Worker exited without result",
            error_type="ProcessError",
            wall_time=wall,
        )
    return GradeResult(
        passed=bool(item.get("passed")),
        feedback=str(item.get("feedback") or ""),
        error_type=str(item.get("error_type") or ""),
        kl=item.get("kl"),
        kl_reversed=item.get("kl_reversed"),
        top_counts=list(item.get("top_counts") or []),
        output_type=str(item.get("output_type") or ""),
        wall_time=wall,
    )
