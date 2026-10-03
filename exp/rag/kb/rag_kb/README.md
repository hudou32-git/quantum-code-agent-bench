# Oracle RAG 知识库

本目录是 **RAGFlow 知识库的本地副本**，并补充了量子算法语义页，供 Oracle 的 RAG 实验臂检索。

## 来源

| 路径 | 说明 |
|------|------|
| `qiskit-human-eval/op/RAG_qiskit_api/` | Qiskit API 文档切片（RAGFlow 主库） |
| `.../RAG_qiskit_recipes/` | 题类配方（Sampler/Estimator/Bell 等） |
| `.../RAG_qiskit_human_eval_runtime/` | Runtime / primitives / transpile 对照 |
| `.../RAG_qiskit_human_eval_topics/` | HumanEval 主题聚合页 |
| **`RAG_quantum_algorithms/`（新增）** | GHZ/Bell/W/QFT/BV/相位 oracle/endian/ancilla 等算法语义 |

重新构建：

```bash
python Oracle/oracle_mvp/scripts/setup_rag_kb.py
```

## 文件统计

| 子库 | 文件数 |
|------|-------:|
| RAG_qiskit_api | 520 |
| RAG_qiskit_recipes | 10 |
| RAG_qiskit_human_eval_runtime | 13 |
| RAG_qiskit_human_eval_topics | 9 |
| RAG_quantum_algorithms | 9 |
| **合计** | **561** |

## 分层说明（与 op 原设计一致）

- **L1（语法/缩进/输出形态）**：不靠知识库解决；由评测契约 / normalize 处理。
- **L2（API/Runtime 用错）**：主要靠 `RAG_qiskit_*` 检索纠正。
- **L3（相位/相干/oracle 语义）**：靠 `RAG_quantum_algorithms` + 模型推理；KB 只给模式与易错点，不给标准答案电路抄写。

## 本地检索

```python
from oracle_mvp.rag import LocalKbRetriever
r = LocalKbRetriever()
hits = r.retrieve("prepare 3-qubit GHZ with CNOT fanout", top_k=4)
```

无需启动 RAGFlow 也可本地检索。若要与线上 RAGFlow 对齐：

```bash
python oracle_mvp/scripts/sync_ragflow_kb.py diff
python oracle_mvp/scripts/sync_ragflow_kb.py sync --dry-run
python oracle_mvp/scripts/sync_ragflow_kb.py sync                 # 全库 upload+parse
python oracle_mvp/scripts/sync_ragflow_kb.py sync --tier quantum  # 仅算法补充页
```

凭证：仓库根 `.env` 的 `RAGFLOW_*`。

## 与实验臂的关系

见 `oracle_mvp/scripts/run_method_ablation.py`：

- **baseline**：无检索
- **rag**：本库 top-k 片段注入 prompt（线上召回需先 sync RAGFlow）
- **iterative / cot**：默认不读库（消融隔离）；可用 CLI 组合
