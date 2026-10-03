# Qiskit 2.4.1 API: `qiskit.transpiler.passes.scheduling.time_unit_conversion.InstructionDurations`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler.passes.scheduling.time_unit_conversion`
- API: `qiskit.transpiler.passes.scheduling.time_unit_conversion.InstructionDurations`
- Kind: `class`

## 一句话用途
Helper class to provide durations of instructions for scheduling.

## 功能说明
Helper class to provide durations of instructions for scheduling.

It stores durations (gate lengths) and dt to be used at the scheduling stage of transpiling.
It can be constructed from ``backend`` or ``instruction_durations``,
which is an argument of :func:`transpile`. The duration of an instruction depends on the
instruction (given by name), the qubits, and optionally the parameters of the instruction.
Note that these fields are used as keys in dictionaries that are used to retrieve the
instruction durations. Therefore, users must use the exact same parameter value to retrieve
an instruction duration as the value with which it was added.

## 函数签名
```python
(instruction_durations: 'InstructionDurationsType | None' = None, dt: 'float | None' = None)
```

## 相关量子编程概念
- backend execution
- parameterized circuit
- transpilation

## 检索标签
- backend_provider
- circuit_construction
- parameterized_circuit
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.transpiler.passes.scheduling.time_unit_conversion.InstructionDurations` 怎么用？
- `InstructionDurations` 的参数是什么？
- Qiskit 2.4.1 中 `InstructionDurations` 的最小示例是什么？
