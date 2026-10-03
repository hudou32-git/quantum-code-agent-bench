# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.sort`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.sort`
- Kind: `method`
- Owner class: `SparsePauliOp`

## 一句话用途
Sort the rows of the table.

## 功能说明
Sort the rows of the table.

After sorting the coefficients using numpy's argsort, sort by Pauli.
Pauli sort takes precedence.
If Pauli is the same, it will be sorted by coefficient.
By using the `weight` kwarg the output can additionally be sorted
by the number of non-identity terms in the Pauli, where the set of
all Pauli's of a given weight are still ordered lexicographically.

**Example**

Here is an example of how to use SparsePauliOp sort.

.. plot::
   :include-source:
   :nofigs:

    import numpy as np
    from qiskit.quantum_info import SparsePauliOp

    # 2-qubit labels
    labels = ["XX", "XX", "XX", "YI", "II", "XZ", "XY", "XI"]
    # coeffs
    coeffs = [2.+1.j, 2.+2.j, 3.+0.j, 3.+0.j, 4.+0.j, 5.+0.j, 6.+0.j, 7.+0.j]

    # init
    spo = SparsePauliOp(labels, coeffs)
    print('Initial Ordering')
    print(spo)

    # Lexicographic Ordering
    srt = spo.sort()
    print('Lexicographically sorted')
    print(srt)

    # Lexicographic Ordering
    srt = spo.sort(weight=False)
    print('Lexicographically sorted')
    print(srt)

    # Weight Ordering
    srt = spo.sort(weight=True)
    print('Weight sorted')
    print(srt)

.. code-block:: text

    Initial Ordering
    SparsePauliOp(['XX', 'XX', 'XX', 'YI', 'II', 'XZ', 'XY', 'XI'],
                  coeffs=[2.+1.j, 2.+2.j, 3.+0.j, 3.+0.j, 4.+0.j, 5.+0.j, 6.+0.j, 7.+0.j])
    Lexicographically sorted
    SparsePauliOp(['II', 'XI', 'XX', 'XX', 'XX', 'XY', 'XZ', 'YI'],
                  coeffs=[4.+0.j, 7.+0.j, 2.+1.j, 2.+2.j, 3.+0.j, 6.+0.j, 5.+0.j, 3.+0.j])
    Lexicographically sorted
    SparsePauliOp(['II', 'XI', 'XX', 'XX', 'XX', 'XY', 'XZ', 'YI'],
                  coeffs=[4.+0.j, 7.+0.j, 2.+1.j, 2.+2.j, 3.+0.j, 6.+0.j, 5.+0.j, 3.+0.j])
    Weight sorted
    SparsePauliOp(['II', 'XI', 'YI', 'XX', 'XX', 'XX', 'XY', 'XZ'],
                  coeffs=[4.+0.j, 7.+0.j, 3.+0.j, 2.+1.j, 2.+2.j, 3.+0.j, 6.+0.j, 5.+0.j])

Args:
    weight (bool): optionally sort by weight if True (Default: False).
    By using the weight kwarg the output can additionally be sorted
    by the number of non-identity terms in the Pauli.

Returns:
    SparsePauliOp: a sorted copy of the original table.

## 函数签名
```python
(self, weight: 'bool' = False)
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
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp.sort` 怎么用？
- `sort` 的参数是什么？
- Qiskit 2.4.1 中 `sort` 的最小示例是什么？
