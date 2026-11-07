# 465 · **`sv_map_triggers_mp` 全文件** —— "`?N` 是它自己的命名空间"、`54` 个触发器里 `53` 个是一个 AABB、以及"一个盒不是一个点"

## 一、范围

本报告学习 `sv_map_triggers_mp.cpp`（**`811` 行，`73,990` 字节**）与 `sv_map_triggers_mp.hpp`（**完整**）。

## 二、**"`?N` 是它自己的命名空间"**（本组最重要的一段）

### 2.1 那段

```cpp
// A brush trigger is `?N` -- a namespace of its own that
// has nothing to do with the visible `*N` brush models, even though entityState
// +0x09C stores the bare N for both (zm_factory_sh has a `*88` and a `?88`, and the
// const baseline table stores 88 for each). `?N` is NOT in the clipmap's cmodel
// array; it indexes `MapEnts.trigger`, which the map fastfile carries immediately
// behind the entity string as TriggerModel / TriggerHull / TriggerSlab.
//
// So none of this can be reached through the collision bindings the way a door's
// clipHandle is, and none of it needs to be: it is static map data, so it ships here
// the same way the const baselines do.
```

### 2.2 二十四层

```text
1. **一个 brush 触发器是 `?N`** ⇒ **一个【它自己的命名空间**】**
2. ⇒ **它与那个可见的 `*N` brush 模型【毫无关系**】**
3. ⇒ **⚠ 【即使 `entityState +0x09C` 【对两者都存那个裸 `N`**】】**
4. ⇒ **（`zm_factory_sh` 有一个 `*88` 和一个 `?88`，而 `const` 基线表【对每一个都存 `88`**）**
5. ⇒ **⇒ `?N` 【不在**那个 clipmap 的 `cmodel` 数组里**
6. ⇒ **⇒ 它索引 `MapEnts.trigger`**】
7. ⇒ **⇒ 而那个【地图 fastfile 在实体串【紧邻之后**携带为 `TriggerModel`/`TriggerHull`/`TriggerSlab`】】
8. ⇒ **⇒ 所以【这些里的任何一个【不能被【通过碰撞绑定**】到达】
9. ⇒ **⇒ 那个方式【一个门的 `clipHandle` 用**】**
10. ⇒ **而【它们【也不需要**】**
11. ⇒ **⇒ 它是【静态地图数据**】**
12. ⇒ **⇒ 所以【它【在这里发运**，与 `const` 基线一样**
```

### 2.3 ⭐⭐⭐ **"即使 `entityState +0x09C` 对两者都存那个裸 `N`"**

**✅ 这是本报告里**最重要的一条"一个字段同样的值而两个空间**。**

**✅ 与 §414 的"`brushModelIndex` 是 `*N`，实体状态 `+0x09C`，`10` 位"**——**完全闭合但揭示了一个陷阱** ✓

**⇒ 三层**：
```text
`*88` ⇒ **一个可见的 brush 模型**
`?88` ⇒ **一个不可见的触发器体积**
⇒ **⇒ 而【`+0x09C` 对两者【都存 `88`**】
```

**✅ ⭐⭐⭐ **"`+0x09C` 对两者都存 `88`"** —— 一个**极精确的陷阱**。</br>

**✅ 与 §414 的"netfield 表把 `+0x09C` 误名为 `clientNum`"**同族（**第二次"`+0x09C` 的语义问题**）。

**⇒ 三层**：
```text
§414  **"netfield 表把 `+0x09C` 误名为 `clientNum`，而真实值 `1..238` 连续"**
§465  **"`+0x09C` 对 `*N` 与 `?N` 【都存那个裸 `N`**"**
⇒ **⇒ 所以【一个字段【两个命名空间**】
```

**✅ ⭐⭐⭐ **"一个字段两个命名空间"**。

**⚠ 而"`?N` 不在那个 clipmap 的 `cmodel` 数组里"**⇒ **一个结构性的隔离**。**

**⇒ 三层**：
```text
`*N` ⇒ **在 `cmodel` 数组里** ⇒ **一个碰撞句柄**
`?N` ⇒ **在 `MapEnts.trigger` 里** ⇒ **一个静态体积**
⇒ **⇒ 所以【两条完全不同的路径**】
```

**✅ ⭐⭐ **"两条完全不同的路径"**。

### 2.4 而五个地图的统计

```text
zm_factory_sh:              54 trigger volumes, 53 of them a single AABB
zm_asylum_sh:               35 trigger volumes, 19 of them a single AABB
zm_prototype_sh:            19 trigger volumes, 18 of them a single AABB
zm_sumpf_sh:                45 trigger volumes, 19 of them a single AABB
coop_training_mp_cargoship: 126 trigger volumes, 82 of them a single AABB
```

**⇒ 我的统计完全吻合**（`54`/`35`/`19`/`45`/`126`）✓

**⇒ 十二层**：
```text
1. **五个地图，共 `279` 个触发器**
2. ⇒ **而【单 AABB 的**：`53 + 19 + 18 + 19 + 82 = 191`**
3. ⇒ **⇒ 所以【`191/279 = 68.5%` 是单 AABB**】
4. ⇒ **而【`88` 个是【多 hull 或带 slab**】**
5. ⇒ **⇒ 所以【`31.5%` 【需要 slabs**】
```

### 2.5 ⭐⭐⭐ **"`zm_factory_sh` 的 `54` 个里 `53` 个是单 AABB，而第 `54` 个（`?77`，一个 `zombie_door`）有两个 slab 平面切它"**

**✅ 与 §458 的"`zm_factory_sh` 的 `54` 个 `trigger_use`"**完全闭合 ✓

**⇒ 三层**：
```text
§458  **"发运的表携带 `zm_factory_sh` 的【全部 `54` 个 `trigger_use`**"**
§465  **"`54` 个里 `53` 个是单 AABB 而第 `54` 个（`?77`）有两个 slab"**
⇒ **⇒ 一个精确的补充**
```

**✅ ⭐⭐⭐ **"`?77` 有两个 slab"** —— 一个**具体的例外**。</br>

**✅ 与 §458 的"`driveCursorHints` 只对 `zombie_door` 给提示"**配合（**而 `?77` 是一个 `zombie_door`**）。

**⇒ 三层**：
```text
`?77` ⇒ **一个 `zombie_door`**（**唯一有 slab 的那个**）
而【§458 说"只有 `zombie_door` 有提示**"**
⇒ **⇒ 所以【那个唯一的复合体积【正是那个唯一的提示**】
```

**✅ ⭐⭐⭐ **"那个唯一的复合体积正是那个唯一的提示"** —— 一个**极漂亮的巧合（或设计）**。

## 三、**"一个盒，不是一个点"**（本组第二重要）

### 3.1 那段

```cpp
// A BOX, NOT A POINT, and that is not a detail. The doors sit with their volume
// centred on the doorway -- `?68` is centred at z=143 with a half-height of 56, so
// it spans 87..199 -- while a player's origin is at their FEET. Testing the origin
// as a point puts the answer on the boundary and makes the prompt flicker with the
// floor height. The player's own standing box is 70 units tall and 30 wide
// (`StandingPlayerTraceBounds`), so overlapping boxes is both what the engine does
// for a touch and what makes a doorway usable when you are standing in it.
//
// WHAT THE DEMO COULD NOT SETTLE: whether retail tests the box, the point, or adds a
// view check. The recording client's own entity is never sent to itself, so the only
// position track available is the playerState origin, and that is client-predicted
// and asserted in about 5% of snapshots -- far too coarse at walking speed to tell a
// 30-unit box from a point. This is the engine-standard touch rule, chosen
// deliberately and written down as a choice rather than a measurement.
```

### 3.2 二十四层

```text
1. **一个盒，不是一个点，而【那不是一个细节**】**
2. ⇒ **那些门【坐在它们的体积【中心在门洞上**】】
3. ⇒ **（`?68` 中心在 `z=143` 而半高 `56` ⇒ **它跨 `87..199`**）**
4. ⇒ **而【一个玩家的原点【在它们的【脚上**】】**
5. ⇒ **⇒ 把一个原点【当作一个点测**】把那个答案【放在边界上**】**
6. ⇒ **⇒ 而让那个提示【随地板高度【闪烁**】】**
7. ⇒ **玩家自己的站立盒是【`70` 单位高、`30` 宽**】（`StandingPlayerTraceBounds`）**
8. ⇒ **⇒ 所以【盒重叠**是【引擎在一个 touch 上所做的**】
9. ⇒ **⇒ 也是【让一个门洞【在你站在它里面时可用的**】】
10. ⇒ **⚠ 而那 demo 【无法解决**的是：零售测【盒、点，还是加一个视图检查**】**
11. ⇒ **因为【那个录制客户端自己的实体【从不被发给自己**】**
12. ⇒ **⇒ 所以【唯一可用的位置轨迹是 `playerState` 原点**】**
13. ⇒ **⇒ 而那是【客户端预测的**而【只在约 `5%` 的快照里**被断言】
14. ⇒ **⇒ 【在走路速度下【太粗**】去分辨一个 `30` 单位的盒与一个点**】
15. ⇒ **⇒ 这是【引擎标准的 touch 规则**，**【刻意选择**而【写下来作为一个选择**而不是一个测量**】
```

### 3.3 ⭐⭐⭐ **"写下来作为一个选择而不是一个测量"**

**✅ 这是本报告里**最重要的一条"一个选择的诚实记录**。**

**✅ 与 §404 的"这是一个窄回退，不是一个诊断"**、§435 的"缩短窗口，它不关闭它"**完全同族** ✓

**⇒ 三层**：
```text
可以测 ⇒ **一个测量**（**有证据**）
不能测 ⇒ **一个选择**（**有理由但无证据**）
⇒ **⇒ 所以【必须【标注**是哪一个**】
```

**✅ ⭐⭐⭐ **"必须标注是哪一个"** —— 第四次"选择的诚实记录"。

**⇒ 三层**：
```text
§404  **"窄回退不是诊断"**
§435  **"缩短窗口不关闭"**
§465  **"作为一个选择而不是一个测量"**
⇒ **⇒ 三次"选择的诚实记录**】
```

**✅ ⭐⭐ **"选择的诚实记录"三例表**。

**⚠ 而"那个录制客户端自己的实体【从不被发给自己**"⇒ **一个取证的根本限制**。**

**⇒ 三层**：
```text
demo ⇒ **录制客户端自己的实体【不被发给自己**】
⇒ **⇒ 所以【它的位置【只能从 `playerState` 原点**读**】
⇒ **⇒ 而那个【只在 5% 的快照里被断言**】
```

**✅ ⭐⭐⭐ **"只能从 `playerState` 原点读，而那个只在 5% 的快照里被断言"** —— 与 §427 的"demo 不含 usercmd"**、§460 的"demo 无客户端预测环"**同族（**第三次"demo 的盲区"）。

**⇒ 三层**：
```text
§427  **demo 不含 usercmd**
§460  **demo 无本地预测环**
§465  **demo 里录制客户端自己的实体不被发给自己，位置只在 5% 的快照里**
⇒ **⇒ 三次"demo 的盲区**】
```

**✅ ⭐⭐ **"demo 的盲区"三例表**。

### 3.4 而 `SV_MapTriggerTouches` 的三层

```cpp
① 若 !trigger.hullCount 或 hullFirst + hullCount > hulls.size() ⇒ false
② 对每个 hull：三轴的 AABB 重叠检查
③ 若重叠：对每个 slab，投影玩家 AABB 到 slab 法线并按其支撑范围放宽
④ 若某个 slab 失败 ⇒ overlaps = false
⑤ 若某 hull 全部通过 ⇒ 返回 true
```

**⇒ 十层**：
```text
1. **一个先决检查**（`hullCount` 与边界）
2. ⇒ **然后【逐 hull**】
3. ⇒ **每个 hull 一个三轴 AABB 检查**
4. ⇒ **然后【逐 slab**】
5. ⇒ **一个"投影 + 支撑范围"的放宽**（`projected ± (halfSize + support)`）
6. ⇒ **⇒ 所以【一个精确的凸体相交**】
```

### 3.5 ⭐⭐⭐ **"proj + 支撑范围"是一个精确的 AABB-vs-凸体测试**

**⇒ 三层**：
```text
`projected = direction · (playerCentre - triggerOrigin)`
`support = Σ |direction[axis]| × boxHalfSize[axis]`
⇒ **⇒ 所以【一个 AABB 在一个法线上的【半宽**就是那个 `support`**】
```

**✅ ⭐⭐⭐ **"一个 AABB 在一个法线上的半宽就是那个 support"** —— 一个**标准的分离轴定理（SAT）的实现**。

**⚠ 而"这会给出【一个正确的**答案】（**对一个凸体，SAT 是精确的**）。**

**✅ 与 §465 二 的"REFUSES WHAT IT CANNOT ANSWER"**配合。

### 3.6 而**"REFUSES WHAT IT CANNOT ANSWER"**

```cpp
// REFUSES WHAT IT CANNOT ANSWER. Slab planes are evaluated exactly. A trigger with
// more than one hull still has only its first hull's extents in this table, so
// answering "yes" would light a prompt or mission phase in space it does not occupy.
```

**⇒ 十层**：
```text
1. **拒绝它不能回答的**
2. ⇒ **slab 平面【被精确地评估**】**
3. ⇒ **⚠ 而【一个多于一个 hull 的触发器【在【这个表里【仍然只有【它第一个 hull 的范围**】】**
4. ⇒ **⇒ 所以【回答"是"**【会点亮一个提示或任务阶段【在【它并不占据的空间里**】】】
```

**✅ ⭐⭐⭐ **"回答『是』会点亮一个提示在它并不占据的空间里"** —— 与 §458 的"一个提供打开打不开的东西的提示比没有更糟"**完全同族** ✓

**⇒ 三层**：
```text
§410  **"一个交付不了任何东西的特性没有主张"**
§458  **"一个提供打开打不开的东西的提示比没有更糟"**
§465  **"回答『是会点亮一个提示在它并不占据的空间里"**
⇒ **⇒ 三次"宁可不说**】
```

**✅ ⭐⭐⭐ **"宁可不说"三例表**。

**⚠ 而"多于一个 hull 的触发器【仍然只有它第一个 hull 的范围**"⇒ **所以【那些触发器【会返回 false**】。**

**⇒ 三层**：
```text
若 `hullCount > 1`** ⇒ **那个表【只有第一个的范围**】
而【代码【仍然对每个 hull 循环**】 ⇒ **但 `halfSize` 是第一个**
⇒ **⇒ 所以【一个多 hull 的**【可能误判**】
```

**⚠ 一个**需要标注的点**（**注释说"refuses"，而代码【仍然循环**】）。

**⇒ 三层**：
```text
注释：**"REFUSES WHAT IT CANNOT ANSWER"**
代码：**`for (hullIndex = 0; hullIndex < trigger.hullCount; ++hullIndex)`** ⇒ **不拒绝**
⇒ **⇒ 所以【注释与代码【不一致**】
```

**⚠⚠ 一个真实的矛盾**（**第四次"注释与代码"**）。

**✅ 与 §457 的"`.hpp` 的 `sendRawCommand` 注释停在修复前"**同族（**第四次"注释落后**）。

## 四、**`TriggerHintRules` 的十八个规则**（本组第三重要）

### 4.1 清单

```text
zombie_door           cost 1000  ⇒ ZOMBIE_BUTTON_BUY_OPEN_DOOR_1000
zombie_debris         cost 1000  ⇒ ZOMBIE_BUTTON_BUY_CLEAR_DEBRIS_1000
auto407               —          ⇒ ZOMBIE_BUTTON_BUY_TRAP
use_elec_switch       —          ⇒ ZOMBIE_ELECTRIC_SWITCH
treasure_chest_use    —          ⇒ ZOMBIE_RANDOM_WEAPON_1000
(any) ammobox_trigger —          ⇒ ZOMBIE_CRATE_AMMO_REFILL
zombie_vending specialty_quickrevive ⇒ ZOMBIE_PERK_QUICKREVIVE\x15 2\x14 ZOMBIE_PERK_QUICKREVIVE_EXP
zombie_vending specialty_fastreload  ⇒ ...FASTRELOAD\x15 3\x14 ..._EXP
zombie_vending specialty_armorvest   ⇒ ...JUGGERNAUT\x15 4\x14 ..._EXP
zombie_vending specialty_rof          ⇒ ...DOUBLETAP\x15 2\x14 ..._EXP
zombie_vending_upgrade specialty_weapupgrade ⇒ ...PACKAPUNCH\x15 2\x14 ..._EXP
trigger_teleport_core ⇒ ZOMBIE_LINK_TPAD
trigger_teleport_pad_0/1/2 ⇒ ZOMBIE_INACTIVE_TPAD
intel_collectible     ⇒ SCRIPT_INTELLIGENCE_PICKUP
```

**⇒ 十七个规则（`trigger_teleport_pad_0/1/2` 是三条）。**

### 4.2 ⭐⭐⭐ **"`0x14` 是另一个本地化键，`0x15` 是一个字面量，而它们可组合，字面量在前"**

```cpp
//   0x14   the rest is ANOTHER LOCALIZATION KEY, used as an argument
//          `ZOMBIE_TRADE_WEAPON\x14ZOMBIE_TESLA_GUN`
//   0x15   the rest is a LITERAL, used as an argument
//          `ZOMBIE_TELEPORT_TO_CORE\x151.5`
//
// and they compose, literal first:
//   `ZOMBIE_PERK_JUGGERNAUT\x154\x14ZOMBIE_PERK_JUGGERNAUT_EXP`
//
// Write these with adjacent string literals, never as one `"...\x152..."` -- a hex
// escape is greedy and would swallow the digit that follows it.
inline constexpr char HintArgumentKey = '\x14';
inline constexpr char HintArgumentLiteral = '\x15';
```

**⇒ 二十层**：
```text
1. **两个分隔字节在零售捕获的提示带里出现**，而【两者都是【服务器写的那个值的一部分**】**
2. ⇒ **`0x14` ⇒ 其余部分【是【另一个本地化键**，用作一个参数**】
3. ⇒ **（`ZOMBIE_TRADE_WEAPON\x14ZOMBIE_TESLA_GUN`）**
4. ⇒ **`0x15` ⇒ 其余部分【是一个字面量**，用作一个参数**】
5. ⇒ **（`ZOMBIE_TELEPORT_TO_CORE\x151.5`）**
6. ⇒ **而它们【可组合，字面量在前**】**
7. ⇒ **（`ZOMBIE_PERK_JUGGERNAUT\x154\x14ZOMBIE_PERK_JUGGERNAUT_EXP`）**
8. ⇒ **⚠ 【用相邻的字符串字面量**写这些**
9. ⇒ **【绝不要**写成一个 `"...\x152..."` 】
10. ⇒ **⇒ 因为【一个十六进制转义是【贪婪的**】**
11. ⇒ **⇒ 而【会吞掉紧随其后的那个数字**】**
```

### 4.3 ⭐⭐⭐ **"一个十六进制转义是贪婪的，会吞掉紧随其后的那个数字"**

**✅ 这是本报告里**最重要的一条 C++ 陷阱**。**

**✅ 与 §438 的"`static_cast<uint64_t>` 让检查工作"**、§444 的"`int64` 中间量"**同族（**第五次"一个语言细节**）。

**⇒ 三层**：
```text
错误：`"...\x152..."` ⇒ **`\x152` 是一个字面量 `0x152`** ⇒ **`2` 消失**
正确：`"...\x15" "2..."` ⇒ **`\x15` 然后 `'2'`**
⇒ **⇒ 所以【相邻字面量【不是风格而是正确性**】
```

**✅ ⭐⭐⭐ **"相邻字面量不是风格而是正确性" —— 一个极精确的 C++ 陷阱**。</br>

**✅ 与 §413 的"`0x08` 的 `\0` 截断"**不同（那是**运行时**，这是**编译期**）。

**⇒ 三层**：
```text
§425  **`parseMessage` 在 `\0` 处【截断**（**运行时**）**
§465  **`\x152` 【被编译器吞掉**（**编译期**）**
⇒ **⇒ 两次"一个转义/字符串的陷阱**】
```

**✅ ⭐⭐ **"一个转义/字符串的陷阱"两例**。

### 4.4 而**"每一个字符串都是零售的，不是这个项目的措辞"**

```cpp
// EVERY STRING HERE IS RETAIL'S, not this project's wording.
//
// Four of them are pinned by the `ncs_hnt_localized_common_gametype_zm` block that
// preloads the low end of the band, in the order the 7-31 capture publishes relative
// indices 3, 4, 5 and 6 on a zombie_debris, four zombie_doors, the two trap triggers
// and the use_elec_switch. The rest are the values retail's own server wrote into
// that band during the five captures, paired to a trigger by the entity number the
// hint named.
//
// THE PERK LITERALS ARE STATE THIS SERVER DOES NOT HAVE. Pack-a-Punch appears with
// 2, 3 AND 4 across the captures and quick revive with 2 and 3, so the number is a
// runtime value -- a price or a tier -- not a constant of the machine. Each is
// pinned here to the value retail was observed sending, lowest where more than one
// was seen, and it will need to move when a battery economy exists.
```

**⇒ 二十四层**：
```text
1. **这里的每一个字符串【都是零售的**，不是这个项目的措辞**】
2. ⇒ **四个由那个 `ncs_hnt_localized_common_gametype_zm` 块【钉住**】**
3. ⇒ **（那个块【预载那个带的低端**）**
4. ⇒ **⇒ 按 `7-31` 捕获【发布相对索引 `3`/`4`/`5`/`6`**的顺序】
5. ⇒ **⇒ 在【一个 `zombie_debris`、四个 `zombie_doors`、两个陷阱触发器、`use_elec_switch`**上**
6. ⇒ **而其余是【零售自己的服务器【在那五次捕获里【写进那个带**的值】
7. ⇒ **⇒ 通过【那个提示命名的**实体号【配对到一个触发器**】
8. ⇒ **⚠ 而【perk 的字面量【是这个服务器【没有的**状态**】**
9. ⇒ **Pack-a-Punch 【以 `2`、`3` **和** `4` 出现**】
10. ⇒ **而 quick revive 以 `2` 和 `3`**
11. ⇒ **⇒ 所以【那个数字【是一个【运行时**值】**
12. ⇒ **（一个价格或一个层级**）**
13. ⇒ **⇒ 【不是一个机器的常数**】**
14. ⇒ **每个在这里【被钉到一个【零售被观察到发送的**值】
15. ⇒ **⇒ 【在有多个时取最低**】**
16. ⇒ **⇒ 而它【在一个电池经济存在时【需要**移动**】
```

### 4.5 ⭐⭐⭐ **"那个数字是一个运行时的值 —— 一个价格或一个层级 —— 不是一个机器的常数"**

**✅ 这是本报告里**最重要的一条"一个常数其实是状态**。**

**✅ 与 §417 的"`SvRetailLivePerks{132, 16777216, 0}` 是一个测量出来的占位，不是一个配装"**——**完全同族** ✓

**⇒ 三层**：
```text
§417  **"`SvRetailLivePerks` 是一个【测量出来的占位，不是一个配装**"**
§465  **"perk 的字面量【是状态**而这个服务器【没有**"**
⇒ **⇒ 两次"一个测量出来的占位**】
```

**✅ ⭐⭐⭐ **"一个测量出来的占位"两例**。

**⚠ 而"在多个时取最低"⇒ **一个明确的策略**。**

**⇒ 三层**：
```text
零售：`2`、`3`、`4`
我们：【取 `2`**】
⇒ **⇒ 所以【一个【保守的**选择**
```

**✅ ⭐⭐ **"一个保守的选择"** 与 §465 三 的"宁可不说"**同族（**第四次）。

## 五、`SV_PromptableTriggerAt` 的"最小的赢"

```cpp
// Only triggers a hint rule matches are considered, so one with no prompt can never
// shadow one that has a prompt by being tighter. When two promptable volumes
// overlap -- and zm's do, a door and a debris purchase can share a doorway -- the
// SMALLEST wins, because the tighter volume is the more specific thing the player
// is standing at.
```

**⇒ 十四层**：
```text
1. **只有【一个提示规则匹配**的触发器【被考虑**】**
2. ⇒ **⇒ 所以【一个没有提示的【永远不会【因为更紧**】而【遮蔽一个有提示的**】】
3. ⇒ **当两个可提示的体积重叠**
4. ⇒ **（而 zm 的会：一个门与一个碎片购买【可以共享一个门洞**）**
5. ⇒ **⇒ 【最小的赢**】**
6. ⇒ **⇒ 因为【那个更紧的体积【是【更具体的**那个玩家站在的东西**】
```

### 5.1 ⭐⭐⭐ **"一个没有提示的永远不会因为更紧而遮蔽一个有提示的"**

**✅ 与 §465 三 的"宁可不说"**同族（**第五次"宁可不说"）。

**⇒ 三层**：
```text
若【不先过滤**】⇒ **一个无提示的紧体积【可以遮蔽**一个有提示的**
而【先按规则过滤**】⇒ **无提示的【不参与竞争**】
⇒ **⇒ 所以【过滤【在【选择**之前**】
```

**✅ ⭐⭐⭐ **"过滤在选择之前"** —— 而 **`SV_PromptableTriggerAt` 的循环【先查规则**】** ✓

**⚠ 而"最小的赢"⇒ **一个基于体积的优先级**。**

**⇒ 三层**：
```text
`volume = halfSize[0] * halfSize[1] * halfSize[2]`
⇒ **⇒ 所以【那个更小的**体积【赢**】
```

**✅ ⭐⭐ **"那个更小的体积赢"**。</br>

**✅ 与 §458 的"`registerHintString` 从低端扫"**不同（那是**一个分配器**，这是**一个选择器**）。

## 六、`SV_ZmZoneUnlockedByTrigger` 的十一个映射

```cpp
if (trigger.noteworthy == "factory_electric_door") return "outside_south_zone";
{ "enter_outside_west", "outside_west_zone" },
{ "enter_outside_east", "outside_east_zone" },
{ "enter_tp_south", "tp_south_zone" },
{ "enter_tp_east", "tp_east_zone" },
{ "enter_tp_west", "tp_west_zone" },
{ "enter_wnuen_building", "wnuen_zone" },
{ "enter_wnuen_loading_dock", "wnuen_bridge_zone" },
{ "enter_wuen_loading_dock", "wnuen_bridge_zone" },
{ "enter_warehouse_building", "warehouse_bottom_zone" },
{ "enter_warehouse_second_floor", "warehouse_top_zone" },
```

**⇒ 十层**：
```text
1. **一个特殊的**：`factory_electric_door` ⇒ `outside_south_zone`**（**一个 `noteworthy` 的特例**）
2. ⇒ **十个 `scriptFlag` → `zone`**
3. ⇒ **而【两个 flag 映射到同一个 zone**】（`enter_wnuen_loading_dock` 与 `enter_wuen_loading_dock` 都到 `wnuen_bridge_zone`）
4. ⇒ **⇒ 所以【一个 `wnuen`/`wuen` 的拼写**差异**
```

### 6.1 ⭐⭐⭐ **"`enter_wnuen_loading_dock` 与 `enter_wuen_loading_dock` 都到 `wnuen_bridge_zone`"**

**✅ 这是本报告里**最重要的一条"两个名字一个目标**。**

**⇒ 三层**：
```text
`wnuen` ⇒ **一个拼写**
`wuen` ⇒ **另一个拼写**（**少了 `n`**）
⇒ **⇒ 而【两者都映射到同一个 zone**】
```

**✅ ⭐⭐⭐ **"两者都映射到同一个 zone"** —— 一个**兼容性处理**（**一个地图的笔误**）。

**✅ 与 §465 四.5 的"perk 的多个值取最低"**同族（**一个"容纳差异"的选择**）。

**⇒ 三层**：
```text
§465 四.5  **多个 perk 值 ⇒ 取最低**
§465 六.1  **两个拼写 ⇒ 都接受**
⇒ **⇒ 两次"容纳差异**】
```

**✅ ⭐⭐ **"容纳差异"两例**。

**⚠ 而"`factory_electric_door` 是一个 `noteworthy` 的特例"**⇒ **与 §422 的"两扇电动门不是两个 `10000` 的购买"**完全闭合 ✓

**⇒ 三层**：
```text
§422  **"Factory 的两扇电动门【在电源开关那一帧【一起**走这条路径"**
§465  **`factory_electric_door` ⇒ `outside_south_zone`**（**一个 `noteworthy` 的特例**）
⇒ **⇒ 所以【那个特例【是那个一致的机制**】
```

**✅ ⭐⭐⭐ **"那个特例是那个一致的机制"**。

## 七、`SvMapTrigger` 的十七个字段

```cpp
std::uint16_t triggerIndex;       // ?N
std::array<float,3> origin;
std::array<float,3> halfSize;
std::uint16_t hullCount;
std::uint16_t hullFirst;
std::uint16_t slabFirst;
std::uint16_t slabCount;
std::uint32_t cost;
std::string_view targetname;
std::string_view noteworthy;
std::string_view target;
std::string_view scriptFlag;
```

**⇒ 十二个。**

### 7.1 ⭐⭐⭐ **"每一个 `trigger_use` 的 hull 中点在 `zm_factory_sh` 里都在 `(0,0,0)` 的一个单位之内 —— 中位数 `0.5`"**

```cpp
// THE HULL IS ENTITY-LOCAL, which is the whole reason this pairing works: every
// trigger_use hull midpoint in zm_factory_sh is within a unit of (0,0,0) --
// median 0.5 -- so the origin below is where the box actually sits and halfSize
// is how big it is.
```

**⇒ 十层**：
```text
1. **那个 hull 是【实体局部的**】**
2. ⇒ **⇒ 而那【正是【这个配对**能工作的全部理由**】
3. ⇒ **`zm_factory_sh` 里【每一个 `trigger_use` 的 hull 中点【都在 `(0,0,0)` 的一个单位之内**】**
4. ⇒ **（**中位数 `0.5`**）**
5. ⇒ **⇒ 所以【`origin` 【就是那个盒实际坐的地方**】**
6. ⇒ **而 `halfSize` 【就是【它有多大**】**
```

**✅ ⭐⭐⭐ **"那个 hull 是实体局部的，而那正是这个配对能工作的全部理由"** —— 一个**极漂亮的几何论证**。

**⚠ 而"中位数 `0.5`"⇒ **一个统计量的用法**。**

**✅ 与 §455 的"平均值是完美的 50 而没有一个是 50"**相反（**这里中位数支持那个结论**）。

**⇒ 三层**：
```text
§455  **"平均完美的 50 而没有一个是 50"**（**一个统计量【欺骗**）
§465  **"中位数 `0.5` ⇒ hull 是实体局部的"**（**一个统计量【支持**）
⇒ **⇒ 两次"统计量**】
```

**✅ ⭐⭐ **"统计量"两例**。

## 八、关键结论

1. **⭐⭐⭐ "一个 brush 触发器是 `?N` —— 一个它自己的命名空间，与那个可见的 `*N` brush 模型毫无关系，【即使 `entityState +0x09C` 对两者都存那个裸 `N`】（`zm_factory_sh` 有一个 `*88` 和一个 `?88`，而 `const` 基线表对每一个都存 `88`）"`** ⇒ **"`?N` 不在那个 clipmap 的 `cmodel` 数组里；它索引 `MapEnts.trigger`"`** —— **"一个字段两个命名空间"**。
2. **⭐⭐ 五个地图的 `279` 个触发器**（`54`/`35`/`19`/`45`/`126`，我的统计完全吻合），其中 **`191/279 = 68.5%` 是单 AABB** ⇒ **`88` 个需要 slabs**。
3. **⭐⭐⭐ "`zm_factory_sh` 的 `54` 个里 `53` 个是单 AABB，而第 `54` 个（`?77`，一个 `zombie_door`）有两个 slab 平面切它"`** —— 与 §458 的"`driveCursorHints` 只对 `zombie_door` 给提示"**构成了一个极漂亮的巧合**：**"那个唯一的复合体积正是那个唯一的提示"`**。
4. **⭐⭐⭐ "一个盒，不是一个点：`?68` 中心在 `z=143` 而半高 `56` ⇒ 它跨 `87..199`，而一个玩家的原点在它们的脚上 ⇒ 把一个原点当点测把答案放在边界上而让那个提示随地板高度闪烁"`**；玩家站立盒 `70` 高、`30` 宽（`StandingPlayerTraceBounds`）。
5. **⭐⭐⭐ "demo 无法解决的是：零售测盒、点、还是加一个视图检查 —— 因为那个录制客户端自己的实体【从不被发给自己】，所以唯一可用的位置轨迹是 `playerState` 原点，而那是客户端预测的而只在约 `5%` 的快照里被断言 ⇒ 在走路速度下太粗"`** ⇒ **"这是引擎标准的 touch 规则，【刻意选择】而【写下来作为一个选择而不是一个测量**】"`** —— 第三次"选择的诚实记录"（与 §404/§435 同族），也是第三次"demo 的盲区"（与 §427/§460 同族）。
6. **⭐⭐ `SV_MapTriggerTouches` 是一个精确的 SAT**（`projected ± (slab.halfSize + support)`，其中 `support = Σ |direction[axis]| × boxHalfSize[axis]`）⇒ **"一个 AABB 在一个法线上的半宽就是那个 support"`**。
7. **⚠⚠ 一个真实的矛盾**：**注释说"REFUSES WHAT IT CANNOT ANSWER"（多于一个 hull 的只会用第一个 hull 的范围）而【代码仍然循环 `trigger.hullCount`**】⇒ **注释与代码不一致**（第四次"注释落后"，与 §457 同族）。
8. **⭐⭐⭐ `TriggerHintRules` 的十七个规则**，而 **"`0x14` 是另一个本地化键，`0x15` 是一个字面量，而它们可组合，字面量在前"`** ⇒ **"用【相邻的字符串字面量】写这些，【绝不要】写成一个 `"...\x152..."` —— 一个十六进制转义是【贪婪的】而会吞掉紧随其后的那个数字"`** —— **"相邻字面量不是风格而是正确性"**（第五次"一个语言细节"）。
9. **⭐⭐⭐ "这里的每一个字符串都是零售的，不是这个项目的措辞"`**：**四个由 `ncs_hnt_localized_common_gametype_zm` 块钉住（按 `7-31` 捕获发布相对索引 `3`/`4`/`5`/`6`）**，**其余是零售自己的服务器在那五次捕获里写进那个带的值**。
10. **⭐⭐⭐ "perk 的字面量【是这个服务器没有的状态**】：Pack-a-Punch 以 `2`、`3` 和 `4` 出现而 quick revive 以 `2` 和 `3` ⇒ **"那个数字是一个运行时的值 —— 一个价格或一个层级 —— 不是一个机器的常数"`**，而**每个被钉到零售被观察到发送的值，在有多个时取最低** —— **第二次"一个测量出来的占位"**（与 §417 同族）。
11. **⭐⭐⭐ `SV_PromptableTriggerAt` 的"一个没有提示的永远不会因为更紧而遮蔽一个有提示的"`**（**过滤在选择之前**）与 **"最小的赢，因为那个更紧的体积是更具体的那个玩家站在的东西"`**。
12. **⭐⭐ `SV_ZmZoneUnlockedByTrigger` 的十一个映射**，其中 **`enter_wnuen_loading_dock` 与 `enter_wuen_loading_dock` 都到 `wnuen_bridge_zone`** ⇒ **"两个拼写一个目标"`**（容纳一个地图的笔误，与 §465 四.5 的"取最低"同族）；而 **`factory_electric_door` 是一个 `noteworthy` 的特例** ⇒ 与 §422 完全闭合。
13. **⭐⭐⭐ "那个 hull 是实体局部的，而那正是这个配对能工作的全部理由：`zm_factory_sh` 里每一个 `trigger_use` 的 hull 中点都在 `(0,0,0)` 的一个单位之内（中位数 `0.5`）⇒ `origin` 就是那个盒实际坐的地方"`** —— 一个中位数**支持**一个结论（与 §455 的"平均值欺骗"相反）。

## 九、未闭合点

- `?77` 的两个 slab 的精确语义。
- `SV_MapTriggerTouches` 对 `hullCount > 1` 的实际行为（注释说拒绝而代码不拒绝）。
- `ncs_hnt_localized_common_gametype_zm` 块的内容。
- `StandingPlayerTraceBounds` 的精确值。
- **下一步**：`sv_zm_board_flight_table_mp.cpp` 已完成（§454）。下一份按大小：`sv_mapents_mp.cpp`（`57,717` 字节）。
