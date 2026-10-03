# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.depth`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.depth`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Return circuit depth (i.e., length of critical path).

## 功能说明
Return circuit depth (i.e., length of critical path).

The depth of a quantum circuit is a measure of how many
"layers" of quantum gates, executed in parallel, it takes to
complete the computation defined by the circuit.  Because
quantum gates take time to implement, the depth of a circuit
roughly corresponds to the amount of time it takes the quantum
computer to execute the circuit.


.. warning::
    This operation is not well defined if the circuit contains control-flow operations.

Args:
    filter_function: A function to decide which instructions count to increase depth.
        Should take as a single positional input a :class:`CircuitInstruction`.
        Instructions for which the function returns ``False`` are ignored in the
        computation of the circuit depth.  By default, filters out "directives", such as
        :class:`.Barrier`.

Returns:
    int: Depth of circuit.

Examples:
    Simple calculation of total circuit depth::

        from qiskit.circuit import QuantumCircuit
        qc = QuantumCircuit(4)
        qc.h(0)
        qc.cx(0, 1)
        qc.h(2)
        qc.cx(2, 3)
        assert qc.depth() == 2

    Modifying the previous example to only calculate the depth of multi-qubit gates::

        assert qc.depth(lambda instr: len(instr.qubits) > 1) == 1

## 函数签名
```python
(self, filter_function: 'Callable[[CircuitInstruction], bool]' = <function QuantumCircuit.<lambda> at 0x7f0acc5d4670>) -> 'int'
```

## 相关量子编程概念
- Bell state / entanglement
- circuit construction
- measurement
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- measurement
- single_qubit_gate
- two_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.depth` 怎么用？
- `depth` 的参数是什么？
- Qiskit 2.4.1 中 `depth` 的最小示例是什么？
