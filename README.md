# 量子代码生成智能体的可靠性增益与错误分布迁移

本仓库是量子代码生成智能体研究的实验代码仓库，包含主对比网格 **13 条实验臂**的运行
代码与基准评测栈；分析脚本、设计文档与实验结果数据不随仓库发布。

## 研究问题

大语言模型为量子编程提供了从自然语言规格生成完整量子程序的途径，但两条路径的相对贡献
尚缺乏受控证据：一是**智能体化**（agentization）——让模型从被动接收评测反馈，升级为
能在提交前主动调用执行工具、观测运行环境；二是在此之上继续增加**智能体复杂度**
（agent complexity）——叠加证据组织、交互治理与定向修复等干预机制。

论文在统一协议（单一基础模型、每题至多 3 次官方评测提交、任务聚类 bootstrap 推断）与
两个 Qiskit 基准上回答：

- **RQ1** 执行式智能体相对现有量子代码生成方法的有效性如何？
- **RQ2** 智能体化之后还剩哪些失败？失败面如何随干预层演化、对定向干预的可处理性如何？
- **RQ3** 成本结构如何？交互机制如何改变可靠性与成本的权衡？
- **RQ4** 架构的哪些部分承载了可靠性、效率与失败恢复？层间如何相互作用？

核心发现概括：可靠性增益主要由简单的执行式智能体承载；在其上继续叠加机制未带来总体
通过率的稳定提升，而是**改变错误发生的位置**（失败面在框架接口通道与语义通道之间迁移）
与交互成本；残余语义失败大多不携带可解析的行为期望，针对性修复的可处理靶群由评测反馈
的诊断信息可得性决定。

## 实验臂

全部实验臂构建在同一基础模型、同一评测环境（Python 3.10 + Qiskit 2.4.1）与同一
预算结构（每题 ≤3 次官方提交）之上，按三个能力层级组织：

| 层级 | 实验臂 | 交互能力 |
|---|---|---|
| 静态单轮（pass@3 三次独立采样） | `oneshot`、`cot`、`qscot`、`rag` | 不利用当前候选程序的执行反馈；`rag` 在首次生成时注入三层知识库检索 |
| 被动反馈环（≤3 次提交） | `loop`、`loop_cot`、`loop_qscot`、`loop_rag` | 首次生成与对应静态臂逐字节一致，失败后接收官方错误回灌修订，不能主动探索环境 |
| 执行式智能体 | **E0** | ReAct 风格工具环（沙盒 `Shell` 主动取证 → `Write` 候选 → `Eval` 官方评测），内建 Z0 执行卫生层（探查硬预算、重试熔断、残码提交门、名额兜底） |
| 干预阶梯 | **E1–E4** | E0 之上按预注册顺序累积叠加：Z1 结构化取证（E1）、Z2 交互治理（E2）、Z3 接口契约修复（E3）、Z4 语义对照（E4） |

- **Z1 结构化取证**：将零散 Shell 探索替换为按证据族组织的批量取证工具 BatchProbe；
- **Z2 交互治理**：状态感知控制栈，按进展、证据效用与剩余预算在四类动作中决策；
- **Z3 接口契约修复**：面向框架接口错误（ENV），经环境探针、提交前预检、失败账本与
  定向契约探针两条通路供给运行时契约事实；
- **Z4 语义对照**：面向语义规划错误（SEM），由冻结失败签名触发武装后，将失败反馈携带的
  行为期望与候选程序实际行为做本地对照（fail-open）。

两个基准代表两种判分模式：`QHE_local_hard`（143 题，隐藏测试与断言，ENV 主要来源）与
`QuanBench+ Qiskit`（42 题，测量分布 KL 失配阈值 0.05，作为 Z4 的预注册负控域）。

`rag` 臂的三层知识库（K1 API/框架参考 79 篇、K2 安全用法配方 20 篇、K3 算法模式卡
24 张，含构建 MANIFEST）随仓库提供于 `exp/rag/kb/`。

## 仓库结构

```text
.
├── README.md                        # 本文件
├── LICENSE                          # MIT
├── .env.example                     # 环境变量模板（复制为 .env 后填入；切勿提交 .env）
├── bench/                           # 基准与官方评测栈（数据 + grader，不含实验逻辑）
│   ├── qhe/                         #   Qiskit-HumanEval local_hard（143 题；sealed/ 为隐藏测试）
│   └── qbplus/                      #   QuanBench+ Qiskit 子集（42 题）
├── exp/                             # 实验代码（每臂一个包，run.py 为入口；exp/config.py 为中心配置）
│   ├── oneshot/ cot/ qscot/ rag/            # 静态单轮臂（rag/ 内含三层知识库 kb/）
│   ├── loop/ loop_cot/ loop_qscot/ loop_rag/ # 被动反馈环臂
│   ├── d5conv/                      #   E0 运行器（ReAct 式工具环，react_e0 模式）
│   ├── fcea/                        #   E1–E4 运行器（deurq_z1 / deurq_base /
│   │                                #   deurq_baseenv_v2 / deurq_final 变体）
│   ├── eqpa/                        #   沙盒执行基础设施（bwrap/jail/tools），被 E0–E4 复用
│   ├── d4shell/ evidence_eqpa/      #   上述运行器依赖的基础配置模块
│   └── common/                      #   共享基础设施（LLM 客户端、评测调用、沙盒辅助）
└── analysis/                        # 仅含运行器启动时读取的两份冻结输入文件
    ├── rq4_fcea/qhe_evidence_utility_prior.json     #   冻结效用先验（Z2）
    └── agent_ceiling_analysis/PROTOCOL_rq4b_A16.md  #   冻结协议文档（Z4 探针）
```

## 运行方式

在仓库根目录执行（各包 `run.py` 为入口，`--bench` 选择基准，`--dev` 为小规模试跑，
`--workers` 控制并发）：

```bash
# 静态单轮臂（oneshot / cot / qscot / rag 同构）
python -m exp.oneshot.run --bench qhe
python -m exp.rag.run --bench qbplus      # rag 臂需在 .env 配置 RAGFlow 服务

# 被动反馈环臂（loop / loop_cot / loop_qscot / loop_rag 同构）
python -m exp.loop.run --bench qhe

# 执行式智能体 E0
python -m exp.d5conv.run --bench qhe

# 干预阶梯 E1–E4（--variant 区分层）
python -m exp.fcea.run --bench qhe --variant deurq_z1        # E1 = E0 + Z1
python -m exp.fcea.run --bench qhe --variant deurq_base      # E2 = E1 + Z2
python -m exp.fcea.run --bench qhe --variant deurq_baseenv_v2 # E3 = E2 + Z3
python -m exp.fcea.run --bench qhe --variant deurq_final      # E4 = E3 + Z4
```

运行结果写入各臂包内 `results/` 目录（逐 episode JSONL + 汇总）。该目录已被
`.gitignore` 排除，按发布决定不随仓库分发。

## 环境准备

1. Python 3.10，安装 Qiskit 2.4.1 评测栈依赖；
2. `cp .env.example .env`，填入 DeepSeek API 配置（`rag` 臂另需可用的 RAGFlow
   多数据集检索服务）；`.env` 已被 `.gitignore` 排除；
3. `analysis/` 下两份冻结输入文件（效用先验与 Z4 探针协议）是 E0–E4 启动时读取的
   运行必需项，请保持其相对路径不变。

## 许可证

代码以 [MIT](LICENSE) 许可证发布。`bench/` 内两基准的题目与判分沿用上游
（Qiskit HumanEval、QuanBench+），重分发遵循其各自许可证。

