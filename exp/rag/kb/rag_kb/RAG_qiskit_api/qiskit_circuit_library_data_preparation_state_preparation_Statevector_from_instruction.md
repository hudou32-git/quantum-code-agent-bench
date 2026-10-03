# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_instruction`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_instruction`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Return the output statevector of an instruction.

## 功能说明
Return the output statevector of an instruction.

The statevector is initialized in the state :math:`|{0,\ldots,0}\rangle` of the
same number of qubits as the input instruction or circuit, evolved
by the input instruction, and the output statevector returned.

Args:
    instruction (qiskit.circuit.Instruction or QuantumCircuit): instruction or circuit

Returns:
    Statevector: The final statevector.

Raises:
    QiskitError: if the instruction contains invalid instructions for
                 the statevector simulation.

## 函数签名
```python
(instruction: 'Instruction | QuantumCircuit') -> 'Statevector'
```

## 相关量子编程概念
- simulation
- state simulation
- state vector
- 态向量

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_instruction` 怎么用？
- `from_instruction` 的参数是什么？
- Qiskit 2.4.1 中 `from_instruction` 的最小示例是什么？
