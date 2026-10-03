# RAG 入库：`RAG_qiskit_human_eval_runtime`

本目录为 **Qiskit HumanEval 评测栈** 专用检索文档，与 `op/RAG_qiskit_api`（单 API 页）和 `op/RAG_qiskit_recipes`（通用 recipe）互补。

## 为何单独建目录

- 评测环境使用 **`qiskit_ibm_runtime.Sampler` / `Estimator` + `mode=` + `qiskit_aer.AerSimulator`**，以及 **`qiskit_ibm_runtime.fake_provider` 具体机名**。
- `RAG_qiskit_api` 中大量 `qiskit.primitives.*` 页面在检索 Sampler 题时易误导模型；本目录页面在标题与检索标签中强调 **runtime 与 primitives 分流**。

## RAGFlow 建议步骤

1. 将本目录下全部 `heval_*.md` 上传到与现有 Qiskit 文档 **同一 dataset**（或新建 dataset 后合并检索配置）。
2. 分块：按 `##` 标题切分，单块建议 **≥ 400 字符**（避免清洗后低于 80 字符导致 `empty_or_short_chunk`）。
3. 入库后抽查：用题目 docstring + imports 做检索，应能命中 `heval_runtime_sampler_estimator_mode.md` 或 fake/transpile 对应页。
4. 重新跑消融的 RAG 臂验证 `chunk_recalled_tasks` 与 pass@1。

机器可读清单：`MANIFEST.json`。
