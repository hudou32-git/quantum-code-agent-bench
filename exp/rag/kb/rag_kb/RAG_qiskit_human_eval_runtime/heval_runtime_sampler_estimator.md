# HumanEval-Qiskit: qiskit_ibm_runtime Sampler / Estimator（mode= 栈）

## 基本信息
- Framework: Qiskit HumanEval (QHE)
- Version: Qiskit 2.4.1 + qiskit-ibm-runtime 0.45.x
- Kind: `human_eval_runtime_stack`
- Topics: `Sampler`, `Estimator`, `mode`, `AerSimulator`, `sampler.run`, `transpile`

## 何时使用本文
Prompt 的 **Available imports** 含 `from qiskit_ibm_runtime import Sampler` 或 `Estimator`，且题目要求 Aer 仿真、counts、bitstrings 或 expectation values。

## 标准流程（Sampler + transpile）— 请优先照此写代码
1. 建 `QuantumCircuit`，`measure_all()` 若题目要 counts。
2. `backend = AerSimulator()`（或 fake + `AerSimulator.from_backend(fake_device)`）。
3. `pass_manager = generate_preset_pass_manager(optimization_level=..., backend=backend)`（题目指定 level）。
4. `isa_circuit = pass_manager.run(qc)`。
5. `sampler = Sampler(mode=backend)`。
6. `result = sampler.run([isa_circuit], shots=...).result()`。
7. `return result[0].data.meas.get_counts()` 或 `get_bitstrings()`。

## Estimator
- `estimator = Estimator(mode=AerSimulator())`。
- `estimator.run([(qc, observable)])`；observable 常为 `SparsePauliOp`（prompt 已 import 时用）。
- 返回 `job.result()[0].data.evs` 等与 test 一致的结构。

## 函数体片段（HumanEval：仅缩进体，勿复制 def）
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

## 常见 Q2 异常对照
- `TypeError: SamplerV2.__init__() got an unexpected keyword argument 'backend'` → 改用 `mode=`
- `ValueError: An invalid Sampler pub-like` → `run([circuit])`
- `AttributeError: 'DataBin' object has no attribute 'meas'` → 用 `job.result()[0].data.meas.get_counts()`
- `ValidationError` on `SamplerOptions` → 勿用未文档化字段；种子用 `options.simulator.seed_simulator`

## 勿使用的旧 API（禁止照抄到代码中）

以下仅作排错对照，**不要**在生成代码中书写「禁止」列写法：

| 禁止 | 应使用 |
|------|--------|
| `Sampler(backend=...)` / `Sampler(simulator=...)` / `Sampler(seed=...)` | `sampler = Sampler(mode=backend)` |
| `sampler.run(circuit)` 单对象 | `sampler.run([circuit])` |
| `from qiskit import Aer` | `from qiskit_aer import AerSimulator`（仅当 prompt 已 import） |
| `from qiskit.primitives import Sampler` 当 prompt 已是 runtime | 只用 prompt 里的 `qiskit_ibm_runtime` |
| `result.quasi_dists` / 旧式 `get_counts()` on primitive result | `job.result()[0].data.meas.get_counts()` |

## 检索标签
- qiskit_ibm_runtime
- sampler
- estimator
- mode_backend
- aer_simulator
- sampler.run
- get_counts
- get_bitstrings
- generate_preset_pass_manager

## 适合回答的问题
- Run Bell circuit with Qiskit Sampler and Aer simulator; return counts dictionary.
- Need exact Qiskit API calls for Sampler(mode=backend) and sampler.run([circuit]).
- Transpile with pass manager optimization level 1 then run on Sampler.
