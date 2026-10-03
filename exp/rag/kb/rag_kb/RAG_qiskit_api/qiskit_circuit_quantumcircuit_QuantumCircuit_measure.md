# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.measure`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.measure`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Measure a quantum bit (``qubit``) in the Z basis into a classical bit (``cbit``).

## 功能说明
Measure a quantum bit (``qubit``) in the Z basis into a classical bit (``cbit``).

When a quantum state is measured, a qubit is projected in the computational (Pauli Z) basis
to either :math:`\lvert 0 \rangle` or :math:`\lvert 1 \rangle`. The classical bit ``cbit``
indicates the result
of that projection as a ``0`` or a ``1`` respectively. This operation is non-reversible.

Args:
    qubit: qubit(s) to measure.
    cbit: classical bit(s) to place the measurement result(s) in.

Returns:
    qiskit.circuit.InstructionSet: handle to the added instructions.

Raises:
    CircuitError: if arguments have bad format.

Examples:
    In this example, a qubit is measured and the result of that measurement is stored in the
    classical bit (usually expressed in diagrams as a double line):

    .. plot::
       :include-source:
       :nofigs:
       :context: reset

       from qiskit import QuantumCircuit
       circuit = QuantumCircuit(1, 1)
       circuit.h(0)
       circuit.measure(0, 0)
       circuit.draw()


    .. code-block:: text

              ┌───┐┌─┐
           q: ┤ H ├┤M├
              └───┘└╥┘
         c: 1/══════╩═
                    0

    It is possible to call ``measure`` with lists of ``qubits`` and ``cbits`` as a shortcut
    for one-to-one measurement. These two forms produce identical results:

    .. plot::
       :include-source:
       :nofigs:
       :context:

       circuit = QuantumCircuit(2, 2)
       circuit.measure([0,1], [0,1])

    .. plot::
       :include-source:
       :nofigs:
       :context:

       circuit = QuantumCircuit(2, 2)
       circuit.measure(0, 0)
       circuit.measure(1, 1)

    Instead of lists, you can use :class:`~qiskit.circuit.QuantumRegister` and
    :class:`~qiskit.circuit.ClassicalRegister` under the same logic.

    .. plot::
       :include-source:
       :nofigs:
       :context: reset

        from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
        qreg = QuantumRegister(2, "qreg")
        creg = ClassicalRegister(2, "creg")
        circuit = QuantumCircuit(qreg, creg)
        circuit.measure(qreg, creg)

    This is equivalent to:

    .. plot::
       :include-source:
       :nofigs:
       :context:

        circuit = QuantumCircuit(qreg, creg)
        circuit.measure(qreg[0], creg[0])
        circuit.measure(qreg[1], creg[1])

## 函数签名
```python
(self, qubit: 'QubitSpecifier', cbit: 'ClbitSpecifier') -> 'InstructionSet'
```

## 使用示例
### 示例 1
```python
from qiskit import QuantumCircuit



qc = QuantumCircuit(1, 1)

qc.h(0)

qc.measure(0, 0)
```

## 相关量子编程概念
- circuit construction
- measurement
- observable / Hamiltonian
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- measurement
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.measure` 怎么用？
- `measure` 的参数是什么？
- Qiskit 2.4.1 中 `measure` 的最小示例是什么？
