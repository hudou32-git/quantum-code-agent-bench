# Bernstein–Vazirani

```text
card_id: k3_bv
framework: qiskit
knowledge_layer: K3
common_set_map: algo_05
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_bv;qiskit_tb_phase_kickback
```

## Algorithm Goal

Learn hidden bitstring s with one query to an oracle for f(x)=s·x (mod 2).

## Quantum Principle

Hadamard sandwich around a phase/bit oracle extracts s via interference (phase kickback on a |−⟩ ancilla).

## Circuit Structure

1. Prepare data in |+…+⟩; put ancilla in |−⟩ (`h` then `z`, or `x` then `h`).
2. Apply inner-product oracle: for each bit of s that is 1, CX from that data qubit onto the ancilla.
3. Hadamards on data; measure data register.

## Required Operations

H, Z/X (ancilla), CX per bits of s, measure.

## Framework Mapping (Qiskit)

Textbook BV reverses the classical string (`s = s[::-1]`) so string index 0 matches Qiskit qubit 0. Identity on `s_i=0` bits is optional (omit no-ops in 2.4.1).

## Common Semantic Pitfalls

- Bit oracle vs phase-oracle mismatch.
- Endianness when mapping s onto qubits (forgetting `s[::-1]`).
- Leaving ancillas entangled when a clean ancilla was required.

## Minimal Generic Fragment

```python
# Pattern from Qiskit Textbook Bernstein–Vazirani chapter (cell constructing bv_circuit).
# Adapted comments for Qiskit 2.4.1 (no Aer/assemble).
from qiskit import QuantumCircuit

n = 3
s = "011"  # hidden string in textbook MSB-left notation

bv = QuantumCircuit(n + 1, n)
bv.h(n)
bv.z(n)  # ancilla |->
for i in range(n):
    bv.h(i)

s_le = s[::-1]  # reverse to fit Qiskit qubit ordering
for q in range(n):
    if s_le[q] == "1":
        bv.cx(q, n)

for i in range(n):
    bv.h(i)
    bv.measure(i, i)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_bv` | Qiskit Textbook (OSS) *Bernstein-Vazirani Algorithm* |
| `qiskit_tb_phase_kickback` | Textbook *Phase Kickback* (oracle phase mechanism) |

Provenance excerpt: `qiskit/sources/k3_official_excerpts/excerpt_textbook_bv_circuit.py`.  
Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
