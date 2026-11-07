# 20 — 交叉验证结果 / CROSS-VALIDATION RESULTS

> 本文件记录**在现有只读证据范围内实际完成**的交叉验证（任务书 §12 优先序 ①–④）。
> **E-10..E-13（运行时/抓包）在本任务中未执行**，不在授权范围内，结果保留为 `BLOCKED`。
> 所有相似度均由本档案**实测复算**，可重放。

---

## 结果总览

| ID | 验证项 | 结果 | 等级 |
|---|---|---|---|
| R-01 | OLD ↔ 1113 文件字节一致性 | **216/217 逐字节相同** | VERIFIED |
| R-02 | OLD/1113 ↔ CoD4x 行级相似度 | Jaccard 67%–99.7% | VERIFIED |
| R-03 | OLD/1113 fork 关系 | 字面证据 "a fork of CoD4x" | VERIFIED |
| R-04 | 2697 ↔ 1113 符号共享度 | 共享 9,522 名 / Jaccard 73.2% | VERIFIED |
| R-05 | 2697 专属符号数 | 302（2697 命名） | VERIFIED |
| R-06 | legacy writer 是否仍存在于 2697 | 是（`_CODOL_WriteGamestate` 0xA865A 等） | VERIFIED |
| R-07 | CODOL netchan 常量 vs CoD4x | 不同（1162 vs 0x20000） | VERIFIED |
| R-08 | IW4x 双克隆差异 | A 多 3 文件（ServerDemo.*） | VERIFIED |
| R-09 | 2697 内部 `0x06` 后是否继续写 | 是（HUD/entities） | VERIFIED |
| R-10 | 黄金向量独立性 | 非独立（CONSTRUCTED） | VERIFIED（审计） |
| R-11 | 运行时/抓包验证 | 未执行 | BLOCKED |

---

## R-01 — OLD ↔ 1113 文件字节一致性（实测）

**方法：** 对 OLD `src\` 顶层 217 个文件逐个计算 SHA-256，与 1113 `CODOL_Server\dedicated\src\` 比对。

**结果：**

| 指标 | 值 |
|---|---|
| 顶层文件总数 | 217 |
| **逐字节相同** | **216** |
| 不同 | 1 |
| 缺失 | 0 |
| 唯一不同文件 | `g_sv_main.c` |
| `codol\` 子树递归差异 | **0** |

**结论：** H-LIN-02 **CONFIRMED**。OLD 与 1113 是同一源码的两个构建，唯一差异是启动器侧玩法改动（移除 `player_sprintTime` 的 `CVAR_CHEAT`）。

**对历史结论的影响：** 任何把 OLD 与 1113 当作“两个不同协议版本”的论述必须**撤回**。

---

## R-02 / R-03 — OLD/1113 ↔ CoD4x（实测）

**方法（R-02）：** 行集合 Jaccard（`\s+` 归一化，忽略 ≤8 字符行）。
**方法（R-03）：** 源码字面检索。

**结果（R-02）：**

| 文件 | 公共行 | Jaccard |
|---|---|---|
| `huffman.c` | 2,387 | **99.7%** |
| `cvar.c` | 884 | **97.9%** |
| `cmd.c` | 575 | **97.6%** |
| `netchan.c` | 320 | **95.0%** |
| `filesystem.c` | 2,029 | **93.8%** |
| `common.c` | 725 | 86.6% |
| `sv_game.c` | 389 | 85.7% |
| `msg.c` | 1,513 | 81.9% |
| `sv_main.c` | 2,591 | 74.7% |
| `sv_client.c` | 1,407 | 70.2% |
| `sv_snapshot.c` | 1,018 | 67.0% |
| `sv_init_mp.cpp` | 48 | **100.0%** |

**结果（R-03）：**

```
q_shared.h:6   "This file is part of IW4OL source code, a fork of CoD4x."
qcommon.h:6    （同上）
```

**结果（CODOL 标记统计）：**

| 检索 | OLD src | CoD4x src |
|---|---|---|
| `CODOL` 标记 | 1,844 | 0 |
| `2697` 标记 | 0 | 0 |

**结论：** H-LIN-01 **CONFIRMED**。OLD/1113 **就是** CoD4x 的 fork（IW4OL）；`codol\` 专用层是 CODOL 新增，CoD4x 中不存在。

---

## R-04 / R-05 / R-06 — 2697 ↔ 1113 符号分析（实测）

**方法：** 解析 `_data\syms_NEW.json` 与 `syms_1113.json`，比较 `.text` 且非段的符号名。

**结果（R-04）：**

| 指标 | 值 |
|---|---|
| 2697（NEW）`.text` 函数符号 | 9,824 |
| 1113 `.text` 函数符号 | 12,715 |
| **共享符号名** | **9,522** |
| 名称 Jaccard | **73.2%** |

**共享引擎函数（抽样）：**
`_Com_Init`、`_Com_InitZoneMemory`、`_Cvar_Init`、`_Huffman_InitMain`、`_SV_Frame`、`_SV_DirectConnect`、`_SV_SendClientGameState`、`_SV_WriteSnapshotToClient`、`_MSG_WriteByte/Bits/DeltaEntity/DeltaClient/DeltaPlayerstate/…`、`_CODOL_NetchanProcess/Submit/Transmit/TransmitNextFragment`

**结果（R-05）：** 2697-only 符号 = **302**，全部为 2697 命名，例如：
`_CODOL2697_WriteGamestate`、`_CODOL2697_WriteSnapshot`、`_CODOL2697_WriteConfigstrings`、`_CODOL2697_PrepareHistory`、`_CODOL2697_WriteActors`、`_CODOL2697_WriteClients`、`_CODOL2697_WritePlayerArrays`、`_CODOL2697_AdaptEntity`、`_CODOL2697_TranslateCommand`、`_SV_ProfileCommand2697`、`_CODOL_MountTarget2697Archives`、`_CODOL2697_InstallResources`、`_CODOL2697_PublicationAudit_f`、`_CODOL_BuildWeapon2697Registry`、`_CODOL_LoadEngineWeapon2697`、`_CODOL2697_ParseWeaponRecipe`、`_CODOL2697_DefaultUsercmd`、`_CODOL_SendScoreboard2697`、`_CODOL_AcceptClientStats2697`

**结果（R-06）：legacy writer 在两者中都存在，但 RVA 不同：**

| 符号 | NEW (2697) | 1113 |
|---|---|---|
| `_CODOL_WriteGamestate` | 0xA865A | 0x9CB65 |
| `_CODOL_WriteConfigstrings` | 0xA857F | 0x9CA9F |
| `_SV_WriteReliableCommand` | 0x8612E | **不存在** |
| `_SV_Frame` | 0x8404C | 0x834BA |
| `_SV_DirectConnect` | 0x6F2C0 | 0x6ED8A |
| `_SV_SendClientGameState` | 0x70E47 | 0x707B2 |
| `_SV_WriteSnapshotToClient` | 0x86315 | 0x850E5 |
| `_MSG_WriteByte` | 0x2B40A | 0x2B2EC |

**结论：**
- H-LIN-03 **STRONG_INFERENCE 增强为接近已证实**：2697 与 1113 共享 73.2% 的函数名，且**legacy writer 在两份构建中都保留**（只有 RVA 不同）。
- **R-06 是关键发现：** 2697 **保留了旧通道 writer**（`_CODOL_WriteGamestate`/`_CODOL_WriteConfigstrings`），同时新增 2697 writer → 证实 `0x02/0x03` 与 `0x03/0x04` **并存**，不是替换。
- `_SV_WriteReliableCommand` **在 1113 中不存在** → 它是 2697 新增的可靠命令复合 writer。

**同名函数 RVA 相同者极少（15/9,522 ≈ 0.16%）** → 印证“代码重排/版本演化”，**不能**用 RVA 相等判断同源。

---

## R-07 — CODOL netchan 常量 vs CoD4x（实测）

| 项 | CODOL（OLD 源码） | CoD4x |
|---|---|---|
| 分片大小 | `CODOL_FRAGMENT_SIZE 1162u` | — |
| 上限 | `CODOL_MAX_MESSAGE (1162 * CODOL_MAX_FRAGMENTS)` | `MAX_MSGLEN 0x20000` |
| 分片位 | `CODOL_FRAGMENT_BIT 0x80000000` | `FRAGMENT_BIT (1<<31)` |
| 包头 | `{u32 seq|flags, [u16 qport]}` | `PACKET_HEADER 10`（4 seq + [2 qport] + 4 frag start） |
| body 变换 | `CODOL_Xor` | 无 |

**结论：** H-LIN-06 **CONFIRMED**。二者 netchan 是不同实现（分片描述与上限都不同）。

---

## R-08 — IW4x 双克隆差异（实测）

| 项 | 克隆 A（DEV-BOOKING） | 克隆 B（IW4X\Client核心代码） |
|---|---|---|
| HEAD | `d1b175da…`（2026-09-20） | `0699a7e5…`（2026-09-17） |
| 最后提交 | Add server-side demo recording | Register controller dvars on dedicated servers |
| 非 `.git` 文件数 | 568 | 565 |
| src 文件数 | 519 | 517 |

**差异：** A 独有的 3 个文件：
- `.git-blame-ignore-revs`
- `src\Components\Modules\ServerDemo.cpp`
- `src\Components\Modules\ServerDemo.hpp`

**结论：** H-LIN 的“双克隆告警”**已经量化**。差异集中在 **server-side demo recording** 功能。引用 IW4x 行为时必须绑定 HEAD。

---

## R-09 — 2697 内部 `0x06` 的调用顺序

**证据：** EV-2697-Snap-Seq（已有 `_data\disasm_key2697.txt` 与 E2 报告）。

序列（RVA）：

```
0xA4CAF  _CODOL_WriteGlass 之后写 0x06      ← 内部标记
0xA4CEE  _CODOL2697_ReachHud                ← 之后仍继续写
0xA4D4B  _CODOL2697_WriteActors
0xA4D99  _CODOL2697_WriteEntities
0xA4DF4  _CODOL2697_ReachClient
...
0x87104  外层终止符选择（0x05/0x06）
```

**结论：** H-PRO-03 **CONFIRMED**。内部 `0x06`（0xA4CAF）**不是**整条消息的 EOF。

---

## R-10 — 黄金向量独立性审计

| 向量 | 来源标注 | 独立？ |
|---|---|---|
| RC-BIN-001 | E3 RVA（字段规则） | ❌ 与 E3 共享假设 |
| RC-TEXT-001 | E3 RVA | ❌ 同上 |
| CF-001 | E1 RVA（header/trailer VERIFIED，body synthetic） | ❌ body 为合成 |
| GS-001 | E1 RVA（字段序 VERIFIED，语义 BLOCKED） | ❌ 语义未验证 |
| SN-TOKEN-001 / SN-OUTER-001 | E2 RVA | ❌ 同上 |

**结论：** 所有向量均为 **CONSTRUCTED**。它们验证“实现 ≡ 规范”，**未**验证“规范 ≡ 真实客户端”。**不构成独立验证。**

---

## R-11 — 未执行的验证（明确登记）

| 项 | 状态 | 原因 |
|---|---|---|
| E-10 运行时解包 dump | **BLOCKED** | 不在授权范围 |
| E-11 分派回调注册观察 | **BLOCKED** | 不在授权范围 |
| E-12 `0xA2E50` 命中计数 | **BLOCKED** | 不在授权范围 |
| E-13 2697 战斗通道抓包 | **BLOCKED** | 未发生真实互通；且需授权 |
| E-04 `.rimp` 还原 | **未在本轮执行** | 计划项（需新工作，非授权问题） |
| E-05 注册门控完整放行 | **未在本轮执行** | 计划项 |

---

## 结果对假设台账的更新

| 假设 | 更新前 | 更新后 |
|---|---|---|
| H-LIN-01（fork） | CONFIRMED | **CONFIRMED（含定量）** |
| H-LIN-02（OLD≡1113） | CONFIRMED | **CONFIRMED（216/217）** |
| H-LIN-03（2697 同族） | STRONG_INFERENCE | **STRONG_INFERENCE（增强，73.2% + 302 专属 + legacy 并存）** |
| H-LIN-06（netchan 不同） | STRONG_INFERENCE | **CONFIRMED（常量实测）** |
| H-PRO-03（内部 0x06 ≠ EOF） | STRONG_INFERENCE | **CONFIRMED** |
| H-PRO-05（旧/2697 通道并存） | STRONG_INFERENCE | **CONFIRMED（R-06）** |
| H-PRO-01（0x02 ↔ 0xA2E50） | WEAK_INFERENCE | **不变**（客户端侧未闭合） |
| H-CLI-01/02 | CONFIRMED/OPEN | **不变**（需运行时） |

---

## 结论

1. **离线可完成的验证已全部完成**（R-01..R-10）。
2. **血统类结论已从“推断”升级为“定量已证实”**：fork、OLD≡1113、netchan 差异、2697 同族。
3. **R-06 是新增的关键结构性发现**：2697 **同时保留**旧通道 writer 与新增 2697 writer → 两条通道**并存**。
4. **协议类结论仍停在同一处**：客户端消费链（`0x02`/`0x06`/gamestate/configstring/snapshot）**无法用现有证据闭合**。
5. **所有未执行的验证均已明确登记为 BLOCKED**，不做隐性假设。
---

# === 追加：第二轮交叉验证执行结果（UPDATE-2, 2026-10-12） ===

> 本轮**实际执行**了 `19` 中标记为“可离线完成”的验证项（E-01/E-02/E-03/E-04/E-05/E-06/E-14/E-15）。
> 工具：Python 3.11.9 + capstone 5.0.7 + pefile 2024.8.26。
> 原始输出：`_analysis\RAW_RESULTS_BUNDLE.txt`；脚本：`_analysis\*.py`。全程只读，未启动任何进程。

## 新增结果总览

| ID | 验证项 | 结果 | 等级 | 对结论的影响 |
|---|---|---|---|---|
| R-12 | 2697 客户端恢复镜像的区段保真度 | `.data` 声明 218 MB，**仅 0.14% 在文件内** | VERIFIED | **重大** |
| R-13 | `.rdata` 指针完整性 | 30,895 个对齐 VA→.text 指针 + 613 个连续指针表 | VERIFIED | 修正“指针表被破坏”的强度 |
| R-14 | `0xA2E50` 直接调用者（正确 RVA→offset 映射） | `.text` = **0**；`.tvm0` = 1（噪声） | VERIFIED | **强化** BLOCKED |
| R-15 | `.tvm0` E8/E9 命中可靠性 | 落在函数入口 = **0.0%**（纯噪声） | VERIFIED | 排除 `.tvm0` 命中的证据价值 |
| R-16 | 消息解析簇可达性 | 仍有 **1,458** 次调用进入 RVA 0xA0000–0xAFFFF | VERIFIED | 簇是活的 |
| R-17 | 2697 服务端 netchan 常量 | `0x489`(1161)、`0x24500`(1162×128)、`0x70CC729` | VERIFIED | **E-02 判定 = 已证实** |
| R-18 | `0x02`/`0x01` 选择条件（指令级） | `ret<0→Com_Error`；`ret==0→0x01`；`>0→0x02` | VERIFIED | E-03 复核通过 |
| R-19 | 注册格式串三变体 | `%u %x %u` / `+%c` / `+%u %x %c` | VERIFIED | E-05 补强 |

---

## R-12 — 恢复镜像区段保真度（本轮最重要的新证据）

**方法：** 逐区段比较 `Misc_VirtualSize`（加载后声明大小）与 `SizeOfRawData`（文件中实际存在）。

| 区段 | VA | VSize | RawSize | 覆盖率 | 原始字节非零率 |
|---|---|---|---|---|---|
| `.text` | 0x00001000 | 0x007AC90B | 0x007ACA00 | 100.0% | 90.8% |
| `.rdata` | 0x007AE000 | 0x00142880 | 0x00142A00 | 100.0% | 65.1% |
| **`.data`** | 0x008F1000 | **0x0D05C420 (218 MB)** | **0x00049600** | **0.138%** | 55.5% |
| `.tls` | 0x0D94E000 | 0x00000019 | 0x00000200 | — | 0.0% |
| `.rsrc` | 0x0D94F000 | 0x00008DF8 | 0x00008E00 | 100.0% | 68.9% |
| `.tvm0` | 0x0D958000 | 0x002B9000 | 0x002B8C00 | 100.0% | 78.6% |
| `.rimp` | 0x0DC11000 | 0x00002964 | 0x00002A00 | 101.5% | 82.4% |

**含义：** `.data` 声明 218 MB，但文件中**只有 0.14%**。它不是一个“被略微修补”的区段，而是**绝大部分内容不在文件内**的区段。

**但必须同时报告反证（R-13）：** `.data` 那 0.14%（0x49600 字节）**确实包含已初始化的函数指针**：
- → `.rdata`：18,156
- → `.data`：9,084
- → `.text`：2,375
- → `.tvm0`：56

**结论（重要且双向）：**
- 不能再说“`.data` 被破坏导致 vtable 全部丢失”——**部分 vtable 确实存在**。
- 也**不能**再说“`.rdata`/`.data` 指针表**已被完整恢复**”——`.data` 有 99.86% 不在文件里。
- 因此“在现有镜像中找不到 `0xA2E50` 的调用者”**仍然是 BLOCKED，不是 REFUTED**：候选 vtable 可能落在缺失的 99.86% `.data` 中。

---

## R-13 — `.rdata` 指针完整性

| 指标 | 值 |
|---|---|
| `.rdata` 原始大小 | 0x142A00（1,321,472 B） |
| 对齐 u32 中指向 `.text` 的 VA 指针 | **30,895** |
| 连续指针表段（≥4 连续） | **613** |
| `.rdata` 前 0x400 字节中指向 `.rimp` 的 u32 | **243/256** |
| `.rdata` 全表中指向 `.rimp` 的 u32 | **386** |

**结论：**
- `@0x7ACE00` 处是一个指向 `.rimp` 的**导入/修复指针表头**，`0x7ACE00 + 8*idx` 指向 `.rimp` 内的名字串——这解释了 `.rimp` 里为何混有 `advapi32.dll`/`GetUserNameA`/`ImmGetContext` 等 ASCII 名字。
- `.rdata` **本身指针表大体完整可搜**（30,895 个 `.text` 目标、613 个连续表）。
- **但**目标为 `0xA2E50` 的 `.rdata` 指针 = **0**（在 330,368 个对齐槽中）。

---

## R-14 / R-15 — `0xA2E50` 直接调用者（正确映射后的定论）

**先修正一个方法学要点：** 区段表存的是 **RVA**，映射公式为 `file_offset = PointerToRawData + (RVA − VirtualAddress)`。
已用交接值双向校验：`RVA 0x1AC1D0 → off 0x1AB5D0`（✔）、`RVA 0xA2E50 → off 0xA2250`（✔）。
（本档案第一轮曾误把 VA 当作 RVA 传入，得出“`0xA2E50` 位于 thunk 中段”的错误中间结果；该错误**已在本轮自行发现并纠正**，记录于此以示可追溯。）

**修正后结果：**

| 扫描 | 结果 |
|---|---|
| `.text` 内 E8/E9 → VA 0x4A2E50 | **0** |
| `.tvm0` 内 E8/E9 → VA 0x4A2E50 | 1（RVA 0xD9D940F） |
| 全文件 u32 == VA 0x4A2E50 | **0** |
| `.rdata` 指针 → RVA 0xA2E50 | **0** |
| `.rdata` 指针 → 0xA2E00–0xA2EFF | **0** |

**`.tvm0` 命中可忽略（R-15 定量证明）：**

| 区段 | E8 字节数 | 目标在映像内 | 落在“可能函数入口”（前字节为 `0xCC` 或 `0xC3`） | 可靠性 |
|---|---|---|---|---|
| `.text` | 168,888 | 137,010 | 130,362 | **95.1%** |
| `.tvm0` | 29,474 | 23,184 | **0** | **0.0%** |

**结论：**
- `.text` 内 E8/E9 扫描在**95.1%** 的情况下落在真实函数入口 → 它是**高度可信**的调用图工具。
- 因此 `.text` 内 **0** 次调用 `0xA2E50` 是一个**强负面信号**。
- `.tvm0` 内 E8/E9 命中落在函数入口的概率是 **0.0%** → 该区段命中是**纯扫描噪声**，不构成调用者证据。
- **最终：** `opcode 0x02 → 0xA2E50` 的分派 **BLOCKED（维持）**，且分派**不在** `.text` 的线性直接调用图中；候选位置限于 `.tvm0`（未完全解码）、缺失的 `.data`（99.86%）、或运行时生成/回调路径。

---

## R-16 — 消息解析簇仍然是“活的”

| 指标 | 值 |
|---|---|
| 进入 RVA 0xA0000–0xAFFFF 的 E8 调用 | **1,458** |
| 该范围内不同调用目标 | 252 |
| 命中最多的目标 | RVA 0xAFAB0（132 次）、0xACB50（25）、0xA50F0（24） |
| 0xA2000–0xA3000 内的被调入口 | 含 0xA2660、0xA2980、0xA2D90、**0xA2E50**（各 1 次，来自 `.tvm0` 噪声） |

**含义：** 该地址簇**不是死代码**（有 1,458 次进入），但 `0xA2E50` 本身**没有任何可信的 `.text` 调用者**。两者同时成立 → 该簇由若干入口函数构成，`0xA2E50` 位于其中但**当前不可达**。

---

## R-17 — 2697 服务端 netchan 常量（E-02 判定：已证实）

从 `S-2697` 的 `_CODOL_NetchanTransmit`（RVA 0x999B6）与 `_CODOL_NetchanTransmitNextFragment`（RVA 0x998D8）反汇编中直接读出：

```asm
; _CODOL_NetchanTransmit
004999F1  mov  edx,[ecx+0x44]
004999F6  jne  ...
004999F8  mov  ecx,[ecx]
004999FA  cmp  ecx,0x1fffffff      ; ← CODOL 序列号掩码
00499A00  ja   ...
00499A02  cmp  eax,0x489           ; ← 1161 = CODOL_FRAGMENT_SIZE-1
00499A07  jle  0x499A4f            ;    ≤1161 → 单包路径

; _CODOL_NetchanTransmitNextFragment
00499900  mov  eax,0x70cc729       ; ← ceil(2^37 / 1162) 的魔数
00499905  mul  edx
00499907  shr  edx,5               ; /32 → 等价于 /1162 的分片序号
```

**常量校验（可复算）：**

| 二进制常量 | 数值 | 对应 CODOL 源码常量 | 匹配 |
|---|---|---|---|
| `0x489` | 1161 | `CODOL_FRAGMENT_SIZE - 1`（1162−1） | ✔ |
| `0x24500` | 148,736 | `CODOL_FRAGMENT_SIZE × CODOL_MAX_FRAGMENTS`（1162×128） | ✔ |
| `0x1fffffff` | — | `CODOL_FRAGMENT_BIT` 之外的 29 位序列掩码 | ✔ |
| `0x70cc729` | 118,277,929 | `ceil(2^37 / 1162)` | ✔ **精确** |

**结论（E-02 = 已证实，从“较强推断”升级）：**
- 2697 服务端**编译进了 CODOL 专有 netchan 的常量**（1162 分片、128 上限、29 位掩码、除 1162 魔数）。
- 该 netchan **不是** CoD4x 的 netchan（后者 `PACKET_HEADER 10` / `MAX_MSGLEN 0x20000`），**也不是** IW4x 的（与 CoD4x 同）。
- 因此 **H-LIN-06 由 STRONG_INFERENCE 升级为 CONFIRMED_BY_EVIDENCE**。
- 同时证明：2697 的**传输层确实沿用 CODOL 家族**，与 1.1.1.13 旧源码的 `codol_wire.h` 常量一致 —— 这是“OLD→2697 传输层 `PORTED_CODE`”的首个**二进制常量级**证据（此前只有符号级）。

---

## R-18 — `0x02` / `0x01` 选择条件（E-03 指令级复核通过）

```asm
; _SV_WriteReliableCommand  RVA 0x8612E
0048614e  mov  eax,ecx
00486150  call 0x4860de            ; _SV_ProfileCommand2697 → EAX = 长度(>0) / 0 / <0
00486155  test eax,eax
00486157  js   0x4861af            ; <0  → Com_Error("Invalid target profile delta")
00486159  mov  [ebp-8],esi
0048615c  mov  esi,eax
0048615e  je   0x4861c5            ; ==0 → 旧格式 0x01
00486160  mov  [esp+4],2
00486168  mov  [esp],ebx
0048616b  call 0x42b40a            ; MSG_WriteByte(2)          ← 0x02
0048617d  call 0x42b464            ; MSG_WriteLong(seq)
00486189  call 0x42b434            ; MSG_WriteShort(len)
0048619f  call 0x42b4f5            ; MSG_WriteData(payload,len)
...
004861c5  mov  [esp+4],1
004861d0  call 0x42b40a            ; MSG_WriteByte(1)          ← 0x01
004861e2  call 0x42b464            ; MSG_WriteLong(seq)
004861ee  call ...                 ; MSG_WriteString
```

**选择条件（VERIFIED）：**
- `_SV_ProfileCommand2697` 返回 `<0` → `Com_Error`（不发）
- `==0` → `0x01 | long | NUL-string`（旧格式）
- `>0` → `0x02 | long | short(len) | data[len]`（新格式）

**上游门控（R-18 附带）：** `_SV_ProfileCommand2697`（RVA 0x860DE）：
- `call 0x540133`（`_CODOL_Target2697ArchivesActive`）；返回 0 → 立即 `ret`（返回 0）
- `call 0x765630` 读 CVar `@0x7B98E0`（`CODOL2697_PROFILE_WIRE`）；与 `@0x7B98F7`（`"text"`）比较，相等 → 返回 0
- 否则 `mov ecx,0x3fc ; call 0x485d32`（`_CODOL2697_ProfileCommandBytes`）

→ **2697 的 `0x02` 二进制格式需要同时满足：archive 激活 + `CODOL2697_PROFILE_WIRE != "text"` + profile 转换成功。**

---

## R-19 — 注册格式串三变体（E-05 补强）

| 字符串（VA / RVA） | 内容 |
|---|---|
| 0x7C42A0 / 0x3C42A0 | `codol2697-registration %u %x %u` |
| 0x7C42C0 / 0x3C42C0 | `codol2697-registration %u %x %u %c` |
| 0x7C42E4 / 0x3C42E4 | `codol2697-registration %u %x %u %u %x %c` |
| 0x7C4261 / 0x3C4261 | `withheld: verified client registration export is required` |
| 0x7EDEEA / 0x3EDEEA | `verified client registration export for target gamestate publication` |

**`_CODOL2697_ReadRegistration`（RVA 0xA3EA0）结构（VERIFIED）：**
- `mov eax,0xc8d8 ; call 0x74e900 ; sub esp,eax` → 分配 0xC8D8 栈帧
- `lea eax,[ebp-0xc820]` + `memset(..., 0, 0xc814)` → 本地 blob 基址 `[ebp-0xC820]`，大小 **0xC814**（与全局结构 `0x14973B00` 一致）
- 空指针/空串检查 → `fopen`（0x7655E0）→ `fgets(...,0x80)`（0x7655D8）
- `sscanf(buf, "codol2697-registration %u %x %u", ...)`（0x7572E0）→ `cmp eax,3 ; jne 失败`
- `lea eax,[edx-1] ; cmp eax,1 ; ja 失败` → **kind 必须 ∈ {1,2}**
- CRC32 校验 → 全部通过后：`mov dword [ebp-0x6418], 1`
- **偏移算术：** 本地 blob 基址 `[ebp-0xC820]`，正文中的 `[ebp-0x6418]` = 基址 + `0x6408`。随后 `memcpy(0x14973B00, [ebp-0xC820], 0xC814)`。
- → **确认门控标志 `+0x6408 == 1` 只在注册文件通过 CRC 后才被置位**（与 E1 一致，本轮独立复算）。

**磁盘样本交叉验证：** `evidence\client-registration2697.txt` 首行 `codol2697-registration 2 6b6fb5d0 180 139 f78302fe` → `kind=2`（∈{1,2} ✔）、`%x`=0x6b6fb5d0、后接 180/139/f78302fe。**与 `%u %x %u %u %x %c` 变体形状一致。**

**E-05 判定：** 机制 **已证实**；5 字段的**业务语义**仍 `OPEN`（数值含义未定），但**格式与校验链已闭合**。

---

## R-20 — 2697 `scripts` / `runtime-assets` 内容普查（E-15）

| 目录 | 文件数 | 字节 |
|---|---|---|
| `scripts` | 1,341 | 19,154,634 |
| `runtime-assets` | 11,033 | 1,797,434,023 |

`scripts` 扩展名分布：`.gsc` 1,198、`.csv` 86、`.txt` 23、`.atr` 18、`.shock` 12、其他 4。

**含 `2697|gamestate|netconst|registration` 标记的脚本 = 15 个**，例如 `coop/maps/mp/gametypes/coop.gsc`、`maps/mp/gametypes/_codol_bots.gsc`、`maps/mp/killstreaks/_codol.gsc`、`zm/maps/mp/gametypes/zm.gsc`。

**结论：** `scripts` 主要是**游戏逻辑脚本**（地图/模式/僵尸/连杀），**不是**协议/线格式脚本。`2697` 相关的协议级逻辑集中在 **EXE**，不在脚本。→ **H-2697-03 被削弱**（脚本并非协议逻辑所在）。

---

## 追加结论

1. **E-02 由“较强推断”升级为“已证实”**：2697 服务端二进制携带 CODOL 专有 netchan 常量（1162/128/掩码/魔数）。这是 OLD→2697 传输层延续的**首个二进制常量级证据**。
2. **E-04 的分派结论被强化而非推翻**：用**正确** RVA→offset 映射后，`.text` 对 `0xA2E50` 的直接调用仍为 **0**；且 `.text` 扫描的可靠性经量化确认为 **95.1%**，`.tvm0` 命中可靠性为 **0.0%**。
3. **新增结构性发现（R-12）：** 恢复镜像的 `.data` 声明 218 MB，**仅 0.14% 在文件内** → 候选 vtable 可能落在缺失的 99.86% 中。这**既削弱**“客户端不支持”的推断，也**削弱**“已完整恢复”的前提。
4. **E-03/E-05/E-06 三条服务端链条已指令级复核通过**。
5. **E-15 削弱**“脚本含协议逻辑”的假设。
