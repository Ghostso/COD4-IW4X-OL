# CODOL TCLS ServerDir 结构分析

分析日期：2026-09-24  
范围：CODOL `ServerDir`、TCLSHost/TCLSCore 桥接、目录树节点和启动参数。  
方式：只读静态 PE 分析、既有日志/抓包/反汇编证据交叉核对。  
限制：没有修改 sandbox、TCLS DLL、INI、hosts、路由、防火墙或网卡；没有对游戏本体注入，也没有启动或杀死进程。

## 结论先行

1. `ServiceID=715019302` 是 TCLS 的服务标识，用来让 `ServerDir` 选择/查询对应业务目录；它不是大厅 IP、端口，也不是 `server_id`。
2. `gameID=29` 是 CODOL 产品标识；`CrossSvrID=2102017` 是 WeGame/TCLS 注册上下文中的 Cross 服务标识。两者都不等于大厅地址。
3. `server_id=0` 在 CODOL 的 `FetchServerDirForTgp()` 调用中是“没有指定单个游戏服条目”的选择参数。它不能解释成 `0.0.0.0`、第 0 个 IP 或默认大厅地址。
4. `TCLSHostApp::SendServerDirToTgp(), result: 1` 只证明 ServerDir 处理/桥接成功，不证明已经得到可连接的大厅端点。当前日志没有把目录树或 URL 打出来。
5. 目录树中的动态地址字段确实存在：`Dir.dll` 输出 `ip:%s virURL:%s`，选服路径输出 `url:%s`；TCLS launcher 还准备 `ServerID/ServerName/ServerAppLen/ServerAppData` 作为启动元数据。真正的大厅地址如果来自 ServerDir，应该来自这些运行时节点/应用数据，而不是 `ServiceID` 或 `dirserver.xml` 的目录节点地址。
6. 在当前失败复现中，没有看到有效目录条目之后的大厅 socket 连接。静态失败路径包含 `select server failed`、`ERROR_INVALID_SERVER_ID`、空目录和 `Get Game Server Info fail`，与“无有效条目时先判定失败”一致；没有证据表明客户端会自动连接一个硬编码默认 IP。
7. 因此，本轮对用户问题的直接回答是：**TCLS 层不是默认地址回退，而是目录/选服失败；本次游戏随后没有发起大厅连接，最终 UI 才显示 `[100]`。** `[100]` 的精确生成点属于游戏/Demonware 侧，不能仅凭 TCLS 日志证明是 TCLS 返回的数值。

## 1. ID 的职责边界

### 1.1 `gameID=29`

既有 TCLSHost 日志反复记录：

```text
AddGame, gameID: 29, version: 844506536214550(3.19.26.22),
BranchID: 1, CrossSvrID: 2102017.
```

`29` 在当前链路中是产品/游戏注册 ID。它用于选择 CODOL 的本地 TCLS 路径、版本和业务配置，不是目录服务器索引，也不是大厅 endpoint。

### 1.2 `ServiceID=715019302`

`WeGame\tcls\tcls_core.exe` 的字符串池包含：

```text
ServerDir::ReadServiceID() ServiceID = %d
Service\\id
ServerDir::FetchWithUin() tclsPath: %s, gameID: %llu
```

这条静态证据把 `ServiceID` 放在 `ServerDir` 对象和 `Service\\id` 配置键/路径附近。运行日志随后打印 `715019302`，说明该值在 ServerDir 初始化/查询时已经被解析出来。

对关键 PE 做了四种形式搜索：小端/大端 32 位、ASCII 十进制、UTF-16LE 十进制。`715019302` 在以下关键文件中均没有直接命中：

```text
COD OL\TCLS\Tenio\TCLS.dll
COD OL\TCLS\Tenio\Dir.dll
COD OL\TCLS\Tenio\June.dll
COD OL\TCLS\Client.exe
COD OL\TCLS\TCLSClient.dll
COD OL\TCLS\ClientBase.dll
WeGame\tcls\tcls_core.exe
WeGame\tcls\common.dll
WeGame\apps\Rail\rail4tcls.dll
```

这排除了“把 715019302 直接写死在这些关键 PE 中”的解释，但没有排除加密/压缩资源、运行时配置、TCLS IPC 或远端返回体。现有证据能确定的是它的**职责**，不能确定它的最终上游字节来源。

### 1.3 `CrossSvrID=2102017`

`CrossSvrID` 出现在 `TCLSHostApp::AddGame` 的日志格式中，而不是目录树地址字段中。`cls_core.exe` 还包含 `Cross\\id` 这一类 Cross 配置键名。关键 PE 中没有直接固化 `2102017` 的四种编码命中，因此它更像 WeGame/TGP 注册阶段传入的运行时业务 ID，而不是游戏服地址。

## 2. `server_id=0` 到底是什么

### 2.1 Host 调用层

`TCLSHostApp` 的日志格式为：

```text
TCLSHostApp::FetchServerDirForTgp(), gameID: %llu, server_id:%u
```

CODOL 多次运行都记录 `server_id:0`。CF 的对照日志则出现 `server_id:4098`，并且出现不同的：

```text
SendSingleServerDirToTgp()
```

这说明 `server_id` 是“是否/哪个具体游戏服条目被选中”的业务参数，而不是 `ServiceID`。CODOL 的 `0` 更符合“先取目录/未指定单个条目”，而不是“连接默认 IP”。

### 2.2 目录模块层

`COD OL\TCLS\Tenio\Dir.dll` 的字符串池提供了完整的目录树语义：

```text
ServerList
[TACC][CDir::UpdateRecentServerListUI] ZoneName:%s, SrvName:%s,
    SrvID:%u, SrvStatus:%d, PlayerCount:%d
[Dir][CDir::OutputNodeTree] %s ip:%s virURL:%s
[Dir][CDir::PlayerSelectedServer] ... nodeid:%u CanenterFlag=%d
[Dir][CDir::PlayerSelectedServer] Succeed! ... name:%s, url:%s
[Dir][CDir::OnMessageRecvDirData] ERROR! Empty tree!
[Dir][CDir::SetDirMapInfo]total Server Count is %d
DIRTREERSP
```

因此至少存在三种不同的 ID/索引概念：

| 字段 | 所属层 | 含义 |
|---|---|---|
| `SuccessfulServerID` in `dirserver.xml` | 目录连接配置 | 选择 `tcls.qq.com` 等目录节点的索引 |
| `server_id` in `FetchServerDirForTgp` | TGP/TCLS 请求 | 指定单服或不指定单服的业务选择参数 |
| `SrvID`/`ServerID`/`nodeid` in `Dir.dll` | 运行时目录树 | 目录树节点或实际游戏服条目 ID |

把这三种 ID 混为一个值，会得到错误的“默认地址”结论。

## 3. ServerDir 返回内容的客户端侧落点

### 3.1 目录树和选中节点

`Dir.dll` 不是只读目录 host 的薄封装。它将目录响应解析为树，并保留至少以下动态字段：

```text
ip
virURL
url
ZoneName
SrvName
SrvID
SrvStatus
PlayerCount
```

`ip`/`virURL` 是节点输出字段，`url` 在选中服务器时被输出。当前本地文件扫描没有发现 CODOL 的真实大厅 URL 明文，这与“地址随目录响应进入内存”的模型一致。

### 3.2 启动桥接参数

`COD OL\TCLS\Tenio\TCLS.dll` 的 launcher 字符串为：

```text
--tcls --tcls-uId=%u --tcls-cltkey=%s --tcls-gameSignature=%s
--tcls-ServerID=%d --tcls-ServerName=%s
--tcls-ServerAppLen=%d --tcls-ServerAppData=%s
```

已有反汇编记录 `analysis_logs\TCLS_launch_config.txt:1793`，并在相邻指令中看到该格式被传给启动命令构造函数。这个结构说明：

- `ServerID` 是选中节点/服务条目的 ID；
- `ServerName` 是展示/标识字段；
- `ServerAppLen` 和 `ServerAppData` 是可变长度的应用数据载荷；
- 地址、票据、区域或大厅入口如果要随启动链传递，最可能位于 `ServerAppData` 或其后续解析对象中；
- 该命令格式本身没有把 IP 或端口作为独立硬编码参数。

这也解释了为什么只改 `dirserver.xml` 的目录 host，不能自动产生一个可用 CODOL 大厅：目录连接节点和“目录返回的游戏服务应用数据”是两层东西。

### 3.3 `lobbyLandingURL` 的边界

`TCLS.dll` 里存在键名 `lobbyLandingURL`，但它位于通用 launcher 的配置/共享数据处理路径。相邻资源包含旧的 LOL landing URL 模板，而不是 CODOL 大厅 endpoint。它只能证明启动共享数据支持 landing URL 字段，不能证明 CODOL 当前大厅地址就是该字段，更不能证明存在一个默认 CODOL IP。

## 4. 无有效大厅条目时的行为

### 4.1 静态失败证据

相关字符串和调用语义包括：

```text
TCLSHostApp::OnFetchServerDirEnd(), select server failed, server id: %d, error code: %d
TCLSHostApp::CheckUpdateBeforeLaunching(), error: ERROR_INVALID_SERVER_ID
[Launch][CLaunchUI::GetLoginInfo]Get Game Server Info fail!
[Dir][CDir::OnMessageRecvDirData] ERROR! Empty tree!
[Dir][CDir::GetAllGameDirInfo] Error when call GetDirInfo
[Dir][CDir::PlayerSelectedServer] ERROR! Invalid nodeid ...
```

这些分支都围绕“没有可选节点/节点 ID 无效/游戏服务信息缺失”处理，没有看到“使用默认 host/port 再 connect”的字符串或配置字段。

### 4.2 运行时交叉证据

最佳采集目录：

```text
run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326
```

对游戏 PID 的 AFD 归因显示：

- `116.130.224.66:8000` 是一次 UDP `ur` 地址发现请求/响应；
- 随后只有 SSDP 和 QoS 心跳；
- 没有新的大厅 TCP/UDP `connect`；
- 没有看到一个“默认大厅地址”被尝试。

所以当前可观察到的实际行为是：**没有有效大厅地址时，客户端在 TCLS/启动数据验证或后续大厅初始化前就结束本次尝试，没有连接到默认 IP。** UI 之后显示的 `[100]` 不能反推成“它连接了某个默认地址”。

已有 `CODOLServer\LOBBY_STACK_ANALYSIS.md` 对游戏本体的静态分析把 `[100]` 与 `bdLobbyErrorCode`/Demonware 错误格式化路径联系起来；这属于游戏层证据。TCLS 本身的日志只记录 `result=true`、`SendServerDirToTgp result=1` 或选择失败，不能证明 `[100]` 是 TCLS 返回码。

## 5. 对“是否可以本地伪造”的回答

从结构上看，**可以伪造目录响应中的运行时节点/应用数据，但不是靠伪造 `ServiceID` 或把 `server_id` 改成某个数字就够了**。至少需要同时满足：

1. 目录响应能被 `Dir.dll` 解析成非空目录树；
2. 选中节点的 `SrvID/nodeid`、状态和可进入标志合法；
3. 选中结果能生成 `url`/`ip`/`virURL` 或有效 `ServerAppData`；
4. 后续游戏层需要的登录票据、签名、title/zone 参数和大厅协议也成立。

当前报告没有改写客户端、hosts、路由、防火墙或真实远端流量，也没有实现伪造服务。下一步若继续做，应先对已捕获/合法测试数据做离线目录树解析和回放，先验证字段结构，再考虑最小化的本地测试端点。

## 6. 仍未解析的点

以下结论不能由现有静态材料单独确认：

1. `715019302` 的最终字节上游是 `Service\\id` 的哪一个物理文件、TCLS IPC，还是远端目录响应；关键 PE 中没有明文/32 位常量命中。
2. `CrossSvrID=2102017` 的确切生产者；现有日志表明它在 `AddGame` 注册上下文出现，静态字符串只显示了 `Cross\\id` 这类键名。
3. CODOL 的真实 `ServerAppData` schema，以及其中是否包含 Blaze host、端口或只包含票据/区域信息。
4. 游戏层 `[100]` 对应的确切 Demonware/Blaze 枚举名；这不属于 TCLS `ServerDir` 返回值本身。

## 7. 证据索引

| 证据 | 关键内容 |
|---|---|
| `WeGame\log\tcls\log\TCLSHost_2026-9-24-1790221027.log` | `gameID=29`、`CrossSvrID=2102017`、`server_id=0`、`ServiceID=715019302`、`result=true`、`SendServerDirToTgp result=1` |
| `COD OL\TCLS\config\dirserver.xml` | 目录连接节点、端口和 `SuccessfulServerID=1`；不是游戏服条目 |
| `COD OL\TCLS\Tenio\Dir.dll` | `DIRTREERSP`、目录树、`ip`、`virURL`、`url`、`SrvID`、状态和玩家数 |
| `WeGame\tcls\cls_core.exe` | `ServerDir` 类、`Service\\id`、`Cross\\id`、读取/选择/失败日志 |
| `COD OL\TCLS\Tenio\TCLS.dll` | 启动元数据格式、`ServerID/ServerName/ServerAppLen/ServerAppData`、`lobbyLandingURL` |
| `analysis_logs\TCLS_launch_config.txt:1793` | 启动命令格式的反汇编记录 |
| `CODOLServer\LOBBY_CANDIDATE_ANALYSIS.md` | 当前采集没有大厅 socket，只有 IIPS 地址发现/QoS/SSDP |
| `CODOLServer\LOBBY_STACK_ANALYSIS.md` | 游戏层大厅错误格式化和 `[100]` 的已有静态线索 |

## 8. 复现脚本

只读扫描器：

```text
CODOLServer\_tcls_serverdir_static.py
```

运行示例：

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
python .\CODOLServer\_tcls_serverdir_static.py wegame-core codol-dir codol-tcls
```

脚本只读取 PE 文件并打印结果，不写报告、不启动进程、不修改网络状态。
