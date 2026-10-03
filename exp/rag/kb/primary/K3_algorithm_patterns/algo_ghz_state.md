# GHZ state

```text
card_id: k3_ghz
framework: qiskit
knowledge_layer: K3
common_set_map: algo_01 (Bell / GHZ)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_entangled
```

## Algorithm Goal

Prepare an n-qubit GHZ⁺ state (|0…0⟩+|1…1⟩)/√2.

## Quantum Principle

One qubit in superposition fans out entanglement to all others via CNOTs (Bell is the n=2 case from the Textbook entangled-states chapter).

## Circuit Structure

1. H on qubit 0.
2. For each i=1..n-1: CX(0, i) (star topology) — or an equivalent CX chain.
3. Avoid unintended relative phases unless GHZ⁻ is required.

## Required Operations

H, CX (fan-out or chain).

## Framework Mapping (Qiskit)

`QuantumCircuit(n)`; `h(0)`; loop `cx(0, i)`. Same H+CX motif as Textbook Bell, extended by fan-out.

## Common Semantic Pitfalls

- CX direction that breaks GHZ support.
- Accidental Z phases → GHZ⁻.
- Mid-circuit measure/reset destroying coherence while leaving 50/50 populations.

## Minimal Generic Fragment

```python
# GHZ as n-qubit extension of Textbook Bell (H then CX fan-out).
from qiskit import QuantumCircuit

n = 3
qc = QuantumCircuit(n)
qc.h(0)
for i in range(1, n):
    qc.cx(0, i)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_entangled` | Qiskit Textbook (OSS) *Multiple Qubits & Entangled States* (Bell motif; GHZ = fan-out) |

Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
