"""Frozen utility prior loader.

Loads analysis/rq4_fcea/qhe_evidence_utility_prior.json (built once from QHE
local_hard traces by analysis/rq4_fcea/build_prior.py; never edited after QB+
experiments begin). Provides tier lookups for the two phase-1 variants:
  global (V2): pooled ranking for every failure
  fcond  (V3): per-observed-failure-context ranking

NoSubmit is deliberately NOT routed in phase 1 (see task spec section six).
"""
from __future__ import annotations

import json
from functools import lru_cache

from exp.fcea import config as fcfg


@lru_cache(maxsize=1)
def _prior() -> dict:
    return json.loads(fcfg.PRIOR_PATH.read_text(encoding="utf-8"))


def prior_sha256() -> str:
    return fcfg.prior_sha256()


def tiers_for(variant: str, failure_context: str) -> dict:
    """Return {category: tier} for the variant/context.

    NoSubmit and Other are NEVER routed in phase 1 (task-spec design: NoSubmit
    is not an evidence-selection problem). The prior file may carry NoSubmit
    statistics, but this routing layer refuses to serve them, so a loop change
    alone cannot accidentally start routing NoSubmit.
    """
    if failure_context in ("NoSubmit", "Other"):
        return {}
    d = _prior()
    if variant == "fcond":
        pc = d["per_context"].get(failure_context) or {}
        return dict(pc.get("tiers") or {})
    if variant in set(fcfg.VARIANTS) - {"fcond"}:
        # every fcea variant except fcond reads the global prior tiers for
        # the notice; only the routing/decision layer differs by variant.
        # Derived from the variant registry so new variants cannot crash
        # here (the deurc/deurc_noescape smoke incidents).
        return dict(d["global"]["tiers"])
    raise ValueError(f"unknown variant {variant!r}")


def recommended_for(variant: str, failure_context: str) -> list[str]:
    tiers = tiers_for(variant, failure_context)
    return sorted([c for c, t in tiers.items() if t == "HIGH"])


def global_q0() -> dict[str, float]:
    """Q0 for DEU-v2: global-pool U_recovery per category (frozen prior)."""
    cells = _prior()["global"]["cells"]
    return {e: float(cells[e]["U_recovery"]) for e in ("E1", "E2", "E3", "E4")
            if cells.get(e, {}).get("U_recovery") is not None}


def provenance() -> dict:
    d = _prior()
    return {
        "generated_at_utc": d.get("generated_at_utc"),
        "source_dataset": d["provenance"]["source_dataset"],
        "analyzer_sha256": d["provenance"]["analyzer_sha256"],
        "global_tiers": d["global"]["tiers"],
        "per_context_tiers": {f: v["tiers"] for f, v in d["per_context"].items()},
    }
