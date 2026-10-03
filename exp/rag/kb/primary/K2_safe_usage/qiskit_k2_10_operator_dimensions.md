# Qiskit K2 — Operator inspection

```text
recipe_id: qiskit_k2_10
framework: qiskit
topic: operator_dimensions
relevant_api: Operator, equiv, to_matrix
source_ids: qiskit.quantum_info.Operator
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Convert circuits/gates to operators and compare them safely.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use for unitary checks, teaching equivalence, and debugging gate networks.

## Minimal correct usage

```python
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

qc = QuantumCircuit(1)
qc.x(0)
op = Operator(qc)
mat = op.data  # complex matrix
# Operator.equiv compares up to global phase by default in many workflows
```

## Common pitfalls

- Comparing operators with mismatched dimensions.
- Expecting exact array equality when only global phase differs.
- Building `Operator` after irreversible measures.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`operator_dimensions`, `qiskit_k2`, `qiskit`
