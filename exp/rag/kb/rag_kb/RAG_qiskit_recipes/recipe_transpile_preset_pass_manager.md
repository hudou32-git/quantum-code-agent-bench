# Qiskit 2.4.1 Recipe: transpile + generate_preset_pass_manager + backend

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `transpile`, `PassManager`, `backend`, `optimization_level`, `QuantumCircuit`, `Target`

## 任务描述（HumanEval 风格）
Transpile a `QuantumCircuit` for a specific backend (including IBM Fake backends or `AerSimulator`) using a preset pass manager with a chosen `optimization_level` (0–3). Return the transpiled circuit. Common wording: "transpile using pass manager with optimization level as N".

## Available imports（常见）
- `from qiskit import QuantumCircuit, transpile`
- `from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager`
- `from qiskit_aer import AerSimulator`
- `from qiskit_ibm_runtime.fake_provider import FakeKyoto`（或题目给定的 Fake backend）

## 实现要点
1. 构建或接收原始 `QuantumCircuit`。
2. 获取 `backend`（`AerSimulator()` 或 `FakeBackend()` 实例）。
3. **推荐（Qiskit 1.x/2.x 常用）**：`pm = generate_preset_pass_manager(backend=backend, optimization_level=1)`，`transpiled = pm.run(qc)`。
4. **备选**：`transpile(qc, backend=backend, optimization_level=1)` 直接返回线路。
5. 对 noisy / DD / scheduling 题目，pass manager 可能还需 `seed_transpiler` 或 backend 的 `target`；以题目 imports 为准。

## 完整示例代码
```python
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

def transpile_circuit(qc: QuantumCircuit) -> QuantumCircuit:
    backend = AerSimulator()
    optimization_level = 1
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=optimization_level,
    )
    transpiled_qc = pm.run(qc)
    return transpiled_qc
```

## 相关量子编程概念
- transpilation
- pass manager
- backend
- optimization level

## 检索标签
- transpile
- passmanager
- preset_pass_manager
- backend
- qiskit

## 适合回答的问题
- Transpile a bell circuit using pass manager with optimization level 1.
- How to use generate_preset_pass_manager with AerSimulator?
- Return transpiled QuantumCircuit for Fake backend target.
