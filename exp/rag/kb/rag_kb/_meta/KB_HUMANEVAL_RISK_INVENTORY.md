# HumanEval 知识库风险与 L1/L2 关联清单（`op/`）

生成依据：`op/RAG_qiskit_api/HUMANEVAL_API_DOC_AUDIT.json` 静态审计 + 四臂评测 `l0l3_classified_*` 与 `vllm_rag.jsonl` / `vllm_user_rag.jsonl` 检索元数据。

## 一、静态审计：易导致写错 API 的 `op/RAG_qiskit_api` 文档

| 规则 ID | 说明 | 文件数 | 相对路径（均在 `op/RAG_qiskit_api/` 下） |
|---------|------|--------|------------------------------------------|
| `legacy_providers_job` | qiskit.providers JobV1 / basic_provider 路径 | 8 | `qiskit_providers_basic_provider_basic_provider_Backend.md`, `qiskit_providers_basic_provider_basic_provider_job_JobV1.md`, `qiskit_providers_basic_provider_basic_simulator_BackendV2.md`, `qiskit_providers_basic_provider_basic_simulator_Clifford.md`, `qiskit_providers_basic_provider_basic_simulator_Options.md` … 共 8 篇 |
| `primitives_vs_runtime_sampler` | qiskit.primitives 与 HumanEval 的 runtime Sampler 不一致 | 19 | `qiskit_primitives_backend_estimator_v2_BackendV2.md`, `qiskit_primitives_backend_estimator_v2_Options.md`, `qiskit_primitives_backend_estimator_v2_PassManager.md`, `qiskit_primitives_backend_estimator_v2_Pauli.md`, `qiskit_primitives_backend_estimator_v2_PauliList.md` … 共 19 篇 |

### 1.1 `primitives_vs_runtime_sampler` 完整 19 篇（建议检索降权或加脚注）

- `op/RAG_qiskit_api/qiskit_primitives_backend_estimator_v2_BackendV2.md`
- `op/RAG_qiskit_api/qiskit_primitives_backend_estimator_v2_Options.md`
- `op/RAG_qiskit_api/qiskit_primitives_backend_estimator_v2_PassManager.md`
- `op/RAG_qiskit_api/qiskit_primitives_backend_estimator_v2_Pauli.md`
- `op/RAG_qiskit_api/qiskit_primitives_backend_estimator_v2_PauliList.md`
- `op/RAG_qiskit_api/qiskit_primitives_backend_sampler_v2_BackendV2.md`
- `op/RAG_qiskit_api/qiskit_primitives_backend_sampler_v2_Options.md`
- `op/RAG_qiskit_api/qiskit_primitives_base_base_estimator_Job.md`
- `op/RAG_qiskit_api/qiskit_primitives_base_base_estimator_Job_status.md`
- `op/RAG_qiskit_api/qiskit_primitives_base_base_estimator_SparsePauliOp.md`
- `op/RAG_qiskit_api/qiskit_primitives_base_base_primitive_v1_Options.md`
- `op/RAG_qiskit_api/qiskit_primitives_base_base_sampler_Job.md`
- `op/RAG_qiskit_api/qiskit_primitives_base_validation_v1_PauliList.md`
- `op/RAG_qiskit_api/qiskit_primitives_base_validation_v1_SparsePauliOp.md`
- `op/RAG_qiskit_api/qiskit_primitives_containers_bindings_array_Parameter.md`
- `op/RAG_qiskit_api/qiskit_primitives_containers_observables_array_Pauli.md`
- `op/RAG_qiskit_api/qiskit_primitives_containers_observables_array_PauliList.md`
- `op/RAG_qiskit_api/qiskit_primitives_containers_observables_array_SparsePauliOp.md`
- `op/RAG_qiskit_api/qiskit_primitives_statevector_estimator_SparsePauliOp.md`

### 1.2 `legacy_providers_job` 完整 8 篇

- `op/RAG_qiskit_api/qiskit_providers_basic_provider_basic_provider_Backend.md`
- `op/RAG_qiskit_api/qiskit_providers_basic_provider_basic_provider_job_JobV1.md`
- `op/RAG_qiskit_api/qiskit_providers_basic_provider_basic_simulator_BackendV2.md`
- `op/RAG_qiskit_api/qiskit_providers_basic_provider_basic_simulator_Clifford.md`
- `op/RAG_qiskit_api/qiskit_providers_basic_provider_basic_simulator_Options.md`
- `op/RAG_qiskit_api/qiskit_providers_basic_provider_basic_simulator_StabilizerState.md`
- `op/RAG_qiskit_api/qiskit_providers_basic_provider_basic_simulator_Target.md`
- `op/RAG_qiskit_api/qiskit_providers_job_JobV1.md`

## 二、`op/` 非 API 库：含「反例/旧 API」字样（模型易照抄禁止列）

| 文件 | 风险类型 | 说明 |
|------|----------|------|
| `op/RAG_qiskit_recipes/recipe_primitives_estimator_sampler_bell.md` | 对照页 | 含禁止构造对照；召回 Sampler 题时必要，但表格行含错误写法 |
| `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md` | 对照页 | L1/L2 失败检索最高频；禁止列表含 `Sampler(backend=)` 等 |
| `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator_mode.md` | 重复 | 与上篇主题重复，可能分流正确 chunk |
| `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile.md` | 反例提及 | 列举 FakeProvider 错误名 |
| `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile_pass_manager.md` | 反例提及 | 同上 |
| `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_patterns.md` | 旧 API | 提及 `.c_if` 已移除 |
| `op/RAG_qiskit_recipes/recipe_fake_provider_machine_names.md` | 反例提及 | 列举 FakeProvider |

## 三、实证：RAG 臂 L1/L2 失败时检索到的 chunk（按命中失败次数排序）

| 命中次数 | 知识库路径 | 关联失败题数 |
|----------|------------|--------------|
| 37 | `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md` | 13 |
| 21 | `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_patterns.md` | 16 |
| 11 | `op/RAG_qiskit_recipes/recipe_quantum_circuit_compose_measure_patterns.md` | 8 |
| 11 | `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile.md` | 7 |
| 8 | `op/RAG_qiskit_api/qiskit_circuit_quantumcircuit_QuantumCircuit_cx.md` | 5 |
| 7 | `op/RAG_qiskit_recipes/recipe_statevector_quantum_info_bell.md` | 6 |
| 6 | `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile_pass_manager.md` | 4 |
| 6 | `op/RAG_qiskit_human_eval_topics/heval_topic_runtime_sampler_transpile_measure.md` | 3 |
| 5 | `op/RAG_qiskit_recipes/recipe_transpile_preset_pass_manager.md` | 3 |
| 3 | `op/RAG_qiskit_human_eval_topics/heval_topic_dag_passmanager_transpiler.md` | 2 |
| 3 | `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_qiskit2_api.md` | 2 |
| 3 | `op/RAG_qiskit_recipes/recipe_aer_bell_phi_plus_simulation.md` | 3 |
| 3 | `op/RAG_qiskit_recipes/recipe_qasm2_export_import.md` | 3 |
| 3 | `op/RAG_qiskit_api/qiskit_circuit_quantumcircuit_QuantumCircuit_measure.md` | 2 |
| 2 | `op/RAG_qiskit_recipes/recipe_circuit_library_efficient_su2.md` | 1 |
| 2 | `op/RAG_qiskit_api/qiskit_quantum_info_PauliList_group_commuting.md` | 1 |
| 2 | `op/RAG_qiskit_api/qiskit_circuit_library_n_local_evolved_operator_ansatz_SparsePauliOp_group_commuting.md` | 1 |
| 2 | `op/RAG_qiskit_api/qiskit_quantum_info_concurrence.md` | 2 |
| 2 | `op/RAG_qiskit_api/qiskit_quantum_info_states_concurrence.md` | 2 |
| 1 | `op/RAG_qiskit_api/qiskit_circuit_library_data_preparation_pauli_feature_map_Parameter.md` | 1 |
| 1 | `op/RAG_qiskit_api/qiskit_quantum_info_operators_symplectic_random_Clifford.md` | 1 |
| 1 | `op/RAG_qiskit_api/qiskit_quantum_info_mutual_information.md` | 1 |
| 1 | `op/RAG_qiskit_api/qiskit_quantum_info_states_mutual_information.md` | 1 |
| 1 | `op/RAG_qiskit_api/qiskit_quantum_info_states_partial_trace.md` | 1 |
| 1 | `op/RAG_qiskit_api/qiskit_transpiler_passes_routing_commuting_2q_gate_routing_swap_strategy_CouplingMap.md` | 1 |

### 3.1 典型 task → chunk 示例（L2）

- **qiskitHumanEval/106** (rag): `AttributeError(API属性不存在: type object 'CNOTDihedral' has no a` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_patterns.md`*, `op/RAG_qiskit_api/qiskit_circuit_quantumcircuit_QuantumCircuit_cx.md`*
- **qiskitHumanEval/122** (rag): `TypeError(API参数签名变更)` → chunks: `op/RAG_qiskit_recipes/recipe_circuit_library_efficient_su2.md`*, `op/RAG_qiskit_recipes/recipe_transpile_preset_pass_manager.md`*
- **qiskitHumanEval/128** (rag): `TypeError(API参数数量变更)` → chunks: `op/RAG_qiskit_recipes/recipe_quantum_circuit_compose_measure_patterns.md`*, `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_qiskit2_api.md`*
- **qiskitHumanEval/131** (rag): `AttributeError(API属性不存在: module 'qiskit_ibm_runtime.fake_pro` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile.md`*, `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile_pass_manager.md`*
- **qiskitHumanEval/132** (rag): `TypeError(API参数签名变更)` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*, `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile_pass_manager.md`*
- **qiskitHumanEval/139** (rag): `TypeError(API参数数量变更)` → chunks: `op/RAG_qiskit_recipes/recipe_statevector_quantum_info_bell.md`*, `op/RAG_qiskit_api/qiskit_quantum_info_states_partial_trace.md`*
- **qiskitHumanEval/148** (rag): `AttributeError(API属性不存在: 'qiskit._accelerate.circuit.DAGCirc` → chunks: `op/RAG_qiskit_api/qiskit_transpiler_passes_routing_commuting_2q_gate_routing_swap_strategy_CouplingMap.md`*, `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_patterns.md`*
- **qiskitHumanEval/149** (rag): `AttributeError(API属性不存在: 'BitArray' object has no attribute ` → chunks: `op/RAG_qiskit_recipes/recipe_aer_bell_phi_plus_simulation.md`*, `op/RAG_qiskit_recipes/recipe_qasm2_export_import.md`*
- **qiskitHumanEval/33** (rag): `ValidationError(API配置参数变更)` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*, `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*
- **qiskitHumanEval/34** (rag): `AttributeError(API属性不存在: 'Batch' object has no attribute 'ba` → chunks: `op/RAG_qiskit_human_eval_topics/heval_topic_runtime_sampler_transpile_measure.md`*, `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile.md`*
- **qiskitHumanEval/35** (rag): `ValueError(API参数值错误)` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*, `op/RAG_qiskit_human_eval_runtime/heval_fake_provider_transpile.md`*
- **qiskitHumanEval/37** (rag): `AttributeError(API属性不存在: 'DataBin' object has no attribute '` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*, `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*
- **qiskitHumanEval/40** (rag): `ValidationError(API配置参数变更)` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*, `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator_mode.md`*
- **qiskitHumanEval/51** (rag): `AttributeError(API属性不存在: 'DataBin' object has no attribute '` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_patterns.md`*, `op/RAG_qiskit_human_eval_runtime/heval_quantum_circuit_qiskit2_api.md`*
- **qiskitHumanEval/54** (rag): `AttributeError(API属性不存在: 'DataBin' object has no attribute '` → chunks: `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*, `op/RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md`*

## 四、整库缺口（审计结论，非单文件错误）

- `op/RAG_qiskit_api` **不含** `qiskit_ibm_runtime` / `qiskit_aer` / `fake_provider` 官方 API 页，依赖 `op/RAG_qiskit_human_eval_runtime/` 与 recipes 补栈。
- 若 RAGFlow 未 ingest `RAG_qiskit_human_eval_runtime` 或 `RAG_qiskit_human_eval_topics`，检索会回落到 **518 篇 API 页**，L2 中 `qiskit.primitives` / `DataBin` 类错误会上升。

## 五、L1 / L2 解决方法（工程侧）

### L1（Python 语法层）

1. **生成后处理**：评测前对四臂统一 `normalize_qhe_completion`（dedent + 4 空格 + 抽 `def` 体）。
2. **提示词**：+RAG standalone 增加一句「只输出缩进函数体」；QHE 契约已覆盖 user_qhe / user_rag。
3. **检索**：Statevector/Operator 题提高 `heval_topic_quantum_info_operator_statevector.md` 权重，降低无关 `recipe_statevector_quantum_info_bell.md` 整段 Sampler 示例干扰。
4. **对照页改写**：将 `heval_runtime_sampler_estimator.md` 等文档的「禁止」列改为独立 `## 常见错误（勿使用）` 并加粗，减少模型抄错列。
5. **max_tokens / no-thinking**：避免推理占满 token 导致截断 SyntaxError。

### L2（API 兼容层）

1. **ingest 顺序**：RAGFlow 必含 `op/RAG_qiskit_human_eval_runtime/` 全部 + `recipe_primitives_estimator_sampler_bell.md` + `heval_primitives_vs_runtime_import_rules.md`。
2. **检索降权**：对 `op/RAG_qiskit_api/qiskit_primitives_*` 19 篇在 Sampler/Estimator 题上 metadata 降权或 exclude。
3. **QHE 规则与 KB 对齐**：`scripts/vllm/vllm_common.py` 中 `QHE_QISKIT_API_RULES` 与 `requirements.txt`（runtime 0.45.x）同步；Options 字段以 `heval_runtime_results_sampler_options.md` 为准。
4. **检索后过滤**：`extract_rag_context_content` 后若 chunk 含 `Sampler(backend=` 且无 `禁止` 上下文，strip 或替换为 mode= 片段。
5. **评测环境**：锁定 `cyy` 环境与数据集 canonical_solution 同版本；L2 中 ValidationError 多为 Options 字段名与 pydantic 模型不一致。
6. **DataBin.meas**：在 `heval_runtime_results_sampler_options.md` 置顶 V2 结果读取模板，减少 `PrimitiveResult` 误用。

