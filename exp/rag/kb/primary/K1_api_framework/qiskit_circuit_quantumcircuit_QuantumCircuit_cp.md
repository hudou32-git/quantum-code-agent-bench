# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.cp`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.cp`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.CPhaseGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.CPhaseGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    theta: The angle of the rotation.
    control_qubit: The qubit(s) used as the control.
    target_qubit: The qubit(s) targeted by the gate.
    label: The string label of the gate in the circuit.
    ctrl_state:
        The control state in decimal, or as a bitstring (e.g. '1').  Defaults to controlling
        on the '1' state.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, theta: 'ParameterValueType', control_qubit: 'QubitSpecifier', target_qubit: 'QubitSpecifier', label: 'str | None' = None, ctrl_state: 'str | int | None' = None) -> 'InstructionSet'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- backend_provider
- circuit_construction
- transpilation

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.cp` 怎么用？
- `cp` 的参数是什么？
- Qiskit 2.4.1 中 `cp` 的最小示例是什么？
