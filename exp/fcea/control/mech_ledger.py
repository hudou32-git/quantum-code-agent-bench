"""MECH-1 shared per-episode ledger (C failure-signature memory + D-F/D1
contract coverage).

Pure logic only (no sandbox, no LLM) so the selftest can exercise it
directly. The loop owns one MechLedger per episode; the deferred hooks feed
it at failure boundaries and probe completions.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

# ---- error-signature normalization (frozen 2026-09-30) --------------------

def normalize_sig(msg: str | None) -> str:
    m = re.sub(r"[0-9]+\.[0-9]+", "N", msg or "")
    m = re.sub(r"0x[0-9a-fA-F]+", "ADDR", m)
    return m.strip()[:110]


def code_hash(code: str | None) -> str:
    return hashlib.sha1((code or "").strip().encode()).hexdigest()[:10]


# ---- failing-API token extraction (frozen rules, 2026-09-30 analysis) -----

_TOKEN_PATTERNS = (
    r"'([\w.]+)' object has no attribute",      # SDK receivers + attrs
    r"(\w+)\.__init__\(\) got an unexpected",
    r"(\w+)\.__init__\(\) missing",
    r"(?<![\w.])(\w+)\.\w+\(\) got an unexpected",
    r"(?<![\w.])(\w+)\(\) takes \d+ positional",
    r"(?<![\w.])(\w+) must be specified",
    r"cannot import name '(\w+)'",
    r"module '([\w.]+)' has no attribute",
    r"(?<![\w.])(\w+)\(\) got an unexpected keyword",
    r"No (\w+) for experiment",
)
_TOKEN_STOP = {"str", "int", "float", "list", "dict", "tuple", "NoneType",
               "bool", "numpy", "self"}


def api_tokens_from_error(msg: str | None) -> set[str]:
    """SDK/API names implicated by an error message (audit rule frozen)."""
    out: set[str] = set()
    for pat in _TOKEN_PATTERNS:
        for m in re.findall(pat, msg or ""):
            base = m.split(".")[-1]
            if base and base not in _TOKEN_STOP:
                out.add(base)
    return out


def ctor_lines(code: str | None, tokens: set[str]) -> list[str]:
    """Code lines that touch any implicated token (for the ledger block)."""
    if not code or not tokens:
        return []
    hits = []
    for ln in code.splitlines():
        s = ln.strip()
        if any(t in s for t in tokens) and ("import " not in s or len(hits) == 0):
            hits.append(s[:120])
    return hits[:4]


# ---- ledger ----------------------------------------------------------------

class MechLedger:
    """Per-episode memory: failed signatures + probed contracts."""

    def __init__(self) -> None:
        self.failures: list[dict[str, Any]] = []      # shots worth
        self.contracts: dict[str, dict[str, Any]] = {}  # target -> probe result

    # -- failures (C) --
    def record_failure(self, msg: str | None, code: str | None) -> None:
        toks = api_tokens_from_error(msg)
        self.failures.append({
            "sig": normalize_sig(msg),
            "tokens": sorted(toks),
            "code_hash": code_hash(code),
            "ctor_lines": ctor_lines(code, toks),
        })

    def saw_signature(self, msg: str | None) -> bool:
        sig = normalize_sig(msg)
        return any(f["sig"] == sig for f in self.failures)

    def failure_block(self) -> str:
        """[failure ledger] text appended to feedback (C). Empty if unused."""
        if not self.failures:
            return ""
        lines = ["[failure ledger — already-failed attempts this episode]"]
        for i, f in enumerate(self.failures, 1):
            line = f"  shot{i}: {f['sig'][:90]}"
            if f["ctor_lines"]:
                line += f" | at: {f['ctor_lines'][0][:70]}"
            lines.append(line)
        lines.append("  Do not resubmit a construction already listed above;")
        lines.append("  use ApiProbe to check the installed contract first.")
        return "\n".join(lines)

    def revert_note(self, new_code: str | None) -> str | None:
        """Warn when the patch re-visits APIs that already failed (C)."""
        if not self.failures or not new_code:
            return None
        cur = code_hash(new_code)
        if any(f["code_hash"] == cur for f in self.failures):
            return ("[mech ledger] this patch is byte-identical to an "
                    "already-failed attempt.")
        toks = {t for f in self.failures for t in f["tokens"]}
        touched = sorted(t for t in toks if t in new_code)
        if touched:
            return ("[mech ledger] the patch touches APIs that already "
                    f"failed this episode: {touched[:4]}; check their "
                    "installed contract via ApiProbe before submitting.")
        return None

    # -- contracts (A / D-F / D1) --
    def record_contract(self, target: str, result: dict[str, Any]) -> None:
        self.contracts[target] = {
            "ok": bool(result.get("ok")),
            "digest": hashlib.sha1(
                str(result.get("output", ""))[:400].encode()).hexdigest()[:10],
        }

    def contract_covered(self, targets: set[str]) -> bool:
        """True iff every target has a recorded (executed) contract probe."""
        if not targets:
            return True
        return all(t in self.contracts for t in targets)

    def uncovered_targets(self, msg: str | None) -> set[str]:
        toks = api_tokens_from_error(msg)
        return {t for t in toks if t not in self.contracts}

    def coverage_note(self) -> str:
        if not self.contracts:
            return ""
        parts = [f"{t}:{'ok' if v['ok'] else 'err'}"
                 for t, v in sorted(self.contracts.items())]
        return "[contract coverage] " + ", ".join(parts[:8])
