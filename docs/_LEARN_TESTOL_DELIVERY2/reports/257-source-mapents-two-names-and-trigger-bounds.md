# 257 · `custom1..5` 的七个字符、`MapEnts` 的两种命名、`dmz_empty_mp` 与夹紧链

## 一、范围

本报告学习 `EngineBindings.cpp` 15850–16050 行。

## 二、`resolveSessionWeaponLoadout` 的三项前置

```cpp
if (!valid(request) || classIndex >= request.classes.size() ||
    !(request.classMask & (1u << classIndex)))
    return nullopt;
...
if (!resolveWeaponRequest(loadoutClass.weapons[0], loadout.primary) ||
    !resolveWeaponRequest(loadoutClass.weapons[1], loadout.secondary))
    return nullopt;
```

### 2.1 **主武器与副武器都必须成功**

**注意：`||` 短路 ⇒ 如果主武器失败，副武器**不会被尝试**。**

**而 §254 里 `resolveSessionEquipment` 用的是 `continue`（跳过）。**

**§252 里附件的六级跳过 ⇒ "一个陈旧 id 不丢枪"。**

**⇒ 但武器的两级是**致命**的**：

```text
主武器失败  ⇒ 整个 loadout 失败
副武器失败  ⇒ 整个 loadout 失败
```

**这与 §237 里 §252 的"①空槽合法化：`itemId == 0` 表示没有武器，返回 true + 空 selection"是**配套**的。**

**⇒ 所以副武器为空（`itemId == 0`）**不会**失败 —— 因为 `resolveWeaponRequest` 对 `itemId == 0` 返回 true。**

**而如果副武器**有 id 但解析失败** ⇒ 整个失败。**

**这是一条隐含的语义** —— 值得指出。

## 三、`custom1..5` 的**七个字符**

```cpp
if (selectedLoadout.size() != 7 ||
    !selectedLoadout.starts_with("custom") || selectedLoadout[6] < '1' ||
    selectedLoadout[6] > '5' || characterIndex >= 12)
    return nullopt;

const auto classIndex = (uint32)(selectedLoadout[6] - '1');
const auto firstSlot = characterIndex * 10 + classIndex * 2;
```

### 3.1 三项

```text
长度 == 7
前缀 "custom"
第 7 个字符 '1'..'5'
```

### 3.2 两个约束的顺序

**`size() != 7` 在 `starts_with("custom")` 之前** —— 所以一个 6 字符的 `"custom"` 会因为长度先被拒绝。

**而如果顺序相反，`starts_with` 是安全的（`string_view` 不会越界）** —— 所以顺序不影响正确性，只是早退。

### 3.3 **`characterIndex >= 12`**

**与 §255 的 `characterIndex >= 12` 是**同一个界** ✓

**而 §255 的注释说"12 是我们的界而非引擎的"。**

### 3.4 `firstSlot` 与 §256 **完全相同**

```cpp
const auto firstSlot = characterIndex * 10 + classIndex * 2;
```

**两处独立计算同一个公式** ✓ —— 而 `>= 120` 的界（§242）由 `12 * 10` 保证。

### 3.5 这条路径**只用 staged**

```cpp
if (!readStagedWeaponRequest(firstSlot, ...) || !readStagedWeaponRequest(firstSlot + 1, ...) || ...)
```

**不是 `profile || staged`** —— 只有 staged。

**⇒ 所以这是"旧路径"，而 §256 的 `captureClientLoadoutRequest` 是"新路径"（profile 优先）。**

**⇒ 两个函数并存，一个已被取代但保留。**

## 四、`readMapEntityString` 的**两种命名**（本组最重要的一段）

### 4.1 那段实测

```cpp
// A CAMPAIGN MAP NAMES ITS MapEnts ".mapents"; AN MP MAP REUSES THE BSP
// NAME. Measured by decrypting both zones:
//
//   mp_nuked                    maps/mp/mp_nuked.d3dbsp        (no .mapents)
//   coop_training_mp_cargoship  maps/mp/....mapents            (no .d3dbsp)
```

### 4.2 两个实测对

```text
mp_nuked                     maps/mp/mp_nuked.d3dbsp        【没有 .mapents】
coop_training_mp_cargoship   maps/mp/....mapents            【没有 .d3dbsp】
```

**⇒ 一个 MP 地图用 BSP 名，一个 coop 地图用 `.mapents` 名。**

### 4.3 而两个候选的**assetType 也不同**

```cpp
struct MapEntsCandidate { uint32 assetType; std::string name; };
const std::array<MapEntsCandidate, 2> candidates{
    { AssetTypeMapEnts,      "maps/mp/" + map + ".d3dbsp"  },
    { AssetTypeAddonMapEnts, "maps/mp/" + map + ".mapents" },
};
```

```text
AssetTypeMapEnts         + ".d3dbsp"      mp 地图
AssetTypeAddonMapEnts    + ".mapents"     coop 地图
```

**⇒ "Addon" 是一个不同的资产类型** —— 而不是同一个类型两个名字。

### 4.4 后果链（注释给的）

```text
// Building only the .d3dbsp form made this return nullopt on every coop
// level, which surfaced as `world spawn pending stage=map_entity_asset`,
// then no entities, then `spawn refused ... NO_SPAWN_POINT` -- a fully
// rendered map the player cannot stand in. HANDOFF section 152t.
```

**四层**：

```text
1. 只建 .d3dbsp 形式 ⇒ 每个 coop 关卡返回 nullopt
2. ⇒ `world spawn pending stage=map_entity_asset`
3. ⇒ 没有实体
4. ⇒ `spawn refused ... NO_SPAWN_POINT` ⇒ 【一个渲染完整但玩家站不进去的地图】
```

**"一个渲染完整但玩家站不进去的地图"** —— 这是一个极好的症状描述。

### 4.5 四项验证

```cpp
const auto bytes = readableBytes(found);
if (bytes && *bytes >= sizeof(*found)) { assetPath = ...; mapEnts = found; mapEntsBytes = bytes; break; }
```

**`readableBytes` 返回"这个资产有多大"** —— 而 `*bytes >= sizeof(MapEnts)` 保证头完整。

### 4.6 **`*assetName != assetPath` 的反向校验**

```cpp
const auto assetName = readCString(mapEnts->name, 256);
if (!assetName || *assetName != assetPath || !mapEnts->entityString ||
    mapEnts->numEntityChars <= 0 ||
    (size_t)mapEnts->numEntityChars > MaximumMapEntityChars)
    return nullopt;
```

### 4.7 **"资产自报的名字必须等于我们查的名字"**

**这是一个强校验** —— 如果 `findXAsset` 返回了一个不同的资产，名字不匹配就拒绝。

**与 §236/§245/§249/§252 的"双向验证"同族，但这里是**资产自证**。**

### 4.8 `numEntityChars` 的三项

```text
> 0
<= MaximumMapEntityChars
entityString 可读 numEntityChars 字节
```

### 4.9 尾部 NUL 的处理

```cpp
std::string result(mapEnts->entityString, entityChars);
while (!result.empty() && result.back() == '\0') result.pop_back();
if (result.empty() || result.find('\0') != std::string::npos) return nullopt;
```

### 4.10 两步

```text
1. 去掉【尾部】的 NUL
2. 如果还剩下【内部】NUL ⇒ 拒绝
```

**"一个内部 NUL 说明 `numEntityChars` 过大"** —— 所以拒绝。

**这与 §241 里"`record` 的 `std::copy_n` 全量" 不同 —— 那里用的是定长，这里用变长 + 净化。**

## 五、`resolveTriggerModelHulls` 的**五项界**（本组第二重要）

```cpp
// EVERY BOUND CHECKED BEFORE ANY READ. These arrays are reached through
// pointers in a foreign process image; a wrong stride still yields plausible
// floats, so refuse rather than return something shaped correctly.
constexpr std::int32_t MaximumTriggerModels = 4096;
constexpr std::int32_t MaximumTriggerHulls = 65535;
constexpr std::int32_t MaximumTriggerSlabs = 65535;
if (mapEnts->modelCount <= 0 || mapEnts->modelCount > MaximumTriggerModels ||
    mapEnts->hullCount < 0 || mapEnts->hullCount > MaximumTriggerHulls ||
    mapEnts->slabCount < 0 || mapEnts->slabCount > MaximumTriggerSlabs ||
    !mapEnts->models || !mapEnts->hulls)
    return nullopt;
if (triggerModel >= (uint32)mapEnts->modelCount) return nullopt;
if (!readableSpan(mapEnts->models, modelCount) ||
    !readableSpan(mapEnts->hulls, hullCount))
    return nullopt;
```

### 5.1 三个上界

```text
modelCount   4096
hullCount    65535   （= uint16 满值）
slabCount    65535
```

### 5.2 那句"错误的步长同样产生貌似合理的浮点"

**"一个错误的步长仍然产生貌似合理的浮点，所以拒绝而不是返回某种形状正确的东西。"**

**⇒ 这是"形状正确但内容错误"的防御** —— 与记忆里"指针 100% 吻合也骗人"（§144）同族。

### 5.3 `modelCount <= 0` 但 `hullCount/slabCount` 允许 0

```text
modelCount   必须 > 0
hullCount    >= 0（0 合法）
slabCount    >= 0（0 合法）
```

**⇒ 一个模型可以没有 hull（凸包）或 slab（板）。**

### 5.4 那个 `readableSpan(mapEnts->models, modelCount)` 的**元素尺寸**

**`readableSpan(ptr, N)` 的 N 是**字节数** —— 而这里传 `modelCount`。**

**⚠ 如果 `models` 是一个 `Model*` 数组（每项 4 字节），那应该传 `modelCount * sizeof(void*)`。**

**而这里传 `modelCount`** —— **少乘了 4 倍。**

**等等**：如果 `mapEnts->models` 是 `uint8_t*` 或 `char*`，那 `modelCount` 就是字节数。

**但 `triggerModel >= modelCount` 的检查暗示 `models` 是**索引表**（每项 1 字节 = 一个 model 索引）。

**⇒ 所以它是一种**字节数组**的模型索引表。**

**而 `hullCount` 同类** —— `readableSpan(mapEnts->hulls, hullCount)`。

**这与 slab 的"65535"上界一致**（`uint16` 索引的字节数组）。

**所以 `models` 与 `hulls` 是 `uint8`/`uint16` 索引数组** —— 而不是结构数组。

**这是一处需要交叉验证的判断** —— 但从三个常量的类型可以推出。

## 六、`readableBytes` 的语义

```cpp
const auto bytes = readableBytes(found);
if (bytes && *bytes >= sizeof(*found)) { ... }
```

### 6.1 与 `readableSpan` 的区别

```text
readableSpan(ptr, N)    这个范围内的 N 字节可读吗
readableBytes(ptr)      这个【资产】有多大
```

**⇒ 所以 `readableBytes` 走的是资产注册表（可能用 §246 的 120,000 池）。**

### 6.2 这解释了为什么需要它

**`MapEnts` 是变长的**（`entityString` 后面跟着字符）—— 所以"可读多少"必须由资产系统回答。

## 七、`AssetTypeAddonMapEnts` 与 §236 的类型枚举

**§236 说两个哨兵从 `{19, 21}` 变成 `{21, 23}`** —— 那是**配置串类型**。

**而这里的 `AssetTypeMapEnts` / `AssetTypeAddonMapEnts` 是**资产类型**（XAsset type）。

**§143 里学过 `XAsset` 类型**：`GfxImage=10`, `Material=5`, `XModel=4`, `XModelSurfs=3`, `XAnimParts=2`, `Weapon=28`, `StringTable=37`。

**⇒ `MapEnts` 与 `AddonMapEnts` 是另两个类型号。**

## 八、`resolveSessionCharacterPresentation` 的**十三项失败记录**

```cpp
characterPresentationResolveFailure_.store(InvalidRequest);
characterPresentationResolveRecordIndex_.store(0xFFFFFFFF);
characterPresentationResolveItemId_.store(0);
if (bindings) return nullopt;

// 三项输出
enum ClientCharacterPresentationResolveFailure {
    None,
    InvalidRequest,
    ItemName,
    Selection,
    BaseItemDefinition,
    CharacterDefinitionTable,
    CharacterDefinition,
    ConstantConfigStrings,
    ViewmodelConfigString,
};
```

**九个枚举值**（从代码可见）。

### 8.1 三项原子的"三字段快照"

```cpp
struct ClientCharacterPresentationResolveStatus {
    failure, recordIndex, itemId
};
```

**⇒ 三字段分开存**（不是原子结构）—— 所以读取时可能看到**混合**状态。

**⇒ 这是本文件里的一处**非原子**设计** —— 而其他地方的失败记录都是单一 enum。

### 8.2 而 `recordIndex = 0xFFFFFFFF` 表示"无"

**与 `itemId = 0` 一起表示"初始"状态。**

### 8.3 五个失败点**带 `recordIndex`**

```cpp
// 只有 ItemName 这一个设置了 recordIndex 与 itemId
characterPresentationResolveRecordIndex_.store(recordIndex);
characterPresentationResolveItemId_.store(itemId);
```

**⇒ 所以只有 `ItemName` 失败能定位到"哪个记录项"。**

**而 `BaseItemDefinition` 失败时 `recordIndex = 0`**（因为它是 `characterItemIds[0]`）。

**其它六个失败点**不设置**这两个字段** —— 所以它们保持上一次的值。**

**⚠ 这是三字段快照的一个缺陷** —— 因为 `failure` 会在开头被重置但 `recordIndex`/`itemId` 只在两处设置。

## 九、`CCS_EnsureInitialized` 的位置

```cpp
if (!CCS_EnsureInitialized())
{
    store(ConstantConfigStrings);
    return nullopt;
}
for (index = 1; index <= MaximumWeaponAssetIndex; ++index)
{
    const auto name = readCString(nativeConfigString(ModelConfigStringBase + index), 128);
    if (name && *name == GenericCharacterViewhands) { presentation.viewmodelIndex = index; break; }
}
```

### 9.1 **CCS 必须在 `nativeConfigString` 之前初始化**

**⇒ 这与 §235 里 `readConfigString` 的 `!CCS_Initialized()` 检查一致 ✓

### 9.2 而 `nativeConfigString` 是**无检查的原生访问器**

**`readCString(nativeConfigString(...), 128)`** —— 如果索引越界，`nativeConfigString` 可能返回野指针。

**而 `index <= MaximumWeaponAssetIndex`** —— **用武器索引上界去访问模型配置串！**

**⚠ 这是一处可能越界** —— 除非 `ModelConfigStringBase + MaximumWeaponAssetIndex` 恰好也在模型配置串区间内。

**`MaximumWeaponAssetIndex` 大概是 1700 左右，而模型配置串可能也有这么多项。**

**⇒ 这是一个**可疑的界**，值得记录。**

### 9.3 而线性搜索到第一个匹配

**`GenericCharacterViewhands` 是固定名** —— 所以如果多个模型共用这个名，取第一个。

## 十、`viewmodelIndex` 缺失即失败

```cpp
if (!presentation.viewmodelIndex)
{
    store(ViewmodelConfigString);
    return nullopt;
}
```

**⇒ "找不到通用 viewhands" ⇒ 整个 presentation 失败。**

**而这在 §256 里被描述为"character-specific recovery fallback"** —— 所以它是**必需的**。

## 十一、`resolveClientWeaponLoadout` 的**三层重置**

```cpp
loadoutResolveFailure_.store(ClientLoadoutResolveFailure::None);
if (size != 7 || ...) return nullopt;
```

### 11.1 **先重置再检查**

**所以一个格式错误的 loadout 名会**清除**上一次的失败记录。**

**⇒ 这可能是一个诊断缺陷**（清除了有意义的信息）。

**对比 §252 里 `resolveWeaponItem` 的 `store(None)` 在**最后**（成功时）。**

**两处的位置不同。**

## 十二、关键结论

1. **武器两级致命、附件六级跳过** —— 因为空槽（`itemId == 0`）返回 true。
2. **`custom1..5` 的七个字符** + `characterIndex >= 12` 与 §255 同一个界。
3. **两处独立计算 `characterIndex * 10 + classIndex * 2`** —— 而 `12 × 10 = 120` 与 §242 的界一致。
4. **`readMapEntityString` 只用 staged 路径**（旧路径保留）。
5. **MP 地图用 `.d3dbsp` + `AssetTypeMapEnts`，coop 地图用 `.mapents` + `AssetTypeAddonMapEnts`**。
6. **"一个渲染完整但玩家站不进去的地图"** —— 那段四层因果链的症状描述。
7. **`*assetName != assetPath` 是资产自证** —— 反向校验。
8. **内部 NUL ⇒ 拒绝**，尾部 NUL ⇒ 剥掉。
9. **三个界 4096/65535/65535，而 `modelCount` 必须 > 0 其它两个可以为 0**。
10. **"错误的步长仍产生貌似合理的浮点"** —— 形状正确但内容错误的防御。
11. **`readableSpan(models, modelCount)` 没乘元素尺寸 ⇒ `models` 是字节索引数组**。
12. **三字段快照非原子，而且只有 `ItemName` 失败会设置全部三个**。
13. **`nativeConfigString(ModelConfigStringBase + index)` 用武器索引上界去访问模型配置串** —— 可疑的界。
14. **`loadoutResolveFailure_.store(None)` 在检查之前** —— 会清除有意义的信息。

## 十三、未闭合点

- `ModelConfigStringBase + MaximumWeaponAssetIndex` 是否在模型区间内。
- `models`/`hulls` 的元素尺寸（1 或 2 字节）。
- 三字段快照的非原子性是否有实际影响。
- `MapEnts`/`AddonMapEnts` 的 XAsset 类型号。
- `EngineBindings.cpp` 16050 行之后未读取。
