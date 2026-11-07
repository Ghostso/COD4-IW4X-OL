# CODOL 服务器侧进度评估（截至 2026-10-09）

**评估对象**：`ol-mod-olfinal` 的服务端子系统 + 并行的 `CODOLServer` 协议逆向轨道
**评估基准**：会话工作区 `D:\BaiduNetdiskDownload\使命召唤OL`，工程副本 `_e1_regression\ol-mod-olfinal`（HEAD `2a75bdd`，`OLfinal-live`）
**口径**：只读采集。凡本工作区内无实物证据者一律标注为"文档自述"或"无法独立复核"。
**证据分级**：✅ 可复核（代码/日志/哈希/清单） · 📄 文档自述 · ❓ 未知

---

## 0. 一页结论

| 子系统 | 代码 | 离线测试 | 实机证据 | 综合状态 |
| --- | --- | --- | --- | --- |
| 后端 DW3 控制面（Auth3/LSG/service/matchmaking/booking/持久化） | ✅ 10,458 行 | ✅ 通过 | 📄 有，**本区无实物** | **功能已重建，未成为独立 daemon** |
| 专用游戏服务器（帧/快照/usercmd/Pmove） | ✅ 95,729 行 | ✅ 通过 | 📄 有，**本区无实物** | **可跑通单局骨架，非完整 playable** |
| 武器 / 伤害 / 实体 / 碰撞 | ✅ | ✅ 通过 | 📄 有 | **普通玩家子集闭环，通用 `G_Damage` 未完成** |
| GSC/Lua 脚本层 | ✅ | ✅ 通过 | 📄 有 | **VM+registry 已建，无 thread/wait/通用 notify** |
| 原生引擎绑定 `EngineBindings` | ✅ 18,029 行 / 146 RVA / 82 前缀 | ❌ **不在任何测试目标** | — | **面向 `out.exe`，宿主身份被 B1 阻断** |
| 传输（DTLS/netchan/UDP） | ✅ 2,480 行 | ✅ 新增真 socket 生命周期测试 | 📄 有 | **语义闭环，真机长时未复验** |
| 游戏模式（SD）+ 僵尸/Factory | ✅ 大量 | ✅ 通过 | 📄 有 | **SD 回合状态机不完整；Factory 内容最成熟** |
| 部署/运行 | ✅ 5 插件 + 1 owner + 44 项 overlay | — | ✅ 沙箱 44/44 齐备 | **就绪但未注入** |
| CODOLServer 协议逆向（并行轨道） | — | — | — | **层一已通，第一档⑤卡住** |

**总判断**：服务器侧的**离线重建已经相当深入**（约 15 万行服务端代码、8 个测试目标全部可构建、9 套契约测试有记录通过），但**端到端实机验收尚未发生**——卡在两处：**宿主身份 B1**（`out.exe` 缺失）与**多客户端 room owner 接线**。此外，**最关键的 9 个插件专属文件（31,953 行）不进入任何测试目标**，这是当前最大的工程风险。

---

## 1. 工程结构与规模

### 1.1 代码量（实测，仅 `src/` 与 `tests/`）

| 目录 | 文件 | 行数 |
| --- | --- | --- |
| `src/game_server` | 173 | **139,300** |
| ├ `server_mp` | 134 | 95,729 |
| └ `qcommon` | 8 | 2,480 |
| `src/backend` | 61 | 10,458 |
| `src/shared` | 10 | 2,557 |
| `src/localnetworking` | 6 | 1,351 |
| `src/platformwrapper` | 7 | 701 |
| `src/client_bridge` | 2 | 220 |
| `tests` | 14 | 40,178 |

### 1.2 构建目标（`xmake.lua`，实测 16 个）

| 组 | 目标 |
| --- | --- |
| 插件 | `ol_localnetworking`（`LocalnetworkingRe.Ayria32`）、`ol_platformwrapper`（`PlatformwrapperRe.Ayria32`）、`ol_backend`（`AlwaysofflineRe.Localnet32`）、`ol_game_server`（`CodolGameServer.Localnet32`） |
| 服务进程 | `ol_room_owner`（`ol_room_owner.exe`，共享 room/booking roster owner） |
| 测试 | `ol_backend_tests`、`ol_game_server_tests`、`ol_playerdata_def_tests`、`ol_dedicated_control_tests`、`ol_lua_runtime_tests`、**`ol_transport_lifecycle_tests`**、`ol_localnetworking_tests`、`ol_platformwrapper_tests` |
| 辅助 | `ol_localnetworking_fixture`、`ol_archived_tls_probe`（probe）、`ol_deploy`（phony） |

工具链：xmake ≥ 3.0.9、MSVC x86、`c++latest`、static MT、LTO、vcpkg OpenSSL + mhook + nlohmann_json 3.12.0 + Lua 5.4.8（静态）。

### 1.3 进程角色（`src/shared/ProcessRole.hpp`）

`OLMOD_PROCESS_ROLE` = `combined`（默认，兼容旧单进程）/ `client`（backend 依附客户端 socket bridge）/ `dedicated`（仅游戏服务器）。**后端尚未成为独立网络 daemon**——这是文档明确承认的边界（`backend.md:7`）。

---

## 2. 后端（DW3 控制面）进展

### 2.1 已重建的链路

`backend.md:23-41` 给出的主链路：

```text
room request → service 0x0B handler → event 8 push → local ready committed
  → service 0x15 task 5, query kind 1 FIND_SERVERS → Session.Role=server
  → service 0x06 task 14 mmbook → event 21 accepted → task 14 mmstart
  → BookingSink → DedicatedBookingDispatcher worker
  → client bridge 在 Com_Frame 捕获原生 booking selection + item-ID loadout
  → backend entitlement 校验 → versioned SessionStart
  → dedicated 线程自行解析资产并配置 booking
```

| 组件 | 状态 | 关键实现 |
| --- | --- | --- |
| **Auth3** | ✅ 已重建 | task 28 恢复 `userId/sessionKey`；ticket/LSG/房间/dedicated `SessionStart` 共用 `AuthSession` |
| **玩家身份持久化** | ✅ 闭环 | `PlayerIdentityStore` 按 `1004/<USERID>/Identity.json`；改名经 `setDisplayName` 原子持久化；非法档案 fail closed |
| **LSG / TitleUtilities / Friends2 / InstantMessage / ContentUnlock2 / Marketplace / Profiles2 / Storage2** | ✅ 已重建 | 各 service 独立源文件（`src/backend/Demonware/*.cpp`） |
| **Matchmaking** | ✅ 闭环 | query kind `1`=FIND_SERVERS、`3`=FIND_LOBBIES_BY_PLAYLIST；`Session.Demonware` 作为 opaque descriptor 原样保存回显（不重写） |
| **Booking 转交** | ✅ 闭环 | `mmbook → mmstart → BookingSink → DedicatedBookingDispatcher`（单 worker、递增 request ID、capture 失败最多重试 3 次） |
| **Entitlement** | ✅ 部分 | 依据 CODOL `CODOL_ItemAvailability_Query 0x695BC0` 的两类来源；secure unlock/rank 条件**未**成为完整输入 |
| **Marketplace** | ✅ 闭环 | task 203 返回全部 115 项；永久物品 `expireDateTime=UINT32_MAX` 归一化 |
| **Storage2** | ✅ 闭环 | `0x0A/10` 上传、`0x0A/12` 下载；按 BO2 PDB 命名为 `bdStorage::uploadFile/getFile`；原子替换 |
| **共享 room owner** | ✅ **新完成** | `SharedRoomSessionOwner` + `ol_room_owner.exe`（loopback 端口默认 28970）；按 XUID 持有 display name / bridge port / token / ready；同 XUID 重连生成新 token；generation-scoped roster freeze 幂等 |
| **多成员 SessionStart** | ✅ schema v5 | 可编码通用成员数组；dispatcher 逐成员 bridge capture 原生 selection/loadout，要求 selection 一致，按各自 XUID 校验 entitlement，全成功才原子发送 |

### 2.2 后端剩余缺口（文档自述）

- **后端未脱离客户端进程**：`client` 角色下仍是进程内 Localnetworking socket bridge，没有独立 daemon。
- **launcher 多实例**：多 client 进程清单、每实例唯一 identity/bridge **未完成**。
- **两个真实客户端**的自然 `room → ready → capture → connect → snapshot` 验证**未发生**。
- **改名卡上层事务**（资格、扣除、唯一性、敏感词）未实现。
- **首次 clean launch 的库存 UI cache** 是否无需购买即稳定显示仍是独立边界。
- `0x0B/1/9/10/11` 语义未知；`0x0B/task 4` 仍是通用 channel broadcast。

---

## 3. 专用游戏服务器（authoritative gameplay）进展

### 3.1 目录清单确认的子系统（`src/game_server/server_mp/`，134 文件）

帧调度、client ingress、usercmd 队列、shared Pmove、native playerstate/entitystate、snapshot、gamestate、碰撞、子弹、伤害、死亡、半径伤害、手雷（发射/飞行/接触/引爆/爆炸）、近战、导弹、装备、奖励、记分板、脚本 builtin/Lua/source、地图触发器、MapEnts、Forge（bundle/image/publish）、无人机/连杀、battlechatter、alpha 武器/Barrett、反延迟、可破坏物、弹道轨迹、use object、perks、playlist 等。

### 3.2 广度优先恢复矩阵（`codol_server_function_matrix.json`）

**实测统计（39 条目）**：

| 维度 | 分布 |
| --- | --- |
| 分类 | `server_only` 27 / `embedded_server` 6 / `client_shared` 6 |
| 实现状态 | **`partial` 38 / `missing` 1**（`g_run_frame_for_entity` 为 missing） |
| 置信度 | `high` 35 / `medium` 4 |

**依赖缺口最多的条目**（即最不完整的核心）：

| 条目 | 缺失依赖数 |
| --- | --- |
| `g_damage`（G_Damage） | 9 |
| `fire_weapon` / `client_think_real` | 8 |
| `pmove` / `player_die` | 7 |
| `client_impacts` / `client_spawn` / `client_disconnect` / `bullet_process` / `sv_write_snapshot_to_client` / `bg_update_player_dobj` | 5 |

> ⚠️ **该目录已过期且目标错误**：`updated_at = 2026-08-16`，其 `reference_builds.codol.idb_path` 指向 **`Call of Duty Online [3.3.3.3 QA Build] (2015-06-15)`**。而源码在 `2026-08-18`（提交 `55fcdbf`）已翻转到 `out.exe`（1649370）。**目录的 CODOL 参考构建与源码目标不一致**——与哈希误用属同一类问题。

### 3.3 覆盖表的评级（`game_server_coverage.md`，2026-08-16）

该表要求 `source → native → wire → client consumer` 四段都有证据才算闭环。**实测评级分布（抽样读取）**：

| 链路 | 状态 |
| --- | --- |
| 身份与 slot | **闭环，高**（双客户端名字/slot 自然验证） |
| `ET_PLAYER` 身份与类型 | **闭环，高** |
| 记分板玩家行 | **闭环，高**（roster presence/team + 基础 score） |
| ingress/netchan | **闭环，高** |
| per-client snapshot baseline | **闭环，高** |
| 客户端 parse/ACK | **闭环，高** |
| `packet clients` 基础记录 | 部分，中高 |
| clientInfo 角色组合 | 部分，中高（最终 DObj 待验证） |
| 世界武器模型 | 部分，中高（普通枪 append 未闭合） |
| 动画与姿态 | 部分，中高 |
| 命中/伤害/死亡 | 部分，中高（pain/view kick/score/killcam/respawn 未闭环） |
| usercmd 队列所有权 | 部分，中高 |
| shared Pmove | 部分，中高 |
| 固定 server frame | 部分，中高 |
| 序列化/DTLS/UDP | 部分，中高 |
| 多客户端性能 | 部分，中 |
| entity snapshot 可见性 | 部分，中（CODOL per-client PVS policy 未恢复） |
| 世界模型缩放 | 部分，中高（`1.0f` 初始化 producer 未定位） |
| **SD 模式全部 10 条链路** | **部分，中～中低**（回合状态机、炸弹、安装/拆除、2D/3D objective 均未闭环） |

### 3.4 源码审计覆盖（`codol_gameplay_source_audit.json`，2026-10-01）

223 条 review：

| coverage | 条数 |
| --- | --- |
| `symbol` | 141 |
| `full_file` | 39 |
| `function` | 32 |
| 未标注 | 11 |

scope = `src/game_server/**.{cpp,hpp}`。**`coverage=symbol` 只证明命名函数/逻辑块，不等于整文件审计完成。**

### 3.5 GSC/Lua 脚本层（`gsc.md`）

- ✅ 官方 **Lua 5.4.8** 静态 VM 已落地（内存 text source、generation、结构化 error/traceback、source/内存/指令预算限制；不开放 package/io/os/debug/ffi）。
- ✅ VM 无关的 **`kind:name` builtin registry**（`sv_script_builtin_mp.*`）已建：值边界覆盖 undefined/bool/int/number/string/vector/object reference；结构化错误区分未知 binding/参数/receiver/对象缺失/非 Playing/未持武器。
- ✅ `method:getvelocity/isonground` 只读 authoritative world；`method:setweaponammoclip/setweaponammostock` 经 `SvServerWorld` 受控 mutation 并夹紧。
- ✅ 地图脚本按 `common.lua → gametypes/<gt>.lua → maps/<map>.lua` 顺序加载，缺文件 `continue` 容错。
- ❌ **无 thread/coroutine、无 wait/endon、无通用 notify、无生产 loader**。
- ❌ 完整 P0 builtin 表仍有大量 `missing`（ADS/sprint/spawn weapon、perk、完整 damage/death、通用 entity spawn/delete）。
- ✅ 已确认：CODOL 客户端**没有**通用 GSC compiler/VM，authoritative GSC 必须由 `ol_game_server` 承载。

---

## 4. 原生引擎绑定层（`EngineBindings`）——最大的单点风险

| 指标 | 实测值 |
| --- | --- |
| `EngineBindings.cpp` | **18,029 行** |
| `EngineBindings.hpp` | 146 个 `*Rva` 常量 |
| `EngineBindings.cpp` | 82 个前缀守卫数组、82 处 `std::equal(` 校验 |
| 门禁点 | 4 处（`bind()`、`DedicatedProcessPatches` ×2、`ClientProcessPatches` ×1） |
| 宿主身份常量 | `ExpectedTimestamp=0x6096930A`、`ExpectedImageSize=0x0E5D6000`、`ComFrameRva=0x0FEA20` |

**状态**：
- ✅ 该层是"CODOL 引擎 ↔ 重建服务端"的唯一桥梁，已完成 146 个 RVA 的绑定与前缀校验。
- ❌ **宿主身份被 B1 阻断**：期望的是去壳 `out.exe`（记录哈希 `044c396c…257F9`），但工作区只有加壳零售客户端（`36997674…`，`SizeOfImage=0x0E659000` ≠ 期望 `0x0E5D6000`）。
- ❌ **该层不在任何测试目标内**（见 §6.2）。

---

## 5. 传输层

| 组件 | 状态 |
| --- | --- |
| DTLS（CODOL P-224 ECDH、`NET_DtlsPacket` INIT→INIT_ACK→CHALLENGE→CONNECT） | ✅ 有固定向量测试（`ServerCoreTests.cpp:27411-27494`） |
| netchan 分片重组 / ACK / reliable / ring | ✅ 已重建，📄 自述 60 秒自然运行 `snapshot=1201`（≈19.97 Hz）、`accepted=1743 / rejected=0` |
| usercmd delta（`0x005A1BE0`） | ✅ 按本体 writer 恢复 |
| UDP socket 生命周期 | ✅ **新增** `ol_transport_lifecycle_tests`（2026-10-09）：loopback bind、`start()` 幂等、端口冲突、`stop()` 清理、重绑、粘性错误、占用端口失败、INADDR_ANY 语义；**真 socket，非内存模拟** |
| 长时稳定性 | ⚠️ 未复验 |

---

## 6. 构建、测试与部署

### 6.1 构建与测试记录（工作区日志）

| 记录 | 内容 | 结果 |
| --- | --- | --- |
| `_build_olgs.log`（13:46） | xmake v3.1.1 + MSVC 2022 x86 release，OpenSSL/mhook/Lua 安装成功 | ✅ |
| `_run_tests.log` | `ol_game_server_tests` / `ol_dedicated_control_tests` / `ol_playerdata_def_tests` | **exit 0**（3 套） |
| `_batch1/2_build.log`、`_p1_*.log`、`_a6_build.log` | `ol_transport_lifecycle_tests` 反复构建+运行 | **exit 0** |
| `_t1_compat.log` | `ol_game_server` 重链，产物 `6,556,672 B / 0EABD5F5…` | ✅ |

`_run_tests.log` 打印的具体断言覆盖（节选）：`LIVING_WEAPON`、`ZM_REVIVE`、`FACTORY_DOOR`、`FACTORY_PRESENTATION`、`ZM_ROUND_COLORS`、`ZM_CORPSE`、`ZM_NUMBER_WIRE`、`ZM_FX_PACKET`、`ZM_DEATH_FX`、`ZM_FACE_GLOW`、`FACTORY_POWER`、`FACTORY_PERKS`、`FACTORY_AMMO`、`BATTERY_HUD`、`FACTORY_PAP_GATE`、`FACTORY_BO1_TRAVEL`、`FACTORY_TELEPORT` 等。

### 6.2 ⚠️ 测试覆盖缺口（本轮确认）

`xmake.lua` 中 `game_server_core` 只包含 `client_bridge/`、`ClientProcessPatches.cpp`、`ClientAnimtreeHook.cpp`、`ClientRenderFrameHook.cpp`、`DedicatedProcessPatches.cpp`、`DisconnectWitness.cpp`、`PlayerDataDef.cpp`、`qcommon/`、`server_mp/`、`win32/`、`shared/`。

**只有 `ol_game_server`（生产插件）才编译以下 9 个文件**：

| 文件 | 行数 |
| --- | --- |
| `Appmain.cpp` | 9,520 |
| `EngineBindings.cpp` | 18,029 |
| `NativePmoveBindings.cpp` | 2,024 |
| `NativeWeaponMovementBindings.cpp` | 661 |
| `NativeWeaponBindings.cpp` | 434 |
| `ClientNoclipHotkey.cpp` | 262 |
| `NativeEntityStateBindings.cpp` | 199 |
| `ClientCommandTrace.cpp` | 749 |
| `FrameHook.cpp` | 75 |
| **合计** | **31,953** |

即：**约 3.2 万行、承载 54 个导出与全部 RVA/前缀校验的插件边界，零直接测试**。这是当前服务器侧最严重的工程风险。

### 6.3 部署状态

- `distribution/runtime-components.json`：titleId 1004、x86、15 项 destination（2 legacy + 5 rebuilt + 2 config + 5 资源目录 + 1 launcher）。
- overlay manifest：44 条目，每项都有 `source` / `installPolicy` / 恢复条件。
- 沙箱 `E:\CODOL_SANDBOX\RUN001`：`Ayria\` 44/44 齐备（`Injector32.exe`、`Bootstrapper32.dll`、4 插件、`ol_room_owner.exe`、`Launch_OLMod.bat`、Assets）。
- 沙箱插件 `CodolGameServer.Localnet32` = `6D493B82…6B2021`（13:49 构建），**与两个"当前构建"（`0EABD5F5…`、`21D14817…`）都不同**。
- `ol_deploy` 会在 `config/codol-game-dir.txt` 非空时自动调用 `InstallCodolRuntime.ps1`；该文件当前指向一个不存在的目录。

---

## 7. 游戏模式与内容

| 模式/内容 | 状态 |
| --- | --- |
| **SD（搜索摧毁）** | 部分，中～中低：能分队出生、击杀失能，但**回合不完整结束/重开**、炸弹创建/拾取/掉落不正确、**不能 plant/defuse**、2D objective 用户不可见、3D waypoint wire 已实现但实机不可见、回合计时/比分/HUD 未闭环 |
| **Factory（僵尸图）** | **最成熟**：电源/升桥/蒸汽、perk 购买、弹药补充、电池 HUD、神秘箱、滑门、传送器、Pack-a-Punch 门、特殊奖品、合作倒地救援、回合配色、尸体、伤害数字、记分牌、导航/窗口入口、可编辑房间 |
| **多人 FFA / Nuketown** | 📄 同构建双客户端实测记录存在 |

> ⚠️ Factory 的多数参数（概率、权重、清理策略、移动轨迹）是**重建策略**而非恢复的原版值，文档已明确标注。

---

## 8. 并行轨道：`CODOLServer` 协议逆向

这是与 `ol-mod-olfinal` 并行的另一条服务器侧工作线（`CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md`，7074 行 / 55+ 小节）：

| 项 | 状态 |
| --- | --- |
| 层一 `.ff` 解密 | ✅ 全线打通（明文在 `_cleanout\ff_layer1\`） |
| 层二 `.ff` 解密 | ❌ 未完成（`Base.dll` 的 `.tls` 受 VMProtect 保护） |
| 第一档① `0x81` 握手 | ✅ 闭合 |
| 第一档② `0x82` / `+0x5FC` | ✅ 闭合 |
| 第一档③ `0x83` 回显 | ✅ 闭合 |
| 第一档④ `0x85` 帧结构/方向/seq/AES-CBC/HMAC | ✅ 闭合（多次交叉验证） |
| **第一档⑤ 状态机推进** | ❌ **未闭合，卡点已定位**：客户端收到 `0x85` 后内层流首字节不是 `0x87`，导致 `0x87` arm 分支不进入、`[obj+0x644]` 恒为 0 |
| `ICH059`（PRCL `.tls` scheduler） | `NOT_LOCATED`——`.tls` 中的 API 名全是 import name table 条目，不是调用点；`0x00CA0000` 的 90 次出现全在 VM bytecode/数据中 |

---

## 9. 当前阻塞与风险（按严重度）

| # | 阻塞 | 影响 | 状态 |
| --- | --- | --- | --- |
| **B1** | 宿主身份：`out.exe`（`044c396c…`）缺失；现有客户端加壳且 `SizeOfImage` 不匹配 | **全部实机验收** | **BLOCKED** |
| **B2** | 启动客户端/注入需授权 | 全部实机验收 | BLOCKED |
| **R1** | 9 个插件专属文件（31,953 行）零测试 | 插件边界正确性不可验证 | **未处理** |
| **R2** | 后端未成为独立 daemon；launcher 多实例未完成 | 多客户端 room/booking | 部分完成（owner 已建，接线未做） |
| **R3** | 地图 `.ff`：`mp_crash_tropical` 已离线解包可用；`mp_nuked` 解包失败 | 实机进图 | 部分解除 |
| **R4** | 文档与代码漂移：`codol_server_function_matrix.json`（8-16，指向 3.3.3.3）、`game_server_coverage.md`（8-16）、`game_server.md`（10-02）均落后于 10-09 的代码 | 评估失真 | 未处理 |
| **R5** | `.runtime/` 在本工作区**不存在** | 所有"自然实机运行"证据**无法独立复核** | **重要** |

> ⚠️ **R5 特别说明**：模块文档引用了大量形如 `.runtime/natural-match/20260809_.../summary.json` 的运行证据，但该目录被 `.gitignore` 忽略且**本工作区内不存在**。因此本报告中所有"自然实机验证"均只能标注为**文档自述**，不构成本工作区可复核的事实。

---

## 10. 建议的下一步优先级

| 优先级 | 事项 | 理由 |
| --- | --- | --- |
| **P0** | 获取 `out.exe`（或来源说明 + 完整 SHA-256） | 解除 B1 的唯一路径；否则所有服务器实机验收无从谈起 |
| **P0** | 把 9 个插件专属文件纳入测试目标（至少导出面/生命周期冒烟） | 3.2 万行零覆盖是最大工程风险 |
| **P1** | 裁定唯一工程基准（F vs D） | 避免在错误副本上继续构建 |
| **P1** | 修正文档漂移：matrix 的 CODOL 参考构建、`GOLDEN_COPY_SPEC` G1 默认哈希、`EngineBindings.hpp:434-437` 过期注释 | 消除跨构建误用 |
| **P2** | 完成 launcher 多实例 + 两个真实客户端的 `room → ready → capture → connect → snapshot` 验证 | 解除 R2 |
| **P2** | 通用 `G_Damage`（non-player/车辆/穿透） | 矩阵中缺失依赖最多（9 项） |
| **P3** | SD 回合状态机与炸弹交互 | 当前唯一"模式级"不完整项 |
| **P3** | GSC thread/wait/通用 notify | 脚本层能力上限 |

---

## 附：本评估的证据边界

- ✅ **可复核**：代码规模、目标清单、常量/前缀计数、目录统计、构建与测试日志、插件哈希、部署清单、Git 历史、目录 JSON。
- 📄 **文档自述**：全部 `.runtime/...` 实机运行、双客户端 FFA 实测、性能数字、玩家确认结论。
- ❓ **未知**：加壳客户端解壳后与 `out.exe` 的等价性；`out.exe` 本体是否存在；SD/僵尸内容在真实客户端上的实际表现。

---

*本文件由只读评估生成；采集过程未修改任何既有文件、未构建、未测试、未部署、未注入、未启动任何进程。*
