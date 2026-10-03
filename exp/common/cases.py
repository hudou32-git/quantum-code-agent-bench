"""Case loaders for the two benchmarks (public fields only)."""

from __future__ import annotations

import json
from typing import Any

from exp import config

_QHE_CACHE: dict[str, dict[str, Any]] | None = None


def _qhe_dataset() -> dict[str, dict[str, Any]]:
    global _QHE_CACHE
    if _QHE_CACHE is None:
        path = config.QHE_DATASET_DIR / "dataset_qiskit_test_human_eval_local_hard.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        _QHE_CACHE = {p["task_id"]: p for p in rows}
    return _QHE_CACHE


def load_case(case_id: str) -> dict[str, Any]:
    """QHE local_hard public case: prompt / entry_point / hidden test."""
    ds = _qhe_dataset()
    if case_id not in ds:
        raise KeyError(case_id)
    problem = ds[case_id]
    return {
        "case_id": case_id,
        "entry_point": problem["entry_point"],
        "prompt": problem.get("prompt") or "",
        "test": problem.get("test") or "",
        "benchmark": "qhe",
        "framework": "qiskit",
    }


def load_base_case(case_id: str, *, bench: str, framework: str = "qiskit") -> dict[str, Any]:
    if (bench or "qhe").strip().lower() == "qbplus":
        from exp.common.grader_qbplus import load_qbplus_case

        return load_qbplus_case(case_id, framework=framework)
    return load_case(case_id)
