# Qiskit K2 — State preparation basics

```text
recipe_id: qiskit_k2_07
framework: qiskit
topic: state_preparation_basics
relevant_api: initialize, reset, standard prep
source_ids: qiskit.circuit.QuantumCircuit.initialize; QuantumCircuit.reset; QuantumCircuit.x
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Prepare computational or arbitrary states with supported Qiskit APIs.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use for product states, basis flips, or amplitude loading via `initialize` when appropriate.

## Minimal correct usage

### Basis flip
```python
from qiskit import QuantumCircuit
qc = QuantumCircuit(1)
qc.x(0)  # |0> -> |1>
```

### reset then prepare
`reset(q)` returns a qubit toward `|0>` (non-unitary). Follow with gates/`initialize` as needed.

### initialize
`initialize(state, qubits)` can load a statevector onto qubits; dimensions must match `2**n`. Prefer gate circuits when a simple unitary prep exists.

## Common pitfalls

- `initialize` dimension mismatch.
- Using `reset` mid-algorithm when coherence was still required.
- Confusing state prep with measurement post-selection.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`state_preparation_basics`, `qiskit_k2`, `qiskit`
