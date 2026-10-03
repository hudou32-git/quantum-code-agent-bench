# Qiskit K2 — Circuit inversion

```text
recipe_id: qiskit_k2_17
framework: qiskit
topic: circuit_inversion
relevant_api: inverse, global phase
source_ids: QuantumCircuit.inverse
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Invert a unitary circuit while understanding global-phase caveats.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use for uncomputation and reverse evolution of unitary blocks.

## Minimal correct usage

```python
from qiskit import QuantumCircuit
fwd = QuantumCircuit(1)
fwd.s(0)
rev = fwd.inverse()
```

If the block contained irreversible ops (measure/reset/initialize), inversion may fail or be meaningless. Global phase differences can be irrelevant physically but may matter for exact matrix equality tests.

## Common pitfalls

- Inverting measured circuits.
- Forgetting that inverse gate order is reversed.
- Confusing global phase with relative phase.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`circuit_inversion`, `qiskit_k2`, `qiskit`
