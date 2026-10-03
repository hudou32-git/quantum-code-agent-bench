# Qiskit K2 — Parameter binding

```text
recipe_id: qiskit_k2_06
framework: qiskit
topic: parameter_binding
relevant_api: Parameter, ParameterVector, assign_parameters
source_ids: qiskit.circuit.Parameter; ParameterVector; QuantumCircuit.assign_parameters
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Build parameterized circuits and bind numeric values before execution.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use for variational forms, sweeps, and any symbolic angle.

## Minimal correct usage

```python
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, ParameterVector

theta = Parameter("θ")
qc = QuantumCircuit(1)
qc.ry(theta, 0)
bound = qc.assign_parameters({theta: 0.3})

phis = ParameterVector("φ", 2)
qc2 = QuantumCircuit(2)
qc2.rx(phis[0], 0)
qc2.rz(phis[1], 1)
```

## Common pitfalls

- Executing a circuit that still contains unbound `Parameter` objects.
- Binding the wrong dict keys / vector length.
- Mutating the unbound template unintentionally when `inplace` semantics differ by call.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`parameter_binding`, `qiskit_k2`, `qiskit`
