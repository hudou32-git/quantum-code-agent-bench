# Qiskit 2.4.1 API: `qiskit.providers.basic_provider.basic_simulator.BackendV2`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.providers.basic_provider.basic_simulator`
- API: `qiskit.providers.basic_provider.basic_simulator.BackendV2`
- Kind: `class`

## 一句话用途
Abstract class for Backends

## 功能说明
Abstract class for Backends

This abstract class is to be used for all Backend objects created by a
provider. This version differs from earlier abstract Backend classes in
that the configuration attribute no longer exists. Instead, attributes
exposing equivalent required immutable properties of the backend device
are added. For example ``backend.configuration().n_qubits`` is accessible
from ``backend.num_qubits`` now.

The ``options`` attribute of the backend is used to contain the dynamic
user configurable options of the backend. It should be used more for
runtime options that configure how the backend is used. For example,
something like a ``shots`` field for a backend that runs experiments which
would contain an int for how many shots to execute.

A backend object can optionally contain methods named
``get_translation_stage_plugin`` and ``get_scheduling_stage_plugin``. If these
methods are present on a backend object and this object is used for
:func:`~.transpile` or :func:`~.generate_preset_pass_manager` the
transpilation process will default to using the output from those methods
as the scheduling stage and the translation compilation stage. This
enables a backend which has custom requirements for compilation to specify a
stage plugin for these stages to enable custom transformation of
the circuit to ensure it is runnable on the backend. These hooks are enabled
by default and should only be used to enable extra compilation steps
if they are **required** to ensure a circuit is executable on the backend or
have the expected level of performance. These methods are passed no input
arguments and are expected to return a ``str`` representing the method name
which should be a stage plugin (see: :mod:`qiskit.transpiler.preset_passmanagers.plugin`
for more details on plugins). The typical expected use case is for a backend
provider to implement a stage plugin for ``translation`` or ``scheduling``
that contains the custom compilation passes and then for the hook methods on
the backend object to return the plugin name so that :func:`~.transpile` will
use it by default when targeting the backend.

Subclasses of this should override the public method :meth:`run` and the internal
:meth:`_default_options`:

.. automethod:: _default_options

## 函数签名
```python
(provider=None, name: str | None = None, description: str | None = None, online_date: datetime.datetime | None = None, backend_version: str | None = None, **fields)
```

## 相关量子编程概念
- backend execution
- transpilation

## 检索标签
- backend_provider
- circuit_construction
- primitive
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.providers.basic_provider.basic_simulator.BackendV2` 怎么用？
- `BackendV2` 的参数是什么？
- Qiskit 2.4.1 中 `BackendV2` 的最小示例是什么？
