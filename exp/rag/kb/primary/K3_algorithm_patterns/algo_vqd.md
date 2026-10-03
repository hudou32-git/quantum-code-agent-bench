# Variational Quantum Deflation (VQD)

```text
card_id: k3_vqd
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_algo_tut_04_vqd
```

## Algorithm Goal

Find excited eigenstates by penalizing overlap with previously found states.

## Quantum Principle

Augment the VQE cost with Σ β_k |⟨ψ_k|ψ(θ)⟩|^2 penalties (deflation).

## Circuit Structure

Same ansatz family as VQE; add overlap estimation between current and prior optima; optimize.

## Required Operations

VQE stack + overlap/swap-test or state fidelity estimates; optimizer.

## Framework Mapping (Qiskit)

Algorithm Tutorials `04_vqd.ipynb` (`VQD` class).

## Common Semantic Pitfalls

Too-small penalty weights; reusing the same initial point without diversity.

## Minimal Generic Fragment

```python
# See qiskit-algorithms docs/tutorials/04_vqd.ipynb for VQD(estimator, ansatz, optimizer, k=...).
```

## Sources

| `qiskit_algo_tut_04_vqd` | Algorithm Tutorials *VQD* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
