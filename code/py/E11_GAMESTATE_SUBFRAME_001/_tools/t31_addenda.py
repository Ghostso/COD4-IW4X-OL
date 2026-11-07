# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001"
F={}
F["08_EVIDENCE_REGISTER_ADDENDUM.md"]=r"""# 08 — 证据登记（E-11 追加）/ EVIDENCE REGISTER ADDENDUM

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md` 与 E-10 的 `08_EVIDENCE_REGISTER_ADDENDUM.md`。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-11-01 | DISPATCH | 客户端 `0x350170` | 顶层分派器：读 1 字节 opcode，`dec eax`，`cmp eax,3`，`jmp [eax*4+0x75025C]` | `_data/out_top_dispatch.txt` | DIRECT |
| EV-11-02 | TABLE | `0x75025C` | 4 项：1→`0x350040`，2→`0x34FD80(0)`，3→`0x34FD80(1)`，4→`0x3547D0` | `_data/out_top_dispatch.txt` | DIRECT |
| EV-11-03 | SUBFRAME | `0x354100` | 子帧分派器：`movzx [ebp+0xc]`，`cmp 8`，`jmp [eax*4+0x7547AC]` | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-04 | LOOP | `0x3547D0` | 读 1 字节；`cmp al,9`/`cmp al,0xA` 退出；否则调 `0x354100` | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-05 | CASE6 | `0x354697` | `memset 256KB` → `MSG_InitReadOnly` → 读 4 字节 LEN → 读 LEN 字节 → `0x352F80` | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-06 | CURSOR | `0x352FA1` | `inc eax; mov [esi+0x1C],eax`：进 body reader 前 +1 字节 | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-07 | READER | `[client+0x89244]` | 可插拔读函数指针：`0x35141E`→`0x752570`；`0x3515D9`/`0x356701`→`0x74F090` | `_data/out_3512a0_precise.txt` | DIRECT |
| EV-11-08 | SERVER | `0xA07F8` | `WriteByte(4)`，唯一调用者 `0xA22C1`（`WriteConfigstrings`） | `_data/out_srv_writer_and_prims.txt` | DIRECT |
| EV-11-09 | SERVER | `0xA0997`/`0xA22F8`/`0xA4CAF` | 三个 `WriteByte(6)`，层级不同 | `_data/out_srv_writebyte.txt` | DIRECT |
| EV-11-10 | SERVER | `0x99551` | `mov ecx,1` → `0x994FC` → `MSG_WriteData(len=1)` | `_data/out_srv_writer_and_prims.txt` | DIRECT |
| EV-11-11 | CONFLICT | `0xA21B8` vs `0x34FD80` | 服务端 `0x03` 体为 `{i32,cstr,cstr,i32,...}`；客户端 `0x34FD80` 为 `{i32,i32,u32 len,payload}`，字段序不匹配 | `_data/out_34FD80.txt` | DIRECT |
| EV-11-12 | REFUTE | E-10 `01` | E-10 字符串探测误传 VA 给 `bytes_rva`；E-11 用 `VA-ImageBase` 修正 | `_data/out_t03_xrefs.txt` | DIRECT |
| EV-11-13 | CLIENT | `0xA2660` | 进入后 `lea edi,[eax+2]` + `push 2` + `MSG_ReadData`：首字段 2 字节 | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-14 | NULL | `0x350000-0x360000`/`0xA0000-0xA3000` | `cmp/sub == 4` 无消息读取比较；`cmp/sub == 6` 无字节流比较 | `_data/out_cmp4.txt`、`_data/out_cmp_scan.txt` | DIRECT（否定） |
| EV-11-15 | STRUCT | `0x1AC670` | 客户端 `MSG_ReadBits` 用 `[msg+0x20]` 作 bitpos；服务端用 `[msg+0x10]` | `_data/out_srv_writer_and_prims.txt` | DIRECT |
"""

F["09_HYPOTHESIS_LEDGER_ADDENDUM.md"]=r"""# 09 — 假设台账（E-11 追加）/ HYPOTHESIS LEDGER ADDENDUM

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\17_HYPOTHESIS_LEDGER.md` 与 E-10 的 `09_...`。

---

### H-E11-01：客户端顶层消息分派器是 `0x350170`（4 项表）
- 类别：协议分派
- 支持：`movzx al` → `dec eax` → `cmp eax,3` → `jmp [eax*4+0x75025C]`；表项 4 个（EV-11-01/02）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：跳转表运行时被重写
- 下一步：无

### H-E11-02：`0x354100` 是子帧分派器，不是顶层分派器
- 类别：协议分层
- 支持：唯一调用者 `0x3547D0`（EV-11-03/04）；顶层表已由 EV-11-02 确定
- 反证：E-10 曾称其为外层分派器，但未提供跳转表证据
- 状态：**CONFIRMED_BY_EVIDENCE**（更正 E-10）
- 下一步：无

### H-E11-03：子帧循环退出由 `0x09`/`0x0A` 决定，与 `0x04`/`0x06` 无关
- 类别：循环语义
- 支持：`0x3547FD cmp al,9`、`0x354801 cmp al,0xA`（EV-11-04）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E11-04：case 6 = `u32 LEN` + `LEN` 字节载荷
- 类别：字段格式
- 支持：`0x3546D4` 读 4 字节 → `0x3546EE` 以该值为长度读载荷（EV-11-05）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**（更正 E-10 "4+4 字节"）
- 下一步：确认 `LEN` 写入者

### H-E11-05：`0x352F80` 固定 +1 字节后才进 body reader
- 类别：游标
- 支持：`0x352FA1 inc eax` / `0x352FA2 mov [esi+0x1C],eax`（EV-11-06）
- 反证：无（越界分支同样 +1）
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E11-06：被跳过的 1 字节就是服务端 `0x04`
- 类别：**内部子帧识别（待证）**
- 支持：位置一致（服务端 `0xA07F8` 紧接 `WriteInt32(field4)` 之后为 1 字节）（EV-11-08/06）
- 反证：客户端**无** `cmp == 4`（EV-11-14）；`0x352F80` 无条件 +1，不校验值
- 状态：**STRONG_INFERENCE**（不足以升 PROVEN）
- 可证伪：发现该字节能取非 4 值仍进入 `0xA2660`
- 下一步：G-11-2

### H-E11-07：`0x03` 的客户端消费者尚未定位
- 类别：**Gamestate 消费（待证）**
- 支持：顶层分派器 `0x03→0x34FD80(1)`（EV-11-02），但字段序与服务端 `0xA21B8` 不匹配（EV-11-11）
- 反证：`0x34FD80` 为长度前缀分片消费者
- 状态：**BLOCKED**
- 可证伪：找到读 `{i32,cstring,cstring,i32}` 的客户端函数
- 下一步：G-11-1

### H-E11-08：客户端 MSG 结构与服务端 msg 结构不同
- 类别：内存布局
- 支持：客户端 `MSG_ReadBits` 用 `[msg+0x20]` bitpos；服务端 `MSG_WriteBits` 用 `[msg+0x10]`（EV-11-15）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E11-09：`0x06` 的客户端读取点未定位
- 类别：终止语义
- 支持：`0xA2660` 读完 A3 后 `ret`；四区域无字节流 `cmp == 6`（EV-11-14）
- 反证：无
- 状态：**BLOCKED**（按约束 6 不宣称不存在）
- 下一步：G-11-4
"""

F["10_CLAIM_EVIDENCE_DEPENDENCY_GRAPH_ADDENDUM.md"]=r"""# 10 — 结论—证据依赖图（E-11 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\21_CLAIM_EVIDENCE_GRAPH.md` 与 E-10 的 `10_...`。

---

```
◆ C-11-01  客户端顶层消息分派器 = 0x350170（4 项表）
   ├─✔ EV-11-01（dec eax / cmp eax,3 / jmp [eax*4+0x75025C]）
   └─✔ EV-11-02（表项 4 个：1/2/3/4）

◆ C-11-02  0x354100 是子帧分派器（9 项），不是顶层分派器
   ├─✔ EV-11-03（cmp 8 + jmp [eax*4+0x7547AC]）
   ├─✔ EV-11-04（唯一调用者 0x3547D0）
   └─✔ EV-11-02（顶层表已由 0x350170 给出）

◆ C-11-03  子帧循环退出由 0x09/0x0A 决定
   └─✔ EV-11-04（cmp al,9 / cmp al,0xA）

◆ C-11-04  case 6 = u32 LEN + LEN 字节载荷 → 0x352F80 → 0xA2660
   ├─✔ EV-11-05（0x3546D4 / 0x3546EE / 0x3546F3）
   └─✔ EV-11-06（0x352FA1 +1 字节）

◆ C-11-05  Configstring body 字段序两侧一致
   ├─✔ EV-11-13（客户端首字段 2 字节）
   ├─✔ EV-11-08（服务端 WriteByte(4) + WriteShort(count1)）
   └─✔ E-10 EV-10-13（A3 的 10/7/4/12 bit）

◆ C-11-06  被跳过的 1 字节 = 服务端 0x04
   ├─✔ EV-11-06（+1 字节，DIRECT）
   ├─✔ EV-11-08（服务端 1 字节写，DIRECT）
   └─⚠ EV-11-14（无 cmp == 4）—— **依赖未满足 → STRONG_INFERENCE / BLOCKED**

◆ C-11-07  0x03 的客户端消费者字段序匹配
   ├─✔ EV-11-02（0x03 → 0x34FD80(1)）
   └─⚠ EV-11-11（字段序与服务端 0xA21B8 不匹配）—— **依赖未满足 → BLOCKED**

◆ C-11-08  0x06 读取/对齐/终止
   ├─✔ EV-11-09（服务端三处写入，层级不同）
   ├─✔ EV-11-10（WriteByte = 1 字节）
   └─⚠ EV-11-14（无字节流 cmp == 6）—— **依赖未满足 → BLOCKED**

◆ C-11-09  客户端与服务端 MSG 结构布局不同
   └─✔ EV-11-15（bitpos 偏移 +0x20 vs +0x10）
```

## 依赖缺口汇总

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| C-11-06 内部 `0x04` 识别 | 无值比较 | INFERRED（不升级） |
| C-11-07 `0x03` 消费 | 字段序不匹配 | BLOCKED |
| C-11-08 `0x06` | 无客户端读取点 | BLOCKED |
"""

F["11_START_GATING_AUDIT_ADDENDUM.md"]=r"""# 11 — 开工准入审计（E-11 追加）/ START GATING AUDIT ADDENDUM

> 追加修订，不覆盖 E-09/E-10 的对应审计，也不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\22_SERVER_START_GATING_AUDIT.md`。

---

## 1. 判据状态变化（相对 E-10）

| # | 判据 | E-10 | E-11 | 依据 |
|---|---|---|---|---|
| G-13 | 客户端 opcode 分派 | ⚠️ 部分 | ✅ **顶层分派器 PROVEN** | `0x350170` + 表 `0x75025C` |
| G-16 | 外层消息分派器 | ⚠️ 部分 | ⚠️ 部分（分层已澄清） | `0x04` 是子帧头；顶层域 1..4 |
| G-10 | 客户端 body 字段消费顺序 | ✅ | ✅ | 维持 |
| G-11 | count1 宽度 | ✅ 2 字节 | ✅ 2 字节 | 维持 |
| G-12 | `0x06` 终止定位 | ⚠️ 部分 | ⚠️ 部分（客户端仍缺） | 无新读取证据 |
| **G-17（新）** | `0x03` 客户端消费者字段匹配 | — | ❌ | `0x34FD80` 字段序不匹配 |
| **G-18（新）** | 子帧循环退出语义 | — | ✅ | `0x3547D0` 用 0x09/0x0A |

**E-10：通过 10 / 部分 4 / 未通过 2 → E-11：通过 12 / 部分 3 / 未通过 3。**

（G-13 转为通过；新增 G-17 未通过、G-18 通过。）

## 2. 阻断项状态

| ID | E-10 | E-11 | 说明 |
|---|---|---|---|
| BLK-3c `0x06` 客户端读取 | 阻断（缺口缩小） | **阻断** | 已排除 `0xA2660` 内部与子帧循环；最小证据 = 读取+比较 6 的指令 |
| BLK-7 外层消息分派器 | 部分解除 | **进一步解除** | 顶层 `0x350170`（1..4）+ 子帧 `0x354100`（0..8）均已定位 |
| BLK-8 `0x06` 位流 vs 字节标记 | 阻断 | **阻断** | 服务端 1 字节；客户端未知 |
| **BLK-9（新）** | — | **阻断** | `0x03` 客户端消费者字段序不匹配（G-17） |
| BLK-4/5/6 | 阻断 | 阻断 | 未变 |

## 3. 准入裁定

### 3.1 可继续（纯静态，无需授权）

| 工作 | 目标 | 依据 |
|---|---|---|
| A-11-1 | 定位读 `{i32,cstring,cstring,i32}` 的客户端函数 | 解除 BLK-9 |
| A-11-2 | 定位 case 6 `LEN` 的写入者 | 解除 `0x04`/`0x06` 分片假设 |
| A-11-3 | 在 case 6 后继链中继续搜索 1 字节常量比较 | 解除 BLK-3c |
| A-11-4 | 核对 `0x352570` 与 `0x34F090` 的字节语义差异 | 确认网络/回放路径分离 |

### 3.2 仍不可宣称

- 不得宣称内部 `0x04` 已值级识别（仅 STRONG_INFERENCE）。
- 不得宣称 `0x06` 读取/对齐/终止已证实。
- 不得宣称 `0x03` 客户端消费路径已闭合（字段序不匹配）。
- 不得宣称整条 Configstring 消息互操作已证实。
- 不得在无原始帧字节时宣称字节级兼容。

### 3.3 裁定

**`CONDITIONAL GO（维持放宽；新增 1 项阻断 BLK-9）`**

- 相对 E-10 的放宽**不变**：count1 = 2 字节；body 字段可按已证规格实现。
- 新增部分解除：顶层与子帧两级分派器均已定位。
- 新增阻断：`0x03` 客户端消费者字段序不匹配，需按 A-11-1 继续静态定位。
"""

for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
