# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.DensityMatrix.expectation_value`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.DensityMatrix.expectation_value`
- Kind: `method`
- Owner class: `DensityMatrix`

## 一句话用途
Compute the expectation value of an operator.

## 功能说明
Compute the expectation value of an operator.

Args:
    oper (Operator): an operator to evaluate expval.
    qargs (None or list): subsystems to apply the operator on.

Returns:
    complex: the expectation value.

## 函数签名
```python
(self, oper: 'Operator', qargs: 'None | list[int]' = None) -> 'complex'
```

## 相关量子编程概念
- density matrix
- mixed state
- state simulation
- 密度矩阵

## 检索标签
- circuit_construction
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.DensityMatrix.expectation_value` 怎么用？
- `expectation_value` 的参数是什么？
- Qiskit 2.4.1 中 `expectation_value` 的最小示例是什么？
