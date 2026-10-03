# Qiskit 2.4.1 API: `qiskit.quantum_info.PauliList.equiv`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.PauliList.equiv`
- Kind: `method`
- Owner class: `PauliList`

## 一句话用途
Entrywise comparison of Pauli equivalence up to global phase.

## 功能说明
Entrywise comparison of Pauli equivalence up to global phase.

Args:
    other (PauliList or Pauli): a comparison object.

Returns:
    np.ndarray: An array of ``True`` or ``False`` for entrywise equivalence
                of the current table.

## 函数签名
```python
(self, other: 'PauliList | Pauli') -> 'np.ndarray'
```

## 相关量子编程概念
- observable / Hamiltonian

## 检索标签
- observable_hamiltonian
- quantum_info

## 适合回答的问题
- `qiskit.quantum_info.PauliList.equiv` 怎么用？
- `equiv` 的参数是什么？
- Qiskit 2.4.1 中 `equiv` 的最小示例是什么？
