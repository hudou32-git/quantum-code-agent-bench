# Qiskit K2 — Circuit composition (compose / append / barrier)

```text
recipe_id: qiskit_k2_02
framework: qiskit
topic: circuit_composition
relevant_api: QuantumCircuit.compose, append, barrier
source_ids: qiskit.circuit.QuantumCircuit.compose; QuantumCircuit.append; QuantumCircuit.barrier
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Combine subcircuits safely with `compose`/`append` and optional barriers for visual/logical separation.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when building oracles, modular blocks, or staged algorithms from smaller circuits.

## Minimal correct usage

### compose
```python
from qiskit import QuantumCircuit
inner = QuantumCircuit(2)
inner.h(0)
inner.cx(0, 1)
outer = QuantumCircuit(2)
outer.compose(inner, inplace=True)
# or: outer = outer.compose(inner)
```

### append
`append` adds an instruction/gate to specific qubits. Prefer `compose` for whole subcircuits.

### barrier
```python
qc.barrier()  # optional separator; usually not semantically required
```

## Common pitfalls

- Composing onto the wrong qubit map (`qubits=` mismatch).
- Forgetting `inplace=True` when expecting mutation.
- Treating `barrier` as a computational gate.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`circuit_composition`, `qiskit_k2`, `qiskit`
