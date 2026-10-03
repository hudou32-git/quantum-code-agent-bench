# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.reset`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.reset`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Reset state or subsystems to the 0-state.

## 功能说明
Reset state or subsystems to the 0-state.

Args:
    qargs (list or None): subsystems to reset, if None all
                          subsystems will be reset to their 0-state
                          (Default: None).

Returns:
    Statevector: the reset state.

Additional Information:
    If all subsystems are reset this will return the ground state
    on all subsystems. If only some subsystems are reset this
    function will perform a measurement on those subsystems and
    evolve the subsystems so that the collapsed post-measurement
    states are rotated to the 0-state. The RNG seed for this
    sampling can be set using the :meth:`seed` method.

## 函数签名
```python
(self, qargs: 'list[int] | None' = None) -> 'Statevector'
```

## 相关量子编程概念
- measurement
- simulation
- state simulation
- state vector
- 态向量

## 检索标签
- circuit_construction
- measurement
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.reset` 怎么用？
- `reset` 的参数是什么？
- Qiskit 2.4.1 中 `reset` 的最小示例是什么？
