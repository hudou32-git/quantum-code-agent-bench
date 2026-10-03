"""FCEA tracing helpers: structured records for evidence-allocation analysis.

Phase-1 requirement: never again lose the command face. Every BatchProbe round
records each probe's requested query text and requested category (the model's
kind label), plus the actual category scored from the output by the frozen
taxonomy classifier. Failure events record the observed context, the injected
prior, and the recommended types — the inputs to the
recommended -> actual -> outcome chain.
"""
from __future__ import annotations

from typing import Any

from exp.fcea.evidence.taxonomy import KIND_TO_CATEGORY


def new_episode_trace() -> dict[str, list]:
    return {"probe_log": [], "failure_events": []}


def record_probes(
    trace: dict[str, list],
    *,
    round_no: int,
    shot: int,
    evidence: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    classify_output,
) -> None:
    for e in evidence or []:
        query = str(e.get("query") or "")
        requested_kind = str(e.get("kind") or "")
        out = str(e.get("output") or "")
        actual_cat, conf = classify_output(out)
        trace["probe_log"].append({
            "probe_round": round_no,
            "shot": shot,
            "probe_query": query,
            "requested_evidence_kind": requested_kind,
            "requested_evidence_type": KIND_TO_CATEGORY.get(requested_kind, ""),
            "actual_evidence_type": actual_cat,
            "actual_confidence": conf,
            "probe_ok": bool(e.get("ok")),
            "probe_status": str(e.get("status") or ""),
            "probe_result_chars": len(out),
            "probe_tokens_est": round(len(out) / 4.0),
        })
    for r in rejected or []:
        trace["probe_log"].append({
            "probe_round": round_no,
            "shot": shot,
            "probe_query": "",
            "requested_evidence_kind": "",
            "requested_evidence_type": "",
            "actual_evidence_type": "Rejected",
            "actual_confidence": 0.0,
            "probe_ok": False,
            "probe_status": f"rejected: {r.get('reason')}",
            "probe_result_chars": 0,
            "probe_tokens_est": 0,
        })


def record_failure(
    trace: dict[str, list],
    *,
    shot: int,
    error_message: str,
    failure_context: str,
    confidence: float,
    nosubmit: bool,
    utility_prior: dict | None,
    recommended: list[str] | None,
    injected: bool,
) -> None:
    trace["failure_events"].append({
        "shot": shot,
        "failure_message": (error_message or "")[:400],
        "failure_context": failure_context,
        "failure_context_confidence": confidence,
        "nosubmit": bool(nosubmit),
        "utility_prior": utility_prior or {},
        "recommended_evidence_types": recommended or [],
        "priority_injected": bool(injected),
    })
