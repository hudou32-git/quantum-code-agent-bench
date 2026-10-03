# Qiskit 2.4.1 API: `qiskit.qasm2.load`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.qasm2`
- API: `qiskit.qasm2.load`
- Kind: `function`

## 一句话用途
Parse an OpenQASM 2 program from a file into a :class:`.QuantumCircuit`. The given path should be ASCII or UTF-8 encoded, and contain the OpenQASM 2 program.

## 功能说明
Parse an OpenQASM 2 program from a file into a :class:`.QuantumCircuit`.  The given path
should be ASCII or UTF-8 encoded, and contain the OpenQASM 2 program.

Args:
    filename: The path to the OpenQASM 2 file.
    include_path: order of directories to search when evaluating ``include`` statements.
    include_input_directory: Whether to add the directory of the input file to the
        ``include_path``, and if so, whether to *append* it to search last, or *prepend* it to
        search first.  Pass ``None`` to suppress adding this directory entirely.
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
(filename: str | os.PathLike, *, include_path: collections.abc.Iterable[str | os.PathLike] = ('.',), include_input_directory: Optional[Literal['append', 'prepend']] = 'append', custom_instructions: collections.abc.Iterable[qiskit.qasm2.parse.CustomInstruction] = (), custom_classical: collections.abc.Iterable[CustomClassical] = (), strict: bool = False) -> qiskit.circuit.quantumcircuit.QuantumCircuit
```

## 相关量子编程概念
- OpenQASM
- backend execution

## 检索标签
- backend_provider
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.qasm2.load` 怎么用？
- `load` 的参数是什么？
- Qiskit 2.4.1 中 `load` 的最小示例是什么？
