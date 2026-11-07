# 141 · 投掷物全链、爆炸半径、奖励、轨迹与 Wetwork 场景

## 学习范围

完整阅读 `server_mp` 以下 **23 个文件**：

- `sv_grenade_detonation_mp.hpp/.cpp`
- `sv_grenade_explosion_mp.hpp/.cpp`
- `sv_grenade_launch_mp.hpp/.cpp`
- `sv_missile_mp.hpp/.cpp`
- `sv_missile_contact_mp.cpp`
- `sv_missile_flight_mp.cpp`
- `sv_radius_damage_mp.hpp/.cpp`
- `sv_radius_visibility_mp.cpp`
- `sv_rewards_mp.hpp/.cpp`
- `sv_trajectory_mp.hpp/.cpp`
- `sv_wetwork_scene_mp.hpp/.cpp`
- `sv_native_entitystate_mp.hpp`

Wetwork 的180条生成记录也全部顺序读完。报告按“发射→飞行→接触→爆炸→伤害/表现”串起来，避免只记 offsets 而漏掉时间语义。

## 一、轨迹：`SvNativeTrajectory` 36字节与防误调边界

结构：

```text
int32 type       +0
int32 time       +4
int32 duration   +8
float base[3]    +12
float delta[3]   +24
```

`static_assert(sizeof==36, base==12, delta==24)`。这是 plain trajectory，供保留原生 `0x410BD0` 使用；`0x410EA0` 是另一套 address-obfuscated base，不能混用。此记录放在 WorldClientState 外，避免 address-bound 原生布局被源对象大小改变。

### 1.1 `SV_IsTrajectoryValid`

- type 必须0..12；duration>=0；base/delta全 finite；
- type4/7/8 的 duration 不得为0，防止原生除零；
- `atTime - trajectory.time` 必须能装入 int32；
- type3/7/8 还要求 `trajectory.time + duration <= INT32_MAX`，因为原生有限轨迹会在 clamp 前做有符号加法。

注意 type3/7/8 没有要求 `time+duration >= INT32_MIN`；当前条件主要防正向溢出。

### 1.2 `SV_EvaluateTrajectory`

- evaluator 必须非空，先过上面的 guard；
- 复制 trajectory 后传给原生，防异常 callee 改所有者状态；
- point 预填 NaN，要求 callee 返回true且3分量都变 finite，否则 `nullopt`。

因此“原生未写输出”“部分写输出”“Com_Error/default分支前的非法输入”都不会被当成有效坐标。原生可能抛 `Com_Error` 的长期跳转仍需外层 native fault policy，单靠返回 guard 不能替代它。

## 二、手雷 WeaponDef 读取

### 2.1 Launch 参数 `SV_ReadGrenadeLaunchParameters`

要求 definition 至少 **3838 bytes**：

| 字段 | offset | 约束 |
|---|---:|---|
| weaponType | 1416 | 必须1（offhand/grenade） |
| offhand/slot/count field | 1436 | >0 |
| speed | 2616 | >0 |
| speedUp | 2620 | >=0 |
| fuseMilliseconds | 2284 | >=0 |
| cookOffHold byte | 3811 | 0/1 |
| timedDetonation byte | 3837 | 0/1 |

`weapon` 还必须非零且 `<=0x7FF`。`cookOffHold` 只是读取保留，不直接在本次 launch 公式中改时间；timedDetonation 决定 fuse 还是30 s cleanup。

### 2.2 Blast 参数 `SV_ReadGrenadeBlastParameters`

要求至少 **3834 bytes**：

- type1416==1、field1436>0；
- projExplosion +2660 ==0，限定普通爆炸，不允许 flash/smoke/heavy/knife 静默变普通伤害；
- stickiness +2680 必须0/1；
- cone float +2604 必须 **恰好180.0f**（当前只接纳已确认值，尽管后面计算支持 cone）；
- forceNormalUp +3833 必须0/1；
- radius +2588 >=0、inner +2596 >=0、outer +2600 >=0；
- weapon非零且<=MaximumWeaponAssetIndex；
- coneAngle 在0..180 finite。

`traceAlongContact = stickiness==1`，`forceNormalUp = definition[3833]!=0`。

## 三、发射 `SV_ComputeGrenadeLaunch`

输入还要求：

- basis 有效，basis.weaponAssetIndex==parameters.weapon，basis.weaponType==1；
- owner<2046、heldFuse>=0、toAngles非空；
- playerVelocity/angularVelocity finite。

### 3.1 初速度和角度

```text
toss = basis.forward * speed
toss.z += speedUp
speed = |toss|
delayValue = 85 - speed*35/600
delay = uint32(clamp(delayValue,20,50))
```

toss/angularVelocity 必须各分量落在 int32 可表示区间，speed finite且>0。`delayValue` 转 uint32 在 clamp 后执行，所以高速不会让负值下溢。

`m.position={type5,time=now,duration0,base=muzzleTrace,delta={}}`。角度先由 toss 方向计算，pitch/yaw 在0..360、roll必须0。若 rotate：

- angles.type=2（本 build linear，不能搬 BO1 的3）；
- time=now；
- base.pitch 减120，若<0则+360；
- delta=angularVelocity各项 trunc。

最终 `position.delta = trunc(toss) + inheritedProjection`，其中：

```text
direction = toss / speed
inherited = dot(playerVelocity,direction)
position.delta[i] = trunc(toss[i]) + inherited*direction[i]
```

这不是简单把玩家 velocity 全量相加，而是**把玩家速度投影到投掷方向后，再加到投掷速度的每个分量**。

### 3.2 launchTime 与 fuseDeadline 不同

- timedDetonation=true：`fuse = heldFuse!=0 ? heldFuse : definitionFuse`；PM 已经递减 cooked fuse，不能再减 hold。
- false：30,000 ms，是清理上限，不是爆炸承诺。
- lifetime=min(fuse,60,000)。
- launchTime = time+delay（表现延迟）；
- fuseDeadline = time+lifetime；
- 两个时间的较大者不得越过 INT32_MAX；
- 若 fuseDeadline 算成0，改30000，保留 InitGrenadeTimer 在 clock0 的 nextthink fallback。

`SvMissileSpawnRequest.initial.number` 按接口应为0，世界随后分配 generation-safe handle；本函数不消耗弹药，也不推进 RNG/计时器。

## 四、飞行步进 `SV_ComputeMissileFlightStep`

校验：

- atTime<=INT32_MAX、atTime>=lastUpdateTime；
- handle.entityNum==network.number；
- 当前 missile 能成功投影；
- currentOrigin finite。

在同一个 atTime 分别评估 position 和 angles，**不截到 fuseDeadline**。destination 是轨迹目标，currentOrigin 是上次已提交点，两者不能混。

step 初始：

- origin=currentOrigin；
- angles=评估角；
- fuseDue = `fuseDeadline!=0 && fuseDeadline<=atTime`。

若位移 `<0.001`：不做 trace、不更新 origin，但 fuseDue 仍可触发 think，静止雷能到期。

### 4.1 trace 修正与时间

- provider 必须存在；fraction0..1，不能 `allSolid && !startSolid`；
- startSolid：fraction改0，normal设为 `-delta/distance`；
- fraction<1 时 normal 长度平方必须接近1（误差<=0.02），且 entity hitId<=2047；
- impactTime = `lastUpdateTime + min(elapsed, uint32(elapsed*float(fraction)))`；
- fraction==1 时 origin=destination，否则 current+delta*fraction。

`impactTime` 使用浮点 fraction 后 trunc，随后 clamp 到 elapsed；它可能比精确有理数少1 ms，这是当前实现选择的原生形状近似。所有 step 结果只计算不发布，impact 要先于 fuse 完成 continuation。

## 五、粘附世界 `SV_StickMissileToWorld`

额外要求：

- step.impact 存在；
- network.position.type 非零；
- missile fuseDeadline/step atTime/impactTime 都<=INT32_MAX，且 impactTime<=atTime，二者>=lastUpdate；
- impact fraction `0<=f<1`；
- 不能 allSolid&&!startSolid，不能 surfaceFlags&4；
- hitType==0 或 `TraceHitTypeEntity && hitId==world(2046)`，其他实体不走本 world-stick；
- normal长度平方误差<=0.02。

结果：

- runtime origin=step.origin；
- runtime angles=**原 network.angles.base**，不是本帧 spin 评估值；零售 Semtex stop 保持发射模型角，网络 spin 是客户端表现；
- `network.position={0,0,0,step.origin,{}}`；
- `network.angles={0,0,0,originalAngles,{}}`；
- ground=world；
- surfaceType=(surfaceFlags>>20)&31；
- timedDetonation=false 时 fuseDeadline=0，否则保留原 fuse；
- contactNormal=trace.normal。

若 `!startSolid`，追加 event95（stick）到 `events[eventSequence&3]` 并 eventSequence+1；startSolid 抑制 contact event 但仍完成停止。方向 byte 必须<162。注释还列出本 build：94 bounce、95 stick、96 rest。

## 六、Missile 网络投影

`SvMissileNetworkState` 是 world-side 独立结构，不嵌入 client/native image。`SV_ProjectMissileEntity` 要求：

- number37..2045；
- weapon1..0x7FF；
- owner/ground<=2047；
- eFlags<=0x3FFFFFFF；
- surfaceType<=31；
- scale finite>0；
- 4个 events 全有效；
- position/angles trajectory 有效。

映射到 `SvEntityState`：

- eType=4 missile；
- owner→otherEntityNum，ground→groundEntityNum；
- origin/delta/type/time/duration 分 position 和 angles；
- modelScale、launchTime→lerpData0058、surfaceType→impactSurfaceType；
- eventSequence/events 原样；
- `scriptMoverField00E4=0`，其它 stale union 字段由默认 entity 初始化。

`SV_IsMissileEntityValid` 重建 network state 再投影，要求 **完整相等**，所以能拒绝截断和属于其他 eType 的残留字段，不只检查 eType。

## 七、普通干爆 `SV_ComputeDryGrenadeDetonation`

前置约束：

- parameters 有效且与 missile.weapon一致；
- handle number一致、generation非零；
- missile projection成功；
- fuseDeadline非零，request.time>=fuseDeadline 且>=lastUpdate；
- request.time<=INT32_MAX；
- weaponName 1..127字节且无 NUL；
- surfaceTraceMask/radiusTraceMask 非零；
- surfaceTrace/encodeDirection 必须存在；
- targets<=18、ignoreClientNum<18；
- targets clientNum唯一，spawnSequence 按 client 记录。

“dry”由调用方先确认不在水中，本函数不替它做水域判定。

### 7.1 爆炸点和表面

1. 在 **当前 request.time** 求 position，而不是 fuse 时刻；
2. 每分量检查 int32 范围并 `trunc`；
3. 若 traceAlongContact 且 ground!=none：contactNormal 必须单位（误差1e-4），end=origin-normal*16；
4. 否则 end=origin-(0,0,16)；
5. surfaceTrace 用 CollisionOnly、passEntityNum=missile.number；
6. fraction0..1、normal finite；
7. forceNormalUp 时 normal={0,0,1}，否则 trace.normal；
8. direction=encodeDirection(normal)，必须<162；
9. effect={origin,weapon,direction,surface=(flags>>20)&31}，weaponName原样带上。

这个 surface trace 只选效果表面/法线，**不把 radius-damage origin 移到 trace 命中点**。

### 7.2 伤害

若 `innerDamage==0`，直接返回只有 effect，不调用 radius damage。

否则 blast 请求：origin=整数爆炸点、radius、inner/outer、inflictor=missile.number、ignore、mask。

cone<180 时必须 anglesToForward，评估当前 angles，cone={cos(degrees),forward}。虽然参数 reader 当前只接180，底层支持未来已证其它角度。

调用 `SV_ComputePlayerRadiusDamage` 后：

- 任一 hit.shieldProtection!=0：整个返回 `nullopt`，因为 shield feedback/flags continuation 未实现，不能假装普通伤害；
- damage<=0 跳过；
- 其余构造 player payload：damageFlags=5、MOD_GRENADE_SPLASH、weapon、point=origin、direction=hit.direction、multiplier1；
- 每个 damage 带 spawnSequence 和 hit.spawnGeneration，供 world 在提交前重新核对生命所有权。

## 八、半径伤害算法

### 8.1 输入和基础衰减

- origin/radius/inner/outer 检查 finite；inner/outer在 `[0,2^31)`；
- contentMask必须非零；
- inflictor<2048、ignore<18、targets<=18且client唯一；
- bounds/halfSize有限且非负，shieldProtection在0..1；
- cone angleCos在[-1,1]，若不是-1，direction必须单位（1e-4）。

`radius=max(1,request.radius)`。每个轴到 AABB 最近距离：

```text
separation[axis] = max(0,
    abs(blast[axis] - bounds.midpoint[axis]) - bounds.halfSize[axis])
```

`distance=|separation|`，若 `distanceSquared >= radiusSquared` 排除，**正好外沿无伤害**。

未遮挡衰减：

```text
damage = (inner-outer)*(1-distance/radius)+outer
```

### 8.2 五点暴露

- horizontal = blast-target.origin，z=0，normalize；若重合保持零向量；
- midpoint=(origin+eye)/2；
- halfHeight=(eye.z-origin.z)/2；
- lateral=(-horizontal.y*15,horizontal.x*15,0)，固定15单位，不取碰撞半宽/站高。

五点：

1. midpoint；
2. midpoint+lateral+halfHeight.z；
3. midpoint+lateral-halfHeight.z；
4. midpoint-lateral+halfHeight.z；
5. midpoint-lateral-halfHeight.z。

每个点若 cone 启用，先算 point-blast 并 normalize，dot<angleCos 则跳过，不消耗 trace。其余必须 tracePassed 存在；provider 返回 `optional<bool>`，null 表示不可用，整次计算失败，false 是遮挡。

`exposure=min(1,visible/3)`，所以3/5已经全暴露。最终：

```text
scaled = damage * exposure * (1-shieldProtection)
result.damage = int32(scaled)  // trunc，非四舍五入
```

`result` 保留所有 in-radius非ignored目标，包括0伤害，供 shield feedback；direction=target.origin-blast，再加 z24，不归一化。

## 九、Radius visibility 的两层排除

`SV_IsRadiusDamageTraceRequestValid` 要求 start/end finite、mask非零、target<18、inflictor<2048。

`SV_TestRadiusDamageVisibility`：

1. 校验 entity 列表<=MaximumServerCollisionEntityNum+1，每项合法且无重复；
2. 先跑 worldAndStaticModels；false 直接遮挡，null 直接不可用；
3. 遍历 linked 且 contents&mask 的实体；
4. 排除 target 和 inflictor；
5. **也排除 ownerEntityNum 等于 target/inflictor 的实体**；
6. broadphase 不命中则跳过；
7. 对候选调用 entityTrace，false遮挡，null不可用；全过才true。

这里第二个排除不是普通 `passOwnerEntityNum` 的同义词。G_LocationalTracePassed/SV_PointSightTraceToEntity 要同时忽略目标、inflictor及其拥有实体。

## 十、Grenade explosion 表现实体

`SV_ProjectGrenadeExplosionEntity` 要求：

- entityNum37..2045；
- weapon有效；
- direction<162、surfaceType<=31；
- origin 每分量 finite 且 `v==trunc(v)`，确保干爆的整数位置。

以 zero baseline 填：

- eType=0（ET_GENERAL）；
- eFlags=16；
- origin、weapon、impactSurfaceType；
- modelScale=1；
- eventSequence=1；
- events[0]={98,direction}。

其余字段保持零，符合零售 Semtex 十二效果的记录。`SV_IsGrenadeExplosionEntityValid` 先查 parameter<162，再完整重建比对，防多余字段/不匹配。

## 十一、奖励：earning、grant 与 profile cost 是三层

### 11.1 `SvUavEarningState`

字段：owned、life、grantedLife、earnedThisLife。

`observe(generation,alive,eligible,streak,threshold)`：

- !alive：life/grantedLife reset、earned=false，owned保留；
- generation改变：换 life，grantedLife reset、earned=false；
- eligible && !earned && streak>=threshold && owned!=UINT32_MAX：`owned++`、earned=true。

只负责每命 earning，不直接发物品。grantedLife 字段本函数没写，是供 grant owner 防重复授予的另一阶段。

### 11.2 `SV_GrantUavWeapon`

校验：

- weapon/ammo index 1..2047；
- clipIndex 1..2046；
- clipCapacity 1..511。

对 state 做 copy：

- held 先找同 weapon，否则空槽；
- clip 先找同 clipIndex，否则空槽；
- pool 先找同 ammoIndex，否则空槽；
- 三者任一没有可用槽则整体失败，不写原 state。

成功后：

- held 只写 weaponAssetIndex，flags/tail零；
- clip.count={1,0}；
- pool.count=0；
- rewardActionType=1、rewardActionWeapon=weapon。

保留引用样本只证明库存形状，不证明该快照时刻确实 earned；earning owner 仍须防重复。

### 11.3 `SV_ResolveProfileRewards`

3个 profile item：

- item<=1 是空槽，跳过；
- item>65535整批失败；
- lookup(item-1)；
- reward必须存在、runtimeId 1..255、normal/persistent cost都<=31；
- 失败不能通过 `atoi("")=0` 变成合法0成本奖励。

`SV_EquippedRewardTargets`：

- shift 必须 finite、整数值、-100..100；
- 只对 runtimeId!=0 的槽计算 cost+shift；
- target 0..31，runtimeId<=255；
- 返回 id/target 的8位对。

选择/cost 与角色 modifier/grant/spend 分离，不在此实现。

## 十二、Wetwork 场景不是 const baseline 的替代品

`SV_WetworkInitialScene()` 返回生成数组，记录来自 `C-2021-7-25[22-11-33]coop.demo` admission snapshot serverTime 10250。

- const fastfile 有700项、最后 entity823；
- 此数组另含 **180 个 full-state ET_SCRIPTMOVER**；
- 它们从 entity824 起，但不连续，后续有967、1330、1331、1383..、1765..1776等；
- 全部记录 eType6，brush index 0或229..278，model index包括320/382/383/384/386/389/398/415/417/270/284/285/290/295/121等；
- 这是任务自有 movers 的**已传输全状态**，不是客户端 `_const.ff` baseline。

类型复用 `SvConstBaselineEntry` 只是因为字段子集相同。不能把180行塞回 const baseline 查表协议，也不能假设客户端会脱离服务器自行拥有它们。

## 十三、Native entityState 的 build-specific 约束

`SvNativeEntityState::Size = 0x118`，比旧0x110多8，alignas uint32。还携带 `secureOriginAddressBound` 元数据，不属于原生 ABI。拷贝/移动自定义，说明地址绑定状态不能只按 bytes 复制语义。

`SvEntityEventCount=170` 是**有参数宽度声明的事件数**，不是 event id 上限。event id 本身 codec 是 raw byte，所以 `SvMaximumEntityEventId=0xFF`；超出宽度表的事件参数宽为0，不应按170拒绝整个 snapshot。

`MaximumEntityAnimationIndex=0xFFF`，本 build legs/torso 各12 bit，在 native entityState 0xDC/0xE0。旧0x7FF 会错误拒绝2048/2796。

Projection 中需特别保留：

- unk00A0 是28-bit域，用32-bit存储；
- presentationWeapon/offhandWeapon/coKnifeStatsIndex 是不同概念；
- unk00E0 整个 dword 保留，不只 dirty byte；
- `SV_ReadNativeEntityState` 可选 originKeys 验证 address-bound origin。

`SV_ResetNativeEntityState` 只创建 unbound bootstrap，注释明确 TODO：完整 ClientSpawn→ClientEndFrame/native conversion 顺序未闭合，不能把 bootstrap 在首次正式转换前当完成状态发布。

## 十四、全链关键不变量

1. **时间有三种**：发射表现 delay、当前帧轨迹求值、引信/cleanup deadline；不能互相代替。
2. **runtime origin 与 network trajectory base 分离**：自由飞行改 runtime，不 rebase network；粘附时才把 network type/position定格。
3. **每个副作用都是事务结果**：flight step、stick update、detonation 都是 immutable candidate，world 只有在 mirror/removal能提交时才发 visual/script damage。
4. **trace 不可用不是“通过”**：所有 `optional<bool>` 的 null 都 fail closed，只有显式 true 才是 clear。
5. **普通爆炸不覆盖特殊机制**：flash/smoke/heavy/knife、shield、water、player/mover attachment 都有单独 continuation，不能落进普通 Semtex 路径。
6. **生成表与线格式必须同 build**：trajectory type、animation width、event id/width、entityState size 都要按1649370，不搬旧 ordinal。

**本组23文件完成。下一步继续 alpha Barrett、antilag、client events/spawn、collision 与 Forge。**
