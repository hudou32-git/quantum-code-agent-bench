# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.to_list`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.to_list`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Convert to a list Pauli string labels and coefficients.

## 功能说明
Convert to a list Pauli string labels and coefficients.

For operators with a lot of terms converting using the ``array=True``
kwarg will be more efficient since it allocates memory for
the full Numpy array of labels in advance.

Args:
    array (bool): return a Numpy array if True, otherwise
                  return a list (Default: False).

Returns:
    list or array: List of pairs (label, coeff) for rows of the PauliList.

## 函数签名
```python
(self, array: 'bool' = False)
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.to_list` 怎么用？
- `to_list` 的参数是什么？
- Qiskit 2.4.1 中 `to_list` 的最小示例是什么？
