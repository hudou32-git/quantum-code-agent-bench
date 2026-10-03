# Qiskit 2.4.1 API: `qiskit.qasm3.dumps`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm3`
- API: `qiskit.qasm3.dumps`
- Kind: `function`

## 一句话用途
Serialize a :class:`~qiskit.circuit.QuantumCircuit` object in an OpenQASM 3 string.

## 功能说明
Serialize a :class:`~qiskit.circuit.QuantumCircuit` object in an OpenQASM 3 string.

Args:
    circuit (QuantumCircuit): Circuit to serialize.
    **kwargs: Arguments for the :obj:`.Exporter` constructor.

Returns:
    str: The OpenQASM 3 serialization

## 函数签名
```python
(circuit, **kwargs) -> 'str'
```

## 相关量子编程概念
- OpenQASM

## 检索标签
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.qasm3.dumps` 怎么用？
- `dumps` 的参数是什么？
- Qiskit 2.4.1 中 `dumps` 的最小示例是什么？
