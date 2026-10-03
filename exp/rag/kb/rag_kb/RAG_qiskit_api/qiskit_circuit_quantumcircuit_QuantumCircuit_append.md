# Qiskit 2.4.1 API: `qiskit.circuit.quantumcircuit.QuantumCircuit.append`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.quantumcircuit`
- API: `qiskit.circuit.quantumcircuit.QuantumCircuit.append`
- Kind: `method`
- Owner class: `QuantumCircuit`

## 一句话用途
Append one or more instructions to the end of the circuit, modifying the circuit in place.

## 功能说明
Append one or more instructions to the end of the circuit, modifying the circuit in
place.

The ``qargs`` and ``cargs`` will be expanded and broadcast according to the rules of the
given :class:`~.circuit.Instruction`, and any non-:class:`.Bit` specifiers (such as
integer indices) will be resolved into the relevant instances.

If a :class:`.CircuitInstruction` is given, it will be unwrapped, verified in the context of
this circuit, and a new object will be appended to the circuit.  In this case, you may not
pass ``qargs`` or ``cargs`` separately.

Args:
    instruction: :class:`~.circuit.Instruction` instance to append, or a
        :class:`.CircuitInstruction` with all its context.
    qargs: specifiers of the :class:`~.circuit.Qubit`\ s to attach instruction to.
    cargs: specifiers of the :class:`.Clbit`\ s to attach instruction to.
    copy: if ``True`` (the default), then the incoming ``instruction`` is copied before
        adding it to the circuit if it contains symbolic parameters, so it can be safely
        mutated without affecting other circuits the same instruction might be in.  If you
        are sure this instruction will not be in other circuits, you can set this ``False``
        for a small speedup.

Returns:
    qiskit.circuit.InstructionSet: a handle to the :class:`.CircuitInstruction`\ s that
    were actually added to the circuit.

Raises:
    CircuitError: if the operation passed is not an instance of :class:`~.circuit.Instruction` .

## 函数签名
```python
(self, instruction: 'Operation | CircuitInstruction', qargs: 'Sequence[QubitSpecifier] | None' = None, cargs: 'Sequence[ClbitSpecifier] | None' = None, *, copy: 'bool' = True) -> 'InstructionSet'
```

## 使用示例
### 示例 1
```python
from qiskit import QuantumCircuit

from qiskit.circuit.library import XGate



qc = QuantumCircuit(1)

qc.append(XGate(), [0])
```

## 相关量子编程概念
- circuit construction
- parameterized circuit
- quantum circuit
- 量子线路

## 检索标签
- circuit_construction
- parameterized_circuit

## 适合回答的问题
- `qiskit.circuit.quantumcircuit.QuantumCircuit.append` 怎么用？
- `append` 的参数是什么？
- Qiskit 2.4.1 中 `append` 的最小示例是什么？
