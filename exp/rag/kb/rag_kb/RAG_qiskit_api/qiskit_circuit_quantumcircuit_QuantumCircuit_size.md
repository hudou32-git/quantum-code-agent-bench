# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.size`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.size`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Returns total number of instructions in circuit.

## 功能说明
Returns total number of instructions in circuit.

Args:
    filter_function (callable): a function to filter out some instructions.
        Should take as input a tuple of (Instruction, list(Qubit), list(Clbit)).
        By default, filters out "directives", such as barrier or snapshot.

Returns:
    int: Total number of gate operations.

## 函数签名
```python
(self, filter_function: 'Callable[..., int]' = <function QuantumCircuit.<lambda> at 0x7f0acc5d4550>) -> 'int'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.size` 怎么用？
- `size` 的参数是什么？
- Qiskit 2.4.1 中 `size` 的最小示例是什么？
