# 259 · `5236` 字节的模块化记录、`170-320 ms` 的开局停顿、`_stricmp` 的两个已实测行为

## 一、范围

本报告学习 `EngineBindings.cpp` 16250–16450 行。

## 二、`modelConfigStringBand`：**1024 个配置串一次扫**

```cpp
// MAP LOAD ONLY. One pass over up to 1024 configstrings; section 119q is
// the record of what this kind of scan does when run per frame.
std::vector<std::pair<uint16, std::string>> band;
if (!configStringGet_ || !CCS_Initialized()) return band;
for (uint16 index = 1; index < ModelConfigStringCount; ++index)
{
    const auto candidate = readCString(nativeConfigString(ModelConfigStringBase + index), 128);
    if (candidate && !candidate->empty()) band.emplace_back(index, *candidate);
}
```

### 2.1 两个常量

```text
ModelConfigStringCount   ~1024（注释说"up to 1024"）
ModelConfigStringBase    ?
```

### 2.2 那句"§119q 是这类扫描每帧跑时会怎么样的记录"

**⇒ 一次实测记录** —— 而 §259 后面给出了具体数字（170–320 ms）。

### 2.3 索引从 **1** 开始

**⇒ 索引 0 是保留的** ✓ 与 §236 的 `for (index = 1; ...)` 一致。

## 三、**`5236` 字节的模块化记录与 170–320 ms 停顿**（本组最重要的一段）

### 3.1 `weaponDisplayBodyCenter` 的两条路径

```cpp
const auto name = readWeaponDefinitionName(weaponAssetIndex);
if (!name || name->empty()) return nullopt;
const std::uint8_t *model{};
if (name->front() == '*') {
    // 【模块化路径】
} else {
    // 【普通路径】
}
```

**⇒ 名字的首字符 `'*'` 分开两条路径** ✓

**与 §245 里"`'*'` 名的模块化分支"一致。**

### 3.2 模块化路径的四个常量

```cpp
constexpr std::uintptr_t RecordCountRva = 0x1588634;
constexpr std::uintptr_t RecordsRva     = 0x15E30F0;
constexpr std::size_t    Stride         = 5236;
```

### 3.3 **`0x1588634` 与 §245 里 `registryWord(0x1588634u)`**

**§245 里**：

```cpp
registryWord(0x1588634u),     // "counter"
```

**⇒ 同一个 RVA 在 §245 被称作 "counter"，而这里被称作 "RecordCount"。**

**⇒ 所以那个全局既是"计数器"也是"记录数"** —— 因为每次注册都会加一而每条记录都占一个槽。

**这是一处交叉确认** ✓

### 3.4 记录的布局（从代码推出）

```text
+0      名字（readCString(record, 128)）
+146    world-model count（uint8，`record[146]`）
+152    parent 索引（uint32，当 +146 == 0 时用）
+4412   一个 uint16，必须 == 0
+4444   model 指针（void*）
```

### 3.5 **`+146` 是 `record[146]`（单字节）**

```cpp
if (!record[146]) {
    const auto parent = *(const uint32*)(record + 152);
    if (!parent || parent >= *count) return nullopt;
    record = module_ + RecordsRva + Stride * parent;
    ...
}
if (!record[146] || record[146] > 32 ||
    *(const uint16*)(record + 4412) != 0) return nullopt;
```

### 3.6 三层的"父记录"跳转

```text
1. 如果 +146 为 0（这个记录没有自己的 world 模型）
2. ⇒ 读 +152 的 parent 索引（必须 1..count-1）
3. ⇒ 跳到 parent 记录
4. ⇒ parent 的 +146 必须 1..32 且 +4412 必须 0
```

**"`+146` 是 world-model count 而 `+152` 是 parent 索引"** —— 注释说"world-model count+146 和指针+4444"。

**⇒ 所以 `+146` 为 0 意味着"这个模块化变体没有自己的 world 模型，用父的"。**

**这是一个"变体继承"的机制** ✓

### 3.7 `+4412` 必须为 0 是**根标签检查**

```cpp
// Root tags must be zero: child attachment bounds use a different coordinate frame.
```

**"根标签必须为零：子附件的包围盒用不同的坐标框架。"**

**⇒ 所以这个检查保证"我们拿到的是根模型的包围盒而不是附件的"。**

**⇒ 一个非零值意味着坐标框架不同 ⇒ 包围盒会错。**

**这是一个语义正确的检查** ✓

### 3.8 普通路径

```cpp
const auto *slot = module_ + WeaponDefinitionsRva + sizeof(void*) * weaponAssetIndex;
const auto *definition = *(const uint8*const*)slot;
if (!readableSpan(definition, 28)) return nullopt;
model = *(const uint8*const*)(definition + 24);
```

```text
+24    world model 指针（普通武器）
```

**⇒ 与 §243 里 `definition[+12]` 是 host 名不同** —— `+24` 是模型指针。

**`readableSpan(definition, 28)`** ⇒ **需要 28 字节** —— 所以 `+24` 的指针在 `24..27` ✓

### 3.9 两条路径汇合后的**三项验证**

```cpp
if (!readableSpan(model, 0x158)) return nullopt;
const auto modelName = readCString(*(const char*const*)model, 128);
if (!modelName || *modelName == "tag_origin" ||
    findXAsset(AssetTypeXModel, modelName->c_str(), false).data != model)
    return nullopt;
```

### 3.10 三项

```text
1. model 可读 0x158 字节
2. 名字可读且【不是 "tag_origin"】
3. 【findXAsset 得到的指针必须等于 model】
```

### 3.11 **`tag_origin` 的拒绝**

**§255 里 `tag_` 是"差一个槽"缺陷的指纹。**

**而这里 `tag_origin` 是**具体的占位模型**（§249 里"CheyTac clone has tag_origin in both element-zero fields"）。**

**⇒ 所以 `tag_origin` = "这个模型槽没有被替换"** ⇒ 拒绝 ✓

### 3.12 第三项是**资产自证**（与 §257/§258 同族）

**"`findXAsset` 返回的指针必须等于我们手上这个"** —— 一个强的一致性检查。

### 3.13 包围盒的两个判据

```cpp
TraceBounds bounds{};
memcpy(&bounds, model + 0x140, sizeof(bounds));
const auto bounded = [](float x) { return std::isfinite(x) && std::abs(x) < 512.0f; };
if (!all_of(bounds.midpoint, bounded) ||
    !all_of(bounds.halfSize, [&](float x) { return bounded(x) && x >= 0; }) ||
    bounds.halfSize[0] <= 0 || bounds.halfSize[1] <= 0) return nullopt;
return bounds.midpoint;
```

### 3.14 四项

```text
midpoint  三个都有限且 |x| < 512
halfSize  三个都有限且 |x| < 512 且 >= 0
halfSize[0] > 0
halfSize[1] > 0
```

**⚠ `halfSize[2]` 只要求 `>= 0`** —— 所以 z 方向的半尺寸可以是 0。

**⇒ 这是一个"扁平的"包围盒** —— 而 x/y 必须 > 0。

**这可能是一个有意的放宽**（因为"body center"只需要 x/y 有尺寸）。

### 3.15 `512` 的界

**⇒ 一个 1024×1024 单位的包围盒是上限。**

**而 COD 的地图通常只有几千单位** ⇒ 512 是一个合理的上界。

### 3.16 那句 `170-320 ms`

```cpp
// Spawning one actor used to walk all 1023 model configstrings for the
// body and then do the same walk for its head.  The measured Factory
// opening burst consequently stopped the authoritative frame for
// 170-320 ms on every successful spawn.
```

### 3.17 四层

```text
1. 生成一个 actor 走全部 1023 个模型配置串（找身体）
2. 然后为它的【头】再走一遍
3. ⇒ 实测的 Factory 开场爆发把权威帧停了 170–320 ms
4. ⇒ 而这是【每一次成功生成】都发生
```

**"Factory opening burst"** —— §144 学过的 `zm_factory` 的开场。

### 3.18 而解法是**验证过的提示缓存**

```cpp
// This is deliberately a validated hint rather than a process-lifetime
// asset-index cache. The client and dedicated rebuild this namespace at
// every map load; before reusing an index, read that slot from the CURRENT
// configstring table and require its text to remain byte-for-byte equal.
// A new map therefore turns a stale hint into one ordinary full scan, then
// refreshes it. This keeps the map-generation safety of the original
// resolver while reducing steady-state actor spawns from 2046 native
// configstring reads to two.
```

### 3.19 五层

```text
1. 不是"进程生命周期的资产索引缓存"而是【验证过的提示】
2. 每次地图加载客户端与专用服都重建这个命名空间
3. ⇒ 重用索引前从【当前】配置串表读那个槽，要求文本【逐字节相等】
4. ⇒ 新地图把陈旧提示变成【一次普通全扫】然后刷新
5. ⇒ 稳定状态下 actor 生成从 2046 次原生配置串读降到【两次】
```

### 3.20 **`2046` 这个数**

```text
1023（身体）× 2（客户端与专用服？）+ ... = 2046
```

**或者**：

```text
1023 × 2 = 2046   ⇒ 身体一次 + 头一次
```

**✓ 完全吻合 "walk all 1023 for the body and then do the same walk for its head"。**

**⇒ 2046 = 1023 + 1023。**

### 3.21 而"降两次"

```text
1 次  提示命中时的验证读
1 次  头（如果头是不同的模型，可能需要第二次）
```

**"两次"** —— 而前面说"2046 次原生配置串读" ⇒ 减少 1023 倍。

### 3.22 而**DB 查找也省了**

```cpp
// Consult it before DB_FindXAssetHeader too: byte-for-byte equality in the
// current model configstring band already proves the model is published
// for this map, and the native asset lookup was still being paid twice for
// every otherwise-cached zombie spawn.
```

**⇒ 提示命中时就**跳过** `findXAsset`** —— 因为"当前配置串带里的逐字节相等已经证明模型已为这张地图发布"。

**这是一个"用更便宜的证明替代更贵的查询"** ✓

## 四、`_stricmp` 与 **Wetwork 的大小写实测**（本组第二重要）

```cpp
// Fastfile asset names are case-insensitive. Add-on map entities do
// not always preserve the configstring band's spelling (Wetwork has
// `cs_cargoship_door_PUll_EDGE` while its native band publishes
// `cs_cargoship_door_pull_edge`). Treating those as different models
// allocated a second configstring index and made the server's static
// entity delta disagree with the client's const-baseline model.
```

### 4.1 一个实测对

```text
Wetwork 的地图实体  cs_cargoship_door_PUll_EDGE
原生配置串带        cs_cargoship_door_pull_edge
```

**⇒ 大小写完全不同（`PUll_EDGE` vs `pull_edge`）。**

### 4.2 三层后果

```text
1. 把两者当成不同模型
2. ⇒ 分配了【第二个】配置串索引
3. ⇒ 服务器的静态实体 delta 与客户端的 const-baseline 模型【不一致】
```

**"const-baseline"** —— 与 §147 学过的 `cl.entityBaselines` / `<map>_const.ff` 相关 ✓

**⇒ 一个大小写差异导致服务端与客户端**用了不同的模型索引**。**

**这是一个非常具体的、可复现的 bug 机制。**

### 4.3 而解法是 `_stricmp`

```cpp
_stricmp(candidate->c_str(), requestedModelName.c_str()) == 0
```

**用两次**：提示验证、全扫匹配。

### 4.4 而 §257 的 `readMapEntityString` 用的是**精确比较**

**⇒ 两处的比较语义不同** —— 但那是对的，因为一个是模型名一个是资产路径。

## 五、提示缓存的**两个 `scoped_lock`**

```cpp
static std::mutex modelHintMutex;
static std::unordered_map<std::string, uint16> modelHints;
const std::string requestedModelName(modelName);
const auto &key = requestedModelName;
{
    std::scoped_lock lock(modelHintMutex);                    // ← 【读锁范围】
    if (const auto hint = modelHints.find(key); hint != modelHints.end())
    {
        const auto candidate = readCString(nativeConfigString(ModelConfigStringBase + hint->second), 128);
        if (candidate && _stricmp(candidate->c_str(), requestedModelName.c_str()) == 0)
            return hint->second;
        modelHints.erase(hint);                               // ← 陈旧即删
    }
}
// ... findXAsset ... 全扫 ...
{
    std::scoped_lock lock(modelHintMutex);                    // ← 【写锁】
    modelHints.insert_or_assign(key, index);
    return index;
}
```

### 5.1 三项

```text
1. 命中且验证通过 ⇒ 返回
2. 命中但验证失败 ⇒ 【删除】
3. 未命中或已删 ⇒ 全扫后【写入】
```

### 5.2 **"陈旧即删"** 而不是"留着等下次"

**⇒ 所以一个失效的提示只影响**一次**。**

### 5.3 ⚠ **读锁范围里做了 `readCString`**

**⇒ 持锁期间做了一次跨进程内存读。**

**这是一个"锁的粒度偏大"** —— 但只在 map load 与 spawn 时发生，不是每帧。

### 5.4 `key` 是 `const std::string&` 指向 `requestedModelName`

**⇒ 所以 `modelHints` 用 `std::string` 作键而 `requestedModelName` 是局部的** —— `insert_or_assign` 会**拷贝**它 ✓

### 5.5 **`const auto &key = requestedModelName;` 是多余的一层**

**⇒ 只是一个别名** —— 没有额外开销但也没有作用。

## 六、`animConfigStringBand` 与 `SV_AnimationAliasFromConfigString`

```cpp
for (uint16 index = 1; index < AnimConfigStringCount; ++index)
{
    const auto candidate = readCString(nativeConfigString(AnimConfigStringBase + index), 128);
    if (candidate && !candidate->empty())
        band.emplace_back(*SV_AnimationAliasFromConfigString(AnimConfigStringBase + index), *candidate);
}
```

### 6.1 **返回的索引不是 `index`**

```cpp
*SV_AnimationAliasFromConfigString(AnimConfigStringBase + index)
```

**⇒ 配置串索引先被**转换成别名索引**。**

**⇒ 所以"配置串索引"与"动画别名索引"是两个空间。**

### 6.2 而 `SV_AnimationAliasFromConfigString` 返回 `optional`

**`*` 解引用 ⇒ 如果返回 nullopt 会 UB。**

**⚠ 这是一个**未检查的解引用**。**

**⇒ 除非这个函数对 `AnimConfigStringBase + index` 恒定有值。**

**这是一处潜在缺陷** —— 值得指出。

### 6.3 那段"用这个引擎自己的字符串"

```cpp
// It exists because per-state animation selection has to be built from THIS
// engine's own strings. `codol-ship-the-games-own-strings`: the names are in
// the fastfiles, and the band is where the engine puts the ones it actually
// holds. Guessing at `ai_zombie_*` spellings and hoping resolve() catches the
// misses is how invented values get on the wire.
```

### 6.4 三层

```text
1. 按状态的动画选择必须从【这个引擎自己的字符串】建立
2. 名字在 fastfile 里，而 band 是引擎放它实际持有的那些的地方
3. ⇒ 猜 `ai_zombie_*` 的拼写并指望 resolve() 捕获失败的，是【发明值上线】的路
```

**"invented values get on the wire"** —— 与本项目"不猜偏移"（§252）同族。

## 七、`effectConfigStringBand` 的**双向转换**

```cpp
for (uint16 eventParameter = 1; eventParameter < EffectConfigStringCount; ++eventParameter)
{
    const auto configStringIndex = SV_EffectEventParameterToConfigString(eventParameter);
    if (!configStringIndex) continue;
    const auto candidate = readCString(nativeConfigString(*configStringIndex), 128);
    if (candidate && !candidate->empty()) band.emplace_back(eventParameter, *candidate);
}
```

### 7.1 **与 anim 的方向相反**

```text
anim band    遍历【配置串索引】→ 转成【别名索引】
effect band  遍历【事件参数】  → 转成【配置串索引】
```

### 7.2 而 `emplace_back` 的 key 是 `eventParameter` 而不是 `configStringIndex`

**⇒ 所以 effect band 的键是**事件参数号**。**

**这与 `modelConfigStringBand` 的键（配置串索引）不同。**

**⇒ 三个 band 的键空间各不相同**：

```text
model band    配置串索引
anim band     别名索引
effect band   事件参数号
```

**这是一处重要的语义区分** —— 三个函数签名相同（`vector<pair<uint16, string>>`）但键空间不同。

### 7.3 那段

```cpp
// resolveEffectEventParameter walks this band to turn a
// NAME into an index; this is the other direction, so a map load can log
// the names this engine actually holds instead of anyone inventing one.
```

**"这个函数是另一个方向"** —— 所以 `resolveEffectEventParameter` 是"名 → 索引"而这里是"遍历并列出所有"。

## 八、`AssetTypeXAnim = 2` 的来源

```cpp
// AssetTypeXAnim is 2 in CODOL's own XAssetType enum, read out of out.exe's
// asset-type name pointer array at 0xA5C808 (20-zm-actor-lifecycle.md 12.57).
// The three ids this file already uses -- xmodel 4, fx 30, fx_map 20 -- come
// from the same table, which is what makes 2 safe to add.
```

### 8.1 四个类型号（同一张表）

```text
xmodel    4
fx        30
fx_map    20
xanim     2
```

**⇒ `0xA5C808` 是资产类型名的指针数组。**

### 8.2 而 §143/§257 里的类型号

```text
GfxImage        10
Material        5
XModel          4      ✓
XModelSurfs     3
XAnimParts      2      ✓
Weapon          28
StringTable     37
```

**⇒ `XModelSurfs = 3` 与 `XAnimParts = 2` 与这里的 "xanim 2" 一致** ✓

**⇒ 而 `fx 30`/`fx_map 20` 是两个新类型号。**

### 8.3 那句"同表 ⇒ 2 可以安全地加"

**⇒ 因为三个已知类型来自同一张表，所以第四个同源。**

**这是一个"来源一致性"的论证** —— 比"它应该是对的"强。

## 九、关键结论

1. **`1023 × 2 = 2046`** —— 身体与头各扫一遍的全部配置串读。
2. **一个 actor 生成停权威帧 170–320 ms**（Factory 开场实测）。
3. **`0x1588634` 既是"计数器"（§245）也是"记录数"（§259）** —— 一次交叉确认。
4. **模块化记录 `5236` 字节，布局 `+0` 名、`+146` world 模型数、`+152` parent、`+4412` 根标签、`+4444` 模型指针**。
5. **`+146 == 0` ⇒ 跳到父记录**（变体继承）。
6. **`+4412` 必须为 0** —— 根标签，因为子附件包围盒用不同坐标框架。
7. **普通武器 `+24` 是 world 模型指针**。
8. **`tag_origin` 的拒绝** —— 它是"模型槽未替换"的指纹。
9. **`findXAsset(...).data != model` ⇒ 拒绝** —— 资产自证。
10. **包围盒 `|x| < 512`、`halfSize[0]/[1] > 0` 但 `halfSize[2] >= 0`**。
11. **验证过的提示缓存** —— 逐字节相等才复用，新地图把陈旧提示变成一次全扫。
12. **提示命中时跳过 `findXAsset`** —— 更便宜的证明替代更贵的查询。
13. **Wetwork 的 `cs_cargoship_door_PUll_EDGE` vs `cs_cargoship_door_pull_edge`** —— 大小写差异导致第二个配置串索引、服务端与客户端模型不一致。
14. **`SV_AnimationAliasFromConfigString` 的返回值被无条件解引用** —— 潜在 UB。
15. **三个 band 的键空间不同**（配置串索引 / 别名索引 / 事件参数号）。
16. **`xmodel 4 / fx 30 / fx_map 20 / xanim 2` 来自同一张 `0xA5C808` 表**。

## 十、未闭合点

- `SV_AnimationAliasFromConfigString` 是否恒有值。
- `ModelConfigStringCount`（1024 还是 1023+1）与 `AnimConfigStringCount`/`EffectConfigStringCount` 的具体值。
- `5236` 字节记录的完整布局（只有五个偏移被用到）。
- `EngineBindings.cpp` 16450 行之后未读取。
