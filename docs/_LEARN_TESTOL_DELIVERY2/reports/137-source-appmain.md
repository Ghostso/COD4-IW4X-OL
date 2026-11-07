# 137 · `source/src/game_server/Appmain.cpp` 专属学习报告

## 一、学习范围与完成度

- 只读学习 `F:\桌面\ol\TESTOL 完整交付版`。
- 本报告对象：`source/src/game_server/Appmain.cpp`。
- 本次从第 1 行连续读到第 **10,784** 行，已到 `DllMain` 后的文件结尾；不是抽样阅读。
- 先前进度摘要中的“10,564 行”与当前文件实际行数不一致，以本次工具读取到的 **10,784 行**为准。
- 本文件是 `game_server` 插件的总装配层：它把原生引擎绑定、网络传输、`ServerCore`、Dedicated 控制面、客户端桥接、配装/角色资源、地图世界、机器人、玩法脚本和诊断导出接到同一帧循环中。大量规则在 `server_mp`，本文件负责提供依赖和决定调用顺序。
- 报告区分“源码明确实现”“源码注释声称的实测”“尚未闭合”；注释里的实机记录不当作本次重新运行验证。

## 二、全局对象、线程与所有权

### 2.1 核心对象

| 对象 | 责任 |
|---|---|
| `Bindings` | 原生 CODOL 引擎资源、ABI、碰撞、动画、模型、武器、角色等访问 |
| `Server` | `ServerCore`，由 gamestate/snapshot 构建回调和三种资源索引解析回调构造 |
| `Network` | `SvUdpTransport`，负责 `NET_Frame` 和 `NET_SendPackets` |
| `DedicatedControlServer` | Dedicated 本地控制协议 |
| `ClientSessionBridge` | 客户端侧配装/预约采集及诊断命令 |
| `RegisteredSessionAssets` | xuid 对应的角色、五套配装、技能、装备、奖励 |
| `PendingBooking` / `PendingWorldAsset` | 分阶段预约与世界准备状态 |
| `DedicatedMapGeneration` | 地图+游戏类型的 zone/world/CCS 代际缓存 |

`buildGameState` 和 `buildSnapshot` 都先开 **64 KiB** 缓冲，再使用 `EngineMsgWriter`。快照失败按 `(clientNum, failure)` 变化打印，避免每帧刷屏；成功路径可选择把实际线上字节转成 `SNAPHEX`，而不是仅检查写入器内部状态。

### 2.2 锁与队列

- `DedicatedControlMutex` 保护控制线程投递的预约、SessionStart、配装更新、播音和原始命令队列。
- `LoadoutMutex` 保护 prepared/registered 配装和角色资源。
- `BookingMutex` 保护 `PendingBooking`。
- `WorldAssetMutex` 保护 `PendingWorldAsset`。
- `StartupMutex` 与 `Installed` 防重复初始化。
- 控制线程原则上只解析和入队；游戏线程在 `processDedicatedControlMessages` 中交换队列并真正修改世界/可靠命令环。
- `DllMain(DLL_PROCESS_ATTACH)` 只禁用线程通知并调用 `initialize()`；注释明确避免在 loader lock 中 join 控制线程，但这不表示所有启动工作都无 loader-lock 风险，仍应把实际启动路径作为整体审查。

## 三、初始化顺序与 `.tp3` 解壳门槛

### 3.1 延迟启动

`startupImageUnpacked()` 不成立时，`scheduleDeferredInitialize()` 启一个一次性 worker：

1. 每 10 ms 检查一次；
2. 必须连续 **100 次**成立，即约 1 s 稳定；
3. 最多 6000 次，约 60 s；
4. 稳定后只调用一次 `initialize()`，不做无限重试。

源码注释记录：插件入口约在 t=0 执行，而零售客户端仍有 `.tp3` 密文；部分 RVA 在约 2068–4065 ms 后才呈现正确明文。等待不能发生在游戏主线程，否则会阻止解壳本身。

### 3.2 `initialize()` 的真实顺序

1. `Installed` 已置位则返回；未解壳则转延迟启动。
2. 读取进程角色。
3. 客户端和 Dedicated 均可尽早安装 unsigned-fastfile 可选补丁。
4. 非 Dedicated 尽早发布 TCLS mapping，避免把登录时序绑定到渲染器或帧 hook。
5. Client：安装 vectored fault witness、noclip/battery 热键、每秒只读 characterInfo 报告线程，并处理多实例 mutex。
6. Dedicated：安装进程补丁，失败则停止后续初始化。
7. `Bindings.bind()`。
8. Client 可选 alpha weapon gamestate 补丁。
9. 非 game-server 角色只安装客户端帧 hook 和输入补丁。
10. game-server 角色向 `Server` 注册所有 provider/runner，最后安装帧 hook。

关键理解：**角色外观和配装不是单纯 Lua 数据**；它们依赖原生 zone、weapon registry、model/configstring band 与角色定义，故必须在 `Bindings.bind()` 和地图代际准备完成后使用。

## 四、帧循环总图

`onServerFrame(now)` 的阶段号为：

| phase | 区域 |
|---:|---|
| 0 | `not_started` |
| 1 | entry |
| 2 | role/client patches |
| 3 | dedicated control |
| 4 | loadout refresh |
| 5 | pending booking/worldspawn |
| 6 | `Server.onComFrame` |
| 7 | 探针、脚本日志、网络发送 |
| 8 | 状态与周期报告 |

主要顺序：

1. 复制帧线程 handle，启动 watchdog。
2. `Bindings.observeGameThread()`；审计 XModel/alpha weapon。
3. 客户端：电源状态、raw input 窗口、g_gametype dvar cache、ClientSessionBridge。
4. Dedicated/服务端：启动控制服务、消费控制队列。
5. 必要时准备客户端五套配装；`Network.NET_Frame`。
6. 处理 pending booking、pending world spawn、bot 创建。
7. `Server.onComFrame` 产出 outbound packets。
8. 运行可选 DObj/capsule 探针、排空 Lua 日志、`NET_SendPackets`。
9. 输出 client census、clientThink 拒绝、包拒绝、性能和 ack 变化。

### 4.1 性能观测

- 帧、发送和每客户端快照构建都用 `SvTimingAccumulator`，报告 last/avg/max 和 buckets。
- 超过 50 ms 的 server frame 额外比较墙钟与同一线程 CPU 时间；CPU 来自 `GetThreadTimes`，用于区分真正计算和调度/IO 等待，不是完整 profiler。
- `FRAMESTALL` 每秒最多一条。

### 4.2 watchdog 的实际边界

独立线程每 100 ms 检查 `FrameTick`，300 ms 无变化且 **phase 必须等于 6** 才报告。它会短暂 suspend 帧线程，抓 EIP 和最多 4 KiB 栈，立即 resume 后再做模块解析和格式化，避免在目标持锁时分配内存。

**源码内值得保留的矛盾**：上方注释描述为“报告任意帧阶段”，当前条件却只覆盖 `Server.onComFrame`。因此 phase 1–5/7–8 的卡死不会因为这套条件而触发同一条 stall 报告；不能把 watchdog 描述成全阶段覆盖。

## 五、客户端桥接与诊断面

`ensureClientSessionBridge()` 每秒最多尝试启动一次。诊断分两类：

- **后台 detached 审计**：`item-names`、`equipped-equipment`、`equipped-perks`、`weapon-table`、`reward-table`、`alpha-barrett-templates`、`unlock-coverage`；结果去 CSV/log，不经过 bridge 返回大对象。
- **同步安装/查询**：command trace 与 playerstate trace 的 start/stop/status，以及 FPS 探针。

FPS 命令包括 `fps`、`fps-uncap`、`fps-restore`、`fps-set-<n>`；任意值允许 0..10000，避免只能测试作者预设的 0 和 200。

客户端 bridge 每轮采集：roster item handles、characterInfo、profile slots、`captureClientLoadoutRequest()`、`readClientBookingSelection()`。当前重要语义：

- 没有 loadout 时返回空 capture；
- 没有 booking selection **不再一并否决 loadout**；菜单阶段本就可以有配装而无预约；
- booking 有有效 rotation index 才填入，否则保留默认 booking；
- refusal 字符串区分 `NO_LOADOUT`、`NO_BOOKING_SELECTION`、`ROTATION_INDEX_NEGATIVE`，且仅在变化时打印。

另有 `OLMOD_CLIENT_UI_DVAR_REPAIR`（默认开）和延迟毫秒配置：客户端若不加载 `ui_mp`，g_gametype dvar cache 可能为空；等待默认 30 s 后调用原生 `sub_4E8990`，同时保留“引擎自己是否后来填充”的可观测性。

## 六、Dedicated 控制协议与会话消费

### 6.1 控制消息

| 消息 | 当前行为 |
|---|---|
| `ConfigureSession` | 配置 session descriptor、启动网络、enable，返回 endpoint |
| `QueryEndpoint` | 要求空 payload |
| `QueryGameplayStatus` | 要求空 payload，编码完整 gameplay 状态 |
| `DebugGrantBattery` | 空 payload 或 `<18` 槽位，按发送方 IPv4 授权 |
| `SetNoclip` | userId + peer IPv4 定位客户端，可限时 |
| `SessionStart` | 解码、入队，地图资源准备后消费 |
| `UpdateLoadout` | u64 userId + LoadoutRequest，入队到游戏线程 |
| `PlayAnnouncer` | 验证 announcer 参数范围后入队 |
| `SendRawCommand` | 只有 `OLMOD_ALLOW_RAW_COMMAND=1` 才接受 |
| `Booking` | 检查长度，入队后由导出函数配置 |
| 其他 | `UnsupportedMessage` |

noclip 同一 IP 多客户端时可能取最低活动槽，并在日志标明 shared address；正常按键重复不持续刷日志，只记录边沿和失败。

### 6.2 SessionStart 流水线

1. 由 members 建 roster 并累计请求 classMask。
2. `stageSessionRoster(requestId, roster)`。
3. 地图或游戏类型变化才 `beginLevelZoneLoad`；同一代际复用，避免重复 zone load。
4. 等 `zoneLoaded`，然后只做一次 `initializeLevelWorld`、`CCS_Clear`。
5. 确保 CCS 初始化、mantle 动画、weapon registry、server animation context。
6. 逐 member 解析角色、奖励、最多五套 custom class 的武器/perks/equipment。
7. `configureBooking(..., CurrentGeneration)`。
8. 发布 `PreparedLoadouts`，记录 session generation 与 resolved classMask。
9. 置 `ActiveDedicatedSession`；任何失败通过统一 `failSession` 回滚 roster 并记录精确阶段。
10. 资源未准备好的 session 以原顺序退回队列前端，下帧重试。

**版本语义已改**：`SessionStart` 当前复制 session 为 `pinnedSession`，但不再把 gametype 改成 dm。旧 §187o 注释仍大段存在；当前注释记录 d28 证明“钉 dm + sd 形状 match rules”会被严格校验拒绝，所以直接服务 booked gametype。团队分配/伤害是另外的问题，不能再用隐藏改 gametype 的方式掩盖。

### 6.3 gameplay 控制读回

控制状态不仅包含队伍和炸弹，还包含：

- reliable sequence/ack、网络收发计数和错误；
- usercmd pending/oldest/newest/received/dispatched/executed/discarded；
- clientThink attempted/committed/failure；
- buttons/angles/weapon/offhand/move；
- origin/viewAngles/health；
- 最近一次 bullet trace 的起点、终点、fraction、hitType/entity、model/part/result；
- 每客户端 objective 与最近 reliable commands。

空 optional 在 C ABI 中通常编码为 `UINT32_MAX`，调用方必须按协议还原，不能把该哨兵当真实时间/槽位。

## 七、角色外观：三个容易混淆的命名空间

### 7.1 角色呈现记录

`ClientCharacterPresentation` 包含：

- `characterIndex`；
- `viewmodelIndex`；
- 11 个 `selectionIds`；
- `characterItemId`；
- 12 项 `recordItemIds`（entry0 角色，1..11 装饰/部件）。

OLfinal 缺少旧 `CharacterSelectionResolve` 体系时，代码允许继续：viewmodel 先给合法占位 1，selectionIds[0]=1，角色 item 和12项记录从客户端上传复制。日志 `BOTTRACE|human-presentation` 同时打输入项数、非零输入、输出非零项和具体槽，区分“客户端没上传”“服务端没复制”“客户端没呈现”。

`OLMOD_CHARACTER_ITEM` 或 `Ayria\Logs\olmod-character.txt` 可覆盖角色；覆盖时清空其他 11 项，让客户端使用该角色默认套装，而不是混穿不同角色。

### 7.2 bot xuid 必须区间判断

bot 的身份带是：

```text
base  = 0x0B07000000000000
range = [base, base + 4096)
```

旧逻辑只写 `userId >= base`，而真实 Demonware 64 位账号数值也可能大于 base，导致真人被当 bot、装饰被清零。当前条件同时检查上下界。这是本文件最重要的身份安全边界之一：不同 ID 命名空间不能只比大小。

### 7.3 viewhands、body model、modelIndex 是不同东西

- `viewmodelIndex`：第一人称手部，是 **model configstring 索引**，10 bit；优先角色自己的 `han_`，其次 `viewhands_tf141`，不能把占位 1 发出去。源码记录占位 1 在该地图解析成 `defaultvehicle`，客户端因缺 `tag_weapon` 报 1073。
- `bodyModelConfigStringIndex`：clientState `+0x14` 的 fallback body，也是 model band 索引，角色 resolver 不可用时给客户端一个可绘制的 `fpa_` 身体。
- `customization.modelIndex` / clientState `+0x150`：**不是 model band 索引**；是 4 bit 的角色选择字段，合法范围 1..15，实测语料常见 0/6/7/8。把数百的 band index 写进去会让 customization 无效，clientInfo 被移除，活人不可见而尸体短暂可见。

这三个索引曾因名字相似被混用，当前代码分别处理。

### 7.4 装饰 bitmask 与 stowed attachment 不是同一通道

- netfields 21..32 是角色定义的 **384-bit option selection mask**；按 item 是否属于该角色 option 来置位，不是直接写 item id。
- `outfitAttachmentModelIndexes` 所属 model/tag 通道后来被认定为背负/收枪附件通道，不是服装 option 通道。当前 `OLMOD_OUTFIT_ATTACHMENTS` 默认关，只有显式 `=1` 才启用。
- 62 个零售 demo 的注释证据说明大量 attachment tag 对应空 configstring 仍可显示，所以“tag 0 必然使 DObj 失败”是已撤回的推理，不是实测事实。
- 角色身体与手部在 world 配置阶段就发布进 gamestate，避免客户端已拿 gamestate 后才 live broadcast 而漏收。
- hands/body/outfit 都按角色或12项 outfit 做缓存，**miss 也缓存**，避免每帧每玩家扫描 1024 个 configstring；空名称列表不会过早锁存。

`CharacterOptionMasks` 独立放在 customization 外，是因为向地址敏感的 world/client 节点增字段曾导致死亡动画回归；这不是单纯风格选择。

## 八、配装、动态武器与实时刷新

### 8.1 gamestate 注册

- 先取 `firstDynamicWeaponAssetIndex`，读取原生 dynamic tail，并要求 outgoing index 与原生 registry 完全一致。
- 不允许另造“看起来紧凑”的尾部，否则客户端显示一把枪而服务端执行另一份 WeaponDef。
- 每个 modular dependency 先注册，再注册主武器；注册后回写新 asset index。
- 若原 `clipIndex == originalWeaponAssetIndex`，同步改成注册后的 index。
- `chicken_melee_mp` 特例保留在 base registry，不走 modular 动态表；空手枪槽也用它补合法近战 fallback。
- Wetwork/coop 路径带一份录制武器定义表； retail zombie seed 有 34 项，但由 `SvSeedRetailWeaponSet` 编译期开关控制且 skip-on-clash。
- `RecordedWetworkWeapons` 的录制 index 只用于映射日志，真正索引由当前进程重新注册决定。

### 8.2 `UpdateLoadout`

实时刷新只更新指定 xuid 的武器、perks、equipment、offhands/rewards，并保留角色。它不会重建地图。

当前实现把新武器追加到 live gamestate dynamic block，但**不广播 `%`**；玩家需退回并重新加入以重读完整 gamestate。原因记录为 `%` 更新会触发客户端 181 weapon-index/slot 检查。附件不能像旧实验那样剥掉，否则与 SessionStart 的去重/依赖次序不同，重连后武器槽可能偏移并触发 181。

## 九、gamestate 内容装配

`configureGameStateImpl` 的失败由 `GameStateConfigurationStage` 精确记录。关键内容：

- booked gametype 经 `SV_EngineGameType` 转成引擎词汇，后续统一用 engine name。
- 必须有非零 configStringChecksum、当前角色、匹配的 PreparedLoadouts、有效 dynamic weapon range。
- `SV_PopulateRequiredConfigStrings`。
- `timescale` configstring 为 `0 0 1 1`。
- damage/kill/scavenger/UAV/announcer 等素材按名称解析，避免把某局录制里的动态 alias index 当全局常量。
- SD 必须解析 A/B target、defend、defuse、bomb、escort 八种 material，否则拒绝。
- sessionGeneration 下 player names 按 xuid 排序后写入，再补 required configstrings。
- 全部成员配装成功后才原子替换 `RegisteredSessionAssets` 并提交 `Server.configureGameState`。
- 成功后创建 `PendingWorldAsset`；失败在 sessionGeneration 下回滚 roster。

### 9.1 DMZ loot band

`dmz` 且 `OLMOD_DMZ_LOOT_BAND != 0` 时直接写入 gamestate：

- cs12504 = `mp/dmzloot.csv`；
- 64 个录制 loot 槽，cs12506..12692 非连续；
- 值为绝对 weapon asset index 1148..1211。

它不能用普通 `SV_SetConfigString` 替代，因为后者在 gamestate 前不存储、之后又只对已加载客户端发 live `d`。这里重放的是一份真实布局，不是恢复出的零售随机器；不同零售局的槽位会重排。该 band 仍带开关，因为 configstring validator 的类型接受范围曾是加入失败嫌疑点。

### 9.2 声音结论必须按当前资源边界理解

- hit/kill alias 通过名称双大小写查找；UAV 低带失败时使用已测高带 1277/1605。
- lead/lost/winning 可用 CCS 名称、高带 fallback 和环境变量覆盖。
- medal/splash alias 列表当前为空。源码记录 75 个已载 alias 实测都不是奖牌声；资源存在于 fastfile 不等于存在于可网络引用的 constant-string table。因此当前选择“不响”而不是发错误声音。

## 十、世界准备与地图资源

`configurePendingWorldSpawn` 只有 gamestate 已配置、存在 active client 且 world 尚未配置时运行；失败按 1 s 节流重试并只在 stage 改变时记录。

主要顺序：

1. map entity string 与 glass metadata/threshold。
2. brush/script model spawn 解析。
3. ZM 可选大量资源准备。
4. 预留 model band 空槽：**2 × 18 + 16 = 52**，覆盖 18 人的 body+hands 和16个 script model。
5. SD 炸弹 trigger/presentation。
6. 解析 brush collision、script model index、destructible owner。
7. 结束比赛 camera/podium、角色 band 发布。
8. 选取 connection/mode spawn，逐点 capsule ground trace。
9. logical entities、Lua gameplay source。
10. `Server.configureWorldSpawn` 已在第8步前提交基础世界，之后补 DMZ 空手、脚本、SD presentation 等。

### 10.1 出生点规则

- spawn 来源是地图实体字符串，不能由“有没有小地图”决定；ZM 无 compass 也仍有 spawn。
- 每点向下最多 8192 units，要求有效、非 solid、walkable、命中 world。
- 单个坏点只丢弃，不再让整张地图失败；全部被拒才报 `initial_spawn_ground_trace`。
- 原点按 trace fraction 移到实际地面。
- 缺 `info_player_start` 时用第一个合法 mode spawn 停车，不因此拒绝地图。

### 10.2 const baseline 与静态实体

地图 `<map>_const.ff` 的 `mp/constbaselines/bl_pc_<map>_<gametype>.bin` 提供零售实体号基线。若表存在，静态实体按零售编号发布并启用 snapshot flag 0x10；无表才回退顺序编号。注释明确否定“按所有 mapent 的出现顺序推算编号”的旧假设。

### 10.3 尚未闭合的 actor model 发布

文件明确记录：ZM actor model 的首次 spawn live 发布和 map-load 按 actor_* 发布两种尝试都失败，后者还选错模型且出现超时。当前只预解析 `c_zom_ger_body_blue` / `c_zom_ger_head` 的 lookup，不在这里发布 actor model。故“ZM 世界资源全接通”不能由本文件其它大量资源代码推出。

## 十一、ZM/Factory 可选装配

这部分大多是 opt-in 重建，不等于恢复原 CODOL 服务端决策器。

- zones：从 map entities 解析区域、trigger hull 和 spawn point；解析失败只记录，不阻断原有世界生成。
- nav：支持 CODOL recovered 与 `OLMOD_ZM_NAV_SOURCE=bo1_hybrid`；后者只在 Factory 生效，普通 walk 仍需实时地面/身体 clearance 验证，楼梯可用有界 step 验证。
- barriers：board group 与 traversal/node pair 关联，在 nav graph 后提交。
- tear clips：3 lane × 6 slot，读取 `board`/`end` notify 时间，重复 marker 或缺任一者不采用。
- presentation：身体颜色、头、死亡动画、肢解/眼部/口部 FX、BO1-derived tesla 序列等都有独立开关和已解析资源门槛。
- arrival/teleporter/box：模型、bone、anim tree、sound、effect 按地图加载时一次解析，不在 actor tick 中扫描 DB。
- box 普通池只使用已发布 dynamic tail，并排除重复 base、非 bullet、无弹匣/弹药、alt child。
- reconstructed special pool 是固定命名目录，权重明确“重归一化，不是原 CODOL 概率”。
- MP/Factory offhand 有 grenade/flash/smoke 类型与原生 launch/blast 参数校验，不支持的变体明确拒绝。

 Factory 的 `OLMOD_FACTORY_*` 开关很多，阅读运行日志时必须同时记录开关，否则不能把可选预览能力当作默认行为。

## 十二、机器人创建策略

### 12.1 默认不自动填人

源码注释记录操作要求是使用官方原生 bot，不默认制造合成 6v6；原生 AI 不在这个 retail client engine 中。因此：

- `OLMOD_BOT_FILL` 默认不启用；
- `OLMOD_BOTS` 和导出 `CODOL_GameServerRequestBots` 仍可显式请求；
- 启用 fill 且未显式指定数量时，普通团队模式默认 12，`cha` 为18；每边为 target/2；
- teamless 模式保持 `SvTeam::None`，团队模式等真人已经选边后再补，避免全是 None 而不能 spawn。

### 12.2 名称、职业与外形

- 名称来自内嵌 738 个官方21代名称池，可由 `OLMOD_BOT_NAMES` 逗号列表替换。
- 职业从 `OfficialBotClasses` 解析，bare name 和 `name_mp` 都试；当前九套全解析失败则不创建，不回退克隆真人职业。
- 默认 bot 角色列表12项：545、569、570、592、612、635、649、671、789、792、2056、2105；可用 `OLMOD_BOT_CHARACTER` 或 `OLMOD_BOT_CHARACTERS` 覆盖。
- 每个 bot 单独写 `RegisteredSessionAssets`，不再复制真人整份角色/装备。
- `BotXuidBase + index` 是合成身份，和真人账号严格分带。

### 12.3 节奏与成本

每次间隔 **400 ms** 最多创建一个，且时间戳在工作完成后写入。源码记录一次性 full baseline 曾导致约890 ms CPU / 977 ms wall，因此不能一帧创建11个。

职业解析耗时单独记录 lookup/read/total；`createBotClient` 本身实测远小于整个创建阶段。`BotsCreated` 按 session generation 重置，避免第二张图以后再无 bot。

**仍需注意的依赖**：正式创建前仍要求 `BotSeedSource` 能从已发布成员中找到非零 characterItemId 和合法 loadout，作为允许创建的 gate；虽然后续职业和角色已改成 bot 专属，但这意味着“完全没有任何可用真人资源种子时能否独立创建 bot”仍受此 gate 限制。这里应描述为现状，而不是宣称 bot 已完全独立于 roster。

## 十三、射击、近战、发射器与投掷物

### 13.1 子弹

`executeServerBulletFire` 负责组合依赖：

1. `SV_BuildBulletFirePlan`；
2. 原生 endpos；
3. `traceServerPoint`；
4. penetration continuation（当前 stub 返回 false）；
5. direction byte；
6. damageable player/entity、glass、damage payload；
7. impact event 转 `pendingEntitySpawns`。

self-damage probe 默认关；开启后重写 basis 并允许 shooter 成为候选，只用于验证真实伤害链。penetration diagnostics 限量打印。每 `(failure reason, weapon)` 最多记录一次，避免把13种拒绝都压成 `client_events_rejected`。

`BulletTraceDiagnostics=false` 编译期关闭昂贵的逐弹 capsule 报告；相关日志包括 miss、实际 stance maxsZ 70/50/30 与 hit height，但默认运行不能依赖它。

### 13.2 近战

- meleeDamage 按 asset 缓存，从原生 WeaponDef 读取。
- 不穿透，第一命中即结果。
- 每次 swing 打一行结果。
- Applied 且 staged point 存在时补 `melee=true` 的 impact event，避免受害者有伤害却无近战命中表现。

### 13.3 weaponType==2 的第四条开火路径

源码注释记录 rpg/javelin/stinger/at4/crossbow/sparrow 的 weaponType 都为2，不能进入只接受 bullet 的 plan。当前顺序：

1. `weaponType == 2`：读取 launcher projectile 七项参数，计算 velocity/angles，创建 `SvMissileSpawnRequest`。
2. Factory special：`SV_LaunchFactorySpecial`。
3. 其余：`executeServerBulletFire`。

launcher 的 `position` 初值包含 `{5, serverTime, 0, muzzleTrace, {}}`，delta 取 velocity 的 trunc，fuseDeadline 是保守30 s 清理上限，不是恢复出的撞击引信完整逻辑。无参数明确 Failed，不静默落进必然失败的 bullet 分支。

### 13.4 offhand

普通 MP 与 Factory 共用 `offhandWeaponKind`、grenade launch、trajectory evaluator。若不支持则 `DeferredImpact`；缺 basis/launch parameters/launch 则 Failed。成功后清原生 grenade timer 与 `ps.grenadeTimeLeft`。FireTrap..Monkey 范围不旋转，其它飞行物旋转。

## 十四、alt weapon 与触发渠道的结论史

- alt→host 反查表只建一次，来源是所有注册武器的定义链接；只有表内 alt 才能通过 `SV_SetAltWeaponLookup` 射击，不变成“任意武器皆可开火”。
- host→alt 是另一方向，供 spawn 把 alt 加进 `heldWeapons`；没有它，原生 finish-weapon-change 找不到 cmd.weapon 并写0。
- `setWeaponDefinitionResolver` 则是有意不受 alt allowlist 限制的通用定义读取，供 grant 获得完整 ammo/clip。
- 旧把 `0x100000` 当 alt-fire 实为开镜；`0x08000000` 也被后续测量否定。
- 当前注释认定键3通过 reliable command `n 89`，不是 usercmd button；默认安装 alt-fire resolver（`OLMOD_ALT_FIRE=0` 才关闭）。但同段仍写“switch 已触发、呈现却回到 host，撤销阶段待仪器定位”，所以不能报告为 alt-fire 已完全可用。

## 十五、其他 provider 的职责边界

初始化注册的 runner 包括：

- loadout/reward/perk/equipment provider；
- UAV/AC130 test grant、30 s radar；
- character model/script animation/effect resolver；
- shared pmove、weapon movement、playerState→entityState、death/spawn animation；
- trajectory、point/capsule/radius/trigger trace；
- native entity mirror synchronizer；
- client events handler。

`AC130_TEST_GRANT` 只验证授予与通用使用链，副作用仍是 UAV 雷达，不表示 AC130 炮艇视角/炮塔/HUD 已实现。

`setCharacterCustomizationProvider` 还会从 body model 名中的 `_sc_f`/`_tf_m` 推 battlechatter 性别；源码称此方法对456个身体模型中452个成立，仍不是完整定义级真值。

## 十六、ABI 导出与采样结构

### 16.1 插件入口

- `onStartup(bool)`、`onInitialized(bool)`；
- `Createserver(const char*)` 返回 null，但保留导出使 loader 留住模块；
- `DllMain`。

### 16.2 状态导出

导出覆盖 enable/network/netchan/connectionless/ingress/gamestate/loading/usercmd/reject/reliable/menu/gameplay/session consumption/loadout/gamestate configuration/character/snapshot/world/SD/objective/think/events/bullet/player/trace transport 等。

所有导出通常先 `ensureInstalled()` 并逐一检查输出指针，失败返回 false；字符串由 `SV_CopyStatusText` 带容量和实际长度复制，二进制 prefix 按源、内部数组、调用方容量三者最小值复制。

### 16.3 `CodolWorldPlayerSample` 版本兼容

- V1 固定 **192 bytes**，`static_assert` 保证4字节对齐。
- V2 固定 **352 bytes**，以 V1 为 base，`pmType` offset 192。
- V2 调 `makeWorldPlayerSampleV1(sample, sizeof(*output), 2)`，因此 base.structSize=352、schemaVersion=2，旧字段布局保持原位。
- V2 增加视角、ladder、sprint、mantle、双手武器状态、legs/torso、prone、bobCycle。
- 调用方必须传足够 outputSize；不能把 V1/V2 指针混用。

## 十七、预约匹配规则的当前判断

`configureBooking` 统一拒绝日志带具体 reason：

- command 可解析；
- command 有 playlist id 时才与 capture 比，避免用默认0否决；
- map/gameType 不一致时以 command 为准并记录；
- rotationIndex 不一致只记录，不拒绝。源码实测 capture index 与 command 可不同，而 map 始终跟踪 command；非零 rotation 才暴露旧错误。
- Dedicated 必须有 matchRules，并按 **engine gametype** 校验，不是 booked token。
- 最后持 BookingMutex 设置 `PendingBooking`，再递增 loadout request sequence。

导出 `CODOL_GameServerConfigureBooking` 从客户端原生 booking 补 selection，但 Dedicated 控制面的 SessionStart 不经过这个导出，所以所有真正需要统一的语义必须放在内部 `configureBooking` 或 SessionStart 消费漏斗，而不能只放在导出外壳。

## 十八、关键学习结论

1. **Appmain 是依赖装配和事务边界，不是单纯 main。** 角色、武器、地图和网络能否工作，往往由它调用 provider 的时机决定。
2. **gamestate、live configstring、原生 registry 是三种不同发布面。** 写入其中一种不会自动保证另外两种一致；武器181、角色不可见、DMZ loot 无声写入都源于此。
3. **索引必须带命名空间。** model band index、4-bit model selector、weapon asset index、configstring index、角色 item id、平台/Demonware/bot xuid 不可互换。
4. **真人/bot 判断必须用完整区间。** 64位账号数值大小不是类型标签。
5. **所有昂贵资源解析要移出每帧路径。** 1024槽扫描、角色 option 解析、bot 职业解析都证明“功能正确但每帧调用”会直接破坏可玩性；缓存 miss 同样重要。
6. **注释是历史记录，不全是当前规则。** dm pin、outfit attachment、watchdog、alt-fire 等处必须读最终条件和开关，不能只摘上方段落。
7. **大量 Factory/ZM 内容是可切换的重建/预览。** 当前源码没有把原服务端全部决策恢复，也没有闭合 actor model 发布、完整 launcher 引信、AC130表现和 alt switch 呈现。
8. **事务设计是主线。** usercmd 内伤害先 staged，整条命令成功才提交；session/world/loadout 失败有 stage 与 roster rollback；资源未就绪跨帧 deferred，而非以空数据继续。

## 十九、本文件读后仍待后续源码核对

- `ServerCore` 各 provider 的实际调用频次、事务提交点和快照字段实现，需到 `sv_main_mp.cpp` / `sv_snapshot_mp.cpp` 等文件核实。
- `OLMOD_*` 的完整清单和默认值分散在多个文件，本报告只覆盖 Appmain 出现的开关。
- ZM actor model 发布、角色 torsoAnim、alt-fire 最终呈现、完整穿透 continuation、launcher 引爆语义不能据本文件宣称完成。
- `RecordedWetworkWeapons`、retail zombie seed 与 DMZ loot 都是录制样本重放/注册数据，不是通用资产生成算法。
- watchdog 当前只报告 phase6，若后续报告引用其能力必须保留这个限制。

**本文件学习完成。下一步：`game_server/server_mp` 154 文件，逐个顺序学习并持续写专属报告。**
