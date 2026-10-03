# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.compose`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.compose`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Return the operator composition with another SparsePauliOp.

## 功能说明
Return the operator composition with another SparsePauliOp.

Args:
    other (SparsePauliOp): a SparsePauliOp object.
    qargs (list or None):  a list of subsystem positions to
                          apply other on. If None apply on all
                          subsystems (default: None).
    front (bool): If True compose using right operator multiplication,
                  instead of left multiplication [default: False].

Returns:
    SparsePauliOp: The composed SparsePauliOp.

Raises:
    QiskitError: if other cannot be converted to an operator, or has
                 incompatible dimensions for specified subsystems.

.. note::
    Composition (``&``) by default is defined as `left` matrix multiplication for
    matrix operators, while ``@`` (equivalent to :meth:`dot`) is defined as `right` matrix
    multiplication. That is that ``A & B == A.compose(B)`` is equivalent to
    ``B @ A == B.dot(A)`` when ``A`` and ``B`` are of the same type.

    Setting the ``front=True`` kwarg changes this to `right` matrix
    multiplication and is equivalent to the :meth:`dot` method
    ``A.dot(B) == A.compose(B, front=True)``.

## 函数签名
```python
(self, other: 'SparsePauliOp', qargs: 'list | None' = None, front: 'bool' = False) -> 'SparsePauliOp'
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.compose` 怎么用？
- `compose` 的参数是什么？
- Qiskit 2.4.1 中 `compose` 的最小示例是什么？
