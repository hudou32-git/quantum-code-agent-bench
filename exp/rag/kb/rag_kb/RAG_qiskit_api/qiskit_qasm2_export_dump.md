# Qiskit 2.4.1 API: `qiskit.qasm2.export.dump`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm2.export`
- API: `qiskit.qasm2.export.dump`
- Kind: `function`

## 一句话用途
Dump a circuit as an OpenQASM 2 program to a file or stream.

## 功能说明
Dump a circuit as an OpenQASM 2 program to a file or stream.

Args:
    circuit: the :class:`.QuantumCircuit` to be exported.
    filename_or_stream: either a path-like object (likely a :class:`str` or
        :class:`pathlib.Path`), or an already opened text-mode stream.

Raises:
    QASM2ExportError: if the circuit cannot be represented by OpenQASM 2.

## 函数签名
```python
(circuit: 'QuantumCircuit', filename_or_stream: 'os.PathLike | io.TextIOBase', /)
```

## 相关量子编程概念
- OpenQASM

## 检索标签
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.qasm2.export.dump` 怎么用？
- `dump` 的参数是什么？
- Qiskit 2.4.1 中 `dump` 的最小示例是什么？
