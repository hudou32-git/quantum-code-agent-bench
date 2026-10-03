# Bell state Φ⁺

```text
card_id: k3_bell_phi_plus
framework: qiskit
knowledge_layer: K3
common_set_map: algo_01 (Bell / GHZ)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_entangled
```

## Algorithm Goal

Prepare the two-qubit Bell state (|00⟩+|11⟩)/√2 (Φ⁺).

## Quantum Principle

A Hadamard creates superposition; a CNOT entangles the second qubit with the first.

## Circuit Structure

1. H on qubit 0.
2. CX with control 0 and target 1.
3. Optional single-qubit Paulis yield other Bell labels (Φ⁻, Ψ±).

## Required Operations

H, CX; optional Z/X for related Bell states.

## Framework Mapping (Qiskit)

`QuantumCircuit(2)` then `h(0)`, `cx(0,1)` — same construction as the Textbook *Multiple Qubits & Entangled States* chapter. Inspect with `Statevector` if exact amplitudes are needed.

## Common Semantic Pitfalls

- Swapped CX control/target.
- Product state `|+⟩|0⟩` (missing CX).
- Extra relative phase changing the Bell label while leaving computational probabilities unchanged.

## Minimal Generic Fragment

```python
# From Qiskit Textbook: Multiple Qubits & Entangled States (Bell construction).
from qiskit import QuantumCircuit

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_entangled` | Qiskit Textbook (OSS) *Multiple Qubits & Entangled States* |

Excerpt: `qiskit/sources/k3_official_excerpts/excerpt_textbook_bell_phi_plus.py`.  
Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
