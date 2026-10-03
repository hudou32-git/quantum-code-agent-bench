# Qiskit 2.4.1 API: `qiskit.transpiler.passes.layout.trivial_layout.Target`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler.passes.layout.trivial_layout`
- API: `qiskit.transpiler.passes.layout.trivial_layout.Target`
- Kind: `class`

## 一句话用途
The intent of the ``Target`` object is to inform Qiskit's compiler about the constraints of a particular backend so the compiler can compile an input circuit to something that works and is optimized for a device. It currently contains a description of instructions on a backend an...

## 功能说明
The intent of the ``Target`` object is to inform Qiskit's compiler about
the constraints of a particular backend so the compiler can compile an
input circuit to something that works and is optimized for a device. It
currently contains a description of instructions on a backend and their
properties as well as some timing information. However, this exact
interface may evolve over time as the needs of the compiler change. These
changes will be done in a backwards compatible and controlled manner when
they are made (either through versioning, subclassing, or mixins) to add
on to the set of information exposed by a target.

As a basic example, let's assume a backend has two qubits, supports
:class:`~qiskit.circuit.library.UGate` on both qubits and
:class:`~qiskit.circuit.library.CXGate` in both directions. To model this
you would create the target like::

    from qiskit.transpiler import Target, InstructionProperties
    from qiskit.circuit.library import UGate, CXGate
    from qiskit.circuit import Parameter

    gmap = Target()
    theta = Parameter('theta')
    phi = Parameter('phi')
    lam = Parameter('lambda')
    u_props = {
        (0,): InstructionProperties(duration=5.23e-8, error=0.00038115),
        (1,): InstructionProperties(duration=4.52e-8, error=0.00032115),
    }
    gmap.add_instruction(UGate(theta, phi, lam), u_props)
    cx_props = {
        (0,1): InstructionProperties(duration=5.23e-7, error=0.00098115),
        (1,0): InstructionProperties(duration=4.52e-7, error=0.00132115),
    }
    gmap.add_instruction(CXGate(), cx_props)

Each instruction in the ``Target`` is indexed by a unique string name that uniquely
identifies that instance of an :class:`~qiskit.circuit.Instruction` object in
the Target. There is a 1:1 mapping between a name and an
:class:`~qiskit.circuit.Instruction` instance in the target and each name must
be unique. By default, the name is the :attr:`~qiskit.circuit.Instruction.name`
attribute of the instruction, but can be set to anything. This lets a single
target have multiple instances of the same instruction class with different
parameters. For example, if a backend target has two instances of an
:class:`~qiskit.circuit.library.RXGate` one is parameterized over any theta
while the other is tuned up for a theta of pi/6 you can add these by doing something
like::

    import math

    from qiskit.transpiler import Target, InstructionProperties
    from qiskit.circuit.library import RXGate
    from qiskit.circuit import Parameter

    target = Target()
    theta = Parameter('theta')
    rx_props = {
        (0,): InstructionProperties(duration=5.23e-8, error=0.00038115),
    }
    target.add_instruction(RXGate(theta), rx_props)
    rx_30_props = {
        (0,): InstructionProperties(duration=1.74e-6, error=.00012)
    }
    target.add_instruction(RXGate(math.pi / 6), rx_30_props, name='rx_30')

Then in the ``target`` object accessing by ``rx_30`` will get the fixed
angle :class:`~qiskit.circuit.library.RXGate` while ``rx`` will get the
parameterized :class:`~qiskit.circuit.library.RXGate`.

You can optionally specify a bound on valid values on a gate in the target
by using the ``angle_bounds`` keyword argument when calling the :meth:`.add_instruction`
method. Bounds are set on operations not individual instructions, so when
you call :meth:`.add_instruction` the bounds are applied for all qargs that it
is defined on. The bounds are specified of a list of 2-tuples of floats where
the first float is the lower bound and the second float is the upper bound. For example,
if you specified an angle bound::

    [(0.0, 3.14), (-3.14, 3.14), (0.0, 1.0)]

this indicates the angle bounds for a 3 parameter gate where the first
parameter accepts angles between 0 and 3.14, the second between -3.14 and
3.14, and the third parameter between 0 and 1. All bounds are set
inclusively as well. A bound can also be specified with ``None`` instead
of a 2-tuple which indicates that parameter has no constraints. For example::

    [(0.0, 3.14), None, None]

indicates an angle bound for a 3 parameter gate where only the first
parameter is restricted to angles between 0.0 and 3.14 and the other
parameters accept any value.

You can check if any operations in the target have angle bounds set with,
:meth:`.has_angle_bounds` and also if a specific name in the target has
angle bounds set with :meth:`.gate_has_angle_bounds`. Whether a particular
set of parameter values conforms to the angle bounds can be checked
with :meth:`.supported_angle_bound`. In the preset pass managers the
:class:`.WrapAngles` pass is used to enforce the angle bounds, for this
to work you need to provide a function to the :class:`.WrapAngleRegistry`
used by the pass. You can see more details on this in:
:ref:`angle-bounds-on-gates`.

This class can be queried via the mapping protocol, using the
instruction's name as a key. You can modify any property for an
instruction via the :meth:`.update_instruction_properties` method.
Modifica

...[truncated]

## 函数签名
```python
(description: 'str | None' = None, num_qubits: 'int | None' = 0, dt: 'float | None' = None, granularity: 'int' = 1, min_length: 'int' = 1, pulse_alignment: 'int' = 1, acquire_alignment: 'int' = 1, qubit_properties: 'list | None' = None, concurrent_measurements: 'list | None' = None, **_subclass_kwargs)
```

## 相关量子编程概念
- Bell state / entanglement
- backend execution
- backend target
- basis gates
- parameterized circuit
- transpilation
- 后端目标

## 检索标签
- backend_provider
- circuit_construction
- parameterized_circuit
- single_qubit_gate
- transpilation
- two_qubit_gate

## 适合回答的问题
- `qiskit.transpiler.passes.layout.trivial_layout.Target` 怎么用？
- `Target` 的参数是什么？
- Qiskit 2.4.1 中 `Target` 的最小示例是什么？
