# Generic state preparation

```text
card_id: k3_state_preparation_generic
framework: qiskit
knowledge_layer: K3
common_set_map: algo_02
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_defining;qiskit_tb_entangled;qiskit_algo_tut_02_vqe
```

## Algorithm Goal

Prepare a target state |ψ⟩ on n qubits from |0⟩^⊗n (exact or approximate).

## Quantum Principle

Any state has a unitary preparation; practical circuits use product rotations, entanglement blocks, or `initialize`/`StatePreparation`.

## Circuit Structure

Choose encoding: computational basis X/H; amplitudes via `initialize`; variational via `n_local`/`efficient_su2`; entangled motifs (Bell/GHZ/W).

## Required Operations

Single-qubit rotations, entangling gates, optional `QuantumCircuit.initialize` / library StatePreparation.

## Framework Mapping (Qiskit)

Textbook *Defining Quantum Circuits* discusses circuit construction / VQE example. Algorithm/VQE tutorials use `n_local`. Cross-link K2 `qiskit_k2_07_state_preparation_basics`.

## Common Semantic Pitfalls

- Normalize amplitudes incorrectly.
- Endianness when loading classical amplitude vectors.
- Confusing state prep with measurement post-selection.

## Minimal Generic Fragment

```python
from qiskit import QuantumCircuit
from qiskit.circuit.library import n_local

qc = QuantumCircuit(2)
qc.initialize([1, 0, 0, 1], [0, 1])  # unnormalized OK; Qiskit normalizes
# or variational: ansatz = n_local(2, "ry", "cz", reps=1)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_defining` | Textbook *Quantum Circuits* / VQE example section |
| `qiskit_tb_entangled` | Entangled-state prep motifs |
| `qiskit_algo_tut_02_vqe` | `n_local` ansatz prep |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
