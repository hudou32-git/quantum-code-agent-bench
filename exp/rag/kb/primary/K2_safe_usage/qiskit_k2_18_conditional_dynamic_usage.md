# Qiskit K2 — Conditional / dynamic circuits

```text
recipe_id: qiskit_k2_18
framework: qiskit
topic: conditional_dynamic_usage
relevant_api: if_test, classical conditions (version-aware)
source_ids: qiskit.circuit.QuantumCircuit control-flow APIs
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Apply classical feed-forward only with APIs supported by the installed Qiskit version.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when mid-circuit measurement must control later gates.

## Minimal correct usage

### Guidance
Qiskit 2.x prefers structured control-flow (`if_test` / control-flow boxes) over legacy `c_if` patterns on instruction sets. Check the installed version’s docs before writing classical conditions.

Dynamic circuits generally require measurement results available at runtime; local statevector-only paths may not support the same control flow.

## Common pitfalls

- Copying Qiskit 0.x `c_if` snippets into 2.x codebases.
- Conditioning on classical bits that were never measured.
- Assuming all simulators support identical dynamic features.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`conditional_dynamic_usage`, `qiskit_k2`, `qiskit`
