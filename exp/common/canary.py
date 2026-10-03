"""Random hidden canaries on the host dataset / sealed / grader trees."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from exp import config

CANARY_FILENAME = ".eqpa_canary"
_PLACEMENTS = {
    "dataset": config.QHE_DATASET_DIR,
    "sealed": config.QHE_SEALED_DIR,
    "grader": config.QHE_EVAL_DIR,
}


def _token() -> str:
    return "SECRET_CANARY_" + secrets.token_hex(32)


def ensure_canaries() -> dict[str, str]:
    """Create or reuse canary files. Returns {placement: token}."""
    state_path = config.EQPA_CANARY_STATE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tokens: dict[str, str] = {}
    if state_path.is_file():
        try:
            tokens = json.loads(state_path.read_text(encoding="utf-8")).get("tokens") or {}
        except json.JSONDecodeError:
            tokens = {}
    for name, directory in _PLACEMENTS.items():
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / CANARY_FILENAME
        token = tokens.get(name) or _token()
        if not path.is_file() or path.read_text(encoding="utf-8").strip() != token:
            path.write_text(token + "\n", encoding="utf-8")
            os.chmod(path, 0o644)
        tokens[name] = token
    payload = {
        "filename": CANARY_FILENAME,
        "tokens": tokens,
        "paths": {k: str(v / CANARY_FILENAME) for k, v in _PLACEMENTS.items()},
    }
    state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return tokens


def canary_values(tokens: dict[str, str] | None = None) -> tuple[str, ...]:
    toks = tokens or ensure_canaries()
    return tuple(toks.values())


def scan_text(text: str, tokens: dict[str, str] | None = None) -> list[str]:
    hits = []
    for token in canary_values(tokens):
        if token and token in (text or ""):
            hits.append(token)
    return hits


def host_canary_path(placement: str = "dataset") -> Path:
    return _PLACEMENTS[placement] / CANARY_FILENAME
