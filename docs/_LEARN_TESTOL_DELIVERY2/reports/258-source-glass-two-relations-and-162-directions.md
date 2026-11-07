# 258 · 触发体的三层嵌套、玻璃的两条关系（27/27 实测）、`162` 个方向字节

## 一、范围

本报告学习 `EngineBindings.cpp` 16050–16250 行。

## 二、触发体的**三层嵌套**

```cpp
const auto &model = mapEnts->models[triggerModel];
if ((int32)model.firstHull + model.hullCount > mapEnts->hullCount) return nullopt;

for (index < model.hullCount)
{
    const auto &hull = mapEnts->hulls[model.firstHull + index];
    if ((int32)hull.firstSlab + hull.slabCount > mapEnts->slabCount) return nullopt;
    SvZmVolumeHull out{ .midpoint = hull.midpoint, .halfSize = hull.halfSize };
    for (slab < hull.slabCount)
    {
        const auto &source = mapEnts->slabs[hull.firstSlab + slab];
        out.slabs.push_back({ .direction, .midPoint, .halfSize });
    }
    hulls.push_back(std::move(out));
}
```

### 2.1 三层

```text
models[triggerModel]          → (firstHull, hullCount)
hulls[firstHull + i]          → (firstSlab, slabCount, midpoint, halfSize)
slabs[firstSlab + j]          → (direction, midPoint, halfSize)
```

### 2.2 **两处"区间包含"检查**

```cpp
model.firstHull + model.hullCount > mapEnts->hullCount         ⇒ 拒绝
hull.firstSlab + hull.slabCount > mapEnts->slabCount           ⇒ 拒绝
```

**都是 `start + count > total` 的形式** —— 与 §238 里"`base + count*stride <= weaponClassStride`"同族。

### 2.3 **`static_cast<std::int32_t>(hull.firstSlab) + hull.slabCount`**

**注意 `firstSlab` 被转成 `int32` 而 `slabCount` 没有。**

**⇒ 所以 `firstSlab` 可能是 `uint16` 而 `slabCount` 也是 `uint16` ⇒ 两个 uint16 相加会溢出。**

**⇒ 但 `firstSlab` 转 `int32` 后再加，结果提升为 `int32` ⇒ 不溢出** ✓

**这是一个有意的防溢出转换。**

**而 `model.firstHull` 同样被转** ✓

### 2.4 `for (uint16 index = 0; index < model.hullCount; ++index)`

**`hullCount` 是 `uint16`** ⇒ **最多 65535 个 hull。**

**而如果 `hullCount == 65535`，循环会正确地跑 65535 次**（因为 `index < 65535` 在上界内）。

**⚠ 但如果 `hullCount == 65535` 而 `index` 也是 `uint16`，`++index` 到 65535 时 `index < 65535` 为假 ⇒ 正常结束** ✓

**边界正确。**

### 2.5 `out.slabs.reserve(hull.slabCount)` 然后 `push_back`

**没有 `resize`** —— 所以是追加式。

**而 `SvZmVolumeHull out{...}` 是聚合初始化后 `out.slabs` 为空 ⇒ `reserve` 有效。**

## 三、`resolveGlassMapMetadata`：**8% 与 14% 的余量**（本组最重要的一段）

### 3.1 那条"每个地图一行"的日志

```cpp
// Kept after section 93 settled both bounds, because it is the line that says WHICH
// number refused a map, and the two live maxima have only 7% and 14% of slack. It costs
// one line per map load and it is silent on a map with no glass.
char glassLine[192]{};
snprintf(glassLine, sizeof(glassLine),
    "fxglass header map=%.32s definitions=%u pieceLimit=%u "
    "pieceWords=%u initialPieces=%u cells=%u active=%u",
    mapName, definitionCount, pieceLimit, pieceWordCount, initialPieceCount, cellCount, activePieceCount);
```

### 3.2 **六个量**

```text
definitions      glass.definitionCount
pieceLimit       glass.pieceLimit
pieceWords       glass.pieceWordCount
initialPieces    glass.initialPieceCount
cells            glass.cellCount
active           glass.activePieceCount
```

### 3.3 那句"两个实测最大值只有 7% 和 14% 余量"

**⇒ 所以这个日志**必须保留** —— 因为上限很紧，一次实测就能看到接近上限。**

**"它对没有玻璃的地图保持沉默"** —— 因为 `definitionCount == 0` 时各项都是 0。

**⚠ 但日志本身**没有** `definitionCount` 为零时的守卫** —— 所以它**总是**打印。

**"silent on a map with no glass"** 指的可能不是日志静默而是"没有后续处理"。

**这处措辞与实现不完全一致。**

### 3.4 四条判据（本组核心）

```cpp
if (glass.definitionCount > MaximumFxGlassDefinitionCount ||
    glass.pieceLimit > MaximumFxGlassPieceLimit ||
    glass.initialPieceCount > SvGlassPieceCount ||
    glass.initialPieceCount > glass.pieceLimit ||
    // The two relations section 93 measured on 27 of 27 glassed maps.
    (glass.pieceLimit &&
        (glass.pieceWordCount != ((glass.pieceLimit + 31) >> 5) ||
         glass.pieceLimit != glass.initialPieceCount + SvGlassPieceCount)) ||
    (glass.initialPieceCount &&
        (!glass.definitionCount ||
         !readableSpan(glass.initialPieceStates,
             initialPieceCount * sizeof(*initialPieceStates)))))
    return nullopt;
```

### 3.5 六项

```text
① definitionCount <= MaximumFxGlassDefinitionCount
② pieceLimit <= MaximumFxGlassPieceLimit
③ initialPieceCount <= SvGlassPieceCount
④ initialPieceCount <= pieceLimit
⑤ pieceLimit 非零时：
     pieceWordCount == (pieceLimit + 31) / 32      ← 【位图字数】
     pieceLimit == initialPieceCount + SvGlassPieceCount  ← 【§93 的关系】
⑥ initialPieceCount 非零时：
     definitionCount 非零
     initialPieceStates 可读 initialPieceCount * sizeof(一个)

```

### 3.6 **第 ⑤ 项的两个关系是 27/27 实测**

```cpp
// The two relations section 93 measured on 27 of 27 glassed maps. A map that
// breaks either was not built by this game's compiler, and reading its piece
// array on the strength of a header that disagrees with itself is the thing
// these bounds exist to prevent.
```

**两个关系**：

```text
pieceWordCount == (pieceLimit + 31) >> 5          位图字数 = ceil(pieceLimit / 32)
pieceLimit     == initialPieceCount + SvGlassPieceCount
```

### 3.7 而第二个关系是**关键的**

**`SvGlassPieceCount` 是"运行时新增的玻璃块数"。**

**⇒ `pieceLimit = initialPieceCount + SvGlassPieceCount`** 意味着**"上限 = 初始 + 可破碎新增"。**

**记忆里 §192–213 学过 `glass limit derivation (pieceLimit == initialPieceCount + 1024, 27/27 maps)`** ✓

**⇒ `SvGlassPieceCount = 1024`。**

**这是一处交叉确认** —— 而 §258 的代码没有给出 1024 这个数（它用常量名）。

### 3.8 第 ⑤ 项的**双重结构**

```cpp
(glass.pieceLimit &&
    (A || B))
```

**⇒ 只有当 `pieceLimit != 0` 时才检查 A 与 B。**

**⇒ 一个 `pieceLimit == 0` 的地图（没有玻璃）跳过这两项 ✓**

### 3.9 第 ⑥ 项的**双重结构**

```cpp
(glass.initialPieceCount &&
    (!definitionCount || !readableSpan(...)))
```

**⇒ 只有当 `initialPieceCount != 0` 时才检查。**

### 3.10 六个条件的**四个"非零时才检查"**

```text
⑤ pieceLimit != 0
⑥ initialPieceCount != 0
```

**⇒ 两个都为 0 时只查 ①②③④** —— 而 ③④ 在 0 时也平凡满足。

**⇒ 一个完全空的玻璃系统**总是通过** ✓

## 四、**每条玻璃块的九项校验**

```cpp
for (index < glass.initialPieceCount)
{
    const auto &piece = glass.initialPieceStates[index];
    const auto finite = [](const auto &values) {
        return all_of(values, [](float v) { return std::isfinite(v); });
    };
    if (!finite(piece.quaternion) || !finite(piece.origin) ||
        !finite(piece.textureCoordinateOrigin) ||
        !std::isfinite(piece.radius) || piece.radius < 0.0f ||
        !std::isfinite(piece.doubledArea) || piece.doubledArea < 0.0f ||
        piece.definitionIndex >= glass.definitionCount)
        return nullopt;
    result.initialPieces.push_back({ ... 九个字段 ... });
}
```

### 4.1 三组 `finite` + 两个 `>= 0` + 一个 `definitionIndex`

```text
quaternion                  4 个 float 必须有限
origin                      3 个 float 必须有限
textureCoordinateOrigin     2 个 float 必须有限
radius                      有限且 >= 0
doubledArea                 有限且 >= 0
definitionIndex             < definitionCount
```

### 4.2 **`radius` 与 `doubledArea` 允许 0**

**⇒ 一个退化的玻璃块（零半径）是合法的。**

### 4.3 九个字段

```cpp
.quaternion
.origin
.radius
.textureCoordinateOrigin
.supportMask
.doubledArea
.definitionIndex
.vertexCount
.fanDataCount
```

**九项** —— 而其中五项被校验（quaternion/origin/textureCoord/radius/doubledArea/definitionIndex = 六项）。

**`supportMask`、`vertexCount`、`fanDataCount` 未校验** —— 所以它们可以是任何值。

**⚠ `vertexCount` 与 `fanDataCount` 是**计数** —— 而它们未被校验意味着下游可能越界。**

**这是一个潜在缺陷** —— 除非下游有检查。

## 五、`assetPaths` 的**两段（campaign 借用）**

```cpp
std::vector<std::string> assetPaths{ "maps/mp/" + map + ".d3dbsp" };
// The campaign zone is an add-on layered over the stock multiplayer
// cargo ship. Its own fastfile has no FxWorld, just as it has no
// clipmap, so resolve the same borrowed mp_cargoship world used by
// initializeLevelWorld.
if (const auto at = map.rfind("mp_"); at != std::string::npos && at != 0)
    assetPaths.push_back("maps/mp/" + map.substr(at) + ".d3dbsp");
```

### 5.1 `rfind("mp_")` 的**两个条件**

```text
at != npos   找到 "mp_"
at != 0      不在开头
```

### 5.2 那个子串剥离

**`map.substr(at)`** —— 从 `"mp_"` 开始的部分。

**⇒ 所以 `"coop_training_mp_cargoship"` 会变成 `"mp_cargoship"`。**

**⇒ 然后查 `"maps/mp/mp_cargoship.d3dbsp"`** ✓

**这与 §257 的 "coop_training_mp_cargoship" 例子一致** —— 而注释明确说了"borrowed mp_cargoship world"。

### 5.3 `at != 0` 的理由

**如果 map 就是 `"mp_xxx"`，`rfind` 返回 0 ⇒ 第二个候选与第一个相同 ⇒ 跳过。**

**⇒ 避免重复查询** ✓

### 5.4 而 §257 的 `readMapEntityString` **没有**这个借用

**⇒ 两处的兼容策略不同**：

```text
readMapEntityString      两种命名（.d3dbsp / .mapents）
resolveGlassMapMetadata  两段（原名 / mp_ 之后的部分）
```

**§257 的注释说"coop 地图没有 .d3dbsp"** —— 而这里说"campaign zone 没有 FxWorld"。

**⇒ 两个不同的缺失，两种不同的借用。**

## 六、`dbIsXAssetDefault_` 的**预先拒绝**

```cpp
for (const auto &candidate : assetPaths)
{
    if (dbIsXAssetDefault_(AssetTypeFxMap, candidate.c_str())) continue;
    const auto header = findXAsset(AssetTypeFxMap, candidate.c_str(), false);
    ...
}
```

### 6.1 与 §235 的 `findXAsset` 的对照

**§235**："`allowDefault=false only suppresses the default on the MISS path`"

**⇒ 所以 `findXAsset(..., false)` **可能**仍然返回默认项**（如果默认项存在）。

**⇒ 这里额外的 `dbIsXAssetDefault_` 是**第二道**检查。**

**这是一个正确的双重防御** —— 而 §235 的注释也说了这一点。

### 6.2 三项验证

```cpp
if (!readableSpan(found, sizeof(*found))) continue;
const auto assetName = readCString(found->name, 256);
if (!assetName || *assetName != candidate) continue;
```

```text
1. 头可读
2. 名字可读
3. 【名字等于我们查的名字】
```

**第三项与 §257 的 `*assetName != assetPath` 是同一手法** ✓

## 七、`directionToByte`：**162 个方向**（本组第二重要）

```cpp
constexpr std::size_t DirectionCount = 162;
const auto *const directions = (const std::array<float,3>*)(module_ + ByteDirectionsRva);
float bestDot{};
uint8 best{};
for (index < 162)
{
    const auto &candidate = directions[index];
    if (!all_of(candidate, isfinite)) return nullopt;
    const auto dot = direction[0]*candidate[0] + direction[1]*candidate[1] + direction[2]*candidate[2];
    if (!isfinite(dot)) return nullopt;
    if (dot > bestDot) { bestDot = dot; best = (uint8)index; }
}
return best;
```

### 7.1 **162 个量化方向**

**而 `uint8` 只能表示 256 个值** ⇒ **162 是一个子集。**

### 7.2 `bestDot` 初值是 **0**

```cpp
float bestDot{};
```

**⇒ 只有 `dot > 0` 的候选才会更新 `best`。**

**⚠ 如果所有候选的 `dot <= 0`（方向与所有量化方向都相反），`best` 保持 0。**

**⇒ 返回 `0` 而不是 nullopt** —— **所以"没有任何正点积"会静默返回方向 0。**

**这是一个潜在问题** —— 但 `162` 个方向覆盖了球面的大部分，所以任何方向的**最大点积**都应该是正的。

**⇒ 除非方向是 NaN（已被 `isfinite` 拒绝）或零向量。**

**⚠ 零向量：`dot = 0` 对所有候选 ⇒ `best = 0`** —— **所以零向量静默返回方向 0。**

**这是一个值得指出的边界。**

### 7.3 `Directions` 的数组是 `std::array<float,3>` 的数组

**⇒ `module_ + ByteDirectionsRva + index * 12`。**

### 7.4 而每个候选也被 `isfinite` 检查

**⇒ 如果**任何一个**候选是非有限的，整个函数返回 nullopt。**

**⇒ 这是一个"全表必须健康"的要求** —— 而不仅仅是"最佳候选健康"。

**这与 §249 的 `closedAnimations.size() == animations.size()`、§254 的 `additions.empty()` 同族**（"恰好全部"）。

## 八、`valid()` 的前置

```cpp
if (!valid() || !all_of(direction, isfinite)) return nullopt;
```

**⇒ `valid()` 是 §214–222 学过的 80 项检查。**

**⇒ 所以 `directionToByte` 要求整个绑定系统健康。**

## 九、`modelConfigStringBand` 的开头

```cpp
std::vector<std::pair<std::uint16_t, std::string>> EngineBindings::modelConfigStringBand() const
```

**⇒ 返回 `(索引, 名字)` 对的向量。**

**而 §256 里 `viewmodelIndex` 的搜索用的正是 `ModelConfigStringBase + index`** —— 所以这个函数可能是那个搜索的更完整版本。

**⇒ 待读。**

## 十、关键结论

1. **触发体三层嵌套，两处"start + count > total"的区间包含检查**。
2. **`static_cast<int32>(firstHull/firstSlab)` 防 uint16 相加溢出**。
3. **玻璃日志的"7% 和 14% 余量"** ⇒ 上限很紧，日志必须保留。
4. **玻璃的两条关系在 27/27 地图上实测**：`pieceWordCount == ceil(pieceLimit/32)` 与 `pieceLimit == initialPieceCount + SvGlassPieceCount`。
5. **`SvGlassPieceCount = 1024`**（由 §192–213 的记忆交叉确认）。
6. **六个条件里两个是"非零时才检查"** ⇒ 完全空的玻璃系统总是通过。
7. **九个玻璃字段里六项被校验，`supportMask`/`vertexCount`/`fanDataCount` 未校验** —— 潜在越界源。
8. **`assetPaths` 的第二段用 `rfind("mp_") && at != 0` 借用 `mp_cargoship`** —— 与 §257 的两种命名是**两个不同的兼容策略**。
9. **`dbIsXAssetDefault_` + `findXAsset(..., false)` 是双重防御**（因为后者只在 miss 路径抑制默认）。
10. **162 个量化方向，而 `bestDot` 初值 0 ⇒ 零向量静默返回方向 0**。
11. **任何一个候选非有限 ⇒ 整个函数失败**（"全表必须健康"）。
12. **`directionToByte` 要求 `valid()` 这个 80 项检查全过**。

## 十一、未闭合点

- `vertexCount`/`fanDataCount` 未校验是否导致下游越界。
- 零向量静默返回方向 0 的后果。
- 玻璃日志"对没有玻璃的地图保持沉默"与"总是打印"的不一致。
- `EngineBindings.cpp` 16250 行之后未读取。
