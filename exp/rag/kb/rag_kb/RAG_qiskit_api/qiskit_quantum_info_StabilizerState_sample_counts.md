# Qiskit 2.4.1 API: `qiskit.quantum_info.StabilizerState.sample_counts`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.StabilizerState.sample_counts`
- Kind: `method`
- Owner class: `StabilizerState`

## 一句话用途
Sample a dict of qubit measurement outcomes in the computational basis.

## 功能说明
Sample a dict of qubit measurement outcomes in the computational basis.

Args:
    shots (int): number of samples to generate.
    qargs (None or list): subsystems to sample measurements for,
                        if None sample measurement of all
                        subsystems (Default: None).

Returns:
    Counts: sampled counts dictionary.

Additional Information:

    This function *samples* measurement outcomes using the measure
    :meth:`probabilities` for the current state and `qargs`. It does
    not actually implement the measurement so the current state is
    not modified.

    The seed for random number generator used for sampling can be
    set to a fixed value by using the state's :meth:`seed` method.

## 函数签名
```python
(self, shots: 'int', qargs: 'None | list' = None) -> 'Counts'
```

## 相关量子编程概念
- measurement

## 检索标签
- circuit_construction
- measurement
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.StabilizerState.sample_counts` 怎么用？
- `sample_counts` 的参数是什么？
- Qiskit 2.4.1 中 `sample_counts` 的最小示例是什么？
