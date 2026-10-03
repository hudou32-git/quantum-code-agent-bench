"""loop baseline arm entry. Run from submit/: python3 -m exp.loop.run"""

from __future__ import annotations

import argparse

from exp.common.baseline.runner import run_e4_base

ARM = "loop"


def main() -> int:
    ap = argparse.ArgumentParser(description=f"loop baseline arm (v5, no system prompt)")
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
