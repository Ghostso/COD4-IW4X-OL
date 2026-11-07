# 140 · Lua/metadata、use、weapon movement、alpha weapons、const baselines

## 学习范围与读取完整性

本报告完整学习以下 **12 个文件**：

1. `sv_script_source_mp.hpp/.cpp`
2. `sv_splash_mp.hpp/.cpp`
3. `sv_use_object_mp.hpp/.cpp`
4. `sv_weapon_movement_mp.cpp`
5. `sv_alpha_weapon_port_mp.hpp/.cpp`
6. `sv_client_spawn_mp.hpp`
7. `sv_const_baselines_mp.hpp/.cpp`

其中 `sv_const_baselines_mp.cpp` 为 **902,974 B / 3,674 行**。先前端按250–300行连续读取至3674行，覆盖18张表的全部记录，未只读头尾。该文件是生成数据，本报告概括全表结构和差异，不把几千条坐标无意义地重抄一遍。

`sv_weapon_movement_mp.cpp` 的 ABI struct 声明位于其头文件，本组先读实现；相关原生布局会在后续读 `sv_weapon_fire_mp.hpp` 时继续串联。

## 一、Gameplay source 与 map metadata 是两条不同的 Lua 路径

### 1.1 选择名与大小限制

`SV_IsValidGameplaySourceSelection` 要求：

- 非空、最多64字节；
- 只允许 `_`、`-`、数字、英文字母；
- 不允许 `/`、`\`、`.`、空格，因此 map/gameType 不能逃逸预期目录。

`SV_LoadGameplaySource` 还要求 `maximumSourceBytes != 0`，默认 **1 MiB**，是拼接后所有源码及包装文本的总上限，不是每个文件各自1 MiB。

### 1.2 加载顺序和包装

候选顺序固定：

1. `common.lua`
2. `gametypes/<gameType>.lua`
3. `maps/<mapName>.lua`

不存在的普通文件跳过；`exists`/`is_regular_file`/打开/读取错误为 `ReadFailed`；超大为 `SourceTooLarge`；最后一个文件都没有为 `NoSource`。

每个文件被包成：

```lua
-- source: <relative>
do
<file bytes>
end
```

这样既隔离每份文件的顶层 `local` 和 `return`，又保留来源注释。`files` 记录 generic relative path；`sourceName` 是 `gametype/<type>/map/<map>`，用于后续 Lua runtime 标识，不是磁盘路径。

大小检查同时覆盖 fileSize、prefix、suffix 和已累计值，防整数回绕。读完后还核对 `source.size()==fileSize && !stream.bad()`，防止把截断读当完整源码。

### 1.3 `SV_LoadMapScriptMetadata` 单独执行 map Lua

它只读 `maps/<map>.lua`，在独立 Lua state 中执行，并要求返回 table；只取 `minimap_material` 字段。材质必须：

- Lua string，非空、长度<=255；
- 不含双引号、反斜杠和 NUL；
- 其他可打印/路径字符由当前规则原样接受，未额外限制为 `validName`。

`luaL_loadbufferx(...,"t")` 只允许文本 chunk，不加载二进制 bytecode。

### 1.4 资源限制

- Lua allocator 记账上限 **512 KiB**；
- instruction budget **100,000**；
- count hook 每 **1000** 指令触发。

Allocator 对 realloc 的 oldSize 按 pointer 是否存在记账；newSize=0 释放并扣旧值；增长若突破512 KiB返回null。增长前通过 `MapMetadataMaximumMemoryBytes - min(limit, usedBytes)` 计算余量，避免 unsigned underflow。

Instruction hook 在剩余 `<=1000` 时归零并 `luaL_error`，因此不会超过下一段1000指令。limits 指针存在 `lua_getextraspace`，close 在返回前执行。 metadata 不调用 `luaL_openlibs`，所以标准库并未在这里主动开放；它能执行的脚本环境比正式 gameplay state 更小，正式内建函数由 `sv_script_lua_mp.cpp` 另行提供。

**边界**：map metadata 返回 `nullopt` 同时覆盖“文件不存在”“选择非法”“太大”“读失败”“Lua错误”“未返回table”“材质非法”，调用方不能仅凭它区分这些原因。Appmain 另外用 `exists` 对比 `mapMetadata.has_value()` 来把“有文件但metadata失败”当 MiniMapUnavailable。

## 二、Splash：row 是本 build 的表索引，不是通用 medal enum

`SV_BuildSplashCommand` 仅格式化：

```text
w <slot> <row> <points>
```

客户端 `sub_C1C860` 从 `mp/splashTable.csv` 按 row 取显示时长（column4）和 icon（column11），slot 被客户端夹到0..4。

### 2.1 当前 wired 常量

| 名称 | row | points |
|---|---:|---:|
| announcer_line | 4 | 0 |
| headshot | 16 | 50 |
| revenge | 29 | 50 |
| first blood | 33 | 0 |
| first place kill | 38 | 0 |

默认 slot=0；callout slot=2。旧3.3.3.3 row 曾把 first blood 错发成 row32 multikill，本 build 已改33。

announcer_line 是空白展示槽，必须配合同帧高带 `p` 才有声音；单独发送 `w 2 4 0` 不显示也不发声。

### 2.2 队列和分数边界

- 同 slot 释放间隔 **1500 ms**；
- 队列上限 **8**，超过应丢弃并记录，而非静默截断；
- 同帧连发会覆盖前一个展示槽，所以不能按每次击杀直接全部发出。

points 是 banner 文本，不等于 scoreboard 实际得分。当前 headshot banner 可显示+50，但 `dm.lua` 不额外加这50；源码明确保留这个 seam，而不是把 points 改0掩盖。

### 2.3 未 wired 的触发不能臆造

- double/triple/multikill：没有可靠时间窗；demo 中2200 ms 两杀也没有 multikill，反驳直接搬4000 ms。
- longshot：距离阈值未定。
- buzzkill：需要 streak length。
- avenger/defender：需要双方伤害历史。
- destroyed_uav 和 callouts：对应实体尚不存在。

`SvHitLocationHelmet=1`、`SvHitLocationHead=2` 供 headshot 触发。该头文件也保留“名称表19项”的旧文字，但 `sv_damage_mp.hpp` 后续修正为20项（含shield）；报告以最新修正为准。

## 三、Use object：按已提交 usercmd 计算进度

### 3.1 定义和候选

- activate bit = **0x00000008**。
- definition 含 objectId、ownerTeam、allowedRelation、useDuration、requiresKeyObject。
- Any 关系不要求 ownerTeam，Friendly/Enemy 要求 ownerTeam 是 Tf/Sc。
- objectId 必须非零且全表唯一；`configure` 不接受空定义数组，失败时保留旧配置，成功时先 reset 再赋值。
- candidate 的顺序由调用方/native trigger ranking 决定，本系统不按距离重排。

队伍规则：

- Any：仅 Tf/Sc；
- Friendly：队伍必须等于 ownerTeam；
- Enemy：Tf/Sc 且不等于 ownerTeam；
- None/Spectator 不能操作。

`eligibleDefinition` 还要求 playing && alive && activate，candidate.insideTrigger，若 requiresKeyObject 则 candidate.hasKeyObject。

### 3.2 commandTime 去重

`processCommittedCommand` 只接 `commandTime > lastCommandTime`；等于或更旧直接忽略且不修改任何状态。`cancelClient` 允许等于上次时间的取消，但拒绝更旧；若更新则记录新的 lastCommandTime。

这意味着 complete/cancel 后再次以同一 commandTime 调用 process 不会重新开始。

### 3.3 Begin / Cancel / Complete

- 无合法 definition：取消现有进度并返回 Cancel（若有）。
- 切换到不同 object：先 Cancel 旧对象，再尝试 Begin 新对象，因此同一返回 vector 可能 `[Cancel, Begin]`，若 duration=0还可再 `[Complete]`。
- objectClaimants 确保同一对象同时只有一个 client；被别人占用时静默等待，不重置别人的进度。
- Begin 的 elapsed 默认0，start=last=当前 commandTime。
- 后续命令更新 lastCommandTime。
- `elapsed = current - start`，达到或超过 useDuration 即 Complete，清 claimant/progress。
- Cancel 的 elapsed 用 **lastCommandTime - start**，不是取消调用时的时间；取消事件自身 commandTime 仍是本次取消时间。

进度和 claimant 查询均返回 optional 拷贝，不暴露内部 map 引用。

## 四、Weapon movement：原生状态的构造、保存与输出验证

### 4.1 输入验证

`validFrameInput`：

- playerState 非空；
- xyspeed finite 且>=0；
- frameTime finite 且>=0；
- shellShockDuration/FadeTime>=0。

`validClientState` 要求 damagePitch/Roll、lastIdleFactor 和 base/recoil/sway 各向量都 finite。

这些是通用 builder 验证；头注释说明 native adapter 还可要求 frameTime非零、拒绝不支持的 shellshock，不能把 builder 接受视为原生函数一定接受。

### 4.2 两种 native state

`SV_BuildViewMovementState` 输出 viewState 所需：

- playerState bytes pointer；
- damageTime、time、damagePitch/Roll；
- xyspeed、frameTime、lastIdleFactor；
- 指向 `clientState.weaponIdleTime` 的指针。

`SV_BuildWeaponMovementState`  additionally 复制 baseAngles/Origin、recoilAngles/Speed、swayAngles/Origin/ViewAngles 和 shellshock 三字段。

指针指向 source-owned clientState，而不是临时 output 自己；后续原生函数可在其上读写。

### 4.3 Save-back 防 detached output

`SV_SaveWeaponMovementState` 要求：

- calculated state 的 playerState 和 weaponIdleTime 非空；
- xyspeed/frameTime 非负且 finite；
- shellshock 非负；
- 所有计算向量 finite；
- **`input.weaponIdleTime == &clientState.weaponIdleTime`**，防止把别处/悬空状态保存到本 client。

保存采用 `next=clientState`，更新 lastIdleFactor 和 base/recoil/sway，再验证后一次性赋值。`weaponIdleTime` 本身因原生已经通过指针修改而不需再复制。

`SV_IsWeaponMovementOutputValid` 最后只检查 viewAngles、weaponAngles 全 finite 和 gunPitch/gunYaw finite，是枪口角发布前的最低完整 guard，不验证其语义范围。

## 五、Alpha weapon port：11个目录项与完整字段 patch

### 5.1 血统分类

| alpha name | OLfinal source | lineage | network index |
|---|---|---|---:|
| `fal_mp` | `ff58_mp` | MeasuredDescendant | 1224 |
| `coltanaconda_mp` | `magnumncm_mp` | MeasuredDescendant | 1225 |
| `tavor_mp` | `tar21_mp` | CompatibilityAlias | 1226 |
| `masada_mp` | `acr_mp` | CompatibilityAlias | 1227 |
| `uzi_mp` | `miniuzi_mp` | CompatibilityAlias | 1228 |
| `m21_mp` | `m21ebr_mp` | CompatibilityAlias | 1229 |
| `glock_mp` | `g18_mp` | CompatibilityAlias | 1230 |
| `beretta393_mp` | `m93_mp` | CompatibilityAlias | 1231 |
| `beretta_mp` | `m9_mp` | CompatibilityAlias | 1232 |
| `deserteaglegold_mp` | `degold_mp` | CompatibilityAlias | 1233 |
| `barrett_heartbeat_mp` | `cheytac_mp` | ConvertedPresentation | 1234 |

`AlphaWeaponNetworkBaseIndex=1224`，`SV_AlphaWeaponNetworkAssetIndex` 按声明顺序计算。Dedicated 私建 registry 顺序可能不同，必须用 alpha name 重新翻译，不能直接把这个索引进程内通用化。

`MissingModelFamily` enum 存在，但当前11项没有该 lineage。

### 5.2 通用 tuning 与命中倍率

`SvAlphaWeaponTuning` 只携带已被消费的标量/数组，不携带 alpha 的 model/material/anim/sound 指针。OLfinal WeaponDef size = **0x101C (4124)**。

StandardHitLocations 共21项：index0=1.0，1/2=1.4，3..17=1.0，18/19=0，20=1.0。Barrett/M21 使用各自21项曲线。

所有11项 meleeDamage=135；每把枪的 ammo/damage/range/spread/fire timing 独立来自 alpha 0xC28 记录，而不是从 OLfinal descendant 继承。血统只决定被 clone 的指针资产和模型家族，tuning 要覆盖的字段由 patch 明确写出。

### 5.3 patch  offsets

| field | OLfinal offset |
|---|---:|
| name pointer | 0 |
| type/class/penetrate/impact/fireType | 1416/1420/1424/1428/1432 |
| startAmmo | 2016 |
| maxAmmo/shotCount | 2040/2044 |
| meleeDamage | 2072 |
| fireDelay | 2088 |
| drop/raise time | 2188/2192 |
| overlayReticle | 2348 |
| hipSpread[6] | 2384 |
| damage[6] | 3344 |
| damageRange[6] | 3368 |
| hitLocationMultipliers[21] | 3404 |
| clipSize | 3688 |
| fireTime | 3696 |
| aimDownSight byte | 3806 |
| ammoCountClipRelative byte | 3865 |

Patch 要求 definition span **恰好**0x101C 且 persistentNameAddress!=0，tuning valid。名称存储必须比 DB entry 长寿；linker 浅拷贝 pointer 成员。

### 5.4 tuning 验证

- type/class/penetrate/impact/fireType>=0；
- startAmmo>0、shotCount>0、meleeDamage>0、clipSize>0、fireTime>0；
- maxAmmo>=clipSize；
- damage/minDamage>=0，minDamage<INT32_MAX（因为后面写 minDamage+1）；
- fireDelay/drop/raise>=0；
- maxDamageRange>0，minDamageRange>maxDamageRange，且 minDamageRange<=StandardBulletRange；
- hipSpread finite>=0；
- 21个 hit multipliers finite 且0..20。

没有额外限制 fireType/weaponClass 的枚举上限；这些是已测源值输入，验证主要防内存/数值破坏而非完整语义审核。

### 5.5 六点伤害曲线如何保留 alpha 两点线性

写入：

```text
damage = { damage, minDamage, minDamage, minDamage, minDamage, minDamage+1 }
ranges = { maxDamageRange, minDamageRange, 0, 0, 0, StandardBulletRange+1 }
```

前两点保持 alpha 原线性衰减。尾部 guard 在普通 bullet 可达范围之外，避免浮点末端因几个 ulp 被截成 minDamage-1，并避开 retained routine 在最后 range 回退 damage[0] 的行为。

`ammoCountClipRelative=0` 必须清零，否则 descendant 的 clip-relative flag 会把已经是绝对发数的 alpha maxAmmo 再乘 clipSize。

`SV_StringTableHash` 是 ASCII 大写转小写后 `hash = hash*31 + lower`，用于 string table 第0列的文本指针旁缓存 hash；修改 alias model 表时文本和 hash 必须同步。

## 六、Client spawn 接口（本组头文件）

`SvClientSpawnConfig` 默认 gravity=800、speed=190、moveSpeedScale=1、maxHealth=100；含 clientNum/serverTime/origin/angles/ground/viewmodel/userCmd。

`unarmed` 是独立 spawn flag：仍先验证完整 loadout，但不装备它。这样 DMZ 空手不会被“空 loadout 非法”提前拒绝。

`unarmedWeaponAssetIndex` 可携带 `dmz_empty_mp`，因为 weapon0 没 viewmodel，会连手臂也没有；值为0保留旧的完全无手模型退化，不让资源缺失导致 spawn 失败。

`SV_ClientSpawn` 输出 source playerState + native playerState 的已确认子集，可传 `failureReason` 以区分失败位置；不是完整原生 ClientSpawn。`SV_EquipResolvedLoadout` 只做 source compatibility refresh，原生投影在下个 command boundary。

## 七、Const baselines：18张表的真实覆盖

文件头声明18张表，尾部 `Tables[]` 也是18项：

| map / gametype | entries | entity range | brush models |
|---|---:|---|---:|
| `zm_factory_sh/zm` | 397 | 37..699 | 238 |
| `zm_asylum_sh/zm` | 346 | 43..673 | 193 |
| `zm_prototype_sh/zm` | 234 | 38..451 | 121 |
| `zm_sumpf_sh/zm` | 275 | 37..670 | 172 |
| `mp_nuked/dd` | 108 | 79..689 | 38 |
| `mp_nuked/dm` | 100 | 177..685 | 37 |
| `mp_nuked/dom` | 130 | 174..688 | 50 |
| `mp_nuked/sd` | 137 | 174..689 | 53 |
| `mp_nuked/sr` | 137 | 174..689 | 53 |
| `mp_nuked/war` | 99 | 177..685 | 36 |
| `mp_nuked/cha` | 99 | 177..685 | 36 |
| `mp_nuked/tjugg` | 99 | 177..685 | 36 |
| `mp_nuked/conf` | 103 | 177..692 | 36 |
| `mp_nuked/tag` | 103 | 177..692 | 36 |
| `mp_nuked/hp` | 265 | 57..853 | 54 |
| `mp_nuked/borg` | 99 | 182..754 | 36 |
| `mp_nuked/chicken` | 99 | 177..685 | 36 |
| `coop_training_mp_cargoship/coop` | 700 | 37..823 | 217 |

**map+gametype 是联合键**。例如 nuked/dd 第一表不是 nuked/dm 的编号，不能按 map 单独复用。当前查找在精确 pair 未中时有 `mapOnly` fallback：返回该 map 第一张表（nuked 是 dd）。这意味着未知 gametype 会使用另一模式的 baseline；源码注释将其作为单模式地图便利，但对 nuked 多模式地图，调用方必须确保传入 engine 的正确 gameType，不能把 fallback 当无损。

`OLMOD_CONST_BASELINES=0` 完全关闭查询，恢复顺序编号和 flag0x10关闭。默认开启。

### 7.1 每条 entry 保存哪些 baseline 字段

`SvConstBaselineEntry` 含：

- entityNum、eType、brushModelIndex、xmodelIndex；
- solid、eFlags；
- origin/angles/scale 的 raw bits；
- field0058/00E4/0098/0070；
- position/angle trajectory type、time、duration、delta bits；
- surfType。

保留 float raw bits 是为了与 map parse 做精确相等，而不是 decimal round-trip 改变 delta。

Trajectory delta 不可省：Factory 475..480 的 zapper arms 在 trType1 下带线性速度/旋转。若服务端只对0做 baseline 比较而客户端继承非零 delta，实体会自行漂移/旋转。

### 7.2 brush 与 script model 的定位

- brush 用 `*N`/clipHandle 对 brushModelIndex，要求非零；直接线性扫描表，找到即 entityNum。
- script model 用 origin 三个 float 精确比较，要求 eType==6 且 brushModelIndex==0。
- 两函数都从 **slot1** 开始，故意跳过表 slot0。
- 唯一 origin 时可直接取 entityNum。
- 同 origin 多行时，以 xmodelIndex 做 tie-break；必须 **恰好一个** matching tieBreak，重复匹配会清零并最终 `nullopt`。
- xmodelIndex=0 时不能用于消歧。
- `SV_ConstBaselineScriptModelRowByOrigin` 只接受唯一 origin，>1直接null，用于测量双方 model band offset。
- `SV_ConstBaselineEntityState` 同样跳过 slot0，供 writer 找客户端实际会使用的 baseline。

### 7.3 slot0 的协议意义

客户端 baseline index array 以0表示无 baseline，guard `v2>0`，所以文件数组的第0项不能被引用。Factory slot0 entity37 在 demo 中按 zero baseline/eType0 到达，而不是按文件里 eType6。服务端若把 slot0 当真，就会与客户端使用不同 baseline，产生实际字段错误，不只是少省字节。

### 7.4 数据观察

- 不是所有 entry 都是 eType6；表中有 eType8（FX）、11（light）和个别 eType0记录。
- nuked 不同模式共享大量 map geometry，但 brush index、entity number、model band、trajectory、eFlags 和 light/FX 参数会变化，验证联合键必要。
- hp 有265项、最大 entity853，明显不是普通 dm 的100项子集。
- coop 有700项、最高823，包含大量 brush/actor presentation 数据。
- `solid` 不全为0或0xFFFFFF，flags 和 surfType 也真实变化；不能用简化三项 struct 重建完整 baseline。

## 八、跨文件结论与未闭合点

1. **资源执行必须分级**：metadata 的 Lua 是受限一次性求值，gameplay Lua 是三段包装的正式源，不可混用安全/生命周期假设。
2. **所有持续动作都应基于 committed command**：use object 拒绝重复/倒退 commandTime，weapon movement 以 source-owned candidate 保存，避免未提交输入产生副作用。
3. **alpha port 是“clone指针资产 + 覆盖已证标量”**，不是完整跨版本 WeaponDef memcpy。
4. **const baseline 是客户端共享真值**，不能只当压缩优化；错误的 map/mode/slot0 会直接改变模型、位置、碰撞和运动。
5. **mapOnly fallback 是多模式地图风险点**：后续必须核对调用方 gameType 已转 engine vocabulary，否则 nuked 非 dd 模式可能意外回落 dd。
6. `sv_client_spawn_mp.cpp` 的实际 spawn 事务、weapon movement 原生 ABI 和 `sv_script_lua_mp.cpp` 的 Lua builtins 是下一步必须接续的实现文件。

**本组12文件完成。继续 `server_mp` 后续 grenade/missile/radius/rewards/trajectory/wetwork 等文件。**
