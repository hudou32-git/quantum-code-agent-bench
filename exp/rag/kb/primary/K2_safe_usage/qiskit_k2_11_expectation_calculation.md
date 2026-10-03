# Qiskit K2 — Expectation values

```text
recipe_id: qiskit_k2_11
framework: qiskit
topic: expectation_calculation
relevant_api: SparsePauliOp, Estimator, Pauli
source_ids: qiskit.quantum_info.SparsePauliOp; qiskit.primitives Estimator interfaces
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Estimate ⟨ψ|O|ψ⟩ for Pauli / SparsePauli observables.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use for energy-like observables and Pauli strings; prefer Estimator primitives over manual sampling when available.

## Minimal correct usage

### Observable
```python
from qiskit.quantum_info import SparsePauliOp
obs = SparsePauliOp.from_list([("ZZ", 1.0), ("XI", 0.5)])
```

### Estimator (concept)
Bind a parameterized circuit, then run an Estimator primitive (`run` / pub-style APIs depending on Qiskit version) with the observable. Exact local alternatives include `Statevector` expectations for small systems.

## Common pitfalls

- Pauli string length ≠ qubit count.
- Mixing Estimator pubs with Sampler bitstring workflows.
- Forgetting to bind parameters before estimation.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`expectation_calculation`, `qiskit_k2`, `qiskit`
