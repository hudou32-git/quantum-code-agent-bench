# HumanEval 评测：RAGFlow ingest 与降权说明

## 目的

降低 **L2**（`qiskit.primitives` vs `qiskit_ibm_runtime`）与 **L1**（整段脚本示例导致错误 import/缩进）。

## 必须入库（高优先级）

与 `op/RAG_qiskit_human_eval_runtime/MANIFEST.json`、`op/RAG_qiskit_recipes/MANIFEST.json` 一致：

- `op/RAG_qiskit_human_eval_runtime/*.md`
- `op/RAG_qiskit_human_eval_topics/*.md`
- `op/RAG_qiskit_recipes/recipe_primitives_estimator_sampler_bell.md`
- `op/RAG_qiskit_recipes/recipe_no_runtime_service_local_eval.md`

## 建议降权或排除（Sampler/Estimator 类题目）

以下 **19** 篇为官方 `qiskit.primitives` API，易与 HumanEval prompt 中的 **IBM Runtime** 冲突：

- 凡文件名以 `qiskit_primitives_` 开头（见 `HUMANEVAL_API_DOC_AUDIT.json` → `primitives_vs_runtime_sampler`）

**RAGFlow 操作（任选其一）**：

1. 单独 dataset「qiskit_api_official」，HumanEval 检索 dataset **不包含**该集合；或  
2. 文档 metadata：`human_eval_downweight: true` / `tags: [official_api, not_runtime_stack]`；或  
3. 依赖代码侧过滤：`vllm_common.sanitize_rag_context_for_human_eval`（已实现，重新 ingest 后仍生效）。

## 建议降权（legacy providers）

`legacy_providers_job` 规则中的 8 篇 `qiskit_providers_*`（非 `qiskit_ibm_runtime.fake_provider`）。

## 改 op 后

1. 重新上传变更的 `.md` 到 RAGFlow。  
2. 复跑 `rag` / `user_rag` 臂（建议 `--production-eval`）。  
3. 对比 `l0l3_classification_report.md` 中 L1/L2。
