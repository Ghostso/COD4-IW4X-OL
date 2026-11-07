# 237 · 正确的偏移把服务器变成僵尸服、`combat` 这个新代际

## 一、范围

本报告学习 `EngineBindings.cpp` 8499–8698 行。

## 二、`readClientBookingSelection` 的五级拒绝

```cpp
if (!module_) return refuse("module");
if (!slotBytes || *slotBytes < sizeof(uint8*)) return refuse("room-slot-unreadable");
if (!roomBytes || *roomBytes <= RotationIndexOffset) return refuse("room-too-small");
if (!selectionKind || (*selectionKind != "playlist" && *selectionKind != "combat"))
    return refuse("selection-kind");
if (!gameType || !mapName || !validBookingName(*gameType) || !validBookingName(*mapName))
    return refuse("map-or-gametype-name");
```

**五个具名原因** —— 而 §236 说"这个读取器有五个静默 nullopt"。

**现在是五个具名拒绝** —— 所以"命名路径"这一半已经做到了。

## 三、正确的偏移把服务器变成僵尸服（本组最重要的一段）

### 3.1 那次实际发生的序列

```text
client booking selection unavailable reason=selection-kind
SessionStart queued map=zm_factory_sh gametype=zm members=1
gamestate configuration ACCEPTED                  <- the zombies one
connectionless rejected ... XUID is not in the session roster
SessionStart queued map=mp_rust_long gametype=dm members=2   <- too late
```

**六行日志，时间顺序**：

```text
1. 选择读取失败（selection-kind）
2. 回退到【僵尸】默认
3. 【僵尸的 gamestate 被接受】
4. 然后拒绝所有 booking 了 deathmatch 的客户端
5. 太迟了才排队正确的 SessionStart
```

### 3.2 那句总结

```text
Unable to read the selection, this fell back to a zombies default,
committed THAT gamestate, and then rejected every client who had
booked deathmatch. They all timed out, and no client has reached
`active` unattended since.
```

**"读不到选择就回退到僵尸默认，提交【那个】gamestate，然后拒绝每一个 booking 了死亡竞赛的客户端。"**

**这是"静默回退"的最坏形态** —— **它成功提交了一个错误的 gamestate**。

## 四、移植正确的偏移反而破坏了游戏（本组最有价值的一段）

### 4.1 移植后发生什么

```cpp
// REVERTED TO 3.3.3.3's ON PURPOSE. Section 187p.
//
// The ported 1649370 offsets (67056/67060/67064/67068/67100) are CORRECT and
// are kept below for whoever finishes this. They made the dedicated read the
// client's real booking and self-book it -- which is the right behaviour and
// immediately served `cha`, Charge, a TEAM mode, because that is what the menu
// had selected. Two players on one side cannot damage each other, so shooting
// stopped working.
```

### 4.2 完整逻辑

```text
1. 正确的偏移让服务器读到客户端真实的 booking
2. 它自己 book 那个 → 这是【正确行为】
3. 立刻服务了 `cha`（Charge，一个【队伍模式】），因为菜单选的就是它
4. 两个玩家在同一侧无法互相伤害
5. ⇒ 【射击不工作了】
```

**"正确的读取 + 正确提交 = 游戏坏了"** —— 因为**队伍分配还不支持把两个玩家分到对立侧**。

### 4.3 三次尝试固定 gametype 全部失败

```text
Three attempts to pin the gametype downstream all missed:
    the export next to readClientBookingSelection is not on the path,
    and pinning the SessionStart control message logged `PINNED cha -> dm`
    while configureGameState still reported `booked=cha`
    -- the gamestate takes its gametype from the stored booking,
       not from that message.
```

**三层**：

```text
1. 旁边的 export 不在路径上
2. 固定 SessionStart 消息 ⇒ 日志说 "PINNED cha -> dm"，但 configureGameState 仍报 "booked=cha"
3. ⇒ gamestate 从【存储的 booking】取 gametype，不从那个消息
```

**"gamestate 从存储的 booking 取 gametype"** —— 这是一个关键的架构事实。

### 4.4 所以回退

```text
Rather than keep guessing at which record wins, this puts the server back
where it was when deathmatch last worked (17:20:09 and 17:47:59, both
`booked=dm`): unable to read the client booking, so configure-session's
`--gametype dm` is the only session-start there is.
```

**两个时间戳**：`17:20:09` 与 `17:47:59`，两次都是 `booked=dm`。

**"读不到 ⇒ `--gametype dm` 是唯一的会话启动来源"** —— 所以回退是【故意的功能降级】。

### 4.5 那段"留着给后来者"

```text
THE PORTED VALUES, for when team assignment can put two players on opposing
sides -- do not re-derive them, they are measured and corroborated
(tools/runtime/CodolMatchFlow.py, and §187i):
    SelectionKind 67056  GameType 67060  MapName 67064
    PlaylistSlot  67068  RotationIndex 67100
```

**"留给队伍分配能把两个玩家放在对立侧的时候 —— 不要重新推导它们，它们是测量过并被佐证的"**

**这是"保留正确的值但暂时不用"** —— 与 §178 里 `UnexpectedBytes` 的详细说明同族。

## 五、**又一次改回来了**（中文注释）

### 5.1 那段 2026-10-07 的记录

```cpp
// ★★★ 2026-10-07 05:1x -- **改用 1649370 组偏移**（我方 3.19.26.13 现场实测成立；单变量）：
//   实测（客户端 pid 2776，菜单选中快速匹配 / 26 / sd）：
//     room+67056 -> "playlist"      （而 3.3.3.3 组 room+63280 全零 —— 这就是 d26 的
//     room+67060 -> "sd"              `client booking selection unavailable reason=selection-kind`
//     room+67064 -> "mp_crash_tropical" 与随后 `match_rules_rejected playlist=0 …` 的来源）
//     room+67068 字节 = 0x1A = 26    （= 客户端 mmstart 命令里的 "playlist 26"）
//     room+67100 字节 = 0
```

### 5.2 五个实测值

```text
room+67056 → "playlist"
room+67060 → "sd"
room+67064 → "mp_crash_tropical"
room+67068 → 0x1A = 26
room+67100 → 0
```

**`pid 2776`、菜单选中"快速匹配 / 26 / sd"** —— 完整的现场记录。

### 5.3 与 3.3.3.3 组的对照

```text
3.3.3.3 组 room+63280 全零 ⇒ 这就是 d26 的 `reason=selection-kind`
```

**"这是 `reason=selection-kind` 的来源"** —— 所以那次失败是【偏移错】而不是【选择不存在】。

### 5.4 为什么又改回来

```text
//   注意：§187p 的回退（3.3.3.3 组）针对的是老外双人测试的 team 模式问题；我方当前单变量目标 =
//   把"客户端自己选的那张图/模式"服务对，先跑通进图，再谈模式差异。
```

**"§187p 的回退针对的是老外双人测试的 team 模式问题；我方当前单变量目标 = 把客户端自己选的那张图/模式服务对，先跑通进图，再谈模式差异。"**

**所以最终决定是：用正确的偏移**，因为**单变量目标不同**（进图 vs 双人伤害）。

### 5.5 这是一个**三次反转**

```text
1. 原：3.3.3.3 的偏移（错的）⇒ 读不到
2. §187p：改成 1649370 的（对的）⇒ 读到了，但 served cha ⇒ 射击失效 ⇒ 回退
3. §187i/2026-10-07：又改回 1649370 的 ⇒ 因为目标改成"先进图"
```

**同一个常量被改了三次** —— 而**每次的理由都不同**（读不到 / 破坏双人 / 目标是进图）。

**这是本报告最值得记的一条**：**"正确"取决于当前目标**。

## 六、五个偏移的最终值

```cpp
constexpr std::size_t SelectionKindOffset = 67056;
constexpr std::size_t GameTypeOffset = 67060;
constexpr std::size_t MapNameOffset = 67064;
constexpr std::size_t PlaylistSlotOffset = 67068;
constexpr std::size_t RotationIndexOffset = 67100;
```

**注意 `PlaylistSlot(67068) → RotationIndex(67100)` 相差 32** —— 中间那 28 字节是别的字段。

## 七、`combat` 这个新代际（第二个发现）

### 7.1 实测

```cpp
// OLMOD(L1-selection-kind-combat) 2026-10-13: THIS GENERATION ALSO BOOKS AS
// "combat". Measured live in a 人机 (combattraining) room at 19:21:05 -- the
// room's selection-kind reads "combat" while gameType/mapName/playlistSlot/
// rotationIndex are all populated (sd / mp_mountain / 33 / 4), and the old
// `!= "playlist"` test refused the whole read, which surfaced downstream as
//     client booking selection unavailable reason=selection-kind
//     match_rules_rejected playlist=0 rotation=0 map= gametype=
//     gamestate NOT sent client=0 GAMESTATE_NOT_CONFIGURED   (stuck on "设置游戏")
```

### 7.2 "人机"（combattraining）房间的五个字段

```text
selection_kind  = "combat"       ← 新的
gameType        = "sd"
mapName         = "mp_mountain"
playlistSlot    = 33
rotationIndex   = 4
```

**"四个字段全都有"** —— 所以 `combat` 只是选择类型的名字不同。

### 7.3 那次下游表现

```text
client booking selection unavailable reason=selection-kind
match_rules_rejected playlist=0 rotation=0 map= gametype=
gamestate NOT sent client=0 GAMESTATE_NOT_CONFIGURED   (stuck on "设置游戏")
```

**四行**，最后卡在 UI 的 **"设置游戏"**。

### 7.4 修法：**两个值都接受**

```cpp
if (!selectionKind ||
    (*selectionKind != "playlist" && *selectionKind != "combat"))
    return refuse("selection-kind");
```

**"`combat` 携带同样的四个字段，所以它以同样的权重被接受；这个读取器里别的什么都没变（单变量）。"**

**"单变量"** —— 只改这一个判断。

## 八、`validBookingName` 的复用

```cpp
if (!gameType || !mapName ||
    !validBookingName(*gameType) || !validBookingName(*mapName))
    return refuse("map-or-gametype-name");
```

**与 §217 里 `initializeLevelWorld` 用同一个 `validBookingName`** —— 因为名字要拼路径。

## 九、`ClientBookingSelection` 的四个字段

```cpp
return ClientBookingSelection{
    .mapName = *mapName,
    .gameType = *gameType,
    .playlistSlot = room[PlaylistSlotOffset],                        // uint8
    .rotationIndex = (int8_t)room[RotationIndexOffset],              // int8
};
```

### 9.1 两个类型

```text
playlistSlot    uint8    0..255
rotationIndex   int8     -128..127
```

**`rotationIndex` 是有符号** —— 而 `ClientBookingSelection` 声明是 `std::int8_t rotationIndex{}`（§181）✓

**`playlistSlot` 是 `std::uint8_t`** ✓

**而 `SvBookingCommand`（§151）里是 `uint32 playlistId` 与 `uint32 rotationIndex`** —— **两个结构用了不同的宽度**。

## 十、`readProfileWeaponRequest`：那段"这不是玩家的职业"

### 10.1 三条实测证据

```text
two clients report byte-identical loadouts while holding an M4 and a CheyTac;
editing a class in the UI moves no returned value;
the ids (10000, 10009, 10014 ...) appear NOWHERE in mp_coweapitemswea.csv,
    the 838-row weapon table where m4a1tech_mp is 42.
```

**三条**：

```text
1. 两个持有不同枪的客户端返回【逐字节相同】的 loadout
2. UI 里改职业不改变任何返回值
3. 这些 id（10000/10009/10014）在 838 行的武器表里【任何地方都不出现】
```

### 10.2 结论

```text
Most likely sub_7F9090()+160 is not the loaded player profile in this
calling context. The fix is to stop asking the client at all: the server
already holds the blob and mp/playerdata.def decodes it
```

**"很可能 `sub_7F9090()+160` 在这个调用上下文里不是已加载的玩家 profile。修法是【根本不再问客户端】。"**

## 十一、`readProfileWeaponRequest` 的实现

```cpp
const auto* base = secondary ? "secondaryBase" : "primaryBase";
const auto* attach = secondary ? "secondaryAttach" : "primaryAttach";
const auto index = (int32)classIndex;

const auto itemId = invokeWeaponClassFieldGet(weaponClassFieldGet_, -1, base, index);
if (!itemId || *itemId < 0 || *itemId > 0xFFFF)
{
    loadoutResolveFailure_.store(StagedSlot);
    return false;
}
```

### 11.1 `-1` 是"标量字段"

```cpp
invokeWeaponClassFieldGet(function, -1, base, index)
```

**`elementIndex = -1`** —— 与 §202 里"`ecx = -1` 表示标量字段"一致。

### 11.2 附件用 `0..AttachmentCount-1`

```cpp
for (slot = 0; slot < AttachmentCount; ++slot)
{
    const auto attachment = invokeWeaponClassFieldGet(
        weaponClassFieldGet_, slot, attach, index);
    if (!attachment || *attachment < 0 || *attachment > 0xFFFF)
        continue;                        // ← 【跳过，不是失败】
    candidate.attachmentItemIds[slot] = (uint32)*attachment;
}
```

**附件读不到就跳过** —— 而武器读不到就失败。

**"没有武器不是失败"** 的注释与实现相反：

```cpp
// NO WEAPON IS NOT A FAILURE. A class with an empty secondary is a
// legal class, and refusing it here would drop the whole loadout the
// way the staged reader used to.
if (!itemId || *itemId < 0 || *itemId > 0xFFFF)
{
    loadoutResolveFailure_.store(StagedSlot);
    return false;                        // ← 仍然失败了
}
```

**注释说"没有武器不是失败"，而代码仍然 `return false`** —— **这是一处注释与实现矛盾**。

**可能注释的意思是"应该"不失败，但实现还没改。**

## 十二、关键结论

1. **五个具名拒绝** 取代了五个静默 nullopt。
2. **正确的偏移让服务器成为僵尸服** —— 因为它提交了错误的 gamestate。
3. **"正确的读取 + 正确提交 = 游戏坏了"** —— 因为队伍分配还不支持对立侧。
4. **三层固定 gametype 的尝试全部失败** —— gamestate 从存储的 booking 取值。
5. **同一个常量被改了三次，每次理由不同** —— "正确"取决于当前目标。
6. **`combat` 是新一代的 selection kind**，四个字段同样有值。
7. **`readProfileWeaponRequest` 读到的"不是玩家的职业"** —— 三条实测证据。
8. **"没有武器不是失败"的注释与实现矛盾**。

## 十三、未闭合点

- `readProfileWeaponRequest` 的注释与实现的矛盾。
- `SvBookingCommand` 与 `ClientBookingSelection` 的宽度不一致。
- `EngineBindings.cpp` 8698 行之后未读取。
