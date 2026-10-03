"""Evidence-EQPA tools: BatchProbe (batched, structured, clipped) + EQPA Write/Eval.

BatchProbe reuses exp.eqpa.bwrap.run_sandboxed (same sandbox boundary, same
environment) and exp.eqpa.tools.run_write/run_eval unchanged. The only new code
paths are: query normalization/capping, per-probe clipping, output-kind
classification, structured JSON evidence assembly, and the batch canary gate.
"""

from __future__ import annotations

import json
import re
from typing import Any

from exp.eqpa.tools import EVAL_TOOL, WRITE_TOOL, run_eval, run_write  # noqa: F401 (re-exported)
from exp.eqpa.bwrap import SandboxError, run_sandboxed
from exp.common.canary import scan_text
from exp.eqpa.jail import IsoSession

from exp.evidence_eqpa import config as bcfg

BATCH_TOOL = bcfg.BATCH_TOOL
EVIDENCE_TOOLS = [BATCH_TOOL, WRITE_TOOL, EVAL_TOOL]

_KINDS = ("api", "behavior", "runtime", "env")


def classify_output_kind(text: str) -> str:
    t = text or ""
    if re.search(r"\(self\b|-> *'|: *'[A-Za-z]|signature|__doc__|Number of qubits|Duration:|Instructions:", t):
        return "api_fact"
    if re.match(r"^\['?[A-Z]", t) and t.count(",") > 8:
        return "api_fact"
    if re.search(r"\d\.\d+\.\d+", t) and len(t) < 60:
        return "version"
    if re.search(r"\{'[01]+' ?:|-> *\{|Statevector|DensityMatrix|┌|Key.*Expected|shots|counts|purity|fidelity", t, re.I):
        return "behavior_probe"
    if re.search(r"Traceback|Error|error:", t):
        return "error_probe"
    return "other"


def _normalize_queries(raw: Any) -> tuple[list[dict], list[dict]]:
    """-> (accepted, rejected_with_reason). Accepts strings or {kind, query}."""
    accepted: list[dict] = []
    rejected: list[dict] = []
    seen: set[str] = set()
    items = raw if isinstance(raw, list) else []
    for idx, item in enumerate(items):
        if isinstance(item, str):
            kind, q = "", item.strip()
        elif isinstance(item, dict):
            kind = str(item.get("kind") or "").strip().lower()
            q = str(item.get("query") or "").strip()
        else:
            rejected.append({"i": idx + 1, "reason": "query must be a string or {kind, query}"})
            continue
        if not q:
            rejected.append({"i": idx + 1, "reason": "empty query"})
            continue
        if q in seen:
            rejected.append({"i": idx + 1, "reason": "duplicate query (already in this batch)"})
            continue
        if kind and kind not in _KINDS:
            kind = ""
        if len(accepted) >= bcfg.MAX_QUERIES_PER_BATCH:
            rejected.append({"i": idx + 1, "reason": f"batch cap {bcfg.MAX_QUERIES_PER_BATCH} reached"})
            continue
        seen.add(q)
        accepted.append({"i": len(accepted) + 1, "kind": kind, "query": q})
    return accepted, rejected


def run_batch_probe(
    queries: Any,
    *,
    session: IsoSession,
) -> dict[str, Any]:
    """Execute one BatchProbe round. Returns a structured observation dict."""
    accepted, rejected = _normalize_queries(queries)
    if not accepted:
        return {
            "ok": False, "blocked": True, "official_eval": False, "sandboxed": True,
            "n_requested": len(rejected), "n_run": 0,
            "text": json.dumps({"evidence": [], "rejected": rejected,
                                "note": "no runnable query in batch"}, ensure_ascii=False),
        }
    evidence: list[dict[str, Any]] = []
    combined_parts: list[str] = []
    for item in accepted:
        try:
            obs = run_sandboxed(
                item["query"],
                jail=session.host_dir,
                timeout=bcfg.PROBE_TIMEOUT_S,
                max_bytes=bcfg.PROBE_MAX_CHARS,
            )
        except SandboxError as exc:
            evidence.append({"i": item["i"], "kind": item["kind"] or "env", "ok": False,
                             "output": f"probe blocked: {exc}"})
            continue
        out = (obs.get("text") or "")
        status = "ok" if obs.get("ok") else (obs.get("reason") or "nonzero exit")
        evidence.append({
            "i": item["i"],
            "kind": item["kind"] or classify_output_kind(out),
            "ok": bool(obs.get("ok")),
            "status": status,
            "output": out[: bcfg.PROBE_MAX_CHARS],
        })
        combined_parts.append(out)
    combined = "\n".join(combined_parts)
    hits = scan_text(combined)
    if hits:
        return {
            "ok": False, "blocked": True, "official_eval": False, "sandboxed": True,
            "canary_hits": len(hits), "n_requested": len(accepted) + len(rejected),
            "n_run": 0,
            "text": "BatchProbe blocked: sealed pattern in output (no content returned)",
        }
    result = {
        "evidence": evidence,
        "rejected": rejected,
        "n_requested": len(accepted) + len(rejected),
        "n_run": len(accepted),
    }
    text = json.dumps(result, ensure_ascii=False)
    return {
        "ok": True, "blocked": False, "official_eval": False, "sandboxed": True,
        "n_requested": result["n_requested"], "n_run": result["n_run"],
        "evidence": evidence, "rejected": rejected,
        "text": text[: bcfg.PROBE_MAX_CHARS * len(evidence) + 400],
    }
