"""Immutable raw artifact store + concurrent-safe JSONL append."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from experiments.p12_nl_codegen.retention.hashutil import sha256_bytes, sha256_text

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _file_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ImmutableWriteError(RuntimeError):
    pass


def write_bytes_immutable(path: Path, data: bytes, *, label: str = "") -> str:
    """Write file if absent; if present require identical SHA-256. Returns hash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_bytes(data)
    lock = _file_lock(path)
    with lock:
        if path.exists():
            existing = sha256_bytes(path.read_bytes())
            if existing != digest:
                raise ImmutableWriteError(
                    f"immutable conflict {label or path}: existing={existing} new={digest}"
                )
            return existing
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    return digest


def write_text_immutable(path: Path, text: str, *, label: str = "") -> str:
    return write_bytes_immutable(path, (text or "").encode("utf-8"), label=label)


def write_json_immutable(path: Path, obj: Any, *, label: str = "") -> str:
    blob = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return write_bytes_immutable(path, blob, label=label)


def append_jsonl(path: Path, row: dict) -> None:
    """Append one JSON object as a single line; flush; process-local lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    lock = _file_lock(path)
    with lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


class RawLayout:
    """Paths under experiments/p12_nl_codegen/raw/{block}/..."""

    def __init__(self, pkg_root: Path, block: str) -> None:
        self.block = block
        self.root = pkg_root / "raw" / block
        self.prompts = self.root / "prompts"
        self.responses = self.root / "responses"
        self.extracted = self.root / "extracted_code"
        self.retrieval = self.root / "retrieval"
        self.feedback = self.root / "feedback"
        self.eval_stdout = self.root / "evaluator_stdout"
        self.eval_stderr = self.root / "evaluator_stderr"
        self.eval_meta = self.root / "evaluator_meta"
        self.api_attempts = self.root / "api_attempts"

    def ensure(self) -> None:
        for p in (
            self.prompts,
            self.responses,
            self.extracted,
            self.retrieval,
            self.feedback,
            self.eval_stdout,
            self.eval_stderr,
            self.eval_meta,
            self.api_attempts,
        ):
            p.mkdir(parents=True, exist_ok=True)
