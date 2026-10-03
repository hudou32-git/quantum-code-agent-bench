# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.DensityMatrix.from_instruction`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.DensityMatrix.from_instruction`
- Kind: `method`
- Owner class: `DensityMatrix`

## 一句话用途
Return the output density matrix of an instruction.

## 功能说明
Return the output density matrix of an instruction.

The statevector is initialized in the state :math:`|{0,\ldots,0}\rangle` of
the same number of qubits as the input instruction or circuit, evolved
by the input instruction, and the output statevector returned.

Args:
    instruction: instruction or circuit

Returns:
    The final density matrix.

Raises:
    QiskitError: if the instruction contains invalid instructions for
                 density matrix simulation.

## 函数签名
```python
(instruction: 'circuit.instruction.Instruction | QuantumCircuit') -> 'DensityMatrix'
```

## 相关量子编程概念
- density matrix
- mixed state
- state simulation
- 密度矩阵

## 检索标签
- circuit_construction
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.DensityMatrix.from_instruction` 怎么用？
- `from_instruction` 的参数是什么？
- Qiskit 2.4.1 中 `from_instruction` 的最小示例是什么？
