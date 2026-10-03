# Qiskit K2 — Statevector from QuantumCircuit

```text
recipe_id: qiskit_k2_09
framework: qiskit
topic: statevector_inspection
relevant_api: QuantumCircuit, Statevector
source_ids: qiskit.quantum_info.Statevector; qiskit.circuit.QuantumCircuit
benchmark_derived: false
version: 2.4.1
knowledge_layer: K2
public_release_status: primary_candidate
```

## Goal

Show the **official** composition of `QuantumCircuit` construction with `qiskit.quantum_info.Statevector` for inspecting a pure state (no shot sampling).

This page is a safe-usage pattern. It is **not** a benchmark solution template.

## When to use this stack

Use `Statevector` when you need exact amplitudes / probabilities from a unitary circuit and you are **not** running a shot-based Sampler/Estimator workflow.

Do **not** mix this path with Aer shot counts or Runtime Sampler result unpacking unless the programming context explicitly requires those APIs.

## Minimal correct usage

### 1. Build a small circuit, then wrap as Statevector

```python
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
sv = Statevector(qc)
# sv is a Statevector; inspect with .data / .probabilities() as needed
```

### 2. Bell Φ⁺ structure (algorithmic note, not a graded entrypoint)

The two-qubit circuit `H` on qubit 0 followed by `CX(0, 1)` prepares
\((|00\rangle + |11\rangle)/\sqrt{2}\) in the computational basis (little-endian register order as used by Qiskit).

Relative-phase variants (e.g. Φ⁻) are obtained by additional single-qubit Z-type operations; choose them from the task physics, not from a fixed function name.

### 3. Amplitudes without a circuit (optional)

When amplitudes are known explicitly, `Statevector` can also be constructed from an array or label helpers provided by the installed Qiskit version. Prefer the circuit→`Statevector(qc)` path when the state is defined by gates.

## Common pitfalls

- Returning measurement **counts** while the caller expects a `Statevector`.
- Inserting mid-circuit measure/reset before wrapping `Statevector(qc)` (collapses / changes the pure state).
- Assuming shot-noise Sampler APIs are required for exact statevector inspection.

## Non-goals (excluded from this page)

- Benchmark function names or HumanEval-style “implement `def …`” contracts.
- Copy-paste submitable graded solutions.
- Runtime / FakeBackend / Sampler stacks.

## Retrieval tags

`statevector`, `quantum_info`, `QuantumCircuit`, `bell_pattern`, `qiskit_k2`
