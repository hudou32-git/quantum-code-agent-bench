# Qiskit 2.4.1 API: `qiskit.quantum_info.PauliList.group_commuting`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.PauliList.group_commuting`
- Kind: `method`
- Owner class: `PauliList`

## 一句话用途
Partition a PauliList into sets of commuting Pauli strings.

## 功能说明
Partition a PauliList into sets of commuting Pauli strings.

Args:
    qubit_wise (bool): whether the commutation rule is applied to the whole operator,
        or on a per-qubit basis.  For example:

        .. plot::
           :include-source:
           :nofigs:

            >>> from qiskit.quantum_info import PauliList
            >>> op = PauliList(["XX", "YY", "IZ", "ZZ"])
            >>> op.group_commuting()
            [PauliList(['XX', 'YY']), PauliList(['IZ', 'ZZ'])]
            >>> op.group_commuting(qubit_wise=True)
            [PauliList(['XX']), PauliList(['YY']), PauliList(['IZ', 'ZZ'])]

Returns:
    list[PauliList]: List of PauliLists where each PauliList contains commuting Pauli operators.

## 函数签名
```python
(self, qubit_wise: 'bool' = False) -> 'list[PauliList]'
```

## 使用示例
### 示例 1
```python
from qiskit.quantum_info import PauliList
op = PauliList(["XX", "YY", "IZ", "ZZ"])
op.group_commuting()
```

### 示例 2
```python
op.group_commuting(qubit_wise=True)
```

## 相关量子编程概念
- observable / Hamiltonian

## 检索标签
- observable_hamiltonian
- quantum_info

## 适合回答的问题
- `qiskit.quantum_info.PauliList.group_commuting` 怎么用？
- `group_commuting` 的参数是什么？
- Qiskit 2.4.1 中 `group_commuting` 的最小示例是什么？
