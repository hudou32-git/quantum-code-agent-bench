# Qiskit 2.4.1 API: `qiskit.quantum_info.PauliList.sort`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.PauliList.sort`
- Kind: `method`
- Owner class: `PauliList`

## 一句话用途
Sort the rows of the table.

## 功能说明
Sort the rows of the table.

The default sort method is lexicographic sorting by qubit number.
By using the `weight` kwarg the output can additionally be sorted
by the number of non-identity terms in the Pauli, where the set of
all Paulis of a given weight are still ordered lexicographically.

**Example**

Consider sorting all a random ordering of all 2-qubit Paulis

.. plot::
   :include-source:
   :nofigs:

    from numpy.random import shuffle
    from qiskit.quantum_info.operators import PauliList

    # 2-qubit labels
    labels = ['II', 'IX', 'IY', 'IZ', 'XI', 'XX', 'XY', 'XZ',
              'YI', 'YX', 'YY', 'YZ', 'ZI', 'ZX', 'ZY', 'ZZ']
    # Shuffle Labels
    shuffle(labels)
    pt = PauliList(labels)
    print('Initial Ordering')
    print(pt)

    # Lexicographic Ordering
    srt = pt.sort()
    print('Lexicographically sorted')
    print(srt)

    # Weight Ordering
    srt = pt.sort(weight=True)
    print('Weight sorted')
    print(srt)

.. code-block:: text

    Initial Ordering
    ['YX', 'ZZ', 'XZ', 'YI', 'YZ', 'II', 'XX', 'XI', 'XY', 'YY', 'IX', 'IZ',
     'ZY', 'ZI', 'ZX', 'IY']
    Lexicographically sorted
    ['II', 'IX', 'IY', 'IZ', 'XI', 'XX', 'XY', 'XZ', 'YI', 'YX', 'YY', 'YZ',
     'ZI', 'ZX', 'ZY', 'ZZ']
    Weight sorted
    ['II', 'IX', 'IY', 'IZ', 'XI', 'YI', 'ZI', 'XX', 'XY', 'XZ', 'YX', 'YY',
     'YZ', 'ZX', 'ZY', 'ZZ']

Args:
    weight (bool): optionally sort by weight if ``True`` (Default: ``False``).
    phase (bool): Optionally sort by phase before weight or order
                  (Default: ``False``).

Returns:
    PauliList: a sorted copy of the original table.

## 函数签名
```python
(self, weight: 'bool' = False, phase: 'bool' = False) -> 'PauliList'
```

## 相关量子编程概念
- observable / Hamiltonian

## 检索标签
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.PauliList.sort` 怎么用？
- `sort` 的参数是什么？
- Qiskit 2.4.1 中 `sort` 的最小示例是什么？
