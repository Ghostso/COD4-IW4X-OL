# 286 · **`181 ** 646 0 0 1243 1242`** 的实测、`%` 广播会触发客户端的 181 检查、"与 SessionStart 逐字节相同"是不变式

## 一、范围

本报告学习 `Appmain.cpp` 3460–3680 行。

## 二、`SV_RegisterModularWeaponConfigString` 的**四项参数**

```php
SV_RegisterModularWeaponConfigString(
    gameState,
    firstDynamicWeaponAssetIndex,
    {
        .baseWeaponAssetIndex = (uint16)weapon.baseWeaponAssetIndex,
        .value8 = (uint8)weapon.modularValue8,
        .optionalValue9 = (uint16)weapon.modularValue9,
        .attachmentAssetIndexes = std::move(attachmentAssetIndexes),
    });
```

### 2.1 四项

```text
baseWeaponAssetIndex    基址
value8                  一个 uint8
optionalValue9          一个 uint16
attachmentAssetIndexes  附件索引表
```

### 2.2 **而 `value8` 与 `optionalValue9` 正是 `**` 串的第二个与第三个数字**

**⇒ 与 §285 的"1168 的 `140`、1177 的 `72`、1204 的 `11`"对上。**

**⇒ `value8` = `** 串第二字段` = 那个 140/72/11/0。**

**⇒ 所以那个字段**有语义**，而我们**总是写 0**。**

### 2.3 而 `value8` 是 **uint8**

**⇒ 所以 0..255。**

**⇒ 而观测到的 140、72、11 都在范围内** ✓

**⇒ 而 `140` 与 §240 的 `0x8C` 无关（那是偏移）。**

## 三、**`clipIndex` 的特殊处理**

```php
weapon.weaponAssetIndex = *registeredWeaponAssetIndex;
if (weapon.clipIndex == (int32)originalWeaponAssetIndex)
    weapon.clipIndex = *registeredWeaponAssetIndex;
```

### 3.1 三层

```text
1. 武器索引换成新注册的
2. 【而如果 clipIndex 恰好等于原索引】
3. ⇒ clipIndex 也换成新索引
```

### 3.2 **这是一个奇怪的耦合**

**⇒ 为什么 `clipIndex` 会等于 `weaponAssetIndex`？**

**⇒ 除非"clip 的编号空间就是武器索引空间"。**

**⇒ 从 §240 的 `ammoIndex`/`clipIndex` 是 `WeaponAmmoIndexOffset`/`WeaponClipIndexOffset` 读的 ⇒ 它们是**弹匣表**的索引。**

**⇒ 而弹匣表可能与武器表**共用编号空间**。**

**⚠ 一个难以置信但可能的约定。**

**⇒ 而这个 `if` 是在修"重新注册后索引漂移"的一个特例。**

## 四、`buildWeaponConfigStringUpdatePayload` 的**4096**

```cpp
std::array<std::uint8_t, 4096> buffer{};
EngineMsgWriter message(Bindings, buffer);
SV_WriteWeaponConfigStringUpdateCommand(message, weaponAssetIndex, configString);
if (message.overflowed()) return {};
const auto data = message.data();
return { data.begin(), data.end() };
```

### 4.1 **4096 比 64 KB 小得多**

**⇒ 因为一个配置串更新命令很短。**

**⇒ 而 §270 的 `buildGameState`/`buildSnapshot` 用 64 KB。**

### 4.2 而溢出 ⇒ 空

**⇒ 与 §270 的 `buildGameState` 失败返回空 `vector` 一致。**

## 五、`liveRegisterWeaponConfigString` 与 `registerWeaponConfigString` 的**对照**

```text
registerWeaponConfigString      SV_RegisterModularWeaponConfigString(gameState, ...)
liveRegisterWeaponConfigString  Server.registerDynamicWeaponConfigString(..., buildWeaponConfigStringUpdatePayload)
```

### 5.1 两个**几乎相同**的函数

```text
① 先注册依赖
② 收集附件索引
③ 保存 originalWeaponAssetIndex
④ 注册本体
⑤ 更新 weaponAssetIndex 与 clipIndex
```

**⇒ 五步完全一致。**

**⇒ 只有调用目标不同（`SV_*` vs `Server.*`）。**

**⚠ 一处代码重复** —— 两个 30 行的函数逻辑相同。**

## 六、**`%` 广播会触发 181 检查**（本组最重要的一段）

### 6.1 那段完整注释

```php
// Refresh ONE roster member's weapons in place. Weapons-only for now: the
// member's character is preserved (a live character-model swap is a separate
// follow-up). §160: the new weapons are APPENDED to the live gamestate's
// dynamic block (no '%' broadcast -- that trips the client's 181 weapon-index
// check, [[codol-181-is-weapon-index-vs-slot]]); the member reaches them by
// BACKING OUT AND REJOINING, which re-parses the whole gamestate and
// registers the weapons at their correct dense slots. Run --update-loadout
// while the player is at the menu; their rejoin spawns the new guns, no world
// rebuild and no disturbance to the other players.
```

### 6.2 六层

```text
1. 只刷新武器（角色保留，实时换角色模型是另一件事）
2. 新武器【追加】到活 gamestate 的动态块
3. 【不】用 `%` 广播 —— 那会触发客户端的 181 武器索引检查
4. ⇒ 成员通过【退出再重进】到达它们，重进会重新解析整个 gamestate
5. ⇒ 武器落在正确的密集槽位
6. ⇒ 在菜单时跑 `--update-loadout`；重进时生成新枪，无需世界重建也不打扰其他玩家
```

### 6.3 而 `[[codol-181-is-weapon-index-vs-slot]]` 是**一个记忆条目**

**⇒ 所以 `Com_Error(181)` 的语义是"武器索引 vs 槽位"的混淆。**

**⇒ 与 §285 的 `Com_Error("181 %s %d %d")`（§245 的 walk 前缀）**同一个 181。**

### 6.4 而"退出再重进"作为**刷新机制**

**⇒ 这是一个**实用但笨拙**的设计。**

**⇒ 而 §281 的 `--update-loadout` 就是触发它的命令。**

## 七、**`181 ** 646 0 0 1243 1242`** 的实测（本组第二重要）

### 7.1 那段完整记录

```php
// §161a: DO NOT strip attachments here. The strip existed only to keep
// the retired '%' broadcast small; with the broadcast gone the live
// path must resolve weapons EXACTLY as SessionStart does (it uses the
// same resolveWeaponRequest), so the appended dynamic-weapon block is
// byte-identical to the one a SessionStart would build -- same
// attachments, same nested modularDependencies published in order.
// Stripping made them DIFFERENT: the stripped weapons never dedup
// against SessionStart's attachment'd ones and the dropped
// dependencies shift the client's registration counter, so on a
// reconnect re-parse a weapon landed at slot+1 and Com_Error(181)'d
// (measured 2026-08-26: `181 ** 646 0 0 1243 1242`). Identical to
// SessionStart is the invariant; SessionStart is proven to spawn.
```

### 7.2 七层

```text
1. 剥附件只为了缩小那个【已退役的】 `%` 广播
2. 而广播没了 ⇒ 活路径必须与 SessionStart **完全一样**地解析武器（同一个 `resolveWeaponRequest`）
3. ⇒ 追加的动态块与 SessionStart 构建的**逐字节相同** —— 同样的附件、同样的嵌套依赖按序发布
4. 而【剥附件让它们不同】：
     · 剥过的武器永远不会与 SessionStart 的有附件版本去重
     · 而被丢掉的依赖**移动了客户端的注册计数器**
5. ⇒ 在一次重连重解析时一个武器落在 slot+1 并 `Com_Error(181)`
6. 实测 2026-08-26：`181 ** 646 0 0 1243 1242`
7. ⇒ **"与 SessionStart 相同"是不变式**；SessionStart 被证明能 spawn
```

### 7.3 而 `181 ** 646 0 0 1243 1242` 的**五个字段**

```text
181        错误号
** 646 0 0 1243 1242    出错的串
```

**⇒ 所以 `646` 是武器，`1243`/`1242` 是两个**新注册的索引**。**

**⚠ 而 §285 的 1163 是 `** 646 0 0 8738 9321`。**

**⇒ 而这里的 `** 646 0 0 1243 1242` 是**动态生成的**（因为 646 的附件变成了 1243/1242）。**

**⇒ 所以 `1243`/`1242` 是**运行时注册的附件索引**。**

**⇒ 而错误说"武器索引 vs 槽位" ⇒ 客户端把 1243 当成槽位而它应该是索引（或反之）。**

### 7.4 而"**剥附件让注册计数器移动**"是关键机制

```text
SessionStart 注册：武器 + 附件 + 依赖     ⇒ 计数器 +N
剥附件的 live 路径：武器 + （无附件）      ⇒ 计数器 +M < N
⇒ 两个路径的计数器不同
⇒ 重连重解析时槽位计算错
```

**⇒ 所以"计数器必须一致"是一个**隐式契约**。**

**⇒ 与 §284 的"`registeredClassMask == resolvedClassMask`"相关的**顺序依赖**。**

### 7.5 而"SessionStart 被证明能 spawn"是**判据**

**"Identical to SessionStart is the invariant; SessionStart is proven to spawn."**

**⇒ 所以**以能工作的路径为基准**。**

**⇒ 与 §277 的"用一条已经测量过能打中的线"同族。**

**⇒ 第三次"用已验证的作为基准"。**

## 八、`refreshMemberLoadout` 的**五段**

```php
const auto firstDynamicWeaponAssetIndex = Bindings.firstDynamicWeaponAssetIndex();
if (!firstDynamicWeaponAssetIndex) return false;

// ① 取成员的呈现
CodolGameServer::RegisteredSessionAssets member;
{
    const std::lock_guard lock(LoadoutMutex);
    const auto *const presentation = RegisteredSessionAssets.character(userId);
    if (!presentation)
    {
        logGameServer("loadout refresh failed reason=character_missing user=" + N);
        return false;
    }
    member.characterPresentation = *presentation;
}

// ② 奖励
member.rewards = Bindings.resolveSessionRewards(request);
if (!member.rewards) logGameServer("reward refresh unavailable xuid=" + N);

// ③ 逐职业
for (classIndex)
{
    if (!(classMask & (1u << classIndex))) continue;
    const auto perks = Bindings.resolveSessionPerks(request, classIndex);
    const auto offhands = Bindings.resolveSessionEquipment(request, classIndex);
    if (!perks || !offhands) { logGameServer("... reason=perks_or_equipment ..."); return false; }
    auto primary = Bindings.resolveWeaponSelection(request.classes[classIndex].weapons[0]);
    auto secondary = Bindings.resolveWeaponSelection(request.classes[classIndex].weapons[1]);
    if (!primary || !secondary) { logGameServer("... reason=weapon ..."); return false; }
    ...
}

// ④ 若一个 loadout 都没有 ⇒ false
if (member.loadouts.empty()) return false;

// ⑤ 更新
const std::lock_guard lock(LoadoutMutex);
return RegisteredSessionAssets.updateMember(userId, std::move(member));
```

### 8.1 五段

```text
① 取成员呈现（缺失 ⇒ `character_missing`）
② 奖励（【缺失不致命】，只记日志）
③ 逐职业（任一失败 ⇒ 【整个刷新失败】）
④ 无 loadout ⇒ false
⑤ updateMember
```

### 8.2 **奖励缺失不致命而职业失败致命**

**⇒ 一个明确的优先级**：

```text
rewards    可选（连杀奖励）
职业       必需
```

**✓ 合理。**

### 8.3 而"客户端在 SessionStart 之前发 UpdateLoadout"

```php
// The member is not registered yet (the client emits
// UpdateLoadout BEFORE the SessionStart that registers it). Say
// so instead of dropping the refresh with a bare false.
```

**⇒ 一个**时序事实**：客户端的消息顺序是 `UpdateLoadout` **先于** `SessionStart`。**

**⚠ 所以第一次 `UpdateLoadout` 必然失败（`character_missing`）。**

**⇒ 这是一个**已知的、可接受的**失败。**

**⇒ 而"说出来而不是裸 false"是正确的。**

### 8.4 而 `primary`/`secondary` 的**两个 optional**

**⇒ 而 §252 说"副武器允许为空（`itemId == 0` 返回 true + 空 selection）"。**

**⇒ 所以 `!secondary` 只在**解析失败**时为真（不是空槽）。**

**✓ 与那段注释"区分『没装副武器』与『解析失败』"一致。**

## 九、`prepareClientLoadouts` 的开头

```php
std::uint64_t requestSequence{};
{ const std::lock_guard lock(LoadoutMutex); requestSequence = LoadoutPrepareRequestSequence; }
const auto characterIndex = Bindings.currentCharacterIndex();
const auto characterPresentation = characterIndex
    ? Bindings.resolveClientCharacterPresentation(*characterIndex) : std::nullopt;
PreparedClientLoadouts prepared;
PreparedSessionMember preparedMember;
std::uint32_t resolvedClassMask{}, registeredClassMask{};
if (characterIndex)
{
    prepared.requestSequence = requestSequence;
    preparedMember.characterIndex = *characterIndex;
    if (characterPresentation) preparedMember.characterPresentation = *characterPresentation;
}
for (std::uint32_t index = 0; index < 5; ++index) { ... }
```

### 9.1 **两个 classMask 的初值**

**⇒ `resolvedClassMask` 与 `registeredClassMask` 都在这里初始化。**

**⇒ 所以 `prepareClientLoadouts` 是那个"两阶段"的**另一条路径**（客户端路径 vs 服务端会话路径）。**

### 9.2 而 `for (index = 0; index < 5; ++index)`

**⇒ **5** 个职业（`custom1..5`）** ✓

## 十、关键结论

1. **`value8`/`optionalValue9` 就是 `**` 串的第二/第三个数字** —— 而零售会非零（140/72/11），我们恒写 0。
2. **`clipIndex` 与原索引相同时也跟着换** —— 说明弹匣表与武器表可能共用编号空间。
3. **`buildWeaponConfigStringUpdatePayload` 用 4096 而不是 64 KB**。
4. **`registerWeaponConfigString` 与 `liveRegisterWeaponConfigString` 是 30 行完全相同的两份** —— 一处重复。
5. **`%` 广播会触发客户端的 181 武器索引检查** ⇒ 所以彻底退役了广播。
6. **刷新靠"退出再重进"** —— 重进重解析整个 gamestate。
7. **`181 ** 646 0 0 1243 1242`（2026-08-26 实测）** —— 剥附件让注册计数器移动，武器落在 slot+1。
8. **"与 SessionStart 逐字节相同"是不变式**，因为 SessionStart 被证明能 spawn。
9. **`[[codol-181-is-weapon-index-vs-slot]]`** —— 181 的语义是索引 vs 槽位的混淆。
10. **奖励可选、职业必需**。
11. **客户端消息顺序是 `UpdateLoadout` 先于 `SessionStart`** ⇒ 第一次必然 `character_missing`。
12. **`prepareClientLoadouts` 是另一条有"两个 classMask"的路径**。

## 十一、未闭合点

- `value8`/`optionalValue9` 的实际语义。
- `clipIndex` 与 `weaponAssetIndex` 共用编号空间的依据。
- 两个注册函数的重复是否有意。
- `Appmain.cpp` 3680 行之后未读取。
