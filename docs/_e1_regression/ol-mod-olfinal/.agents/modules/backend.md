# Backend 模块

## 责任

`src/backend` 是 DW3 控制面，负责 Auth3、LSG、service/task 分发、publisher storage、玩家持久化、房间消息、matchmaking 和 booking 转交。它不负责地图模拟、`SV_Frame`、GSC、实体或 snapshot。按原版 COD 职责，backend 与 dedicated game server 都属于服务端基础设施，但不是同一模块；本地部署以后可以由一个 server launcher 同时启动二者，不应因此合并数据所有权。

当前仍是迁移拓扑：`OLMOD_PROCESS_ROLE=client` 时 backend 继续依附客户端进程内的 Localnetworking socket bridge，`combined` 保留旧单进程兼容。它尚未成为独立网络 daemon；在客户端只保留 endpoint redirect、backend 能独立接受连接之前，不能宣称控制面已移出客户端。

逻辑目标名为 `ol_backend`，兼容输出仍为 `AlwaysofflineRe.Localnet32`。

## 玩家身份配置

运行时玩家名现在由 backend `PlayerIdentityStore` 按 `titleId/userId` 持有，live 文件为 `Ayria/Assets/Alwaysoffline/1004/<USERID>/Identity.json`，字段为 `schemaVersion=1/displayName`。首次认证时若玩家档案不存在，才从根目录 `Ayria/Assets/Alwaysoffline/Identity.json` 读取 `username` 作为迁移种子并原子创建档案；种子缺失时使用源码中唯一的 `DefaultUsername`。档案建立后修改迁移种子不会影响既有账号。显示名必须为 1 至 16 字节 printable ASCII；已存在档案格式非法时认证 fail closed，不静默回退另一身份。`setDisplayName` 提供后续改名事务的唯一持久化 primitive；改名卡的资格、扣除、唯一性与敏感词校验仍待 backend 上层事务实现。

Auth3 task 28 仍从客户端请求恢复 `userId` 和 `sessionKey`，随后按该 `userId` 查询玩家档案；请求中的旧 username 不再覆盖 server-owned display name。Auth3 ticket、LSG、TitleUtilities、好友、聊天、房间消息和 dedicated `SessionStart` 继续统一读取同一个 `AuthSession`。Matchmaking 的 `Session.Demonware` 虽然当前样本可解码为字符串，但属于客户端状态机提交的 opaque session descriptor；归档 `Matchmaking_createSession/updateSession/findSessions` 会原样保存和回显。2026-08-09 实机已证实用 backend display name 重写该字段会导致改名后加入房间持续等待，因此 backend 只把它作为 matchmaking/booking 的客户端材料，不作为玩家名权威来源。归档 `Platformwrapper.Ayria32` 的 `Username.txt` 也不是当前大厅显示名权威来源。

同日又确认 room internal ID 属于独立的客户端 platform identity 链。源码化 `ol_platformwrapper` 通过 Tencent tag `22` 提供 full platform ID `0x01100001DEADC0DE`；clean 自然运行后，room member identity 和内嵌 `MatchMakingInfo` 均持有 internal ID `0xDEADC0DE`，并闭合 QuickMatch 到 world。该 ID 不能替代 backend display name，也不能由 backend 重写 opaque matchmaking descriptor；正式所有权是 backend 按 authenticated user ID 持有玩家资料，Platformwrapper 只提供 CODOL 客户端兼容 platform/OpenID。

`dest1yo` clean 改名运行 `.runtime/natural-match/20260809_dest1yo_storage_persist_v5/` 又验证了该边界：Auth3 ticket/response、LSG、房间成员与大厅显示均使用 backend 档案中的 `dest1yo`，platform ID 仍保持 `0x01100001DEADC0DE`。Storage2 `service 0x0A/task 10` 现按捕获 wire 读取 `context/name/visibility/blob/owner/platform/flags` 和最后一个 raw zero terminator，只允许当前已认证用户写普通文件名，并以进程与序列唯一的临时文件原子替换；本轮 `the.json` 自身条目已从旧名持久化为 `dest1yo`，response `error=0`。首次 forced allocation 的 booking capture 暂时失败时客户端仍可能弹一次“服务器繁忙”，dispatcher 随后以 request `2` 重试并完成 `SessionStart -> mp_crash_tropical/sd -> world -> snapshots`；最终为 `286` 个 snapshot message、`383 accepted / 0 rejected` client packets。该重试属于既有 capture 时序边界，不再与改名或 user-file 持久化混淆。

`the.json` 是 CODOL 客户端原生命名。客户端 `sub_4AA270` 在 lobby 可用后下载 blob，在内存中解析 `blacklist/Recentmetlist`，修改后重新序列化并约三秒后上传；backend 的磁盘文件只是当前 emulator 的服务端持久化映射，不是原版客户端直接读取的文件。BO2 PDB/i64 的同类 SDK 接口正式名为 `bdStorage::uploadFile/getFile`，Ghosts server i64 也保留 `bdStorage::getFile`；源码因此以这组名称登记 CODOL `0x0A/10` 与 `0x0A/12`。CODOL task 编号及 `context/platform/flags` 等 wire 字段相对 BO2 有扩展，不能反向声称已找到 CODOL 自身的完整 SDK 符号。`the` 的展开含义仍无可靠证据。

## Ready 到 Booking

```text
room request
  -> service 0x0B handler
  -> event 8 push
  -> local ready committed
  -> service 0x15 task 5, query kind 1 FIND_SERVERS
  -> explicit Session.Role=server result
  -> service 0x06 task 14 mmbook
  -> event 21 mmbook accepted
  -> service 0x06 task 14 mmstart
  -> BookingSink
  -> DedicatedBookingDispatcher worker
  -> client bridge captures native booking selection and item-ID loadout on Com_Frame
  -> backend entitlement validation
  -> versioned SessionStart
  -> dedicated game thread resolves its own assets and configures booking
```

query kind `1` 是 `FIND_SERVERS`，kind `3` 是 `FIND_LOBBIES_BY_PLAYLIST`。不能把玩家自己创建的 lobby 当作 server 返回。

`BookingSink` 接受 `mmstart` 只表示 game server 已接管并排队该 booking；CCS reset/reinitialize 和 `gamestate_configured` 在后续 `Com_Frame` 中完成，不能把 sink 返回值解释为即时 gamestate 成功。

`DedicatedBookingDispatcher` 收到 `mmstart` 后先通过 client bridge 捕获该 booking generation 的 native selection/loadout。该捕获由客户端 `Com_Frame` 消费，加载切换期可能在 1.5 秒窗口内暂时返回 `Rejected`；dispatcher 对这个只读操作使用同一 request ID 最多重试三次，再做 entitlement 与 `SessionStart`。不可在第一次 transient capture 失败后静默丢弃已经接受的 booking，否则客户端会在加载边界显示服务器离线；协议错误仍立即失败，重试也不得重复提交 dedicated side effect。

当前跨进程 descriptor v2 只携带 backend 已认证的 user ID/display name、booking command、客户端原生选择的 playlist/rotation/map/gametype、角色 item IDs、五套 class 的武器/附件 item IDs 和获准 class mask；不传客户端指针、临时 weapon index、模型地址或 registry slot。dispatcher 使用单 worker 避免在 `mmstart` 游戏线程同步等待 client bridge；每个 booking 分配递增 request ID，capture 与 `SessionStart` 共用该 ID。client bridge 的控制线程只排队并有界等待，由 `Com_Frame` 原子采集一次 native booking selection 与 staged loadout；dedicated 收到后校验 selection 与 `mmstart` command 一致，并使用自己进程的 item/asset 表重新解析。codec、超时、重启、并发 capture、entitlement 接受/拒绝和 `SessionStart` 解码已有自动回归。自然双进程运行 `.runtime/natural-match/20260808_dedicated_session_selection_v16/` 已闭环 `mmstart -> capture -> entitlement -> SessionStart -> dedicated CCS/loadout -> booking accepted`，五套 class 为 `requested/resolved=31/31`。客户端尚未连接 dedicated，后续 `session_configured/transport_bound` 与 gameplay packet 均为零；因此 booking handoff 已完成，但 gameplay session 分配仍未完成。

backend entitlement 当前按 CODOL `CODOL_ItemAvailability_Query 0x695BC0` 已恢复的两类来源裁决：有效且数量非零的持久 inventory，以及 `CODOL_DefaultAvailableItems_Init 0x7052F0` 恢复出的 build 固定默认集合。过期、零数量和未知 item 固定拒绝；item-definition `flags & 2` 只影响已授予 inventory item 的非过期语义，不作为授予来源。secure unlock/rank 条件和 onboarding-only fallback 尚未成为 backend provider 的完整输入，因此不能把当前实现描述为全部 CODOL entitlement 规则已恢复，也不能用“全部允许”绕过该边界。

## 多客户端共享 room/session 边界

当前 backend 不能让两个真实客户端加入同一个控制面房间。每个 client 进程都各自构造一套
`ServerFactory -> AuthSession -> LobbyServer`；`LobbyServer` 又独占 `MatchmakingService`、
`LobbyProtocol` 和 `DedicatedBookingDispatcher`。`LanDiscovery` 只广播 session properties 和
channel/instant-message event，能发现另一个进程的广告，却不持有 room member、ready、host、
booking generation 或成员到 bridge endpoint 的权威映射。当前 `AuthSession` 也只保存一个身份，
因此不能把两个进程各自的 local state 拼成 roster。

跨进程 `SessionStart` schema v4 曾是单成员描述：一个 `userId/username/loadout` 加一份比赛选择和
规则。schema v5 已能编码通用成员数组，但 dispatcher 仍固定访问 `configuredClientBridgePort()`，只能
从触发 `mmstart` 的本进程捕获一份 loadout。dedicated 已完成多成员资产消费和 generation-scoped XUID
连接授权；这仍不能冒充共享 room owner、bridge 路由和按每位成员冻结 entitlement 已恢复。

正式最小链路按以下顺序实现，不使用固定两个账号或复制首账号 loadout 的运行时特判：

1. 建立独立于 client 进程的共享 backend owner。它按 authenticated user ID 保存 connection、
   display name、room membership、ready 和可版本化的 client bridge endpoint；客户端内 backend
   退化为原协议接入/重定向边界。第一阶段只需支持单个本地 room，但 room ID 和 member map 必须
   是一般结构，断线和重复登录要有确定清理语义。
2. booking owner 从共享 room 冻结 generation-scoped roster。它分别向每个成员登记的 bridge port
   请求 `ClientSessionCapture`，校验所有 capture 的 booking selection 一致，并按成员自己的 backend
   inventory 执行 entitlement；任何成员超时、身份漂移、selection 冲突或非法物品都使整次 booking
   fail closed，不能提交半个 roster。
3. 新增版本化 match-start descriptor，公共 booking/rules 只编码一次，成员数组至少携带 authenticated
   `userId`、server-owned display name 和该成员的 item-ID loadout。dedicated 接收后冻结允许连接的
   XUID 集合，并在 `SV_DirectConnect` 后按 XUID 将成员绑定到 slot；未列入 roster、重复 XUID 或缺失
   loadout 均拒绝。账号复制工具只用于制造第二份持久测试资料，不成为 session 权威来源。

自动回归边界必须分别覆盖：两个 Auth 会话加入同一 room、ready/离开/断线；两个 bridge 乱序返回仍按
user ID 聚合；一名成员 capture 超时不产生 dedicated side effect；不同 selection/非法 entitlement
原子拒绝；descriptor round-trip 保持成员身份和各自 loadout；dedicated 以相反连接顺序仍按 XUID
绑定正确 slot。完成这些离线边界后，才进入两个真实 client 的自然 `room -> mmstart -> connect ->
snapshot` 验证。

共享 owner 的协议无关状态核心现已建立为 `SharedRoomSessionOwner`：按 authenticated XUID 保存 display
name、独立 client bridge port、connection token 和 ready；同一 XUID 重连会产生新 token，旧连接的
disconnect/ready 事件不能删除或修改新登录。room 有一般化容量限制，成员按 XUID 稳定排序，只有当前
全部成员 ready 才能按非零 booking generation 冻结 roster；同一 generation 的重复 freeze 永远返回
首次快照，不随之后重连或离开漂移。该 owner 已线程安全，并通过独立 `ol_room_owner.exe` 在 loopback
端口（默认 `28970`，`OLMOD_ROOM_OWNER_PORT` 可覆盖）提供有界 connect/disconnect/ready/freeze IPC；codec
严格拒绝未知 schema、截断和尾随数据，真实 TCP 往返已有回归。标准 `launch-dedicated` 现会先启动
owner、等待端口就绪并把 PID/端口纳入原子 process state 与失败回滚；部署清单也安装该 target。它尚未
接入 dispatcher 的多 bridge capture。归档 oracle 与既有真实运行证据已把 `0x0B/13` 确认为 room-entry
object、`0x0B/2` 确认为 room-exit user ID，并把已捕获 `0x0B/4` event-8 的 16-byte payload 确认为本地
ready 提交。client 角色现在通过 token-safe `SharedRoomClient` 把这三个已确认边界分别映射为
connect/leave/ready IPC，身份来自 `AuthSession`，bridge 来自该进程环境；owner 失败会让对应 DW task
fail closed，`combined` 兼容模式不依赖 owner。task 4 仍是通用 channel broadcast，只有精确匹配已捕获
ready fixture 时才修改 owner；unready payload 尚未捕获，保留 `TODO(CODOL)`。`0x0B/1/9/10/11` 仍保持
未知语义，不能凭字段形状命名。当前 client 内 `ServerFactory` 仍各自持有协议适配状态，但 room 的成员、
ready 和 endpoint 已汇聚到唯一 owner。booking dispatcher 现在用 booking request ID 冻结同 generation
roster，逐成员 bridge capture 原生 selection/loadout，要求 selection 完全一致，并按成员 XUID 从各自
`Inventory.json` 校验 entitlement；全部成员成功后才原子发送一个 `SessionStart v5`。任一 capture、
descriptor、selection、entitlement 或 match-rules 失败都不会产生 dedicated side effect。owner 和
dispatcher 均拒绝重复 XUID/bridge endpoint，测试覆盖双成员不同 loadout、按 XUID entitlement、
selection mismatch 与第二成员 entitlement 失败。当前剩余边界是 launcher 的多 client 进程清单、每实例
唯一 identity/bridge，以及两个真实 CODOL client 的自然 room/ready/capture/connect 验证。

## 资产和持久化

正式分类如下：`assets/backend/1004/Server` 与 `Cloud` 是不可变 publisher/backend 输入；`MarketplaceSkus.json` 是项目恢复的 backend catalog；user ID 目录下的 profile、inventory、wallet 与 identity 是 backend 可变状态；根目录 `Identity.json` 只是首次迁移种子；`Ayria/Assets/Platformwrapper` 只服务源码化客户端兼容插件，不属于 backend 状态。`CODOLBackend/`、profile `.bak` 和 `Publicprofile-test` 不属于 live asset contract，前者确认无消费者后移出运行目录，后两者作为不可再生测试快照归档而不由 installer 管理。publisher 文件没有 legacy playlist `26`；跨进程 descriptor 仍传递并校验客户端原生 selection。若该 playlist ID 存在，backend 严格校验指定 rotation/map/gametype；若原生 legacy ID 在 publisher 中缺失，则扫描包含相同 map/gametype 的候选，忽略只提供 rotation 而没有完整模式规则的容器，并且只在至少一个完整候选存在且所有完整候选完全一致时接受；零完整候选或规则冲突一律拒绝，不通过硬编码 ID 映射或任意选择候选来补洞。自然 `.runtime/natural-match/20260812_sd_objectives_v7/` 已用 `26/0/mp_crash_tropical/sd` 闭合 `SessionStart`、world、gamestate 和持续 snapshot。

- title `1004` 是 CODOL。
- playlist 最低人数修改是响应时的有界变换，不改原文件。
- `Publicprofile`、inventory、purchase 与 publisher data 必须优先服从客户端实际序列化和归档行为。
- `Inventory.json` 中仍属重建扩展的部分必须明确标注，不能反推它是游戏原生文件。

2026-08-07 的持久库存复核确认磁盘 `Inventory.json` 与 Marketplace task `203` 均可返回全部 `115` 项。归档中的永久物品以 `expireDateTime=UINT32_MAX` 表示；其 JSON `expiryDuration` 经过十进制序列化后可能舍入到略大于 `INT64_MAX`，handler 只对这一永久 sentinel 归一化为 `INT64_MAX`，限时物品的越界 duration 仍严格拒绝。

同日 clean launch 定位了 profile 被清空的真实时序：task `203` response 已携带 115 个对象，但旧 hook 在原生 `CODOL_Marketplace_OnInventoryComplete` 已消费任务后再次读取 `bdRemoteTask +0x24`，得到清理后的 `0`，并重复调用 `CODOL_Marketplace_FinalizeInventory(1, 0)`。客户端下载原始 1982-byte profile 后因此按空库存 repair，并通过 Profiles2 `8/3` 上传 1943-byte 替代文件；上传 payload 与磁盘文件逐字节、SHA-256 完全一致。当前实现不再 hook `bdMarketplace_StartGetInventory` 或重复 finalizer，而是在原生 `CODOL_Marketplace_FinalizeInventory` 返回后只记录 completion 并放行 profile 下载。clean PID `16296` 中 task `203` 原生完成为 `115 objects`，随后才请求 Profiles2 `8/1`；有界捕获内没有 `8/3`，恢复的 1982-byte profile 仍保持 `DC9AAE6...D4464B`。

角色选择与跨重启恢复也已在同日闭环。`0x68C580` 的唯一 caller `0x5F01A0` 属于 onboarding，除选择角色外还写 `onboardCharacterID` 和 telemetry；普通 Scaleform 入口 `CL_SetDefaultCharacter/CL_SetCurrentCharacterID 0x69C850` 转入 `CODOL_CurrentCharacter_SelectItem 0x689FF0`，以 `EDI=itemId` 查找或创建 character slot、更新 `currentCharacterIndex`、flush Publicprofile 并刷新角色表现，不写 onboarding 状态。`CodolMatchFlow.py --character-index` 已改走该普通 selector。

此前 clean restart 从 CRC 有效的 character `3` 恢复成 `0`，不是 entitlement 或磁盘 profile repair。启动约 `4.8s` 时 UI 在 profile 尚空时调用 `CODOL_CurrentCharacter_GetIndex 0x68A0E0`，把 `0xCD7E3C` 的 lazy cache 从 `-1` 锁为 `0`；约 `13.2s` 后 profile 与 inventory 已完整，后续 character init 仍复用旧 cache。backend 现在只在 `public + download + succeeded + errorCode 0` 的原生 profile completion 返回后把该 cache 恢复为 `-1`。clean PID `31148` 未传角色参数自然读回 `current_character_index=3`，随后 booking loadout 为 `current/prepared/registered=3`、mask `31/31`。证据见 `.runtime/natural-match/20260807_current_character_cache_fix_v1/`。

loadout 不需要在大厅定期重读：每次新 booking 的 generation-scoped staged loadout 读取会使用当时客户端状态。首次库存 UI cache 是否无需购买即可稳定显示仍是独立边界。clean world run `.runtime/natural-match/20260807_current_character_cache_clean_world_v3/` 再次自然读回角色 `3`，但 fresh process 的 game-server resolver 以 `base_weapon_lookup`、mask `0/0` 在 gamestate 前 fail closed；这是具体武器资产解析问题，不回退为角色/profile 持久化失败。

稳定 handler 必须有 byte fixture、语义测试或归档 oracle 对比；只收到 success reply 不代表 side effect 已恢复。

backend 日志统一通过 `src/shared/RuntimeLog` 写入 `Ayria/Logs/AlwaysofflineRe.Localnet32.log`；`OLMOD_CONSOLE_LOG=1` 时同步到当前 client/combined 进程的控制台。Storage2 下载与上传只记录文件名、owner、字节数和结果，不输出文件内容或逐 packet 数据。
