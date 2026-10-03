# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.to_gate`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.to_gate`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Create a :class:`.Gate` out of this circuit. The circuit must act only on qubits and contain only unitary operations.

## 功能说明
Create a :class:`.Gate` out of this circuit.  The circuit must act only on qubits and
contain only unitary operations.

.. seealso::
    :func:`circuit_to_gate`
        The underlying driver of this method.

Args:
    parameter_map: For parameterized circuits, a mapping from parameters in the circuit to
        parameters to be used in the gate. If ``None``, existing circuit parameters will
        also parameterize the gate.
    label : Optional gate label.

Returns:
    Gate: a composite gate encapsulating this circuit (can be decomposed back).

## 函数签名
```python
(self, parameter_map: 'dict[Parameter, ParameterValueType] | None' = None, label: 'str | None' = None) -> 'Gate'
```

## 相关量子编程概念
- circuit construction
- parameterized circuit
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- conversion
- parameterized_circuit
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.to_gate` 怎么用？
- `to_gate` 的参数是什么？
- Qiskit 2.4.1 中 `to_gate` 的最小示例是什么？
