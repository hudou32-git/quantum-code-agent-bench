"""Context gate: mode-based adaptive context assembly.

The LLM does not see the full history blindly. Messages are segmented into
ATOMIC TURNS first — one assistant message (with its tool_calls) plus every
following role=="tool" message — so pruning never breaks tool_call/tool
pairing at the API level. Turn kinds:
  "evidence"   turn contains a BatchProbe result
  "patch"      turn contains a Write or Eval result (candidate/validation)
  "reasoning"  plain assistant turn (no tool calls)
  "notice"     user turn (boundary feedback / controller directives)
  "header"     system + initial task user message (always kept)

Policies (rq4_deurc_design.md §context gate):
  SEARCH     full            keep everything
  FOCUS      focused         drop all but the last `keep_evidence_turns`
                             evidence turns; drop reasoning turns except the
                             last; keep patch/validation and notices
  ESCAPE     escaped         drop reasoning turns except the last; drop
                             evidence turns (failed reasoning + failed
                             evidence paths); keep patch/validation, notices,
                             header
  TERMINATE  final           keep header, the LAST patch turn (best candidate
                             + validation), and notices; drop everything else

Pure function over the message list; returns the new list plus reduction
stats (turn/char ratios — a primary mechanism metric).
"""
from __future__ import annotations

from exp.fcea.control.mode_selector import (
    CONTEXT_POLICY, ESCAPE, FOCUS, SEARCH, TERMINATE,
)

DEFAULT_CONSTANTS = {
    "keep_evidence_turns": 2,     # FOCUS: newest evidence turns kept
}

_KIND_BY_TOOL = {"BatchProbe": "evidence", "Write": "patch", "Eval": "patch"}


def segment_turns(messages: list[dict]) -> dict:
    """Split the message list into header + list of turns. Each turn is
    {"kind", "msgs", "chars"}; kind = evidence|patch|reasoning|notice."""
    header: list[dict] = []
    turns: list[dict] = []
    i = 0
    header_done = False
    while i < len(messages):
        m = messages[i]
        role = m.get("role")
        if role == "system" or (role == "user" and not header_done):
            header.append(m)
            header_done = header_done or role == "user"
            i += 1
            continue
        if role == "assistant":
            turn = [m]
            j = i + 1
            while j < len(messages) and messages[j].get("role") == "tool":
                turn.append(messages[j])
                j += 1
            kind = "reasoning"
            for t in turn:
                name = t.get("name") or ""
                if name in _KIND_BY_TOOL:
                    kind = _KIND_BY_TOOL[name]
                    break
            turns.append({"kind": kind, "msgs": turn,
                          "chars": sum(len(str(x.get("content") or ""))
                                       for x in turn)})
            i = j
            continue
        # user boundary / feedback messages are standalone turns
        turns.append({"kind": "notice", "msgs": [m],
                      "chars": len(str(m.get("content") or ""))})
        i += 1
    return {"header": header, "turns": turns}


def assemble(mode: str, messages: list[dict],
             constants: dict | None = None) -> tuple[list[dict], dict]:
    """Return (new_messages, stats). Deterministic; API-safe turn boundaries."""
    c = dict(DEFAULT_CONSTANTS)
    if constants:
        c.update(constants)
    policy = CONTEXT_POLICY.get(mode, "full")
    seg = segment_turns(messages)
    header, turns = seg["header"], seg["turns"]
    chars_before = sum(t["chars"] for t in turns) + sum(len(str(m.get("content") or ""))
                                                        for m in header)
    if policy == "full" or mode == SEARCH:
        kept = list(turns)
    else:
        last_reasoning = max((i for i, t in enumerate(turns)
                              if t["kind"] == "reasoning"), default=-1)
        last_patch = max((i for i, t in enumerate(turns)
                          if t["kind"] == "patch"), default=-1)
        last_notice = max((i for i, t in enumerate(turns)
                           if t["kind"] == "notice"), default=-1)
        evidence_idx = [i for i, t in enumerate(turns) if t["kind"] == "evidence"]
        kept = []
        for i, t in enumerate(turns):
            if t["kind"] == "notice":
                # boundary/feedback/directive turns: keep recent ones — in the
                # final policy only the last one (older failure breadcrumbs
                # are exploration history)
                if policy != "final" or i == last_notice:
                    kept.append(t)
            elif t["kind"] == "patch" and i == last_patch:
                kept.append(t)              # current candidate + validation
            elif t["kind"] == "evidence" and policy == "focused":
                # keep the NEWEST keep_evidence_turns evidence turns
                recency = len(evidence_idx) - evidence_idx.index(i)
                if recency <= c["keep_evidence_turns"]:
                    kept.append(t)
            elif t["kind"] == "reasoning" and i == last_reasoning:
                kept.append(t)
            # everything else (old reasoning / old evidence / old patches) is
            # pruned — the failed paths the mode is escaping from
    new_messages = list(header) + [m for t in kept for m in t["msgs"]]
    kept_ids = {id(t) for t in kept}
    chars_after = chars_before - sum(t["chars"] for t in turns
                                     if id(t) not in kept_ids)
    stats = {
        "context_policy": policy,
        "turns_before": len(turns), "turns_kept": len(kept),
        "chars_before": chars_before, "chars_after": chars_after,
        "reduction_ratio": round(1.0 - chars_after / chars_before, 4)
        if chars_before else 0.0,
    }
    return new_messages, stats
