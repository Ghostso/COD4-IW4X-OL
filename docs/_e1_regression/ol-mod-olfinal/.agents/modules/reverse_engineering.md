# 逆向工程

## CODOL 主数据库

```text
E:\codol_research\Call of Duty Online [3.3.3.3 QA Build] (2015-06-15)\CODOL_Experience_V3.3.3.3_FULL\codoMP_client_shipRetail.exe.i64
```

该库可写，直接原地维护，不创建日常分析副本。稳定 annotation 同步到 `tools/reverse/annotations`。

归档 Alwaysoffline 的主分析库仍位于：

```text
E:\codol_research\Ayria2\diagnostics\ida\Alwaysoffline.Localnet32.i64
```

它是归档 DLL 唯一可写主库；`Ayria2\Bin\diagnostics` 仅是旧证据快照。批处理工具直接打开主库，确认后的名称和注释写入 `tools/reverse/annotations`，由 `tools/reverse/IdaApplyAnnotations.py` 应用。

## IDALib 语义标注链路

当前自动分析统一使用 headless `idalib-mcp`，由 `tools/reverse/IdalibMcpClient.py` 调用；需要 GUI 插件的 `ida-pro MCP` 不是本项目的默认入口。启动服务时用进程参数数组传递目标 i64，避免含空格路径被 PowerShell 拆开。

## Gameplay 源码证据审计

`tools/reverse/catalogs/codol_server_function_matrix.json` 清点需要恢复的原生函数；
`tools/reverse/catalogs/codol_gameplay_source_audit.json` 反向清点现有 gameplay 源码是否已经逐块核对。
后者的 scope 必须覆盖 `server_mp`、`EngineBindings` 和所有 `Native*Bindings`，未登记 review 的
文件自动视为未审计，不能因为它能编译、通过单元测试或曾经实机可用而提升置信度。
单个局部逻辑块使用 `coverage=symbol`。一个函数已从入口到出口检查时使用
`coverage=function`，并登记稳定的起止源码锚点和 `blocks`；每个控制流块必须分类为
`native_reference/codol_difference/project_boundary/todo`，附对应 marker、证据和退出条件。
不要使用易随格式化漂移的行号表达审计范围。只有文件中每个函数、手写布局、ABI、状态
owner、fallback 和 TODO 都已逐块分类后才允许 `coverage=full_file`。完整覆盖只说明检查范围
闭合，不改变 `reviewed_partial/project_boundary/complete` 所表达的实现程度。

源码中的长期证据统一使用四种可搜索标识：

- `CODREF(matrix_id)`：写明 BO1 Windows x86、Ghosts PS4 x64 的函数和地址；两者分歧时再写 BO2。CODOL 本体函数、字段、wire 或 consumer 证据必须同时注明。
- `CODDIFF(matrix_id)`：只放在真正产生差异的分支旁，说明为何不能照搬参考游戏，以及差异由哪条 CODOL 证据裁决。
- `OLMOD(boundary)`：项目自己的事务、跨进程、诊断或兼容边界，不冒充 COD 原生设计。
- `TODO(CODOL)`：写清缺失语义和退出条件。只写“以后完善”不算有效 TODO。

每个核心恢复函数至少有一个函数级 `CODREF` 头；连续同构代码按逻辑块标一次，字段投影、
特殊分支和项目边界在对应代码旁标注。无需机械地解释每一条赋值，但任何手写结构布局、
原生 ABI、状态 owner、fallback 或参考游戏差异都必须能从代码旁直接追到证据。审计状态仅表示
该函数当前声明范围已读过，不等于整个 function-matrix 项已经实现完成。

运行：

```text
python tools/reverse/ValidateCodolGameplaySourceAudit.py
```

默认输出剩余未审计文件并验证 review、matrix id 和源码 marker 一致；只有准备声明整个 scope
完成时才使用 `--require-complete`。不得为了让检查变绿而批量加入空洞 marker。

PowerShell 调用 MCP tool 时优先让参数 JSON 走 stdin，避免 native argv 再次剥掉 JSON 双引号：`@{database='session-id'; addr='0x401000'} | ConvertTo-Json -Compress | python tools/reverse/IdalibMcpClient.py decompile -`。最后的 `-` 是固定入口；不要反复试拼内嵌 JSON 字符串。

同一 idalib worker 切换多个 i64 时，strings cache 可能仍指向上一数据库。2026-08-03 在 CODOL/BO1 切换中观察到 BO1 `cscr_*.cpp` 字符串被错误返回为 CODOL 结果，而 CODOL 对应地址的真实 bytes 为零或无关数据。跨库查询必须在 `idb_open` 后核对 `server_health.idb_path/module`，并用当前库 `get_bytes/find_bytes` 验证关键字符串；最好让参考库使用独立 worker。没有 bytes 或当前代码 xref 的字符串缓存命中只能视为工具污染候选。

高置信度的结构和命名应及时写入主 i64，改善后续 Hex-Rays 输出，不必等到完整结构全部恢复。partial struct 只声明已确认字段，中间空洞保留显式 padding；参考游戏名称可以辅助命名，但不能单独确定 CODOL offset 或字段类型。一次语义修改按以下顺序闭环：

1. 用 `declare_type` 声明或更新类型，并用 `type_inspect` 核对总大小、member offset 和 member type。
2. 用 `type_apply_batch/set_type` 应用函数原型、参数、global/local/stack 类型；用 `rename` 写入已确认名称。
3. 将同一分析步骤中的类型、原型、名称和 operand type 修改组成一批；完成 layout 与应用结果检查后，调用空 `items` 的 `force_recompile`，统一使全库 Hex-Rays cache 失效。不要在同一批中的每个字段或名称修改后重复调用。
4. 全库 cache invalidation 不会立即输出或重新分析所有 pseudocode，只保证以后每个函数第一次 `decompile` 都基于最新 IDB 语义生成结果。因此无需计算可能遗漏的 caller/type-consumer 闭包，也无需预先反编译整个调用图。
5. 对当前工作集调用 `decompile` 获取刷新后的 pseudocode；其余函数保持懒加载。没有发生 IDB 语义修改时可以直接复用当前反编译，不需要每次读取都刷新。
6. 若刷新结果与 xref、offset、调用约定或控制流冲突，降低类型置信度并直接检查 `disasm`，不能为了让 pseudocode 好看而保留错误类型。

### 试验性语义

为改善难读 pseudocode，可以添加尚待验证的名称和类型，但不得与稳定 annotation 混淆：

- 已确认名称使用正常 COD/项目命名，不加置信度前缀。
- 工作假设统一使用 `hyp_` 前缀，例如 `hyp_PM_CheckMantle`、`hyp_mantleState_t`、`hyp_playerState`，并在对应函数或地址添加以 `[HYP]` 开头的简短注释，写明依据与待验证点。
- 只确认位置而不知道语义的 struct member 使用 `unk_XXXX`，其中 `XXXX` 是十六进制 byte offset；结构空洞保留 `pad_XXXX`，不能靠相邻字段猜出语义。
- 试验性类型优先应用到一个函数的 local/parameter，不直接改变函数边界、calling convention、共享 global 或稳定公共原型。变更前记录原名称、原型或类型，刷新后同时比较 pseudocode 与关键 disassembly；无改善或出现矛盾就回退。
- CODOL-local 证据确认后移除 `hyp_` 并允许同步到稳定 annotation；被证伪的假设立即删除。`hyp_` 名称不得进入 authoritative C++ 实现或 module 的已确认结论。

确认后的名称和注释继续同步到 annotation JSON；类型与原型在 annotation schema 尚未覆盖前以主 i64 为准。试验性语义只保存在分析库和 `.runtime` 变更记录中，不进入稳定 annotation JSON。

## 已确认入口

| 作用 | VA | RVA |
|---|---:|---:|
| QuickMatch | `0x006F2C10` | `0x002F2C10` |
| room ready getter | `0x006E5320` | `0x002E5320` |
| client allocation entry | `0x006E4A20` | `0x002E4A20` |
| room singleton slot | `0x078B0708` | `0x074B0708` |
| XAsset lookup | `0x0049E7D0` | `0x0009E7D0` |
| bulk XAsset header enumeration | `0x0049ED90` | `0x0009ED90` |
| XAsset zone loader | `0x0049F960` | `0x0009F960` |
| common MP zone descriptor append | `0x0049FD00` | `0x0009FD00` |
| zone loaded query | `0x004A0820` | `0x000A0820` |
| RawFile copy/inflate | `0x004A1620` | `0x000A1620` |
| parse client FX source | `0x00435740` | `0x00035740` |
| load client FX RawFile | `0x00435920` | `0x00035920` |
| parse client FX mapping | `0x00435B00` | `0x00035B00` |
| load client FX mapping RawFile | `0x00435E20` | `0x00035E20` |
| start client-side map FX | `0x00435F60` | `0x00035F60` |
| CCS initialize | `0x005850B0` | `0x001850B0` |
| first-person view offset | `0x0051D3B0` | `0x0011D3B0` |
| linked view-angle transform | `0x0051D2A0` | `0x0011D2A0` |
| PM effective stance | `0x00415CD0` | `0x00015CD0` |
| PM friction | `0x00416390` | `0x00016390` |
| PM view-height lerp duration | `0x004187A0` | `0x000187A0` |
| PM view-height waypoint lerp | `0x00418820` | `0x00018820` |
| PM view-height lerp fraction | `0x004188D0` | `0x000188D0` |
| PM view-height adjust | `0x004189B0` | `0x000189B0` |
| PM stance and duck update | `0x00419270` | `0x00019270` |
| PM clip velocity | `0x00415B40` | `0x00015B40` |
| PM project velocity | `0x00415BC0` | `0x00015BC0` |
| PM restrictive-plane ordering | `0x00420C90` | `0x00020C90` |
| PM slide move | `0x00420D40` | `0x00020D40` |
| PM step slide move | `0x00421680` | `0x00021680` |
| Pmove | `0x0041E860` | `0x0001E860` |
| PmoveSingle | `0x0041DBA0` | `0x0001DBA0` |
| PM player trace wrapper | `0x00415A10` | `0x00015A10` |
| PM ground trace | `0x00418500` | `0x00018500` |
| client handler capsule trace | `0x00459C20` | `0x00059C20` |
| jump check | `0x0040EAC0` | `0x0000EAC0` |
| DTP update | `0x0040E1F0` | `0x0000E1F0` |
| mantle check | `0x0040FDB0` | `0x0000FDB0` |
| mantle start | `0x0040F530` | `0x0000F530` |
| mantle move | `0x0040FE10` | `0x0000FE10` |
| binding action dispatcher | `0x00460870` | `0x00060870` |
| native key down | `0x0045E890` | `0x0005E890` |
| native key up | `0x0045E8D0` | `0x0005E8D0` |
| binding action lookup | `0x00462480` | `0x00062480` |
| client key event | `0x004629C0` | `0x000629C0` |

`0x006E4A20` 会进入 `MatchMaking_FIND_SERVERS_Query` 相关路径，不是 authoritative server startup。`0x006E6F60` 处理 `mmbook accepted`，`0x006E6BF0` 构造 outbound `mmstart`。

CODOL `DB_GetAllXAssetOfType 0x0049ED90` 以 `EDI` 接收可空的 `XAssetHeader *` 输出数组、栈上传入 `XAssetType` 并由 `EAX` 返回数量；它自行取得 DB hash read lock，没有 callback 或 maxCount。`DB_GetRawBuffer 0x004A1620` 以 `ECX` 接收 16-byte `RawFile *`，栈上传 destination/capacity，并按 `compressedLen` 选择复制或 inflate。两个稳定名称、`RawFile` partial struct 和 register ABI 已写入主 i64；全库 `force_recompile` 为 `32971/32971` 并已保存，名称和注释同步到 annotation JSON。完整 GSC 证据边界见 [`gsc.md`](gsc.md)。

Dedicated v40-v44 又确认 `DB_LoadXAssets 0x0049F960`、`DB_IsZoneLoaded 0x004A0820`、`DB_AppendCommonMPZones 0x0049FD00` 和 `Com_PollCommonXAssetInitialization 0x0059D730`。只加载四个 common MP zone 并强制执行 registry 后半段时，registry 停在 `1 weapon / 2 attachment models` 并在 `CODOL_Weapon_InitRegistry` 触发访问异常；保留完整 `Com_StartHunkUsers -> 0x0059DD20 -> 0x0059C180` 原生链后，v44 自然推进到 `357/151`。四个稳定名称和七处因果边界注释已写入主 i64，执行全库 `force_recompile 32971/32971` 后保存并同步 annotation；`0x0059C180` 的精确函数名仍未闭合，因此只记录注释，不添加猜测名称。

随后通过精确 xref、调用参数和 BO1 PDB 的 `UIViewer` 类型闭合了此前未知的 `0x0B584C53`。全部 11 个 direct xref 都是读取；真正的置位发生在 `UIViewer_Show 0x00566940` 对 `viewer+3` 的 word 写入，`UIViewer_Hide 0x00566B70` 对称清零。对应 early fields 为 `show/deferredShow`，而非通用 DB 状态。`UIViewer_Init 0x005660D0`、`UIViewer_Shutdown 0x005664A0`、`UIViewer_LoadMap 0x00566560` 和 `UIViewer_Update 0x00567860` 也由 CODOL 控制流与 BO1 同名函数闭合。`0x0059DD20` 的整体次序与 BO1 `Com_AssetLoadUI` 一致，现使用该稳定名称；其内部仍保留 CODOL 特有的本地 client memory、UI/common zone accounting 和 frontend 初始化。上述名称和因果注释已同步到主 i64 与 annotation。下一步应追 `sub_584D30` 读取的 weapon-group list producer；不能再把 `uiViewer.show` 当成可直接设置的 dedicated asset gate。

只读 v51 进一步校正了优先级：dedicated 的 `0x02DF7D50` 从空变为非空时 weapon registry
已为 `353` 且 `common_mp` 已 loaded，而 `uiViewer.show` 仍为 `0`；完整 session、loadout、
gamestate、world 与 snapshot 同轮通过。因此 `sub_584D30` 的 list 是 post-registry 状态，
不是当前拆分必须先复制的 registry owner。hardware watchpoint 会改变 CODOL 运行结果，不能
继续用于该地址的 writer 归因。细拆工作现有意暂缓，保留该静态问题供未来无头部署优化，
当前逆向优先级返回 server entity/event/bullet/damage gameplay 链。

地图 FX source 的消费者已由 CODOL 控制流和 KisakCOD `cg_client_side_effects_mp.cpp` 对照闭环：`CG_StartClientSideEffects 0x00435F60` 只构造 `maps/mp/%s_fx.gsc` 与 `maps/createfx/%s_fx.gsc`；`CG_LoadClientEffectMapping_FastFile 0x00435E20 -> CG_ParseClientEffectMapping 0x00435B00` 解析 `level._effect/loadfx` 映射，`CG_LoadClientEffects_FastFile 0x00435920 -> CG_ParseClientEffects 0x00435740` 解析 createfx entity 文本。后两者分别使用 `ECX=buffer` 和 `EDI=localClientNum, EDX=buffer` 的 CODOL register ABI，未强行应用 cdecl prototype。这是专用客户端表现解析器，不是 GSC VM。

`0x006F2C10 -> 0x006F0940` 会直接解引用 `0x07809CA4`、`0x01A2A52C`、`0x078B0708`、`0x078B070C`、`0x078B07F4`、`0x078B0800` 和 `0x078B0804` 所指对象，并经 room 与 room-service vtable 调用方法。clean launch 黑屏阶段即使顶层地址已经 mapped，强行调用仍曾触发低地址 `0x3AB8` access violation，说明对象范围与内部方法尚未就绪。client connection state 不是该函数的显式输入，且 2026-08-01 17:38 已在稳定主大厅 state `0` 下闭环 QuickMatch、ready 与 client-native allocation；因此 runtime guard 使用本轮 `ClientLoadTime`、完整对象范围、vtable 可执行性和连续稳定，不再把 state `1` 或 PVP UI 当作前置条件。

角色选择链已由 caller、RTTI 注册和 clean-start 时序闭环。普通 `CODOL_CurrentCharacter_SelectItem 0x00689FF0` 使用 `EDI=itemId`，由 `CODOL_GFx_SetCurrentCharacterID 0x0069C850` 暴露为 `CL_SetDefaultCharacter/CL_SetCurrentCharacterID`；`CODOL_GFx_SetCurrentCharacterLoadoutIndex 0x0069CB20` 是相邻但独立的 class 入口。`CODOL_Onboarding_SelectCharacterItem 0x0068C580` 使用 `EAX=itemId`，唯一 caller 会额外写 `onboardCharacterID`，不能作为普通 selector。`CODOL_CurrentCharacter_GetIndex 0x0068A0E0` 的 lazy cache 位于 `0x00CD7E3C`；Publicprofile 延迟到 inventory 完成时，启动 UI 可在空 profile 上先把它从 `-1` 固化为 `0`。当前 backend 只在成功 public-profile download completion 后重新置 `-1`，让后续原生 reader 从已解析 DDL 重载。四个函数名、ABI/职责注释已写入主 i64，全库 `force_recompile 32971/32971` 后保存并同步 annotation。

`0x0051D3B0` 与 BO1 `CG_OffsetFirstPersonView` 的整体职责同构，但 CODOL 末段额外调用 `0x0051D2A0`。后者从 predicted playerstate `+0x200` 读取 11-bit entity reference，非 `2047` 时取该实体 angles 并变换 refdef angles；CODOL descriptor 将它列为 field `227`。同一视角路径还以 `+0x1F0 == 2047` 作为普通 first-person view-height 分支门槛，该 offset 是 11-bit field `68`。动态 trace 与修复后的真实 parser 已确认这两个字段的 none sentinel；稳定名称暂用 `linkEntityNum/viewEntityNum`，不从 BO1 layout 外推其他相邻字段。

`PM_CheckDuck 0x00419270` 的站立目标路径在 `0x00419BDD` 写入 `PM_GetStandViewHeight 0x004124D0`；同族 `PM_GetCrouchViewHeight 0x00412500` 与 `PM_GetProneViewHeight 0x00412530` 分别返回 `int(playerSizeScale * 40/11)`，站立 helper 返回 `int(playerSizeScale * 60)`。完整 descriptor 将 playerstate `+0x98` 列为 field `217`、`bits=0`。动态 trace 在旧 snapshot 下观察到 `60 -> 0`，写入 field `217=1.0` 后同一路径稳定为 `60 -> 60`；因此当前语义名使用 `playerSizeScale`。`PM_ViewHeightAdjust/GetViewHeightLerpTime/ViewHeightTableLerp`、四张 `viewLerp_*` 表、`PM_ClipVelocity/ProjectVelocity/PermuteRestrictiveClipPlanes` 也已在 2026-08-04 的三方核对后写入主 i64 与 annotation JSON；新增保守 `pml_t` 和 `viewLerpWaypoint_s` partial struct，表项类型与标准 cdecl helper prototype 已应用，custom register ABI 只记录注释。批量修改后全库 `force_recompile` 为 `32971/32971` 并已保存；`sub_412470/sub_4124A0` 的碰撞高度语义尚未单独命名。`sub_5A27F0` 的 `bits==0` full-float reader 先消费两个 control bits，再读取 raw 32-bit XOR baseline，这一顺序已有固定 writer fixture 和真实 parser 验证。

本轮进一步确认 `playerState_s.otherFlags=+0x10`、`playerState_s.eFlags=+0xF0`，分别对应 descriptor fields `54/28`；field `28` 是 `-98` 语义的 30-bit flag，CODOL `sub_5A22E0 @ 0x005A22E0` 在 full branch 明确调用 `MSG_ReadBits(30)`，compact branch 读取 5-bit index 后与 baseline XOR。BO1 `MSG_WriteEFlags` 使用 24 bits，Ghosts `MSG_WriteDeltaField` 对应分支使用 29 bits，均不能覆盖 CODOL-local 结论。`PM_GroundTrace 0x00418500` 的 one-unit probe 读取 `eFlags & 0xC00`，不是 `pm_flags`。`PM_GetEffectiveStance 0x00415CD0` 以 `EDI=playerState_s *` 的 custom ABI 返回 prone `1`、crouch `2`、特殊 viewheight target `22` 的 stance `3`，否则为 standing `0`；`PM_WalkMove 0x004174C0` 用该返回值选择 acceleration，stance `3` 与 prone 共用 `19`。`PM_GetViewHeightLerp 0x004188D0` 提供 crouch/prone 过渡 fraction。`PM_Friction 0x00416390` 以 XY speed 计算 walking friction，但将 scale 写回 XYZ，与 BO1/Ghosts 控制流一致。上述字段、名称、custom ABI 注释已写入主 i64 和 annotation JSON；全库 `force_recompile 32971/32971` 后已保存。

CODOL `Pmove` 在 `0x0041E860`，以 `1000 ms` clamp 和最多 `66 ms` 分片调用 `PmoveSingle 0x0041DBA0`，循环后调用 `PM_SetPitchValues 0x0041E720`；后者与 Ghosts server helper 的控制流和字段职责吻合。`PmoveSingle` 经 `PM_GroundTrace 0x00418500 -> PM_playerTrace 0x00415A10` 使用 `pmove_t + 0x128` 的 handler。`CG_PredictPlayerState 0x004522B0` 以 `0x12C` stride 持有每个 local client 的 `pmove_t`，当前 partial type 也已补齐到该大小。`pmoveHandlers 0x00CE4330` 已由原始 bytes、xref 和三方参考确认是 8-byte `{trace, playerEvent}` 表，但 CODOL 客户端镜像只有 handler `0` 一项：`{CG_TraceCapsule 0x00459C20, null}`，紧随的 `+0x8` 已是无关字符串指针；`BG_PlayerToEntity_ProcessEventInternal 0x004130C0` 会在 callback 非空时分派 player event，说明 null 槽不能替代 server event 边界。BO1 与 Ghosts server build 则保留独立 handler `1`。此外 `Pmove 0x0041E925..0x0041E968` 只在 handler `0` 时计算 client-global base，非零 handler 会以零为 base 写 `+0x2A8/+0x2AC`；Ghosts server `Pmove` 在 `PM_SetPitchValues` 后直接返回，没有这段 client-only tail。因此不能把参考 server 的 `handler=1` 填入本客户端入口，也不能把 handler `0` 的客户端碰撞和对象写入冒充 authoritative server。后续应恢复一个薄的 server wrapper，复用原生 `PmoveSingle/PM_SetPitchValues` 并提供独立 trace callback；player event 则留在后续 playerstate-to-entity conversion 阶段，而不是伪装成 Pmove 内部副作用。

BO1 handler `1` 的第一、第二槽分别是 `G_TraceCapsule 0x00723880` 与 `G_PlayerEvent 0x005FE1C0`。前者建立 `IgnoreEntParams`/`col_context_t` 后调用 `SV_TraceCapsule`；后者签名为 `(clientNum, event)`，只处理需要服务器 recoil/vehicle state 的事件。Ghosts 的 `pmoveHandler_t` 扩展为 `0x48` bytes/9 个 callback，但职责未变：server entry 的 trace 是 `G_TraceCapsuleEx 0x140132A30 -> SV_Trace`，player event 是 `G_PlayerEvent 0x140115DF0`；`BG_PlayerToEntity_ProcessEventInternal 0x140076B50` 在复制事件到 entityState 时才调用它。CODOL `0x004130C0` 具有同一四槽 event ring、64-step wrap 和 server-only/single-client event 过滤控制流，因此已按该稳定名称写入主 i64。该结论把 trace callback、Pmove 与 event conversion 拆成三个所有权阶段，后续 adapter 不得混为一个回调生命周期。

CODOL `CG_TraceCapsule 0x00459C20 -> CG_Trace 0x00459940` 先调用 `CM_WorldTrace 0x0058AFE0` 执行底层 collision-map trace，再按 point/swept bounds 分支叠加 `CG_PointTraceToEntities 0x00459890` 或 `CG_ClipMoveToEntities 0x00459180`，并处理 client dynamic entities。`CM_WorldTrace` 的 custom x86 ABI 已由全部直接 caller 闭合：`EDX=contentMask`、`EDI=end`，栈上依次为 `results/start/bounds/callbacks`；`Bounds=0x18`、`traceWork_t=0xC4`。其下游 `CM_AssignTraceWork 0x0058AA40` 与 `CM_BrushModelTraceFinish 0x0058ACC0` 在字段写入和控制流上与 Ghosts 同名函数逐项同构，BO1 则保留较老的 `CM_BoxTrace -> CM_Trace` 组织。四个 trace 名称、保守结构和 register ABI 已写入主 i64；`CM_IsGlassSolid 0x0043DF20` 也已确认是客户端 callbacks 中的玻璃状态谓词。authoritative callback 可以复用 `CM_WorldTrace` 的静态 world primitive，但仍必须自行叠加服务器实体，并为玻璃状态提供 server-owned callback，不能调用完整 `CG_Trace` 或把客户端玻璃状态当作服务器状态。

CODOL `CM_TransformedBrushModelTrace 0x0058B230` 与 Ghosts 同名实现同构；其 caller assembly 固定 `ECX=angles`、`EDX=trace result`，栈上传入 `start/end/moving Bounds/clipHandle/contentMask/origin` 并由 caller cleanup `0x18`。其中 `CM_BrushModelTraceFinish` 消费 `clipHandle` 作为 72-byte brush-model index，`CM_AssignTraceWork` 消费 `contentMask`；2026-08-10 的车辆碰撞实机异常又以越界 model index 动态确认该顺序。函数与 rotated helper 在 `0x0058B0C2/0x0058B2A7` 写入的 glass callback operand 都指向恒 false 的 `sub_6DF680`，两处指令 bytes 均为 `C7 45 B4 80 F6 6D 00`。`CM_TransformedCapsuleTrace 0x0058B330` 同样保留 stationary overlap、swept capsule、winning normal 回转和 walkable 派生职责。BO1/Ghosts server trace 共同要求 contents filter、忽略 pass entity、忽略由 pass entity 或其 owner 拥有的实体，并在 transformed primitive 命中后由 server wrapper 写 entity identity。源码据此建立 `SvGlassState`、`SvCollisionEntity` 与 `traceServerCapsule`，不借用客户端玻璃或客户端实体状态。实际 MSVC x86 对象反汇编确认 wrapper 对 `CM_WorldTrace` 保存 `EDI`、设置 `EDX/EDI`、压入四参并 caller cleanup `0x10`；对 transformed capsule 设置 `EAX=end`、`ECX=targetOrigin`、压入五参并 cleanup `0x14`。当前未绑定 `CM_TraceBox/TraceExtents` broad phase，只适用于少量 server-owned entities；该结论是 source/ABI 与实机异常证据，尚不覆盖所有动态实体类型。

BO1 `ClientSpawn/G_SetClientContents` 与 Ghosts server i64 `ClientSpawn 0x140119690/G_SetClientContents 0x140116140` 共同确认：活玩家 entity contents 为 `0x02000000`，与 trace query mask 分离；player owner undefined；spawn player bounds 为 midpoint `[0,0,35]`、half-size `[15,15,35]`。Ghosts `G_SetClientContents` 会重新 link，`SV_UnlinkEntity 0x14020BEE0` 清 linked 后移出 collision tree；BO1/Ghosts `ClientThink_real` 都在 Pmove 后把输出 bounds 写回 entity、处理 `ClientEvents`，再调用 `SV_LinkEntity`。2026-08-09 直接复核 BO1 `SV_LinkEntity 0x0071F960`、Ghosts `0x14020A6C0` 与 BO2 `0x007077A0` 后，又闭合普通非模型玩家的稳定子集：`solid` 由 local max X、`1-min Z`、`max Z+32` 截断并 clamp 为三个字节，`0xFFFFFF` 保留给 brush model；absolute midpoint 为 `origin + local midpoint`，absolute half-size 在 Pmove bounds 上每轴外扩 `1.0`。CODOL `CODOL_DecodeEntitySolidBounds 0x00458850` 直接闭合相同 24-bit consumer。源码现由 `SV_EncodePlayerSolid` 与 `SV_LinkPlayerCollisionEntity` 在候选提交后生成并校验 capsule solid/link；失败、Waiting、Inactive、disconnect 与 reset 不泄漏状态。brush model 的 source/native narrow-phase 子集也已恢复：三份参考共同约束 `solid=0xFFFFFF`、零旋转 expanded bounds 与旋转 radius broad phase；CODOL `cm +0x90/+0x94` 提供 count/model pointer，model stride `72`、bounds `+0x00`、contents `+0x24 | +0x28`。源码把两个 hardcoded glass operand 原子改接 scoped server state，并让动态 entity 持有 shape/angles/clip handle；没有 active server trace 时 callback 仍为 false。production 现已从真实 MapEnts 原子建立 `script_brushmodel` lifecycle/collision owner，fixed-slot mirror 也已通过自然运行确认 native spatial link；受控 capsule trace 对照已完成但 source 仍是 owner。trigger、locational DObj、leaf/cluster 和 map entity snapshot 仍未恢复，不能称为完整 `SV_LinkEntity`。

2026-08-10 主 i64 进一步确认 CODOL 映像保留完整 embedded-server entity core，而不只是客户端 consumer。`G_Spawn 0x004E8C30` 与 Ghosts allocator 逐字段同构，使用 `0x2C8` gentity、2046 个可分配槽和 500 ms FIFO 门槛；`G_FreeEntity 0x004E8E70` 完成 unlink、DObj/script/subsystem cleanup、整槽清零与 secure-origin key 恢复，并以 `entityNum >= 27` 作为动态 free queue 边界。`SV_LinkEntity 0x005FAE70`、`SV_UnlinkEntity 0x005FAC80`、`CM_LinkEntity 0x0058CC90` 和 `SV_Trace 0x005FB940` 又闭合固定 `g_entities 0x02AB3410`、`svEntity_s=0x18`、native CM tree 与 point-locational DObj traversal。稳定名称、partial struct 和注释已写入 i64并全库刷新；annotation 与 27-entry matrix 同步。源码已按这些字段建立普通玩家 capsule 与无 DObj brush 的 transactional fixed-slot mirror，并调用原生 link/unlink。`CM_LinkEntity 0x0058CC90 + 0x8A` 通过 `sv_gameEntities 0x03150048` 读取 `gentity_s::contents`；CODOL `G_Spawn` 内联发布该指针和 `sv_numGameEntities 0x0315004C`，BO1/Ghosts 则由 `SV_LocateGameData` 承担同一职责。dedicated 未运行原生 allocator 导致旧值均为零，是首次 native link 异常的直接根因；源码现只在 owner 为空或已指向固定 `g_entities` 时发布，并维护 entity high-water。自然 v7/v8 已确认 mirror、移动和 snapshot 持续推进，原生内存中 published pointer 正确、count 为 212、linked/in-use 为 138。完整 allocator/free 仍不在 `level`/script/DObj 前置条件闭合前接管生命周期；native trace 现只有下段受控 capsule 双跑证据，仍未晋级为 production owner。

`SV_Trace 0x005FB940` 的 public capsule ABI 随后由唯一 CODOL caller `sub_4E2180` 闭合：`ECX=IgnoreEntParams*`，其中两个 `int32` 依次为 `baseEntity/parentEntity`；`EDX=end`；栈为 `result/start/bounds/contentMask`，caller cleanup `0x10`。Ghosts 同名函数直接确认 ignore pair 语义，BO1 则继续提供较旧的 `SV_TraceCapsule` wrapper 责任边界。源码已增加 game-thread-only、SEH 隔离的 source/native capsule 影子比较，调用前要求 fixed-slot mirror 的 source projection、实际 `g_entities` slot bytes、published pointer/count 全部一致，并排除 zero-bounds locational 与已有破碎玻璃状态。自然 v2 在真实 `custom3` 出生和前进输入期间启动比较且未记录差异或异常，commandTime、snapshot 与 parser 保持稳定。该结果确认 ABI 和所测 capsule 样本，不证明 DObj/priority-map/locational 或 glass impact 已恢复；source 仍是 production owner。主 i64 注释已更新并全库 `force_recompile 32971/32971` 后保存，annotation 与 matrix 同步。

2026-08-11 又从 CODOL 本体闭合 glass snapshot owner。`CL_ParseSnapshot 0x0046D170` 在 client infos 后调用 `CG_ReadGlassChanges 0x0043E070`；后者消费 `hasChanges + sparse/full selector`，sparse 使用 11-bit index 和 `1024` terminator，full 使用 11-bit prefix count，两者都用 2-bit state，destroyed 可附带 raw direction byte 与两个 6-bit position。`CG_ApplyGlassChanges 0x0043E1D0` 遍历全部 `1024` piece 并经 `CG_Glass_SetPieceState 0x0043DD40` 应用递增状态；`CM_IsGlassSolid 0x0043DF20` 直接确认 state `<2` 才 solid。主 i64 已新增五字节 `clientGlassPieceState_t` 和 `g_clientGlassPieces[1024] 0x01A0FBD0`，稳定命名上述函数及 `MSG_ReadByte 0x005A14E0`，全库 `force_recompile 32971/32971` 后重新反编译确认字段化结果。Ghosts `G_Glass_WriteChanges/G_Glass_WriteImpactInfo` 与该 wire 最贴切，仅 terminator 为 `1536`；BO1/BO2 的 `GlassesServer` 则确认旧式 damage/touch/snapshot 职责边界，不能覆盖 CODOL 格式。源码现恢复四态 owner、collision、frame freeze、full/delta writer、damage/stateChangeTime 与非穿透 bullet producer；glass touch 仍缺，`25/100` 阈值仍是标注 TODO 的 Ghosts-derived 恢复默认值。

glass impact 的 CODOL-local 数学链也已闭合。`QuatToAxis 0x0062A5A0` 的 custom ABI 为 `EAX=float[4] quat/ECX=float[3][3] axis`；位置分量按 `clamp(round(value * 63/512 + 31.5), 0, 63)` 量化。方向解码 `ByteToDir 0x00628810` 使用 `EAX=byte/ECX=float[3] output` 与 `bytedirs[162][3] 0x00CDA330`；全部 xref 只发现 decoder 和两个内联读取点，没有可调用的 `DirToByte`。源码逆变换因此直接扫描 CODOL 自身表，并采用 BO1/Ghosts strict-max dot 算法。三项稳定命名、ABI 注释和类型已写入主 i64，执行全库 `force_recompile 32971/32971` 后保存并同步 annotation。

2026-08-16 又闭合 CODOL 角色肤色 selector 的本体语义。`CODOL_CharacterCustomization_BuildLocalModelList 0x00569C50` 从 base item secondary definition `+2` 读取 female；`+3` 是原始肤色枚举，并在 `0x00569CFA..0x00569D20` 按 `0/1/2/3 -> wht/cau/yel/blk` 选取字符串。`CODOL_CharacterCustomization_ColorNameToSelector 0x0040C4C0` 再按运行时模型表顺序 `wht/yel/blk/cau -> 0/1/2/3` 转成最终 selector，因此完整映射为 `0/3/1/2`。`CODOL_CharacterCustomization_ParseVariantMask 0x0040D050` 证明 `s/ss/sss` 分别是 gender/faction/color 通配符；`hea_zombiehunter,model,f ss yel,...` 不依赖阵营。旧 Alice oracle 的 raw selection `30`、female `1` 均正确，但 raw color `2` 被源码直接发送后只能得到 head `0`；同一原生 registry 在 selector `1` 下得到 head model ID `42`。这套 secondary-definition 和 CSV variant registry 是 CODOL 专属层，BO1 `G_UpdateClientInfo 0x005FCC70` 与 Ghosts `0x1401167F0` 只提供 authoritative server character-model generation 的职责对照，不复用其字段或映射。九个相关函数已稳定命名并写注释，全库 `force_recompile 32972/32972` 后保存；源码使用同一四值转换，source fixture 已通过，最终 DObj 可见性待自然运行验证。

2026-08-10 又闭合 live-player server DObj 的本体边界。`sub_4E8460` 已按 8 槽 corpseInfo、BO1 对应函数和调用流命名为 `G_RunCorpseAnimate`，不得再作为活玩家入口；CODOL `BG_UpdatePlayerDObj 0x0040B700`、`BG_ResolveCharacterModels 0x0040C7A0`、`Com_GetServerDObj 0x0059E570`、`Com_ServerDObjCreate 0x0059E740`、`DObjCreate 0x006450B0` 和 `DObjFree 0x00645190` 均已稳定命名并记录 custom ABI。主 i64 新增 `DObjModel_s=0x2C`、`DObj_s=0xCC` 与 `characterInfo_t=0x3B8` partial types，以及 2048 项 server DObj map/in-use/pool 和 free counter typed globals；`DObjCreate` 证明 `+0xC0` 紧凑存储先放 `numModels` 个 XModel 指针，`DObjFree` 按 `5*numModels` allocator units 释放。空 attachment tag/model name 需要稳定空字符串而非 null 的结论由两次 `BG_UpdatePlayerDObj` 异常和随后自然创建共同闭合。源码又以原生 `DB_FindXAssetHeader` 对 DObj XModel 指针做逐项身份校验；角色 2 自然出生后只读确认 map/in-use、两个模型指针、bone count 与 radius 可读。同进程 selection-change free/recreate 尚未自然验证；zero-bounds locational 已由后续条目闭环。

2026-08-11 又完成 weapon append policy 的跨版本裁定。CODOL `BG_UpdatePlayerDObj` 从 `entityState_s +0x60/+0x64/+0xE2` 更新 `characterInfo_t +0x324/+0x328/+0x32C`，随后可调用 `0x00445460`；该目标从 native weapon registry 解析 world model并写一个 `DObjModel_s`，但 `ignoreCollision=0`，且其仅有两个客户端初始化 data xref。BO1 当前 server i64 证实 `G_InitGame 0x006267E0` 安装 `G_AttachWeapon 0x006298F0`，旧 Kisak `AttachWeapon=0` 已证伪；BO2 `G_InitGame 0x005EFCD0 -> G_AttachWeapon 0x005EC010` 同样安装 server callback。两者普通 held/dual world model 都用 `ignoreCollision=1`，额外 melee、offhand 或 clip model 才可用 `0`。Ghosts `BG_UpdatePlayerDObj 0x140070070` 虽向 `BG_UpdateCharacterDObj 0x14006F6F0` 传 held/stowed/thrown weapon，但 `G_InitGame 0x1401306C0` 明确将 optional callback 置零。CODOL 没有保留 dedicated `G_AttachWeapon` 或初始化证据，因此 production 保持 slot `+0x96DFC=null`，不把客户端 callback 误作 server locational policy；该项只在新增 CODOL server/运行证据时重开。

源码侧已据 CODOL `playerState_s=0x3564` 建立精确尺寸的持久 native buffer，但只把 descriptor/i64 已确认的字段显式映射到 `SvPlayerState`。每条 command 的候选事务会复制完整 buffer，成功保留本生命中的未知字节，runner/conversion/event handler/投影/commandTime/identity 任一失败则连同 source-level client/entity 一起回滚；读取 native 数据先校验到临时对象，避免 destination 部分更新。spawn 则按 BO1/Ghosts 共有职责新建全零 native 候选、投影已确认字段并 round-trip 校验，成功后同时替换 source/native owner，避免旧生命的未知字节跨 respawn。CODOL `PmoveSingle 0x0041DBA0` 已直接确认 `pm_flags 0x400` 的出生等待释放语义。`BG_PlayerStateToEntityState 0x004134B0` 已由 custom ABI、字段投影和 caller 闭合：`EAX=entityState_s*`、`ECX=playerState_s*`，它把 playerState `eFlags +0xF0` 复制到 entityState `+0x08`，再转换两组 event ring。完整 copy 又闭合 `entityState_s=0x110`；主 i64 的 partial type 当前确认 number `+0x00`、eType `+0x04`、eFlags `+0x08`、eventSequence `+0xAC`、四槽 events `+0xB0`、weapon `+0xD0`、torsoAnim `+0xD4` 与 legsAnim `+0xD8`，其中旧记录的 legsAnim `+0xD0` 已纠正。playerState partial type 进一步确认 predictable sequence `+0xF4`、四个 8-byte event/parameter pair `+0xF8`、predictable old cursor `+0x118`、第二组 sequence/old/ring `+0x11C/+0x120/+0x124` 和 `clientNum +0x144`；第二组 ring 覆盖到 `+0x143`，因此旧 `clientNum +0x130` 假设已证伪。`PM_GroundTrace` 把 `+0x144` 作为 pass entity，`sub_5593E0 0x005593E0` 又多次按十进制 `+324` 将其作为 client index，构成独立本体证据。源码让 `SvGameEntity` 持有完整 native object，并在 Pmove 后由只允许已观察游戏线程调用、带 SEH 和内部候选提交的 binding 执行 conversion；转换推进的 player event cursor、native player/entity state、source entity 和 collision view 作为同一事务提交或回滚。BO1 `ClientEvents 0x005F82E0` 与 Ghosts `0x140114940` 共同确认 conversion 后还需以 Pmove 前保存的 predictable sequence 消费最后四项，并在 `old > current + 64` 时减 256；源码已恢复该结构 batch 和失败回滚，但 production `HandleClientEvent` 仍为空，所以不能声称 weapon/script/gameplay side effect 已恢复。`CG_ProcessSnapshots` 的三条重复路径在转换后对新旧 entityState `eFlags` 做 XOR，并以 bit `0x2` 变化进入 `CG_Respawn`，从而为参考 server 的 `old eFlags ^ 2` spawn 写法补齐 CODOL-local consumer；源码已按该契约实现。`level.time-100` 初始 commandTime 仍只有参考证据，未进入实现。该边界已有 source regression，不提升为 CODOL runtime 证据。2026-08-06 又由 `MSG_ReadDeltaPlayerstate 0x005A4230` 和六个本体 helper 闭合 weapon auxiliary：双手 active weapon state 位于 `+0x26C/+0x288`，`weaponsEquipped[15]` 位于 `+0x2A4`，每槽五个 byte flag 位于 `+0x2E0`，`ammoPools[15]` 位于 `+0x364`、stride `8`，`ammoClips[15]` 位于 `+0x3DC`、stride `12`，其中 clip 保存两手计数。源码 overlay 已双向投影这些槽位并在完整校验后一次提交；非法索引、计数、重复槽和非 bool flag 均不会造成部分更新。五个 byte 目前只稳定命名首项 `heldBefore`，其余保持 `unk_*`。其余可能需要非零的 native spawn 默认值、具体 event/link/impact/activation 和完整 entity serializer 仍未闭合；runner/converter/受限 handler 已接入 production，但尚未获得实机证据。

`BG_PlayerToEntity_SetMisc 0x004131A0` 对 weapon 的本体写入已细分为两个相邻 16-bit 字段：`entityState +0xD0 = playerState current weapon`；`+0xD2` 在普通武器分支同样取 current weapon，但当当前 `WeaponDef +0x488`（十进制 `1160`）为 `3` 时改取 `playerState +0x344`。packed entity field `17/+0xD0/32 bits` 会把两者一并发送，`BG_UpdatePlayerDObj 0x0040B700` 优先取 `+0x60`，否则以 `+0xD2` 作为第三人称 DObj weapon selector。源码已分别保留 gameplay 与 presentation selector；spawn reset 中两者相等只标为普通 loadout bootstrap，完整 native conversion 后才可视为原生值。`playerState +0x344` 的 producer 与 WeaponDef-type-3 语义尚未闭合，不能把两字段永久视为别名。

同一链的其余 presentation 字段已按本体表和 producer/consumer 拆开。`BG_PlayerToEntity_SetMisc` 仅在右手 `weaponState 16..20` 且 `playerState +0x32C` 对应 WeaponDef `+0x478` 等于 build-local marker 时把该候选写入 `entityState +0x60`，否则写零；随后无条件把 `playerState +0x33C` 写入 `+0x64`。`BG_UpdatePlayerDObj` 以 `+0x60 ?: +0xD2` 选择 DObj weapon，并把 `+0x64` 与 byte `+0xE2` 一起缓存到 characterInfo `+0x328/+0x32C`。当前 `entityStatePlayerFields 0x00C52B68` 精确对应 fields `36/+0x60/16`、`37/+0x64/16` 和 `21/+0xE0/32`；`+0xE2` 不是独立 netfield。进一步核对 `BG_LoadCoKnifeStats 0x0042D3E0`、`mp/coKnifeStatsTable.csv`、`0x0042DA20`、`0x0041CA20`、`0x00426620` 和 `CG_AttachWeaponWorldModel 0x00445460` 后，field `37/+0x64` 已确定为 one-based `coKnifeStatsIndex`：表项大小 `0x5C`，其 `+0x44/+0x48` 是两套 knife XModel。它不是 BO1 `weaponModel`、XModel index、第二 WeaponDef 或动态武器 base index；BO1/Ghosts 在这里仅能约束 DObj 更新职责。源码因此使用 `offhandWeaponAssetIndex` 与 `coKnifeStatsIndex`，并完整保留 opaque `unk00E0`。不得把动态武器 `352 -> base 32` 写入该字段，也不得把 `+0xE2` 缩成自造 bool或用固定 weapon/visibility flag/`1.0f` 代替 producer。主 i64 的 `playerState_s +0x32C/+0x33C` 仍位于 `pad_032B`：`+0x33C` 的 consumer 语义已闭合，但 dedicated 写入 owner 尚未定位，仍不足以安全扩张整份 `0x3564` 结构；`+0x344` 在 WeaponDef-type-3 分支中的来源也未闭合。

普通第三人称枪模型是另一条链。`CG_AttachWeaponWorldModel` 先取 `characterInfo +0x324` 对应 WeaponDef；`WeaponDef +0x34` 非空时它是首选模型，`characterInfo +0x348` 可抑制该分支；`+0x34` 为空时仅在 `characterInfo +0x349 != 0` 才使用 `WeaponDef +0x2C`，随后才考虑上述 coKnife 覆盖。CODOL 动态 WeaponDef 构建 `0x0042E3B0` 会从 base definition 复制完整 `0xE28` 字节，再由 `0x0042BA70 -> 0x0042B940 -> 0x0042B380` 按附件元数据 offset 应用覆盖，因此不能仅凭复制动作断言 `+0x2C/+0x34` 保持不变。现有自然捕获证明远端 weapon `352` 已到 `characterInfo +0x324`、两个 visibility byte 均为零而最终 DObj 没有武器；下一次证据必须同时记录动态/base WeaponDef 的 `+0x2C/+0x34` 和 visibility producer，区分资产构建与客户端状态问题。`CodolViewmodelTrace.py` 已加入 offset-derived 读数；在证据出现前不写固定 flag、不手动附加模型。

具体 event 已恢复到第一条可执行边界。CODOL `eventnames 0x00CE4390` 有 163 项；`PM_Weapon_FireWeapon_SendFireWeaponEvent 0x004258B0` 从右/左手与 clip-empty 分支写入 `EV_SV_FIRE_WEAPON 0x31`、`LASTSHOT 0x32`、`LEFT 0x33`、`LASTSHOT_LEFT 0x34`，参数恒为零。2026-08-06 重新读取 `BG_PlayerToEntity_ProcessEventInternal` 与 `0x00C5BA98` 的完整 dword 表，确认 server-only 集合精确为 `0x16/0x1C/0x1D/0x22/0x31..0x34` 后接零；其余 ID 不属于该表，独立 single-client filter 从 `0x00C5BA4C` 开始。Ghosts 的同名 helper 与 dispatcher 确认 hand/last-shot 职责；BO1 `ClientEvents 0x005F82E0` 与 BO2 `0x005B1B70` 保留较旧的 eventParm-to-FireWeapon 合同。production dispatcher 现跳过已由 native conversion 处理的普通表现事件，并对八项 server-only event 保持 fail-closed，直到对应 FireWeapon/reload/switch/offhand effect 恢复。

BO1 `FireWeapon 0x006978F0` 先以 `ent->s.weapon` 调 `Weapon_SetWeaponParamsWeapon`，Ghosts `FireWeapon 0x140169280` 同样从 `ent->s.weapon` 解析 normal/alternate definitions，随后才进入 muzzle、spread 与 bullet/projectile 分派。源码据此让 ClientEvents 从已验证的 entity weapon 解析冻结 `SvResolvedWeapon`，而不是继续向 handler 传整套 loadout 或解释恒零 event parameter；handler 前后均校验 player/entity weapon 未漂移。当前冻结 registry 仅含活动 primary/secondary，完整 world weapon registry 与具体 FireWeapon side effects 仍缺失。

CODOL 本体 `BG_GetPlayerEyePosition 0x00414150` 已由字段访问和全部 caller 闭合：复制 `playerState.origin +0x1C`，叠加 `viewHeightCurrent +0x15C`、第一人称纵横 bob、linked-entity-aware `BG_GetPlayerViewDirection 0x004142D0` 与 lean，最后将眼高下限约束为 `origin.z + 8`。`CG_GetPlayerViewOrigin 0x004E1E00` 对 `eFlags & 0xC00` 走 turret `tag_player`，普通分支则调用该 shared primitive；`BG_IsThirdPersonMode 0x00414D40` 控制是否跳过第一人称 bob。BO1 的同层函数仍名为 `BG_GetPlayerViewOrigin`，Ghosts 已改名 `BG_GetPlayerEyePosition`，CODOL 控制流与后者更贴近。源码新增 build-prefix、game-thread 和 SEH 保护的 `EngineBindings::getPlayerEyePosition`，目前只接受未 link、非 turret 的 native playerState，拒绝把缺失的 server tag/link ownership 隐藏在 fallback 中。

服务端 gun-angle producer 的职责边界已按受限重建接入 production，但仍不是缺失 CODOL server wrapper 的二进制复原。BO1 `ClientThink_real 0x005F9980` 与 BO2 `0x005BF2A0` 在 Pmove 前执行 `G_BuildWeaponState -> BG_CalculateWeaponMovement -> G_SaveWeaponState` 并写入 `gclient.fGunPitch/fGunYaw`；Ghosts `0x140114E10` 在 Pmove 后执行同类链并把 save-back 内联。CODOL `CG_AddViewWeapon 0x0055C8A0` 没有旧版单一总包装，而是直接串联 `BG_CalculateWeaponMovement_Base 0x00430990`、`Sway 0x00430B50`、`Recoil 0x004310F0`、`Bob 0x004312F0`、`BG_SetWeaponMovementAngles 0x00431460` 与 `BG_SetWeaponMovementOrigin 0x00431550`。typed i64 现确认 `weaponState_t` 为 `0x90` 字节，先前的 `0x94` 是 caller 为相邻 bookkeeping 一并保留的空间；`viewState_t` 为 `0x24` 字节。Base 又闭合为 `Stance 0x00430350`、`Movement 0x004304D0`、`GetSprintLerp 0x004306F0`、`WeaponState 0x00430760` 与 `Save 0x00430810` 五个内部阶段。它仅在 `playerState.linkEntityNum != 2047` 时把首参 context 传给 `BG_GetPlayerViewDirection` 的实体角度回调，普通未链接分支不消费该 context；固定 context 因而只适用于显式拒绝 linked/turret 的受控 adapter。CODOL `CG_OffsetFirstPersonView 0x0051D3B0` 证明 view 阶段顺序为 damage kick、idle、bob、ADS bob；client gun-angle producer `0x00559D10` 证明 current weapon `+0x340` 的 `aimDownSight +3446`、`weaponPosFrac +0x34C != 0` 与选中 overlay weapon 的 `overlayReticle +2028 == 0` 时执行 `weaponAxis * viewAxis`，否则使用 view angles；`+0x348` bit `0x2` 会把 overlay 查询切到 alternate weapon `+0x32C`。由 `BG_GetPlayerViewDirection` 和该 producer 的 caller 交叉复核后，主 i64 已命名并定型 `AnglesToAxis 0x0062C1A0`、`MatrixMultiply 0x00629730`、`AxisToAngles 0x0062AE50`。BO1、BO2 和 Ghosts 服务端都直接把该 matrix 转为 angles；CODOL client 中间的 matrix/quaternion/matrix 往返属于渲染 quaternion ownership，不进入 server adapter。源码现以 server-owned 候选持有 damage、weapon idle、idle factor、base/recoil/sway，并由 `NativeWeaponMovementBindings.cpp` 按准确 x86 ABI调用 shared view/weapon/ADS 阶段；它用 native `currentWeapon +0x340` 从 frozen loadout 选择 per-command definition，只允许已观察游戏线程和普通未链接、非 turret、无 shellshock 玩家，未知/错配武器、alternate-overlay flag、SEH、owner 与 finite 校验失败都会回滚完整候选。两个 weapon definition 条件随 `SvResolvedWeapon` 保存，避免为普通 ADS eligibility 重读 client definition。`CG_BuildWeaponState/CG_SaveWeaponState` 仍只作 cgame layout 证据。剩余边界是 alternate weapon ownership、native shellshock 字段、CODOL-local Pmove 前后时序与 linked/turret context；不能以裸 `playerState.viewangles` 或单独 weapon offset 代替已提交 gun-angle owner。语义更新后全库 `force_recompile 32971/32971` 并保存。

FireWeapon 的普通玩家 muzzle 与 spread 前置现已形成 source-tested partial。BO1 `G_CalcMuzzlePoints 0x00697760`、BO2 `0x00676280` 与 Ghosts `CalcMuzzlePoints 0x1401690D0` 共同确认 muzzle origin 取 player eye/view origin，pitch/yaw 取 server-owned gun angle，而 roll 保留 player view roll；CODOL `AnglesToAxis 0x0062C1A0` 的第二行是 left axis，转换为 `weaponParms.right` 时必须取反。`EngineBindings::buildServerWeaponFireBasis` 因而在 weapon ownership 校验后调用 CODOL `BG_GetPlayerEyePosition` 与 `AnglesToAxis`，构造 weapon identity/type、ADS fraction、muzzle trace 和有方向约束的单位正交轴。CODOL playerstate descriptor 与 weaponDef 访问闭合 spread ownership，运行态扫描又闭合最终 weaponDef `+0xBF0` 的 21 项 hit-location multiplier。当前仍只接受普通未链接、非 turret 玩家；production 执行非穿透 bullet 的 native `Bullet_Endpos`、locational trace、六段 damage、glass mutation、普通玩家 damage payload 与普通 world/non-player impact presentation。合法 miss 与 world impact 完成；non-player damage、穿透、爆炸和盾牌返回 `DeferredImpact`。projectile、view kick 和完整死亡/复活状态机仍未恢复。

`PmoveSingle -> PM_UpdateViewAngles 0x0041BC90 -> PM_UpdateLean 0x0041AAE0/PM_UpdateViewAngles_Prone 0x0041B640` 已由 CODOL 调用位置、参数形状及 BO1/Ghosts 控制流三方闭环并写入主 i64。两条下游只修改 caller-owned playerState 并通过 handler 选择 trace；handler `0` 原本进入 `CG_TraceCapsule`，其碰撞来源是当前客户端已加载的 clipMap 与 client entities。`Pmove` 自身在共享计算之后还写入当前 client object 的两个 32-bit 字段，因此 production 不调用完整 `Pmove`。当前 scoped runner 只在游戏线程临时替换 trace slot，执行 `PmoveSingle/PM_SetPitchValues`，消费 server-owned glass/collision 后恢复原槽；完整候选失败仍回滚。本批全库 `force_recompile 32971/32971` 后已保存 i64，稳定名称和注释同步到 annotation JSON。

handler `0` 的 trace ABI 为 `trace(result, start, end, bounds, passEntityNum, contentMask)`；normal player mask 为 `0x02814011`，scale `1.0` 的 standing bounds midpoint/half-size 分别为 `[0,0,35]` 与 `[15,15,35]`。`trace_t` 至少为 `0x28` bytes，已确认 fraction `+0x00`、normal `+0x04`、hit type `+0x18`、hit id `+0x1C`、allsolid/startsolid/walkable `+0x24/+0x25/+0x26`。PM_GroundTrace 的 all-solid correction、start-solid retry、missed/almost-ground-plane、non-walkable contents 和 ladder exception 曾约束已删除的 server 原型；当前只保留为 native adapter 的 ABI、layout 与控制流证据。局内窗口线程动态调用从 `[-313,2160,259.7]` 向下命中 world `2046`，落点 `z=231.73076`、walkable normal 近似 `+Z`。大厅同一调用 fraction 为 `1`，说明 binding 依赖当前已加载 clipMap，不能当作独立 server collision asset。本批在主 i64 写入 `pmoveHandler_t`、`pmoveHandlers` 与地址级注释，全库 `force_recompile 32971/32971` 后保存。

CODOL 原生输入链已从 action table 与真实 usercmd 闭环：`CL_KeyEvent 0x004629C0` 读取当前 key binding action ID，并调用 `CL_ExecuteBindingAction 0x00460870`；后者再分派到 `IN_KeyDown 0x0045E890` / `IN_KeyUp 0x0045E8D0`。`Key_GetBindingAction 0x00462480` 对 `s_bindingActionNames 0x00CE1CC0` 的 99 项 action string 做大小写无关查询。动态调用 `+forward/-forward` 已产生非零 usercmd movement、连续 server-owned origin 和正确 release；因此这些名称是 CODOL-local 稳定 annotation，不是从参考游戏移植。`CL_ExecuteBindingAction` 的 `localClientNum` 位于 `ECX`，action ID 与 key code 位于 stack；在尚未建立可准确表达该 custom ABI 的 prototype 前不强行套用普通 `__cdecl`。

同一 CODOL table 的 entries `1/2` 已确认是 `+attack/-attack`；key-name table 中 `MOUSE1` entry 明确携带 `0xC8`，运行时也解析为 action IDs `1/2` 并产生 usercmd button bit `1`。主 i64 已将 `0x00429320/0x00425250/0x00425930/0x00424C70` 分别命名为 `PM_Weapon`、`PM_Weapon_ShouldBeFiring`、`PM_Weapon_FireWeapon`、`PM_Weapon_WeaponTimeAdjust`；批量命名后全库 `force_recompile` 为 `32971/32971`，并已保存 i64。

2026-08-02 已将上述 Pmove、trace、jump、DTP 和 mantle 入口的稳定名称写入 CODOL 主 i64，并声明保守的 partial `usercmd_s`、`trace_t`、`MantleState`、`playerState_s` 和 `pmove_t`。已核对 `usercmd_s=0x2C`、`trace_t=0x28`、`MantleState=0x10`、`playerState_s.mantleState=0x25C`、`pmove_t.cmd/oldcmd/tracemask/numtouch/handler=0x04/0x30/0x5C/0x60/0x128`。2026-08-05 又由 CODOL `0x0044F280` 的 `[0,0x3524)` copy 与 `0x0046D760` 随后的 16 个 dword `+0x3524..+0x3560` copy 闭环 `sizeof(playerState_s)=0x3564`；主 i64 类型已扩展到该大小，但未确认区域继续保持 padding，不能因完整尺寸已知就宣称字段语义完整。`PM_playerTrace` 与 `Mantle_Check` 保留 CODOL 的 `__usercall` register ABI。`PM_GroundTrace` 明确把 `ps+0x144` 作为 trace callback 第五参数，但这与旧的 tentative `weapon` 标签冲突，因此 i64 和 runtime probe 都保留为 `unk_0144`，待更多 CODOL-local xref 或运行证据再命名。

2026-08-06 又从 CODOL 实际读写点闭合完整 `pmove_t=0x12C`：`touchents +0x64`、`Bounds +0xE4`、`xyspeed +0xFC`、prone/mantle/view-change 输出 `+0x100..+0x11C`、`fTorsoPitch/fWaistPitch +0x120/+0x124` 和 `handler +0x128`。`PmoveSingle 0x0041DBA0` 已准确标为双 stack 参数的 `__cdecl`；`PM_SetPitchValues 0x0041E720` 标为 `EAX=playerState_s*` 加单 stack `pmove_t*`；`PM_playerTrace` 与全局 `pmoveHandler_t[1]` 也已应用准确类型。`pmoveHandlers 0x00CE4330` 位于 PE `.data`，characteristics 为 `0xC0000040`，原始 8 bytes 为 `{0x00459C20,0}`。类型应用后全库 `force_recompile 32971/32971`，刷新反编译已直接显示上述字段；主 i64 与稳定 annotation 同步保存。

同日 weapon auxiliary 的 partial types 也已写入主 i64。刷新后的 `BG_GetAmmoInClipForWeaponDef 0x00421E30`、`BG_GetAmmoNotInClip 0x00421EE0`、`BG_AddClipAmmo 0x0042A230` 与 `BG_RemoveWeaponAndGlobalAmmo 0x0042F1E0` 已直接显示 `playerState_s::weaponsEquipped/ammoPools/ammoClips`；`sub_42F420/sub_42F7F0` 只应用已确认的 playerstate 参数和职责注释，未猜测更高层名称。BO1 server 提供较旧的 15-slot 结构蓝本，Ghosts server 则确认五个 equipped-state byte 与双手 clip 计数职责；两者都未覆盖 CODOL offset。全库 `force_recompile 32971/32971` 后主 i64 已保存，稳定名称和注释已同步到 annotation JSON。

同日进一步将 `BG_PlayAnim 0x00409260`、`BG_RunLerpFrameRate 0x0040A220`、`BG_PlayerAnimation_VerifyAnim 0x0040A600`、`BG_PlayerAngles 0x0040A8C0`、`BG_AnimPlayerConditions 0x0040AC60` 和 `BG_PlayerAnimation 0x0040B5D0` 写入主 i64。CODOL 本体控制流、netfield table 与动态 `165 -> 1024` trace 共同确认 playerstate `+0xD0`/field `27` 是 11-bit `legsAnim`，其中 `0x400` 为 `ANIM_TOGGLEBIT`；原 `currentWeaponAssetIndex` 类型和注释已从 i64、annotation、serializer 与 probe 撤销。`BG_AnimPlayerConditions` 的 `+0xD0` 参数属于 `entityState_s`，不能仅因 offset 相同就与 playerstate 混用。修改后执行了全库 `force_recompile`（32971/32971）并保存 i64。

2026-08-09 从当前 3.3.3.3 i64 闭合了 entity wire 读链，不再使用 `CODOL 0.0.2.2` 的旧 netfield dump。`CL_ParsePacketEntities 0x0046C2F0` 合并 `0x110` 字节条目并以 11-bit `2047` 结束；`CL_DeltaEntity 0x0046C1C0` 管理 snapshot ring；`MSG_ReadDeltaEntity 0x005A3670` 读取 remove/delta/just-unlinked、6-bit lastChanged、3-bit skip chunks，并按 `g_entityStateNetFieldLists 0x00C56CB8[min(eType,22)]` 选择表。当前 `entityStatePlayerFields 0x00C52B68` 的实际 bytes 为 61 个 12-byte descriptor：`eType 0/+0x04/-77`、`eventSequence 6/+0xAC/-75`、`torsoAnim 8/+0xD4/11`、`legsAnim 9/+0xD8/11`、`eFlags 10/+0x08/-98`、events `11..14/+0xB0..+0xC8/-94`、`solid 16/+0xA4/24`、packed weapon `17/+0xD0/32`，且无 `changeHint==2`。field `35/+0xA0/-55` 是独立于 solid 的 conversion-owned 13-bit raw 字段；`MSG_ReadDeltaFlags13 0x005A2750` 证明低 7 位与高 `7..12` 位各有独立 changed bit，exact gameplay 语义仍未知。`MSG_ReadDeltaEventField 0x005A2240` 与实际 162 项 `s_eventParmBits 0x00C56D70` 又闭合组合 event/parm codec 和 `EV_MAX=162` sentinel；BO1 仍分离 event/parm，Ghosts `MSG_WriteEvent` 则确认组合字段、baseline type/parm 复用与按 event 选择参数位宽的职责。BO1/Ghosts 的 ABI/layout/field count 未移植。稳定名称、`entityState_s::solid` 类型与边界注释已写入主 i64 和 annotation JSON，全库 `force_recompile 32971/32971` 后保存。

同表的 trajectory 子集现进一步闭合：origin Y/X/Z 为 fields `1/+0x1C/-82`、`2/+0x18/-83`、`5/+0x20/-81`，angles Y/X/Z 为 `3/+0x40/-79`、`7/+0x3C/-79`、`26/+0x44/-79`，`groundEntityNum` 为 `15/+0x88/-96`，两组 trajectory type 为 `27/+0x0C/8` 与 `33/+0x30/8`。`BG_PlayerToEntity_SetTrajectory 0x00413360` 证明 origin 使用字段地址、float bits 与运行时 keys `0x00CDA23C/240/244` 加密，`+0x5C` 来自 playerState `+0xEC` 的 `movementDir`，不是 ground；ground 由 `BG_PlayerToEntity_SetMisc 0x004131A0` 从 playerState `+0xAC` 写到 `+0x88`。`MSG_ReadOriginFloat 0x005A2320` 与 `MSG_ReadOriginZFloat 0x005A23D0` 使用 `floor(value+0.5)`、7-bit 小差和 configstring `16` map center 的 16-bit XOR；Ghosts server writer同构，BO1 仅 Z full branch 为 17-bit，不能覆盖 CODOL。`MSG_ReadGroundEntityNum 0x005A2190` 闭合 world/zero/general 三分支；`MSG_ReadDeltaAngle 0x005A25C0` 的 full branch为 angle16，压缩 lookup/12-bit delta 尚未恢复 writer。四个稳定函数名、SetTrajectory/SetMisc 纠错、netfield table 注释已写回主 i64，执行全库 `force_recompile 32971/32971`、刷新工作集并保存，同步 annotation JSON。

同一 trajectory 的辅助字段也已闭合：position trDelta Y/X/Z 为 fields `40/+0x28/-80`、`41/+0x24/-80`、`44/+0x2C/-80`，duration/time 为 `42/+0x14/-71`、`43/+0x10/-72`；angle trDelta X/Y/Z 为 `49..51/+0x48..+0x50/-78`，time/duration 为 `54/+0x34/-74`、`55/+0x38/-73`。`MSG_ReadDeltaField 0x005A27F0` 的 CODOL 分支确认 delta 与 duration 读取绝对 32-bit，`MSG_ReadDeltaTime 0x005A20C0` 确认 time 以 snapshot time 为基准，在过去 255 ms 内读取 8-bit subtraction，否则读取 full 32-bit。BO1/Ghosts 只用于确认 writer 职责，字段顺序和 codec 仍以 CODOL 表为准。两条稳定名称、函数与表注释已写回主 i64，全库 `force_recompile 32971/32971` 后保存并同步 annotation。

movement presentation 的首项也已闭合。CODOL `BG_PlayerToEntity_SetTrajectory 0x00413360` 将 playerState `+0xEC` 写到 entityState `movementDir +0x5C`，ET_PLAYER field `4` 使用 codec `-76`。客户端 reader 确认紧凑分支为 `baseline + read5 - 16`，即 delta `[-16,15]`；否则读取 8-bit baseline XOR 并符号扩展。BO1 server 的同字段是固定 5-bit，Ghosts server 虽也使用 `-76`，紧凑范围却只有 `[-7,7]`，所以源码保留 CODOL 自身分支。主 i64 的 reader 与表注释、annotation 和 direct fixture 已同步。

第一人称 bob phase 也已闭合为独立 playerstate owner。CODOL `PM_Footsteps 0x0041A680` 在移动时推进 `playerState_s +0x18`，descriptor field `12` 对同一 slot 使用 `bits=8/changeHint=3`；`BG_CalculateViewMovement_BobAngles 0x00431C40` 和 `BG_CalculateWeaponMovement_Bob 0x004312F0` 均消费其低字节。BO1 `BG_CalcBob 0x00436680/BG_GetBobCycle 0x004640C0`、Ghosts `PM_Footsteps 0x14007D8F0/BG_CalculateViewMovement_Angles_Bob 0x1400A2110`、BO2 `BG_CalcBob 0x009567B0/BG_GetBobCycle 0x0098E590` 确认职责和数据流，不提供 CODOL offset。主 i64 已将 `sub_41A680` 晋级为稳定 `PM_Footsteps` 并注释字段/wire consumer，全库 `force_recompile 32971/32971` 后同步 annotation；当前 partial `playerState_s` 的 `pad_0014[8]` 尚未通过现有 idalib 类型编辑接口安全拆分，源码与文档明确记录 `+0x18`，不为修改展示效果重声明整份 0x3564 struct。

冲刺状态现按相同证据标准闭合。CODOL `playerState_s +0x23C..+0x24C` 是连续 `SprintState`：`sprintButtonUpRequired/sprintDelay/lastSprintStart/lastSprintEnd/sprintStartMaxLength`；235-entry descriptor 分别映射 fields `101/93/35/36/43`，codec 为 `1/1/-97/-97/16`，其中 `101/93` 属于 `changeHint=2` second pass。BO1 同名 `SprintState` 只用于确认五字段职责和 `0x14` layout；CODOL offset、field index 与 16-bit max length 均来自本体表和运行 wire。主 i64 已新增 `SprintState`、更新 `PM_Footsteps/BG_PlayAnim/MSG_ReadDeltaField` 注释并全库 `force_recompile 32971/32971` 后保存；父 `playerState_s` 仍保留该区间 pad，避免在缺少局部 member 编辑接口时重声明整份结构。动态捕获进一步确认 `PM_Footsteps -> moveType 20 -> BG_PlayAnim(anim 309, bodyPart 3, forceDuration 1550, isContinue 1)`，原生结果只更新 torso；自然 sprint run 的 predicted/snapshot `torsoAnim` 依次 `1419 -> 328 -> 1333 -> 395`，均在 1 至 2 个 snapshot 样本内收敛，而 `torsoTimer/legsTimer/legsAnim` 持续为零。因此不得添加 synthetic legs animation 特判。

玩家 identity field 也已闭合。CODOL `BG_PlayerToEntity_SetMisc 0x004131A0` 明确把 playerState `clientNum +0x144` 写到 entityState `+0x9C`，ET_PLAYER field `34` 使用 6 bits；BO1 `BG_PlayerToEntitySetMisc` 与 Ghosts `BG_PlayerToEntity_SetMisc` 都确认同一 conversion 职责，但 layout 与 field index 不复用。主 i64 的 `entityState_s` partial struct 已拆出完整 trajectory、`movementDir +0x5C`、`groundEntityNum +0x88` 和 `clientNum +0x9C`，全库 `force_recompile 32971/32971` 后重新反编译确认并保存。

梯子状态也已完成本体命名与结构记录：`PM_CheckLadderMove 0x0041C200` 建立 `pm_flags & 8` 并写 `playerState_s::vLadderVec +0xB0`，`PM_UpdateViewAngles_LadderClamp 0x0041B230` 用它同步修改 yaw 的 `delta_angles +0xA4` 与 `viewangles +0x150`，`PM_LadderMove 0x0041C4F0` 用它计算 ladder facing、侧移和 `movementDir`。BO1/Ghosts server 均确认该向量由 playerstate 持有；源码只复用职责，不复用 Ghosts x64 layout。主 i64 已命名三函数并记录 `+0xB0`，全库 `force_recompile 32971/32971` 后保存，annotation JSON 同步。CODOL descriptor fields `161/177/188` 为三个 float 分量；当前 wire 已有精确 fixture，但仍缺 Playing 梯子动作对 `pm_flags/vector/deltaAngles/viewAngles/weapon state` 的同时采样。

CODOL playerState descriptor 与 BO1 PDB 相邻布局共同闭合 shellshock 三字段：`+0x5AC shellshockIndex`、`+0x5B0 shellshockTime`、`+0x5B4 shellshockDuration`，分别对应 fields `105/4 bits`、`103/codec -97`、`104/16 bits/changeHint 2`。BO1 客户端消费链确认这组三元组进入 shellshock vision/blend，但 CODOL 客户端的直接 consumer 尚未闭合；因此该映射可以约束 native projection、spawn 和 wire，却不能单凭布局宣布紫红 overlay 的根因。weapon-movement adapter 仍拒绝 active shellshock，直到 time/duration/index 到该阶段 start/fade 输入的 CODOL-local 转换语义确定。

## 服务器函数恢复总表

[`codol_server_function_matrix.json`](../../tools/reverse/catalogs/codol_server_function_matrix.json) 是 breadth-first 服务器恢复的唯一详细总表。当前 29 项覆盖 `SV_UserMove -> SV_ClientThink -> ClientThink -> ClientThink_real -> Pmove/ClientEvents`、Ghosts 候选 `SV_ProcessClientThinks` 分支、spawn/frame/snapshot、weapon state、`FireWeapon -> Bullet_Trace -> Bullet_Process -> G_Damage`、death、`ClientDisconnect`、通用 entity 根节点与 live-player `BG_UpdatePlayerDObj`；其中 `server_only=20`、`embedded_server=6`、`client_shared=3`，实现状态为 `partial=28/missing=1`。只有 CODOL 本体确认存在的 shared 或 embedded-server 入口记录本体地址；server-only 项必须保持 `address/name=null` 和 `not_applicable_server_only`，不能把参考服务器符号伪造成 CODOL 映射。

CODOL 小地图 configstring 消费链已写入主 i64 和 annotation catalog：`CG_ConfigStringModified 0x0057A300` 的 cases `0x7F5/0x7F6` 分别进入 `CG_NorthDirectionChanged 0x0043D770` 与 `CG_MiniMapChanged 0x0043D500`。前者消费 north yaw 并缓存 sin/cos，后者解析 `"<material>" x1 y1 x2 y2` 并计算 compass world size。命名与注释后已执行全库 `force_recompile 32971/32971` 并保存 IDB。IW4、BO1、BO2 `_compass.gsc` 共同约束两个 `minimap_corner` 的选择与旋转算法；Ghosts server 只用于复核 `GScr_SetMiniMap/SetMapCenter/GetNorthYaw` 的职责边界，不复用 x64 ABI/layout。`.runtime/natural-match/20260812_minimap_v1/` 已确认真实客户端消费两项 configstring 并自然绘制 crash 小地图，故本地图 producer 可标为 natural；该证据不自动覆盖其他地图的材质和角点资产。

CODOL 客户端输入链现已闭合到 `MainWndProc 0x00643FE0`、`IN_RecenterMouse 0x0063DCB0`、`IN_ClampMouseMove 0x0063DE00`、`IN_MouseMove 0x0063DE70` 与唯一 `CL_MouseEvent 0x0045EE80` caller。BO1 PDB 的同名函数具有逐分支一致的 `GetCursorPos -> frame delta -> CL_MouseEvent -> SetCursorPos` 形状，并同样在 `MainWndProc` 入口调用 `SetThreadExecutionState(2)`。AW dump `0x1404DB1AF` 的 S1x NOP 地址通过 IAT 证实也是 `SetThreadExecutionState`，而非先前推测的 `Sleep(1)`；S1x scheduler 默认 interval 为零，因此迁移后是每主帧一次。IW8 Xbox PDB 又提供新版相对输入 owner：`IN_OnMouseMovedEvent 0x1419E1580` 从系统 `MouseDelta` 取整型相对量，在 `IN_RelativeMouseLock/Unlock` 内累加 `s_wmv.deltaX/Y`；`IN_MouseMove 0x1419E1100` 每帧原子取走清零并交给 `CL_Input_MouseEvent`。CODOL 源码只复用这一职责，不移植 WinRT/Xbox ABI：Windows client 用 `WM_INPUT/GetRawInputData` 累加相对量，在 `0x0063DEE2` 的唯一调用边界替换自定义 ABI `EDI=deltaX, stack=(cursorX,cursorY,deltaY)`，未收到 raw event 时保持 legacy fallback。主 i64 已写入五个稳定名称、ABI/patch 注释，全库 `force_recompile 32971/32971` 后保存；自然 500/1000Hz A/B 尚未完成。

2026-08-05 的首轮细化反编译确认：BO1/BO2 `SV_UserMove` 对每条合法递增 command 直接调用 `SV_ClientThink`；Ghosts 在即时累计 think 预算不足时把 command 按时间有序放入 8 条环形队列，网络包排空后由 `Com_ServerPacketEvent -> SV_ProcessClientThinks` 在 `sv_cumulThinkTime` 预算内继续处理。该函数只在 Ghosts 参考中存在，不能因 CODOL 的 Raven 维护背景直接移植。三方 `SV_ClientThink` 的共有边界只有拒绝超前 `20000 ms` 的 command、复制 `client_t.lastUsercmd`、设置 last server time 和调用 `ClientThink`；`ClientThink` 再建立 `gclient.sess.oldcmd/cmd`、`lastCmdTime=level.time` 与 `level_bgs` thread context。真正的 `pmove_t` 组装、server handler `1`、Pmove、playerstate-to-entity、events、link、impacts 和 activation 均属于 `ClientThink_real`。因此现有 world loop 不能仅靠改名升级为原生链路。

当前源码已形成 `received -> pending queue -> dispatched -> candidate SvGameClient/SvGameEntity/SvGlassState/player damage/impact event -> executed queue-front commit` 的最小所有权链。`lastReceivedUserCmd` 只保留 wire 诊断；server 只 dispatch 当前队首，持久 source-level owner 承接完整 native player/entity buffer、网络实体、authoritative origin 与 collision view，但不冒充 CODOL native gclient/gentity layout。每条 command 只有在 runner、native conversion、event handler、投影与 exact `commandTime` 全部成功后才原子提交，失败项留在队首并回滚未知 bytes、collision、glass、damage payload 和 temp event entity。scoped `PmoveSingle/PM_SetPitchValues`、server collision callback、`BG_PlayerStateToEntityState`、普通玩家 solid/link、真实 MapEnts brush producer、保守 brush activation、brush native narrow phase、fixed-slot native mirror、动态 bounds/touch 和 event batch 已接入；v6 及后续自然运行已给出移动、动作与 snapshot/prediction 收敛证据。`PmoveSingle` 自然调用 `PM_Weapon`；非穿透 ordinary bullet 现可提交合法 miss、glass damage/impact、普通 `Playing` 玩家 `PlayerDamage` payload，或普通 world/non-player `EV_BULLET_HIT` 表现事件。non-player 的通用伤害、盾牌和 penetration 仍使用 `DeferredImpact` 保留 shared weapon state。整体仍缺原生 `+20000 ms`/`G_SetLastServerTime`、首条 `SV_ClientEnterWorld oldcmd`、native gclient layout、未映射 spawn state、完整通用 `G_Damage`、车辆/动态实体伤害、view kick、pain/last stand/score/respawn、剩余 entity serializer 和 production `ClientImpacts`。

2026-08-15 source audit 又确认项目 packet-thread/game-thread handoff 的 pending queue 不是任一参考游戏的已恢复原生实现：BO1/BO2 在 `SV_UserMove` 直派，Ghosts 才有 `SV_ProcessClientThinks` 的 8 槽累计预算分支。项目仍保留独立 queue owner，但已将 `std::vector + erase(begin)` 的 O(N²) 队首删除改为 `std::deque + pop_front`；这只修复确定的容器热点，不决定 CODOL 的队列上限或每帧 think budget。后两项在 CODOL/参考链路证据闭合前保持 `TODO(CODOL)`，此前短时双客户端性能样本也不再作为整体闭环结论。

2026-08-07 已将 CODOL 客户端 `0x0055A4A0` 闭合并命名为 `CG_BulletTrace`。它与 BO1 cgame `BulletTrace` 同层：调用 client-owned `CG_Trace`、使用 `0x0280E831`、填充 hit position/ignore/depth surface，并以 `trace_t.partGroup==19` 处理盾牌。CODOL scalar `trace_t=0x28` 的 `modelIndex/partName/partGroup` 已确认在 `+0x1E/+0x20/+0x22`，partial `BulletFireParams/BulletTraceResults` 与 custom ABI 已写入主 i64，全库 `force_recompile 32971/32971` 后保存。该函数只约束 layout 和客户端表现分类；矩阵中的 server-only `Bullet_Trace/Bullet_Process` 仍保持 `address/name=null`，当前 `traceServerCapsule` 也因缺 locational priority map、DObj bone hit、完整 ignore 与 impact 规则而不能冒充它们。

2026-08-10 再次刷新 BO1/Ghosts `Bullet_Trace` 后，caller-owned 包装层已形成 partial。BO1 `G_LocationalTraceAllowChildren 0x00723970` 构造 `IgnoreEntParams` 与 `col_context_t` 后调用 `SV_TracePoint`；Ghosts `0x140130F80` 以 zero bounds、locational=1、priority map 和同类 ignore 参数调用 `SV_Trace`。`SvBulletTraceInput/Result` 现选择 bullet/rifle locational request、mask `0x0280E831`、allow-children 和 firing-entity filter，保留 valid miss，解析普通实体、glass 与 static/world 分类，计算 hit position，并通过显式 resolver 取得 ignore 决策；CODOL `partGroup 19 -> surfaceFlags 0x01D00000`、5-bit depth surface、`0x100` 清零与 last-surface fallback 均有 fixture。2026-08-11 已进一步闭合 CODOL 下层 `CM_CalcTraceExtents -> CM_PointTraceToEntities -> SV_PointTraceToEntity -> DObjTraceline`：源码 locational provider 使用完整 `pointtrace_t=0x58`、`IgnoreEntParams=12` bytes 和暂定 Ghosts 22-byte priority map，且只在游戏线程与完整 native mirror 下开放。恢复 `playerState.playerSizeScale -> entityState_s +0x54` 后，自然 probe 命中 entity `0` 并返回 `modelIndex=2/partName=1626/partGroup=5`。production FireWeapon 现调用该 primitive 完成非穿透 glass、普通玩家与普通 world/non-player impact presentation；CODOL-local priority-map 尾部、penetration、车辆/通用实体伤害与通用 `G_Damage` 仍不能宣称恢复。

2026-08-12 进一步闭合 CODOL `ET_EVENTS` 的普通 bullet impact wire。`g_entityStateNetFieldLists[22]` 指向 `0x00C52888` 的 61-entry descriptor；`EV_BULLET_HIT=0x4A` 使用 fields `0/2/3/4/5/6/9/10/16/22`，对应 `eType/origin/eventParm/surface/source/flags/weapon/hitEntity`。`MSG_ReadDeltaField 0x005A27F0` 的 codec `-93` 直接使用 `s_eventParmBits[event]`，实际 bytes 确认 `s_eventParmBits[0x4A]=8`。BO1、BO2 与 Ghosts 的 `Bullet_ImpactEffect/G_TempEntity` 只用于约束 effect-before-damage、坐标向零截断、free-after-event 和严格 `>300 ms` 生命周期；CODOL field table、`ET_EVENTS=22` 与最终 `eType=96` 不复用参考 layout。主 i64 已写入三处注释并全库 `force_recompile 32971/32971` 后保存。源码固定 bitstream、candidate rollback、动态 entity 分配和 snapshot removal tests 已通过；自然客户端 impact 表现尚未验证。

BO2 server i64 的伤害分发已补齐第三方核对。`G_DamageClient 0x005DC730` 与 BO1 `0x00614250`、Ghosts `0x140126B70` 共有的核心职责是校验 target/client、连接或死亡状态、weapon、hitLoc 和 MOD，应用命中部位倍率并保证正伤害，随后调用脚本层；它不直接扣减生命。BO2 额外记录 match hit，并在 `Scr_PlayerDamage 0x006336A0` 后执行 spawn-system 与 lagged-damage side effect。BO2 的脚本入口把 inflictor、attacker、damage、dflags、MOD、weapon、point、direction、hitLoc、timeOffset 和新增 boneIndex 共 11 项压入 `CodeCallback_PlayerDamage`。CODOL 运行态扫描确认最终 weapon definition `+0xBF0` 为 21 项 inline `float` 倍率，12/12 个 definition 命中；这与 BO2 `WeaponDef +0x8FC` 指针和附件覆盖表布局不同，因此源码冻结 CODOL 最终 definition，不移植 BO2 offset。普通非穿透玩家命中现按 `int(baseDamage * multiplier)`、最小 `1` 构造 `SvPlayerDamagePayload`，保留 `partName -> boneIndex`，并只在整条 command candidate 提交后发布 `player_damage`；失败候选不泄漏。BO1 `PlayerCmd_finishPlayerDamage 0x006080A0/P_DamageFeedback 0x005F6500`、Ghosts `0x1401218E0/0x140117820` 与 BO2 `PlayerCmd_finishPlayerDamage 0x005D7440` 进一步确认：脚本规则后才累计 blood、保存最后方向、扣 health 并在 server frame 投影 damage fields。源码已恢复普通玩家非致死 feedback、受限死亡 transition、team/friendly-fire，并独立恢复 world/non-player impact presentation。non-player/车辆伤害、盾牌、view kick、pain/last stand/score/respawn 与 penetration 仍未恢复。主 i64 已在 `CODOL_WeaponDefPartial +0xBF0` 写入 `hitLocationMultipliers[21]`，全库 `force_recompile 32971/32971` 后保存。

真实 MapEnts brush producer 已补上 collision primitive 的 production owner。只读运行时工具从 `mp_crash_tropical` 导出 262262-byte entity string，确认 2123 个实体中有 185 个连续 `script_brushmodel *1..*185`，另有 3 个 `script_vehicle_collmap` 保持独立职责。dedicated 的 CODOL `cm +0x90/+0x94` pool 共 189 项；`*1..*185` 中 28 项的 `contents +0x24|+0x28` 为零，另有 28 项携带 `script_gameobjectname`。BO2 `SV_SetBrushModel 0x006F1CE0/SV_LinkEntity 0x007077A0` 与 Ghosts `0x1401F6A70/0x14020A6C0` 的刷新反编译一致证明：有效 brush model 无条件保留 brush identity、bounds、linked lifecycle 与 `solid=0xFFFFFF`，仅在 `contents==0` 时执行 CM unlink，而不是判 spawn 失败。IW4、BO2 与 Ghosts 的 `_gameobjects::main(allowed)` 又一致证明 gametype startup 删除不匹配的 `script_gameobjectname` entity。源码因此保留全部 source lifecycle owner 和标签，但在正式 gameplay owner 接管前只激活无标签 brush。旧全量激活版本在 SD 出生点命中 `hostage *106` 后产生 native trace failure；修正后的 `20260810_map_brush_activation_v5` 已闭合 185 项原子提交、157 项默认 active、Playing 后 commandTime 持续提交和零 think failure。BO1 本轮 i64 worker 被现存 lock 占用，但此前三方 `SV_LinkEntity` 对 `0xFFFFFF` 与 link 顺序的核对仍有效；本轮新增的零 contents 分支由 BO2 x86 与 Ghosts x64 双方直接一致约束，未声称重新刷新 BO1。

每项固定记录 BO1、Ghosts、BO2 对应函数、caller/callee、关键常量与字段、数据所有权、CODOL 差异、缺失依赖、实现状态、置信度和证据。低置信映射可以进入总表，但不能直接进入运行代码。结构和分类规则通过以下命令校验：

```text
python tools/reverse/ValidateCodolServerFunctionMatrix.py
```

## 参考纪律

2026-08-12 又闭合了 CODOL objective material 消费链。`CG_ServerMaterialName 0x00448E10` 接受相对 index `0..1023`，读取 configstring `4355 + index`，并要求名称非空且短于 64 bytes；`CG_ObjectiveIcon 0x00448D20` 对 index `0` 或解析失败回退默认 objective material，成功时注册 material asset type `7`。`0x0043A4B0` 遍历 playerstate 的 32 个 objective 并消费这些 icon；`CG_ConfigStringModified 0x0057A300` 的 `4355..5378` 分支只负责 server material 刷新，与 `2051` 起的 XMODEL 区间分离。主 i64 已写入两个高置信函数名和三个保守边界注释，全库 `force_recompile 32971/32971` 后刷新确认；未完全闭合职责的 material helper 与 compass draw consumer 只注释、不强行命名。CODOL common MP IFS 直接包含 `waypoint_target_a/b`、`waypoint_defend_a/b` 与 `waypoint_defuse_a/b`；IW4、BO2、Ghosts SD 脚本又共同确认 planted 后防守方看 defuse、攻击方看 defend 的单目标职责。源码据此发布初始两站点与 planted 单站点目标，不借用参考游戏的 ABI、layout 或本地 HUD。

2026-08-14 进一步排除了 playerstate 后一位是 SD round/match state 的旧假设。CODOL `CL_ParseSnapshot 0x0046D170` 的顺序是 playerstate、packet sound commands、packet clients、packet entities、client infos、glass；`CL_ParsePacketSoundCommands 0x0046D060` 管理 44-byte 环形记录，记录由 `MSG_ReadSoundCommandDictionary 0x005A3B50`、`MSG_ResetSoundCommandDictionary 0x005A3BE0` 与 `MSG_ReadSoundCommand 0x005A3C90` 解码，并由 `CG_ProcessSnapshotSoundCommands 0x0051A780 -> CG_ExecuteSnapshotSoundCommand 0x005075D0` 按类型进入声音系统的 start/update/stop/fade 路径。BO1 `CL_ParsePacketMatchState 0x005703C0` 和 BO2 `0x0050EEA0` 均在 playerstate 前读取单个 128-byte MatchState；Ghosts 改为 playerstate 后的 scoreboard/omnvars，也不具有 CODOL 44-byte sound record 形状。因此 dedicated writer 在该位置写空 sound-command section 是正确的最小行为，SD HUD、回合状态和目标表现必须继续从 configstring、可靠命令、objective material 与实体 consumer 定位。六个稳定名称和职责注释已写入主 i64，全库 `force_recompile 32971/32971` 后保存并同步 annotation。

同日继续闭合了 CODOL HudElem 链。`MSG_ReadDeltaPlayerstate 0x005A4230` 在 objectives 后用一个 presence bit 连续调用 `MSG_ReadDeltaHudElems 0x005A4010`，目的地分别为 `ps+0xA78` 和 `ps+0x1ED0`，两者相差 `31 * 0xA8`。reader 对每组读取 5-bit active count、每项 6-bit last field，并按 `hudelemFields[42] 0x00C56AC0` 的 3-bit skipped-field codec 更新；`GetSortedHudElems 0x00515FB0` 又从同一两组 31 项数组收集 `type!=0` 的记录。Ghosts 的 `hudelem_s` 也是精确的 `0xA8/42 fields`，字段 offsets 与 CODOL descriptor 逐项吻合；BO1 保持 31/31 投影职责但旧结构仅 `0x70`，因此只用于较旧职责核对。CODOL 自身位于 `0x00509D8F` 的 3D consumer 接受 type `13/14`，要求 `flags & 0x4000`、`materialIndex 1..1023` 与非零 alpha；`targetEntNum==2047` 时使用记录内 `x/y/z`。主 i64 已新增 `hudelem_s`、三个稳定名称/注释，全库 `force_recompile 32971/32971` 后保存；dedicated 据此在 objective 后的 auxiliary section 9 写 current/archival HudElem，而不替代原有 2D objectives。

KisakBlack/BO1、BO2、Ghosts、S1x、IW8、PDB 和反编译源码用于确认可能的角色、布局与调用顺序，不能直接建立 CODOL offset。各参考 PDB/MAP 的符号已经加载进对应 i64，分析时直接从 i64 的名称、类型、xref 和当前反编译开始，不再重复搜索或导入同一份 PDB。BO1/Kisak 反编译源码同样基于 BO1 PDB，但可能受当时反编译器版本限制；与当前 i64 输出不一致时，以 i64 和进一步的反汇编证据为主，源码只作可读辅助。自动分析可以保存；手工修改参考库时保持最小化和可解释性。

### 核心 primitive 三方核对（强制）

Pmove、prediction、snapshot/wire、weapon、collision、player/entity lifecycle 和 script builtin 下层能力属于核心 authoritative primitive。开始实现或改变其行为前，默认核对以下三方，缺少其中一方时不得把结果描述为已按 COD 原生实现：

1. **CODOL 本体**：先固定目标函数、caller/callee、字段或 wire、关键分支和运行边界；它负责最终裁决。
2. **BO1 Windows x86 server**：读取已载入 PDB/MAP 的 server i64，核对较早的 authoritative server 职责和 x86 代码组织；Kisak PDB-derived 源码只帮助阅读，不能代替当前 i64。
3. **Ghosts PS4 x64 server**：读取已载入 PDB/MAP 的 server i64，核对较新的 Raven/IW 演进、仍保留的算法不变量和新增职责；只比较算法、控制流、调用关系与所有权，不复制 x64 ABI、offset、alignment 或 layout。

每次至少记录职责边界、关键控制流/常量、调用与 side effect、数据所有权、CODOL 差异五项。BO1 与 Ghosts 分歧、CODOL 看起来处在中间演进点，或 Ghosts 的 x64/Orbis 差异无法排除时，再用 BO2 Windows x86 server 交叉裁决。三方共有的形状优先恢复成可追溯的 PDB-derived 代码组织，CODOL-local 协议、字段和分支以小而明确的定向修正覆盖；不得把参考游戏的后期系统顺手移植进来。

参考 i64 被 GUI lock、损坏或暂时不可读时，MAP、原始 machine code 或社区源码只能形成临时线索，不能替代本轮规定的 i64 核对。应在数据库可用后通过 headless `idalib-mcp` 补齐再落实现结论。核对中确认的 CODOL 函数、global、字段、partial struct 和可靠原型必须在同一工作回合写入主 i64；custom ABI 尚不能准确表达时只命名并写明寄存器证据，不强套常规 prototype。不确定项使用 `TODO(CODOL)`，IDA 中使用 `hyp_`/`[HYP]`。一批语义修改后执行全库 `force_recompile`、刷新当前工作集、保存 i64，并把稳定名称/注释同步到 annotation JSON。

2026-08-04 对 `PM_SlideMove / PM_StepSlideMove / PM_ViewHeightAdjust` 的首次强制三方实践得到：

| 边界 | BO1 与 Ghosts 共同形状 | CODOL-local 裁决 | 不应移植的 Ghosts 后期内容 |
|---|---|---|---|
| slide move | 4 bumps、最多 8 planes、ground normal 加 normalized original-velocity plane、`0.999/0.1` 阈值、restrictive plane 排序、crease 投影、gravity end velocity 与 `pm_time` primal velocity | 控制流与上述骨架同构；`PM_ClipVelocity` 使用 `parallel -= abs(parallel) * 0.001`，gravity 结束整体写回裁剪后的 end velocity | platform penetration、contact entity 与扩大后的 trace/platform 状态 |
| step slide | prone/normal step `10/18`、向上 `step+1`、ground snap `9`、`0.3` walkable 门槛、`dot(delta,startVelocity)+0.001` 比较、斜面 `PM_ProjectVelocity` | entity hit cutoff 为 `19`，airborne jump-step 由 CODOL `Jump_GetStepHeight` 门控；已删除原型曾只覆盖 grounded 分支 | moving-platform up vector、platform adjustment、bot-stuck callback 与 Ghosts 的 entity cutoff |
| view height | `11/40/standing`、`400/200/400 ms`、四张 waypoint 表、`100-fraction` 反向和非标准目标 `180 units/s` fallback | standing 为 `60 * playerSizeScale`；只有 scale 精确为 `1.0` 且目标为 `11/40/60` 才走原生表，四表 bytes 已由主 i64 核对 | aliens-mode standing/crouch 表与 Ghosts 的全局 standing-height policy |

这轮核对曾发现旧原型只在 gravity 结束写回 `endVelocity.z`，而三方都整体写回三个分量；原型和 fixture 当时据此修正，之后已随手写共享 Pmove 删除。该结论继续作为 native adapter 和未来完整源码重建的证据，也说明三方规则用于找出会影响后续帧状态的细小差异，而不是为了形式化增加阅读量。

### COD 参考矩阵

该表维护开始调查前的排查顺序和调查后的基本印象。日期取本地资料或目录标注的 build 基准，不等同于游戏公开发售日期；优先级按具体模块判断，不形成覆盖 CODOL-local 证据的全局排名。

| 参考 | 本地形态与架构 | 已验证的贴近点 | 已验证差异或风险 | 当前推荐用途与优先级 | 调查覆盖 |
|---|---|---|---|---|---|
| CODOL 3.3.3.3 QA，`2015-06-15` | Windows x86 client i64；当前恢复目标 | 本体 xref、反编译、descriptor、wire bytes 和运行状态 | 客户端不提供可直接复用的完整 authoritative server 实现 | 所有模块最终裁决，最高 | 持续 |
| BO1 server，`2011-08-31` | Windows x86 dedicated server i64，MAP/PDB 符号已载入；KisakBlack 为同源可读辅助 | 完整 `SV_UserMove -> ClientThink_real -> Pmove`；reliable hash；`changeHint==2` second pass；float `delta_angles`；`1000 ms/66 ms` Pmove slicing；1328 项 server/client builtin 直接绑定表 | usercmd 是旧式嵌套 branch bits，没有 CODOL/Ghosts 的 `7/2/5` trailer；本地 GSC archive 缺完整 BO1 MP corpus | authoritative gameplay 组织、Windows x86 ABI、基础 Pmove 与 GSC binding contract：高；精确 wire：中 | gameplay 五项与 builtin resolver/table 已核对；源码只作辅助 |
| BO2 server，`2014-05-07` | Windows x86 dedicated server i64，MAP/PDB 符号已载入 | 完整 server gameplay 入口；与 CODOL 相同的 reliable hash、playerstate second pass 和 float `delta_angles`；DW3 service/task、publisher 与 matchmaking 结构已有证据 | usercmd 仍是 BO1 式嵌套 bits，无 `7/2/5`；Pmove 最大 commandTime 回退为 `150 ms`，虽仍以 `66 ms` 分步但不同于 BO1/Ghosts | DW3/backend：高；x86 server layout 与 playerstate 交叉核对：中高；Pmove 常量和 wire 直接复用：中低 | backend 已深入；gameplay 已完成首轮关键函数抽样 |
| Ghosts PS4 server，`2014-10-25` | Orbis x64 dedicated server i64，MAP/PDB 符号已载入 | usercmd unchanged/partial/full 的 `7/2/5` trailer 与 CODOL 明确吻合；完整 authoritative server 链；playerstate second pass、float `delta_angles`、`1000 ms/66 ms` slicing | x64 PS4 ABI 与 CODOL x86 Windows 不同；movement 为条件 8-bit 而 CODOL 为 4-bit direction；含 sight masks、remote control、airburst、vehicle 等新系统 | BO1 之后的 usercmd/wire 演进和较新 server 调用结构：高；offset/layout：低 | gameplay 五项已核对 |
| IW4/IW4x | MW2/IW4 世代 Windows x86 资料、脚本/config 与重建源码；不是当前 PDB server i64 | 与 CODOL 的早期 IW 血缘适合解释基础 GSC、配置、asset 和 movement 角色 | 年代早，不能证明 CODOL 后期 wire 与 Raven 改动 | GSC/config、基础引擎职责和旧链路命名：中高；现代协议：低 | 脚本/config 快速调查，gameplay 尚未系统矩阵化 |
| s1x | Advanced Warfare/S1 世代 x64 社区源码参考，不作为本地 PDB i64 使用 | DW3 Auth/LSG server shape、ticket、crypto 和 reply serialization 清晰 | title ID、endpoint、token、service coverage 与 gameplay branch 均不能外推 CODOL | DW3 server state machine：高；gameplay ABI/wire：低 | DW3 已调查 |
| IW8 | `2020-08-09` Xbox One x64 PDB i64及本地导出源码 | 部分 `bdTencent` service/task 名称和字段顺序可解释 CODOL bytecode | 比 CODOL 晚约五年，64-bit、新结果类和 task 编号存在漂移 | 仅在 CODOL task/字段已经局部吻合时作语义补全：中；gameplay：低 | Tencent/backend 定点调查 |

使用矩阵时先按当前函数所属模块选参考，再比较同名函数的控制流、数据布局和 wire；发现新的直接 i64 证据时改写对应单元格，不追加互相冲突的历史结论。

参考 i64/PDB/MAP 原地打开，不复制到项目。正常 IDA 自动分析和保存允许；只有证据要求时才修复函数边界、类型或反编译问题。IW8 IDA 9 参考库为：

```text
D:\_Random\IDA_WS\[XBONE] Call of Duty - Modern Warfare [2020-08-09] (PDB+MAP)\ida9\1-game_test.exe.i64
```

导出的 pseudocode、trace 和大型诊断产物保持 untracked，不进入仓库。
2026-08-12 刷新核对 BO1 `G_Damage 0x00614980`、Ghosts `0x140126580` 与 BO2 `0x005DCD80`。BO1/BO2 的稳定分派为 client、actor、vehicle、显式 takedamage generic；Ghosts 改为 client、agent，并在显式 takedamage 内继续分 vehicle、scriptable、generic。三者共同的 generic 边界包括有效实体生命周期、最低 1 点正伤害、cannot-die、damage/death notify 与 handler table pain/die，不能简化为“所有 gentity 都有 health”。CODOL 当前 MapEnts 实证又显示 destructible 脚本实体只有 `destructible_type` 等初始化线索而无直接 health，因此 source 只增加显式注册的 generation-safe generic damage contract；车辆、destructible、actor/agent/scriptable 仍保持独立 TODO，不复用参考游戏 ABI、offset 或布局。

crash MapEnt destructible 对照进一步确认 IW4 `_destructible.gsc` 的主 part 是有序状态数组：`destructible_create` 建 state 0，后续 `destructible_state` 建下一状态；伤害耗尽时把溢出伤害结转，并在进入下一状态时执行模型、FX、声音、动画和爆炸动作。因而不能把每个对象简化成单个总 health。真实 crash 共 82 个对象、12 种类型；7 种可按完全同名 IW4 定义建立可信主 part 阶段，`toy_ceiling_fan` 的零血动画初态以及 CODOL 的 tropical/ratnest02/tubetvsound 扩展仍需 CODOL-local 定义证据。BO1 `_destructible.gsc` 未提供这些 IW4 MP toy 类型表，只作为同代脚本/原生职责边界参考。

2026-08-15 的双客户端性能证据将 Pmove capsule 从影子比较晋级为 production native owner。BO1 `G_TraceCapsule -> SV_TraceCapsule`、Ghosts `G_TraceCapsuleEx -> SV_Trace` 和 CODOL `SV_Trace 0x005FB940` 唯一 caller 共同约束 server handler 的职责；既有 source/native comparison 累计超过 `400000` 次且 `mismatch=0/unavailable=0`。旧 source 路径在每条 usercmd 的每次 Pmove trace 遍历全部动态实体，和每 command collision-view rebuild 叠加成主要热点；5 秒诊断窗口中 `clientThink` 曾出现 `645ms/1797ms/1424ms` 峰值，而 snapshot build、UDP send 和 SD mode 均为微秒级。production 现只在 fixed-slot mirror 成功、published `g_entities` 与游戏线程有效时直接调用 native `SV_Trace`，失败即拒绝 command；source/native 双跑仅由 `OLMOD_NATIVE_TRACE_COMPARISON=1` 显式启用。clean 双端同时前进后，15 秒 wall time 内 `server_time` 推进 `15050ms`，两端各发送 `294` snapshot，最大 pending `6`、received-to-executed `78/77ms`、ACK gap `3`。该结论只覆盖普通 Pmove capsule；point/locational、DObj 和破碎玻璃 parity 仍各自保持现有边界。
