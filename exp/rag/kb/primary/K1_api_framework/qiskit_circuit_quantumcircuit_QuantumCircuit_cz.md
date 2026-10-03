# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.cz`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.cz`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.CZGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.CZGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    control_qubit: The qubit(s) used as the controls.
    target_qubit: The qubit(s) targeted by the gate.
    label: The string label of the gate in the circuit.
    ctrl_state:
        The control state in decimal, or as a bitstring (e.g. '1').  Defaults to controlling
        on the '1' state.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, control_qubit: 'QubitSpecifier', target_qubit: 'QubitSpecifier', label: 'str | None' = None, ctrl_state: 'str | int | None' = None) -> 'InstructionSet'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- backend_provider
- circuit_construction
- transpilation
- two_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.cz` 怎么用？
- `cz` 的参数是什么？
- Qiskit 2.4.1 中 `cz` 的最小示例是什么？
