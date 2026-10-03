# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_sparse_list`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_sparse_list`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Construct from a list of local Pauli strings and coefficients.

## 功能说明
Construct from a list of local Pauli strings and coefficients.

Each list element is a 3-tuple of a local Pauli string, indices where to apply it,
and a coefficient.

For example, the 5-qubit Hamiltonian

.. math::

    H = Z_1 X_4 + 2 Y_0 Y_3

can be constructed as

.. plot::
   :include-source:
   :nofigs:

    from qiskit.quantum_info import SparsePauliOp

    # via triples and local Paulis with indices
    op = SparsePauliOp.from_sparse_list([("ZX", [1, 4], 1), ("YY", [0, 3], 2)], num_qubits=5)

    # equals the following construction from "dense" Paulis
    op = SparsePauliOp.from_list([("XIIZI", 1), ("IYIIY", 2)])

Args:
    obj (Iterable[tuple[str, list[int], complex]]): The list 3-tuples specifying the Paulis.
    num_qubits (int): The number of qubits of the operator.
    do_checks (bool): Whether to perform validity checks on the input indices.
    dtype (type | None): Data type for the coefficients. If ``None`` (default), the dtype is
        automatically inferred.


Returns:
    SparsePauliOp: The SparsePauliOp representation of the Pauli terms.

Raises:
    QiskitError: If the number of qubits is incompatible with the indices of the Pauli terms.
    QiskitError: If the designated qubit is already assigned.

## 函数签名
```python
(obj: 'Iterable[tuple[str, list[int], complex]]', num_qubits: 'int', do_checks: 'bool' = True, dtype: 'type | None' = None) -> 'SparsePauliOp'
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_sparse_list` 怎么用？
- `from_sparse_list` 的参数是什么？
- Qiskit 2.4.1 中 `from_sparse_list` 的最小示例是什么？
