# Qiskit 2.4.1 API: `qiskit.compiler.transpiler.Layout.compose`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.compiler.transpiler`
- API: `qiskit.compiler.transpiler.Layout.compose`
- Kind: `method`
- Owner class: `Layout`

## 一句话用途
Compose this layout with another layout.

## 功能说明
Compose this layout with another layout.

If this layout represents a mapping from the P-qubits to the positions of the Q-qubits,
and the other layout represents a mapping from the Q-qubits to the positions of
the R-qubits, then the composed layout represents a mapping from the P-qubits to the
positions of the R-qubits.

Args:
    other: The existing :class:`.Layout` to compose this :class:`.Layout` with.
    qubits: A list of :class:`.Qubit` objects over which ``other`` is defined,
        used to establish the correspondence between the positions of the ``other``
        qubits and the actual qubits.

Returns:
    A new layout object the represents this layout composed with the ``other`` layout.

## 函数签名
```python
(self, other: 'Layout', qubits: 'list[Qubit]') -> 'Layout'
```

## 相关量子编程概念
- transpilation

## 检索标签
- circuit_construction
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.compiler.transpiler.Layout.compose` 怎么用？
- `compose` 的参数是什么？
- Qiskit 2.4.1 中 `compose` 的最小示例是什么？
