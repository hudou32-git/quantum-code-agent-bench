"""Evidence-EQPA runner. Structure mirrors exp.eqpa.run (resume-safe,
manifest+protocol recording) with the batch knobs and variant flags recorded.

Variants (mutually comparable, separate tags):
  batch only (default)          e7_evidence_eqpa[_cohort|_dev|_qbplus]
  + --planning                  ..._plan
  + --progress                  ..._prog
  + --planning --progress       ..._plan_prog
"""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from exp import config
from exp.common.canary import ensure_canaries, scan_text
from exp.common.env_guard import require_grader_python
from exp.eqpa.env_guard import require_grader_runtime
from exp.common.llm import DeepSeekClient, official_chat_url
from exp.common import llm_obs
from exp.common.repeat_guard import generation_guard_record
from exp.common.traceio import load_traces
from exp.evidence_eqpa import config as bcfg
from exp.evidence_eqpa import loop as ev_loop
from exp.eqpa.bwrap import require_bwrap

_io_lock = threading.Lock()
_tls = threading.local()
PROTOCOL_PATH = Path(__file__).resolve().parent / "README_EVIDENCE_EQPA.md"


def _client() -> DeepSeekClient:
    return DeepSeekClient(
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
        disable_thinking=True,
        system=bcfg.BATCH_SYSTEM,
        max_retries=3,
    )


def _thread_client() -> DeepSeekClient:
    c = getattr(_tls, "client", None)
    if c is None:
        c = _client()
        _tls.client = c
    return c


def _clamp_workers(n: int | None, pending: int) -> int:
    raw = config.JOB_WORKERS if n is None else int(n)
    cap = min(config.JOB_WORKERS_MAX, config.LLM_CONCURRENCY_LIMIT)
    want = max(1, min(raw, cap))
    return min(want, max(1, pending)) if pending else 1


def _pass_at_1(row: dict[str, Any]) -> bool:
    for s in row.get("shots") or []:
        if int(s.get("k") or 0) == 1:
            return bool(s.get("passed"))
    return False


def _load_cohort_ids() -> list[str]:
    coh = json.loads((config.PKG / "eqpa/results/isoabl/e4_isoabl_cohort.json").read_text())
    return sorted({str(t) for t in coh["cohort"]})


def run_evidence(
    *,
    case_ids: list[str] | None = None,
    dev: bool = True,
    cohort: bool = False,
    tag: str | None = None,
    workers: int | None = None,
    bench: str = "qhe",
    planning: bool = False,
    progress: bool = False,
) -> dict[str, Any]:
    bcfg.set_modes(planning, progress)
    require_bwrap()
    ensure_canaries()
    bench = (bench or "qhe").strip().lower()
    if bench == "qhe":
        require_grader_runtime()
    if cohort:
        ids = _load_cohort_ids()
        split = "cohort"
    elif case_ids:
        ids = list(case_ids)
        split = "dev" if dev else "eval"
    elif dev:
        ids = list(bcfg.EQPA_DEV_CASES)
        split = "dev"
    elif bench == "qbplus":
        from exp.common.grader_qbplus import list_ids

        ids = list_ids("qiskit")
        split = "eval"
    else:
        from exp.common.cases import _qhe_dataset

        ids = sorted(_qhe_dataset().keys())
        split = "eval"
    tag = tag or bcfg.default_tag(bench=bench, dev=dev, cohort=cohort)
    bcfg.refuse_foreign_tag(tag)
    results_root = config.arm_results("evidence_eqpa")
    results_root.mkdir(parents=True, exist_ok=True)
    run_root = results_root / tag
    run_root.mkdir(parents=True, exist_ok=True)
    # Phase 0 observability: one llm_calls.jsonl sidecar per run/tag.
    llm_obs.activate(
        run_root / "llm_calls.jsonl",
        runner="evidence_eqpa", tag=tag, bench=bench,
    )
    out_path = results_root / f"{tag}_traces.jsonl"
    summary_path = results_root / f"{tag}_summary.json"

    manifest = {
        "split": split,
        "case_ids": ids,
        "protocol_sha256": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()[:16],
        "llm_endpoint": official_chat_url(),
        "model": config.MODEL,
        "decoding_temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "thinking_mode": "disabled",
        "system_prompt": bcfg.BATCH_SYSTEM,
        "batch": bcfg.batch_frozen_constants(),
        "config_hashes": bcfg.config_hashes(),
        "grader_runtime": require_grader_python(),
        "generation_guard": generation_guard_record("detect"),
        "note": (
            "Evidence-EQPA: BatchProbe replaces per-command Shell; planning/"
            "progress flags recorded in batch{}; protocol otherwise identical "
            "to e4_eqpa_40960 (T=0.6, 40960, conda-qhe grading, 3 official shots)."
        ),
    }
    mpath = run_root / f"{tag}_manifest.json"
    if mpath.is_file() and out_path.is_file() and out_path.read_text(encoding="utf-8").strip():
        old_m = json.loads(mpath.read_text(encoding="utf-8"))
        for key in ("decoding_temperature", "max_tokens"):
            if key in old_m and old_m[key] != manifest[key]:
                raise SystemExit(
                    f"REFUSE: tag {tag} has {key}={old_m[key]}, current pin is "
                    f"{manifest[key]}. Archive the old run or pass a new --tag.")
        old_batch = old_m.get("batch") or {}
        new_batch = manifest["batch"]
        for key in ("planning_enabled", "progress_enabled", "max_queries_per_batch"):
            if key in old_batch and old_batch[key] != new_batch[key]:
                raise SystemExit(
                    f"REFUSE: tag {tag} was run with batch.{key}={old_batch[key]}, "
                    f"current is {new_batch[key]}. Archive or use a new --tag.")
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    done: set[str] = set()
    if out_path.is_file():
        rows, _ = load_traces(out_path)
        for row in rows:
            if row.get("arm") == bcfg.ARM_NAME and row.get("pass_fail") in {"PASS", "FAIL"}:
                done.add(row["case_id"])
    pending = [c for c in ids if c not in done]
    n_workers = _clamp_workers(workers, len(pending))
    print(f"[evidence_eqpa] tag={tag} bench={bench} split={split} "
          f"n={len(ids)} pending={len(pending)} workers={n_workers} "
          f"planning={bcfg.PLANNING_ENABLED} progress={bcfg.PROGRESS_ENABLED}")

    def _one(cid: str) -> dict[str, Any]:
        # Phase 0 observability: one ledger episode per agent episode.
        with llm_obs.episode_context(method="batch_eqpa", task_id=cid, bench=bench) as ep:
            row = ev_loop.run_evidence_eqpa(cid, _thread_client(), tag=tag, bench=bench)
            ep.record_outcome(
                success=(row.get("pass_fail") == "PASS"),
                iterations=row.get("official_attempts"),
                llm_calls_reported=row.get("llm_calls"),
            )
            return row

    errors = 0
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futs = {pool.submit(_one, cid): cid for cid in pending}
        for fut in as_completed(futs):
            cid = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001
                errors += 1
                print(f"[job_error] {cid}: {type(exc).__name__}: {exc}")
                continue
            with _io_lock:
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

    rows, _ = load_traces(out_path)
    scoped = [r for r in rows if r.get("arm") == bcfg.ARM_NAME and r.get("case_id") in set(ids)]
    n_pass = sum(1 for r in scoped if r.get("passed"))
    p1 = sum(1 for r in scoped if _pass_at_1(r))
    p2 = sum(1 for r in scoped if any(s.get("k", 9) <= 2 and s.get("passed") for s in r.get("shots") or []))
    canary = sum(
        len(scan_text("\n".join([r.get("parsed_code") or "", r.get("error_message") or "",
                                 *(str(t.get("text") or "") for t in r.get("tool_log") or [])])))
        for r in scoped)
    n = max(len(scoped), 1)
    summary = {
        "tag": tag, "arm": bcfg.ARM_NAME, "benchmark": bench, "split": split,
        "n": len(scoped),
        "pass": n_pass, "pass_rate": round(n_pass / n, 4),
        "pass_at_1": p1, "pass_at_2": p2, "pass_at_3": n_pass,
        "avg_llm_calls": round(sum(r.get("llm_calls", 0) for r in scoped) / n, 2),
        "avg_tool_rounds": round(sum(r.get("tool_rounds", 0) for r in scoped) / n, 2),
        "avg_probe_queries": round(sum(r.get("probe_queries", 0) for r in scoped) / n, 2),
        "avg_batch": round(sum(r.get("avg_batch", 0) for r in scoped) / n, 2),
        "avg_evidence_chars": round(sum(r.get("evidence_chars", 0) for r in scoped) / n, 2),
        "avg_prompt_tokens": round(sum(r.get("prompt_tokens", 0) for r in scoped) / n, 2),
        "avg_completion_tokens": round(sum(r.get("completion_tokens", 0) for r in scoped) / n, 2),
        "total_llm_calls": sum(r.get("llm_calls", 0) for r in scoped),
        "canary_hits": canary,
        "job_errors": errors,
        "plan_injections": sum(r.get("plan_injections", 0) for r in scoped),
        "replan_injections": sum(r.get("replan_injections", 0) for r in scoped),
        "planning_enabled": bcfg.PLANNING_ENABLED,
        "progress_enabled": bcfg.PROGRESS_ENABLED,
        "llm": {"model": config.MODEL, "workers": n_workers,
                "decoding_temperature": config.TEMPERATURE, "max_tokens": config.MAX_TOKENS},
        "manifest": str(mpath),
        "traces": str(out_path),
        "note": manifest["note"],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    # Phase 0 observability: run-level cost summary (GATE 3/4 cost fields).
    llm_obs.write_cost_summary()
    print(json.dumps({k: v for k, v in summary.items() if k not in ("case_ids",)}, ensure_ascii=False, indent=1))
    return summary


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--cohort", action="store_true")
    ap.add_argument("--bench", default="qhe")
    ap.add_argument("--cases", nargs="*", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--planning", action="store_true")
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args()
    run_evidence(dev=args.dev, cohort=args.cohort, case_ids=args.cases, tag=args.tag,
                 workers=args.workers, bench=args.bench,
                 planning=args.planning, progress=args.progress)


if __name__ == "__main__":
    main()
