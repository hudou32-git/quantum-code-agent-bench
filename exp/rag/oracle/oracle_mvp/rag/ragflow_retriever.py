"""RAGFlow multi-dataset retriever modes for P14 (no silent local fallback)."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from oracle_mvp.rag.ragflow_client import (
    RagFlowChunk,
    default_page_size,
    default_similarity_threshold,
    default_timeout,
    fetch_rag_context,
    parse_rag_chunks,
    ragflow_credentials,
)
from oracle_mvp.rag.retriever import LocalKbRetriever, RetrievalHit


@dataclass
class RetrievedChunk:
    chunk_id: Optional[str]
    document_id: Optional[str]
    dataset_id: Optional[str]
    dataset_name: Optional[str]
    document_family: Optional[str]
    content: Optional[str]
    score: Optional[float]
    keyword_score: Optional[float] = None
    vector_score: Optional[float] = None
    rerank_score: Optional[float] = None
    source_path: Optional[str] = None
    text_hash: Optional[str] = None
    rank: Optional[int] = None

    def to_hit(self) -> RetrievalHit:
        return RetrievalHit(
            doc_id=self.chunk_id or self.document_id or f"rank_{self.rank}",
            path=self.source_path or self.document_id or "",
            title=self.chunk_id or "",
            score=float(self.score or 0.0),
            snippet=(self.content or "")[:900],
            source_dir=self.document_family or "RAGFLOW",
        )


def _family_from_keyword(keyword: str) -> str:
    key = (keyword or "").replace("\\", "/")
    base = key.rsplit("/", 1)[-1]
    for fam in (
        "RAG_qiskit_api",
        "RAG_qiskit_recipes",
        "RAG_qiskit_human_eval_runtime",
        "RAG_qiskit_human_eval_topics",
        "RAG_quantum_algorithms",
    ):
        if fam in key:
            return fam
    if base.startswith("heval_") or "heval_" in base:
        return "RAG_qiskit_human_eval_runtime"
    if base.startswith("recipe_") or "recipe_" in base:
        return "RAG_qiskit_recipes"
    if base.startswith("algo_") or "algo_" in base:
        return "RAG_quantum_algorithms"
    # Local API docs are named qiskit_*.md without directory prefix in RAGFlow keyword.
    if base.startswith("qiskit_") or base.startswith("qiskit."):
        return "RAG_qiskit_api"
    return "UNKNOWN"


def _chunk_to_retrieved(
    ch: RagFlowChunk,
    *,
    dataset_id: str,
    dataset_name: str,
    rank: int,
    raw_obj: Optional[dict] = None,
) -> RetrievedChunk:
    # keyword/vector scores only if present in raw chunk dict — not forged
    return RetrievedChunk(
        chunk_id=ch.keyword or ch.chunk_id or None,
        document_id=ch.document_id or None,
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        document_family=_family_from_keyword(ch.keyword),
        content=ch.content,
        score=ch.similarity,
        keyword_score=None,
        vector_score=None,
        rerank_score=None,
        source_path=ch.keyword or None,
        text_hash=hashlib.sha256(ch.content.encode("utf-8")).hexdigest() if ch.content else None,
        rank=rank,
    )


class MultiDatasetRagFlowRetriever:
    """Supports ALL_IN_ONE / JOINT / SEPARATE modes. Never falls back to TF-IDF."""

    MODE_ALL_IN_ONE = "RAGFLOW_ALL_IN_ONE"
    MODE_JOINT = "RAGFLOW_MULTI_DATASET_JOINT"
    MODE_SEPARATE = "RAGFLOW_MULTI_DATASET_SEPARATE"

    def __init__(
        self,
        *,
        mode: str,
        dataset_map: Dict[str, str],
        # dataset_map: name -> id
        page_size: Optional[int] = None,
        per_dataset_k: int = 3,
        similarity_threshold: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> None:
        url, _, key = ragflow_credentials()
        if not (url and key and dataset_map):
            raise RuntimeError("RAGFlow credentials/dataset_map required; no local fallback")
        self.mode = mode
        self.dataset_map = dict(dataset_map)
        self.retrieval_url = url
        self.api_key = key
        self.page_size = page_size or default_page_size()
        self.per_dataset_k = per_dataset_k
        self.similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else default_similarity_threshold()
        )
        self.timeout = timeout if timeout is not None else default_timeout()
        self.last_raw_responses: Dict[str, str] = {}
        self.last_wall_seconds: float = 0.0
        self.last_service_error: Optional[str] = None
        self.docs: List = []

    def retrieve(
        self,
        query: str,
        top_k: int,
        *,
        task_id: str | None = None,
    ) -> List[RetrievedChunk]:
        self.last_service_error = None
        self.last_raw_responses = {}
        wall_total = 0.0

        if self.mode == self.MODE_ALL_IN_ONE:
            name = "P14_QISKIT_ALL_IN_ONE_BASELINE"
            if name not in self.dataset_map:
                # fall back to single provided dataset
                name = next(iter(self.dataset_map))
            ids = [self.dataset_map[name]]
            raw, wall = fetch_rag_context(
                question=query,
                retrieval_url=self.retrieval_url,
                dataset_id=ids[0],
                api_key=self.api_key,
                page_size=max(top_k, self.page_size, 5),
                similarity_threshold=self.similarity_threshold,
                timeout=self.timeout,
            )
            wall_total += wall
            self.last_raw_responses[name] = raw
            if raw.startswith("[RAG 检索失败"):
                self.last_service_error = raw
                self.last_wall_seconds = wall_total
                return []
            chunks = parse_rag_chunks(raw)
            out = [
                _chunk_to_retrieved(ch, dataset_id=ids[0], dataset_name=name, rank=i)
                for i, ch in enumerate(chunks[:top_k], 1)
            ]
            self.last_wall_seconds = wall_total
            return out

        if self.mode == self.MODE_JOINT:
            # One request with multiple dataset_ids via extended payload
            names = [n for n in self.dataset_map if n != "P14_QISKIT_ALL_IN_ONE_BASELINE"]
            ids = [self.dataset_map[n] for n in names]
            # fetch_rag_context currently takes one dataset_id; call joint helper
            raw, wall = self._fetch_multi(query, ids, page_size=max(top_k, self.page_size, 5))
            wall_total += wall
            self.last_raw_responses["JOINT"] = raw
            if raw.startswith("[RAG 检索失败"):
                self.last_service_error = raw
                self.last_wall_seconds = wall_total
                return []
            chunks = parse_rag_chunks(raw)
            out = []
            for i, ch in enumerate(chunks[:top_k], 1):
                # dataset id unknown per chunk unless present; leave from chunk if any
                out.append(
                    RetrievedChunk(
                        chunk_id=ch.keyword or ch.chunk_id or None,
                        document_id=ch.document_id or None,
                        dataset_id=None,
                        dataset_name="JOINT",
                        document_family=_family_from_keyword(ch.keyword),
                        content=ch.content,
                        score=ch.similarity,
                        source_path=ch.keyword or None,
                        text_hash=hashlib.sha256(ch.content.encode()).hexdigest(),
                        rank=i,
                    )
                )
            self.last_wall_seconds = wall_total
            return out

        if self.mode == self.MODE_SEPARATE:
            merged: List[RetrievedChunk] = []
            names = [n for n in self.dataset_map if n != "P14_QISKIT_ALL_IN_ONE_BASELINE"]
            for name in names:
                dsid = self.dataset_map[name]
                raw, wall = fetch_rag_context(
                    question=query,
                    retrieval_url=self.retrieval_url,
                    dataset_id=dsid,
                    api_key=self.api_key,
                    page_size=self.per_dataset_k,
                    similarity_threshold=self.similarity_threshold,
                    timeout=self.timeout,
                )
                wall_total += wall
                self.last_raw_responses[name] = raw
                if raw.startswith("[RAG 检索失败"):
                    self.last_service_error = raw
                    self.last_wall_seconds = wall_total
                    return []  # no silent partial fallback
                for ch in parse_rag_chunks(raw)[: self.per_dataset_k]:
                    merged.append(
                        _chunk_to_retrieved(ch, dataset_id=dsid, dataset_name=name, rank=0)
                    )
            merged.sort(key=lambda c: float(c.score or 0.0), reverse=True)
            out = []
            for i, c in enumerate(merged[:top_k], 1):
                c.rank = i
                out.append(c)
            self.last_wall_seconds = wall_total
            return out

        raise ValueError(f"Unknown mode: {self.mode}")

    def _fetch_multi(self, question: str, dataset_ids: Sequence[str], page_size: int):
        import json
        import time
        import urllib.request

        payload = {
            "question": question,
            "dataset_ids": list(dataset_ids),
            "page_size": page_size,
            "similarity_threshold": self.similarity_threshold,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        t0 = time.perf_counter()
        try:
            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                self.retrieval_url, data=body, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8")
            return text, time.perf_counter() - t0
        except Exception as e:
            return f"[RAG 检索失败: {e}]", time.perf_counter() - t0

    def retrieve_hits(self, query: str, top_k: int) -> List[RetrievalHit]:
        return [c.to_hit() for c in self.retrieve(query, top_k)]
