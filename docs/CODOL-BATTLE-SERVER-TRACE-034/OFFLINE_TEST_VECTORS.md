# OFFLINE_TEST_VECTORS — 离线测试向量

**原则（任务书 §6）：**
- 每项已确认协议规则尽可能对应 ≥1 个离线测试。
- 测试必须使用**明确记录来源**的样本或**合成数据**。
- **合成数据只能验证实现的内部一致性，不能单独证明与真实客户端兼容。**
- **本轮未执行任何真实客户端 E2E；不得声称 E2E 通过。**

---

## 1. 测试向量来源分类

| 类别 | 含义 | 本轮是否可用 |
|---|---|---|
| `TGT-CONFIRMED` | 断言直接来自本目标镜像的已证实事实（RVA + 字节） | **可用** |
| `TGT-INFERRED` | 断言来自本目标的推断（在报告中标 `INFERRED`） | 可用，但需标注为推断 |
| `SYNTH` | 完全合成，仅验证实现内部一致性 | 可用，**不得**作为兼容性证据 |
| `REF-OLD` | 来自冻结服务器/C-3333/2697 等旧协议材料 | **不可**作为目标断言 |
| `REAL-CAPTURE` | 真实目标版本抓包 | **本轮不存在** |

> 本轮**没有**任何 `REAL-CAPTURE`。因此**没有任何**测试可以宣称兼容性已被证明。

---

## 2. 可用向量（全部 `TGT-CONFIRMED` 或 `SYNTH`）

### TV-01 — OOB 状态门：允许值域

- **规则（`TGT-CONFIRMED`）**：`[0x76446B0] ∈ {3,4,5,6}` 才进入构造；否则 `0x1C0F1B` 直接返回。
- **证据**：`evidence\dis_oob_full.out.txt`（`0x1C0635`–`0x1C0647`）。
- **测试**：
  - `SYNTH` 输入 `state ∈ {0,1,2,7,0xFF}` → 期望**不产生**任何 OOB 输出。
  - `SYNTH` 输入 `state ∈ {3,4,5,6}` → 期望进入下一级门。
- **边界**：内部一致性；**不代表**真实客户端取值分布。

### TV-02 — 状态 → 命令映射

- **规则（`TGT-CONFIRMED`）**：
  - `state == 3` → `getchallenge 0 "%s"`（`push 0x00DBFD04` @ `0x1C071E`）
  - `state == 6` → `heartbeat`（`push 0x00DBFE40` @ `0x1C0EBB`）
- **证据**：`evidence\dis_oob_full.out.txt`。
- **测试**：
  - `SYNTH` `state=3` → 断言输出前缀恰为 `getchallenge 0 "`。
  - `SYNTH` `state=6` → 断言输出恰为 `heartbeat`（无参数）。
  - `state=4` / `state=5` → 断言**不**等于上述两者（已证字面量不同），并断言输出**非空**。
- **注意**：`state=4`/`state=5` 的**精确**文本本轮未证（仅知含 `%08x%08x` / `0xDBFE38` `stats` 族）。

### TV-03 — 节流门

- **规则（`TGT-CONFIRMED`）**：
  - 状态 3/4：`(now - [ebx+0x30]) >= 3000`（`cmp eax, 0xBB8`）
  - 状态 5：`(now - [ebx+8]) >= 100`（`cmp ecx, 0x64`）
  - 状态 6：`(now - [ebx+8]) >= 500`（`cmp ecx, 0x1F4`）
- **证据**：`evidence\dis_oob_full.out.txt`（`0x1C06B3`/`0x1C06C9`/`0x1C06D3`）。
- **测试**：
  - `SYNTH` `state=3, delta=2999` → 期望被抑制；`delta=3000` → 期望放行。
  - `SYNTH` `state=5, delta=99` → 抑制；`delta=100` → 放行。
  - `SYNTH` `state=6, delta=499` → 抑制；`delta=500` → 放行。

### TV-04 — 对象侧二级门

- **规则（`TGT-CONFIRMED`）**：`ecx != 0 && ebx != 0 && [ebx+0x100260] != 1`。
- **证据**：`evidence\dis_oob_full.out.txt`（`0x1C064D`–`0x1C065C`）。
- **测试**：
  - `SYNTH` `[ebx+0x100260] == 1` → 期望直接返回（不发包）。
  - `SYNTH` `ecx == 0` 或 `ebx == 0` → 期望直接返回。

### TV-05 — 挑战失败上报

- **规则（`TGT-CONFIRMED` 存在性）**：挑战校验失败路径引用 `EXE_CLIENTFAILEDTOCHALLENGE`。
- **证据**：`evidence\state_globals.out.txt`（字符串 VA `0x00DBB708`）；`evidence\dis_oob_full.out.txt`（`0x1C076A` `push 0xDBB708` + `push 2`）。
- **测试**：
  - `SYNTH` 构造"挑战不匹配"输入 → 断言实现走上报分支且错误码为 `EXE_CLIENTFAILEDTOCHALLENGE`（数值 `2`）。
- **注意**：挑战比较的**具体算法**本轮未证。

### TV-06 — 主机不可达上报

- **规则（`TGT-CONFIRMED` 存在性）**：`0x1C067A` 分支引用 `EXE_HOSTUNREACH`。
- **证据**：`evidence\dis_oob_full.out.txt`（`0x1C0687` `push 0xDB45C4`）；`evidence\state_globals.out.txt`。
- **测试**：`SYNTH` 模拟 `0x1BE700` 返回 0 → 断言上报 `EXE_HOSTUNREACH`。

### TV-07 — `challengeResponse` / `connectResponse` 文本形态

- **规则（`TGT-CONFIRMED` 字面量）**：响应文本为 `challengeResponse` / `connectResponse`（无参数、`mov edx, imm32` 装载）。
- **证据**：`evidence\locate_local_battle_entries.out.txt`。
- **测试**：
  - `SYNTH` 生成响应 → 断言字符串恰为这两个之一（区分大小写，无尾随空格）。
  - `SYNTH` 断言 `connectResponse` ≠ `challengeResponse`（前缀区分）。
- **注意**：本轮**未证**客户端是否用它们做**比较**；该断言只验证服务端输出形态。

### TV-08 — 增量类型索引表边界（表 A）

- **规则（`TGT-CONFIRMED` 结构）**：索引 `> 0x139` → 拒绝（`ja`）；默认项 `0x50`；共 314 项。
- **证据**：`evidence\dump_typetables.out.txt`。
- **测试**：
  - `SYNTH` `idx = 0x139` → 断言映射到表 A 的某一分支（非越界）。
  - `SYNTH` `idx = 0x13A` → 断言越界拒绝。
  - `SYNTH` 遍历 `0..0x139` → 断言**恰好 223** 项映射到 `0x50`，且处理分支编号 ∈ `0..0x50`。

### TV-09 — 增量类型索引表边界（表 B）

- **规则（`TGT-CONFIRMED` 结构）**：索引 `> 0x87` → 拒绝；默认项 `0x15`；共 136 项。
- **证据**：`evidence\dump_typetables.out.txt`。
- **测试**：
  - `SYNTH` `idx = 0x87` → 合法；`idx = 0x88` → 越界拒绝。
  - `SYNTH` 遍历 `0..0x87` → 断言**恰好 115** 项映射到 `0x15`，处理分支编号 ∈ `0..0x15`。

### TV-10 — configstring 禁用字节规则**不**存在

- **规则（`TGT-CONFIRMED` 否定）**：目标 configstring 区间（`0x6D870..0x6E100`）**没有** `cmp …,0x25` / `cmp …,0x92`。
- **证据**：`evidence\check_forbidden_bytes.out.txt`。
- **测试**：
  - `SYNTH` 构造含 `0x25` 与 `0x92` 的 configstring → **期望实现不拒绝**（与冻结服务器行为相反）。
  - 该测试的作用是**防止错误移植**服务器侧约束。

---

## 3. 不能作为目标断言使用的向量（登记以显式排除）

| 项 | 来源 | 为何不能用 |
|---|---|---|
| `MotionSnapshot.BuildCore` 的 `ack+0x00+serverTime+first{0,8}/{1,4}` | 冻结服务器 / C-3333 | 无目标证据（`REF-OLD`） |
| `ExpectedIndexOrder` 29 项字段序 | 冻结服务器 / C-3333 | 无目标证据（`REF-OLD`） |
| configstring index-skip（1bit / 1bit+13bit）与上界 `0x1DD6` | 冻结服务器 2697 | 无目标证据（`REF-OLD`） |
| `BuildGameState(version, map, field4, fieldC, field8, …)` | 2697 服务端 RVA | 属另一版本（`REF-OLD`） |
| netchan 6B 头 + 6B 分片描述 | 冻结服务器 2697 | 无目标证据（`REF-OLD`） |
| `sv_client_mp.cpp` 的 `ClientState` 枚举 | 同构建**服务端**源码 | 与客户端状态空间不同（`REF-OLD`） |

---

## 4. 覆盖矩阵

| 任务书要求的测试类型 | 本轮可用的向量 | 状态 |
|---|---|---|
| 正常消息 | TV-02（state 3/6 正常构造） | **可写（内部一致性）** |
| 截断消息 | — | **不可**（帧边界 `UNKNOWN`） |
| 非法长度 | — | **不可**（帧边界 `UNKNOWN`） |
| 序号 / 确认状态异常 | — | **不可**（序号消费路径 `UNKNOWN`） |
| 不存在的 delta baseline | — | **不可**（基线机制 `UNKNOWN`） |
| 实体新增/更新/删除 | — | **不可**（实体编码 `UNKNOWN`） |
| 初始化状态不匹配 | TV-01 / TV-04（状态门拒绝） | **可写（内部一致性）** |

**结论：** 7 类要求中 **3 类**（正常消息、初始化状态不匹配，及"命令映射"）可用本轮已证事实构造离线向量；
其余 **4 类**因目标证据不足**不得**构造。

---

## 5. 执行状态

| 项 | 状态 |
|---|---|
| 本轮是否实现并运行上述向量 | **未执行**（`NOT_RUN`） |
| 原因 | 本任务为**只读静态追踪**；任务书 §6 要求"不得声称真实客户端 E2E 已通过"——本轮亦**未**运行任何 E2E |
| 后续 | 上述 TV-01..TV-10 可直接在独立任务中编码为单元测试（不需要 snapshot、启动链或大厅匹配） |

> **纪律：** 本文件是**向量设计**，不是**测试结果**。未执行的项一律标 `NOT_RUN`。
