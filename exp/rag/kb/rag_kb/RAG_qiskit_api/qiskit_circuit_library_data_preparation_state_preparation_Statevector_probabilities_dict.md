# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.probabilities_dict`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.probabilities_dict`
- Kind: `method`
- Owner class: `Statevector`

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
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.probabilities_dict` 怎么用？
- `probabilities_dict` 的参数是什么？
- Qiskit 2.4.1 中 `probabilities_dict` 的最小示例是什么？
