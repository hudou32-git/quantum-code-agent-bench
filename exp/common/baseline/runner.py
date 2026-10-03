"""Run one v5 baseline arm (or the whole grid). Official API, no system prompt."""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from exp import config
from exp.common.canary import ensure_canaries
from exp.common.repeat_guard import generation_guard_record
from exp.common.traceio import load_traces


def _refuse_canon(v: Any) -> str:
    """Order-insensitive comparison for dict/list protocol fields."""
    return json.dumps(v, sort_keys=True, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v).strip()
from exp.common.baseline.config import (
    ARMS,
    DECODING_TEMPERATURE,
    LLM_PROVIDER,
    MAX_OFFICIAL,
    MODEL,
    MODEL_FAMILY,
    PASSK_ARMS,
    PASS_K,
    PROTOCOL_DOC,
    PROTO_VERSION,
    SINGLE_TURN,
    default_tag,
    normalize_arm,
    normalize_bench,
    refuse_locked_tag,
    require_model,
)
from exp.common.baseline.loop import run_base_task
from exp.common.env_guard import require_grader_python
from exp.common.llm import DeepSeekClient, official_chat_url, make_official_client
from exp.common import llm_obs

_io_lock = threading.Lock()
_tls = threading.local()


def _client(arm: str) -> DeepSeekClient:
    require_model(MODEL)
    c = make_official_client(
        max_tokens=config.MAX_TOKENS,
        temperature=config.TEMPERATURE,
    )
    # Key/URL/model all resolved from .env inside make_official_client;
    # the resolved endpoint is recorded in protocol.json. No channel gating.
    if not (c.url or "").strip():
        raise RuntimeError("REFUSE: chat URL unresolved")
    # v5: no system prompt for any baseline arm.
    c.system = ""
    return c


def _refuse_protocol_mismatch(root: Path, proto: dict[str, Any], out_path: Path) -> None:
    """Do not mix traces from a different protocol pin under one tag."""
    path = root / "protocol.json"
    if not path.is_file():
        return
    if not out_path.is_file() or not out_path.read_text(encoding="utf-8").strip():
        return
    old = json.loads(path.read_text(encoding="utf-8"))
    checks = (
        ("model_identifier", proto.get("model_identifier") or proto.get("model")),
        ("model", proto.get("model_identifier") or proto.get("model")),
        ("llm_provider", proto.get("llm_provider")),
        ("llm_endpoint", proto.get("llm_endpoint")),
        ("system_prompt", proto.get("system_prompt")),
        # decoding pin: protocols predating the field were T=0 (v5 and earlier)
        ("decoding_temperature", proto.get("decoding_temperature")),
        ("pass_k", proto.get("pass_k")),
        # budget/thinking pin: protocols predating these fields were 4096/disabled
        ("max_tokens", proto.get("max_tokens")),
        ("thinking_mode", proto.get("thinking_mode")),
        # e7 P0-7: length-cut resample rule is a frozen protocol dimension
        ("length_retry", proto.get("length_retry")),
        # e7 generation_guard (2026-09-20): refuse tags from a different client
        # behavior — exact protocol hash + guard record must both match
        ("protocol_hash", proto.get("protocol_hash")),
        ("generation_guard", proto.get("generation_guard")),
    )
    for key, want in checks:
        got = old.get(key)
        if got is None and key == "model_identifier":
            got = old.get("model")
        if got is None and key == "decoding_temperature":
            got = 0.0
        if got is None:
            continue
        if _refuse_canon(got) != _refuse_canon(want):
            raise RuntimeError(
                f"REFUSE: tag {root.name} has existing {key}={got!r}, "
                f"runner wants {want!r}. Archive the old traces/protocol "
                "before continuing under the current protocol pin."
            )


def _thread_client(arm: str) -> DeepSeekClient:
    store = getattr(_tls, "clients", None)
    if store is None:
        store = {}
        _tls.clients = store
    c = store.get(arm)
    if c is None:
        c = _client(arm)
        store[arm] = c
    return c


def _clamp_workers(n: int | None, pending: int) -> int:
    raw = 10 if n is None else int(n)
    cap = min(config.JOB_WORKERS_MAX, config.LLM_CONCURRENCY_LIMIT)
    want = max(1, min(raw, cap))
    return min(want, max(1, pending)) if pending else 1


def _pass_at_k(row: dict[str, Any], k: int) -> bool:
    for s in row.get("shots") or []:
        if int(s.get("k") or 0) <= k and s.get("passed"):
            return True
    return False


def _latest_by_case(rows: list[dict[str, Any]], arm: str) -> dict[str, dict[str, Any]]:
    key = arm.upper()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r.get("arm") == key and r.get("pass_fail") in {"PASS", "FAIL"} and r.get("case_id"):
            out[str(r["case_id"])] = r
    return out


def protocol_record(arm: str, *, bench: str, pass_k: int = 1) -> dict[str, Any]:
    a = normalize_arm(arm)
    b = normalize_bench(bench)
    sampling = a in PASSK_ARMS and pass_k > 1
    frozen = {
        "method": f"e4-base-{PROTO_VERSION}-passk" if sampling else f"e4-base-{PROTO_VERSION}",
        "protocol_version": PROTO_VERSION,
        "arm": a,
        "benchmark": b,
        "split": "local_hard" if b == "qhe" else "qbplus_qiskit",
        "tools": [],
        "model_family": MODEL_FAMILY,
        "model_identifier": MODEL,
        "model": MODEL,
        "llm_provider": LLM_PROVIDER,
        "system_prompt": None,
        "decoding_temperature": DECODING_TEMPERATURE,
        "pass_k": pass_k if sampling else 1,
        "sampling_mode": "independent_passk" if sampling else "adaptive_feedback",
        "estimator": "per_problem_any_of_k" if sampling else "per_problem_single_shot",
        "max_attempts": 1 if sampling else (1 if a in SINGLE_TURN else MAX_OFFICIAL),
        "protocol_doc": PROTOCOL_DOC,
        "rag_backend": "RAGFLOW_MULTI_DATASET_SEPARATE" if a in {"rag", "loop_rag"} else None,
        # output budget + thinking pin (2026-09-18): 40960/disabled from now on;
        # historical rows ran 4096 and predate these fields (treated as 4096/disabled).
        "max_tokens": config.MAX_TOKENS,
        "thinking_mode": "disabled",
        # e7 P0-7 (2026-09-20): degenerate length-cut draws with unextractable
        # code are resampled once; both calls stay on the trace.
        "length_retry": 1,
        "length_retry_policy": "resample-once-on-length-cut-unextractable",
        # e7 generation_guard (user resolution 2026-09-20): execution-level
        # early abort on degenerate loops — no retry/resample/budget change.
        "generation_guard": generation_guard_record("enforce"),
    }
    blob = json.dumps(frozen, sort_keys=True, ensure_ascii=False).encode("utf-8")
    rec = dict(frozen)
    rec["protocol_hash"] = hashlib.sha256(blob).hexdigest()
    rec["llm_endpoint"] = official_chat_url()
    rec["grader_runtime"] = require_grader_python()
    return rec


def _wilson95(p: float, n: int) -> list[float]:
    """Wilson score interval at 95% for a binomial proportion."""
    if n <= 0:
        return [None, None]
    z = 1.959963984540054
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def build_summary(
    *,
    ids: list[str],
    rows: list[dict[str, Any]],
    tag: str,
    arm: str,
    bench: str,
    out_path: Path,
    n_workers: int,
    n_skipped: int,
    n_errors: int,
    split: str,
    proto: dict[str, Any],
) -> dict[str, Any]:
    a = normalize_arm(arm)
    by_id = _latest_by_case(rows, a)
    if by_id:
        scoped = list(by_id.values())
        ids_used = sorted(by_id)
        scope = "traces_latest_per_task"
    else:
        scoped = [r for r in rows if r.get("case_id") in set(ids) and r.get("arm") == a.upper()]
        ids_used = list(ids)
        scope = "invocation_ids"
    n_pass = sum(1 for r in scoped if r.get("passed"))
    n = len(ids_used)
    rate = None if not n else round(n_pass / n, 4)
    passk_mode = bool(scoped) and all(int(r.get("pass_k") or 1) > 1 for r in scoped)
    n_samples = int(proto.get("pass_k") or 1)
    # per-sample pass counts and anypass curve over the first j samples
    sample_pass = {
        f"sample_{j}_pass": sum(
            1
            for r in scoped
            for s in (r.get("shots") or [])
            if int(s.get("k") or 0) == j and s.get("passed")
        )
        for j in range(1, max(1, n_samples) + 1)
    }
    pass_curve = {
        f"pass_at_{j}": sum(
            1
            for r in scoped
            if any(
                int(s.get("k") or 0) <= j and s.get("passed")
                for s in (r.get("shots") or [])
            )
        )
        for j in range(1, max(1, n_samples) + 1)
    }
    ext_dist: dict[str, int] = {}
    for r in scoped:
        for s in r.get("shots") or []:
            key = str(s.get("extraction_status") or "unknown")
            ext_dist[key] = ext_dist.get(key, 0) + 1
    # generation_guard usage accounting (e7): estimated token draws must never
    # be mixed with real ones — surfaced here and in the audit
    n_est = sum(
        1 for r in scoped for s in r.get("shots") or []
        if isinstance(s, dict) and s.get("completion_tokens_estimated")
    )
    n_guard = sum(
        1 for r in scoped for s in r.get("shots") or []
        if isinstance(s, dict) and (str(s.get("finish_reason") or "") == "client_repeat_stop"
                                    or (isinstance(s.get("repeat_guard"), dict) and s["repeat_guard"].get("fired")))
    )
    return {
        "tag": tag,
        "arm": a,
        "benchmark": bench,
        "split": split,
        "n": n,
        "case_ids": ids_used,
        "summary_scope": scope,
        "pass": n_pass,
        "pass_rate": rate,
        "pass_rate_wilson95": _wilson95(n_pass / n, n) if n else [None, None],
        "pass_at_1": sum(1 for r in scoped if _pass_at_k(r, 1)),
        "pass_at_2": sum(1 for r in scoped if _pass_at_k(r, 2)),
        "pass_at_3": sum(1 for r in scoped if _pass_at_k(r, 3)),
        "metric": f"pass@{n_samples}" if passk_mode else "pass@1",
        "samples_passed_mean": (
            None if not scoped
            else round(sum(int(r.get("n_samples_passed") or 0) for r in scoped) / len(scoped), 4)
        ),
        **pass_curve,
        **sample_pass,
        "extraction_status_dist": ext_dist,
        "llm": {
            "model": MODEL,
            "model_family": MODEL_FAMILY,
            "n_calls": sum(int(r.get("llm_calls") or 0) for r in scoped),
            "mean_per_task": None
            if not scoped
            else round(sum(int(r.get("llm_calls") or 0) for r in scoped) / len(scoped), 2),
            "prompt_tokens": sum(int(r.get("prompt_tokens") or 0) for r in scoped),
            "completion_tokens": sum(int(r.get("completion_tokens") or 0) for r in scoped),
            "workers": n_workers,
            "decoding_temperature": DECODING_TEMPERATURE,
            "completion_tokens_estimated_calls": n_est,
            "usage_estimated": bool(n_est),
            "client_guard_stops": n_guard,
        },
        "official_attempts": sum(int(r.get("official_attempts") or 0) for r in scoped),
        "canary_hits": sum(int(r.get("canary_hits") or 0) for r in scoped),
        "had_tools": False,
        "max_attempts": proto.get("max_attempts"),
        "traces": str(out_path),
        "protocol": proto,
        "skipped": n_skipped,
        "job_errors": n_errors,
        "note": (
            f"{PROTO_VERSION} baseline: no system prompt, decoding temperature "
            f"{DECODING_TEMPERATURE}, max_tokens={proto.get('max_tokens')}, "
            "thinking disabled, conda-qhe grading, official API. "
            + (
                f"Single-turn arms report pass@{n_samples} "
                "(any of k independent samples; no feedback between samples). "
                "pass = pass@k primary metric; extraction_status failures are "
                "infrastructure failures, check extraction_status_dist before "
                "cross-arm comparison. "
                if passk_mode
                else "Single-turn arms report Pass@1; loop family "
                "(loop, loop_cot, loop_qscot, loop_rag) runs adaptive EF"
                f"x{MAX_OFFICIAL} — loop_X arms change only the first shot's "
                "prompt (byte-identical to arm X), rounds 2-3 are standard "
                "typed-error feedback. "
            )
            + "Do not mix with e4_base_v4/v5 rows (different decoding protocol) or other channels."
        ),
    }


def run_e4_base(
    *,
    arm: str,
    bench: str = "qhe",
    case_ids: list[str] | None = None,
    dev: bool = False,
    tag: str | None = None,
    workers: int | None = None,
    pass_k: int | None = None,
) -> dict[str, Any]:
    from exp.config import arm_results

    ensure_canaries()
    a = normalize_arm(arm)
    b = normalize_bench(bench)
    if a not in ARMS:
        raise ValueError(a)
    # v6: single-turn arms default to pass@3 independent sampling; pass_k=1
    # gives the single-shot schedule under its own passk1 tag.
    n_samples = (PASS_K if pass_k is None else int(pass_k)) if a in PASSK_ARMS else 1
    if n_samples < 1:
        raise ValueError(f"pass_k must be >=1, got {n_samples}")
    if a in {"rag", "loop_rag"}:
        from exp.rag.retrieve import require_ragflow

        require_ragflow()
    grader = require_grader_python()
    proto = protocol_record(a, bench=b, pass_k=n_samples)
    proto["grader_runtime"] = grader
    results_root = arm_results(a)

    if case_ids:
        ids = list(case_ids)
        split = "dev" if dev else "eval"
    elif dev:
        ids = list(config.BASELINE_DEV_CASES) if b == "qhe" else list(config.QBPLUS_SMOKE_CASES)
        split = "dev"
    elif b == "qbplus":
        from exp.common.grader_qbplus import list_ids

        ids = list_ids()
        split = "eval"
    else:
        from exp.common.cases import load_case

        ids = sorted(_qhe_ids())
        split = "eval"

    tag = tag or default_tag(a, bench=b, dev=dev, pass_k=n_samples if a in PASSK_ARMS else None)
    refuse_locked_tag(tag)

    root = results_root / tag
    root.mkdir(parents=True, exist_ok=True)
    # Phase 0 observability: one llm_calls.jsonl sidecar per run/tag.
    llm_obs.activate(
        root / "llm_calls.jsonl",
        runner="e4_base_grid", tag=tag, arm=a, bench=b, split=split,
        pass_k=n_samples,
    )
    out_path = results_root / f"{tag}_traces.jsonl"
    summary_path = results_root / f"{tag}_summary.json"
    _refuse_protocol_mismatch(root, proto, out_path)
    (root / "protocol.json").write_text(
        json.dumps(proto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    done: set[str] = set()
    rows: list[dict[str, Any]] = []
    if out_path.is_file():
        rows, _removed = load_traces(out_path)  # P0-4: dedup keep-last, file compacted
        for row in rows:
            if row.get("arm") == a.upper() and row.get("pass_fail") in {"PASS", "FAIL"}:
                done.add(row["case_id"])

    pending = [cid for cid in ids if cid not in done]
    n_workers = _clamp_workers(workers, len(pending))
    print(
        f"{tag} arm={a} bench={b} split={split} workers={n_workers} "
        f"pending={len(pending)} skipped={len(done)} pass_k={n_samples} "
        f"T={DECODING_TEMPERATURE} "
        f"model={MODEL} provider={LLM_PROVIDER} endpoint={proto.get('llm_endpoint')} "
        f"grader={grader['executable']} qiskit={grader['qiskit']}",
        flush=True,
    )

    errors: list[str] = []
    n_written = 0

    def _one(cid: str) -> dict[str, Any]:
        # Phase 0 observability: one ledger episode per task-run (pass@k arms:
        # the whole task; per-attempt costs stay in the per-shot trace fields).
        with llm_obs.episode_context(method=a, task_id=cid, bench=b) as ep:
            row = run_base_task(
                cid,
                _thread_client(a),
                arm=a,
                bench=b,
                tag=tag,
                results_root=results_root,
                pass_k=n_samples,
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
                except Exception as exc:  # noqa: BLE001
                    msg = f"{cid} {a}: {type(exc).__name__}: {exc}"
                    errors.append(msg)
                    print(f"ERROR {msg}", flush=True)
                    continue
                with _io_lock:
                    rows.append(row)
                    with out_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                    n_written += 1
                    done.add(cid)
                    _write_samples(results_root, tag, row)
                print(
                    f"{row['arm']} {row['case_id']} {row.get('pass_fail')} "
                    f"k={row.get('official_attempts')} llm={row.get('llm_calls')} "
                    f"({n_written}/{len(pending)}) "
                    f"err={(row.get('error_message') or '')[:70]}",
                    flush=True,
                )

    if errors:
        print(f"{tag} job_errors={len(errors)} first={errors[0]}", flush=True)

    summary = build_summary(
        ids=ids,
        rows=rows,
        tag=tag,
        arm=a,
        bench=b,
        out_path=out_path,
        n_workers=n_workers,
        n_skipped=len(ids) - len(pending),
        n_errors=len(errors),
        split=split,
        proto=proto,
    )
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # Phase 0 observability: run-level cost summary (GATE 3/4 cost fields).
    llm_obs.write_cost_summary()
    printable = {k: summary[k] for k in summary if k != "case_ids"}
    print(json.dumps(printable, indent=2, ensure_ascii=False), flush=True)
    return {"summary": summary, "errors": errors, "traces": str(out_path)}


def _safe_case_dir(case_id: str) -> str:
    return "".join("__" if c in '/\\:"<>|*? ' else c for c in str(case_id))


def _write_samples(results_root: Path, tag: str, row: dict[str, Any]) -> None:
    """P0-2: persist every sample's code/raw output + per-call meta to
    results/<tag>/samples/<case_id>/k{n}.{py,raw.txt} + meta.json."""
    shots = [s for s in row.get("shots") or [] if isinstance(s, dict)]
    if not shots:
        return
    out = results_root / tag / "samples" / _safe_case_dir(row.get("case_id") or "")
    out.mkdir(parents=True, exist_ok=True)
    for s in shots:
        k = int(s.get("k") or 0)
        base = out / f"k{k}"
        try:
            if s.get("code"):
                base.with_suffix(".py").write_text(s["code"], encoding="utf-8")
            if s.get("raw_output"):
                (out / f"k{k}.raw.txt").write_text(s["raw_output"], encoding="utf-8")
            meta = {
                kk: s.get(kk)
                for kk in (
                    "k", "passed", "error_type", "error_message", "feedback_kind",
                    "extraction_status", "extraction_recovery", "code_chars",
                    "finish_reason", "prompt_tokens", "completion_tokens",
                )
                if kk in s
            }
            (out / f"k{k}.meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            print(f"WARN samples write failed {out}/k{k}: {exc}", flush=True)


def _qhe_ids() -> list[str]:
    from exp.common.cases import _qhe_dataset

    return list(_qhe_dataset().keys())


def run_e4_base_grid(
    *,
    benches: list[str] | None = None,
    arms: list[str] | None = None,
    dev: bool = False,
    workers: int | None = None,
) -> dict[str, Any]:
    order_b = [normalize_bench(x) for x in (benches or ["qhe", "qbplus"])]
    order_a = [normalize_arm(x) for x in (arms or list(ARMS))]
    results: list[dict[str, Any]] = []
    for bench in order_b:
        for arm in order_a:
            print(f"===== GRID start arm={arm} bench={bench} dev={int(dev)} =====", flush=True)
            try:
                out = run_e4_base(arm=arm, bench=bench, dev=dev, workers=workers)
            except Exception as exc:  # noqa: BLE001
                rec = {
                    "arm": arm,
                    "benchmark": bench,
                    "error": f"{type(exc).__name__}: {exc}",
                    "job_errors": 1,
                }
                results.append(rec)
                print(f"===== GRID fail arm={arm} bench={bench} {rec['error']} =====", flush=True)
                if arm == "rag":
                    print("RAG arm refused; continuing other arms", flush=True)
                    continue
                raise
            s = out["summary"]
            results.append(
                {
                    "arm": arm,
                    "benchmark": bench,
                    "tag": s.get("tag"),
                    "n": s.get("n"),
                    "pass": s.get("pass"),
                    "pass_at_1": s.get("pass_at_1"),
                    "pass_at_3": s.get("pass_at_3"),
                    "llm": (s.get("llm") or {}).get("n_calls"),
                    "job_errors": s.get("job_errors"),
                }
            )
            print(
                f"===== GRID done arm={arm} bench={bench} "
                f"P@1={s.get('pass_at_1')} P@3={s.get('pass_at_3')} "
                f"llm={((s.get('llm') or {}).get('n_calls'))} =====",
                flush=True,
            )
    table = {
        "model": MODEL,
        "model_family": MODEL_FAMILY,
        "llm_provider": LLM_PROVIDER,
        "dev": dev,
        "arms": results,
    }
    path = config.ROOT / "docs" / "results" / (
        f"e4_base_{PROTO_VERSION}_grid_dev_summary.json"
        if dev
        else f"e4_base_{PROTO_VERSION}_grid_summary.json"
    )
    path.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(table, indent=2, ensure_ascii=False), flush=True)
    return table
