# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.DensityMatrix.reset`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.DensityMatrix.reset`
- Kind: `method`
- Owner class: `DensityMatrix`

## 一句话用途
Reset state or subsystems to the 0-state.

## 功能说明
Reset state or subsystems to the 0-state.

Args:
    qargs (list or None): subsystems to reset, if None all
                          subsystems will be reset to their 0-state
                          (Default: None).

Returns:
    DensityMatrix: the reset state.

Additional Information:
    If all subsystems are reset this will return the ground state
    on all subsystems. If only some subsystems are reset this
    function will perform evolution by the reset
    :class:`~qiskit.quantum_info.SuperOp` of the reset subsystems.

## 函数签名
```python
(self, qargs: 'list[int] | None' = None) -> 'DensityMatrix'
```

## 相关量子编程概念
- density matrix
- mixed state
- state simulation
- 密度矩阵

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.DensityMatrix.reset` 怎么用？
- `reset` 的参数是什么？
- Qiskit 2.4.1 中 `reset` 的最小示例是什么？
