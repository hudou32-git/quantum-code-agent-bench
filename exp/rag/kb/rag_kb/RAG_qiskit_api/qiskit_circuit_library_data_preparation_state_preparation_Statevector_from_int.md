# Qiskit 2.4.1 API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_int`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.data_preparation.state_preparation`
- API: `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_int`
- Kind: `method`
- Owner class: `Statevector`

## 一句话用途
Return a computational basis statevector.

## 功能说明
Return a computational basis statevector.

Args:
    i (int): the basis state element.
    dims (int or tuple or list): The subsystem dimensions of the statevector
                                 (See additional information).

Returns:
    Statevector: The computational basis state :math:`|i\rangle`.

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
(i: 'int', dims: 'int | tuple | list') -> 'Statevector'
```

## 相关量子编程概念
- simulation
- state simulation
- state vector
- 态向量

## 检索标签
- circuit_construction
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.data_preparation.state_preparation.Statevector.from_int` 怎么用？
- `from_int` 的参数是什么？
- Qiskit 2.4.1 中 `from_int` 的最小示例是什么？
