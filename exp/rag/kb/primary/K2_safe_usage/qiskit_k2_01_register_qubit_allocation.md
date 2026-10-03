# Qiskit K2 — Registers and qubit allocation

```text
recipe_id: qiskit_k2_01
framework: qiskit
topic: register_qubit_allocation
relevant_api: QuantumRegister, ClassicalRegister, QuantumCircuit
source_ids: qiskit.circuit.QuantumRegister; qiskit.circuit.ClassicalRegister; qiskit.circuit.QuantumCircuit
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Allocate qubits and classical bits with explicit registers or integer widths.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when a program needs named registers, separate classical storage, or clear ownership of qubit ranges.

## Minimal correct usage

### Integer-width circuit
```python
from qiskit import QuantumCircuit
qc = QuantumCircuit(3, 3)  # 3 qubits, 3 classical bits
```

### Named registers
```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
qr = QuantumRegister(2, "q")
cr = ClassicalRegister(2, "c")
qc = QuantumCircuit(qr, cr)
```

Gates address qubits by index within the circuit or by `QuantumRegister` elements (`qr[0]`).

## Common pitfalls

- Mixing register objects from different circuits.
- Creating classical bits only at measure time when a fixed width was required up front.
- Assuming register *names* affect little-endian Statevector indexing (they do not).

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`register_qubit_allocation`, `qiskit_k2`, `qiskit`
