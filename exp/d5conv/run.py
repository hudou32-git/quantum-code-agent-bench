"""D5 (d5conv) runner: d4shell + A1 + A2 + B1 + B2 over the free-form Shell.

Mirrors exp.d4shell.run (resume-safe, manifest+protocol recording, Phase 0
observability wiring) with the d5_conv identity and the D5 deviation record.
Writes only rq4_d5conv* tags. Frozen design: docs/protocols/d5conv_design_20261001.md.
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
from exp.common.llm import DeepSeekClient, official_chat_url
from exp.common import llm_obs
from exp.common.repeat_guard import generation_guard_record
from exp.common.traceio import load_traces
from exp.eqpa.bwrap import require_bwrap
from exp.eqpa.env_guard import require_grader_runtime
from exp.d5conv import config as dcfg
from exp.d5conv import loop as d_loop
from exp.fcea.utility import prior as uprior

_io_lock = threading.Lock()
_tls = threading.local()
PROTOCOL_PATH = Path(__file__).resolve().parents[2] / "analysis/rq4_fcea/qhe_evidence_utility_prior.json"


def _client() -> DeepSeekClient:
    # D5-6: streaming transport (SSE) for all calls including tool calls.
    # The read timeout becomes an inter-chunk stall detector instead of a
    # total-generation wall (fixes the 2026-10-01 case-26 ReadTimeout hole:
    # 3 x 600s exhausted on one 40960-token Write). Guard stays "detect" —
    # behavior-identical sampling, transport robustness only.
    return DeepSeekClient(
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
        disable_thinking=True,
        system=dcfg.D5_SYSTEM,
        max_retries=3,
        stream=True,
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


def run_d5_split(
    *,
    case_ids: list[str] | None = None,
    dev: bool = False,
    tag: str | None = None,
    workers: int | None = None,
    bench: str = "qbplus",
) -> dict[str, Any]:
    require_bwrap()
    ensure_canaries()
    bench = (bench or "qbplus").strip().lower()
    if bench == "qhe":
        require_grader_runtime()
    if case_ids:
        ids = list(case_ids)
        split = "dev" if dev else "eval"
    elif dev:
        ids = list(dcfg.EQPA_DEV_CASES)
        split = "dev"
    elif bench == "qbplus":
        from exp.common.grader_qbplus import list_ids

        ids = list_ids("qiskit")
        split = "eval"
    else:
        from exp.common.cases import _qhe_dataset

        ids = sorted(_qhe_dataset().keys())
        split = "eval"
    tag = tag or dcfg.default_tag(bench=bench, dev=dev)
    dcfg.refuse_foreign_tag(tag)
    results_root = config.arm_results("d5conv")
    results_root.mkdir(parents=True, exist_ok=True)
    run_root = results_root / tag
    run_root.mkdir(parents=True, exist_ok=True)
    llm_obs.activate(
        run_root / "llm_calls.jsonl",
        runner="d5_conv", tag=tag, bench=bench, variant="d5_conv",
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
        "system_prompt": dcfg.D5_SYSTEM,
        "variant": "d5_conv",
        "batch": dcfg.batch_frozen_constants(),
        "prior": uprior.provenance(),
        "prior_sha256": uprior.prior_sha256(),
        "config_hashes": dcfg.config_hashes(),
        "grader_runtime": require_grader_python(),
        "generation_guard": generation_guard_record("detect"),
        "d5_deviation": dcfg.d5_deviation_record(),
        "note": (
            "D5 (d5conv): frozen d4shell plus four conversion mechanisms — "
            "A1 shell hard budget, A2 deadline ladder (Shell removed from "
            "tools from call 15 of any shot without an official eval), "
            "B1 corrective length retry, B2 fallback artifact gate "
            "(frozen preflight, fail-open). DEU stack, prompt, budgets "
            "(16/8/3), T=0.6, MAX_TOKENS=40960 and the termination protocol "
            "are unchanged; NoSubmit accounting unchanged (A3/A4/B3/B4 not "
            "adopted this round). Design: "
            "docs/protocols/d5conv_design_20261001.md."
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
        if old_m.get("variant") != manifest["variant"]:
            raise SystemExit(
                f"REFUSE: tag {tag} was run with variant={old_m.get('variant')}, "
                "current is d5_conv. Use a different tag.")
        if old_m.get("prior_sha256") != manifest["prior_sha256"]:
            raise SystemExit(
                f"REFUSE: tag {tag} was run with prior sha {old_m.get('prior_sha256')}, "
                "current prior differs. The prior is frozen; use a new --tag.")
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    done: set[str] = set()
    if out_path.is_file():
        rows, _ = load_traces(out_path)
        for row in rows:
            if row.get("arm") == dcfg.ARM_NAME and row.get("pass_fail") in {"PASS", "FAIL"}:
                done.add(row["case_id"])
    pending = [c for c in ids if c not in done]
    n_workers = _clamp_workers(workers, len(pending))
    print(f"[d5conv] tag={tag} bench={bench} split={split} n={len(ids)} "
          f"pending={len(pending)} workers={n_workers} "
          f"prior={manifest['prior_sha256'][:12]}")

    def _one(cid: str) -> dict[str, Any]:
        with llm_obs.episode_context(method="d5_conv", task_id=cid, bench=bench) as ep:
            row = d_loop.run_d5(cid, _thread_client(), tag=tag, bench=bench)
            ep.record_outcome(
                success=(row.get("pass_fail") == "PASS"),
                iterations=row.get("official_submits"),
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
    scoped = [r for r in rows if r.get("arm") == dcfg.ARM_NAME and r.get("case_id") in set(ids)]

    def _field(name: str) -> int:
        return sum(int(r.get(name) or 0) for r in scoped)

    n_pass = sum(1 for r in scoped if r.get("passed"))
    p1 = sum(1 for r in scoped if _pass_at_1(r))
    ns_shots = sum(1 for r in scoped for s in (r.get("shots") or [])
                   if (s.get("error_message") or "").startswith("no official submit"))
    len_cuts = sum(1 for r in scoped for c in (r.get("llm_call_log") or [])
                   if c.get("length_cut_no_tool"))
    len_double = sum(1 for r in scoped for c in (r.get("llm_call_log") or [])
                     if c.get("length_retry") and c.get("finish_reason") == "length")
    canary = sum(
        len(scan_text("\n".join([r.get("parsed_code") or "", r.get("error_message") or "",
                                 *(str(t.get("text") or "") for t in r.get("tool_log") or [])])))
        for r in scoped)
    n = max(len(scoped), 1)
    summary = {
        "tag": tag, "arm": dcfg.ARM_NAME, "variant": "d5_conv",
        "benchmark": bench, "split": split,
        "n": len(scoped),
        "pass": n_pass, "pass_rate": round(n_pass / n, 4),
        "pass_at_1": p1, "pass_at_3": n_pass,
        "avg_llm_calls": round(sum(r.get("llm_calls", 0) for r in scoped) / n, 2),
        "total_llm_calls": sum(r.get("llm_calls", 0) for r in scoped),
        "total_prompt_tokens": sum(r.get("prompt_tokens", 0) for r in scoped),
        "total_completion_tokens": sum(r.get("completion_tokens", 0) for r in scoped),
        "avg_shell_calls": round(sum(r.get("shell_calls", 0) for r in scoped) / n, 2),
        "avg_tool_rounds": round(sum(r.get("shell_rounds", 0) for r in scoped) / n, 2),
        "priority_injections": _field("priority_injections"),
        "failure_events": sum(len(r.get("failure_events") or []) for r in scoped),
        "controller_withdrawn_episodes": sum(
            1 for r in scoped if r.get("controller_shell_withdrawn_final")),
        "canary_hits": canary,
        "job_errors": errors,
        # D5 gates (design doc §11): G1/G2/G3 read directly from here
        "nosubmit_shots": ns_shots,
        "length_cut_calls": len_cuts,
        "length_double_cuts": len_double,
        "shell_budget_refusals": _field("shell_budget_refusals"),
        "shell_deadline_refusals": _field("shell_deadline_refusals"),
        "escalate_injections": _field("escalate_injections"),
        "narrowed_shots": _field("narrowed_shots"),
        "retry_corrected": _field("retry_corrected"),
        "artifact_gate_rejects": _field("artifact_gate_rejects"),
        "llm": {"model": config.MODEL, "workers": n_workers,
                "decoding_temperature": config.TEMPERATURE, "max_tokens": config.MAX_TOKENS},
        "prior_sha256": uprior.prior_sha256(),
        "manifest": str(mpath),
        "traces": str(out_path),
        "note": manifest["note"],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    llm_obs.write_cost_summary()
    print(json.dumps({k: v for k, v in summary.items() if k not in ("case_ids",)},
                     ensure_ascii=False, indent=1))
    return summary


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--bench", default="qbplus")
    ap.add_argument("--cases", nargs="*", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    run_d5_split(dev=args.dev, case_ids=args.cases, tag=args.tag, workers=args.workers,
                 bench=args.bench)


if __name__ == "__main__":
    main()
