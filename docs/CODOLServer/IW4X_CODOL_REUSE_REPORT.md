# IW4X 与 CODOL 服务器复用性评估

日期：2026-09-24

本报告把 `IW4X` 目录源码与最近一次 CODOL 管理员 AFD ETW 运行时采集放在一起比较。结论只建立在本地源码、静态配置和实际运行事件上；当前采集没有用户态调用栈，也没有报文载荷，因此不把任何端口或长度猜成 CODOL 对战协议。

## 结论先行

1. IW4X 与 CODOL 都属于 IW4 系谱；这使得 IW4X 的 dedicated 生命周期、服务器状态组织、消息分发和基础网络模型具有真实移植价值。
2. 这不等于二者二进制 ABI 或线上协议相同。IW4X 的 `-dedicated` 是针对其特定 MW2/IW4 构建的无头模式，源码中存在固定地址、函数指针和 ABI 依赖；它不能直接加载到 `codoMP_client_shipRetail.exe`。
3. 最近一次启动复现已经锁定真实游戏进程：`PID 904`，`codoMP_client_shipRetail.exe`。该窗口观测到的是启动/更新/本地 IPC/QoS 候选流量，没有观测到可以确认是 CODOL 对战服的 UDP/TCP 链路，也没有得到载荷。
4. IW4X 可以作为“服务器工程结构参考”，但不能作为 CODOL 字段、封包、认证或端口的来源。写 CODOL 服务器之前仍需要在客户端进入大厅、匹配或战局后，获得带载荷的合法本地测试采集。

## 引擎血缘纠正

这里更准确的表述不是“两个不同引擎”，而是：**CODOL 与 IW4X 都属于 IW4 系谱，且当前 CODOL 游戏二进制、CODOL Base DLL 与 E 盘 IW4X 主程序都是 x86/PE32。**

本地文件证据：

- `COD OL\\codoMP_client_shipRetail.exe`：x86/PE32，SHA-256 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`
- `COD OL\\codoMP_client_shipRetailBase.dll`：x86/PE32，SHA-256 `EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20`
- `E:\\IW4X\\iw4x.exe`：x86/PE32，SHA-256 `49EA90E34C9CD64D9D0AE7F4B399E4ECC5EA13976823B2B8667390A4B8767009`

这条血缘关系改变了工程路线：可以合理地移植 IW4X 的服务器生命周期、dvar/状态模型、OOB 分发、房间/玩家状态组织和引擎层分工，再逐步替换 CODOL 的匹配、房间、认证、安全和资源适配层。

它仍然不意味着可以直接复制固定地址或把 `iw4x.dll` 加载到 CODOL：两个 x86 构建的编译版本、函数布局、结构体 ABI、资源包和服务层都可能不同，必须用 CODOL 自己的调用点和载荷做校验。G 盘当前 Steam `iw4mp.exe` 是 x64/PE32+，不能作为 E 盘这套 x86 IW4X 或 CODOL x86 适配层的直接替代品。

## E 盘部署包复核

用户指出的 `E:\\IW4X` 与前面检查的 `D:\\...\\IW4X` 不是同一个对象。E 盘目录是已经展开的 IW4X Multiplayer 运行包，包含：

- `E:\\IW4X\\iw4x.exe`
- `E:\\IW4X\\iw4x\\iw4x_00.iwd` 至 `iw4x_05.iwd`
- `E:\\IW4X\\zone\\patch\\*.ff`
- `E:\\IW4X\\miles\\*`
- `E:\\IW4X\\binkw32.dll`、`E:\\IW4X\\mss32.dll`
- `E:\\IW4X\\Unlinker.exe`、`E:\\IW4X\\zonebuilder.exe`

`iw4x.exe` 的文件信息为：

- Product：`IW4x`
- FileDescription：`IW4x Multiplayer`
- FileVersion/ProductVersion：`4.2.0.0`
- PE：x86/Win32
- SHA-256：`49EA90E34C9CD64D9D0AE7F4B399E4ECC5EA13976823B2B8667390A4B8767009`

它的 PE 导入表明确包含 `iw4x.dll`。但当前 E 盘目录及已检查的 D 盘 IW4X 树中都没有找到 `iw4x.dll`，同时 E 盘也没有 `server.cfg` 或 `autoexec.cfg`。因此这不是“没有多人服务器入口”，而是当前部署不完整，缺少核心运行 DLL 和用户服务端配置。

对 E 盘 `iw4x.exe` 执行了一次短时隔离探测：

```text
iw4x.exe -dedicated -stdout -nointro +set sv_lanOnly 1 +set net_port 28960 +map mp_rust
```

进程退出码为 `0xC0000135`（`STATUS_DLL_NOT_FOUND`），没有建立 TCP/UDP 监听。这与导入表缺少 `iw4x.dll` 相互印证；该探测进程已结束，没有修改 E 盘文件。

资源包 `iw4x_00.iwd` 内存在 `default_mp.cfg`、`default_mp_gamesettings.cfg`、`ui_mp/createserver.menu` 和 `ui_mp/joinserver.inc`。这些内容确认了多人/建服 UI、`sv_hostname`、`sv_maxclients`、地图和游戏模式等服务端配置模型，但它们不是 CODOL 配置，也不能补足缺失的 `iw4x.dll`。

因此，对 `E:\\IW4X` 的准确标签是：**IW4X Multiplayer 专服运行包（当前缺少核心 DLL，尚未可运行）**。补齐与该 `iw4x.exe` 同版本匹配的 `iw4x.dll` 后，才适合继续验证 `-dedicated` 的监听端口、OOB 请求和服务器状态响应。

## 与正版 Steam MW2 的配对结果

用户提供的：

`G:\\SteamLibrary\\steamapps\\common\\Call of Duty Modern Warfare 2`

确实是正版 Steam 多人安装。`G:\\SteamLibrary\\steamapps\\appmanifest_10190.acf` 显示：

- AppID：`10190`
- 名称：`Call of Duty: Modern Warfare 2 (2009) - Multiplayer`
- BuildID：`25126410`
- 安装文件约 `12.1 GB`
- 有原版 `iw4mp.exe`、`main\\` 和 `zone\\english\\` 资源

但是，这个当前 Steam 安装与 E 盘 IW4X 包存在架构代际差异：

| 文件 | 架构 | SHA-256 |
|---|---|---|
| `G:\\...\\iw4mp.exe` | x64 / PE32+ | `FD3AFF1F539525F5A798C5F5953DDBF651037AFBC52D50C5ABBEA749EFD2ABE2` |
| `E:\\IW4X\\iw4x.exe` | x86 / PE32 | `49EA90E34C9CD64D9D0AE7F4B399E4ECC5EA13976823B2B8667390A4B8767009` |

E 盘 IW4X 目录没有 `main\\`，而正版 G 盘目录没有 `iw4x\\` 覆盖资源；两者从目录结构上是“基础游戏 + IW4X 覆盖包”的关系。但 x64 的当前 Steam `iw4mp.exe` 不能直接替代 IW4X 所针对的 x86 MW2 引擎，E 盘 x86 `iw4x.exe` 也不能直接加载成 x64 零售程序的 DLL。

因此目前不能做以下操作：

- 不要把 G 盘 `iw4mp.exe` 改名覆盖 E 盘 `iw4x.exe`。
- 不要把 x64 Steam 可执行文件当成 x86 IW4X 的引擎基址。
- 不要从 G 盘随意复制 DLL 到 E 盘，尤其不能用 x64 DLL 填补 `iw4x.dll`。
- 不要在未确认版本匹配前把两套 `main`、`zone` 或 IWD/FF 文件强行合并。

准确的当前状态是：**正版许可证和基础资源已经找到，但 G 盘当前 Steam 多人程序不是 E 盘这套 x86 IW4X 运行包所需的同代引擎；E 盘还缺少匹配的 x86 `iw4x.dll`。** 需要同版本 IW4X 发布包/源码构建产物与其对应的 MW2 x86 基础环境，才能做实际专服启动验证。

## IW4X 的实际性质

本地仓库状态：

- 路径：`IW4X\\Client核心代码\\iw4x-client`
- 分支：`main`
- HEAD：`0699a7e5716ded53bcfa6748bcb89a535f8f39f0`
- 项目类型：`SharedLib`
- 架构：x86/Win32
- 支持命令行：`-dedicated`

源码中的 `src\\Game\\Server.cpp` 使用 MW2 进程内固定地址，例如 `0x48AD30`、`0x4BC3A0`、`0x460480` 和 `0x31D9390`。这些地址不是 CODOL 的网络地址，而是 IW4X 对特定 MW2 引擎布局的调用入口。即使两个产品都来自 Call of Duty 系列，也不能据此共享服务器 ABI。

## IW4X 可以提供的协议参考

下面是“形状上的参考”，不是 CODOL 协议证据：

- `Network.cpp` 的 OOB 数据前置四字节 `FF FF FF FF`，随后是命令、换行和数据。`SendCommand` 形成的逻辑结构是 `command + "\\n" + data`。
- `ServerList.cpp` 使用 `getinfo` 加 challenge 查询服务器摘要；服务器地址列表还来自 IW4X 自己的 `master.iw4x.io/v1/servers/iw4x?protocol=...` HTTP 服务。
- `ServerInfo.cpp` 使用 `getstatus`，并用 `statusResponse` 返回信息字符串和玩家列表。这可以启发 CODOL 服务器的状态模型，但不能说明 CODOL 也接受同名命令。
- `Dedicated.cpp` 在 dedicated 生命周期中执行初始化、地图/帧循环和定时 heartbeat，源码中的 heartbeat 是发送 `heartbeat IW4` 到 IW4X master。这个调度模式可以复用，地址和字段不能复用。
- `Auth.cpp` 的连接流程包含 challenge、ECC 签名、公钥、token、infostring，以及 `Proto::Auth::Connect` protobuf。它是 IW4X 自己的认证协议，不能直接拿来替代 CODOL 的 TCLS、TenProxy、TCLS/匹配会话或安全校验。
- `Node.cpp` 提供 `nodeListRequest`/`nodeListResponse` 和节点存活时间管理。这是 NAT/节点发现的工程模式，只有在 CODOL 运行时证据证明存在同等功能后才值得实现。

关键源码位置：

- `IW4X\\Client核心代码\\iw4x-client\\src\\Components\\Modules\\Network.cpp:184-228`
- `IW4X\\Client核心代码\\iw4x-client\\src\\Components\\Modules\\ServerList.cpp:427-429,1228-1232`
- `IW4X\\Client核心代码\\iw4x-client\\src\\Components\\Modules\\ServerInfo.cpp:78-80,202-254`
- `IW4X\\Client核心代码\\iw4x-client\\src\\Components\\Modules\\Dedicated.cpp:163-178,286-289`
- `IW4X\\Client核心代码\\iw4x-client\\src\\Components\\Modules\\Auth.cpp:146-152,155-272`
- `IW4X\\Client核心代码\\iw4x-client\\src\\Components\\Modules\\Node.cpp:46-56,303-349`

## CODOL 最近一次运行时复现

采集原始目录：

`run_codol_001\\runs\\NET_CAPTURE_ELEVATED_20260924_134453`

游戏专属重解析文件：

`run_codol_001\\runs\\NET_CAPTURE_ELEVATED_20260924_134453\\game_etw.jsonl`

运行归因：

- 进程：`codoMP_client_shipRetail.exe`
- PID：`904`
- 运行时窗：约 `13:44:58` 至 `13:45:10`（中国标准时间）
- AFD 事件：`1461`
- socket 世代：`68`
- 成功 `connect`：`20`
- `sendto`：`113`
- 采集能力：地址、端口、socket 类型、操作顺序和字节数
- 采集缺口：用户态调用栈、线程、报文内容和协议字段

观测到的对端分层如下：

- `122.96.96.225:8081`：UDP `sendto` 密集流量，DNS 交叉证据为 `tqos.gamesafe.qq.com`。长度出现 `84`、`132`、`196`、`228`、`244`、`260`、`308`、`324`、`356`、`372`、`388`、`756` 等。当前窗口没有对应的 `recvfrom` 载荷，因此只能标为 QoS/遥测候选，不能标为对战服。
- `101.72.248.61:80` 和 `61.241.53.221:80`：成功 TCP 连接并发生请求/响应，形态符合 HTTP/引导或更新流量。
- `218.61.165.132:443` 和 `101.72.248.61:443`：成功 TCP 连接并发生 TLS 形态的收发，当前无法从 AFD 事件恢复明文服务语义。
- `127.0.0.1:62543`、`62545`、`62549`、`62551`、`62555`、`62557`、`62562`、`62564`：游戏进程到本机服务的回环连接，属于本地 IPC/辅助组件候选，不是外部对战服证据。

本次窗口没有出现“外部 UDP 双向游戏流”或“能够从调用者和载荷证明是对战层”的 socket。`game_rt_report.md` 因此正确地把游戏候选 socket 保留为未确认，而不是强行输出 `GAME_CONFIRMED`。

## 为什么不能直接套 IW4X

- **同系但不同构建**：CODOL 与 IW4X 都基于 IW4 系谱，但 CODOL 客户端/`codoMP_client_shipRetailBase.dll` 与 IW4X 的 MW2 基础构建有不同的内存布局、函数 ABI、消息对象、资源布局和安全组件。亲缘关系支持移植思路，不支持直接复用地址或 DLL。
- **协议未证实相同**：`FF FF FF FF`、`getinfo`、`getstatus`、`connect` 和 IW4X protobuf 只在 IW4X 源码中得到证实。CODOL 当前没有任何载荷证据支持这些字段。
- **认证不可移植**：IW4X 的 ECC challenge 签名、公钥和 token 是其生态自己的信任链。复制这些字段既不能让 CODOL 客户端通过，也会把猜测误当成实现。
- **发现服务不同**：IW4X master 是公开的 IW4X 服务；CODOL 静态配置中的 TCLS、版本服务、STUN、IIPS、Cross 和 QoS 不能互相替代，更不能把 QoS 地址改名为游戏服。
- **当前传输形态不同**：本次 CODOL 启动窗口的主要 UDP 外联是单向 `:8081`，主要 TCP 外联是 `:80/:443`。这与 IW4X 的游戏 OOB/服务器浏览器结构不是同一份证据。

## 当前实现路线

`CODOLServer\\codol_server.py` 已从单纯回显器升级为可运行的 IW4 系谱服务器内核：

- `EngineState`：hostname、地图、模式、容量、房间状态、玩家列表和 match generation。
- `ProtocolAdapter`：观测、精确回放、固定响应、显式回显和 IW4 OOB 状态查询可独立组合。
- `Iw4OobAdapter`：只实现有源码证据的 `getinfo`/`getstatus` 形状，不实现猜测的 `connect`。
- `ReplayAdapter`：只按已捕获的完整请求字节回放对应响应，避免凭空制造 CODOL 字段。
- `ProtocolRecorder`：保存输入、输出、消息识别结果和连接生命周期，作为后续协议 def-use 的实验材料。

这个内核是服务器工程的第一层；下一层才是 CODOL 适配器，目标是把已验证的匹配查询、房间消息和游戏服务器会话逐步接入状态机。

## 可复用与不可复用边界

可以复用：

- 传输层和业务层分离的代码组织。
- 按命令或消息类型注册处理器的结构。
- challenge 到 connect 的显式状态机思想，但字段必须重新确定。
- server info、玩家列表、地图、人数和 ping 的独立状态模型。
- dedicated 生命周期、定时任务、heartbeat 和日志结构。
- 节点/房间发现的缓存、超时和重试框架，前提是后续采集证明 CODOL 需要它。

不能复用：

- IW4X 的 `FF FF FF FF` OOB framing。
- `getinfo`、`getstatus`、`statusResponse`、`heartbeat IW4` 等命令名及其字段。
- `Proto::Auth::Connect` 的 protobuf 编号和 ECC 签名流程。
- `master.iw4x.io`、IW4X protocol number、IW4X 端口和节点列表。
- `Game::Server` 中的固定地址、函数指针、结构体布局和客户端 ABI。

## 服务器编写的当前门槛

现有 `CODOLServer\\codol_server.py` 继续保持为本地 raw-frame 观察/回放工作台：默认回显，支持 TCP/UDP、十六进制响应、JSONL 和前缀记录。它还没有宣称实现账号、反作弊、安全签名或游戏对战协议，这是当前证据水平下正确的边界。

下一次动态采集的有效入口是：

1. 使用已经固化的启动链进入客户端自己的大厅、匹配或战局流程。
2. 同时保留 PID 归因，单独记录 `codoMP_client_shipRetail.exe` 的网络事件。
3. 获取带载荷的受控本地测试记录，再按连接建立前后、方向、长度、重复字段和错误响应分离协议层。
4. 只有出现可重复的客户端请求和服务端响应后，才开始写 CODOL 的握手/房间/对战状态机。

在这之前，IW4X 的正确定位是“同系服务器架构基线”，而不是“CODOL 字段和认证的直接替代品”。
