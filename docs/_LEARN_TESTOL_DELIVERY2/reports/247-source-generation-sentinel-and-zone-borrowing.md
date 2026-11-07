# 247 · 资产"代际哨兵"、`cheytac_mp` 的 zone 借用、材质路由兼容性的五项检查

## 一、范围

本报告学习 `EngineBindings.cpp` 12050–12450 行。

## 二、三组尺寸常量

```cpp
struct PublishedBarrettModel  { ... std::array<std::byte, 360> header{}; ... };
struct PublishedBarrettAnimation { ... std::array<std::byte, 88> header{}; ... };
```

**`360` = XModel 尺寸、`88` = XAnimParts 尺寸** —— 与 §143 学到的 `XModel 360 B` / `XAnimParts 88 B` **完全一致** ✓

**而 `AlphaBarrettOlfinalGfxImageSize` / `AlphaBarrettOlfinalMaterialSize` 是命名常量** —— 说明这两个在 OLfinal 上**与 IW4X 不同**。

## 三、动画的**十个数据流**

```cpp
std::vector<std::uint16_t> boneNames;
std::vector<std::byte> notify;
std::vector<std::byte> dataByte;
std::vector<std::byte> dataShort;
std::vector<std::byte> dataInt;
std::vector<std::byte> randomDataShort;
std::vector<std::byte> randomDataByte;
std::vector<std::byte> randomDataInt;
std::vector<std::byte> indices;
std::array<std::byte, 1> emptyStreamSentinel{};
```

### 3.1 九个流 + **一个哨兵**

```text
boneNames           uint16 表
notify              通知
dataByte/Short/Int  普通数据（三种宽度）
randomDataByte/Short/Int  随机数据（三种宽度）
indices             索引
```

**"六个数据流"是 XAnimParts 的标准布局（`dataByte`/`dataShort`/`dataInt`/`randomDataShort`/`randomDataByte`/`randomDataInt`）** ✓ 与 IW4X 一致。

### 3.2 `emptyStreamSentinel` 是**1 字节**

```cpp
std::array<std::byte, 1> emptyStreamSentinel{};
```

**为什么需要**：如果某个流是空的，`vector::data()` 可能返回 `nullptr`，而引擎可能**不检查 nullptr 直接读**。

**所以给一个 1 字节的非空指针** —— 这是"零长度流也要有合法指针"的防御。

**这是一个值得记的手法** —— 与 §235 的 `INT32_MIN` 哨兵、§242 的 `addressable` 哨兵同族但目的不同（那是"不可能的值"，这是"合法的空"）。

## 四、`PublishedBarrettAssets` 的**五个 `unique_ptr` 向量**

```cpp
struct PublishedBarrettAssets
{
    bool attempted{};
    bool ready{};
    std::vector<std::unique_ptr<PublishedBarrettImage>> images;
    std::vector<std::unique_ptr<PublishedBarrettMaterial>> materials;
    std::vector<std::unique_ptr<PublishedBarrettSurfs>> surfs;
    std::vector<std::unique_ptr<PublishedBarrettModel>> models;
    std::vector<std::unique_ptr<PublishedBarrettAnimation>> animations;
};
static PublishedBarrettAssets publishedBarrettAssets;
```

### 4.1 为什么用 `unique_ptr`

**因为结构里有 `std::array<byte, N> header` 且引擎持有它的地址** —— 如果 `vector<PublishedX>` 扩容会让所有 `header` 地址失效 ⇒ **引擎的指针悬垂**。

**`unique_ptr` ⇒ 每个对象独立分配、地址稳定** ✓

**这与 §246 里 `publishedModelTables` 用 `std::vector<PublishedModelTable>`（值）不同** —— 那里**没有 `header` 被外部持有**（`storage.header` 是结构自己的成员，而 `linkedHeader = &storage.header` 传出去……）。

**实际上 §246 的 `&storage.header` 也被传出去 ⇒ 同样有扩容失效风险。**

**这是一处不一致** —— 值得指出。

### 4.2 `attempted` 与 `ready` 两个标志

```text
attempted   已经尝试过一次（无论成败）
ready       成功完成
```

**`attempted` 在尝试**之前**置 true** ⇒ 失败后**永不重试**（除非代际过期重置）。

## 五、**代际哨兵**（本组最重要的一段）

```cpp
// common_mp is loaded once for the front end and again for the booked map.
// The engine removes every runtime-linked entry owned by the old generation
// during that transition, while this process-local cache naturally survives.
// Use the private base model as the generation sentinel and rebuild the closure
// from the immutable metadata when it disappears. At that point every private
// entry from the same zone has already been unlinked, so releasing its old
// backing storage is safe.
if (barrettMetadataEnabled && publishedBarrettAssets.ready &&
    !findXAsset(XModelAssetType, "viewmodel_barrett", false).data)
{
    publishedBarrettAssets = {};
    write("alpha Barrett asset generation expired; rebuilding closure");
}
```

### 5.1 四层因果

```text
1. common_mp 载入两次：前端一次、预定地图一次
2. 引擎在切换时【移除旧代际的全部运行期链接条目】
3. 而本进程的缓存【自然存活】
4. ⇒ 用私有基础模型 "viewmodel_barrett" 作【代际哨兵】
```

### 5.2 为什么可以安全释放

**"在那一点上，来自同一个 zone 的每一个私有条目都已经被 unlink 了，所以释放它旧的支撑存储是安全的。"**

**这是一个"引擎先清、我们后清"的顺序论证** —— 而不是引用计数。

### 5.3 哨兵的选择

**`"viewmodel_barrett"` 被称作 "the private base model"** —— 而查询用 `findXAsset(XModelAssetType(4), name, false)`。

**`false` = 不允许默认值** —— 所以这是严格查询（§235 的 `findXAsset` 第二问）✓

### 5.4 `publishedBarrettAssets = {}` 的**整体重置**

**包括 `attempted = false`** ⇒ 下次会重新尝试 ✓

**但注意 `unique_ptr` 的析构会释放全部存储** —— 而引擎可能仍持有指针。

**论证是"引擎已经 unlink 了全部"** —— 而这个论证依赖"代际切换会清空同 zone 的全部条目"。

**这是一处**强依赖**：如果引擎漏清一个，我们释放的就是引擎仍在用的内存。**

## 六、`SV_LoadAlphaBarrettBundle` 的**七项失败出口**

```cpp
std::string loadError;
const auto bundle = SV_LoadAlphaBarrettBundle(std::filesystem::path(barrettMetadataPath.data()), loadError);
if (!bundle) return failBarrettAssets(InvalidDefinition, loadError);
```

### 6.1 `OLMOD_ALPHA_BARRETT_METADATA` 的**两次读取**

```cpp
// 第一次（上面用过）
const auto convertedBarrettEnabled = GetEnvironmentVariableA("OLMOD_ALPHA_BARRETT_METADATA", nullptr, 0) > 1;

// 第二次
std::array<char, 32768> barrettMetadataPath{};
const auto barrettMetadataLength = GetEnvironmentVariableA(..., barrettMetadataPath.data(), 32768);
const auto barrettMetadataEnabled =
    barrettMetadataLength > 0 && barrettMetadataLength < barrettMetadataPath.size();
```

### 6.2 **两次判据不同**

```text
第一次  > 1                    （长度至少 2）
第二次  > 0 且 < 32768          （长度至少 1，且未溢出）
```

**所以值恰好是 1 个字符时**：

```text
convertedBarrettEnabled = false   （> 1 不成立）
barrettMetadataEnabled  = true    （> 0 成立）
```

**这是两个不同的"启用"含义** —— 名字相似但语义不同，**且都在同一个函数里**。

**`convertedBarrettEnabled` 控制"是否把 `SourceAssetMissing` 当可恢复"，而 `barrettMetadataEnabled` 控制"是否发布 Barrett 资产"。**

**所以 `X`（一个字符）⇒ 会尝试发布，但不会把缺失当可恢复。**

### 6.3 `< 32768` 的溢出检查

**`GetEnvironmentVariableA` 在缓冲区不足时返回**所需长度**（不含 NUL）并**不写入**。

**所以 `length >= 32768` ⇒ 截断/未写入 ⇒ 拒绝 ✓**

## 七、**四处前缀守卫**

### 7.1 `GfxImageInitializeRva`

```cpp
constexpr std::size_t GfxImageInitializeRva = 0x7E7470;
constexpr std::array<std::uint8_t, 7> GfxImageInitializePrefix{ 0x8B, 0x44, 0x24, 0x04, 0x83, 0xEC, 0x20 };
```

```asm
8B 44 24 04    mov eax, [esp+4]      ; ← 第一个参数
83 EC 20       sub esp, 20h
```

**这是 `__stdcall`/`__cdecl` 的函数入口（`[esp+4]` 读第一个参数）** —— 与 §164 里 `BG_PlayerStateToEntityState` 的参数位置问题相关。

### 7.2 `exactPrefix` lambda（两处）

```cpp
const auto exactPrefix = [this](std::size_t rva, std::initializer_list<uint8_t> expected) {
    return readableSpan(module_ + rva, expected.size()) &&
        std::equal(expected.begin(), expected.end(), module_ + rva);
};
```

```text
ScriptStringInternRva  = 0x34BD10   { 55, 8B, EC, 83, EC, 14 }
XModelStreamQueueRva   = 0x09A2B0   { 55, 8B, EC, A1 }
```

### 7.3 反汇编

```asm
55            push ebp
8B EC         mov ebp, esp
83 EC 14      sub esp, 14h
```

```asm
55            push ebp
8B EC         mov ebp, esp
A1            mov eax, [imm32]        ; ← 读一个全局
```

**`A1` 是 `mov eax, moffs32`** ⇒ 这个函数一开头就读一个全局地址。**所以它至少 8 字节（`55 8B EC A1` + 4 字节地址）。**

### 7.4 前缀守卫的**局限**（§192–213 已学）

**"前缀守卫不能区分两个已存在的函数"** —— 这里 4-7 字节的前缀确实很弱。

**但它抓的是"这个 RVA 上是不是我以为的那个函数"** —— 对于"RVA 完全错"能抓，对"RVA 是另一个同前缀函数"不能抓。

## 八、**借用 `cheytac_mp` 的 zone**（本组第二重要）

```cpp
// Runtime links otherwise inherit loading zone 0 and are swept as
// defaults during the following map transition. All converted
// dependencies use stable ol-mod storage, so give them the same
// resident lifetime as the retained CheyTac WeaponDef clone.
const auto retainedBarrettOwner = findXAsset(WeaponAssetType(28), "cheytac_mp", false).data;
const auto retainedBarrettZone = retainedBarrettOwner
    ? assetZoneForHeader(WeaponAssetType, retainedBarrettOwner)
    : std::optional<std::uint8_t>{};
if (!retainedBarrettZone)
    return failBarrettAssets(SourceAssetMissing, "retained CheyTac WeaponDef source zone is missing");
```

### 8.1 问题

```text
运行期 link 的条目【继承 loading zone 0】
⇒ 在下一次地图切换时【被当作默认值扫掉】
```

### 8.2 解法

**把每个新条目显式设成 `cheytac_mp` 的 zone** —— 因为 CheyTac 是"retained"（保留下来的）克隆，它的 zone 有正确的生存期。

### 8.3 而 `cheytac_mp` 是**另一个 alpha 武器**

**与 §246 里 `SV_AlphaWeaponPorts()` 的谱系（`ConvertedPresentation` = Barrett）** 相关 —— CheyTac 是同一个"保留克隆"机制的另一例。

**所以这是"同一个机制的两个实例，一个借另一个的 zone"**。

### 8.4 `assetZoneForHeader` 的 120,000 次扫描在这里只调一次

**而 §246 说它是线性扫描** —— 所以这里付一次 120,000 × 28 字节的代价。

**可以接受（一次性），但如果调用多次就会很贵。**

## 九、`address32` 与 32 位地址空间

```cpp
const auto address32 = [](const void *pointer) -> optional<uint32> {
    const auto value = (uintptr_t)pointer;
    if (!value || value > numeric_limits<uint32>::max()) return nullopt;
    return (uint32)value;
};
```

### 9.1 三项

```text
非空
<= 0xFFFFFFFF
```

### 9.2 为什么需要

**引擎的结构里存的是 **32 位指针**（`uint32`）** —— 而本项目是 32 位进程（`module_` 加 RVA），所以地址能塞进 32 位。

**但 `> max` 的检查保证"如果将来变 64 位就会失败而不是静默截断"** ✓

## 十、GfxImage 的三步发布

```cpp
// ① 构造
SV_BuildOlfinalAlphaBarrettImage(source, *loadDefAddress, *nameAddress, storage->header, storage->loadDef);

// ② 如果已存在 ⇒ 直接复用
if (const auto existing = findXAsset(GfxImageAssetType(10), storage->name.data(), false).data)
{ storage->linked = existing; continue; }

// ③ 初始化 + 链接 + 设 zone
tryInitializeGfxImage(module_ + GfxImageInitializeRva, storage->header.data(), fault);
tryLinkXAssetEntry(dbLinkXAssetEntry_, GfxImageAssetType, &linkedHeader, entry, fault);
trySetXAssetEntryZone(entry, *retainedBarrettZone, fault);

// ④ 反查一致性
if (findXAsset(GfxImageAssetType, storage->name.data(), false).data != storage->linked)
    return failBarrettAssets(LinkFailed, "image lookup differs after link: " + name);
```

### 10.1 `loadDef` 是**16 字节**

```cpp
std::array<std::byte, 16> loadDef{};
```

**而 `SV_BuildOlfinalAlphaBarrettImage` 同时填 `header` 与 `loadDef`** —— 所以 GfxImage 有一个 16 字节的"加载定义"附属块。

**这与 §143 里 `GfxImage 52 B` 是**主结构**，而 `loadDef` 是额外的 16 字节** —— 两个不同的东西。

### 10.2 第 ④ 步是**唯一的一致性检查**

```cpp
findXAsset(...) != storage->linked   ⇒  失败
```

**"链上去了，但按名字再查一次得到的不是同一个指针"** —— 这是 §236 里 `weaponLookup_ != weaponAssetIndex` 的同族。

**注意用 `!=` 而不是 `!`** —— 要求**逐位相同**。

### 10.3 而"已存在就直接复用"

```cpp
if (existing) { storage->linked = existing; continue; }
```

**所以重入时不会重复链接** ✓ —— 这解决了 §246 里 `publishedModelTables` 的可重入问题。

**这里的设计比 §246 好。**

## 十一、材质的**路由兼容性五项检查**（本组第三重要）

```cpp
bool routingCompatible = SV_OlfinalAlphaBarrettMaterialLayoutCompatible(source, templateSpan);
const std::byte *templateTextures{}; const std::byte *templateConstants{};
if (routingCompatible)
{
    std::memcpy(&templateTextures, finalTemplate + 92, sizeof(templateTextures));
    std::memcpy(&templateConstants, finalTemplate + 96, sizeof(templateConstants));
    routingCompatible = readableSpan(templateTextures, source.textures.size() * 12) &&
        readableSpan(templateConstants, source.constants.size());
}
for (index; routingCompatible && index < source.textures.size(); ++index)
    routingCompatible = std::equal(source.textures[index].slotHeader.begin(),
        source.textures[index].slotHeader.end(), templateTextures + index * 12);
for (offset; routingCompatible && offset < source.constants.size(); offset += 32)
    routingCompatible = std::equal(source.constants.begin() + offset,
        source.constants.begin() + offset + 4, templateConstants + offset);
```

### 11.1 五项

```text
① 整体布局兼容（SV_OlfinalAlphaBarrettMaterialLayoutCompatible）
② textures 指针可读（size * 12 字节）
③ constants 指针可读（size 字节）
④ 每个纹理槽的 slotHeader（12 字节）与模板【完全相同】
⑤ 每 32 字节常量的【前 4 字节】与模板相同
```

### 11.2 两个偏移

```text
finalTemplate + 92   ⇒ textures 指针
finalTemplate + 96   ⇒ constants 指针
```

**两个指针相隔 4 字节** —— 所以材质头里 `+92` 与 `+96` 是两个连续指针。

### 11.3 第 ⑤ 项的语义

```cpp
// The first four bytes identify the material constant.
// The remaining 28 bytes are the material-specific value
// that the alpha port intentionally replaces.
```

```text
每 32 字节常量：
  前 4 字节   常量【标识】
  后 28 字节  该材质的【值】—— alpha 移植【有意替换】它
```

**所以检查只比标识、不比值** —— 因为值本来就该不同。

**这是一个"验证结构而不验证内容"的检查** —— 精确到位。

### 11.4 而"不兼容 ⇒ 保留原材质"

```cpp
if (barrettSafeMaterialsEnabled || !routingCompatible)
{
    retainedBarrettMaterialNames.insert(source.name);
    continue;
}
```

### 11.5 **两条退路合成一条**

```text
安全材质模式开      ⇒ 全部保留原材质，不发布
路由不兼容          ⇒ 该材质保留原材质，不发布
```

**"retained" = 不替换，用游戏原本的材质。**

**所以这是一个"宁可外观不对，也不让客户端崩"的降级。**

**与 §244 里"两个方向代价不对称"是同一条原则** —— 材质不对是外观问题，材质错位是崩溃。

### 11.6 `retainedBarrettMaterialNames` 的用途

**一个 `std::set<string>`** —— 后面（未读部分）应该用来告诉模型构建"这些材质不要替换"。

## 十二、材质的两个数组布局

```cpp
storage->textures.resize(source.textures.size());        // vector<array<byte,12>>
storage->constants = source.constants;
storage->stateBits = source.stateBits;

for (index) {
    std::copy(source.textures[index].slotHeader.begin(), ...end(), storage->textures[index].begin());
    const auto image = findXAsset(GfxImageAssetType, source.textures[index].image.c_str(), false).data;
    const auto imageAddress = address32(image);
    if (!imageAddress) return fail(Something, "material image is missing: " + image);
    std::memcpy(storage->textures[index].data() + 8, &*imageAddress, 4);
}
```

### 12.1 12 字节槽的**三段**

```text
+0..7   slotHeader（8 字节）
+8..11  image 指针（4 字节）
```

**所以 `slotHeader` 是 **8 字节**，而非 12。**

**这与 §247 里 `readableSpan(templateTextures, size * 12)` 与 `equal(slotHeader.begin(), slotHeader.end(), templateTextures + index*12)` 一致 —— 但 §247 的 ④ 检查比较的是**整个 12 字节**，即包括 image 指针。

**而 image 指针在模板里指向**别的图**，所以 ④ 的检查必然失败？**

**除非模板的 image 指针也相同**（同一个纹理）。

**这是一个潜在矛盾** —— 值得指出。

### 12.2 `storage->textures[index].data() + 8`

**`array<byte,12>::data() + 8`** —— 所以 image 指针在偏移 8 ✓

### 12.3 `SV_BuildOlfinalAlphaBarrettMaterial` 的**七个参数**

```cpp
SV_BuildOlfinalAlphaBarrettMaterial(source, templateSpan,
    *nameAddress,
    texturesAddress.value_or(0),
    constantsAddress.value_or(0),
    stateBitsAddress.value_or(0),
    storage->header)
```

**七个**：

```text
1. source
2. templateSpan（模板材质）
3. name 地址
4. textures 地址
5. constants 地址
6. stateBits 地址
7. header（输出）
```

**三个数组用 `value_or(0)`** —— 因为空数组允许传 0。

**而前面的检查保证"非空则地址有效"** ✓

## 十三、材质发布与图片发布的**同构**

```cpp
for (auto &storage : publishedBarrettAssets.materials)
{
    if (const auto existing = findXAsset(MaterialAssetType, storage->name.data(), false).data)
    { storage->linked = existing; continue; }
    ...link + set zone...
    if (findXAsset(...).data != storage->linked) return fail(LinkFailed, "material lookup differs after link: ...");
}
```

**完全同构**（只是少了 `tryInitializeGfxImage` 那一步，因为材质不需要初始化）。

**所以这四段代码是同一模式的三次拷贝**（image / material / surfs / model / animation）。

**这是一处明显的重复** —— 五个 `for` 循环，每个做"存在则复用 / 否则链接 / 反查"。

## 十四、关键结论

1. **`XModel 360` / `XAnimParts 88` 与 §143 一致**，而 GfxImage/Material 用命名常量（OLfinal 特有）。
2. **`emptyStreamSentinel` 是"零长度流也要有合法指针"** —— 与哨兵值不同族。
3. **`unique_ptr` 保证对象地址稳定**（引擎持有 `header` 地址）—— 而 §246 的 `std::vector<PublishedModelTable>` 有同类风险但未用 `unique_ptr`。
4. **代际哨兵 = `viewmodel_barrett` 是否还在** —— 引擎先清、我们后清。
5. **`OLMOD_ALPHA_BARRETT_METADATA` 被读两次，两次判据不同**（`>1` vs `>0 && <32768`）。
6. **四处字节前缀守卫**，其中两处是 `A1`（读全局）——4 字节极弱。
7. **zone 借用 `cheytac_mp`** —— 避免"继承 zone 0 ⇒ 下次地图切换被扫掉"。
8. **`address32` 拒绝 > 0xFFFFFFFF** —— 为将来 64 位留下失败而不是截断。
9. **GfxImage 的 `loadDef` 是独立的 16 字节块**，不是主结构的一部分。
10. **材质路由兼容性五项检查** —— 常量只比前 4 字节标识，后 28 字节有意不同。
11. **"安全材质模式"与"不兼容"合成一条退路** —— 宁可外观不对也不能崩。
12. **`slotHeader` 是 8 字节而槽是 12 字节**，④ 检查比较整个 12 字节会包含 image 指针 —— 与"image 指针在本实现里被写入"潜在矛盾。

## 十五、未闭合点

- ④ 检查比较 12 字节（含 image 指针）与"image 指针是本实现写入的"是否矛盾。
- `SV_AlphaBarrettModelTable()` 返回类型（§246 遗留）。
- 五个 `for` 循环的重复（image/material/surfs/model/animation 同构）。
- `EngineBindings.cpp` 12450 行之后未读取。
