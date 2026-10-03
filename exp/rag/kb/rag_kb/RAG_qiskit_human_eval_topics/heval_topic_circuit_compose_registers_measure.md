# HumanEval-Qiskit Topic: compose, registers, measure_all, multi-qubit circuits

## Metadata
- Kind: `human_eval_topic_recipe`
- Topics: `QuantumCircuit`, `compose`, `QuantumRegister`, `measure_all`, `append`, `HumanEval`

## Common patterns
- `qc.compose(oracle, inplace=True)` for oracles (Deutsch–Jozsa, algorithms).
- `QuantumRegister` / `ClassicalRegister` when the function stub uses them.
- `qc.measure_all()` when tests expect standard measurement layout.

## Gate API (Qiskit 2.x)
- `qc.cx(control, target)` — not `cnot`.
- `qc.barrier()` when optimization or tests reference barriers before measure.

## Output contract
Return only indented function body; no duplicate `def`, no markdown fences.

## Retrieval tags
QuantumCircuit compose, measure_all, QuantumRegister, multi-qubit circuit, HumanEval basic circuit, append gates

## Questions this answers
- Build QuantumCircuit with compose and measure HumanEval function body
- Quantum register classical register pattern Qiskit HumanEval
