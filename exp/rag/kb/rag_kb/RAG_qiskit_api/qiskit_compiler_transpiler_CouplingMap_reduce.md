# Qiskit 2.4.1 API: `qiskit.compiler.transpiler.CouplingMap.reduce`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.compiler.transpiler`
- API: `qiskit.compiler.transpiler.CouplingMap.reduce`
- Kind: `method`
- Owner class: `CouplingMap`

## 一句话用途
Returns a reduced coupling map that corresponds to the subgraph of qubits selected in the mapping.

## 功能说明
Returns a reduced coupling map that
corresponds to the subgraph of qubits
selected in the mapping.

Args:
    mapping (list): A mapping of reduced qubits to device
        qubits.
    check_if_connected (bool): if True, checks that the reduced
        coupling map is connected.

Returns:
    CouplingMap: A reduced coupling_map for the selected qubits.

Raises:
    CouplingError: Reduced coupling map must be connected.

## 函数签名
```python
(self, mapping, check_if_connected=True)
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
- `qiskit.compiler.transpiler.CouplingMap.reduce` 怎么用？
- `reduce` 的参数是什么？
- Qiskit 2.4.1 中 `reduce` 的最小示例是什么？
