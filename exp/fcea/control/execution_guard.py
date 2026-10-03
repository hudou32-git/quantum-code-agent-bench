"""deurq_base execution guards (v1, 2026-10-01): length-cut corrective retry
+ fuse, fallback artifact gate, slot salvage.

Targets the three documented execution-layer defects of the mainline stack
(docs/book/new.md §6; Shell-substrate quantification 2026-09-30):

  1. Silent length-cut resample: a 40960-token truncated draw is resampled
     with no corrective signal, and the resample can truncate too (5/11
     double burns measured on the Shell substrate). The /148 event burned
     ~0.4-0.5M output tokens because the streaming repeat guard cannot
     catch "changing but non-repeating" degeneration — the fuse here caps
     the resample spend at the episode level (the candidate fix recorded in
     the MECH-1 protocol appendix, adopted).
  2. Truncated text reaching the official fallback path: a truncated draw
     extracted via extract_module and submitted burned an official slot
     with a NameError-class残码 (qbplus/26).
  3. NoSubmit with a written-but-never-graded candidate: the attempt slot
     burns either way (official += 1), so grading the candidate converts a
     dead slot into a real measurement (10/18 Shell-substrate NoSubmit
     shots; the MECH-1 smoke /149 preflight-loop class).

Design constraints (deurq_base): every guard is a default-off flag, so all
pre-existing variants stay byte-identical. Corrective/fuse directives are
injected as plain user messages BEFORE the resample (changing the sampling
condition, not re-drawing from the same one). The fuse is episode-scoped:
after `exec_length_fuse_cap` cut events no further resample is paid for in
this episode, and each shot gets at most one hard "submit now" directive.
The salvage deliberately bypasses the MECH preflight gate: the slot is
consumed regardless, so the official grade is strictly more information
than a rejection (FAIL-OPEN by construction).

This module is a leaf: it imports nothing from the package.
"""
from __future__ import annotations

EXEC_GUARD_DEFAULTS = {
    "exec_retry_corrective": False,   # inject a corrective directive before the length resample
    "exec_length_fuse_cap": 2,        # max length-cut resamples paid per episode
    "exec_artifact_gate": False,      # truncated draws may not enter the fallback submit path
    "exec_slot_salvage": False,       # grade a written-but-unevaluated candidate at shot close
    "exec_probe_budget": False,       # BatchProbe round budget enforced at execution layer (C7)
}

# C7: execution-layer refusal when the per-shot probe budget is exhausted.
# Mirrors the controller-withdrawal refusal schema (tool message, no backend run).
PROBE_BUDGET_REFUSAL = (
    "BatchProbe inspect budget for this attempt is used ({used}/{cap} queries). "
    "Do not call BatchProbe again this attempt: Write attempt_{k}.py with your "
    "best solution and call Eval()."
)

# injected BEFORE the resample draw (corrective retry, d5 B1 semantics)
CORRECTIVE_TEXT = (
    "[execution guard] Your previous message hit the output-token limit and "
    "contained no tool call, so it was discarded. Do not restate your "
    "reasoning. In your next message call Write with the complete "
    "attempt_<current>.py module, then Eval()."
)

# injected ONCE per shot after the fuse blows (no further resamples paid)
FUSE_TEXT = (
    "[execution guard] Output-limit cuts have exceeded this episode's "
    "retry budget. No further resampling will be paid. Call Write with the "
    "complete attempt_<current>.py module and Eval() now; shorter output."
)

# injected when a truncated draw is blocked from the fallback submit path
GATE_TEXT = (
    "[execution guard] That message was truncated by the output-token "
    "limit; the partial module was discarded and NOT submitted. Call Write "
    "with the complete attempt_<current>.py module, then Eval()."
)


class LengthFuse:
    """Episode-scoped resample budget. cap <= 0 disables resampling entirely."""

    def __init__(self, cap: int):
        self.cap = max(0, int(cap))
        self.cuts = 0
        self.retries_paid = 0
        self.blown = False

    def on_cut(self) -> str:
        """Call once per length-cut draw. Returns "retry" or "blown"."""
        self.cuts += 1
        if self.blown or self.cuts > self.cap:
            self.blown = True
            return "blown"
        self.retries_paid += 1
        return "retry"

    def snapshot(self) -> dict:
        return {"cap": self.cap, "cuts": self.cuts,
                "retries_paid": self.retries_paid, "blown": self.blown}
