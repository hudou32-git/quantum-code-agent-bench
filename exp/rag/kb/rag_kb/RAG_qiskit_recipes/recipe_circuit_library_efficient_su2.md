# Qiskit 2.4.1 Recipe: circuit_library EfficientSU2 / 预制 ansatz

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Kind: `task_recipe`
- Topics: `circuit_library`, `QuantumCircuit`, `gate`, `ansatz`

## 任务描述（HumanEval 风格）
Generate an `EfficientSU2` (or `efficient_su2`) circuit with given `num_qubits`, `reps`, and options such as `insert_barriers=True`. Return the circuit object.

## Available imports（常见）
- `from qiskit.circuit.library import efficient_su2` 或 `EfficientSU2`
- `from qiskit.circuit.library import EfficientSU2`

## 实现要点
1. 使用库函数：`from qiskit.circuit.library import efficient_su2` → `qc = efficient_su2(num_qubits=3, reps=1, insert_barriers=True)`。
2. 或类构造：`EfficientSU2(num_qubits=3, reps=1, insert_barriers=True)`。
3. 参数名以 prompt 为准：`entanglement`, `su2_gates` 等可选。
4. 返回 `QuantumCircuit` 实例，勿 transpile 除非题目要求。

## 完整示例代码
```python
from qiskit.circuit.library import efficient_su2

def create_efficient_su2():
    qc = efficient_su2(
        num_qubits=3,
        reps=1,
        insert_barriers=True,
    )
    return qc
```

## 相关量子编程概念
- circuit library
- ansatz
- quantum circuit

## 检索标签
- circuit_library
- efficientsu2
- ansatz
- qiskit

## 适合回答的问题
- Generate EfficientSU2 circuit with 3 qubits, 1 reps, insert_barriers true.
- How to use qiskit.circuit.library efficient_su2?
- Task needs circuit_library API not manual gate list.
