# 212 · StringTable 的双重校验、15 个阶段名、`bind()` 的链式失败命名

## 一、范围

本报告学习 `EngineBindings.cpp` 3556–3735 行。

## 二、`parseWeaponAttachmentSlot` 的返回

```cpp
const auto slot = std::ranges::find(SlotNames, name);
if (slot == SlotNames.end()) return std::nullopt;
return static_cast<std::uint8_t>(slot - SlotNames.begin());
```

**索引 = 指针差** —— 所以 `SlotNames` 的顺序就是槽号。

## 三、`readStringTable`：**先问 `allowDefault=false`，再单独问 `IsDefault`**

### 3.1 那段注释

```cpp
// A table that is in the pool but not loaded still comes back as
// the default even with allowDefault=false, so ask separately too.
const auto header = findAsset(AssetTypeStringTable, name.data(), false);
if (header.data && isDefault &&
    isDefault(AssetTypeStringTable, name.data()))
{
    return nullptr;
}
```

**"一个在池里但未加载的表，即使 `allowDefault=false` 仍会作为默认值回来，所以还要单独问一次。"**

**这与 §182 里 `DB_FindXAssetHeader` 的分析完全一致**：

> `allowDefault=false` 只在**未命中**路径上抑制默认值 —— 一个存在但尚未加载的资产**仍然会作为默认值回来**。

**这里是那条规则的实际应用**。

### 3.2 六项结构校验

```cpp
if (!readableSpan(table, sizeof(*table)) ||
    table->columnCount < minimumColumns || table->columnCount > 256 ||
    table->rowCount <= 0 || table->rowCount > 4096 || !table->values)
{
    return nullptr;
}
```

```text
表本身可读（16 字节）
columnCount ∈ [minimumColumns, 256]
rowCount   ∈ (0, 4096]
values 非空
```

**四个范围**：列数 256 上限、行数 4096 上限、列数下限、行数下限。

### 3.3 名字必须**反向匹配**

```cpp
const auto tableName = readCString(table->name, 128);
if (!tableName || !asciiCaseInsensitiveEqual(*tableName, name))
    return nullptr;
```

**这不只是校验，而是身份确认** —— 因为 `findAsset` 可能返回一个"看起来对"的默认对象，而**只有名字能确认真的是它**。

### 3.4 单元格总数与可读性

```cpp
const auto cellCount = (size_t)table->columnCount * (size_t)table->rowCount;
if (!readableSpan(table->values, cellCount * sizeof(StringTableCell)))
    return nullptr;
```

**两次 `size_t` 转换再相乘** —— 防止 `int32 * int32` 溢出。

**`cellCount * 8`** —— 而 `sizeof(StringTableCell) == 8` ✓

**`readableSpan` 是逐区域推进的**（§210），所以即使表跨多个页也能正确验证。

## 四、`findStringTableRow`：**三态返回**

```cpp
std::optional<const StringTableCell*> findStringTableRow(
    const StringTable& table, std::string_view key)
{
    for (rowIndex = 0; rowIndex < table.rowCount; ++rowIndex)
    {
        row = table.values + rowIndex * table.columnCount;
        rowName = readStringTableCell(row[0]);
        if (!rowName) return std::nullopt;        // ← 【读失败】
        if (*rowName == key) return row;          // ← 【找到】
    }
    return static_cast<const StringTableCell*>(nullptr);  // ← 【没找到】
}
```

### 4.1 三态的语义

```text
optional 有值        → 找到了，指向那一行
optional 为空(nullopt) → 【读过程中出错】
optional 含 nullptr  → 【读完了，没有这个 key】
```

**这是三层信息**：

1. "找到"；
2. "读不出"（数据损坏）；
3. "读了但没有"（正常未命中）。

**与 §193 里"`count=0` 与 `unreadable` 是不同答案"是同一条原则**。

### 4.2 `static_cast<const StringTableCell*>(nullptr)`

**用 `nullptr` 显式构造一个"有值的 optional"** —— 而不是 `std::nullopt`。

**这个写法不常见但完全正确**：`optional<T*>` 可以持有 `nullptr` 作为值。

### 4.3 逐行线性扫描

**`rowCount` 上限 4096** —— 所以最坏 4096 次字符串比较。

**这与 §143 里 XAsset 哈希表 O(1) 查找形成对照** —— StringTable 没有哈希索引。

## 五、`ServerAnimationInitializationStatusName`：15 项

```text
not_initialized / ready / invalid_binding / wrong_thread / context_busy
begin_load_anim_trees_failed / load_anim_trees_failed
animation_script_assets_unavailable / find_anims_failed
parse_anim_script_failed / precache_anim_trees_failed
find_anim_trees_failed / end_load_anim_trees_failed
finalize_player_anims_failed / invalid_output
```

### 5.1 九个 `_failed` 对应 CL_ParseGamestate 的九个步骤

```text
BeginLoadAnimTrees → LoadAnimTrees → AnimationScriptAssets
→ FindAnims → ParseAnimScript → PrecacheAnimTrees → FindAnimTrees
→ EndLoadAnimTrees → FinalizePlayerAnims
```

**与 §199 里 `sub_74B010`（`EndLoadAnimTrees`）与 `BG_FindAnimTrees`/`BG_FinalizePlayerAnims` 的顺序关系对应**。

### 5.2 三个前置状态

```text
NotInitialized / InvalidBinding / WrongThread / ContextBusy
```

**`WrongThread`** —— 与 `gameThreadId_` 检查对应。

**`ContextBusy`** —— 动画上下文被占用（可能因为另一个线程在跑）。

## 六、`SV_CurrentNativeStage`：`atomic<const char*>`

```cpp
const char* SV_CurrentNativeStage()
{
    const auto* stage = CurrentNativeStage.load(std::memory_order_acquire);
    return stage ? stage : "none";
}

void SV_SetCurrentNativeStage(const char* stage)
{
    CurrentNativeStage.store(stage ? stage : "none", std::memory_order_release);
}
```

### 6.1 acquire/release 配对

**写用 `release`、读用 `acquire`** —— 保证指针写入对读者可见。

### 6.2 空值归一

**两个方向都归一成 `"none"`** —— 所以调用方永远拿到非空指针。

**`"none"` 是静态存储**（字符串字面量），所以原子指针永远指向有效内存。

## 七、`bind()` 的六重前置

### 7.1 先撤销旧的发布

```cpp
bindingCommitted_.store(false, std::memory_order_release);
```

注释：

> **一次失败的重新绑定也必须撤销之前已提交的发布。**

**"先失效，再验证"** —— 所以任何失败路径都不会留下"已提交"的假象。

### 7.2 PE 头三级校验

```cpp
module_ = GetModuleHandleW(nullptr);
if (!module_) return false;

dos->e_magic != IMAGE_DOS_SIGNATURE → false
nt->Signature != IMAGE_NT_SIGNATURE
|| nt->FileHeader.TimeDateStamp != ExpectedTimestamp
|| nt->OptionalHeader.SizeOfImage != ExpectedImageSize → false
```

**五项**：模块句柄、DOS 签名、NT 签名、时间戳、镜像大小。

**`ExpectedTimestamp = 0x6096930A`**、**`ExpectedImageSize = 0x0E659000`**（§183 的本地覆盖）。

### 7.3 前缀校验的**链式命名**

```cpp
const auto nativeEntityPrefixFailure =
    !equal(SVLinkEntityPrefix, module_ + SVLinkEntityRva) ? "SV_LinkEntity"
  : !equal(SVUnlinkEntityPrefix, module_ + SVUnlinkEntityRva) ? "SV_UnlinkEntity"
  : !equal(SVTracePrefix, module_ + SVTraceRva) ? "SV_Trace"
  : nullptr;

if (nativeEntityPrefixFailure)
{
    log("native entity binding prefix mismatch function=" + nativeEntityPrefixFailure);
    return false;
}
```

**三层嵌套三元** —— 返回**第一个失败者的名字**。

**这是本组最实用的模式**：

```text
不是 "bind failed"
而是 "native entity binding prefix mismatch function=SV_Trace"
```

### 7.4 第二组链式

```cpp
const auto playerDObjPrefixFailure =
    !equal(NativeLerpFrameAccessorInitializePrefix, ...) ? "native lerp-frame accessor initializer"
  : !equal(BGPlayerAnimationPrefix, ...) ? "BG_PlayerAnimation"
  : !equal(BGUpdatePlayerDObjPrefix, ...) ? "BG_UpdatePlayerDObj"
  : ...
```

**注释说明了为什么某几项不在链里**：

```cpp
// CODDIFF(character_customization): the world character model
// resolver is checked on 3.3.3.3 and CANNOT be checked here. It
// does not exist in OLfinal -- see re/OLFINAL-FFA-HANDOFF.md §16a
// and §18d. OLfinal replaced the whole selector/slot-base/name-table
// scheme with an item-driven one, so there is no counterpart address
// to guard, and leaving the 3.3.3.3 RVA here would have guarded an
// unrelated function that happens to live there.
```

**"把 3.3.3.3 的 RVA 留在这里会守卫一个恰好住在那里、但无关的函数"** —— 这是**删掉校验的正确理由**，而不是"反正它不在了"。

## 八、关键结论

1. **`allowDefault=false` 不够** —— 池里未加载的资产仍回默认值，必须单独问 `IsDefault`。
2. **名字反向匹配是身份确认**，不只是校验。
3. **`optional<T*>` 可以持有 `nullptr`** —— 这是三态返回的正确写法。
4. **15 个状态里 9 个 `_failed` 对应 CL_ParseGamestate 的九个步骤**。
5. **`"none"` 是静态字面量** ⇒ 原子指针永远有效。
6. **链式三元返回"第一个失败者名字"** —— 比 "bind failed" 有用得多。
7. **删掉一个校验要给理由**（对端地址会指向无关函数）。

## 九、未闭合点

- `readStringTable` 被调用时的 `minimumColumns` 取值未在本组。
- `EngineBindings.cpp` 3735 行之后未读取。
