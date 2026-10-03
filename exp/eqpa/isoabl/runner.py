"""Runner for the ISO mechanism ablation: smoke + Phase II matched blocks.

Entry: python3 -m exp.eqpa.isoabl.runner <smoke|blocks> [--workers N]

- smoke: dev cases x A/B/C/R, tag e4_isoabl_SMOKE (never enters formal data).
- blocks: frozen mechanism cohort x A/B/C/R in randomized matched blocks;
  resume-safe (completed (task, arm) rows in traces are skipped).

Client wiring: official DeepSeek (make_official_client, deepseek-v4-flash).
Peak windows (operator rule): Beijing Mon-Fri 09:00-12:00, 14:00-18:00 —
launchers must wait for off-peak windows before starting.
"""

from __future__ import annotations

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

from exp.common.llm import make_official_client
from exp import config
from exp.eqpa.config import EQPA_DEV_CASES
from exp.eqpa.isoabl.arms import ARM_NAMES, FROZEN_BUDGETS
from exp.eqpa.isoabl.episode import run_ablation_episode

ART = config.PKG / "eqpa" / "results" / "isoabl"
SMOKE_TAG = "e4_isoabl_SMOKE"
BLOCKS_TAG = "e4_isoabl_qhe"

_io_lock = Lock()


def _make_client():
    # DeepSeekClient is thread-safe per instance for sequential chat_messages;
    # one client per thread avoids shared counters contention.
    # Key/URL/model resolved from .env inside make_official_client.
    return make_official_client(
        max_tokens=config.MAX_TOKENS,
        temperature=config.TEMPERATURE,
    )


def _cohort_path() -> Path:
    return ART / "e4_isoabl_cohort.json"


def load_cohort() -> list[str]:
    """Frozen mechanism cohort (task ids). Written by the labeling step (S2)."""
    p = _cohort_path()
    if not p.is_file():
        raise SystemExit(
            f"REFUSE: cohort file missing: {p}\n"
            "Freeze S_binding ∪ S_planning first (freeze plan §2/§11; codebook_v1)."
        )
    doc = json.loads(p.read_text())
    ids = list(doc.get("cohort") or [])
    if not ids:
        raise SystemExit("REFUSE: cohort file has no tasks")
    return ids


def plan_blocks(case_ids: list[str], *, block_size: int = 12, seed: int = 20260915) -> list[dict[str, Any]]:
    """Deterministic matched blocks: tasks grouped, arm order randomized per task."""
    rng = random.Random(seed)
    ids = sorted(case_ids)
    blocks: list[dict[str, Any]] = []
    for bi in range(0, len(ids), block_size):
        chunk = ids[bi : bi + block_size]
        plan = []
        for tid in chunk:
            order = list(ARM_NAMES)
            rng.shuffle(order)
            plan.append({"task_id": tid, "arm_order": order})
        blocks.append({"block_id": f"blk{len(blocks) + 1:02d}", "tasks": plan})
    return blocks


def _append_row(path: Path, row: dict[str, Any]) -> None:
    with _io_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _done_keys(path: Path) -> set[tuple[str, str]]:
    done: set[tuple[str, str]] = set()
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            done.add((row["case_id"], row["arm"]))
    return done


def _run_plan(plan: list[dict[str, Any]], *, tag: str, out_path: Path, workers: int) -> dict[str, Any]:
    jobs = []
    for blk in plan:
        for ti, t in enumerate(blk["tasks"]):
            for ai, arm in enumerate(t["arm_order"]):
                jobs.append(
                    {
                        "case_id": t["task_id"],
                        "arm": arm,
                        "block_id": blk["block_id"],
                        "arm_order_in_block": ai,
                    }
                )
    done = _done_keys(out_path)
    pending = [j for j in jobs if (j["case_id"], j["arm"]) not in done]
    print(
        f"{tag} episodes total={len(jobs)} done={len(jobs) - len(pending)} pending={len(pending)} "
        f"workers={workers} budgets={FROZEN_BUDGETS['max_model_calls']}/{FROZEN_BUDGETS['max_eval_calls']}",
        flush=True,
    )
    errors: list[str] = []
    n = 0
    t0 = time.time()

    def _one(job: dict[str, Any]) -> dict[str, Any]:
        client = _make_client()
        try:
            return run_ablation_episode(
                job["case_id"],
                job["arm"],
                client,
                tag=tag,
                block_id=job["block_id"],
                arm_order=job["arm_order_in_block"],
            )
        finally:
            pass

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_one, j): j for j in pending}
        for fut in as_completed(futs):
            job = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001 - runner must survive single failures
                msg = f"{job['case_id']}/{job['arm']}: {type(exc).__name__}: {exc}"
                errors.append(msg)
                print(f"ERROR {msg}", flush=True)
                continue
            _append_row(out_path, row)
            n += 1
            print(
                f"[{row['arm']}] {row['case_id']} terminal_pass={row['terminal_candidate_pass']} "
                f"llm={row['llm_calls']} insp={row['inspect_calls']} eval={row['eval_calls']} "
                f"wr={row['write_calls']} blk={row['blocked_capability_attempt_count']} "
                f"rst={row['context_reset_count']} sub={row['agent_submitted']}/"
                f"{'F' if row['forced_submit'] else '-'} ({n}/{len(pending)}) "
                f"err={(row.get('terminal_error') or '')[:60]}",
                flush=True,
            )
    if errors:
        print(f"{tag} job_errors={len(errors)} first={errors[0]}", flush=True)
    print(f"{tag} DONE n={n} errors={len(errors)} wallclock={time.time() - t0:.0f}s", flush=True)
    return {"n": n, "errors": errors}


def run_smoke(case_ids: list[str] | None = None, workers: int = 4) -> dict[str, Any]:
    ids = list(case_ids or EQPA_DEV_CASES[:2])
    plan = [{"block_id": "smoke", "tasks": [{"task_id": t, "arm_order": list(ARM_NAMES)} for t in ids]}]
    out = ART / f"{SMOKE_TAG}_traces.jsonl"
    print(f"SMOKE tag={SMOKE_TAG} cases={ids} arms={ARM_NAMES} — excluded from formal data", flush=True)
    return _run_plan(plan, tag=SMOKE_TAG, out_path=out, workers=workers)


def run_blocks(workers: int = 16, block_size: int = 12, seed: int = 20260915) -> dict[str, Any]:
    cohort = load_cohort()
    plan = plan_blocks(cohort, block_size=block_size, seed=seed)
    plan_path = ART / f"{BLOCKS_TAG}_block_plan.json"
    plan_path.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    out = ART / f"{BLOCKS_TAG}_traces.jsonl"
    print(f"BLOCKS tag={BLOCKS_TAG} cohort={len(cohort)} blocks={len(plan)} plan={plan_path.name}", flush=True)
    return _run_plan(plan, tag=BLOCKS_TAG, out_path=out, workers=workers)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = argv[0] if argv else "smoke"
    workers = 16
    if "--workers" in argv:
        workers = int(argv[argv.index("--workers") + 1])
    if mode == "smoke":
        out = run_smoke(workers=workers)
    elif mode == "blocks":
        out = run_blocks(workers=workers)
    else:
        raise SystemExit(f"unknown mode {mode!r}; use smoke|blocks")
    return 0 if not out.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
