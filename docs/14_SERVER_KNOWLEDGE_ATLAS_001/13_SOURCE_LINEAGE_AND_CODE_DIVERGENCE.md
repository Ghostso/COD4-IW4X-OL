# 13 — 源码血统与代码分歧 / SOURCE LINEAGE & CODE DIVERGENCE

> 本文件回答“**为什么相同**”与“**为什么不同**”。所有定量相似度均由本档案**实测复算**（行集合 Jaccard 相似度 + 逐文件 SHA-256）。
> 分类：`IDENTICAL_SOURCE` / `PORTED_CODE` / `STRUCTURAL_MATCH` / `ARCHITECTURAL_ANALOGY` / `SAME_NAME_ONLY` / `UNRELATED_OR_DIVERGED` / `UNKNOWN`

---

## 0. 决定性发现（本文件最重要的一条）

**OLD 服务端源码是 `IW4OL`——它自称“a fork of CoD4x”。**

```
q_shared.h:6    "This file is part of IW4OL source code, a fork of CoD4x."
qcommon.h:6     同上
```

证据：EV-R-OldSrc（`grep` 实测）。这**一次性解释**了 OLD/1113 与 CoD4x 的大量结构相同，并把它从“猜想”升格为**有源码字面证据的血统**。

---

## 1. OLD ↔ 1113：`IDENTICAL_SOURCE`（最强血统）

实测（逐文件 SHA-256，顶层 217 个文件中的 `.c`）：

| 指标 | 值 |
|---|---|
| 顶层 `.c` 抽样对比 | **identical = 82，differing = 1** |
| 唯一差异文件 | `g_sv_main.c`（移除 `player_sprintTime` 的 `CVAR_CHEAT`，加“无限冲刺”注释） |
| `codol\` 子树（递归）差异 | **0** |

→ **裁定：`IDENTICAL_SOURCE`**（生命周期/传输/序列化/业务全层）。差异仅一处玩法改动。

**含义：** OLD 与 1113 的“版本演化”在源码层**不存在**；二者是同一源码的两个构建。任何把 OLD 与 1113 当作“不同版本协议”的结论都必须先排除这一点。

---

## 2. OLD/1113 ↔ CoD4x：`PORTED_CODE`（fork，非平行实现）

### 2.1 定量相似度（行集合 Jaccard，`\s+` 归一化，忽略 ≤8 字符行）

| 文件 | 公共行 | OLD 行集 | CoD4x 行集 | Jaccard |
|---|---|---|---|---|
| `huffman.c` | 2387 | 2390 | 2390 | **99.7%** |
| `cvar.c` | 884 | 893 | 894 | **97.9%** |
| `cmd.c` | 575 | 586 | 578 | **97.6%** |
| `netchan.c` | 320 | 334 | 323 | **95.0%** |
| `filesystem.c` | 2029 | 2153 | 2038 | **93.8%** |
| `common.c` | 725 | 810 | 752 | 86.6% |
| `sv_game.c` | 389 | 444 | 399 | 85.7% |
| `msg.c` | 1513 | 1776 | 1584 | 81.9% |
| `sv_main.c` | 2591 | 3445 | 2615 | 74.7% |
| `sv_client.c` | 1407 | 1990 | 1421 | 70.2% |
| `sv_snapshot.c` | 1018 | 1499 | 1038 | 67.0% |
| `sv_init_mp.cpp` | 48 | 48 | 48 | **100.0%** |

### 2.2 分歧的结构（CODOL 在 fork 之上叠加）

`netchan.c`（95.0% 相同，差异集中在 CODOL 分支）：

```c
#include "codol_wire.h"      // CODOL-only
#include "codol_network.h"   // CODOL-only
...
#ifdef CODOL_SERVER
    if (fragmentBuffer && fragmentBufferSize >= (int)sizeof(codol_fragments_t))
        memset(fragmentBuffer, 0, sizeof(codol_fragments_t));
#endif
...
#ifdef CODOL_SERVER
    return CODOL_NetchanProcess(chan, msg);   // ← CODOL 接管 netchan
#endif
```

| 观察 | 证据 |
|---|---|
| CoD4x `netchan.c` 中 `grep 'CODOL|Xor|stride|1162'` = **0 命中** | EV-R-Cod4x |
| OLD `netchan.c` 含 `#ifdef CODOL_SERVER` 分支与 `codol_*` 头 | EV-R-OldSrc |
| OLD 顶层 `.c` 中 `CODOL` 标记 = **1,844 处** | EV-R-OldSrc |
| CoD4x 顶层 `.c` 中 `CODOL` 标记 = **0 处** | EV-R-Cod4x |
| OLD 顶层 `.c` 中 `2697` 标记 = **0 处** | EV-R-OldSrc |
| CoD4x 顶层 `.c` 中 `2697` 标记 = **0 处** | EV-R-Cod4x |

### 2.3 裁定

| 对照对 | 分类 | 依据 |
|---|---|---|
| OLD/1113 ↔ CoD4x 引擎层 | `PORTED_CODE`（fork） | 字面 “fork of CoD4x” + 高 Jaccard |
| OLD/1113 ↔ CoD4x 的 `codol\` 层 | **CoD4x 中没有**（CODOL 新增） | `codol\` 子树在 CoD4x 中不存在 |

**关键结论：** “OLD 与 CoD4x 相同”**不是**因为“都是 CoD 引擎”，而是因为 OLD **就是** CoD4x 的 fork。这是**共同来源**已证明的情形。

---

## 3. OLD/1113 ↔ 2697：`PORTED_CODE`（同族延续，非新协议）

| 证据 | 内容 |
|---|---|
| 骨架一致 | 同 EntryPoint 0x14e0（2697 与 1113）、同 11 节区、同 Characteristics 0x326、同 DllCharacteristics 0x140 |
| 工具链一致 | 二者均 ld 2.47 / MSYS2 GCC 16.2.0 |
| 导入近似 | 2697 与 1113 仅差 9 项导入（`_lock/_unlock/fgetc/isxdigit/strcspn` + `WSASetLastError/getpeername/htonl/inet_pton`） |
| 共享导出 | 185 `Plugin_*` 完全一致 |
| 新增 | 2697 新增约 20 个 `codol_2697_*` 模块 + weapon 2697 + loopback 守卫 + netconst + archive probe |

**裁定：`PORTED_CODE`。** 2697 = 同族骨架 + 2697 专属层。**不是**新协议家族。

**为什么不同（因果）：**
1. 目标客户端从 1.1.1.13（Old/1113）变为 2.6.9.7（2697）→ 需要新 opcode 集（0x02/0x03/0x04/0x06）。
2. 2697 需要 file/handle 探测（新增 `GetFileType/GetFileInformationByHandle/_open_osfhandle/_stati64`）以读取注册导出与挂载 archive。
3. 2697 需要面向“特定客户端净约束”的发布审计（`dry encode`/`netconst checksum`）。
4. 2697 需要 loopback 守卫（11 个 `_guard_*`）+ `inet_pton/htonl`。

以上 4 条均可由**导入差分 + 新增模块清单 + 诊断串**解释，属**版本演化/协议升级/业务定制**（H7/H6），不是“换引擎”。

---

## 4. 2697 ↔ 任意本地源码：`UNKNOWN`/`UNRELATED_OR_DIVERGED`

| 检验 | 结果 |
|---|---|
| OLD 源码树 `grep 2697` | 0 命中 |
| CoD4x 源码树 `grep 2697` | 0 命中 |
| 本地是否存在 2697 源码 | **不存在** |

→ 2697 只能**反汇编**。其与 2697 客户端的关系只能通过**协议字节**建立，不能通过源码。

**禁止：** 不得把 OLD 源码中的 `codol_*` 逻辑**直接**当作 2697 的实现（旧通道 opcode 与 2697 通道不同）。旧源码只能作**语义参照**。

---

## 5. OL-mod 血统：`UNRELATED_OR_DIVERGED`（相对 IW4x）

| 主张 | 证据 | 裁定 |
|---|---|---|
| ol-mod 基于 IW4x | AUDIT.md：**不基于 IW4x**；它是 CODOL 专有链路（Project Nova / Ayria 组件）源码重建 | **REFUTED** |
| ol-mod 复用 IW4/BO1/BO2/Ghosts | 仅 CODREF/CODDIFF 跨版本反编译参照 | `SAME_NAME_ONLY`（参考） |
| ol-mod 目标版本 | 3.3.3.3 QA（title 1004），非 2.6.9.7 | VERIFIED |
| ol-mod 是否有非 CODOL 资产替代 | 有 3 处，其中 2 处默认开启 | VERIFIED（审计发现） |

**裁定：** ol-mod 与 IW4x 在**血统上无关**；它自身是独立的 CODOL 重建。

---

## 6. CoD4x ↔ IW4x：`IDENTICAL_SOURCE`（`netchan_t`）

| 检验 | 结果 |
|---|---|
| `netchan_t` 布局 | CoD4x 与 IW4x **1:1 相同** |
| 共同来源 | Quake3（Id） |

**裁定：`IDENTICAL_SOURCE`（就 `netchan_t` 布局而言）。** 但这是**它们的**血统，**不是** CODOL 的血统——CODOL 未发现该结构（EV-Netchan-IW4x）。

**重要否定：** CODOL 未发现 `netchan_t`，说明 CODOL 的 netchan 是**自有实现**，与 CoD4x/IW4x 的 netchan 是 `ARCHITECTURAL_ANALOGY`（或更弱）。

---

## 7. C# 战斗服 / Codec MVP：`UNRELATED_OR_DIVERGED`（有意）

| 主张 | 证据 |
|---|---|
| 自研、未复制上游源码 | README 声明（B3 路线） |
| 字段定义来自 E1–E3 | `02_PROTOCOL_SPEC.json` 引用 RVA |
| 与 2697 服务端共享同一错误假设风险 | 高（非独立来源） |

**裁定：** 与 CODOL/CoD4x/IW4x 均无代码血统；仅**协议语义模仿**。其黄金向量是 **CONSTRUCTED**（非原版抓包）。

---

## 8. 血统总图

```
                    Quake3 / Id Tech 引擎骨架
                              │
              ┌───────────────┼───────────────┐
              │               │               │
          COD4 (IW3)      MW2 (IW4)       (CoD 通用)
              │               │
        ┌─────┴─────┐         │
        │           │         │
    CoD4x_Server  IW4x-client │
      (AGPL)      (仅客户端)   │
        │  netchan_t 1:1 相同 ─┘
        │
        │  fork  ──（字面证据：IW4OL, a fork of CoD4x）
        ▼
    OLD / 1113 服务端（含 CODOL 专用层 codol\*）
        │
        │  PORTED_CODE（同族延续 + 2697 层）
        ▼
      2697 服务端（无源码；叠加 codol_2697_* 层）

    独立分支（与上述无代码血统）：
      · ol-mod（CODOL 3.3.3.3 专有链路重建；注入+插件）
      · C# 战斗服 / Codec MVP（自研协议模仿）
      · REF_LOBBY_KIT（第三方大厅）
```

---

## 9. 分歧的因果分类（回答任务书 §4/§7）

| 差异 | 因果 | 证据 |
|---|---|---|
| OLD/1113 与 CoD4x 大量相同 | **H1 共同源码祖先**（fork，已证明） | q_shared.h:6 字面 + Jaccard 93–99% |
| OLD/1113 与 CoD4x 的 CODOL 层差异 | **H6 CODOL 业务定制** | CODOL 标记 1,844 vs 0 |
| OLD ↔ 1113 几乎全同 | **H10 样本身份**（同源码两构建） | 82/83 文件字节相同 |
| 2697 与 Old/1113 的差异 | **H7 版本演化 + 协议升级** | 新 opcode 集、新导入、新模块、新门控 |
| CODOL 与 CoD4x/IW4x 握手差异 | **H5 独立实现相同功能** | CoD4x/IW4x 无 cookie+ECDH |
| CoD4x 与 IW4x netchan 相同 | **H1 共同源码祖先**（Quake3） | `netchan_t` 1:1 |
| OLMOD 与 IW4x 的“相似” | **H1/H11 假象**（CODREF 参照 + 命名） | AUDIT.md 明示不基于 IW4x |
| 2697 与客户端 `0xA2E50` 的“匹配” | **H11 静态恢复/搜索假象** 尚未排除 | 无分派、无运行时 |
| 2697 门控失败即扣留 | **H6 CODOL 业务/协议定制** | 硬前置条件 |

---

## 10. 血统结论

1. **已证明的共同来源：** OLD/1113 是 CoD4x 的 fork（IW4OL）；CoD4x 与 IW4x 共享 Quake3 netchan。
2. **已证明的身份相同：** OLD ≡ 1113（源码 82/83 字节相同）。
3. **已证明的延续：** 2697 = Old/1113 同族骨架 + 2697 层。
4. **已证明的独立：** CODOL 战斗握手/加密为自有实现；ol-mod 与 IW4x 无关。
5. **未闭合：** 2697 ↔ 2697 客户端的代码对应（无源码、客户端分派 BLOCKED）。
6. **纪律：** 任何“共同祖先”断言必须有**字面证据或定量相似度 + 结构解释**，不能仅凭函数名/目录名。
---

# === 追加：常量级血统证据（UPDATE-2, 2026-10-12） ===

## R-17 补充：2697 传输层常量的源码对应

| 2697 二进制常量 | 数值 | OLD 源码常量（`codol_wire.h`） | 匹配 |
|---|---|---|---|
| `0x489` | 1161 | `CODOL_FRAGMENT_SIZE - 1`（1162−1） | ✔ |
| `0x24500` | 148,736 | `CODOL_FRAGMENT_SIZE × CODOL_MAX_FRAGMENTS`（1162×128） | ✔ |
| `0x1fffffff` | 29 位 | netchan 序列掩码（`CODOL_FRAGMENT_BIT` 之外） | ✔ |
| `0x70cc729` | 118,277,929 | `ceil(2^37 / 1162)` | ✔ 精确 |

**读取位置：** `_CODOL_NetchanTransmit`（RVA 0x999B6）`cmp eax,0x489`；`_CODOL_NetchanTransmitNextFragment`（RVA 0x998D8）`mov eax,0x70cc729 ; mul ; shr edx,5`。

**血统含义（本轮新增分类判定）：**

| 对照对 | 变更前 | 变更后 |
|---|---|---|
| OLD/1113 ↔ 2697 传输层 | `PORTED_CODE`（仅符号级） | **`PORTED_CODE`（符号级 + 常量级）** |
| CODOL ↔ CoD4x 传输层 | `STRUCTURAL_MATCH` / 握手 `UNRELATED_OR_DIVERGED` | 维持（2697 常量与 CoD4x `PACKET_HEADER 10` / `MAX_MSGLEN 0x20000` 不同） |
| CODOL ↔ IW4x 传输层 | `ARCHITECTURAL_ANALOGY` | 维持（IW4x 与 CoD4x 同） |

**共享骨架符号矩阵（本轮实测，RVA 各不同）：**

| 符号 | 2697 | 1113 | OLD |
|---|---|---|---|
| `_Com_Init` | 0x9B04 | 0x9A03 | 0x3660B |
| `_Com_Frame` | 0xA49E | 0xA3A2 | 0x36FAA |
| `_SV_Frame` | 0x8404C | 0x834BA | 0x154A2 |
| `_MSG_WriteByte` | 0x2B40A | 0x2B2EC | 0x77A70 |
| `_MSG_WriteDeltaEntity` | 0x2CD7C | 0x2CC06 | 0x7938A |
| `_Netchan_Transmit` | 0x30D58 | 0x30984 | 0x27660 |
| `_Huffman_InitMain` | 0x24F8D | 0x24F2E | 0x37652 |
| `_CODOL_NetchanProcess` | 0x99690 | 0x96D44 | 0x983C8 |
| `_CODOL_WriteGamestate`（legacy） | 0xA865A | 0x9CB65 | 0xA8DE5 |
| `_CODOL_WriteConfigstrings`（legacy） | 0xA857F | 0x9CA9F | 0xA8D1F |
| `_SV_WriteReliableCommand` | **0x8612E** | — | — |
| `_SV_ProfileCommand2697` | **0x860DE** | — | — |
| `_CODOL2697_*` 全组 | 有 | — | — |

**注意：** 同一引擎函数在三份构建中 **RVA 全部不同**（仅 0.16% 同名符号 RVA 相同），因此 **RVA 相等不是血统判据**；本档案一律以符号名 + 常量 + 控制流形状判定。

## 脚本层排除（R-20）

2697 `scripts`（1,341 文件，19,154,634 B）以 `.gsc` 为主（1,198）；含 `2697|gamestate|netconst|registration` 标记者仅 15 个且均为游戏逻辑 → **协议逻辑不在脚本层**，血统比较应聚焦 EXE。
