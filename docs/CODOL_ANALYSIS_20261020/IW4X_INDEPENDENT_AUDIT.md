# IW4X 独立审计

日期：2026-10-21（Asia/Shanghai）

范围：`IW4X/iw4x-client` 自身源码、宿主二进制、依赖、资产与文档。按用户要求，本文件在 CoD4x 独立审计完成后开始，不提前引用 CoD4x 或 CODOL 的协议结论。

当前输入边界：

- 主仓库 HEAD：`675c4f1e0355c0f07e9d2679429f3d90d9ed175d`（2026-10-20 08:32:26 -0400）。
- 远端：`https://github.com/iw4x/iw4x-client.git`。
- 主仓库源：264 个 `.cpp`、279 个 `.hpp`、543 个 C/C++/H/HPP 文件。
- 主仓库是注入式客户端扩展；`-dedicated` 模式运行在 MW2/IW4 宿主进程，不是 CoD4x 式完整独立服务器源码树。
- 主仓库引用 540 个函数指针 typedef；`src/Game/*.cpp` 有 797 行 32 位地址常量，`src/Components/*.cpp` 有 2,081 行地址常量，全仓库共有 1,612 行 `Utils::Hook`/`Hook::Nop`/`Hook::Set`/`Hook::Call`/`HOOK_*` 调用。这些是宿主 ABI 绑定和补丁点，不等于宿主实现。
- 16 个 git submodule 全部未初始化，包括资产格式所依赖的 `deps/iw4-open-formats`。
- 工作区另有 `DEV-BOOKING/_lineage021/iw4x-rawfiles`，包含约 7,439 个文件、1.03 GB 原始资产与 `iw4x.exe`（3,932,160 B，SHA-256 `49EA90E34C9CD64D9D0AE7F4B399E4ECC5EA13976823B2B8667390A4B8767009`）。它可作为后续独立资产审计输入，但不能替代缺失子模块。
- 工作区 `COD8/iw4mp.exe` 为 6,254,136 B，SHA-256 `926F8A47959F2B24420898D07F599883E0866050D42D5289F94EEF546A4A3492`；是否与 IW4X 固定地址匹配尚未证明。

## 0. 审计状态与完成边界

状态：**进行中，未完成。**

本轮不写入 IW4X 与 CoD4x/CODOL 的交叉结论。IW4X 的“完整审计”至少需要同时完成四层：

1. 扩展源码层（主仓库 `src`）；
2. 宿主 IW4/MW2 二进制层（固定地址、结构布局、版本匹配）；
3. 依赖与资产层（submodule、fastfile/zone、rawfiles）；
4. 构建与运行层（x86 DLL、dedicated、真实宿主、日志与失败路径）。

本轮只完成了第 1 层的大部分静态入口发现，以及第 2-4 层的输入与边界登记，不能称为完整。

A-S 当前状态：

| 域 | 状态 | 说明 |
|---|---|---|
| A 身份与构建 | 部分完成 | 主仓库身份已确认；子模块与宿主版本尚未闭合 |
| B 入口与生命周期 | 部分完成 | Loader、组件注册、dedicated 初始化路径已定位 |
| C 帧循环与线程 | 部分完成 | Scheduler、server frame hook、dedicated wait 已定位 |
| D 网络基础层 | 部分完成 | OOB 构造、客户端回调、socket 补丁已定位 |
| E 连接状态机 | 部分完成 | Auth/DirectConnect 包装层已定位，宿主状态机未反汇编 |
| F 消息与传输 | 部分完成 | Huffman、网络发送与接收入口已定位，完整 netchan 在宿主 |
| G 地图与资产 | 未完成 | `iw4-open-formats` 子模块缺失；资产结构主要在 `Structs.hpp` 声明 |
| H 世界与碰撞 | 部分完成 | PM/Trace 地址包装存在；实际 trace 实现不在主仓库 |
| I 移动与控制 | 部分完成 | PMoveSingle、PM_playerTrace、PM_Trace 地址绑定；未执行 |
| J 实体与状态 | 部分完成 | `Structs.hpp` 有大结构声明；未逐字段与宿主版本校验 |
| K 快照与复制 | 部分完成 | hooks 和类型存在；snapshot 读写由宿主实现 |
| L 游戏逻辑 | 未完成 | 主仓库不是完整 game logic；宿主函数只通过地址暴露 |
| M 脚本与规则 | 部分完成 | GSC 组件与脚本补丁存在，未做行为审计 |
| N 管理面 | 部分完成 | RCon、ServerCommands、Download、HTTP/Mongoose 层已定位 |
| O 认证与安全 | 部分完成 | Auth challenge/ECC、bin check、voice 限制已定位 |
| P 插件与平台 | 部分完成 | 组件框架、hooks、Steam 代理、IPC 已定位 |
| Q 外部服务 | 部分完成 | master heartbeat、party、node、Steam 层已定位 |
| R 构建与验证 | 未完成 | 没有生成 build、无 `version.h/hpp`、未构建、未运行 |
| S 缺口 | 进行中 | 见本文件后续缺口表 |

## 1. 输入身份与版本边界

主仓库：

- `IW4X/iw4x-client`，HEAD `675c4f1e0355c0f07e9d2679429f3d90d9ed175d`，提交日期 2026-10-20。
- 主工作树干净；未发现未提交修改。
- 许可证：仓库 `LICENSE` 为 GPL-3.0（需按文件确认，当前未逐条审阅例外条款）。
- 构建目标：`premake5.lua` 的 `project "iw4x"`，`kind "SharedLib"`，x86 Win32，C++20，MSVC。
- 版本头 `src/version.h/.hpp` 当前未生成；由 `premake5 generate-buildinfo` 预构建生成。
- 当前无 `build` 目录、无已构建 `iw4x.dll`，因此没有可验证的主仓库二进制产物。

历史克隆：

- `DEV-BOOKING/_lineage021/iw4x-client` HEAD `d1b175da1a25d31043246de103a702b206269e5a`，2026-10-07。
- 它与当前主仓库不同版本，只能作为历史对照，不能把两者文件混合计数或混用结论。

宿主/资产候选：

- `DEV-BOOKING/_lineage021/iw4x-rawfiles/iw4x.exe`：3,932,160 B，SHA-256 `49EA90E34C9CD64D9D0AE7F4B399E4ECC5EA13976823B2B8667390A4B8767009`；这是 rawfiles 仓中的运行器，不是主仓库构建产物。
- rawfiles 约 7,439 文件、1.03 GB；`zone`、`zone_raw`、`zone_source`、`zonedata` 存在，但尚未完成逐资产格式核验。
- `COD8/iw4mp.exe`：6,254,136 B，SHA-256 `926F8A47959F2B24420898D07F599883E0866050D42D5289F94EEF546A4A3492`。它是否是 IW4X 固定地址所对应的宿主版本，尚未证明；不得仅凭文件名认定。

## 2. 源码层与宿主层边界

### 2.1 主仓库真正实现的层

主仓库负责：

- 组件注册与生命周期；
- 宿主固定地址包装与 hook；
- 网络 OOB 构造、连接协议辅助；
- 认证信息构造/解析；
- 资产 handler、zone builder、服务器命令、RCON、HTTP 下载；
- 控制器、Steam、Sentry、UI/客户端扩展；
- 部分服务器端 demo 与 voice 逻辑。

证据：

- `src/Components/Loader.cpp:129` 注册 `ConnectProtocol`，`:134` 注册 `Dedicated`。
- `src/Components/Modules/Dedicated.cpp:21` `IsEnabled`，`:33` `IsRunning`，`:39` `InitDedicatedServer`，`:64` `PostInitialization`。
- `Dedicated.cpp:190` 通过 `0x60BE98` hook 初始化 dedicated，随后关闭 renderer、sound、UPnP、UI 等宿主子系统。
- `src/Components/Modules/Threading.cpp:241` 在 dedicated/zonebuilder 下改变服务器线程与等待路径。
- `src/Components/Modules/Scheduler.cpp` 提供 server/client/main/renderer 管线并 hook 宿主帧函数。

### 2.2 宿主实现的层

主仓库没有：

- `SV_Frame`/`SV_SpawnServer` 的完整独立 C/C++ 实现；
- `CM_BoxTrace`/BSP brush 的完整实现；
- 完整 pmove 算法；
- 完整 game entity / weapon / damage / score 逻辑。

这些能力通过 `src/Game/*.cpp` 的固定地址函数指针和 `Structs.hpp` 结构声明注入宿主：

- `Game/Server.cpp:20` `SV_ClientThink = 0x44ADD0`。
- `Game/PlayerMovement.cpp:6` `PM_playerTrace = 0x458980`，`:7` `PM_Trace = 0x441F60`。
- `Game/Functions.cpp:157` `PMoveSingle = 0x5743E0`。
- `Game/Functions.cpp:327` `cm = 0x1AA6480`。
- `Game/Structs.hpp:3298` `clipMap_t` 等结构定义。

上述地址只有在宿主版本匹配时才有意义。主仓库的 hooks 和地址常量数量很大，不能以“地址存在”说明宿主行为已经审完。

## 3. 网络与认证

### 3.1 OOB 与客户端回调

`Network.cpp` 确认了扩展层对宿主网络栈的接管方式：

- `Network::Send` 自行加 4 字节 `FF FF FF FF`，再调用 `Sys_SendPacket`；注释明确不使用只接受文本的 `NET_OutOfBandPrint`。
- `SendCommand` 采用 `command + '\n' + data`，用于 `heartbeat`、`connect` 等 OOB。
- `CL_HandleCommandStub` hook 宿主 `0x5AA703`，以命令名查 `CL_Callbacks` / `CL_RawCallbacks`；未命中则回宿主分派。
- 原始 `print` 回调校验来源地址与 `serverAddress` 的 base address，避免任意包覆盖本地服务端消息。

### 3.2 IW4X 连接认证信封

`Auth.cpp` 是 IW4X 自有认证层，不是引擎原始 connect 文本：

- 客户端从 `getchallenge` 的 info string 读取 challenge；
- 组装 `Proto::Auth::Connect`：`signature`、`publickey`、`token`、`infostring`；
- 服务器端 `ParseConnectData` 从消息偏移 12 后解析 protobuf；
- 校验 XUID 与公钥散列、`steamid`/argv GUID 一致性、ECC challenge 签名、安全等级；
- 通过后调用宿主 `SV_DirectConnect`。

`auth.proto`：

```proto
message Connect {
  bytes signature  = 1;
  bytes publickey  = 2;
  bytes token      = 3;
  bytes infostring = 4;
}
```

这说明 IW4X 的认证是**扩展层自有的加密信封**，而宿主仍消费解析后的普通 connect 命令。不能把此 protobuf 信封直接等同于宿主原始协议，也不能把它当作 CODOL 的握手。

### 3.3 宿主 netchan 与快照

IW4X 主仓库没有独立 `netchan.c`，但有：

- `PROTOCOL = 0x99`（`src/Game/Structs.hpp:3`）；
- `netchan_t` 等宿主结构声明；
- 固定地址发送/接收/连接函数包装；
- Huffman 模块与 `SV_ExecuteClientMessage` hook；
- `SV_ClientThink`、`PMoveSingle`、`PM_Trace` 地址绑定；
- server demo 模块。

由此可得的是：**IW4X 复用宿主 netchan 与游戏消息，扩展层负责协议号、认证、OOB、回调与补丁**。完整字段级协议仍必须连同宿主二进制一起审计。

## 4. 地图与碰撞

### 4.1 资产结构

- `Game/Structs.hpp` 声明了 `clipMap_t`、`MapEnts`、`cbrush_t`、`cmodel_t`、`cLeaf_t`、`cNode_t`、`CollisionAabbTree` 等宿主结构。
- `Components/Modules/AssetInterfaces/IclipMap_t.cpp` 的 `AssertSize(Game::clipMap_t, 256)` 说明它是依据固定布局处理资产，而不是重新实现地图几何。
- `IclipMap_t::load` 通过 `builder->getIW4OfApi()->read<Game::clipMap_t>(ASSET_TYPE_CLIPMAP_MP, _name)` 读取资产。
- `IMapEnts` 通过同样的 `getIW4OfApi()->read` 读取实体串；`mark` 会从实体串提取模型和武器名并登记资产。
- 真实格式解析依赖 `deps/iw4-open-formats`，当前子模块未初始化，故资产格式审计当前无法完成。

### 4.2 碰撞与移动

主仓库只提供宿主函数地址：

- `PM_playerTrace = 0x458980`；
- `PM_Trace = 0x441F60`；
- `PMoveSingle = 0x5743E0`；
- `cm = 0x1AA6480`。

`Components/Modules/PlayerMovement.cpp` 中能看到扩展层对 pmove 的 patch：

- `PM_PlayerTraceStub` 在原 trace 结果上附加 `SURF_LADDER`；
- `PmoveSingle_Stub` 按 `tracemask` 增删 `MASK_PLAYER_CLIP` / `MASK_BARRIER_CLIP`；
- `PM_StepSlideMoveStub` 按 dvar 选择宿主原始步进路径；
- `PM_CheckLadderMove_Stub`、跳跃、落地减速等均有补丁。

这些补丁的行为验证依赖宿主版本和真实世界 trace。当前没有构建产物、没有运行证据，也没有逐 patch 的宿主反汇编对照，因此不能宣称 IW4X 的移动/碰撞已被完整验证。

## 5. 移动与快照

### 5.1 客户端消息接收保护

`Security.cpp` 显示 IW4X 在宿主解析前后加了多层边界检查：

- `NET_DeferPacketToClient_Hk` 在 `0x6267E3` 拦截延迟包，超过 `DeferredMsg::data` 上限直接丢弃；
- `SV_ExecuteClientMessage_Stub` 检查 `reliableSequence - reliableAcknowledge < 0`，发现负值时记录 Fail2Ban、修正 ack 并断开；
- 通过后调用宿主 `0x414D40`；
- `Huffman` 初始化后接管 `Msg_ReadBitsCompressCheckSV/CL`，否则仍在 `0x414D92`、`0x4A9F56` 加检查。

这属于**服务器接收路径的防御补丁**，不是完整 netchan 重实现。真正的 clc 解码、usercmd delta、snapshot writer 仍在宿主。

### 5.2 Server demo

`ServerDemo.cpp` 是主仓库比较少见、能在源码层直接看到服务器数据输出的模块：

- 记录的 network record 为 `[type 0][netchan sequence][length][wireData]`，在 `SV_Netchan_Transmit` 之前通过 `SV_Netchan_Transmit_Stub` 抓取；
- archive record 为 `[type 1][slot][origin][velocity][movementDir][bobCycle][commandTime][viewangles][locationSelectionInfo]`；
- demo 以 gamestate 开头，达到大小上限后干净关闭而不是拆成第二个文件；
- 可在连接建立后从滚动缓冲补写历史。

这为“服务器发出过什么”提供了可验证的 host-side sink，但它仍依赖宿主生成的 wire data，不是服务端语义实现。

### 5.3 快照和可靠命令的源码边界

主仓库提供：

- `server demo`、`server commands`、`configstrings` 等辅助模块；
- `Game::Server`/`Game::Client` 的固定地址函数包装；
- `Structs.hpp` 的结构布局与 `static_assert`；
- 针对旧版 exploit 的 hook。

但快照的 `delta` 选择、entity/client/playerstate 字段写读、netchan 重传与校验仍由宿主完成。要把它审计成“可重写服务器”，下一步必须锁定宿主可执行文件版本，并对这些宿主函数做出反汇编证据；仅凭扩展层调用点不够。

## 6. party/node/master

### 6.1 节点发现

`Node.cpp` 与 `node.proto` 确认了 IW4X 自己的节点层：

- 节点列表持久化在 `players/nodes.json`，旧 `nodes.dat` 可迁移；
- `nodes_default.dat` 是 ZLib 压缩的 protobuf；
- `nodeListRequest` / `nodeListResponse` 通过 `Session` 发送；
- `Proto::Node::List` 包含 repeated nodes、port、isNode、protocol；
- dedicated 模式下 `isNode` 反映 `Dedicated::IsEnabled()`；
- `Node::RunFrame` 维护请求、响应、超时和淘汰。

### 6.2 Session 信封

`Session.cpp` 设计了一个 ECC 签名的 session 协议：

```text
sessionSyn
  -> sessionAck(challenge)
  -> sessionFin(Proto::Session::Packet)
       publickey, signature, command, data
```

`session.proto`：

```proto
message Packet {
  bytes signature = 1;
  bytes publicKey = 2;
  bytes command   = 3;
  bytes data      = 4;
}
```

但是 `Session.hpp` 当前定义了 `#define DISABLE_SESSION`。在本构建下，`Session::Send` 走的是带 500–700 ms 随机延迟的重发包装，而不是上面的 ECC session 队列；`Session::Handle` 直接注册 `Network::OnClientPacket`。

因此：

- 源码中存在一套完整 session 设计；
- 当前默认构建关闭了该设计；
- 不能把 `Session.cpp` 的 ECC 流程当作默认运行行为。

这一区别必须带入后续交叉验证。

### 6.3 Party 与 master

`Party.cpp` 包含：

- `PARTY_LOBBY`、`PRIVATE_PARTY` 等匹配类型；
- `getinfo` / `infoResponse` / `getplaylist`；
- `CL_ConnectFromParty` 的固定地址调用；
- 对 `SV_DirectConnect`、gamestate parse、party migrate、heartbeat timeout 的大量 patch；
- server 启动时的线程同步 hook。

`Dedicated.cpp:163-177` 的 heartbeat：

- `sv_lanOnly` 时不发心跳；
- `com_masterServerName` + `com_masterPort` 构造目标；
- `Network::SendCommand(master, "heartbeat", "IW4")`；
- 首次一次、之后每 2 分钟。

`Discovery.cpp` 另有一套局域网发现：

- `discovery <challenge>` 广播；
- 仅接受本地地址和匹配挑战的 `discoveryResponse`；
- 不依赖公网 master。

### 6.4 Steam / IPC

- `src/Steam` 提供 Steam 代理与接口实现，dedicated 下许多逻辑被显式绕开。
- `Session` 与 `IPC` 的 proto 定义存在，但 IPC 是否参与 dedicated 控制链需按组件注册与运行进一步验证。
- 主仓库的 party/node/master 属于扩展协议层，不应和宿主 IW4 的普通对战 netchan 混为一谈。

## 7. 构建与验证

### 7.1 构建系统

- `premake5.lua` 生成 VS solution，目标 `SharedLib`、x86、C++20。
- `generate.bat` 负责 submodule 初始化、premake 生成与构建辅助。
- 预构建运行 `tools/premake5 generate-buildinfo`，生成 `src/version.h` 与 `src/version.hpp`。
- 当前未执行生成，没有 `build` 目录，也没有版本头。
- 16 个 submodule 均未初始化；其中 `iw4-open-formats` 为资产层必要依赖，`protobuf`、`mongoose`、`curve25519/libTomCrypt`、`udis86`、`sentry-native`、`sqlite` 等亦为功能依赖。

### 7.2 构建与运行状态

本轮没有：

- 初始化 submodule；
- 生成 Visual Studio solution；
- 构建 `iw4x.dll`；
- 启动 IW4X dedicated；
- 启动宿主 MW2；
- 运行真实地图或客户端；
- 验证固定地址与宿主版本匹配；
- 验证 server demo、RCon、Node、Party、Steam 的实际连通。

因此 R 域保持“未完成”。

### 7.3 测试

主仓库当前未发现独立单元测试目录；主要是构建 workflow 和运行时模块。少量 `assert`、`static_assert` 用于结构尺寸/偏移和参数边界，不构成端到端服务器测试。由于子模块和构建均未完成，本轮也没有运行它自己的自动检查。

## 8. 缺口登记

| 缺口 | 原因 | 获取方式 | 解除什么 |
|---|---|---|---|
| 宿主版本未锁定 | 固定地址需要精确宿主；现有 `iw4mp.exe` 与 `iw4x.exe` 身份未对应 | 用 IW4X 校验和/版本日志确认宿主 SHA 与地址基准 | 所有固定地址 hook 的可信性 |
| 16 个子模块缺失 | 主仓库未初始化 submodule | 在隔离目录按其 `.gitmodules` 锁定提交初始化 | 资产、protobuf、压缩、崩溃报告和完整构建 |
| `iw4-open-formats` 缺失 | 同上 | 初始化对应 submodule | clipMap/mapEnts/fastfile 格式审计 |
| 无 `version.h/.hpp` | 未运行 prebuild | 调用 premake `generate-buildinfo` | 可复现构建身份 |
| 未构建 `iw4x.dll` | 缺依赖、未执行 premake/MSVC | 安装匹配的 VS 工具链并在隔离目录构建 | 扩展层编译验证 |
| 未运行 dedicated | 无构建产物/宿主未锁定 | 在合法 MW2 安装和匹配宿主中运行 | 生命周期、网络、party、demo 实机验证 |
| 宿主函数行为未反汇编 | 主仓库只提供地址包装 | 对锁定宿主逐地址反汇编和调用图 | pmove/trace/snapshot/game logic |
| rawfiles 未逐资产解析 | 1.03 GB/7,439 文件尚未逐文件分类 | 按 zone/raw/source 分类并记录哈希 | 资产格式与加载验证 |
| 游戏逻辑不在主仓库 | 设计边界 | 通过宿主反向分析或独立重建 | 完全可重构服务器 |
| 默认 `DISABLE_SESSION` | `Session.hpp` 主动定义 | 确认目标构建是否覆盖该宏，再按实际行为验证 | node/party 的会话可信性 |

## 9. 独立结论

IW4X 当前主仓库是一个**以固定宿主地址为核心的注入式客户端/dedicated 扩展工程**，不是一份独立完整的 IW4 服务器源码。

本轮已确认：

- `-dedicated` 确实有入口与生命周期补丁；
- 网络 OOB、Auth protobuf/ECC、Scheduler、server demo、RCon、Node、Party、Steam 和资产接口有源码层实现；
- `clipMap_t`、`MapEnts`、PM/Trace、快照等数据/函数通过宿主结构和固定地址接入；
- server demo 能记录宿主发出的 wire data，但不能因此反推完整服务端逻辑；
- 默认 `DISABLE_SESSION` 使套件中的 ECC session 设计不是当前实际默认路径。

本轮不能宣布：

- IW4X 已被构建、运行或与特定 MW2 宿主匹配；
- 资产格式已被完整解析；
- 碰撞、pmove、snapshot 和游戏逻辑已被独立验证；
- 它可作为 CODOL 3.19 的协议或资产替代品；
- 它是 CoD4x 之外的独立服务器内核。

下一步必须是：锁定宿主身份、初始化锁定提交的依赖、生成并构建，再对宿主函数逐层反汇编和运行核对。

## Second-round verification
All 16 submodules are uninitialized; no build directory, version headers, or iw4x.dll were found.
`Session.hpp` defines `DISABLE_SESSION`; default sends are direct plus one delayed resend.
