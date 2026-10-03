# Qiskit 2.4.1 API: `qiskit.primitives.base.base_sampler.Job`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.primitives.base.base_sampler`
- API: `qiskit.primitives.base.base_sampler.Job`
- Kind: `class`

## 一句话用途
Class to handle jobs

## 功能说明
Class to handle jobs

This first version of the Job abstract class is written to be mostly
backwards compatible with the legacy providers interface. This was done to ease
the transition for users and provider maintainers to the new versioned providers. Expect,
future versions of this abstract class to change the data model and
interface.

## 函数签名
```python
(backend: 'Backend | None', job_id: 'str', **kwargs) -> 'None'
```

## 相关量子编程概念
- backend execution

## 检索标签
- backend_provider
- primitive

## 适合回答的问题
- `qiskit.primitives.base.base_sampler.Job` 怎么用？
- `Job` 的参数是什么？
- Qiskit 2.4.1 中 `Job` 的最小示例是什么？
