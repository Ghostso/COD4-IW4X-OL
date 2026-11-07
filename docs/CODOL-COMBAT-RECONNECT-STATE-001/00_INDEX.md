# 00 — 轮次报告 / ROUND REPORT — CODOL 最终版战斗服务器：断线/重连状态管理 001

**任务**：`CODOL-COMBAT-RECONNECT-STATE-001` — 在 `CODOL-Combat-Server-v0.1` 内实现**身份门控**的断线与重连状态管理
**目标版本**：CODOL 3.9.9.7 / 2.6.9.7（本地逆向事实源不变；本轮**未**引入任何未验证的 2697 字段）
**日期**：2026-10-13（Asia/Shanghai）
**本轮性质**：**正式服务器代码实现 + 构建 + 自动化测试**（未另起工程）
**上游依据**：`CODOL-COMBAT-LIFECYCLE-001`（连接生命周期）、`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001` §02 步骤 5/8（身份与断线语义）
**冻结基线**：未触碰（`GOLDEN-LOBBY-001`、`REF_LOBBY_KIT`、`_e1_regression/ol-mod-olfinal`、`tests/golden_*.hex`、`config/firingrange-gamestate.bin` 全部原文未改）

---

## 1. 实际修改了哪些代码

| 文件 | 变更 |
|---|---|
| `src/Engine/PlayerIdentity.cs` | **新增**。`ReconnectMode` / `IdentityKind` / `PlayerIdentity`（`connect` 身份解析）/ `PlayerRestoreRecord`（可恢复记录，按类型不含传输字段） |
| `src/Engine/ClientSession.cs` | 新增 `Identity`、`Restored` |
| `src/Engine/ClientLogic.cs` | 重连缓存 + 身份门控恢复 + 释放时登记 + 超窗淘汰 + 停机清空；`connect` 解析身份；新增重连计数 |
| `src/Engine/ServerConfig.cs` | 新增 `reconnect_policy`（off/identity）与 `reconnect_window_ms`；未知值 → Off 并 WARN |
| `src/Engine/ServerHost.cs` | `reconnect_window_ms` 启动校验；CFG 打印策略（Off 时显式说明"不恢复"） |
| `src/SelfTest.cs` | **新增第 10 节（40 项断言）** + `CmdConnect` / `ConnectPlayer` / `ReconnectCfg` 夹具 |
| `config/combat_server.cfg` | 文档化两个新键；默认 `reconnect_policy = off` |

> 源文件数 22 → **23**（新增 `PlayerIdentity.cs`）。上一轮源码指纹 `4738710b…` → 本轮 `99e98dc8…`。

---

## 2. 关键决策：身份依据从哪来，凭什么敢恢复

### 2.1 证据
- **`connect` 命令携带 `\name\` 与 `\xuid\`** —— 实机抓包逐字复刻于 `CodolClientReplay.OobConnect`：
  `connect e7c8a98a6b4c2d0e "\name\TTctRThTNkNsaWVudA==\xuid\e7c8a98a6b4c2d0e\natType\1"`
  审计 `…REVERSE-COVERAGE-001` §02 步骤 5 记为 **CONFIRMED**（但**仅 3.3.3.3**；2697 未观测）。
- **断线/重连语义 = UNKNOWN**：同审计 §02 步骤 8 ——「服务端侧清理/重连语义**未分析**（BQ-09）」。
- **本服没有任何服务端校验依据**：无票据、无签名、无权威账号后端 ⇒ `\xuid\` 只能是**客户端自述**。

### 2.2 由此确定的三条纪律（已落到代码）
1. **身份键只取 `\xuid\`，绝不使用 ip:port**。`PlayerIdentity.Key` 只可能返回 xuid；`ReconnectCache` 的键是 xuid。
2. **默认策略 = `Off`（从不恢复）**。只有运维显式写 `reconnect_policy = identity` 才启用；该配置在日志里被显著标注为"xuid 为客户端自述，未校验"。
3. **新会话不继承任何传输状态**。可恢复记录 `PlayerRestoreRecord` **按类型**不含 Cookie/ServerTag/ClientTag/TransportKey/SendSeq/NetchanSeq/ClientReliableAck/GameState*/Snapshot*/LastRxMs/Stats*，"旧密钥跨会话残留"在类型层面无法表达。`ApplyTo` 还会**二次复核 xuid** 才写入。

---

## 3. 各类终止路径的清理语义

| 触发 | 代码路径 | 是否登记可恢复记录 | 会话/槽位/玩家实体 | 计数 |
|---|---|---|---|---|
| `cancelConnect`（客户端取消） | `HandlePlain` → `DropSession(s,"cancel")` | **是**（若策略 Identity 且已 connect 且有 xuid） | 立即回收槽位；`Player.Connected=false` | `Dropped++` |
| **握手超时**（未取到传输密钥，`state < Connected`） | `SweepTimeouts` → `DropSession(s,"timeout")` | **否**（未 connect ⇒ 无玩法状态可恢复） | 同上 | `Timeouts++` |
| **静默超时**（已 connect，无收包 > `sv_timeout_ms`） | `SweepTimeouts` → `DropSession(s,"timeout")` | **是** | 同上 | `Timeouts++` |
| **正常断开** | — | — | — | **v0.1 未观测到客户端的"正常断开"命令**（审计 §02 步骤 8 = UNKNOWN/BQ-09）；当前唯一的正常终止路径是服务器关闭。**如实标注为未闭合**，未伪造实现 |
| **服务器关闭** | `ServerHost.Dispose` → `ClientLogic.Shutdown` | **否**（显式排除） | 全部会话回收 | `Dropped++`，且 `_reconnect.Clear()` |

其它边界：
- **满员拒收**（`sv_maxclients`）：在 init-ack 阶段就返回，**不消费也不套用**任何重连记录（测试 I3/I4）。
- **重复 connect**（同一会话再次发 connect）：只在**首次** connect 判定身份与恢复，不重复计数、不重复套用（测试 G1/G2）。
- **超窗记录**：`Update()` 每 tick `PruneReconnect`，超 `reconnect_window_ms` 即淘汰（测试 J2/J3）。

---

## 4. 字段级策略：**哪些可恢复、哪些被重置**（验收明确项）

### 4.1 可恢复（身份域内的玩法状态，`PlayerRestoreRecord`）
| 字段 | 说明 |
|---|---|
| `Player.X/Y/Z` | 位置 |
| `Player.VX/VY/VZ` | 速度 |
| `Player.Pitch/Yaw/Roll` | 视角 |
| `Player.OnGround` | 落地状态 |
| `ClientSession.IsAiming` / `AimFraction` | 瞄准（长按态） |
| `Equipment.Backpack`（1/2） | 背包——**决定整套 loadout**（经 `SelectBackpack` 重建，与运行期路径一致） |
| `Equipment.SelectedSlot` | 当前武器槽索引（越界则忽略） |

### 4.2 必须重置（新会话自行建立，**不**跨会话）
| 字段 | 原因 |
|---|---|
| `Cookie` / `ServerTag` / `ClientTag` | 每次 DTLS init 重新签发 |
| `TransportKey` | 由新 cookie + 新 ECDH 重新派生（`ReferenceEquals(s1.TransportKey, s2.TransportKey) == false`，测试 E10） |
| `SendSeq` / `NetchanSeq` | 新会话从 0 / 1 起（测试 E9：新 seq < 旧 seq、新 netchan == 1） |
| `ClientReliableAck` / `ClientReliableCommand` | 可靠命令序号重新累积 |
| `GameStateSent/Attempts/DueMs/Loading` | 重新主动下发首个 game state |
| `SnapshotDueMs/Sent/Attempts/EpochMs` | 快照周期重新起算 |
| `LastRxMs` / `CookieTimeMs` | 计时器重新起算 |
| `InputBaselines` / `ProcessedInputTime` / `InputPackets` | 输入基线由客户端重建 |
| `StatsChunks` / `StatsSaved` | 统计分块重新上传 |
| `Player.Move` / `Player.Buttons` / `LastCommandTime` / `InputsProcessed` | 输入时序——恢复"上一刻还按着前进"是错的（测试 E8） |

### 4.3 当前工程根本不存在、因此不恢复
血量 / 伤害 / 弹药消耗 / 得分 / 击杀 / 武器世界模型 —— v0.1 均未实现（无 BSP/Clip、无 `G_Damage`）。恢复语义留待这些系统落地后再定。

---

## 5. 安全边界落实（对应任务"安全边界"）

- **不复用旧会话对象**：`DropSession` 从 `_byPeer` / `_cookies` 移除；新会话一律由 init-ack 分支 `new ClientSession(...)` 新建。测试 E2/E10 断言 `s2 != s1`、cookie/密钥非同一实例。
- **旧密钥/cookie/序列/握手状态不残留**：见 §4.2 与测试 E9/E10。
- **不凭地址认定同一玩家**：F1 用**完全相同的 ip:port**、不同 xuid，断言**不恢复**；E2 用**不同地址**、相同 xuid，断言**恢复** —— 两条合起来证明判定只由 xuid 决定。
- **缺少可靠身份依据时不伪造连续性**：无 `\xuid\` → `RestoreNoIdentity` 且不恢复（F2）；默认策略 Off → 一律不恢复（D1–D3）。

---

## 6. 新增自动化测试（第 10 节，共 40 项，全部通过）

| 组 | 覆盖 | 项数 |
|---|---|---|
| **K** | 身份解析：用**真实抓包字符串**解出 xuid/name；无 xuid / 非 connect 形状 / 空 xuid → None；大小写规范化；`Verified` 恒 false | 7 |
| **D** | `reconnect_policy=off`（默认）：释放不登记、同 xuid 重连按新玩家、位置回出生点 | 3 |
| **E** | `identity` + 同 xuid：位置/速度/视角/瞄准/背包装备恢复；输入时序重置；**序列回到全新起点**；cookie/密钥非复用；记录一次性消费 | 11 |
| **F** | 身份隔离：同地址不同 xuid 不恢复；无 xuid 不恢复；同 xuid 同时在线不接管 | 3 |
| **G** | 重复 connect 不重复计数、不重复套用 | 2 |
| **H** | 静默超时后重连可恢复（`reason=timeout` 也登记） | 3 |
| **I** | 满员时重连被拒、不消费记录、释放槽位后恢复 | 6 |
| **J** | 超窗淘汰 + `shutdown` 不登记且清空缓存 | 4 |

**原有用例全部保持通过**：第 1–9 节 137 项未变。

---

## 7. 实际执行的构建与测试

| # | 项目 | 命令 | 结果 |
|---|---|---|---|
| B-1 | 可重复构建 (release) | `powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1` | **BUILD OK**，`sources: 23`（1 条既有告警 `ClientCommandReader.cs(213) CS0675`） |
| T-1 | 离线自测（全 10 节） | `build/bin/CODOLCombatServer.exe --selftest` | **通过 177 项，失败 0 项，exit=0** |
| T-2 | 来源指纹 | `--fingerprint` | `99e98dc8e18808b80ce4434f564889c93fbe42c2be8cb2657e018a6c2152c2c4` == `BUILD_MANIFEST.txt` 的 `source_sha256` |
| R-1 | 运行时冒烟：默认策略 | `--run +set port 28963` | **成功**：`reconnect_policy=Off reconnect_window_ms=30000 (不恢复状态: 默认策略…)`，监听 28963，进入主循环 |
| R-2 | 运行时冒烟：显式启用 | `--run +set port 28964 +set reconnect_policy identity` | **成功**：`reconnect_policy=Identity … (仅按 xuid 恢复玩法字段；xuid 为客户端自述，未校验)` |

**NOT_RUN（明确标注，未以离线测试替代）**
- `NOT_RUN` — **真实 CODOL 客户端端到端兼容**：本服仍从未被真实客户端连接（`收包=0`）。本轮全部结论均为**服务端自证**，**不构成**任何"客户端可互通"主张。
- `NOT_RUN` — 2697 客户端侧 `0x02/0x04/0x06` 消费链、snapshot 帧边界（T-01/T-02/T-03/T-04）、2697 战斗通道真实字节（T-05）。
- `NOT_RUN` — 交互式 Ctrl+C 停机（本机非控制台会话无法投递控制事件；`Shutdown()` 由测试 J4 直接覆盖）。
- `NOT_RUN` — ol-mod（L1）插件线与 booking/DedicatedControl 接线。

---

## 8. 仍然阻塞 / 未闭合

| # | 项 | 原因 |
|---|---|---|
| BL-1 | 真实客户端互通 | 结构性：无同 SHA-256 客户端运行时镜像；ACE 使内存读取失效（审计 BLK-1/2/5/6） |
| BL-2 | **"正常断开"语义** | v0.1 未观测到客户端正常断开命令；`cancelConnect` 是唯一已捕获的客户端主动终止（审计 §02 步骤 8 = UNKNOWN/BQ-09）。本轮**未伪造**该路径 |
| BL-3 | 重连后的战斗连续性 | 移动/碰撞/弹道/伤害未实现，恢复的也只有位置/视角/装备这些 v0.1 已有字段 |
| BL-4 | 在线会话接管（同一 xuid 双连） | v0.1 不做接管（F3 已固化该行为）；需要 2697 证据才能定义"踢旧留新"语义 |
| BL-5 | 玩家身份可信性 | `\xuid\` 无服务端校验依据；启用 `identity` 是运维的显式风险决定，不是已验证的账号绑定 |

---

## 9. 下一项可以直接执行的代码修改

1. **把恢复记录接进世界实体表**（本工程）：`GameWorld` 目前每帧从 `_logic.Sessions` 重建玩家列表；改为维护 `slot → PlayerState` 权威表，使重连后**实体索引稳定**（现在槽位可被他人占走）。直接解锁 M5 的"退出/重连实体一致性"。
2. **`--run --max-seconds N`**（本工程，约 10 行）：让"启动→清理"可自动化，把本轮 R-1/R-2 的人工 kill 变为可断言用例。
3. **booking/DedicatedControl 最小接线**（副本工程，`T-07`）：源码已在 `_e1_regression/ol-mod-olfinal/src/backend`，在本服侧实现 booking 六步离线回归并消费 `SessionExporter` 的端点/密钥（不动 Golden）。

---

## 10. 哈希

- 改动文件与产物 SHA-256：见 `CHANGED_FILES.tsv`。
- 构建/自测原始日志：`V0_3_BUILD_AND_TEST_LOG.txt`；运行时冒烟：`V0_3_RUN_SMOKE_OFF_POLICY.txt` / `V0_3_RUN_SMOKE_IDENTITY_POLICY.txt`。
- 本目录交付物哈希：见 `SHA256SUMS.txt`。
