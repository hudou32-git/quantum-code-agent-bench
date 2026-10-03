# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.reverse_bits`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.reverse_bits`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Return a circuit with the opposite order of wires.

## 功能说明
Return a circuit with the opposite order of wires.

The circuit is "vertically" flipped. If a circuit is
defined over multiple registers, the resulting circuit will have
the same registers but with their order flipped.

This method is useful for converting a circuit written in little-endian
convention to the big-endian equivalent, and vice versa.

Returns:
    QuantumCircuit: the circuit with reversed bit order.

Examples:

    input:

    .. code-block:: text

             ┌───┐
        a_0: ┤ H ├──■─────────────────
             └───┘┌─┴─┐
        a_1: ─────┤ X ├──■────────────
                  └───┘┌─┴─┐
        a_2: ──────────┤ X ├──■───────
                       └───┘┌─┴─┐
        b_0: ───────────────┤ X ├──■──
                            └───┘┌─┴─┐
        b_1: ────────────────────┤ X ├
                                 └───┘

    output:

    .. code-block:: text

                                 ┌───┐
        b_0: ────────────────────┤ X ├
                            ┌───┐└─┬─┘
        b_1: ───────────────┤ X ├──■──
                       ┌───┐└─┬─┘
        a_0: ──────────┤ X ├──■───────
                  ┌───┐└─┬─┘
        a_1: ─────┤ X ├──■────────────
             ┌───┐└─┬─┘
        a_2: ┤ H ├──■─────────────────
             └───┘

## 函数签名
```python
(self) -> 'QuantumCircuit'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.reverse_bits` 怎么用？
- `reverse_bits` 的参数是什么？
- Qiskit 2.4.1 中 `reverse_bits` 的最小示例是什么？
