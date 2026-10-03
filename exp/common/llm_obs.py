"""Unified LLM call observability layer (Phase 0, 2026-09-25).

One middleware for every runner family (baseline grid, EQPA, FCEA/DEU,
evidence_eqpa, loop_qspr_rq, and the future D4 Shell runner): all LLM traffic
funnels through exp.common.llm.DeepSeekClient.chat_messages, and this module
records one JSON object per logical call to a run-sidecar `llm_calls.jsonl`.

Observation-only contract (Phase 0 freeze):
  - payloads, prompts, tools, controller rules, tool protocols: untouched
  - retries / timeouts / streaming / generation-guard behavior: untouched
  - exceptions: recorded, then re-raised unchanged
  - with no recorder activated the client behaves exactly as before
    (observer=None → no I/O, no behavior change)

Record schema (one JSON object per line; the nine required fields first):
    call_id                    int    monotonic within the episode (run-level
                                      when no episode is set; a resume creates
                                      a new obs_session, so ids repeat across
                                      sessions but never within one)
    timestamp_start            str    ISO-8601 UTC wall clock
    timestamp_end              str    ISO-8601 UTC wall clock
    latency_seconds            float  logical-call duration (retries and
                                      backoff included)
    input_tokens               int
    output_tokens              int
    total_tokens               int
    model                      str
    temperature                float
    tokens_estimated           bool   channel sent no usage block (chars/3.5
                                      estimate — never mix with real totals)
    usage_present              bool
    transport                  str    non_stream | stream | stream_fallback
    finish_reason              str
    guard_fired                bool   generation_guard repeat detector fired
    n_tool_calls               int
    http_attempts              int    HTTP attempts consumed by the logical call
    attempt_latency_seconds    float  successful-attempt latency (excl. retries)
    error                      str|None
    context                    dict   obs_session / schema_version / runner /
                                      tag / arm / bench / variant / episode_id
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

SCHEMA_VERSION = 1
REQUIRED_FIELDS = (
    "call_id",
    "timestamp_start",
    "timestamp_end",
    "latency_seconds",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "model",
    "temperature",
)

# GATE 4 cost-measurement specification (frozen identity block, 2026-09-25
# review; verbatim mirror of docs/protocols/gate4_manifest_20260925.yaml).
# Embedded into every run's recorder context, cost_summary.json, and the
# GATE 4 protocol manifest; latency != wall-clock episode time.
COST_MEASUREMENT: Dict[str, Any] = {
    "measurement": {
        "cost": {"calls": True, "tokens": True, "latency": True},
    },
    "latency": {
        "include": ["llm_api_call"],
        "exclude": ["simulator", "environment"],
    },
    "replicate": {
        "policy": {"external_control": True},
    },
    "latency_detail": {
        "name": "cumulative_llm_api_latency",
        "unit": "seconds",
        "note": "latency != wall-clock episode time; 'environment' comprises "
                "tool execution, grading and simulator runtime",
    },
    "token_definition": {
        "input": "provider usage.prompt_tokens",
        "output": "provider usage.completion_tokens",
        "estimated_fallback": "chars/3.5 when the channel omits usage; "
                              "flagged tokens_estimated=true, never mixed "
                              "with real totals",
    },
    "quantum_executions": "not metered by the LLM layer; taken from the "
                          "runner-provided outcome field or offline trace "
                          "extraction",
}


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class EpisodeHandle:
    """Runner-facing handle yielded by `episode_context`: attach outcome facts
    (success / iterations / quantum_executions) any time before the with-block
    exits; they land in the episode-ledger line's `outcome` object."""

    def __init__(self, recorder: "LLMCallRecorder", identifiers: Dict[str, Any]) -> None:
        self._recorder = recorder
        self.identifiers = dict(identifiers)
        self.outcome: Dict[str, Any] = {}
        self.started_at = ""
        self.ended_at = ""

    def record_outcome(self, **fields: Any) -> None:
        self.outcome.update(fields)


class LLMCallRecorder:
    """Thread-safe JSONL recorder shared by every client of one run.

    Runner families use thread-local clients (ThreadPoolExecutor workers), so
    all clients of a run attach the same recorder instance; the write lock
    serializes JSONL appends and keeps line order == call_id order.
    """

    def __init__(self, path: Path, context: Optional[Dict[str, Any]] = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.context: Dict[str, Any] = dict(context or {})
        self.context.setdefault("obs_session", uuid.uuid4().hex[:12])
        self.context["schema_version"] = SCHEMA_VERSION
        self.context["cost_measurement"] = COST_MEASUREMENT
        self._lock = threading.Lock()
        self._fh = open(self.path, "a", encoding="utf-8")
        self._ledger_path = self.path.parent / "episode_ledger.jsonl"
        self._ledger_fh = open(self._ledger_path, "a", encoding="utf-8")
        self._episodes: list[Dict[str, Any]] = []
        self._call_id = 0
        self._episode = None  # process-wide episode (single-worker runners)
        self._tls = threading.local()  # worker-scoped episode override
        self._broken = False  # fail-safe: True once an observer-internal error occurred
        self._warned = False
        self.totals: Dict[str, Any] = {
            "n_calls": 0,
            "n_errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_seconds": 0.0,
        }

    # ── episode context (call_id scope) ──

    def set_episode(self, episode_id: Any, **ctx: Any) -> None:
        """Process-wide episode: resets the call_id counter to 1."""
        with self._lock:
            self._episode = {"episode_id": episode_id}
            self._episode.update(ctx)
            self._call_id = 0

    def clear_episode(self) -> None:
        with self._lock:
            self._episode = None
            self._call_id = 0

    def set_thread_episode(self, episode_id: Any, **ctx: Any) -> None:
        """Worker-scoped episode for ThreadPool runners: call at the top of the
        worker function; overrides the process-wide episode for the calling
        thread only, so concurrent workers never cross-contaminate ids."""
        self._tls.episode = {"episode_id": episode_id}
        self._tls.episode.update(ctx)
        self._tls.call_id = 0

    def clear_thread_episode(self) -> None:
        self._tls.episode = None
        self._tls.call_id = 0

    def _current_context(self) -> Dict[str, Any]:
        ep = getattr(self._tls, "episode", None) or self._episode
        out = dict(self.context)
        if ep:
            out.update(ep)
        return out

    # ── episode context (per-task/replicate cost + outcome ledger) ──

    @contextmanager
    def episode_context(self, **identifiers: Any) -> Iterator[EpisodeHandle]:
        """One experiment episode. Every LLM call made on this thread inside
        the with-block is attributed to this episode (call_id scope + cost
        accumulator); on exit — normal or exceptional — one line is appended
        to `episode_ledger.jsonl`:

            {obs_session, runner, tag, method, task_id, replicate, episode_id,
             started_at, ended_at, completed_normally,
             cost: {llm_calls, input_tokens, output_tokens, total_tokens,
                    llm_latency_seconds, llm_errors},
             outcome: {success, iterations, quantum_executions, ...}}

        Runner-provided outcome fields come via EpisodeHandle.record_outcome.
        Exceptions are ledgered (completed_normally=false) and re-raised
        unchanged."""
        identifiers.setdefault("method", self.context.get("method"))
        identifiers.setdefault("replicate", self.context.get("replicate"))
        if not identifiers.get("episode_id"):
            identifiers["episode_id"] = "{bench}:{task_id}:r{replicate}".format(
                bench=identifiers.get("bench", self.context.get("bench", "")),
                task_id=identifiers.get("task_id", "?"),
                replicate=identifiers.get("replicate", 1),
            )
        self.set_thread_episode(
            identifiers["episode_id"],
            **{k: v for k, v in identifiers.items() if k != "episode_id"},
        )
        self._tls.acc = {
            "llm_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "llm_latency_seconds": 0.0,
            "llm_errors": 0,
        }
        handle = EpisodeHandle(self, identifiers)
        handle.started_at = _iso(time.time())
        completed = False
        try:
            yield handle
            completed = True
        except BaseException as exc:  # noqa: BLE001 — ledger the episode, re-raise as-is
            handle.outcome["exception"] = "{}: {}".format(type(exc).__name__, exc)[:500]
            raise
        finally:
            handle.ended_at = _iso(time.time())
            line = {
                "schema_version": SCHEMA_VERSION,
                "obs_session": self.context.get("obs_session"),
                "runner": self.context.get("runner"),
                "tag": self.context.get("tag"),
                "started_at": handle.started_at,
                "ended_at": handle.ended_at,
                "completed_normally": completed,
                **identifiers,
                "cost": dict(getattr(self._tls, "acc", {})),
                "outcome": dict(handle.outcome),
            }
            self.clear_thread_episode()
            try:
                with self._lock:
                    self._ledger_fh.write(json.dumps(line, ensure_ascii=False) + "\n")
                    self._ledger_fh.flush()
                self._episodes.append(line)
            except Exception as exc:  # noqa: BLE001 — never break the run
                self._break("ledger write failed; observer disabled", exc)

    def write_cost_summary(self, path: Any = None) -> Optional[Dict[str, Any]]:
        """Run-level cost summary (GATE 3/4 cost fields) from the episode
        ledger. The runner calls this once after its own summary write; the
        ledger JSONL stays the source of truth if the run crashes."""
        if self._broken:
            return None
        try:
            eps = self._episodes
            n = len(eps)

            def _sum(key: str) -> int:
                return sum(int(e["cost"].get(key) or 0) for e in eps)

            def _mean(key: str) -> Optional[float]:
                return round(_sum(key) / n, 4) if n else None

            n_success = sum(
                1 for e in eps if e.get("outcome", {}).get("success") is True
            )
            summary: Dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "runner": self.context.get("runner"),
                "tag": self.context.get("tag"),
                "cost_measurement": COST_MEASUREMENT,
                "episodes": n,
                "success_rate": round(n_success / n, 4) if n else None,
                "llm_calls_total": _sum("llm_calls"),
                "mean_llm_calls_per_episode": _mean("llm_calls"),
                "input_tokens_total": _sum("input_tokens"),
                "output_tokens_total": _sum("output_tokens"),
                "total_tokens_total": _sum("total_tokens"),
                "mean_total_tokens_per_episode": _mean("total_tokens"),
                "llm_latency_seconds_total": round(_sum("llm_latency_seconds"), 3),
                "mean_llm_latency_seconds_per_episode": _mean("llm_latency_seconds"),
                "llm_errors_total": _sum("llm_errors"),
            }
            out = Path(path) if path else self.path.parent / "cost_summary.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary
        except Exception as exc:  # noqa: BLE001 — never break the run
            self._break("cost summary failed; observer disabled", exc)
            return None

    # ── recording ──

    def observe(self, client: Any, res: Any, t0_wall: float) -> None:
        """Fail-safe by contract: an observer-internal error (e.g. a closed
        recorder after re-activation, disk full) degrades to a silent no-op —
        it must never propagate into the experiment."""
        if self._broken:
            return
        try:
            self._observe(client, res, t0_wall)
        except Exception as exc:  # noqa: BLE001 — observation must not break runs
            self._break("observe failed; observer disabled", exc)

    def observe_error(self, client: Any, t0_wall: float, exc: BaseException) -> None:
        """Failed logical call (e.g. HTTP after retries): zero-token record with
        the exception text; the exception itself is re-raised by the caller."""
        if self._broken:
            return
        try:
            self._observe_error(client, t0_wall, exc)
        except Exception as err:  # noqa: BLE001 — observation must not break runs
            self._break("observe_error failed; observer disabled", err)

    def _break(self, msg: str, exc: Exception) -> None:
        self._broken = True
        if not self._warned:
            self._warned = True
            print(f"WARN llm_obs: {msg} ({type(exc).__name__}: {exc}); "
                  "calls continue unobserved", flush=True)

    def _observe(self, client: Any, res: Any, t0_wall: float) -> None:
        usage = res.usage or {}
        in_tok = int(usage.get("prompt_tokens") or 0)
        out_tok = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (in_tok + out_tok))
        wall = max(0.0, float(res.wall_time or 0.0))
        t_end = t0_wall + wall
        raw = res.raw or {}
        transport = "stream" if raw.get("transport") == "stream" else "non_stream"
        if raw.get("transport_fallback"):
            transport = "stream_fallback"
        rec = {
            "call_id": None,  # assigned under the write lock
            "timestamp_start": _iso(t0_wall),
            "timestamp_end": _iso(t_end),
            "latency_seconds": round(t_end - t0_wall, 6),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "total_tokens": total,
            "model": str(res.model or getattr(client, "model", "")),
            "temperature": float(client.temperature),
            "tokens_estimated": bool(getattr(res, "completion_tokens_estimated", False)),
            "usage_present": bool(usage),
            "transport": transport,
            "finish_reason": str(res.finish_reason or ""),
            "guard_fired": bool(getattr(res, "repeat_guard", None)),
            "n_tool_calls": len(res.tool_calls or []),
            "http_attempts": max(1, int(getattr(client, "_last_http_attempts", 0) or 1)),
            "attempt_latency_seconds": round(wall, 6),
            "error": None,
            "context": self._current_context(),
        }
        self._emit(rec)

    def _observe_error(self, client: Any, t0_wall: float, exc: BaseException) -> None:
        t_end = time.time()
        rec = {
            "call_id": None,
            "timestamp_start": _iso(t0_wall),
            "timestamp_end": _iso(t_end),
            "latency_seconds": round(t_end - t0_wall, 6),
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model": str(getattr(client, "model", "")),
            "temperature": float(getattr(client, "temperature", 0.0)),
            "tokens_estimated": False,
            "usage_present": False,
            "transport": "error",
            "finish_reason": "",
            "guard_fired": False,
            "n_tool_calls": 0,
            "http_attempts": max(1, int(getattr(client, "_last_http_attempts", 0) or 1)),
            "attempt_latency_seconds": 0.0,
            "error": "{}: {}".format(type(exc).__name__, exc)[:500],
            "context": self._current_context(),
        }
        self._emit(rec)

    # ── internals ──

    def _emit(self, rec: Dict[str, Any]) -> None:
        with self._lock:
            if getattr(self._tls, "episode", None):
                self._tls.call_id = int(getattr(self._tls, "call_id", 0)) + 1
                rec["call_id"] = self._tls.call_id
                acc = getattr(self._tls, "acc", None)
                if acc is not None:
                    acc["llm_calls"] += 1
                    acc["input_tokens"] += rec["input_tokens"]
                    acc["output_tokens"] += rec["output_tokens"]
                    acc["total_tokens"] += rec["total_tokens"]
                    acc["llm_latency_seconds"] += rec["latency_seconds"]
                    if rec["error"]:
                        acc["llm_errors"] += 1
            else:
                self._call_id += 1
                rec["call_id"] = self._call_id
            self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._fh.flush()
            t = self.totals
            t["n_calls"] += 1
            t["input_tokens"] += rec["input_tokens"]
            t["output_tokens"] += rec["output_tokens"]
            t["total_tokens"] += rec["total_tokens"]
            t["latency_seconds"] += rec["latency_seconds"]
            if rec["error"]:
                t["n_errors"] += 1

    def close(self) -> None:
        with self._lock:
            try:
                self._fh.flush()
                self._fh.close()
            except Exception:
                pass
            try:
                self._ledger_fh.flush()
                self._ledger_fh.close()
            except Exception:
                pass

    def describe(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "path": str(self.path),
                "context": dict(self.context),
                "totals": dict(self.totals),
                "schema_version": SCHEMA_VERSION,
            }


_active: Optional[LLMCallRecorder] = None
_active_lock = threading.Lock()


def activate(path: Any, **context: Any) -> LLMCallRecorder:
    """Activate run-level call recording: call ONCE per run, right after the
    run directory is created. Every client constructed afterwards auto-attaches
    (DeepSeekClient.__init__ reads current_recorder()). A resume creates a new
    obs_session appended to the same file; a re-activation closes the previous
    recorder first."""
    global _active
    with _active_lock:
        if _active is not None:
            _active.close()
        _active = LLMCallRecorder(Path(path), context)
        return _active


def deactivate() -> None:
    global _active
    with _active_lock:
        if _active is not None:
            _active.close()
            _active = None


def current_recorder() -> Optional[LLMCallRecorder]:
    return _active


class _NullEpisode:
    """Fail-safe no-op episode: recorder not active (or closed)."""

    def record_outcome(self, **fields: Any) -> None:
        pass

    def __enter__(self) -> "_NullEpisode":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


_null_episode = _NullEpisode()


def episode_context(**identifiers: Any):
    """Module-level facade (the runner wiring calls llm_obs.episode_context).
    Delegates to the active recorder; silent no-op when none is active — the
    same fail-safe contract as the observation layer itself."""
    rec = current_recorder()
    if rec is None:
        return _null_episode
    return rec.episode_context(**identifiers)


def write_cost_summary(path: Any = None) -> Optional[Dict[str, Any]]:
    """Module-level facade for the recorder's run-level cost summary."""
    rec = current_recorder()
    if rec is None:
        return None
    return rec.write_cost_summary(path)
