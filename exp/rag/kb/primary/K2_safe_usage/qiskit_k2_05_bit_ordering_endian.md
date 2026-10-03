# Qiskit K2 — Bit ordering and endianness

```text
recipe_id: qiskit_k2_05
framework: qiskit
topic: bit_ordering_endian
relevant_api: Statevector indexing, counts bitstrings
source_ids: qiskit.quantum_info.Statevector; result counts conventions
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Interpret bitstrings and Statevector indices under Qiskit’s little-endian convention.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when translating textbook (MSB-left) algorithms or reading Sampler/counts keys.

## Minimal correct usage

### Rules of thumb
- In Qiskit, qubit 0 is the **least significant** bit in `Statevector` integer indices.
- Counts bitstrings are typically labeled with qubit 0 on the **right** (little-endian string).
- When a paper writes `s = 011` with MSB on the left, map carefully onto `qc` indices before wiring oracles.

## Common pitfalls

- Reversing only printed classical strings, not the quantum wiring.
- Off-by-one when implementing bit-reversal SWAP networks after QFT.
- Mixing big-endian oracle layouts with little-endian preparation.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`bit_ordering_endian`, `qiskit_k2`, `qiskit`
