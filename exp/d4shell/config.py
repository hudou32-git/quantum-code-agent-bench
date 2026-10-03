"""D4 (full − C0) runner config: DEU-RQ's utility + controller re-implemented
over the EQPA free-form Shell substrate.

D4 removes C0 (the BatchProbe backbone): the whole decision loop must act
through free-form Shell. Per the frozen implementation plan (攻关.md RQ3):
prompt semantics, utility computation, controller rules, budget policy and
termination protocol are UNCHANGED; only interface-necessary adaptations
differ, each recorded in the GATE 4 manifest deviation list:

  D4-1  evidence family attribution: Shell outputs carry no requested-kind
        channel — the frozen output classifier (taxonomy.py) supplies the
        category; requested_evidence_kind is empty in traces.
  D4-2  the evidence gate's execution-layer query filtering has no attachment
        point on free-form commands: blocked-family enforcement degrades to
        the prompt layer (the directive's Forbidden Evidence line); the
        controller's decision is still logged in control_log.
  D4-3  tool-layer withdrawal mirrors the frozen deurc semantics exactly: the
        withdrawn tool stays in the tools list and refusal happens at
        execution (controller refusal message; the frozen fcea tools-list
        filter is a no-op — BATCH_TOOL has no top-level "name" field — and
        D4 deliberately reproduces the same observable mechanism rather than
        the stricter design-intent variant, so C3's commitment strength is
        unchanged between the compared arms).
  D4-4  probe budget: BatchProbe's per-batch caps (5 queries / 8 s / 900
        chars) do not exist on Shell; the substrate's native per-attempt cap
        MAX_SHELL_PER_SHOT=8 and its budget notice apply.
  D4-5  system prompt: the two BatchProbe sentences and the kind-labeling
        sentence are replaced by the Shell sentence and an output-classification
        sentence; the workspace block's inspect line likewise names Shell
        (exp.eqpa.tools.workspace_block); every other sentence (notice
        guidance, submission contract) is byte-identical to FCEA_SYSTEM.
  D4-6  Shell commands run with the EQPA substrate's sandbox defaults (no
        per-probe timeout/clip); canary gate identical.

C1 (state manager), C2 (frozen prior + EMA updater, sha-frozen prior file),
C3 (RepairController, deurc_noctx constants incl. context gate OFF) are
imported unchanged from exp.fcea — zero rule drift by construction.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from exp import config
from exp.evidence_eqpa import config as bcfg
from exp.fcea import config as fcfg
from exp.fcea.control.controller import DEFAULT_CONSTANTS as _RC_DEFAULTS

ARM_NAME = "D4"
TAG_PREFIX = "rq4_d4shell"

# ---- protocol pins: identical to the FCEA/EQPA line ----
MAX_LLM_PER_SHOT = bcfg.MAX_LLM_PER_SHOT          # 16
MAX_OFFICIAL = bcfg.MAX_OFFICIAL                  # 3
MAX_SHELL_PER_SHOT = 8                            # EQPA substrate native cap

# Controller: the full DEU-RQ stack (deurc_noctx) — context gate OFF, hard
# FOCUS, ESCAPE on. Byte-identical constants to the Phase A arm.
D4_CONTROLLER_CONSTANTS = dict(_RC_DEFAULTS)
D4_CONTROLLER_CONSTANTS.update(fcfg.DEURC_NOCTX_CONSTANTS)

EQPA_DEV_CASES = fcfg.EQPA_DEV_CASES

D4_SYSTEM = (
    "You solve one Qiskit programming task against the live interpreter. "
    "Hidden tests are not provided. The host benchmark repository is not visible. "
    "Use Shell to inspect installed Qiskit (python, importlib, inspect, ls). "
    "Shell outputs are classified into evidence categories: environment facts "
    "such as API signatures, versions, and imports (E1), execution feedback "
    "from minimal repros (E2), and self-designed behavioral experiments such "
    "as statevector or counts checks (E3). "
    "After a failure you may receive an evidence-priority notice. Treat it as "
    "soft guidance: prefer evidence categories with higher estimated utility, "
    "but you may use another category when the current program or error "
    "provides a concrete reason. The notice labels the observed failure style "
    "only; it is not a root-cause claim. "
    "Scratch files belong in /tmp. /workspace is read-only. "
    "Submit with Write using the exact filename attempt_1.py, attempt_2.py, or attempt_3.py, "
    "then call Eval() to run official tests. Do not try to read dataset, sealed, or grader files."
)


def prompt_sentence_diff_ok() -> bool:
    """Deviation D4-5 guard: D4_SYSTEM must be FCEA_SYSTEM with ONLY the
    BatchProbe/kind sentences swapped for the Shell/classification sentences;
    the remaining sentences (split on ' ') must match one-to-one."""
    a = [s for s in fcfg.FCEA_SYSTEM.split(". ") if s.strip()]
    b = [s for s in D4_SYSTEM.split(". ") if s.strip()]
    swapped = {"Use BatchProbe to inspect installed Qiskit: it runs a small batch of shell "
               "commands in the isolated environment in ONE round and returns structured, "
               "clipped evidence per command",
               "Group related inspections into a single BatchProbe call (API signatures, "
               "versions, object construction, and small behavioral experiments belong "
               "together); do not spend one call per fact",
               "Label each query with its kind: api, behavior, runtime, or env",
               "Evidence kinds map to utility categories: api and env collect environment "
               "facts (E1), runtime collects execution feedback from minimal repros (E2), "
               "behavior collects self-designed behavioral experiments such as statevector "
               "or counts checks (E3)",
               "Use Shell to inspect installed Qiskit (python, importlib, inspect, ls)",
               "Shell outputs are classified into evidence categories: environment facts "
               "such as API signatures, versions, and imports (E1), execution feedback "
               "from minimal repros (E2), and self-designed behavioral experiments such as "
               "statevector or counts checks (E3)"}
    kept_a = [s for s in a if not any(s.startswith(w[:40]) for w in swapped)]
    kept_b = [s for s in b if not any(s.startswith(w[:40]) for w in swapped)]
    return kept_a == kept_b and len(a) - len(kept_a) == 4 and len(b) - len(kept_b) == 2


def refuse_foreign_tag(tag: str) -> None:
    t = (tag or "").strip()
    if not t.startswith(TAG_PREFIX):
        raise ValueError(
            f"REFUSE: d4shell writes only {TAG_PREFIX}* tags, got {t!r}. "
            "Historical results are frozen and untouchable.")


def default_tag(*, bench: str = "qbplus", dev: bool = False) -> str:
    bench = (bench or "qbplus").strip().lower()
    tag = TAG_PREFIX
    if bench == "qbplus":
        tag += "_qbplus"
    if dev and not tag.endswith("_dev"):
        tag += "_dev"
    return tag


def d4_deviation_record() -> dict:
    """The GATE 4 manifest d_variants.D4 deviation list (final wording)."""
    return {
        "removed_component": "C0 (BatchProbe backbone / acquisition channel)",
        "substrate": "EQPA free-form Shell + Write + Eval (exp.eqpa.tools, unchanged)",
        "unchanged": [
            "C1 state manager (exp.fcea.utility.state, same instance semantics)",
            "C2 frozen prior Q0 + episode-dynamic EMA updater (prior file sha-frozen)",
            "C3 RepairController with deurc_noctx constants (context gate OFF)",
            "utility_notice evidence-priority notice (frozen global tiers)",
            "official budget (MAX_OFFICIAL=3), per-shot LLM budget (16), "
            "termination protocol, NoSubmit penalty, fallback submit, canary gate",
        ],
        "interface_adaptations": [
            "D4-1 evidence family attribution by output classification only "
            "(no requested-kind channel on Shell)",
            "D4-2 execution-layer query filtering unenforceable on free-form "
            "commands; evidence-gate blocking degrades to the prompt layer "
            "(decision still logged)",
            "D4-3 FOCUS/TERMINATE withdrawal = execution-layer refusal on "
            "Shell, mirroring the frozen deurc mechanism (tools-list filter "
            "is a no-op in the frozen stack; D4 reproduces the observable "
            "semantics, not the stricter design-intent variant)",
            "D4-4 probe budget = substrate-native MAX_SHELL_PER_SHOT=8 with "
            "the Shell budget notice (BatchProbe batch caps do not exist here)",
            "D4-5 system prompt: BatchProbe/kind sentences swapped for "
            "Shell/classification sentences; workspace block inspect line "
            "names Shell (eqpa variant); all other sentences byte-identical",
            "D4-6 Shell runs with EQPA sandbox defaults (no per-probe "
            "timeout/clip); canary gate identical",
        ],
    }


def config_hashes() -> dict:
    here = Path(__file__).resolve().parent
    out = {}
    for name in ("config.py", "loop.py", "run.py"):
        p = here / name
        if p.is_file():
            out["d4shell/" + name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    out["fcea/config.py"] = hashlib.sha256(
        (here.parent / "fcea" / "config.py").read_bytes()).hexdigest()[:16]
    out["fcea/control/controller.py"] = hashlib.sha256(
        (here.parent / "fcea" / "control" / "controller.py").read_bytes()).hexdigest()[:16]
    return out


def batch_frozen_constants() -> dict:
    return {
        "arm": ARM_NAME,
        "variant": "d4_shell",
        "max_llm_per_shot": MAX_LLM_PER_SHOT,
        "max_official": MAX_OFFICIAL,
        "max_shell_per_shot": MAX_SHELL_PER_SHOT,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "prior": fcfg.prior_summary(),
        "controller_constants": "exp.fcea.config.DEURC_NOCTX_CONSTANTS",
    }
