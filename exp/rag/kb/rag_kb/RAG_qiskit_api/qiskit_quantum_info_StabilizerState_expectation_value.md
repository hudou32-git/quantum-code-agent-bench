# Qiskit 2.4.1 API: `qiskit.quantum_info.StabilizerState.expectation_value`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.StabilizerState.expectation_value`
- Kind: `method`
- Owner class: `StabilizerState`

## 一句话用途
Compute the expectation value of a Pauli or SparsePauliOp operator.

## 功能说明
Compute the expectation value of a Pauli or SparsePauliOp operator.

Args:
    oper: A Pauli or SparsePauliOp operator to evaluate the expectation value.
    qargs: Subsystems to apply the operator on.

Returns:
    The expectation value.

Raises:
    QiskitError: if oper is not a Pauli or SparsePauliOp operator.

## 函数签名
```python
(self, oper: 'Pauli | SparsePauliOp', qargs: 'None | list' = None) -> 'complex'
```

## 相关量子编程概念
- observable / Hamiltonian

## 检索标签
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.StabilizerState.expectation_value` 怎么用？
- `expectation_value` 的参数是什么？
- Qiskit 2.4.1 中 `expectation_value` 的最小示例是什么？
