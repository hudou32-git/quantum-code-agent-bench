# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.inverse`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.inverse`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Invert (take adjoint of) this circuit.

## 功能说明
Invert (take adjoint of) this circuit.

This is done by recursively inverting all gates.

Args:
    annotated: indicates whether the inverse gate can be implemented
        as an annotated gate.

Returns:
    QuantumCircuit: the inverted circuit

Raises:
    CircuitError: if the circuit cannot be inverted.

Examples:

    input:

    .. code-block:: text

             ┌───┐
        q_0: ┤ H ├─────■──────
             └───┘┌────┴─────┐
        q_1: ─────┤ RX(1.57) ├
                  └──────────┘

    output:

    .. code-block:: text

                          ┌───┐
        q_0: ──────■──────┤ H ├
             ┌─────┴─────┐└───┘
        q_1: ┤ RX(-1.57) ├─────
             └───────────┘

## 函数签名
```python
(self, annotated: 'bool' = False) -> 'QuantumCircuit'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.inverse` 怎么用？
- `inverse` 的参数是什么？
- Qiskit 2.4.1 中 `inverse` 的最小示例是什么？
