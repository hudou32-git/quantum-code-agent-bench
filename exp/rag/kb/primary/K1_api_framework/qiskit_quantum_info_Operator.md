# Qiskit 2.4.1 API: `qiskit.quantum_info.Operator`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info`
- API: `qiskit.quantum_info.Operator`
- Kind: `class`

## 一句话用途
Matrix operator class

## 功能说明
Matrix operator class

This represents a matrix operator :math:`M` that will
:meth:`~Statevector.evolve` a :class:`Statevector` :math:`|\psi\rangle`
by matrix-vector multiplication

.. math::

    |\psi\rangle \mapsto M|\psi\rangle,

and will :meth:`~DensityMatrix.evolve` a :class:`DensityMatrix` :math:`\rho`
by left and right multiplication

.. math::

    \rho \mapsto M \rho M^\dagger.

For example, the following operator :math:`M = X` applied to the zero state
:math:`|\psi\rangle=|0\rangle (\rho = |0\rangle\langle 0|)` changes it to the
one state :math:`|\psi\rangle=|1\rangle (\rho = |1\rangle\langle 1|)`:

.. plot::
   :include-source:
   :nofigs:

    >>> import numpy as np
    >>> from qiskit.quantum_info import Operator
    >>> op = Operator(np.array([[0.0, 1.0], [1.0, 0.0]]))  # Represents Pauli X operator

    >>> from qiskit.quantum_info import Statevector
    >>> sv = Statevector(np.array([1.0, 0.0]))
    >>> sv.evolve(op)
    Statevector([0.+0.j, 1.+0.j],
                dims=(2,))

    >>> from qiskit.quantum_info import DensityMatrix
    >>> dm = DensityMatrix(np.array([[1.0, 0.0], [0.0, 0.0]]))
    >>> dm.evolve(op)
    DensityMatrix([[0.+0.j, 0.+0.j],
                [0.+0.j, 1.+0.j]],
                dims=(2,))

## 函数签名
```python
(data: 'QuantumCircuit | Operation | BaseOperator | np.ndarray', input_dims: 'tuple | None' = None, output_dims: 'tuple | None' = None)
```

## 使用示例
### 示例 1
```python
import numpy as np
from qiskit.quantum_info import Operator
op = Operator(np.array([[0.0, 1.0], [1.0, 0.0]]))  # Represents Pauli X operator
```

### 示例 2
```python
from qiskit.quantum_info import Statevector
sv = Statevector(np.array([1.0, 0.0]))
sv.evolve(op)
```

## 相关量子编程概念
- observable / Hamiltonian
- operator
- state simulation
- unitary
- 算符

## 检索标签
- observable_hamiltonian
- quantum_info

## 适合回答的问题
- `qiskit.quantum_info.Operator` 怎么用？
- `Operator` 的参数是什么？
- Qiskit 2.4.1 中 `Operator` 的最小示例是什么？
