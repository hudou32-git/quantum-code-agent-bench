"""DEU-v2 Phase 2: online marginal evidence utility update (EMA).

Q(e, s_t) semantics (design rev2): marginal utility of evidence family e under
the current repair state — initialized from the frozen global prior
(Q0 = U_recovery(global)) and updated within the episode only. State resets per
task; no cross-task learning, no QB+ feedback path. No RL, no bandit.

Update (analysis/rq4_fcea/deu_v2_design.md rev2 §4):
  outcome_novelty_e = mean(output_novelty of e's probes this step)
                      * step_state_change
  R_t               = 0.5 * progress_score + 0.5 * outcome_novelty_e
  Q_{t+1}(e)        = clip((1-alpha) Q_t(e) + alpha R_t, q_floor, 1.0)
  if no_progress_count >= 2: Q(e) <- max(q_floor, Q(e) * decay)  for all e

progress_score ∈ {-1, 0, +1} comes from the Phase-1 state manager (both
non-neutral tiers require code_changed; same-code error changes are sampling
noise, task 31). Pure functions; unit-testable without an LLM.
"""
from __future__ import annotations

CATEGORIES = ("E1", "E2", "E3", "E4")


def q0_from_prior(prior: dict) -> dict:
    """Initial marginal utilities from the frozen prior's global cells."""
    cells = prior["global"]["cells"]
    return {e: float(cells[e]["U_recovery"]) for e in CATEGORIES
            if cells.get(e, {}).get("U_recovery") is not None}


class DynamicUtilityUpdater:
    def __init__(self, q0: dict[str, float], constants: dict | None = None):
        self.alpha = float((constants or {}).get("alpha", 0.3))
        self.decay = float((constants or {}).get("decay", 0.8))
        self.q_floor = float((constants or {}).get("q_floor", 0.05))
        self.Q: dict[str, float] = {e: float(q0[e]) for e in q0}

    @staticmethod
    def _clip(v: float) -> float:
        return max(0.05, min(1.0, v))

    def update_step(self, *, progress_score: int, step_state_change: bool,
                    category_novelties: dict[str, list[int]],
                    no_progress_count: int) -> dict:
        """Close one repair step: update Q for categories probed this step.

        category_novelties: {category: [output_novelty per probe]} for the step
        (from the Phase-1 state manager). Returns the logging record.
        """
        before = {e: round(self.Q.get(e, 0.0), 4) for e in self.Q}
        outcome_novelty: dict[str, float] = {}
        for e, novs in (category_novelties or {}).items():
            if e not in self.Q:
                continue
            mean_nov = (sum(novs) / len(novs)) if novs else 0.0
            outcome_novelty[e] = mean_nov * (1.0 if step_state_change else 0.0)
        for e, nov in outcome_novelty.items():
            r = 0.5 * progress_score + 0.5 * nov
            self.Q[e] = self._clip((1.0 - self.alpha) * self.Q[e] + self.alpha * r)
        if no_progress_count >= 2:
            for e in self.Q:
                self.Q[e] = max(self.q_floor, self.Q[e] * self.decay)
        if outcome_novelty:
            mean_nov_all = sum(outcome_novelty.values()) / len(outcome_novelty)
        else:
            mean_nov_all = 0.0
        reward = 0.5 * progress_score + 0.5 * mean_nov_all
        return {
            "marginal_utility_before": before,
            "reward": round(reward, 4),
            "outcome_novelty": {e: round(v, 4) for e, v in outcome_novelty.items()},
            "marginal_utility_after": {e: round(self.Q[e], 4) for e in self.Q},
        }


def update_tiers(*args, **kwargs):  # pragma: no cover - retired placeholder
    raise NotImplementedError(
        "update_tiers was the Phase-1 placeholder name; use DynamicUtilityUpdater."
    )
