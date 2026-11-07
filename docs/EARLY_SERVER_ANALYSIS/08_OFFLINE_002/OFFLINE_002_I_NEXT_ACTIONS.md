# OFFLINE_002 — I：下一步建议与最小验证任务

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §7（回答六个收束问题 + 给出下一步最小任务）。
> 输入：只读。**本文件只提建议，不执行任何运行验证。** 派生脚本/证据仅写 `08_OFFLINE_002\`。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## I.0 六个收束问题（逐条回答）

### 问 1：当前协议基线哪些已确认、哪些仍未知？
- **已确认（CONFIRMED）**：明文 OOB（NAT/QoS/getchallenge/connectResponse）、bdDTLS INIT/COOKIE/DATA **外层记录**、DATA MAC **构造**（四实现）、serverCommand=1 / EOF=5、**会话描述符 258B = 33 字段 + securityKey field#15@147**、服务端 gamestate/configstrings/snapshot **编码路径（源码级）**。
- **强候选（STRONG_CANDIDATE）**：观测会话原语 = SHA1 派生 + AES-128；本会话 COOKIE_ECHO = 219B；**CODOL 自定义 svc opcode 空间 2/3/5/1**（REF + 真实客户端实测旁证）。
- **仍未知/阻塞（UNKNOWN / INSTRUMENTATION_BLOCKED / NOT_OBSERVED）**：**snapshot opcode**（原生 `0x00` vs REF "still unknown"）；客户端 svc 分派表 / 解码入口 / `CS_PRIMED` 转换点（VMProtect）；clc 生产端；真实会话 8B MAC 逐字节复算；258B 37B 短地址 vs 67B 长地址实机对应；序列化器产出可被客户端解析。详见 `OFFLINE_002_PROTOCOL_BASELINE.md` P.1/P.2。

### 问 2：会话描述符字段编号是否已经统一？
- **是，已裁决（CONFIRMED）**：**field#15**（258B 记录，0-based，含 5 个前置字段）与 **field#19**（`session_desc.pickle`，28 字段）是**两个不同结构**上的两个索引，**不是**零基/一基冲突（字段总数 33≠28、索引差 4≠1）。**不需要强行统一**；统一口径 = "两套独立结构各自编号"。详见 `OFFLINE_002_C_DESCRIPTOR_INDEX_REVIEW.md`。

### 问 3：服务端编码入口和客户端解码入口分别在哪里？
- **服务端编码入口（CONFIRMED，源码级）**：
  - gamestate：`sv_main.c:3939 SV_WriteGameState` →（CODOL 分支）`codol_sv_state.c:119 CODOL_WriteServerGamestate` → `codol_configstrings.c:288 CODOL_WriteGamestate`。
  - snapshot：`sv_snapshot.c:224 SV_WriteSnapshotToClient` → `codol_sv_snapshot.c:241 CODOL_PrepareServerSnapshot` → `codol_snapshot.c:8 CODOL_WriteSnapshotDeltaNumber`。
  - 出网：`sv_snapshot.c:642 SV_SendMessageToClient` → `:688 SV_Netchan_Transmit`。
- **客户端解码入口**：
  - **字符串存在（CONFIRMED）**：`CL_ParseGamestate: begin parse`@`0x849358`、`bad command byte`@`0x849388`、`configStrings: %d`@`0x849210`、`CL_GetSnapshot: truncated`@`0x846370`、`non-SNAPFLAG_BASELINE…Discarding packet`@`0x848f70`、`EXE_AWAITINGGAMESTATE`@`0x86b724`。
  - **入口 RVA / 语义 = UNKNOWN / INSTRUMENTATION_BLOCKED**：关键串 xref 为空或落在 VMProtect 加壳区；`CS_PRIMED` 转换点未定位。详见 `OFFLINE_002_E_SERIALIZER_CLIENT_MAP.md`。

### 问 4：gamestate / configstrings / snapshot 中哪一部分可以直接复用？
- **没有一段达到"可直接复用"（CONFIRMED 级）**。
- **服务端编码器源码自洽 = CONFIRMED**；**可复用性 = CANDIDATE**：
  - gamestate/configstrings 的 **opcode 空间（2/3/5/1）**有 REF + 真实客户端实测旁证 → 移植信心提升，但 **payload 无字节级比对**。
  - **snapshot opcode 与 6 段 payload 均未与客户端比对** → 最不可复用。
  - 差分 codec（`codol_delta.c`，自述 C1 `sub_5A0510`）= **STRONG_CANDIDATE**。
- **明确排除**：C# `MotionSnapshot`（263B gamestate / 单段 29 字段）**不得**作为原生 CoDOL 的验证替身（`OFFLINE_002_H` H.3/H.6）。详见 `OFFLINE_002_H_ROUTE_COMPARISON.md`。

### 问 5：当前进入本地战斗的最大阻塞是什么？
- **闸门 = 面向真实客户端的下行世界帧序列化 + 客户端可解析性**（`04_BLOCKERS.md` K1）。拆解为本轮三大阻塞：
  1. **BLK-1 无游戏层载荷抓包**（`wiretap_report.md:185`：No game-layer events）→ 阻塞所有逐字节验证。
  2. **BLK-3 snapshot opcode 未定**（原生 `0x00` vs REF unknown）→ 直接决定客户端能否解析快照首字节。
  3. **BLK-2/BLK-4 客户端 VMProtect 加壳 + 解码入口未闭合** → 无法静态确证客户端期望格式。
- 传输层（219B + SHA1/AES128）**不再是首要闸门**（001 已裁决基线）；真正卡点是**序列化器 payload 的客户端接受性**。

### 问 6：下一步最小验证任务是什么？
- 见 I.1（分 Tier，均**需另行授权**；本轮**不执行**）。

---

## I.1 下一步最小任务（按价值/前置排序，只建议）

| 序 | 任务 | Tier | 前置 | 预期收益 | 是否需授权 |
|---|---|---|---|---|---|
| **N1** | **闭合 snapshot opcode**：从客户端 svc 分派表定位 snapshot 比较常量，或用一份带 snapshot 载荷的下行抓包实测首字节 | 0/1 | 未加壳客户端或带载荷抓包 | 直接判定 `0x00` 是否被接受（当前最大闸门） | 需（抓包/调试） |
| **N2** | **获取一份含完整 gamestate/snapshot 载荷的下行抓包**（非 `pkt[:128]` 截断） | 1 | 受控单会话 | 对原生序列化器产出做**逐字节比对** | 需 |
| **N3** | **定位客户端解码入口 + `CS_PRIMED` 转换点** | 1 | 动态调试或未加壳版本 | 给出双端映射的客户端侧确切 RVA | 需 |
| **N4** | **闭合真实会话 8B MAC 逐字节复算**：受控单会话记录完整 24B key（绑定 seq）或同期 ECDH 私钥/共享 X | 1 | 密钥上下文采集方案 | 把 A 从"部分裁决"升级为"逐字节裁决" | 需；密钥不落盘 |
| **N5** | **确认目标运行时唯一 16B securityKey** + 闭合 37B/67B 地址形态 | 0 | 部署参数核对 | 消除传输密钥分叉（静默丢包）风险 | 需 |
| **N6** | **对齐 clc_* 客户端生产端布局** | 0/1 | 客户端反汇编 | 输入解析不错位 | 需 |
| **N7** | **解阻 lobby→battle booking**（ol-mod 源码不在本机） | 外部 | ol-mod 仓库 | 打通 booking → battle endpoint | 需外部输入 |

**最小充分集（若只能做一件事）**：**N2**（一份带完整载荷的下行抓包）——它同时为 N1（snapshot opcode）与序列化器逐字节比对提供唯一数据源。**若无法取得抓包**，退而求其次做 **N1 的静态分支**（客户端 svc 分派表），但受 BLK-2 约束。

---

## I.2 停止条件核对（§7）

| §7 停止条件 | 是否触发 | 处理 |
|---|---|---|
| 关键源文件缺失 | 否 | 服务端 `codol\` 源文件齐全（D 报告） |
| 客户端对应路径无法定位 | **是** | 已标 **UNKNOWN/INSTRUMENTATION_BLOCKED**（E 报告），列出 N1/N3 |
| 字段编号无法从真实解析逻辑确定 | 否 | 已裁决（C 报告） |
| 序列化器编码格式仍然未知 | 部分 | 服务端格式**已确认**；客户端可解析性 **UNKNOWN** → 未用推测填补，列出 N1/N2 |
| 证据相互冲突且无法解释 | 部分 | svc 编号系已解释为自定义空间；snapshot opcode 保留 UNKNOWN |

**结论**：触发"客户端对应路径无法定位"与"序列化器（客户端侧）仍未知"两项 → 已按要求**保留 UNKNOWN 并列出最小后续任务**，未用推测填补。

---

## I.3 本轮**不**做的事（约束重申）

- **不启动**服务端/客户端；**不执行** `.cmd`/未知脚本。
- **不修改**原始样本、捕获文件、既有报告；**不新增补丁**；**不实现服务端**。
- **不输出**认证口令/私钥/密钥材料（仅记录哈希与长度）。
- **不进行**运行验证——I.1 全部任务**须另行授权**后方可执行。

---

## I.4 复算/核对命令（只读）

```
Get-Content -LiteralPath '...\EARLY_SERVER_ANALYSIS\08_OFFLINE_002\OFFLINE_002_PROTOCOL_BASELINE.md'
Get-Content -LiteralPath '...\EARLY_SERVER_ANALYSIS\08_OFFLINE_002\OFFLINE_002_G_SERIALIZER_BLOCKERS.md'
Get-Content -LiteralPath '...\EARLY_SERVER_ANALYSIS\08_OFFLINE_002\OFFLINE_002_H_ROUTE_COMPARISON.md'
```
