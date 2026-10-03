"""E3-new / E4 acceptance pipeline (frozen 2026-10-01).

docs/E3_E4_ACCEPTANCE_PIPELINE.md is the normative spec; this module is its
only implementation. Everything here is ADDITIVE and default-off: legacy
variants (E0-E2, deurc_*, mech1_*, legacy deurq_baseenv) never construct
these objects and stay byte-identical.

Pipeline (submission acceptance, per candidate revision):

    candidate (Write / fallback / salvage)
      -> Z0 artifact hygiene            (exec_artifact_gate, unchanged)
      -> Z3 runtime validation          (mech preflight; Z3-first)
      -> Z4 semantic alignment          (armed expectation probe; E4 only)
      -> official evaluation

Frozen rules (protocol freeze 2026-10-01):
  R1 Z3-first: semantic alignment is evaluated only after runtime validity —
     a candidate rejected by Z3 is never probed by Z4 on this attempt.
  R2 Gate-bound salvage: a gate rejection is non-official on the model-
     initiated Eval path (slot NOT consumed, feedback returned), but on the
     end-of-shot salvage path the slot IS consumed and the candidate is
     recorded as NoSubmit (nosubmit_reason=...). The legacy FAIL-OPEN
     salvage (loop.py, exec_slot_salvage alone) is superseded on E3-new/E4
     and preserved byte-identically on E0-E2.
  R3 Revision identity: candidate_hash = sha256(normalized contents). A
     revision rejected by an active gate is ineligible for salvage until
     its contents change (a modified revision re-enters the full pipeline).
  R4 Independent budgets: Z3 caps (preflight_reject_cap_per_shot) and the
     Z4 cap (TRACE_REJECT_CAP_PER_SHOT) count separately; enabling Z4 does
     not change any Z3 cap.
  R5 Fail-open: any gate that cannot produce a verdict (indeterminate /
     timeout / crash-classified as probe artifact) lets the candidate
     through to the next stage.
"""
from __future__ import annotations

import hashlib
from typing import Any

from exp.fcea.control import rq4b as rqb


def revision_hash(contents: str | None) -> str:
    """Frozen revision identity (R3): sha256 over the CRLF-normalized,
    fence-stripped contents — exactly the bytes run_write persists."""
    body = (contents or "").replace("\r\n", "\n")
    if body.startswith("```"):
        body = body.split("\n", 1)[-1]
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3]
    return hashlib.sha256((body.strip() + "\n").encode("utf-8")).hexdigest()


class AcceptanceGate:
    """Per-episode acceptance state: revision provenance + counters.

    Exists only for deurq_baseenv_v2 (E3-new) and deurq_final (E4).
    `rejected` maps revision_hash -> gate that rejected it ("z3" | "z4");
    marks are cleared per revision (a NEW hash is a new candidate).
    """

    def __init__(self) -> None:
        self.rejected: dict[str, str] = {}
        self.z3_reject_events = 0
        self.z4_reject_events = 0
        self.z4_final_boundary_rejects = 0
        self.gate_rejected_before_salvage = 0
        self.nosubmit_reasons: list[str] = []
        self.last_nosubmit_reason: str | None = None

    def mark_rejected(self, chash: str, gate: str) -> None:
        self.rejected[chash] = gate
        if gate == "z3":
            self.z3_reject_events += 1
        elif gate == "z4":
            self.z4_reject_events += 1

    def rejection_gate(self, chash: str) -> str | None:
        return self.rejected.get(chash)

    def block_salvage(self, reason: str) -> None:
        """Frozen R2: the salvage slot is consumed and recorded as NoSubmit."""
        self.gate_rejected_before_salvage += 1
        self.nosubmit_reasons.append(reason)
        self.last_nosubmit_reason = reason

    def stats(self) -> dict[str, Any]:
        return {
            "z3_reject_events": self.z3_reject_events,
            "z4_reject_events": self.z4_reject_events,
            "z4_final_boundary_rejects": self.z4_final_boundary_rejects,
            "gate_rejected_before_salvage": self.gate_rejected_before_salvage,
            "nosubmit_reasons": list(self.nosubmit_reasons),
        }


class Z4Gate(rqb.TraceGateV2):
    """E4 semantic alignment gate: the frozen A16 v2 machinery with the
    E4 armed lifecycle (protocol freeze 2026-10-01 §6):

      - informative signature appears  -> armed (expectation recorded)
      - armed persists across Write    -> unchanged from v2 (violation
        accounting + verbatim re-injection; Z3 rejections never discharge)
      - a NEW signature REPLACES the previous armed expectation
        (single-slot; v2 accumulated a dict — E4 reads one expectation)
      - discharge: L3 model trace-probe round (v2 rule) OR L2 probe verdict
        "passed" (the revised artifact satisfies the expectation)
      - shot end: armed state is cleared (new_shot)

    Counters added on top of the v2 tally: armed_count, replaces,
    deferred_l1 (arm-now/probe-later when a Z3 contract gap co-triggers at
    the same boundary), resumed_l1, l2_discharges, rejections_after_defer.
    """

    def __init__(self) -> None:
        super().__init__()
        self.armed_sig: str | None = None
        self.armed_count = 0
        self.replaces = 0
        self.deferred_l1 = 0
        self.resumed_l1 = 0
        self.l2_discharges = 0
        self.l3_discharges = 0
        self.official_discharges = 0
        self.pending_l1 = False

    # ---- lifecycle ---------------------------------------------------------
    def on_failure(self, msg: str | None) -> str | None:
        """Arm on informative signature; single-slot replace. Returns the
        frozen A1 contract text when the expectation is NEW (injection is
        the caller's concern), None when unchanged/re-armed."""
        sig = rqb.informative_signature(msg)
        if sig is None:
            return None
        body = self.body_of(msg)
        self.last_body = body
        if sig == self.armed_sig:
            return None                      # same expectation, still armed
        if self.armed_sig is not None:
            self.replaces += 1               # new signature replaces the old
        else:
            self.armed_count += 1
        self.armed_sig = sig
        self.armed_bodies = {sig: body}      # keep v2 bookkeeping coherent
        self.armed = [sig]                   # single slot (v2 list kept in
                                             # sync for the inherited hooks)
        self.injections += 1
        return rqb.trace_contract(body)

    def arm_silent(self, msg: str | None) -> bool:
        """arm-now/probe-later: record the expectation WITHOUT returning
        injection text (the Z3 blocks own the frame). True iff newly armed."""
        sig = rqb.informative_signature(msg)
        if sig is None:
            return False
        if sig == self.armed_sig:
            return False
        self.last_body = self.body_of(msg)
        if self.armed_sig is not None:
            self.replaces += 1
        else:
            self.armed_count += 1
        self.armed_sig = sig
        self.armed_bodies = {sig: self.last_body}
        self.armed = [sig]                   # single slot (see on_failure)
        self.injections += 1
        return True

    def defer_l1(self) -> None:
        self.deferred_l1 += 1
        self.pending_l1 = True

    def resume_l1(self) -> None:
        self.resumed_l1 += 1
        self.pending_l1 = False

    def on_l2_outcome(self, outcome: str) -> None:
        """L2 tri-state bookkeeping + frozen discharge rule: a "passed"
        verdict satisfies the armed expectation (R6: success discharges)."""
        if outcome == "failed":
            self.l2_rejects += 1
            self.l2_rejects_this_shot += 1
        elif outcome == "indeterminate":
            self.l2_indeterminate += 1
        elif outcome == "passed":
            self.l2_passthrough += 1
            self.discharge("l2")

    def discharge(self, channel: str) -> None:
        if self.armed_sig is None:
            return
        if channel == "l2":
            self.l2_discharges += 1
        elif channel == "l3":
            self.l3_discharges += 1
        elif channel == "official":
            self.official_discharges += 1
        self.armed_sig = None
        self.armed_bodies.clear()
        self.armed.clear()

    def on_probe_round(self, kinds: list[str]) -> bool:
        """L3 channel: a kind="trace" round discharges the armed expectation."""
        if "trace" in [k for k in kinds if k] and self.armed_sig is not None:
            self.probe_rounds_trace += 1
            self.discharge("l3")
            return True
        return False

    def new_shot(self) -> None:
        """Shot boundary (frozen §6, interpretation decision 2026-10-01):
        the PER-SHOT reject cap resets; the armed expectation and the
        pending-L1 flag PERSIST. Rationale: arming happens at shot-end
        failure boundaries while the responding revision is evaluated in
        the NEXT shot — a literal shot-end wipe would make the L2 gate
        unreachable and contradict "armed persists until a successful
        revision discharges it"."""
        self.l2_rejects_this_shot = 0

    def stats(self) -> dict[str, Any]:
        out = super().stats()
        out.update({
            "armed_final": self.armed_sig is not None,
            "armed_sig_final": self.armed_sig,
            "armed_count": self.armed_count,
            "replaces": self.replaces,
            "deferred_l1": self.deferred_l1,
            "resumed_l1": self.resumed_l1,
            "l2_discharges": self.l2_discharges,
            "l3_discharges": self.l3_discharges,
            "official_discharges": self.official_discharges,
        })
        return out


def salvage_decision(accept: AcceptanceGate, chash: str, *,
                     preflight_failed: bool, z4_rejected: bool) -> tuple[bool, str | None]:
    """Frozen R2/R3 decision at the end-of-shot salvage boundary.

    Returns (salvage_proceeds, nosubmit_reason). A blocked salvage consumes
    the official slot with a NoSubmit record (the caller owns the slot
    bookkeeping); reason precedence: previously-rejected revision > fresh
    Z3 failure > fresh Z4 rejection.
    """
    prev = accept.rejection_gate(chash)
    if prev is not None:
        return False, f"revision_rejected_by_{prev}"
    if preflight_failed:
        return False, "z3_gate_failed_at_salvage"
    if z4_rejected:
        return False, "z4_gate_rejected_at_salvage"
    return True, None
