# Qiskit 2.4.1 Recipe: QHE 本地评测 — 勿用 QiskitRuntimeService / 真机账号

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `AerSimulator`, `Sampler`, `local`, `HumanEval`, `evaluation`

## 任务描述
Qiskit HumanEval 评测在 **无 IBM Quantum 账号** 的隔离环境执行。任何调用云端 Runtime 账号的代码会 `AccountNotFoundError` 或类似失败。

## 禁止在 completion 中引入或使用
- `from qiskit_ibm_runtime import QiskitRuntimeService`
- `QiskitRuntimeService()` / `service.backend()` / `service.least_busy()`
- `IBMProvider` / `load_account()` / 真实 `Backend` 作业提交

## 应使用的本地路径
- 仿真：`from qiskit_aer import AerSimulator`；`backend = AerSimulator()` 或 `AerSimulator.from_backend(fake_device)`。
- Primitives：`from qiskit_ibm_runtime import Sampler, Estimator` 配合 **`Sampler(mode=backend)`**（mode 为 AerSimulator 实例），不是云端 service。
- Fake 设备：仅 prompt 中的 `qiskit_ibm_runtime.fake_provider.Fake*` 具体类名。

## 若题目 docstring 提到 “least busy device”
评测仍期望 **本地可运行** 的实现：用 prompt 指定的 `Fake*` 或 `AerSimulator()`，不要用 `QiskitRuntimeService` 解析真机。

## 函数体片段（preset pass manager 无云端）
```python
    backend = AerSimulator()
    pass_manager = generate_preset_pass_manager(optimization_level=3, backend=backend)
    return pass_manager
```

## 检索标签
- local_eval
- aer_simulator
- no_runtime_service
- account_not_found
- human_eval

## 适合回答的问题
- HumanEval Qiskit evaluation without IBM Quantum account.
- Do not use QiskitRuntimeService for benchmark completion.
- Generate pass manager locally with AerSimulator backend.
