# Qiskit 2.4.1 API: `qiskit.quantum_info.states.purity`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info.states`
- API: `qiskit.quantum_info.states.purity`
- Kind: `function`

## 一句话用途
Calculate the purity of a quantum state.

## 功能说明
Calculate the purity of a quantum state.

The purity of a density matrix :math:`\rho` is

.. math::

    \text{Purity}(\rho) = Tr[\rho^2]

Args:
    state (Statevector or DensityMatrix): a quantum state.
    validate (bool): check if input state is valid [Default: True]

Returns:
    float: the purity :math:`Tr[\rho^2]`.

Raises:
    QiskitError: if the input isn't a valid quantum state.

## 函数签名
```python
(state: 'Statevector | DensityMatrix', validate: 'bool' = True) -> 'float'
```

## 相关量子编程概念
- state simulation

## 检索标签
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.states.purity` 怎么用？
- `purity` 的参数是什么？
- Qiskit 2.4.1 中 `purity` 的最小示例是什么？
