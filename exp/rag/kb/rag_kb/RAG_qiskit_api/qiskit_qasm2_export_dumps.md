# Qiskit 2.4.1 API: `qiskit.qasm2.export.dumps`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm2.export`
- API: `qiskit.qasm2.export.dumps`
- Kind: `function`

## 一句话用途
Export a circuit to an OpenQASM 2 program in a string.

## 功能说明
Export a circuit to an OpenQASM 2 program in a string.

Args:
    circuit: the :class:`.QuantumCircuit` to be exported.

Returns:
    An OpenQASM 2 string representing the circuit.

Raises:
    QASM2ExportError: if the circuit cannot be represented by OpenQASM 2.

## 函数签名
```python
(circuit: 'QuantumCircuit', /) -> 'str'
```

## 相关量子编程概念
- OpenQASM

## 检索标签
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.qasm2.export.dumps` 怎么用？
- `dumps` 的参数是什么？
- Qiskit 2.4.1 中 `dumps` 的最小示例是什么？
