"""FCEA arm config. Protocol pins are imported from exp.evidence_eqpa so any
drift there is inherited loudly rather than silently forked."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from exp import config
from exp.evidence_eqpa import config as bcfg

ARM_NAME = "FCEA"
TAG_PREFIX = "rq4_fcea"
# MECH-1 (2026-09-30): additive tag namespace — rq4_fcea untouched;
# mech1_fcea* is the 实验MECH-1 arm family (docs/实验MECH-1_协议.md);
# rq4b_fcea* is the S4-trace / replan family (analysis/agent_ceiling_analysis/
# PROTOCOL_rq4b_trace_replan.md v2.1; rq5 prefix stays reserved for the
# information line per the MECH-1 coordination appendix).
TAG_PREFIXES = ("rq4_fcea", "mech1_fcea", "rq4b_fcea")

EQPA_DEV_CASES = bcfg.EQPA_DEV_CASES

# ---- protocol pins: identical to e4_eqpa_40960 / e7_evidence_eqpa ----
MAX_LLM_PER_SHOT = bcfg.MAX_LLM_PER_SHOT        # 16
MAX_OFFICIAL = bcfg.MAX_OFFICIAL                # 3

# ---- batch knobs: identical to e7_evidence_eqpa ----
MAX_QUERIES_PER_BATCH = bcfg.MAX_QUERIES_PER_BATCH
PROBE_TIMEOUT_S = bcfg.PROBE_TIMEOUT_S
PROBE_MAX_CHARS = bcfg.PROBE_MAX_CHARS
MAX_PROBES_PER_SHOT = bcfg.MAX_PROBES_PER_SHOT

# ---- variants ----
VARIANTS = ("global", "fcond", "deu", "deu3", "deuact", "deurand", "deurc",
            "deurc_noescape", "deurc_softfocus", "deurc_jointrelax",
            "deurc_noctx", "deurc_noctx_joint", "d2_clean", "d3", "dcc",
            "deurq_fix", "mech1_prev", "mech1_rep", "mech1_full",
            "deurc_trace", "deurc_restart", "deurc_replan", "deurc_trace_v2",
            "deurq_base", "deurq_z1", "deurq_baseenv",
            "deurq_baseenv_v2", "deurq_final",
            "deurq_baseenv_noz2", "deurq_final_noz2")
DEU_PHASE = 1          # Phase 1 = state tracking only (no update, no guidance)

# DEU-v2 constants (frozen into the manifest when variant == "deu"); semantics:
# analysis/rq4_fcea/deu_v2_design.md rev2. Phase 1 uses only the thresholds.
from exp.fcea.utility.state import DEFAULT_CONSTANTS as _DEU_DEFAULTS  # noqa: E402
DEU_CONSTANTS = dict(_DEU_DEFAULTS)
VARIANT: str = "global"

# DEU-v3 Action Adapter (proof of concept; variant == "deu3"): action-level
# guidance layered on the UNCHANGED DEU-v2 machinery (same state manager, EMA,
# reward, notice path). Thresholds: same-error/no-progress from the PoC spec
# (default 2); utility-drop = the frozen H2 median nonzero |delta_Q|
# (analysis/rq4_fcea/rq4_deu_utility_state_alignment.json).
from exp.fcea.adapter import DEFAULT_CONSTANTS as _DEU3_DEFAULTS  # noqa: E402
DEU3_CONSTANTS = dict(_DEU3_DEFAULTS)

# DEU-v3-ACT (variant == "deuact") and its random ablation ("deurand"):
# rule-based Action Selector is a real decision layer; actions are COMMITTED
# (evidence-focus query filter, BatchProbe withdrawal on FINALIZE). Same DEU
# machinery underneath. Thresholds frozen from the H2 analysis.
from exp.fcea.action_selector import DEFAULT_CONSTANTS as _DEUACT_DEFAULTS  # noqa: E402
DEUACT_CONSTANTS = dict(_DEUACT_DEFAULTS)

# DEU-RC (variant == "deurc"): Repair Control layer on the UNCHANGED DEU-v2
# machinery (same state manager, EMA updater, prior). Control state chain:
# RCI -> RepairMode (SEARCH/FOCUS/ESCAPE/TERMINATE) -> evidence branch gating
# + mode-based context assembly. The controller restricts the LLM decision
# space; the LLM only executes the selected mode. Weights/thresholds frozen
# here; ablation flags (enable_mode_controller / enable_evidence_gate /
# enable_context_gate) support the Phase-2 arms without code changes.
from exp.fcea.control.controller import DEFAULT_CONSTANTS as _DEURC_DEFAULTS  # noqa: E402
DEURC_CONSTANTS = dict(_DEURC_DEFAULTS)

# Phase 2.2 Experiment 1 (variant deurc_noescape): identical to deurc except
# the ESCAPE mode is ablated — when the frozen rule selects ESCAPE, the
# no-escape fallback applies (FOCUS if the focus gate holds, else SEARCH).
# Every other component (RCI, weights, evidence gate, context gate, thresholds)
# is byte-identical to deurc.
DEURC_NOESCAPE_CONSTANTS = {**DEURC_CONSTANTS, "enable_escape_mode": False}

# Phase 2.2 Experiment 2 (variant deurc_softfocus): identical to deurc except
# FOCUS evidence restriction is soft — BatchProbe stays available, the
# best-utility family is marked preferred and the others take a priority
# penalty (no family removal). ESCAPE/TERMINATE/RCI/gates all unchanged.
DEURC_SOFTFOCUS_CONSTANTS = {**DEURC_CONSTANTS, "focus_hard_restriction": False}

# Phase 2.2 joint relaxation (variant deurc_jointrelax): BOTH single-channel
# ablations combined — ESCAPE transitions removed AND FOCUS restriction soft.
# Pure flag combination; no new logic. Tests the additivity of the two
# damage channels identified by Exp1 (+4) and Exp2 (+4).
DEURC_JOINTRELAX_CONSTANTS = {**DEURC_CONSTANTS, "enable_escape_mode": False,
                              "focus_hard_restriction": False}

# Phase 2.2 context preservation (variant deurc_noctx): identical to deurc
# except the context gate is disabled — full message history every attempt
# (no mode-based pruning). Tests the third restriction channel in isolation.
DEURC_NOCTX_CONSTANTS = {**DEURC_CONSTANTS, "enable_context_gate": False}

# Phase 2.2 interaction test (variant deurc_noctx_joint): context preserved
# AND both behavior relaxations — all three restriction flags off. Tests
# whether ESCAPE/FOCUS constraints retain independent marginal damage once
# context is fully preserved (H-CTX-INT).
DEURC_NOCTX_JOINT_CONSTANTS = {**DEURC_CONSTANTS,
                               "enable_context_gate": False,
                               "enable_escape_mode": False,
                               "focus_hard_restriction": False}

# RQ3 Phase B (2026-09-25), both on the deurc-noctx stack (= full DEU-RQ).
#
# D2 clean (variant d2_clean, full − C2): the controller and every mechanism
# are byte-identical to deurc_noctx — the utility INPUT is replaced upstream
# (loop.py) by a seeded noise surrogate at every consumption point (controller
# Q / utility_drop, RCI utility components, notice tiers). No controller flag:
# the substitution happens before on_boundary, so this constant dict stays
# identical to the full stack on purpose.
from exp.fcea.utility.noise import DEFAULT_CONSTANTS as _D2_NOISE_DEFAULTS  # noqa: E402
D2_CLEAN_CONSTANTS = {**DEURC_NOCTX_CONSTANTS}
D2_NOISE_CONSTANTS = dict(_D2_NOISE_DEFAULTS)

# RQ-fix (variant deurq_fix, 2026-09-29): engineering-repair arm on the
# deurc-noctx stack, from the D2 mechanism analysis (analysis/deurq_fix/).
# Three repairs, each behind a default-off flag so every existing variant
# stays byte-identical:
#   F1 utility channel state-only — handled in loop.py (Q pinned uniform
#      {E:0.5}, drop=0) AND the evidence-priority notice is not injected
#      (the QHE-misaligned prior tiers are deleted, not randomized — the
#      sole design delta vs d2_clean's matched-form random notice);
#   F2 FOCUS coverage criterion — focus_min_evidence 4->8 plus at least one
#      E3 (behavioral) probe sampled this episode (early-FOCUS episodes pass
#      42% vs 84% otherwise; KL-graded tasks need distribution-check evidence);
#   F3 KL-type failures exempt from evidence-family attribution (a KL mismatch
#      is an implementation-semantics failure, not an evidence-path failure —
#      the ESCAPE-chain root; full arm fired ESCAPE 43x vs d2_clean 34x).
DEURQ_FIX_CONSTANTS = {**DEURC_NOCTX_CONSTANTS,
                       "focus_min_evidence": 8,
                       "focus_requires_e3": True,
                       "kl_neutral_attribution": True}

# deurq_fsm (v1.1, control-correctness patch, parent d4shell+deurq_fix):
# repairs the state controller's event misclassification (G2/G3), unreachable
# convergence state (G1) and mode oscillation (G4) + one consistency hole
# (G5). Every guard is a default-off flag — all pre-existing variants stay
# byte-identical. G2 opts in via the process registry
# (exp.fcea.utility.commitment_state.fsm_enable_from_constants, called by the
# runner; the loops construct the state manager with the shared frozen
# DEU_CONSTANTS, so the flag cannot travel per-instance). G1/G3/G4/G5 are
# per-episode controller constants. This is a control-correctness patch, NOT
# policy optimization: research question is whether fixing event types,
# convergence reachability and transition stability reduces invalid repair
# trajectories at non-inferior pass. Ablation arms (spec §13):
#   A deurq_fsm_G2G3  — NoSubmit semantic pollution only
#   B deurq_fsm_G1    — termination reachability only
#   C deurq_fsm       — full G1-G5
DEURQ_FSM_G1_CONSTANTS = {**DEURQ_FIX_CONSTANTS,
                          "fsm_g1_terminate": True}
DEURQ_FSM_G2G3_CONSTANTS = {**DEURQ_FIX_CONSTANTS,
                            "fsm_g2_chain": True,
                            "fsm_g3_evidence_guard": True}
DEURQ_FSM_CONSTANTS = {**DEURQ_FIX_CONSTANTS,
                       "fsm_g1_terminate": True,
                       "fsm_g2_chain": True,
                       "fsm_g3_evidence_guard": True,
                       "fsm_g4_hysteresis": True,
                       "fsm_g5_best_q": True}

# deurq_base (基座, v1 2026-10-01): the corrected-mechanism mainline. Parent
# = deurc_noctx (the published DEU-RQ arm) + the deurq_fsm guards (G1-G5,
# controller/state-side, see analysis/deurq_fsm/) + the execution guards
# (loop-side, exp/fcea/control/execution_guard.py: corrective length-cut
# retry + fuse, fallback artifact gate, slot salvage). Targets the three
# documented mechanism defects — state-transition faults (TERMINATE 0/484,
# oscillation 124 flips, NS misclassification) and execution waste
# (nosubmit slots, 40960-token burns incl. /148, truncated-residue submits).
# This is the BASE for the upcoming error-class optimizations: MECH-1
# (framework-interface / ENV, docs/book/new.md) and semantic-planning work
# layer ON TOP of it as additional default-off flags; nothing here conflicts
# with those hooks. All flags default False elsewhere -> legacy variants
# byte-identical. Research question: does the corrected controller + waste
# elimination hold or improve pass at equal protocol (QB+/QHE 42x3 vs the
# frozen deurc_noctx mainline)?
DEURQ_BASE_CONSTANTS = {**DEURC_NOCTX_CONSTANTS,
                        "fsm_g1_terminate": True,
                        "fsm_g2_chain": True,
                        "fsm_g3_evidence_guard": True,
                        "fsm_g4_hysteresis": True,
                        "fsm_g5_best_q": True,
                        "exec_retry_corrective": True,
                        "exec_length_fuse_cap": 2,
                        "exec_artifact_gate": True,
                        "exec_slot_salvage": True,
                        "exec_probe_budget": True}

# deurq_z1 (E1 = ReAct-scaffold + Z1 only): BatchProbe substrate + the SAME
# execution-hygiene set as the ladder, with the whole Z2 decision stack OFF
# (no controller, no C1/C2, no evidence-priority notice — the notice belongs
# to Z2 per the v2 audit C2 decision). Adjacent-arm rule: E2 - E1 = Z2 only.
DEURQ_Z1_CONSTANTS = {**DEURC_NOCTX_CONSTANTS,
                      "exec_retry_corrective": True,
                      "exec_length_fuse_cap": 2,
                      "exec_artifact_gate": True,
                      "exec_slot_salvage": True,
                      "exec_probe_budget": True}

# deurq_baseenv (E3 = final): deurq_base + the frozen mech1_rep mechanism set
# (Z3, framework-interface repair; docs/book/new.md). Dual-channel wiring:
# these constants feed the controller-side gates, while
# control/mech_flags.EXPERIMENTAL_ARM_FLAGS feeds the loop-side hooks.
# Defined after the MECH imports below (see DEURQ_BASEENV_CONSTANTS).

# MECH-1 (variant mech1_prev/rep/full, protocol frozen 2026-09-30):
# docs/实验MECH-1_协议.md. Engineering-repair arms on the deurc-noctx stack;
# every mechanism is a default-off flag in exp/fcea/control/mech_flags.py, so
# all pre-existing variants stay byte-identical. Arm semantics:
#   prev = E(env probe) + A(api tool) + B(preflight)
#   rep  = A + B + C(ledger) + D-F(FOCUS coverage gate) + D1(auto probe) + v2 text
#   full = all of the above
from exp.fcea.control.mech_flags import MECH_ARM_FLAGS as _MECH_ARM_FLAGS  # noqa: E402
from exp.fcea.control.mech_flags import MECH_CONSTANTS as _MECH_CONSTANTS  # noqa: E402

MECH1_AUTO_MAX_PER_EPISODE = _MECH_CONSTANTS["auto_probe_max_per_episode"]
MECH1_AUTO_MAX_PER_BOUNDARY = _MECH_CONSTANTS["auto_probe_max_per_boundary"]
MECH1_PREFLIGHT_REJECT_CAP_PER_SHOT = _MECH_CONSTANTS["preflight_reject_cap_per_shot"]

def _mech1_constants(arm: str) -> dict:
    c = {**DEURC_NOCTX_CONSTANTS}
    c.update({k: True for k, v in _MECH_ARM_FLAGS[arm].items() if v})
    return c

MECH1_PREV_CONSTANTS = _mech1_constants("mech1_prev")
MECH1_REP_CONSTANTS = _mech1_constants("mech1_rep")
MECH1_FULL_CONSTANTS = _mech1_constants("mech1_full")

# deurq_baseenv (E3 = final): deurq_base + the frozen mech1_rep mechanism set
DEURQ_BASEENV_CONSTANTS = {
    **DEURQ_BASE_CONSTANTS,
    **{k: True for k, v in _MECH_ARM_FLAGS["mech1_rep"].items() if v}}

# E3-new (variant deurq_baseenv_v2, 2026-10-01 freeze; superseded tag for the
# era-1 legacy arm deurq_baseenv — see analysis/deurq_base/E3NEW_MANIFEST.json).
# Z3_complete = the SAME frozen mech1_rep mechanism set as legacy E3 plus the
# acceptance-pipeline completion, both default-off flags so every other
# variant stays byte-identical:
#   z3_gate_salvage   — end-of-shot salvage runs the acceptance gates; a
#                       gate-rejected candidate consumes the slot as NoSubmit
#                       (supersedes the legacy FAIL-OPEN bypass, loop.py)
#   z3_fallback_gate  — the no-tool-call fallback submit path passes the Z3
#                       preflight before the official grade (submission-path
#                       coverage; non-official rejection on failure)
DEURQ_BASEENV_V2_CONSTANTS = {
    **DEURQ_BASEENV_CONSTANTS,
    "z3_gate_salvage": True,
    "z3_fallback_gate": True,
}

# E4 (variant deurq_final): E3-new + Z4 semantic alignment gate
# (exp/fcea/control/acceptance.py Z4Gate; frozen A16 v2 probe machinery with
# the E4 armed lifecycle). z4_arm_defer_when_z3 implements arm-now/probe-later:
# when a Z3 contract gap co-triggers at the same failure boundary, Z4 records
# the expectation but defers its L1 probe to the next boundary (Z3-first).
DEURQ_FINAL_CONSTANTS = {
    **DEURQ_BASEENV_V2_CONSTANTS,
    "z4_trace_gate": True,
    "z4_arm_defer_when_z3": True,
}

# D-ladder (2026-10-03, user-directed Z2 ablation on deepseek-flash):
#   D2 = E3 − Z2 (variant deurq_baseenv_noz2): Z1 constants (Z0 exec guards +
#        BatchProbe substrate, the ladder's shared hygiene layers) + the frozen
#        mech1_rep Z3 mechanism set. Z2 (evidence notice + deu_state tracking +
#        FSM G1–G5) is removed by construction: the variant mirrors
#        deurq_z1's Z2 anatomy — absent from the loop's deu_state tuple and
#        FSM enable lists, and excluded from the notice injection gate.
#   D3 = E4 − Z2 (variant deurq_final_noz2): D2 + the Z3 acceptance-pipeline
#        completion (z3_gate_salvage / z3_fallback_gate) + the Z4 semantic
#        alignment gate (z4_trace_gate / z4_arm_defer_when_z3), same Z2 removal.
# Adjacent-arm contract: D2 − D1 isolates Z3 without Z2; D3 − D2 isolates Z4
# without Z2; D2 vs E3 and D3 vs E4 isolate Z2's contribution at fixed Z3/Z4.
DEURQ_BASEENV_NOZ2_CONSTANTS = {
    **DEURQ_Z1_CONSTANTS,
    **{k: True for k, v in _MECH_ARM_FLAGS["mech1_rep"].items() if v}}
DEURQ_FINAL_NOZ2_CONSTANTS = {
    **DEURQ_BASEENV_NOZ2_CONSTANTS,
    "z3_gate_salvage": True,
    "z3_fallback_gate": True,
    "z4_trace_gate": True,
    "z4_arm_defer_when_z3": True,
}

# D3 (variant d3, full − C1): state layer blinded (controller flag) + utility
# pinned to the frozen prior Q0 (no EMA updates → utility_drop ≡ 0). With the
# state path dead, TERMINATE (needs no_progress ≥ 2) and ESCAPE (needs branch
# failure attribution) are unreachable; the controller degrades to
# utility-only, episode-blind steering (SEARCH + the utility-driven FOCUS).
D3_CONSTANTS = {**DEURC_NOCTX_CONSTANTS, "state_blind": True}

# rq4b (2026-09-30, PROTOCOL v2.1 — analysis/agent_ceiling_analysis/
# PROTOCOL_rq4b_trace_replan.md): three arms on the unchanged deurc-noctx
# stack. All mechanism constants live in exp/fcea/control/rq4b.py (frozen);
# these dicts only register the variants with the noctx constants so the
# state/controller plumbing treats them as DEU-RQ stack members.
#   deurc_trace   A|trace: informative-assertion trigger + self-constructed
#                 trace probes + soft obligation gate (QHE)
#   deurc_restart B1: late-stall shot-3 restart (context surgery, neutral)
#   deurc_replan  B2: + strategy-invalidation sentence pair (QB+)
RQB_TRACE_CONSTANTS = {**DEURC_NOCTX_CONSTANTS, "rq4b_trace": True}
RQB_RESTART_CONSTANTS = {**DEURC_NOCTX_CONSTANTS, "rq4b_replan_kind": "restart"}
RQB_REPLAN_CONSTANTS = {**DEURC_NOCTX_CONSTANTS, "rq4b_replan_kind": "replan"}

# rq4b A16 (2026-10-01, PROTOCOL_rq4b_A16.md): forced-contract probe v2 on the
# unchanged deurc-noctx stack, variant deurc_trace_v2. Mechanism constants in
# exp/fcea/control/rq4b.py (TRACE_*), probe runner in control/trace_probe.py.
# v1 deurc_trace stays byte-identical; v2 = v1 A1 contract + harness L1
# boundary auto-probe + L2 Eval tri-state interception + L3 model channel.
RQB_TRACE_V2_CONSTANTS = {**DEURC_NOCTX_CONSTANTS, "rq4b_trace_v2": True}

# DCC (variant dcc, 2026-09-29): Depth-Conditioned Commitment Controller on
# the unchanged deurc-noctx stack — the decision layer is REPLACED by the
# frozen depth schedule (exp/fcea/dcc/policy.py: depth1 SEARCH / depth2 FOCUS
# / depth>=3 COMMIT, only input = failure_depth). Stack constants identical
# to deurc_noctx (context gate off, matching DEU-RQ/D3); the state/utility
# machinery keeps running for trace parity and is ignored by the controller.
from exp.fcea.dcc import DEFAULT_CONSTANTS as _DCC_DEFAULTS  # noqa: E402
DCC_CONSTANTS = dict(_DCC_DEFAULTS)

# Frozen QHE-only utility prior (built by analysis/rq4_fcea/build_prior.py).
PRIOR_PATH = Path(__file__).resolve().parents[2] / "analysis/rq4_fcea/qhe_evidence_utility_prior.json"


def set_variant(v: str) -> None:
    global VARIANT
    if v not in VARIANTS:
        raise ValueError(f"unknown FCEA variant {v!r}; expected one of {VARIANTS}")
    VARIANT = v


def set_action_seed(seed: int | None) -> int:
    """Repetition runs: override the deurand selector seed; None restores the
    frozen 20260923. Returns the effective seed. Behavior of deuact is
    unchanged either way (its selector is deterministic)."""
    global DEUACT_CONSTANTS
    frozen = _DEUACT_DEFAULTS["random_seed"]
    DEUACT_CONSTANTS = {**DEUACT_CONSTANTS,
                        "random_seed": frozen if seed is None else int(seed)}
    return DEUACT_CONSTANTS["random_seed"]


def variant_suffix() -> str:
    return f"_{VARIANT}"


def default_tag(*, bench: str = "qhe", dev: bool = False,
                framework: str = "qiskit") -> str:
    bench = (bench or "qhe").strip().lower()
    fw = (framework or "qiskit").strip().lower()
    tag = TAG_PREFIX
    if bench == "qbplus":
        tag += "_qbplus"
    # e9 pattern (2026-09-25): non-qiskit QB+ runs carry an explicit framework
    # suffix so the three QB+ suites never share a results directory.
    if bench == "qbplus" and fw not in ("", "qiskit"):
        tag += f"_{fw}"
    if dev and not tag.endswith("_dev"):
        tag += "_dev"
    return tag + variant_suffix()


def refuse_foreign_tag(tag: str) -> None:
    t = (tag or "").strip()
    if not t.startswith(TAG_PREFIXES):
        raise ValueError(
            f"REFUSE: fcea writes only {TAG_PREFIXES}* tags, got {t!r}. "
            "Historical e4_*/e7_* results are frozen and untouchable."
        )


def prior_sha256() -> str:
    return hashlib.sha256(PRIOR_PATH.read_bytes()).hexdigest()


def prior_summary() -> dict:
    d = json.loads(PRIOR_PATH.read_text(encoding="utf-8"))
    return {
        "path": str(PRIOR_PATH),
        "sha256": prior_sha256(),
        "generated_at_utc": d.get("generated_at_utc"),
        "global_tiers": d["global"]["tiers"],
        "per_context_tiers": {f: v["tiers"] for f, v in d["per_context"].items()},
        "source": d["provenance"]["source_dataset"],
    }


# System prompt: IDENTICAL for variants global and fcond (the treatment delta
# is only the injected priority content). Extends the Batch-EQPA system prompt
# with the evidence taxonomy used by the utility prior and the soft-guidance
# rule. The tool schema already asks the model to label queries with a kind.
FCEA_SYSTEM = (
    "You solve one Qiskit programming task against the live interpreter. "
    "Hidden tests are not provided. The host benchmark repository is not visible. "
    "Use BatchProbe to inspect installed Qiskit: it runs a small batch of shell "
    "commands in the isolated environment in ONE round and returns structured, "
    "clipped evidence per command. Group related inspections into a single "
    "BatchProbe call (API signatures, versions, object construction, and small "
    "behavioral experiments belong together); do not spend one call per fact. "
    "Label each query with its kind: api, behavior, runtime, or env. "
    "Evidence kinds map to utility categories: api and env collect environment "
    "facts (E1), runtime collects execution feedback from minimal repros (E2), "
    "behavior collects self-designed behavioral experiments such as statevector "
    "or counts checks (E3). "
    "After a failure you may receive an evidence-priority notice. Treat it as "
    "soft guidance: prefer evidence categories with higher estimated utility, "
    "but you may use another category when the current program or error "
    "provides a concrete reason. The notice labels the observed failure style "
    "only; it is not a root-cause claim. "
    "Scratch files belong in /tmp. /workspace is read-only. "
    "Submit with Write using the exact filename attempt_1.py, attempt_2.py, or attempt_3.py, "
    "then call Eval() to run official tests. Do not try to read dataset, sealed, or grader files."
)

FCEA_TOOL = bcfg.BATCH_TOOL  # identical tool schema (kinds api/behavior/runtime/env)


def fcea_system(framework: str = "qiskit") -> str:
    """Framework-parametrized system prompt (e9 pattern, 2026-09-25).
    qiskit returns FCEA_SYSTEM byte-identical; the cirq/pennylane variants
    swap only the framework facts (both 'Qiskit' occurrences), keeping the
    notice-guidance and submission sentences untouched."""
    fw = (framework or "qiskit").strip().lower()
    if fw == "qiskit":
        return FCEA_SYSTEM
    name = {"cirq": "Cirq", "pennylane": "PennyLane"}.get(fw, fw.capitalize())
    return FCEA_SYSTEM.replace("Qiskit", name)


def batch_frozen_constants() -> dict:
    return {
        "arm": ARM_NAME,
        "variant": VARIANT,
        "max_llm_per_shot": MAX_LLM_PER_SHOT,
        "max_official": MAX_OFFICIAL,
        "max_queries_per_batch": MAX_QUERIES_PER_BATCH,
        "probe_timeout_s": PROBE_TIMEOUT_S,
        "probe_max_chars": PROBE_MAX_CHARS,
        "max_probes_per_shot": MAX_PROBES_PER_SHOT,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "prior": prior_summary(),
    }


def config_hashes() -> dict:
    here = Path(__file__).resolve().parent
    out = {}
    for name in ("prompts.py", "loop.py", "config.py", "run.py", "adapter.py",
                 "action_selector.py",
                 "control/control_index.py", "control/mode_selector.py",
                 "control/mode_selector_noescape.py",
                 "control/evidence_gate.py", "control/context_gate.py",
                 "control/controller.py", "control/rq4b.py",
                 "control/acceptance.py",
                 "utility/prior.py", "utility/scorer.py", "utility/noise.py",
                 "evidence/taxonomy.py", "evidence/planner.py",
                 "dcc/policy.py", "dcc/controller.py", "dcc/logging.py"):
        p = here / name
        if p.is_file():
            out[name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out
