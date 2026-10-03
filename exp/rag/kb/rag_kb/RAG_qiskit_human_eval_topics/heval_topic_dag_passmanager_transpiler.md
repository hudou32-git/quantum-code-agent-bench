# HumanEval-Qiskit Topic: DAGCircuit, PassManager, custom transpiler flows

## Metadata
- Kind: `human_eval_topic_recipe`
- Topics: `DAGCircuit`, `PassManager`, `transpile`, `CouplingMap`, `HumanEval`

## Task pattern
Imports include `qiskit.dagcircuit.DAGCircuit` or `qiskit.transpiler.PassManager` (not only `generate_preset_pass_manager`).

## Typical approach
- Build or receive a `QuantumCircuit`, convert with `circuit_to_dag` / `dag_to_circuit` when the task requires DAG manipulation.
- Use `PassManager(passes)` or library passes consistent with **Qiskit 2.x** signatures in the prompt.

## Avoid
- `StagedPassManager.run(backend=...)` — backend belongs in preset manager construction, not `run()`.
- Inventing deprecated Qiskit 0.x transpiler APIs.

## Preset manager still valid when imported
```python
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    return pm.run(qc)
```

## Retrieval tags
DAGCircuit, PassManager, transpile, coupling map, custom pass, HumanEval transpiler advanced

## Questions this answers
- Transpile using PassManager or DAGCircuit HumanEval Qiskit 2.x
