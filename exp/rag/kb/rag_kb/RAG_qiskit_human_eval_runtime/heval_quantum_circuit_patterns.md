# HumanEval-Qiskit: QuantumCircuit 写法与 quantum_info

## 基本信息
- Kind: `human_eval_runtime_stack`
- Topics: `QuantumCircuit`, `Operator`, `Statevector`, `cx`, `measure`

## API 习惯（Qiskit 2.x）
- 两比特门：`qc.cx(0, 1)` 或 `qc.cx([...], [...])`；**无** `qc.cnot` 方法。
- 测量：`qc.measure(q, c)`、`qc.measure_all()`；**勿**对 `InstructionSet` 使用已移除的 `.c_if` 链式旧 API。
- 参数门：`qc.u(theta, phi, lam, qubit)`；`qc.ry`, `qc.rz` 等。

## Operator / 矩阵题
- `from qiskit.quantum_info import Operator`：`return Operator(qc).data` 或题目要求的 numpy 数组。
- **无** `QuantumCircuit.to_operator()`；用 `Operator(qc)`。

## compose / append
- `qc.compose(other, inplace=True)`、`qc.append(gate, qargs, cargs)` 按题目。

## 检索标签
- quantumcircuit
- operator
- statevector
- cx
- measure_all
- unitary matrix

## 适合回答的问题
- Get unitary matrix for bell circuit return Operator data.
- Custom U gate with angles pi/2 on QuantumCircuit.
- Build circuit with cx gates for HumanEval function body.
