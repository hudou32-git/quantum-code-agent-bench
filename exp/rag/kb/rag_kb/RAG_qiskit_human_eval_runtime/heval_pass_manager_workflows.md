# HumanEval-Qiskit: generate_preset_pass_manager 端到端

## 基本信息
- Kind: `human_eval_runtime_stack`
- Topics: `generate_preset_pass_manager`, `PassManager`, `transpile`, `optimization_level`

## 核心 API
```python
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    pass_manager = generate_preset_pass_manager(
        optimization_level=1,
        backend=backend,
    )
    transpiled = pass_manager.run(circuit)
```

## 注意
- `pass_manager.run(circuit)` 的 `circuit` 是 `QuantumCircuit`；**不是** `StagedPassManager.run(backend=...)` 误用。
- `TranspilerService` 仅在 prompt import 时使用；构造参数以题目为准（常见 `optimization_level`）。

## 与 Sampler 串联
先 `isa = pass_manager.run(qc)`，再 `sampler.run([isa], shots=...)`。

## 仅返回 PassManager 的题
```python
    backend = AerSimulator()
    return generate_preset_pass_manager(optimization_level=3, backend=backend)
```

## 检索标签
- generate_preset_pass_manager
- pass_manager.run
- optimization_level
- transpile
- staged_pass_manager

## 适合回答的问题
- Transpile circuit using pass manager optimization level 1 for Aer backend.
- Return preset pass manager with optimization level 3 for AerSimulator.
- Need exact API for pass_manager.run after generate_preset_pass_manager.
