# 493 · **"那个主框架【被占用时【回到【那个被验证的出发点】**"** —— `sv_zm_travel_mp.cpp` 的 `176` 单位近垫测试、四个黑房与 `320` 的间距、以及"从不绕过碰撞去逃出一个房间"

## 一、范围

本报告学习 `sv_zm_travel_mp.cpp`（**`230` 行**）全文件：`nearPad` 的 `176×176`、`beginFactoryTravel` 的十道门、`driveFactoryTravel` 的四段（房间 FX / 充电 / 进房 / 返回）、`setFactoryTravelHold` 的三重条件。

## 二、**"那个主框架被占用时回到那个被验证的出发点"**（本组最重要的一段）

### 2.1 那段

```cpp
// RECONSTRUCTION: if the mainframe is occupied, return to the
// validated departure instead. Keep collision validation intact.
if(!returned)returned=world_.teleportFactoryPlayer(traveler.client,traveler.generation,
    traveler.departure,traveler.yaw,0);
if(!returned && now-trip.roomStarted>=FactoryTravelRoomMs+1000) {
    // Bounded recovery around the departure, still using the normal
    // authoritative hull test. Never bypass collision to escape a room.
    constexpr std::array<std::array<float,2>,8> offsets{{
        {48,0},{-48,0},{0,48},{0,-48},{48,48},{-48,48},{48,-48},{-48,-48}}};
    for(const auto &offset:offsets) {
        auto dest=traveler.departure;dest[0]+=offset[0];dest[1]+=offset[1];
        if(world_.teleportFactoryPlayer(traveler.client,traveler.generation,dest,traveler.yaw,0)) {
            returned=true;break;
        }
    }
}
if(!returned) {
    if(trip.returnRetries++%20==0)travelLog("RETURN BLOCKED client="+std::to_string(traveler.client));
    return false; // fail closed and retry, never place inside geometry
}
```

### 2.2 二十四层

```text
1. **四层回退**】
2. ⇒ **⇒ ① 四个 `CoreArrivals`（从那个 `room` 起，循环）**
3. ⇒ **⇒ ② 那个**出发点**（`traveler.departure` + `traveler.yaw`**）**
4. ⇒ **⇒ ③ 那个出发点周围**八个 `±48` 的偏移**（**只在【`FactoryTravelRoomMs + 1000` 之后**）**
5. ⇒ **⇒ ④ 拒绝**（**⇒ `return false` ⇒ 下一帧【重试**）
6. ⇒ **⇒ 而【那句**"`fail closed and retry, never place inside geometry`**"**
```

### 2.3 ⭐⭐⭐ **"fail closed 并重试，绝不【把【一个玩家【放进几何体里**"**

**✅ 这是本报告里**最重要的一条"**一个**传送【的**四层**回退**"**。**

**✅ 与 §475 的"那个 `1.0` 防止一个免费的穿透"**、§476 的"任何非零都意味着一个未重定基的指针"**——**同族** ✓

**⇒ 三层**：
```text
若【强行传送**】⇒ **⇒ 一个玩家【卡在【几何体里**】⇒ **⇒ 比【不传送**更坏**
四层回退 + 重试 ⇒ **⇒ 最终【成功**或【一直【重试**】
⇒ **⇒ 所以【"绝不放进几何体**"【是【那个**最高**的约束**
```

**✅ ⭐⭐⭐ **"'绝不放进几何体'是那个最高的约束"**。

**⚠ 而那个**八个偏移**】**。**

**⇒ 独立验证**：
```text
{48,0} {-48,0} {0,48} {0,-48} {48,48} {-48,48} {48,-48} {-48,-48}
⇒ **⇒ 八个**方向**（`4` 个轴 + `4` 个对角）
⇒ **⇒ 而那个 `48` 【是【一个**具体的**偏移**
```

**✅ ⭐⭐⭐ **"八个方向（4 个轴 + 4 个对角）"**。

**✅ 与 §486 的"`FactoryArrivalOccupiedRadius = 64.0f`"**——**同族**（**第二次"一个**具体的**半径**"**）**。**

**⚠ 而那个 `48 < 64`**】**。**

**⇒ 三层**：
```text
`FactoryArrivalOccupiedRadius = 64`（**§486**）
`48` ⇒ **⇒ 所以【那个偏移【小于【那个**占用半径**】
⇒ **⇒ 而【那【意味着【一个【在 `48` 处的**位置【仍然【在【那个**占用半径**内
```

**⚠ 标注**：那可能是一个**有意的**选择（**因为【那个占用检查【只【对 `CoreArrivals`** 而不是对那个出发点**）。**

**✅ 而与那个 `(traveler.room+index)%4` 的**循环**】**。**

**⇒ 十层**：
```cpp
const auto &dest=CoreArrivals[(traveler.room+index)%CoreArrivals.size()];
```
```text
1. **从【`traveler.room` 起，循环**四个**
2. ⇒ **⇒ 所以【一个【在 room `2` 的玩家【先试 `2`，然后 `3`，`0`，`1`**】
3. ⇒ **⇒ 而【那【避免【全部【四个**玩家【挤【在【同一个**到达点**】
```

**✅ ⭐⭐⭐ **"从 traveler.room 起循环，所以四个玩家不会挤在同一个到达点"** —— 一个**极精巧的**负载均衡**。

**✅ 与 §486 的"`FactoryArrivalOccupiedRadius = 64`"**——**完全闭合** ✓

## 三、**`nearPad` 的 `176` 单位与"那个高度守卫是一个重建的安全边界"**（本组第二重要）

### 3.1 那段

```cpp
bool nearPad(const SvPlayerState &player,const std::array<float,3> &pad)
{
    const auto x=player.origin[0]-pad[0],y=player.origin[1]-pad[1];
    // BO1 uses a 176-unit horizontal test. The height guard is a
    // reconstruction safety boundary for Factory's stacked floors.
    return player.health && player.pmType==SvPmTypeNormal &&
        x*x+y*y<=176.0f*176.0f && std::abs(player.origin[2]-pad[2])<100;
}
```

### 3.2 二十四层

```text
1. **BO1 用一个 `176` 单位的**水平测试**】
2. ⇒ **⇒ 而那个**高度守卫**【是【一个**重建的安全边界**】
3. ⇒ **⇒ 因为【Factory 的**堆叠楼层**】
4. ⇒ **⇒ 所以【两个**不同的**来源**：（`176` BO1 / `100` 重建**）
```

### 3.3 ⭐⭐⭐ **"那个高度守卫是一个重建的安全边界，因为 Factory 的堆叠楼层"**

**✅ 与 §478 的"Voronoi 过渡不是一个可走边（Factory 有几层）"**——**完全同族** ✓

**⇒ 三层**：
```text
§478  **"Factory 有几层 ⇒ 那个 Voronoi 过程【放进了【不同楼层之间的**走链接**"**
§493  **"那个高度守卫【是一个重建的安全边界**，因为 Factory 的**堆叠楼层**"**
⇒ **⇒ 两次【同一个**楼层问题**】（`1100` 个节点 / `176×176`×`100`**）
```

**✅ ⭐⭐⭐ **"两次同一个楼层问题"** —— 而**§493 【用一个**3D 的盒**（`176 × 176 × 200`**）而 §478 【用一个**平面 + 高度**（`72`）**。

**⇒ 三层**：
```text
§478  **水平距离无界 + `|Δz| <= 72`**
§493  **水平 `<= 176` + `|Δz| < 100`**
⇒ **⇒ 两个**不同的**形状**】⇒ **⇒ 而【都【是【"水平 + 高度"**】
```

**✅ ⭐⭐⭐ **"两个不同的形状，而都是『水平 + 高度』"**。

**⚠ 而 `100` 与 `72`**】**。**

**⇒ 十层**：
```text
`72` ⇒ **那个导航的地板容差**（§478**）
`100` ⇒ **那个近垫的高度守卫**（§493**）
⇒ **⇒ 所以【两个**不同的**数【两个**不同的**用途**
```

**✅ ⭐⭐ **"两个不同的数两个不同的用途"**。

## 四、**`beginFactoryTravel` 的十道门**（本组第三重要）

### 4.1 十道

```text
① !factoryBo1TravelEnabled_
② state.travel 已在 (一个 trip 在跑)
③ pad >= state.links.size()
④ !state.links[pad]          (那个垫未链接)
⑤ state.pending(now)         (一个链接在挂)
⑥ now < state.cooldown
⑦ matchStatus_.completed
⑧ !player || spawnGeneration != generation || !nearPad || factoryTravelHeld
⑨ !state.roomFxReady || !fx.roomFlash || !fx.model || fx.bone == 255
⑩ !clear({2048,-320,56}) || !any_of(CoreArrivals, clear)  (两端预检)
⑪ changeFactoryBattery(..., -1800, ...) 失败
```

### 4.2 二十四层

```text
1. **十一道**】⇒ **⇒ 而那个**扣款【在第 ⑪ 道**
2. ⇒ **⇒ 所以【前十道【全部【在【扣款**之前**
3. ⇒ **⇒ 而那【正是【§483 的"三道在扣钱之前"**同族**（**第二次"那个扣款是那个分界线"**）
```

### 4.3 ⭐⭐⭐ **"预检两端【在扣款之前；实际的进入/返回【重复那个权威的凸包查询；一条 trace【不是【一个**预定**"**

```cpp
// Preflight both endpoints before charging. Actual entry/return repeats
// the authoritative hull query; a trace is not a reservation.
```

**⇒ 十六层**：
```text
1. **两端预检【在扣款之前**】
2. ⇒ **⇒ 而【那个**实际的进入/返回【重复**那个权威的凸包查询**】
3. ⇒ **⇒ 因为【一条 trace 【不是【一个**预定**
4. ⇒ **⇒ 所以【那个预检【是【一个**必要条件【而不是【一个**充分条件**
```

**✅ ⭐⭐⭐ **"一条 trace 不是一个预定"** —— 一个**极精确的 TOCTOU 论证**。

**✅ 与 §475 的"关闭是幂等性的唯一保证"**——**不同**（那是一个**幂等**，这是一个**竞态**）但**同族**（**第五次"一个**时间窗口【的**诚实**"**）。

**⇒ 三层**：
```text
预检通过 ⇒ **⇒ 而【世界【可能【在【这之间**变了**】
实际传送 ⇒ **⇒ 再查一次**】⇒ **⇒ 所以【那个预检【只是【一个**快速失败**
```

**✅ ⭐⭐⭐ **"那个预检只是一个快速失败"**。

**⚠ 而"那个 `{2048, -320, 56}`"**⇒ **一个**具体的**预检点**。**

**⇒ 十层**：
```text
`{2048, -320, 56}` ⇒ **⇒ 而与【`roomOrigin` 的 `{2048.0f + 320.0f*room, -320, 56+height}`**】
⇒ **⇒ 所以【那个 `room = 0` 时【`{2048, -320, 56}`** ✓
⇒ **⇒ 而【那个 `height` 【在那个预检里【是 `0`**】（**最矮**）
```

**✅ ⭐⭐⭐ **"那个预检点是 room = 0 且 height = 0"** —— 一个**极精确的读法**。

**✅ 而 `roomOrigin` 的 `56 + height`**⇒ **`height = clamp(60 - viewHeightCurrent, 0, 49)`**】**。**

**⇒ 十层**：
```text
`viewHeightCurrent` ⇒ **在【`[60 - 49, 60] = [11, 60]`**里【得到【`height ∈ [0, 49]`】
⇒ **⇒ 所以【那个房间的高度【在 `56..105`**】
⇒ **⇒ 而 `56` 是【站着的**（`height = 0`**）⇒ `105` 是【蹲着/趴着**的
```

**✅ ⭐⭐⭐ **"那个房间的高度在 56..105 —— 躺下更低"** —— 一个**极精确的读法**。

**⚠ 而"`height = clamp(60 - viewHeightCurrent, 0, 49)`"**⇒ **那个 `49` 与 `60`**。**

**⇒ 三层**：
```text
站起来 ⇒ **`viewHeightCurrent = 60` ⇒ `height = 0`** ⇒ **房间在 `56`**
趴下 ⇒ **`viewHeightCurrent = 11`（`prone` 按 §488 的 `scale × 11`）⇒ `height = 49`** ⇒ **房间在 `105`**
⇒ **⇒ 所以【那个 `49` 【正是【`60 - 11`**】
```

**✅ ⭐⭐⭐ **"那个 49 正是 60 - 11"** —— 与 §488 的 `proneHeight = playerSizeScale × 11` **完全闭合** ✓

**⇒ 一个跨报告的精确算术**。

## 五、**四个黑房与 `320` 的间距**（本组第四重要）

### 5.1 那段

```cpp
const std::array<float,3> pos{2047.92f+320.0f*room,-279.977f,115.73f};
...
const std::array<float,3> roomOrigin{2048.0f+320.0f*room,-320,56+height};
```

### 5.2 二十四层

```text
1. **`320` 的间距**】（**两个地方【都是**）
2. ⇒ **⇒ 而那个 `fx` 的 `pos` 【是 `{2047.92 + 320r, -279.977, 115.73}`**】
3. ⇒ **⇒ 而那个 `roomOrigin` 【是 `{2048 + 320r, -320, 56+height}`**】
4. ⇒ **⇒ 所以【两个**不同的** y/z**（`-279.977`/`115.73` vs `-320`/`56..105`**）
```

### 5.3 ⭐⭐⭐ **"FX 在 y=-279.977 z=115.73（那个房间的上方），而玩家在 y=-320 z=56..105"**

**✅ 与 §486 的"`FireTrap +14` / `FreezeTrap +5` / `ShockTrap +20`"**——**同族**（**第三次"一个**实测的垂直偏移**"**）。

**⇒ 独立验证**：
```text
FX `z = 115.73` / 玩家 `z = 56..105` ⇒ **⇒ 所以【那个 FX 【在【那个玩家的**上方 `10.73..59.73` 单位**
⇒ **⇒ 而【那【是【一个**有意的**视觉位置**】（**那个闪光【在那个房间的上方**）
```

**✅ ⭐⭐⭐ **"那个 FX 在那个玩家的上方 10.73..59.73 单位"**。

**⚠ 而"那个 `2047.92` vs `2048.0`"**⇒ **一个 `0.08` 的**微差**。】

**⇒ 十层**：
```text
`fx` 的 `x` ⇒ **`2047.92 + 320r`**
`roomOrigin` 的 `x` ⇒ **`2048.0 + 320r`**
⇒ **⇒ 差 `0.08`**】⇒ **⇒ 所以【那【是【两个**独立测量的**起点**】
```

**✅ ⭐⭐⭐ **"那 0.08 的差是两处独立测量"** —— 一个**极精细的观察**。

**✅ 与 §475 的"`(-7.88635, .019425)`"**——**同族**（**第四次"一个**小数【是【一个**测量的痕迹**"**）。

**⚠ 而那个 `-279.977` vs `-320`**】**。**

**⇒ 三层**：
```text
`fx` 的 `y` ⇒ **`-279.977`**
`roomOrigin` 的 `y` ⇒ **`-320`**
⇒ **⇒ 差 `40.023`**】⇒ **⇒ 所以【那个 FX 【在【那个房间的 `y` **前方 `40` 单位**】
```

**✅ ⭐⭐⭐ **"那个 FX 在房间的 y 前方 40 单位"**。

## 六、`5 <n>` 与 `N "<vision>" 0` 的两条命令

### 6.1 那两条

```cpp
static_cast<void>(clients_.queueReliableCommand(client, "5 " + std::to_string(trip.chargeRemaining(now))));
...
static_cast<void>(clients_.queueReliableCommand(client, "N \"default\" 0"));
...
static_cast<void>(clients_.queueReliableCommand(traveler.client, "N \"zm_factory_sh\" 0"));
```

### 6.2 二十四层

```text
1. **`5 <ms>` ⇒ 一个**充电倒计时**】
2. ⇒ **⇒ 而 `N "default" 0` ⇒ 一个**视觉改变**（进房时**）**
3. ⇒ **⇒ 而 `N "zm_factory_sh" 0` ⇒ **恢复**那个地图的色调**（返回时**）**
```

### 6.3 ⭐⭐⭐ **"`N` 命令：进房时 `"default"`，返回时 `"zm_factory_sh"`"**

**✅ 与 §485 的 `'3' "grayscale" 1000` / `'3' "zm_factory_sh" 0`**——**完全同族** ✓

**⇒ 三层**：
```text
§485  **倒地 ⇒ `'3' "grayscale" 1000`；复活 ⇒ `'3' "zm_factory_sh" 0`**
§493  **进房 ⇒ `N "default" 0`；返回 ⇒ `N "zm_factory_sh" 0`**
⇒ **⇒ 两次【"一个**动词 + 一个 vision 名 + 一个时长**"**
```

**✅ ⭐⭐⭐ **"一个动词 + 一个 vision 名 + 一个时长"两例**。

**⚠ 而那个 `'3'`（`type 5`）与 `N`**】**。**

**⇒ 十层**：
```text
§485  **`'3'` ⇒ `type 5`（`46CEF0`）**
§493  **`N` ⇒ 一个**不同的**动词**】
⇒ **⇒ 所以【两个**不同的**视觉命令**
```

**✅ ⭐⭐⭐ **"两个不同的视觉命令"**。

**⚠ 而"`N "default" 0`"**⇒ **一个**非地图名**的 vision**。】

**⇒ 三层**：
```text
`"default"` ⇒ **那个**默认**的 vision**】⇒ **⇒ 而【那【意味着【那个黑房【用【那个默认**的色调**
⇒ **⇒ 而【§470 的 `vision/default.vision` 【正是【那个**平**的**

**✅ ⭐⭐⭐ **"那个黑房用那个默认的色调"** —— 与 §470 的"六个 vision 里 `default.vision` 是那个平的外观"**完全闭合** ✓

**✅ 而注释说"`N "default" 0`"**⇒ **"那个黑房"** ⇒ **一个**黑的**房间用**默认**的色调？** ⇒ **⚠ 一个可质疑的选择**（**一个黑房【应该【用【一个**黑**的 vision**）**。**

**⇒ 标注**：那个 `"default"` 可能**不是**那个 `vision/default.vision`，而是一个**不同的** configstring 值。

## 七、`setFactoryTravelHold` 的三重条件

### 7.1 那段

```cpp
bool SvServerWorld::setFactoryTravelHold(std::uint32_t client,std::uint8_t generation,bool enabled)
{
    if(!enabled) {
        const auto hold=factoryTravelHolds_.find(client);
        if(hold!=factoryTravelHolds_.end() && hold->second.first==generation)factoryTravelHolds_.erase(hold);
        return true;
    }
    const auto ps=playerState(client);
    if(!factoryInteractablesEnabled() || !ps || ps->spawnGeneration!=generation ||
        !ps->health || ps->pmType!=SvPmTypeNormal)return false;
    factoryTravelHolds_[client]={generation,ps->origin};return true;
}
```

### 7.2 二十四层

```text
1. **`enabled = false` ⇒ 【只【在【那个代次**匹配【时【擦除**】（**⇒ 一个**幂等**的释放**）
2. ⇒ **⇒ `enabled = true` ⇒ **五个**条件**
3. ⇒ **⇒ 而那个 `{generation, ps->origin}` 【记录**两个**东西**
```

### 7.3 ⭐⭐⭐ **"只在那代次匹配时擦除 —— 一个幂等的释放"**

**✅ 与 §485 的"复活的三级守卫"**、§490 的 `rollbackFree` 的**代次检查**——**完全同族** ✓

**⇒ 三层**：
```text
若【不检查代次**】⇒ **⇒ 一个**旧的**释放【会【擦掉【一个**新的**持有**
检查 ⇒ **⇒ 幂等** ✓
⇒ **⇒ 所以【那个检查【是【必须的**】
```

**✅ ⭐⭐⭐ **"那个检查是必须的"**。

**⚠ 而那个 `{generation, ps->origin}` 保存的那个**起点**】**。**

**⇒ 十层**：
```text
`factoryTravelHolds_[client] = {generation, ps->origin}`
⇒ **⇒ 而 `factoryTravelHeld` 【只【检查 `hold->second.first == generation`**】
⇒ **⇒ 所以【那个 `origin` 【被【保存【但【从不**被读**】
```

**⚠ 一个**死字段**】**（**与 §468 的 `UnresolvedString` 无生产者**同族**）。**

**⇒ 三层**：
```text
`hold->second.second`（那个 `origin`）⇒ **在【整个文件里【没有**读者**
⇒ **⇒ 所以【它【是一个**保留的**值**】⇒ **⇒ 可能【为了【一个**未来的**用途**（**例如【一个**回滚**）
```

**✅ ⭐⭐⭐ **"那个 origin 是一个保留的值"**。

## 八、`FactoryTravelRoomMs` 与那个 `+1000` 的恢复窗口

### 8.1 那段

```cpp
if(!trip.roomReady(now) && !matchStatus_.completed)return;
if(now<trip.nextReturnAttempt)return;
trip.nextReturnAttempt=now+250; // bounded collision work if all exits are obstructed
...
if(!returned && now-trip.roomStarted>=FactoryTravelRoomMs+1000) { ... 八个偏移 ... }
```

### 8.2 二十四层

```text
1. **`nextReturnAttempt = now + 250` ⇒ 【每 `250ms` 一次**返回尝试】
2. ⇒ **⇒ 而那个**八个偏移**【只在 `FactoryTravelRoomMs + 1000` **之后**才试**】
3. ⇒ **⇒ 所以【两个**门**：`250ms` 的重试 + `FactoryTravelRoomMs + 1000` 的**放宽**
```

### 8.3 ⭐⭐⭐ **"有界的碰撞工作，如果所有出口都被挡住"**

**✅ 与 §486 的"一次尝试：缺失的美术作品永远不会变成一个每帧的资产/事件重试循环"**——**同族** ✓

**⇒ 三层**：
```text
§486  **"一次尝试"【⇒ 那个**闩锁【在【尝试之前**
§493  **`nextReturnAttempt = now + 250`** ⇒ **⇒ 每 `250ms` 一次**】⇒ **⇒ 一个**有界的**重试**】
⇒ **⇒ 两次"一个**有界的**重试**"**
```

**✅ ⭐⭐⭐ **"一个有界的重试"两例**。

**⚠ 而那个 `returnRetries++%20==0`**】**。**

**⇒ 十层**：
```text
`returnRetries++ % 20 == 0` ⇒ **⇒ 每 `20` 次重试【打一行日志**】
⇒ **⇒ 而【每 `20 × 250 = 5000ms`**】⇒ **⇒ 所以【每 `5` 秒一行**】
```

**✅ ⭐⭐⭐ **"每 5 秒一行"** —— 与 §479 的"`121` 个拒绝"**同族**（**第二次"一个**有界的诊断**"**）。

## 九、关键结论

1. **⭐⭐⭐ "四层回退 + `fail closed and retry, never place inside geometry`"**：① 四个 `CoreArrivals`（**从 `traveler.room` 起循环**）⇒ ② 那个被验证的出发点 ⇒ ③ 八个 `±48` 的偏移（**只在 `FactoryTravelRoomMs + 1000` 之后**）⇒ ④ 拒绝并重试 ⇒ **"'绝不放进几何体'是那个最高的约束"**；而那个 `(room + index) % 4` 的循环 ⇒ **"从 traveler.room 起循环，所以四个玩家不会挤在同一个到达点"**（一个精巧的负载均衡）。
2. **⭐⭐⭐ `nearPad` 的 `176 × 176`（BO1）+ `|Δz| < 100`（重建）** ⇒ **"那个高度守卫是一个重建的安全边界，因为 Factory 的堆叠楼层"** —— 与 §478 的"Voronoi 过渡不是可走边（Factory 有几层）"**同族**（**"两次同一个楼层问题"**），而那个 `72`（导航）与 `100`（近垫）是**两个不同的数两个不同的用途**。
3. **⭐⭐⭐ `beginFactoryTravel` 的十一道门**，而那个**扣款在第 ⑪ 道** ⇒ **"前十道全部在扣款之前"**（与 §483 同族）；而 **"预检两端在扣款之前；实际的进入/返回重复那个权威的凸包查询；**一条 trace 不是一个预定**"** ⇒ **"那个预检只是一个快速失败"**（一个极精确的 TOCTOU 论证）。
4. **⭐⭐⭐ 那个 `{2048, -320, 56}` 的预检点正是 `room = 0` 且 `height = 0`** ⇒ 而 **`height = clamp(60 - viewHeightCurrent, 0, 49)`** ⇒ **独立验证：那个 `49` 正是 `60 - 11`** —— 而 **`11` 是 §488 的 `proneHeight = playerSizeScale × 11`** ⇒ **一个跨报告的精确算术**；所以那个房间的高度在 `56..105`（站 56 / 趴 105）。
5. **⭐⭐⭐ 四个黑房与 `320` 的间距**：`fx` 在 `{2047.92 + 320r, -279.977, 115.73}` 而玩家在 `{2048.0 + 320r, -320, 56+height}` ⇒ **"那个 FX 在那个玩家的上方 10.73..59.73 单位"**（一个有意的视觉位置）；而 **那个 `0.08` 的 `x` 微差（`2047.92` vs `2048.0`）"是两处独立测量"**（与 §475 的 `(-7.88635, .019425)` 同族）；而那个 `y` 的 `40.023` 差 ⇒ **"那个 FX 在房间的 y 前方 40 单位"**。
6. **⭐⭐⭐ `5 <ms>` / `N "default" 0` / `N "zm_factory_sh" 0` 三个命令** ⇒ **"一个动词 + 一个 vision 名 + 一个时长"**（与 §485 的 `'3' "grayscale" 1000` / `'3' "zm_factory_sh" 0` 同族）；而进房用 `"default"` 而返回用 `"zm_factory_sh"` ⇒ **⚠ 一个可质疑的选择**（**一个黑房用一个"default" 的 vision**？）。
7. **⭐⭐⭐ `setFactoryTravelHold` 的"只在代次匹配时擦除 —— 一个幂等的释放"**（与 §485/§490 同族）；而 **那个 `{generation, ps->origin}` 的 `origin` 在整个文件里没有读者** ⇒ **"那个 origin 是一个保留的值"**（与 §468 的 `UnresolvedString` 无生产者同族）。
8. **⭐⭐⭐ "有界的碰撞工作，如果所有出口都被挡住"**：`nextReturnAttempt = now + 250` ⇒ **"每 250ms 一次返回尝试"**（与 §486 的"一次尝试"同族）；而 `returnRetries++ % 20 == 0` ⇒ **"每 5 秒一行"**（一个有界的诊断）。

## 十、`sv_zm_travel_mp.cpp` 全文件总览

**`230` 行。**

**`6` 个常量/几何**：
```text
CoreArrivals            {-88,256,116} {-24,256,116} {-88,328,116} {-24,328,116}
nearPad 水平            176
nearPad 高度            < 100
房间间距               320
房间 y                 -320        （FX 在 -279.977）
房间 z                 56 + height （height = clamp(60 - viewHeightCurrent, 0, 49)）
FX z                   115.73
```

**`4` 个函数**：`travelLog` / `nearPad` / `beginFactoryTravel` / `driveFactoryTravel` / `setFactoryTravelHold` / `factoryTravelHeld`。

**`5` 条可靠命令**：`5 <ms>`（充电倒计时）/ `N "default" 0`（进房）/ `N "zm_factory_sh" 0`（返回）/ `3 ...`（§485 那边的）/ `a`/`y`（§485）。

**`8` 个测量锚点**：
```text
176-unit 的水平测试（BO1）
2s 充电 / 2s 黑房 / 5s 冷却（BO1 Der Riese 的 patched player_teleporting）
1700 ms 的音效
250 ms 的返回重试
FactoryTravelRoomMs + 1000 的放宽
2047.92 / 2048.0 的 0.08 差
-279.977 / -320 / 115.73 / 56
49 = 60 - 11
```

## 十一、未闭合点

- `N` 动词的语义（与 `'3'` 的 `type 5` 的区别）。
- `N "default" 0` 里 `"default"` 指哪个 vision 资产。
- `factoryTravelHolds_[client].second`（那个 `origin`）的未来用途。
- 下一个文件：`sv_battlechatter_mp.hpp`（`12,244` 字节）或按大小继续。
