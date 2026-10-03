# Qiskit 2.4.1 API: `qiskit.quantum_info.states.measures.concurrence`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info.states.measures`
- API: `qiskit.quantum_info.states.measures.concurrence`
- Kind: `function`

## 一句话用途
Calculate the concurrence of a quantum state.

## 功能说明
Calculate the concurrence of a quantum state.

The concurrence of a bipartite
:class:`~qiskit.quantum_info.Statevector` :math:`|\psi\rangle` is
given by

.. math::

    C(|\psi\rangle) = \sqrt{2(1 - Tr[\rho_0^2])}

where :math:`\rho_0 = Tr_1[|\psi\rangle\!\langle\psi|]` is the
reduced state by taking the
:func:`~qiskit.quantum_info.partial_trace` of the input state.

For density matrices the concurrence is only defined for
2-qubit states, it is given by:

.. math::

    C(\rho) = \max(0, \lambda_1 - \lambda_2 - \lambda_3 - \lambda_4)

where  :math:`\lambda _1 \ge \lambda _2 \ge \lambda _3 \ge \lambda _4`
are the ordered eigenvalues of the matrix
:math:`R=\sqrt{\sqrt{\rho }(Y\otimes Y)\overline{\rho}(Y\otimes Y)\sqrt{\rho}}`.

Args:
    state (Statevector or DensityMatrix): a 2-qubit quantum state.

Returns:
    float: The concurrence.

Raises:
    QiskitError: if the input state is not a valid QuantumState.
    QiskitError: if input is not a bipartite QuantumState.
    QiskitError: if density matrix input is not a 2-qubit state.

## 函数签名
```python
(state: 'Statevector | DensityMatrix') -> 'float'
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
- `qiskit.quantum_info.states.measures.concurrence` 怎么用？
- `concurrence` 的参数是什么？
- Qiskit 2.4.1 中 `concurrence` 的最小示例是什么？
