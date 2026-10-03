# HumanEval-Qiskit Topic: quantum_info Operator, Statevector, unitary matrix

## Metadata
- Kind: `human_eval_topic_recipe`
- Topics: `Operator`, `Statevector`, `unitary`, `get_unitary`, `quantum_info`, `HumanEval`

## Task pattern
Prompt imports from `qiskit.quantum_info` such as `Operator`, `Statevector`, `SparsePauliOp`.  
**Not** a Bell Sampler counts task unless `Sampler` appears in imports.

## Operator / unitary return
```python
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return Operator(qc).data
```
There is no `QuantumCircuit.to_operator()` in standard Qiskit API.

## Statevector
```python
    qc = QuantumCircuit(n)
  # ... build ...
    return Statevector(qc)
```

## Rules
- Match return type in docstring (`ndarray`, `Statevector`, etc.).
- Do not import `qiskit_ibm_runtime.Sampler` when prompt has no runtime imports.
- Ignore retrieved Bell histogram or Aer Sampler examples if imports are only `quantum_info`.

## Retrieval tags
Operator, Statevector, unitary matrix, get_unitary, quantum_info, phi plus bell circuit matrix, HumanEval

## Questions this answers
- Get unitary matrix for phi plus bell circuit return Operator data
- Statevector from QuantumCircuit HumanEval quantum_info
