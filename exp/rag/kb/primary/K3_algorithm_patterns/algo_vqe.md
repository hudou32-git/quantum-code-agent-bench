# VQE / variational expectation

```text
card_id: k3_vqe
framework: qiskit
knowledge_layer: K3
common_set_map: algo_10
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_algo_tut_02_vqe;qiskit_docs_vqe_spin;qiskit_tb_app_vqe
```

## Algorithm Goal

Approximate the ground-state energy of a Hamiltonian by optimizing a parameterized ansatz.

## Quantum Principle

Variational theorem: minimize ⟨ψ(θ)|H|ψ(θ)⟩ over θ using a classical optimizer + quantum expectation estimates.

## Circuit Structure

Ansatz U(θ)|0⟩ → estimate Pauli/SparsePauliOp expectations (Estimator) → optimizer updates θ.

## Required Operations

Parameterized ansatz (`n_local` / `efficient_su2`), Estimator primitive, classical optimizer.

## Framework Mapping (Qiskit)

Algorithm Tutorials: `VQE(estimator, ansatz, optimizer)` with `StatevectorEstimator`. IBM docs *spin-chain VQE*: hand-rolled cost with `EstimatorV2`. Textbook applications: *VQE Molecules*.

## Common Semantic Pitfalls

- Observables not aligned with transpiled layout (`apply_layout`).
- Mixing Sampler counts with Estimator expectations incorrectly.
- Ansatz qubit count ≠ Hamiltonian qubits.

## Minimal Generic Fragment

```python
# Pattern from qiskit-algorithms VQE tutorial (2.x primitives).
from qiskit.circuit.library import n_local
from qiskit.primitives import StatevectorEstimator
from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import COBYLA

estimator = StatevectorEstimator()
ansatz = n_local(2, rotation_blocks="ry", entanglement_blocks="cz")
vqe = VQE(estimator, ansatz, COBYLA(maxiter=80))
# result = vqe.compute_minimum_eigenvalue(operator=H)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_algo_tut_02_vqe` | Algorithm Tutorials *Advanced VQE Options* |
| `qiskit_docs_vqe_spin` | IBM docs *spin-chain VQE* |
| `qiskit_tb_app_vqe` | Textbook *VQE Molecules* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
