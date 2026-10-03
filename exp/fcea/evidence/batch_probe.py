"""FCEA BatchProbe wrapper.

Reuses the Batch-EQPA normalization rules, sandbox primitive, clipping caps and
canary gate UNCHANGED (exp.evidence_eqpa.tools._normalize_queries,
exp.eqpa.bwrap.run_sandboxed, exp.common.canary.scan_text); the only difference
is that each evidence item KEEPS its query text and the model's requested kind,
because RQ4 allocation analysis needs the command face (recommended -> actual
-> outcome). exp/evidence_eqpa/ itself is never modified.
"""
from __future__ import annotations

import json
from typing import Any

from exp.common.canary import scan_text
from exp.eqpa.bwrap import SandboxError, run_sandboxed
from exp.eqpa.jail import IsoSession
from exp.evidence_eqpa.tools import _normalize_queries

from exp.fcea import config as fcfg


def run_fcea_batch_probe(queries: Any, *, session: IsoSession) -> dict[str, Any]:
    accepted, rejected = _normalize_queries(queries)
    if not accepted:
        return {
            "ok": False, "blocked": True, "official_eval": False, "sandboxed": True,
            "n_requested": len(rejected), "n_run": 0,
            "evidence": [], "rejected": rejected,
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
                timeout=fcfg.PROBE_TIMEOUT_S,
                max_bytes=fcfg.PROBE_MAX_CHARS,
            )
        except SandboxError as exc:
            evidence.append({"i": item["i"], "kind": item["kind"], "query": item["query"],
                             "ok": False, "status": f"probe blocked: {exc}", "output": ""})
            continue
        out = (obs.get("text") or "")
        status = "ok" if obs.get("ok") else (obs.get("reason") or "nonzero exit")
        evidence.append({
            "i": item["i"], "kind": item["kind"], "query": item["query"],
            "ok": bool(obs.get("ok")), "status": status,
            "output": out[: fcfg.PROBE_MAX_CHARS],
        })
        combined_parts.append(out)
    combined = "\n".join(combined_parts)
    hits = scan_text(combined)
    if hits:
        return {
            "ok": False, "blocked": True, "official_eval": False, "sandboxed": True,
            "canary_hits": len(hits), "n_requested": len(accepted) + len(rejected),
            "n_run": 0, "evidence": [], "rejected": rejected,
            "text": "BatchProbe blocked: sealed pattern in output (no content returned)",
        }
    n_run = len(accepted)
    text = json.dumps({
        "evidence": [{k: e[k] for k in ("i", "kind", "ok", "status", "output")} for e in evidence],
        "rejected": rejected, "n_requested": len(accepted) + len(rejected), "n_run": n_run,
    }, ensure_ascii=False)
    return {
        "ok": True, "blocked": False, "official_eval": False, "sandboxed": True,
        "n_requested": len(accepted) + len(rejected), "n_run": n_run,
        "evidence": evidence, "rejected": rejected,
        "text": text[: fcfg.PROBE_MAX_CHARS * n_run + 400],
    }
