# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.dot`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.dot`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Return the right multiplied operator self * other.

## 功能说明
Return the right multiplied operator self * other.

Args:
    other (Operator): an operator object.
    qargs (list or None):  a list of subsystem positions to
                          apply other on. If None apply on all
                          subsystems (default: None).

Returns:
    Operator: The right matrix multiplied Operator.

.. note::
    The dot product can be obtained using the ``@`` binary operator.
    Hence ``a.dot(b)`` is equivalent to ``a @ b``.

## 函数签名
```python
(self, other, qargs=None) -> typing_extensions.Self
```

## 相关量子编程概念
- Hamiltonian
- Pauli 算符
- observable
- observable / Hamiltonian

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.dot` 怎么用？
- `dot` 的参数是什么？
- Qiskit 2.4.1 中 `dot` 的最小示例是什么？
