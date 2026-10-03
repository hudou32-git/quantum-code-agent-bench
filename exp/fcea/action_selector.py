"""DEU-v3-ACT Action Selector (rule-based) + random ablation selector.

Pipeline: State -> Dynamic Utility Estimator -> Action Selector -> A_t ->
action-conditioned repair. The selector is a REAL decision layer: its action
is committed mechanically for the next attempt (see loop.py):
  CONTINUE         no constraint
  SWITCH_EVIDENCE  evidence-focus filter on BatchProbe queries (next attempt)
  SWITCH_STRATEGY  strategy-change directive (next attempt)
  FINALIZE         BatchProbe tool withdrawn until episode end (no auto-submit)

Precedence (PoC spec §6): FINALIZE > SWITCH_STRATEGY > SWITCH_EVIDENCE >
CONTINUE. Every trigger input is an existing trace field; no new oracle.
utility_drop threshold reuses the frozen H2 median nonzero |delta_Q| (0.046).
"""
from __future__ import annotations

import random

ACTIONS = ("CONTINUE", "SWITCH_EVIDENCE", "SWITCH_STRATEGY", "FINALIZE")
PROBEABLE = ("E1", "E2", "E3")          # E4 has no probe kind
FAMILY_KINDS = {"E1": ("api", "env"), "E2": ("runtime",), "E3": ("behavior",)}

DEFAULT_CONSTANTS = {
    "finalize_no_progress_threshold": 2,
    "finalize_utility_drop_threshold": 0.046,
    "strategy_same_error_threshold": 2,
    "switch_evidence_delta": 0.046,
    "random_seed": 20260923,
}

HEADER = "[Action gate — adaptive within this episode]"
FOOTER = ("This is contextual guidance, not a claim about the underlying root "
          "cause; the decision remains yours.")
FINALIZE_TEXT = ("No additional probing and no new evidence requests for the "
                 "rest of this episode. Prepare and evaluate your best current "
                 "solution.")
STRATEGY_TEXT = ("The previous repair direction is considered ineffective. "
                 "Generate a different repair approach.")
SWITCH_TEXT = ("Evidence focus for this attempt: {family}. New evidence queries "
               "are restricted to kinds {kinds}; other query kinds will not be "
               "executed.")


class ActionSelector:
    """Rule-based f(s_t, Q_t). Deterministic."""

    def __init__(self, constants: dict | None = None):
        self.c = dict(DEFAULT_CONSTANTS)
        if constants:
            self.c.update(constants)

    def select(self, *, no_progress_count, same_error_count, code_changed,
               novelty_mean_now, novelty_mean_prev, utility_drop,
               Q, current_family) -> dict:
        c = self.c
        novelty_falling = (novelty_mean_now is not None
                           and novelty_mean_prev is not None
                           and novelty_mean_now < novelty_mean_prev)
        if (no_progress_count >= c["finalize_no_progress_threshold"]
                and utility_drop >= c["finalize_utility_drop_threshold"]):
            action, reason = "FINALIZE", (
                "no_progress={np} >= {t} and utility_drop={d} >= {dt}".format(
                    np=no_progress_count, t=c["finalize_no_progress_threshold"],
                    d=round(utility_drop, 4), dt=c["finalize_utility_drop_threshold"]))
        elif (same_error_count >= c["strategy_same_error_threshold"]
                and novelty_falling):
            action, reason = "SWITCH_STRATEGY", (
                "same_error={se} >= {t} and novelty falling "
                "({a} < {b})".format(se=same_error_count, t=c["strategy_same_error_threshold"],
                                     a=_r(novelty_mean_now), b=_r(novelty_mean_prev)))
        else:
            focus, gap = self._focus(Q, current_family)
            if focus and gap > c["switch_evidence_delta"]:
                action, reason = "SWITCH_EVIDENCE", (
                    "Q({f})={qf} exceeds Q(current={cur})={qc} by {g} > {t}".format(
                        f=focus, qf=_r(Q.get(focus)), cur=current_family,
                        qc=_r(Q.get(current_family)), g=round(gap, 4),
                        t=c["switch_evidence_delta"]))
            else:
                action, reason = "CONTINUE", "no gate condition met"
        return {"action": action, "reason": reason,
                "focus_family": focus if action == "SWITCH_EVIDENCE" else None}

    def _focus(self, Q, current_family):
        """Best probeable family, but only when the current family is NOT the
        utility argmax (never switch away from the best family)."""
        if current_family not in PROBEABLE or not Q:
            return None, 0.0
        cands = [e for e in PROBEABLE if e in Q]
        if not cands:
            return None, 0.0
        best = max(cands, key=lambda e: Q[e])
        if best == current_family:
            return None, 0.0
        return best, float(Q[best]) - float(Q[current_family])


class RandomActionSelector:
    """Ablation: uniform random action, seeded; ignores state and utility."""

    def __init__(self, constants: dict | None = None):
        c = dict(DEFAULT_CONSTANTS)
        if constants:
            c.update(constants)
        self.rng = random.Random(c["random_seed"])

    def select(self, **_) -> dict:
        a = self.rng.choice(ACTIONS)
        focus = None
        if a == "SWITCH_EVIDENCE":
            focus = self.rng.choice(list(PROBEABLE))
        return {"action": a, "reason": "random ablation", "focus_family": focus}


def action_message(decision: dict) -> str | None:
    """Action-conditioned commitment text; CONTINUE gets none."""
    a = decision["action"]
    if a == "FINALIZE":
        body = FINALIZE_TEXT
    elif a == "SWITCH_STRATEGY":
        body = STRATEGY_TEXT
    elif a == "SWITCH_EVIDENCE":
        f = decision["focus_family"]
        body = SWITCH_TEXT.format(family=f, kinds=", ".join(FAMILY_KINDS[f]))
    else:
        return None
    return "\n".join([HEADER, body, FOOTER])


def _r(v):
    return round(v, 5) if isinstance(v, float) else v
