# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.assign_parameters`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.assign_parameters`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Assign parameters to new parameters or values.

## 功能说明
Assign parameters to new parameters or values.

If ``parameters`` is passed as a dictionary, the keys should be :class:`.Parameter`
instances in the current circuit. The values of the dictionary can either be numeric values
or new parameter objects.

If ``parameters`` is passed as a list or array, the elements are assigned to the
current parameters in the order of :attr:`parameters` which is sorted
alphabetically (while respecting the ordering in :class:`.ParameterVector` objects).

The values can be assigned to the current circuit object or to a copy of it.

.. note::
    When ``parameters`` is given as a mapping, it is permissible to have keys that are
    strings of the parameter names; these will be looked up using :meth:`get_parameter`.
    You can also have keys that are :class:`.ParameterVector` instances, and in this case,
    the dictionary value should be a sequence of values of the same length as the vector.

    If you use either of these cases, you must leave the setting ``flat_input=False``;
    changing this to ``True`` enables the fast path, where all keys must be
    :class:`.Parameter` instances.

Args:
    parameters: Either a dictionary or iterable specifying the new parameter values.
    inplace: If False, a copy of the circuit with the bound parameters is returned.
        If True the circuit instance itself is modified.
    flat_input: If ``True`` and ``parameters`` is a mapping type, it is assumed to be
        exactly a mapping of ``{parameter: value}``.  By default (``False``), the mapping
        may also contain :class:`.ParameterVector` keys that point to a corresponding
        sequence of values, and these will be unrolled during the mapping, or string keys,
        which will be converted to :class:`.Parameter` instances using
        :meth:`get_parameter`.
    strict: If ``False``, any parameters given in the mapping that are not used in the
        circuit will be ignored.  If ``True`` (the default), an error will be raised
        indicating a logic error.

Raises:
    CircuitError: If parameters is a dict and contains parameters not present in the
        circuit.
    ValueError: If parameters is a list/array and the length mismatches the number of free
        parameters in the circuit.

Returns:
    A copy of the circuit with bound parameters if ``inplace`` is False, otherwise None.

Examples:

    Create a parameterized circuit and assign the parameters in-place.

    .. plot::
       :alt: Circuit diagram output by the previous code.
       :include-source:

       from qiskit.circuit import QuantumCircuit, Parameter

       circuit = QuantumCircuit(2)
       params = [Parameter('A'), Parameter('B'), Parameter('C')]
       circuit.ry(params[0], 0)
       circuit.crx(params[1], 0, 1)
       circuit.draw('mpl')
       circuit.assign_parameters({params[0]: params[2]}, inplace=True)
       circuit.draw('mpl')

    Bind the values out-of-place by list and get a copy of the original circuit.

    .. plot::
       :alt: Circuit diagram output by the previous code.
       :include-source:

       from qiskit.circuit import QuantumCircuit, ParameterVector

       circuit = QuantumCircuit(2)
       params = ParameterVector('P', 2)
       circuit.ry(params[0], 0)
       circuit.crx(params[1], 0, 1)

       bound_circuit = circuit.assign_parameters([1, 2])
       bound_circuit.draw('mpl')

       circuit.draw('mpl')

## 函数签名
```python
(self, parameters: 'Mapping[Parameter, ParameterValueType] | Iterable[ParameterValueType]', inplace: 'bool' = False, *, flat_input: 'bool' = False, strict: 'bool' = True) -> 'QuantumCircuit | None'
```

## 相关量子编程概念
- circuit construction
- parameterized circuit
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- parameterized_circuit
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.assign_parameters` 怎么用？
- `assign_parameters` 的参数是什么？
- Qiskit 2.4.1 中 `assign_parameters` 的最小示例是什么？
