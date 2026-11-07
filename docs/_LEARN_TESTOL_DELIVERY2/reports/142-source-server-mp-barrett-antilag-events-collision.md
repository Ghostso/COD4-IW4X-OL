# 142 · Barrett 资源、antilag、client events/spawn、碰撞与玻璃

## 一、范围

本报告完整学习 **9 个文件**：

- `sv_alpha_barrett_assets_mp.hpp/.cpp`
- `sv_antilag_mp.hpp/.cpp`
- `sv_client_events_mp.hpp/.cpp`
- `sv_client_spawn_mp.cpp`
- `sv_collision_mp.hpp/.cpp`

至此本轮累计写完 `server_mp` **63/154** 文件的对应学习报告。报告以本 build 的源码、其记录的原生实测和局部逆向为准；外部项目仅作参考，不把旧 build 常量当权威。

## 二、Alpha Barrett：不是复制整包，而是严格闭集验证后的资产转换

### 2.1 四种资源的闭集

Bundle 只允许固定内容：

- 4×4 `model_table`，每行 `barrett_mp,skin,worldModel,viewModel`；
- 17张图片；
- 4套 skeleton：weapon_view29骨、weapon_world11骨、modular_view20骨、modular_world15骨；
- 9个构造 material、15个 retained material；
- 10个 model：完整 view/world Barrett + 4套 modular world/view；
- 15段动画。

source zone 必须是 `ui_viewer_mp.zone`，SHA256 必须等于 `f39e86d5...da9d9b`；格式字符串必须为 `olfinal-alpha-barrett-metadata-v4`。不是这些来源就直接拒绝。

`model_table` 的4行只换 skin 0..3及对应模型名，world/view 名称必须全部在10个 model 中。图片名、sourceName、semantic、模型 resources、material names 都按顺序全等验证，不能只查“文件里有几个”。

### 2.2 图片转换

`SV_BuildOlfinalAlphaBarrettImage` 要求：

- loadDef/name 地址非零且长期有效；
- alpha header +0/+28 指针为零；
- width/height/depth（+20/+22/+24）均非零；
- alphaLoadDef+12 为零。

OLfinal header52字节：先清零，复制 alpha+4..11 到 final+4，复制 alpha+20..26 到 final+32，alpha+27→final+40，final+0=loadDefAddress，final+48=nameAddress。loadDef16字节保留 alpha 内容。

Bundle 另验证 image type3、semantic符合表、pixel format3、loadDef+0/+4为零、+8是 `DXT1` 或 `DXT5` 小端码、+12为零。图片 mesh/IWI 原始字节不进入 metadata对象，仍属另 hashed loose overlay。

### 2.3 Material 布局兼容

OLfinal material104字节。构造函数先验证：

- nameAddress非零；
- texture/constant/stateBits 表为空时地址必须为0，非空时必须非零；
- textures<=255；
- constants大小为32倍数，stateBits大小为8倍数；
- 三个 table 数量必须与 alphaHeader[72..74]一致；
- retained template 的路由 scalar 必须兼容。

兼容比较：

- alpha+16..21 ↔ final+20..25；
- alpha+4 ↔ final+26；
- alpha+5..7 ↔ final+28..30；
- alpha+24..71 ↔ final+32..79；
- alpha+72..78 ↔ final+81..87。

通过后才复制 final template，并写 final+16=name、+92=texture table、+96=constants、+100=stateBits。这防止 retained technique 按自己的参数布局读到表外。

### 2.4 Skeleton、XModel、XAnim 验证

Skeleton：

- boneNames 数量精确、无空名；
- childCount=boneCount-rootCount；
- parentList=childCount bytes；
- quats=childCount*8；
- translations=childCount*12；
- partClassification=boneCount；
- baseMatrices=boneCount*32；
- bone_name_indices只校验长度，不沿用其 process-local script-string id，后续必须按名字 intern。

XModel header360字节：

- boneCount +4、rootCount +5、surfaceCount +6、lodCount +297；
- +0/+44/+48/+52/+56/+60/+64/+68/+300/+312/+352/+356 指针必须零；
- 每个LOD的 +8/+12/+48 指针必须零；
- materials/resources/boneInfo 都按 model spec 验证；
- model 名称不可重复且必须覆盖全部10项。

XAnim header88字节：

- 0及+48..84 的指针必须零；
- 10个 pointerPresence 中第9（delta part）必须 false；
- boneCount/notifyCount、frames、index width、dataByte/Short/Int/random streams 全按 header 计算；
- rotation/translation 五类计数都等于 boneCount；
- notify records 每条8字节，首 u16 必须0，禁止保留 alpha notify index；
- 非空 stream 对应 pointerPresence 必须为 true。

这套验证的要点是：**来自 alpha 的进程指针和 script-string id 都不能直接跨进程使用；资源名、尺寸、标量可移植，运行时指针必须重建。**

## 三、AntiLag：只在同一生命代际内插值

最大 rewind = **400 ms**，record 保留窗口 = **500 ms**（400+100）。

`record`：

- 删除非 finite origin；
- 按 clientNum 排序，发现重复 client 就整帧不记录；
- 同 serverTime 覆盖最后帧，否则追加；
- 删除比当前时间早超过500 ms 的旧帧。

`originAt`：

- frameMilliseconds 必须非零，currentOrigin finite；
- `age=serverTime-commandTime`（uint32）；
- 仅当 `age>frameMilliseconds && age<=400` 才 rewind；
- older 是最后一个 `frame.serverTime<=commandTime` 且含同 client+spawnGeneration 的帧；
- newer 是第一个 `frame.serverTime>=commandTime` 的匹配帧，找不到就用 currentOrigin/serverTime；
- 没有 older 直接失败；
- newerTime==olderTime 返回 older；
- 若 commandTime<olderTime 或 newerTime<commandTime（按 int32 比较）则失败；
- 否则线性插值，最终结果必须 finite。

这避免拿上一条命/另一玩家的坐标补偿当前子弹。时间差采用有符号比较来处理部分回绕，但 age 本身仍是 uint32，服务端和 commandTime 必须来自同一时间基准。

## 四、Client events：当前 build 的 id 与事务顺序

### 4.1 关键事件表

| 事件 | id |
|---|---:|
| OffhandEndNotify | 0x17 (23) |
| ReloadStartNotify | 0x1D (29) |
| ReloadAddAmmo | 0x1E (30) |
| WeaponSwitchStarted | 0x23 (35) |
| SV fire right / last | 0x36 / 0x37 (54/55) |
| SV fire left / last left | 0x38 / 0x39 (56/57) |
| variant A/B | 0x3A / 0x3B |
| melee commit | 0x3D (61) |
| offhand use | 73 |
| alt-related observed event | 74（不在 server-only array） |

旧3.3.3.3的 fire id +5 才是本 build；reload/notify是+1。0x3A/0x3B在 server-only array 中，但选择条件未知，所以 predicate 承认它们，fire decoder仍拒绝，属于**明确丢弃**而非漏写。

`SV_DecodeFireWeaponEvent` 要求 parameter==0，并将四种 id 映射 right/left × normal/lastShot。`SV_IsRewindableAttackEvent` 接受这四种或 melee 0x3D。

### 4.2 `SV_PresentationFireEventId`

仅用于 **entity presentation ring**：

- 54→41
- 55→42
- 56→47
- 57→48
- 其他原样，包括0x3A/0x3B。

绝不能改 playerState predictable ring，否则真实子弹路径失去输入。远端枪声与 compass ping 来自客户端对 event41 的处理，而不是把54直接发给客户端。

`SV_AddEntityPresentationEvent` 写 `events[eventSequence&3]={id,0}`，随后 sequence+1。调用顺序必须在 native projection 后，避免新增事件被覆盖。

### 4.3 Detailed handler 的结果语义

- 最多4事件，超过 `Invalid/event-slice-too-large`；
- `Applied`/`DeferredImpact` 可以提交；
- `Unsupported`/`Invalid`/`Failed` 拒绝整个 usercmd，包括此前事件产生的候选修改；
- `DeferredImpact` 保留原生 PM_Weapon 的确定性状态，但明确表示子弹/穿透/伤害 continuation 缺失，不能假装完成。

每个拒绝有 thread_local 字符串原因，如 melee参数、offhand ownership、switch target、fire basis、handler result等。alt/host lookup 和 perk scale 也是独立外部依赖，避免扩大地址敏感的 client state。

### 4.4 分支顺序

1. **Melee 0x3D** 先于 server-only filter：parameter必须0；weapon来自 entity.networkState，必须能在 loadout或alt解析且与 playerState current一致；无 handler时忽略；Failed才拒绝，Missed/Glass等不是执行失败。
2. **Offhand use 73**：parameter必须1..0x7FF且在 equipment中，并且 heldWeapons拥有；handler Applied继续，Deferred标记，Failed拒绝。无 handler则 Deferred，不二次扣 ammo（PM已消费）。
3. 非 server-only：忽略，并且每种 id 只打一次 FIRST SIGHTING，便于识别74等新通道。
4. WeaponSwitchStarted 0x23：parameter0..MaximumWeaponAssetIndex；目标依次查 loadout/alt、owned offhand、当前 rewardActionType1且weapon匹配的UAV；均不命中则拒绝。成功只排队 script notification。
5. OffhandEnd/ReloadStart/ReloadAddAmmo：PM已有权威 timers/ammo，当前只跳过，脚本通知仍TODO。
6. Fire：entity weapon必须与 source player current一致；构造 basis/spread；spread输入 stance/viewHeight/playerSize/weaponPosition/currentAim/spreadOverride/hipMinMax/ads/perk。basis weapon/type必须一致且合法。
7. 无 fire handler：非 bullet Unsupported；bullet则 Deferred。
8. 有 handler：调用后再次确认 weapon未在变，Applied继续、Deferred标记、其它失败。
9. 成功 fire 后向 **entity ring** 添加转换后的 presentation event。

`SV_HandleClientEvents` 是 bool 适配，只把 Applied/Deferred当true，详细原因需用 Detailed版本。

## 五、ClientSpawn：候选重建、原生 round-trip、特殊 unarmed 分离

### 5.1 输入拒绝条件

- clientNum>63；
- origin/angles非 finite；
- ground>2047；
- gravity/speed为0；
- moveSpeedScale非 finite或<=0；
- viewmodelIndex>0x3FF；
- maxHealth为0或>255；
- loadout无效。

全部在修改原 player 前检查。failureReason区分 admission、equip和native round trip。

### 5.2 Source candidate 重建

`next` 不从旧玩家整体继承，而是逐项建立：

- clientNum；
- commandTime=userCmd?userCmd.commandTime:serverTime；
- pmType=0；
- pmFlags=0x400 respawned；
- eFlags=旧eFlags XOR teleport bit2；
- otherFlags=Player；
- perks先清零，使客户端后续出现 clear→set 的 HUD边沿；
- origin/gravity/speed/moveScale/viewAngles；
- weaponAnim保留用于 toggle；
- health/maxHealth=config；
- spawnGeneration=旧值+1（uint8回绕）；
- viewHeight current/target/lerpTarget=60；
- playerSizeScale保留正值，非正视为未设并用1.0；
- ground=config；view/moving/remote/link entity均为none；
- damage/shellshock/deadYaw清零。

若有 userCmd：

- deltaAngles[i] = config.angles[i] - `BG_ShortToAngle(userCmd.angles[i])`；
- buttons 清 `0x300`，其余保留；
- forward/right继承。

第一 usercmd/commandTime baseline 仍是TODO，不冒称恢复零售精确顺序。

### 5.3 装备与 alt

`equipResolvedLoadout` 先验证 loadout，然后：

- current=primary（unarmed时用 unarmedWeaponAssetIndex）；
- 两手 weaponAnim 各翻转 `~anim & 0x400`；
- weapon time/delay/restrict/state/handFlags/shotCount清空；
- held/clips/pools清空。

普通 spawn：

- held[0]=primary、held[1]=secondary，heldBefore=true；
- unknownState[0]=dualWieldCapable，**不是 partner weapon index**；
- 对 primary/secondary分别 `SV_LookupAltWeaponForHost`，成功才加入 resolvedWeapons和后续 held槽；
- clips 按 clipIndex 合并，count[0]=max(old,clipSize)，dual wield 时 count[1]同样；
- pools 按 ammoIndex 合并，count加 maxAmmo并 clamp到0x7FF。共享 ammoIndex 的“相加”是当前源政策，注释明确不是已恢复原生 give-ammo 规则。

alt 的方向不可写反：`SV_LookupAltWeapon` 输入 ALT 验证能否射击，`SV_LookupAltWeaponForHost` 输入 HOST 找其 alt。spawn需要后者。

### 5.4 Unarmed 特例

- source current=unarmedWeaponAssetIndex；
- held[0]只放空手武器并 heldBefore=true，不投射普通 loadout、不填 alt/clips/pools；
- round-trip后 native current被强制设0。

这是**唯一允许 source/native 不一致的字段**：客户端需要 dmz_empty_mp 画手，原生 weapon movement 又不能接受一个不在真实 loadout里的武器。若在 round-trip前清零，source/native全等检查会失败；所以顺序是先验证后清 native。

### 5.5 原生提交

- `nextNative{}` 全零；
- source→native overlay；
- native→source roundTrip；
- 必须成功且 `roundTrip==next`，否则不修改原玩家；
- unarmed 清 native current；
- hold breath 设 scale1.0/time0；
- 最后分别移动 source/native 给调用方，实现原子外观。

## 六、Collision：形状、过滤、packed solid 与 glass

### 6.1 常量与基本结构

- StandingPlayerTraceBounds：midpoint(0,0,35)，half(15,15,35)；
- DeadPlayerTraceBounds：midpoint(0,0,15)，half(15,15,15)；
- PlayerCollisionContentMask=0x02814011；
- PlayerCollisionContents=0x02000000；
- DeadPlayerCollisionContents=0x04000000；
- PlayerSolidEncodingContents=0x02004001；
- max collision entity=2045；
- hitType entity=1、glass=4；
- BrushModelSolid=0x00FFFFFF；
- KnownLocationalPriorityCount=20，map大小256。

`SvCollisionEntity` 是归一化 source view，不是 gentity。`SV_IsCollisionEntityValid` 要求：

- shape<=ScriptModelDObj，bodyRole<=Actor；
- 非 capsule 的 bodyRole必须None；
- BrushModel 必须有 clipHandle且 modelName空；
- ScriptModel 必须无 clipHandle、modelName非空、不是`*`开头、无NUL、scale>0；
- capsule modelName空，angles pitch/roll必须0（yaw-only）；
- entity/owner<=2045，origin/angles/bounds/absoluteBounds全合法。

### 6.2 Link 后的 absoluteBounds

Player/actor：

```text
absolute.midpoint = origin + localBounds.midpoint
absolute.halfSize = localBounds.halfSize + 1
```

actor 复用 player 然后 bodyRole=Actor。

Brush：

- 无旋转同 player 的+1扩展；
- 有旋转时 `extent[axis]=abs(midpoint[axis])+halfSize[axis]`，radius=sqrt(sum extent²)，midpoint=origin，halfSize.fill(radius+1)。

ScriptModel 不拿玩家 capsule近似，bounds/absoluteBounds默认零，真实 DObj broadphase由 native 后续权威负责；必须有非空 modelName和contents。

### 6.3 packed solid

Decode 仅 `0<solid<0xFFFFFF`：

```text
radius = (solid&255)-1
bottom = 2 - ((solid>>8)&255)
top = ((solid>>16)&255)-33
```

要求 radius>0且top>bottom；midpoint.z=(top+bottom)/2，halfZ=(top-bottom)/2。

Encode player：

- 若 contents不含 `0x02004001`，返回0（例如 corpse 仍可 linked 但不发 packet solid）；
- horizontal=clamp(int(halfSize.x),1,255)；
- lower=clamp(int(1-minZ),1,255)；
- upper=clamp(int(maxZ+32),1,255)；
- solid=horizontal | lower<<8 | upper<<16；
- 若恰为0xFFFFFF，改成1，避免被当 brush sentinel。

`SV_EncodeBrushModelSolid` 对合法 bounds 直接返回0xFFFFFF。

### 6.4 Trace 请求与过滤

`SV_IsTraceEntityFilterValid`：passEntityNum/passOwner<=2045；passOwner存在时 passEntity必须存在。

Point request 要求 start/end finite、mask非零、filter合法、mode<=RifleLocational、worldOnly与entitiesOnly互斥；CollisionOnly 不允许 allowChildren或entitiesOnly。

`SV_ShouldClipToEntity`：

- linked且contents&mask；
- 无 passEntity则通过；
- entity==passEntity排除；
- owner==passEntity排除；
- 若有 passOwner 且 owner==passOwner也排除。

Broadphase 是 swept AABB：每轴 moving min/max 加 bounds，与 absolute AABB 比较，分离即拒绝，边界接触仍通过。`SV_ApplyEntityTraceHit` 只在 entityTrace.fraction<aggregate.fraction 时覆盖，并写 hitType=entity、hitId=entityNum、contents=entity.contents。

`SV_CompareTraceResults` 按 fraction→normal→surfaceFlags→contents→hitType→hitId→modelIndex→partName→partGroup→allSolid→startSolid→walkable 返回第一差异；fraction/normal容差默认1e-4，非 finite直接判差。

### 6.5 Locational priority 表

bullet 前20项：

```text
1,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,0,101
```

rifle 前20项：

```text
1,9,9,9,8,7,6,6,6,6,5,5,4,4,4,4,3,3,0,101
```

其余236项零。20是实际表长，index20/21不可仿照其他游戏补上；旧 index19=201也是外部值，不是本 build 的101。

### 6.6 Glass metadata 与 impact quantization

- `SvGlassPieceCount=1024`：既是11-bit sparse list终止值，也是地图为碎片预留的 headroom；
- definitionCount<=1024、initialPieces<=1024；
- 有 initial pieces 时 definitionCount非零；
- 每片 quaternion/origin/uv有限，radius/area>=0，definitionIndex<definitionCount。

Quantize：

1. metadata、pieceIndex、hitPosition/damageDirection有效；
2. 零方向返回无 impact，不需要 encoder；
3. encoder必须存在并给出方向；
4. quatToAxis 要求四元数范数>0，以2/norm²构造轴；
5. offset=hit-piece.origin，X=dot(offset,axis0)，Y=dot(offset,axis1)；
6. pack = `round(position*63/512 + 31.5)`，clamp0..63。

`SV_ShouldSendGlassImpact` 是 `lastStateChangeTime+1000 >= snapshotTime`，用 int64防溢出，含第1000 ms边界。

### 6.7 `SvGlassState`

状态：Pristine0、Weakened1、Destroyed2、Deleted3。

- set 要求 pieceIndex<1024、state<=Deleted；
- 有 impact 只允许 Destroyed，X/Y<=63；
- Pristine 从排序 vector 删除，其他状态插入/替换；
- pieceState 未记录即 Pristine；
- solid 当 state<Destroyed，即 pristine/weakened；
- nonSolidPieceCount 统计>=Destroyed。

### 6.8 `SvGlassDamageState`

`configure`：

- pieceCount<=1024；
- weaken非零；
- destroy!=0xFFFF；
- weaken<=destroy。

`damagePiece`：

- index有效、damage非零、threshold合法；
- damageTaken累加并饱和到 **65534**，0xFFFF留 deleted sentinel；
- 按 damageTaken 判断 pristine/weakened/destroyed；
- 只有状态变化才写 lastStateChangeTime=levelTime；
- 返回 stateChanged，不直接修改 wire/collision，提交仍由外层事务决定。

## 七、关键结论与未闭合点

1. Barrett port 的安全核心是**闭集和进程无关性**，不是素材能读就能直接 link。
2. AntiLag 的核心是**同 spawnGeneration + 有界插值**，不能用历史最新位置冒充命中时刻位置。
3. Client event 需要把“真实输入”“远端表现”“事务提交”分开；id错一位或改错环都会同时破坏战斗与表现。
4. Spawn 的 source/native 全等 round-trip 是强校验，但 unarmed 是唯一经过论证的例外，不能为图方便再把其它字段豁免。
5. Collision 的 absolute broadphase、packed solid、DObj narrow phase 是三层，不能用其中一个替代另两个。
6. 当前未闭合仍包括：特殊 offhand 原生 continuation、完整 script notification、精确第一 usercmd spawn顺序、共享 ammoIndex 的原生 give-ammo规则、glass 的完整原生 support graph/专用caller。

**本组9文件完成。下一步继续 Forge 与 ZM 系列文件。**
