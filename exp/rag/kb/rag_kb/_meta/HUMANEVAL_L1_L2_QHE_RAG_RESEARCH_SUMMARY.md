# HumanEval-Qiskit：L1 / L2 与 QHE、RAG、QHE+RAG 分工总结

> 供后续会话接续研究。评测四臂：`baseline` | `user_qhe` | `rag` | `user_rag`（见 `scripts/vllm/qhe_ablation_arms.py`）。

## 1. 错误层级定义（本仓库用法）

| 层级 | 典型表现 | 主因（简化） |
|------|----------|----------------|
| **L0** | 无法执行 / 空输出 / 严重格式崩坏 | 推理泄漏、无 normalize、分类器边界 |
| **L1** | SyntaxError、IndentationError、NameError、重复 `def`/import、整段脚本 | **输出形态**不符合 HumanEval「只追加函数体」 |
| **L2** | Runtime API 误用（`Sampler(backend=)`、primitives 与 runtime 混用、`DataBin`/Options 读错） | **API 栈与题目 import 不一致** |
| **L3** | 断言/语义错 | 模型推理；错误 API 有时表现为 L3 |

**核心结论**：L1 主要靠 **QHE 契约 + normalize**；L2 主要靠 **知识库内容 + 检索后过滤 + Qiskit 规则**；**只有 `user_rag` 臂**同时系统化结合两者。**单独 `rag` 臂 L1 偏高是消融设计预期**，不应把函数体契约写进 standalone RAG 或 KB 来「刷分」。

---

## 2. 三种技术各自解决什么

### 2.1 QHE（`user_qhe` 臂）

**目标**：压 **L1**；顺带用 **QHE_QISKIT_API_RULES** 压一部分 **L2**（无检索时模型仍易写错 API）。

**机制**：

- 用户提示追加 `QHE_NO_RAG_PROMPT_CONTRACT`（`scripts/vllm/vllm_common.py`）：只输出 4 空格函数体、勿围栏/勿重复 `def`/import 等。
- `QHE_QISKIT_API_RULES`：runtime `mode=`、Aer、`run([circuit])`、`data.meas`、Fake 机名、Options 等（与评测栈 0.45.x 对齐）。
- **Production**：`normalize_qhe_completion()`（`vllm_common.py`）— dedent、抽围栏/`def` 体、补函数内 import、统一 4 空格缩进。
- 协议跑法：`run_qhe_protocol_ablation.py --production-eval`（或 `user_rag`-only 时自动开启）→ 生成侧 **不** 传 `--no-qhe-normalize`；评测用 `QHE_EVAL_PYTHON` / 默认 `cyy`。

**主要修改文件**：

| 文件 | 内容 |
|------|------|
| `scripts/vllm/vllm_common.py` | `QHE_NO_RAG_PROMPT_CONTRACT`、`QHE_QISKIT_API_RULES`、`normalize_qhe_completion`、`QHE_ABLATION_VERSION` |
| `scripts/vllm/run_qhe_protocol_ablation.py` | `--production-eval`、eval python 选择 |
| `qiskit-eval-v2/l0l3_classify.py` / `scripts/vllm/qhe_l0l3_classifier.py` | L0/L1 边界（如 IndentationError 归 L1） |
| `scripts/vllm/repair_l0_four_arm.py` | 历史 JSONL normalize 修复 |

**不做什么**：不改 RAGFlow 知识库；不在 standalone RAG 模板里写函数体契约。

---

### 2.2 RAG（`rag` 臂）

**目标**： primarily **L2**（召回正确 API/步骤）；**不**承担 L1 契约（消融对照）。

**机制**：

- 检索：`rag_retrieval_question()`（偏通用 QA），`fetch_rag_context` → RAGFlow（`.env` 中 `RAGFLOW_*`）。
- 提示：`build_rag_standalone_prompt` + `RAG_STANDALONE_INSTRUCTION`（`scripts/vllm/rag_prompt_templates.py`）— 中文「知识库 + 用户任务」，**无** QHE 函数体规则。
- 用户消息多为 **数据集 raw prompt**（`--user-prompt-mode raw`）。
- 生成默认 **`--no-qhe-normalize`**（消融），故 L1 通常高于 `user_qhe` / `user_rag`。

**知识库（`op/`）— L2 侧（本阶段重点）**：

| 类别 | 路径 | 作用 |
|------|------|------|
| Runtime 叙事 | `op/RAG_qiskit_human_eval_runtime/*.md` | `mode=`、transpile、sampler 读 counts 等 |
| 题类 topic | `op/RAG_qiskit_human_eval_topics/` | 低相似度题检索补强 |
| Recipe | `op/RAG_qiskit_recipes/` | 多步流程 |
| 官方 API 页 | `op/RAG_qiskit_api/`（~518） | 泛 API；Sampler 题易误导 |
|  ingest 说明 | `op/RAG_qiskit_api/HUMANEVAL_RAG_INGEST_NOTE.md` | primitives 降权策略 |

**入库与对齐工具**：

| 文件 | 作用 |
|------|------|
| `op/rag_kb_sync.py` | `diff` / `sync` / `download` / `retire-deprecated` |
| `op/rag_txt.ipynb` | 手工上传试验 |
| `op/RAG_qiskit_human_eval_runtime/MANIFEST.json` | 正式列表 + `deprecated_merge_before_reingest` |

**已做 KB 运维**：删除 5 对 deprecated runtime 双份（op + RAGFlow）；`sync` 按 SHA256 更新变更文件；L2 样例文排版（正确用法前置、禁止表后置）。

**RAG 管线里与 QHE 无关的部分（仍属 RAG 臂）**：

- `sanitize_rag_context_for_human_eval()`：丢 `qiskit_primitives_*`、legacy providers、MANIFEST 等 chunk（**L2**）。
- `_HUMANEVAL_RAG_CONTEXT_PREAMBLE`：短栈说明（runtime vs primitives）。
- `evaluate_rag_gate` / `rag_retrieval_question_for_qhe`：仅 **QHE 检索查询**用；**`rag` 臂**用通用 query。

---

### 2.3 QHE + RAG（`user_rag` 臂）— 一体化

**目标**：**同时压 L1 与 L2**（生产配置看此臂，版本 **`qhe_prompt_ablation_v5_rag_qhe_unified`**）。

**机制（流水线）**：

```text
题目 prompt
  → rag_retrieval_question_for_qhe(prompt)     # 检索 query 带 import/任务 hint（L2 召回）
  → RAGFlow 召回 chunk
  → extract_rag_context_content
  → sanitize_rag_context_for_qhe(cleaned, prompt)   # L2 过滤 + L1 脱敏（见下）
  → build_rag_plus_qhe_prompt:
        RAG_QHE_INSTRUCTION + 检索块 + 【用户任务】
        + QHE_RAG_ADDENDUM（RAG/QHE 分工 + import_anchor + QHE_QISKIT_API_RULES）
  → vLLM 生成
  → normalize_qhe_completion（production-eval）
  → evaluate_completions（cyy）
```

**相对「纯 RAG」多出来的 QHE 优化（重要：RAG 不只 KB）**：

| 组件 | 文件 | L1 / L2 |
|------|------|---------|
| `RAG_QHE_INSTRUCTION` | `rag_prompt_templates.py` | 明确检索只供 API，禁止照抄 `def`/整段脚本 |
| `QHE_RAG_ADDENDUM` | 同上 | 契约 + RAG/QHE 分工 + 禁止表勿写进代码 |
| `build_qhe_rag_import_anchor(prompt)` | `vllm_common.py` | 勿重复题目 import |
| `sanitize_rag_context_for_qhe` | `vllm_common.py` | 在 `sanitize_rag_context_for_human_eval` 上去 `def` 行、围栏、MANIFEST chunk |
| `build_rag_plus_qhe_prompt` | `rag_prompt_templates.py` | 组装 standalone 模板 + QHE 追加段 |
| `user_prompt_mode=qhe_contract` | `qhe_ablation_arms.py` | 与 `user_qhe` 同契约族 |
| `--production-eval` | `run_qhe_protocol_ablation.py` | `user_rag`-only 自动开启 normalize |

**共享（`rag` 与 `user_rag` 检索路径均可触及，但 `user_rag` 用 QHE 专用 sanitize）**：

- `sanitize_rag_context_for_human_eval` / chunk drop keywords
- KB 内容与 `op/rag_kb_sync.py` 同步状态

---

## 3. 修改清单速查（按路径）

### `op/`（知识库 + 运维，主攻 L2）

- 内容：`heval_runtime_sampler_estimator.md`、recipes、topics、`HUMANEVAL_RAG_INGEST_NOTE.md` 等。
- 策略：`RAG_KB_CONTENT_SCOPE.md`、`KB_HUMANEVAL_RISK_INVENTORY.md`。
- 工具：`rag_kb_sync.py`、`rag_txt.ipynb`；导出 `ragflow_export/`（gitignore）。
- 研究总结：本文档。

### `scripts/vllm/`（生成与消融，L1 + 检索管线）

- `vllm_common.py` — QHE 规则、normalize、RAG fetch/sanitize/gate、QHE 检索 query。
- `rag_prompt_templates.py` — standalone vs QHE+RAG 模板。
- `qhe_ablation_arms.py` — 四臂 flags。
- `run_qhe_protocol_ablation.py` — 生成/评测/分类报告。
- `repair_l0_four_arm.py`、`qhe_l0l3_classifier.py` — 后处理与指标。

### 评测与分类

- `scripts/evaluate_completions.py` + `QHE_EVAL_PYTHON` / env `cyy`。
- `qiskit-eval-v2/l0l3_classify.py`（l0l3-v3.1 等）。

---

## 4. 实验与指标应如何读

| 对比目的 | 应看臂 | 配置 |
|----------|--------|------|
| KB / 检索是否改善 API | `rag` vs `baseline` | 默认 ablation（无 normalize）→ L1 偏高正常 |
| QHE 契约是否改善格式 | `user_qhe` vs `baseline` | 建议 `--production-eval` |
| **KB + 契约联合** | **`user_rag` vs `user_qhe`** | **`--production-eval`**（v5）；看 L1↓ L2↓ |
| 仅 KB 更新是否有效 | 勿只用 `rag` 判 L1 | 看 `user_rag` L2 与 `chunk` 元数据 |

典型输出目录：`outputs/*/local_human_eval_pass1/`、`l0l3_classified_*.jsonl`、`qhe_ablation_version` 字段。

---

## 5. 后续研究建议（另一会话可直接接着做）

1. **跑 v5 对比**：同一数据集 144/151，`user_qhe` vs `user_rag`，`--production-eval`，对比 `l0l3_classification_report` 与 `vllm_user_rag.jsonl` 中 `rag_used` / skip reason。
2. **检索诊断**：`scripts/vllm/diagnose_rag_recall.py`（注入率、相似度阈值 `rag_similarity_threshold`）。
3. **KB 迭代**：改 `op/` → `python op/rag_kb_sync.py sync`；deprecated → `retire-deprecated`。
4. **勿混淆**：standalone `RAG_STANDALONE_INSTRUCTION` 与 `RAG_QHE_INSTRUCTION` 用途不同；不要把 L1 契约塞进 KB 正文。
5. **版本字段**：JSONL / timing 里 `qhe_ablation_version`：`v4_production` → **`v5_rag_qhe_unified`** 区分 RAG+QHE 一体化前后。

---

## 6. 一句话对照

| 技术 | L1 | L2 | 改动的本质 |
|------|----|----|------------|
| **QHE** | 主战场 | 规则辅助 | 提示契约 + normalize + 评测 Python |
| **RAG** | 不主打（消融无契约） | 主战场 | **`op/` 知识库** + ingest/sync + 检索门控与 **通用** chunk 过滤 |
| **QHE+RAG** | QHE 契约 + 检索脱敏 + normalize | KB + **QHE 检索 query** + **双 sanitize** + 同一套 Qiskit 规则 | **提示与检索管线**与 KB **并列**，不是「RAG = 只改库」 |
