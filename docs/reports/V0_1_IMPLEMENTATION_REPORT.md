# V0_1_IMPLEMENTATION_REPORT.md

> 交付物 7/8 之一（任务 §四.7）
> 工程: `CODOL-Combat-Server-v0.1/`  ·  构建: `build/bin/CODOLCombatServer.exe`
> 证据日志: [V0_1_BUILD_AND_TEST_LOG.txt](CODOL-Combat-Server-v0.1/docs/evidence/V0_1_BUILD_AND_TEST_LOG.txt)
> 验收对照: [V0_1_ACCEPTANCE_MATRIX.md](V0_1_ACCEPTANCE_MATRIX.md)

---

## 0. 本轮结论（先说实话）

| 维度 | 状态 |
|---|---|
| 独立服务器目标能构建 | ✅ **已达成**（22 个源文件，`BUILD OK`，SHA-256 可复现） |
| 协议层（握手/会话/命令/快照） | ✅ **已达成**，对真实抓包字节离线复放 **122/122 全绿** |
| 地图/游戏模式初始化 | ✅ **已达成**（靶场 gamestate 259B 实机素材） |
| 权威帧循环持续推进 | ✅ **已达成**（128 Hz，服务端主动推进，实测启动后持续运行） |
| 权威会话描述符（战斗地址下发） | ✅ **本轮新增并逐字节验证**（对齐冻结参考实现） |
| **CODOL 客户端建立真实战斗会话** | ❌ **未达成** —— 本机从未观测到客户端连入 28960 |
| **玩家命令参与模拟（来自真客户端）** | ❌ **未达成**（仅离线复放真实抓包字节，非活体客户端） |
| **进入可玩战斗** | ❌ **未达成** |

**一句话**：战斗服的**服务端一侧已经完成并且自证**；卡点在**客户端为什么不来连**，
而本轮把那个卡点第一次变成了服务器侧**可导出、可校验、可定位**的东西（§3）。

---

## 1. 本轮实际新增/修改的代码

### 1.1 修好了"交付物其实是旧的"这个致命问题（★ 最重要）

构建脚本在会话开始时是**坏的**，而 `build/bin/CODOLCombatServer.exe` 存在 ——
也就是说**仓库里那个 exe 无法由当前源码复现**，任何"已交付"的说法都不成立。

| 文件 | 问题 | 修复 |
|---|---|---|
| `src/SelfTest.cs` | 第 755 / 765 行两处 `Console.WriteLine` 丢了调用前缀，留下裸字符串表达式 → `CS1002/CS1525`，**构建失败** | 补回 `Console.WriteLine(...)`，并把 `h.OutCount` 改成实际存在的 `h.Out.Count` |
| `src/SelfTest.cs` | 第 288-291 行曲线方程检查 `x^3-3x` 的 else 分支把 `p - (3x - x3)` 写成先算 `Sub(m3x,x3)` 再被 `p` 兜底，触发 `BigUint.Sub` 的 `a>=b` 前置条件 → **分节 2 整体崩溃** | 改为模意义下相减：`rhs = Sub(P, Sub(m3x, x3))` |
| `src/Engine/ServerConfig.cs` | 配置文件**不支持行内注释**：`session_playlist =  # 留空 = 1` 会把注释当值解析 → 报错 | 新增 `StripInlineComment`：行首或前面是空白的 `#` 起为注释（`logs/a#b.log` 这类值不受影响） |

修好后：**构建成功 + 自测 87/87 全绿**（修复前为 `构建失败` + `1 项失败`）。

### 1.2 新增：权威会话描述符（战斗地址下发通道）

**动机（有证据，不是猜测）**：`DEV-BOOKING` 的静态审计结论是
"客户端去哪台战斗服的地址**不由** `mmbook accepted` 下发，而由
**21/5 findSessions 的 session 对象**下发"
（`MVP-PVE-MATCH-ENTRY-009` §8：`ENDPOINT_SOURCE = CONFIRMED`）。
而那个对象里还夹带 **16B securityKey** —— 它是 ECDH 派生的一半输入。
**两侧不一致 = 传输密钥不同 = 客户端连上也会静默丢包**。

上一版战斗服**完全没有**这一层：地址和密钥只硬编码在大厅脚本里，战斗服无法自证
"我给的地址和密钥就是我实际在听的"。这是一个会**静默失败**的结构性缺口。

| 文件 | 内容 |
|---|---|
| `src/Codol/SessionDescriptor.cs`（新增，234 行） | 逐字节移植 3 种描述符：37B `bdCommonAddr`、258B session 记录、21/5 mission session 对象（24B / 67B 两种地址块）；含 `Buf` 带 tag 字段写入器 |
| `src/Codol/SessionGolden.cs`（新增，自动生成） | 4 组黄金向量（37 / 258 / 268 / 237 字节），**由生成器产出，禁止手抄** |
| `src/Engine/SessionExporter.cs`（新增） | 把本服权威描述符落盘：`session_record_258.bin`、`mission_normal.bin`、`mission_firingrange.bin`、`battle_security_key.txt`、`endpoint.txt`、`session_descriptor.json`（含 SHA-256） |
| `src/Engine/ServerConfig.cs` | 新增 `session_endpoint` / `session_addr_layout` / `session_map` / `session_gametype` / `session_maxplayers` / `session_currentplayers` / `session_playlist` / `session_export_dir` |
| `src/Engine/ServerHost.cs` | 启动时校验"会话端点 == 实际监听端点"，不一致直接 `ERROR`（不静默）；随后自动导出描述符 |
| `src/Program.cs` | 新增 `--print-session`（打印字节）与 `--export-session`（落盘） |
| `config/combat_server.cfg` | 加入会话描述符配置段（默认值与实机一致） |
| `tests/gen_session_golden.py`（新增） | 黄金向量生成器：从冻结参考实现产出，长度不符即拒绝写出 |
| `src/SelfTest.cs` | 新增 `[7] 权威会话描述符` 分节共 **27 项断言** |

### 1.3 新增：会话描述符的黄金向量自测（为什么这不是"自测自"）

自测的**对照物不是本版自己**，而是**已冻结的参考实现**
`REF_LOBBY_KIT/codol_crypto.py`（它又源自 ol-mod `MatchmakingService.cpp`
与三方 C# `CodolLocalLobbyServer.cs`）。生成器在**本机实际执行**该参考实现并固化字节，
C# 侧再逐字节比对。

覆盖 4 组黄金向量：

| 对象 | 长度 | 来源 |
|---|---|---|
| `bdCommonAddr` | 37B | `codol_crypto.bd_common_addr((127,0,0,1), 28960)` |
| matchmaking session 记录 | 258B | `build_session_record(0x1122334455667788, ...)` |
| 21/5 靶场 session 对象 | 268B | `build_mission_session_object(True)` |
| 21/5 普通 session 对象 | 237B | `build_mission_session_object(False)` |

另外还断言了三条"错了就崩"的门槛（`roomId` 非零十进制 / host uid ≠ 玩家 CODOID /
地址块长度精确 0x43 或 0x18），以及"导出记录与黄金向量的差异**只允许**落在 securityKey 区段"。

---

## 2. 关键调用链（实际代码路径）

### 2.1 初始化与生命周期（对应阶段 B.1/B.2）

```
Program.Main
 └─ ServerConfig.Load(configPath, args, log)            // 配置 + 命令行覆盖（+set / --k=v）
 └─ ServerHost.Initialize()                              // 显式阶段机，每步可定位
     ├─ Phase.Environment   pid / runtime / cwd
     ├─ Phase.Config        取值校验（tick_hz/snap_hz/port/sv_maxclients 越界即抛）
     │                      SESSION 校验：会话端点 == 实际监听？不一致 -> ERROR
     │                      SessionExporter.Export()      // ★ 本轮新增
     ├─ Phase.Logging       Logger(minLevel, file)
     ├─ Phase.MapAssets     登记 map_assets / _map_extract 下的 .ff（只登记不解析 BSP）
     ├─ Phase.GameState     GameWorld.Initialize(MapName, GameType)
     │                      LoadGameState() -> config/firingrange-gamestate.bin (259B)
     ├─ Phase.Transport     UdpTransport.Bind(127.0.0.1:28960)
     ├─ Phase.ProtocolKeys  ClientLogic: P-224 密钥对 + cookie key + securityKey
     └─ Phase.Loop          进入 Run()
```

错误退出路径：任一阶段返回 `false` → `FailReason` + `Phase=Shutdown` → `Program` 打印
`[FATAL] 初始化失败 phase=... : ...` 并返回退出码 **2**（`main` 内 `try/catch` 兜底）。

### 2.2 主循环与游戏帧调度（对应阶段 B.3）

```
ServerHost.Run()
 while (!_stop):
   ├─ 收包：UdpTransport.TryReceive × 最多 256/帧 -> ClientLogic.HandlePacket
   ├─ 权威推进：GameWorld.Frame(dt, players)   // dt 由 IClock 给出，封顶 MaxFrameTime
   │             └─ IntegratePlayer: yaw 方向水平积分 + 重力/跳跃竖直积分
   └─ 调度：ClientLogic.Update()  -> PumpGameState / PumpSnapshot
   Thread.Sleep(1)
```

`ServerHost.Frames` / `GameWorld.TickCount` 是权威推进的计数器（`--selftest` 断言 128 tick == 1000ms）。

### 2.3 网络、会话与玩家命令（对应阶段 B.5/B.6）

```
ClientLogic.HandlePacket(pkt, ip, port)
 ├─ 已有传输密钥 -> CodolProtocol.TryReadData（校验 serverTag=cookie[14:16] + HMAC-SHA1[:8]）
 │                   └─ HandlePlain
 │                       ├─ OOB：getchallenge / connect / heartbeat / stats / gamestateupdate / cancelConnect
 │                       └─ netchan：ClientCommandReader.ReadReliable + ReadInput -> UserCommand[]
 │                                   └─ 写 s.Player.Move/Buttons/Pitch/Yaw/Roll、Equipment.Step（开火/ADS）
 ├─ 阶段1 NAT：TryBuildNatReply（29B，首字节 0D -> 0C，尾部 6B 必须等于对端自身地址）
 ├─ 阶段2 DTLS init：TryBuildInitAck -> 38B cookie（FinalizeCookie 签名 + 本地地址）
 └─ 阶段3 密钥交换：TryParseKeyExchange(219B) -> P224.DeriveTransportKey -> 114B key ack
```

### 2.4 状态快照生成与发送（对应阶段 B.6）

```
ClientLogic.PumpSnapshot(s, now)            // 按 snap_hz
 └─ MotionSnapshot.Build(...)               // index-skip 位流，字段序列 29/29 对齐实录
     └─ ClientLogic.SendData -> CodolProtocol.BuildData（AES 流 + HMAC-SHA1[:8]）
```

### 2.5 权威会话描述符（★ 本轮新增链路）

```
ServerHost.Initialize (Phase.Config)
 └─ SessionExporter.Export(cfg, log)
     ├─ SessionDescriptor.BuildSessionRecord(...)         // 258B，含 37B bdCommonAddr
     ├─ SessionDescriptor.BuildMissionSessionObject(...)   // 268B 靶场 / 237B 普通
     └─ 落盘 session_descriptor/ 6 个文件 + session_descriptor.json(SHA-256)
         -> 大厅应直接消费该目录，而不是各自硬编码 IP/端口/密钥
```

---

## 3. CODOL 适配层：已证实 / 推断 / 未知（对应阶段 C）

任务 §三.C 要求逐项区分。以下是**本轮及既有证据**下的分级。

### 3.1 已证实（有实机抓包或冻结参考实现支撑）

| 项 | 证据 |
|---|---|
| 战斗服是 **UDP**，端口 **28960** | 2026-10-06 21:28 完整会话抓包（`REF_LOBBY_KIT/battle_srv.log` 2320-2564） |
| 握手四阶段：NAT 29B → DTLS init 16B → cookie 38B → 219B → 114B ack | 同上，且离线复放 122/122 通过 |
| 数据帧 `06 02 <serverTag:2> <seq:2> <hmac8> <len:2> <cipher>` | 同上 |
| `<serverTag>` 取自 **cookie[14:16]**，不是 clientTag | 同上（写错会静默丢包） |
| 传输密钥 = `SHA1(ECDH-P224 共享x(28B 大端) ‖ securityKey(16B)) + 0000` | 同上；双方独立互推一致（自测断言） |
| `securityKey` = **16 个 0x01** | 实机核实（build 1649370 ID 1） |
| OOB 文本协议：`getchallenge`/`connect`/`stats`/`heartbeat` | 抓包逐条解出 |
| 真实客户端 usercmd 明文 = 14B `01 00 00 00 | 00×8 | 00 02` | 抓包实录；自测第 (9) 步断言"必须被接受" |
| 快照 index-skip 字段序列 **29/29** 对齐 | `playerstate-motion-trace.json`（`completed=True, totalBits=497`） |
| **战斗地址来自 21/5 session 对象**（不是 mmbook accepted） | `MVP-PVE-MATCH-ENTRY-009` §8 `ENDPOINT_SOURCE = CONFIRMED` |
| 会话描述符 3 种字节形态（37B / 258B / 268B / 237B） | 本轮：与冻结参考实现**逐字节一致** |
| 客户端**不**硬编码 28960（字符串 0 命中） | `OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030` §9 |

### 3.2 推断（有间接证据，未闭合）

| 项 | 推断 | 为什么未闭合 |
|---|---|---|
| 客户端 battle UDP socket 创建点 | 位于 0xE3xxxx 模块（DTLS/ECDH/secp224 字符串所在段） | `CLIENT-BOOKING-BATTLE-TRIGGER-014` §5/§6：matching/lobby → battle **无直接 call**，是跨模块间接触发 |
| `mmbook accepted` 的正确 PvE 应答格式 | 应为"裸 blob = u32(15) + 文本，带内层长度前缀" | ol-mod 存档断言支持，但本机**没有** ol-mod 源码，也从未抓到真实 PvE 应答 |
| 会话对象地址块该用 24B 还是 67B | 靶场用 67B（`0xB95C50` 要求 0x43），普通场景未定 | 两种布局都只对齐了参考实现，**未**经客户端验证 |

### 3.3 未知（阻塞项）

| 项 | 说明 |
|---|---|
| 客户端 booking→battle 的**专属消费者** | 读 endpoint + 建 battle socket 的代码未定位（listener 注册源未找到） |
| 服务端主动下发的 `[esi+4]` listener 注册源 | `CLIENT-BOOKING-BATTLE-TRIGGER-014` §9 的 NEXT_GATE |
| `0x632680` accepted 之后如何**跨模块**触发 battle | 已否证"accepted 直接触发 battle" |
| PvE `101.67.36.18:10035` 这个地址是谁下发的 | `BATTLE_SERVER_PROTOCOL` §8.9：客户端把对战流量送去外部腾讯地址，全程 28960 出现 0 次 |

### 3.4 明确**否证**的路径（不得再当假设用）

- ❌ 28960 客户端硬编码
- ❌ `mmbook accepted` 里含 battle endpoint
- ❌ battle = TCP（证据是 UDP）
- ❌ `0x818de0` = booking→battle 分派器（实为 `chat.private`）
- ❌ `0x803830` = socket/connect（实为 transport manager 单例 getter）
- ❌ transport manager connect = battle connect（实为 Lobby 主连接）
- ❌ `0x632680` = Battle start
- ❌ 用靶场 booking 信封回 PvE booking（**9/9 断连**）

---

## 4. 未完成的功能（如实标记）

| # | 未完成项 | 具体是什么 | 为什么没做完 |
|---|---|---|---|
| 1 | **CODOL 客户端接入战斗服** | 客户端从未连 28960（`battle_srv.log` / `combat_server.log` 全程 `收包=0`） | 需要真实客户端运行；任务 §二.6 禁止擅自启动/注入客户端；且根因（§3.3）尚未定位 |
| 2 | **活体玩家命令参与模拟** | 目前只离线复放**真实抓包字节**，不是活体客户端 | 同上，依赖 #1 |
| 3 | **地图 BSP / Clip 真实碰撞与视线** | `GameWorld` 只做运动学积分，无碰撞体 | 需要 CODOL 引擎的地图数据解析（`_map_extract` 有素材但未解析） |
| 4 | **弹道 / 伤害 / 命中判定** | 完全未实现 | 需要 CODOL 战斗实体表 |
| 5 | **PvE booking 应答格式** | 未实现（靶场信封已否证） | 缺真实应答样本 |
| 6 | **多客户端 / 多玩家** | `sv_maxclients=1`（沿用实机已验证组合） | 未验证；单玩家链都没闭合 |
| 7 | **服务器列表 / 账号 / 匹配 / 管理面板** | 按任务 §三.D 明确**不做** | 属"最短闭环"之外 |
| 8 | **地图换图** | 换图必须同时提供该图 gamestate 文件 | 只有靶场 259B 素材经实机验证 |

### ★ 特别声明（任务 §三.D 明确要求）

**本版没有以"兼容 IW4x 客户端"的测试冒充 CODOL 实战验证。**
本版所有"通过"的断言，对照物是：
① 从**真实 CODOL 客户端抓包**里固化的字节，或
② 已在**本机实机验证过**的参考实现（`REF_LOBBY_KIT`）。
没有任何一条来自 IW4x 客户端。**IW4x 只用于架构阅读，未复用代码**（见 §6）。

同样，**端口监听、日志打印、模拟客户端都不作为"真实战斗创建"的证据** ——
本报告 §0 明确把"客户端建立真实战斗会话"标记为**未达成**。

---

## 5. 构建与测试

### 5.1 可重复构建

```powershell
# 1)（可选）重新生成会话描述符黄金向量 —— 需要本机 python 与 REF_LOBBY_KIT
python -X utf8 tests/gen_session_golden.py

# 2) 构建
powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1
# -> build/bin/CODOLCombatServer.exe + build/bin/BUILD_MANIFEST.txt (含 SHA-256)
# -> build/logs/build_release_<时间戳>.log
```

- 编译器：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`（本机唯一可用的本机代码链路，
  见 [TOOLCHAIN_ENVIRONMENT.md](CODOL-Combat-Server-v0.1/docs/TOOLCHAIN_ENVIRONMENT.md)）
- **零第三方依赖**，**不联网**，**不写仓库外**
- 本轮实测：`sources: 22`，`BUILD OK`

#### ★ "可重复构建"到底可重复到什么程度（本版实测，必须说清）

本机唯一的编译链路 `.NET Framework 4.0` 的 `csc.exe` **不支持 `/deterministic`**
（实测：`csc /?` 无该开关）。因此：

| 量 | 是否可重复 | 实测 |
|---|---|---|
| 产物**大小** | ✅ 恒定 | 连续多次构建均 `126464` 字节 |
| 产物 **SHA-256** | ❌ **每次不同** | 连测 3 次得到 3 个不同哈希（每次编译都有新的 MVID） |
| 自动化测试结果 | ✅ 恒定 | 122/122 全绿，退出码 0 |
| **源码指纹** | ✅ **恒定且可断言** | `61982c961396249f9f5cc9ebef9b11308e990ecd528527ef0d5412910e16bbdd` |

所以本版把"可重复构建"定义成**可验证**的形式，而不是宣称二进制逐位一致：

```
source_fingerprint = SHA256( 每源文件: 相对路径(归一化 '/') + 0x00 + 内容,
                             按路径序数排序 )        // 与时间/顺序/机器无关
```

`build.ps1` 在**编译成功之后**（★ 顺序重要：编译前算会拿旧产物描述新源码）用
`CODOLCombatServer.exe --fingerprint` 计算它，写进 `BUILD_MANIFEST.txt`；
自测分节 8 再算一次并断言相等 —— **任何源码改动都会让断言失败**，
这正是"这个 exe 确实由这批源码编译而来"的证明。

自测还用一个**合成目录**独立验证了指纹语义：写入顺序不影响结果、改一个字节会改变结果、
改文件路径也会改变结果。（本轮实测：连续 3 次 重新构建 + 自测，源码指纹稳定不变。）

### 5.2 自动化测试

```powershell
.\build\bin\CODOLCombatServer.exe --selftest      # 退出码 0 = 全绿
.\build\bin\CODOLCombatServer.exe --print-protocol
.\build\bin\CODOLCombatServer.exe --print-session
.\build\bin\CODOLCombatServer.exe --export-session
```

本轮实测：**通过 122 项，失败 0 项，全绿**（退出码 0）。
**本轮实测：通过 122 项，失败 0 项，全绿（退出码 0）。**
八个分节：① 密码学 KAT ② 大整数/P-224 ③ 协议编解码 ④ 客户端命令解析
⑤ 快照位级编码 ⑥ 端到端离线复放 ⑦ 权威会话描述符 ⑧ 构建来源指纹。

分节 ⑥ 是**复放真实抓包字节**走完整条链：NAT → DTLS → ECDH（客户端侧独立互推密钥）
→ getchallenge → connect → stats → heartbeat → 服务端**主动**下发 game state（263B）
→ 真实 14B usercmd 被接受 → 快照自动开始 → 权威帧循环推进。

---

## 6. COD4X / IW4x 复用代码及许可证（任务 §四.3）

| 上游 | 许可证 | 工作树 / HEAD | 本版复用了什么 |
|---|---|---|---|
| CoD4x_Server (`callofduty4x/CoD4x_Server`) | **AGPL-3.0** | `DEV-BOOKING/_lineage021/CoD4x_Server` @ `ddd65fc`，干净 | **仅架构分层思想**（初始化顺序、固定步长帧调度、client 槽位状态机、baseline+delta 快照概念、SV_Map 职责划分）。**零代码复制** |
| iw4x-client (`IW4x/iw4x-client`) | **GPL-3.0**（★ 本版更正；上一版误记为"未明示"） | `DEV-BOOKING/_lineage021/iw4x-client` @ `d1b175d`；`IW4X/Client核心代码/iw4x-client` @ `0699a7e5`，均干净 | **无代码复用**，仅用于确认"CODOL 属 IW4 系谱但 ABI 不同"这一**否定性结论** |

**AGPL 与 GPL 的区分（任务 §二.8 要求）**：AGPL-3.0 比 GPL-3.0 多 §13
——通过网络提供服务时须向用户提供 Corresponding Source。本版**没有链接、嵌入或翻译**
任何 AGPL 代码，因此不因 CoD4x_Server 成为 AGPL 派生作品。**若将来真要编译其代码片段，
整个服务端必须按 AGPL-3.0 §5 发布并按 §13 提供源码 —— 那必须在动手前单独决策。**

**本版新增的会话描述符移植链**（详见
[LICENSE_POLICY_REUSE.md](CODOL-Combat-Server-v0.1/docs/LICENSE_POLICY_REUSE.md) §2.4）：
本版移植的是 **`REF_LOBBY_KIT/codol_crypto.py` 那份可在本机执行的冻结参考实现**，
而不是直接读 ol-mod 源码（**ol-mod 源码不在本机**：原包 `E:\handoff2\ol-mod-olfinal.zip` 已不存在）。

已遵守：未修改上游工作树（`git status` 均干净）、未移除任何版权声明、**未提交、未推送**。

---

## 7. 下一步直接实现什么

按"能不能离线验证"排序，优先级从高到低：

1. **闭合"客户端为什么不来连"**（唯一真正的阻塞点）
   - 目标：定位 `[esi+4]` listener 注册源，或从 0xE3xxxx 的 DTLS/ECDH 表反查 UDP socket 创建点
     （`CLIENT-BOOKING-BATTLE-TRIGGER-014` §9 给出的 NEXT_GATE）。**纯静态，不需要运行客户端。**
   - 可交付判据：把 `ACCEPTED → listener → battle UDP socket` 这条链画到 RVA 级。

2. **让大厅消费本服导出的描述符**（消除静默不一致）
   - 把大厅的 `GAME_IP/GAME_PORT/SEC_KEY` 改为**读取战斗服的 `session_descriptor/`**。
   - 现状不一致已实测：大厅 `SEC_KEY = 16×0x00`，战斗服默认 `16×0x01` —— **两侧不同**，
     这正是"连上也会静默丢包"的种子。

3. **拿到真实 PvE booking 应答样本**（否则 PvE 路线一定停住）
   - 只有两条来源：官方 pcap，或 ol-mod 源码（本机没有）。
   - 在此之前，靶场路线（三方唯一验证过、不经 gcloudvoice）仍是确定性更高的验证路径。

4. **在获得明确运行授权后**，安排隔离环境端到端：启动战斗服 → 启动大厅（消费导出的描述符）
   → 手动点进对局 → 观察 `RX #1 16B`（客户端连上 28960 的实锤）。

---

## 8. 证据索引

| 证据 | 位置 |
|---|---|
| 构建 + 自测全量日志 | [V0_1_BUILD_AND_TEST_LOG.txt](CODOL-Combat-Server-v0.1/docs/evidence/V0_1_BUILD_AND_TEST_LOG.txt) |
| 构建清单（SHA-256） | [BUILD_MANIFEST.txt](CODOL-Combat-Server-v0.1/build/bin/BUILD_MANIFEST.txt) |
| 会话描述符导出物 | [session_descriptor/](CODOL-Combat-Server-v0.1/build/bin/session_descriptor) |
| 黄金向量生成器 | [gen_session_golden.py](CODOL-Combat-Server-v0.1/tests/gen_session_golden.py) |
| 许可证与复用说明 | [LICENSE_POLICY_REUSE.md](CODOL-Combat-Server-v0.1/docs/LICENSE_POLICY_REUSE.md) |
| 构建环境探测 | [TOOLCHAIN_ENVIRONMENT.md](CODOL-Combat-Server-v0.1/docs/TOOLCHAIN_ENVIRONMENT.md) |
| 战斗协议规格（实机抓包） | [BATTLE_SERVER_PROTOCOL.md](REF_LOBBY_KIT/BATTLE_SERVER_PROTOCOL.md) |
| booking→battle 静态交叉审计 | [OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030.md](DEV-BOOKING/OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030.md) |
| PvE 入场阻塞点分析 | [MVP-PVE-MATCH-ENTRY-009.md](DEV-BOOKING/MVP-PVE-MATCH-ENTRY-009.md) |
| accepted→battle 触发静态追踪 | [CLIENT-BOOKING-BATTLE-TRIGGER-014.md](DEV-BOOKING/CLIENT-BOOKING-BATTLE-TRIGGER-014.md) |