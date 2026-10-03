"""zero-shot baseline arm entry. Run from submit/: python3 -m exp.zeroshot.run"""

from __future__ import annotations

import argparse

from exp.common.baseline.runner import run_e4_base

ARM = "zeroshot"


def main() -> int:
    ap = argparse.ArgumentParser(description=f"zero-shot baseline arm (v6, pass@k, no system prompt)")
    ap.add_argument("--bench", default="qhe", choices=["qhe", "qbplus"])
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--cases", nargs="*", default=None, help="explicit case ids")
    ap.add_argument(
        "--pass-k",
        type=int,
        default=None,
        help="independent samples per problem (default: protocol PASS_K=3); 1 = single shot",
    )
    args = ap.parse_args()
    out = run_e4_base(
        arm=ARM,
        bench=args.bench,
        dev=args.dev,
        workers=args.workers,
        case_ids=args.cases,
        pass_k=args.pass_k,
    )
    return 1 if out["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
