# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.to_matrix`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.to_matrix`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Convert to a dense or sparse matrix.

## 功能说明
Convert to a dense or sparse matrix.

Args:
    sparse: if ``True`` return a sparse CSR matrix, otherwise return dense Numpy
        array (the default).
    force_serial: if ``True``, use an unthreaded implementation, regardless of the state of
        the `Qiskit threading-control environment variables
        <https://quantum.cloud.ibm.com/docs/guides/configure-qiskit-local#environment-variables>`__.
        By default, this will use threaded parallelism over the available CPUs.

Returns:
    array: A dense matrix if `sparse=False`.
    csr_matrix: A sparse matrix in CSR format if `sparse=True`.

## 函数签名
```python
(self, sparse: 'bool' = False, force_serial: 'bool' = False) -> 'np.ndarray'
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.to_matrix` 怎么用？
- `to_matrix` 的参数是什么？
- Qiskit 2.4.1 中 `to_matrix` 的最小示例是什么？
