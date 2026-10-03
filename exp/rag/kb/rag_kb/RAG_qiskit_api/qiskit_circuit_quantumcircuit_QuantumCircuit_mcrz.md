# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.mcrz`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.mcrz`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply Multiple-Controlled Z rotation gate

## 功能说明
Apply Multiple-Controlled Z rotation gate

Args:
    lam: The angle of the rotation.
    q_controls: The qubits used as the controls.
    q_target: The qubit targeted by the gate.
    use_basis_gates: use p, u, cx basis gates.

## 函数签名
```python
(self, lam: 'ParameterValueType', q_controls: 'Sequence[QubitSpecifier]', q_target: 'QubitSpecifier', use_basis_gates: 'bool' = False)
```

## 相关量子编程概念
- Bell state / entanglement
- circuit construction
- quantum circuit
- transpilation
- 量子线路

## 检索标签
- backend_provider
- circuit_construction
- transpilation
- two_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.mcrz` 怎么用？
- `mcrz` 的参数是什么？
- Qiskit 2.4.1 中 `mcrz` 的最小示例是什么？
