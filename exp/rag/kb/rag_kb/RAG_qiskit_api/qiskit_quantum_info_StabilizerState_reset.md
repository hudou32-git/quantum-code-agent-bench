# Qiskit 2.4.1 API: `qiskit.quantum_info.StabilizerState.reset`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.StabilizerState.reset`
- Kind: `method`
- Owner class: `StabilizerState`

## 一句话用途
Reset state or subsystems to the 0-state.

## 功能说明
Reset state or subsystems to the 0-state.

Args:
    qargs (list or None): subsystems to reset, if None all
                          subsystems will be reset to their 0-state
                          (Default: None).

Returns:
    StabilizerState: the reset state.

Additional Information:
    If all subsystems are reset this will return the ground state
    on all subsystems. If only some subsystems are reset this
    function will perform a measurement on those subsystems and
    evolve the subsystems so that the collapsed post-measurement
    states are rotated to the 0-state. The RNG seed for this
    sampling can be set using the :meth:`seed` method.

## 函数签名
```python
(self, qargs: 'list | None' = None) -> 'StabilizerState'
```

## 相关量子编程概念
- measurement

## 检索标签
- circuit_construction
- measurement
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.StabilizerState.reset` 怎么用？
- `reset` 的参数是什么？
- Qiskit 2.4.1 中 `reset` 的最小示例是什么？
