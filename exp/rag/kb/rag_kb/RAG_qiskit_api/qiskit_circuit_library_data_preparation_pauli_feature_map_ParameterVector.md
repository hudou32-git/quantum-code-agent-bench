# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.pauli_feature_map.ParameterVector`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.pauli_feature_map`
- API: `qiskit.circuit.library.data_preparation.pauli_feature_map.ParameterVector`
- Kind: `class`

## 一句话用途
A container of many related :class:`Parameter` objects.

## 功能说明
A container of many related :class:`Parameter` objects.

This class is faster to construct than constructing many :class:`Parameter` objects
individually, and the individual names of the parameters will all share a common stem (the name
of the vector).  For a vector called ``v`` with length 3, the individual elements will have
names ``v[0]``, ``v[1]`` and ``v[2]``.

The elements of a vector are sorted by the name of the vector, then the numeric value of their
index.

This class fulfills the :class:`collections.abc.Sequence` interface.

## 函数签名
```python
(name, length=0)
```

## 相关量子编程概念
- observable / Hamiltonian
- parameterized circuit

## 检索标签
- circuit_construction
- observable_hamiltonian
- parameterized_circuit
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.pauli_feature_map.ParameterVector` 怎么用？
- `ParameterVector` 的参数是什么？
- Qiskit 2.4.1 中 `ParameterVector` 的最小示例是什么？
