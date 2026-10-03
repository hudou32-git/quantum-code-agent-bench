# Qiskit 2.4.1 Recipe: fake_provider 具体机名（禁止 FakeBackendV2 / FakeProvider）

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `fake_provider`, `backend`, `transpile`, `Sampler`, `AerSimulator`

## 任务描述
QHE 题目在 **prompt 里已写明** 要用的 fake 设备类名。只 import 并使用该类，不要发明泛型名字。

## 禁止使用的符号（会导致 ImportError / AttributeError）
- `FakeBackendV2`
- `FakeProvider`
- `from qiskit_ibm_runtime.fake_provider import FakeBackendV2`
- `fake_provider.FakeProvider`

## 数据集中出现的合法机名（示例，以 prompt 为准）
- `FakeBelemV2`, `FakeCairoV2`, `FakeSydneyV2`, `FakeTorontoV2`
- `FakePerth`, `FakeOslo`, `FakeAuckland`, `FakeAthensV2`
- `FakeAlgiers`（Batch / 多任务题）
- 其他 `Fake*` 类：仅当 **当前题目的 prompt** 已 `from qiskit_ibm_runtime.fake_provider import ...` 时出现

## 实现要点
1. **不要新增 import**：prompt 已 `from qiskit_ibm_runtime.fake_provider import FakeCairoV2` 时，代码里直接 `device = FakeCairoV2()`。
2. 噪声仿真常见模式：`device_backend = FakeBelemV2()`；`simulator = AerSimulator.from_backend(device_backend)`；transpile 与 `Sampler(mode=simulator)` 的 `backend`/`mode` 与 canonical 一致。
3. 仅 transpile、不上机：`pass_manager = generate_preset_pass_manager(optimization_level=..., backend=FakeCairoV2())` 等，按题目要求。

## 函数体片段（transpile for named fake backend）
```python
    device = FakeCairoV2()
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=device)
    return pass_manager.run(circuit)
```

## 检索标签
- fake_provider
- fake_belem
- fake_cairo
- transpile
- backend
- qiskit_ibm_runtime

## 适合回答的问题
- Transpile circuit for Fake Cairo V2 backend using pass manager.
- Use FakeBelemV2 with AerSimulator.from_backend for noisy simulation.
- Which fake provider class name to import for Qiskit HumanEval task?
