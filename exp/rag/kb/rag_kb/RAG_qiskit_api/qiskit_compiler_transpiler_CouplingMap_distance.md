# Qiskit 2.4.1 API: `qiskit.compiler.transpiler.CouplingMap.distance`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.compiler.transpiler`
- API: `qiskit.compiler.transpiler.CouplingMap.distance`
- Kind: `method`
- Owner class: `CouplingMap`

## 一句话用途
Returns the undirected distance between physical_qubit1 and physical_qubit2.

## 功能说明
Returns the undirected distance between physical_qubit1 and physical_qubit2.

Args:
    physical_qubit1 (int): A physical qubit
    physical_qubit2 (int): Another physical qubit

Returns:
    int: The undirected distance

Raises:
    CouplingError: if the qubits do not exist in the CouplingMap

## 函数签名
```python
(self, physical_qubit1, physical_qubit2)
```

## 相关量子编程概念
- connectivity
- coupling map
- transpilation
- 硬件拓扑

## 检索标签
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.compiler.transpiler.CouplingMap.distance` 怎么用？
- `distance` 的参数是什么？
- Qiskit 2.4.1 中 `distance` 的最小示例是什么？
