# QHE v8：统一量子编程提示（非 HumanEval 专用 API 条文）

**版本字段：** `qhe_ablation_version = qhe_prompt_ablation_v8_unified_quantum`

## 设计原则

| 保留 | 移除 |
|------|------|
| **统一量子编程原则**（栈无关、任务/import 为准） | 长列表 **Qiskit API 细则**（`QHE_QISKIT_API_RULES*`）作为默认 QHE |
| **提交格式**（函数体、4 空格缩进） | 将 HumanEval 评测专用规则冒充「通用 QHE」 |
| **生成后 `normalize_qhe_completion`** | — |

旧模式 `qhe_contract` / `qhe_contract_short` 仍可通过 CLI 使用（含 API 规则），供历史复现。

## 四臂默认（`qhe_ablation_arms.py`）

- **QHE**（`user_qhe`）：`--user-prompt-mode qhe_unified` + normalize  
- **RAG+QHE**（`user_rag`）：`qhe_rag_soft` + 统一 QHE 文末分工（无 API 规则块）

实现：`scripts/vllm/vllm_common.py`（`QHE_UNIFIED_QUANTUM_PRINCIPLES`、`build_qhe_unified_no_rag_prompt`）、`rag_prompt_templates.py`（`QHE_RAG_ADDENDUM_UNIFIED`）。

## GPT 重跑目录

`outputs/gpt55/local_human_eval_pass1_v9_unified_qhe/` — 仅 **user_qhe** 臂（并发 6）。

**结果（GPT-5.5）：** **117/143**（与 v7/v8 短契约 + API 规则 QHE 同分）；失败 L1=5、L2=9、L3=12（API 条文移除后 L2↑、L3↓）。
