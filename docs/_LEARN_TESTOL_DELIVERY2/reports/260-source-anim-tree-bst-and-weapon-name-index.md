# 260 · XAnimParts 的六个偏移、动画树 BST 的二分查找、`165–300 ms` 的单次配置串扫

## 一、范围

本报告学习 `EngineBindings.cpp` 16442–16650 行。

## 二、`resolveAnimConfigStringIndex` 的四项前置

```cpp
constexpr std::uint32_t AssetTypeXAnim = 2;
if (!configStringGet_ || !dbFindXAssetHeader_ || !CCS_Initialized() ||
    animName.empty() || animName.size() >= 128 ||
    animName.find('\0') != std::string_view::npos)
    return nullopt;
```

### 2.1 **同一组四项在三个函数里重复**

```text
resolveModelConfigStringIndex    （还有 modelName.front() == '*'）
resolveAnimConfigStringIndex
resolveWeaponConfigStringIndex
```

**共同的三项**：

```text
CCS_Initialized()
name 非空
name.size() < 128
name 无 NUL
```

**⇒ 三个函数各自写一遍。**

### 2.2 **"居留优先"（RESIDENCY FIRST）**

```cpp
// RESIDENCY FIRST, exactly as the model resolver does. A name the engine does
// not hold must come back empty rather than matching a stale band entry.
if (!findXAsset(AssetTypeXAnim, std::string(animName).c_str(), false).data)
    return nullopt;
```

**⇒ 引擎不持有的名字必须返回空，而不是匹配一个陈旧的 band 条目。**

**这是一个"先证明存在再查索引"的顺序** —— 与 §259 的提示缓存**相反**（那里先查提示）。

**⇒ 两处的顺序不同，因为一个是有缓存的（提示先验），一个是无缓存的（必须全扫）。**

### 2.3 而这里用**精确比较** `*candidate == animName`

```cpp
if (candidate && *candidate == animName)
```

**⇒ 而 §259 的模型解析用 `_stricmp`。**

**⇒ 动画名的大小写敏感而模型名不敏感。**

**这是一个有意的区分** —— 但没有注释说明。

### 2.4 那段别名转换的注释

```cpp
// 514880 subtracts band base AND its reserved-slot flag (1)
// before 661C50. 74A420/7858B0 put that zero-based NCS alias
// into the tree map consumed by 540040/785870. Packet aliases
// are not the flat configstring-relative index.
return SV_AnimationAliasFromConfigString(AnimConfigStringBase + index);
```

### 2.5 五个地址

```text
514880  减 band 基址与保留槽标志(1) 之后交给 661C50
661C50  
74A420/7858B0  把零基 NCS 别名放进 540040/785870 消费的树映射
```

### 2.6 三层

```text
1. 别名 = 配置串索引 - band 基址 - 1
2. 所以"保留槽标志 1"被减去 ⇒ band 基址 + 1 的别名为 0
3. ⇒ 包里的别名【不是】配置串相对索引
```

**⇒ 所以 `SV_AnimationAliasFromConfigString` 做的正是这个减法。**

## 三、`resolveScriptModelAnimationTree`：**动画树的 BST 二分查找**（本组最重要的一段）

### 3.1 五项前置

```cpp
if (!module_ || !bindingCommitted_.load() || aliases.empty() || aliases.size() > 8 ||
    any_of(aliases, [](a) { return !a || a > 0xFFF; }))
    return nullopt;
```

```text
module 非空
bindingCommitted_ 为真
aliases 非空
aliases.size() <= 8          ← 【最多 8 个】
所有 alias 在 1..0xFFF
```

### 3.2 两个全局

```cpp
constexpr auto countAddress = module_ + 0x749C634;     // 计数
constexpr auto registryAddress = module_ + 0x749C534;  // 指针数组
const std::uint32_t count;                              // 必须 1..64
const std::uint32_t nodeCount;                          // 必须 1..4096
```

### 3.3 **`0x749C634` 与 `0x749C534`**

**⇒ 两个相邻的地址（差 `0x100`）。**

**`0x749C534` 是"指针数组"而 `0x749C634` 是"计数"。**

### 3.4 遍历循环

```cpp
std::optional<uint8> result;
for (std::uint32_t i = 1; i <= count; ++i)          // ← 【闭区间 1..count】
{
    const std::uint8_t *definition{};
    memcpy(&definition, module_ + 0x749C534 + 4*i, sizeof(definition));   // ← 【+4*i 即跳过 [0]】
    if (!definition || !readableSpan(definition, 12)) continue;
    const auto wireId = definition[10];                                    // ← 【+10 是线 id】
    std::uint32_t nodeCount{}; memcpy(&nodeCount, definition, 4);           // ← 【+0 是节点数】
    if (!wireId || wireId > 31 || !nodeCount || nodeCount > 4096) continue;

    bool matches = true;
    for (const auto alias : aliases)
    {
        const std::uint8_t *link{};
        memcpy(&link, definition + 4, sizeof(link));                       // ← 【+4 是 BST 根】
        std::uint16_t node{};
        for (unsigned depth = 0; link && depth < 64; ++depth)             // ← 【最多 64 层】
        {
            if (!readableSpan(link, 12)) break;
            std::uint16_t key{}; memcpy(&key, link, 2);                    // ← 【+0 是 key】
            if (key == alias) { memcpy(&node, link + 2, 2); break; }        // ← 【+2 是 node】
            memcpy(&link, link + (key > alias ? 4 : 8), sizeof(link));     // ← 【+4 左、+8 右】
        }
        if (!node || node >= nodeCount) { matches = false; break; }        // ← 【0 是"没找到"】
    }
    if (!matches) continue;
    if (result) return nullopt;                                            // ← 【二义即失败】
    result = wireId;
}
return result;
```

### 3.5 **一个 12 字节的 BST 节点**

```text
+0   key      uint16
+2   node     uint16
+4   left     指针
+8   right    指针
```

**⇒ 12 字节 = 2 + 2 + 4 + 4** ✓

### 3.6 **`key > alias ? 4 : 8`**

```text
key > alias  ⇒ 走 +4（【左】）
key < alias  ⇒ 走 +8（【右】）
key == alias ⇒ 已在上面的 if 里 break
```

**⇒ 所以 `+4` 是"更小的子树的指针"而 `+8` 是"更大的"。**

**⚠ 这是一个**反向**的 BST** —— 通常 `+4` 是左（小）而 `+8` 是右（大）。

**⇒ 而这里 `key > alias` 走 `+4` ⇒ 所以 `+4` 是"key 更小"的方向 ⇒ 它是左子树 ✓**

**✓ 标准 BST。**

### 3.7 **`depth < 64` 的界**

**⇒ 树最多 64 层。**

**⇒ 防止环或损坏的树导致无限循环。**

**这是一个正确的防御** ✓

### 3.8 `node == 0` 是"没找到"

```cpp
if (!node || node >= nodeCount) { matches = false; break; }
```

**⇒ `node == 0`（初始值）表示 BST 里没有这个 alias。**

**⇒ 而 `node >= nodeCount` 表示越界。**

### 3.9 **"二义即失败"**

```cpp
// OLMOD(script_model_tree_resolution): ambiguity fails closed;
// sharing an alias is not permission to pick an arbitrary tree.
if (result) return nullopt;
result = wireId;
```

**⇒ 如果**两个**定义的 alias 集合都匹配 ⇒ 返回 nullopt。**

**"共享一个 alias 不是挑一棵任意树的许可。"**

**⇒ 这与 §244 里 `readAttachmentModelSlot` 的 `ambiguous = true` 同族。**

### 3.10 整体的语义

```text
输入：一组 alias（最多 8 个，都是 1..0xFFF）
输出：唯一匹配的 wireId（1..31）
```

**⇒ 一个"用 alias 集合识别动画树"的查询。**

**而 `wireId` 是 5 位（0..31）** —— 与 32 个动画树槽一致。

## 四、`animationNotifyTimes`：**XAnimParts 的六个偏移**（本组第二重要）

### 4.1 那段 CODREF

```cpp
// CODREF(out.exe): 485B40 loads 88 bytes; 485AC0 resolves u16 marker
// names in 8-byte entries. 789E20 reads count+27, pointer+80, frameCount+14,
// framerate+40, and returns entry.time * frameCount / framerate.
if (!parts || !readableSpan(parts, 88)) return nullopt;
```

### 4.2 五个偏移

```text
+0    名字指针（char*）
+14   frameCount（uint16）
+27   notify count（uint8）
+40   framerate（float）
+80   markers 指针
```

**而 `88` 字节 = XAnimParts 尺寸**（§143/§250）✓

### 4.3 **`+27` 是单字节**

```cpp
const auto count = parts[27];
...
if (!count) return result;      // ← 【0 个 marker 合法】
```

**⇒ 最多 255 个 marker。**

### 4.4 **marker 条目是 8 字节**

```cpp
memcpy(&id, markers + 8*i, sizeof(id));               // +0  id  uint16
memcpy(&normalized, markers + 8*i + 4, sizeof(normalized));   // +4  time float
```

```text
+0   id        uint16
+2   （未用）
+4   time      float（0..1 归一化）
```

**⇒ 8 字节里只有 6 个被用。**

### 4.5 **时间换算**

```cpp
const auto seconds = normalized * frames / rate;
```

```text
seconds = normalized * frameCount / framerate
```

**⇒ XAnimParts 存的 time 是**归一化的**（0..1 表示"整段动画的百分比"）。**

**⇒ 换算成秒需要 `× frameCount / framerate`。**

### 4.6 四项校验

```cpp
if (!frames || !isfinite(rate) || rate <= 0 || !markers ||
    !readableSpan(markers, count * 8)) return nullopt;
...
if (!isfinite(normalized) || normalized < 0 || normalized > 1 ||
    !isfinite(seconds) || seconds > FLT_MAX) return nullopt;
```

```text
frames != 0
rate 有限、> 0
markers 非空且可读 count*8
每个 normalized 有限且在 0..1
seconds 有限且 <= FLT_MAX
```

**⚠ `seconds > FLT_MAX` 恒为假**（因为 `seconds` 已经是 `double` 而 `FLT_MAX` 巨大）。

**⇒ 这个检查是**无效的** —— 除非 `normalized * frames / rate` 溢出 `double`（不可能）。**

**这是一个冗余/无效的检查** —— 值得指出。

**而真正的意图可能是 `seconds > 某个合理的上限`。**

### 4.7 而 `normalized > 1` 被拒绝

**⇒ 所以一个 time > 1 的 marker 让整个函数失败。**

**⇒ 这可能是过严** —— 因为一些动画可能有 > 1 的 time（如果它跨越多次循环）。

### 4.8 那句"拒绝默认/缺失资产的替换"

```cpp
const auto residentName = readCString(name, 128);
if (!residentName || *residentName != animName)
    return nullopt; // refuse a default/missing asset substitution
```

**⇒ 资产自证**（与 §257/§258/§259 同族）。

## 五、`animationNotifyName`：**`pool + 20*id + 4`**

```cpp
// CODREF(out.exe): 786B28 loads the marker's u16 ID into ESI;
// 786860 uses that ID to form pool+20*ID+4 for its notify queue.
// This is not the attachment/configstring namespace.
constexpr std::size_t NotifyStringPoolRva = 0x0749C524;
std::uint32_t pool{}; memcpy(&pool, slot, sizeof(pool));
const auto address = std::uint64_t{pool} + 20u * nameId + 4u;
if (!pool || address > 0xFFFFFFFF) return nullopt;
return readCString((const char*)(uintptr_t)address, 128);
```

### 5.1 三项

```text
pool 非零
address <= 0xFFFFFFFF（32 位）
readCString(address, 128)
```

### 5.2 **`+4` 是"跳过条目的前 4 字节"**

**⇒ 每个条目 20 字节，而名字在 `+4`。**

**所以前 4 字节是别的（可能是 flags 或计数）。**

### 5.3 **`std::uint64_t{pool}` 防溢出**

**⇒ 因为 `20 * nameId` 可能让 `uint32` 溢出。**

**⇒ 用 `uint64` 计算再检查 `> 0xFFFFFFFF`** ✓

**这是一个正确的溢出防御。**

### 5.4 那句"这不是附件/配置串命名空间"

**⇒ 以免有人把它当成 `internedAttachmentName`（§251）。**

**§251 的 `InternedStringTableRva` 与这里的 `NotifyStringPoolRva` 是两个不同的池。**

## 六、`resolveWeaponConfigStringIndex`：**165–300 ms 的单次扫描**（本组第三重要）

### 6.1 那段中文注释的完整记录

```cpp
// ★★★ 2026-10-14 修复（甲方「进图到创建人机完毕这段卡」的**真因**）——
//   原来**每次调用都线性扫 1700 条配置串**（`for index = 1 .. WeaponConfigStringCount`，
//   每次 `readCString(..., 128)` + 比较），一次未命中的名字要交两遍（配置串表 + 注册表回退）
//   ⇒ 实机实测 **单次 165–300 ms**（`BOTTRACE|class-resolve … lookupUs=1184729 lookupCalls=4`
//   ⇒ 4 次调用 0.66–1.18 s；11 个人机 ≈ 8–13 s 的连续卡顿）。
//   改为「**扫一次建名表，之后 O(1) 查**」；表随**配置串基址指针变化**（= 新 gamestate）自动重建。
//   语义完全不变：仍然返回**第一个**字符串相等的下标，未命中仍走原注册表回退。
```

### 6.2 六个数据

```text
1700 条配置串          每次调用线性扫
165–300 ms             单次实测
lookupUs=1184729       一次调用 1.18 秒（4 次调用合计）
lookupCalls=4          4 次调用
0.66–1.18 s            4 次调用合计
11 个人机 ≈ 8–13 s      连续卡顿
```

### 6.3 完整因果链

```text
1. 每次调用线性扫 1700 条
2. 而一次未命中的名字要交【两遍】（配置串表 + 注册表回退）
3. ⇒ 单次 165–300 ms
4. ⇒ 4 次调用 0.66–1.18 s
5. ⇒ 11 个人机 ⇒ 8–13 s 的连续卡顿
6. ⇒ 甲方症状：「进图到创建人机完毕这段卡」
```

**这是一个完整的"性能缺陷 → 玩家可感症状"链** —— 而注释标明"真因"。

### 6.4 与 §259 的 `170–320 ms` 对照

```text
§259  actor 生成（模型配置串）  170–320 ms
§260  武器配置串解析           165–300 ms
```

**两个**几乎相同**的量级** —— 都是 1023~1700 次跨进程读 + 字符串比较。

**⇒ 这是"跨进程线性扫描"这个模式的固有代价。**

**⇒ 而两处的解法不同**：

```text
§259  验证过的提示缓存（按名字存索引）
§260  一次性建名表（按代际重建）
```

**§260 的解法更好** —— 因为一次扫描建表后所有名字都 O(1)。

### 6.5 名表结构

```cpp
struct WeaponNameIndex
{
    const void *generation{};
    std::unordered_map<std::string, std::uint16_t> byName;
};
static WeaponNameIndex nameIndex;
const void *const generation = nativeConfigString(WeaponConfigStringBase + 1);
if (generation && nameIndex.generation != generation)
{
    nameIndex.byName.clear();
    nameIndex.generation = generation;
    for (index = 1; index < WeaponConfigStringCount; ++index) { ... }
}
```

### 6.6 **代际 = `nativeConfigString(WeaponConfigStringBase + 1)` 的指针**

**⇒ 用"槽 1 的字符串指针"作代际标识。**

**⇒ 因为新 gamestate 会重建配置串表 ⇒ 指针会变。**

**这是一个巧妙的代际检测** —— 不需要单独的版本号。

**但有一个假设**：槽 1 的字符串在每次重建后**必然不同指针**。

**⚠ 如果两次 gamestate 的槽 1 恰好分配在同一地址（内存复用），代际检测会失效。**

**⇒ 而结果是一个陈旧的名表。**

**这是一个潜在缺陷** —— 但因为 `byName` 存的是名字→索引，而如果表内容相同则索引也相同 ⇒ 陈旧无害。

**⇒ 只有当"同地址但内容不同"时才出错。** 而在实践中不太可能。

### 6.7 三项**语义保持**

```text
1. 仍然返回【第一个】字符串相等的下标
2. 未命中仍走原注册表回退
3. 名表未覆盖（空）时保留原线性扫描作为兜底
```

### 6.8 那个"兜底"的实现

```cpp
if (!nameIndex.byName.empty())
{
    const auto found = nameIndex.byName.find(std::string(weaponName));
    if (found != nameIndex.byName.end()) return found->second;
}
// 名表未覆盖（例如名表尚未建立）时，保留原线性扫描作为兜底，行为与修复前一致。
if (nameIndex.byName.empty())
{
    for (index = 1; index < WeaponConfigStringCount; ++index) { ... }
}
```

### 6.9 **两段的条件是互补的**

```text
名表非空   ⇒ 查名表（未命中则【不】回退到线性扫描）
名表为空   ⇒ 线性扫描
```

**⇒ 所以"名表建了但没这个名"⇒ 直接往下走（注册表回退）。**

**⇒ 这是一个正确的分层** ✓

### 6.10 ⚠ **`emplace` 保留第一个**

```cpp
nameIndex.byName.emplace(*candidate, index);
```

**`unordered_map::emplace` 在键已存在时**不覆盖**。**

**⇒ 所以"第一个"语义由容器保证** ✓ 与注释的"仍然返回第一个字符串相等的下标"一致。

**这是一个精致的正确性细节** —— 如果用 `insert_or_assign` 就会返回**最后**一个。

## 七、`bindingCommitted_` 的前置

**三个函数要求 `bindingCommitted_.load(acquire)`**：

```text
resolveScriptModelAnimationTree
animationNotifyTimes
animationNotifyName
```

**而 `resolveAnimConfigStringIndex` 与 `resolveWeaponConfigStringIndex` 要求 `CCS_Initialized()`。**

**⇒ 两组不同的前置条件** —— 一组关于"绑定已提交"，一组关于"配置串已初始化"。

## 八、关键结论

1. **三个 `resolveXConfigStringIndex` 共享四项前置**（重复写三遍）。
2. **模型名 `_stricmp` 不敏感而动画名精确敏感** —— 一个有意的区分但无注释。
3. **别名 = 配置串索引 - band 基址 - 1**（减去保留槽标志）。
4. **动画树查找是一个 12 字节节点的 BST**（key/node/left/right），`depth < 64` 防环。
5. **`key > alias ? 4 : 8` 是标准 BST 方向**。
6. **"二义即失败"** —— 共享 alias 不是挑任意树的许可。
7. **`wireId` 是 1..31（5 位）** —— 32 个动画树槽。
8. **XAnimParts 五个偏移：`+0` 名、`+14` frames、`+27` count、`+40` rate、`+80` markers**。
9. **marker 条目 8 字节，`+0` id、`+4` 归一化 time**。
10. **`seconds > FLT_MAX` 是一个无效检查**（`seconds` 是 `double`）。
11. **`normalized > 1` 被拒绝** —— 可能过严。
12. **`pool + 20*id + 4`** 用 `uint64` 算防溢出。
13. **"这不是附件/配置串命名空间"** —— 与 §251 的 `InternedStringTable` 不同。
14. **1700 次跨进程读 + 比较 = 165–300 ms/次**；4 次 = 0.66–1.18 s；11 个人机 = 8–13 s。
15. **§259 与 §260 的两个 165–320 ms 是同一个模式**（跨进程线性扫描）。
16. **代际检测用"槽 1 的字符串指针"** —— 巧妙但有同地址复用的理论风险。
17. **`unordered_map::emplace` 保留第一个** —— 与"返回第一个"的语义一致。

## 九、未闭合点

- `nativeConfigString(WeaponConfigStringBase + 1)` 在两次重建后是否必然不同地址。
- `seconds > FLT_MAX` 的检查意图。
- `normalized > 1` 是否真的有动画违反。
- 三个 band 函数（model/anim/effect）与三个 `resolveXConfigStringIndex` 的对应关系。
- `EngineBindings.cpp` 16650 行之后未读取。
