"""loop_cot baseline arm entry: adaptive EFx3 loop with a cot first shot.
Rounds 2-3 are the standard typed-error feedback rounds, unchanged.
Run from submit/: python3 -m exp.loop_cot.run"""

from __future__ import annotations

import argparse

from exp.common.baseline.runner import run_e4_base

ARM = "loop_cot"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=f"loop_cot arm (v6: loop EFx3, cot first shot, no system prompt)"
    )
    ap.add_argument("--bench", default="qhe", choices=["qhe", "qbplus"])
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--cases", nargs="*", default=None, help="explicit case ids")
    args = ap.parse_args()
    out = run_e4_base(
        arm=ARM,
        bench=args.bench,
        dev=args.dev,
        workers=args.workers,
        case_ids=args.cases,
    )
    return 1 if out["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
