# 400 · **"缓存键必须含那个状态，否则第二个玩家的实时提示会卡在 `NEED_POWER`"** —— 六级提示优先级、`0x14`/`0x15` 的本地化插值标记、`y 906` 的装备播报

## 一、范围

本报告学习 `sv_main_mp.cpp` 3450–3800 行。

## 二、**六级提示优先级链**（本组最重要的一段）

### 2.1 六级

```text
① 复活/倒地（`reviveTarget || down || zombieTeamWiped`）⇒ 独占，`continue`
② 战利品（`nearestLoot`）⇒ 独占
③ 屏障修复（`repairBarrier`，只在 zm）
④ 普通地图触发器（`SV_PromptableTriggerAt`）
⑤ 工厂特手机（`SV_FactoryPerkTriggerAt`，只在 `factoryPerkMachinesEnabled()`）
⑥ 财宝箱（`treasure_chest_use`，只在 `factoryInteractablesEnabled_`）
```

### 2.2 十层

```text
1. **六级，严格短路**
2. ⇒ **① 最早而 `continue`**（不参与后续）
3. ⇒ **②③ 是"具体的世界对象"**
4. ⇒ **④ 是"地图作者化的触发器"**
5. ⇒ **⑤⑥ 是两个"工厂特例补丁"**
6. ⇒ **所以优先级是：【状态 > 具体对象 > 作者化 > 特例】**
```

**✅ 与 §354 的"`repairableZmBarrierAt` 用 board 的 home 而不是导航节点"**配合。**

**⚠ 而 ④ 的"`SV_PromptableTriggerAt` 带一个输出参数 `&rule`"⇒ **所以返回值与规则分开**。**

**✅ 一个**双输出的查找**。

### 2.3 而 ⑤ 的"固体柜子阻止触碰作者化的 use 外壳"

```php
// OLMOD(factory_perk_machines): solid cabinets prevent touching the
// authored use hull. A bounded machine-only fallback reaches the
// original hull from its accessible edge; other prompts keep priority.
if(!trigger && !nearestLoot && !repairBarrier && mapTriggers_ && alive &&
    world_.factoryPerkMachinesEnabled()) {
    trigger=SV_FactoryPerkTriggerAt(mapTriggers_,playerState->origin,
        StandingPlayerTraceBounds.midpoint,StandingPlayerTraceBounds.halfSize);
    if(trigger)rule=SV_TriggerHintRule(*trigger);
}
```

**⇒ 六层**：

```text
1. **固体柜子阻止触碰【作者化的 use 外壳】**
2. ⇒ **一个【有界的、机柜专用的回退】从它【可达的边缘】到达原始外壳**
3. ⇒ **其它提示【保持优先】**
4. ⇒ **所以是"只在没有别的提示时"**
5. ⇒ **而它【只搜特手机】**
6. ⇒ **⇒ 一个有界的补偿**
```

**✅ 与 §352 的"`factoryInteractablesEnabled_` 的五个 OLMOD"**配合。**

**⚠ 而"从可达的边缘"⇒ **一个几何上的补偿**。**

**✅ 与 §354 的"`RepairRadius = 112`"**同族。

### 2.4 而 ⑥ 的"`reach[0] += 12` 与 `reach[1] += 12`"

```php
auto reach = StandingPlayerTraceBounds.halfSize;
reach[0] += 12; reach[1] += 12;
for(const auto &t: mapTriggers_->triggers) {
    if(t.targetname != "treasure_chest_use") continue;
    if(!SV_MapTriggerTouches(*mapTriggers_, t, playerState->origin,
        StandingPlayerTraceBounds.midpoint, reach)) continue;
    trigger = &t; rule = SV_TriggerHintRule(t); break;
}
```

**⇒ 五层**：

```text
1. **只给 x/y 各加 12**（**z 不变**）
2. ⇒ **所以是"水平放宽"**
3. ⇒ **而只找 `treasure_chest_use`**
4. ⇒ **第一个命中就 `break`**
5. ⇒ **所以是"最近顺序不确定"**（依赖 `triggers` 的数组顺序）
```

**⚠ 而"第一个命中"⇒ **与 ② 的"最近的战利品"**不同**。**

**⇒ 三层**：

```text
② 战利品 ⇒ **取最近的**（显式距离比较）
⑥ 财宝箱 ⇒ **取第一个命中的**（数组顺序）
```

**⚠ 一处**不一致**（一个按距离一个按顺序）。**

**✅ 而理由可能是**财宝箱不重叠**。**

### 2.5 而**"一个死玩家不被提供任何东西"**

```php
// A DEAD PLAYER IS NOT OFFERED ANYTHING. The prompt is an offer to spend
// batteries on something, and the client draws it regardless of pmType.
```

**⇒ 四层**：

```text
1. **一个死玩家不被提供任何东西**
2. ⇒ **提示是一个"花电池在某物上"的邀约**
3. ⇒ **而客户端【不管 `pmType`】都画它**
4. ⇒ **所以必须在服务端拒绝**
```

**✅ 与 §381 的"拒绝而不是钳制"**同族（**第二次"客户端不检查所以服务端必须"）。**

## 三、**六级判定的十项**（本组第二重要）

### 3.1 那段

```php
const auto unopened = trigger && !openedMapTriggers_.contains(trigger->triggerIndex);
const auto ordinaryDoor = unopened && rule &&
    (trigger->targetname == "zombie_door" || trigger->targetname == "zombie_debris") &&
    trigger->noteworthy != "factory_electric_door" &&
    trigger->cost && !trigger->target.empty();
const auto powerSwitch = unopened && rule && !zmPowerOn_ && trigger->targetname == "use_elec_switch";
const auto perk = trigger ? zmPerkMachine(*trigger) : nullptr;
const auto perkOwned = perk && (playerState->perks[perk->word] & perk->mask) != 0;
const auto perkPrompt = unopened && rule && perk && !perkOwned;
const auto ammoBox = rule && trigger && world_.factoryPerkMachinesEnabled() &&
    trigger->noteworthy == "ammobox_trigger";
const auto actionable = ordinaryDoor || powerSwitch || perkPrompt || ammoBox || !interactionHint.empty();
```

### 3.2 十二层

```text
1. **`unopened` = 触发器存在且【未在 `openedMapTriggers_` 里】**
2. ⇒ **`ordinaryDoor` 五项**：
      · `unopened` / `rule` / `targetname ∈ {zombie_door, zombie_debris}`
      · **`noteworthy != "factory_electric_door"`**
      · **`cost` 非零且 `target` 非空**
3. ⇒ **`powerSwitch` 三项**（`unopened` / `rule` / **`!zmPowerOn_`** / `use_elec_switch`）
4. ⇒ **`perk` 由 `zmPerkMachine(*trigger)` 查**（§389）
5. ⇒ **`perkOwned` = 玩家已拥有那个位**
6. ⇒ **`perkPrompt` = `unopened && rule && perk && !perkOwned`**
7. ⇒ **`ammoBox` = `ammobox_trigger` 且工厂特手机启用**
8. ⇒ **`actionable` = 四个之一 或 `interactionHint` 非空**
9. ⇒ **不可行动 ⇒ 清 `trigger` / `rule` / `mapTriggerHintTarget_`**
```

### 3.3 ⭐ **七种 `targetname` 与 `noteworthy`**

```text
targetname:
    zombie_door            普通门
    zombie_debris          碎石门
    use_elec_switch        电源开关
    treasure_chest_use     财宝箱
    zombie_vending         特手机（由 §389 的 `zmPerkMachine` 判）
noteworthy:
    factory_electric_door  （**排除**出普通门）
    ammobox_trigger        弹药箱
```

**✅ 一个**具体的字符串协议**。**

**⚠ 而"`factory_electric_door` 被【排除】出普通门"⇒ **所以它是一个【独立的类别**（由 ⑤ 或别处处理）。**

**✅ 与 §350 的"`noteworthy` 用旁表"**配合。

### 3.4 而**"一个已通电的机柜在开关之前仍可提示"**

```php
// A powered machine is still promptable before the switch: retail
// answers it with ZOMBIE_NEED_POWER. After power it changes to the
// machine's price string, unless this life already owns the perk.
const auto perkPrompt = unopened && rule && perk && !perkOwned;
```

**⇒ 五层**：

```text
1. **一个已通电的机柜在开关之前【仍可提示】**
2. ⇒ **零售用 `ZOMBIE_NEED_POWER` 回答它**
3. ⇒ **通电之后它变成机柜的价格字符串**
4. ⇒ **除非这一世已经拥有那个技能**
5. ⇒ **所以提示文本是三态**
```

**✅ 与 §389 的"四条特手机（含价格）"**完全闭合 ✓

**⚠ 而"这一世"⇒ **所以 `spawnGeneration` 参与**。**

**✅ 与 §362 的"代际"**配合。

## 四、**`0x14` 与 `0x15` 的本地化插值标记**（本组第三重要）

### 4.1 那段

```php
std::string pricedPerkHint;
if(perkPrompt && zmPowerOn_ && world_.factoryPerkMachinesEnabled()) {
    pricedPerkHint = rule->hintString;
    const auto begin = pricedPerkHint.find('\x15'), end = pricedPerkHint.find('\x14');
    if(begin != std::string::npos && end != std::string::npos && end > begin)
        pricedPerkHint.replace(begin+1, end-begin-1,
            std::to_string(SV_FactoryPerkPriceUnits(playerState->perks[0])));
}
```

### 4.2 九层

```text
1. **`rule->hintString` 是一个本地化键，含内嵌的插值标记**
2. ⇒ **`\x15` = 开始，`\x14` = 结束**
3. ⇒ **两者之间是【占位符**】
4. ⇒ **所以替换成价格数字**
5. ⇒ **而守卫是 `begin != npos && end != npos && end > begin`**
6. ⇒ **`replace(begin+1, end-begin-1, ...)`**（**保留两个标记**）
```

**✅ ⭐ **一个"保留标记只换内容"的插值**。**

**⚠ 而 `\x15`/`\x14`⇒ **两个非打印控制字符**。**

**⇒ 三层**：

```text
`\x15` = 0x15 = 21
`\x14` = 0x14 = 20
⇒ **所以是"21 开始 20 结束"**（**倒序！**）
```

**⚠ 一个**反直觉的标记对**（开始 > 结束）。**

**✅ 与 §399 的"`typeByte` `0x15` 或 `>= 0x17`"**同值不同义**（**第二次**）。**

**⇒ **一个容易混淆的地方**。**

### 4.3 而**"每个价格拥有自己的本地化字符串"**

```php
// OLMOD(factory_perk_machines): own a separate localized string per
// price, so one buyer never rewrites another buyer's displayed cost.
```

**⇒ 四层**：

```text
1. **每个价格拥有自己的本地化字符串**
2. ⇒ **所以一个买家【绝不重写】另一个买家的显示成本**
3. ⇒ **因为缓存按【文本】去重**
4. ⇒ **所以不同价格 ⇒ 不同槽**
```

**✅ 与 §399 的"`registerHintString` 按内容去重"**完全闭合 ✓

**⇒ **第二次确认那个去重。**

**⚠ 而"一个买家绝不重写另一个买家"⇒ **一个真实的并发 UI 问题**。**

**✅ 与 §399 的"两个驱动各自只在它们自己的答案变化时行动"**同族。

## 五、**缓存键的完整构造**（本组第四重要）

### 5.1 那段

```php
const auto previous = cursorHintTrigger_.find(client.clientNum);
auto current = nearestLoot
    ? SvLootHintKeyBase | nearestLoot->handle.entityNum
    : (repairBarrier ? 0x40000000u
                     : (trigger ? trigger->triggerIndex : 0xFFFFu));
// The same trigger changes text when power changes. Include that
// state in the cache key so a second player's live prompt cannot
// remain stuck on NEED_POWER after the switch is thrown.
if (perkPrompt) {
    current |= zmPowerOn_ ? 0x00010000u : 0x00020000u;
    if(world_.factoryPerkMachinesEnabled())
        current |= SV_FactoryPerkPriceUnits(playerState->perks[0])<<20;
}
const bool interactionChanged = factoryInteractionHintCache_[client.clientNum] != interactionHint;
factoryInteractionHintCache_[client.clientNum] = interactionHint;
if (!interactionChanged && previous != cursorHintTrigger_.end() && previous->second == current)
    continue;
cursorHintTrigger_[client.clientNum] = current;
```

### 5.2 十二层

```text
1. **一个复合键**：
      · 战利品 ⇒ `SvLootHintKeyBase | entityNum`
      · 屏障 ⇒ `0x40000000`
      · 触发器 ⇒ `triggerIndex`
2. ⇒ **而 `perkPrompt` 再加两项**：
      · **`zmPowerOn_ ? 0x00010000 : 0x00020000`**（**两个位互为相反**）
      · **`SV_FactoryPerkPriceUnits(...) << 20`**
3. ⇒ **所以是"对象 + 状态 + 价格"的三维键**
4. ⇒ **而 `interactionHint` 单独比较**
5. ⇒ **两者都未变 ⇒ `continue`**
```

### 5.3 ⭐⭐ **"缓存键必须含那个状态"**

**✅ 与 §399 的"`cursorHint` 只有一个写入者"**完全闭合 ✓

**⇒ 三层**：

```text
若键只有 `triggerIndex`
⇒ **通电前后是同一个键 ⇒ 不更新 ⇒ 卡在 `NEED_POWER`**
⇒ **⇒ 所以键必须含状态**
```

**✅ ⭐ **一个"缓存键必须覆盖所有影响输出的输入"的标准教训**。**

**⚠ 而"第二个玩家的实时提示"⇒ **所以是**跨客户端**的陈旧**。**

**✅ 与 §399 的"第二个客户端从一个不同瞬间构建的 gamestate 里取值"**同族（**第三次"跨客户端的时序"）。**

### 5.4 而**`0x00010000` / `0x00020000` 的两个位**

**⇒ 三层**：

```text
`zmPowerOn_` ⇒ `0x00010000`（bit 16）
否则         ⇒ `0x00020000`（bit 17）
⇒ **所以是"二选一的两个位"**
```

**⚠ 而"`1u << 16` 与 `1u << 17`"⇒ **一个枚举编码**。**

**✅ 与 §338 的"`abilities.mask` 是六个 uint32 的位集"**不同（这是**一个二值域**）。

### 5.5 而 **`SV_FactoryPerkPriceUnits(...) << 20`**

**⇒ 三层**：

```text
1. **价格左移 20 位**
2. ⇒ **所以占 bit 20+**
3. ⇒ **而 `0x00010000`/`0x00020000` 占 16/17**
4. ⇒ **所以 18/19 空着**
```

**⚠ 而"价格 << 20"⇒ **一个**宽字段**。**

**✅ 与 §389 的"`displayUnits * 1200`"**不同（这是**显示单位**）。

## 六、**`y <offhandWeaponAssetIndex>` 的装备播报**（本组第五重要）

### 6.1 那段

```php
if (!life->second.announced)
{
    // CODREF(1649370): y updates equipped-offhand at cg+C7FB0,
    // which feeds usercmd+18; retail sends y906 on each spawn.
    const auto equipped = world_.playerState(client.clientNum);
    if (equipped)
        life->second.announced = clients_.queueReliableCommand(client.clientNum,
            "y " + std::to_string(equipped->offhandWeaponAssetIndex));
}
```

### 6.2 七层

```text
1. **`y` 更新"已装备副手"在 `cg+C7FB0`**
2. ⇒ **它喂进 `usercmd+18`**
3. ⇒ **而零售在每次出生发 `y906`**
4. ⇒ **所以 `"y " + offhandWeaponAssetIndex`**
5. ⇒ **而 `announced` 是一个每世的标志**
6. ⇒ **所以每世发一次**
```

**✅ 与 §352 的"`a <n>` 与事件 35"**同族（**第四次"可靠命令作为武器通道"）。**

**⚠ 而"`y906`"⇒ **一个具体的号**。**

**✅ 与 §342 的"`packEntityWeapon`"**不同（这是**副手**）。

### 6.3 而**装备授予的四项条件**

```cpp
if (life == equipmentLives_.end() || life->second.xuid != slot.xuid ||
    life->second.spawnGeneration != ps->spawnGeneration ||
    life->second.selectedLoadout != slot.selectedLoadout)
{
    const auto equipment = equipmentLoadoutProvider_ ? equipmentLoadoutProvider_(slot.xuid, slot.selectedLoadout) : std::nullopt;
    if (!equipment || !world_.equipPlayerEquipment(client.clientNum, *equipment)) continue;
    life = equipmentLives_.insert_or_assign(client.clientNum, EquipmentLife{slot.xuid, ps->spawnGeneration, false, slot.selectedLoadout}).first;
}
```

**⇒ 六层**：

```text
1. **四个条件触发【重新解析】**
      · 无记录
      · **`xuid` 变了**
      · **`spawnGeneration` 变了**
      · **`selectedLoadout` 变了**
2. ⇒ **然后调 provider**
3. ⇒ **成功 ⇒ 记 `EquipmentLife`**（含 `announced = false`）
```

**✅ 与 §380 的"`equipPlayerEquipment` 的背包交换"**完全闭合 ✓

**⇒ **第二次确认那条链。**

**⚠ 而"`xuid` 变了"⇒ **所以换人（同一个槽）会重解析**。**

**✅ 与 §362 的"代际"**同族（**第二次"身份 + 代际"双条件**）。

## 七、`addClientXp` 的"gp 随之而来"

```php
// The AAR row carries xp and gp together, so gp is awarded wherever xp
// is; the ratio is the single RECONSTRUCTION POLICY constant in
// sv_scoreboard_mp.hpp. A gp failure is not an xp failure.
static_cast<void>(clients_.addClientGp(clientNum, SV_GpForXp(delta)));
```

**⇒ 五层**：

```text
1. **`AAR` 那一行【同时】携带 `xp` 与 `gp`**
2. ⇒ **所以 `xp` 在哪 `gp` 就在哪**
3. ⇒ **比率是 `sv_scoreboard_mp.hpp` 里【唯一的重建策略常数】**
4. ⇒ **而一个 `gp` 失败【不是**一个 `xp` 失败**
5. ⇒ **所以 `static_cast<void>` 忽略它的返回值**
```

**✅ 与 §355 的"更好的是省略而不是错"**不同（这是**一个派生值**）。**

**⚠ 而"唯一的重建策略常数"⇒ **一个明确标记**。**

**✅ 与 §350 的"`SvActorSendUnmeasuredSpawnWords`"**同族（**标记为未测量）。

## 八、关键结论

1. **⭐⭐ 六级提示优先级链**（① 复活/倒地 ⇒ 独占 `continue` / ② 战利品 / ③ 屏障 / ④ 地图触发器 / ⑤ 特手机 / ⑥ 财宝箱）—— **【状态 > 具体对象 > 作者化 > 特例】**。
2. **"固体柜子阻止触碰作者化的 use 外壳 ⇒ 一个有界的机柜专用回退从可达边缘到达原始外壳，而其它提示保持优先"`**。
3. **⑥ 的 `reach[0] += 12` 与 `reach[1] += 12`**（**只放宽 x/y 不放宽 z**），而**"第一个命中就 break"**（与 ② 的"最近的"**不一致**）。
4. **⭐ "一个死玩家不被提供任何东西：提示是一个花电池的邀约，而客户端【不管 `pmType`】都画它"`** —— 第二次"客户端不检查所以服务端必须"。
5. **⭐ 七种 `targetname`/`noteworthy`**（`zombie_door` / `zombie_debris` / `use_elec_switch` / `treasure_chest_use` / `zombie_vending` / `factory_electric_door`（**排除**）/ `ammobox_trigger`）。
6. **"一个已通电的机柜在开关之前仍可提示：零售用 `ZOMBIE_NEED_POWER` 回答，通电之后变成价格字符串，除非这一世已经拥有"`** —— **三态提示文本**。
7. **⭐⭐ `\x15` = 开始 / `\x14` = 结束** —— **一个反直觉的倒序标记对**（**开始 21 > 结束 20**），而 `replace(begin+1, end-begin-1, ...)` **保留两个标记**。
8. **"每个价格拥有自己的本地化字符串，所以一个买家绝不重写另一个买家的显示成本"`** —— 第二次确认"按内容去重"的后果。
9. **⭐⭐ "缓存键必须含那个状态，否则第二个玩家的实时提示会卡在 `NEED_POWER` 上"`** —— 一个"缓存键必须覆盖所有影响输出的输入"的标准教训。
10. **复合键的三维**：**对象（战利品/屏障/触发器）+ 状态（`zmPowerOn_` 的两个位）+ 价格（`<< 20`）**。
11. **`y <offhandWeaponAssetIndex>` 的装备播报**：**`y` 更新 `cg+C7FB0` 喂进 `usercmd+18`，而零售每次出生发 `y906`** —— 第四次"可靠命令作为武器通道"。
12. **装备授予的四项条件**（无记录 / `xuid` 变 / `spawnGeneration` 变 / `selectedLoadout` 变）—— **身份 + 代际 + 选择的三重**。
13. **"`AAR` 那一行同时携带 xp 与 gp，比率是 `sv_scoreboard_mp.hpp` 里【唯一的重建策略常数】，而一个 gp 失败不是一个 xp 失败"`**。

## 九、未闭合点

- `SV_PromptableTriggerAt` 与 `SV_TriggerHintRule` 的实现。
- `\x14`/`\x15` 标记在本地化资产里的定义。
- `SvLootHintKeyBase` 的值。
- `SV_FactoryPerkPriceUnits` 与 `SV_FactoryPerkTriggerAt` 的实现。
- `SV_GpForXp` 的比率。
- `sv_main_mp.cpp` 3800 行之后未读取。
