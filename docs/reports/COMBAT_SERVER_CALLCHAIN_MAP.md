# COMBAT_SERVER_CALLCHAIN_MAP — 战斗创建、服务器初始化与对局调用链

**性质**：本图**只表达待验证的依赖关系**，不代表每条连接都已证实。凡历史资料未证明的连接一律标 `UNKNOWN`。若历史资料表明实际调用顺序与默认模板不同，已按证据调整（见第 0.2 节）。

**节点标注口径**
- `[已实现]` 有源码实现
- `[静态证据]` 有静态二进制/反编译证据
- `[真实运行]` 有真实运行日志/实测记录
- `[未验证]` 实现存在但从未在真实目标上跑通
- `[明确失败]` 有真实运行证据表明失败
- `[缺失]` 未定位/未实现
- **⟶ 需要的下一项证据** 该节点从"未验证"变"已判定"所必需的最小证据

---

## 0. 前置：两套并行链，关系 UNKNOWN

### 0.1 两线对照

| | **L1：ol-mod 线** | **L2：协议逆向线** |
|---|---|---|
| 实现 | `src/game_server` → `CodolGameServer.Localnet32`（C++，进程内 DLL） | `REF_LOBBY_KIT/battle_server.py`（Python，UDP 28960 独立进程） |
| 大厅 | 经 Ayria 注入；**未证明到达大厅** | `GOLDEN-LOBBY-001` 冻结基线，**已到达大厅** |
| 战斗创建入口 | 未定位（客户端侧） | `15/5 findSessions` → `6/14 mmbook/mmstart` |
| 进图成果 | 无（`bind()` 失败，帧钩子未装） | 有真实客户端完成握手 + usercmd + snapshot（见 CS-X04 存疑） |
| 当前阻塞 | 引擎绑定宿主身份门禁 | booking 应答帧格式 UNKNOWN + 对局地址被送外网 |

### 0.2 与默认模板不同的地方（依据证据调整）

默认模板为 `大厅 → 战斗创建入口 → 战斗服务器初始化 → 引擎绑定 → 帧循环 → 网络会话 → 客户端进图 → 对局`。**证据支持的修正**：

1. **"引擎绑定"不是全局第二步，而是 ol-mod 线专有的第二步**。L2 没有 `EngineBindings` 这个概念，它的"服务器初始化"= 绑定 UDP 28960 + DTLS/ECDH 会话。
2. **"网络监听"在两线上的因果相反**：L1 中监听是**后端 ConfigureSession 的结果**（不是入口）；L2 中监听是**服务器启动即绑定**。
3. **"战斗创建入口"在两线上位置不同**：L1 未定位；L2 已定位到 `6/14` booking。
4. **帧循环**：L1 依赖 hook 宿主 `Com_Frame`；L2 是自有 `snap_hz`（默认 = tick 128 Hz）循环。二者不可互推。

---

## 1. L1（ol-mod 线）依赖图

```
[现有大厅基线]
   |   x UNKNOWN：GOLDEN-LOBBY-001 冻结链（nt10.py）中从未加载过 CodolGameServer.Localnet32
   |             已有的 Ayria 加载证据来自 Launch_OLMod.bat 路径，而该路径未证明到达大厅
   v
[注入/加载] Localnetworking 枚举 *.Localnet32 -> LoadLibraryW -> GetProcAddress("Createserver")
   |  状态：OK [真实运行] 2026-10-10 三次；Localnetworking.log「Loaded ... CodolGameServer.Localnet32.」
   v
[服务器初始化] DllMain -> initialize() -> processRole()（combined）
   |  状态：OK [真实运行] 到达 bind()
   v
[引擎绑定门禁] EngineBindings::bind()    *** 当前失败点 ***
   |  +- module_ = GetModuleHandleW(nullptr)                      :3654
   |  +- e_magic != IMAGE_DOS_SIGNATURE        -> return false    :3660  【静默】
   |  +- Signature/TimeDateStamp/SizeOfImage   -> return false    :3662-3666【静默】
   |  +- 具名前缀守卫 :3669-3742   （失败会写日志）
   |  +- 未具名 || 链 :3744-4023   （写 stage=function_prefixes）
   |  +- runtime_slots :4153 / message_bindings :4203 / glass_bridge :4210
   |  状态：X [明确失败] 三次均为「engine binding failed」，且**无任何 stage 日志**
   |  --> 需要的下一项证据：运行时映像(O-4) 的 TimeDateStamp + SizeOfImage（区分到具体分支）
   |                        以及 0x0FEA20 / 0x8371A 的运行时字节（真正的正确性判据）
   v
[帧钩子安装] installFrameHook(Bindings, onServerFrame)  Appmain.cpp:8128
   |  +- FrameHook.cpp:39-71 在 module+0x0FEA20 写 0xE9 相对跳转（蹦床）
   |  +- 拒绝原因会写日志：invalid-bindings / null-callback / already-installed /
   |                      trampoline-allocation-failed / protect-failed
   |  状态：X [未验证]（被 bind() 阻断）  --> 需要：bind() 通过后的插件日志
   v
[战斗帧循环] Com_Frame -> comFrameHook(先 call 原函数) -> runServerFrame -> Callback = onServerFrame
   |  onServerFrame: Appmain.cpp:6437 -> runsGameServer 守卫 -> ensureDedicatedControlServer()
   |                  -> processDedicatedControlMessages() -> Network.NET_Frame(:6633)
   |  状态：X [未验证]
   v
[控制面/会话] DedicatedControl TCP 28961 <- backend ConfigureSession
   |  -> Server.configureSessionDescriptor()（sv_main_mp.cpp:1563）
   |  -> Network.start()（sv_network_mp.cpp:20）-> bind(0.0.0.0:28960)（win_net.cpp:113）
   |  -> Server.setEnabled(true)（sv_main_mp.cpp:1166）
   |  状态：X [未验证]，且**28960 从未监听**
   |  依赖：[缺失] 真实 Demonware ConfigureSession 描述符字节（U5）
   v
[网络会话] DTLS INIT->INIT_ACK->COOKIE_ECHO->COOKIE_ACK->DATA
   |           -> SV_ConnectionlessPacket: getchallenge/challengeResponse/connect/connectResponse
   |           -> 在册 XUID 校验 -> ClientState::Connected -> ClientLoading -> Active
   |  状态：X [未验证]（有固定向量离线测试）
   v
[客户端进入地图] gamestate（configstring 0/2 + CCS checksum）+ snapshot + 地图资产
   |  状态：X [未验证]；地图资产只有 mp_crash_tropical 可用，mp_nuked 产物不可用
   v
[实际对局] SD/FFA/Factory 等模式闭环
      状态：X [未验证]；SD 回合机未闭环、G_Damage 缺 9 依赖、PVS 未恢复
```

### 1.1 L1 关键调用链（源码级，逐行；行号以 D 树为准）

```
初始化
  DllMain(DLL_PROCESS_ATTACH)                     Appmain.cpp:9511-9519
    +- initialize()                               Appmain.cpp:7012
        +- StartupMutex / Installed 早退           :7012-7017
        +- role = OlMod::processRole()             :7017      <- OLMOD_PROCESS_ROLE
        +- installUnsignedFastfilePatch()          :7022-7035
        +- [Dedicated] installDedicatedProcessPatches() :7111-7132
        +- Bindings.bind()                         :7133      *** 失败点 ***
        |    +- 失败 -> logGameServer("engine binding failed") -> return  :7135-7136
        +- installFrameHook(Bindings, onServerFrame) :8128 / :7155
             +- FrameHook.cpp installFrameHook     :39-71
                  +- target = bindings.module() + EngineBindings::ComFrameRva(0x0FEA20)
                  +- trampoline = VirtualAlloc(10)
                  +- copy_n(target, 5, trampoline); trampoline[5]=0xE9; rel32 -> target+5
                  +- VirtualProtect(target, 5, RWX); target[0]=0xE9; rel32 -> &comFrameHook
                  +- FlushInstructionCache

每帧
  Com_Frame (RVA 0x0FEA20)
    +- comFrameHook (naked)                        FrameHook.cpp:22-34
         +- call dword ptr [OriginalComFrame]      <- 先执行原函数
         +- pushfd / pushad
         +- call runServerFrame                    :16-20
         |    +- Callback(GetTickCount()) = onServerFrame
         +- popad / popfd / ret

  onServerFrame                                   Appmain.cpp:6437
    +- if (!runsGameServer(role)) return           :6603-6604
    +- ensureDedicatedControlServer()              :6606
    +- processDedicatedControlMessages()           :6607
    +- Network.NET_Frame(Server, now)              :6633
    |    +- sv_network_mp.cpp:64-111  <=64 收包 -> ServerCore::NET_DtlsPacket
    +- Network.NET_SendPackets(outbound, now)      :6710

开服（监听触发）
  backend --ConfigureSession--> DedicatedControl:28961
    +- Server.configureSessionDescriptor(descriptor)   sv_main_mp.cpp:1563
         +- Network.start()                            sv_network_mp.cpp:20
              +- bind(0.0.0.0:28960)                   win_net.cpp:113
                   +- Server.setEnabled(true)          sv_main_mp.cpp:1166
```

---

## 2. L2（协议逆向线）依赖图

```
[现有大厅基线 = GOLDEN-LOBBY-001]  OK [真实运行] 2026-10-05 16:36 大厅 UI 渲染
   |  链路：提权代理 -> hosts/dwauth/CA -> auth 3074 -> lobby 3074
   |        -> nt10 拉起 exe（4 内存补丁 + KDF hook）-> 0x81/0x82/0x83 -> 0x85 任务帧
   v
[战斗创建入口 = 大厅内点击进对局]
   |  +- 15/5 findSessions（query kind 1=FIND_SERVERS / 3=FIND_LOBBIES_BY_PLAYLIST）
   |  +- 21/5 mission session 对象（靶场分支：len=268, map=mp_firingrange, 地址块=127.0.0.1:28960）
   |  +- 6/14 mmbook / mmstart（booking）
   |  状态：部分 OK [真实运行]（已能观察到请求）；应答侧 *** 未完成 ***
   |  --> 需要的下一项证据：6/14 booking 请求的原始字节 + 一个能被客户端接受的应答帧
   v
[booking 应答]  *** L2 的当前阻塞 ***
   |  状态：X [缺失] 帧格式 UNKNOWN；用靶场信封答 PvE -> **9/9 断连**
   |  已知的否证：push 'mmbook accepted' 本身会打断连接（与 seq 号段无关）
   v
[对局地址路由]  ** 已被否证 **
   |  状态：X [明确失败] 客户端把对局流量送到外部腾讯 101.67.36.18:10035（gcloudvoice.dll），
   |                     600 s 日志中 28960 出现 0 次
   |  --> 需要的下一项证据：定位"对局地址由谁下发"（平台/QoS/语音中继？）
   v
[战斗服监听] battle_server.py 绑定 0.0.0.0:28960     OK [已实现]
   v
[战斗握手] NAT 29B -> DTLS init 16B -> cookie 38B -> 219B -> 114B ack -> 数据帧
   |  状态：OK [真实运行]（至少一次完整会话，见 CS-X04 存疑）
   v
[游戏状态] getchallenge -> challengeResponse -> connect -> connectResponse -> stats -> heartbeat
   |           -> usercmd(14B) -> gamestate(259B)
   |  状态：OK [真实运行]
   v
[快照] 运动快照，字段序列 29/29 对齐实录；早期合成快照使客户端越过
   |      "waiting for player data" 进入地图，但世界全黑、玩家不在有效出生状态
   |  状态：部分 OK；"进入实际对局" X [未验证]
   v
[实际对局] X [未验证]
```

### 2.1 L2 已逐字节固化的战斗握手（协议规格，来自真实抓包+离线自测）

```
1) NAT 遍历      C->S 29B   首字节 13 -> 回同包但首字节改 12
2) DTLS init     C->S 16B   01 02 0000 0000 <clientTag:2> 01 00 x7
                 S->C 38B   cookie（首字节改 02 02），[14:16]=serverTag，[24:30]=本地 IP/端口
3) cookie+公钥   C->S 219B  03 02 <serverTag> | cookie(38B) | ...(67B) | u64 1 | 客户端公钥(100B)
                 S->C 114B  04 02 <tag> | 0000 | 服务端公钥(100B)@[6:106] | 01 @106
4) 数据帧       06 02 <serverTag:2> <seq:2> <hmac8> <len:2> <cipher(len)>
   - seq 从 0 开始（握手期 OOB 也占号）
   - serverTag 取自 cookie[14:16]（写错会静默丢包）
   - AES 流密钥 = SHA1(ECDH共享x(28B大端) || securityKey(16B)) -> 24B（末 4B 补 0）
   - securityKey = 16 x 0x01
   - 流加密计数器 = SHA1(seq(2) | 00 00 | serverTag(2))，逐块 +1
   - hmac8 = HMAC-SHA1(key24, [0:6] || [14:])[:8]
5) 应用层       FF FF FF FF getchallenge <challenge> 0
                -> challengeResponse
                FF FF FF FF connect <challenge> "\name\<base64>\xuid\<...>"
                -> connectResponse
                FF FF FF FF stats 0 <index:1> <total:u16=826> <826B>
                -> statResponse 0 0
                FF FF FF FF heartbeat 0（每 1 s）
                -> heartbeatresponse
                usercmd 明文 14B：01 00 00 00 | 00 00 00 00 | 00 00 00 00 | 00 02
```

---

## 3. 节点状态汇总表

| 节点 | L1（ol-mod） | L2（协议逆向线） |
|---|---|---|
| 现有大厅基线 | X **UNKNOWN**（战斗服务器从未在该基线中加载过） | OK **真实运行**（2026-10-05 冻结） |
| 战斗创建入口 | X [缺失]（仅静态猜到 `0x6E4A20` 等候选，未证明） | 部分 OK（`15/5`/`21/5`/`6/14` 已观察） |
| 战斗服务器初始化 | 部分 OK [真实运行] 至 `bind()` | OK [已实现] 绑定 28960 |
| **引擎绑定** | X **明确失败**（宿主身份门禁） | 不适用（无该层） |
| 战斗帧循环 | X [未验证] | OK（自有 `snap_hz` 128 Hz 循环） |
| 网络会话 | X [未验证]（DTLS 有离线固定向量） | OK [真实运行]（握手 + usercmd + 快照） |
| 客户端进入地图 | X [未验证] | 部分 OK（越过 waiting，但世界全黑、无有效出生） |
| 实际对局 | X [未验证] | X [未验证] |
| **booking 应答** | 由 backend `DedicatedBookingDispatcher` 实现（[已实现]） | X **缺格式**，靶场信封答 PvE -> 9/9 断连 |
| **对局地址路由** | 未触及 | X **明确失败**（流量送外部腾讯地址） |

---

## 4. 从现有大厅基线出发：第一个证据支持的未完成节点

### 4.1 主答案（按本任务点名的战斗服务器 = `CodolGameServer.Localnet32`，即 L1）

> **第一个未完成节点 = `EngineBindings::bind()` 的宿主映像身份门禁。**
> 更精确地说：是 `EngineBindings.cpp` `:3656 / :3660 / :3666` 这三个**静默早退点之一**，且**当前证据无法区分是哪一个**（`TimeDateStamp` 与 `SizeOfImage` 同处一个 `if`，代码不记录分支）。

**为什么是它（证据链）**
1. 它是 L1 上**唯一有真实运行失败证据**的节点（三次 `[combined/game-server] engine binding failed`，CS-F02）。
2. 它**一条阻断 100% 的战斗链**：无绑定 ⇒ 无 `bindingCommitted_` ⇒ `installFrameHook` 直接以 `invalid-bindings` 拒绝（`FrameHook.cpp:59-67`）⇒ 无 `Com_Frame` hook ⇒ 无 `onServerFrame` ⇒ 无 `NET_Frame` ⇒ 28960 永不监听 ⇒ 无对局。
3. L1 上在它之前的节点已达成的部分：插件**确实被加载**（CS-F03）、`initialize()` **确实被调用**（否则无 game-server 日志）。
4. 三条静默分支的判定所需数据**无法离线获得**：门禁读的是**运行时映像**（`GetModuleHandleW(nullptr)`），而磁盘加壳件的 `SizeOfImage`（`0x0E659000`）与期望（`0x0E5D6000`）不可比（已裁定为"对象错位"，CS-X07）。

**⟶ 需要的下一项证据（最小集）**
- **E-2**：运行时映像（O-4）的 `TimeDateStamp` / `SizeOfImage` / `Machine` / 段表 —— 用于区分是时间戳、尺寸，还是签名分支。
- **E-3**：运行时映像中 `0x0FEA20`（5 B：`55 8B EC 56 57`）与 `0x8371A`（8 B：`83 7C 24 08 01 0F 94 C0`）的实际字节 —— 这是**真正的正确性判据**，且必须在门禁放宽**之前**取得。
- 采集方式（历史报告已给出、本轮未执行）：**在插件内只读读取自身模块头与指定 RVA 字节并写日志**，不使用 `ReadProcessMemory`、不附加调试器。这需要先获得运行授权；若要区分分支，还需先落地"门禁具名化"的**纯日志**改动（T-3.0，**仅提案未批准**）。

**明确不在此优先级的项（不得排入）**
- 放宽/删除 `SizeOfImage` 检查（禁止，CS-A12）。
- 大规模重标定 145/146 个 RVA（守卫从未执行过，无依据）。
- 修改任何协议常量 / RVA / 前缀 / ABI / 启动链。
- 与 `bind()` 判定无关的服务端可玩性工作（`G_Damage`、SD 回合机、Lua thread、PVS）—— 它们影响"可玩"，但不影响"能否进对局"。

**必须同时登记的依赖（不是本节点，但紧邻）**
- L1 在 `bind()` 之后随即需要 **P2（后端 ConfigureSession 真实描述符，U5）** 才能让 28960 监听；否则即使绑定通过也不会开服。
- L1 **从未在冻结大厅基线中加载过**（第 0.1 节），"从大厅基线出发"这一步在本线**无证据**；若严格以冻结大厅基线为起点，则 L1 的第一个未完成节点应升级为"**把 `CodolGameServer.Localnet32` 载入冻结大厅链**"，而该做法在历史资料中**没有记录**（UNKNOWN）。

### 4.2 并行列出的备选答案（按 L2，仅登记不裁定）

> 若采用**冻结大厅基线自身的进图入口线（L2）**，则第一个未完成节点是：
> **`6/14 mmbook/mmstart` booking 应答帧格式（UNKNOWN）+ 对局地址路由（已被否证：客户端把流量送到外部腾讯 `101.67.36.18:10035`）。**
> 需要的下一项证据：一次**来源可隔离**的运行，证明客户端对局流量确实到达我们监听的 28960（`battle_srv.log` 出现 `RX #1 16B`，且该次日志未被离线自测写入——见 CS-X04）。

**为什么本轮不把它定为唯一答案**：任务书点名的事实（`CodolGameServer.Localnet32`、`Createserver`、`combined/dedicated`、`EngineBindings`、146 RVA / 82 守卫、`0x0E5D6000` vs `0x0E659000`）全部属于 L1；而 L2 属于另一个由 `GOLDEN-LOBBY-001` 冻结的大厅线。**两线关系为 UNKNOWN（CS-D14），需用户裁定使用哪条线。** 本档案并列保留，不合并。

---

## 5. UNKNOWN 连接（禁止补全）

| # | 未证明的连接 | 影响节点 |
|---|---|---|
| U-1 | 冻结大厅基线 → `CodolGameServer.Localnet32` 载入 | L1 起点 |
| U-2 | 原版引擎"战斗/会话创建"函数（`Createserver` 之外） | L1 战斗创建入口 |
| U-3 | `0x6E4A20` 等客户端候选与战斗服的真实关系 | L1 战斗创建入口 |
| U-4 | 后端 `ConfigureSession` 的真实描述符字节 | L1 开服 |
| U-5 | ol-mod 线与协议逆向线的接口关系 | 全图 |
| U-6 | `6/14` booking 应答帧格式 | L2 booking |
| U-7 | "对局地址"的真实下发来源 | L2 地址路由 |
| U-8 | 运行时映像 O-4 的 PE 头与 RVA 字节 | L1 引擎绑定 |
| U-9 | 客户端"进入实际对局"的完成判据 | 两线末端 |
