"""pass@k report from v6 passk traces (read-only).

pass@k per problem uses the unbiased estimator (Codex/HumanEval form):
    pass@k = 1 - C(n-c, k) / C(n, k)
with n = samples per problem (default 3) and c = passing samples.
The reported number is the mean over problems. Run:
    python3 -m exp.common.baseline.passk_report --bench qhe
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def unbiased_pass_at_k(n: int, c: int, k: int) -> float:
    if n - c < k:
        return 1.0
    return 1.0 - math.prod((n - c - i) / (n - i) for i in range(k))


def load_latest(arm: str, bench: str = "qhe", tag_suffix: str = "") -> dict[str, dict]:
    from exp.config import arm_results

    # loop family (adaptive EFx3) lives under e4_base_v6_<arm>; passk arms
    # carry the sample count in the tag.
    if arm.startswith("loop"):
        tag = f"e4_base_v6_{arm}{tag_suffix}"
    else:
        tag = f"e4_base_v6_passk3_{arm}{tag_suffix}"
    if bench == "qbplus":
        tag = f"{tag}_qbplus"
    path = arm_results(arm) / f"{tag}_traces.jsonl"
    if not path.is_file():
        return {}
    latest: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("arm") == arm.upper() and r.get("pass_fail") in {"PASS", "FAIL"}:
            latest[str(r["case_id"])] = r
    return latest


def report_arm(arm: str, bench: str = "qhe", n_samples: int = 3) -> dict | None:
    latest = load_latest(arm, bench=bench)
    if not latest:
        return None
    cs: list[int] = []
    ext: dict[str, int] = {}
    first_shot_pass = 0
    for cid in sorted(latest):
        r = latest[cid]
        shots = r.get("shots") or []
        c = sum(1 for s in shots if s.get("passed"))
        cs.append(c)
        if shots and shots[0].get("passed"):
            first_shot_pass += 1
        for s in shots:
            key = str(s.get("extraction_status") or "unknown")
            ext[key] = ext.get(key, 0) + 1
    n = len(cs)
    out: dict = {
        "arm": arm,
        "n_problems": n,
        "n_samples": n_samples,
        "pass@1": round(sum(unbiased_pass_at_k(n_samples, c, 1) for c in cs) / n, 4),
        "pass@2": round(sum(unbiased_pass_at_k(n_samples, c, 2) for c in cs) / n, 4),
        "pass@3": round(sum(unbiased_pass_at_k(n_samples, c, 3) for c in cs) / n, 4),
        "anypass_count": sum(1 for c in cs if c > 0),
        "first_shot_pass": first_shot_pass,
        "total_samples_passed": sum(cs),
        "extraction_status_dist": ext,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--arms",
        nargs="*",
        default=[
            "oneshot",
            "cot",
            "qscot",
            "rag",
            "loop",
            "loop_cot",
            "loop_qscot",
            "loop_rag",
        ],
    )
    ap.add_argument("--bench", default="qhe", choices=["qhe", "qbplus"])
    ap.add_argument("--n", type=int, default=3, help="samples per problem in the estimator")
    args = ap.parse_args()
    table = []
    for arm in args.arms:
        r = report_arm(arm, bench=args.bench, n_samples=args.n)
        if r:
            table.append(r)
            print(
                f"{arm:>8}: n={r['n_problems']:>3}  "
                f"pass@1={r['pass@1']:.4f}  pass@2={r['pass@2']:.4f}  "
                f"pass@3={r['pass@3']:.4f}  "
                f"(anypass {r['anypass_count']}/{r['n_problems']}, "
                f"first-shot {r['first_shot_pass']}/{r['n_problems']}, "
                f"samples-passed {r['total_samples_passed']}/{r['n_problems'] * r['n_samples']})",
                flush=True,
            )
            print(f"          extraction_status_dist={r['extraction_status_dist']}", flush=True)
        else:
            print(f"{arm:>8}: no v6 passk traces yet", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
