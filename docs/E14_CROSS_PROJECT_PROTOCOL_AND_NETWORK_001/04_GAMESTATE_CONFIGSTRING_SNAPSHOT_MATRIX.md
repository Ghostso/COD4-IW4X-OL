# 04 — Gamestate / Configstring / Snapshot 矩阵

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. Gamestate 顶层格式

| 字段 | 2697 服务端（`0xA21B8`） | CoD4x/OLD `SV_SendClientGameState` | CODOL 客户端 | 裁定 |
|---|---|---|---|---|
| opcode | `WriteByte(3)` @`0xA224C` | `svc_gamestate` 常量 | `0x350170` 表项 3 → `0x34FD80(1)`（demo） | **存在差异** |
| 版本/序号 | `WriteInt32` @`0xA225A` | `MSG_WriteLong` | 读 4B | 实现高度相似 |
| 地图名 | `WriteLenStr` @`0xA2269` | `MSG_WriteString` | **无对应**（客户端读 4B） | **REFUTED（匹配）** |
| 模式名 | `WriteLenStr("mp")` @`0xA2279` | `MSG_WriteString` | **无对应** | **REFUTED（匹配）** |
| field4 | `WriteInt32` @`0xA2288` | — | 读 `len` 字节载荷 | 存在差异 |
| Configstring 子帧 | `call 0xA0468` @`0xA22C1` | `SV_SendClientGameState` 内 | 无对应 | **BLOCKED** |
| 尾字段 C/8 | `WriteInt32` ×2 | — | 无对应 | BLOCKED |
| 顶层尾 | `WriteByte(6)` @`0xA22F8` | — | 无 | BLOCKED |

**结论：** 客户端已定位的 `0x03` 消费者（`0x34FD80(1)`）字段序与服务端**冲突**（第 2 字段 `i32` vs `cstring`）。实时消费者**未定位**。

## 2. Configstring 子帧格式（本轮重新逐指令复核）

| 字段 | 服务端 2697（指令） | 客户端 `0xA2660` | 裁定 |
|---|---|---|---|
| `0x04` | `0xA07F8 WriteByte(4)`（`0x99551`，len=1） | `0x352FA1` +1 字节（无值比较） | 位置 INFERRED；值级 BLOCKED |
| count1 | `0xA0807 WriteShort`（2B） | `push 2` @`0xA26AF` + `movsx word` | **PROVEN** |
| 索引连续标志 | `0xA0400` WriteIndexDelta（1 bit） | `0x44C8C0` + `push 0xD` | **PROVEN** |
| 13-bit 绝对索引 | 13 bit | `0xA26F4 push 0xD` | **PROVEN** |
| A1 字符串 | `WriteLenStr` @`0xA096F`（len+1，含 NUL） | `0xA25F0` NUL 扫描 | **PROVEN** |
| **A2 计数** | **`0xA085F mov [esp+8],0xB`（11 bit）** | **`0xA2765 push 0xB`（11 bit）** | **PROVEN（一致，见 §3）** |
| A2 值 | `0xA08A0 mov [esp+8],0xA`（10 bit） | `0xA27D7 push 0xA` | **PROVEN** |
| A3 计数 | `0xA08BF mov [esp+8],0xA`（10 bit） | `0xA2879 push 0xA` | **PROVEN** |
| A3 记录 | 10/7/4/n×12（`0xA091D`/`0xA0934`/`0xA094B`/`0xA0974`） | `0xA2480` `push 0xA/7/4` | **PROVEN** |
| 索引上限 | `0x1DD7` | `cmp edi,0x1DD7` | **PROVEN** |
| 子帧尾 `0x06` | `0xA0997 WriteByte(6)` | **未定位** | BLOCKED |

## 3. A2 计数字宽差异：本轮消解（重要修订）

E-08 曾把服务端 A2 计数记为 **10 bit**，而客户端实测为 **11 bit**，E-11/E-13 保留为 BLOCKED。

**本轮逐指令复核（服务端 `0xA0468`）：**

```asm
0A084D  mov dword [esp+8], 0xB      ; A2 段计数 = 11 bit
0A085F  call 0x499590               ; MSG_WriteBits
...
0A088A  mov dword [esp+8], 0xA      ; A2 条目值 = 10 bit
0A08A0  call 0x499590
```

**裁定：两侧均为 11 bit → 一致（PROVEN）。E-08 的"10 bit"记录为错误，本轮修订。**

**修订记录：** 不覆盖 E-08 原文；差异记入本文件与 `12_...ADDENDUM`。

## 4. 位写入与对齐

| 项 | 服务端 | 客户端 | 裁定 |
|---|---|---|---|
| 位序 | LSB-first（`0x99590`） | LSB-first（`0x1AC670`） | **PROVEN** |
| 重同步 | `bitpos%8==0 ⇒ bitpos=used*8`（`0x9960A`） | 读取器无等价逻辑（无队列语义） | 服务端 PROVEN；客户端 BLOCKED |
| 字符串 | 裸字节，不更新 bitpos | NUL 扫描 | **PROVEN** |

## 5. `0x04` / `0x05` / `0x06` 层级

| 值 | 服务端位置 | 层级 | 客户端 | 裁定 |
|---|---|---|---|---|
| `0x04` | `0xA07F8` | Gamestate **内部子帧头** | `0x352FA1` +1（位置） | INFERRED |
| `0x05` | `0x87104`（snapshot outer selector） | Snapshot 外层 | 未定位 | BLOCKED |
| `0x06` | `0xA0997`（子帧尾）/`0xA22F8`（顶层尾）/`0xA4CAF`（snapshot 内） | **三层不同** | 未定位 | BLOCKED |

**纪律：** 数值相同但层级不同，**禁止合并**。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| count1 = 2 字节 | **PROVEN** |
| A2 计数 = 11 bit（两侧） | **PROVEN（本轮修订）** |
| A2 值 = 10 bit | **PROVEN** |
| A3 = 10/7/4/n×12 | **PROVEN** |
| `0x04` 值级识别 | **BLOCKED** |
| `0x06` 读取/对齐/终止 | **BLOCKED** |
| Gamestate 顶层格式匹配 | **REFUTED**（demo 消费者） |
| 实时 Gamestate 消费者 | **BLOCKED** |
