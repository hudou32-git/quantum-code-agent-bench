# Qiskit 2.4.1 API: `qiskit.quantum_info.state_fidelity`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.state_fidelity`
- Kind: `function`

## 一句话用途
Return the state fidelity between two quantum states.

## 功能说明
Return the state fidelity between two quantum states.

The state fidelity :math:`F` for density matrix input states
:math:`\rho_1, \rho_2` is given by

.. math::
    F(\rho_1, \rho_2) = Tr[\sqrt{\sqrt{\rho_1}\rho_2\sqrt{\rho_1}}]^2.

If one of the states is a pure state this simplifies to
:math:`F(\rho_1, \rho_2) = \langle\psi_1|\rho_2|\psi_1\rangle`, where
:math:`\rho_1 = |\psi_1\rangle\!\langle\psi_1|`.

Args:
    state1 (Statevector or DensityMatrix): the first quantum state.
    state2 (Statevector or DensityMatrix): the second quantum state.
    validate (bool): check if the inputs are valid quantum states
                     [Default: True]

Returns:
    float: The state fidelity :math:`F(\rho_1, \rho_2)`.

Raises:
    QiskitError: if ``validate=True`` and the inputs are invalid quantum states.

## 函数签名
```python
(state1: 'Statevector | DensityMatrix', state2: 'Statevector | DensityMatrix', validate: 'bool' = True) -> 'float'
```

## 相关量子编程概念
- state simulation

## 检索标签
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.state_fidelity` 怎么用？
- `state_fidelity` 的参数是什么？
- Qiskit 2.4.1 中 `state_fidelity` 的最小示例是什么？
