# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.Operator.equiv`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.Operator.equiv`
- Kind: `method`
- Owner class: `Operator`

## 一句话用途
Return True if operators are equivalent up to global phase.

## 功能说明
Return True if operators are equivalent up to global phase.

Args:
    other (Operator): an operator object.
    rtol (float): relative tolerance value for comparison.
    atol (float): absolute tolerance value for comparison.

Returns:
    bool: True if operators are equivalent up to global phase.

## 函数签名
```python
(self, other: 'Operator', rtol: 'float | None' = None, atol: 'float | None' = None) -> 'bool'
```

## 相关量子编程概念
- operator
- unitary
- 算符

## 检索标签
- circuit_construction
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.Operator.equiv` 怎么用？
- `equiv` 的参数是什么？
- Qiskit 2.4.1 中 `equiv` 的最小示例是什么？
