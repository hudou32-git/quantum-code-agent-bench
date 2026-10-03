# Qiskit 2.4.1 Recipe: Statevector / quantum_info 制备 Bell 与向量

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `Statevector`, `quantum_info`, `Operator`, `circuit`, `qubit`

## 任务描述（HumanEval 风格）
Return a Bell statevector (|φ+⟩ or |φ−⟩) using `qiskit.quantum_info.Statevector` from a small `QuantumCircuit`, or build the statevector directly from amplitudes. Prompts mention "phi plus bell statevector" without always running a backend.

**HumanEval 栈注意**：若题目 prompt **未** import `Sampler` / `qiskit_ibm_runtime`，只使用 `Statevector` / `Operator` 等 quantum_info 路径，**不要**套用依赖 Sampler 或 Aer 采样的流程（避免 API 栈误用，属 L2 类问题；函数体输出格式由 QHE+RAG 契约约束）。

## Available imports（常见）
- `from qiskit import QuantumCircuit`
- `from qiskit.quantum_info import Statevector`
- `from math import sqrt`

## 实现要点
1. 用线路：`qc = QuantumCircuit(2)`；`qc.h(0)`；`qc.cx(0,1)`；`sv = Statevector(qc)`。
2. |φ+⟩ 振幅：`( |00⟩ + |11⟩ ) / √2`；可用 `Statevector.from_label('00')` 等组合（视版本 API）。
3. 若题目要 |φ−⟩：在 Bell 步骤后加 `qc.z(1)` 或等价相位。
4. 返回 `Statevector` 对象，不要混用 `Aer` counts。

## 完整示例代码
```python
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

def create_bell_statevector() -> Statevector:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return Statevector(qc)
```

## 相关量子编程概念
- statevector
- quantum circuit
- bell state

## 检索标签
- statevector
- quantum_info
- bell_state
- qiskit

## 适合回答的问题
- Return a phi plus Bell statevector using Statevector.
- How to construct Statevector from QuantumCircuit for entangled state?
- Task needs exact Qiskit quantum_info API without simulator shots.
