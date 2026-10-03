# Qiskit K2 — Registers vs integer qubit indices

```text
recipe_id: qiskit_k2_20
framework: qiskit
topic: registers_vs_integers
relevant_api: QuantumRegister indexing vs ints
source_ids: QuantumCircuit gate APIs
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Address qubits either by integer positions or register elements consistently.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when combining named registers with numeric gate calls.

## Minimal correct usage

```python
from qiskit import QuantumCircuit, QuantumRegister
qr = QuantumRegister(2, "q")
qc = QuantumCircuit(qr)
qc.h(qr[0])
qc.cx(qr[0], qr[1])
# equivalent integers if qr is the only register starting at 0:
# qc.h(0); qc.cx(0, 1)
```

When multiple registers exist, integer indices are global within the circuit — prefer register elements to avoid off-by-register errors.

## Common pitfalls

- Using integers that silently refer to another register’s qubits.
- Slicing registers incorrectly (`qr[0:2]` semantics).
- Passing classical bits where qubits are required.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`registers_vs_integers`, `qiskit_k2`, `qiskit`
