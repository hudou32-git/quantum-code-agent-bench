# Qiskit 2.4.1 Recipe: Bell |φ+⟩ 线路 + Aer 仿真 + measurement counts

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `QuantumCircuit`, `AerSimulator`, `backend`, `shots`, `measure`, `circuit`

## 任务描述（HumanEval 风格）
Define a phi plus bell state using Qiskit, run it on a simulator backend with shots, and return measurement counts (or quasi-probability distribution). The circuit uses `QuantumCircuit`, Hadamard on qubit 0, CNOT from 0 to 1, then measure qubits into classical registers.

## Available imports（常见）
- `from qiskit import QuantumCircuit`
- `from qiskit_aer import AerSimulator`

## 实现要点
1. 创建 `QuantumCircuit`（需要 classical bits 时用 `QuantumCircuit(2, 2)` 或 `measure` 到 classical register）。
2. Bell |φ+⟩：`qc.h(0)` 然后 `qc.cx(0, 1)`。
3. 测量：`qc.measure([0, 1], [0, 1])` 或 `qc.measure_all()`（注意 API 版本差异）。
4. 仿真（QHE 数据集主路径）：`backend = AerSimulator()`；`sampler = Sampler(mode=backend)`（需 prompt 已 import `Sampler`）；`sampler.run([qc], shots=...).result()[0].data.meas.get_counts()`。
5. 备选（仅当 prompt 无 Sampler）：`backend.run(qc, shots=1024).result().get_counts()`。
6. **勿**使用 `quasi_dists` 等旧 primitives 字段名，除非题目 test 明确使用。

## 完整示例代码
```python
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

def run_bell_state_simulator():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    backend = AerSimulator()
    result = backend.run(qc, shots=1024).result()
    counts = result.get_counts()
    return counts
```

## 相关量子编程概念
- quantum circuit construction
- bell state
- backend simulation
- measure

## 检索标签
- aer_simulation
- bell_state
- circuit_construction
- get_counts
- qiskit

## 适合回答的问题
- How to run a bell circuit on AerSimulator and get counts?
- Define phi plus bell state and run simulator with shots in Qiskit.
- Task: transpile optional; need exact Qiskit API for measure and backend.run.
