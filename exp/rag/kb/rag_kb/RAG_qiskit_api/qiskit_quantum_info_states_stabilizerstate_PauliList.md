# Qiskit 2.4.1 API: `qiskit.quantum_info.states.stabilizerstate.PauliList`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.quantum_info.states.stabilizerstate`
- API: `qiskit.quantum_info.states.stabilizerstate.PauliList`
- Kind: `class`

## 一句话用途
List of N-qubit Pauli operators.

## 功能说明
List of N-qubit Pauli operators.

This class is an efficient representation of a list of
:class:`Pauli` operators. It supports 1D numpy array indexing
returning a :class:`Pauli` for integer indexes or a
:class:`PauliList` for slice or list indices.

**Initialization**

A PauliList object can be initialized in several ways.

    ``PauliList(list[str])``
        where strings are same representation with :class:`~qiskit.quantum_info.Pauli`.

    ``PauliList(Pauli) and PauliList(list[Pauli])``
        where Pauli is :class:`~qiskit.quantum_info.Pauli`.

    ``PauliList.from_symplectic(z, x, phase)``
        where ``z`` and ``x`` are 2 dimensional boolean ``numpy.ndarrays`` and ``phase`` is
        an integer in ``[0, 1, 2, 3]``.

For example,

.. plot::
   :include-source:
   :nofigs:
   :context: reset

    import numpy as np

    from qiskit.quantum_info import Pauli, PauliList

    # 1. init from list[str]
    pauli_list = PauliList(["II", "+ZI", "-iYY"])
    print("1. ", pauli_list)

    pauli1 = Pauli("iXI")
    pauli2 = Pauli("iZZ")

    # 2. init from Pauli
    print("2. ", PauliList(pauli1))

    # 3. init from list[Pauli]
    print("3. ", PauliList([pauli1, pauli2]))

    # 4. init from np.ndarray
    z = np.array([[True, True], [False, False]])
    x = np.array([[False, True], [True, False]])
    phase = np.array([0, 1])
    pauli_list = PauliList.from_symplectic(z, x, phase)
    print("4. ", pauli_list)

.. code-block:: text

    1.  ['II', 'ZI', '-iYY']
    2.  ['iXI']
    3.  ['iXI', 'iZZ']
    4.  ['YZ', '-iIX']

**Data Access**

The individual Paulis can be accessed and updated using the ``[]``
operator which accepts integer, lists, or slices for selecting subsets
of PauliList. If integer is given, it returns Pauli not PauliList.

.. plot::
   :include-source:
   :nofigs:
   :context:

    pauli_list = PauliList(["XX", "ZZ", "IZ"])
    print("Integer: ", repr(pauli_list[1]))
    print("List: ", repr(pauli_list[[0, 2]]))
    print("Slice: ", repr(pauli_list[0:2]))

.. code-block:: text

    Integer:  Pauli('ZZ')
    List:  PauliList(['XX', 'IZ'])
    Slice:  PauliList(['XX', 'ZZ'])

**Iteration**

Rows in the Pauli table can be iterated over like a list. Iteration can
also be done using the label or matrix representation of each row using the
:meth:`label_iter` and :meth:`matrix_iter` methods.

## 函数签名
```python
(data: 'Pauli | list')
```

## 相关量子编程概念
- observable / Hamiltonian

## 检索标签
- circuit_construction
- observable_hamiltonian
- quantum_info
- single_qubit_gate

## 适合回答的问题
- `qiskit.quantum_info.states.stabilizerstate.PauliList` 怎么用？
- `PauliList` 的参数是什么？
- Qiskit 2.4.1 中 `PauliList` 的最小示例是什么？
