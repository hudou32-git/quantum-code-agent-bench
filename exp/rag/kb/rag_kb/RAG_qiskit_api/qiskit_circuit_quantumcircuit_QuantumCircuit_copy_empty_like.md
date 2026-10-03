# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.copy_empty_like`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.copy_empty_like`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Return a copy of self with the same structure but empty.

## 功能说明
Return a copy of self with the same structure but empty.

That structure includes:

* name and other metadata
* global phase
* all the qubits and clbits, including the registers
* the realtime variables defined in the circuit, handled according to the ``vars`` keyword
  argument.

.. warning::

    If the circuit contains any local variable declarations (those added by the
    ``declarations`` argument to the circuit constructor, or using :meth:`add_var`), they
    may be **uninitialized** in the output circuit.  You will need to manually add store
    instructions for them (see :class:`.Store` and :meth:`.QuantumCircuit.store`) to
    initialize them.

Args:
    name: Name for the copied circuit. If None, then the name stays the same.
    vars_mode: The mode to handle realtime variables in.

        alike
            The variables in the output circuit will have the same declaration semantics as
            in the original circuit.  For example, ``input`` variables in the source will be
            ``input`` variables in the output circuit.
            Note that this causes the local variables to be uninitialised, because the stores are
            not copied.  This can leave the circuit in a potentially dangerous state for users if
            they don't re-add initializer stores.

        captures
            All variables will be converted to captured variables.  This is useful when you
            are building a new layer for an existing circuit that you will want to
            :meth:`compose` onto the base, since :meth:`compose` can inline captures onto
            the base circuit (but not other variables).

        drop
            The output circuit will have no variables defined.

Returns:
    QuantumCircuit: An empty copy of self.

## 函数签名
```python
(self, name: 'str | None' = None, *, vars_mode: "Literal['alike', 'captures', 'drop']" = 'alike') -> 'typing.Self'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.copy_empty_like` 怎么用？
- `copy_empty_like` 的参数是什么？
- Qiskit 2.4.1 中 `copy_empty_like` 的最小示例是什么？
