# Qiskit 2.4.1 Recipe: OpenQASM 2 导出 / 解析 QuantumCircuit

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `qasm`, `QuantumCircuit`, `circuit`

## 任务描述（HumanEval 风格）
Export a `QuantumCircuit` to OpenQASM 2 string, or load a circuit from QASM text / file. Tasks mention `qasm2`, `qasm3`, or `QuantumCircuit.from_qasm_str`.

## Available imports（常见）
- `from qiskit import QuantumCircuit`
- `from qiskit.qasm2 import dumps, loads`（Qiskit 2.x 路径以 prompt 为准）
- 或 `qc.qasm()`（旧 API，勿与 prompt 冲突）

## 实现要点
1. 导出：构建线路后 `dumps(qc)` 或题目指定的 `export` 函数。
2. 导入：`loads(qasm_string)` 或 `QuantumCircuit.from_qasm_str(qasm_string)`。
3. 含 `measure` 的线路导出时注意 classical register 声明。
4. 返回类型：字符串或 `QuantumCircuit`，按函数签名。

## 完整示例代码
```python
from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps, loads

def roundtrip_bell_qasm() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    qasm_str = dumps(qc)
    return loads(qasm_str)
```

## 检索标签
- qasm
- openqasm
- quantumcircuit
- qiskit

## 适合回答的问题
- Export QuantumCircuit to QASM string and load it back.
- How to use qiskit qasm2 dumps loads for a bell circuit?
