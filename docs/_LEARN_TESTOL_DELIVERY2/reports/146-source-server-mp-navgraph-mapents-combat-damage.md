# 146 · 导航图实现、地图实体/触发器、能力位、武器/子弹/近战/伤害、记分板

## 一、范围

本报告完整学习 **16 个文件**：

- `sv_zm_navgraph_mp.cpp`（667 行，A* 与图构建实现）
- `sv_zm_teleporters_mp.cpp`（片段）、`sv_zm_special_mp.cpp`（131 行）、`sv_zm_box_mp.cpp`（片段）
- `sv_mapents_mp.hpp`（447 行）
- `sv_map_triggers_mp.hpp`（384 行）
- `sv_perks_mp.hpp`（137 行）
- `sv_weapon_fire_mp.hpp`（158 行）
- `sv_bullet_mp.hpp`（272 行）
- `sv_melee_mp.hpp`（115 行）
- `sv_damage_mp.hpp`（396 行）
- `sv_damage_numbers_mp.hpp`（151 行）
- `sv_scoreboard_mp.hpp`（150 行片段）
- `sv_weapon_loadout_mp.hpp`、`sv_equipment_mp.hpp`、`sv_offhand_kind_mp.hpp`

`server_mp` 进度推进到 **111/154**。

## 二、导航图实现：三处硬编码的实测协商运动 + 一处显式删除的假边

### 2.1 `SvZmNegotiationMotion::position`

```text
elapsed >= duration()        → samples.back()
elapsed < firstInterval      → index 0，按 elapsed/firstInterval 插值
否则                          → index = 1 + (elapsed-firstInterval)/100
                                fraction = ((elapsed-firstInterval) % 100)/100
```

`duration() = firstInterval + (samples.size()-2)*100`。所以第一个采样是"命令时刻位姿"，之后每 100 ms 一个。

### 2.2 三段实测运动（每段都有 demo 出处）

**`FactoryClimb948947`（46 个采样，3750 ms，firstInterval 50，facingYaw 180）**

出处注释：`C-2021-7-31[15-32-16]zm.demo, humanoid 710, command 69100..73550`；type2 起于 69100（首快照 69150），walk-fast 在 72850。第三份 Factory demo 的 actor 711 独立确认 3750 ms、45800→49550。

轨迹形状：起点 (87,221,-3) 在 z 轴上爬升到 ~96，然后**在 x 上继续前进**（87→62→37→31），z 保持 95..96 再缓慢降到 93。注释特别写了：

> walk-fast 在身体跨过作者化边缘裁剪体之前就开始了。保留实测出口，不要画一条到节点中心的直线。

**`FactoryDrop977976`（13 个采样，1150 ms，firstInterval 50，facingYaw 0）**

同一 actor 的下一条有向协商 977→976。命令 74500，首个位置采样 74550，walk 75650。起点在 74450/74550 之间插值；**保留 50 ms 首间隔而不是平移动画时钟**。

形状：(37.5,253,93) → (93,253,-2)，最后四个采样重复 (93,253,-2)（已静止）。

**`FactoryDrop975974`（13 个采样，1150 ms，firstInterval **100**，facingYaw 180）**

西平台出口，actor 709，66350→67500 命令交接。末采样 67550 含 50 ms 的离地行走。

形状：(-151,157,93) → (-208,157,-2) → 最后一帧 (-213,157,-3)。

### 2.3 图构建：先数、再逐点核对，不符就返回空

```text
nodes.size()*3 != table->nodeOriginBits.size()  → return {}
每个节点每个轴 |实际 - 位图| > 0.05           → return {}
```

注释：**"这个顺序就是与表的边索引之间的契约。"** 一个没有 origin 的 node 也直接返回空（"会破坏顺序"）。

### 2.4 三条"推导出来的边界"，不是抄的边

**反向协商边**：遍历 `node_negotiation_begin`，读它的 `target`，找到唯一 `node_negotiation_end` 且 `targetname == target` 的节点；若表中存在该对且 `via != Walk`，就登记 `reverseNegotiationEdges.emplace_back(*to, begin)`（注意方向：end → begin 才是反向）。

**反向屏障边**：对每个 `hasVault` 的 barrier，按**作者身份位置**（0.05 容差逐轴）找 outside / inside 节点号，登记 `(inside, outside)` 为禁行。

这里有一处**距离匹配的翻车修正**：

> Factory demo 15-32-16 的 actors 723/670/713 从 `auto414` 出发下降到 **pf683**（y≈157, z≈6），从不到 pf682（y=30, z=69）。**纯距离匹配选到了相邻的西区窗口。**

修正方式：对 `zm_factory_sh` 的 `pf683_auto1` 特别处理——遍历实体找 `targetname == "auto414"`，把它的 origin 与 (min,max) 的 outside/inside 记进 `spawnBarrierByGoal`。

**结论**：当几何上两个候选窗口都能"解释"时，几何会骗人；只有地图自己的 targetname 关系能定死。

### 2.5 一处显式删除的假边

```cpp
const auto factoryCentreFalseEdge = resolveGround && mapName == "zm_factory_sh" &&
    std::min(edge.a,edge.b) == 617u && std::max(edge.a,edge.b) == 840u;
```

注释记录：绝对 demo 的 Voronoi 重建仍推断出一条穿过 Factory 中央机械的直线。**三个独立活演员（704/707/708）都撞在同一个世界笔刷上**，命中点 (-3.375,-14.860,29.886)，fraction 0.032061，normalZ 0。

> 这是共享的图缺陷，不是演员局部拥堵：构图时一次拒绝，好过让每只僵尸墙跟随 1500 ms 再重新发现同一个障碍。

### 2.6 `usableEdge` 的完整判据

```text
grounded[a] && grounded[b]          两者都有地面
&& !factoryCentreFalseEdge          不是那条假边
&& (via != Walk || |z差| <= 72)     非 Walk 边不受高度门限制
```

注释解释：**保留每一条地图声明的协商**（作者化的翻越/攀爬/下落，垂直位移是故意的），只拒绝**推断出来的普通 Walk** 超过 72 单位的情况。活故障案例：节点 833（Z=24）→ 651（Z=120），地面演员瞄准上层走道，碰撞求解器让它永远贴着中间的墙。

### 2.7 地面投影的接受窗口

```text
z <= authored[2] + 1.0f && z >= authored[2] - 256.0f
```

接受则 `nodes[i][2] = z`；不接受则 `grounded[i] = false`（该节点与它的所有边一起被排除）。

### 2.8 动画解析：按名字去重，一次一名字

53 条协商边共享 6 个名字，所以 `byName` 缓存避免每条边都做一次动画带遍历。解析失败或引擎不持有 ⇒ 该边无条目 ⇒ 演员"不做动画变化地穿过"（与这项功能存在之前完全一样）。

窗口变体只对 `zm_factory_sh` 解析：`ai_zombie_traverse_v6` / `v7`。

### 2.9 三处 negotiationMotion 的**启用前置条件**（很严）

```text
mapName == "zm_factory_sh" && resolveGround && resolveAnim
&& grounded.size() > N && grounded[N] && grounded[M]
&& |nodes[N][2] - 期望值| < 1.0f
&& |nodes[M][2] - 期望值| < 1.0f
&& graph.vaultAnimFor(N,M) 非零
```

即：**只有在实测地面与实测动画同时存在时才启用**。注释写明："作者化的节点 Z 不是脚底 Z，不能锚定这段运动。"

### 2.10 A*：`navEdgeAllowed` 的三道闸

1. 该有向对在 `reverseBarrierEdges` ⇒ 拒绝；
2. 该有向对在 `reverseNegotiationEdges` ⇒ 拒绝；
3. **大垂直位移不算行走**：
   ```text
   |z差| > 72
   && !negotiationMotion.contains({node,next})
   && (next,node) 不在 reverseBarrierEdges
   && 平面距离 < graph.verticalWalkMinPlanar
   → 拒绝
   ```
   `verticalWalkMinPlanar` 在 ZM 侧恒为 0（平面距离永不小于 0），所以这条在 ZM 里等价于"高度 >72 且无协商运动就拒绝"。**MP 路由视图会把它抬高**，因为作者化的 MP 地图没有协商表，真实楼梯/坡道会被同一道门拒掉。实测 2026-10-12 于 mp_crash_tropical：15 条腿 Z 差 >72，平面长度双峰分布——4 条在 6..28（不是行走的邻近链接），11 条在 91..504（真实坡道）——所以 32..128 之间任何值都能同样区分。
4. 再加 `forbiddenEdges` 集合（无向比较）。

启发式用平面直线距离；边代价也是平面直线距离，所以**可采纳**。

### 2.11 三个路由入口

- `SV_ZmNavRoute`：无禁区；
- `SV_ZmNavRouteAvoidingEdge(s)`：带禁区；
- `SV_ZmNavRouteToClosestReachableNode`：Dijkstra（无启发式）从起点铺开，在**有邻居且高差 ≤ maxGoalHeightDelta** 的可达节点里选平面最近的；平局时选**路径代价更低**的。

注释：这是精确目标失败后的回退，**绝不变造边或放宽窗口方向/协商/高度规则**。

### 2.12 `SV_ZmNavNearestNode` 的两个前置

- **跳过孤立节点**：Factory 活演员 707 在碰撞转向后选中节点 867，然后永远得到空路线；
- **先做楼层测试**：`|node.z - point.z| > maxHeightDelta` 直接跳过——"平面最近在多层地图上没有意义：正上方的节点距离 15 单位、高 212 单位。"

## 三、地图实体与触发器：两套完全不同的索引空间

### 3.1 `?N` 与 `*N` 不是一回事

这是本组最重要的一条，`sv_map_triggers_mp.hpp` 开头就写：

- `*N` = 可见 brush model，索引 **clipmap 的 cmodel 列表**；
- `?N` = 触发器，索引 **`MapEnts.trigger`**，在 fastfile 里紧跟实体串之后的 `TriggerModel / TriggerHull / TriggerSlab`。

`entityState +0x09C` 对两者都存裸 N，所以**看起来像一个东西**：zm_factory_sh 同时有 `*88` 和 `?88`，const baseline 表对两者都存 88。但把 `?N` 通过 clipmap 解析会返回一个**无关的笔刷**（注释说这是实测的）。

### 3.2 触发器表结构

`SvMapTrigger` 字段：

- `triggerIndex`（`?N`）；
- `origin`（实体 `origin` 键）——因为**每个 trigger_use 的 hull 中点都在 (0,0,0) 一单位内（中位 0.5）**，所以 origin 就是盒子实际位置；
- `halfSize`（镜像**第一个** hull，供提示优先级与既有诊断）；
- `hullCount` / `hullFirst` / `slabFirst` / `slabCount`；
- `cost`（`zombie_cost` 键）；
- `targetname` / `noteworthy` / `target`（指向 retail 打开时用的 brush/script-model 组）/ `scriptFlag`。

实测分布：zm_factory_sh 54 个 `trigger_use` 里 **53 个是单 hull 无 slab**，第 54 个（`?77`，一个 `zombie_door`）有两个切面。

注释明确写：忽略 slab 的包含测试在 hull 上**保守**（只会漏体积），在 slab 上**乐观**（会声称不属于它的体积）。`SV_MapTriggerTouches` 两者都处理，且**拒绝多 hull 记录**（因为表里只存了第一 hull 的 extent）。

### 3.3 门 → 区域的解锁链接

`SV_ZmZoneUnlockedByTrigger`：两个电门是作者化的例外（retail 从电源开关打开，都不带 script_flag，都通向 `outside_south_zone`）；其余按 `scriptFlag` 映射到十个区域名。

### 3.4 提示串的两种分隔符

```text
\x14  后面是另一个本地化 KEY（作为参数）
      ZOMBIE_TRADE_WEAPON\x14ZOMBIE_TESLA_GUN
\x15  后面是字面量（作为参数）
      ZOMBIE_TELEPORT_TO_CORE\x151.5
```

两者可组合，**字面量在前**：`ZOMBIE_PERK_JUGGERNAUT\x154\x14ZOMBIE_PERK_JUGGERNAUT_EXP`。

**必须用相邻字符串字面量拼接，不能写成 `"...\x152..."`——十六进制转义是贪婪的，会把后面的数字吞掉。** 表里每一处都写成 `"ZOMBIE_PERK_QUICKREVIVE\x15" "2\x14" "ZOMBIE_PERK_QUICKREVIVE_EXP"`。

### 3.5 提示规则表（全部是 retail 的串）

| targetname | noteworthy | cost | 提示串 |
|---|---|---|---|
| zombie_door | | 1000 | ZOMBIE_BUTTON_BUY_OPEN_DOOR_1000 |
| zombie_debris | | 1000 | ZOMBIE_BUTTON_BUY_CLEAR_DEBRIS_1000 |
| auto407 | | 0 | ZOMBIE_BUTTON_BUY_TRAP |
| use_elec_switch | | 0 | ZOMBIE_ELECTRIC_SWITCH |
| treasure_chest_use | | 0 | ZOMBIE_RANDOM_WEAPON_1000 |
| （任意） | ammbox_trigger | 0 | ZOMBIE_CRATE_AMMO_REFILL |
| zombie_vending | specialty_quickrevive | 0 | QUICKREVIVE\x15 2\x14 …_EXP |
| zombie_vending | specialty_fastreload | 0 | FASTRELOAD\x15 3\x14 …_EXP |
| zombie_vending | specialty_armorvest | 0 | JUGGERNAUT\x15 4\x14 …_EXP |
| zombie_vending | specialty_rof | 0 | DOUBLETAP\x15 2\x14 …_EXP |
| zombie_vending_upgrade | specialty_weapupgrade | 0 | PACKAPUNCH\x15 2\x14 …_EXP |
| trigger_teleport_core | | 0 | ZOMBIE_LINK_TPAD |
| trigger_teleport_pad_0/1/2 | | 0 | ZOMBIE_INACTIVE_TPAD |
| intel_collectible | | 0 | SCRIPT_INTELLIGENCE_PICKUP |

两条重要注释：

- **弹药箱按 `script_noteworthy` 单键匹配**，因为 targetname 是每张图各自的名字（factory `pf734_auto1`、sumpf `pf1904_auto1`），而四张图 23 个箱子**全都带 `ammobox_trigger`**；
- **特权机的数字是运行时状态**：Pack-a-Punch 在捕获里出现 2、3、4，quick revive 出现 2 和 3 ⇒ 那个数字是价格或等级，不是机器常量。表里钉在观察到的最低值，"等电池经济存在时要改"。

### 3.6 `SV_MapTriggerTouches`：AABB 不是点

注释写得很清楚：

> 门把体积居中在门口——`?68` 中心在 z=143、半高 56，即覆盖 87..199——而玩家 origin 在**脚底**。把 origin 当点测试会让答案落在边界上，提示随地板高度闪烁。玩家站立盒是 70 高 30 宽（`StandingPlayerTraceBounds`），所以重叠盒测试既符合引擎的 touch 语义，也让门在你站进去时可用。

**demo 无法定论的部分被写下来了**：录制客户端自己的实体从不发给自己，唯一可用的位置轨是 playerState origin，而它在约 5% 的快照里被断言，行走速度下太粗糙，区分不了 30 单位盒与点。所以这是"引擎标准 touch 规则，**作为选择记录在案，而不是测量结果**"。

### 3.7 `SV_PromptableTriggerAt`：最小体积优先

只考虑有提示规则的触发器（无提示的不能因为更紧就遮住有提示的）；多个重叠时取**体积最小者**，因为更紧的体积是玩家真正站在的具体东西。

## 四、MapEnts：实体编号规则

`SV_AssignMapEntityNumbers` 的规则被解出来了：

> 编号从 **37** 开始，按**实体串顺序**发给除 worldspawn 与四个 classname 之外的每个实体：`node_pathnode`、`node_negotiation_begin`、`node_negotiation_end`、`script_struct`。

验证强度：**zm_factory_sh 的 238/238 brush model 与 133/133 script model 全对**。而且是**解出来的**：238 个 brush model 的编号已知（表存 `*N`，实体串也存），给出 20 个未知 classname 上的 237 个间隙方程，拟合恰好产生这个跳过集合。

这替代了"按 origin 匹配 script model 到表行"，后者无法区分 zm_factory_sh 里的**九对同位置实体**（两台相同 `face_identification_machine`、三对机架 A/B、五对宝箱 body/lid——其中一个还把 lid 列在前）。

### 4.1 zm zone / spawner 模型

```text
info_volume --target--> script_struct 组 --target--> goal
"player_volume"          "zombie_spawner"
targetname = ZONE        origin + angles
```

四张图实测：factory 12 区/63 点，sumpf 11/74，prototype 3/41，asylum 9/38 —— **35 区 216 点，每个 origin 都在，每个 zone target 都解析**。

**失败即关**，四种矛盾都会返回 nullopt：`player_volume` 没有 targetname 或 target；两个 volume 给一个 zone 名两个不同组；组成员不是 `script_struct` zombie spawner；某个 zone 的组一个点都没有。注释："部分解析的 zone 模型会把僵尸刷在错的地方，比完全不刷更糟。"

### 4.2 spawn 点的 goal 是一个**名字**不是坐标

注释特别纠正：`goal` 字符串是第一跳的**组名**（factory 第一个 spawn 点的 target 读作 `outside_up_spawners`），所以必须解析，不能当目的地。实测 factory 的 69 个 `zombie_spawner` 里 61 个带 `target`，**全部 61 个都解析成功**，**每一个都解析到 `node_pathnode`**，距离 159..738 单位。

`sumpf_sh` 的 74 个点里只有 32 个带 goal ⇒ **空 goal 是正常的，不是解析失败**。

### 4.3 屏障结构（四张图统一）

- boards：`script_brushmodel` + `script_parameters "board"` + `script_team "classic_boards"`，按 `targetname` 分组，`script_noteworthy` 给 1..6 槽位。factory 168 板/28 组，asylum 147/20，sumpf 114/19，prototype 72/12 —— **每组六板**，除 asylum 三个 15 板组。
- vault：组的 `targetname` 与某个 `node_negotiation_begin` 的 target 共享 `pfNNN` 前缀。factory 28/28 全连，sumpf 19/19，prototype 12/12，asylum 17/20；**板质心距该 begin 节点中位 27 单位**（每张图都是），注释说这是构造规则而非巧合。

`script_noteworthy "<zone>_barriers"` 锚点**不是结构**：factory 有 12 个只覆盖 28 组中的 12 组，另外三张图**一个都没有**却仍有板。**不要用它做解析键。**

## 五、能力位（perks）

`SvAbilityModifierCount = 192`，`mask` 是 6 个 uint32（192 位），**MSB 优先**（与 perks 的位序相反）。

`SV_HasAbility(id)`：`mask[id>>5] & (0x80000000u >> (id&31))`。

关键 id：Scavenger 2、BulletSpreadScale 6、NoRadar 18、SideRolling 80、ArmorExplosiveDamageScale 96、GasMask 99、ReviveRate 105、KillstreakShift 140、ArmorRevive 143、CrateReroll 145、SideRollingExpert 187。

`SvAbilityModifiers` 有三层：

- `mask[6]` + `values[36]` —— **这两层会被序列化/复制进原生 ps**（`clientState+0x98/+0xB0 → ps+0x590/+0x5A8`，`0x54C230..0x54C284`）；
- `resolvedValues[192]` —— 服务端拥有的、**没有客户端浮点槽**的修正值，只留在源侧；
- `moveSpeedScale` / `fallDamageScale` / `killstreakShift`。

`SV_ApplySideRollingExpert`：原生 pmove（`0x41FF20`）用 `modSideRolling`(80) 门控侧滚，而可选特权行只带 `modSideRollingExpert`(187) ⇒ 保留 187 给 clientState 行，**同时在这里授予 80**。

`SV_ResolveProfilePerks`：`item <= 1` 跳过；`lookup(item - 1)`（UI profile getter `0x50FD05` 返回 value-1）；`index >= 96` 则把 item 打成 1（清空）；否则 `bits[index>>5] |= 1 << (index&31)`。

## 六、武器开火：曲线、散布、端点

- `StandardBulletRange = 8192.0f`（CODOL 保留的 `0x46000000`）；
- `MaximumWeaponDamageRange = 1000000.0f`；
- `WeaponDamageCurvePointCount = 6`；
- `WeaponTypeBullet = 0`、`WeaponClassSpread = 4`。

`SvWeaponSpreadInput` 有 **14 个输入**：viewHeightCurrent、playerSizeScale、weaponPositionFraction、normalizedAimSpreadScale、spreadOverride(+State)、6 个 hipSpread（stand/crouch/prone × min/max）、adsSpread、perkSpreadScale。

## 七、子弹：表面类型表与盾

`BulletSurfaceTypeCount = 31`，从**表面表本身**读出（20 字节记录，第三个 dword 是材质标志字 = `index << 20`）：

```text
bark=1 brick=2 carpet=3 cloth=4 concrete=5 dirt=6 flesh=7 foliage=8
glass=9 grass=10 gravel=11 ice=12 metal=13 mud=14 paper=15 plaster=16
rock=17 sand=18 snow=19 water=20 wood=21 asphalt=22 ceramic=23
plastic=24 rubber=25 cushion=26 fruit=27 paintedmetal=28 riotshield=29
slush=30
```

`opaqueglass` **别名回 9**，非表面标志名（clipmissile/playerclip/portal/ladder…）在它之后。两个 build 名字相同、顺序相同、最大项相同 ⇒ **索引空间 0..30**。

`BulletShieldSurfaceFlags = 0x01D00000` 就是 riotshield 自己的标志字（out.exe `0x00E51778`），盾分支原样写入：`mov ecx,13h / cmp word [esi+22h],cx / mov [esi+10h],1D00000h` at `0x005919A1..0x005919AC`（3.3.3.3 同序列在 `0x0055A5A8..0x0055A5B3`）⇒ **部位组与标志来自同一次读取**，19 = 0x13 是这里实测的。

`BulletLocationalContentMask = 0x0280E831`：在两个镜像里各出现 **8 次**，且两边的 `0x01D00000` 都落在同样携带它的某个函数里（3.3.3.3 `sub_55A4A0`，out.exe `sub_5918B0`）——这个配对是识别对应物的依据，相等计数使它成为测量而非巧合。

`BulletImpactEvent` 里有一个 `bool melee`：

> 刀不是子弹。`EV_MELEE_HIT` 是自己的事件实体（eType 98 = 23 + 75），形状也不同：origin、field 9 是攻击者、field 16 是武器、eventParm 1——**全部 36 次零售断言如此**——没有表面、没有 impact flags、没有命中实体。

**为什么用 flag 而不是第二个 vector**：它们在同一个 staged 列表里、由同一个循环生成；列表是堆分配的，所以这不会给 `SvGameEntity` 增加任何东西，也不能移动那个按地址键控的缓冲区（§184h）。

### 7.1 `passFiringEntity` 的那段注释

> trace 通常**放过射击者**，这是对的，也正是本服务器从未打中过任何玩家的原因：地图里只有一个客户端时，射击者是唯一候选，所以每颗子弹都报 `hitEntity=none`，下面整条伤害路径从未到达。设成 false 让他成为合法候选。**游戏路径里没有任何地方设它**——只有 `OLMOD_BULLET_SELF_DAMAGE_PROBE` 探针会写它。

### 7.2 FMJ

> 28700：操作员的规则是"普通穿透是 1，装上 FMJ 就是 2"。下面的 resolver 提供**普通**材质深度，这个 flag 把它的返回值**翻倍**。一个乘数，没有第二张表。

## 八、近战：为什么必须由服务端 trace

`sv_melee_mp.hpp` 开头用数据证明：

- 用 `Tools/demo-re/melee-events.py` 挖 84 份 demo，35 份里 **1514 个近战事件**；
- `EV_MELEE_HIT 0x4B` —— **0 次**；`EV_MELEE_MISS 0x4C` —— **0 次**。

⇒ 真实服务器从不发这两个，客户端也不会报告挥击是否命中。而且 `codol_codecs.EVENT_WIDTH` 把每个近战 id 的参数限制在 **2 位**——本 build 实体号到 2046 需要 11 位——所以即使有事件也点不出受害者。**1514 个全是参数 0。**

因此**服务端自己 trace**，这也是 BO1 的做法（`Weapon_Melee_internal` 调 `Melee_Trace` 再 `G_Damage`，伤害 = `rand()%5 + weapDef->meleeDamage`）。

`SvMeleeRange = 64.0f` 明确标注 **CHOSEN, not measured**（IW/Treyarch 这一系都发 64）。

伤害来源：OLfinal `0x4BC1D0` 读 `WeaponDef +0x818`；alpha 对应物 `0x4D1830` 读 `+0x5F8`（让 alpha 武器克隆保留自己的值）。范围 dvar 在本 build **未恢复**。

`SvMeleeAttackResult` 四态里 `Missed` 是**常见且不是失败**（"近战经常打空"）；`Glass` 与 `Applied` 分开是因为没有玩家伤害载荷但世界确实变了，调用方必须提交。

`glassPieceCount` 必须非零：

> 留 0 不只是跳过玻璃，它会让 `SV_BulletTrace` **拒绝每一次玻璃命中**。

## 九、伤害：MOD 表、命中部位、讣告

### 9.1 20 个 MOD，不是 21 也不是 18

out.exe `sub_4EDE90` at `0x004EED35..0x004EEEC4` 逐个把名字推给字符串分配器，把返回 id 存进 `word_032B360C`、`word_032B360E`…`word_032B3632`（步长 2）。`script_vehicle` 从 `word_032B3634` 开始另一组。

```text
0 UNKNOWN            5 GRENADE_SPLASH   10 GAS              15 SUICIDE
1 PISTOL_BULLET      6 PROJECTILE       11 DOGBITE          16 TRIGGER_HURT
2 RIFLE_BULLET       7 PROJECTILE_SPL   12 SPECIAL_ATTACK   17 EXPLOSIVE
3 EXPLOSIVE_BULLET   8 MELEE            13 CRUSH            18 IMPACT
4 GRENADE            9 HEAD_SHOT        14 FALLING          19 PUNISH
```

3.3.3.3 只有 **18** 个（既没有 MOD_PUNISH 也没有 MOD_SPECIAL_ATTACK）⇒ 这是**按 build 增长的枚举**，21 在两边都越界。验证：`SV_BuildBulletFirePlan` 自己的 1/2/3 正好落在 PISTOL/RIFLE/EXPLOSIVE_BULLET 上。

### 9.2 命中部位表是 20 项，第 19 项就是 `shield`

```text
0 none  1 helmet  2 head  3 neck  4 torso_upper  5 torso_lower
6..11 the arm and hand pairs   12..17 the leg and foot pairs
18 gun  19 shield
```

注释自我修正："上面说名字表是 19 项、把 `BulletShieldPartGroup=19` 称作'在它之外'；它就在里面，所以'用一个合成的 19 占位'是对那两条注释留下的问号的正确读法。"

`HitLocationCount` 仍是 **21 且标注 NOT SETTLED**：`EngineBindings.cpp` 从原生 `WeaponDef` 的 `WeaponHitLocationMultipliersOffset` 精确读这么多 float，读错就**读越数组**。收紧到 19 之前必须真读出该数组长度。

### 9.3 死亡动画三条件

```text
hitLocation : 0 TORSO  1 HEAD  2 NECK  3 LEGS        (out.exe 0x00E606C0, cond 11)
damageType  : 0 BULLET 1 EXPLOSION_LIGHT 2 EXPLOSION (0x00E60688, cond 10)
hitDirection: 0 FRONT  1 LEFT  2 RIGHT 3 BACK        (0x00E606E8, cond 12)
```

三者都是 `ANIM_CONDTYPE_VALUE`（condType 1）⇒ **普通整数不是位标志**。注释：这是 `BG_AnimScriptEvent(DEATH)` 在本服务器上一律返回 -1 的**唯一原因**——之前没有任何地方写过这三者中的任何一个。

### 9.4 讣告参数：客户端写的规则

```text
CG_Obituary (out.exe 0x00531080) 读 12 位参数，只分支一次：
    if ((parm & 0xFFF) >= 0x6A4)        // 1700 == WeaponConfigStringCount
        icon = killicondied; switch (parm - 1700):
            8 melee  9 headshot  11 dogs  13 crush  14 falling
            15 suicide  16 died  18 impact   default: killicondied
    else
        icon = weaponDef[parm]->killIcon
```

那 8 个 case 正好落在 MOD_MELEE / HEAD_SHOT / DOGBITE / CRUSH / FALLING / SUICIDE / TRIGGER_HURT / IMPACT 上——**一个 switch 与一个字符串数组之间的八处独立吻合，且由不同路径读出**。

retail 自己的选择也测了：dm demo 的 145 次讣告里，参数 1708（1700+MELEE）12 次、1709（+HEAD_SHOT）8 次、1718（+IMPACT）1 次，其余 124 次是**普通武器索引**。⇒ 有图标的 MOD 发 MOD，其余发武器。

武器索引 ≥ 1700 或为 0 时走 1700+UNKNOWN ⇒ 落到 switch default = `killicondied`。

### 9.5 伤害数字环

T15 写入格式（`0x67406E..0x674112`）：**slot5 / sequence4 / style4 / amount12 / entity11**，32 条 6 字节记录在 `ps+0x3752`。

- 32 条，`cursor` 0..31；
- `sequence` 在 **1..15** 循环（0 = 未激活记录，不是可见命中）；
- `amount` 上限 **4095**（12 位）；
- `entity` < 2047（11 位）。

### 9.6 ZM 计分（重建）

`SV_ReconstructedZmKillReward`：非致命 0；近战 100；爆头且无头 80；否则 60。

`SV_ZmDamageAward`（score/battery 双币）：

| 情形 | score | battery |
|---|---:|---:|
| 非致命（非衰减） | +10 | +10 |
| 非致命（衰减） | 0 | 0 |
| 普通击杀 | 60 | 30 |
| 爆头击杀 | 80 | 40 |
| 近战击杀 | 100 | 50（重建） |

注释：原始 July31 Factory 实测非致命 +10/+10、普通击杀 +60/+30、爆头计数击杀 +80/+40；**非致命衰减不给任何奖励**；近战 50 电池是重建，等一份独立的原始样本。

`SV_AccumulateZmScore`：**1000 ms 窗口**内累加（贴合 9/9 原始奖励爆发，含两次三杀），上限 16777215（恰好可精确表示的整数 float）。

## 十、记分板：'J' 与 'K' 的那次真实翻车

这是本组最有操作价值的一段。

```text
CG_ServerCommand (0x0057D560) 只有一个记分板写入器 'E'，只写一行的 score
kills/deaths/assists 根本没有命令
CG_InitScoreboardFromProfile (0x0057B760) 从 mp/playerdata.def profile blob 重建每一行
该 blob 由服务端用二进制命令 'J' 填充
```

- `'J'` = 装载**并重建**；
- `'K'` = 只装载不重建 ⇒ 这才让多命令更新成为可能。

`SvProfilePatchMaximumPayload = 0x3FC`（1020）是**自设上限**，引擎限制两边**完全相同**：

```text
sub esp,408h ... lea eax,[ebp-404h] ; push 400h    最多读 1024
push 3FFh ; shl ebx,0Ah ; lea esi,[ebx+ecx+K]      最多存 1023
mov byte [esi+3FFh],0                              NUL 结尾
```

只有环掩码（`0FFh` vs `1FFh`）、环基址（`40154h` vs `80154h`）和全局变量不同。所以 `verb + payload` 的真上限在**两个 build 上都是 1023 字符**。

### 10.1 那条注释记录的事故

> 12 行的一次完整更新是 **1185 字节**（每行 96 B × 12 + 全局 33 B），对 1020 的上限必然分成两条命令。老外的参考实现与我们的 hpp 契约都只在**最后一条**上写 'J'，其余是 'K'——客户端"等整批落地后才重建一次"。**票 22310 把每条都改成 'J'，于是每装载一条就重建一次**，客户端 UI 在重建时读到的是半装载的 profile（`myTeam` 因此恒为 0，甲方实测"我认为无改善"）。老外的 zm/小规模场景 payload 天然只有一条，所以同一个 bug 在那边看不到。

修法：roster（userIds）无变化时不再发身份段（12×13 = 156 B），一次普通比分更新降到 ~1029 B，再靠 round/limit 缓存跨过单条门槛 ⇒ **一次装载、一次重建**。

### 10.2 行的 `team` 字段

```text
OLMOD(scoreboard-team, 20261016-0920)
```
此前把 team 字节留 0，理由是"客户端会从活 clientInfo 自己写"。**2026-10-16 实测否定了它**：整个记录（12 行 × 0x60）里没有任何 1/2 侧序，行 `+0x10` 恒 0，而那正是客户端读 `myTeam` 的字节（`0x6B18EF mov eax,[eax+0x10]`）。值域 1/2 来自同一消费方（1 → myTeam 1，2 → myTeam 0）。

### 10.3 一条**地址混用**的自我纠正

> `sub_C1BF70` 与 `0x0057BF70` 是**同一个 3.3.3.3 地址**。CODOL 的 i64 重定基 +0x6A0000，所以 3.3.3.3 的 `sub_57BF70` 在它里面叫 `sub_C1BF70`。并排写出来像两个 build；out.exe 自己的 `0x00C1BF70` 是无关函数。**下面这些都没有在主机上验证过。**

而且：3.3.3.3 的 `sub_57BF70` 里两个 profile 槽偏移是 `add eax,0x91B8` 和 `add eax,0x90`，**两个立即数在 out.exe 里都不存在** ⇒ profile 记录移动了，对应物必须**按形状找，不能靠重定基这个地址**。

## 十一、装备与武器附件

### 11.1 武器附件去重键是**名字**不是槽位

```text
一个槽只能一个  →  mag_extclip 先来就把 mag_fmj 丢掉
                   两者都解析到 slot 11 (mag)
                   这正好是实测报告「扩容弹夹 + 金属披甲弹同装进图后金属披甲弹不生效」
retail 把两者装在同一个武器串里
```

⇒ 去重键改为**附件名**：完全重复（同名两次）保留第一个，其余计入 `skippedDuplicateSlots`。

**返回 nullopt 对重复项是致命错误**：调用方会**丢弃整个职业**。"附件问题必须只损失一个附件，绝不能损失武器。"

仍然返回 nullopt 的情形：slot 0、槽越界、空名、合并后超过 `MaximumModularWeaponAttachmentCount = 15`。

`WeaponAttachmentSlotCount = 17`。

### 11.2 副武器（lethal/tactical）

`SvResolvedEquipment{ weapons[2] }` **只作侧存储，绝不嵌进 `WorldClientState`**。

`SV_ClearOffhandLoadout` 的存在理由：

> 背包切换把**同一条命**交给另一个职业，而 `SV_EquipOffhandLoadout` 只**增加**——没有这个函数，上一个职业的致命/战术装备会留在库存里。

best-effort：玩家已经用掉或丢掉的条目跳过，而不是让整个切换失败。

`SV_ReplaceOffhandReward`：替换一个装备槽，**保留两把枪和另一个装备的弹药**；调用方负责付款、生命校验和原生发布；失败时两个参数都不变。

### 11.3 MP 普通投掷物

`SV_MultiplayerOffhandKind` 的注释解释了一个真实缺口：

> Factory 池只在 opt-in 的 Factory/僵尸模式打开——代码注释原话「Lookup remains gated to Factory; retaining this table cannot enable specials in multiplayer」。于是多人模式里手雷/闪光/烟雾的投掷物在 handler 第一行就拿到 nullopt、静默返回 `DeferredImpact`，**玩家按 G 什么也不会发生**。

只按**本机武器内部名**判定；飞行/弹跳/引信/爆炸**不新增机制**（`SV_StepFactorySpecial` 已有 Grenade/Flash/Smoke 分支）。

**故意拒绝**：放置类（claymore / c4 / betty / *trap*）与投掷冷兵器（throwingknife / throwinghatchet / throwingcandycane…）——它们需要各自不同的 owner，**半实现比不实现更坏**。

## 十二、特种武器飞行（`sv_zm_special_mp.cpp`）

发射：

- `kind >= Ammo` 拒绝；
- basis 有效、owner < 2046、`now` 不溢出 int32-30000；
- **武器类型必须匹配**：射线/特斯拉要求 `weaponType == 2`，其余要求 `== 1`；
- 前向向量长度必须在 0.99..1.01；
- 速度：射线/特斯拉 **2000**，其余 **350**（明确标注 provisional）；
- 非枪类额外加 `delta[2] += 120`（抛物线）；
- 引信：枪 3000，猴子 8000，其余 30000。

飞行/接触：

- 引信到期：只有 Monkey/Grenade/Flash/Smoke 会引爆，其余退役；
- type 0（静止）：陷阱类（FireTrap..ShrinkTrap）**每 500 ms 边界最多一次脉冲**，永不因滞后补发爆发；
- 撞击且 startSolid/allSolid ⇒ 退役（"缺失碰撞不能卡住服务器"）；
- 枪类撞击 ⇒ 立即引爆，命中实体且 <2046 时传 directHit，表面类型 = `(surfaceFlags>>20)&31`；
- Grenade/Flash/Smoke ⇒ 反弹：沿法线偏移 0.5、重力 −800×dt、`v = (v - 2(v·n)n) * 0.45`；静止条件 `normal[2] >= 0.65 && speed² < 1600`；
- 陷阱类 ⇒ **只有支撑地面（normal[2] ≥ 0.65）才落地布防**（"墙不是漂浮平台"），落地后保留 yaw、丢弃自旋；否则继续下落（`delta = {0,0,-80}`）。

爆炸事件的原点被 `std::trunc` **向零截断**（CODOL event 98 用整数临时实体原点；BO1 `G_ExplodeMissile` 与 Ghosts 同样截断），但精确接触点单独保留给服务端伤害/可见性。

## 十三、传送器

索引：核心触发器 38，三个 pad 触发器 **39 / 41 / 40**（注意顺序不是 39/40/41）。

四个核心落点（`origin_teleport_player_0/_1/_3/_2` 提取值）：

```text
(-88,256,116)  (-24,256,116)  (-88,328,116)  (-24,328,116)
```

到达朝向 yaw = 270，占用半径 64。

提示：未通电 → `ZOMBIE_NEED_POWER`；冷却 → `ZOMBIE_TELEPORT_COOLDOWN`；已连 → `ZOMBIE_TELEPORT_TO_CORE` + 字面量 `1.5`；有 pending → `ZOMBIE_LINK_ACTIVE` / `ZOMBIE_LINK_TPAD`。

传送选择：遍历四个落点，跳过有活着的其他客户端占据 64 半径的；再让 `teleportFactoryPlayer` 做权威胶囊/世界碰撞校验；**校验不过就继续试下一个候选**（"占用检查看不到地图几何"）。

FX 生命周期：`emitFactoryTeleportFx` 有 `factoryTeleportEffects_.size() >= 16` 的上限；队列事件失败立即释放实体（"这些资产可能循环播放，绝不能在用完后留下无主的粒子"）。

## 十四、关键结论

1. **几何会骗人，身份不会**：屏障窗口的匹配从距离改成 `targetname`；导航节点从平面最近改成"有邻居 + 楼层门 + 身份位图核对"。
2. **地图数据的每一步失败都必须关**：数量不符、单点超容差、zone 解析矛盾、触发器多 hull —— 全部返回空而不是猜测。
3. **多客户端缺失会掩盖整条路径**：`passFiringEntity = true` 时单客户端永远打不中自己，所以伤害链从未到达。
4. **记分板 'J'/'K' 事故是"批量事务里逐条 commit"的典型**：客户端每次重建都读到半装载状态。
5. **去重键选错会损失整件东西**：附件按槽去重丢了整个职业，按名字去重只丢一个附件。
6. **MOD 表/命中部位表/表面表都是按 build 变的枚举**，且都有各自的验证方式（连续性、别名回指、两个镜像计数相等）。

## 十五、未闭合点

- `HitLocationCount = 21` 仍是未定值（原生 `WeaponDef` 数组真长未读出）。
- 近战范围 dvar（`player_meleeRange/Width/Height`）本 build 未恢复，64 是选择值。
- Factory 传送/箱子/特权的价格、概率、时长几乎全是重建。
- `SvZmNavTable` 只覆盖 factory（其余 zm 图无实测图 ⇒ 演员停在 spawner）。
- 玻璃的完整原生 support graph 与专用 caller 未恢复。
- MP 侧垂直行走门 `verticalWalkMinPlanar` 只有一个实测建议区间（32..128）。
