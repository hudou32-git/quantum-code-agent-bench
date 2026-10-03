# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_operator`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_operator`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Construct from an Operator object.

## 功能说明
Construct from an Operator object.

Note that the cost of this construction is exponential in general because the number of
possible Pauli terms in the decomposition is exponential in the number of qubits.

Internally this uses an implementation of the "tensorized Pauli decomposition" presented in
`Hantzko, Binkowski and Gupta (2023) <https://arxiv.org/abs/2310.13421>`__.

Args:
    obj (Operator): an N-qubit operator.
    atol (float): Optional. Absolute tolerance for checking if coefficients are zero
        (Default: 1e-8).  Since the comparison is to zero, in effect the tolerance used is
        the maximum of ``atol`` and ``rtol``.
    rtol (float): Optional. relative tolerance for checking if coefficients are zero
        (Default: 1e-5).  Since the comparison is to zero, in effect the tolerance used is
        the maximum of ``atol`` and ``rtol``.

Returns:
    SparsePauliOp: the SparsePauliOp representation of the operator.

Raises:
    QiskitError: if the input operator is not an N-qubit operator.

## 函数签名
```python
(obj: 'Operator', atol: 'float | None' = None, rtol: 'float | None' = None) -> 'SparsePauliOp'
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_operator` 怎么用？
- `from_operator` 的参数是什么？
- Qiskit 2.4.1 中 `from_operator` 的最小示例是什么？
