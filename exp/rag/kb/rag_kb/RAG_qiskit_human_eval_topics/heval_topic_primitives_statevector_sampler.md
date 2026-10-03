# HumanEval-Qiskit Topic: qiskit.primitives StatevectorSampler

## Metadata
- Kind: `human_eval_topic_recipe`
- Topics: `StatevectorSampler`, `qiskit.primitives`, `Deutsch-Jozsa`, `get_counts`, `HumanEval`

## When to use
Prompt contains `from qiskit.primitives import StatevectorSampler` (or similar primitives import).  
**Do not** switch to `qiskit_ibm_runtime.Sampler` without that import line.

## Pattern
```python
    counts = StatevectorSampler().run([qc]).result()[0].data.c.get_counts()
```

## Rules
- `run([circuit])` with list wrapper.
- Classical register naming may appear as `.data.c` — follow prompt/tests.
- Do not mix runtime `mode=` Sampler docs when primitives are imported.

## Retrieval tags
StatevectorSampler, qiskit.primitives, Deutsch-Jozsa, dj_algorithm, HumanEval primitives

## Questions this answers
- Run circuit with StatevectorSampler HumanEval primitives import
