# Qiskit 2.4.1 API: `qiskit.qasm3.loads`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm3`
- API: `qiskit.qasm3.loads`
- Kind: `function`

## 一句话用途
Load an OpenQASM 3 program from the given string.

## 功能说明
Load an OpenQASM 3 program from the given string.

Examples:

    Load a OpenQASM3 string into a quantum circuit with/without `num_qubits` argument.

    .. plot::
       :alt: Circuit diagram output by the previous code.
       :include-source:

       from qiskit import qasm3

       # An OpenQASM 3 program that only uses 2 physical qubits.
       prog = '''
           OPENQASM 3.0;
           include "stdgates.inc";
           h $0;
           cx $0, $1;
       '''
       # The importer can be supplied with the number of qubits in the target backend.
       # so the result is full width.
       qc = qasm3.loads(prog, num_qubits=5)
       assert qc.num_qubits == 5

Args:
    program: the OpenQASM 3 program.
    num_qubits: provides number of physical/virtual qubits.
    annotation_handlers: a mapping whose keys are (parent) namespaces and values are serializers
        that can handle children of those namespaces.  Requires ``qiskit_qasm3_import>=0.6.0``.
Returns:
    QuantumCircuit: a circuit representation of the OpenQASM 3 program.

Raises:
    QASM3ImporterError: if the OpenQASM 3 file is invalid, or cannot be represented by a
        :class:`.QuantumCircuit`.
    ValueError: if number of qubits in qasm3_ckt is more than num_qubits.

.. versionadded:: 2.1
    The ``annotation_handlers`` argument.  This requires ``qiskit_qasm3_import>=0.6.0``.

## 函数签名
```python
(program: 'str', *, num_qubits: 'int | None' = None, annotation_handlers: 'dict[str, annotation.OpenQASM3Serializer] | None' = None) -> 'QuantumCircuit'
```

## 相关量子编程概念
- Bell state / entanglement
- OpenQASM
- backend execution

## 检索标签
- backend_provider
- circuit_construction
- qasm
- transpilation

## 适合回答的问题
- `qiskit.qasm3.loads` 怎么用？
- `loads` 的参数是什么？
- Qiskit 2.4.1 中 `loads` 的最小示例是什么？
