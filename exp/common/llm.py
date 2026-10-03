"""DeepSeek client plus the .env loader it depends on.

DEEPSEEK_API_KEY / DEEPSEEK_API_URL / DEEPSEEK_MODEL are read from the
submit-root .env — the single source of truth (user directive, 2026-09-16).
No hardcoded endpoint or model fallback, no channel gating: whatever .env
points at (official endpoint or DMX proxy) is what gets called.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from exp import config
from exp.common import llm_obs


def load_env(env_file=None) -> None:
    from dotenv import load_dotenv

    path = env_file or config.ENV_FILE
    if not path.is_file():
        raise SystemExit(
            f"env file not found: {path}\n"
            "Copy .env.example to .env at the submit/ root and fill in the values."
        )
    load_dotenv(path, override=False)


def chat_url(raw: str = "") -> str:
    """Endpoint from .env DEEPSEEK_API_URL only; refuse to guess a default."""
    url = (raw or "").strip().rstrip("/")
    if not url:
        raise RuntimeError(
            "DEEPSEEK_API_URL missing: set it in submit/.env "
            "(e.g. https://api.deepseek.com/v1 or the DMX endpoint)"
        )
    if url.endswith("/chat/completions"):
        return url
    return f"{url}/chat/completions"


def resolve_model() -> str:
    """Model id from .env DEEPSEEK_MODEL only; refuse to guess a default."""
    load_env()
    m = (os.getenv("DEEPSEEK_MODEL") or "").strip()
    if not m:
        raise RuntimeError("DEEPSEEK_MODEL missing: set it in submit/.env")
    return m


def _normalize_tool_calls(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not raw:
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        fn = item.get("function") or {}
        args = fn.get("arguments") or item.get("arguments") or "{}"
        if isinstance(args, str):
            try:
                parsed = json.loads(args) if args.strip() else {}
            except json.JSONDecodeError:
                parsed = {"_raw": args}
        elif isinstance(args, dict):
            parsed = args
        else:
            parsed = {"_raw": str(args)}
        out.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(fn.get("name") or item.get("name") or ""),
                "arguments": parsed,
            }
        )
    return out


class _StreamUnsupported(Exception):
    """Gateway rejected the streaming request up-front (no sampling happened)."""


def _normalize_tool_calls_stream(acc: dict[int, dict[str, Any]]) -> list:
    out = []
    for idx in sorted(acc):
        slot = acc[idx]
        args = slot.get("arguments") or "{}"
        try:
            parsed = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
            parsed = {"_raw": args}
        out.append({"id": slot.get("id") or "", "name": slot.get("name") or "", "arguments": parsed})
    return out


def _message_hist(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for m in messages:
        role = str(m.get("role") or "?")
        if role == "assistant" and m.get("tool_calls"):
            ids = []
            for tc in m.get("tool_calls") or []:
                if isinstance(tc, dict):
                    ids.append(str(tc.get("id") or ""))
            parts.append(f"asst:tools={len(ids)}")
        elif role == "tool":
            parts.append(f"tool:{str(m.get('tool_call_id') or '')[:12]}")
        else:
            parts.append(role)
    return ">".join(parts)


def _with_tool_followups(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Official DeepSeek requires every assistant tool_call_id to have a tool reply before any other role."""
    out: list[dict[str, Any]] = []
    i = 0
    n = len(messages)
    while i < n:
        m = messages[i]
        out.append(m)
        tcs = m.get("tool_calls") if m.get("role") == "assistant" else None
        if tcs:
            needed: list[str] = []
            for tc in tcs:
                if isinstance(tc, dict) and tc.get("id"):
                    needed.append(str(tc["id"]))
            answered: set[str] = set()
            j = i + 1
            while j < n and messages[j].get("role") == "tool":
                tid = str(messages[j].get("tool_call_id") or "")
                if tid:
                    answered.add(tid)
                out.append(messages[j])
                j += 1
            for tid in needed:
                if tid not in answered:
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": tid,
                            "content": "tool result missing; skipped by policy",
                        }
                    )
            i = j
            continue
        i += 1
    return out


@dataclass
class LLMResult:
    content: str
    reasoning_content: str = ""
    model: str = ""
    finish_reason: str = ""
    usage: dict = field(default_factory=dict)
    wall_time: float = 0.0
    raw: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)
    assistant_message: dict = field(default_factory=dict)
    # generation_guard (e7, 2026-09-20): trigger diagnostics when the repeat
    # detector fired ("client_repeat_stop"), else empty. Detection-only runs
    # (EQPA) carry the same flag without any abort.
    repeat_guard: dict = field(default_factory=dict)
    # usage accounting: True when completion tokens were estimated (chars/3.5)
    # because the channel delivered no usage block — summaries must never mix
    # estimated and real token totals without this flag.
    completion_tokens_estimated: bool = False

    @property
    def total_tokens(self) -> int:
        u = self.usage or {}
        return int(u.get("total_tokens") or 0)


class DeepSeekClient:
    """Thin requests wrapper with usage accounting. Key/URL/model all come from .env."""

    def __init__(
        self,
        *,
        temperature: float = config.TEMPERATURE,
        max_tokens: int = config.MAX_TOKENS,
        disable_thinking: bool = True,
        timeout: float = config.LLM_TIMEOUT,
        system: str = "You are a careful quantum programmer. Follow instructions exactly.",
        auth_header: Optional[str] = None,
        send_thinking: Optional[bool] = None,
        extra_payload: Optional[dict[str, Any]] = None,
        max_retries: int = 1,
        stream: Optional[bool] = None,
        guard: Optional[str] = None,
    ) -> None:
        load_env()
        self.api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY missing: set it in submit/.env")
        self.model = resolve_model()
        self.url = chat_url(
            os.getenv("DEEPSEEK_API_URL") or os.getenv("DEEPSEEK_BASE_URL") or ""
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.disable_thinking = disable_thinking
        self.send_thinking = disable_thinking if send_thinking is None else send_thinking
        self.extra_payload = dict(extra_payload or {})
        self.max_retries = max(1, int(max_retries))
        self.timeout = timeout
        self.system = system
        if auth_header:
            self.auth_header = auth_header.strip()
        elif self.api_key.lower().startswith("bearer "):
            self.auth_header = self.api_key
        else:
            self.auth_header = f"Bearer {self.api_key}"
        self.n_calls = 0
        self.total_tokens = 0
        self.total_wall = 0.0
        # generation_guard (e7 resolution 2026-09-20): "enforce" = stream with
        # early abort on tools=None text calls (official path only);
        # "detect" = post-hoc flag on the result, never aborts (EQPA default).
        # Direct DeepSeekClient construction keeps the legacy non-stream
        # behavior — make_official_client opts in explicitly.
        self.stream = bool(stream)
        self.guard = guard or config.GENERATION_GUARD.get("mode_direct", "detect")
        # Phase 0 observability (2026-09-25): observation-only middleware. The
        # recorder is whatever exp.common.llm_obs.activate() installed before
        # client construction; None → the client behaves exactly as before.
        self.observer = llm_obs.current_recorder()
        self._last_http_attempts = 0

    def chat(
        self,
        user: str,
        *,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        return self.chat_with_system(system or self.system, user, max_tokens=max_tokens)

    def chat_with_system(
        self, system: str, user: str, *, max_tokens: Optional[int] = None
    ) -> LLMResult:
        return self.chat_messages(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
        )

    def chat_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[str] = "auto",
    ) -> LLMResult:
        """Observability wrapper (Phase 0, 2026-09-25): exactly one record per
        logical call — every transport (non-stream, guarded stream, fallback)
        funnels through here. Exceptions are recorded, then re-raised
        unchanged. Behavior is identical with and without an observer."""
        t0_wall = time.time()
        observer = self.observer
        self._last_http_attempts = 0
        try:
            res = self._chat_messages_impl(
                messages, tools=tools, max_tokens=max_tokens, tool_choice=tool_choice
            )
        except BaseException as exc:  # noqa: BLE001 — record, then re-raise as-is
            if observer is not None:
                observer.observe_error(self, t0_wall, exc)
            raise
        if observer is not None:
            observer.observe(self, res, t0_wall)
        return res

    def _chat_messages_impl(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[str] = "auto",
    ) -> LLMResult:
        # generation_guard enforce path: tools=None text calls on the official
        # (stream-enabled) client only. Tool callers (EQPA) and detect-mode
        # clients keep the legacy non-stream transport unchanged.
        if (
            getattr(self, "guard", "") == "enforce"
            and getattr(self, "stream", False)
            and not tools
            and config.GENERATION_GUARD.get("enabled", True)
        ):
            return self._chat_messages_guarded(messages, max_tokens=max_tokens)
        if getattr(self, "stream", False):
            # D5-6 (d5conv, 2026-10-01): opt-in streaming transport for ALL
            # calls including tool calls (Shell/Write/Eval). Streaming turns
            # the 600s read timeout into an inter-chunk stall detector and
            # removes the non-stream total-generation wall (the case-26
            # ReadTimeout hole: 3 x 600s exhausted on one 40960-token
            # generation). Clients constructed without stream=True keep the
            # legacy non-stream transport unchanged.
            return self._chat_messages_stream_any(
                messages, tools=tools, max_tokens=max_tokens, tool_choice=tool_choice
            )
        t0 = time.perf_counter()
        data = self._post_messages(
            messages,
            tools=tools,
            max_tokens=max_tokens or self.max_tokens,
            tool_choice=tool_choice if tools else None,
        )
        wall = time.perf_counter() - t0
        res = self._parse(data, wall)
        self._post_hoc_guard(res)
        return res

    def _post_hoc_guard(self, res: LLMResult) -> None:
        """Detect-only recording: never alters content/finish_reason/verdict."""
        if self.guard not in ("detect", "enforce"):
            return
        if not config.GENERATION_GUARD.get("enabled", True):
            return
        try:
            from exp.common.repeat_guard import detect

            fired = detect(res.content or "")
        except Exception:  # noqa: BLE001 — detector must never break a call
            fired = None
        if fired:
            res.repeat_guard = fired

    # ── generation_guard enforce path (streaming) ──

    def _chat_messages_guarded(self, messages: list[dict[str, Any]], *, max_tokens: Optional[int]) -> LLMResult:
        import requests.exceptions as _rxe

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self._chat_stream_once(messages, max_tokens=max_tokens or self.max_tokens)
            except _StreamUnsupported as exc:
                # gateway rejected streaming up-front (no sampling happened):
                # fall back to the legacy non-stream call exactly once, marked.
                res = self._chat_messages_fallback(messages, max_tokens=max_tokens)
                res.raw["transport_fallback"] = f"stream_unsupported: {exc}"
                return res
            except (_rxe.Timeout, _rxe.ConnectionError, _rxe.ChunkedEncodingError) as exc:
                # zero-content transport failures only reach here (a mid-stream
                # break raises RuntimeError and is NOT retried — that would
                # double-sample the draw, which the guard resolution forbids)
                last_err = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 15))
        res = self._chat_messages_fallback(messages, max_tokens=max_tokens)
        res.raw["transport_fallback"] = f"stream_transport_error: {last_err}"
        return res

    def _chat_messages_stream_any(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: Optional[list[dict[str, Any]]],
        max_tokens: Optional[int],
        tool_choice: Optional[str],
    ) -> LLMResult:
        """Streaming transport for arbitrary calls (text and tool calls).

        Same retry/fallback contract as _chat_messages_guarded: transient
        transport errors are retried with backoff; gateway rejection
        (_StreamUnsupported) and exhausted retries fall back to the legacy
        non-stream call, marked via raw["transport_fallback"]. Mid-stream
        breaks after partial content raise (no double sampling), like the
        guarded path."""
        import requests.exceptions as _rxe

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._last_http_attempts = attempt
            try:
                return self._chat_stream_once(
                    messages,
                    max_tokens=max_tokens or self.max_tokens,
                    tools=tools,
                    tool_choice=tool_choice if tools else None,
                    abort_on_repeat=self.guard == "enforce",
                )
            except _StreamUnsupported as exc:
                res = self._chat_messages_fallback(
                    messages, max_tokens=max_tokens, tools=tools, tool_choice=tool_choice
                )
                res.raw["transport_fallback"] = f"stream_unsupported: {exc}"
                return res
            except (_rxe.Timeout, _rxe.ConnectionError, _rxe.ChunkedEncodingError) as exc:
                last_err = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 15))
        res = self._chat_messages_fallback(
            messages, max_tokens=max_tokens, tools=tools, tool_choice=tool_choice
        )
        res.raw["transport_fallback"] = f"stream_transport_error: {last_err}"
        return res

    def _chat_messages_fallback(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: Optional[int],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResult:
        t0 = time.perf_counter()
        data = self._post_messages(
            messages,
            tools=tools,
            max_tokens=max_tokens or self.max_tokens,
            tool_choice=tool_choice if tools else None,
        )
        res = self._parse(data, time.perf_counter() - t0)
        self._post_hoc_guard(res)
        return res

    def _chat_stream_once(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        abort_on_repeat: Optional[bool] = None,
    ) -> LLMResult:
        """Single streamed call (SSE). Handles both text deltas and tool_call
        deltas (index-keyed argument reassembly). On detector fire (only when
        abort_on_repeat — default: guard == "enforce"): close the stream
        (server stops), synthesize finish_reason="client_repeat_stop", keep
        the full accumulated text for extraction/grading. No retry on fire —
        the draw is consumed and judged by the normal pipeline."""
        import requests
        import requests.exceptions as _rxe
        from exp.common.repeat_guard import detect, should_check

        if abort_on_repeat is None:
            abort_on_repeat = self.guard == "enforce"

        headers = {"Content-Type": "application/json", "Authorization": self.auth_header}
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _with_tool_followups(messages),
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        if self.send_thinking:
            payload["thinking"] = {"type": "disabled"}
        if self.extra_payload:
            payload.update(self.extra_payload)

        t0 = time.perf_counter()
        resp = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout, stream=True)
        if resp.status_code >= 400:
            body = resp.text[:200]
            resp.close()
            raise _StreamUnsupported(f"HTTP {resp.status_code}: {body}")

        content: list[str] = []
        reasoning: list[str] = []
        finish_reason = ""
        usage: dict[str, Any] | None = None
        tool_acc: dict[int, dict[str, Any]] = {}
        checked_chars = 0
        fired: dict[str, Any] | None = None
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                body = line[5:].strip()
                if body == "[DONE]":
                    break
                try:
                    chunk = json.loads(body)
                except json.JSONDecodeError:
                    continue
                if isinstance(chunk.get("usage"), dict) and chunk["usage"]:
                    usage = chunk["usage"]
                choices = chunk.get("choices") or []
                choice = choices[0] if choices else {}
                delta = choice.get("delta") or {}
                piece = delta.get("content") or ""
                if piece:
                    content.append(piece)
                rc = delta.get("reasoning_content") or delta.get("reasoning")
                if rc:
                    reasoning.append(rc)
                if choice.get("finish_reason"):
                    finish_reason = str(choice["finish_reason"])
                for tc in delta.get("tool_calls") or []:
                    if not isinstance(tc, dict):
                        continue
                    idx = int(tc.get("index") or 0)
                    slot = tool_acc.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                    fn = tc.get("function") or {}
                    slot["id"] = slot["id"] or str(tc.get("id") or "")
                    slot["name"] = slot["name"] or str(fn.get("name") or "")
                    slot["arguments"] += str(fn.get("arguments") or "")
                acc = "".join(content)
                if abort_on_repeat and not fired and should_check(len(acc), checked_chars):
                    if detect(acc):
                        # EXECUTION-LEVEL EARLY ABORT — close the stream; the
                        # draw is consumed and judged as-is (no retry/resample)
                        fired = detect(acc)
                        break
                    checked_chars = len(acc)
        except (_rxe.Timeout, _rxe.ConnectionError, _rxe.ChunkedEncodingError) as exc:
            if content:
                # mid-generation transport break: do NOT re-issue (no double
                # sampling); surface as a job error for the runner to record
                raise RuntimeError(
                    f"stream broke mid-generation after {sum(map(len, content))} chars"
                ) from exc
            raise

        fired = fired if fired else None  # normalize
        text = "".join(content)
        finish = "client_repeat_stop" if fired else (finish_reason or "")
        estimated = usage is None
        if usage is None:
            prompt_chars = sum(len(str(m.get("content") or "")) for m in messages)
            usage = {
                "prompt_tokens": max(1, int(prompt_chars / 3.5)),
                "completion_tokens": max(1, int(len(text) / 3.5)),
                "total_tokens": max(2, int((prompt_chars + len(text)) / 3.5)),
            }
        tool_calls = _normalize_tool_calls_stream(tool_acc)
        assistant_message: dict[str, Any] = {"role": "assistant", "content": text or ""}
        if tool_acc:
            # history copy mirrors the API's own wire format exactly:
            # function.arguments MUST be a string (the normalized tool_calls
            # above carry parsed dicts for the caller loop)
            assistant_message["content"] = None
            assistant_message["tool_calls"] = [
                {"id": s.get("id") or f"call_stream_{idx}", "type": "function",
                 "function": {"name": s.get("name") or "",
                              "arguments": s.get("arguments") or "{}"}}
                for idx, s in sorted(tool_acc.items())
            ]
        res = LLMResult(
            content=text.strip(),
            reasoning_content="".join(reasoning).strip(),
            model=self.model,
            finish_reason=finish,
            usage=dict(usage),
            wall_time=time.perf_counter() - t0,
            raw={"transport": "stream", "finish_reason": finish},
            tool_calls=tool_calls,
            assistant_message=assistant_message,
            repeat_guard=fired or {},
            completion_tokens_estimated=estimated,
        )
        if not abort_on_repeat:
            # detect-mode streaming: same post-hoc flagging as the legacy path
            self._post_hoc_guard(res)
        self.n_calls += 1
        self.total_tokens += res.total_tokens
        self.total_wall += res.wall_time
        return res

    def _post_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int,
        tool_choice: Optional[str] = None,
    ) -> dict[str, Any]:
        import requests

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_header,
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _with_tool_followups(messages),
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        if self.send_thinking:
            payload["thinking"] = {"type": "disabled"}
        if self.extra_payload:
            payload.update(self.extra_payload)
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._last_http_attempts = attempt
            try:
                resp = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code >= 400:
                    hist = _message_hist(payload.get("messages") or [])
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {resp.text[:400]} | hist={hist}"
                    )
                return resp.json()
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_err = e
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 15))
        raise last_err if last_err else RuntimeError("LLM request failed")

    def _parse(self, data: dict[str, Any], wall: float) -> LLMResult:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(str(block.get("text") or block.get("content") or ""))
                else:
                    parts.append(str(block))
            content = "\n".join(p for p in parts if p)
        reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        usage = data.get("usage") or {}
        tool_calls = _normalize_tool_calls(msg.get("tool_calls"))
        raw_tool_calls = msg.get("tool_calls")
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": None if raw_tool_calls else (content or ""),
        }
        if raw_tool_calls:
            assistant_message["tool_calls"] = raw_tool_calls
        result = LLMResult(
            content=str(content).strip() if content is not None else "",
            reasoning_content=str(reasoning).strip(),
            model=str(data.get("model") or self.model),
            finish_reason=str(choice.get("finish_reason") or ""),
            usage=dict(usage),
            wall_time=wall,
            raw={"id": data.get("id"), "finish_reason": choice.get("finish_reason")},
            tool_calls=tool_calls,
            assistant_message=assistant_message,
        )
        self.n_calls += 1
        self.total_tokens += result.total_tokens
        self.total_wall += wall
        return result

    def snapshot(self) -> dict:
        return {
            "model": self.model,
            "n_calls": self.n_calls,
            "total_tokens": self.total_tokens,
            "total_wall": round(self.total_wall, 4),
            "url_host": self.url.split("/")[2] if "://" in self.url else "redacted",
        }


def official_chat_url() -> str:
    load_env()
    return chat_url(os.getenv("DEEPSEEK_API_URL") or os.getenv("DEEPSEEK_BASE_URL") or "")


def official_model() -> str:
    return resolve_model()


def make_official_client(
    *,
    max_tokens: int,
    temperature: float = config.TEMPERATURE,
    timeout: float = config.LLM_TIMEOUT,
) -> DeepSeekClient:
    """DeepSeek chat API. Reads DEEPSEEK_API_KEY / URL / MODEL from .env only.

    generation_guard (e7 resolution 2026-09-20): official-path clients stream
    with the repeat guard enforced on tools=None text calls — early abort only,
    no retry/resample/budget change. Direct DeepSeekClient construction (EQPA)
    is unaffected: non-stream transport, detect-only."""
    load_env()
    key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY missing: set it in submit/.env")
    guard_enabled = bool(config.GENERATION_GUARD.get("enabled", True))
    return DeepSeekClient(
        temperature=temperature,
        max_tokens=max_tokens,
        disable_thinking=True,
        timeout=max(timeout, 600.0),
        send_thinking=True,
        max_retries=3,
        stream=guard_enabled,
        guard=config.GENERATION_GUARD.get("mode_official", "enforce") if guard_enabled else "detect",
    )
