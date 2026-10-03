# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.evolve`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.evolve`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Evolve a quantum state by the operator.

## 功能说明
Evolve a quantum state by the operator.

Args:
    other (Operator | QuantumCircuit | circuit.Instruction): The operator to evolve by.
    qargs (list): a list of Statevector subsystem positions to apply
                   the operator on.

Returns:
    Statevector: the output quantum state.

Raises:
    QiskitError: if the operator dimension does not match the
                 specified Statevector subsystem dimensions.

## 函数签名
```python
(self, other: 'Operator | QuantumCircuit | Instruction', qargs: 'list[int] | None' = None) -> 'Statevector'
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
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.evolve` 怎么用？
- `evolve` 的参数是什么？
- Qiskit 2.4.1 中 `evolve` 的最小示例是什么？
