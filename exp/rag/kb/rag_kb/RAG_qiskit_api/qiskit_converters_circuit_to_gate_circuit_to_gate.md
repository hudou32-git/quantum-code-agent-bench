# Qiskit 2.4.1 API: `qiskit.converters.circuit_to_gate.circuit_to_gate`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.converters.circuit_to_gate`
- API: `qiskit.converters.circuit_to_gate.circuit_to_gate`
- Kind: `function`

## 一句话用途
Build a :class:`.Gate` object from a :class:`.QuantumCircuit`.

## 功能说明
Build a :class:`.Gate` object from a :class:`.QuantumCircuit`.

The gate is anonymous (not tied to a named quantum register),
and so can be inserted into another circuit. The gate will
have the same string name as the circuit.

Args:
    circuit (QuantumCircuit): the input circuit.
    parameter_map (dict): For parameterized circuits, a mapping from
       parameters in the circuit to parameters to be used in the gate.
       If None, existing circuit parameters will also parameterize the
       Gate.
    equivalence_library (EquivalenceLibrary): Optional equivalence library
       where the converted gate will be registered.
    label (str): Optional gate label.

Raises:
    QiskitError: if circuit is non-unitary or if
        parameter_map is not compatible with circuit

Return:
    Gate: a Gate equivalent to the action of the
    input circuit. Upon decomposition, this gate will
    yield the components comprising the original circuit.

## 函数签名
```python
(circuit, parameter_map=None, equivalence_library=None, label=None)
```

## 相关量子编程概念
- parameterized circuit

## 检索标签
- circuit_construction
- conversion
- parameterized_circuit

## 适合回答的问题
- `qiskit.converters.circuit_to_gate.circuit_to_gate` 怎么用？
- `circuit_to_gate` 的参数是什么？
- Qiskit 2.4.1 中 `circuit_to_gate` 的最小示例是什么？
