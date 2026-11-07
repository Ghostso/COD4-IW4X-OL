# 249 · **流式加载的 15 秒等待 + bit3 哨兵**、WeaponDef 的 `+0x10/+0x18` 与 48 个 XAnim 槽

## 一、范围

本报告学习 `EngineBindings.cpp` 12863–13250 行。

## 二、**为什么不能调那三个 post-link 助手**（本组最重要的一段）

```cpp
// Queue every linked type-4 asset through the engine's model-
// stream worker. Do not call the three post-link helpers here: racing that
// worker lets two loaders see the same null XModelSurfs pointer and can
// hand the renderer a null index source. Wait for the native
// attach -> renderer init -> LOD rebuild sequence instead. Bit 3
// at XModel +349 is set only by the final rebuild step.
```

### 2.1 四层

```text
1. 每个 link 过的 type-4 资产都排进引擎的模型流工作线程
2. 【不要】调那三个 post-link 助手
3. 理由：与工作线程竞争能让两个 loader 看到同一个 null XModelSurfs 指针
4. ⇒ 可能把 null 索引源交给渲染器
5. 改为等待原生 attach → renderer init → LOD rebuild 序列
```

### 2.2 这是"不要自己做"的**显式否定**

**"三个 post-link 助手"未命名** —— 但从上下文（§248 的 `tryQueueXModelStream` 之后）推测是某个 attach/renderer-init/LOD-rebuild 的组合。

**关键是**：**顺序必须由引擎自己的工作线程驱动，而不是我们主动调三个助手。**

**这是"竞争条件"的防御** —— 而且是**通过放弃一个看似正确的做法**（主动调助手）来实现的。

### 2.3 与 §239/§244 的"阻塞"教训的对照

**§239**："`auditItemNames` 内联阻塞 bridge 线程 ⇒ 加载屏"
**§249**："我们不能主动推进流式加载 ⇒ 必须等"

**两个都关于"线程/时序"，但方向相反**：

```text
§239  不要在主线程做重活
§249  不要在流式加载时抢活
```

## 三、**`bit 3 at XModel +349`** 是"LOD 重建完成"的哨兵

```cpp
publishedBarrettAssets.models,
[this](const auto &storage) {
    const auto *const linked = (const std::byte *)storage->linked;
    return readableSpan(linked, 350) && ((uint8)linked[349] & 0x08u) != 0;
}
```

### 3.1 三个量

```text
readableSpan(linked, 350)      ⇒ 至少要 350 字节可读
linked[349] & 0x08             ⇒ bit 3
```

**`+349` 的 bit 3 = `0x08`** —— 而注释说"只有最后的 rebuild 步骤会设置它"。

### 3.2 为什么是 350 而不是 352

**`readableSpan(linked, 350)` 访问 `[349]`** —— 需要的字节数是 350（下标 0..349）✓

**精确**。

### 3.3 而 `+349` 与 §248 里 `boneInfo` 在 312

**`349` 在 312 之后 37 字节** —— 所以 `boneInfo` 指针（4 字节，312..315）之后还有 33 字节，然后 `+349` 是这个字段的一部分。

**所以 XModel 里有一个大于 349 字节的结构** —— 而 §143 说 XModel 是 **360 字节** ✓

**`349 < 360`** ✓ 一致。

## 四、`surfs` 的完成判据是**两个字段都非零**

```cpp
publishedBarrettAssets.surfs,
[this](const auto &storage) {
    const auto *const linked = (const std::byte *)storage->linked;
    void *surfaces{};
    std::uint16_t surfaceCount{};
    if (!readableSpan(linked, storage->header.size())) return false;
    std::memcpy(&surfaces, linked + 4, sizeof(surfaces));
    std::memcpy(&surfaceCount, linked + 8, sizeof(surfaceCount));
    return surfaces && surfaceCount;
}
```

### 4.1 偏移

```text
+4   surfaces      指针
+8   surfaceCount  uint16
```

### 4.2 **注意 `+0` 是名字指针**（§248 写的）

**所以 XModelSurfs 的 header 是**：

```text
+0                 名字
+4                 surfaces
+8                 surfaceCount (uint16)
```

**而 `storage->header.size()` 是 48** —— 所以 48 字节里前 12 字节有内容，其余为零。

**而 §248 指出"XModelSurfs 的 header 是我们零构造的（只写 +0）"** —— 所以 `+4` 与 `+8` **在链接前是零**。

**⇒ 这两个字段由引擎的 attach/renderer-init 步骤填入。**

**这就是为什么必须等待流式加载完成** —— 因为 `surfaces` 与 `surfaceCount` 是**引擎填的**，不是我们写的。

**这解释了 §248 里那个"header 只有 48 字节且只写 +0"的疑问**：**其他字段由引擎填。**

## 五、**15 秒等待**与 `Sleep(1)` 轮询

```cpp
constexpr DWORD StreamWaitMilliseconds = 15000;
const auto streamDeadline = GetTickCount64() + StreamWaitMilliseconds;
bool streamsReady{};
do
{
    streamsReady = all_of(surfs, ...) && all_of(models, ...);
    if (!streamsReady) Sleep(1);
}
while (!streamsReady && GetTickCount64() < streamDeadline);
if (!streamsReady)
    return failBarrettAssets(LinkFailed, "native XModel streaming did not finish within 15 seconds");
```

### 5.1 三个要点

```text
1. Sleep(1) 而不是 Sleep(0) 或忙等 ⇒ 让出 CPU
2. do-while ⇒ 【至少检查一次】
3. 超时 15 秒
```

### 5.2 `GetTickCount64` 而不是 `GetTickCount`

**64 位** —— 避免 49.7 天回绕。

**而 §239 里 `MirrorThread` 用过 `Sleep(1)`** —— 同一个手法。

### 5.3 15 秒的**位置**

**它在 `installAlphaWeaponPorts` 里** —— 而这是一个可能被调用多次的函数。

**所以每次代际重建都会阻塞最多 15 秒。**

**这与 §249 开头"不要抢活"的论证**一致**（等待是有意的），但**15 秒的阻塞在游戏线程上是显著的**。

**注释没说调用者能否接受** —— 这是一个潜在问题。

### 5.4 一个可能的死锁

**如果流式加载需要主线程做某事（例如需要 pump 消息），而我们阻塞在这个循环里，就会死锁到 15 秒超时。**

**代码没有给出任何 pump 或 yield 的证据** —— 只有 `Sleep(1)`。

## 六、`ready = true` 之后的那条总结日志

```cpp
publishedBarrettAssets.ready = true;
write("alpha Barrett asset closure ready images=N materials=N surfs=N models=N safeMaterials=N retainedMaterialFallbacks=N");
```

### 6.1 六个计数

```text
images                      发布的图片数
materials                   发布的材质数
surfs                       发布的 surf 数
models                      发布的模型数
safeMaterials               【保留的】材质数（retainedBarrettMaterialNames.size()）
retainedMaterialFallbacks   【用了回退】的次数
```

### 6.2 **`safeMaterials` 与 `retainedMaterialFallbacks` 是两个不同的量**

```text
safeMaterials               被判定为"保留"的材质【名字】数
retainedMaterialFallbacks   实际【走了回退路径】的次数
```

**而 §248 的 ① 分支也会 `++retainedMaterialFallbacks`** —— 所以后者 >= 前者（每个 safe material 至少被引用一次，可能更多）。

### 6.3 而 `animations` **不在日志里**

**日志列了 images/materials/surfs/models 但**没有 animations**。

**而 `publishedBarrettAssets.animations` 是存在的** —— 这是一处遗漏（想数却漏了）。

## 七、`ports` 循环的**六个跳过/失败条件**

```cpp
for (portIndex; portIndex < ports.size(); ++portIndex)
{
    const auto &port = ports[portIndex];
    if (port.lineage == ConvertedPresentation && !barrettMetadataEnabled) continue;      // ① 跳过
    if (port.lineage == ConvertedPresentation && !publishedBarrettAssets.ready)
        return publish(SourceAssetMissing);                                              // ② 失败
    if (port.lineage == MissingModelFamily) continue;                                    // ③ 跳过
    if (!port.alphaName || !*port.alphaName || !port.sourceName || !*port.sourceName)
        return publish(InvalidDefinition);                                               // ④ 失败
    const auto modelTableStatus = ensureModelTable(port, portIndex);                     // ⑤
    if (modelTableStatus != Ready) return modelTableStatus;
    ... （武器定义）...
}
```

### 7.1 四项 + 一个子调用

**注意 ① 与 ② 的先后**：

```text
开关关        ⇒ 【跳过】，不要求 ready
开关开但未 ready ⇒ 【失败】
```

**所以"开关关 ⇒ 整个 port 被忽略"** —— 与 §247 里 `convertedBarrettEnabled` 控制"是否把 SourceAssetMissing 当可恢复"是**同一个开关的两个用途**。

## 八、**WeaponDef 的克隆 + 补丁 + 两个模型指针 + 48 个动画槽**

### 8.1 克隆

```cpp
const auto source = findXAsset(WeaponAssetType(28), port.sourceName, false).data;
if (!source || !readableSpan(source, OlfinalWeaponDefSize)) return publish(SourceAssetMissing);

std::array<std::byte, OlfinalWeaponDefSize> definition{};
std::memcpy(definition.data(), source, definition.size());
```

**`OlfinalWeaponDefSize = 0x101C`**（记忆里）—— **40348 字节**。

**整个 WeaponDef 拷进一个栈/堆局部数组** —— 这是"深拷贝"。

### 8.2 但**浅指针**也被拷了

```cpp
// This is the same ownership lifetime as every shallow pointer copied from that source definition.
```

**"与从那个源定义拷来的每一个浅指针相同的所有权生存期"** —— 承认了这一点。

**所以 `definition` 里有些字段指向 `source` 的内部数据，而 `source` 必须存活。**

**这解释了为什么要"给克隆一个 retained source 的 zone"**（见第九节）。

### 8.3 `SV_PatchAlphaWeaponDefinition(definition, nameAddress, port.tuning)`

```cpp
const auto nameAddress = (uintptr_t)port.alphaName;
if (nameAddress > 0xFFFFFFFF || !SV_PatchAlphaWeaponDefinition(definition, (uint32)nameAddress, port.tuning))
    return publish(InvalidDefinition);
```

**三项**：名字地址、调参。

**`port.alphaName` 是 `const char*`** —— 而它指向的是**静态字符串**（`SV_AlphaWeaponPorts()` 里的字面量）。

**所以 `nameAddress` 永存** ✓ 与 §248 里 `storage->name` 是不同的做法（那里是 `std::array<char,128>`）。

## 九、**`+0x10` / `+0x18` 与 §190 的对照**（本组第二重要）

```cpp
// CODREF(alpha_weapondef): the alpha loader keeps sixteen first-person XModels
// at +0x14 and sixteen world XModels at +0x54. Barrett selects viewmodel_barrett
// and weapon_m82 in element zero of those arrays. OLfinal reduced the two
// arrays to two entries apiece at +0x10/+0x14 and +0x18/+0x1C. The retained
// CheyTac clone has tag_origin in both element-zero fields. Install the complete
// alpha base pair before linking the WeaponDef; keep the alternate element and
// the six later auxiliary models source-owned.
constexpr std::size_t ViewModelOffset = 0x10;
constexpr std::size_t WorldModelOffset = 0x18;
```

### 9.1 **两代布局**

```text
alpha（0.0.2.2）    16 个第一人称在 +0x14，16 个世界模型在 +0x54
OLfinal             各缩到 2 个：+0x10/+0x14 与 +0x18/+0x1C
```

### 9.2 而**保留的 CheyTac 克隆两个 element-zero 都是 `tag_origin`**

**"`tag_origin`" 是一个**占位模型名**（不是真模型）** —— 所以必须被替换。

**"在链接 WeaponDef 之前安装完整的 alpha 基础对"** —— 顺序要求。

### 9.3 **只替换 element zero**

```text
"keep the alternate element and the six later auxiliary models source-owned"
```

```text
element 0      ⇒ 【我们替换】
element 1      ⇒ 源所有
六个后续辅助模型 ⇒ 源所有
```

**所以 `+0x10/+0x14` 里只写 `+0x10`，`+0x14` 保持源值；`+0x18/+0x1C` 里只写 `+0x18`。**

### 9.4 两个模型名

```text
viewmodel_barrett   第一人称
weapon_m82          世界模型
```

**而 §247 的代际哨兵正是 `viewmodel_barrett`** ✓ —— 所以这两个是**同一对**。

## 十、**48 个 XAnim 槽**的 21 个显式填充

### 10.1 那段注释

```cpp
// Exact alpha Barrett array-0 identities. The 0.0.2.2
// WeaponDef loader reads 48 XStrings at +0xEC. Its packed
// block-3 pointers advance in the same order as the
// directly serialized viewmodel_barrett XAnimParts; the
// three inline strings at 34/46/47 corroborate ADS fire,
// up and down independently. OLfinal extends this enum to
// 62 without reordering these original slots.
constexpr std::size_t AnimationArrayOffset = 0x7C;
```

### 10.2 四个数字

```text
48    0.0.2.2 在 +0xEC 读 48 个 XStrings
+0xEC 数组起点（alpha 版）
+0x7C 【本实现用的】数组起点（OLfinal 版）
62    OLfinal 把这个枚举扩展到 62，但【不重排】原来的槽
```

### 10.3 **+0xEC vs +0x7C**

**48 个 uint32 = 192 字节。`0x7C + 192 = 0x13C`。**

**而 `0xEC + 192 = 0x1AC`。**

**两个不同的起点** —— 所以 OLfinal 的动画数组更靠前。

### 10.4 21 个槽的清单

```text
 1  idle          2  idle
 3  fire          5  fire
 9  reload       11  reload_empty
15  pullout      16  pullout      17  breach       18  putaway
21  pullout_quick  22  putaway_quick
23  pullout      24  putaway
25  sprint_in    26  sprint_loop  27  sprint_out
34  ads_fire     35  ads_fire
46  ads_up       47  ads_down
```

**21 个槽** —— 而 `publishedBarrettAssets.animations` 的**每个 name 必须被用到**：

```cpp
if (closedAnimations.size() != publishedBarrettAssets.animations.size())
    return publish(InvalidDefinition);
```

### 10.5 **这是一个"全部覆盖"的要求**

```text
closedAnimations（被填的【名字】集合）必须等于全部发布的动画数
```

**所以**如果发布了一个动画但没在任何槽里用，就失败**。**

**这是一个"没有孤儿资产"的检查** —— 与 §248 里"至少命中一次"（patchedRows）相反方向（那里是"至少一个"，这里是"恰好全部"）。

### 10.6 三个内联字符串位置

```text
34/46/47  ⇒ ADS fire, up, down
```

**这三个位置的字符串在 alpha WeaponDef 里是**内联的**（不是指针）**，所以对照它们能独立确认映射。

**"corroborate ... independently"** —— 三条独立佐证。

### 10.7 `find_if` 用 `name.data() == name` 的比较

```cpp
const auto animation = std::ranges::find_if(
    publishedBarrettAssets.animations,
    [name](const auto &candidate) {
        return candidate->name.data() == name;      // ← 【指针相等】不是 strcmp
    });
```

### 10.8 **这是名字比较的另一种方式**

**`std::array<char,128>::data()` 与 `std::string_view` 比较** —— 但 `==` 在 `const char*` 与 `string_view` 之间是**内容比较**吗？

**`std::string_view` 有 `operator==(const char*, string_view)`**（C++17 后）—— 所以**是内容比较** ✓

**但这里 `candidate->name.data()` 是 `const char*` 而 `name` 是 `std::string_view`** ⇒ 调用 `operator==(const char*, string_view)` ⇒ **内容比较** ✓

**而 §240 里 `candidate->name.data() == name` 如果是 `const char*` 与 `const char*` 就是指针比较** —— **这里因为 `name` 是 `string_view` 才安全。**

**这是一处"类型救了语义"的地方** —— 值得指出。

### 10.9 重复的名字

```text
idle      出现在槽 1 与 2
fire      出现在槽 3 与 5
pullout   出现在槽 15, 16, 23
putaway   出现在槽 18, 24
ads_fire  出现在槽 34, 35
```

**所以同一个动画被写进多个槽** —— 而 `closedAnimations` 是 `set`，所以每个名字只算一次 ✓

**`closedAnimations.size()` 比较的是**唯一名字数** —— 所以一个动画可以被多个槽共用。**

## 十一、链接 + zone 提升 + 链接后验证

### 11.1 链接

```cpp
void *linkedHeader = definition.data();      // ← 【栈/局部数组】
void *entry{};
if (!tryLinkXAssetEntry(dbLinkXAssetEntry_, WeaponAssetType, &linkedHeader, entry, fault) || !entry || !linkedHeader)
    return publish(LinkFailed);
```

### 11.2 **`definition` 是 `std::array<std::byte, 0x101C>` 局部变量**

**如果它在这个函数返回后就销毁，而引擎存的是 `definition.data()`，那就是悬垂。**

**但 `linkedHeader` 是**传址**的 —— 引擎可能替换它到自己的内存。**

**而 §11.4 的验证只检查 `target = findXAsset(...)` 可读 `OlfinalWeaponDefSize`** —— 不检查 `target == linkedHeader`。

**所以：如果引擎拷贝了，`definition` 的生命周期无关；如果引擎没拷贝而 `linkedHeader` 被改成引擎的地址，可能安全；如果引擎存了 `definition.data()` 而又没改 `linkedHeader`，就是悬垂。**

**代码里没有 `publishedBarrettAssets` 持有 `definition`** ⇒ **这是一处以"引擎必然接管"为前提的写法。**

**与 §248 的 `unique_ptr` + 常驻存储形成鲜明对照。**

**这是一个重要的不一致** —— 值得记录。

### 11.3 注释承认了"可能返回不同指针"

```cpp
// A failed lookup earlier in session setup can leave a default
// entry for this name. Linking the real definition replaces
// that entry's engine-owned header, so DB lookup may correctly
// return a different pointer than the linker's transient output.
// findXAsset already rejects default entries; require
// the resolved header and its full WeaponDef extent here.
```

### 11.4 三项要求

```text
target 非空
readableSpan(target, OlfinalWeaponDefSize)
（findXAsset 已经拒绝了默认项）
```

**"DB lookup 可能正确地返回一个与链接器的瞬态输出不同的指针"** —— 这**明确承认**了 `linkedHeader` 与 `target` 可以不同。

**所以这里的验证**放松**了（不比较指针）**，而 §248 的四个链接都**要求指针相等**。

**这解释了为什么 §248 里 XAnim 也不需要指针相等** —— 因为引擎可能重新分配。

## 十二、`zone` 提升的完整因果

```cpp
// DB_LinkXAssetEntry allocates with the current loading-zone
// byte. At this late runtime boundary that byte is zero, which
// makes an otherwise valid new WeaponDef a default placeholder
// and causes the native resolver to reject it. Give the clone
// its retained source's resident zone before asking the DB or
// weapon registry for it. This is the same ownership lifetime
// as every shallow pointer copied from that source definition.
const auto sourceZone = assetZoneForHeader(WeaponAssetType, source);
if (!sourceZone || !trySetXAssetEntryZone(entry, *sourceZone, fault))
    return publish(LinkFailed);
```

### 12.1 四层

```text
1. DB_LinkXAssetEntry 用【当前 loading-zone 字节】分配
2. 这个晚期运行时边界上那个字节是 0
3. ⇒ 一个本来有效的 WeaponDef 变成【默认占位】
4. ⇒ 原生解析器拒绝它
```

### 12.2 解法

**"在向 DB 或武器注册表询问它之前，给克隆它保留源的常驻 zone"**

### 12.3 而 zone 本身的来源是**同一个 `assetZoneForHeader`**

**120,000 次线性扫描** —— 而这里每个 port 都会调一次。

**如果 ports 有 8 个，就是 8 × 120,000 = 960,000 次条目扫描。**

**这是一个性能问题** —— 与 §248 里"只调一次"的假设不同（那里是 Barrett 的 `cheytac_mp` 一次）。

## 十三、注册的**三项检查**（又一次双向验证）

```cpp
if (!tryWeaponResolve(weaponResolver_, port.alphaName, index, fault) ||
    !index || index > MaximumWeaponAssetIndex ||
    weaponLookup_(port.alphaName) != index)
    return publish(RegistrationFailed);
if (!markAlphaBaseWeapon(index))
    return publish(RegistrationFailed);
```

### 13.1 五项

```text
1. resolve 不 fault
2. index 非零
3. index <= MaximumWeaponAssetIndex
4. 【lookup 得到同一个 index】← 双向
5. markAlphaBaseWeapon 成功
```

**第 4 项与 §236 里 `weaponLookup_(nativeName) != weaponAssetIndex` 是同一个手法** ✓

## 十四、关键结论

1. **不能主动调三个 post-link 助手** —— 竞争会让两个 loader 看到同一个 null `XModelSurfs`。
2. **`XModel +349` 的 bit 3** 是"LOD 重建完成"的哨兵，只有最后一步设置。
3. **`XModelSurfs` 的 `+4`（surfaces）与 `+8`（count）由引擎填** —— 这解释了 §248 里"header 只写 +0"的疑问。
4. **15 秒 `Sleep(1)` 轮询**，用 `GetTickCount64` 避免回绕；但没有 pump，若需要主线程推进就会死锁到超时。
5. **日志漏了 `animations` 计数**。
6. **WeaponDef 是**深拷贝** 0x101C 字节，但其中浅指针仍指向源**。
7. **`+0x10/+0x18` 是 OLfinal 的模型数组（各 2 项），而 alpha 是 `+0x14/+0x54`（各 16 项）**。
8. **只替换 element 0**，element 1 与六个辅助模型保留源所有。
9. **`+0x7C` 是 OLfinal 的 XAnim 数组起点，而 alpha 是 `+0xEC`**。
10. **21 个槽必须覆盖全部发布的动画名**（`closedAnimations.size() == animations.size()`）—— 与"至少一次"相反，是"恰好全部"。
11. **`candidate->name.data() == name` 是内容比较，因为 `name` 是 `string_view`** —— 类型救了语义。
12. **同一动画可占多个槽**（`idle` 两槽、`pullout` 三槽），`set` 去重。
13. **`definition` 是局部数组而引擎存其地址** —— 这里以"引擎必然接管"为前提，与 §248 的常驻 `unique_ptr` 不一致。
14. **zone 提升因为它晚期 loading-zone 字节为 0**，每个 port 都付一次 120,000 扫描。

## 十五、未闭合点

- `definition`（局部 `std::array`）被链接后是否悬垂。
- 15 秒阻塞在游戏线程上是否需要 pump（未证）。
- `assetZoneForHeader` 每个 port 一次 120,000 扫描的累计代价。
- `publishedBarrettAssets.animations` 未在完成日志里计数。
- `EngineBindings.cpp` 13250 行之后未读取。
