"""D2 clean (full − C2): seeded noise surrogate for the evidence-utility input.

GATE 2 verdict (攻关.md RQ3): deurand ignores state AND utility, so it is the
RQ4 uninformed-control negative control, NOT a clean −C2. The clean D2 keeps
the state path fully intact and replaces the utility input with a seeded noise
surrogate of matched form at every consumption point on the deurc-noctx stack.

Utility consumption points (enumerated 2026-09-25, see
docs/analysis/rq3_d_variants_implementation_20260925.md):
  C3 (RepairController, via loop.run_controller):
    1. utility_drop  -> TERMINATE gate + RCI utility_drop component
    2. Q             -> branches.set_q_values -> best_q() (FOCUS gate) +
                        escape_worthy() worst-ordering + record q_values
    3. Q             -> compute_rci utility component (shown in the directive)
    4. Q             -> preferred_family (soft-FOCUS; inactive under the frozen
                        hard restriction, substituted anyway for flag parity)
  LLM-facing channels:
    5. directive RCI line (utility / utility_drop values — noise values, since
       the RCI is computed from the surrogate)
    6. the evidence-priority notice (frozen-prior tiers = C2's static half)

Surrogate design (matched form, documented deviation):
  - Q̃(e) ~ Uniform(q_floor, 1.0) iid per family per boundary draw — the same
    support as the real clipped EMA Q. Consecutive draws form the noise walk;
    utility_drop̃ = max_e |Q̃_t(e) − Q̃_{t−1}(e)| — the same operationalization
    as the real drop (max-family |ΔQ| across one update), with the episode
    anchor Q̃_0 playing the role of the frozen Q0.
  - notice tiers: rank the anchor Q̃_0 and assign the frozen global tier
    multiset {1×HIGH, 2×MEDIUM, 1×LOW} by rank — same in-episode constancy and
    message template as the real notice, random family assignment.
  - seeding: per-episode stream seed = sha256("d2|<tag>|<case_id>") —
    reproducible, distinct across tasks and replicate tags. (deurand's shared
    fixed-seed stream convention is NOT inherited: independent noise across
    tasks is the point of a surrogate.)

The C2 machinery (state manager + EMA updater) still computes in the loop for
trace reference only — no consumption point receives real utility (deviation
records this; behavior is identical to not running it).
"""
from __future__ import annotations

import hashlib
import random

CATEGORIES = ("E1", "E2", "E3", "E4")
TIER_MULTISET = ("HIGH", "MEDIUM", "MEDIUM", "LOW")

DEFAULT_CONSTANTS = {
    "random_seed_base": 20260925,
    "q_floor": 0.05,     # real updater clip floor (utility/state.py: q_floor)
    "q_ceil": 1.0,       # real updater clip ceiling
}


def d2_noise_seed(*, tag: str, case_id: str,
                  constants: dict | None = None) -> int:
    """Per-episode surrogate seed: frozen base mixed with the run tag and the
    case id. Reproducible from (tag, case_ids) alone; replicate tags differ."""
    c = dict(DEFAULT_CONSTANTS)
    if constants:
        c.update(constants)
    key = "d2|%s|%s|%s" % (c["random_seed_base"], tag or "", case_id or "")
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:6], "big")


def _draw_q(rng: random.Random, q_floor: float, q_ceil: float) -> dict[str, float]:
    return {e: round(rng.uniform(q_floor, q_ceil), 4) for e in CATEGORIES}


def tiers_from_ranking(Q: dict[str, float]) -> dict[str, str]:
    """Assign the frozen global tier multiset by Q̃_0 rank (ties by family name)."""
    ranked = sorted(CATEGORIES, key=lambda e: (-float(Q.get(e, 0.0)), e))
    return {e: TIER_MULTISET[i] for i, e in enumerate(ranked)}


class NoiseUtilitySource:
    """One instance per episode. draw() once per failure boundary; notice()
    serves the matched-form noise evidence-priority notice."""

    def __init__(self, *, seed: int, constants: dict | None = None):
        self.c = dict(DEFAULT_CONSTANTS)
        if constants:
            self.c.update(constants)
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.q_anchor = _draw_q(self.rng, self.c["q_floor"], self.c["q_ceil"])
        self.tiers = tiers_from_ranking(self.q_anchor)
        self.recommended = sorted([e for e, t in self.tiers.items() if t == "HIGH"])
        self._prev = dict(self.q_anchor)
        self.log: list[dict] = []

    def draw(self) -> tuple[dict[str, float], float]:
        """One boundary draw: (Q̃_t, drop̃). drop̃ = max-family |ΔQ̃| vs the
        previous draw (anchor Q̃_0 for the first boundary)."""
        q = _draw_q(self.rng, self.c["q_floor"], self.c["q_ceil"])
        drop = max(abs(q[e] - self._prev[e]) for e in CATEGORIES)
        self._prev = q
        return q, round(drop, 4)

    def notice(self) -> str:
        """Matched-form evidence-priority notice: byte-identical template to
        planner.utility_notice, tiers from the noise assignment."""
        from exp.fcea.evidence import planner

        return planner.utility_notice(
            variant="global", failure_context="global", confidence=1.0,
            tiers_override=dict(self.tiers))
