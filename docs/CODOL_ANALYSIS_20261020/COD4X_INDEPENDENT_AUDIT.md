# CoD4x 21.2 独立审计

日期：2026-10-21（Asia/Shanghai）

范围：`CoD4x_Server-21.2` 自身源码、构建、资产、文档。此阶段不引用 CODOL 3.19 或 IW4X 的协议结论，不进行交叉推断。

## 0. 审计状态与覆盖定义

状态：**进行中，未完成。**

本文件是 CoD4x 21.2 自身的全栈审计，不引用 CODOL 或 IW4X 的结论。审计对象分为两个实现层，分别计数、分别判定：

1. **可读 C/C++ 层**：`src` 顶层 218 个 `.c/.cpp/.h` 文件，其中 170 个已按粗粒度职责域归类，53 个尚未按细粒度职责归类。这个数字只说明文件盘点，不说明逐文件行为已复核。
2. **反汇编恢复层**：`src/asmsource` 共 110 个 `.asm`，含 2979 个 `global` 导出指令。主要职责域分布为：碰撞/cm 13 文件 163 个导出、物理 6 文件 167 个导出、pmove/移动 4 文件 66 个导出、游戏逻辑 `_g_*` 27 文件 948 个导出、db/资产 5 文件 576 个导出、脚本 8 文件 179 个导出、模型/渲染 13 文件 239 个导出。未逐符号证明行为等价。

此外还有：

- `botlib`：59 文件，约 1.22 MB；
- `bspc`：86 文件，约 20.28 MB；
- `plugins`：14 个目录及公共 ABI 头；
- 内置库源码：`src/mbedtls`（159 文件，约 3.96 MB）、`src/tomcrypt`（202 文件，约 0.77 MB）、zlib；
- 独立测试文件 `src/tests.c`，其中主要 delta 测试体被注释。

### 0.1 A-S 覆盖状态

| 域 | 状态 | 当前依据 |
|---|---|---|
| A 身份与构建 | 部分完成 | 版本 21.2、目标二进制名、GCC/MinGW 32 位、AGPL-3.0、Makefile |
| B 入口与生命周期 | 部分完成 | `Sys_Init -> Com_Init -> SV_Init`、`Com_Frame -> SV_Frame`、`SV_Shutdown` |
| C 帧循环与线程 | 部分完成 | `SV_Frame` 时间残差、`NET_Sleep`、插件帧事件、线程锁 |
| D 网络基础层 | 部分完成 | UDP OOB、TCP RCON、IPv4/IPv6 socket |
| E 连接状态机 | 部分完成 | `SV_DirectConnect`、`getchallenge`、`SV_ClientEnterWorld`、超时 |
| F 消息与传输 | 部分完成 | `netchan.c`、`msg.c`、Huffman、可靠命令、分片 |
| G 地图与资产 | 部分完成 | `SV_SpawnServer -> CM_LoadMap -> CM_LoadMapFromBsp` |
| H 世界与碰撞 | 部分完成 | clipMap 结构、trace、brush、BSP 加载；未逐资产验证 |
| I 移动与控制 | 部分完成 | usercmd 解析、`SV_ClientThink -> ClientThink -> Pmove`、pmove 汇编 |
| J 实体与状态 | 部分完成 | 实体、client、playerstate、field 表存在；未逐字段验证 |
| K 快照与复制 | 部分完成 | snapshot 帧历史、delta entity/client/playerstate、Huffman 发送 |
| L 游戏逻辑 | 部分完成 | `G_InitGame`、实体串、spawn 链；未逐模式/武器/伤害通读 |
| M 脚本与规则 | 部分完成 | GSC VM、script commands、加载器存在；未做完整语义审计 |
| N 配置与管理面 | 部分完成 | cvar、cmd、rcon、download、webadmin |
| O 认证与安全 | 部分完成 | auth、sign/update、XAC、banlist、pure file checks |
| P 插件与平台适配 | 部分完成 | 导出 ABI、回调、插件示例和加载器 |
| Q 外部服务 | 部分完成 | master、auth、TCP RCON、update proxy |
| R 构建与验证 | 未完成 | 未在本工作区构建/运行；无原版 CoD4 资产确认 |
| S 缺口与版本适用性 | 进行中 | 本文件持续登记 |

> 状态“部分完成”表示已找到实现与调用链，不代表所有分支、数据结构、边界行为均已核验。

## 1. 输入身份

| 项 | 核验结果 |
|---|---|
| 目录 | `CoD4x_Server-21.2` |
| 版本 | `src/version/version.c:3` 为 `SYS_COMMONVERSION 21.2` |
| 目标服务器名 | Makefile 的 `TARGETNAME=cod4x18_dedrun` |
| 构建形态 | 32 位，`-m32 -msse2 -mfpmath=sse`；Windows MinGW / Linux GCC |
| 主要产物 | 工作区 `bin` 仅含 0 B `dummy`，未发现构建后的 `cod4x18_dedrun` |
| 许可证 | AGPL-3.0，`License.md` / README |
| 源码规模 | 顶层 C/C++/H 218 文件；汇编 110 文件、2979 个全局符号 |
| 运行资产 | README 要求 Cod4 原版 `main/*.iwd` 与 `zone/*`；工作区未确认完整资产 |
| 构建依赖 | NASM、GCC/G++；mbedTLS、LibTomCrypt、zlib 源码在 `src` 内；`lib/` 仅 `libs.txt`，尚无已构建静态库 |

构建层审计结论：

- 这不是“只有 C”的项目。可读 C/C++ 负责网络、文件系统、命令、插件、部分地图加载；大量核心逻辑（pmove、碰撞、游戏实体、脚本、模型）由 `src/asmsource` 中的反汇编实现。
- 已构建静态库缺失并不意味着源码不完整：Makefile 有 mbedTLS、LibTomCrypt 子构建规则；当前副本仍需先完成这些依赖构建才能最终链接。
- 工作区没有确认 Cod4 原版 zone/iwd 资产，因此即使构建成功，也不能声称可以启动地图。

## 2. 服务端生命周期

已核实的调用主干：

```text
Sys_Init / platform main
  -> Com_Init
       -> Com_InitZoneMemory
       -> Sys_Init
       -> NET_Init
       -> Netchan_Init
       -> SV_Init
  -> Com_Frame
       -> Com_EventLoop
       -> SV_Frame
       -> PHandler_Event(ONFRAME)
       -> NET_Sleep / TCP packet loop / thread callbacks
```

证据：

- `src/common.c:681` `Com_Init`；`:716` `Sys_Init`；`:717` `NET_Init`；`:779` `Netchan_Init`；`:784` `SV_Init`。
- `src/sv_main.c:3126` `SV_Init`，注册命令、cvar、banlist、server id、master heartbeat、SAPI/XAC。
- `src/common.c:1054` 调用 `SV_Frame(usec)`。
- `src/sv_main.c:4156` `SV_Frame`：时间残差累积，未到帧间隔时 `NET_Sleep` 并返回；到间隔后 `SV_PreFrame`、按 `G_RunFrame(svs.time)` 推进、`SV_SendClientMessages`、`SV_CalcPings`、`SV_CheckTimeouts`。
- `src/sv_main.c:2792` `SV_Shutdown`：最终消息、master shutdown、game progs、client、demo、server state 清理。
- `src/sys_net.c:3734` `NET_Sleep`：`select()` 等待 IPv4/IPv6/TCP socket，有包时进入 `NET_Event`。

关键边界：

- 注释明确“Player movement occurs as a result of packet events, which happen before `SV_Frame` is called”。网络输入和世界模拟不是同一层。
- `SV_Frame` 的 `sv_fps` 默认值为 20，`G_RunFrame` 在时间残差内可多次执行；快照发送另有客户端 `snaps` 节流。
- 插件在 `SV_Frame` 后收到 `ONFRAME`，可见插件是帧生命周期的一部分，不是独立 daemon。

## 3. 网络与传输

### 3.1 socket 与事件分发

- `NET_Init` 建立 UDP/TCP socket；`NET_Event` 从 socket 读取最多 `MAX_NETPACKETS` 个包，交给 `NET_UDPPacketEvent`。
- `NET_UDPPacketEvent` 在 `MSG_InitReadOnly` 后调用 `SV_PacketEvent`，允许插件在 `ONUDPNETEVENT` 中提前接管。
- `SV_PacketEvent` 以首 4 字节序列号区分：

```text
0xffffffff -> OOB/connectionless
0xfffffffe -> update proxy（COD4X18UPDATE）
0xfffffff0 -> reliable message fragment
其他       -> qport + client netchan
```

### 3.2 OOB 与 challenge

- `SV_ConnectionlessPacket` 在 `sv_main.c:1848` 开始解析，命令包括 `getstatus`、`getinfo`、`rcon`、`connect`、`stats`、`getchallenge`、update proxy 和 voice。
- `SV_GetChallenge` / `SV_DirectConnect` 的状态转移可从 `SV_ConnectionlessPacket` 追到 `sv_client.c:138` `SV_DirectConnect`，再进入 `ClientConnect`，最后由 `SV_ClientEnterWorld` 调用 `ClientBegin`。
- `sv_client.c:1672` `SV_SendClientGameState` 负责认证后 config/state priming。

### 3.3 netchan 格式

`src/netchan.c` 头注释和实现给出：

```text
4 bytes outgoing sequence（最高位表示 fragment）
2 bytes qport（仅 client -> server）
4 bytes fragment start
2 bytes fragment length
```

- `FRAGMENT_BIT = 1 << 31`；分片由 `Netchan_Transmit` 和 `Netchan_TransmitNextFragment` 处理。
- `Netchan_Process` 丢弃 `sequence <= incomingSequence` 的包，计算 dropped，重组要求 fragment 顺序连续；乱序 fragment 被丢弃，不做乱序缓存补齐。
- `qport` 用于地址端口映射不稳定时匹配连接。
- 传输层为 UDP datagram，不在此文件实现加密；应用层另有 Huffman 压缩。

### 3.4 client/server 消息

`sv_client.c:1865` `SV_ExecuteClientMessage`：

- 先做 Huffman 解压；
- 以 3 bit 读取 clc；
- `clc_move` / `clc_moveNoDelta` -> `SV_UserMove`；
- `clc_clientCommand` -> `SV_ClientCommand`；
- `clc_EOF` 终止。

`net_game_conf.h` 定义 `svc_*` / `clc_*` 枚举，客户端消息不是直接裸结构，而是压缩后的位流。

### 3.5 连接与可靠命令边界

- `sv_client.c:1004` `SV_UserMove` 读取 cmd 数量、按 `sv.checksumFeed` + ack + command hash 的 key 解 delta usercmd、读取 predicted origin/time。
- 重复和过旧 usercmd 使用 `lastUsercmd.serverTime` 丢弃；随后 `SV_ClientThink`，再到游戏侧的 `ClientThink`。
- `sv_snapshot.c:48` 头注释明确服务端消息的层序：sequence、reliable commands、`svc_snapshot`、last reliable、serverTime、lastframe、snapFlags、area、playerstate、packetentities。
- 可靠命令通过 `reliableSequence`/`reliableAcknowledge` 在 `SV_UpdateServerCommandsToClient` 重发，配置串超长时分块。

## 4. 地图与碰撞

### 4.1 地图加载链

已核实：

```text
SV_SpawnServer
  -> DB_LoadXAssets(map)
  -> CM_LoadMap(map, &checksum)
       -> CM_LoadMapFromBsp
            -> CMod_LoadMaterials
            -> CMod_LoadPlanes
            -> CMod_LoadBrushRelated
            -> CMod_LoadNodes
            -> CMod_LoadLeafSurfaces
            -> CMod_LoadCollisionVerts
            -> CMod_LoadCollisionTriangles
            -> CMod_LoadCollisionEdgeWalkable
            -> CMod_LoadCollisionBorders
            -> CMod_LoadCollisionPartitions
            -> CMod_LoadVisibility (optional)
            -> CMod_LoadEntityString
  -> Com_LoadWorld
  -> CM_LinkWorld
  -> SV_InitGameProgs
```

证据：

- `sv_main.c:4727` `SV_SpawnServer`。
- `sv_main.c:4890` `CM_LoadMap`。
- `cm_load_obj.cpp:1066` `CM_LoadMapFromBsp`。
- `cm_local.h:164-230` `clipMap_t` 含 planes、brush sides、brush edges、nodes、leafs、leaf brushes、triangle data、borders、partitions、AABB trees、submodels、brushes、visibility、mapEnts。

### 4.2 碰撞查询

- `sv_world.cpp:1457` `SV_Trace` 先 `CM_BoxTrace(results, start, end, mins, maxs, 0, contentmask)`，再处理静态模型和动态实体。
- `SV_PointContents` 对世界和实体做内容查询。
- `CM_BoxTrace`、`CM_PointContents` 及 brush/AABB 逻辑由 C++/汇编共同实现；本轮确认的是结构和实际调用链，尚未验证每个 brush 边界、斜面、边缘和内容位的语义。

### 4.3 出生实体

- `G_InitGame` 在 `_g_main_mp.asm:505`，其中 `:641` 调用 `G_SpawnEntitiesFromString`。
- `_g_spawn_mp.asm:590` `SP_worldspawn`，`:1375` `G_SpawnEntitiesFromString`。
- 实体串来源于 `CM_LoadMapFromBsp -> CMod_LoadEntityString`；`MapEnts` 结构保存 name、entityString、numEntityChars。

独立结论：CoD4x 拥有完整的“资产 -> clipMap -> trace -> spawn 实体”架构，但本轮只确认了入口、结构和主要调用链，没有用一张 Cod4 地图逐 brush、逐实体做运行验证。

## 5. 移动与玩家状态

### 5.1 usercmd 到客户端逻辑

- `sv_client.c:1004` 解析 usercmd，`sv_client.c:3030` `SV_ClientThink`，随后进入游戏侧 `ClientThink`。
- usercmd 解析包含校验：时间回退/重复丢弃、武器合法性修正、predicted origin 读取。

### 5.2 pmove 是汇编恢复实现

- `_bg_pmove.asm:5633` `Pmove`。
- `_bg_slidemove.asm:620` `PM_StepSlideMove`。
- `_bg_pmove.asm:410` `PM_GroundTrace`。
- `PM_playerTrace`、`PM_ClipVelocity`、`PM_AirMove`、`PM_CheckDuck` 等均在 `_bg_pmove.asm` 的导出表中。

因此，分析 CoD4x 的移动不能只读 `bg_jump.cpp` 或 `sv_client.c`。真正的步进、贴墙、地面 trace 在汇编源内，需按 ASM 行为审计。

### 5.3 玩家/客户端状态

- `playerState_t`、`clientState_t`、实体字段表存在于 `msg.c` / `server.h` / `g_*` 等实现。
- 快照读写通过 `MSG_WriteDeltaPlayerstate`、`MSG_WriteDeltaClient`、`MSG_WriteDeltaEntity`；但字段变化、基线、掩码和溢出边界尚未逐项验证。
- `groundEntityNum` 是状态字段，不是碰撞函数本身；碰撞来源应沿 `PM_GroundTrace -> PM_playerTrace -> CM_BoxTrace` 查，不能用字段值倒推实现。

## 6. 快照与复制

`sv_snapshot.c:109` `SV_WriteSnapshotToClient` 的实现已确认：

1. 选择 delta frame；
2. 写 `svc_snapshot`、serverTime、lastframe、snapFlags；
3. 写 playerstate delta；
4. 按 entity 列表写新增/更新/删除；
5. 按 client 列表写新增/更新/删除；
6. `SV_SendMessageToClient` 做 Huffman 压缩并由 `SV_Netchan_Transmit` 发送。

存在并已定位：

- `client->frames[PACKET_MASK]` 帧历史；
- `deltaMessage` / `lastframe` / `messageAcknowledge`；
- baseline、archived snapshot、cached snapshot buffer；
- 快照频率由 `sv_fps` 与客户端 `snaps` 控制；
- rate 限制与 `rateDelayed`；
- 服务端可靠命令的重发和确认。

未闭合：

- 每个 entity/client/playerstate 字段的 delta 边界；
- archived snapshot 与普通 snapshot 的完整切换条件；
- demo recording 对 delta frame 的强制策略；
- 在真实客户端和真实地图上的帧边界与回放验证。

## 7. 配置、命令与插件

### 7.1 配置与命令

- `cvar.c` / `cmd.c` 可读，`SV_InitCvarsOnce` 注册大量服务器 cvar；`Com_Init` 和 `SV_Init` 都有命令注册。
- `sv_cmds.c` 实现服务器管理命令、地图切换、rcon 等。
- `sv_client.c` 的 download 逻辑包含 pak 校验、HTTP/FTP 重定向和失败清理。

### 7.2 插件 ABI

`plugins` 提供：

- `callback_declarations.h`
- `function_declarations.h`
- `plugin_declarations.h`
- `pinc.h`
- 14 个示例/实际插件目录

插件事件包括 `ONFRAME`、`ONUDPNETEVENT`、`ONCLIENTMOVECOMMAND`、`ONCLIENTENTERWORLD`、`ONPLAYERGOTAUTHINFO` 等。插件可以接管 UDP 事件，因此服务器核心与插件不是完全隔离的。

### 7.3 认证、XAC、更新

- `sv_auth.c`、`sec_*`、`sv_banlist.c`、`xac_helper.c` 均存在。
- `SV_ConnectionlessPacket` 分派 `getchallenge` / `connect` / `stats` / update proxy。
- `sec_update.c` 实现更新代理；不是普通 gameplay 服务器的功能（但属于全服务器运维面）。
- 这些模块的密码学实现与更新协议尚未逐消息、逐错误分支验证。

## 8. 构建、测试与资产

### 8.1 构建

- Makefile 目标：`cod4x18_dedrun`。
- 编译选项：32 位、SSE2、可选 debug/release；C 与 C++ 混编；NASM 汇编。
- 当前 Windows 会话没有可用的 `gcc`、`g++`、`nasm` 或 `mingw32-make`，因此未执行构建。
- `lib/` 尚未生成静态库；mbedTLS、LibTomCrypt 和 zlib 的源码及子构建规则在 `src` 内。
- 工作区 `bin` 只有空 `dummy`，没有已构建服务器。

### 8.2 测试

- `src/tests.c` 中 `MSG_TestDeltaAE`、`MSG_TestDeltaPS`、`MSG_TestDeltaCS` 的主体被整段注释；`Tests_Init()` 也没有注册这些命令。
- GitHub workflow 只执行构建、版本比较和插件打包，没有测试步骤。
- 因此不能把“有 tests.c”当作持续测试或行为验证。

### 8.3 资产

README 要求 Cod4 原版：

```text
main/*.iwd
zone/*
```

但工作区没有确认完整资产。没有原版 zone/iwd 时，无法进行 `+map`、地图加载、clipMap trace、实体串和客户端兼容验证。

## 9. 缺口登记

| 缺口 | 原因 | 获取方式 | 解除什么 |
|---|---|---|---|
| 未完成构建 | 静态库目录缺实际库；未执行 make | 在独立构建目录补齐依赖并编译 | 验证源码可执行 |
| 未实际运行 | 无原版 Cod4 zone/iwd | 获取合法 Cod4 服务端资产 | 验证地图、客户端和生命周期 |
| 未逐符号核验汇编 | asmsource 2979 个全局导出，尚未逐个 | 按域建立符号表，选关键调用链反汇编/运行对照 | pmove、碰撞、游戏逻辑 |
| pmove 边界未验证 | 核心为汇编 | 固定输入 + trace + 状态输出对照 | 贴墙、台阶、斜面、落地 |
| 地图 brush/trace 未验证 | 只有加载链与结构，无地图样本回放 | 用 Cod4 地图做逐坐标 trace | 真实世界碰撞 |
| 测试覆盖弱 | tests.c 被注释；CI 无测试 | 新增隔离测试或外部脚本 | 回归可重复性 |
| 插件事务边界未验证 | 只读公共 ABI 与调用点 | 逐插件导出/回调测试 | 崩溃风险与隔离边界 |
| 资产列表未闭合 | 未确认所有 zone/iwd | 对合法安装做清单与哈希 | 启动与地图可复现 |

## 10. 独立结论

CoD4x 21.2 是一个**完整的有源码思路、但核心逻辑大量落在反汇编实现中的 CoD4 专用服务器**。本轮已经确认：

- 有可追踪的启动、帧循环、网络、地图 load、trace、pmove、snapshot、插件与管理面；
- 有明确的 `SV_SpawnServer -> CM_LoadMap -> SV_Trace` 世界链；
- 有明显的现代服务器扩展（TCP RCON、更新代理、XAC、插件、IPv6）；
- 但它不是 CODOL，也不是 IW4X，不能从本审计直接推导目标协议兼容。

本轮**不能**宣布：

- 已完整审计全部 2979 个汇编导出；
- 已在真实地图上验证 pmove/trace/出生；
- 已构建并运行服务器；
- 已证明客户端兼容；
- 可以把 CoD4x 的消息、字段或资产格式直接用于 CODOL 3.19。

后续独立审计应先补构建和合法资产运行，再按符号职责逐层验证汇编层，最后才进入交叉验证。
