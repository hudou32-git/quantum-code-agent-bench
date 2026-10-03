"""Repetition-block detector (e7 generation_guard, rep-v1, 2026-09-20).

Execution-level early-abort signal for degenerate sampling loops (T=0.6
block-repetition pathology: e.g. the case-104 4-line block repeated 786x until
the 40960 cap). High-precision by design — fires ONLY when the generation tail
is provably stuck in a loop:

  armed        len(text) >= MIN_ARMED_CHARS
  for b in BLOCK_SIZES (lines per block):
      run(b)   = consecutive repeats of the trailing b-line block
      fire(b)  = run >= max(MIN_RUN, ceil(RUN_CHARS_TARGET / block_chars))
                 AND run*block_chars >= MIN_LOOP_CHARS
                 AND loop covers >= SHARE of the last WINDOW_LINES lines
  trigger      any fire(b)

Legit repetitive code (QFT decompositions, gate ladders, repeated comments)
never satisfies the share+volume pair; the case-104 pathology fires within
~2-3K chars of loop onset (~94% token saving vs burning to the cap).

Pure functions only — no I/O, no config import (usable from stubs/tests).
"""

from __future__ import annotations

from typing import Any

DETECTOR_VERSION = "rep-v1"

PARAMS: dict[str, Any] = {
    "version": DETECTOR_VERSION,
    "min_armed_chars": 3000,
    "block_sizes": [1, 2, 3, 4, 5, 6, 8, 10],
    "min_run": 10,
    "run_chars_target": 1200,
    "min_loop_chars": 2000,
    "window_lines": 200,
    "share": 0.80,
    "check_interval_chars": 1024,
    "max_run_scan": 2000,
}


def generation_guard_record(mode: str) -> dict[str, Any]:
    """Frozen protocol/manifest field (enters protocol_hash). mode: enforce|detect."""
    from exp import config

    gg = config.GENERATION_GUARD
    return {
        "enabled": bool(gg.get("enabled", True)),
        "detector": gg.get("detector", DETECTOR_VERSION),
        "mode": mode,
        "policy": (
            "execution-level early abort; no retry/resample/sampling-budget change; "
            "guard stop keeps the full text and flows into extraction/grading as-is "
            "(finish_reason=client_repeat_stop; never counted as API length cut)"
        ),
        "params": PARAMS,
    }


def should_check(chars_now: int, last_checked: int, params: dict[str, Any] | None = None) -> bool:
    """Incremental cadence: arm after min_armed_chars, then every interval."""
    p = params or PARAMS
    if chars_now < int(p["min_armed_chars"]):
        return False
    return chars_now - last_checked >= int(p["check_interval_chars"])


def detect(text: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return trigger diagnostics dict when degenerate, else None."""
    p = dict(PARAMS if params is None else params)
    if text is None or len(text) < int(p["min_armed_chars"]):
        return None
    lines = text.split("\n")
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    min_run = int(p["min_run"])
    max_run_scan = int(p["max_run_scan"])
    best: dict[str, Any] | None = None
    best_loop_chars = 0
    for b in p["block_sizes"]:
        if end < b * min_run:
            continue
        # a cap/guard cut mid-line shifts the tail block phase: try every
        # alignment offset 0..b-1 (the loop always ends within b lines of EOF)
        for trim in range(b):
            end2 = end - trim
            if end2 < b * min_run:
                continue
            block = [l.strip() for l in lines[end2 - b:end2]]
            if not any(block):
                continue
            block_chars = sum(len(l) for l in lines[end2 - b:end2]) + b
            need = max(min_run, -(-int(p["run_chars_target"]) // max(block_chars, 1)))
            # count consecutive repeats of `block` ending at `end2`
            run = 1
            while (
                run < max_run_scan
                and end2 - (run + 1) * b >= 0
                and [l.strip() for l in lines[end2 - (run + 1) * b:end2 - run * b]] == block
            ):
                run += 1
            if run < need:
                continue
            loop_lines = run * b
            loop_chars = run * block_chars
            if loop_chars < int(p["min_loop_chars"]):
                continue
            win = lines[max(0, end2 - int(p["window_lines"])):end2]
            share = min(1.0, loop_lines / max(len(win), 1))
            if share < float(p["share"]):
                continue
            if loop_chars <= best_loop_chars:
                continue
            best_loop_chars = loop_chars
            best = {
                "fired": True,
                "detector": p.get("version", DETECTOR_VERSION),
                "block_lines": b,
                "run_repeats": run,
                "loop_lines": loop_lines,
                "loop_chars": loop_chars,
                "tail_offset": trim,
                "loop_start_char": sum(len(l) + 1 for l in lines[:end2 - run * b]),
                "checked_chars": len(text),
            }
    return best
