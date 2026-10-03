# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.Parameter`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.Parameter`
- Kind: `class`

## 一句话用途
A compile-time symbolic parameter.

## 功能说明
A compile-time symbolic parameter.

The value of a :class:`.Parameter` must be entirely determined before a circuit begins execution.
Typically this will mean that you should supply values for all :class:`.Parameter`\ s in a
circuit using :meth:`.QuantumCircuit.assign_parameters`, though certain hardware vendors may
allow you to give them a circuit in terms of these parameters, provided you also pass the values
separately.

This is the atom of :class:`.ParameterExpression`, and is itself an expression.  The numeric
value of a parameter need not be fixed while the circuit is being defined.

Examples:

    Construct a variable-rotation X gate using circuit parameters.

    .. plot::
        :alt: Circuit diagram output by the previous code.
        :include-source:

        from qiskit.circuit import QuantumCircuit, Parameter

        # create the parameter
        phi = Parameter("phi")
        qc = QuantumCircuit(1)

        # parameterize the rotation
        qc.rx(phi, 0)
        qc.draw("mpl")

        # bind the parameters after circuit to create a bound circuit
        bc = qc.assign_parameters({phi: 3.14})
        bc.measure_all()
        bc.draw("mpl")

## 函数签名
```python
(name, uuid=None)
```

## 相关量子编程概念
- measurement
- parameterized circuit

## 检索标签
- circuit_construction
- measurement
- parameterized_circuit
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.Parameter` 怎么用？
- `Parameter` 的参数是什么？
- Qiskit 2.4.1 中 `Parameter` 的最小示例是什么？
