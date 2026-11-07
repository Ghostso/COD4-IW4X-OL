# -*- coding: utf-8 -*-
import os,hashlib
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001"
F={}
F["08_EVIDENCE_REGISTER_ADDENDUM.md"]=r"""# 08 — 证据登记（E-12 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md` 及 E-10/E-11 的同名追加文件。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-12-01 | IMPORT | PE 导入表 | 网络锚点：`recv` IAT `0xBAE490`、`recvfrom` `0xBAE50C`、`send` `0xBAE4C8`、`sendto` `0xBAE504`、`select` `0xBAE4D8`；文件锚点 `ReadFile` `0xBAE22C`、`CreateFileA` `0xBAE1E4` | `_tools/t21_imports.py` | PROVEN |
| EV-12-02 | CALLSITE | 收包调用点 | `recvfrom`×3（`0x1B0BA1`/`0x6B4E3C`/`0x775ADE`）；`recv`×6（`0x602441`/`0x6029BE`/`0x6052AB`/`0x775A6C`/`0x784F7D`/`0x788133`） | `_data/out_iat_callers.txt` | PROVEN |
| EV-12-03 | STRUCT | `[0x743DE9C]+0x8048` | 3 MB 应用层环形缓冲；`+0x30AF2C`=写游标、`+0x30AF30`=读游标 | `_data/out_t12_buffer2` | PROVEN |
| EV-12-04 | PRIMITIVE | `0x3524F0` | **写侧**：`memcpy(ring+write, src, len)` @`0x352559`，容量 `0x300000` | `_data/out_t14_3524f0` | PROVEN |
| EV-12-05 | PRIMITIVE | `0x352570` | **读侧**：`memcpy(dst, ring+read, len)` @`0x3525D9`，返回 `len` | `_data/out_t14_3524f0` | PROVEN |
| EV-12-06 | POINTER | `[client+0x89244]` | 读取器指针仅 3 处写入：`0x35141E`→`0x752570`；`0x3515D9`/`0x356701`→`0x74F090` | `_data/out_t27_verify.txt` | PROVEN |
| EV-12-07 | CMDREG | `0x34E1B0` | `mov [0xDD4BF44],0x74E7C0` + `call 0x59DCA0`；命令名 `0xCD61D8`=`cl_demo_jumptostart` | `_data/out_34df80_reg.txt`、`_data/out_t37_names.txt` | PROVEN |
| EV-12-08 | STRING | `0xCD61B4`/`0xCD61C4`/`0xCD61D8`/`0xCD61EC` | `cl_demo_play`/`cl_demo_timedemo`/`cl_demo_jumptostart`/`cl_demo_keyboard` | `_data/out_t37_names.txt` | PROVEN |
| EV-12-09 | STATE | `0x8F1D0` | `cmp [0x1BBBCFC],7` / `jl` 返回；`cmp eax,7` / `cmp eax,9` / `jge`；仅状态∈[7,9) 调 `0x350170` | `_data/out_gsupdate_callers.txt` | PROVEN |
| EV-12-10 | STATEVAR | `0x1BBBCFC` | demo/回放状态机（0–10），全镜像 166 处引用 | `_data/out_state_var.txt` | PROVEN |
| EV-12-11 | STRING | `0xCD6384` | `EXE_ERR_PROCESS_DEMO_FILE_FAILED`（辅助证据，非单独依据） | `_data/out_t10_batch2` | PROVEN |
| EV-12-12 | CONFLICT | `0x34FD80(1)` vs `0xA21B8` | 客户端字段序 `{i32,i32,u32 len,payload}`；服务端 `{i32,cstr,cstr,i32,<cfgsub>,i32,i32,0x06}` → 第 2 字段即冲突 | `_data/out_34FD80.txt`、`_data/out_server_gamestate.txt` | REFUTED（匹配） |
| EV-12-13 | NULL | 收包函数 8 层下游 | 未到达 `0x350170`/`0x3547D0`/`0x354100`/`0xA2660`/`0x34FD80` | `_tools/t23_recvchain.py` | 未发现（不升级） |
| EV-12-14 | NULL | `0xA2E50` | 直接调用者 0；数据指针引用 0 | `_data/out_t10_batch2` | 未发现（不升级） |
| EV-12-15 | BITWIDTH | 客户端 `0xA2765` | A2 段计数读取 `push 0xB`（11 bit）；服务端历史记录为 10 bit | `_data/out_t32_pushes.txt` | BLOCKED（服务端未复核） |
| EV-12-16 | BFS | `0x350170` 反向 4 层 | 上游收敛为 9 个函数（depth1: `0x8F1D0`,`0x3512A0`；depth2: `0x9CFE0`,`0x34E7C0`,`0x3519F0`,`0x351A10`,`0x356580`；depth3/4: `0x1A9060`,`0x1A9760`） | `_data/out_bfs_up.txt` | PROVEN |
"""

F["09_HYPOTHESIS_LEDGER_ADDENDUM.md"]=r"""# 09 — 假设台账（E-12 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\17_HYPOTHESIS_LEDGER.md` 及 E-10/E-11 的同名追加。

---

### H-E12-01：`0x350170` 属于 demo/回放路径
- 类别：路径归属
- 支持：`0x34E7C0` = `cl_demo_jumptostart` 回调（EV-12-07/08）；`0x8F1D0` demo 状态门（EV-12-09/10）；demo 读取器安装（EV-12-06）；demo 错误码（EV-12-11）
- 反证：未发现实时上游；但未穷尽间接分派
- 状态：**STRONG_INFERENCE**（未达 CONFIRMED）
- 可证伪：发现实时路径以相同状态值调用 `0x8F1D0`
- 下一步：枚举 `0x1BBBCFC` 写入点，确认状态 7/8/9 仅由 demo 控制流设置

### H-E12-02：`0x34E7C0` 是 `cl_demo_jumptostart` 命令回调
- 类别：命令注册
- 支持：`0x34E19B mov [0xDD4BF44],0x74E7C0` + `0x34E1B0 call 0x59DCA0`；命令名 `0xCD61D8`（EV-12-07/08）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E12-03：`0x3524F0`/`0x352570` 是环形缓冲写/读原语
- 类别：数据结构
- 支持：`+0x30AF2C`/`+0x30AF30` 双游标；`memcpy` 方向相反；容量 `0x300000`（EV-12-03/04/05）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E12-04：实时网络收包点已定位，但到环形缓冲写侧的边未证
- 类别：**实时链（待证）**
- 支持：IAT 锚点 + 9 个收包函数（EV-12-01/02）
- 反证：8 层 BFS 未命中写侧（EV-12-13，负搜索）
- 状态：**BLOCKED**
- 可证伪：在收包函数内找到对 `[0x743DE9C]`/`+0x30AF2C` 的访问
- 下一步：BLK-12-1

### H-E12-05：实时 Gamestate `0x03` 消费者未定位
- 类别：**实时链（待证）**
- 支持：唯一已定位的 `0x03` 处理点 `0x34FD80(1)` 归属 demo
- 反证：`0x34FD80(1)` 字段序与服务端冲突（EV-12-12，REFUTED）
- 状态：**BLOCKED**
- 可证伪：定位读 `{i32,cstring,cstring,i32}` 的客户端函数
- 下一步：BLK-12-2

### H-E12-06：`0x34FD80(1)` 不是服务端 `0xA21B8` 的消费者
- 类别：字段匹配
- 支持：客户端 `{i32,i32,u32 len,payload}` vs 服务端 `{i32,cstr,cstr,i32,...}`，第 2 字段冲突（EV-12-12）
- 反证：无
- 状态：**REFUTED**（该匹配主张）
- 下一步：无

### H-E12-07：`0xA2660` 的“实时”归属未证
- 类别：路径归属
- 支持：3 个调用点（`0x3512A0`、`0x352F80`×2）均无实时上游
- 反证：字段级行为 PROVEN（不构成路径归属）
- 状态：**BLOCKED**
- 下一步：BLK-12-6

### H-E12-08：客户端 A2 计数读取为 11 bit
- 类别：位宽
- 支持：`0xA2765 push 0xB`（EV-12-15，DIRECT）
- 反证：服务端历史记录为 10 bit（本轮未逐指令复核）
- 状态：**BLOCKED**（差异保留）
- 下一步：BLK-12-5
"""

F["10_CLAIM_EVIDENCE_DEPENDENCY_GRAPH_ADDENDUM.md"]=r"""# 10 — 结论—证据依赖图（E-12 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\21_CLAIM_EVIDENCE_GRAPH.md` 及 E-10/E-11 的同名追加。

---

```
◆ C-12-01  实时网络底锚与收包点已定位
   ├─✔ EV-12-01（IAT 锚点：recv/recvfrom/send/sendto/ReadFile）
   └─✔ EV-12-02（9 个收包函数）

◆ C-12-02  应用层 3MB 环形缓冲与读写原语
   ├─✔ EV-12-03（+0x8048 / +0x30AF2C / +0x30AF30）
   ├─✔ EV-12-04（写侧 0x3524F0）
   └─✔ EV-12-05（读侧 0x352570）

◆ C-12-03  收包函数 → 环形缓冲写侧
   ├─✔ EV-12-01/02（收包点）
   └─⚠ EV-12-13（8 层未命中）—— **依赖未满足 → BLOCKED**

◆ C-12-04  0x34E7C0 = cl_demo_jumptostart 回调
   ├─✔ EV-12-07（注册指令）
   └─✔ EV-12-08（命令名 0xCD61D8）

◆ C-12-05  0x350170 归属 demo
   ├─✔ EV-12-07/08（命令回调）
   ├─✔ EV-12-09（demo 状态门 ∈[7,9)）
   ├─✔ EV-12-10（状态机 0x1BBBCFC）
   ├─✔ EV-12-06（demo 读取器安装）
   └─⚠ 未穷尽间接分派 —— **STRONG_INFERENCE，未达 PROVEN**

◆ C-12-06  0x34FD80(1) ≠ 服务端 0xA21B8
   └─✔ EV-12-12（第 2 字段 i32 vs cstring 冲突）

◆ C-12-07  实时 0x03 消费者
   ├─✔ EV-12-12（demo 消费者字段冲突）
   ├─✔ EV-12-14（0xA2E50 无调用者/无指针）
   └─⚠ EV-12-13（实时链中断）—— **依赖未满足 → BLOCKED**

◆ C-12-08  0xA2660 实时归属
   ├─✔ E-11 EV-11-05/06（字段级 PROVEN）
   └─⚠ 3 个调用点均无实时上游 —— **依赖未满足 → BLOCKED**

◆ C-12-09  A2 计数字宽
   ├─✔ EV-12-15（客户端 11 bit，DIRECT）
   └─⚠ 服务端未复核 —— **BLOCKED**
```

## 依赖缺口汇总

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| C-12-03 收包→环形缓冲 | 8 层无调用边 | BLOCKED |
| C-12-05 `0x350170` demo | 未穷尽间接分派 | INFERRED（强） |
| C-12-07 实时 `0x03` | 实时链中断 | BLOCKED |
| C-12-08 `0xA2660` 实时 | 无实时上游 | BLOCKED |
| C-12-09 A2 计数 | 服务端未复核 | BLOCKED |
"""

F["11_START_GATING_AUDIT_ADDENDUM.md"]=r"""# 11 — 开工准入审计（E-12 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\22_SERVER_START_GATING_AUDIT.md` 及 E-09/E-10/E-11 的对应审计。

---

## 1. 判据状态变化（相对 E-11）

| # | 判据 | E-11 | E-12 | 依据 |
|---|---|---|---|---|
| G-13 | 客户端 opcode 分派 | ✅ 顶层 `0x350170` | ⚠️ **降级为 demo 归属** | `0x34E7C0`=`cl_demo_jumptostart` |
| G-16 | 外层消息分派器 | ⚠️ 部分 | ⚠️ 部分 | 分层已澄清；实时层未定位 |
| G-17 | `0x03` 客户端消费者字段匹配 | ❌ | ❌ | `0x34FD80(1)` 字段序冲突 |
| G-18 | 子帧循环退出语义 | ✅ | ✅ | 维持 |
| **G-19（新）** | 实时网络底锚（IAT + 收包点） | — | ✅ | EV-12-01/02 |
| **G-20（新）** | 应用层环形缓冲读写原语 | — | ✅ | EV-12-03/04/05 |
| **G-21（新）** | 收包 → 环形缓冲调用边 | — | ❌ | EV-12-13 |

**E-11：通过 12 / 部分 3 / 未通过 3 → E-12：通过 13 / 部分 4 / 未通过 4。**

（G-19/G-20 通过；G-21 未通过；G-13 从“通过”降为“部分”——其顶层分派器归属 demo。）

## 2. 阻断项状态

| ID | E-11 | E-12 | 说明 |
|---|---|---|---|
| BLK-3c `0x06` 客户端读取 | 阻断 | **阻断** | 未新增读取证据 |
| BLK-7 外层消息分派器 | 部分解除 | **部分解除（重定性）** | `0x350170` 归属 demo，不再是实时候选 |
| BLK-8 `0x06` 位流 vs 字节标记 | 阻断 | **阻断** | 未变 |
| BLK-9 `0x03` 客户端消费者 | 阻断 | **阻断（确认冲突）** | `0x34FD80(1)` REFUTED |
| **BLK-12-1（新）** | — | **阻断** | 收包函数 → 环形缓冲写侧调用边缺失 |
| **BLK-12-2（新）** | — | **阻断** | 实时 `0x03` 消费者未定位 |
| **BLK-12-5（新）** | — | **阻断** | A2 计数字宽服务端未复核 |

## 3. 准入裁定

### 3.1 可继续（纯静态，无需授权）

| 工作 | 目标 | 依据 |
|---|---|---|
| A-12-1 | 在 9 个收包函数内查找对 `[0x743DE9C]`/`+0x30AF2C` 的访问 | 解除 BLK-12-1 |
| A-12-2 | 枚举 `0x1BBBCFC` 写入点，确认状态 7/8/9 仅由 demo 控制流设置 | 将 `0x350170` 归属升为 PROVEN 或推翻 |
| A-12-3 | 在服务端 `0xA0468` 内逐指令定位 A2 计数位宽 | 解除 BLK-12-5 |
| A-12-4 | 在收包函数下游查找读 `{i32,cstring,cstring,i32}` 的函数 | 解除 BLK-12-2 |

### 3.2 仍不可宣称

- 不得宣称实时 Gamestate 消费路径已定位。
- 不得宣称 `0x350170` 属实时网络路径。
- 不得宣称 `0xA2660` 是实时 Configstring body reader。
- 不得宣称服务端 `0xA21B8` 与客户端实时路径字段级匹配。
- 不得在 BLK-12-1/2/4 解除前宣称互操作性。

### 3.3 裁定

**`CONDITIONAL GO（维持放宽；实时链整体 BLOCKED）`**

- 相对 E-11 的**放宽不变**：count1 = 2 字节；body 字段可按已证规格实现（离线自测）。
- **新增重要更正**：E-11 的顶层分派器 `0x350170` 归属 demo，**不再是实时候选**。
- **新增阻断**：实时链在“收包函数 → 环形缓冲写侧”处中断（BLK-12-1），下游全为 BLOCKED。
- 服务器 Gamestate 编码器可实现“服务端自洽”版本，但**不可**声称客户端可验证。
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
