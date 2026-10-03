#!/usr/bin/env python3
"""
Evaluate model completions saved as JSONL against the Qiskit HumanEval dataset.

Each JSONL line must be a JSON object with at least:
  {"task_id": "qiskitHumanEval/0", "completion": "..."}

Multiple lines with the same ``task_id`` are treated as independent samples (same
semantics as OpenAI HumanEval JSONL), enabling unbiased ``pass@k`` estimates
when each task has enough samples per ``k``.

The meaning of completion depends on the dataset variant:

- Standard dataset (dataset_qiskit_test_human_eval.json): ``completion`` is only the
  function body lines (same as ``canonical_solution`` in the benchmark), pasted after
  ``prompt``.
- Hard dataset (dataset_qiskit_test_human_eval_hard.json): use ``--exclude-prompt``.
  Then ``completion`` must be full code as in canonical solutions there: imports plus
  full function definitions, before the ``test`` block is appended (same concatenation as
  test_solutions.py with exclude_prompt).

Usage:
    python scripts/evaluate_completions.py \\
        --dataset dataset/dataset_qiskit_test_human_eval.json \\
        --completions outputs/completions.jsonl

    python scripts/evaluate_completions.py \\
        --dataset dataset/dataset_qiskit_test_human_eval_hard.json \\
        --completions outputs/completions_hard.jsonl \\
        --exclude-prompt

Pass@k (same estimator as OpenAI ``human_eval.evaluation``) and parallel workers::

    python scripts/evaluate_completions.py ... --k 1,10,100 --workers 8

Incomplete JSONL (e.g. while resuming generations)::
    python scripts/evaluate_completions.py ... --subset

**Timing**: each subprocess run records ``eval_wall_seconds`` in ``timing.per_task_eval``.
The ``-o`` JSON adds a ``timing`` object with:

- ``evaluate_loop_wall_seconds`` — wall clock for loading the dataset + scheduling + waiting on all jobs
- ``total_subprocess_wall_seconds`` — sum of per-sample subprocess wall times (spawn + exec + check)
- ``mean_subprocess_wall_seconds`` / ``max_single_task_eval_wall_seconds``
- ``timeout_limit_seconds_per_task`` — default hard cap per task (30s)
- ``timeout_overrides_seconds_by_task`` — per-task overrides (e.g. slow transpile/decompose)
- ``overall_script_wall_seconds`` — from right after CLI parse through end of evaluation (includes JSONL load and ``mp.freeze_support``)
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import multiprocessing as mp
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Union

import numpy as np

# Align with test_solutions.py (default); some tasks need longer subprocess runs.
# Default doubled 30 -> 60 (user directive, 2026-09-16). Per-task overrides were
# emptied by the same directive except task 100 (Solovay-Kitaev, ~106s measured),
# which keeps its official 120s pin; 96/108 stay at the uniform 60s.
EXECUTION_TIMEOUT_SECONDS = 60
TASK_EXECUTION_TIMEOUT_OVERRIDES: dict[str, int] = {
    "qiskitHumanEval/100": 120,
}

logger = logging.getLogger(__name__)


def estimate_pass_at_k(
    num_samples: Union[int, list[int], np.ndarray],
    num_correct: Union[list[int], np.ndarray],
    k: int,
) -> np.ndarray:
    """
    Unbiased pass@k estimate per problem (same closed form as OpenAI HumanEval):
    1 - comb(n - c, k) / comb(n, k), with the stable product implementation.
    """

    def estimator(n: int, c: int, k: int) -> float:
        if n - c < k:
            return 1.0
        return 1.0 - float(np.prod(1.0 - k / np.arange(n - c + 1, n + 1)))

    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array([estimator(int(n), int(c), k) for n, c in zip(num_samples_it, num_correct)])


def _build_restricted_builtins() -> dict[str, Any]:
    import builtins as _builtins

    blocked = {"exec", "eval", "compile", "breakpoint", "input"}
    return {k: v for k, v in vars(_builtins).items() if k not in blocked}


def _child_exec_and_check(code: str, entry_point: str, queue: mp.Queue) -> None:
    """Runs in spawned child: exec + ``check(candidate)``. Puts ``(success, msg)`` on queue."""
    try:
        namespace: dict[str, Any] = {"__builtins__": _build_restricted_builtins()}
        exec(code, namespace)
        if entry_point not in namespace:
            queue.put((False, f'Entry point "{entry_point}" not defined after exec'))
            return
        if "check" not in namespace:
            queue.put((False, 'Test block did not define "check"'))
            return
        namespace["check"](namespace[entry_point])
        queue.put((True, ""))
    except Exception as e:
        queue.put((False, f"{type(e).__name__}: {e}"))


def _execution_timeout_for_task(task_id: str) -> int:
    return TASK_EXECUTION_TIMEOUT_OVERRIDES.get(task_id, EXECUTION_TIMEOUT_SECONDS)


def _run_problem_subprocess(code: str, entry_point: str, *, timeout_seconds: int) -> tuple[bool, str]:
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_child_exec_and_check, args=(code, entry_point, queue))
    proc.start()
    proc.join(timeout_seconds)
    if proc.is_alive():
        proc.terminate()
        proc.join(15)
        return False, f"Execution timeout ({timeout_seconds}s)"
    try:
        return queue.get_nowait()
    except Exception:
        return False, "Worker exited without result (possible crash)"


def _normalize_completion_text(completion: str) -> str:
    """Strip trailing whitespace only — leading indent/newlines matter for AST."""
    return completion.replace("\r\n", "\n").rstrip()


def _build_execution_code(problem: dict[str, Any], completion: str, exclude_prompt: bool) -> str:
    body = _normalize_completion_text(completion)
    if exclude_prompt:
        return body + "\n" + problem["test"]
    return problem["prompt"] + "\n" + body + "\n" + problem["test"]


def _eval_one_sample(
    problem: dict[str, Any],
    completion: str,
    exclude_prompt: bool,
    task_id: str,
    completion_id: int,
) -> dict[str, Any]:
    """Runs one subprocess check; intended to be called from worker threads."""
    required = {"prompt", "test", "entry_point"}
    missing = required - set(problem.keys())
    if missing:
        return {
            "task_id": task_id,
            "completion_id": completion_id,
            "passed": False,
            "error": f"missing dataset fields {missing}",
            "eval_wall_seconds": 0.0,
            "code": "",
            "skipped": True,
        }

    code = _build_execution_code(problem, completion, exclude_prompt)
    entry_point = str(problem["entry_point"])
    timeout_seconds = _execution_timeout_for_task(task_id)
    t_ev = time.perf_counter()
    ok, err = _run_problem_subprocess(code, entry_point, timeout_seconds=timeout_seconds)
    elapsed = round(time.perf_counter() - t_ev, 4)
    return {
        "task_id": task_id,
        "completion_id": completion_id,
        "passed": ok,
        "error": err if not ok else "",
        "eval_wall_seconds": elapsed,
        "code": code[:2000] if not ok else "",
        "skipped": False,
    }


def load_completions_jsonl(path: Path) -> dict[str, list[str]]:
    """Map task_id -> ordered list of completion strings (multiple lines per task allowed)."""
    mapping: dict[str, list[str]] = {}
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            tid = obj.get("task_id")
            comp = obj.get("completion")
            if not tid or comp is None:
                raise ValueError(f"{path}:{line_no}: missing task_id or completion")
            tid_s = str(tid)
            mapping.setdefault(tid_s, []).append(str(comp))
    return mapping


def evaluate_dataset(
    dataset_path: Path,
    completions: dict[str, list[str]],
    exclude_prompt: bool,
    *,
    subset_only: bool,
    k_list: list[int],
    n_workers: int,
) -> tuple[int, int, list[dict[str, Any]], int, dict[str, Any], dict[str, float]]:
    """Return (passed_tasks_all_samples, total_scored_tasks, failures, dataset_size, timing, pass_at_k)."""
    with dataset_path.open(encoding="utf-8") as f:
        problems: list[dict[str, Any]] = json.load(f)

    dataset_size = len(problems)
    failures: list[dict[str, Any]] = []
    ids_in_dataset = {str(p.get("task_id")) for p in problems if p.get("task_id")}
    total_scoring = len(problems)

    if not subset_only:
        for tid in sorted(ids_in_dataset - set(completions.keys())):
            failures.append({"task_id": tid, "error": "missing completion in JSONL"})

    jobs: list[tuple[dict[str, Any], str, bool, str, int]] = []
    for problem in problems:
        tid = str(problem.get("task_id", ""))
        if subset_only and tid not in completions:
            continue
        comp_list = completions.get(tid)
        if comp_list is None:
            continue
        for completion_id, comp in enumerate(comp_list):
            jobs.append((problem, comp, exclude_prompt, tid, completion_id))

    evaluate_loop_t0 = time.perf_counter()
    raw_results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [
            executor.submit(_eval_one_sample, problem, comp, excl, tid, cid)
            for (problem, comp, excl, tid, cid) in jobs
        ]
        for fut in as_completed(futures):
            raw_results.append(fut.result())

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_results:
        by_task[row["task_id"]].append(row)

    per_task_eval: list[dict[str, Any]] = []
    passed_tasks_all_samples = 0
    passed_samples = 0
    n_samples_total = 0

    totals: list[int] = []
    corrects: list[int] = []

    for tid in sorted(by_task.keys()):
        rows = sorted(by_task[tid], key=lambda r: r["completion_id"])
        skipped_any = any(r.get("skipped") for r in rows)
        if skipped_any:
            for r in rows:
                if r.get("skipped"):
                    failures.append({"task_id": tid, "error": r["error"]})
            continue

        passed_flags = [bool(r["passed"]) for r in rows]
        n = len(passed_flags)
        c = sum(passed_flags)
        n_samples_total += n
        passed_samples += c
        totals.append(n)
        corrects.append(c)

        if c == n:
            passed_tasks_all_samples += 1

        for r in rows:
            per_task_eval.append(
                {
                    "task_id": tid,
                    "completion_id": r["completion_id"],
                    "eval_wall_seconds": r["eval_wall_seconds"],
                    "passed": r["passed"],
                }
            )
            if not r["passed"]:
                failures.append(
                    {
                        "task_id": tid,
                        "completion_id": r["completion_id"],
                        "error": r["error"],
                        "code": r["code"],
                    }
                )
                logger.warning(
                    "failed %s sample %s (eval %.4fs): %s",
                    tid,
                    r["completion_id"],
                    r["eval_wall_seconds"],
                    r["error"],
                )
            else:
                logger.debug("passed %s sample %s (eval %.4fs)", tid, r["completion_id"], r["eval_wall_seconds"])

    if subset_only:
        total_scoring = len([p for p in problems if str(p.get("task_id", "")) in completions])

    evaluate_loop_wall = round(time.perf_counter() - evaluate_loop_t0, 4)
    total_subproc = round(sum(x["eval_wall_seconds"] for x in per_task_eval), 4) if per_task_eval else 0.0
    mean_subproc = round(total_subproc / len(per_task_eval), 6) if per_task_eval else 0.0
    max_subproc = max((x["eval_wall_seconds"] for x in per_task_eval), default=None)

    total_arr = np.array(totals, dtype=int)
    correct_arr = np.array(corrects, dtype=int)
    pass_at_k: dict[str, float] = {}
    if len(totals) > 0:
        for k in k_list:
            if (total_arr >= k).all():
                key = f"pass@{k}"
                pass_at_k[key] = float(estimate_pass_at_k(total_arr, correct_arr, k).mean())

    timing: dict[str, Any] = {
        "evaluate_loop_wall_seconds": evaluate_loop_wall,
        "tasks_run_subprocess": len({x["task_id"] for x in per_task_eval}),
        "jsonl_samples_evaluated": n_samples_total,
        "samples_passed": passed_samples,
        "parallel_workers": n_workers,
        "total_subprocess_wall_seconds": total_subproc,
        "mean_subprocess_wall_seconds": mean_subproc,
        "max_single_task_eval_wall_seconds": max_subproc,
        "timeout_limit_seconds_per_task": EXECUTION_TIMEOUT_SECONDS,
        "timeout_overrides_seconds_by_task": dict(TASK_EXECUTION_TIMEOUT_OVERRIDES),
        "per_task_eval": per_task_eval,
        "pass_at_k": pass_at_k,
        "k_requested": k_list,
    }

    return passed_tasks_all_samples, total_scoring, failures, dataset_size, timing, pass_at_k


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate JSONL completions on Qiskit HumanEval.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--completions", type=Path, required=True, help="JSONL with task_id and completion")
    parser.add_argument(
        "--exclude-prompt",
        action="store_true",
        help="Concatenate completion + test only (required for *_hard*.json semantics).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Optional JSON summary path")
    parser.add_argument(
        "--subset",
        action="store_true",
        help=(
            "Only score tasks whose task_id appears in the JSONL "
            '(no "missing completion" errors for uncovered tasks).'
        ),
    )
    parser.add_argument(
        "--k",
        type=str,
        default="1,10,100",
        help="Comma-separated k values for pass@k (only reported when every evaluated task has n>=k).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent threads scheduling subprocess evaluations (default: 4).",
    )
    parser.add_argument(
        "--failures-output",
        type=Path,
        default=None,
        help=(
            "Write every failed sample to JSONL (task_id, completion_id, error, code). "
            "Used by QBugGen taxonomy without re-running eval."
        ),
    )
    args = parser.parse_args()

    overall_t0 = time.perf_counter()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    if not args.exclude_prompt:
        name = args.dataset.name.lower()
        if "hard" in name:
            logger.warning(
                'Dataset filename looks like HARD variant — did you forget --exclude-prompt? '
                "(Hard completions must be full imports + def, not body-only.)"
            )

    k_list = [int(x.strip()) for x in args.k.split(",") if x.strip()]
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    completions = load_completions_jsonl(args.completions)
    n_jsonl_lines = sum(len(v) for v in completions.values())

    mp.freeze_support()

    logger.info(
        "Evaluating %s with %s (%d task ids, %d JSONL samples) workers=%d k=%s",
        args.dataset,
        args.completions,
        len(completions),
        n_jsonl_lines,
        args.workers,
        k_list,
    )

    passed, total_scored, failures, ds_size, timing, pass_at_k = evaluate_dataset(
        args.dataset,
        completions,
        args.exclude_prompt,
        subset_only=args.subset,
        k_list=k_list,
        n_workers=args.workers,
    )
    timing["overall_script_wall_seconds"] = round(time.perf_counter() - overall_t0, 4)

    summary = {
        "dataset": str(args.dataset),
        "completions_file": str(args.completions),
        "exclude_prompt": args.exclude_prompt,
        "subset_only": args.subset,
        "k_requested": k_list,
        "parallel_workers": args.workers,
        "passed": passed,
        "passed_tasks_all_samples": passed,
        "total_scored_tasks": total_scored,
        "total_problems_in_dataset": ds_size,
        "failed_or_missing": len(failures),
        "accuracy_on_scored_tasks": passed / total_scored if total_scored else 0.0,
        "pass_at_k": pass_at_k,
        "timing": timing,
        "failures": failures[:50],
    }

    pass_str = ", ".join(f"{pk}={pv:.4f}" for pk, pv in sorted(pass_at_k.items(), key=lambda x: int(x[0].split("@")[1])))
    logger.info(
        "Result: %d / %d tasks all samples passed (dataset size %d) | samples=%d | %s | subprocess_total=%.2fs loop=%.2fs overall=%.2fs",
        passed,
        total_scored,
        ds_size,
        timing.get("jsonl_samples_evaluated", 0),
        pass_str or "pass@k=(n/a for requested k)",
        timing["total_subprocess_wall_seconds"],
        timing["evaluate_loop_wall_seconds"],
        timing["overall_script_wall_seconds"],
    )

    if args.output:
        with args.output.open("w", encoding="utf-8") as wf:
            json.dump(summary, wf, indent=2, ensure_ascii=False)
            wf.write("\n")

    if args.failures_output:
        args.failures_output.parent.mkdir(parents=True, exist_ok=True)
        with args.failures_output.open("w", encoding="utf-8") as ff:
            for rec in failures:
                ff.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.info("Wrote %d failure records to %s", len(failures), args.failures_output)

    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
