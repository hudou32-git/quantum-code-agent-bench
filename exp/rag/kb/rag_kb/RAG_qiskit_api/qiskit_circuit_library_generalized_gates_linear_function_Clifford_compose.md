# Qiskit 2.4.1 API: `qiskit.circuit.library.generalized_gates.linear_function.Clifford.compose`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.generalized_gates.linear_function`
- API: `qiskit.circuit.library.generalized_gates.linear_function.Clifford.compose`
- Kind: `method`
- Owner class: `Clifford`

## 一句话用途
Return the operator composition with another Clifford.

## 功能说明
Return the operator composition with another Clifford.

Args:
    other (Clifford): a Clifford object.
    qargs (list or None):  a list of subsystem positions to
                          apply other on. If None apply on all
                          subsystems (default: None).
    front (bool): If True compose using right operator multiplication,
                  instead of left multiplication [default: False].

Returns:
    Clifford: The composed Clifford.

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
(self, other: 'Clifford | QuantumCircuit | Instruction', qargs: 'list | None' = None, front: 'bool' = False) -> 'Clifford'
```

## 相关量子编程概念
- Clifford circuit
- stabilizer

## 检索标签
- circuit_construction
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.generalized_gates.linear_function.Clifford.compose` 怎么用？
- `compose` 的参数是什么？
- Qiskit 2.4.1 中 `compose` 的最小示例是什么？
