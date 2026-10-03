# Qiskit K2 — Simulator result extraction

```text
recipe_id: qiskit_k2_14
framework: qiskit
topic: simulator_result_extraction
relevant_api: AerSimulator, StatevectorSampler, result reading
source_ids: qiskit_aer.AerSimulator; qiskit.primitives
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Run local simulation and extract the correct payload type.

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use for local debugging without cloud Runtime.

## Minimal correct usage

### Guidance
- **Shot simulation:** Aer (or reference Sampler) → counts / memory.
- **Exact state:** `Statevector(circuit)` or a statevector sampler/simulator path.
- Always match extraction code to the object you actually received (`Counts`, `DataBin`, `Statevector`, …) for the installed version.

## Common pitfalls

- Parsing Runtime `data.meas` patterns on a local Aer `Result`.
- Calling `.get_statevector()` on jobs that only measured shots.
- Ignoring seed / shots settings when comparing flaky counts.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Benchmark-specific output contracts.

## Retrieval tags

`simulator_result_extraction`, `qiskit_k2`, `qiskit`
