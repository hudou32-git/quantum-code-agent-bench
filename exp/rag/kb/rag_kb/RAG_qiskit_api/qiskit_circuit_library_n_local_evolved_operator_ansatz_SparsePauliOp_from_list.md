# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_list`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_list`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Construct from a list of Pauli strings and coefficients.

## 功能说明
Construct from a list of Pauli strings and coefficients.

For example, the 5-qubit Hamiltonian

.. math::

    H = Z_1 X_4 + 2 Y_0 Y_3

can be constructed as

.. plot::
   :include-source:
   :nofigs:

    from qiskit.quantum_info import SparsePauliOp

    # via tuples and the full Pauli string
    op = SparsePauliOp.from_list([("XIIZI", 1), ("IYIIY", 2)])

Args:
    obj (Iterable[Tuple[str, complex]]): The list of 2-tuples specifying the Pauli terms.
    dtype (type | None): Data type for the coefficients. If ``None`` (default), the dtype is
        automatically inferred.
    num_qubits (int): The number of qubits of the operator (Default: None).

Returns:
    SparsePauliOp: The SparsePauliOp representation of the Pauli terms.

Raises:
    QiskitError: If an empty list is passed and num_qubits is None.
    QiskitError: If num_qubits and the objects in the input list do not match.

## 函数签名
```python
(obj: 'Iterable[tuple[str, complex]]', dtype: 'type | None' = None, *, num_qubits: 'int | None' = None) -> 'SparsePauliOp'
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.from_list` 怎么用？
- `from_list` 的参数是什么？
- Qiskit 2.4.1 中 `from_list` 的最小示例是什么？
