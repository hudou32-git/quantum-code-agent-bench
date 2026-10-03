"""Local TF-IDF and RAGFlow retrievers over the Oracle RAG knowledge base."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

ORACLE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KB = ORACLE_ROOT / "datasets" / "rag_kb"

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|[\u4e00-\u9fff]+|\d+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


@dataclass
class DocChunk:
    doc_id: str
    path: Path
    title: str
    text: str
    source_dir: str


@dataclass
class RetrievalHit:
    doc_id: str
    path: str
    title: str
    score: float
    snippet: str
    source_dir: str


class LocalKbRetriever:
    """Offline sparse retriever (TF-IDF cosine). No RAGFlow dependency."""

    def __init__(
        self,
        kb_root: Path | str | None = None,
        *,
        max_chars_per_doc: int = 4000,
        include_dirs: Optional[Sequence[str]] = None,
    ) -> None:
        self.kb_root = Path(kb_root) if kb_root else DEFAULT_KB
        self.max_chars_per_doc = max_chars_per_doc
        self.include_dirs = list(include_dirs) if include_dirs else None
        self.docs: List[DocChunk] = []
        self._idf: dict[str, float] = {}
        self._tf: List[dict[str, float]] = []
        self._norms: List[float] = []
        if self.kb_root.exists():
            self._build()

    def _iter_md(self) -> Iterable[Path]:
        if not self.kb_root.exists():
            return []
        for path in sorted(self.kb_root.rglob("*.md")):
            rel = path.relative_to(self.kb_root)
            if rel.parts and rel.parts[0] in {"_meta"}:
                continue
            if path.name.upper() in {"README.MD", "INGESTION.MD", "MANIFEST.JSON"}:
                continue
            if path.name in {"README.md", "INGESTION.md", "DO_NOT_READ.md"}:
                continue
            if self.include_dirs and rel.parts[0] not in self.include_dirs:
                continue
            yield path

    def _build(self) -> None:
        import math
        from collections import Counter

        docs: List[DocChunk] = []
        for path in self._iter_md():
            raw = path.read_text(encoding="utf-8", errors="replace")
            text = raw.strip()
            if len(text) < 40:
                continue
            if len(text) > self.max_chars_per_doc:
                text = text[: self.max_chars_per_doc]
            title = ""
            for line in text.splitlines():
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break
            rel = path.relative_to(self.kb_root)
            docs.append(
                DocChunk(
                    doc_id=rel.as_posix(),
                    path=path,
                    title=title or path.stem,
                    text=text,
                    source_dir=rel.parts[0] if rel.parts else "",
                )
            )
        self.docs = docs
        if not docs:
            return

        df: Counter[str] = Counter()
        raw_tfs: List[Counter[str]] = []
        for d in docs:
            toks = _tokenize(d.title + "\n" + d.text)
            c = Counter(toks)
            raw_tfs.append(c)
            for t in c:
                df[t] += 1

        n = len(docs)
        self._idf = {t: math.log((n + 1) / (df[t] + 1)) + 1.0 for t in df}
        self._tf = []
        self._norms = []
        for c in raw_tfs:
            total = sum(c.values()) or 1
            vec = {t: (cnt / total) * self._idf[t] for t, cnt in c.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self._tf.append(vec)
            self._norms.append(norm)

    def retrieve(self, query: str, top_k: int = 4) -> List[RetrievalHit]:
        import math

        if not self.docs:
            return []
        q_toks = _tokenize(query)
        if not q_toks:
            return []
        from collections import Counter

        qc = Counter(q_toks)
        q_total = sum(qc.values()) or 1
        q_vec = {
            t: (cnt / q_total) * self._idf[t] for t, cnt in qc.items() if t in self._idf
        }
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        scored: List[tuple[float, int]] = []
        for i, dvec in enumerate(self._tf):
            dot = sum(q_vec[t] * dvec[t] for t in q_vec if t in dvec)
            score = dot / (q_norm * self._norms[i])
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        hits: List[RetrievalHit] = []
        for score, i in scored[:top_k]:
            d = self.docs[i]
            snippet = d.text
            if len(snippet) > 900:
                snippet = snippet[:900] + "\n..."
            hits.append(
                RetrievalHit(
                    doc_id=d.doc_id,
                    path=str(d.path),
                    title=d.title,
                    score=float(score),
                    snippet=snippet,
                    source_dir=d.source_dir,
                )
            )
        return hits

    def format_context(self, hits: Sequence[RetrievalHit], *, max_chars: int = 3500) -> str:
        if not hits:
            return "(no retrieved documents)"
        parts = []
        used = 0
        for i, h in enumerate(hits, 1):
            block = f"[{i}] {h.title} ({h.doc_id}, score={h.score:.3f})\n{h.snippet}"
            if used + len(block) > max_chars and parts:
                break
            parts.append(block)
            used += len(block)
        return "\n\n---\n\n".join(parts)


class RagFlowRetriever:
    """Online retriever via RAGFlow `/api/v1/retrieval` (QHE-compatible HTTP contract).

    Returns the same ``RetrievalHit`` objects as ``LocalKbRetriever``. Does not
    expose a local ``docs`` list; callers that need a document pool (e.g. shuffled
    controls) should keep a separate ``LocalKbRetriever``.
    """

    backend_name = "RAGFLOW"

    def __init__(
        self,
        *,
        retrieval_url: Optional[str] = None,
        dataset_id: Optional[str] = None,
        api_key: Optional[str] = None,
        page_size: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        timeout: Optional[float] = None,
        snippet_chars: int = 900,
    ) -> None:
        from oracle_mvp.rag.ragflow_client import (
            default_page_size,
            default_similarity_threshold,
            default_timeout,
            ragflow_credentials,
            ragflow_configured,
        )

        url, ds, key = ragflow_credentials()
        self.retrieval_url = (retrieval_url or url).strip()
        self.dataset_id = (dataset_id or ds).strip()
        self.api_key = (api_key or key).strip()
        self.page_size = int(page_size) if page_size is not None else default_page_size()
        self.similarity_threshold = (
            float(similarity_threshold)
            if similarity_threshold is not None
            else default_similarity_threshold()
        )
        self.timeout = float(timeout) if timeout is not None else default_timeout()
        self.snippet_chars = snippet_chars
        self.docs: List[DocChunk] = []  # empty; shuffled must use LocalKbRetriever
        self.last_raw_response: str = ""
        self.last_wall_seconds: float = 0.0
        if not ragflow_configured() and not (self.retrieval_url and self.dataset_id and self.api_key):
            raise RuntimeError(
                "RagFlowRetriever requires RAGFLOW_RETRIEVAL_URL (or RAGFLOW_ADDRESS), "
                "RAGFLOW_DATASET_ID, and RAGFLOW_API_KEY"
            )

    @staticmethod
    def _infer_source_dir(keyword: str) -> str:
        key = (keyword or "").replace("\\", "/")
        for fam in (
            "RAG_qiskit_api",
            "RAG_qiskit_recipes",
            "RAG_qiskit_human_eval_runtime",
            "RAG_qiskit_human_eval_topics",
            "RAG_quantum_algorithms",
        ):
            if fam in key or key.startswith(fam):
                return fam
        # document_keyword is often a basename like heval_runtime_....md
        if key.startswith("heval_"):
            return "RAG_qiskit_human_eval_runtime"
        if key.startswith("recipe_"):
            return "RAG_qiskit_recipes"
        return "RAGFLOW"

    def retrieve(self, query: str, top_k: int = 4) -> List[RetrievalHit]:
        from oracle_mvp.rag.ragflow_client import fetch_rag_context, parse_rag_chunks

        if not (query or "").strip():
            return []
        fetch_k = max(int(top_k), int(self.page_size), 5)
        raw, wall = fetch_rag_context(
            question=query,
            retrieval_url=self.retrieval_url,
            dataset_id=self.dataset_id,
            api_key=self.api_key,
            page_size=fetch_k,
            similarity_threshold=self.similarity_threshold,
            timeout=self.timeout,
        )
        self.last_raw_response = raw
        self.last_wall_seconds = wall
        chunks = parse_rag_chunks(raw)
        hits: List[RetrievalHit] = []
        for ch in chunks[: max(1, int(top_k))]:
            doc_id = ch.keyword or ch.document_id or ch.chunk_id or f"ragflow_{len(hits)}"
            snippet = ch.content
            if len(snippet) > self.snippet_chars:
                snippet = snippet[: self.snippet_chars] + "\n..."
            hits.append(
                RetrievalHit(
                    doc_id=doc_id,
                    path=ch.document_id or doc_id,
                    title=ch.keyword or doc_id,
                    score=float(ch.similarity),
                    snippet=snippet,
                    source_dir=self._infer_source_dir(ch.keyword),
                )
            )
        return hits

    def format_context(self, hits: Sequence[RetrievalHit], *, max_chars: int = 3500) -> str:
        if not hits:
            return "(no retrieved documents)"
        parts = []
        used = 0
        for i, h in enumerate(hits, 1):
            block = f"[{i}] {h.title} ({h.doc_id}, score={h.score:.3f})\n{h.snippet}"
            if used + len(block) > max_chars and parts:
                break
            parts.append(block)
            used += len(block)
        return "\n\n---\n\n".join(parts)


RetrieverBackend = Union[LocalKbRetriever, RagFlowRetriever]


def resolve_rag_backend_name(explicit: Optional[str] = None) -> str:
    """``ragflow`` (default) or ``local``.

    Override with env ``ORACLE_RAG_BACKEND`` / ``ORACLE_RAG_BACKEND=tfidf|local|ragflow``.
    """
    raw = (explicit or os.environ.get("ORACLE_RAG_BACKEND", "ragflow")).strip().lower()
    if raw in {"local", "tfidf", "offline"}:
        return "local"
    return "ragflow"


def build_retriever(
    backend: Optional[str] = None,
    *,
    kb_root: Path | str | None = None,
    max_chars_per_doc: int = 4000,
    include_dirs: Optional[Sequence[str]] = None,
    **ragflow_kwargs,
) -> RetrieverBackend:
    """Construct the active RAG backend for Oracle generation / repair pipelines."""
    name = resolve_rag_backend_name(backend)
    if name == "local":
        return LocalKbRetriever(
            kb_root=kb_root,
            max_chars_per_doc=max_chars_per_doc,
            include_dirs=include_dirs,
        )
    return RagFlowRetriever(**ragflow_kwargs)
