# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001"
files={}
files["08_EVIDENCE_REGISTER_ADDENDUM.md"]=r"""# 08 — 证据登记（E-10 追加）/ EVIDENCE REGISTER ADDENDUM

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md`。
> 每条证据给出：ID、类型、定位、原始输出、等级。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-10-01 | XREF | 客户端 `.text` 全节 | `0xA2660` 直接调用点 3 个：`0x3514F0`(call)、`0x352FA7`(jmp)、`0x352FB4`(jmp) | `_data/out_t01_xref.txt` | DIRECT |
| EV-10-02 | REFUTE | `E-09 01` | `0x352FA7/0x352FB4` 属 `0x352F80`，不是 `0x352E80` | `_data/out_t01_xref.txt` | DIRECT |
| EV-10-03 | DISPATCH | RVA `0x354100` | 9 项跳转表 `0x7547AC`，键 = `movzx [ebp+0xc]`，`cmp 8` | `_data/out_full_dispatch.txt` | DIRECT |
| EV-10-04 | DISPATCH | RVA `0x3547D0` | 读 1 字节键，排除 `0x09`/`0x0A`，循环调用 `0x354100` | `_output` t18 | DIRECT |
| EV-10-05 | CALLPATH | RVA `0x354697` (case 6) | 初始化 msg → 读 4 字节长度 → 读载荷 → `0x352F80` → `0xA2660` | `_data/out_t36_postconfig.txt` | DIRECT |
| EV-10-06 | CURSOR | RVA `0x352FA1` | `inc eax` / `mov [esi+0x1c],eax`：进 body reader 前 +1 字节 | `_data/out_t10` 系列 | DIRECT |
| EV-10-07 | SERVER | RVA `0xA07F8` | `WriteByte(4)`（`0x99551` → `0x994FC`，len=1） | `_data/out_t19_server_writer.txt` | DIRECT |
| EV-10-08 | SERVER | RVA `0x99551`/`0x99566` | WriteByte = `mov ecx,1`；WriteShort = `mov ecx,2` | `_data/out_t28_final_checks` | DIRECT |
| EV-10-09 | SERVER | RVA `0x9960A..0x99635` | `bitpos%8==0 ⇒ bitpos=used*8` 强制重同步 | `_data/out_c09.txt` | DIRECT |
| EV-10-10 | SERVER | RVA `0x9949B`/`0x99651` | `MSG_WriteData`/`WriteLenStr` 不更新 `[msg+0x10]` | `_data/out_c09.txt` | DIRECT |
| EV-10-11 | REFUTE | RVA `0xA2D91` | `0xA2DC1` 属独立入口 `0xA2D91`，不在 `0xA2660` 内 | `_data/out_full_a2660.txt` | DIRECT |
| EV-10-12 | CLIENT | RVA `0xA2660` | 读 count1(2B)、A1/A2/A3 后 @0xA2975 `ret`，无 0x06 读取 | `_data/out_full_a2660.txt` | DIRECT |
| EV-10-13 | CLIENT | RVA `0xA2480` | `push 0xA / 7 / 4` → 10/7/4 bit；n×12 bit | `_data/out_t35_readprims.txt` | DIRECT |
| EV-10-14 | CLIENT | RVA `0x1AC1D0` | `MSG_ReadData` 纯逐字节，无位逻辑 | `_data/out_t35_readprims.txt` | DIRECT |
| EV-10-15 | CLIENT | RVA `0x1AC670` | `MSG_ReadBits` 使用 `[msg+0x20]` bitpos，`and 7`/`sar 3` | `_data/out_t35_readprims.txt` | DIRECT |
| EV-10-16 | NULL | 四区域扫描 | `0x350000-0x360000`/`0xA2000-0xA3000` 无 `cmp == 4/6` 命中 | `_data/out_t28_final_checks` | DIRECT（否定） |
| EV-10-17 | BOUNDARY | RVA `0x352E80` | `0x352E80` 在 `0x352F2A` 前 `ret`，其后 `int3`；与 `0x352F80` 为不同函数 | `_data/out_t09` 系列 | DIRECT |
"""

files["09_HYPOTHESIS_LEDGER_ADDENDUM.md"]=r"""# 09 — 假设台账（E-10 追加）/ HYPOTHESIS LEDGER ADDENDUM

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\17_HYPOTHESIS_LEDGER.md`。

---

### H-E10-01：`0xA2660` 恰有 3 个直接调用点
- 类别：调用图
- 支持：指令级 3 + `E8/E9 rel32` 字节级 3 + 数据指针 0（EV-10-01）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：发现间接调度表项指向 `0x4A2660`
- 下一步：枚举 `.rdata` 中指向 `0x4A2660` 的表项（本轮数据指针扫描为 0）

### H-E10-02：E-09 把后两个调用点归到 `0x352E80` 是函数边界误判
- 类别：地址基准/函数边界
- 支持：`0x352E80` 于 `0x352F2A` ret 后为 int3；C2/C3 属 `0x352F80`（EV-10-02、EV-10-17）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：找到 `0x352F80` 与 `0x352E80` 为同一逻辑函数的证据
- 下一步：无

### H-E10-03：客户端存在外层消息枚举分派器 `0x354100`（9 项）
- 类别：协议分派
- 支持：`cmp eax,8` + `jmp [eax*4+0x7547AC]`；表项 9（EV-10-03）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：该跳转表运行时被重写
- 下一步：确认键的取值域

### H-E10-04：Configstring body 走 `0x354100` 的 case 6，而非 case 4
- 类别：协议分层
- 支持：case 6 → 读 4 字节长度 + 载荷 → `0x352F80` → `0xA2660`（EV-10-05）
- 反证：case 4 只读 1 字节并做 3-float 拷贝，与 Configstring 字段不符
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：发现 case 4 也进入 `0xA2660` 的路径
- 下一步：无

### H-E10-05：进入 `0xA2660` 前跳过的 1 字节就是外层 `0x04`
- 类别：**外层分派（待证）**
- 支持：`0x352FA1 inc / mov [esi+0x1c]` 恰好 +1；服务端 `WriteByte(4)` 为 1 字节（EV-10-06、EV-10-07）
- 反证：客户端**无** `cmp == 4`；分派键与 `0x04` 无常量比较（EV-10-16）
- 状态：**STRONG_INFERENCE**（不足以升 PROVEN）
- 可证伪：发现该字节能取非 4 值仍进入 `0xA2660`
- 下一步：定位 `0x3547D0` 键的生产者，或 case 6 键与 `0x04` 的常量比较

### H-E10-06：客户端读取 `0x06` 的路径位于 `0xA2660` 之外
- 类别：终止语义
- 支持：`0xA2660` 读完 A3 后 @0xA2975 直接 ret，无 0x06 读取（EV-10-12）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE（范围限定）**
- 可证伪：发现 `0xA2660` 内的间接读取
- 下一步：检查 `0xA2660` 返回后的调用链（`0x352FC0`/`0x3532F0`/`0x3537D0`）

### H-E10-07：客户端尚未定位 `0x06` 的 8bit/对齐/终止三项属性
- 类别：终止语义
- 支持：四区域 `cmp == 6` 命中 0（EV-10-16）；`0x3532F0` 检查的是 `0x81`
- 反证：无
- 状态：**BLOCKED**
- 可证伪：找到读取 1 字节并比较 6 的指令
- 下一步：G-06-1（见 `07_E10_VERDICT.md`）

### H-E10-08：`0xA2DC1` 不属于 `0xA2660`
- 类别：函数边界
- 支持：`0xA2D91 push ebp; mov ebp,esp` 为独立入口（EV-10-11）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：找到 `0xA2660` 落入 `0xA2D91` 的控制流
- 下一步：无
"""

files["10_CLAIM_EVIDENCE_DEPENDENCY_GRAPH_ADDENDUM.md"]=r"""# 10 — 结论—证据依赖图（E-10 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\21_CLAIM_EVIDENCE_GRAPH.md`。
> 规则：同一底层证据重复引用只算一个来源。

---

```
◆ C-10-01  0xA2660 有且仅有 3 个直接调用点
   └─✔ EV-10-01（指令级 3 / 字节级 3 / 数据指针 0）
        └─○ 线性扫描含重同步（t01_xref_scan.py）
        └─○ 数据指针全镜像扫描

◆ C-10-02  C2/C3 属 0x352F80，E-09 归属错误
   ├─✔ EV-10-02（调用点函数入口）
   └─✔ EV-10-17（0x352E80 于 0x352F2A ret 后 int3）

◆ C-10-03  客户端存在 9 项外层分派器 0x354100
   ├─✔ EV-10-03（cmp 8 + jmp [eax*4+0x7547AC]，表项 9）
   └─✔ EV-10-04（0x3547D0 读 1 字节键并循环调用）

◆ C-10-04  Configstring body 对应 case 6
   ├─✔ EV-10-05（case 6 → 4 字节长度 + 载荷 → 0x352F80 → 0xA2660）
   ├─✔ EV-10-13（0xA2480 的 10/7/4/12 bit）
   └─⚠ case 4 语义（1 字节 + 3-float）与 Configstring 字段不符（反证）

◆ C-10-05  Configstring body 字段顺序与服务端一致
   ├─✔ EV-10-13（客户端 A3 位宽）
   ├─✔ EV-10-14/15（客户端字节/位读取原语）
   └─✔ E-09 EV-08-01（服务端字段序）

◆ C-10-06  外层 0x04 分派 = 进入 0xA2660 前跳过 1 字节
   ├─✔ EV-10-06（+1 字节，DIRECT）
   ├─✔ EV-10-07/08（服务端 WriteByte(4) 为 1 字节，DIRECT）
   └─⚠ EV-10-16（无 `cmp == 4`）—— **依赖未满足，结论只能 STRONG_INFERENCE / BLOCKED**

◆ C-10-07  0x06 写入侧为 1 字节且位于 body 之后
   ├─✔ EV-10-08（WriteByte = 1 字节）
   └─✔ EV-10-09/10（位同步与 WriteData/WriteLenStr 行为）

◆ C-10-08  0x06 读取侧 8bit / 对齐 / 终止
   ├─✔ EV-10-12（0xA2660 内无 0x06 读取）
   └─⚠ EV-10-16（无 `cmp == 6`）—— **依赖未满足，三项全部 BLOCKED**

◆ C-10-09  count1 = 2 字节
   ├─✔ 客户端：`push 2` + `MSG_ReadData` + `movsx word`
   └─✔ 服务端：`WriteShort` 中 `mov ecx,2`
```

## 依赖缺口汇总

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| C-10-06 外层 `0x04` | 无 `cmp == 4`，键语义未定 | BLOCKED |
| C-10-08 `0x06` | 无客户端读取点 | BLOCKED |
"""

files["11_START_GATING_AUDIT_ADDENDUM.md"]=r"""# 11 — 开工准入审计（E-10 追加）/ START GATING AUDIT ADDENDUM

> 追加修订，不覆盖 `E-09 06_UPDATED_START_GATING_AUDIT.md`，也不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\22_SERVER_START_GATING_AUDIT.md`。

---

## 1. 判据状态变化（相对 E-09）

| # | 判据 | E-09 | E-10 | 变化依据 |
|---|---|---|---|---|
| G-10 | 客户端 body 字段消费顺序 | ✅ | ✅ | 维持 |
| G-11 | count1 宽度 | ✅ 2 字节 | ✅ 2 字节 | 维持 |
| G-12 | `0x06` 非字节对齐终止定位 | ⚠️ 部分 | ⚠️ 部分 | 客户端仍 BLOCKED |
| G-13 | 客户端 opcode 分派 | ❌ | ⚠️ **部分** | **新定位 9 项分派器 `0x354100` + 选择器 `0x3547D0`** |
| G-16 | 外层消息分派器（读 `0x04`/`0x06`） | ❌ | ⚠️ **部分** | 分派器定位；`0x04` 值比较与 `0x06` 读取仍缺 |

**E-09：通过 10 / 部分 2 / 未通过 4 → E-10：通过 10 / 部分 4 / 未通过 2。**

通过数保持不变；两项从"未通过"提升为"部分"：G-13、G-16。

## 2. 阻断项状态

| ID | E-09 | E-10 | 说明 |
|---|---|---|---|
| BLK-3c `0x06` 客户端读取 | 阻断 | **阻断（缺口缩小）** | 已排除 `0xA2660` 内部；最小证据 = `0xA2660` 返回后调用者的 1 字节常量比较 |
| BLK-7 外层消息分派器 | 阻断 | **部分解除** | 已定位 `0x354100`（9 项）+ `0x3547D0`；`0x04` 值级分派仍 BLOCKED |
| BLK-8 `0x06` 位流 vs 字节标记 | 阻断 | **阻断** | 服务端为 1 字节写；客户端对齐行为未知 |
| BLK-4/5/6 | 阻断 | 阻断 | 未变 |

## 3. 准入裁定

### 3.1 可继续（纯静态，无需授权）

| 工作 | 目标 | 依据 |
|---|---|---|
| A-10-1 | 定位 `0x3547D0` 键的生产者/取值域 | 解除外层 `0x04` 值级分派 |
| A-10-2 | 检查 `0xA2660` 返回后的 `0x352FC0`/`0x3532F0`/`0x3537D0` 调用链是否有 1 字节比较 | 解除 `0x06` 读取路径 |
| A-10-3 | 枚举 `.rdata`/`.data` 中指向 `0x4A2660` 的间接表项 | 排除间接调用点 |
| A-10-4 | 核对 case 6 键枚举（0..8）与 wire opcode 的常量映射 | 完成外层映射 |

### 3.2 仍不可宣称

- 不得宣称"外层 `0x04` 分派已证实"（仅强 INFERRED）。
- 不得宣称"`0x06` 读取路径/位宽/对齐/终止已证实"（全部 BLOCKED）。
- 不得宣称"整条 Configstring 消息互操作已证实"（外层框架未闭合）。
- 不得在无原始帧字节的情况下宣称字节级兼容。

### 3.3 裁定

**`CONDITIONAL GO（维持 E-09 放宽，但新增 4 项静态后续）`**

- 相对 E-09 的放宽**不变**：count1 = 2 字节；body 字段可按已证规格实现。
- 新增部分解除：外层分派器**已定位**（`0x354100` 9 项 + `0x3547D0`），但**分派键与 wire `0x04` 的常量映射未证**。
- 保留项：`0x06` 的读取/位宽/对齐/终止与整条消息互操作仍不得宣称完成。
"""

for name,content in files.items():
    with open(os.path.join(wd,name),"w",encoding="utf-8",newline="\n") as f:
        f.write(content)
print("wrote",len(files),"addenda")
