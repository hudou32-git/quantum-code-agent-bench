# Qiskit 2.4.1 API: `qiskit.quantum_info.states.measures.mutual_information`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info.states.measures`
- API: `qiskit.quantum_info.states.measures.mutual_information`
- Kind: `function`

## 一句话用途
Calculate the mutual information of a bipartite state.

## 功能说明
Calculate the mutual information of a bipartite state.

The mutual information :math:`I` is given by:

.. math::

    I(\rho_{AB}) = S(\rho_A) + S(\rho_B) - S(\rho_{AB})

where :math:`\rho_A=Tr_B[\rho_{AB}], \rho_B=Tr_A[\rho_{AB}]`, are the
reduced density matrices of the bipartite state :math:`\rho_{AB}`.

Args:
    state (Statevector or DensityMatrix): a bipartite state.
    base (int): the base of the logarithm [Default: 2].

Returns:
    float: The mutual information :math:`I(\rho_{AB})`.

Raises:
    QiskitError: if the input state is not a valid QuantumState.
    QiskitError: if input is not a bipartite QuantumState.

## 函数签名
```python
(state: 'Statevector | DensityMatrix', base: 'int' = 2) -> 'float'
```

## 相关量子编程概念
- measurement
- state simulation

## 检索标签
- circuit_construction
- measurement
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.states.measures.mutual_information` 怎么用？
- `mutual_information` 的参数是什么？
- Qiskit 2.4.1 中 `mutual_information` 的最小示例是什么？
