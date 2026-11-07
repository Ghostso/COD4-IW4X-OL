# 230 · 五条臂一种消息、"同一地址读写所以恒成立"、整对象转储

## 一、范围

本报告学习 `EngineBindings.cpp` 7104–7303 行。

## 二、`failedPlayerDObjStage` 的两级包装

```cpp
failedPlayerDObjEntity = entry.source.entityNum;
failedPlayerDObjStage = std::move(failureStage);
return false;
```

```cpp
const auto playerDObjFailed = [&failed, &failedPlayerDObjEntity, &failedPlayerDObjStage] {
    const auto stage = failedPlayerDObjStage.empty()
        ? std::string("player_dobj")
        : std::string("player_dobj_") + failedPlayerDObjStage;
    return failed(stage, failedPlayerDObjEntity);
};
```

**两级**：

```text
ensurePlayerDObjs 返回 false ⇒ 记录 entity 与 stage
playerDObjFailed 被调用 ⇒ 拼成 "player_dobj_<stage>" 并转发给 failed
```

**`std::move(failureStage)`** —— 因为 `failureStage` 是局部 `std::string`，后面不再用。

**如果 `stage` 为空** ⇒ 用 `"player_dobj"`（无后缀）。

## 三、`requiredEntityCount` 的计算

```cpp
uint32 requiredEntityCount{};
if (!desired.empty())
    requiredEntityCount = desired.back().source.entityNum + 1;

for (const auto& [entityNum, mirror] : nativeServerEntityMirror_)
    requiredEntityCount = std::max(requiredEntityCount, entityNum + 1);

if (requiredEntityCount && !publishNativeServerEntityData(requiredEntityCount))
    return failed("game_data_publication");
```

### 3.1 两个来源

```text
1. desired 里【最大】实体号 + 1
2. 已镜像的【最大】实体号 + 1
```

**因为要发布的是"至少覆盖到这么多"的容量** —— 与 §218 里 `*serverGameEntityCount_ = max(现有, entityCount)` 一致。

### 3.2 `desired.back()` 依赖排序

**`desired` 是按实体号严格递增构建的**（§228 的 `source_order` 检查）—— 所以 `back()` 就是最大。

## 四、`sameScale` 的比较

```cpp
std::all_of(
    (const float*)(dobj + DObjScaleOffset),
    (const float*)(dobj + DObjScaleOffset) + DObjScaleComponentCount,
    [&source](const float component) {
        return component == source.modelScale;
    });
```

**三个分量都等于 `source.modelScale`** —— 精确浮点比较。

**因为写的就是同一个值** —— 所以精确比较是正确的。

## 五、**"同一地址读写所以恒成立"**（本组最重要的一段）

### 5.1 那段推理

```cpp
// READBACK MISMATCH: DUMP THE OBJECT INSTEAD OF GUESSING WHICH OFFSET MOVED.
// The scale check cannot be the one failing -- it writes and reads the SAME
// address, so it agrees whether or not DObjScaleOffset is right. That leaves
// DObjModelCountOffset (9) and DObjModelPointersOffset (192), both bare literals
// carried from 3.3.3.3.
```

**"scale 检查不可能是失败的那个 —— 它写和读【同一个地址】，所以无论 `DObjScaleOffset` 对不对它都会一致。"**

**这是一个极其干净的推理**：

```text
写：*(float*)(dobj + 0xC8) = 1.0
读：*(float*)(dobj + 0xC8) == 1.0
```

**两者用同一个偏移** ⇒ **恒为真**（除非有并发写）。

**所以失败只可能在另外两个偏移上**：

```text
DObjModelCountOffset      = 9      （裸字面量，来自 3.3.3.3）
DObjModelPointersOffset   = 192    （裸字面量，来自 3.3.3.3）
```

### 5.2 那两个已知值

```cpp
// Two values in this object are KNOWN: the model pointer findXAsset just
// returned, and the float 1.0 written above. Print the header and
// both known values, and the true offsets can be recovered offline by searching
// the dump for them -- no second cycle spent on a guess.
```

**两个已知值**：

```text
模型指针    ← findXAsset 刚返回的
1.0f        ← 刚写进去的（或 source.modelScale）
```

**"在转储里搜这两个已知值就能offline恢复真实偏移"** —— 不需要再花一轮。

**这是"用已知值定位未知偏移"的标准手法**，与 §143 里"用 XAsset 名字重算哈希验证桶"同族。

### 5.3 那句"3.3.3.3 的、按 0xCC 结构尺寸的"

```cpp
// DObjModelPointersOffset/DObjScaleOffset, which
// are 3.3.3.3's and sized for that build's 0xCC struct.
```

**而 §192 已确认本 build 是 `0xD8`** —— **所以这两个偏移确实可能就是错的**。

## 六、五条臂：一个消息

### 6.1 那条设计原则

```cpp
// FIVE WAYS TO FAIL, ONE MESSAGE. `native entity mirror failed stage=script_model_dobj`
// named the lambda, not the arm, and the arms have nothing in common: an already-live
// DObj, a missing XModel asset, a refused engine create, an unwritable DObj, and a
// post-write mismatch. Two of them would indict a per-build constant (AssetTypeXModel,
// DObjScaleOffset) and two would indict the adapter RVAs, so the message has to separate
// them or the next cycle buys nothing. Logged once per (entity, arm).
```

### 6.2 五条臂与它们各自指向的缺陷

| 臂 | 症状 | 会指向 |
|---|---|---|
| `already_live` | DObj 已存在 | 状态管理 |
| `xmodel_not_found` | 资产缺失 | **per-build 常量**（`AssetTypeXModel`） |
| `create_returned_null` | 引擎拒绝创建 | **adapter RVA** |
| `scale_offset_unwritable` | DObj 不可写 | **per-build 常量**（`DObjScaleOffset`） |
| 回读不匹配 | 写后不一致 | **per-build 常量**（两个偏移） |

**"两个会指向 per-build 常量，两个会指向 adapter RVA"**

### 6.3 去重键

```cpp
auto details = "script_model_dobj/" + arm + " entity=" + entityNum +
    " model=" + modelName + " scale=" + scale;
if (details != scriptModelDObjFailure_) { ... log ... }
```

**按完整详情串去重** —— 所以"同一实体的不同臂"会各记一次。

**尽管注释说"once per (entity, arm)"**，而实现是"once per distinct full details"—— **包括 model 与 scale**。

**所以 model 名变化的同一实体会再记一次** —— 比"per (entity, arm)"更细。

## 七、`createScriptModelDObj` 的五步

```cpp
1. if (shape != ScriptModelDObj) return true;          // 不适用
2. if (serverDObjGetAdapter(...)) return dobjNote("already_live", ...);
3. descriptor.model = findXAsset(AssetTypeXModel, name, false).data;
   if (!descriptor.model) return dobjNote("xmodel_not_found", ...);
4. dobj = serverDObjCreateAdapter(&descriptor, 1, nullptr, entityNum, 0,0,0);
   if (!dobj) return dobjNote("create_returned_null", ...);
5. if (!writableBytes(dobj, DObjScaleOffset + 3*4))
       return dobjNote("scale_offset_unwritable", ...);
6. fill_n(dobj + DObjScaleOffset, 3, source.modelScale);
7. if (scriptModelDObjMatches(source)) return true;
8. ... 转储 ...
```

### 7.1 `modelCount = 1`

**`serverDObjCreateAdapter(&descriptor, 1, nullptr, ...)`** —— **一个模型**。

**`tre=nullptr`** —— 与 §226 里演员击打姿势用 `owner.tree.data()` 不同（那里传了树）。

### 7.2 `writableBytes` 的范围

```cpp
DObjScaleOffset + sizeof(float) * DObjScaleComponentCount
= 200 + 12 = 212
```

**只检查到 `+212`** —— 而 §198 说对象延伸到 **216**（因为 `+212` 是 `-1`）。

**所以这里少检查 4 字节** —— 但那 4 字节不写，所以可接受。

### 7.3 `scriptModelDObjMatches` 的四项

```cpp
1. shape == ScriptModelDObj
2. dobj && model && readableSpan(dobj, 212)
3. *(uint8*)(dobj + DObjModelCountOffset) == 1
4. models && readableSpan(models, 4) && models[0] == model
5. all_of(scale[0..3], == source.modelScale)
```

**五项**（含 shape 早退返回 true）。

### 7.4 `already_live` 的那个"不覆盖"

```cpp
if (serverDObjGetAdapter((int32)source.entityNum))
    return dobjNote("already_live", source);
```

**如果槽已有 DObj 就拒绝** —— 而不是覆盖。

**与 §226 里演员姿势的 `fail("foreign-owner")` 同一纪律**。

## 八、转储的两个已知值

```cpp
const auto* bytes = (const std::byte*)serverDObjGetAdapter((int32)source.entityNum);
const auto* model = findXAsset(AssetTypeXModel, source.modelName.c_str(), false).data;
std::string dump;
constexpr size_t DumpBytes = NativeServerDObjSize;    // 0xD8 = 216
if (bytes && readableSpan(bytes, DumpBytes))
    ...
```

**`DumpBytes = 0xD8`** —— 与 §192 的步长一致 ✓

**所以转储整个对象** —— 然后离线搜两个已知值。

## 九、关键结论

1. **`failureStage` 两级包装**：内部 record → `"player_dobj_<stage>"` 转发。
2. **`requiredEntityCount` 取 desired 与已镜像两边的最大值**。
3. **"写和读同一地址，所以恒为真"** —— 这是一个可用于排除嫌疑的强推理。
4. **两个已知值（模型指针 + 1.0f）可以在转储里定位真实偏移** —— 不需要第二轮。
5. **五个臂各自指向不同缺陷**（per-build 常量 vs adapter RVA）。
6. **`already_live` 拒绝而不是覆盖**，与 `foreign-owner` 同一纪律。
7. **转储 `0xD8` 字节**，与已确认的步长一致。

## 十、未闭合点

- `DObjModelCountOffset = 9` 与 `DObjModelPointersOffset = 192` 是否真错，取决于转储结果（不在本组）。
- `EngineBindings.cpp` 7303 行之后未读取。
