"""Normalize chat-completions request bodies for OpenAI-compatible APIs."""

from __future__ import annotations

import copy
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse


def normalize_chat_completions_url(url: str) -> str:
    """
    DeepSeek uses ``POST https://api.deepseek.com/chat/completions`` (see official
    docs). Paths like ``/api/v1/chat/completions`` (OpenAI-style) are not served
    and typically return **404** with an empty body.
    """
    u = (url or "").strip()
    if not u:
        return u

    if "api.deepseek.com" in u.lower():
        u = u.replace("/api/v1/chat/completions", "/chat/completions")
        u = u.replace("/v1/chat/completions", "/chat/completions")
        parsed = urlparse(u)
        if not (parsed.path or "").rstrip("/"):
            parsed = parsed._replace(path="/chat/completions")
            u = urlunparse(parsed)
        return u

    parsed = urlparse(u)
    path = (parsed.path or "").rstrip("/")
    if not path or path == "/":
        parsed = parsed._replace(path="/v1/chat/completions")
        return urlunparse(parsed)
    return u


def _strip_non_openrouter_payload_fields(body: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI-style gateways often reject OpenRouter-only keys and empty assistant primers."""
    body.pop("reasoning", None)
    usage = body.get("usage")
    if isinstance(usage, dict) and set(usage.keys()) <= {"include"}:
        body.pop("usage", None)

    msgs = list(body.get("messages") or [])
    filtered = [
        m
        for m in msgs
        if not (
            isinstance(m, dict)
            and m.get("role") == "assistant"
            and not str(m.get("content") or "").strip()
        )
    ]
    if filtered:
        body["messages"] = filtered
    return body


def sanitize_chat_payload_for_url(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Some providers reject OpenRouter-specific keys or empty assistant primers.

    DeepSeek's API typically does not accept ``reasoning`` or a synthetic
    ``usage: {include: true}`` field, and may reject a trailing assistant message
    with empty ``content`` (used by this repo's pass@k prompt builder).
    """
    body = copy.deepcopy(payload)
    host = url.lower()
    if "openrouter.ai" in host:
        return body
    return _strip_non_openrouter_payload_fields(body)
