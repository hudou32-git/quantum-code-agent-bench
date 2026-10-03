# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.apply_layout`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.apply_layout`
- Kind: `method`
- Owner class: `Pauli`

## 一句话用途
Apply a transpiler layout to this :class:`~.quantum_info.Pauli`

## 功能说明
Apply a transpiler layout to this :class:`~.quantum_info.Pauli`

Args:
    layout: Either a :class:`~.TranspileLayout`, a list of integers or None.
            If both layout and num_qubits are none, a copy of the operator is
            returned.
    num_qubits: The number of qubits to expand the operator to. If not
        provided then if ``layout`` is a :class:`~.TranspileLayout` the
        number of the transpiler output circuit qubits will be used by
        default. If ``layout`` is a list of integers the permutation
        specified will be applied without any expansion. If layout is
        None, the operator will be expanded to the given number of qubits.

Returns:
    A new :class:`~.quantum_info.Pauli` with the provided layout applied

## 函数签名
```python
(self, layout: 'TranspileLayout | list[int] | None', num_qubits: 'int | None' = None) -> 'Pauli'
```

## 相关量子编程概念
- Pauli
- observable
- observable / Hamiltonian
- transpilation

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.Pauli.apply_layout` 怎么用？
- `apply_layout` 的参数是什么？
- Qiskit 2.4.1 中 `apply_layout` 的最小示例是什么？
