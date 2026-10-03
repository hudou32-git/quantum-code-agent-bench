"""QuanBench+ (qiskit) dataset loader and official grader glue.

Grading spawns bench-side eval_qbplus.py under QHE_PYTHON with the submit
root on PYTHONPATH so the `exp` package resolves.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exp import config
from exp.common.grader_qhe import looks_like_full_module

# e9 (2026-09-21): pennylane suite migrated alongside qiskit/cirq (42 tasks,
# ids identical across the three frameworks).
FRAMEWORKS = ("qiskit", "cirq", "pennylane")


@dataclass
class Task:
    benchmark: str
    problem_id: str
    framework: str
    prompt: str
    entry_point: str
    test: str
    canonical_solution: str
    full_canonical_code: str
    category: str = ""
    canonical_output: Any = None
    extra: dict = field(default_factory=dict)


def _assemble_full_code(prompt: str, solution: str) -> str:
    sol = (solution or "").strip("\n")
    if looks_like_full_module(sol) and "def " in sol:
        return sol + "\n"
    return (prompt or "").rstrip() + "\n" + sol + "\n"


_SUITES: dict[str, dict[str, Task]] = {}


def _problems_path(framework: str) -> Path:
    if framework == "qiskit":
        return config.QBPLUS_PROBLEMS
    if framework == "cirq":
        return config.QBPLUS_PROBLEMS_CIRQ
    if framework == "pennylane":
        return config.QBPLUS_PROBLEMS_PENNYLANE
    raise ValueError(f"no sealed suite for framework {framework!r}")


def load_suite(framework: str = "qiskit") -> dict[str, Task]:
    """quanbench_plus sealed suite + canonical outputs, per framework."""
    fw = normalize_framework(framework)
    cached = _SUITES.get(fw)
    if cached is not None:
        return cached
    rows = json.loads(_problems_path(fw).read_text(encoding="utf-8"))
    outputs: dict[str, Any] = {}
    if config.QBPLUS_CANONICAL.is_file():
        raw = json.loads(config.QBPLUS_CANONICAL.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            for item in raw:
                outputs[str(item["task_id"]).zfill(2)] = item.get("canonical_output")
        elif isinstance(raw, dict):
            outputs = {str(k).zfill(2): v for k, v in raw.items()}
    out: dict[str, Task] = {}
    for row in rows:
        tid = str(row["task_id"]).zfill(2)
        prompt = row.get("complete_prompt") or row.get("prompt") or ""
        canon = row.get("canonical_solution") or ""
        cout = row.get("canonical_output")
        if cout is None:
            cout = outputs.get(tid)
        out[tid] = Task(
            benchmark="quanbench_plus",
            problem_id=tid,
            framework=fw,
            prompt=prompt,
            entry_point=str(row.get("entry_point") or ""),
            test=row.get("test") or "",
            canonical_solution=canon,
            full_canonical_code=_assemble_full_code(prompt, canon),
            category=str(row.get("category") or ""),
            canonical_output=cout,
            extra={"grade_metric": row.get("grade_metric")},
        )
    _SUITES[fw] = out
    return out


def get_task(problem_id: str, framework: str = "qiskit") -> Task:
    suite = load_suite(framework)
    if problem_id in suite:
        return suite[problem_id]
    for k, t in suite.items():
        if k == problem_id or k.endswith("/" + problem_id) or k.zfill(2) == problem_id.zfill(2):
            return t
    raise KeyError(f"{problem_id} not in quanbench_plus ({framework})")


def list_ids(framework: str = "qiskit") -> list[str]:
    return sorted(load_suite(framework).keys())


def normalize_framework(name: str | None) -> str:
    fw = (name or "qiskit").strip().lower()
    if fw not in FRAMEWORKS:
        raise ValueError(f"unknown QuanBench+ framework {name!r}; migrated suites: {FRAMEWORKS}")
    return fw


def load_qbplus_case(case_id: str, framework: str = "qiskit") -> dict[str, Any]:
    fw = normalize_framework(framework)
    task = get_task(case_id, fw)
    return {
        "case_id": task.problem_id,
        "entry_point": task.entry_point,
        "prompt": task.prompt or "",
        "test": "",
        "benchmark": "quanbench_plus",
        "framework": task.framework,
    }


def arm_dest(tag: str, case_id: str, *, results_root) -> Path:
    d = Path(results_root) / tag / "BASE" / str(case_id).replace("/", "_")
    d.mkdir(parents=True, exist_ok=True)
    return d


def grade_qbplus(case: dict[str, Any], code: str, *, dest, k: int, framework: str = "qiskit") -> dict[str, Any]:
    """Grade one attempt via the official KL pipeline (spawned, blind)."""
    fw = normalize_framework(framework)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"attempt_{k}.py"
    out = dest / f"attempt_{k}_result.json"
    path.write_text(
        (code or "") + ("\n" if code and not str(code).endswith("\n") else ""),
        encoding="utf-8",
    )
    cmd = [
        str(config.QHE_PYTHON),
        str(config.EVAL_QBPLUS),
        "--task-id",
        str(case["case_id"]),
        "--framework",
        fw,
        "--completion",
        str(path),
        "--out",
        str(out),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(config.ROOT)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(config.ROOT),
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "error_message": "Execution timeout (120s)",
            "error_type": "Timeout",
        }
    payload: dict[str, Any] = {}
    if out.is_file():
        try:
            payload = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    err = str(payload.get("error") or "")
    if not err and not payload.get("passed"):
        err = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[:2000]
    return {
        "passed": bool(payload.get("passed")),
        "error_message": err,
        "error_type": str(payload.get("error_type") or ""),
    }
