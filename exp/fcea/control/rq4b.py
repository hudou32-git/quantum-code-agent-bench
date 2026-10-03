"""rq4b mechanisms (PROTOCOL v2.1, frozen 2026-09-30).

Two additive, default-off mechanisms on the deurc-noctx stack:

  deurc_trace  (A|trace, QHE): informative-assertion trigger + LLM
               self-constructed trace probes + soft obligation gate.
  deurc_restart / deurc_replan (B, QB+): late-stall trigger (shot-2 KL>=5,
               no meaningful improvement) -> shot-3 context surgery +
               tools unbound + forced fresh generation. The two variants
               differ ONLY in the frozen injection sentence pair.

All prompt bytes live here and must match
analysis/agent_ceiling_analysis/rq4b_frozen_prompts.md byte-for-byte
(checked by selftest_rq4b.py). Any byte change = version bump + re-pilot.
"""
from __future__ import annotations

import re

# ---- frozen constants (PROTOCOL v2.1 §3.3/§4.3) --------------------------
TRACE_TRIGGER_MANUAL_PREFIXES = ("KeyError: 'x'", "ValueError: The truth value")
REPLAN_THETA = 5.0            # far-band boundary
REPLAN_STALL_MARGIN = -1.0    # KL2 - KL1 must be > this to count as stalled
REPLAN_MAX_USES = 1
_SIG_NUM_RE = re.compile(r"[0-9.]+")
_KL_RE = re.compile(r"KL=([0-9.]+)")


# ---- A|trace --------------------------------------------------------------
def informative_signature(msg: str | None) -> str | None:
    """Frozen trigger predicate (PROTOCOL §3.3-1).

    Informative assertion failure == (AssertionError with non-empty body)
    OR manual-adjudicated SEM prefix. Returns the normalized signature
    (digits->N, first 40 chars) or None when the failure is not in the
    trigger class (bare assertion / interface / NoSubmit / infra).
    """
    m = (msg or "").strip()
    if not m or "no official submit" in m:
        return None
    if m.startswith("AssertionError"):
        body = m.split(":", 1)[1].strip() if ":" in m else ""
        if not body:
            return None
        return _SIG_NUM_RE.sub("N", body)[:40]
    if m.startswith(TRACE_TRIGGER_MANUAL_PREFIXES):
        return _SIG_NUM_RE.sub("N", m)[:40]
    return None


_TRACE_CONTRACT_HEAD = (
    '[repair-contract] The official check failed with:\n'
    '  "{body}"\n'
    'Before your next submission, run at least one BatchProbe (requested_evidence_kind="trace") that:\n'
    '1. calls your entry function with minimal valid inputs;\n'
    '2. prints the quantity this assertion checks, and\n'
    '3. prints the value your current implementation actually produces.'
)


def trace_contract(assertion_body: str) -> str:
    """A1 injection text (frozen bytes; rq4b_frozen_prompts.md §1)."""
    return _TRACE_CONTRACT_HEAD.replace("{body}", assertion_body)


class TraceGate:
    """Soft obligation gate + per-episode accounting (PROTOCOL §3.3-3/4).

    armed: signatures whose contract was injected and whose probe
    obligation is still pending. A BatchProbe round containing a
    kind="trace" query discharges every armed signature (attribution to a
    specific signature is not observable; conservative discharge).
    A Write issued while signatures remain armed-and-undischarged counts
    one violation and re-injects the pending contract(s) verbatim as a
    suffix on the Write result (soft: never blocks).
    """

    def __init__(self) -> None:
        self.armed: list[str] = []
        self.injections = 0
        self.probe_rounds_trace = 0
        self.violations = 0
        self.writes_while_armed = 0
        self.writes_compliant = 0

    def on_failure(self, msg: str | None) -> str | None:
        """Boundary hook. Returns the injection text when a NEW signature
        is armed (frozen A1 text), else None (no injection)."""
        sig = informative_signature(msg)
        if sig is None or sig in self.armed:
            return None
        self.armed.append(sig)
        self.injections += 1
        body = (msg or "").split(":", 1)[1].strip() \
            if (msg or "").startswith("AssertionError") else (msg or "")[:120]
        return trace_contract(body)

    def on_probe_round(self, kinds: list[str]) -> bool:
        """BatchProbe round hook; True iff the obligation was discharged."""
        if "trace" in [k for k in kinds if k]:
            self.probe_rounds_trace += 1
            if self.armed:
                self.armed.clear()
                return True
        return False

    def on_write(self) -> str | None:
        """Write hook. Returns re-injection text (verbatim contracts) when
        armed signatures were discharged by no prior trace probe."""
        if not self.armed:
            self.writes_compliant += 1
            return None
        self.writes_while_armed += 1
        self.violations += len(self.armed)
        reminder = "\n".join("[repair-contract still pending]\n" + _TRACE_CONTRACT_HEAD
                             for _ in self.armed)
        self.armed.clear()
        return reminder

    def stats(self) -> dict:
        armed_writes = self.writes_while_armed
        return {"triggered": self.injections > 0,
                "injections": self.injections,
                "probe_rounds_with_trace_kind": self.probe_rounds_trace,
                "violations": self.violations,
                "writes_while_armed": armed_writes,
                "writes_compliant": self.writes_compliant,
                "compliance_rate": (round(1 - armed_writes / (armed_writes
                                         + self.writes_compliant), 3)
                                    if (armed_writes + self.writes_compliant) else None)}


# ---- B|restart/replan -----------------------------------------------------
_RESTART_TMPL = ("[attempt-3] The previous implementation was rejected "
                 "(KL={kl}, threshold 0.05) and is unavailable. Create a new "
                 "implementation of the task below.")
_REPLAN_TMPL = ("[attempt-3] The previous implementation was rejected "
                "(KL={kl}, threshold 0.05) and is unavailable. The previous "
                "solution strategy may be invalid. Re-derive the solution "
                "from the task specification, then create a new "
                "implementation of the task below.")


def replan_injection(kind: str, kl_raw: str) -> str:
    """B1/B2 frozen text; kl_raw = the KL digits exactly as the grader
    printed them (no re-formatting, PROTOCOL placeholder spec)."""
    tmpl = _RESTART_TMPL if kind == "restart" else _REPLAN_TMPL
    return tmpl.replace("{kl}", kl_raw)


def kl_raw_of(msg: str | None) -> str | None:
    m = _KL_RE.search(msg or "")
    return m.group(1) if m else None


class ReplanState:
    """Late-stall trigger bookkeeping (PROTOCOL §4.3).

    trigger fires at the END of the shot-2 failure boundary when:
      KL2 >= REPLAN_THETA  and  (KL2 - KL1) > REPLAN_STALL_MARGIN
      and replans_used == 0.
    The shot-3 context surgery is performed by loop.py using surgery().
    """

    def __init__(self, kind: str) -> None:
        assert kind in ("restart", "replan")
        self.kind = kind
        self.fail_kls: list[float] = []
        self.fail_kls_raw: list[str] = []
        self.replans_used = 0
        self.triggered = False
        self.pending = False

    def on_official_failure(self, msg: str | None) -> None:
        raw = kl_raw_of(msg)
        if raw:
            self.fail_kls.append(float(raw))
            self.fail_kls_raw.append(raw)

    def on_shot2_boundary(self, official: int) -> bool:
        """Call at every failing boundary; True when replan is now pending
        (the surgery happens at the start of the next shot)."""
        if (self.replans_used >= REPLAN_MAX_USES or self.pending
                or official != 2 or len(self.fail_kls) < 2):
            return False
        kl1, kl2 = self.fail_kls[-2], self.fail_kls[-1]
        if kl2 >= REPLAN_THETA and (kl2 - kl1) > REPLAN_STALL_MARGIN:
            self.pending = True
            self.triggered = True
            self.replans_used += 1
            return True
        return False

    def surgery(self, system_prompt: str, user0: str) -> list[dict]:
        """Context surgery: [system, original spec, injection]. Returns the
        replacement message list (caller assigns into messages[:])."""
        assert self.pending and self.fail_kls_raw
        self.pending = False
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user0},
            {"role": "user", "content": replan_injection(self.kind,
                                                         self.fail_kls_raw[-1])},
        ]

    def stats(self) -> dict:
        return {"kind": self.kind, "triggered": self.triggered,
                "kl_sequence": self.fail_kls,
                "kl_sequence_raw": self.fail_kls_raw}


# ---- trace kind taxonomy extension (variant-gated in loop.py) -------------
TRACE_KIND = "trace"
TRACE_KIND_CATEGORY = "E3"   # behavioral evidence on own code


# ---- A16 forced-contract probe v2 (PROTOCOL_rq4b_A16.md §3, frozen) --------
# Three harness-side enforcement layers on top of the v1 A1 contract:
#   L1 failure-boundary auto probe (this file + control/trace_probe.py)
#   L2 Eval tri-state interception (loop.py, classify_probe below)
#   L3 model-initiated trace BatchProbe channel (v1 TraceGate semantics kept)
# All default-off (variant deurc_trace_v2 only); v1 variants byte-identical.
TRACE_REJECT_CAP_PER_SHOT = 3     # L2 non-official rejections per shot, then fail-open
TRACE_TIMEOUT_S = 16              # per probe run (v1's 8s truncated /9's entry call)
TRACE_MAX_CALL_COMBOS = 24        # bounded dummy-argument product
# Frozen dummy ladder (§3-L1-2): typed annotation first, then the generic rungs.
TRACE_DUMMY_LADDER = (0.5, 3, "00", [], True)
TRACE_TYPED_DUMMIES = {"float": (0.5,), "int": (3,), "str": ("00",),
                       "list": ([],), "bool": (True,)}

_L1_ARTIFACT_BLOCK = "[trace] assertion expects {body}; your artifact: {artifact}"
_L1_CRASH_BLOCK = ("[trace] assertion expects {body}; "
                   "your artifact: <entry crash: {error}>")
_L1_CONSTRUCT_BLOCK = ("[trace] assertion expects {body}; "
                       "your artifact: <not constructed: {error}>")
_L2_REJECT_HEAD = "[trace — non-official check, this attempt was NOT consumed]"

_EXPECTED_NUM_RE = r"([0-9]+(?:\.[0-9]+)?)"
_EXPECTED_PATTERNS = (
    re.compile(r"expected\s+" + _EXPECTED_NUM_RE, re.I),
    re.compile(r"should\s+be\s+" + _EXPECTED_NUM_RE, re.I),
    re.compile(r"is\s+not\s+" + _EXPECTED_NUM_RE, re.I),
)
_ANY_NUM_RE = re.compile(r"(?<![0-9.])" + _EXPECTED_NUM_RE + r"(?![0-9])")
# Type-coherence guard (pre-freeze validation 2026-10-01, frozen): a
# collection-length probe value may only mismatch when the assertion body
# itself talks about size/expectation — "The concurrence ... is not 0"
# (/144) must NOT reject on a sequence length; "Expected 10 ..., but got 98"
# (/138) and "Length of list is not 10" (/137) must.
TRACE_SIZE_HINT_RE = re.compile(
    r"length|len\(|size|count|number of|expected|elements|items|entries", re.I)


def parse_expected_number(body: str | None) -> float | None:
    """Frozen L2 expectation parser (PROTOCOL_rq4b_A16.md §3-L2; manifest §4).

    Priority: "expected N" > "should be N" > "is not N" > unique number in
    the body. None (no parseable expectation -> L2 FAIL-OPEN) when no
    pattern matches and the body does not contain exactly one number.
    """
    text = (body or "").strip()
    if not text:
        return None
    for pat in _EXPECTED_PATTERNS:
        m = pat.search(text)
        if m:
            return float(m.group(1))
    nums = _ANY_NUM_RE.findall(text)
    return float(nums[0]) if len(nums) == 1 else None


def probe_numeric_value(artifact: dict | None) -> float | None:
    """Frozen artifact->number rule: scalar int/float -> the value;
    sequence/dict -> length; everything else (circuit, container, str,
    bool, None) -> None (not comparable -> L2 FAIL-OPEN)."""
    if not isinstance(artifact, dict):
        return None
    kind = artifact.get("kind")
    if kind == "scalar":
        v = artifact.get("value")
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        return None
    if kind in ("sequence", "dict"):
        n = artifact.get("len", artifact.get("n_keys"))
        return float(n) if isinstance(n, (int, float)) else None
    return None


def mismatch(expected: float | None, value: float | None, *, body: str | None = None,
             artifact_kind: str | None = None) -> bool:
    """Frozen L2 mismatch (type-coherent): parseable expectation AND
    comparable probe value AND they differ AND — for collection-length
    comparisons only — the body is size/expectation-flavored. Anything
    unparseable is NOT a mismatch (fail-open)."""
    if expected is None or value is None or value == expected:
        return False
    if artifact_kind in ("sequence", "dict"):
        return bool(TRACE_SIZE_HINT_RE.search(body or ""))
    return True


class TraceGateV2(TraceGate):
    """v2 gate: v1 accounting kept byte-for-byte; two deltas.

    Delta 1 (A16 §3): the armed obligation is harness-owned — a Write no
    longer discharges it (v1 cleared `armed`; v2 keeps it so L2 can
    intercept the Eval of the just-written attempt). Re-injection and
    violation accounting still fire per v1. Discharge stays with the L3
    channel (model-initiated kind="trace" BatchProbe round).
    Delta 2: A16 counters for the P1/P2 gates (boundary probe delivery,
    L2 tri-state tally) and the raw assertion body of the last trigger
    (the L2 expectation parser's input).
    """

    def __init__(self) -> None:
        super().__init__()
        self.armed_bodies: dict[str, str] = {}
        self.last_body: str | None = None
        self.informative_boundaries = 0
        self.boundary_probes = 0
        self.blocks_delivered = 0
        self.l2_probes = 0
        self.l2_rejects = 0
        self.l2_indeterminate = 0
        self.l2_passthrough = 0
        self.l2_rejects_this_shot = 0

    def on_failure(self, msg: str | None) -> str | None:
        sig = informative_signature(msg)
        if sig is None:
            return None
        self.informative_boundaries += 1
        body = self.body_of(msg)
        self.last_body = body
        self.armed_bodies[sig] = body
        return super().on_failure(msg)

    @staticmethod
    def body_of(msg: str | None) -> str:
        """Frozen assertion-body extraction (v1 on_failure rule): text after
        'AssertionError:' for assertion failures, else the message head."""
        return (msg or "").split(":", 1)[1].strip() \
            if (msg or "").startswith("AssertionError") else (msg or "")[:120]

    def on_write(self) -> str | None:
        """v2: violation accounting + verbatim re-injection, armed PERSISTS."""
        if not self.armed:
            self.writes_compliant += 1
            return None
        self.writes_while_armed += 1
        self.violations += len(self.armed)
        reminder = "\n".join("[repair-contract still pending]\n" + _TRACE_CONTRACT_HEAD
                             for _ in self.armed)
        return reminder

    def on_probe_round(self, kinds: list[str]) -> bool:
        discharged = super().on_probe_round(kinds)
        if discharged:
            self.armed_bodies.clear()
        return discharged

    def new_shot(self) -> None:
        """Shot boundary: the L2 reject cap is per shot."""
        self.l2_rejects_this_shot = 0

    def stats(self) -> dict:
        out = super().stats()
        out.update({
            "informative_boundaries": self.informative_boundaries,
            "boundary_probes": self.boundary_probes,
            "blocks_delivered": self.blocks_delivered,
            "delivery_rate": (round(self.blocks_delivered
                                    / self.informative_boundaries, 3)
                              if self.informative_boundaries else None),
            "l2_probes": self.l2_probes,
            "l2_rejects": self.l2_rejects,
            "l2_indeterminate": self.l2_indeterminate,
            "l2_passthrough": self.l2_passthrough,
        })
        return out


def l1_block(body: str | None, probe: dict) -> str | None:
    """Frozen L1 feedback block (PROTOCOL §3-L1-4). None = not delivered
    (sandbox blocked / timeout / unparseable runner output)."""
    b = (body or "").strip()
    if not b:
        return None
    phase = probe.get("phase")
    if probe.get("status") != "ok":
        return None
    if phase == "artifact" and isinstance(probe.get("artifact"), dict):
        import json as _json
        return _L1_ARTIFACT_BLOCK.replace("{body}", b).replace(
            "{artifact}", _json.dumps(probe["artifact"], separators=(",", ":")))
    if phase == "call":
        return _L1_CRASH_BLOCK.replace("{body}", b).replace(
            "{error}", str(probe.get("error") or "")[:150])
    if phase == "construct":
        return _L1_CONSTRUCT_BLOCK.replace("{body}", b).replace(
            "{error}", str(probe.get("error") or "")[:150])
    return None


def l2_reject_block(body: str | None, probe: dict, expected: float | None,
                    value: float | None) -> str:
    """Frozen L2 rejection text returned as the Eval tool result (the
    attempt was NOT consumed)."""
    b = (body or "").strip()
    lines = [_L2_REJECT_HEAD, l1_block(b, probe) or
             (_L1_ARTIFACT_BLOCK.replace("{body}", b)
              .replace("{artifact}", "<probe evidence unavailable>"))]
    if expected is not None and value is not None:
        lines.append(f"[trace] parsed expectation = {expected}; "
                     f"probe value = {value}")
    return "\n".join(lines)
