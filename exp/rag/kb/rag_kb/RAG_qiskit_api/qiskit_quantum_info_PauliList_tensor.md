# Qiskit 2.4.1 API: `qiskit.quantum_info.PauliList.tensor`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.PauliList.tensor`
- Kind: `method`
- Owner class: `PauliList`

## 一句话用途
Return the tensor product with each Pauli in the list.

## 功能说明
Return the tensor product with each Pauli in the list.

Args:
    other (PauliList): another PauliList.

Returns:
    PauliList: the list of tensor product Paulis.

Raises:
    QiskitError: if other cannot be converted to a PauliList, does
                 not have either 1 or the same number of Paulis as
                 the current list.

## 函数签名
```python
(self, other: 'PauliList') -> 'PauliList'
```

## 相关量子编程概念
- observable / Hamiltonian

## 检索标签
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.PauliList.tensor` 怎么用？
- `tensor` 的参数是什么？
- Qiskit 2.4.1 中 `tensor` 的最小示例是什么？
