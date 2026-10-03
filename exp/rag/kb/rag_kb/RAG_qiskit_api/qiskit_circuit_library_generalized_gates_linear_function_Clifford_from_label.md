# Qiskit 2.4.1 API: `qiskit.circuit.library.generalized_gates.linear_function.Clifford.from_label`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.generalized_gates.linear_function`
- API: `qiskit.circuit.library.generalized_gates.linear_function.Clifford.from_label`
- Kind: `method`
- Owner class: `Clifford`

## 一句话用途
Return a tensor product of single-qubit Clifford gates.

## 功能说明
Return a tensor product of single-qubit Clifford gates.

Args:
    label (string): single-qubit operator string.

Returns:
    Clifford: The N-qubit Clifford operator.

Raises:
    QiskitError: if the label contains invalid characters.

Additional Information:
    The labels correspond to the single-qubit Cliffords are

    * - Label
      - Stabilizer
      - Destabilizer
    * - ``"I"``
      - +Z
      - +X
    * - ``"X"``
      - -Z
      - +X
    * - ``"Y"``
      - -Z
      - -X
    * - ``"Z"``
      - +Z
      - -X
    * - ``"H"``
      - +X
      - +Z
    * - ``"S"``
      - +Z
      - +Y

## 函数签名
```python
(label: 'str') -> 'Clifford'
```

## 相关量子编程概念
- Clifford circuit
- stabilizer

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.generalized_gates.linear_function.Clifford.from_label` 怎么用？
- `from_label` 的参数是什么？
- Qiskit 2.4.1 中 `from_label` 的最小示例是什么？
