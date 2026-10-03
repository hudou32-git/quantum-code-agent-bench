"""FCEA runner (RQ4 phase 1). Mirrors exp.evidence_eqpa.run (resume-safe,
manifest+protocol recording) with the variant flag and prior provenance.

Variants (mutually comparable, separate tags):
  --variant global  rq4_fcea[_dev|_qbplus]_global    (V2)
  --variant fcond   rq4_fcea[_dev|_qbplus]_fcond     (V3)
V1 (Batch-EQPA) is the existing frozen tag e7_evidence_eqpa_qbplus and is never
re-run here.
"""
from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from exp import config
from exp.common.canary import ensure_canaries, scan_text
from exp.common.env_guard import (
    require_grader_python,
    require_grader_python_cirq,
    require_grader_python_pennylane,
)
from exp.common.llm import DeepSeekClient, official_chat_url
from exp.common import llm_obs
from exp.common.repeat_guard import generation_guard_record
from exp.common.traceio import load_traces
from exp.eqpa.bwrap import require_bwrap
from exp.eqpa.env_guard import require_grader_runtime
from exp.fcea import config as fcfg
from exp.fcea.control.mech_flags import flags_for_variant as _mech_flags_for
from exp.fcea.control import rq4b as _rqb
from exp.fcea import loop as f_loop
from exp.fcea.utility import prior as uprior

_io_lock = threading.Lock()
_tls = threading.local()
PROTOCOL_PATH = Path(__file__).resolve().parents[2] / "analysis/rq4_fcea/qhe_evidence_utility_prior.json"
A16_PROTOCOL_PATH = Path(__file__).resolve().parents[2] / "analysis/agent_ceiling_analysis/PROTOCOL_rq4b_A16.md"
A16_TRACE_PROBE_PATH = Path(__file__).resolve().parents[2] / "exp/fcea/control/trace_probe.py"
ACCEPTANCE_PATH = Path(__file__).resolve().parents[2] / "exp/fcea/control/acceptance.py"


def _hash_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _client(framework: str = "qiskit") -> DeepSeekClient:
    return DeepSeekClient(
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
        disable_thinking=True,
        system=fcfg.fcea_system(framework),
        max_retries=3,
    )


def _thread_client(framework: str = "qiskit") -> DeepSeekClient:
    cache = getattr(_tls, "clients", None)
    if cache is None:
        cache = _tls.clients = {}
    client = cache.get(framework)
    if client is None:
        client = _client(framework)
        cache[framework] = client
    return client


def _clamp_workers(n: int | None, pending: int) -> int:
    raw = config.JOB_WORKERS if n is None else int(n)
    cap = min(config.JOB_WORKERS_MAX, config.LLM_CONCURRENCY_LIMIT)
    want = max(1, min(raw, cap))
    return min(want, max(1, pending)) if pending else 1


def _pass_at_1(row: dict[str, Any]) -> bool:
    for s in row.get("shots") or []:
        if int(s.get("k") or 0) == 1:
            return bool(s.get("passed"))
    return False


def run_fcea_split(
    *,
    case_ids: list[str] | None = None,
    dev: bool = False,
    tag: str | None = None,
    workers: int | None = None,
    bench: str = "qbplus",
    variant: str = "global",
    seed: int | None = None,
    framework: str = "qiskit",
) -> dict[str, Any]:
    fcfg.set_variant(variant)
    action_seed = fcfg.set_action_seed(seed)
    require_bwrap()
    ensure_canaries()
    bench = (bench or "qbplus").strip().lower()
    fw = (framework or "qiskit").strip().lower()
    if fw != "qiskit" and bench != "qbplus":
        raise SystemExit(
            f"REFUSE: --framework {fw} is only defined for --bench qbplus "
            "(QHE local_hard is a qiskit benchmark).")
    if bench == "qhe":
        require_grader_runtime()
    if bench == "qbplus" and fw not in ("qiskit", "cirq", "pennylane"):
        raise SystemExit(f"REFUSE: unknown framework {fw!r} (expected qiskit/cirq/pennylane)")
    if case_ids:
        ids = list(case_ids)
        split = "dev" if dev else "eval"
    elif dev:
        ids = list(fcfg.EQPA_DEV_CASES)
        split = "dev"
    elif bench == "qbplus":
        from exp.common.grader_qbplus import list_ids

        ids = list_ids(fw)
        split = "eval"
    else:
        from exp.common.cases import _qhe_dataset

        ids = sorted(_qhe_dataset().keys())
        split = "eval"
    tag = tag or fcfg.default_tag(bench=bench, dev=dev, framework=fw)
    fcfg.refuse_foreign_tag(tag)
    results_root = config.arm_results("fcea")
    results_root.mkdir(parents=True, exist_ok=True)
    run_root = results_root / tag
    run_root.mkdir(parents=True, exist_ok=True)
    # Phase 0 observability: one llm_calls.jsonl sidecar per run/tag.
    llm_obs.activate(
        run_root / "llm_calls.jsonl",
        runner="fcea", tag=tag, bench=bench, variant=variant, framework=fw,
    )
    out_path = results_root / f"{tag}_traces.jsonl"
    summary_path = results_root / f"{tag}_summary.json"

    manifest = {
        "split": split,
        "case_ids": ids,
        "action_selector_seed": (action_seed if variant in ("deuact", "deurand")
                                 else None),
        **({"d2_noise_seed_base": fcfg.D2_NOISE_CONSTANTS["random_seed_base"],
            "d2_noise_seed_rule": "sha256('d2|<tag>|<case_id>') first 6 bytes"}
           if variant == "d2_clean" else {}),
        "protocol_sha256": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()[:16],
        # MECH-1 (docs/实验MECH-1_协议.md): additive manifest keys — the frozen
        # mech flag matrix; empty for every legacy variant. Ladder experiment
        # arms (deurq_*, docs/book/实验.md v3) record theirs the same way.
        **({"mech_flags": {k: bool(v) for k, v in
                           _mech_flags_for(variant).items() if v}}
           if (variant.startswith("mech1_")
               or variant in ("deurq_z1", "deurq_base", "deurq_baseenv",
                              "deurq_baseenv_v2", "deurq_final")) else {}),
        # E3-new / E4 acceptance pipeline (2026-10-01 freeze): additive
        # manifest keys recording the frozen gate wiring + pipeline hashes
        **({"acceptance_pipeline": {
            "spec": "docs/E3_E4_ACCEPTANCE_PIPELINE.md",
            "manifest": "analysis/deurq_base/E3NEW_MANIFEST.json",
            "z3_gate_salvage": True,
            "z3_fallback_gate": True,
            "acceptance_sha256": _hash_file(ACCEPTANCE_PATH),
            "supersedes": "deurq_baseenv (legacy era-1 E3; audit-only)",
        }} if variant == "deurq_baseenv_v2" else {}),
        **({"acceptance_pipeline": {
            "spec": "docs/E3_E4_ACCEPTANCE_PIPELINE.md",
            "manifest": "analysis/deurq_base/E4_MANIFEST.json",
            "sz4_manifest": "analysis/agent_ceiling_analysis/SZ4_MANIFEST.json",
            "z3_gate_salvage": True,
            "z3_fallback_gate": True,
            "z4_trace_gate": True,
            "z4_arm_defer_when_z3": True,
            "z4_reject_cap_per_shot": _rqb.TRACE_REJECT_CAP_PER_SHOT,
            "z4_trace_timeout_s": _rqb.TRACE_TIMEOUT_S,
            "acceptance_sha256": _hash_file(ACCEPTANCE_PATH),
        }} if variant == "deurq_final" else {}),
        # A16 (PROTOCOL_rq4b_A16.md): frozen v2 constants + provenance hashes,
        # additive manifest keys for deurc_trace_v2 only
        **({"rq4b_trace_v2": {
            "protocol_sha256": hashlib.sha256(
                A16_PROTOCOL_PATH.read_bytes()).hexdigest()[:16],
            "trace_probe_sha256": hashlib.sha256(
                A16_TRACE_PROBE_PATH.read_bytes()).hexdigest()[:16],
            "reject_cap_per_shot": _rqb.TRACE_REJECT_CAP_PER_SHOT,
            "trace_timeout_s": _rqb.TRACE_TIMEOUT_S,
            "dummy_ladder": list(map(repr, _rqb.TRACE_DUMMY_LADDER)),
            "typed_dummies": {k: list(map(repr, v))
                              for k, v in _rqb.TRACE_TYPED_DUMMIES.items()},
            "max_call_combos": _rqb.TRACE_MAX_CALL_COMBOS,
        }} if variant == "deurc_trace_v2" else {}),
        "llm_endpoint": official_chat_url(),
        "model": config.MODEL,
        "decoding_temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "thinking_mode": "disabled",
        "framework": fw if bench == "qbplus" else "qiskit",
        "system_prompt": fcfg.fcea_system(fw),
        "variant": variant,
        "batch": fcfg.batch_frozen_constants(),
        "prior": uprior.provenance(),
        "prior_sha256": uprior.prior_sha256(),
        "config_hashes": fcfg.config_hashes(),
        "grader_runtime": (
            require_grader_python_cirq()
            if (bench == "qbplus" and fw == "cirq")
            else require_grader_python_pennylane()
            if (bench == "qbplus" and fw == "pennylane")
            else require_grader_python()
        ),
        "generation_guard": generation_guard_record("detect"),
        "note": (
            "RQ4 FCEA: BatchProbe protocol identical to e7_evidence_eqpa; "
            "after a failed official Eval a soft evidence-priority notice from the "
            "FROZEN QHE-only prior is injected (global tiers for variant=global, "
            "context tiers for variant=fcond). NoSubmit gets no notice. QB+ "
            "results never touched the prior. "
            + ("variant=deu (DEU-v2): online marginal-utility tracking over the "
               "frozen global Q0 (EMA alpha=0.3, per-task reset, no cross-task "
               "learning) with soft routine/saturation guidance at failure "
               "boundaries and per-injection adoption logging; no submit "
               "directive, no QB+ feedback path."
               if variant == "deu" else
               "variant=deu3 (DEU-v3 action-adapter PoC): DEU-v2 machinery "
               "unchanged (same state manager, EMA, reward, utility notice) plus "
               "an ActionAdapter emitting at most two action-level messages "
               "(strategy_switch: same_error>=2 with low/falling novelty; "
               "explore_stop: no_progress>=2 with utility drop >= 0.046) at "
               "EVERY failure boundary including NoSubmit; guidance only, no "
               "action execution, per-boundary adapter_log."
               if variant == "deu3" else
               "variant=%s (DEU-v3-ACT): DEU-v2 machinery unchanged plus a "
               "rule-based Action Selector at every failure boundary choosing "
               "among CONTINUE / SWITCH_EVIDENCE / SWITCH_STRATEGY / FINALIZE; "
               "actions are COMMITTED on the next attempt (SWITCH_EVIDENCE "
               "filters BatchProbe queries to the focus family; FINALIZE "
               "withdraws BatchProbe until episode end, no auto-submit); "
               "decisions logged per boundary in action_log."
               % variant
               if variant == "deuact" else
               "variant=%s (random-action ablation): identical commitment "
               "machinery to deuact but the action is drawn uniformly at random "
               "(seeded), ignoring state and utility."
               % variant
               if variant == "deurand" else
               "variant=%s (DEU-RC): DEU-v2 machinery unchanged (state "
               "manager, EMA utility, prior) plus a deterministic repair-"
               "control layer: RCI -> repair mode (SEARCH/FOCUS/ESCAPE/"
               "TERMINATE) -> evidence branch gating (family BLOCKED on "
               "repeated failures with falling novelty, reversible via new "
               "error signatures) and mode-based context assembly. The "
               "controller restricts the decision space; the LLM executes "
               "the mode. Decisions logged per boundary in control_log."
               % variant
               if variant == "deurc" else
               "variant=%s (DEU-RC, ESCAPE ablation): identical to deurc "
               "(same RCI, evidence branch gate, context gate, thresholds) "
               "except the ESCAPE mode is ablated — when the frozen rule "
               "selects ESCAPE the no-escape fallback applies (FOCUS if the "
               "focus gate holds, else SEARCH); original_mode/escape_blocked "
               "record what frozen DEU-RC would have done. Phase 2.2 "
               "causal-diagnosis arm, not an improved variant."
               % variant
               if variant == "deurc_noescape" else
               "variant=%s (DEU-RC, soft-FOCUS ablation): identical to deurc "
               "(same RCI, mode selector, ESCAPE/TERMINATE, evidence branch "
               "gate, context gate, thresholds) except FOCUS evidence "
               "restriction is soft — BatchProbe stays available, the "
               "best-utility family is marked preferred and the others take "
               "a priority penalty. Phase 2.2 causal-diagnosis arm, not an "
               "improved variant."
               % variant
               if variant == "deurc_softfocus" else
               "variant=%s (DEU-RC, joint relaxation ablation): both "
               "single-channel relaxations combined — ESCAPE transitions "
               "ablated (no-escape fallback) AND FOCUS restriction soft "
               "(preferred family + penalty, no withdrawal). Pure flag "
               "combination of the Exp1/Exp2 arms; tests damage-channel "
               "additivity. Causal-diagnosis arm."
               % variant
               if variant == "deurc_jointrelax" else
               "variant=%s (DEU-RC, context-preservation ablation): "
               "identical to deurc except the context gate is disabled — "
               "full message history every attempt (no mode-based pruning). "
               "Third restriction-channel ablation; ESCAPE/FOCUS/TERMINATE/"
               "RCI/gates all unchanged. Causal-diagnosis arm."
               % variant
               if variant == "deurc_noctx" else
               "variant=%s (DEU-RC, NoCtx+joint interaction test): context "
               "preservation AND both behavior relaxations combined — all "
               "three restriction flags off. Tests H-CTX-INT: do ESCAPE/"
               "FOCUS constraints retain independent marginal damage once "
               "context is fully preserved? Causal-diagnosis arm."
               % variant
               if variant == "deurc_noctx_joint" else
               "variant=%s (RQ3 D2 clean, full − C2): byte-identical to "
               "deurc_noctx in machinery and thresholds; the utility INPUT is "
               "replaced by a seeded noise surrogate at every consumption "
               "point — controller Q (branch states / best_q FOCUS gate / RCI "
               "utility component and its directive text) and utility_drop "
               "(TERMINATE gate + RCI), plus the evidence-priority notice "
               "tiers (matched form: same template, frozen tier multiset "
               "{HIGH, MEDIUM, MEDIUM, LOW} assigned by a random ranking). "
               "Q̃ ~ Uniform(q_floor, 1.0) iid per family per boundary, "
               "drop̃ = max-family |ΔQ̃| between consecutive draws; per-episode "
               "seed sha256('d2|<tag>|<case_id>') base 20260925. State path "
               "fully intact (state manager, stagnation counters, branch "
               "failure attribution, evidence gate, ESCAPE). The C2 machinery "
               "still computes for trace reference only — no consumption "
               "point receives real utility."
               % variant
               if variant == "d2_clean" else
               "variant=%s (RQ3 D3, full − C1): state layer disabled on the "
               "deurc_noctx stack — no failure attribution, no stagnation "
               "counters, no saturation signals (controller flag "
               "state_blind: branches frozen ACTIVE, no_progress/same_error "
               "forced 0, progress/novelty neutral, ESCAPE and TERMINATE "
               "unreachable); utility pinned to the frozen prior Q0 (no EMA "
               "updates, utility_drop ≡ 0); controller degrades to "
               "utility-only episode-blind steering (SEARCH + the "
               "utility-driven FOCUS). Evidence-priority notice unchanged "
               "(frozen global tiers, the C2 static half). A minimal evidence "
               "ledger (counts per classified category) feeds the FOCUS "
               "gate's evidence_samples input."
               % variant
               if variant == "d3" else
               "variant=%s (DCC, depth-conditioned commitment): unchanged "
               "deurc_noctx stack with the decision layer replaced by a "
               "frozen depth schedule — failure_depth 1 -> SEARCH (BatchProbe "
               "open, constraint none), 2 -> FOCUS (BatchProbe withdrawn), "
               ">=3 -> COMMIT (withdrawn, submit-oriented). Only decision "
               "input is the official-attempt counter at the boundary; "
               "state/utility/evidence/error text are ignored. Tests whether "
               "failure depth alone reproduces the D3-style cost profile "
               "(Stage 0 F1 census). Additive trace keys: dcc_trace_schema, "
               "dcc_state, decision_trace."
               % variant
               if variant == "dcc" else
               "variant=%s (RQ-fix, engineering-repair arm on deurc_noctx): "
               "three repairs from the D2 mechanism analysis, each behind a "
               "default-off flag. F1 utility channel state-only — boundary Q "
               "pinned uniform {E:0.5}, drop=0, and the evidence-priority "
               "notice NOT injected (QHE-misaligned prior tiers deleted, the "
               "sole delta vs d2_clean's matched-form random notice). "
               "F2 FOCUS coverage criterion — focus_min_evidence 4->8 AND at "
               "least one E3 (behavioral) probe sampled (early-FOCUS "
               "episodes pass 42%% vs 84%%; KL-graded tasks need "
               "distribution-check evidence). F3 KL-type failures exempt "
               "from evidence-family attribution (KL mismatch is an "
               "implementation-semantics failure, not an evidence-path "
               "failure — the ESCAPE-chain root: full arm 43 ESCAPE vs "
               "d2_clean 34)."
               % variant
               if variant == "deurq_fix" else
               "variant=%s (rq4b A16 forced-contract probe v2, "
               "analysis/agent_ceiling_analysis/PROTOCOL_rq4b_A16.md): "
               "deurc-noctx stack unchanged plus harness-side enforcement of "
               "the v1 A1 repair contract. L1: at every informative-assertion "
               "failure boundary the harness executes the evaluated attempt's "
               "entry with a frozen dummy ladder in the episode sandbox and "
               "injects a '[trace] assertion expects ...; your artifact: ...' "
               "evidence block into the failure feedback. L2: an armed "
               "official Eval is intercepted by the same probe first — entry "
               "crash or parseable mismatch (assertion expectation N vs probe "
               "value != N) rejects the Eval NON-officially (attempt not "
               "consumed, max %d rejections per shot, then fail-open); "
               "indeterminate or matching probes pass through to the official "
               "Eval. L3: the v1 model-initiated kind=trace BatchProbe "
               "discharge channel is kept unchanged. Frozen constants: "
               "TRACE_TIMEOUT=16s, reject cap %d/shot, dummy ladder and "
               "expectation parser in exp/fcea/control/rq4b.py; probe runner "
               "exp/fcea/control/trace_probe.py (sha in this manifest)."
               % (variant, _rqb.TRACE_REJECT_CAP_PER_SHOT,
                  _rqb.TRACE_REJECT_CAP_PER_SHOT)
               if variant == "deurc_trace_v2" else
               "variant=%s (E3-new, E2 + Z3_complete; analysis/deurq_base/"
               "E3NEW_MANIFEST.json): the frozen mech1_rep mechanism set of "
               "the legacy era-1 E3 (deurq_baseenv, superseded) plus the "
               "acceptance pipeline — gate-bound salvage (a gate-rejected "
               "candidate consumes the salvage slot as NoSubmit instead of "
               "the legacy FAIL-OPEN bypass), submission-path coverage (the "
               "no-tool-call fallback passes the Z3 preflight non-officially "
               "before grading), and revision-provenance enforcement (a "
               "rejected revision is salvage-ineligible until modified). "
               "Supersession is a definition-contract fix, not an empirical "
               "failure."
               % variant
               if variant == "deurq_baseenv_v2" else
               "variant=%s (E4, E3-new + Z4 semantic alignment; analysis/"
               "deurq_base/E4_MANIFEST.json + SZ4_MANIFEST.json): the full "
               "E3-new acceptance pipeline plus the Z4 gate — frozen A16 v2 "
               "probe machinery (informative-signature arming, L1 boundary "
               "probe, L2 Eval tri-state interception with the frozen "
               "expectation parser, L3 model channel) under the E4 armed "
               "lifecycle: single-slot expectation (new signature replaces "
               "the old), armed persists across Write, discharge on L3 trace "
               "round or L2 passed verdict, shot-end cleanup, Z3-first "
               "ordering (a Z3-rejected candidate is never Z4-probed), "
               "arm-now/probe-later deferral when a Z3 contract gap "
               "co-triggers, independent per-shot reject caps for Z3 and Z4."
               % variant
               if variant == "deurq_final" else
               "variant=%s: static frozen-prior tiers only." % variant)
        ),
    }
    mpath = run_root / f"{tag}_manifest.json"
    if mpath.is_file() and out_path.is_file() and out_path.read_text(encoding="utf-8").strip():
        old_m = json.loads(mpath.read_text(encoding="utf-8"))
        for key in ("decoding_temperature", "max_tokens"):
            if key in old_m and old_m[key] != manifest[key]:
                raise SystemExit(
                    f"REFUSE: tag {tag} has {key}={old_m[key]}, current pin is "
                    f"{manifest[key]}. Archive the old run or pass a new --tag.")
        if old_m.get("variant") != variant:
            raise SystemExit(
                f"REFUSE: tag {tag} was run with variant={old_m.get('variant')}, "
                f"current is {variant}. Use a different tag.")
        old_fw = old_m.get("framework", "qiskit")
        if old_fw != (fw if bench == "qbplus" else "qiskit"):
            raise SystemExit(
                f"REFUSE: tag {tag} was run with framework={old_fw}, current is "
                f"{fw}. Mixing frameworks inside one tag would corrupt the "
                "cross-framework design; use a different tag.")
        if old_m.get("prior_sha256") != manifest["prior_sha256"]:
            raise SystemExit(
                f"REFUSE: tag {tag} was run with prior sha {old_m.get('prior_sha256')}, "
                "current prior differs. The prior is frozen; use a new --tag.")
        old_seed = old_m.get("action_selector_seed")
        if (old_seed is not None and variant in ("deuact", "deurand")
                and old_seed != action_seed):
            raise SystemExit(
                f"REFUSE: tag {tag} was run with action_selector_seed={old_seed}, "
                f"current is {action_seed}. Mixing seeds inside one tag would "
                "corrupt the repetition design; use a new --tag.")
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    done: set[str] = set()
    if out_path.is_file():
        rows, _ = load_traces(out_path)
        for row in rows:
            if row.get("arm") == fcfg.ARM_NAME and row.get("pass_fail") in {"PASS", "FAIL"}:
                done.add(row["case_id"])
    pending = [c for c in ids if c not in done]
    n_workers = _clamp_workers(workers, len(pending))
    print(f"[fcea] tag={tag} bench={bench} split={split} variant={variant} "
          f"n={len(ids)} pending={len(pending)} workers={n_workers} "
          f"prior={manifest['prior_sha256'][:12]}")

    def _one(cid: str) -> dict[str, Any]:
        # Phase 0 observability: one ledger episode per agent episode.
        with llm_obs.episode_context(method=variant, task_id=cid, bench=bench) as ep:
            row = f_loop.run_fcea(cid, _thread_client(fw), tag=tag, bench=bench,
                                  framework=fw)
            ep.record_outcome(
                success=(row.get("pass_fail") == "PASS"),
                iterations=row.get("official_submits"),
                llm_calls_reported=row.get("llm_calls"),
            )
            return row

    errors = 0
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futs = {pool.submit(_one, cid): cid for cid in pending}
        for fut in as_completed(futs):
            cid = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001
                errors += 1
                print(f"[job_error] {cid}: {type(exc).__name__}: {exc}")
                continue
            with _io_lock:
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

    rows, _ = load_traces(out_path)
    scoped = [r for r in rows if r.get("arm") == fcfg.ARM_NAME and r.get("case_id") in set(ids)]
    n_pass = sum(1 for r in scoped if r.get("passed"))
    p1 = sum(1 for r in scoped if _pass_at_1(r))
    p2 = sum(1 for r in scoped if any(s.get("k", 9) <= 2 and s.get("passed") for s in r.get("shots") or []))
    canary = sum(
        len(scan_text("\n".join([r.get("parsed_code") or "", r.get("error_message") or "",
                                 *(str(t.get("text") or "") for t in r.get("tool_log") or [])])))
        for r in scoped)
    n = max(len(scoped), 1)
    summary = {
        "tag": tag, "arm": fcfg.ARM_NAME, "variant": variant, "benchmark": bench, "split": split,
        "framework": fw if bench == "qbplus" else "qiskit",
        "n": len(scoped),
        "pass": n_pass, "pass_rate": round(n_pass / n, 4),
        "pass_at_1": p1, "pass_at_2": p2, "pass_at_3": n_pass,
        "avg_llm_calls": round(sum(r.get("llm_calls", 0) for r in scoped) / n, 2),
        "total_llm_calls": sum(r.get("llm_calls", 0) for r in scoped),
        "total_prompt_tokens": sum(r.get("prompt_tokens", 0) for r in scoped),
        "total_completion_tokens": sum(r.get("completion_tokens", 0) for r in scoped),
        "avg_tool_rounds": round(sum(r.get("tool_rounds", 0) for r in scoped) / n, 2),
        "avg_probe_queries": round(sum(r.get("probe_queries", 0) for r in scoped) / n, 2),
        "avg_batch": round(sum(r.get("avg_batch", 0) for r in scoped) / n, 2),
        "priority_injections": sum(r.get("priority_injections", 0) for r in scoped),
        "failure_events": sum(len(r.get("failure_events") or []) for r in scoped),
        "canary_hits": canary,
        "job_errors": errors,
        "llm": {"model": config.MODEL, "workers": n_workers,
                "decoding_temperature": config.TEMPERATURE, "max_tokens": config.MAX_TOKENS},
        "prior_sha256": uprior.prior_sha256(),
        "manifest": str(mpath),
        "traces": str(out_path),
        "note": manifest["note"],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    # Phase 0 observability: run-level cost summary (GATE 3/4 cost fields).
    llm_obs.write_cost_summary()
    print(json.dumps({k: v for k, v in summary.items() if k not in ("case_ids",)},
                     ensure_ascii=False, indent=1))
    return summary


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--bench", default="qbplus")
    ap.add_argument("--cases", nargs="*", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--variant", default="global", choices=fcfg.VARIANTS)
    ap.add_argument("--framework", default="qiskit",
                    choices=("qiskit", "cirq", "pennylane"),
                    help="QB+ framework suite (Phase C cross-framework); "
                         "qiskit keeps the historical tag layout")
    ap.add_argument("--seed", type=int, default=None,
                    help="override the deurand selector seed (repetition runs); "
                         "default keeps the frozen 20260923")
    args = ap.parse_args()
    run_fcea_split(dev=args.dev, case_ids=args.cases, tag=args.tag, workers=args.workers,
                   bench=args.bench, variant=args.variant, seed=args.seed,
                   framework=args.framework)


if __name__ == "__main__":
    main()
