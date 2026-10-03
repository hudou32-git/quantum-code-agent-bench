# Qiskit 2.4.1 API: `qiskit.converters.circuit_to_instruction`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.converters`
- API: `qiskit.converters.circuit_to_instruction`
- Kind: `function`

## 一句话用途
Build an :class:`~.circuit.Instruction` object from a :class:`.QuantumCircuit`.

## 功能说明
Build an :class:`~.circuit.Instruction` object from a :class:`.QuantumCircuit`.

The instruction is anonymous (not tied to a named quantum register),
and so can be inserted into another circuit. The instruction will
have the same string name as the circuit.

Args:
    circuit (QuantumCircuit): the input circuit.
    parameter_map (dict): For parameterized circuits, a mapping from
       parameters in the circuit to parameters to be used in the instruction.
       If None, existing circuit parameters will also parameterize the
       instruction.
    equivalence_library (EquivalenceLibrary): Optional equivalence library
       where the converted instruction will be registered.
    label (str): Optional instruction label.

Raises:
    QiskitError: if parameter_map is not compatible with circuit

Return:
    qiskit.circuit.Instruction: an instruction equivalent to the action of the
    input circuit. Upon decomposition, this instruction will
    yield the components comprising the original circuit.

Example:
    .. plot::
        :include-source:
        :nofigs:

        from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
        from qiskit.converters import circuit_to_instruction

        q = QuantumRegister(3, 'q')
        c = ClassicalRegister(3, 'c')
        circ = QuantumCircuit(q, c)
        circ.h(q[0])
        circ.cx(q[0], q[1])
        circ.measure(q[0], c[0])
        circ.rz(0.5, q[1])
        circuit_to_instruction(circ)

## 函数签名
```python
(circuit, parameter_map=None, equivalence_library=None, label=None)
```

## 相关量子编程概念
- Bell state / entanglement
- measurement
- parameterized circuit

## 检索标签
- circuit_construction
- conversion
- measurement
- parameterized_circuit
- single_qubit_gate
- two_qubit_gate

## 适合回答的问题
- `qiskit.converters.circuit_to_instruction` 怎么用？
- `circuit_to_instruction` 的参数是什么？
- Qiskit 2.4.1 中 `circuit_to_instruction` 的最小示例是什么？
