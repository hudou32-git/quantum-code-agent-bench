# QAOA

```text
card_id: k3_qaoa
framework: qiskit
knowledge_layer: K3
common_set_map: algo_11
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_algo_tut_05_qaoa;qiskit_docs_qaoa;qiskit_tb_app_qaoa
```

## Algorithm Goal

Approximate combinatorial optimization solutions via alternating cost/mixer unitaries.

## Quantum Principle

QAOA prepares |β,γ⟩ = (B_β C_γ)^p |+⟩^⊗n and optimizes ⟨C⟩ (or samples bitstrings).

## Circuit Structure

Map problem → cost Hamiltonian (e.g. MaxCut ZZ terms) → `QAOAAnsatz` / QAOA algorithm with p layers → optimize → sample.

## Required Operations

Problem Hamiltonian as `SparsePauliOp`, mixer (usually RX), parameterized QAOA circuit, Sampler/Estimator.

## Framework Mapping (Qiskit)

Docs tutorial: `QAOAAnsatz(cost_operator=..., reps=p)`. Algorithm Tutorials: `QAOA(sampler, optimizer, reps=p)`. Textbook applications: *QAOA*.

## Common Semantic Pitfalls

- Wrong sign/weights on cost Pauli terms.
- Measuring expectation without layout-aware observables after transpile.
- Confusing QAOA bitstring endianness when decoding cuts.

## Minimal Generic Fragment

```python
# Pattern from IBM Quantum docs QAOA tutorial (circuit.library.QAOAAnsatz).
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp

cost = SparsePauliOp.from_sparse_list([("ZZ", [0, 1], 1.0)], num_qubits=2)
circuit = QAOAAnsatz(cost_operator=cost, reps=2)
circuit.measure_all()
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_docs_qaoa` | IBM docs *Quantum Approximate Optimization Algorithm* |
| `qiskit_algo_tut_05_qaoa` | Algorithm Tutorials *QAOA* |
| `qiskit_tb_app_qaoa` | Textbook applications *QAOA* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
