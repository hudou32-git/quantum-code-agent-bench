# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.compose`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.compose`
- Kind: `method`
- Owner class: `Pauli`

## 一句话用途
Return the operator composition with another Pauli.

## 功能说明
Return the operator composition with another Pauli.

Args:
    other (Pauli): a Pauli object.
    qargs (list or None):  qubits to apply dot product
                          on (default: None).
    front (bool): If True compose using right operator multiplication,
                  instead of left multiplication [default: False].
    inplace (bool): If True update in-place (default: False).

Returns:
    Pauli: The composed Pauli.

Raises:
    QiskitError: if other cannot be converted to an operator, or has
                 incompatible dimensions for specified subsystems.

.. note::
    Composition (``&``) by default is defined as `left` matrix multiplication for
    matrix operators, while :meth:`dot` is defined as `right` matrix
    multiplication. That is that ``A & B == A.compose(B)`` is equivalent to
    ``B.dot(A)`` when ``A`` and ``B`` are of the same type.

    Setting the ``front=True`` kwarg changes this to `right` matrix
    multiplication and is equivalent to the :meth:`dot` method
    ``A.dot(B) == A.compose(B, front=True)``.

## 函数签名
```python
(self, other: 'Pauli', qargs: 'list | None' = None, front: 'bool' = False, inplace: 'bool' = False) -> 'Pauli'
```

## 相关量子编程概念
- Pauli
- observable
- observable / Hamiltonian

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.compose` 怎么用？
- `compose` 的参数是什么？
- Qiskit 2.4.1 中 `compose` 的最小示例是什么？
