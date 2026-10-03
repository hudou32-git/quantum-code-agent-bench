# Qiskit 2.4.1 API: `qiskit.transpiler.instruction_durations.BackendV2.run`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler.instruction_durations`
- API: `qiskit.transpiler.instruction_durations.BackendV2.run`
- Kind: `method`
- Owner class: `BackendV2`

## 一句话用途
Run on the backend.

## 功能说明
Run on the backend.

This method returns a :class:`~qiskit.providers.Job` object
that runs circuits. Depending on the backend this may be either an async
or sync call. It is at the discretion of the provider to decide whether
running should block until the execution is finished or not: the Job
class can handle either situation.

Args:
    run_input (QuantumCircuit or list): An
        individual or a list of :class:`.QuantumCircuit` objects to
        run on the backend.
    options: Any kwarg options to pass to the backend for running the
        config. If a key is also present in the options
        attribute/object then the expectation is that the value
        specified will be used instead of what's set in the options
        object.

Returns:
    Job: The job object for the run

## 函数签名
```python
(self, run_input, **options)
```

## 相关量子编程概念
- backend execution
- transpilation

## 检索标签
- backend_provider
- circuit_construction
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.transpiler.instruction_durations.BackendV2.run` 怎么用？
- `run` 的参数是什么？
- Qiskit 2.4.1 中 `run` 的最小示例是什么？
