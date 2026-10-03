# Qiskit 2.4.1 API: `qiskit.qasm3.dump`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm3`
- API: `qiskit.qasm3.dump`
- Kind: `function`

## 一句话用途
Serialize a :class:`~qiskit.circuit.QuantumCircuit` object as an OpenQASM 3 stream to file-like object.

## 功能说明
Serialize a :class:`~qiskit.circuit.QuantumCircuit` object as an OpenQASM 3 stream to
file-like object.

Args:
    circuit (QuantumCircuit): Circuit to serialize.
    stream (TextIOBase): stream-like object to dump the OpenQASM 3 serialization
    **kwargs: Arguments for the :obj:`.Exporter` constructor.

## 函数签名
```python
(circuit, stream, **kwargs) -> 'None'
```

## 相关量子编程概念
- OpenQASM

## 检索标签
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.qasm3.dump` 怎么用？
- `dump` 的参数是什么？
- Qiskit 2.4.1 中 `dump` 的最小示例是什么？
