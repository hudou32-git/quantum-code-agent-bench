# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.swap`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.swap`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.SwapGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.SwapGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    qubit1, qubit2: The qubits to apply the gate to.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, qubit1: 'QubitSpecifier', qubit2: 'QubitSpecifier') -> 'InstructionSet'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate
- two_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.swap` 怎么用？
- `swap` 的参数是什么？
- Qiskit 2.4.1 中 `swap` 的最小示例是什么？
