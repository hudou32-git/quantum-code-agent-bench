# Qiskit 2.4.1 API: `qiskit.compiler.transpiler.transpile`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.compiler.transpiler`
- API: `qiskit.compiler.transpiler.transpile`
- Kind: `function`

## 一句话用途
Transpile one or more circuits, according to some desired transpilation targets.

## 功能说明
Transpile one or more circuits, according to some desired transpilation targets.

Transpilation is potentially done in parallel using multiprocessing when ``circuits``
is a list with > 1 :class:`~.QuantumCircuit` object, depending on the local environment
and configuration.

The prioritization of transpilation target constraints works as follows: if a ``target``
input is provided, it will take priority over any ``backend`` input or loose constraints
(``basis_gates``, ``coupling_map``, or ``dt``). If a ``backend`` is provided
together with any loose constraint
from the list above, the loose constraint will take priority over the corresponding backend
constraint. This behavior is summarized in the table below. The first column
in the table summarizes the potential user-provided constraints, and each cell shows whether
the priority is assigned to that specific constraint input or another input
(`target`/`backend(V2)`).

============================ ========= ========================
User Provided                target    backend(V2)
============================ ========= ========================
**basis_gates**              target    basis_gates
**coupling_map**             target    coupling_map
**dt**                       target    dt
============================ ========= ========================

.. note::

    When the target basis consists of Clifford+T gates, this function constructs
    a specialized Clifford+T transpiler pipeline, see :func:`.clifford_t_pass_manager`
    for documentation. The arguments that apply to transpiling into continuous basis sets
    are ignored in this flow.

Args:
    circuits: Circuit(s) to transpile
    backend: If set, the transpiler will compile the input circuit to this target
        device. If any other option is explicitly set (e.g., ``coupling_map``), it
        will override the backend's.
    basis_gates: List of basis gate names to unroll to
        (e.g.: ``['u1', 'u2', 'u3', 'cx']``). If ``None``, do not unroll.
    coupling_map: Directed coupling map (perhaps custom) to target in mapping. If
        the coupling map is symmetric, both directions need to be specified.

        Multiple formats are supported:

        #. ``CouplingMap`` instance
        #. List, must be given as an adjacency matrix, where each entry
           specifies all directed two-qubit interactions supported by backend,
           e.g.: ``[[0, 1], [0, 3], [1, 2], [1, 5], [2, 5], [4, 1], [5, 3]]``
    initial_layout: Initial position of virtual qubits on physical qubits.
        If this layout makes the circuit compatible with the coupling_map
        constraints, it will be used. The final layout is not guaranteed to be the same,
        as the transpiler may permute qubits through swaps or other means.
        Multiple formats are supported:

        #. ``Layout`` instance
        #. Dict
           * virtual to physical::

                {qr[0]: 0,
                 qr[1]: 3,
                 qr[2]: 5}

           * physical to virtual::

                {0: qr[0],
                 3: qr[1],
                 5: qr[2]}

        #. List

           * virtual to physical::

                [0, 3, 5]  # virtual qubits are ordered (in addition to named)

           * physical to virtual::

                [qr[0], None, None, qr[1], None, qr[2]]

    layout_method: Name of layout selection pass ('trivial', 'dense', 'sabre').
        This can also be the external plugin name to use for the ``layout`` stage.
        You can see a list of installed plugins by using :func:`~.list_stage_plugins` with
        ``"layout"`` for the ``stage_name`` argument.
    routing_method: Name of routing pass
        ('basic', 'lookahead', 'stochastic', 'sabre', 'none').
        This can also be the external plugin name to use for the ``routing`` stage.
        You can see a list of installed plugins by using :func:`~.list_stage_plugins` with
        ``"routing"`` for the ``stage_name`` argument.
    translation_method: Name of translation pass (``"default"``, ``"translator"`` or
        ``"synthesis"``). This can also be the external plugin name to use for the
        ``translation`` stage.  You can see a list of installed plugins by using
        :func:`~.list_stage_plugins` with ``"translation"`` for the ``stage_name`` argument.
    scheduling_method: Name of scheduling pass.
        * ``'as_soon_as_possible'``: Schedule instructions greedily, as early as possible
        on a qubit resource. (alias: ``'asap'``)
        * ``'as_late_as_possible'``: Schedule instructions late, i.e. keeping qubits
        in the ground state when possible. (alias: ``'alap'``)
        If ``None``, no scheduling will be done. This can also be the external plugin name
        to use for the ``scheduling`` stage. You can see a list of installed plugins by
        using :func:`~.list_stage_plugins` with ``"scheduling"`` for the ``stage_name``
        argument.
    dt: Backend sample time (resolution) in seconds.
        If ``None``

...[truncated]

## 函数签名
```python
(circuits: ~_CircuitT, backend: qiskit.providers.backend.Backend | None = None, basis_gates: list[str] | None = None, coupling_map: qiskit.transpiler.coupling.CouplingMap | list[list[int]] | None = None, initial_layout: qiskit.transpiler.layout.Layout | dict | list | None = None, layout_method: str | None = None, routing_method: str | None = None, translation_method: str | None = None, scheduling_method: str | None = None, dt: float | None = None, approximation_degree: float | None = 1.0, seed_transpiler: int | None = None, optimization_level: int | None = None, callback: collections.abc.Callable[[qiskit.transpiler.basepasses.BasePass, qiskit._accelerate.circuit.DAGCircuit, float, qiskit.passmanager.compilation_status.PropertySet, int], typing.Any] | None = None, output_name: str | list[str] | None = None, unitary_synthesis_method: str = 'default', unitary_synthesis_plugin_config: dict | None = None, target: qiskit.transpiler.target.Target | None = None, hls_config: qiskit.transpiler.passes.synthesis.high_level_synthesis.HLSConfig | None = None, init_method: str | None = None, optimization_method: str | None = None, ignore_backend_supplied_default_methods: bool = False, num_processes: int | None = None, qubits_initially_zero: bool = True) -> ~_CircuitT
```

## 使用示例
### 示例 1
```python
from qiskit import QuantumCircuit, transpile



qc = QuantumCircuit(2)

qc.h(0)

qc.cx(0, 1)



tqc = transpile(qc, optimization_level=1)
```

## 相关量子编程概念
- Bell state / entanglement
- backend execution
- optimization level
- parameterized circuit
- transpilation
- 量子编译

## 检索标签
- backend_provider
- circuit_construction
- parameterized_circuit
- quantum_info
- single_qubit_gate
- transpilation
- two_qubit_gate

## 适合回答的问题
- `qiskit.compiler.transpiler.transpile` 怎么用？
- `transpile` 的参数是什么？
- Qiskit 2.4.1 中 `transpile` 的最小示例是什么？
