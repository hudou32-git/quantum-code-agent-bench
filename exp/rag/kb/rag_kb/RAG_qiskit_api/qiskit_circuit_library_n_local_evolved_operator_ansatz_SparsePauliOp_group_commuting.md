# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.group_commuting`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.group_commuting`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Partition a SparsePauliOp into sets of commuting Pauli strings.

## 功能说明
Partition a SparsePauliOp into sets of commuting Pauli strings.

Args:
    qubit_wise (bool): whether the commutation rule is applied to the whole operator,
        or on a per-qubit basis.  For example:

        .. plot::
           :include-source:
           :nofigs:

            >>> from qiskit.quantum_info import SparsePauliOp
            >>> op = SparsePauliOp.from_list([("XX", 2), ("YY", 1), ("IZ",2j), ("ZZ",1j)])
            >>> op.group_commuting()
            [SparsePauliOp(["IZ", "ZZ"], coeffs=[0.+2.j, 0.+1j]),
             SparsePauliOp(["XX", "YY"], coeffs=[2.+0.j, 1.+0.j])]
            >>> op.group_commuting(qubit_wise=True)
            [SparsePauliOp(['XX'], coeffs=[2.+0.j]),
             SparsePauliOp(['YY'], coeffs=[1.+0.j]),
             SparsePauliOp(['IZ', 'ZZ'], coeffs=[0.+2.j, 0.+1.j])]

Returns:
    list[SparsePauliOp]: List of SparsePauliOp where each SparsePauliOp contains
        commuting Pauli operators.

## 函数签名
```python
(self, qubit_wise: 'bool' = False) -> 'list[SparsePauliOp]'
```

## 使用示例
### 示例 1
```python
from qiskit.quantum_info import SparsePauliOp
op = SparsePauliOp.from_list([("XX", 2), ("YY", 1), ("IZ",2j), ("ZZ",1j)])
op.group_commuting()
```

### 示例 2
```python
op.group_commuting(qubit_wise=True)
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.group_commuting` 怎么用？
- `group_commuting` 的参数是什么？
- Qiskit 2.4.1 中 `group_commuting` 的最小示例是什么？
