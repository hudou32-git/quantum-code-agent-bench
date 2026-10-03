# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.equiv`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.equiv`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Return True if other is equivalent as a statevector up to global phase.

## 功能说明
Return True if other is equivalent as a statevector up to global phase.

.. note::

    If other is not a Statevector, but can be used to initialize a statevector object,
    this will check that Statevector(other) is equivalent to the current statevector up
    to global phase.

Args:
    other (Statevector): an object from which a ``Statevector`` can be constructed.
    rtol (float): relative tolerance value for comparison.
    atol (float): absolute tolerance value for comparison.

Returns:
    bool: True if statevectors are equivalent up to global phase.

## 函数签名
```python
(self, other: 'Statevector', rtol: 'float | None' = None, atol: 'float | None' = None) -> 'bool'
```

## 相关量子编程概念
- simulation
- state simulation
- state vector
- 态向量

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.equiv` 怎么用？
- `equiv` 的参数是什么？
- Qiskit 2.4.1 中 `equiv` 的最小示例是什么？
