# Qiskit 2.4.1 Recipe: QuantumCircuit 构图模式（Bell / GHZ / measure / compose）

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `QuantumCircuit`, `gate`, `qubit`, `measure`, `circuit`, `compose`

## 任务描述（HumanEval 风格）
Generate or complete a `QuantumCircuit` for n qubits: Bell states, GHZ states, prepare |1⟩ on a register, add barriers, apply standard gates (h, x, cx, cz, swap), measure to classical bits, or `compose` another circuit inline. HumanEval prompts often ask only for the function body that appends gates after a partial definition.

## HumanEval / QHE 输出契约（RAG 注入时必读）
- Completion 只能是 **4 空格缩进的函数体**；**不要**输出 `import`、`def`、markdown 代码块、`if __name__` 或测试代码。
- 下文「完整示例」中的 `def` 仅说明 API；模型应只生成 `def` **内部** 等价语句。

## Available imports（常见）
- `from qiskit import QuantumCircuit`
- `from qiskit import QuantumRegister, ClassicalRegister`（若 prompt 已创建 register 则勿重复）

## 实现要点
1. **Bell |φ+⟩（2 qubit）**：`qc.h(0)`；`qc.cx(0, 1)`。
2. **GHZ（n qubit）**：`qc.h(0)`；对 `i in range(n-1): qc.cx(i, i+1)`；需要时 `qc.measure_all()`。
3. **制备 |1⟩**：`qc.x(qubit_index)` 或 `qc.reset` 后 `x`（按题目要求）。
4. **测量**：`qc.measure(qubit, clbit)` 或 `qc.measure([...], [...])`；`measure_all()` 会添加 classical register（若尚未存在）。
5. **compose**：`qc.compose(other_circuit, inplace=True)` 或 `qc = qc.compose(other)`。
6. **SWAP from CX**：三次 `cx` 是常见考点；也可用 `qc.swap(i, j)` 若 backend basis 允许。

## 完整示例代码（GHZ + measure）
```python
from qiskit import QuantumCircuit

def create_ghz(n_qubits: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    qc.measure(range(n_qubits), range(n_qubits))
    return qc
```

## 完整示例代码（n-qubit QuantumCircuit 空壳）
```python
from qiskit import QuantumCircuit

def create_quantum_circuit(n_qubits: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits)
    return qc
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- single-qubit gate
- two-qubit gate
- measure

## 检索标签
- circuit_construction
- quantumcircuit
- bell
- ghz
- measure
- qiskit

## 适合回答的问题
- Generate a QuantumCircuit for n_qubits and return it.
- Build GHZ state circuit and measure it.
- Design SWAP using only CX gates on QuantumCircuit.
