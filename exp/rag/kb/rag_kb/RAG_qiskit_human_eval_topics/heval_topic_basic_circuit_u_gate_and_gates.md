# HumanEval-Qiskit Topic: basic circuit — U gate, single-qubit rotations, gate methods

## Metadata
- Kind: `human_eval_topic_recipe`
- Topics: `QuantumCircuit`, `u gate`, `custom_rotation_gate`, `pi/2`, `single qubit`, `HumanEval`, `exact Qiskit API`

## Task pattern
Prompt imports `from qiskit import QuantumCircuit` and often `import numpy as np`.  
Docstring asks for a **U gate** with angles theta, phi, lambda (frequently all `pi/2`).

## Function body pattern (append-only, 4-space indent)
```python
    qc = QuantumCircuit(1)
    theta = np.pi / 2
    phi = np.pi / 2
    lam = np.pi / 2
    qc.u(theta, phi, lam, 0)
    return qc
```

## Rules
- Use `qc.u(theta, phi, lam, qubit)` — not deprecated `u3` unless prompt already uses it.
- Use `qc.cx(c, t)` for CNOT — **never** `qc.cnot`.
- Return the `QuantumCircuit` object when the signature says so.
- Do not add `if __name__` blocks, tests, or extra imports in HumanEval output.

## Common mistakes
- Returning markdown or full `def` instead of body only.
- Using `u3` when `u` is the Qiskit 2.x name on `QuantumCircuit`.

## Retrieval tags
custom_rotation_gate, U gate, theta phi lambda, QuantumCircuit, numpy pi, HumanEval basic circuit, single-qubit rotation

## Questions this answers
- Create custom single-qubit rotation gate U with angles pi/2 HumanEval
- custom_rotation_gate QuantumCircuit function body Qiskit 2.x
