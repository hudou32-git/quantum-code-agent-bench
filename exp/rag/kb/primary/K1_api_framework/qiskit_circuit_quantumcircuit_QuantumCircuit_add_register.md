# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.add_register`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.add_register`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Add registers.

## 功能说明
Add registers.

.. warning::

    If the quantum circuit has an existing :attr:`layout` attribute, adding a
    :class:`.QuantumRegister` will only increase the number of qubits. It will
    not update the layout.

## 函数签名
```python
(self, *regs: 'Register | int | Sequence[Bit]') -> 'None'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- transpilation
- 量子线路

## 检索标签
- circuit_construction
- transpilation

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.add_register` 怎么用？
- `add_register` 的参数是什么？
- Qiskit 2.4.1 中 `add_register` 的最小示例是什么？
