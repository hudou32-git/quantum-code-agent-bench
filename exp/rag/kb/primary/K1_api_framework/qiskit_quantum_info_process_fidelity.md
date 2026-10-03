# Qiskit 2.4.1 API: `qiskit.quantum_info.process_fidelity`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.process_fidelity`
- Kind: `function`

## 一句话用途
Return the process fidelity of a noisy quantum channel.

## 功能说明
Return the process fidelity of a noisy quantum channel.


The process fidelity :math:`F_{\text{pro}}(\mathcal{E}, \mathcal{F})`
between two quantum channels :math:`\mathcal{E}, \mathcal{F}` is given by

.. math::
    F_{\text{pro}}(\mathcal{E}, \mathcal{F})
        = F(\rho_{\mathcal{E}}, \rho_{\mathcal{F}})

where :math:`F` is the :func:`~qiskit.quantum_info.state_fidelity`,
:math:`\rho_{\mathcal{E}} = \Lambda_{\mathcal{E}} / d` is the
normalized :class:`~qiskit.quantum_info.Choi` matrix for the channel
:math:`\mathcal{E}`, and :math:`d` is the input dimension of
:math:`\mathcal{E}`.

When the target channel is unitary this is equivalent to

.. math::
    F_{\text{pro}}(\mathcal{E}, U)
        = \frac{Tr[S_U^\dagger S_{\mathcal{E}}]}{d^2}

where :math:`S_{\mathcal{E}}, S_{U}` are the
:class:`~qiskit.quantum_info.SuperOp` matrices for the *input* quantum
channel :math:`\mathcal{E}` and *target* unitary :math:`U` respectively,
and :math:`d` is the input dimension of the channel.

Args:
    channel (Operator or QuantumChannel): input quantum channel.
    target (Operator or QuantumChannel or None): target quantum channel.
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
    float: The process fidelity :math:`F_{\text{pro}}`.

Raises:
    QiskitError: if the channel and target do not have the same dimensions.

## 函数签名
```python
(channel: 'Operator | QuantumChannel', target: 'Operator | QuantumChannel | None' = None, require_cp: 'bool' = True, require_tp: 'bool' = True) -> 'float'
```

## 检索标签
- backend_provider
- quantum_info
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.quantum_info.process_fidelity` 怎么用？
- `process_fidelity` 的参数是什么？
- Qiskit 2.4.1 中 `process_fidelity` 的最小示例是什么？
