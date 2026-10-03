# Qiskit 2.4.1 API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.n_local.evolved_operator_ansatz`
- API: `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp`
- Kind: `class`

## 一句话用途
Sparse N-qubit operator in a Pauli basis representation.

## 功能说明
Sparse N-qubit operator in a Pauli basis representation.

This is a sparse representation of an N-qubit matrix
:class:`~qiskit.quantum_info.Operator` in terms of N-qubit
:class:`~qiskit.quantum_info.PauliList` and complex coefficients.

It can be used for performing operator arithmetic for hundreds of qubits
if the number of non-zero Pauli basis terms is sufficiently small.

The Pauli basis components are stored as a
:class:`~qiskit.quantum_info.PauliList` object and can be accessed
using the :attr:`~SparsePauliOp.paulis` attribute. The coefficients
are stored as a complex Numpy array vector and can be accessed using
the :attr:`~SparsePauliOp.coeffs` attribute.

.. rubric:: Data type of coefficients

The default ``dtype`` of the internal ``coeffs`` Numpy array is ``complex128``.  Users can
configure this by passing ``np.ndarray`` with a different dtype.  For example, a parameterized
:class:`SparsePauliOp` can be made as follows:

.. plot::
   :include-source:
   :nofigs:

    >>> import numpy as np
    >>> from qiskit.circuit import ParameterVector
    >>> from qiskit.quantum_info import SparsePauliOp

    >>> SparsePauliOp(["II", "XZ"], np.array(ParameterVector("a", 2)))
    SparsePauliOp(['II', 'XZ'],
          coeffs=[ParameterExpression(1.0*a[0]), ParameterExpression(1.0*a[1])])

.. note::

  Parameterized :class:`SparsePauliOp` does not support the following methods:

  - ``to_matrix(sparse=True)`` since ``scipy.sparse`` cannot have objects as elements.
  - ``to_operator()`` since :class:`~.quantum_info.Operator` does not support objects.
  - ``sort``, ``argsort`` since :class:`.ParameterExpression` does not support comparison.
  - ``equiv`` since :class:`.ParameterExpression` cannot be converted into complex.
  - ``chop`` since :class:`.ParameterExpression` does not support absolute value.

## 函数签名
```python
(data: 'PauliList | SparsePauliOp | Pauli | list | str', coeffs: 'np.ndarray | None' = None, *, ignore_pauli_phase: 'bool' = False, copy: 'bool' = True)
```

## 使用示例
### 示例 1
```python
from qiskit.quantum_info import SparsePauliOp



hamiltonian = SparsePauliOp.from_list([

    ("ZI", 1.0),

    ("IZ", 1.0),

    ("XX", 0.5),

])
```

### 示例 2
```python
import numpy as np
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import SparsePauliOp
```

## 相关量子编程概念
- Hamiltonian
- Pauli 算符
- observable
- observable / Hamiltonian
- parameterized circuit

## 检索标签
- circuit_construction
- observable_hamiltonian
- parameterized_circuit
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.n_local.evolved_operator_ansatz.SparsePauliOp` 怎么用？
- `SparsePauliOp` 的参数是什么？
- Qiskit 2.4.1 中 `SparsePauliOp` 的最小示例是什么？
