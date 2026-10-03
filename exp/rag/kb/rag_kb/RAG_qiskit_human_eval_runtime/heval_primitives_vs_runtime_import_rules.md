# HumanEval-Qiskit: qiskit.primitives vs qiskit_ibm_runtime (import alignment)

## Metadata
- Topics: `qiskit.primitives`, `StatevectorSampler`, `qiskit_ibm_runtime`, `import_rules`, `do_not_mix`

## Golden rule
**Match the prompt import block exactly.** The benchmark prepends imports; your function body must not contradict them.

## If prompt has `from qiskit_ibm_runtime import Sampler`
- Use `Sampler(mode=AerSimulator())` or `mode=simulator` as required.
- Do **not** switch to `from qiskit.primitives import Sampler` or `BackendSamplerV2`.
- Ignore retrieved docs that only show `qiskit.primitives.backend_sampler_v2` unless you also change imports (you must not).

## If prompt has `from qiskit.primitives import StatevectorSampler`
- Use `StatevectorSampler().run([qc]).result()[0].data...` per that API.
- Do **not** inject `qiskit_ibm_runtime.Sampler` without the import line.

## If prompt has both runtime and primitives (rare)
Follow the **function docstring** and which class name appears in the signature context; do not add extra imports.

## RAG retrieval caution
Official API pages titled `qiskit_primitives_*` describe a **different stack** from HumanEval runtime tasks. When `<rag_context>` shows primitives examples but `<problem>` imports `qiskit_ibm_runtime`, **follow the problem imports**.

## Statevector / Operator / quantum_info tasks
When prompt imports `Statevector`, `Operator`, `SparsePauliOp` from `qiskit.quantum_info`, use those — not runtime primitives.

## Retrieval tags
primitives_vs_runtime, StatevectorSampler, qiskit_ibm_runtime, import alignment, HumanEval, exact API

## Questions this answers
- Should I use qiskit.primitives or qiskit_ibm_runtime Sampler for this HumanEval task?
- Retrieved context shows BackendSamplerV2 but prompt imports Sampler from runtime
- StatevectorSampler run list HumanEval Deutsch-Jozsa
