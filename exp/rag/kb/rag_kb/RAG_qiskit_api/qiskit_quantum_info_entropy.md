# Qiskit 2.4.1 API: `qiskit.quantum_info.entropy`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.entropy`
- Kind: `function`

## 一句话用途
Calculate the von-Neumann entropy of a quantum state.

## 功能说明
Calculate the von-Neumann entropy of a quantum state.

The entropy :math:`S` is given by

.. math::

    S(\rho) = - Tr[\rho \log(\rho)]

Args:
    state (Statevector or DensityMatrix): a quantum state.
    base (int): the base of the logarithm [Default: 2].

Returns:
    float: The von-Neumann entropy S(rho).

Raises:
    QiskitError: if the input state is not a valid QuantumState.

## 函数签名
```python
(state: 'Statevector | DensityMatrix', base: 'int' = 2) -> 'float'
```

## 相关量子编程概念
- state simulation

## 检索标签
- quantum_info

## 适合回答的问题
- `qiskit.quantum_info.entropy` 怎么用？
- `entropy` 的参数是什么？
- Qiskit 2.4.1 中 `entropy` 的最小示例是什么？
