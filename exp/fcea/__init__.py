"""FCEA: Failure-Conditioned Evidence Allocation (RQ4 phase 1).

Keeps the Batch-EQPA protocol (exp/evidence_eqpa, itself byte-parity with
e4_eqpa_40960) and adds ONE treatment: after a failed official Eval, a frozen
QHE-derived evidence utility prior is turned into a soft evidence-priority
notice. Variants:
  global (V2) — one pooled priority for every failure
  fcond  (V3) — priority conditioned on the observed failure context

The prior is soft guidance only: the model stays free to pick other evidence.
NoSubmit failures get no routing (phase-1 design). No progress/stagnation
module in phase 1. Tags: rq4_fcea* only; exp/eqpa and exp/evidence_eqpa are
never mutated.
"""
