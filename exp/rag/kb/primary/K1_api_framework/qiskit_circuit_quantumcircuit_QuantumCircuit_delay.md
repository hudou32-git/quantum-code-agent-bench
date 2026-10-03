# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.delay`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.delay`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply :class:`~.circuit.Delay`. If qarg is ``None``, applies to all qubits. When applying to multiple qubits, delays with the same duration will be created.

## 功能说明
Apply :class:`~.circuit.Delay`. If qarg is ``None``, applies to all qubits.
When applying to multiple qubits, delays with the same duration will be created.

Args:
    duration (Object):
        duration of the delay. If this is an :class:`~.expr.Expr`, it must be
        a constant expression of type :class:`~.types.Duration`.
    qarg (Object): qubit argument to apply this delay.
    unit (str | None): unit of the duration, unless ``duration`` is an :class:`~.expr.Expr`
        in which case it must not be specified. Supported units: ``'s'``, ``'ms'``, ``'us'``,
        ``'ns'``, ``'ps'``, and ``'dt'``. Default is ``'dt'``, i.e. integer time unit
        depending on the target backend.

Returns:
    qiskit.circuit.InstructionSet: handle to the added instructions.

Raises:
    CircuitError: if arguments have bad format.

## 函数签名
```python
(self, duration: 'ParameterValueType | expr.Expr', qarg: 'QubitSpecifier | None' = None, unit: 'str | None' = None) -> 'InstructionSet'
```

## 相关量子编程概念
- backend execution
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- backend_provider
- circuit_construction
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.delay` 怎么用？
- `delay` 的参数是什么？
- Qiskit 2.4.1 中 `delay` 的最小示例是什么？
