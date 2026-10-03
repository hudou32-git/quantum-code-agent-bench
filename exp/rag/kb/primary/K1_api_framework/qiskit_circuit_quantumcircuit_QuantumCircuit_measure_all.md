# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.measure_all`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.measure_all`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Adds measurement to all qubits.

## 功能说明
Adds measurement to all qubits.

By default, adds new classical bits in a :obj:`.ClassicalRegister` to store these
measurements.  If ``add_bits=False``, the results of the measurements will instead be stored
in the already existing classical bits, with qubit ``n`` being measured into classical bit
``n``.

Returns a new circuit with measurements if ``inplace=False``.

Args:
    inplace (bool): All measurements inplace or return new circuit.
    add_bits (bool): Whether to add new bits to store the results.

Returns:
    QuantumCircuit: Returns circuit with measurements when ``inplace=False``.

Raises:
    CircuitError: if ``add_bits=False`` but there are not enough classical bits.

## 函数签名
```python
(self, inplace: 'bool' = True, add_bits: 'bool' = True) -> 'QuantumCircuit | None'
```

## 使用示例
### 示例 1
```python
from qiskit import QuantumCircuit



qc = QuantumCircuit(2)

qc.h(0)

qc.cx(0, 1)

qc.measure_all()
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
- `qiskit.circuit.quantumcircuit.QuantumCircuit.measure_all` 怎么用？
- `measure_all` 的参数是什么？
- Qiskit 2.4.1 中 `measure_all` 的最小示例是什么？
