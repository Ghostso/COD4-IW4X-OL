# 02 — 战斗连接与初始化链路重建 / BATTLE ENTRY & INITIALIZATION

**任务**：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001` 第二阶段
**起点**：已成功进入大厅的现有基线（`GOLDEN-LOBBY-001`，3.3.3.3 客户端）。
**目标版本**：2.6.9.7（凡证据来自 3.3.3.3/1.1.1.13 者**显式标注**，不得当作 2697 已确认）。

> **两条并行链，关系 = UNKNOWN，必须分开描述**
> - **L1 = ol-mod 线**：进程内插件 `CodolGameServer.Localnet32`，目标 3.3.3.3；有全源码；**从未初始化成功**（引擎绑定门禁）。
> - **L2 = 协议逆向线**：`REF_LOBBY_KIT\battle_server.py`（UDP 28960 独立进程），目标 3.3.3.3；有**真实抓包**；卡在 booking 应答与对局地址路由。
> 二线**不可互换**（`COMBAT_SERVER_CALLCHAIN_MAP.md` CS-D14 / U-5）。

---

## 步骤 1 — 客户端从大厅进入战斗的触发点

| 项 | 内容 |
|---|---|
| **结论** | 触发点 = 大厅控制面 **`21/5 findSessions`** 命中后下发 **session 对象**，随后 **`6/14 mmbook → mmstart`** 走 booking。 |
| **置信** | `PARTIALLY_CONFIRMED`（L2 有真实运行 + 源码；L1 入口未定位） |
| **证据** | `battle_server.py`；`DEV-BOOKING\MVP-PVE-MATCH-ENTRY-009.md` §8；`CODOL_SERVER_PROGRESS_20261009.md` §2.1 |
| **调用链/地址** | 客户端（3.3.3.3）：`QuickMatch 0x6F2C10 → 0x6F0940`；client allocation entry `0x6E4A20`（=FIND_SERVERS 路径，**非** authoritative server startup）；`mmbook accepted` 处理 `0x6E6F60`；`mmstart` 构造 `0x6E6BF0`；room ready `0x6E5320`；room singleton slot `0x078B0708` |
| **数据流** | `room ready(event 8) → FIND_SERVERS(0x15/5 kind=1) → Session.Role=server → mmbook(0x06/14) → event 21 accepted → mmstart` |
| **缺口** | L1 的「冻结大厅基线 → 载入 `CodolGameServer.Localnet32`」在历史中**无记录**（U-1）；原版引擎的战斗/会话创建函数（`Createserver` 之外）**UNKNOWN**（U-2） |

---

## 步骤 2 — 战斗服务器地址、端口与会话参数来源

| 项 | 内容 |
|---|---|
| **结论** | 战斗端点**由大厅下发**（**不是客户端常量**），来自 **21/5 findSessions 的 session 对象**（258 B 记录），其中夹带 **16 B `securityKey`**（ECDH 派生的一半输入）与 `Hostaddress ip:port`。 |
| **置信** | `PARTIALLY_CONFIRMED`（endpoint 布局与下发通道 VERIFIED；对实际客户端是否被采纳 = **CONFLICTED/UNKNOWN**） |
| **证据** | `CODOL-Combat-Server-v0.1\README.md`（权威会话描述符）；`SessionDescriptor.cs`；`SessionGolden.cs`（`gen_session_golden.py` 由 `codol_crypto.py` 生成）；`CODOL_SERVER_PROGRESS_20261009.md` §2.1 |
| **端口** | 28960/UDP（`sv_network_mp.hpp:56`）、28961/TCP（`DedicatedControl.hpp:16`）、28962/TCP（`:17`）、28970/TCP（`SharedRoomControl.hpp:14`）、4200/TCP（`Localnetworking.hpp:27`） |
| **数据流** | `lobby 21/5 → build_session_record(host_ipv4,host_port) → 客户端解析 endpoint+securityKey → 连 UDP 28960` |
| **关键否证** | **CS-D10**：600 s 抓包中客户端把对局流量送 **外部腾讯 `101.67.36.18:10035`**（发送方 `gcloudvoice.dll`）；`28960` 出现 **0 次**。地址下发来源**未定位**（U-7）。 |
| **缺口** | 2697 客户端的 session 对象字段布局/版本未验证；`securityKey` 不一致会**静默丢包** |

---

## 步骤 3 — 客户端实际连接的进程、模块与网络端点

| 项 | 内容 |
|---|---|
| **结论** | 客户端进程（`codoMP_client_shipRetail.exe`）有 **9 处 socket() 创建点**；战斗可用 **AF_INET+SOCK_DGRAM+IPPROTO_UDP**；socket 抽象类 **vtable 0xD8E3A8**、ctor **0xC65D30**、工厂 **0xC65D70**（分配 0x24 B）。 |
| **置信** | `CONFIRMED`（2697 客户端静态）；**实际连接目标** = `CONFLICTED/UNKNOWN` |
| **证据** | `14_SERVER_KNOWLEDGE_ATLAS_001\04_NETWORK_TRANSPORT.md` §2–3（EV-Battle-Sockets、EV-C-2697-NetCalls） |
| **地址** | `socket()` 调用点：`0x77FC11`(AF_IPX)、`0xAD6D7F`(来自描述符,可被 `[edi+0x1B8]` 钩子接管)、`0xBB18B9`(AF_INET+UDP)…共 9 处；`recv` IAT 调用点 `0x602441/0x6029BE/0x6052AD/0x784F7F/0x788135`；`sendto 0x775AA2` |
| **数据流** | 描述符 → socket 工厂 → `[edi+0x1B8]` 钩子（可作为端点接管的潜在切入点） |
| **缺口** | 未证明客户端最终把战斗流量导向我方 28960；`[edi+0x1B8]` 钩子的实际语义未闭合 |

---

## 步骤 4 — 战斗连接建立及初始化的必要消息

| 项 | 内容 |
|---|---|
| **结论** | 真实抓包记录的完整握手（**3.3.3.3 客户端**，`battle_srv.log` 21:28:19–21:28:24）：<br>`NAT 0x0D(29B) → INIT 0x01(16B) → INIT_ACK 0x02(38B cookie) → COOKIE_ECHO 0x03(219B=38 cookie+…67+u64 1+100B 公钥) → COOKIE_ACK 0x04(114B: 100B 服务端公钥@[6:106]+01@106) → DATA 帧(0x06 16B 头+cipher)`。 |
| **置信** | `CONFIRMED`（真实抓包 + 源码，客户端 3.3.3.3）；对 C-2697 = `UNKNOWN` |
| **证据** | `REF_LOBBY_KIT\BATTLE_SERVER_PROTOCOL.md` §1；`battle_server.py`；`codol_crypto.py` |
| **数据帧封装** | `06 02 <serverTag:2> <seq:2> <hmac8> <len:2> <cipher(len)>`；`serverTag` 取自 `cookie[14:16]`；AES 流密钥 = `SHA1(ECDH共享x(28B BE) ‖ securityKey(16B))→24B`；计数器 seed=`seq(2)|0000|serverTag(2)`；`hmac8=HMAC-SHA1(key24,[0:6]‖[14:])[:8]` |
| **曲线/密钥** | P-224 (secp224r1)，公钥 100 B；抓包中 `securityKey` = 16×0x01 |
| **DATA 头字段** | `[0:2]=06 02`，`[2:4]=tag/counter(LE16)`，`[4:6]=counter16`，`[6:14]=MAC8`，`[14:16]=len`，`[16:]=cipher` |
| **2697 差异** | 2697 传输层常量精确匹配 OLD 源码（分片 1162 / 上限 128 / 掩码 0x1fffffff / `ceil(2^37/1162)`）；但**记录层握手是否同构**对 C-2697 未验证 |
| **缺口** | `COOKIE_ECHO` 189（源码）vs 219（抓包）对应哪一版本（CONFLICT-01/BQ-10） |

---

## 步骤 5 — 玩家加入、身份关联与初始状态建立

| 项 | 内容 |
|---|---|
| **结论** | 玩家加入走 OOB 命令流：`getchallenge`(54B) → `challengeResponse` → `connect`(463B，含 `\name\TTctRThTNkNsaWVudA==\xuid\…`) → `connectResponse` → `stats`(855B，`<index:1><total:u16=826><826B>`) → `statResponse` → `heartbeat`(30B，每 1s)。 |
| **置信** | `CONFIRMED`（真实抓包，3.3.3.3）；对 C-2697 语义务必重验 |
| **证据** | `BATTLE_SERVER_PROTOCOL.md` §1 表 5–8 |
| **数据流** | `connect` 携带 name/xuid → 服务端关联身份 → `stats` 826B 分块同步客户端统计 |
| **缺口（L1）** | `client_t` 状态机 `CS_FREE→CONNECTED→CS_PRIMED→CS_ACTIVE`（ol-mod 语义状态机 `sv_client_mp.hpp:61-69`）；`SV_ConnectionlessPacket`(`sv_client_mp.cpp:492`)、`SV_GetChallenge`(`:3262/3360`)、`SV_DirectConnect`(`:3384`) —— **从未真实运行** |

---

## 步骤 6 — 地图及游戏模式初始化

| 项 | 内容 |
|---|---|
| **结论** | 服务端**主动**下发首个 game state（263B，含 `g_gametype`/`mapname`/`coop`），**不等** 客户端发 `gamestateupdate`（客户端从不发它；抓包 0 次）。 |
| **置信** | `PARTIALLY_CONFIRMED`（263B gamestate 与"主动下发"行为 VERIFIED；客户端能否消费 = `UNKNOWN`） |
| **证据** | `BATTLE_SERVER_PROTOCOL.md` §0.1/§0.1-②；`battle_selftest.py` 第 ⑧ 步 |
| **2697 服务端写入链** | `SV_SendClientGameState → _CODOL2697_WriteNativeGamestate(门控) → _WriteGamestate 0xA21B8 → _WriteConfigstrings 0xA0468`（VERIFIED，仅**服务端侧**） |
| **2697 地图挂载** | `_CODOL_MountTarget2697Archives 0x1400C3` + `_CODOL_Target2697ArchivesActive 0x140133`（判 `[edx+0x34]==0x16D`） |
| **资源** | 2697 `runtime-assets`（1.797 GB）、`scripts`（1,341 文件） |
| **缺口** | 2697 configstring 6519 条索引语义（BQ-19）；客户端 `0x03` gamestate parser、`0x04` configstring 外层分帧 = `UNKNOWN` |

---

## 步骤 7 — 首次进入游戏世界、接收世界状态

| 项 | 内容 |
|---|---|
| **结论** | 服务端下发**运动快照**（124 B/帧，`snap_hz` 默认 = tick 128 Hz）；快照字段序列**29/29 对齐实录**。早期合成 snapshot 使客户端**越过 `waiting for player data`**，但**世界全黑、玩家不在有效出生状态** —— 不得当作"进入对局"。 |
| **置信** | `PARTIALLY_CONFIRMED`（快照字段形状 29/29 对齐；实际世界 = `UNKNOWN`） |
| **证据** | `BATTLE_SERVER_PROTOCOL.md` §7.7；`playable_architecture.md:192-218`；`battle_selftest.py` 第 ⑪ 步（共 276 条） |
| **2697 快照写入** | `_CODOL2697_WriteSnapshot 0xA4FA0 → _WriteSnapshotReached 0xA4860 → 分段 writer → 区域复制`；`_CODOL2697_PrepareHistory 0xA249D`；区域拼接常量 `0x728 / 0x2C38 / count*0x1F8 / count*0x13C / count*0x5C` |
| **客户端解码候选** | snapshot delta 解码 `0x6E060`/`0x6D340`（BLOCKED） |
| **缺口** | snapshot 帧边界（BLK-5/BQ-17）；delta 基准；实体字段范围；首个 snapshot 的 EOF/子段语义 |

---

## 步骤 8 — 断线、连接失败及重连处理路径

| 项 | 内容 |
|---|---|
| **结论** | **未闭合**。观察到两类现象：客户端对 booking 失败**每 5 秒重试**；错误 booking 信封导致 **9/9 断连**。服务端侧清理/重连语义**未分析**（BQ-09）。 |
| **置信** | `UNKNOWN`（仅现象，无实现） |
| **证据** | `STAGE_REPORT_BATTLE.md` P0-3；`BATTLE_SERVER_PROTOCOL.md` §9.1–9.12；`11_OPEN_QUESTIONS.md` BQ-09 |
| **2697 服务端** | 关闭/资源销毁路径未分析 |
| **缺口** | 超时判定、ACK 重传调度（BQ-13）、断线清理、重连状态回滚 |

---

## 附：从现有大厅基线出发的**第一个证据支持的未完成节点**（L1）

> **`EngineBindings::bind()` 的宿主映像身份门禁**（`EngineBindings.cpp:3647-3667`）。
> 门禁要求宿主 exe `SizeOfImage == 0x0E5D6000`（且 `TimeDateStamp == 0x6096930A`）——这是**去壳 `out.exe`**（`044c396c…257f9`）；本机唯一存在的客户端映像是加壳零售件 `SizeOfImage = 0x0E659000`（`36997674…`）。
> 真实运行证据 ×3（2026-10-10 15:47:48 / 15:48:28 / 15:50:14）：三次均为 `[combined/game-server] engine binding failed`，且**无任何 stage 日志**。
> 消费点：`Appmain.cpp:7133-7137`（失败即 `return`）；`FrameHook.cpp:59-67`（`!bindings.valid()` ⇒ `invalid-bindings` 拒绝装帧钩子）。
> **一条阻断 100% 战斗链**：无绑定⇒无 `bindingCommitted_`⇒无 `Com_Frame` 钩子⇒无 `onServerFrame`⇒无 `NET_Frame`⇒**28960 永不监听**。
> 三条静默早退点（`:3656 / :3660 / :3666`）**当前证据无法区分是哪一条**（P0-a）。
> 最小解除证据（E-2/E-3）：运行时映像的 `TimeDateStamp`/`SizeOfImage`，以及 `0x0FEA20`(5B `55 8B EC 56 57`)、`0x8371A`(8B `83 7C 24 08 01 0F 94 C0`) 的**实际字节**——必须在放宽门禁**之前**取得。

## 附：L2 从大厅进战斗的最小闭环（唯一有实机握手的一侧）

```
6/14 mmbook/mmstart → booking accepted（格式 UNKNOWN，9/9 断连已否证靶场信封）
→ 客户端连 UDP 28960（判据：battle_srv.log 出现 RX #1 16B）
→ NAT 29B → DTLS 16B → cookie 38B → 219B → P-224 ECDH → 114B ack
→ stats → game state(263B) → 运动快照(124B)
→ 成功标准：原客户端进入实际地图（"进程没退出"不算）
```
当前**唯一硬缺口**：booking 应答帧格式 + 对局地址下发来源。

---

## 链路置信汇总

| 步骤 | 结论置信 | 目标版本适用性 |
|---|---|---|
| 1 触发点 | PARTIALLY_CONFIRMED | 3.3.3.3（2697 UNKNOWN） |
| 2 地址/端口/会话参数 | PARTIALLY_CONFIRMED（实际采纳 CONFLICTED） | 3.3.3.3 |
| 3 客户端连接进程/模块/端点 | CONFIRMED（静态）/ UNKNOWN（实际目标） | 2697 客户端静态 |
| 4 连接建立与初始化消息 | CONFIRMED | 3.3.3.3（2697 UNKNOWN） |
| 5 玩家加入/身份 | CONFIRMED | 3.3.3.3（2697 UNKNOWN） |
| 6 地图/模式初始化 | PARTIALLY_CONFIRMED | 3.3.3.3 + 2697 服务端写入 |
| 7 进入世界/世界状态 | PARTIALLY_CONFIRMED | 3.3.3.3（2697 快照 BLOCKED） |
| 8 断线/失败/重连 | UNKNOWN | 全部 |
