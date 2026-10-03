# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_label`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_label`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Return a tensor product of Pauli X,Y,Z eigenstates.

## 功能说明
Return a tensor product of Pauli X,Y,Z eigenstates.

.. list-table:: Single-qubit state labels
   :header-rows: 1

   * - Label
     - Statevector
   * - ``"0"``
     - :math:`[1, 0]`
   * - ``"1"``
     - :math:`[0, 1]`
   * - ``"+"``
     - :math:`[1 / \sqrt{2},  1 / \sqrt{2}]`
   * - ``"-"``
     - :math:`[1 / \sqrt{2},  -1 / \sqrt{2}]`
   * - ``"r"``
     - :math:`[1 / \sqrt{2},  i / \sqrt{2}]`
   * - ``"l"``
     - :math:`[1 / \sqrt{2},  -i / \sqrt{2}]`

Args:
    label (string): an eigenstate string ket label (see table for
                    allowed values).

Returns:
    Statevector: The N-qubit basis state statevector.

Raises:
    QiskitError: if the label contains invalid characters, or the
                 length of the label is larger than an explicitly
                 specified num_qubits.

## 函数签名
```python
(label: 'str') -> 'Statevector'
```

## 相关量子编程概念
- observable / Hamiltonian
- simulation
- state simulation
- state vector
- 态向量

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_label` 怎么用？
- `from_label` 的参数是什么？
- Qiskit 2.4.1 中 `from_label` 的最小示例是什么？
