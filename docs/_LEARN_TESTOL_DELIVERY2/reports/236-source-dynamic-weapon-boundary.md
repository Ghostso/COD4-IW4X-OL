# 236 · 动态武器边界的三个错、一次"边界比表还大"的实测

## 一、范围

本报告学习 `EngineBindings.cpp` 8299–8499 行。

## 二、类型枚举的两个哨兵

```cpp
// CODDIFF(1649370): the configstring class enum gained two members,
// so both sentinels shift +2 - 3.3.3.3 asks for `19 || >= 21`.
// The gamestate parser is the source: A 0x46DBF6 rejects an index
// unless `type >= 0x15 || type == 19`, C 0x472E56 unless
// `type >= 0x17 || type == 21`, and the weapon-count consumers
// A 0x57A26E / C 0x590A6F test the same pair of values.
if (type == 21 || type >= 23)
{
    configuredBoundary = index;
    break;
}
```

### 2.1 两个 build 的判据

```text
A（3.3.3.3）  0x46DBF6  接受 type >= 0x15(21) || type == 19
              0x57A26E  同样的两个值
C（本 build） 0x472E56  接受 type >= 0x17(23) || type == 21
              0x590A6F  同样的两个值
```

**两个哨兵都 +2** —— 从 `{19, 21}` 变成 `{21, 23}`。

### 2.2 三处独立证据

**每处都是成对出现**：

```text
gamestate 解析器（0x46DBF6 / 0x472E56）
武器计数消费者（0x57A26E / 0x590A6F）
```

**所以判据不是单点观测** —— 两个不同用途的函数用同一对值。

## 三、`registryCount < configuredBoundary` 的早退

```cpp
const auto* registryCount = (const uint32*)(module_ + WeaponRegistryCountRva);
if (!readableSpan(registryCount, sizeof(*registryCount)) ||
    *registryCount < *configuredBoundary)
{
    return configuredBoundary;
}
```

**"注册表计数小于配置边界 ⇒ 直接返回配置边界"** —— 不需要再扫。

**这是"没有动态武器"的快速路径。**

## 四、"skip and retag" 的循环

```cpp
const auto last = std::min<uint32>(*registryCount, WeaponConfigStringCount - 1);
for (uint32 index = *configuredBoundary; index <= last; ++index)
{
    const auto name = readWeaponDefinitionName(index);
    if (!name) { log("dynamic weapon boundary entry unreadable index=" + N); return nullopt; }
    if (SV_ParseModularWeaponConfigString(*name))
        return (uint16)index;
    if (name->starts_with("**"))
    {
        log("dynamic weapon boundary entry malformed index=" + N + " name=" + *name);
        return nullopt;
    }
    types[WeaponConfigStringBase + index] = 19;
}
```

### 4.1 三种情形

```text
名字可解析为模块化配置串  ⇒ 【找到了边界】，返回该 index
名字以 "**" 开头但不可解析 ⇒ 【格式错误】，返回 nullopt
其它（普通武器）          ⇒ 把类型改成 19，继续
```

### 4.2 为什么"重打标签"

```cpp
types[WeaponConfigStringBase + index] = 19;
```

**注释**：

```text
The shipped type table fixes the modular boundary at 1224. Runtime
alpha WeaponDefs are ordinary base weapons, so adding them before the
map's normal weapon walk can push later shipped WeaponDefs beyond
that static boundary. The registry remains dense: skip and retag
every plain WeaponDef until the first actual "** ..." entry. The
returned index must describe the native table itself because both
pmove and the outgoing gamestate use it as the weapon identity.
```

**三个要点**：

```text
1. 随包类型表把模块化边界固定在 1224
2. 运行时的 alpha WeaponDef 是【普通基础武器】，所以在正常武器遍历之前加入它们
   会把后面的随包 WeaponDef 推过那个静态边界
3. 所以：跳过并把每一个普通 WeaponDef 重打标签，直到第一个真正的 "** ..." 条目
```

### 4.3 `19` 是"普通武器"的类型

**`type == 19` 在 3.3.3.3 的判据里是"非武器"哨兵**，而这里把普通 WeaponDef 打上 19。

**所以 19 = "普通/基础武器"** —— 而模块化武器是 `>= 23` 或 `== 21`。

### 4.4 `weaponAssetIndex` 是**身份**

```text
The returned index must describe the native table itself because both
pmove and the outgoing gamestate use it as the weapon identity.
```

**"pmove 与出站 gamestate 都用它作为武器身份"** ⇒ 所以不能"重新编号"，只能"找到真实边界"。

## 五、那次"边界比表还大"的实测（本组最重要的一段）

### 5.1 原判据的问题

```cpp
if (!readableSpan(registryCount, sizeof(*registryCount)) ||
    *registryCount < firstDynamicWeaponAssetIndex ||
    *registryCount >= WeaponConfigStringCount)
{
    ...
    return std::nullopt;
}
```

**三个条件 ⇒ 都返回 `nullopt`。**

### 5.2 实测

```cpp
// ★ 2026-10-18（会话 28330 / 第 5 项）：**边界比表还大不是"没有动态武器"，是边界算错了**。
//   19:22 那局实测：`dynamic weapon registry range unavailable first=1236 count=1231`
//   ⇒ `first`(1236) > `*registryCount`(1231)，原判据直接 nullopt，
//   连锁 `gamestate configuration FAILED stage=dynamic_weapon_registry_unavailable`、整局起不来。
```

### 5.3 三个数字

```text
first = 1236      ← firstDynamicWeaponAssetIndex
count = 1231      ← *registryCount
差 = 5
```

**`first > count` 意味着"注册表里根本没有这么多武器"** —— 而 `firstDynamicWeaponAssetIndex` 的算法（§236）从配置串类型表找边界，**可能找到比注册表还大的边界**。

### 5.4 修法的三层

```cpp
if (readableSpan(registryCount, sizeof(*registryCount)) &&
    *registryCount >= WeaponConfigStringCount)
{
    // 表本身越界才是真错，保持原来的失败语义。
}
else if (readableSpan(registryCount, sizeof(*registryCount)))
{
    log("dynamic weapon boundary clamped first=N count=M -> empty table (no dynamic weapons this map)");
    return std::vector<SvModularWeaponConfigString>{};
}
const auto count = readableSpan(...) ? *registryCount : UINT32_MAX;
log("dynamic weapon registry range unavailable first=N count=M");
return std::nullopt;
```

### 5.5 三层的语义

```text
registryCount >= 1700（表越界）      ⇒ 真错，返回 nullopt（保持原语义）
registryCount 可读但 < WeaponConfigStringCount
                                    ⇒ 【返回空表】，记录 "clamped"
registryCount 不可读                ⇒ count = UINT32_MAX，返回 nullopt
```

**"空表"是合法的** —— 因为"这张地图没有动态武器"是一个正常状态。

### 5.6 那句"原路径一字不改"

```text
修法：`first > count` 时返回**空表**（合法），并把夹紧写进日志；`first <= count` 的原路径一字不改。
```

**只在新条件上分支，不动老路径** —— 这是"最小改动"的做法。

### 5.7 因果链

```text
first > count
  ⇒ 原判据返回 nullopt
  ⇒ gamestate configuration FAILED stage=dynamic_weapon_registry_unavailable
  ⇒ 整局起不来
```

**"整局起不来"** —— 这是又一个"一个边界错误导致整场无法进行"的实例。

## 六、`readDynamicWeaponConfigStrings` 的主循环

```cpp
result.reserve(*registryCount - firstDynamicWeaponAssetIndex + 1);
for (auto index = (uint32)firstDynamicWeaponAssetIndex;
     index <= *registryCount;
     ++index)
{
    const auto name = readWeaponDefinitionName(index);
    const auto configString = name
        ? SV_ParseModularWeaponConfigString(*name)
        : std::nullopt;
    if (!configString)
    {
        log("dynamic weapon registry entry invalid index=" + N +
            " name=" + (name ? *name : "<unreadable>"));
        return std::nullopt;
    }
    result.push_back(*configString);
}
```

### 6.1 `reserve` 的算术

```cpp
*registryCount - firstDynamicWeaponAssetIndex + 1
```

**`+1` 因为闭区间** —— `first..count` 共 `count - first + 1` 项。

### 6.2 循环上界是 `<=`

**闭区间** ✓

### 6.3 任一无效即整批失败

```cpp
if (!configString) return std::nullopt;
```

**不是跳过** —— 因为动态武器是一个连续的块，中间不能有洞。

## 七、`registerModularWeaponConfigString`：三处校验

```cpp
if (!weaponLookup_ || !weaponResolver_ || configString.empty() ||
    configString.size() >= 128 ||
    configString.find('\0') != npos ||
    !SV_ParseModularWeaponConfigString(configString))
{
    return std::nullopt;
}
```

### 7.1 六项

```text
1. 两个函数已绑定
2. 非空
3. 长度 < 128
4. 无 NUL
5. 可解析为模块化配置串
```

**五项**（我把前两项算一项）。

### 7.2 注册后的双向验证

```cpp
const auto weaponAssetIndex = weaponResolver_(nativeName.c_str(), nullptr);
if (!weaponAssetIndex ||
    weaponAssetIndex >= WeaponConfigStringCount ||
    weaponLookup_(nativeName.c_str()) != weaponAssetIndex)
{
    log(...);
    return std::nullopt;
}
```

**三项**：

```text
注册返回非零
注册号在范围内
【反查得到同一个号】
```

**"反查得到同一个号"是最强的一项** —— 它证明注册表真的记住了这个名字。

**与 §201 里"对称往返"不同** —— 这里的两侧是**两个不同的引擎函数**（`weaponResolver_` 与 `weaponLookup_`），所以是真实的一致性检查。

## 八、`readClientBookingSelection`：五个静默 nullopt

### 8.1 那段"从未成功过一次"

```cpp
// OLMOD(booking-selection-refusal-reasons): section 75. THIS READER HAS
// FIVE SILENT `return std::nullopt` PATHS AND ONE CALLER THAT TREATS ALL
// OF THEM AS "the client did not book anything".
//
// scan-image-literals.py reports every one of the five offsets below as
// ABSENT FROM out.exe -- 3.3.3.3 mentions 0xF730 thirty-eight times,
// 0xF738 fourteen, 0xF73C twenty-six, and this build mentions none of
// them at all. They are offsets into the CLIENT's room singleton and
// they are the other build's, so this function cannot have succeeded
// once on 1649370.
```

### 8.2 三个偏移的计数

```text
0xF730   3.3.3.3 提了 38 次
0xF738   3.3.3.3 提了 14 次
0xF73C   3.3.3.3 提了 26 次
本 build 一个都没有
```

**"这个函数在 1649370 上不可能成功过一次"** —— 而不是"偶尔失败"。

### 8.3 为什么没人注意到

```text
Nothing noticed, because CODOL_GameServerConfigureBooking falls back
to the map and gametype in its command string and every cycle passes
those explicitly. What is actually lost is the SAFETY NET: section 28c
records that `playlistMapRotateSequentially 0` makes each side roll
its own map, and that booking one the client did not roll wedges the
session at `clients=1 active=0` WITH NO ERROR. This reader exists to
catch exactly that, and it has been dead the whole time.
```

**三层**：

```text
1. 有回退路径（命令串里带 map 与 gametype）⇒ 功能正常
2. 丢失的是【安全网】—— 捕获"双方各自 roll 地图"的不一致
3. 那种不一致会让会话卡在 `clients=1 active=0` 且【无错误】
```

**"这个读取器正是为了捕获那个，而它整段时间都是死的。"**

### 8.4 那句方法论

```text
Naming the paths does not fix the offsets. It stops the next reader
believing the silence (section 36g).
```

**"命名这些路径不修偏移。它阻止下一个读者相信那个沉默。"**

**这与 §225/§234/§235 是同一原则的第四次出现。**

### 8.5 `refuse` lambda 的封顶

```cpp
const auto refuse = [this](const char* reason) -> optional<ClientBookingSelection> {
    if (bookingSelectionRefusalLogCounter_++ < 4)
        log("client booking selection unavailable reason=" + reason + ...);
    return std::nullopt;
};
```

**封顶 4 次** —— 而原因串区分。

### 8.6 那条被更正的状态说明

```cpp
// THE OFFSETS ARE 1649370'S NOW -- section 187i. This line used
// to end "(the offsets are 3.3.3.3's -- section 75)", and after
// the port that sentence was simply false: it named a cause
// that had been fixed and would have sent the next reader
// straight back to a solved problem. A refusal says WHICH gate
// refused and nothing more.
```

**"在移植之后那句话就是假的：它命名了一个已经修好的原因，会把下一个读者径直送回一个已解决的问题。"**

**"一个拒绝只说【哪个门】拒绝了，仅此而已"** —— 这是错误信息的正确写法。

## 九、关键结论

1. **两个哨兵从 `{19,21}` 变成 `{21,23}`**，两个函数成对验证。
2. **"skip and retag 到 19"** 是因为运行时 alpha 武器会把随包武器推过静态边界 1224。
3. **武器索引是身份，不能重新编号** —— 只能找到真实边界。
4. **`first > count` 是"边界算错"不是"没有动态武器"** —— 实测 `1236 vs 1231`。
5. **修法是返回空表**（合法）并记录夹紧，老路径一字不改。
6. **注册后的双向验证**（resolver 与 lookup 两个不同函数）是真实的一致性检查。
7. **五个静默 nullopt 让一个安全网死了整段时间** —— 而有回退路径所以没人注意。
8. **"命名路径不修偏移，但阻止下一个读者相信沉默"**。

## 十、未闭合点

- 五个 booking 偏移仍是 3.3.3.3 的（已在 §187i 之外说明）。
- `EngineBindings.cpp` 8499 行之后未读取。
