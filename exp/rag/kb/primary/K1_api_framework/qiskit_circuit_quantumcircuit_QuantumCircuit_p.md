# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.p`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.p`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.PhaseGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.PhaseGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    theta: The angle of the rotation.
    qubit: The qubit(s) to apply the gate to.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, theta: 'ParameterValueType', qubit: 'QubitSpecifier') -> 'InstructionSet'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.p` 怎么用？
- `p` 的参数是什么？
- Qiskit 2.4.1 中 `p` 的最小示例是什么？
