# Qiskit 2.4.1 Recipe: Sampler / Estimator（qiskit_ibm_runtime，与 QHE 数据集一致）

## 基本信息
- Framework: Qiskit
- Version: 2.4.1（评测栈见仓库 `requirements.txt`：`qiskit>=2.1`，`qiskit-ibm-runtime==0.45.0`）
- Kind: `task_recipe`
- Topics: `Sampler`, `Estimator`, `AerSimulator`, `QuantumCircuit`, `backend`, `primitives`

## 任务描述（HumanEval 风格）
在 **prompt 已给出的 imports** 下补全函数体：用 `qiskit_ibm_runtime.Sampler` 或 `Estimator` 跑 Bell 或小线路，返回 counts 或 expectation。勿使用 `QiskitRuntimeService`、勿 `import` prompt 里没有的模块。

## Available imports（以 prompt 为准；常见组合）
- `from qiskit import QuantumCircuit`
- `from qiskit_aer import AerSimulator`
- `from qiskit_ibm_runtime import Sampler` 和/或 `Estimator`
- `from qiskit_ibm_runtime.options import SamplerOptions` / `EstimatorOptions`（若 prompt 已 import）
- `from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager`（需要先 transpile 时）
- `from qiskit.quantum_info import SparsePauliOp`（Estimator 题）

## 实现要点（对齐 dataset canonical_solution）
1. **禁止**：`Sampler(backend=...)`、`Sampler(simulator=...)`、`Sampler(seed=...)`。  
   **使用**：`backend = AerSimulator()`（或 `AerSimulator.from_backend(fake_device)`），`sampler = Sampler(mode=backend)`。
2. **禁止**：`sampler.run(circuit)`。  
   **使用**：`sampler.run([circuit])` 或 `sampler.run([isa_circuit], shots=N)`（单线路也要包在列表里）。
3. **结果读取（v2 风格）**：`job.result()[0].data.meas.get_counts()` 或 `get_bitstrings()`；Estimator 用 `result()[0].data.evs` 等，**与题目 test 一致**。
4. **种子**：用 `SamplerOptions()` / `EstimatorOptions()` 设 `simulator.seed_simulator`，不要传给 `Sampler()` 构造函数。
5. **Transpile**：`pass_manager = generate_preset_pass_manager(optimization_level=..., backend=backend)`；`isa_circuit = pass_manager.run(qc)`；再 `sampler.run([isa_circuit], ...)`。
6. **勿混用** `from qiskit.primitives import Estimator` 除非 prompt 明确只有该 import。

## HumanEval 输出形态（RAG 检索时务必遵守）
- 模型只应输出 **4 空格缩进的函数体**，不要复制下面示例中的 `def` / 顶层 `import`（prompt 已含 import）。
- 检索片段中的完整 `def` 仅作 API 参考，不可原样粘贴到 completion。

## 函数体片段示例（Sampler + Bell + counts）
```python
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()
    backend = AerSimulator()
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa_circuit = pass_manager.run(bell)
    sampler = Sampler(mode=backend)
    result = sampler.run([isa_circuit], shots=1000).result()
    return result[0].data.meas.get_counts()
```

## 函数体片段示例（Estimator + SparsePauliOp）
```python
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    observable = SparsePauliOp(["II", "XX", "YY", "ZZ"])
    backend = AerSimulator()
    estimator = Estimator(mode=backend)
    job = estimator.run([(qc, observable)])
    return job.result()[0].data.evs
```

## 常见错误（Q2 分类器高频）
- `TypeError: SamplerV2.__init__() got an unexpected keyword argument 'backend'`
- `ValueError: invalid Sampler pub-like` → 使用 `sampler.run([circuit])`
- `AttributeError: 'PrimitiveResult' object has no attribute 'data'` → 用 `result()[0].data...` 索引
- `ImportError: cannot import name 'Aer' from 'qiskit'` → 使用 `from qiskit_aer import AerSimulator`

## 检索标签
- sampler
- estimator
- qiskit_ibm_runtime
- aer_simulator
- bell_state
- primitives
- mode_backend
- get_counts

## 适合回答的问题
- Run Bell circuit with Qiskit Sampler and AerSimulator; return counts dictionary.
- How to use Sampler(mode=backend) and sampler.run([circuit]) in Qiskit 2.x?
- Estimator expectation values for Pauli observables on a small circuit.
