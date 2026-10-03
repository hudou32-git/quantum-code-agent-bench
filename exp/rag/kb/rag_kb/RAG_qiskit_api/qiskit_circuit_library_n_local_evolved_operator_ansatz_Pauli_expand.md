# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.expand`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.expand`
- Kind: `method`
- Owner class: `Pauli`

## 一句话用途
Return the reverse-order tensor product with another Pauli.

## 功能说明
Return the reverse-order tensor product with another Pauli.

Args:
    other (Pauli): a Pauli object.

Returns:
    Pauli: the tensor product :math:`b \otimes a`, where :math:`a`
        is the current Pauli, and :math:`b` is the other Pauli.

.. note:
    Expand is the opposite operator ordering to :meth:`tensor`.
    For two operators of the same type ``a.expand(b) = b.tensor(a)``.

## 函数签名
```python
(self, other: 'Pauli') -> 'Pauli'
```

## 相关量子编程概念
- Pauli
- observable
- observable / Hamiltonian

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.expand` 怎么用？
- `expand` 的参数是什么？
- Qiskit 2.4.1 中 `expand` 的最小示例是什么？
