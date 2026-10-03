# Qiskit 2.4.1 API: `qiskit.transpiler.preset_passmanagers.plugin.passmanager_stage_plugins`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler.preset_passmanagers.plugin`
- API: `qiskit.transpiler.preset_passmanagers.plugin.passmanager_stage_plugins`
- Kind: `function`

## 一句话用途
Return a dict with, for each stage name, the class type of the plugin.

## 功能说明
Return a dict with, for each stage name, the class type of the plugin.

This function is useful for getting more information about a plugin:

.. plot::
   :include-source:
   :nofigs:

    from qiskit.transpiler.preset_passmanagers.plugin import passmanager_stage_plugins
    routing_plugins = passmanager_stage_plugins('routing')
    basic_plugin = routing_plugins['basic']
    help(basic_plugin)

.. code-block:: text

    Help on BasicSwapPassManager in module ...preset_passmanagers.builtin_plugins object:

    class BasicSwapPassManager(...preset_passmanagers.plugin.PassManagerStagePlugin)
     |  Plugin class for routing stage with :class:`~.BasicSwap`
     |
     |  Method resolution order:
     |      BasicSwapPassManager
     |      ...preset_passmanagers.plugin.PassManagerStagePlugin
     |      abc.ABC
     |      builtins.object
     ...

Args:
    stage: The stage name to get

Returns:
    dict: the key is the name of the plugin and the value is the class type for each.

Raises:
   TranspilerError: If an invalid stage name is specified.

## 函数签名
```python
(stage: str) -> dict[str, qiskit.transpiler.preset_passmanagers.plugin.PassManagerStagePlugin]
```

## 相关量子编程概念
- transpilation

## 检索标签
- circuit_construction
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.transpiler.preset_passmanagers.plugin.passmanager_stage_plugins` 怎么用？
- `passmanager_stage_plugins` 的参数是什么？
- Qiskit 2.4.1 中 `passmanager_stage_plugins` 的最小示例是什么？
