# Qiskit 2.4.1 API: `qiskit.circuit.library.pauli_evolution.Pauli`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.library.pauli_evolution`
- API: `qiskit.circuit.library.pauli_evolution.Pauli`
- Kind: `class`

## 一句话用途
N-qubit Pauli operator.

## 功能说明
N-qubit Pauli operator.

This class represents an operator :math:`P` from the full :math:`n`-qubit
*Pauli* group

.. math::

    P = (-i)^{q} P_{n-1} \otimes ... \otimes P_{0}

where :math:`q\in \mathbb{Z}_4` and :math:`P_i \in \{I, X, Y, Z\}`
are single-qubit Pauli matrices:

.. math::

    I = \begin{pmatrix} 1 & 0  \\ 0 & 1  \end{pmatrix},
    X = \begin{pmatrix} 0 & 1  \\ 1 & 0  \end{pmatrix},
    Y = \begin{pmatrix} 0 & -i \\ i & 0  \end{pmatrix},
    Z = \begin{pmatrix} 1 & 0  \\ 0 & -1 \end{pmatrix}.

**Initialization**

A Pauli object can be initialized in several ways:

    ``Pauli(obj)``
        where ``obj`` is a Pauli string, ``Pauli`` or
        :class:`~qiskit.quantum_info.ScalarOp` operator, or a Pauli
        gate or :class:`~qiskit.QuantumCircuit` containing only
        Pauli gates.

    ``Pauli((z, x, phase))``
        where ``z`` and ``x`` are boolean ``numpy.ndarrays`` and ``phase`` is
        an integer in ``[0, 1, 2, 3]``.

    ``Pauli((z, x))``
        equivalent to ``Pauli((z, x, 0))`` with trivial phase.

**String representation**

An :math:`n`-qubit Pauli may be represented by a string consisting of
:math:`n` characters from ``['I', 'X', 'Y', 'Z']``, and optionally phase
coefficient in ``['', '-i', '-', 'i']``. For example: ``'XYZ'`` or
``'-iZIZ'``.

In the string representation qubit-0 corresponds to the right-most
Pauli character, and qubit-:math:`(n-1)` to the left-most Pauli
character. For example ``'XYZ'`` represents
:math:`X\otimes Y \otimes Z` with ``'Z'`` on qubit-0,
``'Y'`` on qubit-1, and ``'X'`` on qubit-2.

The string representation can be converted to a ``Pauli`` using the
class initialization (``Pauli('-iXYZ')``). A ``Pauli`` object can be
converted back to the string representation using the
:meth:`to_label` method or ``str(pauli)``.

.. note::

    Using ``str`` to convert a ``Pauli`` to a string will truncate the
    returned string for large numbers of qubits while :meth:`to_label`
    will return the full string with no truncation. The default
    truncation length is 50 characters. The default value can be
    changed by setting the class ``__truncate__`` attribute to an integer
    value. If set to ``0`` no truncation will be performed.

**Array Representation**

The internal data structure of an :math:`n`-qubit Pauli is two
length-:math:`n` boolean vectors :math:`z \in \mathbb{Z}_2^N`,
:math:`x \in \mathbb{Z}_2^N`, and an integer :math:`q \in \mathbb{Z}_4`
defining the Pauli operator

.. math::

    P = (-i)^{q + z\cdot x} Z^z \cdot X^x.

The :math:`k`-th qubit corresponds to the :math:`k`-th entry in the
:math:`z` and :math:`x` arrays

.. math::

    \begin{aligned}
    P &= P_{n-1} \otimes ... \otimes P_{0} \\
    P_k &= (-i)^{z[k] * x[k]} Z^{z[k]}\cdot X^{x[k]}
    \end{aligned}

where ``z[k] = P.z[k]``, ``x[k] = P.x[k]`` respectively.

The :math:`z` and :math:`x` arrays can be accessed and updated using
the :attr:`z` and :attr:`x` properties respectively. The phase integer
:math:`q` can be accessed and updated using the :attr:`phase` property.

**Matrix Operator Representation**

Pauli's can be converted to :math:`(2^n, 2^n)`
:class:`~qiskit.quantum_info.Operator` using the :meth:`to_operator` method,
or to a dense or sparse complex matrix using the :meth:`to_matrix` method.

**Data Access**

The individual qubit Paulis can be accessed and updated using the ``[]``
operator which accepts integer, lists, or slices for selecting subsets
of Paulis. Note that selecting subsets of Pauli's will discard the
phase of the current Pauli.

For example

.. plot::
   :include-source:
   :nofigs:

    from qiskit.quantum_info import Pauli

    P = Pauli('-iXYZ')

    print('P[0] =', repr(P[0]))
    print('P[1] =', repr(P[1]))
    print('P[2] =', repr(P[2]))
    print('P[:] =', repr(P[:]))
    print('P[::-1] =', repr(P[::-1]))

## 函数签名
```python
(data: 'str | tuple | Pauli | ScalarOp | QuantumCircuit | None' = None)
```

## 相关量子编程概念
- Pauli
- backend execution
- observable
- observable / Hamiltonian

## 检索标签
- backend_provider
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.circuit.library.pauli_evolution.Pauli` 怎么用？
- `Pauli` 的参数是什么？
- Qiskit 2.4.1 中 `Pauli` 的最小示例是什么？
