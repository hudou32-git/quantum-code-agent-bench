# HumanEval-Qiskit: QuantumCircuit Qiskit 2.x API pitfalls

## Metadata
- Topics: `QuantumCircuit`, `cx`, `compose`, `measure_all`, `Operator`, `QuantumRegister`

## Gate methods (common model mistakes)
- Use `qc.cx(control, target)` — **not** `qc.cnot(...)` (AttributeError on QuantumCircuit).
- Single-qubit: `qc.h`, `qc.x`, `qc.rz`, `qc.u(theta, phi, lam, qubit)`.
- Multi-controlled: use library gates from prompt imports only.

## Measurement
- `qc.measure_all()` is common in HumanEval solutions.
- Classical conditioning: Qiskit 2.x removed old `c_if` on `InstructionSet` patterns — prefer building circuits with `measure` / `if_test` only if prompt imports support it.

## compose / append
- `qc.compose(other_circuit, inplace=True)` for oracles (e.g. Deutsch–Jozsa).
- `qc.barrier()` when task expects barrier before measure.

## Operator and unitary tasks
When prompt imports `from qiskit.quantum_info import Operator`:
```python
    return Operator(qc).data
```
There is no `QuantumCircuit.to_operator()` in standard API.

## Registers
When prompt uses `QuantumRegister`, `ClassicalRegister`, construct circuit with explicit registers as in the stub.

## Retrieval tags
QuantumCircuit, cx, cnot error, compose, measure_all, Operator, quantum_info, HumanEval

## Questions this answers
- QuantumCircuit object has no attribute cnot
- Get unitary matrix Operator circuit HumanEval
- Compose oracle into circuit inplace
