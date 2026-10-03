# Qiskit 2.4.1 API: `qiskit.qasm3.load`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm3`
- API: `qiskit.qasm3.load`
- Kind: `function`

## 一句话用途
Load an OpenQASM 3 program from the file ``filename``.

## 功能说明
Load an OpenQASM 3 program from the file ``filename``.

Args:
    filename: the filename to load the program from.
    num_qubits: keyword argument which provides number of physical/virtual qubits.
    annotation_handlers: a mapping whose keys are (parent) namespaces and values are serializers
        that can handle children of those namespaces.  Requires ``qiskit_qasm3_import>=0.6.0``.
Returns:
    QuantumCircuit: a circuit representation of the OpenQASM 3 program.

Raises:
    QASM3ImporterError: if the OpenQASM 3 file is invalid, or cannot be represented by a
        :class:`.QuantumCircuit`.

.. versionadded:: 2.1
    The ``annotation_handlers`` argument.  This requires ``qiskit_qasm3_import>=0.6.0``.

## 函数签名
```python
(filename: 'str', *, num_qubits: 'int | None' = None, annotation_handlers: 'dict[str, annotation.OpenQASM3Serializer] | None' = None) -> 'QuantumCircuit'
```

## 相关量子编程概念
- OpenQASM

## 检索标签
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.qasm3.load` 怎么用？
- `load` 的参数是什么？
- Qiskit 2.4.1 中 `load` 的最小示例是什么？
