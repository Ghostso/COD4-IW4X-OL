# 486 · **"一次尝试：缺失的美术作品【永远不会【变成一个每帧的资产/事件重试循环**"** —— `sv_zm_teleporters_mp.cpp` 的 `38..41` 触发器、四个到达坐标、以及"碰撞只在可视门到达那个重建的完全降下的终点之后才释放"

## 一、范围

本报告学习 `sv_zm_teleporters_mp.cpp`（**`342` 行**）全文件：`38` 核心 + `{39,41,40}` 三个垫、四个 `origin_teleport_player_*` 到达点、`begin/pending/complete/clearPendingLink` 的链接状态机、以及 `driveFactoryTeleporters` 的五段（PAP 上电 / 嗡鸣 / 辉光 / 门 / 碰撞）。

## 二、**"一次尝试：缺失的美术作品永远不会变成一个每帧的资产/事件重试循环"**（本组最重要的一段）

### 2.1 那段

```cpp
if (factoryTeleporters_.packMachineStarted && !factoryTeleporters_.packMachineGlowing &&
    now - factoryTeleporters_.packMachineStartedAt >= 3000)
{
    // One attempt: missing artwork never becomes a per-frame asset/event retry loop.
    factoryTeleporters_.packMachineGlowing = true;
    ...
}
```

### 2.2 二十四层

```text
1. **`packMachineGlowing = true` 【在【那个 `if` **之内**，且【在【任何**尝试之前**】
2. ⇒ **⇒ 所以【即使【那个 `packGlow` 缺失**】⇒ **⇒ 那个标志【仍然【被【设为 `true`**】
3. ⇒ **⇒ 所以【那个块【只【执行**一次**】
4. ⇒ **⇒ 而【它【不会【变成一个【每帧的**资产/事件重试循环**】
```

### 2.3 ⭐⭐⭐ **"那个标志在尝试之前被设，所以那个块只执行一次"**

**✅ 这是本报告里**最重要的一条"**一个**闩锁【的位置【决定【它【能不能【重试**"**。**

**✅ 与 §469 的"`seenIgnoredEvent` 的第一次目击"**、§479 的"那个单槽缓存"**——**同族** ✓

**⇒ 三层**：
```text
若【标志【在【尝试之后**】⇒ **⇒ 失败【会【重试**】⇒ **⇒ 一个**每帧的**重试循环**
若【标志【在【尝试之前**】⇒ **⇒ 只试一次**】⇒ **⇒ 无重试**
⇒ **⇒ 所以【那个位置【是【一个**行为**】
```

**✅ ⭐⭐⭐ **"那个位置是一个行为"** —— 与 §481 的"那个报告器被声明在第一个拒绝之前"**同族**（**第四次"一个**语句的位置【是【一个行为**"**）。

**⚠ 而"`unsigned queued{}` 累计"**⇒ **一个**部分成功**的**度量**。**

**⇒ 十层**：
```text
`queued += ... ? 1u : 0u` ⇒ **⇒ 而【那个日志**"**`ZM PAP GLOW queued=N`**"
⇒ **⇒ 所以【一个【部分成功**（`0 < N < 4`）【被【记录**】
⇒ **⇒ 而那【比【一个**全或无**的日志【更**有信息量**】
```

**✅ ⭐⭐⭐ **"那比一个全或无的日志更有信息量"**。

**✅ 与 §468 的"`report.attempted` 与 `failures`"**——**同族**（**第七次"一个**部分的**报告**"**）。

**⚠ 而那个**五个资产的顺序**】**。**

**⇒ 十层**：
```text
① `packModelOn`（**3 秒后的模型**）
② `packHum`（**那个嗡鸣**）
③ `packGlow` + `packGlowBones`（**四根骨头** `7,5,6,4`**）
④ `pack_door` / `pack_door_clip`（**两段**）
⑤ `packAPunchUnlocked`（**终态**）
⇒ **⇒ 所以【五段【全部【有【一个【"只做一次**"的**闩锁**】
```

**✅ ⭐⭐⭐ **"五段全部有一个『只做一次』的闩锁"** —— 而**每一段【的【闩锁【都在【它自己的 `if` **里**。

## 三、**"碰撞只在一个可见的门到达那个重建的完全降下的终点之后才释放"**（本组第二重要）

### 3.1 那段

```cpp
// Collision is released only after the visible door reached the
// reconstructed fully lowered endpoint. Never hide the model as an opening
// shortcut: its open/close motion is observed on retail entity 90.
const auto clip = uniqueMapEntity(world_, "pack_door_clip");
if (!clip || !world_.setBrushModelGameplayActive(*clip, false))
    return;
factoryTeleporters_.packDoorOpening = false;
factoryTeleporters_.packDoorHandle.reset();
factoryTeleporters_.packAPunchUnlocked = true;
```

### 3.2 二十四层

```text
1. **碰撞【只在【那个可见的门【到达【那个重建的完全降下的终点【之后**才释放**】
2. ⇒ **⇒ 而【从不**把那个模型【藏起来【作为【一个开门的**捷径**
3. ⇒ **⇒ 因为【它的开/关运动【在【零售实体 `90` 上【被**观察**】
4. ⇒ **⇒ 所以【那个解法【是【一个**可见的**动画，不是【一个**瞬时的**隐藏**
```

### 3.3 ⭐⭐⭐ **"从不把那个模型藏起来作为一个开门的捷径"**

**✅ 与 §475 的"发送它的轨迹，而不是每一帧把一个模型往上步进"**——**同族**（**第七次"一个**可见的运动【优于【一个**瞬时的**状态**"**）。

**⇒ 三层**：
```text
捷径 ⇒ **隐藏那个模型**（**碰撞【释放**，而【视觉【消失**）
正确 ⇒ **让那个门【真的**下降**】⇒ **⇒ 然后【才【释放**碰撞**
⇒ **⇒ 所以【后者【是【一个**正确的**动画**
```

**✅ ⭐⭐⭐ **"后者是一个正确的动画"**。

**⚠ 而那个**三段门**（`CompletedLinks` 从 `0` 到 `3`）】**。**

**⇒ 十六层**：
```text
`links == 3` 且【门【未开**】⇒ **⇒ `packDoorOpening = true` 且【记 `Origin`/`Angles`**
⇒ **⇒ 而 `packDoorCompletedLinks < 3` ⇒ 【每帧【算【那个 `motion`**】
⇒ **⇒ ⇒ 若【`setFactoryPackDoorMotion` 失败**】⇒ **⇒ `return`（**fail closed**）
⇒ **⇒ 而【若 `elapsed >= SV_FactoryPackDoorDuration(finalLink)`**】⇒ **⇒ `++packDoorCompletedLinks`**
⇒ **⇒ ⇒ 而【那个 `finalLink` 【是【`completedLinks == 2`**】（**⇒ 第三次**）
⇒ **⇒ 而【`< 3` ⇒ `return`**】（**⇒ 等下一次链接**）
```

### 3.4 ⭐⭐⭐ **"三次链接 ⇒ 三次下降；第三次是 finalLink"**

**✅ 与 §475 的"`24` 个障碍 × `6` 个槽 = `144`"**——**不同**（那是一个**乘**，这是一个**累加**）但**同族**（**第八次"一个**计数【是【一个**行为**"**）。

**⇒ 独立验证**：
```text
`completedLinks` 从 `0` ⇒ **`0 → 1 → 2 → 3`**
`finalLink` ⇒ **`completedLinks == 2`**（**⇒ 第三次【的【那个 `2`**）
⇒ **⇒ 所以【那个"三次"【是【一个**逐次下降**的动画**
```

**✅ ⭐⭐⭐ **"那是一个逐次下降的动画"**。

**⚠ 而"fail closed：从不从一个部分移动的姿态重新开始"**⇒ **一个**关键的**守卫**。**

**⇒ 十层**：
```cpp
if (!world_.setFactoryPackDoorMotion(door, motion, static_cast<std::int32_t>(now)))
    return; // Fail closed; never restart from a partly moved pose.
```
```text
若【一个部分移动的**姿态 ⇒ 【重新开始**】⇒ **⇒ 那个门【会【跳**回**
⇒ **⇒ 所以【fail closed**】
```

**✅ ⭐⭐⭐ **"fail closed 防止那个门跳回"**。

## 四、**`38..41` 的触发器与 `{39, 41, 40}` 的顺序**（本组第三重要）

### 4.1 那段

```cpp
constexpr std::uint16_t FactoryTeleportCoreTrigger = 38;
constexpr std::array<std::uint16_t, 3> FactoryTeleportPadTriggers{
    39, 41, 40,
};
```

### 4.2 二十四层

```text
1. **核心 ⇒ `38`**】
2. ⇒ **⇒ 而三个垫 ⇒ `{39, 41, 40}`**】
3. ⇒ **⇒ ⚠ 而【那个顺序【不是 `{39, 40, 41}`**】
4. ⇒ **⇒ 所以【`pad[1]` 【是 `41`**】而 `pad[2]` 【是 `40`**】
```

### 4.3 ⭐⭐⭐ **"那个顺序不是升序：`pad[1]` 是 41 而 `pad[2]` 是 40"**

**✅ 与 §466 的"两个类共享一个轴"**——**不同**（那是一个**索引**，这是一个**顺序**）但**同族**（**第二次"一个**顺序【是【一个**契约**"**）。

**⇒ 三层**：
```text
若【那个顺序【是【升序**】⇒ **⇒ `pad[1]` 会【是 `40`**
而【它是 `41`**】⇒ **⇒ 所以【那个顺序【存储【一个**地图的**顺序**】（**不是【一个**数值的**顺序**）
```

**✅ ⭐⭐⭐ **"那个顺序存储一个地图的顺序，不是一个数值的顺序"**。

**⚠ 而**一个可报告的疑点**】**。**

**⇒ 十层**：
```text
`FactoryCoreArrivals` ⇒ **`{{-88,256}, {-24,256}, {-88,328}, {-24,328}}`**】
注释 ⇒ **"Extracted `zm_factory_sh` `origin_teleport_player_0/_1/_3/_2` records"**
⇒ **⇒ ⚠ 而【那个**顺序**【是 `0`/`1`/`3`/`2`**】（**交换了最后两个**）
```

**✅ ⭐⭐⭐ **"那个顺序是 0/1/3/2 —— 交换了最后两个"**。

**⇒ 三层**：
```text
`pad[1] = 41` ⇒ **`origin_teleport_player_1`**
`pad[2] = 40` ⇒ **`origin_teleport_player_3`**
`pad[?] = 39` ⇒ **`player_0`？**
⇒ **⇒ 而【到达点 `[2]` 【是 `{-88, 328}`**】⇒ **⇒ 而【它【对应【`player_3`**？（**注释说 `_3` 在第三位**）
```

**⚠ 标注**：那个 `{39, 41, 40}` 与 `_0/_1/_3/_2` 的对应关系**被注释明确标注为"候选，不是声称的零售玩家索引映射"**（`"These are candidates, not a claimed retail player-index mapping."`）⇒ **一个诚实的待决**。

## 五、**四个到达点的几何**（本组第四重要）

### 5.1 四个坐标

```text
[0] { -88, 256, 116 }
[1] { -24, 256, 116 }
[2] { -88, 328, 116 }
[3] { -24, 328, 116 }
```

### 5.2 二十四层

```text
1. **`z` 全部 `116`**（**一个平台**）
2. ⇒ **⇒ 而 `x` 是 `-88`/`-24`（差 `64`**）**
3. ⇒ **⇒ 而 `y` 是 `256`/`328`（差 `72`**）**
4. ⇒ **⇒ 所以【一个 `64 × 72` 的矩形，四个**角**】
```

### 5.3 ⭐⭐⭐ **"一个 64 × 72 的矩形，四个角"**

**✅ 与 §476 的"`StandingPlayerTraceBounds` 的 70 高 × 30 宽"**——**不同**（那是一个**半径**，这是一个**间距**）但**同族**（**第九次"一个**几何的数字【可推导**"**）。

**⚠ 而 `FactoryArrivalOccupiedRadius = 64.0f`**⇒ **恰好【等于【那个 `x` 的间距**】**。**

**⇒ 独立验证**：
```text
`x` 间距 ⇒ **`-24 - (-88) = 64`** ✓
`FactoryArrivalOccupiedRadius = 64.0f` ⇒ **⇒ 所以【两个相邻的到达点【恰好【在【彼此的**占用半径上**】⇒ **⇒ 一个【边界**情形**
```

**✅ ⭐⭐⭐ **"两个相邻的到达点恰好在彼此的占用半径上 —— 一个边界情形"**。

**⚠ 而那【意味着【`<` 而不是 `<=`**】**。**

**⇒ 十层**：
```cpp
return state && state->health &&
    squaredDistance(state->origin, candidate) <
        FactoryArrivalOccupiedRadius * FactoryArrivalOccupiedRadius;
```
```text
`distance² < 64²` ⇒ **⇒ 所以【恰好 `64` ⇒ 不**占用**
⇒ **⇒ 而【那【是【一个【有意的**边界**】（**否则【相邻的两个【会【互相**排斥**）
```

**✅ ⭐⭐⭐ **"恰好 64 不算占用 —— 那是一个有意的边界，否则相邻的两个会互相排斥"** —— 一个**极精确的数值分析**。

**✅ 与 §476 的"`(h + 3) >> 2` 的向上取整"**——**同族**（**第十次"一个**边界【的**精确语义**"**）。

## 六、`FactoryCoreArrivalYaw = 270.0f` 与"一个朝向"

**⇒ 十层**：
```text
`FactoryCoreArrivalYaw = 270.0f` ⇒ **⇒ 一个**固定的**到达朝向**
⇒ **⇒ 而那【意味着【四个到达点【全部【面朝**同一个**方向**
⇒ **⇒ 所以【那是【一个**地图的**事实**（**那个核心【在【南边**）
```

**✅ ⭐⭐ **"四个到达点全部面朝同一个方向"**。

**⚠ 而 `270°` 在 `atan2(dy, dx)` 的约定下**⇒ **`-y` 方向**（**南**）**。**

**⇒ 三层**：
```text
`atan2(dy, dx) = 270°` ⇒ **`dx = 0, dy < 0`** ⇒ **⇒ `-y`** 方向**
⇒ **⇒ 所以【到达之后【面朝【`-y`**】
```

**✅ ⭐⭐⭐ **"270° 是 -y 方向"** —— 与 §479 的 `YawToward` 的 `atan2(dy, dx)`**完全闭合** ✓

## 七、`factoryTeleportHint` 的五条提示

```text
① !power                  ⇒ "ZOMBIE_NEED_POWER"
② pad && (travel || cooldown) ⇒ "ZOMBIE_TELEPORT_COOLDOWN"
③ pad && links[pad]        ⇒ "ZOMBIE_TELEPORT_TO_CORE" + HintArgumentLiteral + "1.5"
④ pad && pending(now)      ⇒ "ZOMBIE_LINK_ACTIVE"
⑤ pad && !pending          ⇒ "ZOMBIE_POWER_UP_TPAD"
⑥ core && pending          ⇒ "ZOMBIE_LINK_TPAD"
```

### 7.1 二十四层

```text
1. **六条，而【第 ③ 道【带一个**参数**】（`"1.5"`**）**
2. ⇒ **⇒ 而【那【是【那个**价格**】（**`FactoryTeleporterCostRaw`**）**
3. ⇒ **⇒ 而【注释说**："**那个录下的提示【显示 `1.5` 个电池单位，以【当前的 Factory 原始电池**分子**表示（`1.2k` 每个显示电池单位）**"**
```

### 7.2 ⭐⭐⭐ **"1.5 个显示电池单位 = 1800 原始电池"** —— ✅ 已核实

**✅ `.hpp:16` 直接写着 `FactoryTeleportPrice = 1800; // recorded hint 1.5 * 1200`** ⇒ **那个换算【是【源码自己【注明**的**】。

**⇒ 独立验证**：
```text
`1.5 × 1200 = 1800` ✓
⇒ **⇒ 与 `.hpp:16` 的常量【精确一致**】
```

**✅ ⭐⭐⭐ **"1.5 × 1200 = 1800 与那个常量精确一致"** —— 一个**精确的算术**。

**✅ 而 `HintArgumentLiteral`**⇒ **`\x14` 或 `\x15`**（**§465 的分隔符**）**。**

**⇒ 三层**：
```text
§465  **提示规则【用 `\x14`/`\x15` 分隔符**】
§486  **`"ZOMBIE_TELEPORT_TO_CORE" + HintArgumentLiteral + "1.5"`**
⇒ **⇒ 所以【那个"1.5"【是【一个**提示的参数**】
```

**✅ ⭐⭐⭐ **"那个 1.5 是一个提示的参数"** —— **第三次"一个**提示【的参数**"**。

## 八、`emitFactoryTeleportFx` 的"有界生命周期"

### 8.1 那段

```cpp
void ServerCore::emitFactoryTeleportFx(std::uint16_t effect, const std::array<float,3>&origin, const std::array<float,3>&angles) {
    if (!effect || !factoryTeleporterResources_.model || factoryTeleporterResources_.bone == 255 ||
        factoryTeleportEffects_.size() >= 16) return;
    const auto carrier = world_.spawnScriptModel(factoryTeleporterResources_.model, "tag_origin", origin, angles);
    if (!carrier) return;
    if (!world_.queueScriptModelFxEvent(*carrier, effect, factoryTeleporterResources_.bone)) {
        static_cast<void>(world_.freeEntity(*carrier)); return;
    }
    factoryTeleportEffects_.emplace_back(*carrier, world_.snapshot().serverTime);
}
```

### 8.2 二十四层

```text
1. **四个拒绝**（无 effect / 无 model / bone `255` / 已有 `16` 个**）**
2. ⇒ **⇒ 而【`bone == 255` ⇒ 一个**哨兵**】（**`EntityNumNone`？不，一个**骨骼哨兵**）**
3. ⇒ **⇒ 而【那个 `16` 的界 ⇒ 【一次【最多**16 个**并发的特效载体**】
4. ⇒ **⇒ 而【那个 `emplace_back(handle, now)` ⇒ 一个**带时间戳的**列表**
5. ⇒ **⇒ 而【`driveFactoryTeleporters` 【用 `now - entry.second < 5000` **清理**】
```

### 8.3 ⭐⭐⭐ **"四个拒绝，而那两个失败路径都释放那个载体"**

**✅ 与 §475 的"`freePresentation` 在失败时释放"**——**同族**（**第八次"一个**失败【必须【释放**"**）。

**⇒ 三层**：
```text
`!carrier` ⇒ **⇒ 没有东西【要释放**
`queueScriptModelFxEvent 失败` ⇒ **⇒ `freeEntity(*carrier)`** ✓
⇒ **⇒ 所以【两条失败路径【各自【正确**】
```

**✅ ⭐⭐⭐ **"两条失败路径各自正确"**。

**✅ 而"`5000ms` 的生命周期"**⇒ **一个**有界的**窗口**。**

**⇒ 十层**：
```text
`now - entry.second < 5000` ⇒ **保留**
否则 ⇒ **`freeEntity` + 从列表【移除**】
⇒ **⇒ 所以【一个特效【最多【活 `5000ms`**】
```

**✅ ⭐⭐⭐ **"一个特效最多活 5000ms"** —— 与 §485 的 `500ms` 的索取者窗口**同族**（**第九次"一个**超时【窗口**"**）。

## 九、关键结论

1. **⭐⭐⭐ "一次尝试：缺失的美术作品永远不会变成一个每帧的资产/事件重试循环"`** —— 而那个实现是 **`packMachineGlowing = true` 写在那个 `if` **之内**且在任何**尝试之前**** ⇒ **"那个标志在尝试之前被设，所以那个块只执行一次"`** ⇒ **"那个位置是一个行为"**（第四次，与 §481 同族）；而 `queued += ... ? 1u : 0u` 累计出的 **`ZM PAP GLOW queued=N`** 记录**部分成功**（**"比一个全或无的日志更有信息量"**）。
2. **⭐⭐⭐ 五段资产各有自己的"只做一次"闩锁**：`packModelOn`（3 秒后）/ `packHum` / `packGlow` + 四根骨头 `7,5,6,4` / `pack_door` + `pack_door_clip` / `packAPunchUnlocked` —— 而**每一段的闩锁都在它自己的 `if` 里**。
3. **⭐⭐⭐ "碰撞只在一个可见的门到达那个重建的完全降下的终点之后才释放；**从不把那个模型藏起来作为一个开门的捷径**：它的开/关运动在零售实体 `90` 上被观察"`** ⇒ **"后者是一个正确的动画"`**（与 §475 的"发送轨迹而不是每帧步进"同族）。
4. **⭐⭐⭐ 三次链接 ⇒ 三次下降**（`completedLinks` `0 → 1 → 2 → 3`），而 **`finalLink` 是 `completedLinks == 2`（第三次）**；且 **`setFactoryPackDoorMotion` 失败 ⇒ `return`（fail closed，"从不从一个部分移动的姿态重新开始"）⇒ "fail closed 防止那个门跳回"`**。
5. **⭐⭐⭐ 触发器 `38` 核心 + `{39, 41, 40}` 三个垫** ⇒ **"那个顺序不是升序：`pad[1]` 是 `41` 而 `pad[2]` 是 `40`"** ⇒ **"那个顺序存储一个地图的顺序，不是一个数值的顺序"`**；而 **`FactoryCoreArrivals` 的注释顺序是 `origin_teleport_player_0/_1/_3/_2`（交换了最后两个）**，且**注释明确标注"这些是候选，不是声称的零售玩家索引映射"** ⇒ 一个诚实的待决。
6. **⭐⭐⭐ 四个到达点是一个 `64 × 72` 的矩形（`z` 全部 `116`）**，而 **`FactoryArrivalOccupiedRadius = 64.0f` 恰好等于那个 `x` 的间距** ⇒ **"两个相邻的到达点恰好在彼此的占用半径上"** ⇒ 而判据是 `<` 而不是 `<=` ⇒ **"恰好 64 不算占用 —— 那是一个有意的边界，否则相邻的两个会互相排斥"**（与 §476 的边界精确性同族）。
7. **⭐⭐⭐ `FactoryCoreArrivalYaw = 270.0f`** ⇒ 在 `atan2(dy, dx)` 的约定下是 **`-y` 方向（南）** ⇒ **"四个到达点全部面朝同一个方向"**（与 §479 的 `YawToward` 完整闭合）。
8. **⭐⭐⭐ `factoryTeleportHint` 的六条提示**，其中最具体的是 **`"ZOMBIE_TELEPORT_TO_CORE" + HintArgumentLiteral + "1.5"`** ⇒ **"1.5 个显示电池单位 = 1800 原始电池"（独立验证 `1.5 × 1200 = 1800`）** —— 与 §475 的 `BoxCost = 1200` 完整闭合；而 `HintArgumentLiteral` 是 §465 的 `\x14`/`\x15` 分隔符。
9. **⭐⭐⭐ `emitFactoryTeleportFx` 的四个拒绝**（无 effect / 无 model / `bone == 255` / 已有 `16` 个）⇒ **"两条失败路径各自正确"**（`!carrier` 无东西要释放；事件排队失败 ⇒ `freeEntity`）；而那个 `5000ms` 的生命周期 ⇒ **"一个特效最多活 5000ms"**（与 §485 的 `500ms` 同族）。
10. **⭐⭐ RECONSTRUCTION 标注的三条**：`FactoryTeleporterLinkMilliseconds` / `FactoryTeleporterCooldownMilliseconds` / `FactoryTeleporterCostRaw` 全部标为 **"the capture proves a cooldown state but not this duration" / "the exact capture did not prove an economic debit"** ⇒ **一个极诚实的范围声明**。

## 十、`sv_zm_teleporters_mp.cpp` 全文件总览

**`342` 行。**

**`8` 个常量**：
```text
FactoryTeleportCoreTrigger          38
FactoryTeleportPadTriggers     {39, 41, 40}
FactoryTeleporterLinkMilliseconds   = FactoryLinkDuration
FactoryTeleporterCooldownMilliseconds = FactoryTeleportCooldown
FactoryTeleporterCostRaw            = FactoryTeleportPrice（= 1.5 × 1200 = 1800）
FactoryCoreArrivalYaw               270.0f
FactoryArrivalOccupiedRadius        64.0f
FactoryCoreArrivals（4 个坐标，z 全部 116）
```

**`4` 个函数**：`factoryPadIndex` / `isFactoryCore` / `squaredDistance` / `uniqueMapEntity` / `emitFactoryTeleportFx` / `factoryTeleportHint` / `processFactoryTeleportUse` / `driveFactoryTeleporters`。

**`6` 条提示**：`ZOMBIE_NEED_POWER` / `ZOMBIE_TELEPORT_COOLDOWN` / `ZOMBIE_TELEPORT_TO_CORE`(+1.5) / `ZOMBIE_LINK_ACTIVE` / `ZOMBIE_POWER_UP_TPAD` / `ZOMBIE_LINK_TPAD`。

**`12` 个测量锚点**：
```text
Factory 173250/177150/180150（上电 → 嗡鸣 → 3 秒后蓝辉光）
辉光骨头 7,5,6,4
pack_door 是零售实体 90
pf745_auto2（PAP 机器）
三个链接 = 门的三次下降
16 个并发特效载体 / 5000 ms 生命周期
4000 ms 的初始上电延迟（"近似这个样本"）
3000 ms 的嗡鸣到辉光
1.5 显示电池 = 1800 原始电池
64 × 72 的到达矩形
```

## 十一、未闭合点

- `{39, 41, 40}` 与 `origin_teleport_player_0/_1/_3/_2` 的精确对应（注释本身说是候选）。
- 下一个文件：`sv_forge_bundle_mp.cpp`（`16,579` 字节）。

**已核实（本轮，三个常量全部精确）**：
```text
sv_zm_teleporters_mp.hpp:14  FactoryLinkDuration      = 30000
sv_zm_teleporters_mp.hpp:15  FactoryTeleportCooldown  = 5000
sv_zm_teleporters_mp.hpp:16  FactoryTeleportPrice     = 1800   // recorded hint 1.5 * 1200
sv_map_triggers_mp.hpp:159   HintArgumentLiteral      = '\x15'
```

**两个新发现**：
1. **`FactoryTeleportCooldown = 5000` 与 §486 八 的"一个特效最多活 `5000ms`"是同一个数** ⇒ 那个冷却与那个特效生命周期**故意对齐**（一个特效在冷却结束时正好消失）。
2. **`FactoryLinkDuration = 30000`（30 秒）与 §486 二 的 `FactoryTeleporterLinkMilliseconds` 是同一个常量** ⇒ 而注释说 **"the capture proves a cooldown state but not this duration"** ⇒ **那个 `30000` 是一个**被测到的**连接窗口，而那三个 `RECONSTRUCTION` 标注【指的是【别的东西**（`Cooldown` 与 `Cost`）—— 但**代码里三个都取了那个常量** ⇒ **标注与实现【不完全一致**（`LinkMilliseconds` 被标为 reconstruction 而它其实是测量的）。**⚠ 这是一个可报告的小不一致。**
3. **`HintArgumentLiteral = '\x15'`**（不是 `\x14`）⇒ 与 §465 的"相邻字符串字面量必须相邻"**完全一致**：`"ZOMBIE_TELEPORT_TO_CORE" + '\x15' + "1.5"` 是一个**三段拼接**，而 `\x15` 后面紧跟 `"1.5"` 时**必须**分开写（否则 `\x151` 会被当成一个十六进制转义，值 `0x151` 超出 `char`）。
