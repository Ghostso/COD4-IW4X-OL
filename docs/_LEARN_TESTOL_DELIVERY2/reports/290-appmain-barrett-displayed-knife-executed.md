# 290 · **"客户端显示 Barrett 而服务器执行另一把 ⇒ 一把完全能用的刀"**、34 条 zm 零售武器集、空手枪槽回退到刀

## 一、范围

本报告学习 `Appmain.cpp` 4340–4560 行。

## 二、湿活武器带的**注册与映射日志**

```php
for (const auto &weapon : RecordedWetworkWeapons)
{
    const auto registered = Bindings.registerModularWeaponConfigString(...);
    if (!registered)
    {
        logGameServer("... recordedIndex=" + N + " definition=\"" + weapon.definition + "\"");
        GameStateConfiguration.failed(DynamicWeaponRegistryRegistrationFailed);
        return false;
    }
    mapping += (mapping.empty() ? "" : ", ") + N + "->" + *registered;
}
logGameServer("Wetwork weapon map " + mapping);
```

### 2.1 三层

```text
① 逐条注册
② 失败 ⇒ 【整个 gamestate 失败】并打出完整的定义串
③ 成功 ⇒ 累积到 mapping（"1163->1234, 1164->1235, ..."）
```

### 2.2 而 `mapping` 是**完整的重映射表**

**⇒ 所以一次日志给出"录制索引 → 实际索引"的全部 51 对。**

**✓ 一个可审计的映射。**

## 三、**"客户端显示 Barrett 而服务器执行另一把"**（本组最重要的一段）

### 3.1 那段论证

```php
const auto nativeDynamicWeaponConfigStrings =
    Bindings.readDynamicWeaponConfigStrings(*firstDynamicWeaponAssetIndex);
if (!nativeDynamicWeaponConfigStrings)
{
    // The outgoing indexes must be the indexes in the native registry:
    // pmove uses those same values after the client spawns. Inventing a
    // dense outgoing tail here can make a client display Barrett while
    // the server executes a different WeaponDef (observed as the fully
    // functional knife fallback). Wait for a coherent native tail.
    GameStateConfiguration.failed(DynamicWeaponRegistryUnavailable);
    return false;
}
```

### 3.2 五层

```text
1. **出站索引必须是原生注册表里的索引**
2. 因为 **pmove 在客户端 spawn 之后用同样的值**
3. ⇒ 【在这里发明一个密集的出站尾部】可以让**客户端显示 Barrett 而服务器执行一个不同的 WeaponDef**
4. ⇒ 观测为【一把完全能用的刀的回退】
5. ⇒ 等待一个连贯的原生尾部
```

### 3.3 **"客户端显示 Barrett 而服务器执行另一把"**

**⇒ 这是一个**索引错位**的后果**：

```text
客户端按收到的索引 → 显示 Barrett
服务端按同一个索引 → 执行别的武器
```

**⇒ 因为两边的**索引→武器映射不同**。**

**⇒ 而"一把完全能用的刀"是那个"别的武器"的具体身份。**

**⇒ 与 §253 的 `1154`（专用服 Barrett / 客户端 `chicken_melee_mp`）**完全同一个问题** ✓**

**⇒ 所以那段注释的"刀回退"就是 §253 的 1154 分裂。**

### 3.4 而"等待一个连贯的原生尾部"

**⇒ 所以 `readDynamicWeaponConfigStrings` 返回 `nullopt` 时【不发明】而是**失败**。**

**⇒ 与 §236 的"返回空表是合法的"**不同** —— 那里是动态武器范围，这里是**实际内容**。**

**⇒ 两层服务不同目的** ✓

### 3.5 而**逐项核对**

```php
for (offset < nativeDynamicWeaponConfigStrings->size(); ++offset)
{
    const auto registered = SV_RegisterModularWeaponConfigString(
        gameState, *firstDynamicWeaponAssetIndex, (*nativeDynamicWeaponConfigStrings)[offset]);
    const auto expected = (uint32)*firstDynamicWeaponAssetIndex + offset;
    if (!registered || *registered != expected)
    {
        GameStateConfiguration.failed(DynamicWeaponRegistryRegistrationFailed);
        return false;
    }
}
```

### 3.6 **`*registered != *first + offset` ⇒ 失败**

**⇒ 所以**注册后的索引必须恰好等于"基址 + 偏移"**。**

**⇒ 这是一个**密集性**的要求。**

**✓ 与 §236 的"注册表是密集的"一致。**

## 四、**34 条 zm 零售武器集**（本组第二重要）

### 4.1 那段实测

```php
// SEED RETAIL'S WEAPON SET (12.127). Measured, not invented: these are the
// 34 modular weapon config strings a retail zm server published, read
// verbatim out of C-2021-7-31[15-32-16]zm's own gamestate at config string
// indices 7119-7152, i.e. weapon asset indices 1159-1192.
//
// WHY A WEAPON CHANGE IS AN ANIMATION EXPERIMENT. 12.126 measured, on the
// same binary minutes apart: retail loads 50 zones (~37 of them weapon
// zones) and builds a 123-entry generic_human animtree; this server loads
// 18 zones (3 weapon zones) and builds a 519-entry one. Everything wrong
// with the zombies follows from that table -- 12.124/12.125 -- so the
// question is whether the weapon zone set is what determines it.
//
// This is the experiment 12.92 refused to run. The user asked for it and
// I withdrew it on the claim that loadouts come from the backend; the
// backend supplies the LOADOUT, but the gamestate's weapon config strings
// are this server's to publish, and they are what the client precaches
// zones from.
//
// ADDITIVE AND SKIP-ON-CLASH. Anything already registered -- the dynamic
// range above, or a member loadout -- wins; this only fills gaps, so a
// failure to place one entry cannot break a session that worked before.
```

### 4.2 六层

```text
1. **34 条**来自 `C-2021-7-31[15-32-16]zm` 的 gamestate，cs 7119-7152 = 武器索引 1159-1192
2. 而为什么"改武器"是一个**动画实验**：
     · 零售加载 **50 个 zone**（约 37 个武器 zone）⇒ **123 项**的 `generic_human` animtree
     · 本服务器加载 **18 个 zone**（3 个武器 zone）⇒ **519 项**的
     · ⇒ 僵尸的一切问题都从那张表来
     · ⇒ 所以问题是"武器 zone 集合是否决定它"
3. 这是 12.92 拒绝做的实验
4. 用户要求过而**我撤回了**（理由是"loadout 来自后端"）
5. ⇒ 但后端只提供 **loadout**，而 gamestate 的武器配置串是**服务器发布的**
6. ⇒ 而它们正是**客户端从中预缓存 zone 的东西**
```

### 4.3 六个数字

```text
34 条         零售 zm 的模块化武器串
7119-7152     cs 范围
1159-1192     武器索引范围（34 个）
50 zones      零售加载
~37 weapon    其中武器 zone
123 项        零售的 animtree
18 zones      我们加载
3 weapon      其中武器 zone
519 项        我们的 animtree
```

### 4.4 **`123` vs `519` 的 animtree 大小**

**⇒ 519 是 123 的 4.2 倍。**

**⇒ 一个**反直觉**的结果 —— 我们加载更少的 zone 却得到**更大**的 animtree。**

**⇒ 而"僵尸的一切问题都从那张表来"。**

### 4.5 而"这是 12.92 拒绝做的实验"

**⇒ "用户要求过而我撤回了（理由是 loadout 来自后端）"**

**⇒ 这是一个**自我更正** —— 承认之前的拒绝是错的。**

**⇒ 理由**："后端只提供 loadout，而 gamestate 的武器配置串是服务器发布的，而它们正是客户端从中预缓存 zone 的东西。"**

**⇒ 与 §272/§274 的"§73h 被撤回"同族**（第三次撤回）。**

### 4.6 而**"ADDITIVE AND SKIP-ON-CLASH"**

```php
if (CodolGameServer::SV_AddModularWeaponConfigString(gameState, assetIndex, *parsed))
    ++seeded;
else
    ++skipped;
```

### 4.7 三层

```text
1. 已经注册的（动态范围或成员 loadout）【赢】
2. 这个只【填补空位】
3. ⇒ 放一项失败【不能破坏一个之前能工作的会话】
```

**✓ 一个安全的设计。**

### 4.8 而那 34 条与 §285 的 51 条**重叠 34 条**

**⇒ 让核对一下**：

```text
§285 的 51 条：1163..1213
§290 的 34 条：1159..1192
```

**⇒ 1159..1192 是 34 个 ✓**

**⇒ 而从内容看**：

```text
§290  1159 = "** 646 0 0 8738 9321"
§285  1163 = "** 646 0 0 8738 9321"
```

**⇒ ⚠ **同一个串在两个不同的索引上！**

**⇒ 所以 §285 的 1163 与 §290 的 1159 是**同一条记录**但索引差 4。**

**⇒ 因为 `firstDynamicWeapon` 在不同地图/会话里不同。**

**⇒ 与 §243 的"index 是加载顺序证据不是 ABI"**完全一致** ✓**

**⇒ **第四次确认那个原则。** ✓

### 4.9 而两个表的内容**大部分相同**

**⇒ 逐条对照**：

```text
§290                    §285
1159 "** 646 0 0 8738 9321"     1163 同上
1160 "** 249 0 0"               1164 同上
1161 "** 583 0 0 9930 ..."      1165 同上
1162 "** 604 0 0 9930 ..."      1166 同上
1163 "** 1108 0 0 9321 6747 6825"  1167 同上
1164 "** 1038 140 0 ..."        1168 同上
1165 "** 225 0 0"               1169 同上
1166 "** 670 0 0 ..."           1170 同上
1167 "** 180 0 0 ..."           1171 同上
1168 "** 652 0 0 8738"          1172 同上
1169 "** 839 0 0 ..."           1173 同上
1170 "** 320 0 0 ..."           1174 同上
1171 "** 409 0 0 ..."           1175 同上
1172 "** 625 0 0 ..."           1176 同上
1173 "** 810 72 0 ..."          1177 同上
1174 "** 788 0 0 ..."           1178 同上
1175 "** 965 0 0 ..."           1179 同上
1176 "** 956 0 0 ..."           1180 同上
1177 "** 1001 0 0 ..."          1181 同上
1178 "** 992 0 0 9321"          1182 同上
1179 "** 981 0 0 ..."           1183 同上
1180 "** 805 0 0 ..."           1184 同上
1181 "** 356 0 0 ..."           1185 同上
1182 "** 1106 0 0 ..."          1186 同上
1183 "** 571 0 0 ..."           1187 同上
1184 "** 639 0 0 ..."           1188 同上
1185 "** 939 0 0 ..."           1189 同上
1186 "** 633 0 0"               1190 同上
1187 "** 215 0 0 ..."           1191 同上
1188 "** 854 0 0 ..."           1192 同上
1189 "** 200 0 0 ..."           1193 同上
1190 "** 134 0 0 ..."           1194 同上
1191 "** 730 0 0 ..."           1195 同上
1192 "** 374 0 0 ..."           1196 同上
```

**⇒ **34 条中 34 条完全对应，只差索引 +4**。**

**✅ 这是一个**完美的两表交叉验证** —— 两个不同地图（Wetwork coop vs zm）的零售武器带**内容完全相同**而索引不同。**

**⇒ 所以"索引 = 加载顺序，内容 = 真正的 ABI"。**

**⇒ 这是本文件里**最强的一次**该项原则的确认。**

### 4.10 而 §285 的 1197..1213 是**额外的 17 条**

**⇒ 所以 zm 表（34 条）只覆盖 `1159..1192` 而湿活表（51 条）覆盖 `1163..1213`。**

**⇒ 差集是**17 条**（1197..1213）。**

**⇒ 所以 zm 的零售服务器发**更少**的模块化武器 —— 与"3 个武器 zone vs 37 个"一致吗？**

**⚠ 反了** —— 零售加载 37 个武器 zone 而我们 3 个，但零售发 34 条而我们（湿活）发 51 条。

**⇒ 所以"发多少条"与"加载多少 zone"**不是同一个量**。**

## 五、`registerWeaponConfigString` 的**两条失败路径**

```php
const auto primary = registerWeaponConfigString(gameState, registeredLoadout.primary, *first);
if (primary != None)
{
    GameStateConfiguration.failed(
        primary == Dependency ? PrimaryDependencyRegistrationFailed
                              : PrimaryWeaponRegistrationFailed,
        classIndex);
    return false;
}
```

### 5.1 两条

```text
Dependency  ⇒ PrimaryDependencyRegistrationFailed
Weapon      ⇒ PrimaryWeaponRegistrationFailed
```

**⇒ 与 §285 的 `WeaponConfigRegistrationFailure` 三值对应** ✓

### 5.2 而 `classIndex` 被传给 `failed`

**⇒ 所以失败能定位到职业。**

**✓ 与 §284 的 `failedClassIndex` 同族。**

## 六、**空手枪槽回退到刀**（本组第三重要）

```php
// Empty pistol slots are legal profile classes. Resolve the
// retail fallback before gamestate registration so the class
// does not fail at the secondary registration stage.
if (!registeredLoadout.secondary.weaponAssetIndex)
{
    const auto knife = Bindings.resolveWeaponConfigStringIndex("chicken_melee_mp");
    CodolGameServer::ClientWeaponSelection selection{};
    if (!knife || !Bindings.readWeaponSelection(*knife, selection) ||
        !selection.weaponAssetIndex)
    {
        GameStateConfiguration.failed(SecondaryWeaponRegistrationFailed, classIndex);
        return false;
    }
    registeredLoadout.secondary = selection;
}
```

### 6.1 四层

```text
1. 空手枪槽是【合法的 profile 职业】
2. ⇒ 在 gamestate 注册【之前】解析零售回退
3. ⇒ 这样职业不会在【副武器注册阶段】失败
4. 回退是 `chicken_melee_mp`（刀）
```

### 6.2 而三项确认

```text
resolveWeaponConfigStringIndex("chicken_melee_mp") 非空
readWeaponSelection 成功
selection.weaponAssetIndex 非零
```

**⇒ 三项全成才用。**

### 6.3 与 §285 的"`chicken_melee_mp` 必须留在基址 1154"**配套**

**§285**：刀的注册走 `SV_AddSimpleWeaponConfigString`（不走模块化）
**§290**：空手枪槽回退到刀

**⇒ 所以刀的**两条路径**都受保护。**

### 6.4 而 `resolveWeaponConfigStringIndex` 是 §260 的函数

**⇒ 而它现在有 `nameIndex` 缓存 ⇒ O(1)。**

**✓ 所以这里的调用不再花 165-300 ms。**

## 七、`classIndex` 的**从名字反推**

```cpp
const auto classIndex = name.size() == 7 && name.starts_with("custom") &&
    name.back() >= '1' && name.back() <= '5'
    ? (int32)(name.back() - '1')
    : -1;
```

### 7.1 四项

```text
name.size() == 7
starts_with("custom")
最后一个字符在 '1'..'5'
⇒ classIndex = 字符 - '1'
```

**⇒ 否则 -1。**

**⇒ 与 §257 的 `selectedLoadout.size() != 7` **完全相同的判据** ✓**

### 7.2 ⚠ **但 `"custom1"` 是 7 个字符**

```text
c-u-s-t-o-m-1 = 7 ✓
```

**⇒ 而 `name.back()` 是 `'1'`。**

**✓ 正确。**

### 7.3 而 `-1` 时的处理

```cpp
if (classIndex >= 0)
    GameStateConfiguration.registeredClass((uint32)classIndex);
```

**⇒ 只有 `>= 0` 才登记。**

**⇒ 所以一个不合法名字的 loadout 仍然被 `emplace` 但不登记 class。**

**⚠ 这允许一个"无 class 的 loadout"存在。**

## 八、`registeredSessionMembers.emplace` 的**重复检测**

```php
if (registeredMember.loadouts.empty() ||
    !registeredSessionMembers.emplace(preparedMember.xuid, std::move(registeredMember)).second)
{
    GameStateConfiguration.failed(PreparedLoadoutMismatch);
    return false;
}
```

### 8.1 两项

```text
loadouts 非空
emplace 成功（【xuid 不重复】）
```

**⇒ 两项任一失败 ⇒ 整个 gamestate 失败。**

**⇒ 所以**重复 xuid 是不可接受的**。**

## 九、关键结论

1. **湿活的 `mapping` 日志给出完整的"录制索引 → 实际索引"51 对。**
2. **"客户端显示 Barrett 而服务器执行另一把 ⇒ 一把完全能用的刀"** —— 索引错位的后果，与 §253 的 1154 分裂是同一问题。
3. **"出站索引必须是原生注册表的索引"** —— 因为 pmove 用同样的值。
4. **`*registered != *first + offset` ⇒ 失败** —— 密集性要求。
5. **34 条 zm 零售武器集来自 cs 7119-7152 = 武器索引 1159-1192。**
6. **零售 50 zones / ~37 武器 zone ⇒ 123 项 animtree；我们 18 / 3 ⇒ 519 项** —— 反直觉。
7. **"这是 12.92 拒绝做的实验"** —— 第三次撤回自我更正。
8. **"后端只提供 loadout，而 gamestate 的武器配置串是服务器发布的"** —— 关键区分。
9. **`SV_AddModularWeaponConfigString` 的 ADDITIVE AND SKIP-ON-CLASH** —— 安全地填补。
10. **⭐ 34 条 zm（1159..1192）与 51 条湿活（1163..1213）的重叠部分**完全对应**，只差索引 +4** —— 现存最强的"索引是加载顺序、内容是 ABI"证据。
11. **空手枪槽回退到 `chicken_melee_mp`**（刀）—— 在 gamestate 注册之前。
12. **`classIndex` 从名字反推（`size == 7` + `starts_with` + 末字符 '1'..'5'）** 与 §257 相同。
13. **重复 xuid ⇒ 整个 gamestate 失败。**

## 十、未闭合点

- 零售 50 zones 与 34 条武器串的关系（发 34 条而加载 37 个武器 zone）。
- `SV_SeedRetailWeaponSet` 的实验结果（是否改变 animtree）。
- "无 class 的 loadout"是否有害。
- `Appmain.cpp` 4560 行之后未读取。
