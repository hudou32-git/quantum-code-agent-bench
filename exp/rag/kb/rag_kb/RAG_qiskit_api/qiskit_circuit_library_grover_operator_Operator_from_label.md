# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.Operator.from_label`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.Operator.from_label`
- Kind: `method`
- Owner class: `Operator`

## 一句话用途
Return a tensor product of single-qubit operators.

## 功能说明
Return a tensor product of single-qubit operators.

Args:
    label (string): single-qubit operator string.

Returns:
    Operator: The N-qubit operator.

Raises:
    QiskitError: if the label contains invalid characters, or the
                 length of the label is larger than an explicitly
                 specified num_qubits.

Additional Information:
    The labels correspond to the single-qubit matrices:
    'I': [[1, 0], [0, 1]]
    'X': [[0, 1], [1, 0]]
    'Y': [[0, -1j], [1j, 0]]
    'Z': [[1, 0], [0, -1]]
    'H': [[1, 1], [1, -1]] / sqrt(2)
    'S': [[1, 0], [0 , 1j]]
    'T': [[1, 0], [0, (1+1j) / sqrt(2)]]
    '0': [[1, 0], [0, 0]]
    '1': [[0, 0], [0, 1]]
    '+': [[0.5, 0.5], [0.5 , 0.5]]
    '-': [[0.5, -0.5], [-0.5 , 0.5]]
    'r': [[0.5, -0.5j], [0.5j , 0.5]]
    'l': [[0.5, 0.5j], [-0.5j , 0.5]]

## 函数签名
```python
(label: 'str') -> 'Operator'
```

## 相关量子编程概念
- operator
- unitary
- 算符

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.Operator.from_label` 怎么用？
- `from_label` 的参数是什么？
- Qiskit 2.4.1 中 `from_label` 的最小示例是什么？
