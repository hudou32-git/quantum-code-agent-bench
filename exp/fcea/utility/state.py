"""DEU-v2 Phase-1: DynamicEvidenceStateManager — state tracking ONLY.

Phase-1 scope (design review 2026-09-22): observation and logging. No utility
update (Phase 2, updater.py), no guidance generation (Phase 3). Every signal
derives from fields the loop already has: official-eval error messages,
submitted code, probe outputs, call counters — no new oracle.

Semantics (rev2):
  - progress_score ∈ {-1, 0, +1}: +1 error improved (numeric signal better,
    requires code_changed), 0 changed-but-unclear or same, -1 numeric worse.
    Same-code error changes never count as progress (KL sampling noise, task 31).
  - code_changed: hash differs AND difflib ratio < code_ratio_threshold
    (task 31's ±3-char resubmits must classify as unchanged).
  - output_novelty ∈ {0,1}: empty / header-only / normalized-duplicate output
    → 0. (outcome novelty = output_novelty × step_state_change, joined in
    Phase 2; Phase 1 records both components.)
  - submit_pressure: llm_used_in_shot / shot_budget (recorded only; no
    submit guidance in v1 — exploration saturation warning instead).
"""
from __future__ import annotations

import difflib
import hashlib
import re
from typing import Any

from exp.fcea.utility.commitment_state import fsm_enabled

DEFAULT_CONSTANTS = {
    "code_ratio_threshold": 0.98,
    "submit_pressure_threshold": 0.6,
    "alpha": 0.3,        # Phase 2
    "decay": 0.8,        # Phase 2
    "q_floor": 0.05,     # Phase 2
}

_KL_RE = re.compile(r"KL\s*=\s*(-?\d+(?:\.\d+)?)", re.I)
_HEADER_RE = re.compile(r"^\s*(stderr\s*:|status\s*:|Traceback \(most recent call last\)).*$",
                        re.I | re.S)


def norm_err(msg: str) -> str:
    t = re.sub(r"/[\w./+-]+", " <P> ", (msg or "").strip())
    t = re.sub(r"0x[0-9a-fA-F]+", " <A> ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()[:200]


def norm_code(code: str) -> str:
    """Whitespace-insensitive code form: per-line strip, drop empty lines.
    Task 31 resubmissions differ by a handful of chars / blank lines — they are
    not code changes."""
    lines = [ln.rstrip() for ln in (code or "").splitlines()]
    return "\n".join(ln for ln in lines if ln.strip())


def code_hash(code: str) -> str:
    return hashlib.sha1(norm_code(code).encode("utf-8")).hexdigest()[:12]


def code_change_ratio(prev: str, new: str) -> float:
    a, b = norm_code(prev), norm_code(new)
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def output_novelty(output: str, seen_norm: set[str]) -> int:
    t = re.sub(r"\s+", " ", (output or "")).strip()
    if len(t) < 2:                       # empty / trivial
        return 0
    body = _HEADER_RE.sub("", output or "").strip()
    if len(re.sub(r"\s+", "", body)) < 2:  # header-only (stderr:/status:)
        return 0
    n = norm_err(output)
    if n in seen_norm:
        return 0
    seen_norm.add(n)
    return 1


def numeric_signal(error_message: str):
    m = _KL_RE.search(error_message or "")
    return float(m.group(1)) if m else None


class DynamicEvidenceStateManager:
    """Per-episode observation state. All update_* methods are passive."""

    def __init__(self, constants: dict | None = None):
        self.c = dict(DEFAULT_CONSTANTS)
        if constants:
            self.c.update(constants)
        self.current_error = ""
        self.previous_error = ""
        self.error_transition = "first"          # first|improved|same|worse|unclear
        self.code_hash = code_hash("")
        self.previous_code_hash = ""
        self.code_change_ratio = 1.0
        self.evidence_history: list[dict] = []
        self.evidence_novelty_history: list[int] = []
        self.no_progress_count = 0
        self.same_error_count = 0
        self.last_progress_score = 0
        self.submission_status = {
            "official": 0, "nosubmit_events": 0,
            "llm_used_in_shot": 0, "shot_budget": 16,
            "candidate_exists": False, "candidate_changed_since_submit": False,
            "last_submitted_code_hash": "",
        }
        self._seen_probe_outputs: set[str] = set()
        self._prev_code_text = ""

    # ---- probe boundary -------------------------------------------------
    def on_probes(self, shot: int, probes: list[dict]) -> list[dict]:
        records = []
        for p in probes or []:
            out = str(p.get("output") or "")
            nov = output_novelty(out, self._seen_probe_outputs)
            rec = {"shot": shot, "category": p.get("category"), "novelty": nov,
                   "out_chars": len(out)}
            self.evidence_history.append(rec)
            self.evidence_novelty_history.append(nov)
            records.append(rec)
        return records

    # ---- official eval / nosubmit boundary ------------------------------
    def on_eval_result(self, *, shot: int, passed: bool, error_message: str,
                       code: str, nosubmit: bool = False) -> dict:
        # deurq_fsm G2: SUBMISSION_MISSING is a commitment failure, not a
        # technical one. Technical Error Chain Integrity invariant: the
        # comparison chain (current_error / previous_error / code hashes /
        # _prev_code_text baseline) is preserved untouched, so the NEXT
        # technical failure compares against the last TECHNICAL failure.
        # Derived caches (error_transition, last_progress_score) take the
        # legacy-neutral values ("same", 0) because the frozen C2 consumer
        # in the loops (record_deu_step) reads them for step_state_change
        # and reward — with these values its nosubmit-step update is
        # identical to the legacy path. Invariant B: the stagnation
        # counters do not move (no same_error/no_progress increment).
        # Invariant A: the record carries an explicit progress_score=0 so
        # controller-side convergence memory (fsm_g1) counts the boundary
        # as no-improvement (spec 修订 3 dual track).
        if nosubmit and fsm_enabled("G2"):
            self.submission_status["nosubmit_events"] += 1
            self.submission_status["official"] = shot
            # derived caches -> legacy-neutral values; the loops read these
            # attributes directly after this call to feed the frozen C2
            # (step_state_change, reward) — with ("same", 0) its nosubmit-
            # step update is identical to the legacy path
            self.error_transition = "same"
            self.last_progress_score = 0
            rec = self.step_record(shot=shot, passed=passed, code_changed=False)
            rec["error_transition"] = "nosubmit"
            rec["progress_score"] = 0
            rec["boundary_type"] = "nosubmit"
            rec["technical_failure"] = False
            rec["commitment_failure"] = True
            return rec
        prev_error = self.current_error
        self.previous_error = prev_error
        self.current_error = (error_message or "")[:400]
        self.previous_code_hash = self.code_hash
        self.code_hash = code_hash(code)
        self.code_change_ratio = code_change_ratio(self._prev_code_text, code) \
            if hasattr(self, "_prev_code_text") else 1.0
        code_changed = (self.code_hash != self.previous_code_hash
                        and self.code_change_ratio < self.c["code_ratio_threshold"])
        if nosubmit:
            self.error_transition = "same"
            self.submission_status["nosubmit_events"] += 1
        elif not prev_error:
            self.error_transition = "first"
        else:
            if norm_err(self.current_error) == norm_err(prev_error):
                self.error_transition = "same"
            else:
                prev_num = numeric_signal(prev_error)
                cur_num = numeric_signal(self.current_error)
                if prev_num is not None and cur_num is not None:
                    # numeric-tolerance "same": 4th-decimal KL drift on resubmit
                    # is sampling noise (task 31), not an error transition
                    if abs(cur_num - prev_num) <= max(1e-9, 0.01 * abs(prev_num)):
                        self.error_transition = "same"
                    else:
                        self.error_transition = "improved" if cur_num < prev_num else "worse"
                else:
                    self.error_transition = "unclear"
        # progress_score (rev2 three-level; both non-neutral tiers require
        # code_changed — same-code error changes are sampling noise in both
        # directions, task 31)
        if self.error_transition == "improved" and code_changed:
            self.last_progress_score = 1
        elif self.error_transition == "worse" and code_changed:
            self.last_progress_score = -1
        else:
            self.last_progress_score = 0
        # counters
        if self.error_transition == "same" and not code_changed:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0
        if self.error_transition == "same":
            self.same_error_count += 1
        else:
            self.same_error_count = 0
        self._prev_code_text = code or ""
        self.submission_status["official"] = shot
        self.submission_status["candidate_exists"] = bool(code)
        self.submission_status["candidate_changed_since_submit"] = (
            self.code_hash != self.submission_status["last_submitted_code_hash"])
        return self.step_record(shot=shot, passed=passed, code_changed=code_changed)

    def on_code_submitted(self, code: str) -> None:
        """Record the hash of code that was actually (about to be) graded."""
        self.submission_status["last_submitted_code_hash"] = code_hash(code)

    def on_shot_state(self, llm_used_in_shot: int, shot_budget: int) -> dict:
        self.submission_status["llm_used_in_shot"] = llm_used_in_shot
        self.submission_status["shot_budget"] = shot_budget
        return self.pressure()

    def pressure(self) -> dict:
        budget = max(self.submission_status["shot_budget"], 1)
        p = self.submission_status["llm_used_in_shot"] / budget
        return {"submit_pressure": round(p, 3),
                "submit_pressure_high": p >= self.c["submit_pressure_threshold"]}

    def step_record(self, *, shot: int, passed: bool, code_changed: bool) -> dict:
        p = self.pressure()
        rec = {
            "step": shot,
            "error_before": self.previous_error,
            "error_after": self.current_error,
            "error_transition": self.error_transition,
            "code_hash": self.code_hash,
            "previous_code_hash": self.previous_code_hash,
            "code_changed": bool(code_changed),
            "code_change_ratio": round(self.code_change_ratio, 4),
            "evidence_used": self.evidence_used_this_step(),
            "no_progress_count": self.no_progress_count,
            "same_error_count": self.same_error_count,
            "progress_score": self.last_progress_score,
            "passed": bool(passed),
            "submission_pressure": p["submit_pressure"],
            "submit_pressure_high": p["submit_pressure_high"],
            # Phase-2 fields present but null until updater.py goes live
            "marginal_utility_before": None, "reward": None,
            "marginal_utility_after": None, "outcome_novelty": None,
            "guidance_kind": "none",
        }
        return rec

    def evidence_used_this_step(self) -> dict:
        c: dict[str, int] = {}
        for h in self.evidence_history:
            if h.get("category"):
                c[h["category"]] = c.get(h["category"], 0) + 1
        return c

    def category_novelties(self, shot: int) -> dict[str, list[int]]:
        """{category: [output_novelty per probe]} for probes recorded in `shot`."""
        out: dict[str, list[int]] = {}
        for h in self.evidence_history:
            if h.get("shot") == shot and h.get("category"):
                out.setdefault(h["category"], []).append(int(h.get("novelty") or 0))
        return out

    def snapshot(self) -> dict:
        return {
            "current_error": self.current_error, "previous_error": self.previous_error,
            "error_transition": self.error_transition,
            "code_hash": self.code_hash, "previous_code_hash": self.previous_code_hash,
            "code_change_ratio": round(self.code_change_ratio, 4),
            "evidence_history": list(self.evidence_history),
            "evidence_novelty_history": list(self.evidence_novelty_history),
            "no_progress_count": self.no_progress_count,
            "same_error_count": self.same_error_count,
            "submission_status": dict(self.submission_status),
        }
