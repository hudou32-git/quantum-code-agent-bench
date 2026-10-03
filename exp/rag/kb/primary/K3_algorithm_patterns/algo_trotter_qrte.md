# Trotterized quantum real-time evolution

```text
card_id: k3_trotter_qrte
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_algo_tut_13_trotter
```

## Algorithm Goal

Approximate |ψ(t)⟩=e^{-iHt}|ψ(0)⟩ by product formulas (Trotter–Suzuki).

## Quantum Principle

Split H=Σ H_j and replace the exponential by ordered short-time factors.

## Circuit Structure

For each Trotter step: apply e^{-i H_j Δt} factors (Pauli evolutions) for all j; repeat.

## Required Operations

Pauli evolution / `PauliEvolutionGate`, time-step loop, optional observables.

## Framework Mapping (Qiskit)

Algorithm Tutorials `13_trotterQRTE.ipynb`.

## Common Semantic Pitfalls

Too-large Δt; wrong operator ordering; ignoring Trotter error vs depth.

## Minimal Generic Fragment

```python
# Conceptual: for step in range(n_steps): apply product_formula(H, dt)
# See qiskit-algorithms docs/tutorials/13_trotterQRTE.ipynb
```

## Sources

| `qiskit_algo_tut_13_trotter` | Algorithm Tutorials *Trotter QRTE* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
