# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.measure_active`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.measure_active`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Adds measurement to all non-idle qubits. Creates a new ClassicalRegister with a size equal to the number of non-idle qubits being measured.

## 功能说明
Adds measurement to all non-idle qubits. Creates a new ClassicalRegister with
a size equal to the number of non-idle qubits being measured.

Returns a new circuit with measurements if `inplace=False`.

Args:
    inplace (bool): All measurements inplace or return new circuit.

Returns:
    QuantumCircuit: Returns circuit with measurements when ``inplace = False``.

## 函数签名
```python
(self, inplace: 'bool' = True) -> 'QuantumCircuit | None'
```

## 相关量子编程概念
- circuit construction
- measurement
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- measurement

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.measure_active` 怎么用？
- `measure_active` 的参数是什么？
- Qiskit 2.4.1 中 `measure_active` 的最小示例是什么？
