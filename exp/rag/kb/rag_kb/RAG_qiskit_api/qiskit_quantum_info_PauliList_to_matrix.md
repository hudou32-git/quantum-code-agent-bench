# Qiskit 2.4.1 API: `qiskit.quantum_info.PauliList.to_matrix`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.PauliList.to_matrix`
- Kind: `method`
- Owner class: `PauliList`

## 一句话用途
Convert to a list or array of Pauli matrices.

## 功能说明
Convert to a list or array of Pauli matrices.

For large PauliLists converting using the ``array=True``
kwarg will be more efficient since it allocates memory a full
rank-3 Numpy array of matrices in advance.

.. list-table:: Pauli Representations
    :header-rows: 1

    * - Label
      - Symplectic
      - Matrix
    * - ``"I"``
      - :math:`[0, 0]`
      - :math:`\begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}`
    * - ``"X"``
      - :math:`[1, 0]`
      - :math:`\begin{bmatrix} 0 & 1 \\ 1 & 0  \end{bmatrix}`
    * - ``"Y"``
      - :math:`[1, 1]`
      - :math:`\begin{bmatrix} 0 & -i \\ i & 0  \end{bmatrix}`
    * - ``"Z"``
      - :math:`[0, 1]`
      - :math:`\begin{bmatrix} 1 & 0 \\ 0 & -1  \end{bmatrix}`

Args:
    sparse (bool): if ``True`` return sparse CSR matrices, otherwise
                   return dense Numpy arrays (Default: ``False``).
    array (bool): return as rank-3 numpy array if ``True``, otherwise
                  return a list of Numpy arrays (Default: ``False``).

Returns:
    list: A list of dense Pauli matrices if ``array=False`` and ``sparse=False``.
    list: A list of sparse Pauli matrices if ``array=False`` and ``sparse=True``.
    array: A dense rank-3 array of Pauli matrices if ``array=True``.

## 函数签名
```python
(self, sparse: 'bool' = False, array: 'bool' = False) -> 'list'
```

## 相关量子编程概念
- observable / Hamiltonian

## 检索标签
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.PauliList.to_matrix` 怎么用？
- `to_matrix` 的参数是什么？
- Qiskit 2.4.1 中 `to_matrix` 的最小示例是什么？
