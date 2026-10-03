# Qiskit 2.4.1 API: `qiskit.quantum_info.StabilizerState.probabilities`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.StabilizerState.probabilities`
- Kind: `method`
- Owner class: `StabilizerState`

## 一句话用途
Return the subsystem measurement probability vector.

## 功能说明
Return the subsystem measurement probability vector.

Measurement probabilities are with respect to measurement in the
computation (diagonal) basis.

Args:
    qargs (None or list): subsystems to return probabilities for,
        if None return for all subsystems (Default: None).
    decimals (None or int): the number of decimal places to round
        values. If None no rounding is done (Default: None).

Returns:
    np.array: The Numpy vector array of probabilities.

## 函数签名
```python
(self, qargs: 'None | list' = None, decimals: 'None | int' = None) -> 'np.ndarray'
```

## 相关量子编程概念
- measurement

## 检索标签
- circuit_construction
- measurement
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.StabilizerState.probabilities` 怎么用？
- `probabilities` 的参数是什么？
- Qiskit 2.4.1 中 `probabilities` 的最小示例是什么？
