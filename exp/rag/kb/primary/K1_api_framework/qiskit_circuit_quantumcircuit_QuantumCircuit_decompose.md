# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.decompose`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.decompose`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Call a decomposition pass on this circuit, to decompose one level (shallow decompose).

## 功能说明
Call a decomposition pass on this circuit, to decompose one level (shallow decompose).

Args:
    gates_to_decompose: Optional subset of gates to decompose. Can be a gate type, such as
        ``HGate``, or a gate name, such as "h", or a gate label, such as "My H Gate", or a
        list of any combination of these. If a gate name is entered, it will decompose all
        gates with that name, whether the gates have labels or not. Defaults to all gates in
        the circuit.
    reps: Optional number of times the circuit should be decomposed.
        For instance, ``reps=2`` equals calling ``circuit.decompose().decompose()``.

Returns:
    QuantumCircuit: a circuit one level decomposed

## 函数签名
```python
(self, gates_to_decompose: 'str | type[Instruction] | Sequence[str | type[Instruction]] | None' = None, reps: 'int' = 1) -> 'typing.Self'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.decompose` 怎么用？
- `decompose` 的参数是什么？
- Qiskit 2.4.1 中 `decompose` 的最小示例是什么？
