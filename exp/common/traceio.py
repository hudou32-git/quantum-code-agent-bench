"""Shared traces-jsonl hygiene (2026-09-20, e7 plan P0-4).

Resume-append produced duplicate case rows once already (e6_loop_qspr_rq_qbplus
case `24` carried two identical FAIL lines). Every runner now funnels its
startup load through load_traces(): duplicates are collapsed keep-last and the
file is rewritten compacted before any new append, so a tag's traces jsonl
never carries more than one row per case_id.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_traces(path: Path, *, key: str = "case_id") -> tuple[list[dict[str, Any]], int]:
    """Load a traces jsonl, dedup keep-last per `key`, rewrite the file compacted.

    Returns (rows, n_duplicates_removed). Missing/empty file → ([], 0).
    """
    path = Path(path)
    if not path.is_file():
        return [], 0
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"WARN {path.name}: skipping corrupt line", flush=True)
    seen: dict[Any, int] = {}
    for i, row in enumerate(rows):
        seen[row.get(key)] = i  # last occurrence wins
    if len(seen) == len(rows):
        return rows, 0
    kept = [rows[i] for i in sorted(seen.values())]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    os.replace(tmp, path)
    print(
        f"DEDUP {path.name}: removed {len(rows) - len(kept)} duplicate "
        f"{key} row(s), kept last occurrence",
        flush=True,
    )
    return kept, len(rows) - len(kept)
