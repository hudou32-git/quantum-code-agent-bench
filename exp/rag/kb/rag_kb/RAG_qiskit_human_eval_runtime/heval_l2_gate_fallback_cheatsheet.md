# HumanEval-Qiskit: L2 门控降级与高频 API 误用（RAG 注入 / fallback）

## 基本信息
- Framework: Qiskit HumanEval (QHE)
- Version: Qiskit 2.4.1
- Kind: `human_eval_l2_cheatsheet`
- Topics: `gate_fallback`, `L2`, `runtime`, `Statevector`, `transpile`

## 用途
当 RAG 门控因 **栈关键词缺失** 或 **术语重叠不足** 跳过完整 chunk 时，管线会注入本文 **栈最小提示**（见 `vllm_common.build_rag_gate_fallback_context`）。  
ingest 后可被 RAGFlow 召回，与代码侧内置 snippet **互补**。

## Runtime Sampler / Estimator（L2）
- `Sampler(mode=backend)` / `Estimator(mode=backend)`；禁止 `Sampler(backend=...)`
- `sampler.run([circuit])` — 单线路也包在列表里
- counts：`job.result()[0].data.meas.get_counts()`
- evs：`job.result()[0].data.evs`
- transpile：`generate_preset_pass_manager(..., backend=backend)` → `pass_manager.run(qc)`

## quantum_info / Statevector（L2 栈误用）
- prompt **无** `qiskit_ibm_runtime` / `Sampler` 时：**勿**写 Sampler/Aer 采样
- Bell / 振幅题：`Statevector(qc)` 或 `Operator(qc).data`

## Fake backend + preset pass manager
- `AerSimulator.from_backend(Fake*)`
- 先 `pass_manager.run(circuit)` 再 `Sampler(mode=backend).run([isa_circuit])`

## 检索标签
- l2_fallback
- gate_degraded
- human_eval_runtime_stack
- statevector_no_sampler
