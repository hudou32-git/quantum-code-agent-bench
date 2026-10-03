"""Evidence branch control: per-family reversible gating.

EvidenceBranchState per probeable family (E1/E2/E3):

    {"family", "attempts", "failures", "q_value", "status",
     "seen_signatures", "nov_mean_prev"}

Status machine (rq4_deurc_design.md §evidence gate):
    ACTIVE -> DEGRADED  failures >= degrade_family_failures
    DEGRADED/BLOCKED -> BLOCKED   failures >= block_family_failures AND
                                  information gain non-increasing ("novelty
                                  decreases" operationalized as the DEU-v3
                                  adapter does: falling step novelty, or zero
                                  novelty = no new information)
    BLOCKED -> RECOVERABLE        a NEW error signature appears (the repair
                                  left the failed path)
    RECOVERABLE -> ACTIVE         another new signature follows (path changed)
    RECOVERABLE -> BLOCKED        the old signature repeats (recovery failed)

A BLOCKED family cannot be selected by the planner (BatchProbe queries of its
kinds are not executed; reversible — unblocked families run normally).

Key property (task 32 oscillation "KL / ValueError / KL"): failures accumulate
across ERROR-TEXT CHANGES on the same family. The DEU-v2 same_error counter
resets on unclear transitions; the branch state does not — only a genuinely
new error signature changes the recovery state.
"""
from __future__ import annotations

import re

from exp.fcea.utility.state import norm_err      # frozen helper, read-only use

PROBEABLE = ("E1", "E2", "E3")
FAMILY_KINDS = {"E1": ("api", "env"), "E2": ("runtime",), "E3": ("behavior",)}
KIND_TO_FAMILY = {k: fam for fam, kinds in FAMILY_KINDS.items() for k in kinds}

ACTIVE = "ACTIVE"
DEGRADED = "DEGRADED"
BLOCKED = "BLOCKED"
RECOVERABLE = "RECOVERABLE"

DEFAULT_CONSTANTS = {
    "degrade_family_failures": 2,
    "block_family_failures": 3,
    "escape_family_failures": 2,     # ESCAPE-worthy: failures >= N with
                                     # non-increasing gain (DEGRADED/BLOCKED)
}

_SIG_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*"
                     r"(?:Error|Exception|Interrupt|Exit|Warning))\b")
_KL_TOKEN_RE = re.compile(r"KL\s*=\s*-?\d+(?:\.\d+)?(e[+-]?\d+)?", re.I)


def error_signature(error_message: str) -> str:
    """Deterministic coarse signature: exception class if present, else the
    normalized message with numeric signals tokenized (KL=0.31 and KL=0.29 are
    the SAME failure mode; task 31/32)."""
    msg = error_message or ""
    m = _SIG_RE.search(msg)
    if m:
        return m.group(1)
    if _KL_TOKEN_RE.search(msg):
        return _KL_TOKEN_RE.sub("KL=<N>", msg)[:120]
    return norm_err(msg)[:120]


class EvidenceBranchState:
    """All branch states for one episode; updated ONLY at failure boundaries."""

    def __init__(self, constants: dict | None = None, q_values: dict | None = None):
        self.c = dict(DEFAULT_CONSTANTS)
        if constants:
            self.c.update(constants)
        self.branches: dict[str, dict] = {
            fam: {"family": fam, "attempts": 0, "failures": 0, "q_value": 0.0,
                  "status": ACTIVE, "seen_signatures": [], "nov_mean_prev": None}
            for fam in PROBEABLE
        }
        self.set_q_values(q_values or {})

    # ------------------------------------------------------------------
    def set_q_values(self, Q: dict) -> None:
        for fam in PROBEABLE:
            if fam in Q and Q[fam] is not None:
                self.branches[fam]["q_value"] = round(float(Q[fam]), 4)

    @staticmethod
    def dominant_family(evidence_used: dict) -> str | None:
        used = [(k, v) for k, v in (evidence_used or {}).items()
                if k in PROBEABLE and v]
        return max(used, key=lambda kv: kv[1])[0] if used else None

    # ------------------------------------------------------------------
    def on_failure(self, *, evidence_used: dict, error_message: str,
                   family_novelty_now, family_novelty_prev) -> dict:
        """Record one failed repair attempt; returns the updated branch."""
        fam = self.dominant_family(evidence_used)
        if fam is None:
            fam = "E2"          # no probes this attempt: execution feedback
            # (runtime errors are E2-type information; documented default)
        b = self.branches[fam]
        sig = error_signature(error_message)
        b["attempts"] += 1
        new_signature = sig not in b["seen_signatures"]
        b["seen_signatures"].append(sig)
        # RQ-fix F3 (variant deurq_fix): a KL mismatch is an
        # implementation-semantics failure, not an evidence-path failure —
        # record the attempt and signature for trace parity, but exempt it
        # from family-failure accumulation and the DEGRADE/BLOCK state
        # machine (the ESCAPE-chain root identified in the D2 analysis).
        if (self.c.get("kl_neutral_attribution", False)
                and _KL_TOKEN_RE.search(error_message or "")):
            return self.snapshot_family(
                fam, signature=sig, new_signature=new_signature,
                gain_decreasing=None, kl_neutral=True)
        b["failures"] += 1
        nov_now, nov_prev = family_novelty_now, family_novelty_prev
        if nov_now is None:
            nov_now = 0.0       # failed attempt gave no new information
        gain_decreasing = bool(
            (nov_prev is not None and nov_now < nov_prev) or nov_now == 0.0)
        c = self.c
        if b["status"] == RECOVERABLE:
            # recovery failed: old failure mode returned
            b["status"] = BLOCKED if not new_signature else ACTIVE
        elif new_signature and b["status"] == BLOCKED:
            b["status"] = RECOVERABLE       # repair left the failed path
        elif (b["failures"] >= c["block_family_failures"] and gain_decreasing):
            b["status"] = BLOCKED
        elif (b["failures"] >= c["degrade_family_failures"]
              and gain_decreasing and b["status"] == ACTIVE):
            b["status"] = DEGRADED
        b["nov_mean_prev"] = nov_now
        # a genuinely new failure signature anywhere is evidence the repair
        # left a failed path: other RECOVERABLE families return to ACTIVE
        for other in self.branches.values():
            if other["status"] == RECOVERABLE and other is not b \
                    and sig not in other["seen_signatures"]:
                other["status"] = ACTIVE
        return self.snapshot_family(fam, signature=sig,
                                    new_signature=new_signature,
                                    gain_decreasing=gain_decreasing)

    def on_recovery_evidence(self, error_message: str) -> list[str]:
        """A new error signature appeared anywhere: BLOCKED families get one
        RECOVERABLE chance. Returns families moved to RECOVERABLE."""
        sig = error_signature(error_message)
        moved = []
        for fam, b in self.branches.items():
            if b["status"] == BLOCKED and sig not in b["seen_signatures"]:
                b["status"] = RECOVERABLE
                moved.append(fam)
        return moved

    # ------------------------------------------------------------------
    def escape_worthy(self) -> dict | None:
        """Family that triggers ESCAPE mode: failures >= escape threshold with
        non-increasing gain (DEGRADED or BLOCKED). Worst first."""
        c = dict(DEFAULT_CONSTANTS)
        c.update(self.c)
        cands = [b for b in self.branches.values()
                 if b["failures"] >= c["escape_family_failures"]
                 and b["status"] in (DEGRADED, BLOCKED)]
        if not cands:
            return None
        worst = max(cands, key=lambda b: (b["failures"], -b["q_value"]))
        return {"family": worst["family"], "failures": worst["failures"],
                "status": worst["status"]}

    def blocked_families(self) -> list[str]:
        return [f for f, b in self.branches.items() if b["status"] == BLOCKED]

    def allowed_families(self) -> list[str]:
        return [f for f in PROBEABLE if f not in self.blocked_families()]

    def best_q(self) -> float | None:
        # deurq_fsm G5: a BLOCKED family must not carry the FOCUS gate —
        # "best family's evidence is sufficient" is self-contradictory when
        # that family is forbidden to probe. RECOVERABLE stays eligible
        # (it is a pending re-validation, not a failure terminal state;
        # spec 修订 4: exclude BLOCKED only).
        if self.c.get("fsm_g5_best_q", False):
            vals = [b["q_value"] for b in self.branches.values()
                    if b["status"] != BLOCKED and b["q_value"] is not None]
        else:
            vals = [b["q_value"] for b in self.branches.values()
                    if b["q_value"] is not None]
        return max(vals) if vals else None

    def snapshot_family(self, fam: str, **extra) -> dict:
        b = self.branches[fam]
        return {"family": fam, "attempts": b["attempts"],
                "failures": b["failures"], "q_value": b["q_value"],
                "status": b["status"], **extra}

    def snapshot(self) -> dict:
        return {f: {k: (list(v) if isinstance(v, list) else v)
                    for k, v in b.items()}
                for f, b in self.branches.items()}
