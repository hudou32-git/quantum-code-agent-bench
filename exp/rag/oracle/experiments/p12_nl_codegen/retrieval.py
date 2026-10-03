"""KB retrieval for P12-NL.

Formal RAG arms use RAGFlow MULTI_DATASET_SEPARATE (no local fallback).
Local TF-IDF remains for shuffled-context control (C1) and leakage affinity.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

from oracle_mvp.rag.retriever import LocalKbRetriever, RagFlowRetriever

from experiments.p12_nl_codegen.config import (
    CROSS_TASK_SIM_THRESHOLD,
    DATASET,
    RAG_BACKEND,
    RAG_CONTEXT_MAX_CHARS,
    RAG_KB,
    RAG_SNIPPET_CHARS,
    RAG_TOP_K,
    SHUFFLED_RAG_SEED,
    TEMPORAL_LEAKAGE_EXCLUDE,
)
from experiments.p12_nl_codegen.ragflow_separate import retrieve_separate_hits
from experiments.p12_nl_codegen.retention.hashutil import sha256_text

_API = re.compile(
    r"\b(QuantumCircuit|QuantumRegister|ClassicalRegister|measure|cx|Statevector|"
    r"Sampler|Estimator|transpile|Aer|Operator)\b",
    re.I,
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a[:3000], b[:3000]).ratio()


class KbRetriever:
    def __init__(self, backend: Optional[str] = None) -> None:
        if not RAG_KB.exists():
            raise FileNotFoundError(RAG_KB)
        # Local corpus always loaded for shuffled controls + leakage affinity.
        self.local = LocalKbRetriever(RAG_KB, max_chars_per_doc=4000)
        if not self.local.docs:
            raise RuntimeError("empty RAG KB")
        name = (backend or os.environ.get("ORACLE_RAG_BACKEND") or RAG_BACKEND or "ragflow").strip().lower()
        if name in {"local", "tfidf", "offline"}:
            self.backend = self.local
            self.backend_name = "LOCAL_TFIDF_rag_kb"
        else:
            self.backend = RagFlowRetriever(snippet_chars=RAG_SNIPPET_CHARS)
            self.backend_name = "RAGFLOW"
        # Compatibility: shuffled still iterates self.backend.docs for local mode;
        # for RAGFlow mode use self.local.docs.
        self.docs = self.local.docs
        self._tasks = json.loads(DATASET.read_text(encoding="utf-8"))
        self._variant_pairs = self._build_variant_pairs()
        self._entry_to_tasks: Dict[str, List[str]] = {}
        for t in self._tasks:
            ep = t.get("entry_point") or ""
            if ep:
                self._entry_to_tasks.setdefault(ep, []).append(t["task_id"])
        # Lazy: doc affinity only computed for candidate hits
        self._doc_task_affinity: Dict[str, List[Tuple[str, float]]] = {}

    def _build_variant_pairs(self) -> List[Tuple[str, str, float]]:
        pairs = []
        texts = []
        for t in self._tasks:
            blob = _norm((t.get("prompt") or "") + "\n" + (t.get("canonical_solution") or ""))
            texts.append((t["task_id"], blob, t.get("entry_point") or ""))
        # Fast path: same entry_point => variant candidate; then confirm sim
        by_ep: Dict[str, List[Tuple[str, str]]] = {}
        for tid, blob, ep in texts:
            if ep:
                by_ep.setdefault(ep, []).append((tid, blob))
        for ep, items in by_ep.items():
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    s = _sim(items[i][1], items[j][1])
                    if s >= CROSS_TASK_SIM_THRESHOLD:
                        pairs.append((items[i][0], items[j][0], round(s, 4)))
        # Also prompt-only high similarity sampling among nearby ids (optional dense check on first 40)
        for i in range(len(texts)):
            for j in range(i + 1, min(i + 8, len(texts))):
                if texts[i][2] and texts[i][2] == texts[j][2]:
                    continue  # already covered
                s = _sim(texts[i][1], texts[j][1])
                if s >= CROSS_TASK_SIM_THRESHOLD:
                    pairs.append((texts[i][0], texts[j][0], round(s, 4)))
        return pairs

    def variant_map(self) -> Dict[str, List[str]]:
        m: Dict[str, List[str]] = {t["task_id"]: [] for t in self._tasks}
        for a, b, _ in self._variant_pairs:
            m[a].append(b)
            m[b].append(a)
        return m

    def _affinity_for_doc(self, doc_id: str, text: str) -> List[Tuple[str, float]]:
        if doc_id in self._doc_task_affinity:
            return self._doc_task_affinity[doc_id]
        nd = _norm(text)
        hits = []
        # Prefer tasks whose entry_point appears as a def in the doc
        for ep, tids in self._entry_to_tasks.items():
            if re.search(rf"\bdef\s+{re.escape(ep)}\s*\(", text or ""):
                for tid in tids:
                    t = next(x for x in self._tasks if x["task_id"] == tid)
                    nc = _norm(t.get("canonical_solution") or "")
                    sp = _sim(nd, _norm(t.get("prompt") or ""))
                    sc = _sim(nd, nc) if nc else 0.0
                    s = max(sc, sp)
                    if s >= CROSS_TASK_SIM_THRESHOLD * 0.9:  # slightly softer when entry def present
                        hits.append((tid, round(max(s, CROSS_TASK_SIM_THRESHOLD), 4)))
        hits.sort(key=lambda x: -x[1])
        self._doc_task_affinity[doc_id] = hits[:5]
        return self._doc_task_affinity[doc_id]

    def query(self, task: dict, *, formal_rag: bool = False) -> str:
        prompt = task.get("prompt") or ""
        # FSE2027 formal protocol: identical query across K1/K2/K3.
        if formal_rag or (os.environ.get("ORACLE_FSE2027_RAG") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            fw = (os.environ.get("ORACLE_RAG_FRAMEWORK") or "qiskit").strip().lower()
            return f"Framework: {fw}\nTask:\n{prompt}"
        apis = " ".join(sorted(set(_API.findall(prompt))))
        return f"entry={task.get('entry_point')}\n{apis}\n{prompt[:2500]}"

    def _hit_to_doc(self, hit) -> dict:
        snip = hit.snippet or ""
        if len(snip) > RAG_SNIPPET_CHARS:
            snip = snip[:RAG_SNIPPET_CHARS] + "\n..."
        return {
            "record_id": hit.doc_id,
            "doc_id": hit.doc_id,
            "title": hit.title,
            "source_dir": hit.source_dir,
            "snippet": snip,
            "score": float(hit.score),
        }

    def _truncate(self, docs: List[dict]) -> List[dict]:
        out, used = [], 0
        for d in docs:
            n = len(d.get("snippet") or "") + len(d.get("title") or "")
            if used + n > RAG_CONTEXT_MAX_CHARS and out:
                break
            out.append(d)
            used += n
        return out

    def _ban_for_task(self, task: dict, candidate_docs: Optional[List] = None) -> Set[str]:
        if not TEMPORAL_LEAKAGE_EXCLUDE:
            return set()
        tid = task.get("task_id") or ""
        variants = set(self.variant_map().get(tid, []))
        variants.add(tid)
        ban = set()
        docs = candidate_docs if candidate_docs is not None else []
        for d in docs:
            doc_id = getattr(d, "doc_id", None) or (d.get("doc_id") if isinstance(d, dict) else None)
            text = getattr(d, "text", None) or getattr(d, "snippet", None) or (
                d.get("snippet") if isinstance(d, dict) else ""
            ) or ""
            if not doc_id:
                continue
            for hid, _simv in self._affinity_for_doc(doc_id, text):
                if hid in variants:
                    ban.add(doc_id)
                    break
        return ban

    def matched(
        self,
        task: dict,
        *,
        top_k: int = RAG_TOP_K,
        formal_rag: bool = False,
        backend_override: Optional[str] = None,
    ) -> Tuple[List[dict], dict]:
        """Retrieve Top-k context docs.

        formal_rag=True (G3/G4/E2/E3/I2/I3): always RAGFlow SEPARATE; never local.
        backend_override=\"local\": force local TF-IDF for this call (C1 length ref).
        """
        q = self.query(task, formal_rag=formal_rag)
        if formal_rag:
            return self._matched_separate(task, q=q, top_k=top_k)

        backend = self.backend
        backend_name = self.backend_name
        if backend_override:
            ov = backend_override.strip().lower()
            if ov in {"local", "tfidf", "offline"}:
                backend = self.local
                backend_name = "LOCAL_TFIDF_rag_kb"
            elif ov in {"ragflow", "separate"}:
                raise ValueError(
                    "backend_override cannot select SEPARATE; use formal_rag=True"
                )

        hits = backend.retrieve(q, top_k=max(top_k * 5, 15))
        # Temporarily swap names for diag below when override used
        prev_backend, prev_name = self.backend, self.backend_name
        self.backend, self.backend_name = backend, backend_name
        try:
            return self._finalize_matched(task, q=q, hits=hits, top_k=top_k)
        finally:
            self.backend, self.backend_name = prev_backend, prev_name

    def _matched_separate(
        self, task: dict, *, q: str, top_k: int
    ) -> Tuple[List[dict], dict]:
        # FSE2027 / SEPARATE already apply final Top-K inside retrieve_separate_hits.
        hits, sep_meta = retrieve_separate_hits(q, top_k=top_k)
        ban = self._ban_for_task(task, candidate_docs=hits)
        all_ranked = []
        for rank, h in enumerate(hits, 1):
            all_ranked.append(
                {
                    "rank": rank,
                    "chunk_id": h.doc_id,
                    "score": float(h.score),
                    "excluded_temporal": h.doc_id in ban,
                    "source_dir": h.source_dir,
                }
            )
        filtered = []
        excluded = []
        for h in hits:
            if h.doc_id in ban:
                excluded.append(h.doc_id)
                continue
            filtered.append(h)
            if len(filtered) >= top_k:
                break
        selected_ids = {h.doc_id for h in filtered[:top_k]}
        for c in all_ranked:
            c["selected"] = c["chunk_id"] in selected_ids and not c["excluded_temporal"]
        docs = self._truncate([self._hit_to_doc(h) for h in filtered[:top_k]])
        selected_context = "\n\n".join(
            f"[{d['doc_id']}]\n{d.get('snippet') or ''}" for d in docs
        )
        diag = {
            "mode": "matched",
            "retrieval_type": "MATCHED",
            "query_raw": q,
            "query_normalized": q,
            "query_hash": sha256_text(q),
            "ids": [d["doc_id"] for d in docs],
            "scores": [d["score"] for d in docs],
            "source_dirs": [d["source_dir"] for d in docs],
            "backend": sep_meta.get("backend") or sep_meta.get("architecture") or "RAGFLOW_MULTI_DATASET_SEPARATE",
            "query_preview": q[:200],
            "temporal_excluded_doc_ids": excluded[:20],
            "n_variant_tasks": len(self.variant_map().get(task.get("task_id") or "", [])),
            "all_ranked_candidates": all_ranked,
            "selected_chunk_ids": [d["doc_id"] for d in docs],
            "selected_context_text": selected_context,
            "selected_context_hash": sha256_text(selected_context),
            "top_k": top_k,
            "candidate_count": len(all_ranked),
            "latency_seconds": float(sep_meta.get("latency_seconds") or 0.0),
            "retry_count": 0,
            "service_error": None,
            "silent_local_fallback": False,
            "retrieval_trace": sep_meta.get("retrieval_trace") or [],
            "request_parameters": {
                "architecture": sep_meta.get("architecture"),
                "dataset_ids": sep_meta.get("dataset_ids"),
                "per_dataset_k": sep_meta.get("per_dataset_k"),
                "top_k_final": sep_meta.get("top_k_final"),
                "similarity_threshold": sep_meta.get("similarity_threshold"),
                "vector_similarity_weight": sep_meta.get("vector_similarity_weight"),
                "reranker": sep_meta.get("reranker"),
                "walls_s": sep_meta.get("walls_s"),
            },
        }
        if not docs:
            raise RuntimeError(
                f"RAGFLOW_SEPARATE_EMPTY_AFTER_FILTER task={task.get('task_id')}"
            )
        return docs, diag

    def _finalize_matched(
        self, task: dict, *, q: str, hits, top_k: int
    ) -> Tuple[List[dict], dict]:
        ban = self._ban_for_task(task, candidate_docs=hits)
        all_ranked = []
        for i, h in enumerate(hits, 1):
            text = h.snippet or getattr(h, "text", "") or ""
            all_ranked.append(
                {
                    "rank": i,
                    "chunk_id": h.doc_id,
                    "score": float(h.score),
                    "source_file": h.doc_id,
                    "source_dir_family": h.source_dir,
                    "title": h.title,
                    "text": text,
                    "text_hash": sha256_text(text),
                    "selected": False,
                    "excluded_temporal": h.doc_id in ban,
                }
            )
        filtered = []
        excluded = []
        for h in hits:
            if h.doc_id in ban:
                excluded.append(h.doc_id)
                continue
            filtered.append(h)
            if len(filtered) >= top_k:
                break
        selected_ids = {h.doc_id for h in filtered[:top_k]}
        for c in all_ranked:
            c["selected"] = c["chunk_id"] in selected_ids and not c["excluded_temporal"]
        docs = self._truncate([self._hit_to_doc(h) for h in filtered[:top_k]])
        selected_context = "\n\n".join(
            f"[{d['doc_id']}]\n{d.get('snippet') or ''}" for d in docs
        )
        raw_resp = getattr(self.backend, "last_raw_response", None)
        service_error = (
            raw_resp
            if isinstance(raw_resp, str) and raw_resp.startswith("[RAG 检索失败")
            else None
        )
        diag = {
            "mode": "matched",
            "retrieval_type": "MATCHED",
            "query_raw": q,
            "query_normalized": q,
            "query_hash": sha256_text(q),
            "ids": [d["doc_id"] for d in docs],
            "scores": [d["score"] for d in docs],
            "source_dirs": [d["source_dir"] for d in docs],
            "backend": self.backend_name,
            "query_preview": q[:200],
            "temporal_excluded_doc_ids": excluded[:20],
            "n_variant_tasks": len(self.variant_map().get(task.get("task_id") or "", [])),
            "all_ranked_candidates": all_ranked,
            "selected_chunk_ids": [d["doc_id"] for d in docs],
            "selected_context_text": selected_context,
            "selected_context_hash": sha256_text(selected_context),
            "top_k": top_k,
            "candidate_count": len(all_ranked),
            "latency_seconds": float(getattr(self.backend, "last_wall_seconds", 0.0) or 0.0),
            "retry_count": 0,
            "service_error": service_error,
            "silent_local_fallback": False,
            "request_parameters": {
                "page_size": getattr(self.backend, "page_size", None),
                "similarity_threshold": getattr(self.backend, "similarity_threshold", None),
                "dataset_id_set": bool(getattr(self.backend, "dataset_id", None)),
                "retrieval_url_set": bool(getattr(self.backend, "retrieval_url", None)),
            },
        }
        return docs, diag

    def shuffled(
        self,
        task: dict,
        matched_docs: List[dict],
        *,
        top_k: int = RAG_TOP_K,
        seed: int = SHUFFLED_RAG_SEED,
    ) -> Tuple[List[dict], dict]:
        tid = task.get("task_id") or ""
        task_seed = int(hashlib.sha256(f"{seed}:{tid}".encode()).hexdigest()[:8], 16)
        rng = random.Random(task_seed)
        ban = {d["doc_id"] for d in matched_docs} | self._ban_for_task(task, candidate_docs=matched_docs)
        prefer_dirs = {d.get("source_dir") for d in matched_docs if d.get("source_dir")}
        pool_pref = [d for d in self.local.docs if d.doc_id not in ban and d.source_dir in prefer_dirs]
        pool_all = [d for d in self.local.docs if d.doc_id not in ban]
        pool = pool_pref if len(pool_pref) >= top_k else pool_all
        rng.shuffle(pool)
        want_lens = [len(d.get("snippet") or "") for d in matched_docs] or [RAG_SNIPPET_CHARS] * top_k
        chosen = []
        remaining = pool[:]
        for want in want_lens[:top_k]:
            if not remaining:
                break
            best = min(remaining, key=lambda d: abs(len(d.text) - max(want, 200)))
            chosen.append(best)
            remaining.remove(best)
        while len(chosen) < top_k and remaining:
            chosen.append(remaining.pop())
        docs = []
        for d in chosen:
            snip = d.text
            if len(snip) > RAG_SNIPPET_CHARS:
                snip = snip[:RAG_SNIPPET_CHARS] + "\n..."
            docs.append(
                {
                    "record_id": d.doc_id,
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "source_dir": d.source_dir,
                    "snippet": snip,
                    "score": 0.0,
                    "_shuffled": True,
                }
            )
        docs = self._truncate(docs)
        selected_context = "\n\n".join(f"[{d['doc_id']}]\n{d.get('snippet') or ''}" for d in docs)
        all_ranked = [
            {
                "rank": i,
                "chunk_id": d["doc_id"],
                "score": 0.0,
                "source_file": d["doc_id"],
                "source_dir_family": d.get("source_dir"),
                "text": d.get("snippet") or "",
                "text_hash": sha256_text(d.get("snippet") or ""),
                "selected": True,
            }
            for i, d in enumerate(docs, 1)
        ]
        diag = {
            "mode": "shuffled",
            "retrieval_type": "SHUFFLED",
            "ids": [d["doc_id"] for d in docs],
            "scores": [0.0] * len(docs),
            "source_dirs": [d["source_dir"] for d in docs],
            "backend": self.backend_name,
            "shuffled_seed": task_seed,
            "prefer_dirs": sorted(prefer_dirs),
            "temporal_ban_applied": True,
            "excluded_matched_chunk_ids": sorted(ban & {d["doc_id"] for d in matched_docs}),
            "matched_topk_ids": [d["doc_id"] for d in matched_docs],
            "all_ranked_candidates": all_ranked,
            "selected_chunk_ids": [d["doc_id"] for d in docs],
            "selected_context_text": selected_context,
            "selected_context_hash": sha256_text(selected_context),
            "top_k": top_k,
            "candidate_count": len(all_ranked),
            "query_raw": None,
            "query_hash": None,
        }
        return docs, diag
