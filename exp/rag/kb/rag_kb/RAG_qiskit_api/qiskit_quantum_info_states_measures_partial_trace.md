# Qiskit 2.4.1 API: `qiskit.quantum_info.states.measures.partial_trace`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info.states.measures`
- API: `qiskit.quantum_info.states.measures.partial_trace`
- Kind: `function`

## 一句话用途
Return reduced density matrix by tracing out part of quantum state.

## 功能说明
Return reduced density matrix by tracing out part of quantum state.

If all subsystems are traced over this returns the
:meth:`~qiskit.quantum_info.DensityMatrix.trace` of the
input state.

Args:
    state (Statevector or DensityMatrix): the input state.
    qargs (list): The subsystems to trace over.

Returns:
    DensityMatrix: The reduced density matrix.

Raises:
    QiskitError: if input state is invalid.

## 函数签名
```python
(state: 'Statevector | DensityMatrix', qargs: 'list') -> 'DensityMatrix'
```

## 相关量子编程概念
- measurement
- state simulation

## 检索标签
- circuit_construction
- measurement
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.states.measures.partial_trace` 怎么用？
- `partial_trace` 的参数是什么？
- Qiskit 2.4.1 中 `partial_trace` 的最小示例是什么？
