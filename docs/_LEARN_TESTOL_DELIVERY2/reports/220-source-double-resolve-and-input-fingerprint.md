# 220 · 三次解析的差集、FNV-1a 输入指纹、五种 failureStage

## 一、范围

本报告学习 `EngineBindings.cpp` 5107–5306 行。

## 二、`resolveCharacterModelNames` 的收尾

```cpp
if (filledRecord)
    *filledRecord = filled + "|slots=" + slots;
return resolvedModelCount != 0;
```

注释：

```cpp
// ZERO NAMES IS A FAILURE, NOT AN EMPTY SUCCESS. Section 48d's whole warning is
// that this path degrades silently; a character that resolves to nothing has not
// resolved, and reporting true here would build a DObj out of eleven nulls.
```

**"零个名字是失败，不是空成功"** —— 因为返回 true 会让上层"用十一个 null 建 DObj"。

`filledRecord` 的格式：`"0,532,525,...|slots=0,1,2,3,4,6"` —— **id 串 + 原始槽位串**。

## 三、三个消费者

### 3.1 `characterResolvedModelNames`

```cpp
for (index = 0; index < count; ++index)
    if (names[index] && *names[index])
        resolved.emplace_back(names[index]);
```

**双重检查**：指针非空 **且** 首字节非零（非空串）。

**返回 `vector<string>`** —— 所以是拷贝。

### 3.2 `characterBodyModelName`：按**前缀**找身体

```cpp
for (index = 0; index < count; ++index)
{
    if (!names[index] || !*names[index]) continue;
    const std::string name{ names[index] };
    if (name.rfind("fpa_", 0) == 0) return name;
}
return {};
```

注释：

```cpp
// The body is the `fpa_` entry. Named rather than taken by position, because
// the resolver's slot order is the engine's and this project has already paid
// once for reading a slot index as a length (section 67's sparse list).
```

**"按名字找而不是按位置，因为解析器的槽序是引擎的，而本项目已经为'把槽索引当长度'付过一次代价"**

**`rfind("fpa_", 0) == 0`** —— 判前缀的标准写法（`at == 0` 表示从 0 开始找）。

### 3.3 `characterOutfitAttachmentModels`：**同一个角色解析两次**

这是本组最重要的一段。

#### 3.3.1 为什么只发"客户端算不出来的"

```cpp
// WHAT THE CLIENT WOULD NOT WORK OUT FOR ITSELF, and nothing more.
//
// A remote client resolves all eleven of a player's models from ONE wire field
// -- the character item id -- by letting sub_619AD0 fill every empty record
// entry from that character's own per-slot defaults. So the defaults are
// already on screen and must NOT be attached again; attaching a model the
// client also derives would draw it twice.
```

**远程客户端只凭一个线字段（character item id）就能解析出全部十一个模型** —— 因为 `sub_619AD0` 用角色自己的 per-slot 默认值填空条目。

**所以默认模型"已经在屏幕上"，不能再附加** —— 否则**画两遍**。

#### 3.3.2 差集的做法

```text
Resolve the record TWICE against the same engine,
once with the player's equipped pieces and once with entry 0 alone,
and the names present in the first and absent from the second are exactly the
models the wire has to carry.
```

**两次解析**：

```text
第一次：customization（含 recordItemIds）
第二次：defaultsOnly（recordItemIds 全清，只留 [0] = characterItemId）
```

**差集 = 需要走线传的模型**。

#### 3.3.3 `defaultsOnly` 的构造

```cpp
auto defaultsOnly = customization;
defaultsOnly.recordItemIds = {};
defaultsOnly.recordItemIds[0] = customization.characterItemId;
```

**清空后重设 `[0]`** —— 因为 `record[0]` 由 `characterItemId` 决定。

#### 3.3.4 为什么**按名字**比较而不是按槽位

```cpp
// COMPARE BY NAME, NOT BY SLOT. The resolver COMPACTS its output (a sparse
// slot list is the DObj crash from section 67), so the same model can sit at
// a different index in the two answers and index equality would report a
// change that is not one.
```

**"解析器压紧了它的输出，所以同一个模型在两次答案里可以坐在不同的索引上，而索引相等会报告一个不存在的变更。"**

**这是 §219 里"压紧"的副作用**：压紧之后**槽位索引不再稳定**，所以只能按名字比。

**而 §218 里 `mirrorMismatchLogCounter_` 那类诊断仍在用偏移** —— 因为那是字节镜像不是名字列表。

#### 3.3.5 去重

```cpp
if (std::ranges::find(extras, std::string{name}) == extras.end())
    extras.emplace_back(name);
```

**线性去重** —— 因为最多 11 项。

## 四、`updateNativeServerPlayerDObj`：五个具名 `failureStage`

```cpp
failureStage = "binding_or_thread";
if (!valid() || entityNum >= nativeServerCharacterInfo_.size() ||
    gameThreadId_ != GetCurrentThreadId()) return false;

failureStage = "animation_not_ready";
if (serverAnimationInitializationStatus() != Ready) return false;

failureStage = "empty_selection";
if (faction > 1 || color > 3 || none_of(selectionIds, id != 0)) return false;

failureStage = "model_resolution_unported_olfinal";
if (!resolveCharacterModelNames(...)) { ...log...; return false; }
```

### 4.1 `failureStage` 是**输出参数**

```cpp
bool updateNativeServerPlayerDObj(
    uint32 entityNum, const SvCharacterCustomization& customization,
    uint8 spawnGeneration, std::string& failureStage, bool& irreversibleMutationStarted) const
```

**两个输出**：失败阶段名、是否已开始不可逆变更。

**"每进入一个阶段就先设名字"** —— 所以任何 `return false` 都能被归因到那一段。

### 4.2 `empty_selection` 的三重条件

```cpp
faction > 1 ||            // 只能是 0 或 1
color > 3 ||              // 只能是 0..3
none_of(selectionIds, id != 0)   // 至少要有一个非零
```

**`color > 3`** 与 §181 里 `CODOL_CharacterColorSelectorFromDefinitionValue` 的 4 项表一致。

**`faction > 1`** —— 而 §212 里 `SvCharacterFaction` 有 `Tf` 与 `Sc`，对应 0 与 1 ✓

### 4.3 `irreversibleMutationStarted` 的用途

**在 `resolveCharacterModelNames` 之前设为 false** —— 因为那一步不改状态。

**后续步骤若开始改 DObj，就要设 true** —— 让调用方知道"回滚不了"。

## 五、那次"说清输入是什么"的 FNV-1a 指纹

### 5.1 为什么需要

```cpp
// SAY WHAT THE INPUT WAS, ONCE PER ENTITY. The port sketched in sec 48
// forges a twelve-entry item record out of `selectionIds` and hands it to
// sub_61B6C0, and the whole design rests on those ids being marketplace
// item ids in the namespace sub_80E110 looks up. Nothing has ever printed
// them. If they are zeros, or small enum values, the blocker is NOT the
// resolver ABI at all and sec 48 would be built on sand.
```

**关键判断**：

> **"如果它们是零，或者是小的枚举值，那么阻塞点【根本不在解析器 ABI】，而 §48 会建在沙上。"**

**这是一个"假设的上游"的检查** —— 整个方案依赖 `selectionIds` 是 marketplace item id。

### 5.2 FNV-1a 的实现

```cpp
std::uint32_t hash = 2166136261u;
const auto mix = [&hash](const std::uint32_t value) {
    hash = (hash ^ value) * 16777619u;
};
for (const auto id : customization.selectionIds) mix(id);
mix(customization.modelIndex);
mix(customization.viewmodelIndex);
mix(static_cast<uint32_t>(customization.faction));
mix(customization.color);
mix(customization.female ? 1u : 0u);
```

**七个输入**：

```text
selectionIds[11]  ← 11 次
modelIndex
viewmodelIndex
faction
color
female
```

**`2166136261u` = FNV offset basis**、**`16777619u` = FNV prime** ✓

**这是标准 FNV-1a 32 位**。

### 5.3 去重表

```cpp
static std::array<std::uint32_t, 18> reportedSelectionHash{};
if (entityNum < reportedSelectionHash.size() &&
    reportedSelectionHash[entityNum] != hash)
{
    reportedSelectionHash[entityNum] = hash;
    ... log ...
}
```

**18 项** —— 与 `MaximumGameClients` 一致。

**按实体去重**（不是全局）—— 所以每个玩家各记一次。

### 5.4 那条"仪器健康时必须沉默"

```cpp
// Deduped on the value, so a steady player is silent after one line and a
// change -- a respawn with a different class, another client -- reports
// again. See sec 44a: an instrument must be silent when healthy, and this
// path is not healthy yet, so it gets exactly one line per distinct input.
```

**"仪器健康时必须沉默"** —— 而**这条路径还不健康，所以每个不同输入恰好一行**。

### 5.5 日志内容

```text
"character customization entity=N faction=F female=0 colour=C
 modelIndex=M viewmodel=V selectionIds=a,b,c,..."
```

**八个字段** —— 把 `selectionIds` 逐项列出，因为**那正是要检查的东西**。

## 六、关键结论

1. **零个名字是失败**，因为返回 true 会用十一个 null 建 DObj。
2. **按前缀找身体**（`fpa_`），因为槽序是引擎的。
3. **"只发客户端算不出来的"** —— 默认模型已在屏幕上，重复附加会画两遍。
4. **解析两次取差集**是"客户端会自己算的"与"必须走线传的"的分界。
5. **压紧的副作用：槽位索引不再稳定 ⇒ 只能按名字比**。
6. **`failureStage` 是输出参数，每个阶段先设名字** —— 所以任何 `false` 都能归因。
7. **"如果 selectionIds 是零或小枚举值，阻塞点根本不在 ABI"** —— 这是对整个方案的假设检查。
8. **FNV-1a 指纹 + 按实体去重**，让不健康的路径"每个不同输入恰好一行"。

## 七、未闭合点

- `irreversibleMutationStarted` 在哪里被设为 true（5306 行之后）未读取。
- `EngineBindings.cpp` 5306 行之后未读取。
