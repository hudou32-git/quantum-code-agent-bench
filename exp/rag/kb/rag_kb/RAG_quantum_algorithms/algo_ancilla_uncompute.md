# Ancilla hygiene

## Goal
Workspace qubits must return to `|0>` (or the promised clean state) after the computation.

## Pattern
1. Compute into ancilla.
2. Use ancilla to control a phase/bit operation on the main register.
3. **Uncompute** the ancilla with the inverse of step 1.

## Common bugs
- Leaving garbage entanglement — main register looks almost right; joint state fails.
- Measuring / resetting ancilla mid-algorithm when coherence is still required.
- Wrong number of ancillas vs prompt.
