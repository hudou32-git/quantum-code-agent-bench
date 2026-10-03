# Qiskit 2.4.1 API: `qiskit.compiler.transpiler.CouplingMap.neighbors`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.compiler.transpiler`
- API: `qiskit.compiler.transpiler.CouplingMap.neighbors`
- Kind: `method`
- Owner class: `CouplingMap`

## 一句话用途
Return the nearest neighbors of a physical qubit.

## 功能说明
Return the nearest neighbors of a physical qubit.

Directionality matters, i.e. a neighbor must be reachable
by going one hop in the direction of an edge.

## 函数签名
```python
(self, physical_qubit)
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
- `qiskit.compiler.transpiler.CouplingMap.neighbors` 怎么用？
- `neighbors` 的参数是什么？
- Qiskit 2.4.1 中 `neighbors` 的最小示例是什么？
