"""e4 EQPA runner. Dev split is scaffolding only; do not treat as held-out."""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from exp.common.llm import DeepSeekClient, official_chat_url
from exp import config
from exp.eqpa.config import EQPA_DEV_CASES, EQPA_TAG, eqpa_system
from exp.eqpa.bwrap import require_bwrap
from exp.common.canary import ensure_canaries, scan_text
from exp.common.env_guard import (
    require_grader_python,
    require_grader_python_cirq,
    require_grader_python_pennylane,
)
from exp.common.repeat_guard import generation_guard_record
from exp.common.traceio import load_traces
from exp.common import llm_obs
from exp.eqpa import loop as eqpa_loop

_io_lock = threading.Lock()
_tls = threading.local()
PROTOCOL_PATH = Path(__file__).resolve().parent / "eqpa_protocol.md"


def _client(framework: str = "qiskit") -> DeepSeekClient:
    return DeepSeekClient(
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
        disable_thinking=True,
        system=eqpa_system(framework),
        max_retries=3,
    )


def _thread_client(framework: str = "qiskit") -> DeepSeekClient:
    cache = getattr(_tls, "clients", None)
    if cache is None:
        cache = _tls.clients = {}
    client = cache.get(framework)
    if client is None:
        client = _client(framework)
        cache[framework] = client
    return client


def _clamp_workers(n: int | None, pending: int) -> int:
    raw = config.JOB_WORKERS if n is None else int(n)
    cap = min(config.JOB_WORKERS_MAX, config.LLM_CONCURRENCY_LIMIT)
    want = max(1, min(raw, cap))
    return min(want, max(1, pending)) if pending else 1


LEGACY_TAGS = frozenset({
    "e4_eqpa", "e4_eqpa_dev", "e4_eqpa_qbplus", "e4_eqpa_dev_v6", "e4_eqpa_dev_qbplus",
})


def _refuse_legacy_tag(tag: str) -> None:
    """Frozen 4096-era EQPA tags are unwritable (e7 plan, 2026-09-20)."""
    t = (tag or "").strip()
    if t in LEGACY_TAGS or t.startswith("e4_iso"):
        raise SystemExit(
            f"REFUSE: tag {t} is a frozen legacy EQPA result (4096-era, no token "
            "fields). Pass a new --tag (e.g. e4_eqpa_40960[_qbplus][_dev])."
        )


def protocol_sha256() -> str:
    return hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()


def _inspect_ok(row: dict[str, Any], framework: str = "qiskit") -> bool:
    needles = ["importlib", "inspect", "hasattr", "Fake", "qiskit", "dir("]
    fw = (framework or "qiskit").strip().lower()
    if fw == "cirq":
        needles.append("cirq")
    if fw == "pennylane":
        needles.append("pennylane")
    for item in row.get("tool_log") or []:
        if item.get("name") != "Shell":
            continue
        text = item.get("text") or ""
        if any(n.lower() in text.lower() for n in needles) and len(text.strip()) > 20:
            return True
    return False


def _eval_shape_ok(row: dict[str, Any]) -> bool:
    for item in row.get("tool_log") or []:
        if item.get("name") == "Eval":
            return True
    return int(row.get("eval_calls") or 0) > 0 or int(row.get("official_submits") or 0) > 0


def _build_summary(
    *,
    ids: list[str],
    rows: list[dict[str, Any]],
    tag: str,
    out_path: Path,
    n_workers: int,
    n_skipped: int,
    n_errors: int,
    split: str,
    proto_hash: str,
    bench: str = "qhe",
    framework: str = "qiskit",
) -> dict[str, Any]:
    scoped = [r for r in rows if r.get("case_id") in set(ids) and r.get("arm") == "EQPA"]
    n_pass = sum(1 for r in scoped if r.get("passed"))
    n_pass1 = sum(1 for r in scoped if _pass_at_1(r))
    canary = 0
    for r in scoped:
        blob = "\n".join(
            [
                r.get("parsed_code") or "",
                r.get("error_message") or "",
                *(str(t.get("text") or "") for t in (r.get("tool_log") or [])),
            ]
        )
        canary += len(scan_text(blob))
    inspect_n = sum(1 for r in scoped if _inspect_ok(r, framework))
    eval_n = sum(1 for r in scoped if _eval_shape_ok(r))
    gate = {
        "selftest_required": True,
        "eval_returns": eval_n >= 1,
        "inspect_nonempty": inspect_n >= 1,
        "canary_zero": canary == 0,
        "not_all_pass_required": True,
    }
    gate["dev_ok"] = bool(gate["eval_returns"] and gate["inspect_nonempty"] and gate["canary_zero"])
    held = None
    if split == "eval" and bench == "qhe":
        dev = set(EQPA_DEV_CASES)
        held_ids = [i for i in ids if i not in dev]
        held_rows = [r for r in scoped if r.get("case_id") not in dev]
        held_n = len(held_ids)
        held_pass = sum(1 for r in held_rows if r.get("passed"))
        held = {
            "n": held_n,
            "EQPA_pass": held_pass,
            "pass_rate": None if not held_n else round(held_pass / held_n, 4),
            "pass_at_1": sum(1 for r in held_rows if _pass_at_1(r)),
        }
    return {
        "tag": tag,
        "arm": "EQPA",
        "benchmark": bench,
        "framework": framework if bench == "qbplus" else "qiskit",
        "split": split,
        "n": len(ids),
        "case_ids": ids,
        "EQPA_pass": n_pass,
        "pass_at_1": n_pass1,
        "pass_rate": None if not ids else round(n_pass / len(ids), 4),
        "held_out": held,
        "llm": {
            "model": config.MODEL,
            "n_calls": sum(int(r.get("llm_calls") or 0) for r in scoped),
            "workers": n_workers,
            "api_limit": config.LLM_CONCURRENCY_LIMIT,
            "decoding_temperature": config.TEMPERATURE,
            # generation_guard usage accounting (e7, detect-only for EQPA)
            "completion_tokens_estimated_calls": sum(
                1 for r in scoped for c in (r.get("llm_call_log") or [])
                if c.get("completion_tokens_estimated")
            ),
            "degenerate_repeat_calls": sum(
                1 for r in scoped for c in (r.get("llm_call_log") or [])
                if c.get("degenerate_repeat")
            ),
        },
        "shell_calls": sum(int(r.get("shell_calls") or 0) for r in scoped),
        "write_calls": sum(int(r.get("write_calls") or 0) for r in scoped),
        "eval_calls": sum(int(r.get("eval_calls") or 0) for r in scoped),
        "canary_hits": canary,
        "inspect_tasks": inspect_n,
        "eval_shape_tasks": eval_n,
        "gate_dev": gate,
        "traces": str(out_path),
        "protocol": "ctrl_iso_protocol.md",
        "protocol_sha256": proto_hash,
        "tools": ["Shell", "Write", "Eval"],
        "skipped": n_skipped,
        "job_errors": n_errors,
        "note": (
            "dev split is scaffolding; do not treat as held-out. "
            "Dev gate is Eval-shape + inspect + canary=0, not all-pass."
            if split == "dev"
            else "report 143-all and held-out-only for the formal table."
        ),
    }


def _pass_at_1(row: dict[str, Any]) -> bool:
    shots = row.get("shots") or []
    for s in shots:
        if int(s.get("k") or 0) == 1:
            return bool(s.get("passed"))
    return False


def run_eqpa(
    *,
    case_ids: list[str] | None = None,
    dev: bool = True,
    tag: str | None = None,
    workers: int | None = None,
    bench: str = "qhe",
    framework: str = "qiskit",
) -> dict[str, Any]:
    require_bwrap()
    ensure_canaries()
    proto_hash = protocol_sha256()
    bench = (bench or "qhe").strip().lower()
    fw = (framework or "qiskit").strip().lower()
    if fw != "qiskit" and bench != "qbplus":
        raise SystemExit(
            f"REFUSE: --framework {fw} is only defined for --bench qbplus "
            "(QHE local_hard is a qiskit benchmark)."
        )
    if (bench or "qhe").strip().lower() == "qhe":
        from exp.eqpa.env_guard import require_grader_runtime

        require_grader_runtime()
    if case_ids:
        ids = list(case_ids)
        split = "dev" if dev else "eval"
    elif dev:
        ids = list(EQPA_DEV_CASES)
        split = "dev"
    elif bench == "qbplus":
        from exp.common.grader_qbplus import list_ids

        ids = list_ids(fw)
        split = "eval"
    else:
        from exp.common.cases import _qhe_dataset

        ids = sorted(_qhe_dataset().keys())
        split = "eval"
    # e8: cirq runs carry an explicit _cirq tag suffix so the two QB+ framework
    # suites never share a results directory. e9: same for pennylane.
    suffix = "" if (bench != "qbplus" or fw == "qiskit") else f"_{fw}"
    if tag:
        _refuse_legacy_tag(tag)
    elif dev:
        # e7 protocol tags (2026-09-20): budget visible in the tag, legacy
        # e4_eqpa* tags (4096-era, no token fields) stay frozen.
        tag = f"e4_eqpa_40960_dev_qbplus{suffix}" if bench == "qbplus" else "e4_eqpa_40960_dev"
    elif bench == "qbplus":
        tag = f"e4_eqpa_40960_qbplus{suffix}"
    else:
        tag = "e4_eqpa_40960"
    results_root = config.arm_results("eqpa")
    results_root.mkdir(parents=True, exist_ok=True)
    iso_root = results_root / tag
    iso_root.mkdir(parents=True, exist_ok=True)
    # Phase 0 observability: one llm_calls.jsonl sidecar per run/tag.
    llm_obs.activate(
        iso_root / "llm_calls.jsonl",
        runner="eqpa", tag=tag, bench=bench,
    )
    out_path = results_root / f"{tag}_traces.jsonl"
    summary_path = results_root / f"{tag}_summary.json"
    manifest = {
        "split": split,
        "case_ids": ids,
        "protocol_sha256": proto_hash,
        # channel identity recorded like the other arms (was a manifest gap)
        "llm_endpoint": official_chat_url(),
        "model": config.MODEL,
        "decoding_temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "thinking_mode": "disabled",
        # e8: framework identity + the actual system prompt (cirq variant
        # swaps only the framework facts) so the prompt is provable per run.
        "framework": fw if bench == "qbplus" else "qiskit",
        "system_prompt": eqpa_system(fw),
        # e7 P0-7: length-cut turn with no tool call is resampled once
        "length_retry": 1,
        # P0-5: grading runtime recorded in the protocol artifact (was absent
        # in the 4096-era manifests, which left the env unprovable).
        "grader_runtime": (
            require_grader_python_cirq()
            if fw == "cirq"
            else require_grader_python_pennylane()
            if fw == "pennylane"
            else require_grader_python()
        ),
        # e7 generation_guard (2026-09-20): EQPA runs DETECT-ONLY — its client
        # is a direct DeepSeekClient (never make_official_client), so no
        # streaming, no abort, no retry; degenerate text turns are only flagged
        # (`degenerate_repeat`) in llm_call_log. Verdicts unchanged.
        "generation_guard": generation_guard_record("detect"),
        "note": (
            "e7 protocol: scaffolding only, not held-out; T=0.6, max_tokens=40960, "
            "thinking disabled, conda-qhe grading (2026-09-20)"
            if split == "dev"
            else "e7 protocol: formal eval ids; T=0.6, max_tokens=40960, "
                 "thinking disabled, conda-qhe grading (2026-09-20)"
        ),
    }
    mpath = iso_root / f"{tag}_manifest.json"
    if mpath.is_file() and out_path.is_file() and out_path.read_text(encoding="utf-8").strip():
        old_m = json.loads(mpath.read_text(encoding="utf-8"))
        old_t = old_m.get("decoding_temperature")
        if old_t is None:
            old_t = 0.0  # protocols predating the field were T=0 (v5 and earlier)
        if float(old_t) != float(config.TEMPERATURE):
            raise SystemExit(
                f"REFUSE: tag {tag} has decoding_temperature={old_t}, "
                f"current pin is {config.TEMPERATURE}. Archive the old "
                "traces/manifest or pass a new --tag."
            )
        old_mt = old_m.get("max_tokens")
        if old_mt is not None and int(old_mt) != int(config.MAX_TOKENS):
            raise SystemExit(
                f"REFUSE: tag {tag} has max_tokens={old_mt}, "
                f"current pin is {config.MAX_TOKENS}. Archive the old "
                "traces/manifest or pass a new --tag."
            )
        # e7 generation_guard (2026-09-20): refuse mixing client behaviors
        old_gg, new_gg = old_m.get("generation_guard"), manifest.get("generation_guard")
        if old_gg is not None and new_gg is not None and (
            json.dumps(old_gg, sort_keys=True) != json.dumps(new_gg, sort_keys=True)
        ):
            raise SystemExit(
                f"REFUSE: tag {tag} was written under a different generation_guard "
                f"record (old={old_gg.get('mode')}/{old_gg.get('detector')}, "
                f"new={new_gg.get('mode')}/{new_gg.get('detector')}). Archive the "
                "old traces/manifest or pass a new --tag."
            )
    (iso_root / f"{tag}_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (iso_root / "protocol_sha256.txt").write_text(proto_hash + "\n", encoding="utf-8")

    done: set[str] = set()
    rows: list[dict[str, Any]] = []
    if out_path.is_file():
        rows, _removed = load_traces(out_path)  # P0-4: dedup keep-last, file compacted
        for row in rows:
            if row.get("arm") == "EQPA" and row.get("pass_fail") in {"PASS", "FAIL"}:
                done.add(row["case_id"])

    pending = [cid for cid in ids if cid not in done]
    n_workers = _clamp_workers(workers, len(pending))
    print(
        f"{tag} split={split} workers={n_workers} pending={len(pending)} skipped={len(done)} "
        f"protocol={proto_hash[:12]}",
        flush=True,
    )

    errors: list[str] = []
    n_written = 0

    def _one(cid: str) -> dict[str, Any]:
        # Phase 0 observability: one ledger episode per agent episode.
        with llm_obs.episode_context(
            method="EQPA", task_id=cid, bench=bench, framework=fw
        ) as ep:
            row = eqpa_loop.run_eqpa(
                cid, _thread_client(fw), tag=tag, bench=bench, framework=fw
            )
            ep.record_outcome(
                success=(row.get("pass_fail") == "PASS"),
                iterations=row.get("official_attempts"),
                llm_calls_reported=row.get("llm_calls"),
            )
            return row

    if pending:
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futs = {pool.submit(_one, cid): cid for cid in pending}
            for fut in as_completed(futs):
                cid = futs[fut]
                try:
                    row = fut.result()
                except Exception as exc:
                    msg = f"{cid} EQPA: {type(exc).__name__}: {exc}"
                    errors.append(msg)
                    print(f"ERROR {msg}", flush=True)
                    continue
                with _io_lock:
                    rows.append(row)
                    with out_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                    n_written += 1
                    done.add(cid)
                print(
                    f"{row['arm']} {row['case_id']} {row.get('pass_fail')} "
                    f"shots={row.get('official_submits')} llm={row.get('llm_calls')} "
                    f"shell={row.get('shell_calls', 0)} eval={row.get('eval_calls', 0)} "
                    f"canary={row.get('canary_hits', 0)} "
                    f"({n_written}/{len(pending)}) "
                    f"err={(row.get('error_message') or '')[:70]}",
                    flush=True,
                )

    if errors:
        print(f"{tag} job_errors={len(errors)} first={errors[0]}", flush=True)

    summary = _build_summary(
        ids=ids,
        rows=rows,
        tag=tag,
        out_path=out_path,
        n_workers=n_workers,
        n_skipped=len(ids) - len(pending) if not pending else len(done) - n_written,
        n_errors=len(errors),
        split=split,
        proto_hash=proto_hash,
        bench=bench,
        framework=fw,
    )
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    # Phase 0 observability: run-level cost summary (GATE 3/4 cost fields).
    llm_obs.write_cost_summary()
    return {"summary": summary, "rows": rows, "errors": errors}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="e4 EQPA runner (arm=EQPA)")
    ap.add_argument("--bench", default="qhe", choices=["qhe", "qbplus"])
    ap.add_argument("--framework", default="qiskit", help="QB+ framework: qiskit (default), cirq (e8) or pennylane (e9)")
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--cases", nargs="*", default=None, help="explicit case ids")
    ap.add_argument("--tag", default=None, help="explicit result tag")
    args = ap.parse_args()
    out = run_eqpa(
        case_ids=args.cases,
        dev=args.dev,
        tag=args.tag,
        workers=args.workers,
        bench=args.bench,
        framework=args.framework,
    )
    return 1 if out["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
