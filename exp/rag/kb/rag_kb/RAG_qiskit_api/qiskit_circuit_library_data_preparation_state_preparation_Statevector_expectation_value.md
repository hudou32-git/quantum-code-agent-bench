# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.expectation_value`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.expectation_value`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Compute the expectation value of an operator.

## 功能说明
Compute the expectation value of an operator.

Args:
    oper (Operator): an operator to evaluate expval of.
    qargs (None or list): subsystems to apply operator on.

Returns:
    complex: the expectation value.

## 函数签名
```python
(self, oper: 'BaseOperator | QuantumCircuit | Instruction', qargs: 'None | list[int]' = None) -> 'complex'
```

## 相关量子编程概念
- simulation
- state simulation
- state vector
- 态向量

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.expectation_value` 怎么用？
- `expectation_value` 的参数是什么？
- Qiskit 2.4.1 中 `expectation_value` 的最小示例是什么？
