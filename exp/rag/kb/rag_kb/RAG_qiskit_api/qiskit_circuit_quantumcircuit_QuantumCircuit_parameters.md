# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.parameters`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.parameters`
- Kind: `property`
- Owner class: `QuantumCircuit`

## 一句话用途
The parameters defined in the circuit.

## 功能说明
The parameters defined in the circuit.

This attribute returns the :class:`.Parameter` objects in the circuit sorted
alphabetically. Note that parameters instantiated with a :class:`.ParameterVector`
are still sorted numerically.

Examples:

    The snippet below shows that insertion order of parameters does not matter.

    .. plot::
       :include-source:
       :nofigs:

        >>> from qiskit.circuit import QuantumCircuit, Parameter
        >>> a, b, elephant = Parameter("a"), Parameter("b"), Parameter("elephant")
        >>> circuit = QuantumCircuit(1)
        >>> circuit.rx(b, 0)
        >>> circuit.rz(elephant, 0)
        >>> circuit.ry(a, 0)
        >>> circuit.parameters  # sorted alphabetically!
        ParameterView([Parameter(a), Parameter(b), Parameter(elephant)])

    Bear in mind that alphabetical sorting might be unintuitive when it comes to numbers.
    The literal "10" comes before "2" in strict alphabetical sorting.

    .. plot::
       :include-source:
       :nofigs:

        >>> from qiskit.circuit import QuantumCircuit, Parameter
        >>> angles = [Parameter("angle_1"), Parameter("angle_2"), Parameter("angle_10")]
        >>> circuit = QuantumCircuit(1)
        >>> circuit.u(*angles, 0)
        >>> circuit.draw()
           ┌─────────────────────────────┐
        q: ┤ U(angle_1,angle_2,angle_10) ├
           └─────────────────────────────┘
        >>> circuit.parameters
        ParameterView([Parameter(angle_1), Parameter(angle_10), Parameter(angle_2)])

    To respect numerical sorting, a :class:`.ParameterVector` can be used.

    .. plot::
       :include-source:
       :nofigs:

        >>> from qiskit.circuit import QuantumCircuit, Parameter, ParameterVector
        >>> x = ParameterVector("x", 12)
        >>> circuit = QuantumCircuit(1)
        >>> for x_i in x:
        ...     circuit.rx(x_i, 0)
        >>> circuit.parameters
        ParameterView([
            ParameterVectorElement(x[0]), ParameterVectorElement(x[1]),
            ParameterVectorElement(x[2]), ParameterVectorElement(x[3]),
            ..., ParameterVectorElement(x[11])
        ])


Returns:
    The sorted :class:`.Parameter` objects in the circuit.

## 使用示例
### 示例 1
```python
from qiskit.circuit import QuantumCircuit, Parameter
a, b, elephant = Parameter("a"), Parameter("b"), Parameter("elephant")
circuit = QuantumCircuit(1)
circuit.rx(b, 0)
circuit.rz(elephant, 0)
circuit.ry(a, 0)
circuit.parameters  # sorted alphabetically!
```

### 示例 2
```python
from qiskit.circuit import QuantumCircuit, Parameter
angles = [Parameter("angle_1"), Parameter("angle_2"), Parameter("angle_10")]
circuit = QuantumCircuit(1)
circuit.u(*angles, 0)
circuit.draw()
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
- `qiskit.circuit.quantumcircuit.QuantumCircuit.parameters` 怎么用？
- `parameters` 的参数是什么？
- Qiskit 2.4.1 中 `parameters` 的最小示例是什么？
