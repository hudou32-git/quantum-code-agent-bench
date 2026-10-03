# CTRL-ISO：隔离 REPL 方案（堵 E3 泄漏）

日期：2026-09-07（按评审修订：OS 层隔离为主闸、保留 `Shell`、smoke 题改 dev）。  
对象：E3 CTRL 的 **文件系统泄漏**。官方环仍是 Pass@≤3；不把四工具卡塞进 CTRL。  
对齐：Cursor 盲测的 **可见工作区 / 特权 grader 分离**；执行侧用 **mount namespace**，不依赖模型自觉，也不把 `sys.addaudithook` 当沙箱。

**现在不要直接跑 143。** 先按本文改实现、过 isolation selftest（含随机 canary），再开 dev scaffolding，最后才是正式评测。

E3 全量 CTRL 129/143 标成 **污染历史上界**。CTRL-ISO 的干净分才能进主表。

---

## 0. 问题（E3 已证）

E3 禁词只扫 **命令字符串**（`canonical_solution` / `check(` / `dataset_qiskit_test`）。`run_repl` 的 cwd 是仓库根 `/root/cyy/llm_code`。模型可以：

1. `os.listdir` 看到 `qiskit-human-eval/dataset/`；
2. `json.load` 打开题库 JSON（路径里可以不含禁词，或先 listdir 再拼）；
3. stdout 把 `canonical_solution` 和 `def check(` 送回 `role: tool`。

实测：**17/143** 题 stdout 含 gold/test，其中 13 题是 CTRL 相对 CARD 的独过。

Cursor 做的是工作区隔离（`visible/` + `sealed/` + `.cursorignore`），不是 Shell 词表。E3 CTRL 把「环境探索」和「读题库」放在同一个有完整宿主机文件系统的进程里。隔离必须发生在 **工具执行层**。

Python 的 `sys.addaudithook` **不能当主安全边界**（官方文档与 PEP 578：audit hook 用于审计，不是 sandbox；解释器内代码可绕过或卸掉 hook）。主闸必须是 **OS namespace / mount**：**进程的文件系统里根本不存在 dataset/sealed**，而不是「禁止读 dataset」。

---

## 1. 主张与不主张

主张（单因子尽量只改「看不见题库」）：

- **CTRL-ISO − E3 CTRL**：同一套 **`Shell` + `Write` + 多跳 + 3 枪官方环**；唯一要拿掉的是对 benchmark-private 文件的访问。评测从 Agent 自己 `Shell(eval_blind)` 改为特权 **`Eval()`**。
- 干净 Pass@≤3 与 LLM 次数一并报。
- 安全问题与工具能力问题分开：开放 Shell 保留；隔离放在 OS 层。

不主张：

- 用收紧查询（只许 `hasattr` 白名单）来「假装」隔离——那会变成 CARD，且与 E3 CTRL 不可比。
- 把 `Shell` 换成 `Python(code)` 还声称「只做了 isolation」。若实现走窄 Python 口，臂名必须叫 **CTRL-ISO-PY**，不能叫 CTRL-ISO。
- 把 `sys.addaudithook` 当 filesystem jail。
- 用 `/15 /21 /30 /104 /121` 是否官方 PASS 作为 **isolation gate**（这些题已是 dev）。
- 把 budget-matched 无工具多轮塞进本实验（那是 CTRL-ISO 之后的对照）。

探索阶段可以只跑 CTRL-ISO、借用 E3 BARE/CARD。**写 ASE 主表时**应在同一模型快照 / 时间窗 / harness 下重跑 BARE、CARD、CTRL-ISO；旧 E3 CTRL 129 放附录。

---

## 2. 隔离架构（保留并增强）

「Agent 可见执行环境」和「特权 grader」物理分离。这是 E3 泄漏应对的正确结构。

```text
                         LLM
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         Shell(cmd)      Write()       Eval()
             │            │            │
             ▼            │            ▼
      OS sandbox          │      Privileged grader
      ┌─────────────┐     │      ┌───────────────┐
      │ /opt/qhe RO │     │      │ sealed tests  │
      │ /workspace RO│    │      │ gold metadata │
      │ /tmp RW     │     │      │ official eval │
      │ no network  │     │      └───────┬───────┘
      │ no host repo│     │              │
      └─────────────┘     │              ▼
                          │      {passed, error}
                          ▼
                   exact attempt_k.py
                   no symlink / no traversal
```

外围（都不是主闸）：

```text
source policy     可选，减少无意义违规查询；不禁止 listdir/inspect
audit hook        日志 / 检测，不当事后沙箱
stdout scanner    最后泄漏保险（含随机 canary）
```

Cursor：`visible/` ≈ sandbox 里的 `/workspace`；`sealed/` ≈ grader 私有；grader CLI ≈ `Eval()`。  
CTRL-ISO 对 DeepSeek **强制** mount 隔离：即使 `find /`、`os.listdir('/')`、`open('/root/cyy/llm_code/...')`，也看不到题库。

---

## 3. 每题 jail 与 sandbox 视图

Host 上每题目录：`experiment6/artifacts/<tag>/jail/<task_safe>/`

```text
prompt.txt
attempt_1.py
attempt_2.py
attempt_3.py
```

`Eval` 的 result JSON 写在 jail **旁** 的 harness 私有路径（或同目录但 **不 bind 进 sandbox 可写层**），字段仅 `task_id` / `passed` / `error`。

每次 `Shell` 进入独立 mount namespace 后，Agent **只看见**：

```text
/
├── opt/qhe/          # conda qhe：Python + Qiskit，只读 bind
├── workspace/        # 本题 prompt + attempt_*.py，只读 bind
├── tmp/              # writable tmpfs（micro experiment 写这里）
├── usr/lib/...       # 必要系统库，只读
└── proc/             # 仅 sandbox 自己的 proc
```

**不存在：** `/root/cyy/llm_code`、dataset、sealed、grader 源码、其它 task 的 jail、`/root`、shell history、host git。

对 Shell 而言 `/workspace` **只读**。正式 `attempt_k.py` **只能**由 host 侧 `Write` 原子写入后再 bind 进去。模型在 sandbox 里做实验应写 `/tmp/test.py`，不能靠 Shell 改 attempt（保证 provenance、堵住 symlink 借 Write/Eval 逃逸）。

user 只给相对名，**禁止**再贴 `eval_blind.py` 或仓库绝对路径：

```text
Workspace:
- task_id: qiskitHumanEval/N
- visible files: /workspace/prompt.txt, /workspace/attempt_k.py (read-only)
- inspect: Shell 在隔离环境执行（含 qhe Python）
- scratch: /tmp
- submit: Write attempt_k.py, then Eval()
```

---

## 4. 工具：保留 `Shell`，评测拆成 `Eval`

`tools[]` 固定三个 schema，不随题目改 description，不出现 FakeOslo 等题面词。

| 工具 | 模型以为 | harness 实际 |
|------|----------|----------------|
| **`Shell(command)`** | 在评测环境执行一条命令 | **unprivileged sandbox**（§5）；cwd=`/workspace` |
| **`Write(path, contents)`** | 写本题 attempt | host 侧只接受三个精确文件名；§6 |
| **`Eval()`** | 对本题当前 attempt 跑官方评测 | jail **外**的特权 grader；§7 |

这才能说：CTRL-ISO **保留 E3 的交互式 Shell affordance**，只去掉对 benchmark-private 文件的访问。

E3 里 Agent 用 Shell 调 grader，把「环境探索」和「官方评测」混在同一权限里。CTRL-ISO 拆开：

```text
Shell = unprivileged exploratory execution
Eval  = privileged official evaluation
```

内环与 E3 相同：写代码前可多跳 `Shell`（仍最多 8 次非 Eval / 枪）；`Eval` 成功执行才 +1 官方枪；PASS 停题；FAIL 追加 `format_humaneval_feedback`。

若有人实现 `Python(code)` 而无通用 Shell，那是另一臂 **CTRL-ISO-PY**，不能用来解释「129 掉分只因为堵住了泄漏」。

---

## 5. 主闸：OS mount / process sandbox

每一跳 `Shell` 都在新的 namespace 里启动。优先 **bubblewrap**（无则装 `bubblewrap`；备选 nsjail）。本机已有 `unshare`，但正式实现不要手写一套不完整的 mount 逻辑。

Sandbox 必须做到：

| 项 | 设定 |
|----|------|
| 文件系统 | 新 mount ns；只 bind 上表所列路径；`/workspace` ro，`/tmp` rw tmpfs |
| 网络 | 无（`--unshare-net` 或等价） |
| PID | 独立；看不见 host PID 1 的 cmdline / root |
| User | 尽可能 user ns；device / ptrace / host unix socket 关掉 |
| 资源 | CPU / 内存 / 进程数 / stdout 字节上限（沿用 E3 量级：超时约 12s，stdout 约 4KB 可调） |
| 环境 | `HOME=/home/agent`，`PWD=/workspace`，`PYTHONPATH=""`，`PYTHONDONTWRITEBYTECODE=1`；不传 host `PATH` 里指向仓库的项 |

**不是禁止 `listdir`，而是 `/` 下列出的目录里没有题库。** `find / -type f`、`getattr(os,"listdir")("/")`、`pathlib`/`glob`/`mmap`/`subprocess.run(["find","/"])` 都可以跑；成功标准是 **看不到 sealed/dataset**，不必把这些调用标成 `blocked`。

### 5.1 Python 环境本身

`/opt/qhe` 只读挂 conda `qhe`。selftest 必须检查 sandbox 内：

```python
sys.path
site.getsitepackages()
```

不得出现指向 host 仓库的 `.pth`、`.egg-link`、`direct_url.json`、editable install。Agent 的 Python path 中 **不存在 benchmark repository**。即使某个包曾 `pip install -e /root/cyy/llm_code/...`，mount 后目标应不可达；正式产物仍应保证 path 里没有该字符串。

### 5.2 降级层（可选，不是主闸）

```text
OS namespace / mount sandbox     ← 真正安全边界
            ↓
source filter                    ← 可选；只挡明显逃逸（mount/ptrace），不禁止探索
            ↓
audit hook                       ← 日志，不当事后沙箱
            ↓
stdout sanitizer + canary        ← 最后一层泄漏保险
```

**不要**再维护「禁止 `open(` / `Path(` / `os.listdir` / `glob` / `json.load`」的巨型源码黑名单。核心研究的就是模型自主探索已安装的 Qiskit；`os.listdir("/opt/qhe/.../qiskit")` 是合法 grounding。

stdout 扫描保留为保险：随机 canary（§8）为主；`canonical_solution` / `def check(` 为辅。命中则整段观察替换为 `blocked: sealed pattern`，不回灌半截正文。

---

## 6. `Write`：精确文件名，防 symlink escape

schema 仍可叫 `Write(path, contents)`，内部 **只接受三个精确字符串**：

```text
attempt_1.py
attempt_2.py
attempt_3.py
```

- 不允许 `/`、`..`、绝对路径、`/tmp/x.py`。
- 不允许已存在的 symlink：写入前 `lstat`；用 `O_NOFOLLOW` / `openat`+dirfd。
- harness 在 **host** 上原子写入 jail 里对应文件（先写临时文件再 `rename`），再供下一跳 Shell 只读看到。
- 不 `open()` 跟随 symlink 的 `realpath startswith jail` 作为唯一检查。

Shell **不能**写 `/workspace`。sandbox 内对 attempt 的 `ln -s` 若成功，下一跳 Write 仍按 basename 在 host 侧 `O_NOFOLLOW` 打开真实文件；Eval **只读 harness 记录的最近一次成功 Write 路径**，不遍历目录「找一份 attempt」。

---

## 7. `Eval()`（特权 grader）

- 参数：无，或 `k in {1,2,3}`；默认 harness 记下的最近一次成功 Write。
- 在 jail **外**调用 `run_candidate` / `eval_blind.py`；模型看不到命令行、看不到 sealed 路径。
- 回灌 `{passed, error}`。`error` **不得**含 sealed 路径、hidden 测试源码、canonical、gold histogram。QHE 沿用现有 `eval_blind` 合同（失败原文可截断 4000，但需扫 canary 与路径）。
- 官方枪：仅 `Eval()` 成功跑完 +1。`Shell` / `Write` / sandbox 内超时都不算枪。

QHE 与日后 QuanBench+ 共用模型接口，只换 adapter：

```text
EvalAdapter
├── QHE  → assert / hidden test
└── QB+  → shots + KL（matched seeds，见 §11）
```

---

## 8. 随机 canary（泄漏审计）

实验启动时，在 host 的 dataset / sealed / grader 目录各写入 **不可猜** 的随机串，例如 `SECRET_CANARY_<32 hex>`。三处可以不同。

之后扫描：**所有** tool stdout、`role: tool`、messages、attempt 正文。正式报告：

> 0/N tool observations exposed any randomly seeded hidden canary.

比只扫 `canonical_solution` 强：模型可能只泄露内容、不含那些固定词。Canary 文件本身绝不 bind 进 sandbox。

---

## 9. Isolation selftest（无 LLM；不过则禁止评测）

文件：`experiment6/selftest_ctrl_iso.py`。全部是 **synthetic** 命令，**不属于** QHE 题。成功标准以「看不见 host 私有物 / canary」为准；`find /` 允许运行。

| 类 | 例子 | 期望 |
|----|------|------|
| 合法 API | `import qiskit; print(qiskit.__version__)`；`hasattr` Fake 在 runtime 包 | 成功；版本 2.4.1 |
| 直接逃逸 | `../../`、绝对路径读 host、`os.chdir("/")` 再读 repo | 无 dataset/sealed/canary |
| 间接枚举 | `getattr(__import__("os"), "listdir")("/")` | 可见根不等于 host 根 |
| 其它文件 API | `os.open` / `io.open` / `pathlib` / `glob` / `scandir` / `mmap` | 同上 |
| subprocess | `subprocess.run(["find","/","-type","f"])` | **可运行**，输出不含 canary、不含 sealed |
| `/proc` | `/proc/self/root`、`/proc/self/fd`、`/proc/1` | 只见 sandbox |
| symlink | `/tmp/x` → host hidden path | 目标不可见 |
| 环境 | `env`、`sys.path`、`HOME`、`PWD` | 无仓库路径 |
| 跨题 | task A 的 sandbox | 看不见 task B 的 prompt/attempt |
| Write 逃逸 | `../x.py`、`/tmp/x.py`、symlink `attempt_1.py` | Write 失败 |
| canary | 任意探索命令 | stdout/messages 0 命中 |

**不要**把「`/21` 官方 PASS」写成 isolation gate。隔离闸门只验证：Fake 包 **inspect/hasattr 能跑**，不验证某一道 benchmark 过不过。

---

## 10. Dev / Test（防协议过拟合）

`/15 /21 /30 /104 /121` 已反复用于搭脚手架，视为 **development set**，不能再当未碰过的 test。

| 阶段 | 样本 | 目的 |
|------|------|------|
| Security selftest | synthetic（§9） | 隔离是否成立 |
| Scaffolding dev | 固定少量 dev 题（可含上述五题，或另抽 ≤10 题并冻结名单） | 工具环能否跑通、能否 inspect Qiskit |
| 正式 QHE | 其余 held-out `local_hard`；若必须报全 143，则同时报 **143-all** 与 **held-out-only** | Pass@≤3 + LLM |
| QuanBench+ | 协议 **hash 冻结之后** 一次性外部评测 | 外部验证；**不要**用 QB+ 调工具 |

Dev 闸门示例（预注册）：selftest 全过；dev 题上 `Eval` 能返回 `{passed,error}`；至少一次合法 `importlib`/`inspect` 非空；canary 0 命中。**不是**「dev 五题必须过满」。

---

## 11. 实验怎么跑

臂名：**CTRL-ISO**。不要覆盖 `e3_traces.jsonl`。`tag = e4_iso`。

```bash
cd /root/cyy/llm_code/myagent
# 0. 安装 bubblewrap（若尚未有 bwrap）
# 1. isolation selftest
/root/anaconda3/envs/qhe/bin/python -m experiment6.selftest_ctrl_iso
# 2. scaffolding dev（标记为 dev，不写进主结论）
/root/anaconda3/envs/qhe/bin/python -m experiment6.run e4-iso-dev --workers 64
# 3. 正式评测（通过 selftest 之后）
/root/anaconda3/envs/qhe/bin/python -m experiment6.run e4-iso --workers 64
```

探索阶段可只跑 CTRL-ISO，与冻结 E3 BARE/CARD 对照以估计泄漏影响。

ASE 主表（推荐同一次冻结）：

| 臂 | 含义 |
|----|------|
| BARE | 无接地，同时重跑 |
| CARD | 强制四工具卡，同时重跑 |
| CTRL-ISO | 本方案 |
| E3 CTRL 129 | 附录：污染历史上界 |
| Cursor 129 | 对照上界（IDE ignore ≠ 本 sandbox，可见信息应对齐） |

主指标：Pass@≤3、Pass@1、LLM 次数、canary 0 命中。

### 11.1 四种可能结果（解释用，不预注册「必须 90%」）

- **A**：QHE CTRL-ISO ≈ 90% 且日后 QB+ ≫ BARE → 交互环境 grounding 跨基准成立。  
- **B**：QHE 高、QB+ 几乎不涨 → tool loop 主要解决软件/API 环境，解决不了量子语义；后续回到 residual semantic repair。  
- **C**：QHE ISO ≈ 75–80% → E3 的 90.2% 有相当一部分来自泄漏或逛仓库；不要再基于 129 建理论。  
- **D**：ISO ≈ 90% 但日后 budget-matched 无工具也 85–90% → 主因可能是推理预算而非 tool 本身。该对照 **不在** 本 isolation 实验内。

---

## 12. QuanBench+（协议冻结后的外部验证）

模型接口仍是 `Shell` / `Write` / `Eval`，只换 evaluator adapter。QB+ **不要**参与搭脚手架。

额外锁三件事：

1. 模拟器、shot 数、**跨臂匹配的 RNG seed**（同一 `task × attempt` 各臂同 seed，避免 KL 阈值附近的 shot noise 制造假配对差）。  
2. 允许的环境知识：import Qiskit、inspect 已装 API、自己构造电路、自己跑 simulator、看自己的 statevector/distribution。  
3. 不可见：canonical、gold histogram、hidden expected state、hidden tests、带答案的 metadata。

边界：**允许模型自己做实验，不允许读答案。**

---

## 13. 明确不做

- 现在直接跑 143。  
- 把 E3 CTRL 129 当论文主数字（除非附录标明泄漏）。  
- 用 audit hook / 巨型源码黑名单当 filesystem jail。  
- 删掉 `Shell` 换成 `Python` 还声称单因子 isolation。  
- user 里再贴 `eval_blind.py` 或 dataset 路径。  
- 给 `Read`/`Grep`（无 Cursor 那层 ignore）。  
- 用 smoke 五题官方 PASS 当安全闸。  
- 用 QB+ 调工具。  
- 本实验里做 budget-matched 无工具多轮（记下为下一对照即可）。  
- 顺手改 CARD-LLM。

---

## 14. 实现落点（selftest 通过前不评测）

| 文件 | 职责 |
|------|------|
| `ctrl_iso_jail.py` | 建 host jail、RO bind 清单、环境变量 |
| `ctrl_iso_bwrap.py` | bubblewrap 启动 `Shell`；无 `bwrap` 则硬失败，不静默退回 host cwd |
| `ctrl_iso_tools.py` | `Shell` / `Write` / `Eval` schema 与执行；Write 用 `O_NOFOLLOW` |
| `ctrl_iso_loop.py` | 从 E3 `ctrl_loop.py` 复制内环，换工具与 jail；Eval 记 last write |
| `ctrl_iso_canary.py` | 生成/放置/扫描 canary |
| `selftest_ctrl_iso.py` | §9 |
| `run_e4.py` | `e4-iso-dev` / `e4-iso`；新 jsonl；dev 题 id 写进 manifest |

E3 的 `ctrl_loop.py` **冻结**。实现完成后给协议文件做内容 hash，QB+ 只在该 hash 冻结后跑。

---

## 15. CTRL-ISO-v2（控制流 / 语义实验；不覆盖 e4）

设计文档：`ctrl_iso_v2_from_cursor.md`。实现与 e4 并行，**不改** `ctrl_iso_loop.py` 的官方枪语义。

| 臂 | 内容 | CLI |
|----|------|-----|
| **CTRL-ISO-v2a** | A 官方枪:=`eval_completed`；B 禁 inspect（语义错）；E preflight；F 8 LLM + gating + forced submit | `e4-iso-v2a` / `e4-iso-v2a-qbplus` / `e4-iso-v2a-dev` |
| **CTRL-ISO-v2b** | v2a + `Write /tmp` + `RunTmp` + 自洽 endian hint | `e4-iso-v2b*` |

不变量：`official_attempts == eval_completed`。NoSubmit 空枪不再消耗官方预算。  
产物：`artifacts/e4_iso_v2a*_traces.jsonl`（及 summary / protocol.json）。  
自测：`python -m experiment6.run e4-iso-v2-selftest`。
