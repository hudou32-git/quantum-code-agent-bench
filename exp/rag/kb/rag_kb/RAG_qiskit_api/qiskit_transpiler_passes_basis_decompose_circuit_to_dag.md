# Qiskit 2.4.1 API: `qiskit.transpiler.passes.basis.decompose.circuit_to_dag`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler.passes.basis.decompose`
- API: `qiskit.transpiler.passes.basis.decompose.circuit_to_dag`
- Kind: `function`

## 一句话用途
Build a :class:`.DAGCircuit` object from a :class:`.QuantumCircuit`.

## 功能说明
Build a :class:`.DAGCircuit` object from a :class:`.QuantumCircuit`.

This is also accessible as :meth:`.QuantumCircuit.to_dag`.

Args:
    circuit (QuantumCircuit): the input circuit.
    copy_operations (bool): Deep copy the operation objects
        in the :class:`~.QuantumCircuit` for the output :class:`~.DAGCircuit`.
        This should only be set to ``False`` if the input :class:`~.QuantumCircuit`
        will not be used anymore as the operations in the output
        :class:`~.DAGCircuit` will be shared instances and modifications to
        operations in the :class:`~.DAGCircuit` will be reflected in the
        :class:`~.QuantumCircuit` (and vice versa).
    qubit_order (Iterable[~qiskit.circuit.Qubit] or None): the order that the qubits should be
        indexed in the output DAG.  Defaults to the same order as in the circuit.
    clbit_order (Iterable[Clbit] or None): the order that the clbits should be indexed in the
        output DAG.  Defaults to the same order as in the circuit.

Return:
    DAGCircuit: the DAG representing the input circuit.

Raises:
    ValueError: if the ``qubit_order`` or ``clbit_order`` parameters do not match the bits in
        the circuit.

Example:
    .. plot::
        :include-source:
        :nofigs:

        from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
        from qiskit.dagcircuit import DAGCircuit
        from qiskit.converters import circuit_to_dag

        q = QuantumRegister(3, 'q')
        c = ClassicalRegister(3, 'c')
        circ = QuantumCircuit(q, c)
        circ.h(q[0])
        circ.cx(q[0], q[1])
        circ.measure(q[0], c[0])
        circ.rz(0.5, q[1])
        dag = circuit_to_dag(circ)

## 函数签名
```python
(circuit, copy_operations=True, *, qubit_order=None, clbit_order=None)
```

## 相关量子编程概念
- Bell state / entanglement
- measurement
- parameterized circuit
- transpilation

## 检索标签
- circuit_construction
- conversion
- measurement
- parameterized_circuit
- single_qubit_gate
- transpilation
- two_qubit_gate

## 适合回答的问题
- `qiskit.transpiler.passes.basis.decompose.circuit_to_dag` 怎么用？
- `circuit_to_dag` 的参数是什么？
- Qiskit 2.4.1 中 `circuit_to_dag` 的最小示例是什么？
