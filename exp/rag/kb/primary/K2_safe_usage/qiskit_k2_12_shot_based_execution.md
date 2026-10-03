# Qiskit K2 — Shot-based execution (Sampler)

```text
recipe_id: qiskit_k2_12
framework: qiskit
topic: shot_based_execution
relevant_api: Sampler, shots, counts
source_ids: qiskit.primitives Sampler interfaces
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Sample measurement outcomes with a finite shot budget.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when the result must be counts / bitstrings rather than exact amplitudes.

## Minimal correct usage

### Concept
1. Build a circuit that **includes** measurements (or follow Sampler pubs that define measurements).
2. Choose a Sampler primitive (reference / statevector / backend-based depending on stack).
3. Set `shots` appropriately; read counts or bitarrays from the result container for your Qiskit version.

Exact `Statevector` inspection is a different stack — do not expect Sampler APIs when returning a pure `Statevector`.

## Common pitfalls

- Missing measurements on a Sampler path.
- Misreading result containers across Sampler V1/V2.
- Using too few shots for rare events.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`shot_based_execution`, `qiskit_k2`, `qiskit`
