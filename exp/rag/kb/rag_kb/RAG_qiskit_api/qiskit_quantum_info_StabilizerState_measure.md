# Qiskit 2.4.1 API: `qiskit.quantum_info.StabilizerState.measure`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.StabilizerState.measure`
- Kind: `method`
- Owner class: `StabilizerState`

## 一句话用途
Measure subsystems and return outcome and post-measure state.

## 功能说明
Measure subsystems and return outcome and post-measure state.

Note that this function uses the QuantumStates internal random
number generator for sampling the measurement outcome. The RNG
seed can be set using the :meth:`seed` method.

Args:
    qargs (list or None): subsystems to sample measurements for,
                          if None sample measurement of all
                          subsystems (Default: None).

Returns:
    tuple: the pair ``(outcome, state)`` where ``outcome`` is the
           measurement outcome string label, and ``state`` is the
           collapsed post-measurement stabilizer state for the
           corresponding outcome.

## 函数签名
```python
(self, qargs: 'list | None' = None) -> 'tuple'
```

## 相关量子编程概念
- measurement

## 检索标签
- circuit_construction
- measurement
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.StabilizerState.measure` 怎么用？
- `measure` 的参数是什么？
- Qiskit 2.4.1 中 `measure` 的最小示例是什么？
