# Qiskit 2.4.1 API: `qiskit.primitives.base.base_primitive_v1.Options`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.primitives.base.base_primitive_v1`
- API: `qiskit.primitives.base.base_primitive_v1.Options`
- Kind: `class`

## 一句话用途
Base options object

## 功能说明
Base options object

This class is what all backend options are based
on. The properties of the class are intended to be all dynamically
adjustable so that a user can reconfigure the backend on demand. If a
property is immutable to the user (eg something like number of qubits)
that should be a configuration of the backend class itself instead of the
options.

Instances of this class behave like dictionaries. Accessing an
option with a default value can be done with the `get()` method:

>>> options = Options(opt1=1, opt2=2)
>>> options.get("opt1")
1
>>> options.get("opt3", default="hello")
'hello'

Key-value pairs for all options can be retrieved using the `items()` method:

>>> list(options.items())
[('opt1', 1), ('opt2', 2)]

Options can be updated by name:

>>> options["opt1"] = 3
>>> options.get("opt1")
3

Runtime validators can be registered. See `set_validator`.
Updates through `update_options` and indexing (`__setitem__`) validate
the new value before performing the update and raise `ValueError` if
the new value is invalid.

>>> options.set_validator("opt1", (1, 5))
>>> options["opt1"] = 4
>>> options["opt1"]
4
>>> options["opt1"] = 10  # doctest: +ELLIPSIS
Traceback (most recent call last):
...
ValueError: ...

## 函数签名
```python
(**kwargs)
```

## 使用示例
### 示例 1
```python
options = Options(opt1=1, opt2=2)
options.get("opt1")
```

### 示例 2
```python
options.get("opt3", default="hello")
```

## 相关量子编程概念
- backend execution

## 检索标签
- backend_provider
- primitive
- single_qubit_gate

## 适合回答的问题
- `qiskit.primitives.base.base_primitive_v1.Options` 怎么用？
- `Options` 的参数是什么？
- Qiskit 2.4.1 中 `Options` 的最小示例是什么？
