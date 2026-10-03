# Qiskit 2.4.1 API: `qiskit.transpiler.passes.routing.layout_transformation.CouplingMap`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler.passes.routing.layout_transformation`
- API: `qiskit.transpiler.passes.routing.layout_transformation.CouplingMap`
- Kind: `class`

## 一句话用途
Directed graph specifying fixed coupling.

## 功能说明
Directed graph specifying fixed coupling.

Nodes correspond to physical qubits (integers) and directed edges correspond
to permitted CNOT gates, with source and destination corresponding to control
and target qubits, respectively.

## 函数签名
```python
(couplinglist=None, description=None)
```

## 相关量子编程概念
- Bell state / entanglement
- connectivity
- coupling map
- transpilation
- 硬件拓扑

## 检索标签
- backend_provider
- circuit_construction
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.transpiler.passes.routing.layout_transformation.CouplingMap` 怎么用？
- `CouplingMap` 的参数是什么？
- Qiskit 2.4.1 中 `CouplingMap` 的最小示例是什么？
