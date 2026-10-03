# Shor's algorithm (period finding)

```text
card_id: k3_shor
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm (not in 12-topic freeze)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_shor;qiskit_docs_shor;qiskit_lib_qft_241
```

## Algorithm Goal

Find the period r of f(x)=a^x mod N to factor N (order-finding reduction).

## Quantum Principle

Phase estimation on modular-multiplication unitaries yields r via continued fractions.

## Circuit Structure

Counting register H; controlled modular multiplications a^(2^k) mod N; IQFT; classical continued-fraction post-processing.

## Required Operations

Modular multiply unitaries, IQFT/`QFT.inverse()`, measure, classical gcd/continued fractions.

## Framework Mapping (Qiskit)

Textbook *Shor's Algorithm* (`c_amod15`, `qft_dagger`). IBM docs *Shor's algorithm* tutorial uses `circuit.library.QFT` and modular multiply gates.

## Common Semantic Pitfalls

- Wrong modular unitary / register width.
- Mis-parsing the measured phase into r.
- Skipping coprimality checks on a.

## Minimal Generic Fragment

```python
# High-level shape from Textbook Shor / docs Shor (counting H, controlled modular U, IQFT).
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT

n_count = 8
qc = QuantumCircuit(n_count + 4, n_count)
qc.h(range(n_count))
# qc.x(n_count)  # |1> in work register (example)
# for q in range(n_count):
#     qc.append(controlled_modular_pow(a, 2**q), [q] + work_qubits)
qc.append(QFT(n_count, inverse=True), range(n_count))
qc.measure(range(n_count), range(n_count))
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_shor` | Textbook *Shor's Algorithm* |
| `qiskit_docs_shor` | IBM docs *Shor's algorithm* |
| `qiskit_lib_qft_241` | 2.4.1 `QFT` |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
