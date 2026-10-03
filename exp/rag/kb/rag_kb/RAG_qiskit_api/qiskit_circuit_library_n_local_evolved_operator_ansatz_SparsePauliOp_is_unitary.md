# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.is_unitary`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.is_unitary`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Return True if operator is a unitary matrix.

## 功能说明
Return True if operator is a unitary matrix.

This method checks whether the operator composed with its adjoint equals
the identity, up to the provided tolerance. The tolerance is used when
simplifying the composed operator and checking if the result is the identity.

Args:
    atol (float): Optional. Absolute tolerance for checking if
                  coefficients are zero (Default: 1e-8).
    rtol (float): Optional. Relative tolerance for checking if
                  coefficients are zero (Default: 1e-5).

Returns:
    bool: True if the operator is unitary, False otherwise.

## 函数签名
```python
(self, atol: 'float | None' = None, rtol: 'float | None' = None) -> 'bool'
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.is_unitary` 怎么用？
- `is_unitary` 的参数是什么？
- Qiskit 2.4.1 中 `is_unitary` 的最小示例是什么？
