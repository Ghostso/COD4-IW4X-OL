# 学习报告 115（重开）— `MarketplaceService.cpp` 后半（659–1,176 行）

**学习范围**：`backend\Demonware\MarketplaceService.cpp` 第 659–1,176 行
**性质**：全实测（**`MarketplaceService.cpp` 1,176 行全文完成**）
**★★★★★ 本报告收录五个重大发现**：①**`Inventory.json` 的 6 字段与两条"永久"哨兵** ②**`ensureEntitlements` 的自动补种机制** ③**`loadSkuGrants` 的三重缓存键** ④**`applyPurchase` 的过期时间合并算法** ⑤**甲方指令"全解锁客户端不该被拦"**

---

## 一、★★★★★ **`Inventory.json` 的 6 字段与两条"永久"哨兵**

### 1.1 ★★★★★ 物品的完整字段（第 841–848 行）

```cpp
document["items"].push_back({
    { "id", itemId },
    { "quantity", 1 },
    { "expireDateTime", **PermanentExpiration** },
    { "expiryDuration", **PermanentDuration** },
    { "modifiedTime", **PermanentExpiration** },
    { "customSourceType", 0 },
});
```

### ★★★★★ 六个字段

| 字段 | 类型 | 说明 |
|---|---|---|
| **`id`** | u32 | ★ 物品 ID |
| **`quantity`** | u32 | 数量 |
| **`expireDateTime`** | u32 | ★ 过期时间（Unix 秒） |
| **`expiryDuration`** | i64 | ★ 过期时长 |
| **`modifiedTime`** | u32 | 修改时间 |
| **`customSourceType`** | u8 | 来源类型 |

### ★★★★★ 两条"永久"哨兵（第 827–828 行）

```cpp
constexpr auto PermanentExpiration = (std::numeric_limits<std::uint32_t>::max)();   // **0xFFFFFFFF**
constexpr auto PermanentDuration   = (std::numeric_limits<std::int64_t>::max)();    // **0x7FFFFFFFFFFFFFFF**
```

★★★★★ **⇒ 两个精确的哨兵值：**
```
**`PermanentExpiration` = `UINT32_MAX` = `0xFFFFFFFF` = 4,294,967,295**
**`PermanentDuration`   = `INT64_MAX`  = `0x7FFFFFFFFFFFFFFF`**
        ↓
★★★ ⇒ 与报告 078 的 `end_time = 2147483647`（`INT32_MAX`）、
   报告 103 的 `0x7FFFFFFF`（`INT32_MAX`）**同一族"永不过期"手法**
   ⇒ 但这里用的是 **`UINT32_MAX`** 与 **`INT64_MAX`**
```

### ★★★★★ 过期判定（第 799–802 行）

```cpp
const auto entitled = item != inventory.end() &&
    (item->expireDateTime == **(std::numeric_limits<std::uint32_t>::max)()** ||
     item->expireDateTime > now);
```

★★★ **⇒ 两条：**
```
① ★ **`expireDateTime == UINT32_MAX`** ⇒ **永久有效**
② `expireDateTime > now` ⇒ 未过期
```

### ★★★ `loadInventory` 的严格校验（第 692–765 行）

```cpp
if (!id || *id == 0 || *id > UINT32_MAX) continue;                    // ① id 非零
if (entry.contains("quantity")) {
    if (!quantity || *quantity == 0 || *quantity > UINT32_MAX) continue;  // ② quantity 非零
}
if (entry.contains("customSourceType")) {
    if (!source || *source > UINT8_MAX) continue;                     // ③ ≤ u8
}
if (entry.contains("expireDateTime")) {
    if (!expiration || *expiration > UINT32_MAX) continue;            // ④ ≤ u32
}
if (entry.contains("expiryDuration")) {
    const auto maximumDuration = static_cast<std::uint64_t>(INT64_MAX);
    if (*duration > maximumDuration) {
        if (item.expireDateTime != UINT32_MAX) continue;               // ★★ 超 INT64_MAX 时
        item.expiryDuration = INT64_MAX;                               //    必须 expireDateTime == UINT32_MAX
    }
}
if (entry.contains("modifiedTime")) {
    if (!modified || *modified > UINT32_MAX) continue;                // ⑤ ≤ u32
}
// 去重：同 id 只保留第一个
```

★★★ **⇒ 第 ④ 条是关键（逐字）：**
```
`expiryDuration > INT64_MAX`
        ↓
★★★ 若 `expireDateTime != UINT32_MAX` ⇒ **丢弃**
   ⇒ 即：**只有"永久"物品才允许超长时长**
```

★ **⇒ 这是一个**字段间的交叉约束**（`expiryDuration` 的合法性依赖 `expireDateTime`）。**

### ★★★ 去重（第 757–762 行）

```cpp
const auto duplicate = std::find_if(result.begin(), result.end(), [item](const InventoryItem &existing)
{
    return existing.id == item.id;
});
if (duplicate == result.end())
    result.push_back(item);
```

★★ **⇒ **同 id 只保留第一个**（不是合并数量）。**

---

## 二、★★★★★ **`ensureEntitlements` 的自动补种机制**

### 2.1 ★★★★★ 完整实现（第 878–897 行）

```cpp
bool MarketplaceService::ensureEntitlements(
    const std::uint64_t userId, const std::span<const std::uint32_t> itemIds) const
{
    if (!userId) return false;
    const auto missing = missingEntitlements(userId, itemIds);
    if (missing.empty()) return true;
    // ★ 2026-10-07 18:1x -- 甲方指令：客户端是全解锁的，它装得上的任何件都不该
    //   被 booking 拦下。缺件先按"定制形状"补进库存再复检；只有补写失败或补后
    //   仍不过（理论不可能）才走 entitlement_rejected。
    AlwaysofflineRe::log("Marketplace: booking references " +
        std::to_string(missing.size()) +
        " item(s) absent from the inventory; **auto-seeding and continuing** (user " +
        std::to_string(userId) + ").");
    if (!seedInventoryItems(userId, missing))
        return false;
    return missingEntitlements(userId, itemIds).empty();
}
```

### ★★★★★ 完整的自动补种流程

```
① `missingEntitlements(userId, itemIds)` ⇒ 找出缺件
        ↓
② 若为空 ⇒ **直接通过**
        ↓
③ ★★★ 否则 **`seedInventoryItems(userId, missing)`** ⇒ **补进库存**
        ↓
④ **再复检** `missingEntitlements(...).empty()`
        ↓
★★★★★ ⇒ 只有**补写失败或补后仍不过**（"理论不可能"）才走 `entitlement_rejected`
```

★★★ **⇒ 甲方指令（逐字）：**
```
"**客户端是全解锁的，它装得上的任何件都不该被 booking 拦下**"
        ↓
★★★ ⇒ 所以缺件**不是拒绝,而是自动补齐**
```

★ **⇒ 这与报告 114 的 `OLMOD_UNLOCK_ALL=1` 是**两个不同的机制**：**
```
`OLMOD_UNLOCK_ALL` ⇒ **改所有权判断**（`sub_5E3760` 的谓词）
`ensureEntitlements` ⇒ **改库存数据**（自动补种）
        ↓
★★★ ⇒ 两条路都能让"客户端认为有",但机制不同
```

### ★★★ `missingEntitlements` 的两条跳过（第 791–794 行）

```cpp
for (const auto itemId : itemIds)
{
    if (!itemId || **isDefaultEntitlement(itemId)**)
        continue;
    ...
}
```

★★★ **⇒ 两条跳过：**
```
① `itemId == 0` ⇒ 跳过
② ★★ **`isDefaultEntitlement(itemId)`** ⇒ 跳过（**43 个默认权益**）
        ↓
★★★ ⇒ 即：**43 个默认权益永远不算"缺失"**（它们由 `CODOL_DefaultAvailableItems_Init` 提供）
```

### ★★★ `seedInventoryItems` 的"拉直"逻辑（第 851–860 行）

```cpp
// 已存在但不满足判据（过期/零量）⇒ 拉直为永久有效。
const auto oldQuantity = existing->contains("quantity")
    ? jsonUnsigned((*existing)["quantity"]).value_or(0) : 0;
(*existing)["quantity"] = oldQuantity == 0 ? 1 : oldQuantity;      // ★ 零量 ⇒ 1
(*existing)["expireDateTime"] = PermanentExpiration;               // ★ 拉直为永久
(*existing)["expiryDuration"] = PermanentDuration;
(*existing)["modifiedTime"] = PermanentExpiration;
if (!existing->contains("customSourceType"))
    (*existing)["customSourceType"] = 0;
```

★★★ **⇒ 三条"拉直"：**
```
① `quantity == 0` ⇒ 改成 **1**
② `expireDateTime` ⇒ **`UINT32_MAX`**（永久）
③ `expiryDuration` ⇒ **`INT64_MAX`**
        ↓
★★★ ⇒ 即：**已存在但过期/零量的物品会被"拉直"为永久有效**
```

★ **⇒ 这是**"不删不重建,只修正"的做法**（保留原 id）。**

### ★★★ 写入用 CRLF（第 863 行）

```cpp
if (!replaceJson(path, document, /*crlf*/ **true**))
```

★★ **⇒ `Inventory.json` 用 **CRLF** 换行（与报告 077 的 `configs_s.info` 同）。**

---

## 三、★★★★★ **`loadSkuGrants` 的三重缓存键**

### 3.1 ★★★★★ 缓存判断（第 911–916 行）

```cpp
const std::scoped_lock cacheLock(skuGrantsMutex_);
if (skuGrantsCache_ && skuGrantsCachePath_ == path &&
    skuGrantsCacheSize_ == fileSize && skuGrantsCacheWriteTime_ == writeTime)
{
    return skuGrantsCache_;
}
```

### ★★★★★ 三个缓存键

| # | 键 | 说明 |
|---|---|---|
| **1** | **`skuGrantsCachePath_ == path`** | ★ 路径 |
| **2** | **`skuGrantsCacheSize_ == fileSize`** | ★★ **文件大小** |
| **3** | **`skuGrantsCacheWriteTime_ == writeTime`** | ★★ **最后修改时间** |

★★★ **⇒ 三重键 ⇒ 文件改动即失效（无需重启）。**

★★ **⇒ 而 `MarketplaceSkus.json` 是 **2.5 MB**（报告 089）⇒ 缓存很有必要。**

### ★★★ 三个来源（第 904–909 行）

```cpp
const auto fileSize = std::filesystem::file_size(path, error);
const auto writeTime = std::filesystem::last_write_time(path, error);
```

★ **⇒ 用 `file_size` + `last_write_time`（不是哈希）⇒ **廉价但足够**。**

### ★★★ `durationDays` → 秒的转换（第 955–968 行）

```cpp
const auto durationSeconds = [](const nlohmann::json &value, const std::uint32_t fallback)
    -> std::optional<std::uint32_t>
{
    if (!value.contains("durationDays")) return fallback;
    const auto days = jsonUnsigned(value["durationDays"]);
    constexpr auto SecondsPerDay = std::uint64_t{ **24 * 60 * 60** };   // = 86,400
    if (!days || *days > UINT32_MAX / SecondsPerDay) return std::nullopt;
    return static_cast<std::uint32_t>(*days * SecondsPerDay);
};
```

★★ **⇒ `durationDays × 86,400` ⇒ 秒（带溢出检查）。**

★★ **⇒ 与报告 089 的 `durationDays` 的 12 档（1/2/3/5/7/10/14/15/30/40/60/90）**对应** ✓**

### ★★★ 两级 grant 回退（第 1010–1047 行）

```cpp
SkuGrant grant{ .sku = static_cast<std::uint32_t>(*sku) };
const nlohmann::json *grantSource = &entry;
if (!entry.contains("grants") && entry.contains("productId"))
{
    const auto productId = jsonUnsigned(entry["productId"]);
    ...
    const auto product = products.find(static_cast<std::uint32_t>(*productId));
    if (product == products.end()) continue;
    grantSource = product->second;                       // ★ 回退到 products[]
}
if (grantSource->contains("grants")) { ...多 grant... }
else if (const auto item = parseItem(entry)) grant.items.push_back(*item);   // ★ 单 grant
else continue;
```

★★★★★ **⇒ 完整的回退链：**
```
① sku 自身有 `grants` ⇒ 用它
        ↓
② 否则若有 `productId` ⇒ **查 `products[]`** 拿 `grants`
        ↓
③ 若 grantSource 有 `grants` ⇒ **多个 grant**
④ 否则 ⇒ **`parseItem(entry)`**（**单个 grant**,直接读 sku 条目自身）
        ↓
★★★ ⇒ 三级：**sku.grants** → **product.grants** → **sku 自身即 item**
```

★★ **⇒ 与报告 089 的 `MarketplaceSkus.json` 的 `skus` / `products` 两表**完全对应** ✓**

### ★★★ SKU 去重（第 1049–1050 行）

```cpp
if (seenSkus.insert(grant.sku).second)
    result.push_back(grant);
```

★★ **⇒ 用 `unordered_set` 去重（**同 sku 只保留第一个**）。**

---

## 四、★★★★★ **`applyPurchase` 的过期时间合并算法**

### 4.1 ★★★★★ 新物品的过期时间（第 1092–1100 行）

```cpp
if (itemGrant.durationSeconds != 0)
{
    const auto totalDuration = std::uint64_t{ itemGrant.durationSeconds } * quantities[index];
    if (totalDuration > UINT32_MAX - now) return false;
    item.expireDateTime = **now + totalDuration**;
    item.expiryDuration = static_cast<std::int64_t>(totalDuration);
    item.modifiedTime = now;
}
```

★★★ **⇒ 新物品：`expireDateTime = now + (durationSeconds × quantity)`。**

### ★★★★★ 已存在物品的**四种合并情况**（第 1141–1161 行）

```cpp
constexpr auto PermanentExpiration = UINT32_MAX;
constexpr auto PermanentDuration   = INT64_MAX;
const auto oldExpiration = existing->contains("expireDateTime")
    ? jsonUnsigned((*existing)["expireDateTime"]).value_or(PermanentExpiration)
    : PermanentExpiration;

if (addition.expireDateTime == PermanentExpiration || oldExpiration == PermanentExpiration)
{
    // ★★ 情况 A：任一方是永久 ⇒ 结果永久
    (*existing)["expireDateTime"] = PermanentExpiration;
    (*existing)["expiryDuration"] = PermanentDuration;
}
else
{
    // ★★ 情况 B：两者都有限 ⇒ 从较晚者起算延长
    const auto base = std::max<std::uint64_t>(oldExpiration, now);
    const auto extension = static_cast<std::uint64_t>(addition.expiryDuration);
    if (base + extension > PermanentExpiration) return false;
    const auto expiration = base + extension;
    (*existing)["expireDateTime"] = expiration;
    (*existing)["expiryDuration"] = expiration - now;
}
(*existing)["modifiedTime"] = now;
```

### ★★★★★ 完整的合并规则

| 情况 | 条件 | 结果 |
|---|---|---|
| **A** | ★★ **任一方 `expireDateTime == UINT32_MAX`** | **永久**（`expireDateTime = UINT32_MAX`,`expiryDuration = INT64_MAX`） |
| **B** | 两者都有限 | ★★★ **`base = max(oldExpiration, now)`**,然后 **`expiration = base + extension`** |

★★★ **⇒ 情况 B 的三个精确步骤：**
```
① `base = max(oldExpiration, **now**)`
   ⇒ ★ 若已过期（`oldExpiration < now`）⇒ **从"现在"起算**（不是从过期时间）
        ↓
② `expiration = base + extension`
        ↓
③ `expiryDuration = expiration - now`
   ⇒ ★ 存的是**相对现在**的剩余时长
```

★★★★★ **⇒ 第 ① 条的 `max(oldExpiration, now)` 是一个**精确的语义选择**：**
```
续期一个**已过期**的物品 ⇒ 从**现在**起算（不是从过期点续）
        ↓
★★★ 否则会得到"续了但仍是过去"的荒谬结果
```

### ★★★ 数量累加（第 1133–1138 行）

```cpp
const auto oldQuantity = existing->contains("quantity")
    ? jsonUnsigned((*existing)["quantity"]).value_or(1) : 1;
if (oldQuantity > UINT32_MAX - addition.quantity) return false;      // ★ 溢出检查
(*existing)["quantity"] = oldQuantity + addition.quantity;
(*existing)["customSourceType"] = addition.customSourceType;
```

★★ **⇒ 数量**累加**（不是覆盖）,带溢出检查。**

### ★★★ `quantity` 与 `durationSeconds` 的乘法（第 1085–1091 行）

```cpp
if (quantities[index] > UINT32_MAX / itemGrant.item.quantity) return false;
auto item = itemGrant.item;
item.quantity *= quantities[index];
```

★★ **⇒ **购买数量 × 每件数量** ⇒ 总数量（带溢出检查）。**

---

## 五、★★★★★ **`replaceJson` 的原子写（与报告 106 一致）**

### 5.1 ★★★★★ 完整实现（第 168–211 行）

```cpp
bool replaceJson(const std::filesystem::path &path, const nlohmann::json &document,
    const bool crlf = false)
{
    std::error_code error;
    std::filesystem::create_directories(path.parent_path(), error);
    if (error) return false;

    auto temporary = path;
    temporary += L"**.writing**";                              // ★ 同后缀
    {
        std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
        auto text = document.dump(**2**) + '\n';               // ★ 2 空格缩进
        if (crlf)
        {
            std::string converted;
            converted.reserve(text.size() + text.size() / 8);
            for (const auto character : text)
            {
                if (character == '\n') converted += '\r';      // ★ LF → CRLF
                converted += character;
            }
            text.swap(converted);
        }
        stream << text;
        ...
    }
    if (!MoveFileExW(temporary.c_str(), path.c_str(),
        **MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH**))   // ★ 原子替换
    {
        std::filesystem::remove(temporary, error);
        return false;
    }
    return true;
}
```

★★★ **⇒ 与报告 106 的 `saveDisplayName` **完全相同的三要素**：**
```
① 临时后缀 **`.writing`**
② **`MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH`**
③ 失败删临时文件
        ↓
★★★ ⇒ **同一个原子写约定**（第三次出现,前两次是 106 与 096）
```

★ **⇒ 且 `dump(2)` ⇒ **2 空格缩进**（与报告 106 的 `saveDisplayName` 同）。**

### ★★★ `userIdDirectory` 的第二次出现（第 48–62 行）

```cpp
std::string userIdDirectory(const std::uint64_t userId)
{
    std::array<char, 16> buffer{};
    const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), userId, **16**);
    ...
    // 转大写
}
```

★★★ **⇒ 与报告 106 的 `IdentityConfig.cpp` 的 `userIdDirectory` **完全相同的实现**（十六进制 + 大写）。**

★ **⇒ 两个文件各有一份副本 ⇒ **代码重复**（可提取）。**

### ★★★ `inventoryPath`（第 1166–1174 行）

```cpp
return assetRoot_ / std::to_string(identity.titleId) / ownerDirectory / "**Inventory.json**";
```

★★ **⇒ 完整路径：`<assetRoot>/<titleId>/<USERID大写>/Inventory.json`**
**⇒ 与报告 106 的 `Identity.json` **同目录** ✓**

---

## 六、★★★★ **`getSkusPaginated` 的"逐元素读"理由**

### 6.1 ★★★★★ 完整注释（第 554–556 行）

```cpp
// Read element by element rather than through `readU32Array`: the client writes a **bare
// count followed by individually tagged values**, not a bd array (tag **0x6C**), so
// `readU32Array` would reject a request that is **perfectly well formed**.
```

★★★★★ **⇒ 一个精确的 API 选择理由：**
```
客户端写的是 **"裸 count + 逐个带标签的值"**
        ↓
★★★ **不是** bd array（tag **`0x6C`**）
        ↓
★★★ ⇒ **`readU32Array` 会拒绝一个完全合法的请求**
        ↓
⇒ 必须**逐元素读**（`for (index < skuIdCount) input.readU32(skuId)`)
```

★ **⇒ 这与报告 113 的"`message` 是裸字节不能用 `readU32`"**同一类 API 选择问题**（第二次出现）。**

### ★★★ 完整的请求解析（第 541–577 行）

```cpp
input.readString(context)
input.readU32(pageNumber)
input.readU32(itemsPerPage)
input.readBool(showAll)
input.readU32(skuIdCount)
for (index < skuIdCount) input.readU32(skuId)          // ★ 逐个读
input.readU32(skuTypeCount)
for (index < skuTypeCount) input.readU8(skuType)       // ★ u8 不是 u32
input.readString(storeVersion)
```

★★ **⇒ 7 段（含两个循环）。**
**⇒ 且 `skuType` 是 **`u8`**（不是 `u32`）⇒ 与报告 114 的 `80/70` 字节表 `08 00000000`（`numSkuTypes` 为 0）**一致**。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`Inventory.json` 六字段** | `id` / `quantity` / `expireDateTime` / `expiryDuration` / `modifiedTime` / `customSourceType` |
| 2 | ★★★★★ **两条"永久"哨兵** | **`PermanentExpiration = UINT32_MAX`（`0xFFFFFFFF`）** / **`PermanentDuration = INT64_MAX`（`0x7FFFFFFFFFFFFFFF`）** |
| 3 | ★★★ 过期判定 | `expireDateTime == UINT32_MAX` **或** `> now` |
| 4 | ★★★★ **交叉约束** | `expiryDuration > INT64_MAX` 时 **必须 `expireDateTime == UINT32_MAX`**,否则**丢弃** |
| 5 | ★★ 去重 | `loadInventory` **同 id 只保留第一个**（不合并数量） |
| 6 | ★★★★★ **`ensureEntitlements` 自动补种** | 缺件 ⇒ **`seedInventoryItems`** ⇒ **再复检**；只有补写失败或补后仍不过才拒 |
| 7 | ★★★★★ **甲方指令** | "**客户端是全解锁的，它装得上的任何件都不该被 booking 拦下**" |
| 8 | ★★★ 与 `OLMOD_UNLOCK_ALL` 的区别 | 前者**改库存数据**,后者**改所有权判断** |
| 9 | ★★★ 两条跳过 | `itemId == 0` / ★ **`isDefaultEntitlement`（43 个默认权益）** |
| 10 | ★★★★ **"拉直"逻辑** | 已存在但过期/零量 ⇒ `quantity` 0→**1**、`expireDateTime` → **`UINT32_MAX`**、`expiryDuration` → **`INT64_MAX`** |
| 11 | ★★ 换行 | `Inventory.json` 用 **CRLF** |
| 12 | ★★★★★ **`loadSkuGrants` 三重缓存键** | **路径** + **文件大小** + **最后修改时间** ⇒ 文件改动即失效 |
| 13 | ★★★ `durationDays` → 秒 | **`× 86,400`**（`24*60*60`），带溢出检查 |
| 14 | ★★★★★ **三级 grant 回退** | **`sku.grants`** → **`product.grants`**（查 `products[]`）→ **sku 自身即 item** |
| 15 | ★★ SKU 去重 | `unordered_set` ⇒ 同 sku 只保留第一个 |
| 16 | ★★★★ **新物品过期时间** | `expireDateTime = now + (durationSeconds × quantity)` |
| 17 | ★★★★★ **四种合并情况** | **A**：任一方 **`UINT32_MAX`** ⇒ 永久；**B**：`base = **max(oldExpiration, now)**`,然后 `expiration = base + extension` |
| 18 | ★★★★★ **`max(oldExpiration, now)` 的语义** | 续期**已过期**物品 ⇒ **从"现在"起算**（否则会得到"续了但仍是过去"） |
| 19 | ★★ 数量累加 | **累加**（不是覆盖）+ 溢出检查 |
| 20 | ★★★ **`replaceJson` 原子写** | 临时后缀 **`.writing`** + **`MOVEFILE_REPLACE_EXISTING \| MOVEFILE_WRITE_THROUGH`** + 失败删临时（**第三次出现**） |
| 21 | ★★ `dump(2)` | **2 空格缩进** |
| 22 | ★★★ `userIdDirectory` **第二次出现** | 与报告 106 的 `IdentityConfig.cpp` **完全相同的实现**（十六进制 + 大写）⇒ **代码重复** |
| 23 | ★★ `inventoryPath` | `<assetRoot>/<titleId>/<USERID大写>/**Inventory.json**` ⇒ 与 `Identity.json` **同目录** |
| 24 | ★★★★★ **"逐元素读"的理由** | 客户端写 **"裸 count + 逐个带标签值"**,**不是** bd array（tag **`0x6C`**）⇒ **`readU32Array` 会拒绝合法请求** |
| 25 | ★★ `skuType` 是 `u8` | 不是 `u32` ⇒ 与报告 114 的 `80/70` 字节表一致 |

---

## 八、结论

### 1. ★★★★★ **`Inventory.json` 用两条"永久"哨兵（`UINT32_MAX` / `INT64_MAX`）**

★ **⇒ 且 `expiryDuration` 有**交叉约束**（超长时 `expireDateTime` 必须为 `UINT32_MAX`）。**

### 2. ★★★★★ **`ensureEntitlements` 是"自动补种"而不是"拒绝"**

```
甲方指令："客户端是全解锁的,它装得上的任何件都不该被 booking 拦下"
        ↓
★★★ 缺件 ⇒ **补进库存** ⇒ **再复检**
```

### 3. ★★★★★ **`applyPurchase` 的 `max(oldExpiration, now)` 是一个精确的语义选择**

★ **⇒ 续期**已过期**物品时从"现在"起算,而不是从过期点续。**

### 4. ★★★★ **`loadSkuGrants` 的三重缓存键**（路径 + 大小 + 修改时间）

### 5. ★★★★★ **三级 grant 回退**（`sku.grants` → `product.grants` → sku 自身）

### 6. ★★★★ **`readU32Array` 会拒绝合法请求**（客户端不用 bd array 的 `0x6C`）

### 7. ★★★ **`replaceJson` 的原子写是第三次出现**（`.writing` + `MOVEFILE_WRITE_THROUGH`）

---

## 九、下一步

- `MarketplaceService.hpp`（87 行）
- `StatsService`（875 行）/ `LobbyProtocol`（807 行）/ `Profiles2Service`（630 行）
- `ClanService`（623 行）/ `Storage2Service`（450 行）/ `Friends2Service`（325 行）
- `ContentUnlock2Service` / `TencentService` / `TitleUtilitiesService`
- `SharedRoom*` / `Servers.cpp`（624 行）
