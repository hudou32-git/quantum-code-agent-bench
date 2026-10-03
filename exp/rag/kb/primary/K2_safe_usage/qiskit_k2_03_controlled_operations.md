# Qiskit K2 — Controlled operations

```text
recipe_id: qiskit_k2_03
framework: qiskit
topic: controlled_operations
relevant_api: QuantumCircuit.cx, control, controlled gates
source_ids: qiskit.circuit.QuantumCircuit.cx; qiskit.circuit.ControlledGate
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Apply multi-qubit controlled unitaries with correct control/target polarity.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use for entangling gates, oracles, and multi-controlled phase/marking patterns.

## Minimal correct usage

### Built-in CX
```python
from qiskit import QuantumCircuit
qc = QuantumCircuit(2)
qc.cx(0, 1)  # control=0, target=1
```

### Controlled gate via .control()
Many gates expose `.control(num_ctrl_qubits=...)` then `append`/`compose` onto a circuit. Match the qubit order expected by the controlled instruction (controls then targets unless documented otherwise).

## Common pitfalls

- Swapping control and target.
- Open controls (X-wrap pattern) forgotten when the marked bitstring is not all-ones.
- Building classical if/else instead of a unitary controlled gate.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`controlled_operations`, `qiskit_k2`, `qiskit`
