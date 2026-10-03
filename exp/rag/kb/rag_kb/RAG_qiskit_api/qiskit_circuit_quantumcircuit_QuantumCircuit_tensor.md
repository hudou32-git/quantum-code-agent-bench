# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.tensor`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.tensor`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Tensor ``self`` with ``other``.

## 功能说明
Tensor ``self`` with ``other``.

Remember that in the little-endian convention the leftmost operation will be at the bottom
of the circuit. See also
`the docs <https://quantum.cloud.ibm.com/docs/guides/construct-circuits>`__
for more information.

.. code-block:: text

         ┌────────┐        ┌─────┐          ┌─────┐
    q_0: ┤ bottom ├ ⊗ q_0: ┤ top ├  = q_0: ─┤ top ├──
         └────────┘        └─────┘         ┌┴─────┴─┐
                                      q_1: ┤ bottom ├
                                           └────────┘

Args:
    other (QuantumCircuit): The other circuit to tensor this circuit with.
    inplace (bool): If ``True``, modify the object. Otherwise return composed circuit.

Examples:

    .. plot::
       :alt: Circuit diagram output by the previous code.
       :include-source:

       from qiskit import QuantumCircuit
       top = QuantumCircuit(1)
       top.x(0);
       bottom = QuantumCircuit(2)
       bottom.cry(0.2, 0, 1);
       tensored = bottom.tensor(top)
       tensored.draw('mpl')

Returns:
    QuantumCircuit: The tensored circuit (returns ``None`` if ``inplace=True``).

## 函数签名
```python
(self, other: 'QuantumCircuit', inplace: 'bool' = False) -> 'QuantumCircuit | None'
```

## 相关量子编程概念
- circuit construction
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.tensor` 怎么用？
- `tensor` 的参数是什么？
- Qiskit 2.4.1 中 `tensor` 的最小示例是什么？
