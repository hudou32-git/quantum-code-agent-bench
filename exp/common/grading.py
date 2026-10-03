"""Official QuanBench+ Qiskit grader in a spawn worker. Canonical stays in-process."""

from __future__ import annotations

import math
import multiprocessing as mp
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional

from exp.common.grader_qbplus import Task
from exp import config


@dataclass
class GradeResult:
    passed: bool
    feedback: str
    error_type: str = ""
    kl: Optional[float] = None
    kl_reversed: Optional[float] = None
    top_counts: list = field(default_factory=list)
    n_qubits: Optional[int] = None
    n_clbits: Optional[int] = None
    has_measure: Optional[bool] = None
    output_type: str = ""
    wall_time: float = 0.0

    def public_feedback(self) -> str:
        if self.passed:
            return "Official tests passed."
        msg = self.feedback or "failed"
        if len(msg) > 1200:
            msg = msg[:1200] + " …(truncated)"
        prefix = f"{self.error_type}: " if self.error_type else ""
        return prefix + msg


def _kl(p, q, eps=1e-12) -> float:
    import numpy as np

    p = np.clip(np.asarray(p, dtype=float), eps, 1)
    qv = np.clip(np.asarray(q, dtype=float), eps, 1)
    p = p / p.sum()
    qv = qv / qv.sum()
    return float(np.sum(p * np.log(p / qv)))


def _worker(
    code: str,
    entry: str,
    tid: str,
    expected,
    shots: int,
    allow_measure_all: bool,
    q: mp.Queue,
) -> None:
    try:
        import sys
        import io
        sys.path.insert(0, str(config.QBPLUS_ROOT))
        import numpy as np
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
        from utils.get_canonical_results import GLOBAL_INPUTS, get_handler
        from utils.get_kl_div import get_kl_div

        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        key = str(tid).zfill(2) if str(tid).isdigit() else str(tid)
        try:
            # Native QuanBench+ dispatch: lists stay as one argument
            # (VQE_2(parameters), not VQE_2(p0, p1, p2)).
            out = get_handler(key, code, entry, GLOBAL_INPUTS)
        except Exception as exc:
            q.put(
                {
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "feedback": str(exc),
                    "output_type": "",
                }
            )
            return

        info: dict[str, Any] = {
            "passed": False,
            "error_type": "",
            "feedback": "",
            "output_type": type(out).__name__,
            "kl": None,
            "kl_reversed": None,
            "top_counts": [],
            "n_qubits": None,
            "n_clbits": None,
            "has_measure": None,
        }
        if isinstance(out, QuantumCircuit):
            info["n_qubits"] = int(out.num_qubits)
            info["n_clbits"] = int(out.num_clbits)
            # Official convention (bench/qbplus/utils/get_canonical_results.py):
            # "measurable" means the circuit itself contains measure
            # instructions; num_clbits>0 does NOT count. A circuit without any
            # measure instruction is measure_all()'ed before simulation.
            info["has_measure"] = any(
                getattr(getattr(ci, "operation", None), "name", "") == "measure"
                for ci in out.data
            )
            qc = out
            if not info["has_measure"]:
                qc = out.copy()
                qc.measure_all()
                info["has_measure"] = True
                info["n_clbits"] = int(qc.num_clbits)
            try:
                sim = AerSimulator()
                compiled = transpile(qc, sim)
                counts = sim.run(compiled, shots=int(shots)).result().get_counts()
            except Exception as exc:
                info["error_type"] = type(exc).__name__
                info["feedback"] = str(exc)
                q.put(info)
                return
            total = sum(counts.values()) or 1
            ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:5]
            info["top_counts"] = [(str(k), float(v) / total) for k, v in ranked]
            n = len(expected) if isinstance(expected, list) else 0
            if n <= 0:
                info["error_type"] = "GradeError"
                info["feedback"] = "missing canonical_output"
                q.put(info)
                return
            width = int(round(math.log2(n))) if n > 0 else 0
            probs = [counts.get(format(i, f"0{width}b"), 0) / total for i in range(n)]
            rev = [counts.get(format(i, f"0{width}b")[::-1], 0) / total for i in range(n)]
            kl, ok = get_kl_div(np.asarray(probs, dtype=float), np.asarray(expected, dtype=float))
            info["kl"] = float(kl)
            info["kl_reversed"] = _kl(rev, expected)
            if ok:
                info["passed"] = True
                q.put(info)
                return
            info["error_type"] = "KLMismatch"
            info["feedback"] = f"KL={float(kl):.6g} threshold={config.KL_THRESHOLD}"
            q.put(info)
            return
        if isinstance(out, dict):
            n = len(expected) if isinstance(expected, list) else 0
            if n <= 0:
                info["error_type"] = "GradeError"
                info["feedback"] = "missing canonical_output"
                q.put(info)
                return
            width = int(round(math.log2(n))) if n > 0 else 0
            vec = [float(out.get(format(i, f"0{width}b"), 0.0)) for i in range(n)]
            s = sum(vec) or 1.0
            vec = [x / s for x in vec]
            kl, ok = get_kl_div(np.asarray(vec, dtype=float), np.asarray(expected, dtype=float))
            info["kl"] = float(kl)
            if ok:
                info["passed"] = True
            else:
                info["error_type"] = "KLMismatch"
                info["feedback"] = f"KL={float(kl):.6g} threshold={config.KL_THRESHOLD}"
            q.put(info)
            return
        info["error_type"] = "unsupported output type"
        info["feedback"] = type(out).__name__
        q.put(info)
    except Exception as exc:
        q.put(
            {
                "passed": False,
                "error_type": type(exc).__name__,
                "feedback": f"{exc}\n{traceback.format_exc()[-400:]}",
            }
        )


def grade_official(
    task: Task,
    code: str,
    timeout: Optional[float] = None,
    shots: Optional[int] = None,
) -> GradeResult:
    import time

    # e8: cirq tasks route to the cirq worker (upstream cirq_pip semantics);
    # the qiskit path below is untouched.
    if (task.framework or "").strip().lower() == "cirq":
        from exp.common.grading_cirq import grade_official_cirq

        return grade_official_cirq(task, code, timeout=timeout, shots=shots)

    # e9: pennylane tasks route to the pennylane worker (upstream pennylane_pip
    # sample->probs semantics); the qiskit path below is untouched.
    if (task.framework or "").strip().lower() == "pennylane":
        from exp.common.grading_pennylane import grade_official_pennylane

        return grade_official_pennylane(task, code, timeout=timeout, shots=shots)

    t0 = time.perf_counter()
    ctx = mp.get_context("spawn")
    q: mp.Queue = ctx.Queue(maxsize=1)
    allow_measure_all = "without measure" in (task.prompt or "").lower()
    proc = ctx.Process(
        target=_worker,
        args=(
            code,
            task.entry_point,
            task.problem_id,
            task.canonical_output,
            config.QBPLUS_SHOTS if shots is None else int(shots),
            allow_measure_all,
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
        n_qubits=item.get("n_qubits"),
        n_clbits=item.get("n_clbits"),
        has_measure=item.get("has_measure"),
        output_type=str(item.get("output_type") or ""),
        wall_time=wall,
    )


def classify_stage(gr: GradeResult) -> str:
    et = (gr.error_type or "").lower()
    fb = (gr.feedback or "").lower()
    blob = et + " " + fb
    if gr.passed:
        return "PASS"
    if "positional argument" in blob or "required positional" in blob:
        return "SIGNATURE"
    if "parameter" in blob and ("expected" in blob or "got" in blob):
        return "SIGNATURE"
    if any(
        x in blob
        for x in (
            "modulenotfound",
            "importerror",
            "no module named",
            "has no attribute",
            "c_if",
            "cannot import name",
        )
    ):
        return "API"
    if any(
        x in blob
        for x in (
            "unsupported output type",
            "nonetype",
            "no counts",
            "not quantumcircuit",
        )
    ):
        return "CONTRACT"
    if et == "KLMismatch" or blob.strip().startswith("kl=") or "klmismatch" in blob:
        return "KL"
    if "syntax" in blob:
        return "SYNTAX"
    return "OTHER"
