"""Budget & extraction audit over traces jsonl (e7 plan P0-3, 2026-09-20).

Works on OLD (frozen, no finish_reason / token-poor) and NEW (enriched) traces:

- NEW baseline/qspr_v2 shots carry finish_reason + prompt/completion tokens
  per call -> exact per-call cutoff audit.
- NEW eqpa / loop_qspr_rq rows carry `llm_call_log` (per-call finish_reason +
  tokens) -> exact per-call cutoff audit.
- OLD loop_qspr_rq rows carry only task-level token totals -> task-total upper
  bound (task_total >= any single call, so total < cap proves zero cutoffs).
- OLD eqpa rows carry no token fields at all -> audit reports "unprovable".
- OLD baseline/qspr_v2 shots carry tokens but no finish_reason -> cutoff
  inferred from completion_tokens >= cap (exact under an enforced cap).

Usage:
  python3 -m exp.common.audit_budget_extraction TRACES [TRACES ...] \
      [--max-tokens 40960] [--json OUT.json]

Exit code 0 always; the JSON/plain report is the deliverable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ANOMALY_STATUSES = {"invalid_fence", "empty", "not_run"}


def _wilson95(p: float, n: int) -> list[float | None]:
    if n <= 0:
        return [None, None]
    z = 1.959963984540054
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def _pass_at_k(row: dict[str, Any], k: int) -> bool:
    shots = row.get("shots") or []
    if shots and all(("k" in s) for s in shots if isinstance(s, dict)):
        return any(
            int(s.get("k") or 0) <= k and s.get("passed")
            for s in shots
            if isinstance(s, dict)
        )
    return bool(row.get("passed"))


def audit_file(path: Path, *, max_tokens: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    warn_band = 0.95 * max_tokens
    calls_total = 0
    cuts = 0
    over_cap = 0
    warn_band_hits = 0
    # generation_guard (e7 2026-09-20) three-way call classification — a call
    # is exactly one of api_cut / client_guard / natural. Guard stops
    # (finish_reason=client_repeat_stop) are NEVER counted as API truncation.
    api_cut_calls = 0
    client_guard_calls = 0
    natural_calls = 0
    guard_fired_cases: dict[str, dict[str, Any]] = {}
    estimated_usage_calls = 0
    finish_dist: dict[str, int] = {}
    affected: dict[str, dict[str, Any]] = {}
    rows_without_call_audit = 0
    token_unprovable = 0
    completion_tokens_total = 0
    max_call_tokens = 0
    max_task_tokens = 0

    ext_dist: dict[str, int] = {}
    ext_anomalies = 0
    anomaly_cases: dict[str, list[str]] = {}
    recovered_n = 0

    for row in rows:
        cid = str(row.get("case_id"))
        row_cut = False
        row_guard = False
        shots = [s for s in row.get("shots") or [] if isinstance(s, dict)]
        call_log = row.get("llm_call_log") or []

        if call_log:  # NEW eqpa / loop_qspr_rq: exact per-call
            for c in call_log:
                calls_total += 1
                fr = str(c.get("finish_reason") or "unknown")
                ct = int(c.get("completion_tokens") or 0)
                finish_dist[fr] = finish_dist.get(fr, 0) + 1
                completion_tokens_total += ct
                max_call_tokens = max(max_call_tokens, ct)
                if c.get("completion_tokens_estimated"):
                    estimated_usage_calls += 1
                if c.get("degenerate_repeat") or fr == "client_repeat_stop":
                    client_guard_calls += 1
                    guard_fired_cases.setdefault(cid, {"case_passed": bool(row.get("passed")),
                                                       "pass_fail": row.get("pass_fail")})
                    row_guard = True
                elif fr == "length" or ct >= max_tokens:
                    api_cut_calls += 1
                    cuts += 1
                    row_cut = True
                else:
                    natural_calls += 1
                if ct >= max_tokens:
                    over_cap += 1
                if ct >= warn_band:
                    warn_band_hits += 1

        if shots and any(("completion_tokens" in s) for s in shots):
            # baseline / qspr_v2 style: per-call tokens in shots
            for s in shots:
                calls_total += 1
                fr = str(s.get("finish_reason") or "")
                ct = int(s.get("completion_tokens") or 0)
                if fr:
                    finish_dist[fr] = finish_dist.get(fr, 0) + 1
                completion_tokens_total += ct
                max_call_tokens = max(max_call_tokens, ct)
                if s.get("completion_tokens_estimated") or (
                    isinstance(s.get("p1_usage"), dict) and s["p1_usage"].get("completion_tokens_estimated")
                ):
                    estimated_usage_calls += 1
                rg = s.get("repeat_guard") or {}
                guard_hit = fr == "client_repeat_stop" or (
                    isinstance(rg, dict) and rg.get("fired")
                ) or bool(s.get("repeat_guard_fired"))
                if guard_hit:
                    client_guard_calls += 1
                    row_guard = True
                    guard_fired_cases.setdefault(cid, {"case_passed": bool(row.get("passed")),
                                                       "pass_fail": row.get("pass_fail")})
                elif fr == "length" or ct >= max_tokens:
                    api_cut_calls += 1
                    cuts += 1
                    row_cut = True
                else:
                    natural_calls += 1
                if ct >= max_tokens:
                    over_cap += 1
                if ct >= warn_band:
                    warn_band_hits += 1
                st = str(s.get("extraction_status") or "")
                if st:
                    ext_dist[st] = ext_dist.get(st, 0) + 1
                    if st in ANOMALY_STATUSES:
                        ext_anomalies += 1
                        anomaly_cases.setdefault(st, []).append(cid)
                    elif st == "recovered":
                        recovered_n += 1
                    elif st == "ok" and not int(s.get("code_chars") or 0):
                        ext_dist["ok_but_code_empty_suspect"] = (
                            ext_dist.get("ok_but_code_empty_suspect", 0) + 1
                        )
                        ext_anomalies += 1
                        anomaly_cases.setdefault("ok_but_code_empty_suspect", []).append(cid)
        elif call_log:
            pass  # already counted above; extraction via shots below if present
        elif row.get("completion_tokens") is not None:
            # OLD loop_qspr_rq style: task-total upper bound only
            rows_without_call_audit += 1
            tt = int(row.get("completion_tokens") or 0)
            max_task_tokens = max(max_task_tokens, tt)
            completion_tokens_total += tt
        else:
            # OLD eqpa style: no token evidence at all
            rows_without_call_audit += 1
            token_unprovable += 1

        # extraction signals for call_log-style rows (eqpa / rq)
        if not shots or not any(("completion_tokens" in s) for s in shots):
            for s in shots:
                st = str(s.get("extraction_status") or "")
                if st:
                    ext_dist[st] = ext_dist.get(st, 0) + 1
                    if st in ANOMALY_STATUSES:
                        ext_anomalies += 1
                        anomaly_cases.setdefault(st, []).append(cid)
            if not shots:
                # eqpa: shots minimal (no extraction_status) — use error types
                et = str(row.get("error_type") or "")
                if et:
                    ext_dist[f"row_error:{et}"] = ext_dist.get(f"row_error:{et}", 0) + 1
                if row.get("fallback"):
                    ext_dist["row_fallback_parse"] = ext_dist.get("row_fallback_parse", 0) + 1
            rep = row.get("qspr_loop_qspr_rq") or {}
            if rep.get("repair_extraction_failed"):
                ext_anomalies += int(rep.get("repair_extraction_failed") or 0)
                anomaly_cases.setdefault("repair_extraction_failed", []).append(cid)

        if row_cut:
            affected[cid] = {"case_passed": bool(row.get("passed")),
                             "pass_fail": row.get("pass_fail")}

    scoped = [r for r in rows if r.get("pass_fail") in {"PASS", "FAIL"}]
    n_cases = len(scoped)
    n_pass = sum(1 for r in scoped if r.get("passed"))
    max_k = 1
    for r in scoped:
        for s in r.get("shots") or []:
            if isinstance(s, dict) and s.get("k"):
                max_k = max(max_k, int(s["k"]))

    if rows_without_call_audit and calls_total == 0:
        flavor = "task_total_bound" if max_task_tokens else "token_unprovable"
    elif rows_without_call_audit:
        flavor = "mixed_per_call_and_task_total"
    else:
        flavor = "per_call"

    return {
        "traces": str(path),
        "tag": (rows[0].get("tag") if rows else None) or path.stem.replace("_traces", ""),
        "arm": rows[0].get("arm") if rows else None,
        "benchmark": rows[0].get("benchmark") if rows else None,
        "flavor": flavor,
        "max_tokens": max_tokens,
        "cases": n_cases,
        "pass": n_pass,
        "pass_rate": round(n_pass / n_cases, 4) if n_cases else None,
        "pass_rate_wilson95": _wilson95(n_pass / n_cases, n_cases) if n_cases else [None, None],
        **{
            f"pass_at_{j}": sum(1 for r in scoped if _pass_at_k(r, j))
            for j in range(1, max_k + 1)
        },
        "calls_total": calls_total,
        "calls_finish_reason_dist": finish_dist,
        "calls_finish_reason_length": sum(
            v for k_, v in finish_dist.items() if k_ == "length"
        ),
        "calls_completion_over_cap": over_cap,
        "calls_over_warn_band_95pct": warn_band_hits,
        "cut_calls_total": cuts,
        "cut_cases": sorted(affected),
        "cut_case_details": affected,
        # generation_guard three-way split (mutually exclusive, sums to calls_total
        # where per-call data exists): client_repeat_stop is NOT an API cut
        "api_cut_rate": round(api_cut_calls / calls_total, 6) if calls_total else None,
        "client_guard_rate": round(client_guard_calls / calls_total, 6) if calls_total else None,
        "natural_finish_rate": round(natural_calls / calls_total, 6) if calls_total else None,
        "api_cut_calls": api_cut_calls,
        "client_guard_calls": client_guard_calls,
        "natural_calls": natural_calls,
        "client_guard_cases": sorted(guard_fired_cases),
        "client_guard_case_details": guard_fired_cases,
        "estimated_usage_calls": estimated_usage_calls,
        "completion_tokens_sum_seen": completion_tokens_total,
        "max_call_completion_tokens": max_call_tokens,
        "max_task_completion_tokens": max_task_tokens,
        "rows_without_call_audit": rows_without_call_audit,
        "token_unprovable_rows": token_unprovable,
        "extraction_status_dist": ext_dist,
        "extraction_anomalies": ext_anomalies,
        "extraction_anomaly_cases": {
            k_: sorted(set(v))[:50] for k_, v in sorted(anomaly_cases.items())
        },
        "extraction_recovered_used": recovered_n,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("traces", nargs="+", help="traces .jsonl paths")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="budget cap (default: exp.config.MAX_TOKENS)")
    ap.add_argument("--json", dest="json_out", default=None, help="write JSON report here")
    args = ap.parse_args()

    from exp import config

    max_tokens = int(args.max_tokens or config.MAX_TOKENS)
    reports = [audit_file(Path(p), max_tokens=max_tokens) for p in args.traces]

    for rep in reports:
        print(f"\n=== {rep['tag']} ({rep['benchmark']}) flavor={rep['flavor']} ===")
        print(
            f"cases={rep['cases']} pass={rep['pass']} ({rep['pass_rate']}) "
            f"wilson95={rep['pass_rate_wilson95']} "
            f"pass@1..{len([k for k in rep if k.startswith('pass_at_')])}="
            f"{[rep[k] for k in sorted(rep) if k.startswith('pass_at_')]}"
        )
        print(
            f"calls={rep['calls_total']} finish_dist={rep['calls_finish_reason_dist']} "
            f"cut_calls={rep['cut_calls_total']} over_cap={rep['calls_completion_over_cap']} "
            f"warn95={rep['calls_over_warn_band_95pct']}"
        )
        print(
            f"three-way: api_cut={rep['api_cut_calls']} ({rep['api_cut_rate']}) "
            f"client_guard={rep['client_guard_calls']} ({rep['client_guard_rate']}) "
            f"natural={rep['natural_calls']} ({rep['natural_finish_rate']}) "
            f"estimated_usage_calls={rep['estimated_usage_calls']}"
        )
        if rep["client_guard_cases"]:
            print(f"client_guard_cases={rep['client_guard_cases']}")
        if rep["flavor"] in {"task_total_bound", "mixed_per_call_and_task_total"}:
            print(
                f"task_total_bound: max_task_completion_tokens={rep['max_task_completion_tokens']} "
                f"(total < cap => zero cutoffs provable); rows_without_call_audit="
                f"{rep['rows_without_call_audit']}"
            )
        if rep["token_unprovable_rows"]:
            print(
                f"WARNING: {rep['token_unprovable_rows']} rows carry no token fields "
                "(frozen 4096-era EQPA) — cutoff status unprovable from traces"
            )
        print(f"max_call_completion_tokens={rep['max_call_completion_tokens']}")
        print(f"extraction_status_dist={rep['extraction_status_dist']}")
        print(f"extraction_anomalies={rep['extraction_anomalies']} by_case={rep['extraction_anomaly_cases']}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nJSON report -> {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
