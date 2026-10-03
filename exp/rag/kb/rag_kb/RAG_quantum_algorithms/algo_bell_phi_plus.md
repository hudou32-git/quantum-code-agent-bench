# Bell state |Φ+> (Qiskit)

## Goal
`(|00> + |11>) / sqrt(2)` on two qubits.

## Canonical circuit
```python
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
```

## Related Bell states
- |Φ->: H, CX, then Z on qubit 0 (or equivalent).
- |Ψ+>: H, CX, then X on qubit 1.
- |Ψ->: H, CX, then Z and X as needed.

## Common bugs
- Swapped CNOT control/target.
- Extra single-qubit phase → wrong Bell label but same computational probs.
- Building product states `|+>|0>` (forgot CX).
