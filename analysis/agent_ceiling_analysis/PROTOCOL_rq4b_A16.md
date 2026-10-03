# rq4b-A16 实验协议(交接文档):强制契约探针 v2,16 题双基线对照

> 撰写:2026-10-01。状态:**已冻结 2026-10-01**(冻结件 = 本文档 + 提示词
> 字节 + manifest,sha 见 §9 与 rq4b_A16_freeze_manifest.json;先于任何
> LLM 调用)。本文自包含:新会话读这一篇即可继续,
> 依赖的冻结件在 §7 索引。
> 前序:A|trace v1 已实现并跑完 rep1(143/143);B|restart/replan 试点
> NO-GO 归档(先验锚定实锤,**不复活**);QB+ 不在本实验范围(0 个断言
> 触发任务,KL 标量线归信息含量研究)。

---

## 0. 一段话

在 QHE-local-hard 上,有 16 个任务在冻结 run(EQPA×3 + DEU-RQ×3)中出现过
"有信息断言失败"——判分器在错误消息里给出了检查内容与期望值,但模型不做本地
诊断、盲改烧 attempt。实验 A16 把 A|trace v1 升级为 **harness 强制探针**
(失败边界自动执行 + Eval 三态拦截),在这 16 题 × 3 replicate = 48 槽上,
以冻结 EQPA 与 DEU-RQ 为双基线,检验"行为证据强制送达"能否转化基线到不了的
13 个槽位。v1 的教训已内置:软义务门失败(模型 0/7 自发探针),v2 把探针执行
收归 harness,不依赖模型服从。

## 1. 问题定义

**信息在场、诊断缺位(informative-assertion diagnosis absence)**:官方
Eval 失败消息含非空断言体(`AssertionError: <检查内容/期望值>`,或人工裁决
前缀 `KeyError: 'x'` / `ValueError: The truth value`),即判分器已说出
"检查了什么";但模型不把该信息转成对自己代码的本地对照(跑自己的入口函数、
打印实际产出 vs 断言要求),直接盲改重交。冻结证据:
- /138 三枪 `Expected 10 density matrices, but got 98 → 0 → 2`(期望值就在
  反馈里,从未本地数过);
- /68 `Live bomb predictions should be high` ×3 逐字重复;
- 有信息失败的同签名重复率 86.7%(相邻失败枪),signature escape 仅 18.2%。

**触发谓词(冻结,复用 `exp/fcea/control/rq4b.py::informative_signature`)**:
AssertionError 且体非空,∪ 人工前缀两条。bare 空断言、接口类、NoSubmit、
KL 标量均不触发(各自的线不同)。

## 2. 测试集(冻结清单与双基线)

**任务集 = 冻结 run(EQPA×3 + DEU-RQ×3,共 6 replicate/题)中出现过 ≥1 个
有信息断言失败枪的全部任务,共 16 题。** 清单经数据集校验(全部 ∈
`dataset_qiskit_test_human_eval_local_hard.json` 的 143 题;注意该数据集
id 跨度 0..150、剔除 8 个空 id {43,97,98,122,129,133,134,146}——**禁止用
`seq 0 142` 选集**,这是 rq4b v1 踩过的坑)。

| task | inf_shots | inf_eps | EQPA pass/3 | DEU pass/3 | headroom |
|---|---|---|---|---|---|
| 32 | 3 | 3 | 0/3 | 0/3 | **3** |
| 68 | 16 | 6 | 0/3 | 0/3 | **3** |
| 138 | 6 | 4 | 0/3 | 1/3 | **2** |
| 51 | 3 | 2 | 1/3 | 0/3 | **2** |
| 52 | 6 | 5 | 2/3 | 2/3 | **1** |
| 99 | 8 | 3 | 2/3 | 2/3 | **1** |
| 100 | 6 | 3 | 1/3 | 2/3 | **1** |
| 9 | 6 | 6 | 3/3 | 3/3 | 0 |
| 62 | 2 | 2 | 3/3 | 3/3 | 0 |
| 106 | 1 | 1 | 3/3 | 3/3 | 0 |
| 111 | 2 | 2 | 3/3 | 3/3 | 0 |
| 112 | 2 | 2 | 2/3 | 3/3 | 0 |
| 136 | 2 | 2 | 3/3 | 3/3 | 0 |
| 137 | 6 | 6 | 3/3 | 3/3 | 0 |
| 144 | 4 | 3 | 3/3 | 3/3 | 0 |
| 145 | 2 | 2 | 3/3 | 2/3 | 0 |

- **headroom = 13/48 槽**(双基线都到不了的),集中在 7 题:32、68、138、
  51、52、99、100——这是疗效判定的分母;
- 另 7 题双基线 3/3(或折算 0 headroom):**回归哨兵**(v2 必须 3/3 保持,
  跌一个即 K3 违反);
- 预注册基线(冻结):EQPA **32/48**,DEU-RQ **33/48**。

## 3. 优化方法:强制契约探针 v2(三层)

v1 已有并保留:触发谓词、A1 注入文本(rq4b_frozen_prompts.md §1 字节冻结)、
台账。v2 新增三层强制,全部 **harness 侧、零模型服从依赖**:

### L1|失败边界自动探针(核心)
触发边界处,harness 对当前 last_code 自动执行:
1. 沙盒内 import attempt 文件;
2. 内省入口签名 → **dummy 参数阶梯**:无必选参→直接调;有注解→按类型
   (float→0.5, int→3, str→"00", list→[], bool→True);TypeError→换下一档;
   全失败→返回构造错误(也是证据);
3. **工件描述器**(替代断言模板):序列→len+首元素类型;标量→值;
   QuantumCircuit→num_qubits+count_ops;dict→keys;
   DataBin/PrimitiveResult→字段名;其他→repr 截断;
4. 输出块注入反馈:`[trace] assertion expects <parsed>; your artifact: <described>`。

### L2|Eval 三态拦截(强制力所在)
武装态调用 Eval 时,先对 attempt 文件跑 L1 探针,三态:
- **failed**:入口崩溃,或**可解析 mismatch**(断言体含数字 N 且探针数值 ≠ N)
  → **非官方拒绝**,探针证据作为 Eval 工具结果返回(不烧 attempt);
- **indeterminate**:断言无可解析数值 / 构造失败 / 超时 → **FAIL-OPEN 放行**;
- **passed**:放行。
约束:每 shot 拒绝上限 **3**(超帽本 shot 退化放行,杜绝拒绝循环);
trace 探针超时 **16s**(v1 的 8s 截断过 /9 的入口调用)。

### L3|模型自组通道保留
模型自发跑 `requested_evidence_kind="trace"` 的 BatchProbe → 直接放电义务。
双通道并存,harness 自动探针不受其影响。

**冻结常量**:θ 不适用(触发即武装)、REJECT_CAP=3/shot、TRACE_TIMEOUT=16s、
DUMMY 阶梯如上、注入文本 = v2.1 §1 逐字。实现落点:新 flag
`rq4b_trace_v2`(变体 `deurc_trace_v2`),探针执行模块复用 MECH-1 的
`control/preflight.py` 三态骨架与 `evidence/contract_probe.py` 的沙盒执行
模式;全部默认关,既有变体字节不变(`selftest_rq4b` 扩展覆盖)。

## 4. 试点(先行,冻结清单)

| 组 | 任务 | 判据 |
|---|---|---|
| 失败三题 | 68、32、52 | L1 探针送达(每边界 ≥1 块证据);≥1 题转化;拒绝循环 0 |
| 阳性对照 | 138、137 | 送达且不劣于 v1(138 应过) |
| 哨兵 | 9、144 | 3/3 保持,0 误拒 |

门:**P1** 送达率 ≥90%(武装边界中探针块送达比例);**P2** 拒绝循环 0
(cap 生效);**P3** 哨兵 3/3 + 安慰剂行为不变;**P4** /138 或 68 至少
一项改善。全过 → 48 槽全量;失败 → 按分支归档(送达失败=实现问题可修重试;
送达但无转化=证据不转化为修复,喂 RQ-B)。

## 5. 全量(16×3=48 槽,tag `rq4b_fcea_qhe_deurc_tracev2`)

**主终点(疗效)**:48 槽 pass 数 vs 双基线(EQPA 32、DEU 33);**headroom
转化数**(13 槽中 v2 通过数)为机制效力主 readout;
**机制指标**(判定器 `rq4b_metrics.py` 冻结口径):signature same-rate
(基线 86.7%)、escape(基线 18.2%)、basin escape(基线 30.0%);
**安全**:7 哨兵题 3/3 无回归;NoSubmit ≤1;calls/tokens 增量 ≤+25%
(L1/L2 探针为本地执行,LLM 增量主要来自可能的额外修复轮);
**推断**:配对 task-cluster bootstrap(B=10000,seed=20260930)+ 分题
逐槽表(48 槽对 +2~3pp 功效不足,预注册"方向+机制门"为 readout)。
**杀死门**:K1 送达率 <90%(实现问题,修后可重试一次);K2 headroom 转化
= 0 且哨兵无回归 → "强制证据仍不转化"归档(喂 RQ-B);K3 哨兵回归 → 停。

## 6. 与其他线的关系(防撞车)

- **B|restart/replan:已归档不复活**(先验锚定阴性:同规格重生成复现同一
  错误分布,/11 逐字 27.631);若 v2 成功,B 的失败题(远失带)不在本集;
- **MECH-1(并行会话)**:治 ENV 残留(接口域),本实验治语义断言域,flag
  全部默认关、可组合;端点独占惯例:发起 LLM 调用前确认无
  `exp.fcea.run` 进程;
- **QB+ / KL 标量 / bare 空断言(53 题)**:不在本实验;归信息含量线
  (RQ-A)与行为断言源线;
- **S1(规格推导契约)已否决**:v2 的探针只对照"断言体已给出的期望",
  不推导期望分布——零 canonical 泄漏面。

## 7. 现有资产索引(新会话必读)

| 资产 | 路径 |
|---|---|
| 机制实现(已验证 37/37) | `exp/fcea/control/rq4b.py`(v1:谓词/TraceGate/提示词字节);v2 在此扩展 |
| 接线 | `exp/fcea/loop.py`(六处,全变体门控)、`exp/fcea/config.py`(变体注册/TAG_PREFIXES 含 `rq4b_fcea`) |
| 自检 | `exp/fcea/selftest_rq4b.py`(**改动后必跑**,37/37) |
| 提示词冻结件 | `analysis/agent_ceiling_analysis/rq4b_frozen_prompts.md`(字节级) |
| 判定器+基线 | `analysis/agent_ceiling_analysis/rq4b_metrics.py` / `rq4b_metrics_baselines.json` |
| 试点报告(v1) | `analysis/agent_ceiling_analysis/rq4b_PILOT_REPORT.md` |
| 协议 v2.1(A 线前史) | `analysis/agent_ceiling_analysis/PROTOCOL_rq4b_trace_replan.md` |
| 残留归类依据 | `analysis/agent_ceiling_analysis/residual_error_classification.*` |
| 监控脚本(可用) | `/root/rq4b/full_watch.sh`(挂起+NoSubmit 守卫模式,改 tag 即用;**勿放 /tmp,会被并行会话清理**) |
| B 归档数据 | `exp/fcea/results/rq4b_fcea_qbplus_deurc_{restart,replan}_pilot_*` |
| A v1 数据 | `exp/fcea/results/rq4b_fcea_qhe_deurc_trace_traces.jsonl`(rep1 143/143,可作为 A1 参照臂,不并入 v2) |

**运行状态**:A v1 全量在 136/429 处被用户暂停(实际=rep1 143 题中的 136
题,后已补齐 7 题=143/143);B 未进全量;MECH-1(并行会话)Stage-2 已收口。
**恢复命令模板**:`cd /root/cyy/llm_code/submit && python3 -m exp.fcea.run
--bench qhe --variant <variant> --tag <tag> --cases <数据集全id列表> --workers N`
(**--cases 必须来自数据集文件,禁止 range/seq 连续 id**)。

## 8. 冻结前裁决清单

1. 16 题清单与双基线数字(§2)是否认可;
2. v2 三层强制设计(§3)与 FAIL-OPEN 边界;
3. 常量:REJECT_CAP=3、TRACE_TIMEOUT=16s、dummy 阶梯;
4. 试点清单与 P 门(§4);
5. 主终点 = headroom 转化 + 双基线配对(§5),"方向+机制门"readout 声明;
6. tag:`rq4b_fcea_qhe_deurc_tracev2{,_pilot}`;哨兵题无回归作为 K3。

## 9. 冻结记录(2026-10-01,先于任何 LLM 调用)

**§8 裁决:六项全部通过。** 冻结前离线验证(零 LLM 成本,证据脚本入库):

- 第 1 项:`verify_a16_taskset.py` 从六个冻结轨迹重算 §2 表 → **ALL MATCH**
  (16 题逐项一致;headroom 13/48 于 {32,68,138,51,52,99,100};基线
  EQPA 32/48、DEU-RQ 33/48;数据集剔除 id {43,97,98,122,129,133,134,146} 实证)。
- 第 2–6 项:实现落地为变体 `deurc_trace_v2`(默认关,既有变体字节不变,
  三套自检 172/0、37/37、91 检查全过),常量、试点分组、P/K 门、tag、
  readout 与本协议 §3–§6 一致,冻结于 `rq4b_A16_freeze_manifest.json`。

**冻结时对 §3-L2 边界两处细化(实现先行验证逼出,随本记录一并冻结)**:

1. **崩溃拒绝只认 AssertionError**:dummy 输入引发的 QiskitError/
   CircuitError 等崩溃是探针伪影而非代码缺陷(沙盒实测 /99 /100 /112 /145
   的**通过**代码同样在 dummy 下崩溃),归 indeterminate FAIL-OPEN;
   证据仍经 L1 块送达。
2. **类型连贯守卫**:集合长度类探针值仅在断言体含尺寸语义词
   (length/len(/size/count/number of/expected/elements/items/entries)时
   参与 mismatch;否则 indeterminate。依据:/144 "The concurrence … is
   not 0" 会被解析为 expected=0 并把通过代码的序列长度误判为 mismatch,
   击穿试点哨兵 144 的 P3 零误拒门。

**沙盒回放验证(冻结代码,真实 bwrap 环境)**:L1 块在 11/11 个有信息
失败代码上送达;mismatch 拒绝恰好只落在 /137(154 vs 10)与 /138
(24 vs 10);13 个零 headroom 题的通过代码**零误拒**。

冻结件 sha256(全量见 manifest):协议本文 30b6468566c4454c…、
提示词冻结件、判定器、基线、`control/trace_probe.py`(探针模板字节)、
`control/rq4b.py`、`loop.py`、`run.py`、`config.py`、自检——以
`rq4b_A16_freeze_manifest.json`(build_a16_freeze_manifest.py 可再生)为准。
**任何后续字节改动 = 协议修正案 + 重跑试点。**
