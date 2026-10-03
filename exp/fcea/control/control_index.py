"""Repair Control Index (RCI): deterministic scalar control signal in [0,1].

RCI = clip01( w1*utility + w2*progress + w3*novelty
              - w4*stagnation - w5*utility_drop )

All inputs are normalized to [0,1] from fields that already exist in the
DEU-v2 trace (no new oracle):
  utility      mean Q over probeable evidence families (Q itself in [0,1])
  progress     (progress_score + 1) / 2          progress_score in {-1,0,+1}
  novelty      mean outcome novelty of the step  in [0,1]
  stagnation   clip01(max(no_progress, same_error) / stagnation_norm)
  utility_drop clip01(max-family |delta_Q| / drop_norm), drop from EMA update

Weights and normalizers are frozen config (exp/fcea/config.py: DEURC_CONSTANTS);
no hidden constants. Pure function; unit-testable without an LLM.
"""
from __future__ import annotations

PROBEABLE = ("E1", "E2", "E3")          # E4 has no probe kind

DEFAULT_CONSTANTS = {
    "w_utility": 0.40,
    "w_progress": 0.20,
    "w_novelty": 0.15,
    "w_stagnation": 0.15,
    "w_utility_drop": 0.10,
    "stagnation_norm": 4.0,     # counter value mapped to stagnation = 1.0
    "drop_norm": 0.20,          # |delta_Q| mapped to utility_drop = 1.0
}


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def compute_rci(*, Q, progress_score, novelty_mean, no_progress_count,
                same_error_count, utility_drop,
                constants: dict | None = None) -> dict:
    """Return {"rci", "components"} — components are logged, never hidden."""
    c = dict(DEFAULT_CONSTANTS)
    if constants:
        c.update(constants)
    qvals = [float(Q[e]) for e in PROBEABLE if e in Q and Q[e] is not None]
    utility = (sum(qvals) / len(qvals)) if qvals else 0.0
    progress = (float(progress_score) + 1.0) / 2.0
    novelty = float(novelty_mean) if novelty_mean is not None else 0.0
    stagnation = _clip01(max(int(no_progress_count), int(same_error_count))
                         / max(float(c["stagnation_norm"]), 1e-9))
    drop = _clip01(float(utility_drop) / max(float(c["drop_norm"]), 1e-9))
    rci = _clip01(c["w_utility"] * utility
                  + c["w_progress"] * progress
                  + c["w_novelty"] * novelty
                  - c["w_stagnation"] * stagnation
                  - c["w_utility_drop"] * drop)
    return {
        "rci": round(rci, 4),
        "components": {
            "utility": round(utility, 4),
            "progress": round(progress, 4),
            "novelty": round(novelty, 4),
            "stagnation": round(stagnation, 4),
            "utility_drop": round(drop, 4),
        },
    }
