# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.compose`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.compose`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Apply the instructions from one circuit onto specified qubits and/or clbits on another.

## 功能说明
Apply the instructions from one circuit onto specified qubits and/or clbits on another.

.. note::

    By default, this creates a new circuit object, leaving ``self`` untouched.  For most
    uses of this function, it is far more efficient to set ``inplace=True`` and modify the
    base circuit in-place.

When dealing with realtime variables (:class:`.expr.Var` and :class:`.expr.Stretch` instances),
there are two principal strategies for using :meth:`compose`:

1. The ``other`` circuit is treated as entirely additive, including its variables.  The
   variables in ``other`` must be entirely distinct from those in ``self`` (use
   ``var_remap`` to help with this), and all variables in ``other`` will be declared anew in
   the output with matching input/capture/local scoping to how they are in ``other``.  This
   is generally what you want if you're joining two unrelated circuits.

2. The ``other`` circuit was created as an exact extension to ``self`` to be inlined onto
   it, including acting on the existing variables in their states at the end of ``self``.
   In this case, ``other`` should be created with all these variables to be inlined declared
   as "captures", and then you can use ``inline_captures=True`` in this method to link them.
   This is generally what you want if you're building up a circuit by defining layers
   on-the-fly, or rebuilding a circuit using layers taken from itself.  You might find the
   ``vars_mode="captures"`` argument to :meth:`copy_empty_like` useful to create each
   layer's base, in this case.

Args:
    other (qiskit.circuit.Instruction or QuantumCircuit):
        (sub)circuit or instruction to compose onto self.  If not a :obj:`.QuantumCircuit`,
        this can be anything that :obj:`.append` will accept.
    qubits (list[Qubit|int]): qubits of self to compose onto.
    clbits (list[Clbit|int]): clbits of self to compose onto.
    front (bool): If ``True``, front composition will be performed.  This is not possible within
        control-flow builder context managers.
    inplace (bool): If ``True``, modify the object. Otherwise, return composed circuit.
    copy (bool): If ``True`` (the default), then the input is treated as shared, and any
        contained instructions will be copied, if they might need to be mutated in the
        future.  You can set this to ``False`` if the input should be considered owned by
        the base circuit, in order to avoid unnecessary copies; in this case, it is not
        valid to use ``other`` afterward, and some instructions may have been mutated in
        place.
    var_remap (Mapping): mapping to use to rewrite :class:`.expr.Var` and
        :class:`.expr.Stretch` nodes in ``other`` as they are inlined into ``self``.
        This can be used to avoid naming conflicts.

        Both keys and values can be given as strings or direct identifier instances.
        If a key is a string, it matches any :class:`~.expr.Var` or :class:`~.expr.Stretch`
        with the same name.  If a value is a string, whenever a new key matches it, a new
        :class:`~.expr.Var` or :class:`~.expr.Stretch` is created with the correct type.
        If a value is a :class:`~.expr.Var`, its :class:`~.expr.Expr.type` must exactly
        match that of the variable it is replacing.
    inline_captures (bool): if ``True``, then all "captured" identifier nodes in
        the ``other`` :class:`.QuantumCircuit` are assumed to refer to identifiers already
        declared in ``self`` (as any input/capture/local type), and the uses in ``other``
        will apply to the existing identifiers.  If you want to build up a layer for an
        existing circuit to use with :meth:`compose`, you might find the
        ``vars_mode="captures"`` argument to :meth:`copy_empty_like` useful.  Any remapping
        in ``vars_remap`` occurs before evaluating this variable inlining.

        If this is ``False`` (the default), then all identifiers in ``other`` will be required
        to be distinct from those in ``self``, and new declarations will be made for them.
    wrap (bool): If True, wraps the other circuit into a gate (or instruction, depending on
        whether it contains only unitary instructions) before composing it onto self.
        Rather than using this option, it is almost always better to manually control this
        yourself by using :meth:`to_instruction` or :meth:`to_gate`, and then call
        :meth:`append`.

Returns:
    QuantumCircuit: the composed circuit (returns None if inplace==True).

Raises:
    CircuitError: if no correct wire mapping can be made between the two circuits, such as
        if ``other`` is wider than ``self``.
    CircuitError: if trying to emit a new circuit while ``self`` has a partially built
        control-flow context active, such as the context-manager forms of :meth:`if_test`,
        :meth:`for_loop` and :meth:`while_loop`.
    CircuitError: if trying to compose to the front of a circuit when a control-flow builder

...[truncated]

## 函数签名
```python
(self, other: 'QuantumCircuit | Instruction', qubits: 'QubitSpecifier | Sequence[QubitSpecifier] | None' = None, clbits: 'ClbitSpecifier | Sequence[ClbitSpecifier] | None' = None, front: 'bool' = False, inplace: 'bool' = False, wrap: 'bool' = False, *, copy: 'bool' = True, var_remap: 'Mapping[str | expr.Var | expr.Stretch, str | expr.Var | expr.Stretch] | None' = None, inline_captures: 'bool' = False) -> 'QuantumCircuit | None'
```

## 使用示例
### 示例 1
```python
from qiskit import QuantumCircuit



a = QuantumCircuit(1)

a.h(0)



b = QuantumCircuit(1)

b.x(0)



combined = a.compose(b)
```

### 示例 2
```python
lhs.compose(rhs, qubits=[3, 2], inplace=True)
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.compose` 怎么用？
- `compose` 的参数是什么？
- Qiskit 2.4.1 中 `compose` 的最小示例是什么？
