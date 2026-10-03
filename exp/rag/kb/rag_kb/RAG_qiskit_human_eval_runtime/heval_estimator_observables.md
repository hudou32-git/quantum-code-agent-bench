# HumanEval-Qiskit: Estimator, SparsePauliOp, observables

## Metadata
- Topics: `Estimator`, `SparsePauliOp`, `evs`, `mode`, `AerSimulator`

## Prompt pattern
`from qiskit_ibm_runtime import Estimator` and `from qiskit.quantum_info import SparsePauliOp`.

## Standard pattern
```python
    qc = QuantumCircuit(2)
    # ... build qc ...
    observable = SparsePauliOp(["II", "XX", "YY", "ZZ"])
    backend = AerSimulator()
    estimator = Estimator(mode=backend)
    job = estimator.run([(qc, observable)])
    return job.result()[0].data.evs
```

## Rules
- `Estimator(mode=backend)` not `backend=` keyword on constructor.
- Pub tuple `(circuit, observable)` inside a list: `run([(qc, obs)])`.
- Return type per docstring (`float`, array, etc.) — often `evs` for expectation values.

## Do not mix
- `qiskit.primitives.StatevectorEstimator` unless prompt imports it.

## Retrieval tags
Estimator, SparsePauliOp, evs, expectation, Pauli, HumanEval, mode

## Questions this answers
- Bell circuit Estimator expectation II XX YY ZZ
- Estimator run observable tuple list HumanEval
