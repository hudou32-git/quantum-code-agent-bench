# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.dot`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.dot`
- Kind: `method`
- Owner class: `Pauli`

## 一句话用途
Return the right multiplied operator self * other.

## 功能说明
Return the right multiplied operator self * other.

Args:
    other (Pauli): an operator object.
    qargs (list or None):  qubits to apply dot product
                          on (default: None).
    inplace (bool): If True update in-place (default: False).

Returns:
    Pauli: The operator self * other.

## 函数签名
```python
(self, other: 'Pauli', qargs: 'list | None' = None, inplace: 'bool' = False) -> 'Pauli'
```

## 相关量子编程概念
- Pauli
- observable
- observable / Hamiltonian

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.dot` 怎么用？
- `dot` 的参数是什么？
- Qiskit 2.4.1 中 `dot` 的最小示例是什么？
