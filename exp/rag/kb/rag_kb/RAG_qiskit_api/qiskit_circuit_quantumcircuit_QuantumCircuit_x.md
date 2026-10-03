# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.x`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.x`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.XGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.XGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    qubit: The qubit(s) to apply the gate to.
    label: The string label of the gate in the circuit.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, qubit: 'QubitSpecifier', label: 'str | None' = None) -> 'InstructionSet'
```

## 使用示例
### 示例 1
```python
from qiskit import QuantumCircuit



qc = QuantumCircuit(1)

qc.x(0)
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.x` 怎么用？
- `x` 的参数是什么？
- Qiskit 2.4.1 中 `x` 的最小示例是什么？
