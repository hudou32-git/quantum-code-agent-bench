"""Frozen RAGFlow retrieval for the RAG baseline (kb under exp/rag/kb).

Never silent-fallback to local TF-IDF under the RAG tag. The vendored Oracle
retrieval stack lives at exp/rag/oracle (sys.path wired below).
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Any

from exp import config

_LOCK = threading.Lock()
_RETRIEVER = None


class RagFlowUnavailable(RuntimeError):
    pass


def _ensure_oracle_path() -> None:
    oracle = str(config.PKG / "rag" / "oracle")
    if oracle not in sys.path:
        sys.path.insert(0, oracle)


def _env_formal() -> None:
    os.environ["ORACLE_FSE2027_RAG"] = "1"
    os.environ["ORACLE_RAG_FRAMEWORK"] = "qiskit"


def retriever():
    global _RETRIEVER
    with _LOCK:
        if _RETRIEVER is None:
            _ensure_oracle_path()
            _env_formal()
            from experiments.p12_nl_codegen.retrieval import KbRetriever

            _RETRIEVER = KbRetriever()
        return _RETRIEVER


def retrieve_docs(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _ensure_oracle_path()
    _env_formal()
    from experiments.p12_nl_codegen.prompts import format_kb_docs

    task = {
        "task_id": case.get("case_id") or "",
        "prompt": case.get("prompt") or "",
        "entry_point": case.get("entry_point") or "",
    }
    try:
        docs, diag = retriever().matched(task, top_k=3, formal_rag=True)
    except Exception as exc:  # noqa: BLE001
        raise RagFlowUnavailable(f"RAGFlow formal retrieve failed: {type(exc).__name__}: {exc}") from exc
    backend = str((diag or {}).get("backend") or "")
    if "LOCAL" in backend.upper() or "TFIDF" in backend.upper():
        raise RagFlowUnavailable(f"refusing local TF-IDF under RAG tag; backend={backend}")
    block = format_kb_docs(docs or [])
    meta = {
        "backend": backend,
        "ids": list((diag or {}).get("ids") or []),
        "n_docs": len(docs or []),
        "query_preview": str((diag or {}).get("query_preview") or "")[:200],
    }
    return block, meta


def require_ragflow() -> dict[str, Any]:
    """Live gate: one formal retrieve must succeed before the RAG arm burns LLM."""
    _ensure_oracle_path()
    try:
        from dotenv import load_dotenv

        load_dotenv(config.ENV_FILE, override=False)
    except Exception:  # noqa: BLE001
        pass
    _env_formal()
    from oracle_mvp.rag.ragflow_client import resolve_ragflow_retrieval_url

    url = resolve_ragflow_retrieval_url()
    if not url:
        raise RagFlowUnavailable("RAGFLOW_RETRIEVAL_URL / RAGFLOW_ADDRESS unset")
    if not (os.environ.get("RAGFLOW_API_KEY") or "").strip():
        raise RagFlowUnavailable("RAGFLOW_API_KEY unset")
    probe = {
        "case_id": "qiskitHumanEval/0",
        "prompt": "Generate a Quantum Circuit for n_qubits named create_quantum_circuit.",
        "entry_point": "create_quantum_circuit",
    }
    block, meta = retrieve_docs(probe)
    if meta.get("n_docs", 0) <= 0 and "(no documents injected)" in block:
        raise RagFlowUnavailable(f"formal RAG returned no documents: {meta}")
    meta["retrieval_url_set"] = True
    return meta
