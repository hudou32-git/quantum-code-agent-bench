# Quantum key distribution (BB84-style)

```text
card_id: k3_qkd_bb84
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_qkd
```

## Algorithm Goal

Establish a shared secret key by preparing/measuring qubits in conjugate bases (BB84).

## Quantum Principle

Measuring in the wrong basis randomizes outcomes; eavesdropping introduces detectable errors.

## Circuit Structure

Alice prepares random bits in random bases (Z/X); Bob measures in random bases; sifting keeps matching-basis bits; estimate QBER.

## Required Operations

H (basis change), X (bit encode), measure; classical sifting post-process.

## Framework Mapping (Qiskit)

Textbook *Quantum Key Distribution* simulates Alice/Bob circuits and compares bitstrings.

## Common Semantic Pitfalls

Forgetting basis sifting; treating all shots as key bits; wrong H placement for X-basis.

## Minimal Generic Fragment

```python
# BB84 one-shot encode/measure sketch (Textbook QKD).
from qiskit import QuantumCircuit
qc = QuantumCircuit(1, 1)
# Alice: if bit and Z-basis -> X; if X-basis -> H after encode
# Bob: if X-basis measure -> H then measure
qc.measure(0, 0)
```

## Sources

| `qiskit_tb_qkd` | Textbook *Quantum Key Distribution* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
