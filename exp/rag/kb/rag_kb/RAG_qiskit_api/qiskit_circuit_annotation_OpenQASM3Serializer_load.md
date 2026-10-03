# Qiskit 2.4.1 API: `qiskit.circuit.annotation.OpenQASM3Serializer.load`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.circuit.annotation`
- API: `qiskit.circuit.annotation.OpenQASM3Serializer.load`
- Kind: `method`
- Owner class: `OpenQASM3Serializer`

## 一句话用途
Load an annotation, if possible, from an OpenQASM 3 program.

## 功能说明
Load an annotation, if possible, from an OpenQASM 3 program.

The two arguments will be the two components of an annotation, as defined by the OpenQASM 3
specification.  The method should return :data:`NotImplemented` if it cannot handle the
annotation.

Args:
    namespace: the OpenQASM 3 "namespace" of the annotation.
    payload: the rest of the payload for the annotation.  This is arbitrary and free-form,
        and in general should have been serialized by a call to :meth:`dump`.

Returns:
    the created :class:`.Annotation` object, whose :attr:`.Annotation.namespace` attribute
    should be identical to the incoming ``namespace`` argument.  If this class cannot handle
    the annotation, it can also return :data:`NotImplemented`.

## 函数签名
```python
(self, namespace: 'str', payload: 'str') -> 'Annotation | Literal[NotImplemented]'
```

## 相关量子编程概念
- OpenQASM

## 检索标签
- circuit_construction
- qasm

## 适合回答的问题
- `qiskit.circuit.annotation.OpenQASM3Serializer.load` 怎么用？
- `load` 的参数是什么？
- Qiskit 2.4.1 中 `load` 的最小示例是什么？
