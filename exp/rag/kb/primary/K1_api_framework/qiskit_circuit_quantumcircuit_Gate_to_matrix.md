# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.Gate.to_matrix`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.Gate.to_matrix`
- Kind: `method`
- Owner class: `Gate`

## 一句话用途
Return a Numpy.array for the gate unitary matrix.

## 功能说明
Return a Numpy.array for the gate unitary matrix.

Returns:
    np.ndarray: if the Gate subclass has a matrix definition.

Raises:
    CircuitError: If a Gate subclass does not implement this method an
        exception will be raised when this base class method is called.

## 函数签名
```python
(self) -> 'np.ndarray'
```

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.Gate.to_matrix` 怎么用？
- `to_matrix` 的参数是什么？
- Qiskit 2.4.1 中 `to_matrix` 的最小示例是什么？
