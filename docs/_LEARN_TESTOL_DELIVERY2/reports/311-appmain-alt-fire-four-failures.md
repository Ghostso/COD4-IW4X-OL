# 311 · **alt-fire 触发器的四次失败** —— `0x100000` 是右键、`0x08000000` 不是键、`n 89` 才是

## 一、范围

本报告学习 `Appmain.cpp` 8961–9180 行。

## 二、`setTriggerContactRunner` 的**两项委托**

```cpp
Server.setTriggerContactRunner([](playerOrigin, playerBounds, trigger) {
    return Bindings.contactBrushModel(
        playerOrigin, playerBounds, trigger.origin, trigger.angles, trigger.collision);
});
```

**⇒ 五项参数 → `contactBrushModel`（§262 的函数）。**

**✅ 与 §262 的"`contactBrushModel` 用 `start == end` 的 trace 返回 `startSolid`"配合。**

## 三、**`alt` 武器的三个查找方向**

### 3.1 `setWeaponDefinitionResolver` —— **无限制**

```cpp
Server.setWeaponDefinitionResolver([](uint16 weaponAssetIndex, SvResolvedWeapon &resolved) {
    if (!weaponAssetIndex) return false;
    ClientWeaponSelection selection{};
    if (!Bindings.readWeaponSelection(weaponAssetIndex, selection)) return false;
    resolved = toResolvedWeapon(selection);
    return true;
});
```

**⇒ 任何索引都能解析成完整定义。**

**⇒ 那个"仅 alt"的限制是**上面的策略层**而不是访问器的限制。**

### 3.2 `SV_SetAltWeaponLookup` —— **反向表（alt → host）**

```cpp
static std::mutex altMutex;
static std::unordered_map<uint16, uint16> altToHost;
static bool built{};
lock_guard guard(altMutex);
if (!built)
{
    built = true;
    for (host = 1; host < 1700; ++host)
        if (const auto alt = Bindings.altWeaponAssetIndex(host))
            altToHost.emplace(alt, (uint16)host);
    write("alt weapon table built pairs=" + altToHost.size());
}
if (!altToHost.contains(weaponAssetIndex)) return false;
...
```

**⇒ 三层**：

```text
① 一次性建表（host → alt 反成 alt → host）
② 只接受表里的
③ 然后解析它
```

**⚠ 而 `if (!built) { built = true; ... }` 在**建之前**置真（§245 的 `built = true` 同族）。**

### 3.3 `SV_SetHostAltWeaponLookup` —— **正向（host → alt）**

```php
// SECTION 191z: AND THE HOST -> ALT DIRECTION, WHICH IS THE ONE THE SPAWN
// BOOTSTRAP NEEDED AND NEVER HAD.
//
// The lookup above answers "is this index an alt, and what is it made of".
// `sv_client_spawn_mp.cpp` was calling it with the loadout's HOST weapon,
// which is never a key in that map, so it returned false for every weapon
// in every class and the alt never got a heldWeapons slot.
// The log said so all along: `list2F4=1224,1226,0,0,0,0` -- two entries,
// the primary and the secondary, and nothing after them.
```

### 3.4 五层

```text
1. 上面的查找回答"这个索引是一个 alt 吗，它由什么构成"
2. 而 `sv_client_spawn_mp.cpp` **用 loadout 的【宿主武器】调它**
3. ⇒ 宿主**从不是那个 map 的键** ⇒ 所以它**对每个职业的每把武器都返回 false**
4. ⇒ 而 **alt 从未获得一个 `heldWeapons` 槽**
5. ⇒ **日志一直这样说**：`list2F4=1224,1226,0,0,0,0` —— **两个条目，主与副，后面什么也没有**
```

### 3.5 而"**`0x00424470` 遍历那个数组并对任何找不到的 `cmd.weapon` 存零**"

```php
// out.exe's finish-weapon-change routine (0x00424470) walks exactly that
// array and stores a ZERO for any cmd.weapon it does not find, so an
// alt outside the held list cannot become the current weapon however it
// is requested. That is the second half of section 191y.
```

**⇒ 三层**：

```text
1. `0x00424470` 遍历 `heldWeapons` 并对**任何找不到的 `cmd.weapon` 存零**
2. ⇒ 一个**在 held 列表之外的 alt 不能成为当前武器**
3. ⇒ **无论怎么请求**
```

**✅ 与 §252 的"`Pmove` 不检查地索引 `dword_1988B50`"同族（绝对索引问题）。**

## 四、**alt-fire 触发器的四次失败**（本组最重要的一段）

### 4.1 第一次：`0x100000` 被当成 alt-fire

```php
// OFF BY DEFAULT SINCE 2026-09-03, BECAUSE 0x100000 IS NOT THE ALT-FIRE BUTTON.
// Section 190 read it off sub_425440's fire types and never confirmed it against a real
// press. It is AIM DOWN SIGHTS. Measured in a live match, the player's words first:
//
//     "every time i right click it readys my weapon back and forth"
//
//     15:17:46 alt fire SWITCH client=0 from=1227 to=1228     <- one per right-click,
//     15:17:47 alt fire SWITCH client=0 from=1227 to=1228        twenty-odd in ten seconds
//
// Always 1227->1228, never back, so the paired toggle does not even hold: every press
// re-applies the switch and the client replays the weapon raise. That is a WORSE game
// than no alt-fire at all, and it shipped enabled on the strength of a decompile.
```

### 4.2 六层

```text
1. `0x100000` **不是 alt-fire 键**
2. §190 从 `sub_425440` 的 fire types 读出而**从未对着一次真实按键确认**
3. ⇒ **它是【瞄准】（ADS）**
4. **玩家的原话**："每次我右键它把我的武器来回准备好"
5. 日志：**每次右键一次 1227→1228**，十秒里二十多次
6. ⇒ **永远是 1227→1228，从不回来** ⇒ 所以**成对切换都不成立**

**⇒ 每次按都重新施加切换 ⇒ 客户端重放武器举起**

7. ⇒ **那是一个比完全没有 alt-fire 更糟的游戏**
8. ⇒ **而它是凭一次反编译就出货了**
```

### 4.3 **"那是一个比没有 alt-fire 更糟的游戏，而它是凭一次反编译就出货了"**

**✅ 这是整个文件里最直接的一句**方法论批评**。**

**⇒ 与 §310 的"索引 0 是一个找不到的查找"**是推理，从未是测量"**同族。**

### 4.4 第二次：`0x08000000` 也不是键

```php
// OFF AGAIN, AND 0x08000000 IS NOT A KEY EITHER.
//
// Second wrong trigger in two attempts, and the second one was mine. I
// asked the player to press 3 in isolation, saw only 0x08000000, and
// took it -- from TWO edges for TEN presses. A count that does not
// match is not a detail to round off; it was the window telling me it
// was contaminated.
//
// The labelled follow-up settles it: 63 edges of 0x08000000 in three
// minutes INCLUDING a run on the idle second client that nobody was
// touching. It is not a keypress. Most likely it is a HELD bit
// flickering through sect.186's decode -- a delta packet's first
// usercmd deltas against the client's last command, so a held button
// reads as released and re-pressed and yields a rising edge per packet.
```

### 4.5 七层

```text
1. **`0x08000000` 也不是一个键**
2. **两次尝试里第二个错的触发器，而第二个是我（作者）的**
3. 我让玩家单独按 3，只看到 `0x08000000`，就采用了它
4. ⇒ **而那是十次按键里的【两个】边沿**
5. ⇒ **"一个不匹配的计数不是一个可以四舍五入的细节；它是窗口在告诉我它被污染了"**
6. ⇒ 带标签的后续采访定案：**三分钟里 63 个 `0x08000000` 边沿**，**包括一段在没人碰的空闲第二客户端上的运行**
7. ⇒ **它不是按键**
8. ⇒ 最可能是**一个被保持的位在 §186 的解码里闪烁** —— 一个 delta 包的第一个 usercmd 对客户端上一个命令做差值，所以**一个被按住的按钮读作释放并重新按下**而**每个包产生一个上升沿**
```

### 4.6 **"一个不匹配的计数是窗口在告诉我它被污染了"**

**✅ 这是本文件里**最重要的诊断原则**之一。**

**⇒ 与 §294 的"`288/397` 平台期"、§277 的"26 次命中只 1 次能定姿态"同族**（第九次"计数不匹配 = 信号"）。

### 4.7 第三次：按 3 **产生不了任何按钮位**

```php
// WHAT THE SAME MEASUREMENT DID ESTABLISH: pressing 3 produces NO
// distinct button bit at all. The only other bits seen were 0x00000001
// (attack) and one 0x20100800 combination. So alt-fire on this build is
// probably NOT a usercmd button, and the trigger has to be found on the
// command channel instead. Binding a third bit off the same evidence
// would be the same mistake twice more.
```

**⇒ 五层**：

```text
1. **按 3 产生不了任何不同的按钮位**
2. 唯一看到的其它位是 `0x00000001`（攻击）与一个 `0x20100800` 组合
3. ⇒ 所以这个 build 上的 alt-fire **很可能不是一个 usercmd 按钮**
4. ⇒ **触发器必须在命令通道上找**
5. ⇒ **"从同一份证据上绑第三个位就是同一个错误再来两次"**
```

**✅ 与 §279 的"参数化而不是枚举"、§288 的"75 个全试过"同族**（第九次"不再猜"）。

### 4.8 第四次：**`n 89` 才是触发**

```php
// ARMED. THE TRIGGER IS RIGHT AND THE SWITCH IS NOT LANDING YET.
//
// The action is "Weapon Attachments" on key 3 -- the HUD says so, and
// the client has been renaming the gun to the alt on that key since
// before any of this existed. It is not a `+` bind so it never reaches
// a usercmd; it arrives as the reliable command `n 89`, ten presses to
// ten commands.
//
// The switch then fires -- 65 times in one match, 1224->1225 -- and
// `player-presentation` still reports weapon=1224 every time. So the
// assignment is being undone between here and the wire, which is what
// the player sees as "it just readies my weapon" rather than
// transforming it. Which stage undoes it is now instrumented rather
// than guessed (OLMOD_LOG_ALT_WEAPON=1).
```

### 4.9 七层

```text
1. **触发器对了而切换还没落地**
2. 动作是键 3 上的 "Weapon Attachments" —— **HUD 这么说**
3. ⇒ 而**客户端在那个键上一直把枪重命名为 alt**，在这一切存在之前就是
4. ⇒ **它不是一个 `+` 绑定** ⇒ 所以**它从不到达 usercmd**
5. ⇒ **它作为可靠命令 `n 89` 到达**，**十次按键十个命令**
6. ⇒ 而**切换会触发** —— 一场比赛 **65 次，1224→1225**
7. ⇒ **而 `player-presentation` 每一次仍报 `weapon=1224`**
8. ⇒ 所以**这个赋值在【这里】与【线上】之间被撤销了**
9. ⇒ 那就是玩家看到的"它只是把我的武器准备好"而不是变换它
10. ⇒ 哪个阶段撤销它现在**被插桩而不是被猜**
```

### 4.10 **"十次按键十个命令"** 是关键

**⇒ 与第二次的"十次按键两个边沿"**形成完美对照**：**

```text
第二次（0x08000000）   十次按键  两个边沿    ⇒ 不是按键
第四次（n 89）          十次按键  十个命令    ⇒ 【是按键】
```

**✅ 一个**累积的诊断链条** —— 每一次失败都收窄了搜索空间。**

## 五、而 `OLMOD_ALT_FIRE` 的**严格关断**

```cpp
if (const auto *const altFire = std::getenv("OLMOD_ALT_FIRE");
    !(altFire && altFire[0] == '0' && !altFire[1]))
{
    Server.setAltFireResolver([](const std::uint16_t weaponAssetIndex) {
        return Bindings.altWeaponAssetIndex(weaponAssetIndex);
    });
}
```

### 5.1 **`!(altFire && altFire[0] == '0' && !altFire[1])`**

**⇒ 三段**：

```text
altFire 存在
且 altFire[0] == '0'
且 altFire[1] == '\0'      ← 【必须恰好是 "0"】
```

**⇒ 所以只有精确的 `"0"` 关，其它都开（默认开）。**

**✅ 与 §307 的 `v[0] == '1' && v[1] == '\0'` **相反方向但同一种严格性**。**

**⇒ 第十六种解析。**

### 5.2 而 `SV_SetAltWeaponResolver` **在 if 之外**

```cpp
CodolGameServer::SV_SetAltWeaponResolver([](uint16 weaponAssetIndex) {
    return Bindings.altWeaponAssetIndex(weaponAssetIndex);
});
```

**⇒ 所以即使 `OLMOD_ALT_FIRE=0`，这个 resolver 仍设。**

**⚠ 两个 resolver 一个有开关一个没有。**

**⇒ 因为一个是**触发器**（危险）而一个是**定义查询**（安全）。**

**✓ 语义正确。**

## 六、`clientEventsHandler` 的**十四项参数**

```cpp
Server.setClientEventsHandler([](
    SvPlayerState &playerState,
    SvGameEntity &entity,
    SvNativePlayerState &nativePlayerState,
    const SvWeaponAimState &weaponAimState,
    const float currentAimSpreadScale,
    const uint32 serverTime,
    SvGlassState &glassState,
    SvGlassDamageState &glassDamageState,
    const SvGlassMapMetadata &glassMetadata,
    span<const SvCollisionEntity> collisionEntities,
    span<const SvDamageablePlayerView> damageablePlayers,
    const SvResolvedLoadout *resolvedLoadout,
    span<const SvNativePredictableEvent> events) {
    ...
});
```

**⇒ 十三项（我数十三）。**

### 6.1 而 `uavWeapon` 的**三项条件**

```cpp
const auto uavWeapon = playerState.rewardActionType == 1 &&
    playerState.rewardActionWeapon &&
    std::ranges::any_of(events, [&](const auto &event) {
        return event.parameter == playerState.rewardActionWeapon;
    })
    ? Bindings.resolveUavWeapon() : std::nullopt;
```

```text
rewardActionType == 1          （UAV 类型）
rewardActionWeapon 非零
【某个事件的 parameter 等于那个武器】
⇒ 才解析 UAV
```

**✅ 与 §307 的"连杀使用键链"配合 —— 第三个条件是"事件里真的出现了那个武器"。**

## 七、关键结论

1. **三个 alt 查找方向**：无限制定义 / alt→host 反向表 / host→alt 正向。
2. **`sv_client_spawn_mp.cpp` 用宿主武器调了"alt 查找"** ⇒ 每把武器都 false ⇒ **alt 从未获得 `heldWeapons` 槽**。
3. **日志证据 `list2F4=1224,1226,0,0,0,0`** —— 两个条目，后面什么也没有。
4. **`0x00424470` 对找不到的 `cmd.weapon` 存零** ⇒ alt 在 held 列表外不能成为当前武器。
5. **第一次：`0x100000` 是右键（ADS）而不是 alt-fire** —— "每次右键它把武器来回准备好"。
6. **"那是一个比没有 alt-fire 更糟的游戏，而它是凭一次反编译就出货了"**。
7. **第二次：`0x08000000` 不是键** —— **十次按键只有两个边沿**。
8. **"一个不匹配的计数是窗口在告诉我它被污染了"** —— 一个重要的诊断原则。
9. **三分钟 63 个边沿，包括没人碰的空闲客户端 ⇒ 它不是按键**。
10. **最可能是一个被保持的位在 delta 解码里闪烁**（每个包一个上升沿）。
11. **第三次：按 3 产生不了任何按钮位** ⇒ alt-fire 不是 usercmd 按钮。
12. **"从同一份证据绑第三个位就是同一个错误再来两次"**。
13. **第四次：`n 89` 可靠命令才是触发**（十次按键十个命令 ⇒ 完美对照）。
14. **切换触发 65 次（1224→1225）而 `player-presentation` 仍报 1224** ⇒ **赋值在这里与线上之间被撤销**。
15. **"哪个阶段撤销它现在被插桩而不是被猜"**。
16. **`OLMOD_ALT_FIRE` 只认精确 `"0"`** —— 第十六种解析。
17. **`SV_SetAltWeaponResolver` 无开关**（安全）而 `setAltFireResolver` 有（危险）。

## 八、未闭合点

- **哪个阶段撤销了 alt 赋值的（`OLMOD_LOG_ALT_WEAPON` 的结果未知）**。
- `n 89` 命令的完整语义。
- `0x20100800` 组合位的含义。
- `Appmain.cpp` 9180 行之后未读取。
