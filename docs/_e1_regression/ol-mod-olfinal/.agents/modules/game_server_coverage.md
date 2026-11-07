# Game Server 恢复覆盖表

更新时间：2026-08-16

本文是 authoritative gameplay 恢复的当前覆盖索引。详细实现事实仍在
[`game_server.md`](game_server.md)，IDA 证据和参考纪律仍在
[`reverse_engineering.md`](reverse_engineering.md)。表格的每一行只有在
`source -> native -> wire -> client consumer` 四段都有证据时才能标为闭环；仅定位
字段、仅写入 dedicated 本进程 native mirror、仅通过固定 bitstream 测试或仅看到客户端
表现，都不能替代其余环节。

状态：`闭环` 表示本行声明范围内有自然实机证据；`部分` 表示已有正式实现但至少一段缺失；
`待核对` 表示尚未满足 CODOL + BO1 x86 server + Ghosts x64 server 的强制核对；`探针`
表示只用于定位，不是生产实现。

## 玩家实体与 clientInfo

| 链路 | BO1 / Ghosts server 参考 | CODOL producer 与 native | wire | 客户端 consumer | 源码 owner | 状态、置信度与下一缺口 |
|---|---|---|---|---|---|---|
| 身份与 slot | 两者均由 authenticated client、`gclient` 和 configstring/clientInfo 共同持有；具体函数待按本表刷新 | roster 固定 XUID/name，按 XUID 稳定分 slot；名字发布 `CS[1975+clientNum]` | SessionStart v5、userinfo、configstring | `CG_Set/GetClientInfoName`；clan 为 `CS[2015+clientNum]` | `DedicatedSession`、`SvClientSystem`、gamestate writer | **闭环，高**；双客户端名字和 slot 自然验证完成 |
| `packet clients` 基础记录 | BO1 `SV_WriteClientSnapshot` / Ghosts snapshot client section 待补精确地址和字段表 | client slot 的 team、score、身份投影已存在 | CODOL packet-client section 已发送，但字段覆盖未逐项清点 | `CL_ParseSnapshot` 在 playerstate/sound 后解析 packet clients；随后 live cgame client-info 可供 roster rebuild 使用 | `sv_snapshot_mp.*` | **部分，中高（当前 roster 所需 presence/team）**；双端自然捕获已读到 client `0/1` connected、team `0/1`，但不能据此把未清点的 packet-client 字段全部标为闭环 |
| `clientInfo` 角色组合 | BO1 `G_UpdateClientInfo 0x005FCC70` 与 Ghosts `0x1401167F0` 生成 base model 和 6 组 attachment model/tag；布局不复用 | frozen character customization 按 XUID 解析；CODOL `CODOL_CharacterCustomization_UnpackSelectionIds -> ResolveModelIds -> CG_UpdateCharacterModelsFromClientInfo` 解码 11 个 selection，之后另从 slot 6 追加四组显式 attachment；secondary definition raw skin-tone 已按 `0/1/2/3 -> wht/cau/yel/blk -> selector 0/3/1/2` 原生链修正 | 76-bit selection storage 已发送；field `46..49` model CCS / `50..53` tag CCS 的 DTO、校验和 codec 已恢复，但 producer 为空 | 客户端 `CG_UpdateCharacterModelsFromClientInfo 0x0051BC80 -> BG_UpdatePlayerDObj`；旧 Alice trace 的 head 槽为 `0`，source 修复预期为 model ID `42`，待自然验证 | `sv_snapshot_mp.*`、character provider | **部分，中高（selection source/transport 已补，最终 DObj 待验证）**；继续逐 selection 核对最终 DObj，并独立定位四组 attachment 的 server owner，不能用 bitstream fixture 宣称整套角色闭环 |
| ET_PLAYER 身份与类型 | `BG_PlayerStateToEntityState` 共有职责 | native conversion 产出 number/type/clientNum | fields `0/34` | `CL_DeltaEntity -> BG_UpdatePlayerDObj` | `SvGameEntity`、ET_PLAYER writer | **闭环，高** |
| entity snapshot 可见性 | BO1 `SV_AddEntitiesVisibleFromPoint 0x0071C6C0` 使用 per-client PVS；BO2 `0x006FDED0` 与 Ghosts `0x140202580` 改为归档全部 in-use、非 `SVF_NOCLIENT`、number 有效的实体，均不按 eType 决定可见性 | CODOL dedicated producer 已删除；当前 `gameplayActive` 暂时折叠 in-use/publication，实体类型只作为已恢复 descriptor 的 fail-closed codec gate | 已闭合类型进入 packet entities | `CL_ParsePacketEntities -> CL_DeltaEntity` | `shouldArchiveWorldEntity`、`SV_WritePacketEntities` | **部分，中**；当前表现可用不等于原生可见性闭环，仍须拆分 source in-use/svFlags 并恢复 CODOL server per-client policy |
| 世界模型缩放 | BO1/Ghosts DObj 更新没有 CODOL `playerSizeScale` 字段；这是 CODOL 专属差异 | `playerState +0x98 -> BG_PlayerToEntity_SetMisc -> entityState +0x54` | ET_PLAYER field `39`, full-float delta | CODOL `BG_UpdatePlayerDObj 0x0040B700 -> DObj_s+0xC8` | spawn、native projection、snapshot writer | **部分，中高**；字段链和非零表现已闭合，但正常出生值 `1.0f` 的 CODOL 初始化 producer 仍未定位，代码已标 `TODO(CODOL)`，不能把显示成功等同于默认值来源闭环 |
| 世界武器模型 | BO1 `BG_PlayerToEntitySetMisc 0x00425F70 -> BG_UpdatePlayerDObj 0x0040F700` 投影并追加 held/offhand/stowed weapon；Ghosts `0x140076D10 -> 0x140070070 -> BG_UpdateCharacterDObj` 选择 held/stowed/thrown weapon | CODOL conversion 产生 current `+0xD0`、presentation `+0xD2`、weapon-state `16..20` 下的 offhand `+0x60` 和 CODOL 专属 `coKnifeStatsIndex +0x64`；`BG_UpdatePlayerDObj 0x0040B700` 把它们投影到 characterInfo `+0x324/+0x328/+0x32C` | ET_PLAYER fields `17/+0xD0/32`、`21/+0xE0/32`、`36/+0x60/16`、`37/+0x64/16` 已按本体表发送 | `CG_AttachWeaponWorldModel 0x00445460` 以当前 WeaponDef `+0x34` 为首选 world model，或在 client visibility flag `+0x349` 为真时回退 `+0x2C`；`+0x328` 则索引 `mp/coKnifeStatsTable.csv` 的 92-byte 表项并取 `+0x44` knife XModel | native conversion 与 ET_PLAYER writer 已保留全部已知字段；当前远端动态 weapon `352` 已到 `+0x324`，但 DObj 仍只有人物组件 | **部分，中高（状态/wire 已补，普通枪 append 未闭合）**；`coKnifeStatsIndex` 不负责普通枪，不得写 base weapon index。继续核对动态 WeaponDef `+0x2C/+0x34` 与 client-only `+0x348/+0x349` producer；不得固定 flag 或附加某把枪 |
| 动画与姿态表现 | 两者均从 playerstate anim/timers 经 conversion 进入 entityState | native Pmove + conversion 持有 torso/legs anim 和 eFlags | fields `8/9/10`、timers/playerstate fields | player animation/DObj pose 已有有效骨骼矩阵 | shared Pmove adapter、snapshot writer | **部分，中高**；基础动作有效，梯子/翻越/死亡/回合重生未全覆盖 |
| 命中、伤害与死亡 | BO1/Ghosts `FireWeapon -> G_DamageClient -> script damage -> player_die` 同步调用边界已刷新 | 普通 bullet、locational trace、部分 player damage/death 已接线；每条成功 command 后立即提交脚本伤害 | event/playerstate/entity delta | 橙色敌人准星、命中特效、伤害和失能已实机出现；source 双端回归证明同帧后一 command 可见前一死亡 | bullet、damage、world event | **部分，中高（当前普通玩家时序）**；pain/view kick/score/killcam/respawn 未闭环 |
| 记分板玩家行 | BO1/BO2 `MatchState` 不适用于 CODOL；Ghosts scoreboard/omnvar 也仅作职责参考 | live client-info 提供 roster；`SvClientSystem` 响应客户端 `s` 请求并排入 `J/C/D/E` | opcode `2` binary `J` 触发 roster rebuild；opcode `1` 的 `C/D/E` 更新两队和各 client score，共享可靠 sequence/ring/ACK | `CG_RequestScoreboard 0x00452AE0 -> CL_ParseServerMessage 0x0046E6A0 -> CG_InitScoreboardFromProfile 0x0057B760 / CG_ServerCommand 0x0057D560` | `SvClientSystem::queueScoreboardResponse`、client-info/snapshot producer | **闭环，高（roster presence/team 与基础 score）**；clean 双客户端 SD 自然捕获两端均为 `score_count=2` 且包含 client `0/1`。rank、deaths、objective stats 和其真实 profile/gametype producer仍为独立缺口 |

## 双客户端 usercmd 与 snapshot 调度

| 阶段 | BO1 / Ghosts server 参考 | CODOL 当前链路 | 可观测证据 | 源码 owner | 状态、置信度与下一缺口 |
|---|---|---|---|---|---|
| ingress / netchan | BO1 分片重组与 Ghosts 新式 usercmd trailer 共同约束；CODOL wire 最终裁决 | DTLS -> netchan fragment reassembly -> ACK/reliable -> usercmd decode | accepted/duplicate/rejected、sequence、ACK、fragment 状态 | `net_chan_mp.*`、`sv_client_mp.*` | **闭环，高（当前普通/分片包）**；长时异常仍需持续采样 |
| usercmd 队列所有权 | BO1/BO2 从 `SV_UserMove` 直派；Ghosts 可进入 8 槽累计 think-time 队列 | received -> deque pending -> dispatched -> executed，失败只阻塞或按临时 TODO 丢弃精确队首 | 每 client 四个 commandTime、水位与 pending count | `SvClientSystem`、`ServerCore::runFrame` | **部分，中高**；2026-08-15 已消除 vector 队首删除的 O(N²)，但 CODOL 的 direct/budgeted 选择、队列上限和失败策略未闭合 |
| shared Pmove | BO1 x86 与 Ghosts x64 均由 server handler 进入原生 spatial trace；BO2 用于分歧裁决 | scoped 调用 CODOL native `PmoveSingle/PM_SetPitchValues`，临时替换 handler 并由 fixed-slot mirror 进入 `SV_Trace` | think stage/failure、native exception、command commit、双端推进率 | `SvSharedPmoveRunner`、`SvServerWorld`、`EngineBindings` | **部分，中高**；普通 capsule owner 已实机闭环，复杂 linked/turret/梯子、破碎玻璃 parity 及全部 server-only event 未闭环 |
| playerstate -> entityState | 两者共有 `BG_PlayerStateToEntityState` 和 predictable event 消费 | 完整 native candidate，成功后原子投影 source/native | conversion failure、event batch、entity fields | `SvServerWorld::clientThink` | **部分，中高**；必须用字段覆盖表阻止 native-to-source 丢失 |
| 固定 server frame | 两者均为 authoritative `G_RunFrame` 再产出 snapshot；`G_DamageClient -> Scr_PlayerDamage` 在当前 command 栈内同步完成 | 20 Hz scheduler -> begin events -> command + script commit -> mode -> endFrame -> setWorldFrame | 分段耗时、command count、同帧两 command death visibility | `ServerCore::runFrame` | **部分，中高**；已修复帧尾集中伤害偏差，仍缺原生 script thread/per-entity think/精确模式阶段与长期 stall 复验 |
| per-client snapshot baseline | Ghosts `hasAckedBaselineData` 约束 persistent cache；BO1 提供 history 结构 | 每 client 独立 ACK history 与单在途 no-delta initializer | full/delta、message ACK、cache fixtures | `SvClientSystem::buildSnapshotMessage` | **闭环，高（baseline ownership）**；新增字段仍需 coverage gate |
| playerstate / entities / clients / clientInfo / glass | 三方只约束 section 职责；字段必须来自 CODOL descriptor | source frame 按 client 过滤并逐 section 写出 | parser、mask、固定 bitstream | `sv_snapshot_mp.*` | **部分，中**；字段表覆盖率未全量化，`playerSizeScale` 是已修复漏项范例 |
| 序列化、DTLS 与 UDP 发送 | 参考实现均逐 client build/transmit；不得复用 ABI | `SV_SendClientMessages -> snapshotBuilder -> Netchan_Transmit -> DTLS -> Network.send` | C++ 累计耗时/直方图显示 build `70..200us`、send `20..100us` | client system、ServerCore、Network | **部分，中高**；本轮已排除为秒级 stall 根因，仍需 parser/断线长时回归 |
| 客户端 parse / ACK | CODOL `CL_ParseSnapshot/PacketEntities` 最终裁决 | 两端持续回 ACK，60 秒自然 transport 已通过 | snapshot outgoing-ACK、parser reject/overflow（按需） | runtime probe 只读 | **闭环，高（当前测试窗口）**；不能用高频 Frida 采样做性能判据 |
| 多客户端性能 | BO1/Ghosts 的 Pmove server handler 直接使用 native linked-entity trace；两代 command dispatch 策略不同；伤害脚本均随 command 同步 | production capsule trace 已晋级 CODOL `SV_Trace`；pending queue 为 O(1)；不再把全体客户端伤害集中到帧尾 | 先前短样本不作整体结论；source 双端回归已覆盖同帧 command/death 顺序 | `EngineBindings::traceServerCapsule`、`SvClientSystem`、`ServerCore::runFrame`、`runtime-frame` | **部分，中**；已移除一个确定的多端集中处理偏差，仍需审计其余 source owner 后再做长时复杂操作复验 |

## SD 模式状态机

| 链路 | BO1 / Ghosts server 参考 | CODOL producer / consumer 证据 | 当前源码 owner | 状态、置信度与下一缺口 |
|---|---|---|---|---|
| 模式启动、队伍与出生 | BO1/Ghosts `maps/mp/gametypes/sd` 的 level init、team spawn、spectator 流程待系统刷新 | MapEnts 有 team spawns、spectator camera 和 bomb sites；当前能分队并出生 | `ServerCore`、world spawn、Lua map/gametype | **部分，中**；开局仍非完整观察者机位/选包/正式复活流程 |
| 回合状态机 | 两者共有 round init -> playing -> end -> intermission -> restart | CODOL 没有 BO1/BO2 128-byte MatchState section；需从 configstring/reliable/entity consumer 反查 | `SvSdRoundStatus`、`advance/evaluateSdRound` | **部分，中低**；击杀后可失能但回合不完整结束/重开 |
| 炸弹创建与拾取/掉落 | IW4/BO1/Ghosts GSC 均由 script gameobject + trigger + carrier state 协作 | MapEnts bomb/site 已解析，当前炸弹模型和拾取状态不正确 | SD bomb status、script mover、use object | **部分，中**；动态模型/attach/drop 与客户端提示需闭环 |
| 安装/拆除交互 | BO1/Ghosts use/trigger、timed progress、cancel、notify 共有职责待补精确链 | CODOL 包点 trigger 存在，但当前不能 plant/defuse | `sv_use_object_mp.*`、SD command processing | **部分，中低**；先完整恢复 use ownership和时序，不直接改模型掩盖 |
| 2D objective | IW4/BO1/BO2 `_compass.gsc` 与 Ghosts builtin 约束职责 | playerstate objective section、server material consumer 已定位 | `projectSdObjectives`、snapshot writer | **部分，中高**；source 有值但用户看不到，需反查 icon/material/team state |
| 3D waypoint | IW4 `_objpoints` 将其与 2D objective 分离 | CODOL 31+31 HudElem、42 fields、type 13/14、flag `0x4000` 已定位 | archival HudElem projection/writer | **部分，中高**；wire 已实现但实机不可见，需闭合 alpha/material/layout consumer |
| 模式语音 | BO1/Ghosts round/team announcer 由 script state 驱动 | CODOL reliable `p <event>` 和 sound assets 已局部定位；击杀后偶尔播放回合语音 | SD sound queues | **部分，中**；start/end/last alive/side switch 触发时序不完整 |
| 计时、比分与 HUD | BO1/BO2 MatchState 形状已证伪；Ghosts omnvar 不能直接移植 | roster 与基础 `C/D/E` score 已自然闭合；SD `HudSandD` 已创建，booking rules 已投影 `ui_scorelimit/ui_timelimit/ui_halftime` | scoreboard reliable commands、configstring dvar pairs、SD gametype lifecycle | **部分，中**；不能再把玩家行列为缺失。剩余缺口是 SD 回合计时、双方回合分/详细统计及对应 HUD 更新时序，不以通用 `HudScore` 或猜测 MatchState 补齐 |
| 回合结束与重生 | BO1/Ghosts 包含结果判定、score、end notify、清实体、side switch、respawn | 当前有 elimination/bomb outcome 和部分语音，玩家死亡后停留地面 | `evaluateSdRound`、`advanceSdRound` | **部分，中低**；按参考完整列出 side effects 后再实现，避免只翻布尔值 |
| 动态场景/炸点模型 | 三方均由 GSC/entity lifecycle 驱动 stage/model/FX/collision | 静态 script_model 已闭环；炸后包点、梯子、车辆/可破坏物仍不完整 | MapEnts、Lua、dynamic entity lifecycle | **部分，中**；与 SD 状态机共享实体生命周期，但不混成模式特判 |

## 角色与第三人称呈现分段审计

这一链路必须逐段评级，不能因最终人物“可见”就把 wire、selector、模型、附件、武器和
scale 一并标成闭环。BO1/Ghosts 只用于约束 server producer 与 DObj 职责；CODOL 的字段、
表顺序、wire 和 client consumer 始终优先。

| 分段 | CODOL 本体证据 | BO1 / Ghosts 对照 | 当前源码与状态 |
|---|---|---|---|
| 8 段 selection storage | `CODOL_CharacterCustomization_UnpackSelectionIds 0x0040CBD0` 把 clientInfo fields `20/21/22/27/31/32/33/34` 的 76 bits 解成 11 个 ID；每 slot 先读 presence，存在时才读 payload，最多消费 72 bits，其余位保持零 padding | 两者没有 CODOL 这套 wire，不复用 | `SV_PackCharacterCustomization` 是保留客户端解包器的表驱动逆编码，writer cursor 直接沿上述 descriptor entry 的 `10/10/10/10/10/10/10/6` 宽度推进，不再另写 `70+6` 算法；**wire 格式闭合**，但原 dedicated 函数/写法不可见，标为 `CODDIFF(g_update_client_info)`，不代表模型可见 |
| 11 个 selection 语义 | `ResolveModelIds 0x0040C980` 按 faction/female/color mask 和 11 个 slot 解析；color 完整映射为 `0/3/1/2` | 两者只证明 server authoritative character state 职责 | 使用 CODOL 原生 resolver；**高置信**，Alice 最终 head DObj 仍待自然验证 |
| characterInfo 模型列表 | `CG_UpdateCharacterModelsFromClientInfo 0x0051BC80` 按 slot base/name table 解析并紧凑排列；`BG_UpdatePlayerDObj 0x0040B700` 从 `+0x18/+0x20` 消费至首个空名 | `G_UpdateClientInfo 0x005FCC70/0x1401167F0` 从 gentity 更新 base/attachment | ol-mod 复用 CODOL resolver/table 构造缺失 server producer；**部分**，属于 `CODDIFF(g_update_client_info)`，不是原函数复原 |
| 显式附件 | clientInfo fields `46..49` 模型 CCS、`50..53` tag CCS，consumer 追加到 slot `6..9` | 两者 server producer 各写 6 对，布局不能移植 | DTO 与 wire 已分离，production 暂为空；**缺失**，禁止用 `head/tag_head` 特判 |
| 世界武器与可见性 | `BG_PlayerToEntity_SetMisc 0x004131A0` 写 `+0xD0/+0xD2/+0x60/+0x64`；field `37/+0x64` 已由 `BG_LoadCoKnifeStats 0x0042D3E0`、`mp/coKnifeStatsTable.csv` 和多个 consumer 证明为 one-based `coKnifeStatsIndex`；ET_PLAYER field `21` 覆盖 `+0xE0`，其中 `+0xE2` 被 `BG_UpdatePlayerDObj` 用作 DObj dirty 比较；`CG_AttachWeaponWorldModel 0x00445460` 读取 characterInfo `+0x324/+0x328/+0x348/+0x349` | BO1 的 `offhandWeapon/weaponModel/stowedWeapon` 与 Ghosts held/stowed/thrown 只约束职责；两者没有 CODOL coKnife 表，不能提供字段命名或 producer | fields `17/21/36/37` 已从 native conversion 投影到 source 并进入 writer；`+0x64` 已纠正命名，但 dedicated `playerState +0x33C` producer、特殊 WeaponDef-type-3、`+0xE0` 其余位、动态 WeaponDef 普通 world-model append 和 client visibility producer仍未闭合。server DObj callback 保持 null；**部分** |
| 玩家 scale | `BG_PlayerToEntity_SetMisc` 投影 ps `+0x98 -> es +0x54`，ET_PLAYER field `39` 发送 full-float delta，`BG_UpdatePlayerDObj` 再无条件写 `DObj +0xC8` | BO1/Ghosts 的 PDB `playerState_s` 只有 hold-breath、move-speed、aim-spread/grenade/recoil 等其他 scale，没有 player/DObj size 字段；只可证明 DObj 更新职责，不提供默认值 | producer 后的 native/wire/consumer 已闭合；2026-08-16 对 CODOL `+0x98` 直接写入者和 scale 命名入口的定向复核仍未找到 deleted-server initializer。`1.0f` 继续只是 `OLMOD(player-size-bootstrap)`，用于防止 DObj 折叠；原始 ClientSpawn/GSC 初始化 owner **缺失**，不得晋级为 CODOL 默认常量 |

## Coverage gate

修改上表任一链路前，提交或 review 至少回答：

1. BO1 Windows x86 server 与 Ghosts x64 server 的函数、调用顺序和职责是否都已读取？若分歧，BO2 的裁决是什么？
2. CODOL 本体的 producer、native field/offset、wire descriptor 和最终 consumer 分别是什么？
3. 当前源码中哪一个对象拥有状态，哪些转换只生成候选，失败时哪些状态必须一起回滚？
4. 自动测试锁住的是算法、bitstream 还是生命周期；自然实机证据又覆盖了哪一段？
5. 新确认的 CODOL 名称、partial struct、字段或函数类型是否已通过 headless `idalib-mcp` 写回 i64？不确定项是否明确标成 `hyp_`/`TODO(CODOL)`？

源码回扫由 `tools/reverse/catalogs/codol_gameplay_source_audit.json` 管理。它按 scope 自动把所有
既有 gameplay 文件纳入清单，函数块只有同时存在有效 matrix id、证据说明、剩余缺口以及源码
中的 `CODREF/CODDIFF/OLMOD/TODO(CODOL)` 标识才算完成 review。`coverage=symbol` 只证明命名
函数或逻辑块，`coverage=full_file` 才证明该文件已经从头到尾逐块分类；实现仍可保持
`reviewed_partial` 或 `reviewed_project_boundary`，不能把“已读完”混同为“已恢复完成”。运行
`python tools/reverse/ValidateCodolGameplaySourceAudit.py` 可直接查看 fully audited、partial 和
untouched 三类清单；未审计不等于已知错误，但严禁把它当成已经按原生链路恢复。

其他模型或子任务不得直接用参考游戏结论修改主线。它们只提交结构化证据包：目标行、参考游戏函数/地址、完整调用链、字段/offset/bits、CODOL 对应证据、确认与推测边界、建议实现和待验证项。主 agent 复核 CODOL i64、协议和现有 owner 后再落地。
