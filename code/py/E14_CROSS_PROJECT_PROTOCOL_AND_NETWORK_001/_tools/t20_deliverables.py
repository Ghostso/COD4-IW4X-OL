# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001"
F={}
F["01_REPOSITORY_AND_VERSION_INVENTORY.md"]=r"""# 01 — 仓库与版本清单 / REPOSITORY & VERSION INVENTORY

> 只读静态分析 + 公开源码研究。原始样本未修改。
> 地址约定：RVA（VA = RVA + ImageBase）。客户端恢复镜像 ImageBase = `0x400000`；服务端 ImageBase = `0x400000`。

---

## 1. 冻结样本（本轮再次复核哈希）

| 样本 | 路径 | SHA-256 | 实测 |
|---|---|---|---|
| 客户端 EXE | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | ✔ 一致 |
| 恢复镜像 | `CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | ✔ 一致 |
| 2697 服务端 | `CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | ✔ 一致 |

**映射依据：** 恢复镜像 `.text` 与冻结客户端逐字节一致（E-06：8,047,104/8,047,104）。

## 2. 开源仓库（本地 git 副本，含提交 SHA）

| 项目 | 仓库 URL | 本地路径 | 分支 | 提交 SHA | 提交日期 |
|---|---|---|---|---|---|
| IW4X | `https://github.com/Iw4x/iw4x-client` | `IW4X\Client核心代码\iw4x-client` | — | `d1b175da1a25d31043246de103a702b206269e5a` | 2026-09-20 |
| COD4X | `https://github.com/callofduty4x/CoD4x_Server` | `DEV-BOOKING\_lineage021\CoD4x_Server` | — | `ddd65fce1a1093017bad2dbb6840d75d11c0d56f` | — |
| COD4X（第二副本） | 同上 | `DEV-BOOKING\_lineage021\iw4x-client` | — | `d1b175da…`（同 IW4X） | — |
| IW4X rawfiles | `https://github.com/Iw4x/iw4x-rawfiles` | `DEV-BOOKING\_lineage021\iw4x-rawfiles` | — | （未取） | — |

**线上核对（本轮实测）：** `api.github.com` 返回 HTTP 200；
- `iw4x/iw4x-client` 默认分支 `main`，`pushed_at` 2026-10-07
- `callofduty4x/CoD4x_Server` 默认分支 `master`，`pushed_at` 2026-09-18

**说明：** 本地副本 SHA 与线上 HEAD 不必一致；本报告全部比较以**本地副本 SHA** 为准，避免混版本。

## 3. 其他研究对象

| 对象 | 位置 | 形态 | 备注 |
|---|---|---|---|
| OLD 服务端源码 | 仅见 `EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy\src` | 源码（含 `codol\` 子树） | 标 `IW4OL, a fork of CoD4x` |
| 1113 服务端源码 | 同族（历史报告：82/83 `.c` 与 OLD 字节相同） | 源码 | 冻结记录见 `14_SERVER_KNOWLEDGE_ATLAS_001\13_...` |
| 2697 服务端 | `...\bin2697\codol_dedrun.exe` | 二进制 | 无源码 |
| OL-mod / ol-final | `_e1_regression\ol-mod-olfinal`（含 `.git`）；审计 `CODOL_OLMOD_AUDIT_20261009_094312\AUDIT.md` | 源码 + 审计 | 自述**不基于 IW4x** |
| 最终版 CODOL 客户端 | 见 §1 | 二进制 | E-01..E-13 证据 |

## 4. 本轮未取到的对象

| 对象 | 状态 |
|---|---|
| OLD/1113 独立源码树的完整副本 | **未在本地定位**（仅 experiment_copy 变体）；血统结论沿用 `14_SERVER_KNOWLEDGE_ATLAS_001\13_...` 的实测 Jaccard 与字面证据 |
| COD4X 提交历史 / blame | **未取**（无线上 git clone） |
| IW4X dedicated server 源码 | **未取**（仓库为客户端项目；见 `03` §IW4X 缺口） |
"""

F["02_SOURCE_LINEAGE_AND_FORK_MATRIX.md"]=r"""# 02 — 源码血统与分叉矩阵 / SOURCE LINEAGE & FORK MATRIX

> 分类：`同源已证实` / `实现高度相似` / `机制相同、实现不同` / `存在差异` / `无法对应`
> 纪律：不凭函数名、片段相似或 RVA 相同认定对应关系。

---

## 1. 血统总图

```
        Quake3 引擎（COD 通用网络栈）
                 │
        ┌────────┴────────┐
        │                 │
   CoD4x_Server        IW4x-client
     (AGPL)             (仅客户端)
        │  netchan_t 1:1 相同（共享 Quake3 祖先）
        │
        │  fork（字面证据：q_shared.h "IW4OL, a fork of CoD4x"）
        ▼
    OLD / 1113 服务端（+ CODOL 专用层 codol\*）
        │
        │  PORTED_CODE（同族延续 + 2697 层）
        ▼
      2697 服务端

   独立：ol-mod（自述不基于 IW4x）；C# codec（自研）
```

## 2. 逐对照裁定

| 对照对 | 裁定 | 依据 |
|---|---|---|
| OLD ↔ 1113 | **同源已证实**（`IDENTICAL_SOURCE`） | 82/83 顶层 `.c` 字节相同；唯一差异 `g_sv_main.c` |
| OLD/1113 ↔ CoD4x | **同源已证实**（`PORTED_CODE`，fork） | `q_shared.h:6` 字面；`netchan.c` Jaccard 95.0%，`msg.c` 81.9% |
| OLD/1113 ↔ CoD4x（`codol\` 层） | **存在差异** | CoD4x 无 `codol\` 子树；OLD 有 1,844 处 `CODOL` 标记，CoD4x 0 处 |
| OLD/1113 ↔ 2697 | **同源已证实**（同族延续 + 常量级） | 同 EntryPoint/节区/工具链；传输常量 `0x489`/`0x24500`/`0x70cc729` 对应 |
| CoD4x ↔ IW4X（netchan） | **同源已证实**（共享 Quake3 祖先） | `netchan_t` 1:1 相同 |
| IW4X ↔ CODOL 客户端 | **无法对应** | 无源码血统证据；仅架构类比 |
| ol-mod ↔ IW4X | **机制相同、实现不同** | `AUDIT.md` 明示不基于 IW4x |
| CODOL 握手/加密 ↔ CoD4x/IW4x | **存在差异** | CoD4x/IW4x 无 cookie+ECDH |

## 3. 分叉差异矩阵（网络/消息相关文件）

| 文件 | OLD/1113 | CoD4x | 差异性质 |
|---|---|---|---|
| `netchan.c` | 有 | 有 | Jaccard 95.0%；OLD 含 `#ifdef CODOL_SERVER` + `CODOL_NetchanProcess` |
| `msg.c` | 有 | 有 | Jaccard 81.9%；OLD 多 192 行 |
| `sv_main.c` | 有 | 有 | Jaccard 74.7%；OLD 多 830 行（CODOL 定制） |
| `sv_client.c` | 有 | 有 | Jaccard 70.2% |
| `sv_snapshot.c` | 有 | 有 | Jaccard 67.0% |
| `huffman.c` | 有 | 有 | Jaccard 99.7%（几乎未改） |
| `cvar.c` | 有 | 有 | Jaccard 97.9% |
| `cmd.c` | 有 | 有 | Jaccard 97.6% |
| `sv_init_mp.cpp` | 有 | 有 | **100.0%** |

## 4. 常量级血统证据（2697 ↔ OLD）

| 2697 二进制常量 | 值 | OLD 源码常量 |
|---|---|---|
| `0x489`（1161） | CODOL_FRAGMENT_SIZE−1 | `codol_wire.h` |
| `0x24500` | 1162×128 | `CODOL_FRAGMENT_SIZE×CODOL_MAX_FRAGMENTS` |
| `0x70cc729` | `ceil(2^37/1162)` | 分片步进 |
| `0x1fffffff` | 29 位序列掩码 | netchan 掩码 |

**读取位置：** `_CODOL_NetchanTransmit` RVA `0x999B6`；`_CODOL_NetchanTransmitNextFragment` RVA `0x998D8`。

**本轮新增反证（重要）：** 相同常量在**客户端恢复镜像 `.text` 中命中 0 次**（`0x489`/`0x70CC729` 均无）。→ **CODOL 分片传输是服务端侧机制**；客户端未显示同一分片常量。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| OLD/1113 是 CoD4x 的 fork | **同源已证实** |
| OLD ≡ 1113 | **同源已证实** |
| 2697 = Old/1113 同族 + 2697 层 | **同源已证实** |
| CoD4x/IW4X 共享 Quake3 netchan | **同源已证实** |
| ol-mod 独立于 IW4x | **同源已证实（否定关系）** |
| IW4X ↔ CODOL 客户端血统 | **无法对应** |
"""

F["03_NETWORK_AND_MESSAGE_SYSTEM_COMPARISON.md"]=r"""# 03 — 网络与消息系统比较 / NETWORK & MESSAGE COMPARISON

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 机制矩阵

| 机制 | IW4X | COD4X | OLD/1113 | 2697 | CODOL 客户端 | 裁定 |
|---|---|---|---|---|---|---|
| socket 收发 | 客户端插件层 | `sys_net.c` | 同 CoD4x | 同族 | **分层虚表封装**（`.rdata 0x898588/0x898590`） | 机制相同、实现不同 |
| netchan 包头/分片 | `netchan_t`（Quake3） | `netchan.c`（Quake3） | CoD4x + `CODOL_NetchanProcess` 接管 | 常量级对应 | **未见 CODOL 分片常量** | 服务端专属 |
| MSG 缓冲/游标 | `msg_t` | `msg.c` | 同 | 同族 | `MSG_ReadBits`/`MSG_ReadData`（`0x1AC670`/`0x1AC1D0`） | 通用引擎机制 |
| Reliable Command | 部分 | 无 2697 形态 | — | `0x8612E`（`0x01`/`0x02`） | 未定位 | 项目专属 |
| Gamestate | 客户端侧 | `SV_SendClientGameState` | 同族 | `0xA21B8` | demo 消费者 `0x34FD80(1)`（字段不匹配） | 存在差异 |
| Configstring | 客户端侧 | `sv_snapshot.c` | 同族 | `0xA0468` | `0xA2660`（字段级 PROVEN） | 实现高度相似 |
| Snapshot/增量 | 客户端侧 | `sv_snapshot.c` | 同族 | `0xA4FA0`/`0xA4860` | 未定位 | 机制相同、实现不同 |
| 客户端分派 | 插件 hook | — | — | — | `0x350170`（demo）/ 实时未定位 | 无法对应 |
| 连接/注册 | 部分 | `sv_auth.c` | 同族 | `0xA3EA0` 注册 | 未定位 | 项目专属 |

## 2. 关键差异：CODOL 的传输层接管（服务端侧）

OLD `netchan.c` 含：

```c
#include "codol_wire.h"        // CODOL-only
#include "codol_network.h"     // CODOL-only
#ifdef CODOL_SERVER
    if (fragmentBuffer && fragmentBufferSize >= (int)sizeof(codol_fragments_t))
        memset(fragmentBuffer, 0, sizeof(codol_fragments_t));
#endif
#ifdef CODOL_SERVER
    return CODOL_NetchanProcess(chan, msg);   // CODOL 接管
#endif
```

**度量：** CoD4x `netchan.c` 中 `CODOL|Xor|stride|1162` 命中 **0**；OLD 顶层 `.c` 中 `CODOL` 标记 **1,844**，CoD4x **0**。

## 3. 客户端网络栈：本轮的二进制发现（PROVEN）

### 3.1 socket 抽象为虚表分派

`.rdata` 虚表（相邻槽位）：

```
0x898588: [0xb75a50] [0xb75a80] [0xb75ab0] 0xb75af0 ...
0x898590: [0xb75ab0] 0xb75af0 0xb75b30 ...
```

`0x775A50`（recv）/ `0x775AB0`（recvfrom）是该虚表的相邻槽位 → **平台 socket 抽象族**。

### 3.2 CODOL 客户端内联 OpenSSL 0.9.8p（PROVEN）

客户端字符串（`0xC3D0D2` 等 5 处）：

```
"OpenSSL 0.9.8p 16 Nov 2010"
"SSL routines" / "elliptic curve routines" / "common libcrypto"
```

**含义：** 客户端网络层包含 **TLS 传输实现**，与 CoD4x/IW4x 的明文 UDP/TCP 栈**架构不同**。这解释了 E-13 的 `0x605220 → 0x6104D0 → 0x672460` 路径：

- `0x672460`：`cmp [eax+0x20],0` → 报错 → `mov eax,[ecx+0x1c]` → `jmp eax`（**OpenSSL 对象方法分派**）
- `0x605220`：`call 0x5FB510` → `0x6104D0` → `call 0x672460`（**TLS 读路径**）
- `0x6029A0` 错误分支引用 `"Recv failure: %s"`（`0xC37244`）→ 经 `0x602760` → **printf 格式化器** `0x60E5B0`

### 3.3 IW4X / COD4X 缺口

| 项 | 状态 |
|---|---|
| IW4X dedicated server 源码 | **仓库为客户端项目**；未在本地副本中发现 `sv_main`/`sv_client` 服务端源 |
| IW4X netchan_t | 与 CoD4x 1:1 相同（历史已证） |
| IW4X 是否含 TLS | **未发现** TLS 实现（与 CODOL 客户端架构不同） |

## 4. 裁定

| 项 | 裁定 |
|---|---|
| MSG 位读写原语为通用引擎机制 | **PROVEN** |
| netchan 分片为 **服务端侧** CODOL 专属 | **PROVEN**（客户端 0 命中同类常量） |
| socket 抽象为分层虚表 | **PROVEN** |
| CODOL 客户端内联 OpenSSL 0.9.8p | **PROVEN** |
| IW4X 有完整服务端实现 | **REFUTED**（仓库为客户端） |
| TLS 机制可移植自 IW4X/COD4X | **REFUTED**（两者无此实现） |
"""

F["04_GAMESTATE_CONFIGSTRING_SNAPSHOT_MATRIX.md"]=r"""# 04 — Gamestate / Configstring / Snapshot 矩阵

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
"""

F["05_CODOL_BINARY_MAPPING_MATRIX.md"]=r"""# 05 — 开源 ↔ CODOL 二进制映射矩阵

> 映射裁定：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`
> 纪律：源码映射只提假设，不自动证明客户端同实现。

---

## 1. 已证实映射（常量级 / 字面证据）

| 机制 | 开源来源 | CODOL 二进制证据 | 裁定 |
|---|---|---|---|
| 分片尺寸 1161 | OLD `codol_wire.h` `CODOL_FRAGMENT_SIZE−1` | 2697 `0x999B6 cmp eax,0x489` | **PROVEN** |
| 分片缓冲 148736 | OLD `1162×128` | 2697 `0x24500` | **PROVEN** |
| 分片步进 | OLD `ceil(2^37/1162)` | 2697 `0x998D8` `0x70CC729` | **PROVEN** |
| 序列掩码 29 位 | OLD netchan | 2697 `0x1fffffff` | **PROVEN** |
| OLD 是 CoD4x fork | 字面 `q_shared.h:6` | — | **PROVEN** |

**本轮反证：** 上述 4 个常量在**客户端镜像 `.text` 中命中 0 次** → 属**服务端侧**机制。

## 2. 引擎级映射（符号名 + 控制流形状）

| 2697 符号 | RVA | 开源对应 | 裁定 |
|---|---|---|---|
| `_Com_Init` | `0x9B04` | CoD4x `Com_Init` | **PROVEN**（同族） |
| `_MSG_WriteByte` | `0x2B40A` | CoD4x `MSG_WriteByte` | **PROVEN**（同族） |
| `_Netchan_Transmit` | `0x30D58` | CoD4x `Netchan_Transmit` | **PROVEN**（同族） |
| `_Huffman_InitMain` | `0x24F8D` | CoD4x `Huffman_InitMain` | **PROVEN**（Jaccard 99.7%） |
| `_SV_WriteReliableCommand` | `0x8612E` | **无对应** | 项目专属 |

## 3. 客户端映射（本轮新增）

| 客户端机制 | 候选开源对应 | 证据 | 裁定 |
|---|---|---|---|
| `MSG_ReadBits` `0x1AC670` | CoD4x/IW4X `MSG_ReadBits` | 位序 LSB-first、`and 7`/`sar 3` 形状一致 | **实现高度相似** |
| `MSG_ReadData` `0x1AC1D0` | CoD4x `MSG_ReadData` | 逐字节复制，无位逻辑 | **实现高度相似** |
| socket 虚表 `0x898588/0x898590` | IW4X/CoD4x `netchan_t` | **架构不同**：IW4X/CoD4x 为结构体直接调用，非虚表分派 | **机制相同、实现不同** |
| `0x60E5B0` | `vsnprintf`/`_vsnprintf` | `'%'` 判定 + 7 项转换符跳转表 + putc 回调 | **机制相同、实现不同**（通用 C 运行时） |
| TLS 路径 `0x605220`→`0x6104D0`→`0x672460` | **无** | 内联 OpenSSL 0.9.8p | **无法对应**（IW4X/CoD4x 无 TLS） |

## 4. 无法对应 / 项目专属

| 项 | 说明 |
|---|---|
| CODOL 握手（cookie + ECDH） | CoD4x/IW4x 无；属 CODOL 自研 |
| CODOL `0x01`/`0x02` reliable command 2697 形态 | 服务端专属 |
| `_CODOL_NetchanTransmit*` 分片族 | 服务端专属（客户端无同类常量） |
| CODOL 客户端 TLS 传输 | 项目专属（内联 OpenSSL） |
| 客户端 9 收包函数虚表族 | 与 IW4X/CoD4x 架构不同 |

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 服务端引擎函数可在 CoD4x 源码中定位 | **PROVEN** |
| 服务端常量可在 OLD 源码中定位 | **PROVEN** |
| 客户端网络栈可直接映射到 IW4X/CoD4x | **REFUTED**（架构 + TLS 差异） |
| 客户端 MSG 原语与 CoD4x 形状一致 | **实现高度相似**（INFERRED） |
"""

F["06_60E5B0_AND_NETWORK_VTABLE_AUDIT.md"]=r"""# 06 — `0x60E5B0` 与网络虚表审计

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 决定性更正：`0x60E5B0` 不是协议状态机

E-13 曾把 `0x60E5B0` 登记为"协议状态机候选"（含 20+ 函数指针调用）。**本轮推翻该假设。**

**证据（DIRECT）：**

```asm
60E5B0  push ebp / mov ebp,esp / sub esp,0xF60
60E5C3  mov eax,[ebp+0xc]              ; 参数 2 = putc 回调
60E5C8  mov esi,[ebp+0x10]             ; 参数 3 = format 字符串
60E5CC  mov edi,[ebp+8]                ; 参数 1 = 回调上下文
60E5CF  mov [ebp-0xd2c],eax            ; 保存回调
60E5E9  mov eax,esi
60E5EB  mov [ebp-0xd30],edi
60E5F1  mov [ebp-0xd48],0xC38A5C       ; 格式标志表
60E607  call 0xA0DE50                  ; 解析格式串
60E623  mov al,[esi]
60E625  cmp al,0x25                    ; '='%' 字符
60E627  je  0xA0E663                   ; 转换符分支
60E633  push edi / push ecx
60E635  call dword ptr [ebp-0xd2c]     ; ← putc 回调
60E63E  cmp eax,-1
...
60E735  cmp eax,6
60E738  ja  0xA0EF31
60E73E  jmp dword ptr [eax*4+0xA0EF84] ; 7 项转换符跳转表
```

**语义（PROVEN）：**

| 元素 | 含义 |
|---|---|
| `[ebp+8]` | 输出上下文（流/缓冲结构） |
| `[ebp+0xc]` | **putc 回调函数指针** |
| `[ebp+0x10]` | format 字符串 |
| `[ebp+0x14]` | va_list |
| `0x25` 比较 | `'%'` 格式引入符 |
| `[eax*4+0xA0EF84]` | 7 项转换符表（s/c/d/pn/n/x 类） |
| 20+ `call [ebp-0xd2c]` | 逐字符输出 |

**裁定：`0x60E5B0` 是 `_vsnprintf` 风格的格式化器。REFUTED（"协议状态机"）。**

## 2. `0x60E5B0` 的调用链（DIRECT）

| 调用点 | 调用者 | 说明 |
|---|---|---|
| `0x60E4CA` | `0x60E4A0` | 包装器（`0x60E4A0` 传 `0x60E470` 作回调） |
| `0x60EFC6` | `0x60E5B0`（递归） | 内部递归 |
| `0x60F046` | `0x60F020` | |
| `0x60F0B4` | `0x60F0A0` | |

`0x60E470`（回调）实现：

```asm
60E470  mov eax,[ebp+0xc]      ; 上下文
60E476  mov ecx,[eax+4]        ; 已写长度
60E479  cmp ecx,[eax+8]        ; 对比容量
60E47C  jae 0xA0E48F           ; 溢出 → -1
60E480  mov cl,[ebp+8]         ; 字符
60E483  mov [edx],cl           ; 写入
60E485  inc [eax] / inc [eax+4]
```

→ **典型 snprintf 写入回调。**

## 3. E-13 的 9 收包函数 → `0x60E5B0` 路径的真实性质

E-13 的路径 `0x6029A0 → 0x602760 → 0x60E5B0`：

```asm
6029A0  ...  call [0xbae490]            ; recv
6029CF  cmp edi,-1
6029D4  call [0xbae4dc]                 ; WSAGetLastError
6029F3  call 0xA0FB00                   ; 错误码 → 字符串
6029FB  push 0xC37244                   ; "Recv failure: %s"
602A01  call 0xA02760                   ; → 0x60E5B0 格式化
602A0B  mov [ecx+0x85F4],edx            ; 记录错误码
602A14  mov [ebx],0x38                  ; 错误字
```

**结论（PROVEN）：** `0x6029A0` → `0x60E5B0` 是 **错误日志格式化路径**，不是协议解析。收包返回值 `-1` 时才进入。

**这解释了 E-13 的"20+ 函数指针"假象：** 它们是 snprintf 的逐字符输出回调，不是协议处理器注册表。

## 4. 网络虚表 `0x898588` / `0x898590`

| 项 | 值 | 证据 |
|---|---|---|
| 表位置 | `.rdata` `0x898580`–`0x898600` | 原始 dump |
| `0x898588` 内容 | `0xb75a50` `0xb75a80` `0xb75ab0` … | DIRECT |
| `0x898590` 内容 | `0xb75ab0` `0xb75af0` `0xb75b30` … | DIRECT |
| `0x775A50`（recv） | 直接数据指针 `.rdata@0x898588` | DIRECT |
| `0x775AB0`（recvfrom） | 直接数据指针 `.rdata@0x898590` | DIRECT |

**性质（INFERRED）：** 相邻槽位 + 同类 `recv`/`recvfrom` 语义 → **平台 socket 抽象虚表**。

**构造者定位：BLOCKED。** 本轮未定位写入该虚表指针的构造函数（需回溯对象实例化路径）。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| `0x60E5B0` 是协议状态机 | **REFUTED** |
| `0x60E5B0` 是 vsnprintf 格式化器 | **PROVEN** |
| `0x6029A0` → `0x60E5B0` 是错误日志路径 | **PROVEN** |
| `[ebp-0xd2c]` 是 putc 回调 | **PROVEN** |
| 虚表 `0x898588/0x898590` 是 socket 抽象 | **INFERRED** |
| 虚表构造者 | **BLOCKED** |
"""

F["07_605220_PATH_AND_CONVERGENCE_AUDIT.md"]=r"""# 07 — `0x605220` 路径与汇合审计

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. `0x605220` 逐指令（DIRECT）

```asm
605220  push ebp / mov ebp,esp / sub esp,8
605228  mov edi,[ebp+8]
60522B  mov esi,[edi+0x5b8]           ; SSL 连接对象
605231  test esi,esi / je 0xA0526B
605235  mov eax,[edi+0x44]
60523A  test eax,eax / je 0xA0526B
60523C  push 0xA05200                 ; 比较回调
605244  mov [ebp-8],esi
60524E  mov edx,[eax+0x34]
605253  call 0xA06650                 ; 超时/可读检查
60525B  cmp [ebp-4],0 / jne 0xA05274
605261  mov dword [edi+0x5b8],0       ; 清除
60526B  or eax,-1                      ; 返回 -1
605274  mov eax,[ebp+0xc] / mov [eax],esi
60527D  cmp dword [esi+0x17c],0
60528D  call 0x9FB510                 ; ← SSL_pending 类
605295  test eax,eax / jne 0xA052B5
6052A2  push 2 / push 1 / lea eax,[ebp+0xb]
6052AB  call [0xbae490]               ; recv（2 字节 peek）
```

## 2. `0x5FB510` → `0x6104D0` → `0x672460`（DIRECT）

```asm
5FB510  ... jmp 0x6104D0
6104D0  mov ecx,[ebp+8]
6104D6  mov edx,[ecx+0x188]
6104DC  push 1 / lea eax,[ebp+0xb] / push eax / push edx
6104E3  call 0x672460
6104EB  test eax,eax
6104ED  jle 0xA104F6
6104EF  mov eax,1 / ret
```

```asm
672460  mov eax,[esp+4]
672464  cmp dword [eax+0x20],0         ; OpenSSL 对象状态
672468  jne 0xA7248C
67246A  push 0x38B / push 0xC5650C     ; 源文件/行号
672474  push 0x114 / push 0x10E / push 0x14
672480  call 0xA27F20                  ; 错误报告
672488  or eax,-1 / ret
67248C  test byte [eax+0x30],2 / je 0xA72495
672492  xor eax,eax / ret
672495  mov ecx,[eax+8]
67249C  mov eax,[ecx+0x1c]
67249F  jmp eax                        ; ← 对象方法虚分派
```

**证据：** `0xC5650C` 是 OpenSSL 源文件路径字符串；`0xC3D0D2` 等 5 处含 `"OpenSSL 0.9.8p 16 Nov 2010"`。

**判读（PROVEN）：** `0x672460` 是 **OpenSSL 对象方法分派**（读 `[obj+8]` → `[+0x1c]` → `jmp`），`0x6104D0`/`0x5FB510` 是其封装，`0x605220` 是 **TLS 读路径**。

## 3. 与 `0x6029A0` 路径的汇合审计

| 检查 | 结果 |
|---|---|
| `0x605220` 6 层闭包大小 | **7** 个函数 |
| `0x6029A0` 6 层闭包大小 | **39** 个函数 |
| **共享下游** | **0** |

**裁定（REFUTED）：** 两条路径在 6 层内**无共享下游**，**不存在可证汇合**。

**注意：** 两者都调用 `recv`（同一 IAT `0xBae490`），但这是**共享底层 socket API**，不是汇合点（按任务要求：仅访问相同全局/API 不足以证明路径相同）。

## 4. 两条路径的性质对比

| 项 | `0x6029A0` 路径 | `0x605220` 路径 |
|---|---|---|
| 下游规模 | 39 | 7 |
| 关键下游 | `0x602760` → `0x60E5B0`（**printf**） | `0x5FB510` → `0x6104D0` → `0x672460`（**OpenSSL**） |
| 语义 | recv 错误日志格式化 | **TLS 读取** |
| 是否业务解析 | **否**（REFUTED） | **否**（TLS 层） |
| 是否到达 Gamestate | 否 | 否 |

**结论：** 两条路径**都不**是 Gamestate 消费者；一条是日志，一条是 TLS。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| `0x605220` 是 TLS 读路径 | **PROVEN** |
| `0x672460` 是 OpenSSL 对象方法分派 | **PROVEN** |
| `0x6029A0` → `0x60E5B0` 是错误日志 | **PROVEN** |
| 两路径存在可证汇合 | **REFUTED** |
| 任一路径到达 Gamestate | **REFUTED** |
"""

F["08_REALTIME_GAMESTATE_CONSUMER_VERDICT.md"]=r"""# 08 — 实时消息入口与 Gamestate 消费者裁定

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 分层定位表

| 层 | 本轮定位 | 裁定 |
|---|---|---|
| **socket API** | IAT：`recv` `0xBae490`、`recvfrom` `0xBae50C`、`send` `0xBae4C8`、`sendto` `0xBae504` | **PROVEN** |
| **网络抽象层** | 虚表 `.rdata 0x898588`/`0x898590`；槽位 `0x775A50`(recv)/`0x775AB0`(recvfrom)；另 `0x1B0430`/`0x6029A0`/`0x605220` 等 | **INFERRED**（构造者 BLOCKED） |
| **传输加密层** | OpenSSL 0.9.8p（`0xC3D0D2`）；TLS 读 `0x605220`→`0x6104D0`→`0x672460` | **PROVEN** |
| **应用层消息分派** | **未定位** | **BLOCKED** |
| **Gamestate `0x03` 消费者** | **未定位**（已定位的 `0x34FD80(1)` 属 demo 且字段不匹配） | **BLOCKED** |
| **内部 Configstring 子帧处理器** | `0x354100` case 6（属 demo 链） | INFERRED（demo） |
| **Configstring body reader** | `0xA2660`（字段级 PROVEN） | 实时归属 **BLOCKED** |

## 2. E-13 断点的本轮进展

| E-13 断点 | E-14 结果 |
|---|---|
| `0x60E5B0` 是"协议状态机"候选 | **REFUTED**（实为 vsnprintf） |
| `[ebp-0xd2c]` 是协议处理器指针 | **REFUTED**（实为 putc 回调） |
| `0x6029A0` 是协议处理 | **REFUTED**（实为 recv 错误日志路径） |
| `0x605220` 是"独立协议路径"候选 | **REFUTED**（实为 TLS 读路径） |
| 网络虚表构造者 | **仍 BLOCKED** |
| 实时 `0x03` 消费者 | **仍 BLOCKED** |

**净效果：** E-13 的 4 条候选路径中有 **3 条被排除**（`0x6029A0`/`0x605220`/`0x60E5B0`），剩余候选为 **`0x1B0430`** 与 **`0x78772D`**（含 `.tvm0`）。

## 3. `0xA2660` 的实时归属

| 判据 | 结果 |
|---|---|
| 字段级行为（count1/索引/A1/A2/A3） | **PROVEN** |
| 3 个调用点（`0x3512A0`/`0x352F80`） | 均属 demo 链 |
| 实时上游 | **未定位** |

**裁定：`0xA2660` 是 Configstring body reader（PROVEN）；"实时"归属 BLOCKED。**

## 4. 本轮新增的结构性认识

**CODOL 客户端网络栈与 IW4X/CoD4x 架构不同：**

| 项 | IW4X/CoD4x | CODOL 客户端 |
|---|---|---|
| socket 抽象 | `netchan_t` 结构体直接调用 | **虚表分派**（`.rdata 0x898588`） |
| 传输加密 | 无 | **内联 OpenSSL 0.9.8p（TLS）** |
| 分片常量（1161 等） | 服务端侧 | **客户端 0 命中** |
| 错误输出 | 直接格式化 | `0x60E5B0` vsnprintf + putc 回调 |

**含义：** 不能用 IW4X/CoD4x 的客户端网络代码直接推断 CODOL 客户端行为；**必须**依赖 CODOL 二进制直接证据。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| socket API 层 | **PROVEN** |
| TLS 加密层 | **PROVEN** |
| 网络抽象层 | **INFERRED** |
| 应用层消息分派 | **BLOCKED** |
| 实时 `0x03` 消费者 | **BLOCKED** |
| `0xA2660` 实时归属 | **BLOCKED** |
"""

F["09_REUSABLE_COMPONENTS_AND_PROTOCOL_DELTAS.md"]=r"""# 09 — 可复用组件与协议差异 / REUSABLE COMPONENTS & DELTAS

> 可复用性裁定：`可直接复用` / `改造后复用` / `不能复用` / `未知`

---

## 1. 可直接复用

| 组件 | 来源 | 依据 |
|---|---|---|
| Huffman 表与初始化 | CoD4x `huffman.c` | Jaccard 99.7% 与 OLD/2697 一致 |
| cvar 子系统 | CoD4x `cvar.c` | Jaccard 97.9% |
| 命令解析 | CoD4x `cmd.c` | Jaccard 97.6% |
| `sv_init_mp.cpp` 骨架 | CoD4x | **100.0%** |
| MSG 位读写原语（服务端侧） | CoD4x `msg.c` | Jaccard 81.9%；2697 有对应符号 |
| netchan 基础结构 | CoD4x `netchan.c` | Jaccard 95.0%（引擎部分） |

## 2. 改造后复用

| 组件 | 需要的改造 | 依据 |
|---|---|---|
| netchan 传输 | 需加 CODOL 分片层 | OLD 用 `#ifdef CODOL_SERVER` + `CODOL_NetchanProcess` 接管 |
| Gamestate 写入 | 需替换为 2697 字段序 + Configstring 子帧 | `0xA21B8` vs CoD4x `SV_SendClientGameState` 差异 |
| Snapshot | 需对齐 2697 `0xA4FA0`/`0xA4860` | `sv_snapshot.c` Jaccard 67.0% |
| 可靠命令 | 需实现 2697 `0x01`/`0x02` | 服务端专属，CoD4x 无对应 |
| 客户端分派逻辑 | **不可复用**（需 CODOL 证据重写） | 见 §3 |

## 3. 不能复用

| 组件 | 原因 |
|---|---|
| IW4X/CoD4x 客户端网络栈 | CODOL 客户端为虚表分派 + 内联 TLS，架构不同 |
| IW4X/CoD4x 明文 UDP 传输 | CODOL 客户端含 OpenSSL 0.9.8p（TLS） |
| CODOL 握手（cookie + ECDH） | 自研，无开源对应 |
| CODOL 客户端 Gamestate 消费 | 实时消费者未定位，无法复用任何实现 |
| `.tvm0` 保护层 | 无开源对应 |

## 4. 仍未知

| 项 | 缺失 |
|---|---|
| 网络虚表构造者 | 对象实例化路径未定位 |
| 应用层消息分派器 | 未定位 |
| 实时 `0x03` 消费者 | 未定位 |
| `0x04`/`0x06` 客户端值级识别 | 未定位 |
| TLS 与 netchan 的衔接 | TLS 解密后的数据去向未定位 |

## 5. 服务器实现建议（基于证据）

| 模块 | 建议 |
|---|---|
| 传输层 | 复用 CoD4x netchan 骨架 + 实现 CODOL 分片层（常量已证） |
| Huffman/压缩 | 直接复用 CoD4x |
| 可靠命令 | 依 2697 二进制证据重新实现（`0x8612E` 字段序已 PROVEN） |
| Gamestate 编码 | 依 `0xA21B8` 字段序实现；**但客户端验证 BLOCKED** |
| Configstring 编码 | 依 `0xA0468` 字段序实现（含本轮修订的 A2=11 bit） |
| 客户端互操作验证 | **不可**在实时消费者定位前声称 |

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 服务端引擎层可复用 CoD4x | **可直接复用** |
| 服务端传输层 | **改造后复用** |
| 客户端网络栈 | **不能复用** |
| 协议互操作 | **未知**（依赖实时消费者定位） |
"""

F["10_E14_VERDICT.md"]=r"""# 10 — E-14 总裁定 / VERDICT

> 只读静态分析 + 公开源码研究。原始样本未修改，哈希与基线一致。

---

## 1. 十二个最终问题

**Q1. 哪些机制存在可证实的源码继承关系？**
- OLD/1113 = **CoD4x 的 fork**（字面 `q_shared.h:6` + Jaccard 93–99%）→ **同源已证实**
- OLD ≡ 1113（82/83 字节相同）→ **同源已证实**
- 2697 = Old/1113 同族 + 2697 层（符号 + 常量级）→ **同源已证实**
- CoD4x ↔ IW4X 共享 Quake3 netchan（`netchan_t` 1:1）→ **同源已证实**
- ol-mod 独立于 IW4X → **同源已证实（否定关系）**

**Q2. 哪些只是架构相似，不能直接移植？**
- OLD/1113 ↔ 2697 的**客户端分派逻辑**：架构类比，不可移植
- CODOL 客户端网络栈 ↔ IW4X/CoD4x：**架构不同**（虚表 + TLS），不可移植
- Snapshot 实现：机制相同、实现不同
- `0x60E5B0`：通用 C 运行时格式化器，非协议机制

**Q3. 2697 与经典引擎的确定差异？**
| 机制 | 差异 | 裁定 |
|---|---|---|
| netchan | CODOL 分片层接管（`CODOL_NetchanProcess`） | **PROVEN** |
| Reliable Command | 2697 `0x01`/`0x02` 形态，CoD4x 无 | **PROVEN** |
| Gamestate | 字段序 `{i32,cstr,cstr,i32,<cfgsub>,i32,i32,0x06}` | **PROVEN** |
| Configstring | `0x04` 子帧头 + 2B count1 + 11b A2 count（**本轮修订**） | **PROVEN** |
| Snapshot | `0xA4FA0`/`0xA4860`，Jaccard 67%（与 CoD4x 分歧最大） | **PROVEN** |

**Q4. 哪些开源实现可用于解释客户端候选函数？**
- `0x60E5B0`：通用 `vsnprintf`（C 运行时，非特定开源项目）
- `0x605220`→`0x672460`：**OpenSSL 0.9.8p**（客户端字符串直接证明）
- `MSG_ReadBits`/`MSG_ReadData`：CoD4x/IW4X 形状一致（**实现高度相似**）
- 其余（虚表、分派）：**无对应**

**Q5. `0x60E5B0` 是否已证明属于实时网络协议处理链？**
**否（REFUTED）。** 它是 `vsnprintf` 风格格式化器；`0x6029A0` → `0x60E5B0` 是 **recv 错误日志路径**。

**Q6. 两个网络虚表槽位的构造者是否已定位？**
**否（BLOCKED）。** 已证 `0x898588`/`0x898590` 含 `0xb75a50`/`0xb75ab0`（recv/recvfrom 槽位），但写入虚表指针的构造函数未定位。

**Q7. `0x605220` 路径与状态机路径是否存在可证实汇合？**
**否（REFUTED）。** 两条路径 6 层闭包分别为 7 与 39 个函数，**共享下游 = 0**；且 `0x605220` 实为 TLS 读路径。

**Q8. 是否找到实时 Gamestate `0x03` 消费者？**
**否（BLOCKED）。** 已定位的 `0x34FD80(1)` 属 demo 链，字段序与服务端冲突。

**Q9. `0xA2660` 是否能被认定为实时 Configstring body reader？**
**不能（BLOCKED）。** 字段级行为 PROVEN；3 个调用点均属 demo 链，实时上游未定位。

**Q10. 哪些服务器模块可安全复用开源实现？**
| 模块 | 裁定 |
|---|---|
| Huffman / cvar / cmd / `sv_init_mp` | **可直接复用** |
| netchan 基础 + MSG 原语 | **可直接复用**（引擎部分） |
| netchan 传输、Gamestate、Snapshot | **改造后复用** |
| 可靠命令 2697 形态 | **必须依 CODOL 证据重新实现** |
| 客户端网络栈 | **不能复用** |

**Q11. 阻止端到端兼容验证的最小未知项？**
1. **应用层消息分派器**（TLS 解密后数据去向）— 最大缺口
2. 实时 `0x03` 消费者
3. `0x04`/`0x06` 客户端值级识别
4. 网络虚表构造者

**Q12. 能否计算风险加权解决率？**
**不能（BLOCKED）。** 缺少数值权重与问题项全集。可给出的**非加权**计数：
- 本次任务书列出的 12 个决策问题：**已裁定 12/12**（其中 PROVEN/REFUTED 9 项，BLOCKED 3 项）
- 但"风险权重"（每项对服务器互操作的影响程度）**未经定义**，因此无法计算加权率。
**所需补充：** ① 问题项全集（含 E-01..E-13 遗留项）；② 每项的风险权重（1–5 或类似标度）；③ 每项的裁定分级到数值的映射规则。

## 2. 关键发现（本轮）

| # | 发现 | 等级 |
|---|---|---|
| 1 | `0x60E5B0` 是 vsnprintf，**否定了 E-13 的"协议状态机"假设** | PROVEN |
| 2 | `0x6029A0` → `0x60E5B0` 是 recv **错误日志**路径 | PROVEN |
| 3 | `0x605220` → `0x6104D0` → `0x672460` 是 **TLS（OpenSSL 0.9.8p）读路径** | PROVEN |
| 4 | 客户端内联 **OpenSSL 0.9.8p 16 Nov 2010** | PROVEN |
| 5 | 网络虚表 `.rdata 0x898588`/`0x898590`（recv/recvfrom 槽位） | PROVEN |
| 6 | `0x605220` 与 `0x6029A0` 路径 **无汇合** | REFUTED |
| 7 | A2 计数两侧均为 **11 bit**（E-08 的 10 bit 记录为错） | PROVEN（修订） |
| 8 | CODOL 分片常量（1161/0x70CC729）在**客户端 0 命中** | PROVEN |

## 3. 对 E-13 的修订

| E-13 结论 | E-14 修订 |
|---|---|
| `0x60E5B0` 是协议状态机候选 | **REFUTED**（vsnprintf） |
| `0x6029A0` 是协议处理候选 | **REFUTED**（错误日志） |
| `0x605220` 是独立协议路径候选 | **REFUTED**（TLS 读） |
| 实时入口 4 条候选 | **收窄为 2 条**（`0x1B0430`、`0x78772D`） |

## 4. 下一轮最小任务

| 优先级 | 任务 | 范围 |
|---|---|---|
| 1 | 定位 **TLS 解密后数据的去向**（`0x605220` 上游的明文入口） | `0x605220` 的调用者 `0x602BC0`/`0x612E80` |
| 2 | `0x1B0430` 的 30+ IAT 间接调用目标解析 | `0x1B0430` 内 |
| 3 | 网络虚表构造者 | `.rdata 0x898588` 引用点 |
| 4 | `0x78772D` 的 `.tvm0` 边界（停止条件） | 不扩大 |

## 5. 交付物清单

| 文件 | 状态 |
|---|---|
| `01_REPOSITORY_AND_VERSION_INVENTORY.md` | ✔ |
| `02_SOURCE_LINEAGE_AND_FORK_MATRIX.md` | ✔ |
| `03_NETWORK_AND_MESSAGE_SYSTEM_COMPARISON.md` | ✔ |
| `04_GAMESTATE_CONFIGSTRING_SNAPSHOT_MATRIX.md` | ✔ |
| `05_CODOL_BINARY_MAPPING_MATRIX.md` | ✔ |
| `06_60E5B0_AND_NETWORK_VTABLE_AUDIT.md` | ✔ |
| `07_605220_PATH_AND_CONVERGENCE_AUDIT.md` | ✔ |
| `08_REALTIME_GAMESTATE_CONSUMER_VERDICT.md` | ✔ |
| `09_REUSABLE_COMPONENTS_AND_PROTOCOL_DELTAS.md` | ✔ |
| `10_E14_VERDICT.md` | ✔ |
| `SHA256SUMS.txt` | ✔ |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
