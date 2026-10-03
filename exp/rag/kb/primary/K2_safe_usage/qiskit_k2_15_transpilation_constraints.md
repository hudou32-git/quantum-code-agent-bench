# Qiskit K2 — Transpilation constraints

```text
recipe_id: qiskit_k2_15
framework: qiskit
topic: transpilation_constraints
relevant_api: transpile, basis_gates, coupling_map, Target
source_ids: qiskit.compiler.transpile; preset pass managers
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Compile a circuit to a backend basis and connectivity.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use before running on hardware-constrained simulators/devices.

## Minimal correct usage

```python
from qiskit import QuantumCircuit, transpile

qc = QuantumCircuit(2)
qc.cx(0, 1)
# Example shape — supply a real backend or Target in practice:
# tqc = transpile(qc, backend=backend, optimization_level=1)
```

Constraints typically include basis gates, coupling map / Target, and layout/routing. Preset pass managers (`generate_preset_pass_manager`) bundle common flows.

## Common pitfalls

- Transpiling after assuming unrestricted all-to-all connectivity.
- Comparing pre- and post-transpile unitary without accounting for layout.
- Over-optimizing away barriers needed only for visualization.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`transpilation_constraints`, `qiskit_k2`, `qiskit`
