# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.tensor`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.tensor`
- Kind: `method`
- Owner class: `Pauli`

## 一句话用途
Return the tensor product with another Pauli.

## 功能说明
Return the tensor product with another Pauli.

Args:
    other (Pauli): a Pauli object.

Returns:
    Pauli: the tensor product :math:`a \otimes b`, where :math:`a`
        is the current Pauli, and :math:`b` is the other Pauli.

.. note::
    The tensor product can be obtained using the ``^`` binary operator.
    Hence ``a.tensor(b)`` is equivalent to ``a ^ b``.

.. note:
    Tensor uses reversed operator ordering to :meth:`expand`.
    For two operators of the same type ``a.tensor(b) = b.expand(a)``.

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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.tensor` 怎么用？
- `tensor` 的参数是什么？
- Qiskit 2.4.1 中 `tensor` 的最小示例是什么？
