"""Blind QHE eval: exec assembled program + hidden check. Spawned by
grader_qhe.run_candidate (2026-09-19 grader unification).

Run under the conda qhe interpreter (QHE_PYTHON, qiskit 2.4.1) — the SAME
environment the 2026-09-17 canonical full verification used (README §4:
QHE local_hard 143/143, QB+ 42/42):

    QHE_PYTHON exp/common/eval_qhe.py --program prog.py --entry f --out r.json

Self-contained (stdlib only, no exp imports). Semantics mirror the legacy
in-process grader_qhe._worker byte for byte: exec(program) -> entry point
present -> `check` defined -> check(entry). Result JSON:
{passed, error_type, error_message, traceback}.
"""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Blind QHE eval (one attempt)")
    ap.add_argument("--program", type=Path, required=True)
    ap.add_argument("--entry", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    result: dict[str, str | bool] = {
        "passed": False,
        "error_type": "",
        "error_message": "",
        "traceback": "",
    }
    try:
        program = args.program.read_text(encoding="utf-8")
        ns: dict = {}
        exec(compile(program, "<k0>", "exec"), ns, ns)  # noqa: S102  (grader semantics)
        if args.entry not in ns:
            result = {
                "passed": False,
                "error_type": "MissingEntryPoint",
                "error_message": f'Entry point "{args.entry}" not defined',
                "traceback": "",
            }
        elif "check" not in ns:
            result = {
                "passed": False,
                "error_type": "MissingTest",
                "error_message": 'Test block did not define "check"',
                "traceback": "",
            }
        else:
            ns["check"](ns[args.entry])
            result = {"passed": True, "error_type": "", "error_message": "", "traceback": ""}
    except Exception as exc:  # noqa: BLE001  (same catch set as the legacy worker)
        result = {
            "passed": False,
            "error_type": type(exc).__name__,
            "error_message": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS" if result["passed"] else "FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
