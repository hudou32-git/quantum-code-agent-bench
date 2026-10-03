# Qiskit 2.4.1 API: `qiskit.quantum_info.PauliList.evolve`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.PauliList.evolve`
- Kind: `method`
- Owner class: `PauliList`

## 一句话用途
Performs either Heisenberg (default) or Schrödinger picture evolution of the Pauli by a Clifford and returns the evolved Pauli.

## 功能说明
Performs either Heisenberg (default) or Schrödinger picture
evolution of the Pauli by a Clifford and returns the evolved Pauli.

Schrödinger picture evolution can be chosen by passing parameter ``frame='s'``.
This option yields a faster calculation.

Heisenberg picture evolves the Pauli as :math:`P^\prime = C^\dagger.P.C`.

Schrödinger picture evolves the Pauli as :math:`P^\prime = C.P.C^\dagger`.

Args:
    other (Pauli or Clifford or QuantumCircuit): The Clifford operator to evolve by.
    qargs (list): a list of qubits to apply the Clifford to.
    frame (string): ``'h'`` for Heisenberg (default) or ``'s'`` for Schrödinger framework.

Returns:
    PauliList: the Pauli :math:`C^\dagger.P.C` (Heisenberg picture)
    or the Pauli :math:`C.P.C^\dagger` (Schrödinger picture).

Raises:
    QiskitError: if the Clifford number of qubits and qargs don't match.

## 函数签名
```python
(self, other: 'Pauli | Clifford | QuantumCircuit', qargs: 'list | None' = None, frame: "Literal['h', 's']" = 'h') -> 'Pauli'
```

## 相关量子编程概念
- observable / Hamiltonian
- parameterized circuit

## 检索标签
- circuit_construction
- observable_hamiltonian
- parameterized_circuit
- quantum_info

## 适合回答的问题
- `qiskit.quantum_info.PauliList.evolve` 怎么用？
- `evolve` 的参数是什么？
- Qiskit 2.4.1 中 `evolve` 的最小示例是什么？
