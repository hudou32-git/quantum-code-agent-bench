# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.probabilities`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.probabilities`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Return the subsystem measurement probability vector.

## 功能说明
Return the subsystem measurement probability vector.

Measurement probabilities are with respect to measurement in the
computation (diagonal) basis.

Args:
    qargs (None or list): subsystems to return probabilities for,
        if None return for all subsystems (Default: None).
    decimals (None or int): the number of decimal places to round
        values. If None no rounding is done (Default: None).

Returns:
    np.array: The Numpy vector array of probabilities.

Examples:

    Consider a 2-qubit product state
    :math:`|\psi\rangle=|+\rangle\otimes|0\rangle`.

    .. plot::
       :include-source:
       :nofigs:

        from qiskit.quantum_info import Statevector

        psi = Statevector.from_label('+0')

        # Probabilities for measuring both qubits
        probs = psi.probabilities()
        print('probs: {}'.format(probs))

        # Probabilities for measuring only qubit-0
        probs_qubit_0 = psi.probabilities([0])
        print('Qubit-0 probs: {}'.format(probs_qubit_0))

        # Probabilities for measuring only qubit-1
        probs_qubit_1 = psi.probabilities([1])
        print('Qubit-1 probs: {}'.format(probs_qubit_1))

    .. code-block:: text

        probs: [0.5 0.  0.5 0. ]
        Qubit-0 probs: [1. 0.]
        Qubit-1 probs: [0.5 0.5]

    We can also permute the order of qubits in the ``qargs`` list
    to change the qubit position in the probabilities output

    .. plot::
       :include-source:
       :nofigs:

        from qiskit.quantum_info import Statevector

        psi = Statevector.from_label('+0')

        # Probabilities for measuring both qubits
        probs = psi.probabilities([0, 1])
        print('probs: {}'.format(probs))

        # Probabilities for measuring both qubits
        # but swapping qubits 0 and 1 in output
        probs_swapped = psi.probabilities([1, 0])
        print('Swapped probs: {}'.format(probs_swapped))

    .. code-block:: text

        probs: [0.5 0.  0.5 0. ]
        Swapped probs: [0.5 0.5 0.  0. ]

## 函数签名
```python
(self, qargs: 'None | list[int]' = None, decimals: 'None | int' = None) -> 'np.ndarray'
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
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.probabilities` 怎么用？
- `probabilities` 的参数是什么？
- Qiskit 2.4.1 中 `probabilities` 的最小示例是什么？
