"""Full-trace extraction regression harness (no LLM, no grading).

Replays every assistant turn archived in docs/results/xfix_20260915 through
v1 / v2 / v3 and enforces the contract frozen on 2026-09-17:

  R1  v1 still fails on exactly the 45 historically-empty rows (the v1 gate
      is frozen history; any drift here means parse.py changed behavior).
  R2  v2 recovers ALL of them (xfix baseline).
  R3  v3 is non-empty wherever v2 is non-empty (no regression), and parses
      wherever v2's own extraction parses (rows clipped by the 4000-char
      messages_head cap cannot parse under ANY extractor; v3 must flag them
      parse_ok=False with diagnostics instead of silently grading).
  R4  v2 output is byte-identical to the salvaged parsed_code in the xfix
      ledger for every recovered row (guards against silent parser drift).

Run: /usr/bin/python3 -m exp.common.parse_regress   (from submit/)
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from exp.common.parse import extract_module, extract_module_v2
from exp.common.parse_v3 import extract_module_v3

_XDIR = Path(__file__).resolve().parents[2] / "docs" / "results" / "xfix_20260915"
# v4 archive filenames are frozen history: the first static arm kept its legacy
# name "oneshot" there and must not follow the 2026-10-03 arm rename (zeroshot).
_ARMS = ("oneshot", "cot", "qscot", "rag", "loop")


def _rows() -> list[dict]:
    out = []
    for arm in _ARMS:
        path = _XDIR / f"e4_base_v4_{arm}_traces_xfix.jsonl"
        if not path.is_file():
            print(f"WARN missing {path.name}")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                row["_arm"] = arm
                out.append(row)
    return out


def _last_assistant(messages: list) -> str:
    texts = [m.get("content") or "" for m in messages or [] if m.get("role") == "assistant"]
    return texts[-1] if texts else ""


def main() -> int:
    rows = _rows()
    if not rows:
        print("FAIL no traces found")
        return 1
    v1_empty = 0
    v2_empty = 0
    v3_empty = 0
    v3_parse_fail = 0
    v3_entry_missed = 0
    v2_ledger_mismatch = 0
    v3_v2_same = 0
    v3_nonempty = 0
    clipped_rows = 0
    for row in rows:
        text = _last_assistant(row.get("messages_head"))
        v2_code = extract_module_v2(text)
        v3 = extract_module_v3(text, entry_point=row.get("entry_point"))
        v2_parses = False
        if v2_code:
            try:
                ast.parse(v2_code)
                v2_parses = True
            except SyntaxError:
                clipped_rows += 1
        if not extract_module(text):
            v1_empty += 1
            # R4: v2 must reproduce the xfix salvage byte-for-byte
            if row.get("parsed_code") and v2_code != row["parsed_code"]:
                v2_ledger_mismatch += 1
        if not v2_code:
            v2_empty += 1
        if not v3.code:
            v3_empty += 1
            continue
        v3_nonempty += 1
        if v3.code == v2_code:
            v3_v2_same += 1
        if v2_parses and not v3.parse_ok:
            v3_parse_fail += 1
        # R3 entry-point: only enforce where v2's code defines it
        if v2_parses:
            tree = ast.parse(v2_code)
            v2_defines = any(
                isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.name == row.get("entry_point")
                for n in ast.walk(tree)
            )
            if v2_defines and not v3.defines_entry_point:
                v3_entry_missed += 1

    n = len(rows)
    report = {
        "rows": n,
        "v1_empty": v1_empty,
        "v2_empty": v2_empty,
        "v3_empty": v3_empty,
        "clipped_unparseable_rows": clipped_rows,
        "v3_parse_fail": v3_parse_fail,
        "v3_entry_missed_vs_v2": v3_entry_missed,
        "v2_ledger_mismatch": v2_ledger_mismatch,
        "v3_v2_identical": f"{v3_v2_same}/{v3_nonempty}",
    }
    print(json.dumps(report, indent=1))
    ok = (
        v1_empty == 45
        and v2_empty == 0
        and v3_empty == 0
        and v3_parse_fail == 0
        and v3_entry_missed == 0
        and v2_ledger_mismatch == 0
    )
    print("REGRESSION-PASS" if ok else "REGRESSION-FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
