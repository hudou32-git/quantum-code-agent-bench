# Qiskit 2.4.1 API: `qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager.Backend`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager`
- API: `qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager.Backend`
- Kind: `class`

## 一句话用途
Base common type for all versioned Backend abstract classes.

## 功能说明
Base common type for all versioned Backend abstract classes.

Note this class should not be inherited from directly, it is intended
to be used for type checking. When implementing a provider you should use
the versioned abstract classes as the parent class and not this class
directly.

## 函数签名
```python
()
```

## 相关量子编程概念
- backend execution
- transpilation

## 检索标签
- backend_provider
- circuit_construction
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager.Backend` 怎么用？
- `Backend` 的参数是什么？
- Qiskit 2.4.1 中 `Backend` 的最小示例是什么？
