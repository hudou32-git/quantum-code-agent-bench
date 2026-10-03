# Qiskit 2.4.1 API: `qiskit.transpiler.PassManager.run`

## 基本信息
- Framework: Qiskit
- Version: 2.4.1
- Module: `qiskit.transpiler`
- API: `qiskit.transpiler.PassManager.run`
- Kind: `method`
- Owner class: `PassManager`

## 一句话用途
Run all the passes on the specified ``circuits``.

## 功能说明
Run all the passes on the specified ``circuits``.

Args:
    circuits: Circuit(s) to transform via all the registered passes.
    output_name: The output circuit name. If ``None``, it will be set to the same as the
        input circuit name.
    callback: A callback function that will be called after each pass execution. The
        function will be called with 5 keyword arguments::

            pass_ (Pass): the pass being run
            dag (DAGCircuit): the dag output of the pass
            time (float): the time to execute the pass
            property_set (PropertySet): the property set
            count (int): the index for the pass execution

        .. note::

            Beware that the keyword arguments here are different to those used by the
            generic :class:`.BasePassManager`.  This pass manager will translate those
            arguments into the form described above.

        The exact arguments pass expose the internals of the pass
        manager and are subject to change as the pass manager internals
        change. If you intend to reuse a callback function over
        multiple releases be sure to check that the arguments being
        passed are the same.

        To use the callback feature you define a function that will
        take in kwargs dict and access the variables. For example::

            def callback_func(**kwargs):
                pass_ = kwargs['pass_']
                dag = kwargs['dag']
                time = kwargs['time']
                property_set = kwargs['property_set']
                count = kwargs['count']
                ...

        .. note::

            When running transpilation with multi-processing,
            the callback function is invoked within the context
            of each sub-process, independently of the
            parent process.

    num_processes: The maximum number of parallel processes to launch if parallel
        execution is enabled. This argument overrides ``num_processes`` in the user
        configuration file, and the ``QISKIT_NUM_PROCS`` environment variable. If set
        to ``None`` the system default or local user configuration will be used.
    property_set: If given, the initial value to use as the :class:`.PropertySet` for the
        pass manager pipeline.  This can be used to persist analysis from one run to
        another, in cases where you know the analysis is safe to share.  Beware that some
        analysis will be specific to the input circuit and the particular :class:`.Target`,
        so you should take a lot of care when using this argument.

Returns:
    The transformed circuit(s).

## 函数签名
```python
(self, circuits: '_CircuitsT', output_name: 'str | None' = None, callback: 'Callable | None' = None, num_processes: 'int | None' = None, *, property_set: 'dict[str, object] | None' = None) -> '_CircuitsT'
```

## 相关量子编程概念
- backend execution
- pass manager
- transpilation
- 编译流程

## 检索标签
- backend_provider
- circuit_construction
- conversion
- single_qubit_gate
- transpilation

## 适合回答的问题
- `qiskit.transpiler.PassManager.run` 怎么用？
- `run` 的参数是什么？
- Qiskit 2.4.1 中 `run` 的最小示例是什么？
