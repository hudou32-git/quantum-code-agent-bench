# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.copy`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.copy`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Copy the circuit.

## 功能说明
Copy the circuit.

Args:
  name (str): name to be given to the copied circuit. If None, then the name stays the same.

Returns:
  QuantumCircuit: a deepcopy of the current circuit, with the specified name

## 函数签名
```python
(self, name: 'str | None' = None) -> 'typing.Self'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.copy` 怎么用？
- `copy` 的参数是什么？
- Qiskit 2.4.1 中 `copy` 的最小示例是什么？
