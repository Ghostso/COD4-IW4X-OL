# 308 · **`错误 1073 tag_weapon defaultvehicle`**、`48` 字节破坏死亡动画、**"缓存未命中也要缓存"**

## 一、范围

本报告学习 `Appmain.cpp` 8300–8520 行。

## 二、**`48` 字节破坏死亡动画**（本组第二重要）

```php
// THE OUTFIT MASK, HANDED OVER BY CLIENT NUMBER RATHER THAN CARRIED IN THE
// CUSTOMIZATION. Section 184h: forty-eight bytes on SvCharacterCustomization
// put forty-eight bytes into the unordered_map node that also holds the
// address-keyed native playerState, and every death lost its animation
// (durationMs=-1, T-pose) -- measured in both directions, reverting the same
// commit restored 1816 and 2983. So the mask travels beside the customization
// instead of inside it. Guarded by LoadoutMutex, which both providers take.
static std::map<uint32, std::array<uint32,12>> CharacterOptionMasks;
Server.setCharacterOptionMaskProvider([](uint32 clientNum) {
    const std::lock_guard lock(LoadoutMutex);
    const auto found = CharacterOptionMasks.find(clientNum);
    return found != CharacterOptionMasks.end() ? found->second : std::array<uint32,12>{};
});
```

### 2.1 六层

```text
1. `SvCharacterCustomization` 上**四十八字节**
2. ⇒ 把四十八字节放进**同时持有地址键控原生 playerState 的 `unordered_map` 节点**
3. ⇒ **每一次死亡都丢失它的动画**（`durationMs=-1`，**T-pose**）
4. ⇒ **双向测量**：回退同一个 commit 恢复了 **1816 和 2983**
5. ⇒ 所以掩码**在定制化【旁边】走**而不是**在里面**
6. ⇒ 由 `LoadoutMutex` 保护（两个 provider 都取它）
```

### 2.2 而"**1816 和 2983**"是**两个动画编号**

**⇒ 回退后恢复的两个值。**

**✅ 与 §148 的"ragdoll type 9"、"`0x80000`/`0xA0000`/`0x20000` corpse flags"相关。**

### 2.3 而**"地址键控的 playerState"**是关键

**⇒ 与记忆里"复制以地址为键的缓冲区会让指针失效"（§180 的 `0x00198A90`/`0x00DAF2AC`/`0x0041144C` 野跳）**同族。**

**⇒ 所以 `unordered_map` 的**节点地址**被原生代码持有 ⇒ **节点一变，指针全错**。**

**✅ 这是**第二次**同类问题（§184h 与 §180）。**

### 2.4 而"**双向测量**"是方法论

```text
加 48 字节 ⇒ 死亡动画丢
回退     ⇒ 恢复
```

**✅ 与 §305 的"接受杀死它；失败饶它"同族**（第六次"双向差分"）。

## 三、**`错误 1073 tag_weapon defaultvehicle`**（本组最重要的一段）

### 3.1 那段完整的因果

```php
// RESOLVE THE VIEWHANDS BY NAME RATHER THAN SHIP THE PLACEHOLDER.
// viewmodelIndex is an index into the MODEL configstrings, and the
// client finds its own by scanning them for "viewhands_tf141"
// (EngineBindings ~7345). The dedicated could not run the full
// character resolver -- that scheme is absent on OLfinal, section 16a --
// so it shipped 1, the first model slot, which is some unrelated mesh.
// The client duly attached the gun to that model's skeleton and drew a
// smeared object across the whole screen.
//
// ...
// ON, AND IT IS LOAD-BEARING. It was turned off once to rule it out by
// measurement, and the client died on the spot:
//     错误 1073 tag_weapon defaultvehicle
// The profile's own viewmodelIndex is the PLACEHOLDER 1 ("was placeholder 1"
// in this server's own log), and model configstring 1 on this map is
// `defaultvehicle`, which has no tag_weapon -- so the client fatals trying to
// attach the player's weapon to it. This override is not cosmetic: it is
// covering for an unported viewmodel index, and it must stay until the real
// one is derived.
```

### 3.2 八层

```text
1. **按名字解析 viewhands 而不是发占位符**
2. `viewmodelIndex` 是一个**模型配置串索引**，而客户端通过扫 `"viewhands_tf141"` 找到它自己的
3. 专用服**无法跑完整的角色解析器**（那个方案在 OLfinal 上缺席，§16a）
4. ⇒ 所以它发了 **1**，第一个模型槽，那是**某个无关的网格**
5. ⇒ 客户端**把枪挂到那个模型的骨架**上并在整个屏幕上画出一个**涂抹的物体**
6. **它曾经被关掉一次以通过测量排除它，而客户端当场死了**：`错误 1073 tag_weapon defaultvehicle`
7. ⇒ **profile 自己的 `viewmodelIndex` 是占位符 1，而这个地图上的模型配置串 1 是 `defaultvehicle`**
8. ⇒ 而它**没有 `tag_weapon`** ⇒ 所以客户端**致命**地试图把玩家的武器挂上去
```

### 3.3 **"这不是装饰性的：它在为一个未移植的 viewmodel 索引打掩护"**

**⇒ 三层**：

```text
1. 这个覆盖**不是装饰性的**
2. 它在**为一个未移植的 viewmodel 索引打掩护**
3. ⇒ 它**必须留着**直到真正的那个被推导出来
```

**✅ 与 §299 的"临时"标注同族**（第八次"标注临时/打掩护"）。

### 3.4 而**"profile 的 viewmodelIndex 是占位符 1"**

**⇒ 与 §283 的"`viewmodelIndex = 1` 是最小合法占位符"**完全一致** ✓**

**⚠ 而 §283 说"1..128 合法" —— 但**内容**可能是 `defaultvehicle`。**

**⇒ 所以"合法"不等于"正确"。**

**✅ 这是"清零不是错而是无效"的**另一面**：1 是有效的但**语义错**。**

### 3.5 而"**`CG_SetupClientCharacterInfo 0x00541800` 不读它**"

```php
// It also cannot be the invisible player, which is what the test was for:
// viewmodelIndex travels in the PLAYERSTATE (PlayerStateViewmodelIndexField,
// 10 bits) -- a player's OWN first-person hands -- and
// CG_SetupClientCharacterInfo 0x00541800 reads none of it. Its
// inputs are clientState +0x150, +0x154, +0x158, +0x7C and +0x4C.
```

### 3.6 五层

```text
1. 它**也不能**是那个隐形玩家（那正是这个测试要查的）
2. `viewmodelIndex` 在 **PLAYERSTATE** 里走（`PlayerStateViewmodelIndexField`，**10 位**）
3. = 一个玩家**自己的第一人称手**
4. 而 `CG_SetupClientCharacterInfo 0x00541800` **一点不读它**
5. ⇒ 它的输入是 **`clientState +0x150`、`+0x154`、`+0x158`、`+0x7C`、`+0x4C`**
```

### 3.7 而五个偏移与 §255 的对照

**§255**："`+0x150` 是 model index、`+0x7C` 是 character item、`+0x14` 是纯 body model index"

**⇒ 而这里多出 `+0x154`、`+0x158`、`+0x4C`。**

**⇒ 五个输入。**

**⚠ 而 §255 说 `+0x14` 是 body model —— 但这里没列 `+0x14`。**

**⇒ 可能 `+0x14` 是**另一处**读的。**

### 3.8 而 `PlayerStateViewmodelIndexField` 是 **10 位**

**⇒ 与 §283 的"slot 0 是 7 位"**不同的位宽**。**

**⇒ 所以不同字段不同位宽。**

### 3.9 而"**它替换了每一个角色自己的 viewhands 为 tf141**"

```php
// What it does do is replace every character's own viewhands with tf141,
// which is why both players had them, and that is a real wrongness worth
// not shipping.
```

**⇒ 三层**：

```text
1. 它**确实**替换了每一个角色自己的 viewhands 为 tf141
2. ⇒ **这就是为什么两个玩家都有它们**
3. ⇒ 而那是**一种真实的错误，值得不发出去**
```

**✅ 与 §300 的"`han_` 在 `mp_nuked` 不发布 ⇒ 玩家穿着 tf141 的手"**完全一致** ✓**

## 四、**`OLMOD_VIEWHANDS_TF141` 的默认开**

```cpp
static const bool ViewhandsOverrideEnabled = [] {
    std::array<char, 8> value{};
    std::size_t size = 0;
    if (getenv_s(&size, value.data(), value.size(), "OLMOD_VIEWHANDS_TF141") != 0 || size < 2)
        return true;
    return value[0] != '0';
}();
```

### 4.1 三层

```text
getenv_s 失败 或 size < 2  ⇒ true（【默认开】）
否则 ⇒ value[0] != '0'
```

### 4.2 **`size < 2` 意味着"空值 ⇒ 开"**

**⇒ 因为 `getenv_s` 返回的 `size` 含 NUL。**

**⇒ 所以 `size == 1` 是空串 ⇒ 开。**

**✓ 与 §274 的 `!size` 不同（那里 `size == 0`）。**

**⇒ 第十四种解析。**

### 4.3 而"**`OLMOD_VIEWHANDS_TF141=0` 关掉它；预期上面那个致命错误**"

**⇒ 所以这个开关的"关"是**危险的**。**

**⇒ 与 §254 的"宁可外观不对也不能崩"**相反** —— 这里关掉会崩。**

**⚠ 一个**反直觉**的开关方向。**

## 五、**"角色自己的手，不是 tf141 的"**

```php
// THE CHARACTER'S OWN HANDS, NOT tf141's. The resolver already produces
// them: character 545 resolves to
//     fpa_goose_ss_m_15, boo_empty_ss_s, fja_infbasea_sc_m_wht_00,
//     han_infbasea_tf_m_00, hea_socomb_sc_m
// and `han_` is the hands. viewmodelIndex, unlike modelIndex, really IS a
// model configstring index -- it is ten bits, validCharacterCustomization
// bounds it at 0x3FF, and resolveModelConfigStringIndex's 139 for
// viewhands_tf141 is what has been putting tf141 hands on everyone.
```

### 5.1 五层

```text
1. **角色自己的手，不是 tf141 的**
2. 解析器**已经产生**它们：角色 545 解析成 **五个名字**
3. 而 `han_` 是**手**
4. `viewmodelIndex` **不像** `modelIndex`，它**真的**是一个模型配置串索引
5. ⇒ 它是**十位**，`validCharacterCustomization` 在 **`0x3FF`** 处界它
6. ⇒ 而 `resolveModelConfigStringIndex` 对 `viewhands_tf141` 的 **139** 就是把 tf141 的手放在每个人身上的原因
```

### 5.2 而角色 545 的**五个名字**

```text
fpa_goose_ss_m_15        身体
boo_empty_ss_s           ？
fja_infbasea_sc_m_wht_00 ？
han_infbasea_tf_m_00     手
hea_socomb_sc_m          头？
```

**⇒ 五个，与 §296/§300 的 8 个前缀里的 5 个对应。**

**⇒ 而 `hea_` 是**头**（head），`han_` 是**手**（hands）。**

**✅ 这确认了两个前缀的语义。**

### 5.3 而 `139` 是 `viewhands_tf141` 的**索引**

**⇒ 在这个地图上。**

**⚠ 而索引是**每地图的**（§302 的原则）⇒ 所以 139 不可移植。**

**✅ 与 §292 的"参数化而不是枚举"配合 —— 所以这里**按名字**解析而不是硬编码 139。**

## 六、**"缓存未命中也要缓存"**（本组第三重要）

```php
// CACHE THE MISS TOO, and cache per character. resolveModelConfigStringIndex
// SCANS UP TO 1024 CONFIGSTRINGS and this provider runs per frame per client;
// storing only successes is what a player measured as "extremely laggy" the
// last time this pattern was written. And do not latch on an EMPTY name list:
// the names arrive from the DObj build a frame later than the first
// customization.
struct ViewhandsCacheEntry
{
    std::uint16_t characterItemId{};
    std::uint16_t index{};
    bool resolved{};
};
static std::map<uint64, ViewhandsCacheEntry> ViewhandsCache;
static std::atomic<std::uint16_t> CachedGenericViewhandsIndex{};
```

### 6.1 六层

```text
1. **未命中也要缓存**，且**按角色缓存**
2. `resolveModelConfigStringIndex` **扫最多 1024 个配置串**
3. ⇒ 而这个 provider **每帧每客户端**跑
4. ⇒ **只存成功**就是一个玩家实测到的 "极其卡顿"（上次写这个模式时）
5. ⇒ 而**不要在【空的】名字列表上闩锁**：
6. ⇒ 因为名字**比第一次定制化晚一帧**从 DObj 构达到
```

### 6.2 **三层缓存**

```text
characterItemId    缓存键（角色变了就失效）
index              索引
resolved           是否解析成功
```

**⇒ 三项 ⇒ 所以"解析失败"用 `resolved = false` + `index = 1`（哨兵）表示。**

**⚠ 而 `index = 1` 是**占位符 1** —— 那个会导致 `defaultvehicle` 致命的值。**

**⇒ 但因为它 `resolved = false` ⇒ **不会被用**（见下面的判断）。**

### 6.3 而**缓存的四层判断**

```cpp
if (handsCache.characterItemId == presentation->characterItemId &&
    (handsCache.resolved || handsCache.index))
{
    if (handsCache.resolved) characterHands = handsCache.index;
}
else
{
    const auto names = Bindings.characterModelNames(clientNum);
    if (!names.empty())
    {
        handsCache.characterItemId = presentation->characterItemId;
        handsCache.resolved = false;
        handsCache.index = 1;   // asked, and the answer is remembered
        for (const auto &name : names) { ... }
    }
}
```

### 6.4 三项

```text
① 缓存键匹配 且（已解析 或 有 index）
② ⇒ 若已解析 ⇒ 用缓存
③ 否则 ⇒ 重新查（但**只在名字非空时**写入缓存）
```

**⇒ 所以"名字为空"⇒ **不写缓存** ⇒ 下次重试。**

**✅ 这正是"不要在空的名字列表上闩锁"的实现。**

### 6.5 而 `handsCache.index = 1` 的**注释**

```cpp
handsCache.index = 1;   // asked, and the answer is remembered
```

**⇒ 三层**：

```text
1. `index = 1` 是**哨兵**
2. 意思："问过了，而答案被记住了"
3. ⇒ 而 `resolved = false` ⇒ 所以**不会被用**
```

**✓ 一个"三态"的缓存**（未问 / 问了-失败 / 问了-成功）。

**✅ 与 §181–190 的 `optional<T*>` 三态同族。**

## 七、**"解析或注册，与身体用的同一两步"**

```cpp
// RESOLVE OR REGISTER, the same two-step the body uses. The map does not
// publish `han_infbasea_tf_m_00`, so resolving alone always failed and every
// player fell back to tf141's hands -- while the gamestate publisher had
// ALREADY given that exact name a band slot. Registering again returns the
// slot it already holds, so this simply uses it.
auto resolved = Bindings.resolveModelConfigStringIndex(name);
if (!resolved)
    resolved = Server.registerOutfitModelConfigString(name);
```

### 7.1 五层

```text
1. **解析或注册，与身体用的同一两步**
2. 地图**不发布** `han_infbasea_tf_m_00`
3. ⇒ 所以**只解析总是失败**而**每个玩家都回退到 tf141 的手**
4. ⇒ **而 gamestate 发布器已经给那个确切名字一个带槽**
5. ⇒ ⇒ **再次注册返回它已持有的槽** ⇒ 所以这里**就用它**
```

### 7.2 **"再次注册返回它已持有的槽"**

**⇒ 三层**：

```text
1. `registerOutfitModelConfigString` 是**幂等**的
2. ⇒ 同一个名字第二次注册返回同一个槽
3. ⇒ 所以"再注册一次"是安全的
```

**✅ 与 §299 的"`scriptModels` 两路索引"**完全同一模式** ✓**

### 7.3 而两段日志

```text
成功 ⇒ "viewhands: the CHARACTER'S OWN hands index=<n> name=<name>"
失败 ⇒ "viewhands: character hands HAVE NO BAND SLOT name=<name> -- falling back to <tf141>"
```

**⇒ 两句都**明说**结果。**

## 八、三个缓存的**统一形状**

```text
handsCache                 每角色（characterItemId 作键）
CachedGenericViewhandsIndex  全局（atomic）
（characters 的 ModelSlotReserve 那 52 个槽）
```

**⇒ 所以手部的解析有**三层缓存**：**

```text
1. 角色自己的手（按 characterItemId）
2. tf141 的（全局 atomic）
3. 带槽的分配（52 个预留）
```

**✅ 与 §259 的 `modelHints`（验证过的提示）是**第四层**。**

## 九、关键结论

1. **`48` 字节破坏死亡动画** —— `unordered_map` 节点同时持有**地址键控的 playerState**。
2. **"双向测量：回退恢复了 1816 和 2983"** —— 第六次双向差分。
3. **`错误 1073 tag_weapon defaultvehicle`** —— 占位符 1 在那个地图上是 `defaultvehicle`（无 `tag_weapon`）。
4. **"这不是装饰性的：它在为一个未移植的 viewmodel 索引打掩护"**。
5. **"合法不等于正确"** —— 1 是有效索引但**语义错**。
6. **`viewmodelIndex` 在 PLAYERSTATE 里走（10 位）**，而 `CG_SetupClientCharacterInfo` **不读它**。
7. **五个输入**：`clientState +0x150/+0x154/+0x158/+0x7C/+0x4C`。
8. **"它替换了每一个角色自己的 viewhands 为 tf141，两个玩家都有它们就是原因"**。
9. **`OLMOD_VIEWHANDS_TF141=0` 会崩** —— 一个**反直觉**的开关方向。
10. **角色 545 解析成五个名字**，确认 `hea_` 是头、`han_` 是手。
11. **`139` 是 `viewhands_tf141` 的索引**（每地图的，不可硬编码）。
12. **"缓存未命中也要缓存"** —— 因为 `resolveModelConfigStringIndex` 扫 1024 个而 provider 每帧每客户端跑。
13. **"只存成功"就是一个玩家实测到的"极其卡顿"**。
14. **"不要在空的名字列表上闩锁"** —— 名字晚一帧到达。
15. **三态缓存**：未问 / 问了-失败（`index = 1` 哨兵 + `resolved = false`）/ 问了-成功。
16. **"解析或注册，与身体同一两步"** —— `registerOutfitModelConfigString` 幂等。
17. **三层 + 一层的缓存**（角色手 / tf141 全局 / 52 带槽 / §259 的提示）。

## 十、未闭合点

- `1816`/`2983` 两个动画编号的具体身份。
- `+0x154`/`+0x158`/`+0x4C` 三个 clientState 字段的语义。
- `boo_`/`fja_`/`ves_`/`heg_` 四个前缀的语义。
- `Appmain.cpp` 8520 行之后未读取。
