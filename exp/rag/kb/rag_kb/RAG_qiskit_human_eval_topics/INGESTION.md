# 入库说明：`RAG_qiskit_human_eval_topics`

本目录针对 **RAG 召回诊断** 中 71 道 `similarity < 0.35` 题（易被 Bell/statevector 泛化文档抢走、或完全空检索）补充 **按题型** 的检索页。

## 与代码侧改动的关系

仓库已调整默认 RAG 参数（`scripts/vllm/vllm_common.py`）：

| 参数 | 旧默认 | 新默认 |
|------|--------|--------|
| `rag_similarity_threshold` | 0.35 | **0.2** |
| `rag_page_size` | 1 | **3** |

并增强 `rag_retrieval_question_for_qhe()` 的 **Retrieval focus** 行。  
**仍需你把本目录文档入库**，否则降阈值后 top-1 仍可能是无关 Bell recipe。

## RAGFlow 步骤

1. 将 `heval_topic_*.md` 全部上传到当前 `RAGFLOW_DATASET_ID` 对应知识库（与 `RAG_qiskit_api` / `RAG_qiskit_human_eval_runtime` 同库）。
2. 分块建议：按 `##` 切分，单块 ≥ 400 字符。
3. 入库完成后在本机执行：

```bash
conda activate cyy
cd /data/Dp/qcoder/qiskit-human-eval

# 仅诊断召回（不跑 vLLM）
python scripts/vllm/diagnose_rag_recall.py \
  --dataset dataset/dataset_qiskit_test_human_eval.json

# 只重跑 RAG 臂验证 pass@1（建议新 out-dir）
python scripts/vllm/run_qhe_protocol_ablation.py \
  --out-dir outputs/qwen35/ablation_v2/protocol_user_rag_v4 \
  --only rag --only user_rag \
  --no-thinking --max-concurrent 64
```

4. 查看 `protocol_ablation_analysis.md` 中 **RAG 漏斗** 与 `diagnose_rag_recall.md` 注入率（目标：151 题中 `empty_or_short_chunk` 接近 0）。
