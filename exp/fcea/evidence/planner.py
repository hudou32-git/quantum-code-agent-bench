"""Evidence-priority notice builder (the FCEA treatment message).

The notice is SOFT guidance: it states the observed failure context (an
observation label, explicitly not a root-cause claim) and the frozen prior's
evidence tiers, then defers the actual probe choice to the model. Identical
message format for variants global and fcond — only the tiers differ.
"""
from __future__ import annotations

import json

from exp.fcea.evidence.taxonomy import CATEGORY_NAMES
from exp.fcea.utility import prior as uprior

TIER_ORDER = ("HIGH", "MEDIUM", "LOW")

GUIDANCE_LINE = (
    "Prefer evidence categories with higher estimated utility, but you may use "
    "another category when the current program or error provides a concrete reason."
)
NON_CAUSE_LINE = (
    "This labels the observed failure style only; it is not a claim about the "
    "underlying root cause."
)
SATURATION_TEXT = (
    "Current exploration has produced limited state change. Consider "
    "reassessing current strategy."
)
FORBIDDEN_DIRECTIVES = ("use e1", "use e2", "use e3", "use e4")


def deu_kind(no_progress_count: int, consec_zero_novelty: int) -> str:
    """Guidance kind for the current failure boundary (pure, testable)."""
    if no_progress_count >= 2 or consec_zero_novelty >= 2:
        return "saturation_warning"
    return "routine"


def classify_adoption(categories_before, categories_after, code_changed: bool,
                      next_passed: bool | None = None) -> dict:
    """Did the model act on a saturation warning? (interpretable rule)"""
    before = set(categories_before or [])
    after = set(categories_after or [])
    switched = bool(after - before) if before else bool(after)
    followed = bool(switched or code_changed or next_passed)
    return {"switched_category": switched, "code_changed": bool(code_changed),
            "next_passed": next_passed, "followed": followed}


def marginal_notice(*, kind: str, Q: dict, state_hint: dict) -> str:
    """DEU-v2 soft guidance (Phase 3). kind: routine | saturation_warning.

    Never a directive: states the current marginal-utility snapshot and the
    observed repair-state stall; the model decides what to probe.
    """
    ranked = sorted(Q.items(), key=lambda kv: kv[1], reverse=True)
    low = [c for c, v in ranked if v <= Q.get("E4", 0.091) + 1e-9]
    payload = {
        "guidance_kind": kind,
        "marginal_utility": {c: round(v, 3) for c, v in ranked},
        "low_marginal_categories": low,
        "repair_state": dict(state_hint or {}),
        "note": "values initialize from a frozen QHE prior and are updated online "
                "within this episode only",
    }
    lines = [
        "[Evidence marginal-utility guidance — soft, adaptive within this episode]",
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=1)}\n```",
        NON_CAUSE_LINE,
        GUIDANCE_LINE,
    ]
    if kind == "saturation_warning":
        lines.append(SATURATION_TEXT)
    return "\n".join(lines)


def utility_notice(*, variant: str, failure_context: str, confidence: float,
                   tiers_override: dict | None = None) -> str:
    """tiers_override (D2 clean only): serve the given {category: tier} map
    through the byte-identical notice template instead of the frozen prior.
    None keeps the frozen-prior lookup (every existing variant unchanged)."""
    tiers = dict(tiers_override) if tiers_override is not None \
        else uprior.tiers_for(variant, failure_context)
    recommended = sorted([c for c, t in tiers.items() if t == "HIGH"])
    payload = {
        "failure_context": failure_context if variant == "fcond" else "global",
        "evidence_priority": [
            {"type": cat, "tier": tier,
             "meaning": CATEGORY_NAMES.get(cat, "")}
            for cat, tier in sorted(tiers.items(), key=lambda kv: (TIER_ORDER.index(kv[1]), kv[0]))
        ],
        "recommended_evidence_types": recommended,
    }
    lines = [
        "[Evidence priority for this attempt — soft guidance from a frozen prior]",
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=1)}\n```",
        NON_CAUSE_LINE,
        GUIDANCE_LINE,
    ]
    return "\n".join(lines)
