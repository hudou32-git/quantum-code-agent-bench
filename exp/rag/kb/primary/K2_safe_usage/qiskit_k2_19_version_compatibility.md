# Qiskit K2 — Version compatibility (1.x → 2.x)

```text
recipe_id: qiskit_k2_19
framework: qiskit
topic: version_compatibility
relevant_api: migration, deprecated APIs
source_ids: Qiskit release notes / migration guides
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Prefer current Qiskit 2.x APIs and avoid removed 0.x/1.x shortcuts.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use when porting tutorials or model outputs that cite deprecated imports.

## Minimal correct usage

### Frequent migration themes
- Prefer `qiskit.primitives` / Runtime primitives over legacy `execute` + `Backend.run` tutorial patterns when targeting modern stacks.
- Prefer `qiskit_aer` imports over historical `Aer` re-exports from `qiskit`.
- Prefer FakeProvider / V2 backends consistent with the installed packages.
- Prefer control-flow APIs over obsolete classical-conditioning helpers.

Pin `qiskit` (+ Aer/Runtime if used) versions in experiments and keep recipes aligned to that pin (this corpus targets **2.4.1**).

## Common pitfalls

- Generating code that imports removed symbols (`execute`, old fake backends).
- Mixing V1 and V2 result parsing.
- Following outdated blog snippets without checking the pin.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`version_compatibility`, `qiskit_k2`, `qiskit`
