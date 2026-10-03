"""DEU-v3 Action Adapter (proof of concept).

Converts existing DEU state signals into at most two action-level guidance
messages. Pure logic: no code edits, no automatic action execution, no forced
submission, no LLM-autonomy removal — the adapter only emits text and an audit
event. Every trigger input is a field that already exists in the DEU-v2 trace;
no new oracle.

Actions (design: rq4_deu3 action-adapter PoC spec, 2026-09-23):
  strategy_switch — same_error_count >= strategy_same_error_threshold AND
                    novelty low (all-probed zero) or decreasing.
  explore_stop    — no_progress_count >= stop_no_progress_threshold AND
                    last-step utility-drop magnitude >= utility_drop_threshold.

utility_drop_threshold defaults to the frozen H2 analysis's median nonzero
|delta_Q| (analysis/rq4_fcea/rq4_deu_utility_state_alignment.json); the other
thresholds default to the spec. All configurable; the adapter never fires on a
passed boundary and is called on both graded-failure and NoSubmit boundaries
(the NoSubmit reach is the point of the PoC).
"""
from __future__ import annotations

DEFAULT_CONSTANTS = {
    "strategy_same_error_threshold": 2,
    "stop_no_progress_threshold": 2,     # spec allows 2 or 3; 2 maximizes reach
    "utility_drop_threshold": 0.046,
}

HEADER = "[Action-level guidance — adaptive within this episode]"
FOOTER = ("This is contextual guidance, not a claim about the underlying root "
          "cause; the decision remains yours.")

STRATEGY_SWITCH_TEXT = ("Current repair trajectory shows stagnation. "
                        "Consider changing repair strategy rather than continuing "
                        "the current exploration path.")
STOP_EXPLORE_TEXT = ("Current evidence exploration shows diminishing utility. "
                     "Consider stopping further exploration and evaluating the "
                     "current solution.")


class ActionAdapter:
    """Stateless per-boundary evaluator; all counters come from the caller."""

    def __init__(self, constants: dict | None = None):
        self.c = dict(DEFAULT_CONSTANTS)
        if constants:
            self.c.update(constants)

    def on_boundary(self, *, step, boundary_kind, task_id, error_transition,
                    error_message, no_progress_count, same_error_count,
                    code_changed, novelty_mean_now, novelty_mean_prev,
                    utility_drop, attempts_left) -> tuple[str | None, dict]:
        c = self.c
        novelty_low = novelty_mean_now is not None and novelty_mean_now == 0.0
        novelty_falling = (novelty_mean_now is not None and novelty_mean_prev is not None
                           and novelty_mean_now < novelty_mean_prev)
        strategy_fire = (same_error_count >= c["strategy_same_error_threshold"]
                         and (novelty_low or novelty_falling))
        stop_fire = (no_progress_count >= c["stop_no_progress_threshold"]
                     and utility_drop >= c["utility_drop_threshold"])

        texts = []
        types = []
        if strategy_fire:
            types.append("strategy_switch")
            texts.append(STRATEGY_SWITCH_TEXT)
        if stop_fire:
            types.append("explore_stop")
            texts.append(STOP_EXPLORE_TEXT)
        message = None
        if texts:
            message = "\n".join([HEADER, *texts, FOOTER])

        event = {
            "step_id": step,
            "task_id": task_id,
            "boundary_kind": boundary_kind,          # "error" | "nosubmit"
            "action_type": types,                     # [] when nothing fired
            "trigger_signal": {
                "same_error_count": same_error_count,
                "no_progress_count": no_progress_count,
                "code_changed": bool(code_changed),
                "novelty_mean_now": _r(novelty_mean_now),
                "novelty_mean_prev": _r(novelty_mean_prev),
                "novelty_low": novelty_low,
                "novelty_falling": novelty_falling,
                "utility_drop": _r(utility_drop),
                "thresholds": dict(c),
            },
            "utility_state": {"novelty_mean_now": _r(novelty_mean_now),
                              "utility_drop": _r(utility_drop)},
            "error_state": {"transition": error_transition,
                            "message": (error_message or "")[:160],
                            "boundary_kind": boundary_kind},
            "message_sent": message is not None,
            "delivered_next_attempt": attempts_left > 0,
            "message_text": message,
        }
        return message, event


def _r(v):
    return round(v, 5) if isinstance(v, float) else v
