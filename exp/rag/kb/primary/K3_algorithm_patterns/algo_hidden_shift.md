# Hidden shift problem

```text
card_id: k3_hidden_shift
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_hidden_shift
```

## Algorithm Goal

Learn a hidden shift s given oracles for a bent Boolean function and its shifted version.

## Quantum Principle

Quantum queries + interference extract the shift faster than classical query complexity allows for certain function classes.

## Circuit Structure

Prepare superposition; query oracles for f and shifted f; apply Fourier-type / Hadamard layer; measure to learn s.

## Required Operations

Oracle unitaries for bent/shifted functions, H layers, measure.

## Framework Mapping (Qiskit)

Textbook *Hidden Shift Problem* notebook — implement oracles as circuits and compose.

## Common Semantic Pitfalls

Classical branching instead of unitary oracles; endianness of recovered s.

## Minimal Generic Fragment

```python
# Pattern: H⊗n — oracle_f / oracle_shifted — H⊗n — measure (see Textbook Hidden Shift).
from qiskit import QuantumCircuit
n = 4
qc = QuantumCircuit(n)
qc.h(range(n))
# qc.compose(oracle_f, inplace=True)
# qc.compose(oracle_shifted, inplace=True)
qc.h(range(n))
qc.measure_all()
```

## Sources

| `qiskit_tb_hidden_shift` | Textbook *Hidden Shift Problem* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
