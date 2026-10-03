# Qiskit 2.4.1 API: `qiskit.quantum_info.StabilizerState.expand`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.StabilizerState.expand`
- Kind: `method`
- Owner class: `StabilizerState`

## 一句话用途
Return the tensor product stabilizer state other ⊗ self.

## 功能说明
Return the tensor product stabilizer state other ⊗ self.

Args:
    other (StabilizerState): a stabilizer state object.

Returns:
    StabilizerState: the tensor product operator other ⊗ self.

Raises:
    QiskitError: if other is not a StabilizerState.

## 函数签名
```python
(self, other: 'StabilizerState') -> 'StabilizerState'
```

## 检索标签
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.StabilizerState.expand` 怎么用？
- `expand` 的参数是什么？
- Qiskit 2.4.1 中 `expand` 的最小示例是什么？
