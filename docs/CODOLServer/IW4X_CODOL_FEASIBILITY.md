# IW4X 作为 CODOL 服务器/大厅替代的可行性评估

日期：2026-09-24
研究类型：只读静态研究
对象：本地 IW4X 源码、E:\IW4X 运行包、CODOL 运行时抓包与既有分析报告

## 结论摘要

### 直接结论

**把当前 IW4X 服务端直接接到未修改的 CODOL 客户端前，让 CODOL 进入它自己的大厅：不可行。**

原因不是引擎血缘不够近，而是两套产品的服务层和线上契约不同：

1. IW4X 的 dedicated 进程是针对特定 MW2/IW4 构建的服务器运行模式，依赖自己的 `iw4x.dll`、固定的 MW2 内存布局、资源和客户端 ABI。
2. IW4X 的服务器浏览器、Party lobby、匹配选择和游戏连接使用 IW4X 自己的 OOB、InfoString、Session protobuf、ECC 认证和原生 MW2 游戏协议。
3. CODOL 当前已验证的首个载荷是 `ur` UDP 公网地址探测，不是 IW4X 的 `FF FF FF FF` OOB。该探测完成后，CODOL 没有建立可确认的大厅连接，最后报错 `[100] 无法连接大厅服务`。
4. CODOL 的 TCLS、IIPS/TQoS、腾讯大厅/匹配和启动校验链没有被 IW4X 的 master、Party 或 dedicated heartbeat 替代。

因此，IW4X **不能作为 CODOL 的即插即用大厅服务器**。它可以提供服务器工程结构和部分 IW4 系谱实现思路；真正的 CODOL 服务器仍需要单独实现 CODOL 的服务层和客户端所使用的协议适配。

### 可行性分级

- **直接运行 E:\IW4X 的服务端并让 CODOL 连接：不可行。** 当前运行包还缺少与 `iw4x.exe` 配套的 `iw4x.dll`，且协议不匹配。
- **补齐 IW4X 依赖后，让 IW4X 客户端连接 IW4X 服务端：理论上可行。** 这是 IW4X 自己的正常用途，但不能证明 CODOL 兼容。
- **复用 IW4X 的服务器架构，另写 CODOL 兼容服务端：理论上可行。** 需要以 CODOL 的真实请求/响应为依据，逐层替换 TCLS、IIPS、大厅、房间、认证和战局适配器。
- **只把 IW4X 的游戏服端口当作 CODOL 大厅：当前证据不支持。** CODOL 尚未发出任何已知的 IW4X `getInfo`/`connect` 请求。

## 证据等级说明

本文把结论分成三类：

- **已验证事实**：由本地源码、文件清单、既有抓包或运行报告直接支持。
- **合理推断**：由已验证的代码路径或协议结构推导，但尚未由 CODOL 端到端运行确认。
- **未知**：当前材料不足，不能补写协议字段或把猜测当成实现。

本文没有下载或安装 IW4X，没有运行游戏，没有修改 hosts、路由、防火墙、网卡或游戏文件。本报告是任务要求的唯一新增研究产物。

## 一、IW4X 的分层架构

### 1. 基础引擎与 IW4X 自研层

**已验证事实：**

- 本地源码位于 `D:\BaiduNetdiskDownload\使命召唤OL\IW4X\Client核心代码\iw4x-client`。
- 当前 Git 分支为 `main`，提交为 `0699a7e5716ded53bcfa6748bcb89a535f8f39f0`。
- `README.md` 明确将项目描述为 MW2 (2009) 的社区多人平台，并列出 `-dedicated` 命令行模式。
- `src\Game\` 包含对 MW2 引擎函数、dvar、网络结构和服务器数据结构的绑定；`src\Components\Modules\` 包含 IW4X 的模块、Hook、认证、Party、ServerList、Session、Node 等实现。

**合理推断：**

- MW2/IW4 基础引擎提供渲染之外的底层游戏循环、地图/资源加载、实体/玩家状态、基础网络和原生战局服务器能力。
- IW4X 通过 `iw4x.dll` 对这个特定版本的引擎进行 Hook 和扩展，补足 dedicated 启动、服务器浏览、Party、资源下载、认证/安全和社区服务所需的功能。
- 这些 Hook 使用固定地址和特定结构体布局。它们不是通用 IW4 网络插件，也不能直接加载到 CODOL 的 `codoMP_client_shipRetail.exe` 或 Base DLL。

相关证据：`IW4X\Client核心代码\iw4x-client\src\Game\Functions.cpp`、`src\Game\Server.cpp`、`src\Components\Modules\Dedicated.cpp`。

### 2. 游戏服务器 / dedicated 层

**已验证事实：**

- `README.md` 将 `-dedicated` 定义为无头 dedicated server 模式。
- `Dedicated.cpp` 在 dedicated 模式下执行专用初始化，并关闭渲染、音频、部分本地客户端重连和 UPnP 等不需要的子系统。
- 同一文件创建服务器流水线、地图启动和定时任务；它还周期性发送 heartbeat。
- dedicated heartbeat 的代码调用 `Network::SendCommand(master, "heartbeat", "IW4")`。

**架构含义：**

IW4X 的“服务端”不是一个完全独立、与游戏无关的通用大厅程序。它本质上是“特定 MW2 引擎 + IW4X 扩展 DLL”的无头游戏进程。它能加载地图、维护玩家槽位、执行游戏帧和处理战局消息，因此属于**游戏服务器层**。

**未验证事项：**

- 当前 E 盘运行包没有可配对的 `iw4x.dll`，因此本轮没有启动 dedicated，也没有声称已经验证其监听端口或实际战局流量。
- 不应把之前使用 `-dedicated ... +set net_port 28960` 的失败探测当作端口验证；该进程因缺少 DLL 以 `STATUS_DLL_NOT_FOUND` 退出，没有建立监听。

### 3. 主服务器 / server browser 层

IW4X 的“主服务器”主要是服务器发现和登记设施，不等同于 CODOL 的启动服务或大厅服务。

**已验证事实：**

- `ServerList.cpp` 在线列表刷新会访问 `http://master.iw4x.io/v1/servers/iw4x?protocol=...`，读取 JSON 中的服务器 IP、端口和 protocol，并把条目放入查询队列。
- 对于每个服务器，客户端发送 `getinfo` 加 challenge，服务器返回 `infoResponse` 和 InfoString。
- `Dedicated.cpp` 另有 UDP OOB heartbeat，向 master 发送 `heartbeat IW4`。
- `ServerList.cpp` 的代码还保留了 Node System 作为 master 不可用时的发现/同步路径。

这里存在两个不要混淆的通信方向：

1. dedicated server 向 master 发 heartbeat，表示自己可被发现。
2. 客户端向 master 获取列表，再直接向具体游戏服务器发 `getinfo`。

**合理推断：**

IW4X master 解决的是“有哪些 IW4X 游戏服务器”以及“服务器是否存活”，不是账号登录、TCLS ServerDir、地区服务选择或 CODOL 大厅会话。

**不可直接复用的内容：**

- `master.iw4x.io` 的 HTTP JSON 返回结构。
- `heartbeat IW4` 命令和 IW4X protocol number。
- IW4X 的服务器列表筛选字段。

这些字段只在 IW4X 源码中有证据；当前 CODOL 抓包没有出现这些请求。

### 4. Party lobby / 房间层

IW4X 源码里的 lobby 更接近“游戏内 Party/房间”，不是一套独立的腾讯式大厅服务。

**已验证事实：**

- `Party.cpp` 的 `Party::Connect()` 保存目标地址和 challenge，然后发送 `getinfo`。
- 服务端 `getInfo` 处理器返回 `gamename`、`hostname`、`gametype`、`clients`、`sv_maxclients`、`protocol`、`version`、`mapname`、`securityLevel`、下载地址和 `matchtype` 等 InfoString 字段。
- `matchtype` 在源码中明确分为：无匹配、Party lobby、dedicated match、private party。
- 收到 `infoResponse` 后，客户端按照 `matchtype` 分流：
  - dedicated match：调用 `CL_ConnectFromParty()` 进入战局服务器；
  - public party：发送 `getplaylist`；
  - private party：继续本地/Party lobby 流程，并使用 `Steam_JoinLobby()`。
- `Party::PlaylistContinue()` 为房间生成本地 lobby ID，并把 lobby ID 映射到目标网络地址。这个结构说明 IW4X 的房间状态和游戏地址之间由客户端侧 Party 模块组织。

**合理推断：**

- IW4X 的大厅功能主要是“服务器/Party 状态交换 + 本地 UI/Steam 兼容层 + 后续战局连接”，并不是 CODOL 所需的腾讯账号大厅、服务 ID、区服选择和平台安全校验。
- IW4X 源码中没有发现一个可以直接接收 CODOL `ServiceID`、`gameID`、TCLS 结果并把它转换为 IW4X Party 的通用网关。

### 5. 匹配层

**已验证事实：**

- `ServerList.cpp` 有在线服务器列表、过滤、缓存、查询和心跳刷新。
- `Party.cpp` 有 `getInfo`、`infoResponse`、`getplaylist` 和不同 match type 的分流。
- `ServerInfo.cpp` 将 dedicated server 的 `matchtype` 设置为 2，将 Party hosting 的 `matchtype` 设置为 1。
- `ServerInfo.cpp` 的服务端状态查询返回 `statusResponse`，包含服务器 InfoString 和玩家列表。

**合理推断：**

在本地源码可见的范围内，IW4X 的“匹配”更像：服务器列表/节点发现、Party 状态判断、playlist 选择以及连接目标分流。没有足够证据表明它实现了 CODOL 那种由腾讯平台集中维护的账号大厅、排队匹配、跨服房间分配或业务服授权。

因此，IW4X 的 server browser/Party 不能直接替换 CODOL 的大厅服务。

### 6. 会话、节点和安全层

**已验证事实：**

- `Session.cpp` 实现了 `sessionSyn`、`sessionAck`、`sessionFin` 三步会话封装。
- 会话数据使用 protobuf `Proto::Session::Packet`，并使用临时 challenge、ECC 公钥和签名校验。
- `Node.cpp` 使用 `nodeListRequest` / `nodeListResponse` 维护节点列表，并通过 protobuf 保存节点地址、protocol 和端口。
- `Auth.cpp` 的连接流程使用 `connect` 命令、protobuf `Proto::Auth::Connect`、GUID token、公钥、challenge 签名和安全等级。服务端会验证 token、公钥与 XUID 的关系、ECC 签名和 security level，然后才调用 `SV_DirectConnect()`。

**结论：**

这些是 IW4X 自己的安全和节点协议。它们可以作为状态机设计参考，但不能拿来代替 CODOL 的 TCLS/IIPS/平台认证，也不能凭字段名称推断 CODOL 支持同样格式。

## 二、CODOL 已知协议栈对照

### 1. 启动链 / TCLS

**已验证事实：**

- CODOL 的 TCLS `ServerDir` 查询成功，返回过 `ServiceID=715019302`、`gameID=29`、`version=3.19.26.22`、`BranchID=1`、`CrossSvrID=2102017`。
- TCLS 静态 `dirserver.xml`、动态 `dirserverdynamic.ini`、版本服务器配置和 TCLS 明文日志中没有发现 `116.130.224.66`，也没有发现 IW4X master 或 `getinfo` 地址。
- `server_id` 在 CODOL 运行中保持 0；既有对照材料指出 CF 可以出现具体 server_id，但这不等于 CODOL 兼容 IW4X 的 server ID。

**判断：不可直接复用。**

IW4X master heartbeat/JSON 服务器列表无法回答 CODOL 的 TCLS ServerDir 请求。若要让 CODOL 启动链继续走通，需要保留或重实现 CODOL 能理解的 TCLS 返回结构、ServiceID、版本和分支语义；IW4X 的 master 没有这些字段。

### 2. IIPS / TQoS / 公网地址发现

**已验证事实：**

CODOL 捕获到一组完整的 `ur` UDP 交换：

```text
client -> 116.130.224.66:8000 UDP, 24 bytes
75 72 00 10 00 08 00 03 00 00 00 0b 00 00 55 ed
00 00 00 64 00 18 00 00

server -> client UDP, 73 bytes
75 72 00 10 00 39 00 04 00 00 00 0b 00 00 55 ed
00 00 00 00 00 00 00 18 00 00 00 01 00 00 00 0f
31 31 36 2e 31 33 30 2e 32 32 34 2e 36 36 00 00
00 1f 40 00 00 00 0e 32 35 35 2e 32 35 35 2e 30
00 00 00 00 00
```

该帧以 ASCII `ur` 开头，响应携带公网地址字符串、端口 8000 和网段字符串。既有分析已将它归类为 IIPS 公网地址/网段发现；它不是大厅登录握手。

IW4X 的网络 OOB 在 `Network.cpp` 中明确以四字节 `FF FF FF FF` 开头，再拼接命令、换行和数据。两者首部和语义都不同。

**判断：需独立适配，不能复用。**

IW4X server 可以另写一个 `ur` 适配器，但那已经是 CODOL 兼容服务器组件，不是把 IW4X dedicated 直接拿来用。并且 `ur` 响应只解决公网地址发现，不能自动生成 CODOL 大厅地址或房间状态。

### 3. Demonware/Blaze 或腾讯大厅服务层

**已验证事实：**

- 当前最佳采集在游戏进程完成 `ur` 探测后，没有出现可确认的大厅 TCP 连接，也没有出现可归因到大厅的后续 UDP 双向连接。
- 该采集中的 `42.187.183.203:14309` 返回明文 IIPS 配置，包含 `QosMode`、`EnableP2P`、`PsIps` 等，已确认不是大厅协议。
- 采集没有提供 CODOL 大厅请求/响应载荷，也没有提供可用的 Demonware/Blaze 消息样本。

**判断：未知且不能用 IW4X 替代。**

不能因为材料中出现 `DW_LOBBY_*`、`BD_LOBBY_*` 等符号或因为 IW4X 也有 Party，就声称两者线上协议相同。当前最多能说：CODOL 的大厅层尚未被完整寻址或尚未进入；IW4X 的 Party/InfoString 不足以作为替代实现。

### 4. 战局连接层

**已验证事实：**

- 当前 CODOL 捕获没有获得带载荷的对战服握手、状态同步或游戏帧样本。
- IW4X dedicated 对外提供的是它自己的 `getInfo` / `infoResponse`、`getStatus` / `statusResponse`、`connect`、认证 protobuf 和 MW2 原生战局消息。

**判断：未知，不能直接复用。**

只有在后续捕获证明 CODOL 客户端发出的战局连接请求与 IW4/MW2/IW4X 协议相同，才可能复用 IW4X 的某一部分游戏服逻辑。目前没有这样的证据。最稳妥的工程假设是：底层引擎思想可借鉴，线上字段和认证必须重新确认。

## 三、为什么当前 IW4X 不能让 CODOL 进入大厅

### 1. 客户端首先没有发出 IW4X 请求

IW4X 客户端/服务器浏览器的可见入口包括：

```text
FF FF FF FF getinfo\n<challenge>
FF FF FF FF getstatus\n<challenge>
FF FF FF FF connect\n<protobuf>
```

这些是 IW4X 源码中的真实形状，不是 CODOL 抓包中的形状。CODOL 已经捕获到的真实首个协议是：

```text
ur ...
```

因此，IW4X dedicated 即使处在可运行状态，也不会因为“同属 IW4”而自动识别 CODOL 的 `ur` 请求，更不会自动回答 TCLS 或腾讯大厅消息。

### 2. IW4X 的“大厅”不是 CODOL 需要的那一层

IW4X 的 Party 流程通常是：

```text
服务器列表/master
    -> getinfo / infoResponse
    -> matchtype 判断
    -> getplaylist 或 Steam_JoinLobby / CL_ConnectFromParty
    -> IW4X 游戏战局连接
```

CODOL 当前已知流程更接近：

```text
启动链 / TCLS
    -> IIPS / TQoS / 公网地址发现
    -> 腾讯平台大厅或匹配地址选择（当前尚未捕获）
    -> 大厅连接失败，错误 100
    -> 尚未到达战局协议
```

两条链的第一跳、会话对象、认证来源和连接分流均不同。把 IW4X Party 响应伪装成 CODOL 大厅响应，缺少可验证字段依据，也不能绕过 CODOL 客户端前置校验。

### 3. 当前本地运行包本身也不完整

**已验证事实：**

- `E:\IW4X` 包含 `iw4x.exe`、`iw4x\*.iwd`、`zone\patch\*.ff`、`miles\` 和辅助工具。
- `E:\IW4X\iw4x.exe` 的文件信息为 IW4x Multiplayer 4.2.0.0，x86/PE32。
- 该包未发现配套 `iw4x.dll`，也没有 `server.cfg` 或 `autoexec.cfg`。
- 本地 D 盘存在 `iw4x-client` 源码和单独的启动器，但源码仓库不是已经编译好的 `iw4x.dll`。
- 既有隔离探测中，直接启动 `iw4x.exe -dedicated` 因缺少 DLL 以 `0xC0000135 / STATUS_DLL_NOT_FOUND` 退出，未建立监听。

**结论：**

补齐 DLL 只能解决“把 IW4X 自己运行起来”的前置问题，不能解决 CODOL 协议不匹配。不能用 G 盘当前 Steam 的 x64 `iw4mp.exe` 代替 E 盘 x86 IW4X，也不能随机复制 DLL 混配两个构建。

## 四、逐层复用结论

### 可以复用的内容

- dedicated 生命周期：初始化、地图启动、服务器帧、周期任务、日志和退出清理的组织方式。
- 传输与业务分层：将 UDP 接收、消息识别、房间状态、玩家状态和战局状态分开。
- challenge 驱动的请求/响应状态机思路。
- 服务器状态模型：地图、模式、人数、容量、玩家列表、版本和房间状态。
- master/节点发现的缓存、超时、重试和心跳调度思想。
- 现有 `CODOLServer\codol_server.py` 的 adapter、Replay、Recorder 和 `ur` 探测工作台结构。

### 需要适配后才能复用的内容

- UDP OOB 发送/接收框架：只能复用 I/O 组织，必须替换 IW4X 的四字节 OOB 和命令名。
- Server browser：只能借鉴状态查询和缓存，必须改为 CODOL 的真实目录/大厅请求。
- Party/lobby 状态机：必须以 CODOL 的实际大厅请求、房间通知、匹配结果和错误码重新建模。
- 认证和安全：必须使用 CODOL 客户端真实发送的挑战、令牌、签名或平台字段；不能复用 IW4X 的 ECC/Steam GUID 逻辑。
- 战局服务器：必须先获得 CODOL 的战局载荷和版本/资源契约，再判断能否借用 IW4 的实体、快照或可靠消息设计。

### 当前不可复用的内容

- IW4X 固定地址、Hook 地址、结构体 ABI、MW2 函数指针。
- `FF FF FF FF` OOB framing。
- `getinfo`、`getstatus`、`statusResponse`、`heartbeat IW4` 的命令和字段。
- `Proto::Auth::Connect`、`Proto::Session::Packet` 的 protobuf 编号和 ECC 签名流程。
- `master.iw4x.io` / `dp.iw4x.io` 的服务地址、protocol number 和 JSON/heartbeat 契约。
- Steam lobby ID 与 IW4X Party 的地址映射方式。

## 五、最小验证实验

在不修改 CODOL 文件、不改路由/hosts/防火墙、不注入进程的前提下，最小的判别实验应分成三层，不能把三层混成一次“启动服务器”测试。

### 实验 A：验证 IW4X 自身服务器是否完整

目标：只验证 E 盘 IW4X 包能否运行，不涉及 CODOL。

前置条件：获得与该 `iw4x.exe` 同一构建、同一架构的 `iw4x.dll` 及其匹配资源；不能用 G 盘 x64 零售程序或随机 DLL 填补。

验证内容：

1. 在隔离环境中以 LAN-only/本地测试方式启动 dedicated。
2. 确认进程成功初始化并出现 UDP 监听。
3. 用 IW4X 已知 OOB 形状发送 `getinfo`，确认 `infoResponse` 能返回 `gamename=IW4`、protocol、mapname 和 matchtype 等字段。
4. 再用 IW4X 客户端验证 `connect` 和战局初始化。

这只能证明 IW4X 服务端自身可用，**不能证明 CODOL 可以连接**。

### 实验 B：验证 CODOL 是否说 IW4X 协议

目标：在 CODOL 完整重启后进行被动捕获，只观察客户端实际发送的第一批大厅/战局候选请求。

判别规则：

- 如果出现 `FF FF FF FF` 后跟 `getinfo` / `getstatus` / `connect`，才有理由建立 IW4X 协议兼容性假设。
- 如果出现 `ur`、TCLS 自定义帧、TLS 或其他二进制首部，则应先实现对应 CODOL 适配层；IW4X dedicated 不会自动理解它们。
- 必须保留 PID 归因、方向、目标地址、长度和完整载荷；只有端口号不能作为协议结论。

这一步不需要修改网络配置，也不需要让 IW4X 接管 CODOL 的真实远端地址。

### 实验 C：验证能否形成 CODOL 到游戏服的闭环

只有实验 B 找到 CODOL 的大厅/匹配响应并确认客户端会拿到一个战局地址后，才有意义：

1. 记录大厅返回的战局地址、端口、版本、地图/模式和 challenge。
2. 确认 CODOL 随后发出的游戏服握手是否与 IW4X `getinfo`/`connect`/原生战局流一致。
3. 若首部、字段顺序、认证材料或状态码不同，就在 `CODOLServer` 中新增 CODOL adapter，而不是修改 IW4X 的协议名来猜测。
4. 只有请求/响应可重复，且客户端继续推进状态机，才把适配器升级为大厅/房间/战局服务器。

当前材料还没有达到实验 C 的入口，因为 CODOL 在错误 100 之前没有得到可确认的大厅连接。

## 六、对服务器项目的实际建议

### 推荐路线

将 IW4X 定位为**同源服务器架构参考**，将 `CODOLServer` 定位为**CODOL 协议兼容层**：

```text
CODOLServer
  transport / recorder
    -> TCLS adapter
    -> IIPS ur adapter
    -> lobby discovery adapter
    -> room / matchmaking state
    -> game-server adapter
```

现有 `CodolIpProbeAdapter` 可以继续作为 IIPS `ur` 的精确回放/实验组件，但不能把它命名成大厅服务器。它只证明了一个公网地址探测阶段。

### 当前不应做的事情

- 不要把 IW4X 的 `getinfo` 响应直接发给 CODOL 客户端。
- 不要把 CODOL 的 `[100]` 当成 IW4X 认证失败；当前更早的事实是 CODOL 没有成功寻址到大厅。
- 不要把 IIPS/TQoS 的 `8000` 或 `8081` 端口当成 IW4X 游戏服端口。
- 不要把 IW4X 的 `matchtype`、Steam lobby ID 或 `Proto::Auth::Connect` 字段写入 CODOL 协议。
- 不要为了让地址“看起来一致”修改 hosts、路由、网卡或防火墙；这既不能证明协议兼容，也有破坏正常上网的风险。

## 七、最终判定

**问题：把 IW4X 服务器接在 CODOL 客户端前，能否让它连上并进入大厅？**

**答案：以当前未修改的 CODOL 客户端和现有 IW4X 服务端实现，不能。**

卡点按先后顺序是：

1. IW4X 运行包缺少配套 DLL，当前服务端自身尚未可运行。
2. 即使补齐 DLL，CODOL 启动链仍需要 TCLS/TQoS/IIPS 语义，IW4X master/heartbeat 不提供这些结果。
3. CODOL 当前已见的 `ur` 帧与 IW4X OOB 不同。
4. CODOL 尚未发出 IW4X `getinfo`、`infoResponse`、`getplaylist` 或 `connect` 可比对样本。
5. CODOL 大厅和战局认证/资源/版本契约仍未知。

**可行的长期结论：**

可以借用 IW4X 的 dedicated 生命周期、状态机、房间组织、心跳/发现调度和工程分层，另行写出 CODOL 兼容服务器；但那是“基于 IW4X 思路重写 CODOL 服务层”，不是“用 IW4X 服务器直接代替 CODOL 大厅”。

在获得 CODOL 大厅和战局的可重复载荷之前，任何声称“改一个 IP 或换一个 IW4X 端口就能进入大厅”的说法都缺乏证据。

