# Qiskit 2.4.1 API: `qiskit.qasm2.loads`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm2`
- API: `qiskit.qasm2.loads`
- Kind: `function`

## 一句话用途
Parse an OpenQASM 2 program from a string into a :class:`.QuantumCircuit`.

## 功能说明
Parse an OpenQASM 2 program from a string into a :class:`.QuantumCircuit`.

Args:
    string: The OpenQASM 2 program in a string.
    include_path: order of directories to search when evaluating ``include`` statements.
    custom_instructions: any custom constructors that should be used for specific gates or
        opaque instructions during circuit construction.  See :ref:`qasm2-custom-instructions`
        for more.
    custom_classical: any custom classical functions that should be used during the parsing of
        classical expressions.  See :ref:`qasm2-custom-classical` for more.
    strict: whether to run in :ref:`strict mode <qasm2-strict-mode>`.

Returns:
    A circuit object representing the same OpenQASM 2 program.

## 函数签名
```python
(string: str, *, include_path: collections.abc.Iterable[str | os.PathLike] = ('.',), custom_instructions: collections.abc.Iterable[qiskit.qasm2.parse.CustomInstruction] = (), custom_classical: collections.abc.Iterable[CustomClassical] = (), strict: bool = False) -> qiskit.circuit.quantumcircuit.QuantumCircuit
```

## 相关量子编程概念
- OpenQASM
- backend execution

## 检索标签
- backend_provider
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.qasm2.loads` 怎么用？
- `loads` 的参数是什么？
- Qiskit 2.4.1 中 `loads` 的最小示例是什么？
