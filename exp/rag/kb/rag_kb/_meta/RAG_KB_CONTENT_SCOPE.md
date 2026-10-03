# `op/` 知识库调整范围说明（L1 vs L2）

## 结论（与你当前关注点一致）

| 层级 | 是否靠改 `op/` 知识库解决 | 应由谁解决 |
|------|---------------------------|------------|
| **L1**（Syntax / Indent / NameError、整段 `def`、缩进） | **否** | **QHE + RAG（`user_rag` 臂）**：`QHE_RAG_ADDENDUM` + `QHE_QISKIT_API_RULES` + 生成/评测侧 `normalize_qhe_completion`（`--production-eval`）。知识库只提供 **API 事实**，不负责 **输出形态**。 |
| **L2**（Runtime API、Options、`DataBin`、primitives 混用） | **是** | **`op/` 内容 + ingest 策略**：runtime 对照页、recipe 栈对齐、primitives 降权/过滤。 |
| **L3** | 部分 | 语义/断言；KB 可减少错误 API 导致的假 L3，主因仍是模型推理。 |

因此：**单独 `+RAG` 臂**的 L1 高，是消融设计（无 QHE 契约）下的预期现象，**不应**通过把 HumanEval 函数体契约写进 standalone RAG 提示或 KB 来「冒充 RAG 能力」。评测上应看 **`user_rag` + `--production-eval`**（`qhe_prompt_ablation_v5_rag_qhe_unified`）的 L1/L2。

---

## `op/` 仅针对 L2 的调整原则

1. **正文先写「当前评测栈正确用法」**（`qiskit_ibm_runtime` 0.45.x + `mode=` + `data.meas`），**禁止/旧 API 表放在文末**，并标明「勿照抄」。
2. **减少栈混淆**：`qiskit_primitives_*` 官方页不删，但在 ingest 或检索后过滤中 **降权/丢弃**（见 `HUMANEVAL_RAG_INGEST_NOTE.md`）。
3. **补全 API 栈缺口**：`RAG_qiskit_human_eval_runtime/`、`topics/`、`recipe_primitives_estimator_sampler_bell.md` 等，避免 Sampler 题回落到 518 篇泛 API 页。
4. **Recipe 不写「输出格式」**：recipe 只写 **用什么 API、什么步骤**；不写「4 空格函数体」（那是 QHE 契约）。  
   - `recipe_statevector_quantum_info_bell.md` 中的说明是 **栈选择**（无 Sampler import 时不要走采样流程），属于 **L2/题类**，不是 L1 格式契约。

---

## 已改 / 建议改的 `op/` 文件（L2）

| 文件 | 改动意图 |
|------|----------|
| `RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md` | 标准流程与函数体**示例**前置；旧 API 对照表后置。 |
| `RAG_qiskit_api/HUMANEVAL_RAG_INGEST_NOTE.md` | primitives / legacy providers ingest 降权说明。 |
| `RAG_qiskit_recipes/recipe_statevector_quantum_info_bell.md` | 题类栈：无 Runtime import 时不套 Sampler 流程。 |
| `KB_HUMANEVAL_RISK_INVENTORY.md` | 风险清单与实证 chunk（审计用）。 |

**建议继续改（L2，未全部落地）**：

- `heval_runtime_results_sampler_options.md`：置顶 V2 `SamplerOptions` / `data.meas` 读取模板。  
- `heval_primitives_vs_runtime_import_rules.md`：与 QHE 规则同文的短对照（供 **user_rag** 检索）。  
- 合并重复 runtime 文：`heval_runtime_sampler_estimator.md` vs `_mode.md`，避免 chunk 分裂。  
- 对 `recipe_primitives_estimator_sampler_bell.md`：禁止表后置（与 runtime 文同一排版规范）。

---

## `user_rag` 与 KB 的分工

```text
检索 (op/)     → 提供正确 API 片段、步骤、机名、Options 字段
sanitize_qhe   → 丢 primitives/MANIFEST chunk；去掉检索内 def/围栏（L1）
RAG_QHE_INSTRUCTION + QHE_RAG_ADDENDUM → 检索只供 L2，契约压 L1
import_anchor  → 勿重复题目 import
QHE_QISKIT_API_RULES → 与 KB 一致时压 L2
normalize      → 生成侧统一函数体（production-eval，压 L1）
```

改 KB 后请 **重新 ingest RAGFlow**，并在 **`user_rag` + `--production-eval`** 上对比 L1/L2，不要仅用 standalone `rag` 臂判断 KB 是否有效。

---

## 不再作为 KB 目标的项（L1）

- 不在 `RAG_STANDALONE_INSTRUCTION` 或通用 recipe 里写 HumanEval 函数体契约。  
- 不把「4 空格缩进」「勿输出 def」放进 `op/` 正文（避免与 QHE 重复且 standalone RAG 消融失真）。  
- L1 对比基线：优化前后 **`user_rag`** 的 `l0l3_classified_user_rag.jsonl`，而非 `rag` 臂。

详细历史方案见 `RAG_L1_L2_MODIFICATION_PLAN.md`（其中 L1 管线部分以本文为准作废止/归档）。
