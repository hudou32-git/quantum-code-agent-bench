"""D5 (d5conv) runner config: d4shell + four conversion mechanisms.

d5conv = d4shell + tool budget enforcement (A1, D5-1) + end-of-shot deadline
conversion ladder (A2, D5-2) + corrective length retry (B1, D5-3) + fallback
artifact gate (B2, D5-4). Frozen design: docs/protocols/d5conv_design_20261001.md.

Everything not listed in d5_deviation_record() is imported unchanged from
exp.d4shell (which itself imports the DEU stack unchanged from exp.fcea) —
zero rule drift by construction. Each mechanism sits behind its own constant
so any of them can be ablated by config alone.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from exp import config
from exp.d4shell import config as d4cfg
from exp.fcea import config as fcfg

ARM_NAME = "D5"
TAG_PREFIX = "rq4_d5conv"

# ---- protocol pins: re-exported from d4shell (identical bytes) ----
MAX_LLM_PER_SHOT = d4cfg.MAX_LLM_PER_SHOT          # 16
MAX_OFFICIAL = d4cfg.MAX_OFFICIAL                  # 3
MAX_SHELL_PER_SHOT = d4cfg.MAX_SHELL_PER_SHOT      # 8
EQPA_DEV_CASES = d4cfg.EQPA_DEV_CASES
D4_CONTROLLER_CONSTANTS = d4cfg.D4_CONTROLLER_CONSTANTS
# System prompt: byte-identical to the frozen D4_SYSTEM by construction.
D5_SYSTEM = d4cfg.D4_SYSTEM

# ---- D5 mechanisms (independently switchable for ablation) ----
# D5-1 / A1: after MAX_SHELL_PER_SHOT executed shells, further Shell calls in
# the same shot are refused at execution layer (no run, no evidence).
SHELL_BUDGET_HARD = True
# D5-2 / A2: deadline ladder. Thresholds are llm_this values (calls already
# consumed in the shot); the ladder is evaluated pre-call, so ESCALATE_AT=12
# fires before call 13 and NARROW_AT=14 before call 15. After NARROW_AT the
# tools list for the rest of the shot is [Write, Eval] only (invariant I-1).
CONVERT_ESCALATE_AT = 12
CONVERT_NARROW_AT = 14
# D5-3 / B1: on a length-cut response with no tool calls, inject the
# corrective directive BEFORE the single resample; truncated assistant
# messages are discarded (never appended, never re-sent).
RETRY_CORRECTIVE = True
# D5-4 / B2: fallback official submissions (code extracted from a no-tool-call
# reply) must pass the frozen preflight (compile+exec) first; failed ->
# non-official feedback, attempt preserved; indeterminate -> fail open.
FALLBACK_ARTIFACT_GATE = True

# ---- E0 (ReAct+Z0) switches, 2026-10-01 ladder audit ----
# All default to the legacy d5conv behavior; the E0 preset (set_react_e0)
# flips them for the ablation baseline. They exist so E0's Z0 set matches the
# fcea-side ladder arms exactly (audit C1): probe hard budget (A1) +
# corrective retry + length fuse + artifact gate + slot salvage, ladder OFF,
# and the whole Z2 decision stack OFF (controller, notices, C1/C2 bookkeeping).
CONTROLLER_OFF = False
CONVERT_LADDER_OFF = False
LENGTH_FUSE_CAP = None          # None = legacy (no episode-level fuse); E0: 2
SLOT_SALVAGE = False            # E0: True (grade written-but-unevaluated at close)

_E0_FLAGS = ("CONTROLLER_OFF", "CONVERT_LADDER_OFF", "LENGTH_FUSE_CAP",
             "SLOT_SALVAGE")
_E0_PRESET = {"CONTROLLER_OFF": True, "CONVERT_LADDER_OFF": True,
              "LENGTH_FUSE_CAP": 2, "SLOT_SALVAGE": True}


def set_react_e0(on: bool) -> dict:
    """Flip the E0 preset. Returns the previous flag values for restore."""
    prev = {k: globals()[k] for k in _E0_FLAGS}
    for k in _E0_FLAGS:
        globals()[k] = _E0_PRESET[k] if on else prev[k]
    return prev

# ---- frozen message templates (format fields noted per template) ----
# A1_REFUSAL: {used} {cap} {k}
A1_REFUSAL = (
    "Shell budget for this attempt is exhausted ({used}/{cap} used). "
    "Shell will not run again in this attempt. "
    "Call Write with path attempt_{k}.py, then call Eval()."
)
# A2_S1: {k} {left}
A2_S1 = (
    "Attempt {k} deadline: only {left} model calls remain before this attempt "
    "is closed without a submission. Write attempt_{k}.py now and call Eval() "
    "to grade it."
)
# A2_S2_WRITE: {k}
A2_S2_WRITE = (
    "Attempt {k} deadline: Shell is disabled for the rest of this attempt; "
    "only Write and Eval are available. Write attempt_{k}.py now and call Eval()."
)
# A2_S2_EVAL: {k}
A2_S2_EVAL = (
    "Attempt {k} deadline: Shell is disabled for the rest of this attempt. "
    "attempt_{k}.py is on disk — call Eval() now to grade it."
)
# A2_S2_FIX: {k}
A2_S2_FIX = (
    "Attempt {k} deadline: Shell is disabled for the rest of this attempt; "
    "only Write and Eval are available. The last saved attempt_{k}.py failed "
    "to run standalone — Write a fixed attempt_{k}.py and call Eval()."
)
A2_DEADLINE_REFUSAL = (
    "Shell is disabled for the rest of this attempt (deadline). "
    "Only Write and Eval are available."
)
# B1_CORRECTIVE: {k}
B1_CORRECTIVE = (
    "Your previous reply hit the output token limit and was discarded; "
    "no tool call ran. Do not restate analysis. Reply with exactly one "
    "tool call: Write attempt_{k}.py with the complete module, or one "
    "short Shell command."
)
# B2_REJECT: {k} {tb}
B2_REJECT = (
    "Your last reply contained a code block; it was saved to attempt_{k}.py "
    "but FAILS to run standalone, so it was NOT submitted for official "
    "grading (no attempt consumed): {tb} Fix the module and resubmit."
)


def mechanism_invariants_ok() -> bool:
    """Design invariants: ladder strictly inside the per-shot budget."""
    return (
        0 < CONVERT_ESCALATE_AT < CONVERT_NARROW_AT < MAX_LLM_PER_SHOT
        and MAX_SHELL_PER_SHOT >= 1
    )


def refuse_foreign_tag(tag: str) -> None:
    t = (tag or "").strip()
    if not t.startswith(TAG_PREFIX):
        raise ValueError(
            f"REFUSE: d5conv writes only {TAG_PREFIX}* tags, got {t!r}. "
            "Historical results are frozen and untouchable.")


def default_tag(*, bench: str = "qbplus", dev: bool = False) -> str:
    bench = (bench or "qbplus").strip().lower()
    tag = TAG_PREFIX
    if bench == "qbplus":
        tag += "_qbplus"
    if dev and not tag.endswith("_dev"):
        tag += "_dev"
    return tag


def d5_deviation_record() -> dict:
    """Deviations relative to frozen d4shell (design doc §8)."""
    return {
        "base": "exp.d4shell (frozen)",
        "mechanisms": [
            "D5-1 (A1) shell budget hard enforcement: soft one-time notice "
            "upgraded to execution-layer refusal after MAX_SHELL_PER_SHOT "
            "executed shells in the shot; notice text unchanged",
            "D5-2 (A2) deadline conversion ladder: escalation message at "
            "call 13 (llm_this>=12) and Shell removal from the tools list "
            "from call 15 (llm_this>=14) while the shot has no official "
            "eval; the removal uses a working function.name filter (the "
            "frozen fcea/d4shell filter was a no-op by design, D4-3)",
            "D5-3 (B1) corrective length retry: corrective user message "
            "injected before the single resample; truncated assistant "
            "messages (including a resample that also cuts) are discarded "
            "instead of appended",
            "D5-4 (B2) fallback artifact gate: code extracted from a "
            "no-tool-call reply passes the frozen preflight (compile+exec, "
            "fail-open on indeterminate) before consuming an official "
            "attempt; explicit Eval tool calls are NOT gated",
            "D5-6 (2026-10-01) streaming transport: the runner client opts "
            "into SSE streaming for all calls including tool calls (guard "
            "stays detect — no mid-stream aborts). Rationale: the e7 "
            "tool-caller non-stream exemption assumed short structured "
            "outputs; D5 Write contents carry whole modules (single 40960-"
            "token tool calls observed), and the non-stream 600s read "
            "timeout is a total-generation wall — a transient throughput "
            "drop below ~68 tok/s deterministically killed the episode "
            "(case-26 ReadTimeout hole, 3x600s exhausted). This exercises "
            "the revisit clause pre-registered in e7_repeat_guard_design.md "
            "(risk register #3). Streaming is transport-only: sampling, "
            "budgets and guard semantics unchanged; legacy non-stream "
            "fallback retained (raw.transport_fallback).",
        ],
        "unchanged": [
            "C1 state manager, C2 frozen prior + EMA updater, C3 "
            "RepairController (deurc_noctx constants, context gate OFF)",
            "system prompt (byte-identical D4_SYSTEM), budgets 16/8/3, "
            "T=0.6, MAX_TOKENS=40960, termination protocol, NoSubmit "
            "accounting (official += 1 retained; A3 not adopted)",
            "controller FOCUS/TERMINATE execution-layer withdrawal, "
            "evidence-priority notices, canary gate, sandbox defaults",
        ],
        "excluded_this_round": [
            "A3 slot-salvage auto-eval", "A4 FSM guard (nosubmit->FOCUS pin)",
            "B3 per-call max_tokens reduction", "B4 shell-output clipping",
        ],
    }


def config_hashes() -> dict:
    here = Path(__file__).resolve().parent
    out = {}
    for name in ("config.py", "loop.py", "run.py"):
        p = here / name
        if p.is_file():
            out["d5conv/" + name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    out["d4shell/config.py"] = hashlib.sha256(
        (here.parent / "d4shell" / "config.py").read_bytes()).hexdigest()[:16]
    out["fcea/control/controller.py"] = hashlib.sha256(
        (here.parent / "fcea" / "control" / "controller.py").read_bytes()).hexdigest()[:16]
    return out


def batch_frozen_constants() -> dict:
    return {
        "arm": ARM_NAME,
        "variant": "d5_conv",
        "max_llm_per_shot": MAX_LLM_PER_SHOT,
        "max_official": MAX_OFFICIAL,
        "max_shell_per_shot": MAX_SHELL_PER_SHOT,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "prior": fcfg.prior_summary(),
        "controller_constants": "exp.fcea.config.DEURC_NOCTX_CONSTANTS",
        "d5_mechanisms": {
            "shell_budget_hard": SHELL_BUDGET_HARD,
            "convert_escalate_at": CONVERT_ESCALATE_AT,
            "convert_narrow_at": CONVERT_NARROW_AT,
            "retry_corrective": RETRY_CORRECTIVE,
            "fallback_artifact_gate": FALLBACK_ARTIFACT_GATE,
        },
        "transport": "stream (SSE, all calls incl. tool calls; guard=detect; "
                     "non-stream fallback retained) — D5-6",
    }
