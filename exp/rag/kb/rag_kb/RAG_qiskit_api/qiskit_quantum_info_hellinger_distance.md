# Qiskit 2.4.1 API: `qiskit.quantum_info.hellinger_distance`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.hellinger_distance`
- Kind: `function`

## 一句话用途
Computes the Hellinger distance between two counts distributions.

## 功能说明
Computes the Hellinger distance between
two counts distributions.

Parameters:
    dist_p (dict): First dict of counts.
    dist_q (dict): Second dict of counts.

Returns:
    float: Distance

References:
    `Hellinger Distance @ wikipedia <https://en.wikipedia.org/wiki/Hellinger_distance>`_

## 函数签名
```python
(dist_p: 'dict', dist_q: 'dict') -> 'float'
```

## 相关量子编程概念
- parameterized circuit

## 检索标签
- parameterized_circuit
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.hellinger_distance` 怎么用？
- `hellinger_distance` 的参数是什么？
- Qiskit 2.4.1 中 `hellinger_distance` 的最小示例是什么？
