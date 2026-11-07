# CODOL-BATTLE-SERVER-TRACE-034 — 3.19.26.22 / 1649370 战斗消息接收链追踪

**任务性质：** 只读静态追踪 + 既有服务器差距映射。**不进行服务器协议实现**，不修改冻结源码。
**日期：** 2026-10-13（Asia/Shanghai）
**唯一正式目标：** CODOL **3.19.26.22** / Build **1649370**
**分析对象（本轮唯一静态事实来源）：** 运行时解包镜像
`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
`17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`（10,899,456 B）

**本轮显式不做（按任务书）：** 不核验固化启动链、不调查 "100" 弹窗、不恢复 hosts、不以大厅匹配流程为前置条件。

---

## 0. 首要结论（必须先读）

> **①TASK-009 所列战斗链 RVA **不是**本目标的 RVA。**
> 经目标镜像独立复核：该 RVA 列表在本地 3.19.26.22 镜像中**仅 1/48 落在函数序言上**，
> 其唯一命中项 `0x6D060` 也**不是**所标注的 `parseMatchState` 语义。
> 因此 TASK-009 中战斗链的 "CONFIRMED" 标记**不能沿用于本报告**。

> **②本目标的战斗入口已独立定位**（字符串交叉引用 + 序言边界，不依赖上述 RVA 列表）：
> - 连接无关包（OOB）**构造/发送器**：RVA `0x1C05F0`
> - 连接无关包（OOB）**接收/解析器**：RVA `0x1C13A0`
> - `cancelConnect` 处理：RVA `0x1BF1C0`
> - `gamestateupdate` 引用点：RVA `0x73180`
> - 增量字段**类型分派器**：RVA `0x5F830`，类型表 `0x460550`(314 项) / `0x4606E4`(136 项)

> **③snapshot 帧边界、delta 基线、实体增删**在本轮**仍未闭合**（`UNKNOWN`）。
> 本轮新增的静态证据**缩小了搜索空间**，但**不足以**宣布字段级结论。

---

## 1. 地址约定（本轮最重要的方法学修正）

`image_best.bin` 是一个 **PE 文件**，且其布局满足：

```
file_offset = RVA = VA - ImageBase        (ImageBase = 0x400000)
VA          = ImageBase + RVA
```

**证明（不可能被错误约定复现的 ASCII 实测）：**

| 目标 | VA | 文件偏移 | 实际字节 |
|---|---|---|---|
| `mmbook accepted` | `0x00DC69B0` | `0x009C69B0` | `6d 6d 62 6f 6f 6b 20 61 63 63 65 70 74 65 64 00` |
| `mmstart sv_resetServer…` | `0x00DC6800` | `0x009C6800` | `6d 6d 73 74 61 72 74 20 73 76 5f 72 65 73 65 74…` |
| `mmbook` | `0x00DC6724` | `0x009C6724` | `6d 6d 62 6f 6f 6b 00` |

**对照正确性（TASK-031 已证实为该镜像内真实函数）：**

| 对象 | VA | 文件偏移 | 该偏移字节 | 结论 |
|---|---|---|---|---|
| `accepted` 解析器 | `0x00632680` | `0x00232680` | `55 8b ec 83 e4 f8` | **PROLOGUE** |
| `mmstart` 构造器 | `0x00632070` | `0x00232070` | `55 8b ec 83 e4 f8` | **PROLOGUE** |
| 闩锁消费者 | `0x00634340` | `0x00234340` | `55 8b ec 81 ec 54 02` | **PROLOGUE** |

> 任何绕过本约定的读取都会得到乱码源码与伪 "函数"，本轮所有结论**一律**建立在约定 ① 之上。

---

## 2. 交付物索引

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文件 |
| `BATTLE_RX_CALLCHAIN.md` | 战斗接收链：本目标真实入口、调用关系、分支 |
| `GAMESTATE_CONFIGSTRING_TRACE.md` | gamestate / configstring 解析族与消费条件 |
| `SNAPSHOT_FORMAT_AND_DELTA.md` | snapshot / delta 字段与类型分派表 |
| `CLIENT_STATE_TRANSITIONS.md` | 客户端连接状态机与 OOB 状态门 |
| `SERVER_IMPLEMENTATION_GAP.tsv` | 冻结服务器 vs 目标协议 逐项差异 |
| `OFFLINE_TEST_VECTORS.md` | 离线测试向量（含来源标注与合成数据边界） |
| `UNKNOWN_AND_BLOCKERS.md` | 未知项与阻塞 |
| `FILE_HASH_MANIFEST.tsv` | 分析对象与证据文件哈希 |
| `SHA256SUMS.txt` | 本目录交付物完整性清单 |
| `evidence\*` | 全部只读验证脚本与输出（40+ 项） |

---

## 3. 目标二进制核验（开始前，按 §1 要求）

| 对象 | 路径 | 大小 | SHA-256 | 判定 |
|---|---|---:|---|---|
| 目标客户端 EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | 与 008/009/031 一致 **CONFIRMED** |
| 目标主引擎 DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | 一致 **CONFIRMED** |
| 运行时解包镜像 | `…_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` | 本轮静态事实来源 **CONFIRMED** |

PE 身份（EXE 与镜像一致）：`TimeDateStamp 0x6096930A`、`SizeOfImage 0x0E659000`、`ImageBase 0x400000`、7 节区（`.tp3`×6 + `.tvm0`）。

---

## 4. 验收标准回答（详见各专项文件）

1. **哪些战斗协议链路已由目标版本直接证实？**
   **已证实：** ① 目标是 PE、地址约定；② 连接无关包（OOB）命令字符串确实存在于本目标；③ OOB **发送器** `0x1C05F0`（含 `getchallenge`/`heartbeat` 构造）与其状态门；④ OOB **接收解析器** `0x1C13A0`（引用 `challengeResponse`/`connectResponse`）；⑤ `cancelConnect` 处理 `0x1BF1C0`；⑥ 增量字段**类型分派器** `0x5F830` 与两张类型表；⑦ `0x6D000` 区域的解析族函数边界与相互调用。
   **未证实（`UNKNOWN`）：** snapshot 帧边界、delta 基线、实体增删表示、entityId↔表索引、服务端消息 opcode 分派表位置。

2. **gamestate 与 configstring 的实际消费条件是什么？**
   **部分证实：** 本目标存在解析族 `0x6D060 / 0x6D360 / 0x6D6E0 / 0x6D870 / 0x6D960 / 0x6D9D0 / 0x6DA30 / 0x6DAE0 / 0x6DCF0 / 0x6E030 / 0x6E0A0` 及其调用关系（见 `GAMESTATE_CONFIGSTRING_TRACE.md`）。
   **未证实：** 该族与 TASK-009 标签（`parseGameState`/`parseConfigStrings`）的**一一对应**，以及"先 gamestate 后 configstring 后 snapshot"的**顺序与前置条件**。`0x25`/`0x92` 禁用字节规则在本目标 configstring 区域**未出现**（见 §5）。

3. **snapshot 哪些字段/编码规则已确认，哪些仍未知？**
   **已确认：** 存在 16 位与 8 位两套增量类型分派（314 项 / 136 项索引映射），以及它们在 `0x5F830` 内由位流逐个分派。
   **未知：** 各字段位宽、delta 基线来源、`first` 语义、实体列表终止条件、entityId 映射、序号/丢包处理、玩家状态与实体状态是否分开解码。

4. **当前本地服务器与目标客户端协议的最小差异是什么？**
   最小差异 = **目标客户端的 OOB 状态门**：本目标 `CL_ConnectionlessPacket` 发送器要求 `[0x76446B0] ∈ {3,4,5,6}`，并按状态换算命令（state 3 → `getchallenge`，state 6 → `heartbeat`），且有 3000 ms / 100 / 500 的节流门；冻结服务器的 `legacy3333` 路径按旧抓包时序驱动，**未实现该状态门**（见 `SERVER_IMPLEMENTATION_GAP.tsv` 的 `GAP-001`）。

5. **下一项可独立实现、独立测试、不依赖猜测的工作是什么？**
   **离线实现并对测"OOB 连接无关包收发状态机"**：以本轮已证实的 `0x1C05F0`（发送）与 `0x1C13A0`（接收）所暴露的**命令字符串与状态门**为准，构造服务端侧 `challengeResponse`/`connectResponse` 与节流行为的离线测试向量（见 `OFFLINE_TEST_VECTORS.md`）。该工作**不需要** snapshot 字段定义，也**不需要**启动链或大厅匹配。

---

## 5. 关键新增事实（本轮）

| 事实 | 证据 |
|---|---|
| TASK-009 战斗链 RVA 在目标镜像中仅 1/48 命中序言 | `evidence\verify_probe_rva_for_target.out.txt` |
| 目标 OOB 发送器 `0x1C05F0`，其中 `push 0x00DBFD04` = `getchallenge 0 "%s"` | `evidence\dis_oob_full.out.txt` |
| 目标 OOB 接收器 `0x1C13A0`，引用 `challengeResponse`/`connectResponse` | `evidence\locate_local_battle_entries.out.txt` |
| 状态门 `[0x76446B0] ∈ {3,4,5,6}` + 节流 3000 ms / 100 / 500 | `evidence\dis_oob_full.out.txt` |
| 增量类型分派器 `0x5F830`；类型表 `0x460550`(314) / `0x4606E4`(136) | `evidence\dump_typetables.out.txt` |
| 分派器调用链 `0x5F830 ← 0x208432 (in 0x208380) ← 0x1FFB88 (in 0x1FF820) ← 0x20059B` | `evidence\delta_chain_context.out.txt` |
| configstring 区域的 `0x25`/`0x92` 禁用字节规则在目标**不存在** | `evidence\check_forbidden_bytes.out.txt` |
| netchan 分片尺寸常量 1154 出现的 4 处候选 | `evidence\netchan_sigs.out.txt` |

---

## 6. 纪律声明

- 全程**只读**；未修改原始游戏 EXE / DLL / 运行时镜像 / 抓包 / 既有证据。
- 未修改 `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005`；未修改冻结服务器源码。
- 未启动游戏、未注入、未 hook、未断点、未写内存。
- 未执行真实客户端 E2E；本报告**不声称**任何 E2E 通过。
- 所有临时脚本与输出均位于本任务目录内。
- 未把启动链或大厅匹配作为本任务阻塞条件。
