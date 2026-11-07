# 144 · ZM/Factory 子系统（上）：弹药、屏障、翻板飞行、箱子、门、地面、伤势、前瞻、特权机、电力、复活、表现、翻窗、房拓扑、导航图、特种武器、传送器

## 一、范围

本报告完整学习 **23 个文件**：

- `sv_zm_ammo_mp.hpp`
- `sv_zm_barrier_mp.hpp`
- `sv_zm_board_flight_mp.hpp` + `sv_zm_board_flight_table_mp.cpp`
- `sv_zm_box_mp.hpp`
- `sv_zm_door_motion_mp.hpp`
- `sv_zm_ground_mp.hpp`
- `sv_zm_injury_mp.hpp`
- `sv_zm_lookahead_mp.hpp`
- `sv_zm_perk_machines_mp.hpp`
- `sv_zm_power_motion_mp.hpp`
- `sv_zm_revive_mp.hpp` + `sv_zm_revive_hud_mp.hpp`
- `sv_zm_presentation_mp.hpp`
- `sv_zm_window_motion_mp.hpp`
- `sv_zm_factory_room_patch.hpp` + `sv_zm_factory_room_data.hpp`（片段）
- `sv_zm_navgraph_mp.hpp`
- `sv_zm_special_mp.hpp` + `sv_zm_special_policy.hpp/.cpp` + `sv_zm_special_world_mp.cpp`（片段）
- `sv_zm_teleporters_mp.hpp`
- `sv_zm_travel_mp.cpp`（片段）

`server_mp` 进度推进到 **92/154**。

## 二、总原则：ZM 侧几乎全部是"重建策略"，不是原生恢复

这批文件与 MP 侧（事件 id、字段偏移、线格式）性质完全不同。反复出现的标注是：

- `OLMOD(...)` = 本项目重建的**源侧策略**；
- `CODREF(...)` = 本 build 客户端里实测到的原生事实（地址 + 行为）；
- `TODO(CODOL)` = 原生 owner 尚未恢复，明确不做承诺。

**凡涉及"多少个电池""多少毫秒""多少概率"的数值，几乎全是重建，不是零售值。** 这一条必须记住，否则会把它当成"官方行为"去对照。

## 三、Factory 弹药机：按住 2 秒 + HUD 双条

`SvFactoryAmmoHold`：

- `update(held, eligible, target, life, now)`；
- 未按住 ⇒ 整个状态清零；
- `life`（生命代际）变化 ⇒ 整清零；
- 已完成 ⇒ 直接返回 false，不会重复给；
- 不 eligible ⇒ `active=false`，不重置 completed；
- 若 `!active || target 变化 || now-lastSeen>500` ⇒ 重新计时；
- 到达 **2000 ms** ⇒ `active=false, completed=true`，返回 true（一次）。

`SV_BuildFactoryAmmoHud` 出两个 HudElem：

| 元素 | origin | 尺寸 | material | alignOrg | alignScreen | sort | 动画 |
|---|---|---|---|---|---:|---:|---:|---|
| fill | (-60,94,0) | 120×9 | materials[0] | 1 | 0x99 | -2 | `setIconSizeAnimation(3,9,startedAt,2000)` |
| background | (0,94,0) | 120×9 | materials[1] | 5 | 0x99 | -3 | — |

两者 `targetEntNum=2047`（世界锚定）、颜色白。填充条按 `startedAt` 做宽 3→9 插值。

## 四、翻板屏障：三车道 × 六块板，逐窗所有权

`SvZmTearClip{animation, boardMilliseconds, endMilliseconds}`：

- `animation` 1..4095；
- `boardMs > 0`；
- `endMs >= boardMs`。

`SV_ZmTearClipFromMarkers` 用**单精度 `std::ceil`**，注释明确记录：把 `1.7f` 先提升为 double 再缩放会得到 `1700.000047 → 1701`，凭空多延迟一个服务器 tick。

`SvZmBarrierController` 状态：

- `lanes_[3]`：三个 `optional<SvZmTearLease>`；
- `released_[6]`：六块板是否已释放；
- `serial_`：单调序号。

`acquire` 拒绝：

- lane≥3、board≥6、clip 无效；
- `actor.entityNum >= EntityNumWorld`；
- 该 lane 已占用、该 board 已释放；
- 任何 lease 同 actor 或同 board（**一个演员同时只能撕一块**）。

`releaseDue` = 拥有该 lease && 该板未释放 && `elapsed >= boardMs`。

`acknowledgeRelease` 只做状态置位；`commitRelease` 是**带回滚的事务版本**：

```text
if (!releaseDue) return false;
if (!commitMotion()) return false;   // 原生笔刷事务失败 ⇒ 状态不变
return acknowledgeRelease(...);
```

`finish` 要求已 released 且 `elapsed >= endMs`，然后释放车道。

`cancel(actor)` 释放该演员的车道，但**已 released 的板保持 released**——杀掉正在撕板的僵尸不会让已开始飞行的笔刷复位。

`restore(board)` 只在该板已 released 且**没有任何 lease 正在占用该板**时才允许，避免修复动作把正在被撕的板抢回去。

`elapsed` 在 `now < started` 时返回 0，注释写明"时钟重置不能把旧 lease 变成立即释放"。

### 4.1 翻板飞行：实测坐标，不是通用求解器

`SvZmBoardFlightProfile{barrier, slot, launchPosition, launchAngles, restPosition, restAngles}`，`at(releaseTime, now)` 的拒绝条件：

- `now` 超过 int32 上限、`now < releaseTime`；
- `launchPosition.time != 0` 或 `launchAngles.time != 0`（发射相位必须从 0 起）；
- `restPosition.time <= 0`；
- `releaseTime + max(restTimes)` 溢出 int32。

判据：

- position：`elapsed >= restPosition.time` ⇒ 用静止位姿（类型 0），否则发射位姿；
- angles：`elapsed >= restAngles.time` ⇒ 静止角度（类型 0），否则发射角度；
- flags：落地 17，飞行中 1；
- 两条轨迹的 `time` 各加 `releaseTime` 重定基；
- 最终两条都必须通过 `SV_IsTrajectoryValid`。

### 4.2 生成的表内容（节选，共 48 条 profile）

表由三份 Factory demo 生成（`generate_board_flights.py`），每条注释都带 demo 文件与源实体号。观察到的结构：

- 每个 `pf6xx_auto1` 有 6 个 slot；
- 位置轨迹多为类型 **5**（发射）、类型 **0**（静止），时长 450..1700 ms；
- 角度轨迹多为类型 **7** 或 **3**（角速度/线性停止），静止角度类型 0，时长 216..1600 ms；
- 静止位姿 z 常落到负值（如 `-361`、`-357`），说明板是往下掉的。

样例（`pf678_auto1` slot 1/entity 105/release 618300）：

```text
launch pos {5,0,0,{398,-104,147}}
launch ang {7,0,470,{0,0,0},{127.534698486,0,0}}
rest   pos {0,950,0,{570,-104,60}}
rest   ang {0,1000,470,{90,0,0},{127.659576416,0,0}}
```

注意 rest angles 的 `base` 是 90/−180，而 launch 的 `delta` 是 0 —— 说明**角度靠类型 7 的角速度走到 90/−180，再由类型 0 的绝对角锁住**。

## 五、神秘箱：七阶段状态机

`SvFactoryBoxPhase`：`Closed → Rolling → Offer → Closing → Bear → Departing → Relocating`。

`SvFactoryBoxRuntime` 关键字段：

- `sites`（多个刷新点）+ `active` 当前点；
- `seed0x9e3779b9` / `previewSeed`；
- `life`（生命代际）、`offer`（当前报价 asset）、`rewardKind`（Weapon / Ammo）；
- `display` + `effectCarriers[2]` + `poof`；
- `teslaViewSlots[3]`；
- `pulls` / `moves` / `bearRoll`；
- `movingPieces[2]`。

`SvFactoryBoxResources` 里有两处值得注意：

- `weaponBases`："**所有已发布别名，包括被从报价池中剔除的重复项**"——说明同一个 base 可能以多个 asset 号出现；
- `reconstructedPool`：明确标记"池是重建的"。

辅助函数分工：

- `SV_FactoryBoxBearRoll(paidPull, moves, random)` —— 注释写"BO1 参考策略，**不是**恢复的 CODOL 掉落概率"；
- `SV_FactoryBoxNextSite(active, count, random)`；
- `SV_FactoryBoxDisplayOrigin(resources, asset, site)` —— 模块化枪体用**箱盖**的纵向轴，熊奖励用武器刷新点标记轴（`rewardAngles`）；
- `SV_FactoryBoxRise(origin, started, now)` —— 上升轨迹；
- `SV_StartFactoryBoxFx` / `SV_StopFactoryBoxFx`；
- `SV_FactorySoundAliasSlot(slots, name)`。

## 六、门运动：14 条实测 profile，全部绑定 `zm_factory_sh`

`SvFactoryDoorMotionProfile{brush, target, phases[4]}`。每个 profile 固定四相位：

| 相位 | 类型 | time | duration |
|---|---|---:|---:|
| 0 | 7（加速） | 0 | 250 |
| 1 | 3（线性停止） | 250 | 500 |
| 2 | 8（减速） | 750 | 250 |
| 3 | 0（静止） | 1000 | 250 或 500 |

`SV_FactoryDoorMotionProfile(map, brush, target, origin)` 的准入是**三重精确匹配**：

1. `map == "zm_factory_sh"`；
2. `brush` 相等；
3. `target` 字符串相等；
4. `phases[0].base == origin`（逐 float 全等）。

任何一项不符返回 0（无 profile）。注释说明这是为了"保护无关地图与被移动/替换的物体"。

`SV_FactoryDoorTrajectory(profile, start, now)`：按 `elapsed` 选相位（≥1000 → 3，≥750 → 2，≥250 → 1，否则 0），再把 `time` 加上 `start` 重定基。

14 个 profile 覆盖：`warehouse_garage_door`×2、`wnuen_outside_door`×2、`outside_west_door`、`outside_south_east_door`、`outside_south_west_door`、`tp_east_door`、`outside_east_door`、`south_courtyard_door`×2、`tp_west_door`×2。位移多为水平 15..118 单位，其中两条是**垂直下降**（`outside_south_east/west_door`，z 102→-1 / 110→7）。

## 七、地面步进：三个函数，各有明确边界

### 7.1 `SV_ZmWindowOwnsGroundTransition(from,to,outside,inside,passed)`

```text
return !passed && from == outside && to == inside;
```

注释："窗口所有权跟随**当前有向腿**，含重规划后的游标零；重规划前缓存的标志不能建立该所有权。"

### 7.2 `SV_ZmUnsupportedGroundTransition(assignedWindow, hasMotion, authoredNegotiation, heightDelta, arrivalHeight)`

```text
return !assignedWindow && !hasMotion &&
    (authoredNegotiation || |heightDelta| > arrivalHeight);
```

即：没有指派窗口、没有运动轨迹，且（是作者化协商 **或** 高差超过到达阈值）⇒ 不支持的地面转移。

### 7.3 `SV_ZmResolveGroundedStep(previous, proposed, traceStartZ, traceEndZ, ground)`

- ground 有效（非 allSolid、非 startSolid、fraction<1）⇒ `proposed.z = lerp(traceStartZ, traceEndZ, clamp(fraction))`；
- 否则 **返回 previous**（保留原位），注释写明"普通行走在这里没有空中/重力 owner，所以地面查询失败不能授权走向空处"。

### 7.4 `SV_ZmRetrySupportedStep`

常量：`Skin=0.25`、`StepHeight=18`、`GroundDepth=72`。

拒绝条件（任一）：

- 平面位移 < 0.001（没有水平移动）；
- 上探 trace 无效；
- `rise <= Skin`；
- 跨步 trace 未完全空（fraction<1）；
- 下探 trace 无效、fraction≥1（没打到地）、`normal[2] < 0.7`（太斜）；
- 落点 z 超出 `[previous.z-72, previous.z+18]`；
- 落点处自身不空。

关键在于：**不能忽略 startSolid，也不能把目标抬穿天花板**——必须按"上 → 跨 → 下"三段从上一个有支撑位置重新验证。

## 八、僵尸伤势环：8 槽、4/4/12 位

`SvZombieInjury{sequence, style, entity}`：

- `sequence` 4 位（0..15）；
- `style` 4 位（0..1，1 = `zombie_claw%d`）；
- `entity` 12 位（<2047）。

`SvClientZombieInjuries` 含 `clientNum`、`spawnSequence`、`spawnGeneration`、`cursor`、`records[8]`。

`SV_AppendZombieInjury`：`actor<2047`、`cursor<8` 才写；写入 `{record.sequence%15+1, 1, actor}` 后 cursor 循环。

`SV_WriteZombieInjuries` 是增量编码，每条：

```text
MSG_WriteBits(1,1)           // 还有一条
MSG_WriteBits(i,3)           // 槽位 0..7
MSG_WriteBits(sequence,4)
MSG_WriteBits(style,4)
MSG_WriteBits(entity,12)
... 最后 MSG_WriteBits(0,1)
```

注释关键："与 playerstate 在同一已确认不可变帧；显式零值清除旧生命/旧主体；重复包不会产生额外命中。"

## 九、路径前瞻：面积增长/衰减，不是固定前视距离

`SvZmAreaLookahead`：

- 初始面积 **21845.334**（BO1 `Path_Begin`）；
- 清晰 ⇒ `area = min(area*1.1764705 + 6.4, 65536)`；
- 受阻 ⇒ `area = max(maximum * (prevClear ? 0.75 : 0.5625), 0.001)`；
- 若 `completed` ⇒ `area = min(area, max(consumedArea, InitialArea))`。

`SV_ZmAreaLookaheadTargetForRoute` 的边界：

- 最多 **32 个节点**；
- 总前视距离 **192 单位**；
- 高差 > 8 单位即中断；
- 面积预算按 `height * travel` 消耗（height = 点到当前腿的垂距）。

`SV_ZmPassedLookaheadPlane`：要求方向长度² > 0.001、前向投影 ≤ 0、高差 ≤ 8。

## 十、特权机：四台、按已购数量计价

四个位：`Armor = 1<<22`、`Revive = 1<<23`、`Reload = 1<<24`、`Rof = 1<<25`。

`SV_FactoryPerkTriggerAt`：

- 只对 `zm_factory_sh` 生效；
- 只认 `targetname == "zombie_vending"` 且 `noteworthy ∈ {specialty_fastreload, specialty_quickrevive, specialty_armorvest, specialty_rof}`；
- **XY 各加 12 单位 reach**（实测碰撞让接近点落在作者体积外 6..11 单位）；
- 在命中体积的候选里取 XY 距离最近者。

`SV_FactoryPerkPriceUnits(perks)`：

```text
2 + popcount(perks & FactoryMachinePerks)
```

即 0 台 2 电池、1 台 3、2 台 4、3 台 5、4 台 6。注释写明：原始 Factory 观察到 2/3/4 配 0/1/2 台，**第四价 5 是外推**。

`SV_ApplyFactoryPurchasedPerks`：

| 位 | ability id | slot | base | delta |
|---|---:|---:|---:|---:|
| Reload | 1 | 1 | 1 | +1 |
| Rof | 23 | 12 | 1 | +1 |
| Armor | 104 | -1 | 100 | +150 |
| Revive | 105 | -1 | 1 | +2 |

`add` 逻辑：若已拥有则从 `resolvedValues[id]` 起算，否则从 `initial` 起算；结果 clamp 到 ≥0；置 mask 位；写 `resolvedValues[id]`；`slot>=0` 时同时写 `values[slot]`。

`Revive` 明确带 TODO：**原生 reviveRate 存下来了，但合作倒地交互 owner 未恢复，不得声称单人自救可用**。

## 十一、电力：实测相位 + 蒸汽事件

`FactoryPowerDuration = 4000`；`FactorySteamConfigString = 11992`；`FactorySteamEventParameter = 2`。

`SvFactoryPowerPiece{number, brush, clipAt, origin, raised, phases}`，9 个：

- 494/495：南东/南西门，四相位垂直下降；
- 344：一段 300 ms 的小抬升（z +6）；
- 473/474：左右两侧的**旋转门**（位置不变，angles 类型 7→3→8→0，±90 → 0），时长 4000；
- 481/482：clipAt=4000，空 phases（纯碰撞开关）；
- 343：空 phases。

`SV_FactoryPowerPose(piece, epoch, now)`：

- 默认 `pos{0,0,0,origin}` / `ang{0,0,0,raised}`；
- 遍历 phases，起点取 `brush==169||170 ? v.angles.time : v.position.time`；
- `start > now-epoch` 之前的所有相位都被采用；
- 最后 `pos.time += epoch`、`ang.time += epoch`。

注释关键一句：**"phase.time 是原生轨迹起点，`v.at` 只是首个收到快照的时间；投递延迟不是运动暂停。"**

## 十二、复活/倒地

常量：`SvPmTypeZombieDowned = 7`（`PM_CheckDuck` 417D10 对 pm_type 7 强制趴下）、`SvZombieReviveMilliseconds = 4000`、`SvZombieBleedoutMilliseconds = 45000`、`SvZombieReviveRadius = 72`。

`SvZombieDownedState` 字段：`generation / downedAt / round / weaponAssetIndex / bledOut / scoreRecorded / reviver / reviverGeneration / startedAt / lastSeen / duration`。

注释明确警告：`593FED`/`7BDCE0` 的 bit `0x100000` **不只是隐藏视模型**，它还进入一个锁定实体的资产消费者，所以不能当"只隐藏"用。

### 12.1 复活 HUD

`SV_BuildZombieReviveMarker(client, treating, materials)`：

- `type=Waypoint`、`targetEntNum=client`、material 按 treating 取 0/1；
- 16×16、颜色 `0xC833FFFF`、`value=1.0`、`flags=0x408`。

`SV_BuildZombieTreatmentHud(down, now, recipient, materials)`：

- 只在 `*down.reviver == recipient`、未 bledOut、`now-lastSeen<=500`、`duration != 0`、两材质均非零时出；
- 前两个元素复用弹药条（fill/background），并把动画时长改成 `down.duration`；
- 第三个是文本：origin (0,80,0)、白、`alignOrg=5`、`alignScreen=0x99`、`fontScale=0.9`、**`label=59`（MPUI_REVIVING）**、`sort=-1`。

注释要点：**治疗进度属于援助者，受害者只保留倒地覆盖层，不显示第二条进度条。**

### 12.2 游戏结束

`SvZombieResultsMilliseconds = 1500`、`SvZombieMatchEndedMilliseconds = 7600`。

`SV_BuildZombieGameOverHud()`：origin (0,-60,0)、`alignScreen=0x22`、`fontScale=2.0`、**`font=11`、`label=462`（NCS 952+462 = ZOMBIE_GAME_OVER）**。

注释：把"成功 outro"的时间表套到全灭败北是显式重建，**绝不能因此选中 FFA 领奖台/胜者资产**。

## 十三、僵尸外观与死亡表现

### 13.1 回合身体色

`SV_ZmRoundBodyColor(round)`：

```text
round <= 4  → Blue
round <= 8  → Yellow
否则        → Orange
```

依据：5 份原始录像里 1625 具完整尸体，R1-4 蓝、R5-8 黄、R9 橙。**R10+ 保持最后有证据的颜色**（保守回退）。

### 13.2 套装选择

`SvZmOutfit` 含 body/head/torso/lower/behead 五个模型 + 若干骨骼号（默认 255）+ 左右臂偏移 + 颜色 + 眼/嘴发光。

`SV_ZmChooseOutfit(outfits, sequence, round, fallback)`：

1. 按 `round` 得到的颜色在候选里筛；
2. 无该色 ⇒ 用 Blue 集；
3. 再无 ⇒ 用 Unspecified 集；
4. 再无 ⇒ 用 caller 的 fallback。

**按已解析元数据过滤，绝不用别名/索引算术**——缺失色系不能让衣服与颜色错配，也不能接上另一族的头。

### 13.3 死亡阈值（BO1 策略，非 CODOL 概率）

```text
SV_ZmBo1DamageThreshold(damage, before): damage>0 && before>0 && damage*10 >= before
SV_ZmBo1HeadThreshold(remaining, max):   max>0 && remaining*10 <= max
```

（10% 身体伤害阈值、10% 剩余头部阈值。）

### 13.4 手臂归属

`SV_ZmArmSide(location)`：

```text
6 / 8 / 10 → +1（右）
7 / 9 / 11 → -1（左）
其他       → 0
```

### 13.5 死亡片段

`SvZmDeathSpec` 7 条（名字/毫秒/权重）：

| 名字 | ms | weight | electrical |
|---|---:|---:|---|
| ai_zombie_death_v1 | 2250 | 5 | |
| ai_zombie_death_v2 | 2517 | 5 | |
| ai_zombie_tesla_death_a | 4750 | 2 | ✓ |
| ai_zombie_tesla_death_b | 4517 | 2 | ✓ |
| ai_zombie_tesla_death_c | 4750 | 2 | ✓ |
| ai_zombie_tesla_death_d | 4517 | 2 | ✓ |
| ai_zombie_tesla_death_e | 3617 | 2 | ✓ |

时长 = 资产时长四舍五入 + 250 ms 沉降余量。

`SV_ZmChooseDeath(clips, sequence, fallback, electrical, favorOrdinary)`：

- 权重 = `c.weight * (favorOrdinary && !electrical && !c.electrical ? 4 : 1)`；
- 按 `electrical` 过滤；
- `ticket = (sequence * 7) % total`；
- 累减选中；
- 无匹配返回 fallback。

`SvZmDeathClip` 有效性：`animation` 1..4095、`milliseconds` 1000..6000、`weight` 1..10。

`SV_ZmHasDeathSequence`（loop/down 对）：loop 1..4095 且 100..1500 ms；down 1..4095 且 1000..6000 ms。

### 13.6 翻窗根运动

`SvZmWindowClip{name, frames, indices, packed, scale}`：

| 变体 | 名字 | 帧数 | 采样点数 | scale |
|---|---|---:|---:|---|
| 0 | `ai_zombie_traverse_v6` | 34 | 3 | (0.00165771879, 8.65048860e-05, 0) |
| 1 | `ai_zombie_traverse_v7` | 42 | 31 | (0.00108916464, 4.73335058e-05, 0) |

`duration() = frames * 1000 / 30`（30 fps）。源资产 SHA256：`common_gametype_zm.ff` = `7f492728...c06b7c0`；平移语料 SHA256 = `c6f36193...3d7ca57ea`。

`SV_ZmWindowRoot(variant, elapsed)`：

- `frame = clamp(elapsed/duration, 0, 1) * frames`；
- 在 `indices` 上二分找包夹；
- 两采样点线性插值后按 `scale` 缩放。

`SV_ZmWindowRootWorld(variant, elapsed, origin, yaw)`：把局部 (x,y) 按 yaw 旋转后加到 origin，z 直接加。

值得注意的是两个变体的 **z 分量 scale 恒为 0**——注释说"v6/v7 没有根旋转且局部 Z 为零"。

### 13.7 转向与沉降

`SV_ZmTurnBody(current, desired, ms)`：每毫秒 0.3°，上限 `0.3 * min(ms, 100)`。注释："300 deg/s 是重建策略，不是恢复的 CODOL 转速。"

`SV_ZmFacingReady`：`|remainder(desired-current, 360)| <= 0.01`。

`SV_ZmSettleWindowHeight(current, ground, ms)`：每毫秒最多 0.09 单位。

## 十四、Factory 房间拓扑补丁

`SV_ApplyFactoryRoomDraft(current, ground, clear, landingClear)`。

前置：`current.nodes.size() == 1206`（否则拒绝——防止对别的图层套用）。

流程：

1. 对 `FactoryRoomDraft::Points` 每点做地面投影，接受条件 `|z - (p[2]-32)| <= 8`；失败则用 `p[2]-32` 并标记 `good[i]=false`；
2. 建立 `replaced` 集合，但**先从里面剔除所有已有 vault/反向屏障/反向协商边**——"绝不移除任何原始协商 owner"；
3. 对每条 `Links`：两端 good 且双向 clear 才插入；
4. 对每条 `Ports`：**任一失败即整体拒绝**（返回带 accepted/rejected/blockedLinks 的字符串）；端口 (675,680) 允许用 `landingClear` 且要求 XY 距离 ≤ 32；
5. 对既有边：两端都不在 `replaced` 直接保留；两端都在则丢弃；一端在一端不在则尝试**重定向**到同层、平面距离 <96、高差 ≤24 的已接受点；
6. 连通性从 `Ports[2][1]` 出发 BFS；若某个端口点或已连接点不可达 ⇒ 整体拒绝；
7. 仅对被孤立且非端口的提案做省略；
8. **只对追加节点做 ID 压缩**，原生节点与协商 ID 保持不动；
9. 重建 CSR 邻接。

返回值是长诊断串：`applied sha=... nodes=... customAccepted=... rejected=... boundary=... omittedLocalIds=... blockedLinks=...`。

`sv_zm_factory_room_data.hpp` 是生成文件，`SourceSha = ba748d2b...a3981`，`Points[]` 每条带 `// local:<id>` 注释（起始 local:175、302、344…）。

## 十五、导航图：这是"实测地板"，不是零售图

### 15.1 图的来源（这段注释是本文件最重要的部分）

- zm 地图在 MapEnts 里有约 **1100 个 `node_*` 实体**（994 `node_pathnode` + 53 对 `node_negotiation_begin/_end`），**只带位置**；
- 连接属于 `aipaths` 资产，而 `aipaths` 在**每个测过的 zone 里都是空的**（XAsset 记录持有已解析的 header 指针而非写入占位符，零字节，`zm_factory_sh` 与 `zm_asylum_sh` 都一样）；
- 客户端从不需要它——AI 跑在腾讯服务器上；
- 所以边是**实测**的：1063 条零售僵尸行走（从 zm demo 重建）+ 地图自带的 53 对协商（屏障翻越，属地图数据而非观测）。

**明确声明**：这不是零售的图。它是"地板"——每条边都是真实僵尸走过的地方，但 3 份录像没有走遍所有地方，factory 的 30 个 spawner 目标节点里有 5 个完全没有边。目标不可达的演员**留在 spawner 上**，这不是可后续软化的回退：为不可达目标临时发明的路线正是"穿墙行为"。

### 15.2 结构与高度门

`SvZmNavVia{Walk=0, Negotiation=1, WalkAndNegotiation=2}`。

`SvZmNavEdge{a, b, via, animScript, xanim}`：

- `animScript` 是脚本名（零售服务器跑 `mp/animscripts/...`，本服务器没有该层）；
- `xanim` 是**名字不是索引**（客户端在地图加载时重建自己的动画带，索引会指向别的东西）；
- 例：`zombie_mantle_over_40` 对慢速演员发布 `ai_zombie_traverse_v6`，其运行时名不是 animscript 的机械 `ai_` 拼写。

`SvZmNavGraph` 关键字段：

- `nodes` / `adjacencyStart` / `adjacency`（CSR）；
- `reverseBarrierEdges` / `reverseNegotiationEdges`——物理拓扑对称以支持粗粒度连通，但 **A* 必须拒绝这些 inside→outside 的有向跨界**；
- `spawnBarrierByGoal`；
- `vaultAnim`（仅当该 animscript 的 xanim **既实测到又被引擎解析成功**时才存在）；
- `windowTraverseAnimations[2]`（v6/v7）；
- `negotiationMotion`（**有向**：倒着爬不是有效下降动画）；
- `verticalWalkMinPlanar`（MP 侧抬高的高度门，ZM 恒 0）；
- `referenceNodes/EdgesConsidered/EdgesAccepted`（供测试证明混合图确实被用了）。

`SvZmNavHeightTolerance = 72.0f`。注释解释了 72 的来历：

- 纯平面搜索是 bug（spawn 点 4 在其目标节点下方 48 单位）；
- 完全忽略 Z 更糟（实测：z=-122 的演员解析到**上一层**的节点，212 单位高差，然后沿那层的边走，高度插值过去 = 僵尸穿天花板）；
- 72 刚好在 48 之上、一楼层之下；
- 地图自己的跳跃词汇也同意：`ai_zombie_jump_down_*` = 72/96/120/127/184/190，超过 72 是掉落而非台阶。

`SvZmNavPositionTolerance = 0.05f`（身份校验，不是数值校验）。

### 15.3 `SV_BuildZmNavGraph` 的失败即关

表里的边是**实体串顺序**下 `node_*` 列表的索引，所以图和地图必须是同一份列表。校验：数量相同 + 每点都在 0.05 容差内，否则**返回空图**。

理由："半吻合的图会把僵尸引到另一张地图的走廊，比没有路由更糟。"

### 15.4 路由辅助函数

| 函数 | 作用 |
|---|---|
| `SV_ZmFirstRouteWindow(path, reverseWindows)` | 只认**前向**且在地图里真实存在的反向窗口 |
| `SV_ZmWindowQueueApplies` | 只拥有窗外接近段，不拥有窗后 |
| `SV_ZmPursuitYieldApplies` | 追击让位只在有追踪走廊时 |
| `SV_ZmGraphYieldApplies` | 图腿做**纵向**仲裁，不做横向拥挤转向 |
| `SV_ZmGraphYieldScale` | 体径 30、注意半径 42、走廊半宽 20，线性缩放 |
| `SV_ZmRouteLookaheadTarget` | 沿路线瞄准而非在每个节点折向；高差 >8 中断 |
| `SV_ZmLookaheadAdvances` | 捷径必须到达入边前平面 |
| `SV_ZmWaypointPassed` | 用**入边**平面，走廊半宽 32 |
| `SV_ZmRouteNeedsReplan` | 不要每秒重规划（会来回振荡） |
| `SV_ZmPursuitStandOffTarget` | 最近站位点，不绕圈不穿人 |
| `SV_ZmPursuitProbeDue` | 200 ms 或 8 单位位移 |
| `SV_ZmWallFollowNeedsOppositeProbe` / `SV_ZmSelectWallFollowSign` | 5% 滞回 |
| `SV_ZmShortcutCursor` | 前向 2 节点内，不跳协商边 |
| `SV_ZmSupportedWalk` | 每 16 单位采样，地板 ±4，最长 192 |
| `SV_ZmSupportedStairWalk` | 每 8 单位采样，单步 ≤18，总升 ≤112，可抬一步再验空 |

`SV_ZmNavNearestNodeIf`：只在**有邻居**且高差 ≤72、平面距离 ≤max 的候选里按距离排序取第一个通过 `accept` 的。

`SV_ZmNavRouteToClosestReachableNode`：精确目标失败后的回退——只走普通边，返回可达且几何最近节点的路线，**绝不变造边或放宽窗口方向/协商/高度/阻挡规则**。

## 十六、特种武器（箱子奖励）与传送器

### 16.1 奖励池（8 项，重建）

| kind | weapon | model | weight | equipment |
|---|---|---|---:|---|
| Ray | ray_gun_zm | weapon_usa_ray_gun | 10 | |
| Tesla | tesla_gun_zm | weapon_usa_tesla | 10 | |
| FireTrap | trap_fire_zm | t5_tf_bomb_sh | 15 | ✓ |
| FreezeTrap | trap_freeze_zm | t5_tz_bomb_sh | 15 | ✓ |
| ShockTrap | trap_shock_zm | t5_ts_bomb_sh | 15 | ✓ |
| ShrinkTrap | trap_shrink_zm | t5_tk_bomb_sh | 15 | ✓ |
| Monkey | zombie_cymbal_monkey | weapon_zombie_monkey_bomb | 5 | ✓ |
| Ammo | （空） | zombie_ammocan | 15 | |

Monkey 明确标注："资格是重建的，原生模型/定义存在，但五份原始录像里没有任何一份证明最终出现了猴子奖励。"

`SvFactorySpecialCombat{radius=250, innerDamage=100, outerDamage=0, sticky=false}`——原生普通手雷爆炸字段。

`SV_FactoryPreviewWeight(name)`：`tesla_gun_zm` 权重 1，其余 8。**视觉预览权重与获得权重独立**，且注释说特斯拉预览"按用户要求刻意更稀有"。

`SV_SelectFactorySpecialReward(weights, random)`：累加时检测 uint32 溢出并返回 nullopt；`ticket = random % total`；返回索引。

`sv_zm_special_world_mp.cpp` 两个实现要点：

- `spawnFactoryViewFx` 要求 `factoryInteractablesEnabled_`、`slot` 1..31、玩家存活；生成 `eType = EntityTypeEventBase + 117`、`eventParm = slot<<1`，并用 `markFreeAfterEvent` 立即归档；
- `stepFactoryWeaponLights` 按特斯拉剩余弹量选 `tube_view/2/3`：`index = 3 - min(3, clipCount)`，每 100 ms 一次。

`registerMultiplayerOffhandWeapons` 的中文注释记录了一次实测踩坑：**外层门是 `missileFrameRunner_ || !factorySpecialWeapons_.empty() || !multiplayerOffhandWeapons_.empty()`；若表非空而求值器/追踪器缺失，块会进入、每枚投掷物在第一帧被 `!evaluate` 分支静默退役。** 所以缺前置条件时**保持本表为空**。

### 16.2 传送器

常量：`FactoryLinkDuration = 30000`、`FactoryTeleportCooldown = 5000`、`FactoryTeleportPrice = 1800`（记录提示 1.5 × 1200）。

BO1 衍生（需单独 opt-in）：`FactoryTravelChargeMs = 2000`、`FactoryTravelRoomMs = 2000`。

`SvFactoryTeleporterState` 关键方法：

- `begin(pad, now, owner)` 拒绝：已有 travel、pad 越界、该 pad 已连接、有 pending、`now < cooldown`；
- `complete(now)` 要求 pending 且未超时；
- `showsClock(client, generation, now)`——**只有发起者/该生命才看到秒表**；
- `allPadsLinked()`。

`SV_FactoryPackDoorStep(closed, began, now, finalLink)`：

```text
前 1000 ms：类型 7，向上（其实 base 不变，delta {0,0,-35}）
1000 ms 后：base.z -= 17.5，类型 3，时长 duration-1000
超过 duration：base.z -= 35 * ((duration-1000)/1000)，类型 0
```

`SV_FactoryPackDoorDuration(finalLink)` = finalLink ? 3500 : 1500。

注释的几何论证：三段 35 单位共 105，加上最初的 17.5+17.5，模型顶部从 165.58 降到 95.58（地面 114.5），完全进入入口之下。**最后一段开合端点没有任何 demo 捕获到，是重建。**

`SV_BuildFactoryLinkClock(deadline, resources)`：

- 元素 0：`type=ClockDown`、origin (10,20,0)、96×96、`alignScreen=0x11`、`sort=2`、`setClock(deadline, 60000)`；
- 元素 1：`type=Icon`、同位置同尺寸、`sort=3`（玻璃覆盖在表盘上）。

`sv_zm_travel_mp.cpp` 片段：

- `CoreArrivals` 四个落点：(-88,256,116)、(-24,256,116)、(-88,328,116)、(-24,328,116)；
- `nearPad`：水平 176 单位 + 垂直 <100（高度守卫是 Factory 叠层的重建安全边界）；
- `beginFactoryTravel` 前置：`factoryBo1TravelEnabled_`、无进行中 travel、该 pad 已连、无 pending、未冷却、比赛未完成、玩家存在且 generation 匹配、确实在 pad 附近、未持有 travel、`roomFxReady` 且资源齐备；
- **预检两端**：`(2048,-320,56)` 与四个 `CoreArrivals` 至少一个，用 `traceCapsule` 做站立胶囊 trace，要求非 startSolid 非 allSolid；注释强调"trace 不是预约，实际进入/返回仍会重做权威 hull 查询"；
- 扣 `FactoryTeleportPrice` 电池失败则整个中止。

## 十七、关键结论

1. **ZM 侧的可信度结构是分层的**：地图数据（节点、协商对、demo 实测轨迹、xanim 名）是硬证据；时间/价格/概率/权重几乎全是重建。
2. 多条注释记录了**实际踩到的坑**，这些比结论本身更有价值：
   - 单精度 `ceil` 造成 1701 ms 而非 1700；
   - 平面最近节点 → 跨楼层穿天花板；
   - 每秒重规划 → 僵尸在路口来回振荡；
   - 缺少求值器时登记投掷物 → 每枚第一帧被静默退役。
3. `aipaths` 在测过的所有 zone 里为空，这解释了为什么导航图必须靠 demo 重建，也解释了为什么本服务器不能假装拥有零售图。
4. 大部分 ZM 图表都明确写出"不可达就停在 spawner"，这是**设计上的失败即关**，不是待补的简陋实现。

## 十八、未闭合点

- 零售 bot AI 本体不在零售客户端内（在腾讯服务器），本项目只有路由+运动适配，无原生 AI 控制器。
- 箱子掉落概率、Monkey 资格、第四台特权价格均为重建。
- 倒地合作交互（reviveRate 的实际消费方）未恢复。
- `zombie_gib`/`head_should_gib` 的完整调用者校验（攻击者/武器/方式/模型状态）在调用方。
- Factory 最终开合端点无 demo 捕获。
- Pack-a-Punch 机枪、装箱升枪的完整流程未在本组出现。
