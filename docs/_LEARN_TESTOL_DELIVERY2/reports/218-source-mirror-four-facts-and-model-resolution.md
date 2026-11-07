# 218 · 镜像是"四件不同的事"、"先报告再返回"的 lambda、模型解析失败的完整记账

## 一、范围

本报告学习 `EngineBindings.cpp` 4709–4908 行。

## 二、`resetNativeServerEntityMirrorAfterWorldInitialization` 的第二遍

```cpp
for (const auto &[entityNum, mirror] : nativeServerEntityMirror_)
{
    auto* slot = (std::byte*)gEntities_ + entityNum * SvNativeServerEntity::Size;
    if (mirror.source.shape == SvCollisionShape::ScriptModelDObj)
        serverDObjFreeAdapter((int32)entityNum, 0);
    std::memcpy(slot, mirror.baseline.bytes.data(), SvNativeServerEntity::Size);
}
nativeServerEntityMirror_.clear();
```

### 2.1 两件事

```text
1. 若该实体是 ScriptModelDObj ⇒ 释放它的 DObj
2. 把【基线】字节写回 gEntities_ 的槽
```

**"把基线写回"** —— 恢复成发布前的状态。

**这解释了 `NativeServerEntityMirrorSlot` 为什么有 `baseline`**（§189）。

### 2.2 与 §217 里那个"只校验不修改"的循环的关系

**§217 读到的是第一个循环**（只检查 `writableBytes`），**这里是第二个循环**（真正做事）。

**所以整个函数分两个循环**：

```text
第一遍：只校验每个槽可写（失败即返回）
第二遍：释放 DObj + 写回基线
```

**"先全验证，再全执行"** —— 这是事务的标准形状。

## 三、`publishNativeServerEntityData`：三行核心

```cpp
if (!nativeServerEntityBindingsAvailable() || !entityCount ||
    entityCount > SvNativeServerEntity::Capacity)
    return false;

const auto publishedEntities = *serverGameEntitiesPointer_;
if (publishedEntities && publishedEntities != gEntities_)
    return false;

*serverGameEntityCount_ = std::max(*serverGameEntityCount_, entityCount);
*serverGameEntitiesPointer_ = gEntities_;
return *serverGameEntitiesPointer_ == gEntities_ &&
       *serverGameEntityCount_ >= entityCount;
```

### 3.1 三重检查

```text
1. 绑定可用 + 计数非零 + 不超容量
2. 【已发布指针必须是 null 或我们自己的】  ← 关键
3. 写完之后再读回验证
```

### 3.2 第 2 条的意义

> **如果 `*serverGameEntitiesPointer_` 非空且不是 `gEntities_`，说明引擎已经发布了【别的】数组** —— 那么覆盖它会破坏别人的状态。

**所以"已经有人占了这个槽"就拒绝**。

### 3.3 `std::max` 而不是直接赋值

```cpp
*serverGameEntityCount_ = std::max(*serverGameEntityCount_, entityCount);
```

**只增不减** —— 因为**已经发布过的实体号不能被"缩回去"**。

### 3.4 那段注释

```cpp
// CODOL inlines the newer SV_LocateGameData entity publication in
// G_Spawn. This embedded-server path owns the same fixed array but
// does not run the native allocator before CM starts consuming it.
```

**"CODOL 把较新的 `SV_LocateGameData` 实体发布内联在 `G_Spawn` 里"**

**而本路径拥有同一个固定数组，但不在 CM 开始消费它之前跑原生分配器** —— 所以手工发布。

### 3.5 返回值的意义

```cpp
return *serverGameEntitiesPointer_ == gEntities_ &&
       *serverGameEntityCount_ >= entityCount;
```

**不是 `return true`，而是"读回确认"** —— 因为这两个是**引擎拥有的全局**，写进去之后可能被引擎改。

## 四、`nativeServerEntityMirrorMatches`：**"四件不同的事"**

这是本组最重要的一段。

### 4.1 那句设计原则

```cpp
// OLMOD(mirror-mismatch-diagnostics): "the mirror does not match" is
// four different facts and the caller could only ever see one bit of
// it. Name which check failed, for which entity, and - for the byte
// image - the FIRST OFFSET that differs, because that offset is the field.
```

**三点**：

1. **说清是哪一项检查失败**；
2. **说清是哪个实体**；
3. **对字节镜像，说清【第一个不同的偏移】—— 因为那个偏移就是字段**。

### 4.2 `report` lambda 的"先报告再返回"

```cpp
const auto report = [this](const char* which, uint32 entityNum, size_t offset) {
    if (mirrorMismatchLogCounter_++ >= 12) return false;
    snprintf(line, ..., "native entity mirror MISMATCH check=%s entity=%lu offset=%zd",
        which, entityNum, offset);
    RuntimeLog::write(...);
    return false;
};
```

**返回 `false` 而 lambda 的唯一目的就是"记录并返回 false"** —— 所以调用点写成：

```cpp
return report("absent", entity.entityNum, 0);
```

**"先报告再返回 false"** —— 这消除了"忘记记录"的可能。

**`return report(...)` 这种写法**让"记录"与"返回失败"成为一个不可分的动作。

### 4.3 六种失败

```text
"preconditions"     ← 前置检查（4 项）
"absent"            ← 镜像里没有这个实体
"projection-failed" ← SV_BuildNativeServerEntity 返回空
"source"            ← sourceProjection 不匹配
"unreadable"        ← gEntities_ 槽不可读
"linked-image"      ← gEntities_ 槽内容与 linkedImage 不匹配
```

**六种**，而不是一个比特。

### 4.4 第一个不同偏移的找到方式

```cpp
std::size_t offset{};
while (offset != SvNativeServerEntity::Size &&
       mirror->second.sourceProjection.bytes[offset] == projection->bytes[offset])
    ++offset;
return report("source", entity.entityNum, offset);
```

**逐字节比较，找到第一个不同就停** —— 那个偏移就是"哪个字段错了"。

**`offset` 会是 `Size` 吗？** 只有当所有字节相同才可能，而那时前面已经 `!=` 判断过了。所以 `offset != Size` ✓

### 4.5 两类比较

```text
"source"       ：sourceProjection   vs  重新构建的 projection
"linked-image" ：gEntities_ 槽     vs  linkedImage
```

**前者验证"我们的投影函数还是确定的"**；
**后者验证"引擎没有改动我们发布进去的字节"**。

**两个不同的不变量**。

### 4.6 capsule 专用的 entityState 重建

```cpp
if (entity.shape == SvCollisionShape::Capsule)
{
    std::memcpy(entityState.bytes.data(),
        mirror->second.sourceProjection.bytes.data(), SvNativeEntityState::Size);
    entityStatePointer = &entityState;
}
```

**只有 capsule 需要重建 entityState** —— 因为 `SV_BuildNativeServerEntity(entity, entityState)` 的第二个参数是 `SvNativeEntityState*`，只有 capsule 用它。

**注意它从 `sourceProjection` 取 entityState** —— 所以是"用我们上次投影的结果去重建"。

### 4.7 `mirrorMismatchLogCounter_++ < 12` 与 `>= 12`

**两处不同的判断**：

```cpp
前置检查：  if (mirrorMismatchLogCounter_++ < 12) { log }
report：    if (mirrorMismatchLogCounter_++ >= 12) return false;
            { log }
```

**逻辑等价但写法相反** —— 一处"小于则记"，一处"大于等于则提前返回"。

**这是可以指出的风格不一致**，但行为相同。

## 五、模型解析失败：本组最有价值的"未完成"记录

### 5.1 3.3.3.3 的四步

```text
1. CharacterSelectionResolve   0x0040CA30  ┐
2. WorldCharacterModelResolve  0x0040C980  ┘ 把 selection ids 变成稀疏的 11 槽模型 id 列表
3. WorldCharacterModelSlotBases           ┐ 每个非零 id 走一个 per-slot 基址数组
4. WorldCharacterModelNameTable           ┘ 与一个 16 字节步长的名字表
```

### 5.2 四个都不存在

```text
NONE of those four exist in OLfinal -- nine automated methods, two
structural searches and a fingerprint pass all failed on them because
they were searching for counterparts that are not there.
```

**"九种自动方法、两次结构搜索、一次指纹扫描全部失败"** —— **因为它们找的是不存在的对应物**。

**这是"确认不存在"而不是"没找到"** —— 而确认不存在需要多次独立方法。

### 5.3 OLfinal 的替代方案

```text
sub_61B6C0(char *dst[11], const void *record, u16 characterItemId, int ctx)
    memsets dst for 0x2C bytes and fills it with `char *` model names.
    `record` is 12 entries of 12 bytes; entry k is
        {u32 a @+0, u8 enable @+4, u32 b @+8}
    and the item id is ROL32(*(u32*)0x00E4DD90 ^ b ^ a, 8).
    Entry 0 and entry 10 are skipped; entries 1..9 fill dst[0..8]
    and entry 11 fills dst[9], so dst[10] is always left null.
```

### 5.4 这条终于解开了 §202 的疑问

**§202 里我指出 `CharacterRecordToSelectionName{11,0,1,...,11,9}` 与"条目 1..9→名字 0..8、条目 11→名字 9"存在矛盾。**

**现在这里有精确表述**：

```text
条目 1..9  → dst[0..8]
条目 11    → dst[9]
条目 0、10 → 跳过
dst[10]    → 永远 null
```

**十二条目、十一个槽**：

```text
条目: 0  1  2  3  4  5  6  7  8  9  10  11
      ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓
dst:  -  0  1  2  3  4  5  6  7  8  -   9
```

**所以 `dst[10]` 没有来源** —— 而 §200 的数组 `{11,0,1,2,3,4,5,6,7,8,11,9}` 若理解为"dst[i] ← 条目 x[i]"：

```text
dst[0]  ← 条目 11    ✗ 应为 1
dst[1]  ← 条目 0     ✗ 应为 2
...
```

**仍不符**。**若理解为"条目 i → dst[x[i]]"**：

```text
条目 0  → dst[11]    ✗ 跳过
条目 1  → dst[0]     ✓
条目 2  → dst[1]     ✓
...
条目 9  → dst[8]     ✓
条目 10 → dst[11]    ✗ 跳过
条目 11 → dst[9]     ✓
```

**除了条目 0 与 10 之外全部吻合！**

**所以那个数组的意思是"条目 i 映射到 dst[x[i]]"**，而条目 0 与 10 的值（`11`）是**占位/无效**（因为 `dst` 只有 11 项，索引 11 越界，正好表示"不用"）。

**这解开了 §202 的疑问。**

### 5.5 `sub_80E110` 解析单个 id

```text
sub_80E110 resolves one item id: sub_660C90(id) walks the item registry
this file already binds -- ItemBucketOffsets, ItemLookup/Count,
ItemDefinitions at stride 40 -- and requires the definition's type byte
at +5 to be 2, then indexes CharacterItemDefinitionTable at stride 52
by the u16 at +2.
```

**三步**：

```text
1. sub_660C90(id) 走物品注册表（本项目已绑定）
2. 要求 definition 的字节 +5 == 2     （§200 的"分类在 flags>>8"）
3. 用 +2 处的 u16 索引 CharacterItemDefinitionTable（步长 52）
```

**`stride 40`** 是 `ItemDefinitions`，**`stride 52`** 是 `CharacterItemDefinitionTable` —— **两个不同的表，两个不同的步长**。

**这与 §200 里"40 是 3.3.3.3 的、52 才对"**是同一个问题的另一面：`ItemDefinitions` 用 40 是对的（另一个表），而 `CharacterItemDefinitionTable` 用 52。

### 5.6 两件仍未知

```text
* `ctx`（sub_61B6C0 的第 4 个参数，到达 sub_80DEF0）
* 我们的 11 个 selectionIds 中哪一个属于 12 个记录条目中的哪一个，
  考虑到有两个条目被跳过
```

**第一条与 §201 里"变体选择器 = faction + 1"呼应** —— 那个 `ctx` 就是变体选择器。

**第二条**：虽然 5.4 解开了数组语义，但"我们的哪些 id 放进哪些条目"仍未定。

### 5.7 那条"合成记录是平凡的"

```text
Synthesising the record is otherwise trivial -- the encoding inverts
as a = 0, b = key ^ ROR32(id, 8) -- so this is a short follow-up, but
it has to be done against a running server rather than guessed.
```

**`a = 0, b = key ^ ROR32(id, 8)`** —— 与 §201 的 `encodeCharacterItemId` **完全一致**！

```cpp
record.encodedLow = 0;
record.encodedHigh = std::rotr(itemId, 8) ^ decodeKey;
```

**所以 §201 里那个编码器就是"合成记录"的工具，只是槽位映射未定。**

### 5.8 那条"错误槽位映射的后果"

```text
A wrong slot mapping produces a plausible, fully-populated, WRONG set
of model names, which is exactly the failure mode this project keeps
paying for.
```

**"一个错误的槽位映射会产生一组貌似合理的、完全填充的、错误的模型名"**

**这正是 §202 里"§67 第一次活体运行产出两个错误族的名字"的机制。**

### 5.9 失败的具体后果（**有界且已知**）

```text
So the path FAILS LOUDLY here rather than pretending. The cost is
bounded and known: updateNativeServerPlayerDObj's caller logs the
stage and continues, so players still spawn, move and shoot;
what they lack is a server DObj, which means no rendered body
components and the locational trace falls back to the capsule.
```

**三条**：

1. **玩家仍能出生、移动、开枪**；
2. **缺少服务端 DObj ⇒ 没有渲染的身体部件**；
3. **定位 trace 退回到 capsule**。

**"失败但已知边界"** —— 这是本项目里少见的"明确说清缺什么"的记录。

### 5.10 退出条件

```text
TODO(CODOL): implement via sub_61B6C0 once `ctx` and the slot mapping
are read from a live server; exit condition is a resolved name set
that matches what the client renders for the same customization.
```

**"一个与客户端为同一 customisation 渲染的名字集相匹配的解析结果"** —— 可验证的退出条件。

## 六、关键结论

1. **先全验证再全执行**（`reset` 的两个循环）。
2. **"已经有人占了这个槽"就拒绝**（`publishNativeServerEntityData`）。
3. **`std::max` 只增不减** —— 已发布的实体号不能缩回。
4. **"镜像是四件不同的事"** ⇒ 六种具名失败 + 第一个不同偏移。
5. **`return report(...)` 让"记录"与"返回失败"不可分**。
6. **四个 3.3.3.3 的模型解析函数在 OLfinal 中确认不存在**（九种方法 + 两次结构搜索 + 指纹扫描）。
7. **`{11,0,1,2,3,4,5,6,7,8,11,9}` 的语义是"条目 i → dst[x[i]]"**，条目 0 与 10 的 `11` 是"越界=不用"占位 —— **解开了 §202 的疑问**。
8. **`ItemDefinitions` 步长 40 与 `CharacterItemDefinitionTable` 步长 52 是两个不同的表**。
9. **失败边界已知**：出生/移动/开枪正常，缺渲染身体，定位 trace 退回 capsule。

## 七、未闭合点

- `ctx`（变体选择器）与"哪些 id 进哪些条目"仍未从活服务器读。
- `EngineBindings.cpp` 4908 行之后未读取。
