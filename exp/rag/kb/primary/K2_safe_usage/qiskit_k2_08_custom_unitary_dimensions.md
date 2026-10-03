# Qiskit K2 — Custom unitaries and dimensions

```text
recipe_id: qiskit_k2_08
framework: qiskit
topic: custom_unitary_dimensions
relevant_api: UnitaryGate, Operator
source_ids: qiskit.circuit.library.UnitaryGate; qiskit.quantum_info.Operator
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Attach a dense unitary with the correct Hilbert-space dimension.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when synthesizing an explicit matrix onto n qubits.

## Minimal correct usage

```python
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate

U = np.eye(4, dtype=complex)  # must be 2^n x 2^n
gate = UnitaryGate(U)
qc = QuantumCircuit(2)
qc.append(gate, [0, 1])
```

`Operator` from `qiskit.quantum_info` is useful for equivalence checks (`equiv`) and matrix conversion; keep matrix size consistent with qubit count.

## Common pitfalls

- Passing a non-power-of-two matrix.
- Appending onto the wrong qubit list length.
- Ignoring global-phase vs relative-phase distinctions in comparisons.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`custom_unitary_dimensions`, `qiskit_k2`, `qiskit`
