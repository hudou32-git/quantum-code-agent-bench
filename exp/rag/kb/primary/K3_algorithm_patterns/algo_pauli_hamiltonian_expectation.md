# Pauli / Hamiltonian expectation patterns

```text
card_id: k3_pauli_hamiltonian_expectation
framework: qiskit
knowledge_layer: K3
common_set_map: algo_12
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_docs_qaoa;qiskit_docs_vqe_spin;qiskit_algo_tut_02_vqe
```

## Algorithm Goal

Evaluate ⟨ψ|H|ψ⟩ for H expanded as a weighted sum of Pauli strings.

## Quantum Principle

Linearity of expectation: ⟨H⟩ = Σ c_i ⟨P_i⟩ for H = Σ c_i P_i.

## Circuit Structure

Prepare |ψ⟩ (ansatz or fixed circuit); estimate each Pauli (or grouped commuting set) via Estimator; sum coefficients.

## Required Operations

`SparsePauliOp` / Pauli sum, EstimatorV2 or StatevectorEstimator, optional layout apply.

## Framework Mapping (Qiskit)

Docs QAOA builds MaxCut `SparsePauliOp.from_sparse_list`. VQE tutorials pass the operator straight to `compute_minimum_eigenvalue` / Estimator pubs.

## Common Semantic Pitfalls

- Dropping coefficients or double-counting identities.
- Forgetting `hamiltonian.apply_layout(circuit.layout)` after transpile.
- Interpreting Sampler bitstring probs as already-Pauli expectations.

## Minimal Generic Fragment

```python
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import StatevectorEstimator

H = SparsePauliOp.from_list([("ZZ", 1.0), ("XI", 0.5)])
# pub = (circuit, H, [params]); energy = estimator.run([pub]).result()[0].data.evs
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_docs_qaoa` | SparsePauliOp MaxCut construction |
| `qiskit_docs_vqe_spin` | Estimator energy loop |
| `qiskit_algo_tut_02_vqe` | VQE operator expectations |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
