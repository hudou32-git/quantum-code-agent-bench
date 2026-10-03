"""Grader runtime record for the QHE main-table grader.

2026-09-19 grader unification (user directive): QHE grading spawns the conda
qhe interpreter (config.QHE_PYTHON, qiskit 2.4.1) per attempt via
exp/common/eval_qhe.py — the same environment as the 2026-09-17 canonical full
verification (README §4) and the same one QB+ grading uses. The runner itself
may be any python; the legacy in-process 1.2.4 path remains available via
env QHE_GRADER_INPROCESS=1 (grader_qhe.run_candidate_system_python) solely to
reproduce rows frozen before 2026-09-19.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from exp import config

_PROBE_CACHE: dict[str, str] | None = None


def _probe_qhe_env() -> dict[str, str]:
    global _PROBE_CACHE
    if _PROBE_CACHE is not None:
        return _PROBE_CACHE
    try:
        proc = subprocess.run(
            [str(config.QHE_PYTHON), "-c", "import qiskit; print(qiskit.__version__)"],
            capture_output=True, text=True, timeout=60, cwd=str(config.ROOT),
        )
        ver = (proc.stdout or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"conda qhe grader env unreachable ({config.QHE_PYTHON}): {exc}"
        ) from exc
    if not ver:
        raise RuntimeError(
            f"conda qhe grader env cannot import qiskit ({config.QHE_PYTHON}): "
            f"{(proc.stderr or '')[-200:]}"
        )
    _PROBE_CACHE = {"executable": str(config.QHE_PYTHON), "qiskit": ver}
    return _PROBE_CACHE


def require_grader_python() -> dict[str, str]:
    """Record the QHE main-table grading runtime. Default (unified): the conda
    qhe interpreter + its qiskit version, probed live so a broken grader env
    refuses before any LLM budget is spent. Legacy in-process mode
    (QHE_GRADER_INPROCESS=1) records the runner interpreter instead — use only
    to reproduce pre-2026-09-19 frozen rows."""
    import os

    if os.environ.get("QHE_GRADER_INPROCESS") == "1":
        exe = str(Path(sys.executable).resolve())
        try:
            from qiskit import __version__ as qv
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"legacy grader python cannot import qiskit: {exc}") from exc
        return {
            "executable": exe,
            "qiskit": str(qv),
            "mode": "inprocess_legacy_1_2_4",
        }
    rec = dict(_probe_qhe_env())
    rec["runner_executable"] = str(Path(sys.executable).resolve())
    rec["mode"] = "conda_qhe_spawn"
    return rec


def require_grader_python_cirq() -> dict[str, str]:
    """e8 (QB+_cirq): conda qhe runtime + live cirq version probe, on top of
    the standard qiskit probe (the qhe env hosts both frameworks)."""
    rec = require_grader_python()
    try:
        proc = subprocess.run(
            [str(config.QHE_PYTHON), "-c", "import cirq; print(cirq.__version__)"],
            capture_output=True, text=True, timeout=60, cwd=str(config.ROOT),
        )
        ver = (proc.stdout or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"conda qhe grader env unreachable for cirq ({config.QHE_PYTHON}): {exc}"
        ) from exc
    if not ver:
        raise RuntimeError(
            f"conda qhe grader env cannot import cirq ({config.QHE_PYTHON}): "
            f"{(proc.stderr or '')[-200:]}"
        )
    rec["framework"] = "cirq"
    rec["cirq"] = ver
    return rec


def require_grader_python_pennylane() -> dict[str, str]:
    """e9 (QB+_pennylane): conda qhe runtime + live pennylane version probe, on
    top of the standard qiskit probe (the qhe env hosts all frameworks)."""
    rec = require_grader_python()
    try:
        proc = subprocess.run(
            [str(config.QHE_PYTHON), "-c", "import pennylane; print(pennylane.__version__)"],
            capture_output=True, text=True, timeout=60, cwd=str(config.ROOT),
        )
        ver = (proc.stdout or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"conda qhe grader env unreachable for pennylane ({config.QHE_PYTHON}): {exc}"
        ) from exc
    if not ver:
        raise RuntimeError(
            f"conda qhe grader env cannot import pennylane ({config.QHE_PYTHON}): "
            f"{(proc.stderr or '')[-200:]}"
        )
    rec["framework"] = "pennylane"
    rec["pennylane"] = ver
    return rec
