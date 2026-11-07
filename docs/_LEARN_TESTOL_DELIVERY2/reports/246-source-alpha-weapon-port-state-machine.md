# 246 · alpha 武器的七态机、`17 = markAlphaBaseWeapon` 在客户端恒真、模型表的"发布"手法

## 一、范围

本报告学习 `EngineBindings.cpp` 11697–12050 行。

## 二、`OLMOD_ALPHA_WEAPONS` 的**双重判据**

```cpp
const auto enabled = [] {
    std::array<char, 8> value{};
    const auto size = GetEnvironmentVariableA("OLMOD_ALPHA_WEAPONS", value.data(), 8);
    return size == 1 && value[0] == '1';
}();
```

### 2.1 `size == 1 && value[0] == '1'`

**`GetEnvironmentVariableA` 返回的是**不含 NUL 的长度** ⇒ `size == 1` 意味着值恰好是一个字符。**

**所以 `OLMOD_ALPHA_WEAPONS=1` 才启用；`=10`、`= 1`（带空格）都不启用** ✓

### 2.2 而第二个变量用的是 `nullptr, 0`

```cpp
const auto convertedBarrettEnabled =
    GetEnvironmentVariableA("OLMOD_ALPHA_BARRETT_METADATA", nullptr, 0) > 1;
```

**同一个 API 两种用法**：

```text
第一个  传缓冲区，检查内容
第二个  传 nullptr，只检查【是否存在且长度 > 1】
```

**`> 1` 而不是 `> 0`** —— 所以**值必须至少一个字符**（`X=1` 得到 1，不启用；`X=on` 得到 2，启用）。

**这与 §239 里三种环境变量读取方式（`getenv_s`/`_dupenv_s`/`GetEnvironmentVariableA`）又多了两种用法变体。**

## 三、`markAlphaBaseWeapon`：**客户端恒真**

```cpp
const auto markAlphaBaseWeapon = [this](const std::uint32_t index) {
    if (!module_ || !index || index >= BaseWeaponAssetCount)
        return false;
    if (OlMod::processRole() == OlMod::ProcessRole::Client)
        return true;                          // ← 【直接返回 true，不标记】
    auto *const type = module_ + ConfigStringTypesRva + WeaponConfigStringBase + index;
    if (!readableSpan(type, sizeof(*type))) return false;
    *type = 19;
    return true;
};
```

### 3.1 客户端与服务端**相反**

```text
Dedicated   把类型写成 19（普通武器）
Client      【什么都不做】，直接返回 true
```

### 3.2 那段注释的完整因果

```text
ConfigStringTypes is loaded with the shipped weapon boundary: slot 1224 and later are
tagged as modular weapon strings. Native weapon resolution appends our linked alpha
WeaponDefs at that same boundary, but does not retag the new ordinary definitions.

The DEDICATED must retag them while it derives the outgoing modular boundary.

The CLIENT must not: runtime-only alpha base names are absent from its constant
configstring table, so type 19 makes CL_GetConfigString return null and sub_59B560
dereference it.

Its gamestate hook restores the same native registry entries directly and leaves
those empty wire slots tagged as dynamic, which makes the accessor return the safe
empty gamestate string until the real "** ..." row.
```

### 3.3 三层

```text
1. 两边都需要注册 alpha 武器（append 在同一个边界 1224）
2. 专用服必须重打标签（用 19）以计算【出站模块化边界】
3. 客户端【绝不能】：它的 configstring 表里没有这些运行期名字
   ⇒ type 19 让 CL_GetConfigString 返回 null ⇒ sub_59B560 解引用 null ⇒ 崩
```

### 3.4 而客户端有另一条路

**"它的 gamestate 钩子直接恢复同样的原生注册表项，并让那些空线槽保持 tagged as dynamic"**

```text
客户端不重打标签，而是【保留动态标签】
⇒ 访问器返回【安全的空 gamestate 字符串】直到真正的 "** ..." 行
```

**这是一个"用空串当占位"的设计** —— 与 §236 里 `SV_ParseModularWeaponConfigString` 相关的处理同族。

### 3.5 三个类型的完整定义

```cpp
// Type 19 is this build's ordinary weapon type; type 21 and >=23 are the
// measured dynamic sentinels used by firstDynamicWeaponAssetIndex.
```

```text
19          本 build 的【普通】武器类型
21, >= 23   测量到的【动态】哨兵（§236 的两个哨兵）
```

**而 §236 说两个哨兵是 `{21, 23}`** ✓ 完全一致。

## 四、七态机的进入判定（`switch (previous)`）

### 4.1 三个**终态**

```cpp
case InvalidDefinition:
case LinkFailed:
case RegistrationFailed:
    return previous;
```

**永久失败** —— 一旦进入就不再尝试。

### 4.2 `SourceAssetMissing` 是**可恢复**的

```cpp
case SourceAssetMissing:
    // A converted Barrett closure legitimately disappears with the
    // front-end common_mp generation and is rebuilt below after the
    // booked map loads. Missing retained assets remain terminal when
    // that opt-in conversion is not active.
    if (!convertedBarrettEnabled) return previous;
    alphaWeaponPortStatus_.store(WaitingForWeaponRegistry, ...);
    break;
```

**两个分支**：

```text
convertedBarrettEnabled == false  ⇒ 【终态】（真的缺资产）
convertedBarrettEnabled == true   ⇒ 【转为 Waiting】，允许重建
```

**理由**："转换后的 Barrett 闭包本来就会随前端的 `common_mp` 代际消失，并在预定地图加载后重建。"

### 4.3 `Ready` 是**可失效**的

```cpp
case Ready:
{
    // A new map/gamestate generation rebuilds the native weapon registry
    // without unloading the cloned XAssets. The assets stay valid, but their
    // runtime indices disappear. Verify every active port before accepting
    // the cached Ready state and fall through to the normal resolver path
    // when the engine has reset the table.
    bool allRegistered = module_ && weaponLookup_;
    for (const auto &port : SV_AlphaWeaponPorts())
    {
        ...
        allRegistered = tryWeaponLookup(weaponLookup_, port.alphaName, index, fault) &&
            index != 0 && markAlphaBaseWeapon(index);
    }
    if (allRegistered) return previous;
    store(WaitingForWeaponRegistry, ...);
    break;
}
```

### 4.4 `Ready` 不是缓存而是**需要重新验证的断言**

**"一张新的地图/gamestate 代际重建原生武器注册表【而不卸载】克隆的 XAssets。资产仍然有效，但它们的【运行期索引消失】。"**

**所以 `Ready` 每次进入都要遍历全部 port 重新 lookup + 重新标记。**

**这是一个"缓存必须验证"的设计** —— 与 §245 里 "`stage`/`faultStage` 两条记录" 无关，但与 §236 里"反向验证"同族。

### 4.5 三类 port 的跳过条件

```cpp
if (port.lineage == MissingModelFamily ||
    (port.lineage == ConvertedPresentation && !convertedBarrettEnabled))
    continue;
```

```text
MissingModelFamily                         ⇒ 永远跳过
ConvertedPresentation && 未开开关            ⇒ 跳过
```

**`MissingModelFamily` 是一个"没有模型族"的谱系** —— 所以它本来就无法验证。

### 4.6 七个状态

从代码可数：

```text
Disabled                     （环境变量未开）
InvalidDefinition            （终态）
LinkFailed                   （终态）
RegistrationFailed           （终态）
SourceAssetMissing
WaitingForWeaponRegistry
WaitingForCommonAssets
Ready
WrongThread
```

**九个** —— 比"七态"多。

## 五、入口的**六个前置**

```cpp
if (!module_ || !zoneLoaded_ || !dbLinkXAssetEntry_ || !weaponLookup_ || !weaponResolver_)
    return publish(InvalidDefinition);
if (gameThreadId_.load() != GetCurrentThreadId())
    return publish(WrongThread);
if (!zoneLoaded_("common_mp"))
    return publish(WaitingForCommonAssets);
if (!weaponRegistryInitialized())
    return publish(WaitingForWeaponRegistry);
```

### 5.1 四个阶段

```text
① 绑定不全        ⇒ InvalidDefinition（【终态】！）
② 线程不对        ⇒ WrongThread
③ common_mp 未载入 ⇒ WaitingForCommonAssets
④ 注册表未初始化   ⇒ WaitingForWeaponRegistry
```

### 5.2 第一项的问题

**"绑定不全"被判为 `InvalidDefinition`（终态）** —— 但如果绑定是在**启动过程中的某个时刻**才完成的，那么第一次调用就会把它锁死成终态。

**这与 §4.1 的三终态（`InvalidDefinition`/`LinkFailed`/`RegistrationFailed` 永不重试）叠加 ⇒ 一个时序问题会变成永久失败。**

**这是一处值得指出的风险。**

### 5.3 `WrongThread` 不是终态 ✓

**而 `WrongThread` 不在 `switch` 的三个终态里** ⇒ 下次从别的线程调用仍会尝试 ✓

## 六、`XAsset` 池的**线性扫描**

```cpp
constexpr uint32 XAssetEntryPoolRva = 0x1F9B120;
constexpr size_t XAssetEntryCount = 120000;
constexpr size_t XAssetEntrySize = 28;
constexpr size_t XAssetEntryTypeOffset = 0;
constexpr size_t XAssetEntryDataOffset = 8;
constexpr size_t XAssetEntryZoneOffset = 16;

const auto assetZoneForHeader = [this](type, header) -> optional<uint8> {
    for (index = 0; index < XAssetEntryCount; ++index) {
        const auto *entry = entries + index * 28;
        if (!readableSpan(entry, 28)) return nullopt;
        memcpy(&entryType, entry + 0, 4);
        void *entryHeader; memcpy(&entryHeader, entry + 8, sizeof(entryHeader));
        if (entryType == type && entryHeader == header && entry[16] != 0)
            return entry[16];
    }
    return nullopt;
};
```

### 6.1 与 §143 的对照

**§143 学的是 `XAsset hash table（120,000 buckets, 28-byte stride, 81,128/81,128 verified）`** ✓

**同一个数：`120000` 个条目、`28` 步长。**

### 6.2 但这里是**线性扫描**而不是哈希

**`for (index = 0; index < 120000; ++index)`** —— 120,000 次 `memcpy` + 比较。

**"按 header 指针找 zone"这种查询没有哈希** —— 所以只能扫。

### 6.3 三个偏移

```text
+0    type       (uint32)
+8    header     (指针)
+16   zone       (uint8)
```

**注释的名字是 `XAssetEntryDataOffset = 8`** —— 而局部变量叫 `entryHeader`。

**所以"data"与"header"在这里是同一个指针** —— 即条目直接存 XAssetHeader 指针。

### 6.4 `entry[16] != 0` 的条件

**zone 为 0 的条目被跳过** —— 因为 0 是"未加载/无效"。

## 七、`publishedModelTables`：**`std::vector` 的 static 初始化**

```cpp
static std::vector<PublishedModelTable> publishedModelTables(
    SV_AlphaWeaponPorts().size());
```

### 7.1 大小在**静态初始化时**确定

**`SV_AlphaWeaponPorts()` 返回一个 span/数组，而 `.size()` 在第一次进入这个函数时求值一次。**

**而 `PublishedModelTable` 里有 `std::array<char,96>`、`std::vector`、`StringTable`** —— 有析构函数。

**所以这个函数里有需要析构的静态对象** —— 而 §245 说"`__try` 不能与对象展开共存（C2712）"。

**所以 `installAlphaWeaponPorts` 【没有】 `__try`** —— 与 `ensureWeaponRegistryInitialized` 形成对照。

### 7.2 那句"发布"的含义

```cpp
struct PublishedModelTable { std::array<char,96> path; std::vector<StringTableCell> cells; StringTable header; };
```

**"Published" = 把自己的内存交给引擎，然后**不能移动/释放**。**

**而 `storage.header = { storage.path.data(), columnCount, rowCount, storage.cells.data() };`** —— 三个指针全指向**自己的成员**。

**所以这个 struct 在链接之后**必须永久存活** —— 因此是 `static std::vector`。

### 7.3 `if (storage.cells.empty())` 的**幂等**

```cpp
auto &storage = publishedModelTables[portIndex];
if (storage.cells.empty())
{
    ... 填充 ...
}
```

**只在为空时填充** —— 而后续 `tryLinkXAssetEntry` **每次都会重跑**（在 `if` 之外）。

**所以重入时会重新链接同一个 header** —— 而 `linkedHeader = &storage.header` 是同一个地址。

**如果引擎的链接是幂等的（同一个 header 再链接一次覆盖同一条目），这没问题；否则会重复插入。**

## 八、两条**来源**：converted 与 source-table

### 8.1 converted（Barrett 特例）

```cpp
const auto rows = SV_AlphaBarrettModelTable();
if (rows.empty()) return publish(InvalidDefinition);
columnCount = rows.front().size();
rowCount = rows.size();
for (row : rows) {
    for (column) {
        const auto value = column == 0 ? string_view{ port.alphaName } : row[column];
        storage.cells.push_back({ value.data(), SV_StringTableHash(value) });
    }
}
```

**三个要点**：

```text
1. 表是【内建的】（SV_AlphaBarrettModelTable()），不从资产读
2. 列 0 被【替换】成 alphaName
3. 每格都算哈希（SV_StringTableHash）
```

### 8.2 `value.data()` 的生命周期

```cpp
const auto value = column == 0 ? std::string_view{ port.alphaName } : row[column];
storage.cells.push_back({ value.data(), SV_StringTableHash(value) });
```

**`value.data()` 指向 `port.alphaName`（永存）或 `row[column]`（`rows` 的生命周期？）**

**而 `rows` 是 `SV_AlphaBarrettModelTable()` 的返回值** —— 如果是 `const vector&`/span 则永存；如果是值则 `rows` 在 lambda 结束后销毁 ⇒ **悬垂**。

**`const auto rows = ...`（按值）⇒ 若返回的是 `std::vector<string_view>`，`rows` 在作用域结束时销毁，而 `storage.cells` 里的 `data()` 指向的字符串本身（string_view 指向的）可能仍在静态存储。**

**这是一个需要看 `SV_AlphaBarrettModelTable` 签名才能确定的地方。**

### 8.3 source-table（普通情形）

```cpp
columnCount = source->columnCount;
rowCount = source->rowCount;
storage.cells.assign(source->values, source->values + columnCount * rowCount);

std::size_t patchedRows{};
for (rowIndex...) {
    auto &cell = storage.cells[rowIndex * columnCount];        // ← 只看第 0 列
    const auto value = readStringTableCell(cell);
    if (!value) { storage.cells.clear(); return publish(InvalidDefinition); }
    if (*value == port.sourceName) {
        cell.value = port.alphaName;
        cell.hash = SV_StringTableHash(port.alphaName);
        ++patchedRows;
    }
}
if (!patchedRows) { storage.cells.clear(); return publish(InvalidDefinition); }
```

### 8.4 **只替换第 0 列里等于 `sourceName` 的格**

**而 `patchedRows == 0` 就整个失败** —— 因为"如果一行都没改名，那这张表就不是我们想要的那张"。

**这是一个"必须至少命中一次"的判据** —— 与 §236 里"反查得到同一个号"、§245 里"所有 index 都必须匹配"同一族。

### 8.5 `cell.value` 与 `cell.hash` **同时**改

```cpp
cell.value = port.alphaName;
cell.hash = SV_StringTableHash(port.alphaName);
```

**两项必须同时更新** —— 因为表查找可能走哈希也可能走字符串，只改一个会导致不一致。

**这与 §143 里"XAsset hash table 28-byte stride"的记录是同类关切**（哈希与值的同步）。

### 8.6 `storage.cells.clear()` 的三处

```text
1. 某行的第 0 列读不出
2. patchedRows == 0
```

**两处（不是三处）** —— 而都在返回 `InvalidDefinition` 之前。

**目的**：让下次进入时 `storage.cells.empty()` 为真 ⇒ 重新填充 ⇒ **幂等重试**。

**这是一个"失败即复位"的设计** —— 与 §245 里 `built = true` 在失败前（永不重试）**相反**。

## 九、`std::copy_n(targetPath.data(), targetLength + 1, storage.path.data())`

```cpp
std::copy_n(targetPath.data(), targetLength + 1, storage.path.data());
```

### 9.1 `+1` 是拷 NUL

**而前面已经在检查 `targetLength < targetPath.size()`** ✓

**但 `storage.path` 是 96 字节，而 `targetPath` 也是 96** ⇒ 最多拷 96 字节 ✓

### 9.2 `header` 的三个指针

```cpp
storage.header = { storage.path.data(), columnCount, rowCount, storage.cells.data() };
```

**四个字段**：name / columnCount / rowCount / values。

**而 `StringTable` 的字段顺序由此确定** ✓（与 §143 里 `StringTable` 的结构一致）

## 十、链接后的**二次验证**

```cpp
void *linkedHeader = &storage.header;
void *entry{};
if (!tryLinkXAssetEntry(dbLinkXAssetEntry_, StringTableAssetType(37), &linkedHeader, entry, fault)
    || !entry || !linkedHeader) { ...LinkFailed... }

const auto *const target = readStringTable(..., targetPath.data(), 4);
const auto row = target ? findStringTableRow(*target, port.alphaName) : nullopt;
if (!target || !row || !*row) { ...LinkFailed... }
return Ready;
```

### 10.1 三层验证

```text
1. 链接调用不 fault 且返回 entry 非空 且 linkedHeader 非空
2. 【重新按名查表】能查到
3. 【按 alphaName 找行】能找到且非空
```

**第 2、3 项是"发布后从引擎的角度再读一遍"** —— 与 §242 里"双向验证"、§245 里"final verify"同一手法。

### 10.2 `&linkedHeader` 传给引擎

```cpp
void *linkedHeader = &storage.header;
tryLinkXAssetEntry(..., &linkedHeader, entry, fault)
```

**传的是 `&linkedHeader`** —— 所以引擎**可能替换** `linkedHeader` 的值（到它自己管理的内存）。

**而后面验证的是 `!linkedHeader`** —— 所以引擎返回的新指针必须非空。

**但 `storage.header` 的**内容**仍指向 `storage.path` 与 `storage.cells`** —— 如果引擎拷贝了整个 `StringTable` 结构，那 `storage` 的数据仍被引用。

**这是一个"引擎可能接管或可能拷贝"的不确定点。**

### 10.3 验证失败也用 `LinkFailed`

**三种不同的失败（链接 fault、表查不到、行找不到）都返回 `LinkFailed`（终态）。**

**而日志区分了 `lookup=present/missing` 与 `row=present/missing`** ✓ 所以细节不丢。

### 10.4 `AlphaWeaponPortStatus::LinkFailed` 是终态

**所以一次链接失败会永久锁死这个 port。**

## 十一、`PublishedBarrett*` 四组结构

```text
PublishedBarrettImage      name + loadDef(16) + header(GfxImage 尺寸) + linked
PublishedBarrettMaterial   name + textures(vector<12>) + constants + stateBits + header + linked
PublishedBarrettSurfs      name + header(48) + linked
PublishedBarrettModel      name + boneNames + parentList + quaternions + translations
                                  + partClassification + baseMatrices + materials
```

### 11.1 与 §143 的**尺寸对照**

**§143 学到**：

```text
GfxImage      52 B
XModel        360 B
XAnimParts    88 B
Material      104 B
```

**而这里 `AlphaBarrettOlfinalGfxImageSize` 与 `AlphaBarrettOlfinalMaterialSize` 是命名常量** —— 所以尺寸来自常量而不是字面量 52/104。

**注释里的 "Olfinal" 说明这是 OLfinal 特有尺寸** —— 与 §143 的"IW4X 尺寸"可能不同。

### 11.2 `textures` 是 `vector<array<byte,12>>`

**12 字节一个纹理引用** —— 而材质有最多 8 个纹理槽？⇒ 12 字节可能是 `{name pointer, sampler state}`。

**这是一个待核对的尺寸。**

### 11.3 每个结构都有 `void *linked`

**`linked` 记录引擎返回的指针** —— 与 `linkedHeader` 同族。

**所以"发布"的统一形状是**：

```cpp
struct PublishedX { ...自己的存储...; void *linked; };
```

**引擎拿到的指针记在 `linked` 里，而存储永不移动。**

## 十二、关键结论

1. **`size == 1 && value[0] == '1'`** 与 **`> 1`** 是同一个 API 的两种用法，而第二个会接受 `=on`/`=1x`。
2. **`markAlphaBaseWeapon` 在客户端恒真且不写入** —— 因为运行期 alpha 名字不在客户端的常量 configstring 表里，type 19 会让 `CL_GetConfigString` 返回 null 而 `sub_59B560` 解引用崩。
3. **客户端走"保留动态标签 + 返回空串占位"的路**。
4. **"绑定不全"被判为 `InvalidDefinition`（终态）** —— 与三终态叠加 ⇒ 时序问题变永久失败。
5. **`Ready` 每次进入都要重新验证全部 port** —— 因为新地图代际会重建注册表、索引消失、资产仍在。
6. **`SourceAssetMissing` 在开了 converted 开关时可恢复**，否则终态。
7. **`XAsset` 池是 120,000 × 28 的线性扫描**（无哈希），偏移 `+0/+8/+16`。
8. **`publishedModelTables` 必须常驻** —— 引擎持有 `storage.path.data()`/`cells.data()`。
9. **模型表改名的两条路：converted 内建表（列 0 换名）与 source-table（第 0 列按 `sourceName` 匹配）**。
10. **`cell.value` 与 `cell.hash` 必须同时改**。
11. **"至少命中一次"（`patchedRows != 0`）是表正确性的判据**。
12. **失败时 `storage.cells.clear()` ⇒ 下次重新填充 ⇒ 幂等重试**（与 §245 的 `built=true` 相反）。

## 十三、未闭合点

- `SV_AlphaBarrettModelTable()` 的返回类型（值 vs 引用）决定 `value.data()` 是否悬垂。
- `tryLinkXAssetEntry` 是否可能让引擎**拷贝** `StringTable` 结构（若是，`storage` 的数据不再被引用）。
- `PublishedBarrettMaterial::textures` 的 12 字节布局。
- `AlphaBarrettOlfinalGfxImageSize`/`MaterialSize` 的具体值（与 §143 的 52/104 是否相同）。
- `EngineBindings.cpp` 12050 行之后未读取。
