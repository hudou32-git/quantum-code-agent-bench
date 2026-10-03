# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.DensityMatrix.from_label`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.DensityMatrix.from_label`
- Kind: `method`
- Owner class: `DensityMatrix`

## 一句话用途
Return a tensor product of Pauli X,Y,Z eigenstates.

## 功能说明
Return a tensor product of Pauli X,Y,Z eigenstates.

.. list-table:: Single-qubit state labels
   :header-rows: 1

   * - Label
     - Statevector
   * - ``"0"``
     - :math:`\begin{pmatrix} 1 & 0 \\ 0 & 0 \end{pmatrix}`
   * - ``"1"``
     - :math:`\begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix}`
   * - ``"+"``
     - :math:`\frac{1}{2}\begin{pmatrix} 1 & 1 \\ 1 & 1 \end{pmatrix}`
   * - ``"-"``
     - :math:`\frac{1}{2}\begin{pmatrix} 1 & -1 \\ -1 & 1 \end{pmatrix}`
   * - ``"r"``
     - :math:`\frac{1}{2}\begin{pmatrix} 1 & -i \\ i & 1 \end{pmatrix}`
   * - ``"l"``
     - :math:`\frac{1}{2}\begin{pmatrix} 1 & i \\ -i & 1 \end{pmatrix}`

Args:
    label (string): an eigenstate string ket label (see table for
                    allowed values).

Returns:
    DensityMatrix: The N-qubit basis state density matrix.

Raises:
    QiskitError: if the label contains invalid characters, or the length
                 of the label is larger than an explicitly specified num_qubits.

## 函数签名
```python
(label: 'str') -> 'DensityMatrix'
```

## 相关量子编程概念
- density matrix
- mixed state
- observable / Hamiltonian
- state simulation
- 密度矩阵

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.DensityMatrix.from_label` 怎么用？
- `from_label` 的参数是什么？
- Qiskit 2.4.1 中 `from_label` 的最小示例是什么？
