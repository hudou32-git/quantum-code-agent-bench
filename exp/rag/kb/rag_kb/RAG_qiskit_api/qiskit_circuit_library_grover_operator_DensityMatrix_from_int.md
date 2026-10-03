# Qiskit 2.4.1 API: `qiskit.circuit.library.grover_operator.DensityMatrix.from_int`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.grover_operator`
- API: `qiskit.circuit.library.grover_operator.DensityMatrix.from_int`
- Kind: `method`
- Owner class: `DensityMatrix`

## 一句话用途
Return a computational basis state density matrix.

## 功能说明
Return a computational basis state density matrix.

Args:
    i (int): the basis state element.
    dims (int or tuple or list): The subsystem dimensions of the statevector
                                 (See additional information).

Returns:
    DensityMatrix: The computational basis state :math:`|i\rangle\!\langle i|`.

Additional Information:
    The ``dims`` kwarg can be an integer or an iterable of integers.

    * ``Iterable`` -- the subsystem dimensions are the values in the list
      with the total number of subsystems given by the length of the list.

    * ``Int`` -- the integer specifies the total dimension of the
      state. If it is a power of two the state will be initialized
      as an N-qubit state. If it is not a power of two the state
      will have a single d-dimensional subsystem.

## 函数签名
```python
(i: 'int', dims: 'int | tuple | list') -> 'DensityMatrix'
```

## 相关量子编程概念
- density matrix
- mixed state
- state simulation
- 密度矩阵

## 检索标签
- circuit_construction
- quantum_info

## 适合回答的问题
- `qiskit.circuit.library.grover_operator.DensityMatrix.from_int` 怎么用？
- `from_int` 的参数是什么？
- Qiskit 2.4.1 中 `from_int` 的最小示例是什么？
