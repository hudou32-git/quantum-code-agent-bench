# Qiskit 2.4.1 API: `qiskit.converters.dag_to_circuit`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.converters`
- API: `qiskit.converters.dag_to_circuit`
- Kind: `function`

## 一句话用途
Build a ``QuantumCircuit`` object from a ``DAGCircuit``.

## 功能说明
Build a ``QuantumCircuit`` object from a ``DAGCircuit``.

This is also accessible as :meth:`.DAGCircuit.to_circuit`.

Args:
    dag (DAGCircuit): the input dag.
    copy_operations (bool): Deep copy the operation objects
        in the :class:`~.DAGCircuit` for the output :class:`~.QuantumCircuit`.
        This should only be set to ``False`` if the input :class:`~.DAGCircuit`
        will not be used anymore as the operations in the output
        :class:`~.QuantumCircuit` will be shared instances and
        modifications to operations in the :class:`~.DAGCircuit` will
        be reflected in the :class:`~.QuantumCircuit` (and vice versa).

Return:
    QuantumCircuit: the circuit representing the input dag.

Example:
    .. plot::
       :alt: Circuit diagram output by the previous code.
       :include-source:

       from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
       from qiskit.dagcircuit import DAGCircuit
       from qiskit.converters import circuit_to_dag
       from qiskit.circuit.library.standard_gates import CHGate, U2Gate, CXGate
       from qiskit.converters import dag_to_circuit

       q = QuantumRegister(3, 'q')
       c = ClassicalRegister(3, 'c')
       circ = QuantumCircuit(q, c)
       circ.h(q[0])
       circ.cx(q[0], q[1])
       circ.measure(q[0], c[0])
       circ.rz(0.5, q[1])
       dag = circuit_to_dag(circ)
       circuit = dag_to_circuit(dag)
       circuit.draw('mpl')

## 函数签名
```python
(dag, copy_operations=True)
```

## 相关量子编程概念
- Bell state / entanglement
- measurement

## 检索标签
- circuit_construction
- conversion
- measurement
- single_qubit_gate
- two_qubit_gate

## 适合回答的问题
- `qiskit.converters.dag_to_circuit` 怎么用？
- `dag_to_circuit` 的参数是什么？
- Qiskit 2.4.1 中 `dag_to_circuit` 的最小示例是什么？
