# Qiskit 2.4.1 API: `qiskit.quantum_info.operators.measures.average_gate_fidelity`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info.operators.measures`
- API: `qiskit.quantum_info.operators.measures.average_gate_fidelity`
- Kind: `function`

## 一句话用途
Return the average gate fidelity of a noisy quantum channel.

## 功能说明
Return the average gate fidelity of a noisy quantum channel.

The average gate fidelity :math:`F_{\text{ave}}` is given by

.. math::
    \begin{aligned}
    F_{\text{ave}}(\mathcal{E}, U)
        &= \int d\psi \langle\psi|U^\dagger
            \mathcal{E}(|\psi\rangle\!\langle\psi|)U|\psi\rangle \\
        &= \frac{d F_{\text{pro}}(\mathcal{E}, U) + 1}{d + 1}
    \end{aligned}

where :math:`F_{\text{pro}}(\mathcal{E}, U)` is the
:meth:`~qiskit.quantum_info.process_fidelity` of the input quantum
*channel* :math:`\mathcal{E}` with a *target* unitary :math:`U`, and
:math:`d` is the dimension of the *channel*.

Args:
    channel (QuantumChannel or Operator): noisy quantum channel.
    target (Operator or None): target unitary operator.
        If `None` target is the identity operator [Default: None].
    require_cp (bool): check if input and target channels are
                       completely-positive and if non-CP log warning
                       containing negative eigenvalues of Choi-matrix
                       [Default: True].
    require_tp (bool): check if input and target channels are
                       trace-preserving and if non-TP log warning
                       containing negative eigenvalues of partial
                       Choi-matrix :math:`Tr_{\text{out}}[\mathcal{E}] - I`
                       [Default: True].

Returns:
    float: The average gate fidelity :math:`F_{\text{ave}}`.

Raises:
    QiskitError: if the channel and target do not have the same dimensions,
                 or have different input and output dimensions.

## 函数签名
```python
(channel: 'QuantumChannel | Operator', target: 'Operator | None' = None, require_cp: 'bool' = True, require_tp: 'bool' = False) -> 'float'
```

## 相关量子编程概念
- measurement

## 检索标签
- backend_provider
- circuit_construction
- measurement
- quantum_info
- transpilation

## 适合回答的问题
- `qiskit.quantum_info.operators.measures.average_gate_fidelity` 怎么用？
- `average_gate_fidelity` 的参数是什么？
- Qiskit 2.4.1 中 `average_gate_fidelity` 的最小示例是什么？
