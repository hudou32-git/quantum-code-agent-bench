# Qiskit K2 — Initialize and reset pitfalls

```text
recipe_id: qiskit_k2_16
framework: qiskit
topic: initialization_reset
relevant_api: reset, initialize
source_ids: QuantumCircuit.reset; QuantumCircuit.initialize
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Use irreversible reset and state loading deliberately.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when a qubit must be recycled or loaded from amplitudes.

## Minimal correct usage

`reset` is not a unitary. Mid-circuit reset changes the semantics of later coherent interference.

`initialize` overwrites the targeted qubits’ state; it should not be interleaved casually with prior entanglement on those qubits unless that is intended.

## Common pitfalls

- Resetting an ancilla that still needed to be uncomputed unitarily.
- Double-initializing overlapping qubit sets.
- Expecting `reset` to appear in unitary Operator comparisons.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`initialization_reset`, `qiskit_k2`, `qiskit`
