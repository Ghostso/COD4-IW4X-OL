# EARLY_SERVER_05 — 早期版本 vs 现有 CODOL 差异分析

> 阶段 5 交付物（第 1 件）。目标：以**现有可进入大厅的 CODOL** 为基准，比较早期版本。
> 所有指纹为只读实测（SHA-256）。证据标签沿用任务书术语。**未观察 ≠ 不存在。**

---

## 0. 七问速答（详见下文各节）

1. **早期服务端是否具备独立战斗能力？** —— **冲突保留**：作者自述「incomplete port, not playable」（README + PORT.md:3537）；
   docs 声称 2026-09 真人 C1 游玩过；**本快照 qconsole 仅 bot 会话（184 条 status 全 humans=0）**。
   结论：**架构具备、面向真人 C1 的可玩性未被本快照证实**（详见 §3）。
2. **是否有共享协议/模块证据？** —— **是（CONFIRMED）**：客户端字符串表与 CoDOL 二进制符号、IW4 系谱、RVA 交叉引用（§2）。
3. **哪些功能现客户端可直接用？** —— 契约层：明文 OOB 连接文法、`sh1x_status`、准入名册、loopback RCON、lobby↔战斗服文本契约（§5.1）。
4. **哪些需适配？** —— 加密传输记录层、netchan/分片、clc 分发、gamestate/snapshot 序列化（§5.2）。
5. **哪些仅供理解？** —— `codol/player|weapon|vehicle|script` 大量 1.1.1.13 领域逻辑（§5.3）。
6. **现有 Lobby 能否在明确接口边界上配合？** —— **能（CONFIRMED，文本契约）**（§6）。
7. **是否有比从零更短路径？** —— **是（路线 B/C）**（见 `EARLY_SERVER_05_SHORTEST_PATH.md`）。

---

## 1. 可执行文件与模块指纹（CONFIRMED）

| 项 | 早期（AlphaBuild） | 现有（COD OL） |
|---|---|---|
| 客户端形态 | **单体 exe** | **exe + Base.dll** |
| 主程序 | `codoMP_client_shipRetail.exe` 20,918,752B | `codoMP_client_shipRetail.exe` 7,841,344B |
| SHA-256 | `904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6` | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |
| 大模块 | （内嵌于单体 exe） | `codoMP_client_shipRetailBase.dll` 60,327,992B SHA `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |
| FileVersion | 1.1.1.13 | 1649370 |
| 时间戳 | 2014-03-03 | exe 2021-05-08 / Base.dll 2020-02-25 |
| ImageBase/EP | 0x400000 / 0x844917b | 0x400000 / 0xe5dc690 |

- **服务端侧**：早期样本自带 `dedicated\bin\codol_dedrun.exe`（8,469,493B，SHA `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a`，x86，IB 0x400000，EP 0x1480，185 `Plugin_*` 导出）。
- **现有项目**：`CODOL-Combat-Server-v0.1`（C#，UDP 28960）+ `CODOLServer`（逆向成果）——均**无**早期那样完整的原生服务端二进制。

> **差异要点**：早期为**单体 exe**，现有为**瘦 exe + 巨型 Base.dll**。这改变了"协议代码在哪个模块"的定位策略，但不改变**线协议**（见 §2）。

---

## 2. 共享协议/模块证据（CONFIRMED）

- **系谱**：`lobby/README.md`（实测）：C1.exe 携带 `iw4\code_source\src\universal\com_memory.cpp`、
  `iw4\game\pc\codoMP_client_shipRetail.pdb`；254 个 IW4 GSC 常量名逐字存在；`hudelem_s` 与 IW4 逐字节相同；
  `gentity_s` = IW4 + 0x58。→ **CODOL 是 IW4 分支**（测量结论，非假设）。
- **协议符号交叉引用**（阶段 3）：客户端字符串表 `bdNATTravClient::receiveFrom @0x8271132`、
  `bdDTLSAssociation::sendInit @0x8273624`、`bdDTLSData::serialize @0x8275952` 等 ↔ 服务端
  `codol_network.c` / `codol_handshake.c` / `codol_association.c` 分支，**逐条对应**（见 `03_PROTOCOL_MATRIX.csv`）。
- **服务端骨架**：`codol_dedrun.exe` 是 CoD4x fork（IW3 底座）+ CoDOL 叠加层；`SV_ExecuteClientMessage`
  （`sv_client.c:2412`）读 3 位 clc opcode；下行 `SV_WIRE_SERVERCOMMAND=1`/`SV_WIRE_EOF=5`（`sv_snapshot.c:61-62`）。

> **注意**：共享协议证据来自**早期客户端↔早期服务端**对照。现有客户端是否使用**相同 wire 值**，
> 需现有客户端侧证据（现有项目已有部分：`lobby/docs/protocol_map.md` 实测 svc 值、`0x81/0x82/0x83` 为 GSC VM opcode 的 REFUTED 结论）。

---

## 3. 可玩性冲突（必须保留，不强行统一）

| 证据源 | 主张 | 标签 |
|---|---|---|
| `dedicated/README.md` | "This is an incomplete port, not a playable CoDOL server." | CONFIRMED（文本） |
| `docs/CODOL_PORT.md:3537` | "Required before a client can play" 6 项未完成 | CONFIRMED（文本） |
| `docs/CODOL_IMPLEMENTATION_PASS.md`（6942 行日志，2026-09-24/25/28/29） | MP perk 链、43/43 killstreak、Zombies、M4A1 渲染、bots 达 CS_ACTIVE、`map_restart`、12 bots Killhouse | STRONG_CANDIDATE（自述日志） |
| `docs/CODOL_MP_TRIAGE_20260929.md:13` | "A later isolated C1 process joined and played Killhouse with 12 Recruit bots..." | STRONG_CANDIDATE（自述日志） |
| `bin/home/main/qconsole.log`（本快照 2026-10-11） | 184 条 status 全 `humans=0 bots=12`；`CoDOL menucmd` 与 bot 命令配对 | CONFIRMED（本快照运行态） |

**正确表述**：docs 声称 9 月真人 C1 测试通过战斗基线；**本快照自身运行日志未证实真人 C1 可连入当前打包 build**。
不得把 docs 声称当作本快照实测，也不得据 bot-only 日志否定 docs（时间/构建可能不同）。

---

## 4. 数据结构与资源加载差异

- **玩家/实体**：服务端 `gentity_s`/`playerState` 扩展见 `codol/snapshot/codol_playerstate_ext.c`(64KB)、
  `codol_entity_fields.inc`(30KB)；现有项目在 C# 侧独立重建（`MotionSnapshot.cs`、`SessionDescriptor.cs`）。
- **武器 wire ID**：CoDOL 1024 vs 引擎 128 槽（PORT §3）；现有 C# 亦未完成武器映射。
- **configstrings**：6519 条，武器从 5362 起（PORT §4）——两端都**未收敛**。
- **资源格式**：早期 `bin/home/codol_rawfiles`(1341 GSC) + `sh1x_svr_scripts.iwd`(4.28MB)；
  lobby `zones/`(3 py) 读 `.ff`；`paths.py` 指向游戏安装 `client_shipRetail\chinese\*.ff`。

---

## 5. 复用分层（对应 Q3/Q4/Q5）

### 5.1 现客户端可直接使用（契约层，A 类）
- 明文 OOB `getchallenge`/`connect` 文法（`codol_connect.c`）。
- `sh1x_status` 状态行（`codol_match_status.c`）。
- 准入名册（`codol_admission.c`）。
- loopback RCON 控制面（`net_game.c:43-53`）。
- lobby↔战斗服文本/文件契约（`startgame.txt`/`game_admissions.txt`/`securitykey.bin`）。

### 5.2 需兼容适配（B 类）
- bdDTLS 记录层（crypto/association/handshake/ecdh）——**先解冲突 A/B**。
- netchan + 分片（`codol_netchan.c`/`codol_wire.c`）。
- clc 3 位 opcode 分发（客户端生产端待确认）。
- admission / CODOL_PORT。
- gamestate/configstrings/snapshot 序列化（**核心阻塞**）。

### 5.3 仅供理解（C 类）
- `codol/player|weapon|vehicle|script` 的 1.1.1.13 领域逻辑（版本锁定）。
- 早期 docs 与 lobby docs 的逆向笔记。

---

## 6. 与现有 Lobby Server 的配合边界（CONFIRMED）

- **契约**：lobby 写 `resources/mpdata_s.<uid>`、`startgame.txt`、`game_admissions.txt`、`native_server_rcon.txt`；
  战斗服读名册行 `<ipv4> <key:32hex> <uid:16hex|0> <expires> <gamertag>`；lobby 轮询 `sh1x_status`；
  经 RCON 发 5 条命令（`set fs_game`→`set codol_sessionMap`→`set codol_zoneType`→`set g_gametype`→`map`）。
- **语言无关**：纯文本文件 + 明文 RCON + 文本状态行 → **现有 C# 战斗服可复用同一契约**，无需共享源码。
- **边界未闭合**：`startgame.txt`/`mpdata_s.<uid>` 的完整字段语义。

---

## 7. 外部依赖与平台耦合

- 早期服务端：Win32 x86，单进程；依赖 `home/` 下资源与游戏安装（`paths.py` BUILD_ROOT）。
- lobby：Python 3.13 + Docker（可选）；无认证。
- 现有 C# 战斗服：Windows `csc.exe`，零第三方依赖。
- **许可**：早期引擎底座 = **AGPL-3.0**；现有 C# 声明未复制 CoD4x/iw4x 源码（`LICENSE_POLICY_REUSE.md`）。
  若移植 AGPL 源码片段，须按 AGPL 发布（法律决策，超出本轮）。
