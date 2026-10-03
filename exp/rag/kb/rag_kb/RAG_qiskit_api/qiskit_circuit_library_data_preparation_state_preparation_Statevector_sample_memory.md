# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.sample_memory`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.sample_memory`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Sample a list of qubit measurement outcomes in the computational basis.

## 功能说明
Sample a list of qubit measurement outcomes in the computational basis.

Args:
    shots (int): number of samples to generate.
    qargs (None or list): subsystems to sample measurements for,
                        if None sample measurement of all
                        subsystems (Default: None).

Returns:
    np.array: list of sampled counts in the order sampled.

Additional Information:

    This function *samples* measurement outcomes using the measure
    :meth:`probabilities` for the current state and `qargs`. It does
    not actually implement the measurement so the current state is
    not modified.

    The seed for random number generator used for sampling can be
    set to a fixed value by using the state's :meth:`seed` method.

## 函数签名
```python
(self, shots: 'int', qargs: 'None | list' = None) -> 'np.ndarray'
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
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.sample_memory` 怎么用？
- `sample_memory` 的参数是什么？
- Qiskit 2.4.1 中 `sample_memory` 的最小示例是什么？
