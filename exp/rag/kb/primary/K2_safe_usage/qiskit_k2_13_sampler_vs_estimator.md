# Qiskit K2 — Sampler vs Estimator

```text
recipe_id: qiskit_k2_13
framework: qiskit
topic: sampler_vs_estimator
relevant_api: Sampler, Estimator
source_ids: qiskit.primitives
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Choose the primitive that matches the required return type.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use Sampler for bitstrings/counts; Estimator for observable expectations.

## Minimal correct usage

| Need | Prefer |
|------|--------|
| Bitstrings / histograms | Sampler |
| ⟨O⟩ for Pauli/SparsePauliOp | Estimator |
| Exact amplitudes (tiny systems) | `Statevector` / quantum_info |

Do not substitute Sampler counts for Estimator expectations without an explicit observable estimation procedure.

## Common pitfalls

- Calling Sampler then manually hacking incomplete estimators.
- Passing unbounded observables / wrong pub structure.
- Version skew between documentation examples and installed primitives.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`sampler_vs_estimator`, `qiskit_k2`, `qiskit`
