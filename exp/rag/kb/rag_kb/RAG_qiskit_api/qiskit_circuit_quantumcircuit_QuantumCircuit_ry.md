# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.ry`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.ry`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.RYGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.RYGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    theta: The rotation angle of the gate.
    qubit: The qubit(s) to apply the gate to.
    label: The string label of the gate in the circuit.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, theta: 'ParameterValueType', qubit: 'QubitSpecifier', label: 'str | None' = None) -> 'InstructionSet'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.ry` 怎么用？
- `ry` 的参数是什么？
- Qiskit 2.4.1 中 `ry` 的最小示例是什么？
