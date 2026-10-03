# Qiskit 2.4.1 API: `qiskit.providers.basic_provider.basic_simulator.StabilizerState`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.providers.basic_provider.basic_simulator`
- API: `qiskit.providers.basic_provider.basic_simulator.StabilizerState`
- Kind: `class`

## 一句话用途
StabilizerState class. Stabilizer simulator using the convention from reference [1]. Based on the internal class :class:`~qiskit.quantum_info.Clifford`.

## 功能说明
StabilizerState class.
Stabilizer simulator using the convention from reference [1].
Based on the internal class :class:`~qiskit.quantum_info.Clifford`.

.. plot::
   :include-source:
   :nofigs:

    from qiskit import QuantumCircuit
    from qiskit.quantum_info import StabilizerState, Pauli

    # Bell state generation circuit
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    stab = StabilizerState(qc)

    # Print the StabilizerState
    print(stab)

    # Calculate the StabilizerState measurement probabilities dictionary
    print (stab.probabilities_dict())

    # Calculate expectation value of the StabilizerState
    print (stab.expectation_value(Pauli('ZZ')))

.. code-block:: text

    StabilizerState(StabilizerTable: ['+XX', '+ZZ'])
    {'00': 0.5, '11': 0.5}
    1

Given a list of stabilizers, :meth:`qiskit.quantum_info.StabilizerState.from_stabilizer_list`
returns a state stabilized by the list

.. plot::
   :include-source:
   :nofigs:

    from qiskit.quantum_info import StabilizerState

    stabilizer_list = ["ZXX", "-XYX", "+ZYY"]
    stab = StabilizerState.from_stabilizer_list(stabilizer_list)


References:
    1. S. Aaronson, D. Gottesman, *Improved Simulation of Stabilizer Circuits*,
       Phys. Rev. A 70, 052328 (2004).
       `arXiv:quant-ph/0406196 <https://arxiv.org/abs/quant-ph/0406196>`_

## 函数签名
```python
(data: 'StabilizerState | Clifford | Pauli | QuantumCircuit | circuit.instruction.Instruction', validate: 'bool' = True)
```

## 相关量子编程概念
- Bell state / entanglement
- measurement
- observable / Hamiltonian

## 检索标签
- backend_provider
- circuit_construction
- measurement
- observable_hamiltonian
- quantum_info
- single_qubit_gate
- two_qubit_gate

## 适合回答的问题
- `qiskit.providers.basic_provider.basic_simulator.StabilizerState` 怎么用？
- `StabilizerState` 的参数是什么？
- Qiskit 2.4.1 中 `StabilizerState` 的最小示例是什么？
