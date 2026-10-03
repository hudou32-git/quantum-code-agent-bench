# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.rz`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.rz`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.RZGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.RZGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    phi: The rotation angle of the gate.
    qubit: The qubit(s) to apply the gate to.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, phi: 'ParameterValueType', qubit: 'QubitSpecifier') -> 'InstructionSet'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.rz` 怎么用？
- `rz` 的参数是什么？
- Qiskit 2.4.1 中 `rz` 的最小示例是什么？
