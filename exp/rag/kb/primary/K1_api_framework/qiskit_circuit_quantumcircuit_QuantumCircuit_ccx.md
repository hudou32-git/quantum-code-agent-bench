# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.ccx`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.ccx`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~qiskit.circuit.library.CCXGate`.

## 功能说明
Apply :class:`~qiskit.circuit.library.CCXGate`.

For the full matrix form of this gate, see the underlying gate documentation.

Args:
    control_qubit1: The qubit(s) used as the first control.
    control_qubit2: The qubit(s) used as the second control.
    target_qubit: The qubit(s) targeted by the gate.
    ctrl_state:
        The control state in decimal, or as a bitstring (e.g. '1').  Defaults to controlling
        on the '1' state.

Returns:
    A handle to the instructions created.

## 函数签名
```python
(self, control_qubit1: 'QubitSpecifier', control_qubit2: 'QubitSpecifier', target_qubit: 'QubitSpecifier', ctrl_state: 'str | int | None' = None) -> 'InstructionSet'
```

## 相关量子编程概念
- Bell state / entanglement
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- backend_provider
- circuit_construction
- transpilation

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.ccx` 怎么用？
- `ccx` 的参数是什么？
- Qiskit 2.4.1 中 `ccx` 的最小示例是什么？
