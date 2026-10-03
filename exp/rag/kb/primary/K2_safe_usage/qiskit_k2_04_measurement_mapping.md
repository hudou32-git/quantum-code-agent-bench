# Qiskit K2 — Measurement and classical mapping

```text
recipe_id: qiskit_k2_04
framework: qiskit
topic: measurement_mapping
relevant_api: measure, measure_all
source_ids: qiskit.circuit.QuantumCircuit.measure; QuantumCircuit.measure_all
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Map qubits to classical bits explicitly and consistently.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use whenever shot-based results or classical registers are required.

## Minimal correct usage

### Explicit mapping
```python
from qiskit import QuantumCircuit
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure(0, 0)
qc.measure(1, 1)
```

### measure_all
`measure_all()` adds classical bits if needed and measures every qubit. Prefer explicit `measure` when bit indices matter.

## Common pitfalls

- Measuring before entanglement/oracle completes.
- q→c permutation errors (`measure(0,1)` vs intended).
- Calling `measure_all()` when a partial measurement was required.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`measurement_mapping`, `qiskit_k2`, `qiskit`
