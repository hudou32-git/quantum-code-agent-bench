# RAG_qiskit_api × HumanEval 本地评测：文档核对清单

对照此前 Q2/RAG 结论（`q2_api_misuse_catalog.md`、`rag_chunk_audit.md`），在 **`op/RAG_qiskit_api`**（共 **518** 个 `.md`）中扫描「易导致 HumanEval 写错」的模式。说明：该目录页眉为 **Qiskit 2.4.1 官方 API 摘录**，多数**不是**已删除 API，而是与 **HumanEval prompt 规定的 `qiskit_ibm_runtime` + `mode=` + fake 机名** 不一致或缺失。

## 结论摘要

| 类型 | 说明 | 建议你是否改文档 |
|------|------|------------------|
| **A. 字面过时模式** | FakeProvider、`execute`、`quasi_dists` 等 | 本库 **几乎零命中** → **不必逐页改** |
| **B. Primitives 族（19 篇）** | 官方 `qiskit.primitives.*`，无 `mode=` 叙事 | **建议处理**：增补 runtime 对照页或检索降权 |
| **C. Legacy providers（9 篇）** | `JobV1`、`basic_provider` | **可选**：加 HumanEval 脚注，非必须改正文 |
| **D. 栈缺口** | 全库无 `qiskit_ibm_runtime` / `qiskit_aer` / `fake_provider` 文档 | **建议新增**（比改 500 页 API 更高效） |
| **E. PassManager.run（1 篇）** | 签名正确，无 `backend=` 参数 | **无需改**；可优先于错误 recipe 被召回 |

## 全库缺失的 HumanEval 关键栈（整目录搜索）


## 按风险规则命中的文件（供勾选是否更新）

### 0.x 风格 import/执行（HumanEval 会判错） (`legacy_execute_aer_ibm`)

- **命中文件数**：0
- **默认建议**：若命中则删改示例；当前库内多为零命中

  - （无）

### FakeBackendV2 / FakeProvider 泛化名 (`fake_provider_generic`)

- **命中文件数**：1
- **默认建议**：改为 FakeBelemV2 等具体机名说明

  - `HUMANEVAL_API_DOC_AUDIT.md`

### QiskitRuntimeService / 真机账号 (`runtime_service_cloud`)

- **命中文件数**：1
- **默认建议**：本地评测集应标注「仅云端」或勿入库

  - `HUMANEVAL_API_DOC_AUDIT.md`

### qiskit.primitives 与 HumanEval 的 runtime Sampler 不一致 (`primitives_vs_runtime_sampler`)

- **命中文件数**：20
- **默认建议**：保留为官方 API，但检索到 Sampler 题时易误导；建议增补 runtime 对照页或降权

  - `HUMANEVAL_API_DOC_AUDIT.md`
  - `qiskit_primitives_backend_estimator_v2_BackendV2.md`
  - `qiskit_primitives_backend_estimator_v2_Options.md`
  - `qiskit_primitives_backend_estimator_v2_PassManager.md`
  - `qiskit_primitives_backend_estimator_v2_Pauli.md`
  - `qiskit_primitives_backend_estimator_v2_PauliList.md`
  - `qiskit_primitives_backend_sampler_v2_BackendV2.md`
  - `qiskit_primitives_backend_sampler_v2_Options.md`
  - `qiskit_primitives_base_base_estimator_Job.md`
  - `qiskit_primitives_base_base_estimator_Job_status.md`
  - `qiskit_primitives_base_base_estimator_SparsePauliOp.md`
  - `qiskit_primitives_base_base_primitive_v1_Options.md`
  - `qiskit_primitives_base_base_sampler_Job.md`
  - `qiskit_primitives_base_validation_v1_PauliList.md`
  - `qiskit_primitives_base_validation_v1_SparsePauliOp.md`
  - `qiskit_primitives_containers_bindings_array_Parameter.md`
  - `qiskit_primitives_containers_observables_array_Pauli.md`
  - `qiskit_primitives_containers_observables_array_PauliList.md`
  - `qiskit_primitives_containers_observables_array_SparsePauliOp.md`
  - `qiskit_primitives_statevector_estimator_SparsePauliOp.md`

### Sampler(backend=/simulator= 构造（非 mode=） (`sampler_wrong_ctor`)

- **命中文件数**：1
- **默认建议**：改为 Sampler(mode=...) + SamplerOptions

  - `HUMANEVAL_API_DOC_AUDIT.md`

### quasi_dists / 旧 Primitive 结果字段 (`primitive_result_legacy`)

- **命中文件数**：1
- **默认建议**：改为 result[i].data.meas.get_counts() 等

  - `HUMANEVAL_API_DOC_AUDIT.md`

### sampler.run(circuit) 未包列表 (`run_without_list`)

- **命中文件数**：0
- **默认建议**：改为 run([circuit])

  - （无）

### 错误符号名（QFT / QFT 旧名等） (`wrong_import_symbols`)

- **命中文件数**：0
- **默认建议**：与 dataset import 对齐

  - （无）

### qiskit.providers JobV1 / basic_provider 路径 (`legacy_providers_job`)

- **命中文件数**：9
- **默认建议**：易与 AerSimulator + runtime 混淆；可标注「非 HumanEval 主路径」

  - `HUMANEVAL_API_DOC_AUDIT.md`
  - `qiskit_providers_basic_provider_basic_provider_Backend.md`
  - `qiskit_providers_basic_provider_basic_provider_job_JobV1.md`
  - `qiskit_providers_basic_provider_basic_simulator_BackendV2.md`
  - `qiskit_providers_basic_provider_basic_simulator_Clifford.md`
  - `qiskit_providers_basic_provider_basic_simulator_Options.md`
  - `qiskit_providers_basic_provider_basic_simulator_StabilizerState.md`
  - `qiskit_providers_basic_provider_basic_simulator_Target.md`
  - `qiskit_providers_job_JobV1.md`

### QuantumCircuit.to_operator（模型幻觉；官方为 Pauli.to_operator） (`qc_to_operator_hallucination`)

- **命中文件数**：1
- **默认建议**：强调 Operator(qc)

  - `HUMANEVAL_API_DOC_AUDIT.md`

## 附录：全部 `qiskit_primitives_*` 页面（与 runtime Sampler 易混淆）

以下 **19** 篇在检索命中 Sampler/Estimator 题时，容易把模型引向 `qiskit.primitives`而非 prompt 中的 `qiskit_ibm_runtime`：

- `qiskit_primitives_backend_estimator_v2_BackendV2.md`
- `qiskit_primitives_backend_estimator_v2_Options.md`
- `qiskit_primitives_backend_estimator_v2_PassManager.md`
- `qiskit_primitives_backend_estimator_v2_Pauli.md`
- `qiskit_primitives_backend_estimator_v2_PauliList.md`
- `qiskit_primitives_backend_sampler_v2_BackendV2.md`
- `qiskit_primitives_backend_sampler_v2_Options.md`
- `qiskit_primitives_base_base_estimator_Job.md`
- `qiskit_primitives_base_base_estimator_Job_status.md`
- `qiskit_primitives_base_base_estimator_SparsePauliOp.md`
- `qiskit_primitives_base_base_primitive_v1_Options.md`
- `qiskit_primitives_base_base_sampler_Job.md`
- `qiskit_primitives_base_validation_v1_PauliList.md`
- `qiskit_primitives_base_validation_v1_SparsePauliOp.md`
- `qiskit_primitives_containers_bindings_array_Parameter.md`
- `qiskit_primitives_containers_observables_array_Pauli.md`
- `qiskit_primitives_containers_observables_array_PauliList.md`
- `qiskit_primitives_containers_observables_array_SparsePauliOp.md`
- `qiskit_primitives_statevector_estimator_SparsePauliOp.md`

## 附录：providers / basic_provider 相关页面

- `qiskit_providers_Backend.md`
- `qiskit_providers_BackendV2.md`
- `qiskit_providers_Job.md`
- `qiskit_providers_JobV1.md`
- `qiskit_providers_JobV1_status.md`
- `qiskit_providers_Options.md`
- `qiskit_providers_backend_Backend.md`
- `qiskit_providers_backend_BackendV2.md`
- `qiskit_providers_basic_provider_basic_provider_Backend.md`
- `qiskit_providers_basic_provider_basic_provider_job_JobV1.md`
- `qiskit_providers_basic_provider_basic_simulator_BackendV2.md`
- `qiskit_providers_basic_provider_basic_simulator_Clifford.md`
- `qiskit_providers_basic_provider_basic_simulator_Options.md`
- `qiskit_providers_basic_provider_basic_simulator_StabilizerState.md`
- `qiskit_providers_basic_provider_basic_simulator_Target.md`
- `qiskit_providers_job_Backend.md`
- `qiskit_providers_job_Job.md`
- `qiskit_providers_job_JobV1.md`
- `qiskit_providers_options_Options.md`
- `qiskit_providers_providerutils_Backend.md`

## 附录：`generate_preset_pass_manager` 相关页面（10 篇，签名摘录无完整 HumanEval 流程）

无过时 API 字样，但**缺少** `pass_manager.run(circuit)` + `Sampler(mode=backend)` 端到端示例；是否更新取决于你是否要靠 API 库补 recipe 缺口。

- `qiskit_transpiler_preset_passmanagers_generate_preset_pass_manager_Backend.md`
- `qiskit_transpiler_preset_passmanagers_generate_preset_pass_manager_CouplingMap.md`
- `qiskit_transpiler_preset_passmanagers_generate_preset_pass_manager_InstructionDurations.md`
- `qiskit_transpiler_preset_passmanagers_generate_preset_pass_manager_Layout.md`
- `qiskit_transpiler_preset_passmanagers_generate_preset_pass_manager_Target.md`

---
由 `scripts/audit_rag_qiskit_api_human_eval.py` 生成；机器可读：`HUMANEVAL_API_DOC_AUDIT.json`。