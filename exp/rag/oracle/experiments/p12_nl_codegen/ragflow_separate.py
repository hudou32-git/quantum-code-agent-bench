"""RAGFlow MULTI_DATASET_SEPARATE retrieval for formal P12 RAG arms.

Three specialty datasets are queried independently, merged by combined score,
then truncated to top_k. No silent fallback to local TF-IDF.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from oracle_mvp.rag.ragflow_client import resolve_ragflow_retrieval_url
from oracle_mvp.rag.retriever import RetrievalHit

CFG_PATH = Path(__file__).resolve().parent / "config" / "RAGFLOW_SEPARATE_RUNTIME.json"
FSE2027_CFG_PATH = Path(__file__).resolve().parent / "config" / "FSE2027_QISKIT_RAG_RUNTIME.json"

_DATASET_SOURCE_HINT = {
    "P14_QISKIT_API_V241": "RAG_qiskit_api",
    "P14_QISKIT_USAGE_RUNTIME_V241": "RAG_qiskit_recipes",
    "P14_QUANTUM_ALGORITHMS": "RAG_quantum_algorithms",
    "qiskit_k1_primary": "qiskit_k1_primary",
    "qiskit_k2_primary": "qiskit_k2_primary",
    "qiskit_k3_primary": "qiskit_k3_primary",
    "cirq_k1_primary": "cirq_k1_primary",
    "cirq_k2_primary": "cirq_k2_primary",
    "cirq_k3_primary": "cirq_k3_primary",
    "pennylane_k1_primary": "pennylane_k1_primary",
    "pennylane_k2_primary": "pennylane_k2_primary",
    "pennylane_k3_primary": "pennylane_k3_primary",
}


def load_separate_runtime_cfg() -> dict:
    import os

    override = (os.environ.get("ORACLE_SEPARATE_RUNTIME_CFG") or "").strip()
    if override:
        return json.loads(Path(override).read_text(encoding="utf-8"))
    if (os.environ.get("ORACLE_FSE2027_RAG") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return json.loads(FSE2027_CFG_PATH.read_text(encoding="utf-8"))
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def _host_and_key() -> Tuple[str, str]:
    url = resolve_ragflow_retrieval_url()
    if not url:
        raise RuntimeError("RAGFLOW_RETRIEVAL_URL / RAGFLOW_ADDRESS unset")
    host = url.rsplit("/api/", 1)[0] if "/api/" in url else url.rstrip("/")
    import os

    key = (os.environ.get("RAGFLOW_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("RAGFLOW_API_KEY unset")
    return host.rstrip("/"), key


def _retrieval_one(
    host: str,
    key: str,
    *,
    question: str,
    dataset_id: str,
    page_size: int,
    similarity_threshold: float,
    vector_similarity_weight: float,
    timeout: float,
) -> Tuple[List[dict], float, Optional[str]]:
    payload = {
        "question": question,
        "dataset_ids": [dataset_id],
        "page_size": page_size,
        "similarity_threshold": similarity_threshold,
        "vector_similarity_weight": vector_similarity_weight,
        "top_k": 1024,
        "highlight": False,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(
            f"{host}/api/v1/retrieval",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        wall = time.perf_counter() - t0
        if data.get("code") != 0:
            return [], wall, f"code={data.get('code')} msg={data.get('message')}"
        chunks = ((data.get("data") or {}).get("chunks") if isinstance(data.get("data"), dict) else None) or []
        return chunks, wall, None
    except Exception as e:
        return [], time.perf_counter() - t0, f"{type(e).__name__}: {e}"


_RETRIEVE_SEM = None
_RETRIEVE_SEM_LOCK = __import__("threading").Lock()


def _retrieve_sem():
    """Limit concurrent SEPARATE HTTP calls (3 datasets each)."""
    global _RETRIEVE_SEM
    with _RETRIEVE_SEM_LOCK:
        if _RETRIEVE_SEM is None:
            import os
            from threading import Semaphore

            # Default: at most 4 SEPARATE tasks in flight → ≤12 dataset requests.
            n = int(os.environ.get("ORACLE_SEPARATE_MAX_INFLIGHT", "4") or "4")
            _RETRIEVE_SEM = Semaphore(max(1, n))
        return _RETRIEVE_SEM


def retrieve_separate_hits(
    question: str,
    *,
    top_k: int = 3,
    cfg: Optional[dict] = None,
) -> Tuple[List[RetrievalHit], Dict[str, Any]]:
    """Run SEPARATE retrieval; raise on any dataset failure (no local fallback)."""
    sem = _retrieve_sem()
    sem.acquire()
    try:
        return _retrieve_separate_hits_unlocked(question, top_k=top_k, cfg=cfg)
    finally:
        sem.release()


def _retrieve_separate_hits_unlocked(
    question: str,
    *,
    top_k: int = 3,
    cfg: Optional[dict] = None,
) -> Tuple[List[RetrievalHit], Dict[str, Any]]:
    """Run SEPARATE retrieval; raise on any dataset failure (no local fallback)."""
    cfg = cfg or load_separate_runtime_cfg()
    host, key = _host_and_key()
    ds_map: Dict[str, str] = cfg["dataset_ids"]
    per_k = int(cfg.get("per_dataset_k") or 3)
    thr = float(cfg.get("similarity_threshold") or 0.1)
    vw = float(cfg.get("vector_similarity_weight") or 0.5)
    timeout = float(cfg.get("timeout_s") or 120.0)
    snippet_chars = int(cfg.get("snippet_chars") or 900)

    layer_map: Dict[str, str] = dict(cfg.get("knowledge_layer_by_dataset") or {})
    arch = str(cfg.get("retriever_architecture") or "RAGFLOW_MULTI_DATASET_SEPARATE")
    final_k = int(cfg.get("top_k_final") or top_k)
    use_k = max(1, min(int(top_k), final_k))

    merged: List[Tuple[float, str, dict, str, int]] = []
    walls: Dict[str, float] = {}
    errors: List[str] = []

    def _one(ds_name: str, dsid: str):
        chunks, wall, err = _retrieval_one(
            host,
            key,
            question=question,
            dataset_id=dsid,
            page_size=max(per_k, 5),
            similarity_threshold=thr,
            vector_similarity_weight=vw,
            timeout=timeout,
        )
        return ds_name, dsid, chunks, wall, err

    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(_one, name, dsid) for name, dsid in ds_map.items()]
        for fut in as_completed(futs):
            ds_name, dsid, chunks, wall, err = fut.result()
            walls[ds_name] = wall
            if err:
                errors.append(f"{ds_name}:{err}")
                continue
            for layer_rank, ch in enumerate(chunks[:per_k], 1):
                score = float(ch.get("similarity") or ch.get("score") or ch.get("vector_similarity") or -1.0)
                merged.append((score, ds_name, ch, dsid, layer_rank))

    if errors:
        raise RuntimeError(
            "RAGFLOW_SEPARATE_FAILED (no local fallback): " + "; ".join(errors)
        )
    if not merged:
        raise RuntimeError("RAGFLOW_SEPARATE_EMPTY: no chunks from any specialty dataset")

    merged.sort(key=lambda x: x[0], reverse=True)
    hits: List[RetrievalHit] = []
    retrieval_trace: List[dict] = []
    for global_rank, (score, ds_name, ch, dsid, layer_rank) in enumerate(merged, 1):
        content = ch.get("content") or ch.get("content_ltks") or ""
        if len(content) > snippet_chars:
            content = content[:snippet_chars] + "\n..."
        cid = str(ch.get("id") or ch.get("chunk_id") or "")
        doc_id = cid or str(ch.get("document_id") or f"{ds_name}_{global_rank}")
        keyword = str(ch.get("document_keyword") or ch.get("keyword") or doc_id)
        layer = layer_map.get(ds_name) or (
            "K1" if "_k1_" in ds_name else "K2" if "_k2_" in ds_name else "K3" if "_k3_" in ds_name else ds_name
        )
        selected = global_rank <= use_k
        retrieval_trace.append(
            {
                "kb_id": dsid,
                "kb_name": ds_name,
                "knowledge_layer": layer,
                "chunk_id": cid,
                "document_keyword": keyword,
                "retrieval_score": score,
                "layer_rank": layer_rank,
                "global_rank": global_rank,
                "final_selected": selected,
            }
        )
        if selected:
            hits.append(
                RetrievalHit(
                    doc_id=doc_id,
                    path=str(ch.get("document_id") or doc_id),
                    title=keyword,
                    score=score,
                    snippet=content,
                    source_dir=_DATASET_SOURCE_HINT.get(ds_name, ds_name),
                )
            )

    diag_meta = {
        "architecture": arch,
        "backend": arch,
        "dataset_ids": ds_map,
        "per_dataset_k": per_k,
        "top_k_final": use_k,
        "similarity_threshold": thr,
        "vector_similarity_weight": vw,
        "reranker": cfg.get("reranker", "disabled"),
        "walls_s": walls,
        "latency_seconds": sum(walls.values()),
        "n_merged_candidates": len(merged),
        "silent_local_fallback": False,
        "retrieval_trace": retrieval_trace,
        "query": question,
    }
    return hits, diag_meta
