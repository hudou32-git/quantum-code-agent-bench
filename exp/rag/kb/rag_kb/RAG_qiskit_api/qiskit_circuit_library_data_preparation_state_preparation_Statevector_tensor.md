# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.tensor`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.tensor`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Return the tensor product state self ⊗ other.

## 功能说明
Return the tensor product state self ⊗ other.

Args:
    other (Statevector): a quantum state object.

Returns:
    Statevector: the tensor product operator self ⊗ other.

Raises:
    QiskitError: if other is not a quantum state.

## 函数签名
```python
(self, other: 'Statevector') -> 'Statevector'
```

## 相关量子编程概念
- simulation
- state simulation
- state vector
- 态向量

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.tensor` 怎么用？
- `tensor` 的参数是什么？
- Qiskit 2.4.1 中 `tensor` 的最小示例是什么？
