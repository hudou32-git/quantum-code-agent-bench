# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.DensityMatrix.probabilities_dict`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.DensityMatrix.probabilities_dict`
- Kind: `method`
- Owner class: `DensityMatrix`

## 一句话用途
Return the subsystem measurement probability dictionary.

## 功能说明
Return the subsystem measurement probability dictionary.

Measurement probabilities are with respect to measurement in the
computation (diagonal) basis.

This dictionary representation uses a Ket-like notation where the
dictionary keys are qudit strings for the subsystem basis vectors.
If any subsystem has a dimension greater than 10 comma delimiters are
inserted between integers so that subsystems can be distinguished.

Args:
    qargs (None or list): subsystems to return probabilities for,
        if None return for all subsystems (Default: None).
    decimals (None or int): the number of decimal places to round
        values. If None no rounding is done (Default: None).

Returns:
    dict: The measurement probabilities in dict (ket) form.

## 函数签名
```python
(self, qargs: 'None | list' = None, decimals: 'None | int' = None) -> 'dict'
```

## 相关量子编程概念
- density matrix
- measurement
- mixed state
- state simulation
- 密度矩阵

## 检索标签
- circuit_construction
- measurement
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.DensityMatrix.probabilities_dict` 怎么用？
- `probabilities_dict` 的参数是什么？
- Qiskit 2.4.1 中 `probabilities_dict` 的最小示例是什么？
