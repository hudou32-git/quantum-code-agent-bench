"""RAGFlow HTTP retrieval client (aligned with qiskit-human-eval/optimization_common)."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple


def _load_repo_dotenv() -> None:
    """Best-effort load of the submit-root .env (does not override existing env)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # exp/rag/oracle/oracle_mvp/rag/thisfile -> parents[4] = submit root
    repo_env = Path(__file__).resolve().parents[4] / ".env"
    if repo_env.is_file():
        load_dotenv(repo_env, override=False)


_load_repo_dotenv()


def resolve_ragflow_retrieval_url() -> str:
    url = os.environ.get("RAGFLOW_RETRIEVAL_URL", "").strip().strip('"').strip("'")
    if url:
        return url
    host = os.environ.get("RAGFLOW_ADDRESS", "").strip().strip('"').strip("'")
    if not host:
        return ""
    if host.startswith("http://") or host.startswith("https://"):
        base = host.rstrip("/")
    else:
        base = f"http://{host.rstrip('/')}"
    return f"{base}/api/v1/retrieval"


def ragflow_credentials() -> Tuple[str, str, str]:
    """Return (retrieval_url, dataset_id, api_key). Empty strings if unset."""
    return (
        resolve_ragflow_retrieval_url(),
        os.environ.get("RAGFLOW_DATASET_ID", "").strip(),
        os.environ.get("RAGFLOW_API_KEY", "").strip(),
    )


def ragflow_configured() -> bool:
    url, ds, key = ragflow_credentials()
    return bool(url and ds and key)


def _debug() -> bool:
    v = os.environ.get("QCODER_SERVE_DEBUG", "").strip().lower()
    return v in ("1", "true", "yes", "on")


@dataclass
class RagFlowChunk:
    keyword: str
    content: str
    similarity: float
    document_id: str = ""
    chunk_id: str = ""


def fetch_rag_context(
    *,
    question: str,
    retrieval_url: str,
    dataset_id: str,
    api_key: str,
    page_size: int,
    similarity_threshold: float,
    timeout: float,
) -> Tuple[str, float]:
    """POST /api/v1/retrieval — same contract as qiskit-human-eval optimization_common."""
    payload = {
        "question": question,
        "dataset_ids": [dataset_id],
        "page_size": page_size,
        "similarity_threshold": similarity_threshold,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if _debug():
        print(
            f"[RAGFlow] POST {retrieval_url!r} | question_len={len(question)} "
            f"dataset_ids={dataset_id!r} page_size={page_size} "
            f"similarity_threshold={similarity_threshold}",
            flush=True,
        )
    t0 = time.perf_counter()
    try:
        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            retrieval_url,
            data=body_bytes,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
        wall = time.perf_counter() - t0
        if _debug():
            print(f"[RAGFlow] OK | len={len(text)} wall={wall:.3f}s", flush=True)
        return text, wall
    except Exception as e:
        wall = time.perf_counter() - t0
        print(f"[RAGFlow] 失败 {type(e).__name__}: {e!r}", flush=True)
        return f"[RAG 检索失败: {e}]", wall


def _parse_obj_chunks(obj: Any) -> List[RagFlowChunk]:
    chunks_raw: List[Any] = []
    if isinstance(obj, dict):
        data = obj.get("data")
        if isinstance(data, dict) and isinstance(data.get("chunks"), list):
            chunks_raw = data.get("chunks") or []
        elif isinstance(obj.get("chunks"), list):
            chunks_raw = obj.get("chunks") or []
    elif isinstance(obj, list):
        chunks_raw = obj

    out: List[RagFlowChunk] = []
    for chunk in chunks_raw:
        if isinstance(chunk, dict):
            content = chunk.get("content") or chunk.get("text") or chunk.get("chunk")
            keyword = (
                chunk.get("document_keyword")
                or chunk.get("doc_name")
                or chunk.get("document_id")
                or ""
            )
            sim = float(chunk.get("similarity") or 0.0)
            doc_id = str(chunk.get("document_id") or "")
            cid = str(chunk.get("id") or chunk.get("chunk_id") or "")
        else:
            content = str(chunk)
            keyword = ""
            sim = 0.0
            doc_id = ""
            cid = ""
        if content and str(content).strip():
            out.append(
                RagFlowChunk(
                    keyword=str(keyword),
                    content=str(content).strip(),
                    similarity=sim,
                    document_id=doc_id,
                    chunk_id=cid,
                )
            )
    return out


def parse_rag_chunks(rag_text: Any) -> List[RagFlowChunk]:
    if rag_text is None:
        return []
    if isinstance(rag_text, (dict, list)):
        return _parse_obj_chunks(rag_text)
    text = str(rag_text).strip()
    if not text or text.startswith("[RAG 检索失败"):
        return []
    try:
        obj = json.loads(text)
    except Exception:
        return [RagFlowChunk(keyword="", content=text, similarity=0.0)]
    return _parse_obj_chunks(obj)


def default_page_size() -> int:
    try:
        return max(1, int(os.environ.get("RAGFLOW_PAGE_SIZE", "5")))
    except ValueError:
        return 5


def default_similarity_threshold() -> float:
    try:
        return float(os.environ.get("RAGFLOW_SIMILARITY_THRESHOLD", "0.1"))
    except ValueError:
        return 0.1


def default_timeout() -> float:
    try:
        return float(os.environ.get("RAGFLOW_TIMEOUT", "60"))
    except ValueError:
        return 60.0
