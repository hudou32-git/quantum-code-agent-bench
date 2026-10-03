# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.equiv`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.equiv`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Check if two SparsePauliOp operators are equivalent.

## 功能说明
Check if two SparsePauliOp operators are equivalent.

Args:
    other (SparsePauliOp): an operator object.
    atol: Absolute numerical tolerance for checking equivalence.

Returns:
    bool: True if the operator is equivalent to ``self``.

## 函数签名
```python
(self, other: 'SparsePauliOp', atol: 'float | None' = None) -> 'bool'
```

## 相关量子编程概念
- Hamiltonian
- Pauli 算符
- observable
- observable / Hamiltonian

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.equiv` 怎么用？
- `equiv` 的参数是什么？
- Qiskit 2.4.1 中 `equiv` 的最小示例是什么？
