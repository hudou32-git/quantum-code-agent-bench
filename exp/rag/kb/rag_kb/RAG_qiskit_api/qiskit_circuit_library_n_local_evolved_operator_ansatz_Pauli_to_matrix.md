# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.to_matrix`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.to_matrix`
- Kind: `method`
- Owner class: `Pauli`

## 一句话用途
Convert to a Numpy array or sparse CSR matrix.

## 功能说明
Convert to a Numpy array or sparse CSR matrix.

Args:
    sparse (bool): if True return sparse CSR matrices, otherwise
                   return dense Numpy arrays (default: False).

Returns:
    array: The Pauli matrix.

## 函数签名
```python
(self, sparse: 'bool' = False) -> 'np.ndarray'
```

## 相关量子编程概念
- Pauli
- observable
- observable / Hamiltonian

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.to_matrix` 怎么用？
- `to_matrix` 的参数是什么？
- Qiskit 2.4.1 中 `to_matrix` 的最小示例是什么？
