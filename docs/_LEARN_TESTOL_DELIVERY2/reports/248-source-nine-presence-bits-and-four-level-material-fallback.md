# 248 · `pointerPresence` 的九位、材质的四级回退链、XModel header 的三层偏移

## 一、范围

本报告学习 `EngineBindings.cpp` 12450–12850 行。

## 二、动画的**九个流指针 + 一个名字指针**

```cpp
const auto setAnimationPointer = [&](std::size_t pointer, const void *data, bool empty) {
    if (!source.pointerPresence[pointer]) return true;      // ← 【presence 位】
    const auto target = empty ? (const void *)storage->emptyStreamSentinel.data() : data;
    const auto address = address32(target);
    if (!address) return false;
    std::memcpy(storage->header.data() + 48 + pointer * 4, &*address, 4);
    return true;
};
```

### 2.1 两次写入

```cpp
std::memcpy(storage->header.data() + 0, &*nameAddress, 4);      // 名字在 +0
```

```text
+0                      名字指针
+48 + 0*4  = +48        boneNames
+48 + 1*4  = +52        dataByte
+48 + 2*4  = +56        dataShort
+48 + 3*4  = +60        dataInt
+48 + 4*4  = +64        randomDataShort
+48 + 5*4  = +68        randomDataByte
+48 + 6*4  = +72        randomDataInt
+48 + 7*4  = +76        indices
+48 + 8*4  = +80        notify
```

### 2.2 **九个指针从 +48 开始，到 +80 结束**

**而 `XAnimParts` 是 88 字节** ⇒ `+84` 是最后一个 dword（可能是 `flags` 或 `numframes`）。

### 2.3 `pointerPresence` 是**九位的掩码**

```cpp
if (!source.pointerPresence[pointer]) return true;
```

**"这个流存在吗"** —— 如果不存在，**不写指针**（保持 `header` 里的原值）。

**这意味着 `header` 是从 bundle 里**原样拷贝**的**（`storage->header = source.header;`）。

**所以：**

```text
header 里有【目标 build 的完整布局】
而本实现只【覆盖它知道的那些指针】
未覆盖的保持 bundle 里给的值
```

**这是一个"增量覆盖"而不是"从头构造"的设计。**

### 2.4 `emptyStreamSentinel` 在这里被用到

**`empty ? sentinel.data() : data`** —— 空流指向那个 1 字节数组。

**而 `pointerPresence[pointer] == false` 时不写** —— 所以两种"没有这个流"被区分：

```text
presence == false       ⇒ 【不写】，保留 header 里的原值
presence == true 且空   ⇒ 写 sentinel 指针
presence == true 且非空 ⇒ 写真实指针
```

**三种状态对应九位掩码 —— 这是一个第三个"三态"设计**（§242 的 `addressable` 哨兵、§247 的 sentinel 是另外两个）。

## 三、`boneNames` 与 `notifyNames` 的**两次 intern**

```cpp
for (index < source.boneNames.size())
    tryInternScriptString(ScriptStringInternRva, source.boneNames[index].c_str(), storage->boneNames[index], fault);

for (index < source.notifyNames.size())
{
    uint16 interned{};
    tryInternScriptString(..., source.notifyNames[index].c_str(), interned, fault);
    std::memcpy(storage->notify.data() + index * 8, &interned, 2);
}
```

### 3.1 两个不同的输出宽度

```text
boneNames   ⇒ uint16 数组（每项 2 字节）
notify      ⇒ 每项 8 字节，其中【前 2 字节】是 interned 字符串 id
```

### 3.2 为什么 notify 是 8 字节

**XAnim notify 条目通常是 `{name index (uint16), padding, time (float/int)}` 或类似。**

**这里只写了前 2 字节** —— 所以其余 6 字节保持 `source.notify` 里的原值 ✓

**这是"只覆盖知道的字段"的同一手法。**

### 3.3 `tryInternScriptString` 返回的是 uint16

**`ScriptStringInternRva = 0x34BD10`** —— 一处使用，两种输出类型（`uint16&` 与 `interned`）。

## 四、XAnim 链接后的验证**只用 `readableSpan(linked, 88)`**

```cpp
storage->linked = findXAsset(XAnimAssetType, storage->name.data(), false).data;
if (!storage->linked || !readableSpan(storage->linked, 88))
    return failBarrettAssets(LinkFailed, "XAnim lookup differs after link: " + source.name);
```

### 4.1 与其他四组**不同**

```text
image      findXAsset(...) != storage->linked     ⇒ 失败（指针相等性）
material   findXAsset(...) != storage->linked     ⇒ 失败
surfs      findXAsset(...) != storage->linked     ⇒ 失败
model      findXAsset(...) != storage->linked     ⇒ 失败
XAnim      !storage->linked || !readableSpan(linked, 88)     ⇒ 失败（只检查可读）
```

### 4.2 这是一处**不一致**

**XAnim 的验证**放弃**了"反查得到同一个指针"这一项** —— 只要求"能查到且可读"。

**所以一个把 XAnim 链接到错误条目的 bug 不会被这里抓到。**

### 4.3 而错误消息仍叫 "lookup differs after link"

**消息名保留了但检查内容不同** —— 一处措辞与实现的偏差。

## 五、`XModelSurfs` 的一条特殊路径

```cpp
if (const auto existing = findXAsset(XModelSurfsAssetType(3), storage->name.data(), false).data)
{
    storage->linked = existing;
}
else
{
    ...link + set zone...
    storage->linked = linkedHeader;
}
if (findXAsset(XModelSurfsAssetType, storage->name.data(), false).data != storage->linked)
    return failBarrettAssets(LinkFailed, "XModelSurfs lookup differs after link: " + resourceName);
```

### 5.1 **两条路 + 一个共同验证**

**这是本组唯一一个"存在则复用"与"链接"都在 `if/else` 里、而验证在 `if` 外面**的写法。

**而 image/material 的"存在则复用"是 `continue`（跳过验证）。**

### 5.2 所以 surfs 的验证更严格

```text
image      已存在 ⇒ continue（【不】验证）
material   已存在 ⇒ continue（【不】验证）
surfs      已存在 ⇒ 复用后【仍验证】
XAnim      没有"已存在"分支
model      没有"已存在"分支
```

**三种不同的处理策略在同一个函数里。**

### 5.3 `surfs->header` 只有 48 字节

```cpp
struct PublishedBarrettSurfs { std::array<char,128> name; std::array<std::byte,48> header; void *linked; };
```

**48 字节，而 XModelSurfs 在 IW4X 里通常更大** —— 但这里只写名字指针（`+0`），其余保持 bundle 给的值。

**所以 `header = source.header` 吗？**

**不 —— `storage->header` 是 `{}`（零初始化），只写了 `+0`。**

**所以 XModelSurfs 的 header 是**我们构造的**，而不是从 bundle 拷的** —— 与其他不同。

**这可能是一个 bug：**如果 XModelSurfs 需要更多字段（surf 列表、总数），它们是零。

**而 §143 里 `XModelSurfs` 没有被列为已验证尺寸** —— 所以这是一个未验证的结构。

## 六、`retainedBarrettMaterialNames` 的**四级回退链**（本组最重要的一段）

```cpp
const auto resolveBarrettMaterial = [&](const std::string &name) -> const void * {
    // ① 被保留的材质 ⇒ 用它的 cloneSource
    if (retainedBarrettMaterialNames.contains(name))
    {
        const auto retained = retainedBarrettMaterials.find(name);
        if (retained != retainedBarrettMaterials.end())
        {
            ++retainedMaterialFallbacks;
            return findXAsset(MaterialAssetType, retained->second.c_str(), false).data;
        }
    }
    // ② 按原名查
    if (const auto exact = findXAsset(MaterialAssetType, name.c_str(), false).data)
        return exact;
    // ③ 按名字【子串】选回退
    ++retainedMaterialFallbacks;
    const char *fallback = "mc/mtl_weapon_m16";
    if (name.find("reticle") != npos)                     fallback = "mc/mtl_ret_acog02_acota31ncm_alpha";
    else if (name.find("lens") != npos ||
             name.find("screen") != npos)                 fallback = "mc/mtl_weapon_lens_eot_exps";
    else if (name.find("acog") != npos)                   fallback = "mc/mtl_weapon_acog_2_alpha";
    // ④ 返回回退材质
    return findXAsset(MaterialAssetType, fallback, false).data;
};
```

### 6.1 四个层级

```text
① retained 材质的 cloneSource
② 按原名精确查
③ 按子串选一个回退名
④ 用回退名查
```

### 6.2 ③ 的**四个回退名与三个子串**

```text
默认              mc/mtl_weapon_m16
含 "reticle"      mc/mtl_ret_acog02_acota31ncm_alpha
含 "lens"/"screen" mc/mtl_weapon_lens_eot_exps
含 "acog"         mc/mtl_weapon_acog_2_alpha
```

### 6.3 **顺序是 if/else-if**

```text
"reticle" 优先于 "lens"/"screen" 优先于 "acog"
```

**所以 `mtl_ret_acog02_lens` 会选 "reticle" 分支**（因为它同时含 reticle 与 acog）。

**这是一个有意的优先级** —— 但没有注释说明为什么。

### 6.4 `retainedMaterialFallbacks` 的计数

**在 ① 和 ③ 都 `++`** —— 所以它是"用了回退的次数"。

**而 ② 命中不计**（精确匹配不是回退）。

### 6.5 ①的一个漏洞

```cpp
if (retainedBarrettMaterialNames.contains(name))
{
    const auto retained = retainedBarrettMaterials.find(name);
    if (retained != retainedBarrettMaterials.end())
    {
        ++retainedMaterialFallbacks;
        return findXAsset(...retained->second...).data;      // ← 可能是 nullptr
    }
}
```

**没有检查返回值是否非空** —— 如果 cloneSource 查不到，返回 `nullptr`。

**而调用方：**

```cpp
const auto material = resolveBarrettMaterial(materialName);
if (!material) return failBarrettAssets(SourceAssetMissing, "XModel material is missing: " + materialName);
```

**会失败** —— 但错误消息说"original name is missing"而实际是 "cloneSource is missing"。

**这与 §244 里"八个出口一个返回类型"是同一个问题** —— 四级流程塌缩成一个错误消息。

## 七、`writePointer` 与 **`offset + 4 > size`**

```cpp
const auto writePointer = [&address32](auto &destination, std::size_t offset, const void *pointer) {
    const auto address = address32(pointer);
    if (!address || offset + sizeof(*address) > destination.size()) return false;
    std::memcpy(destination.data() + offset, &*address, sizeof(*address));
    return true;
};
```

### 7.1 两项

```text
address32 成功（非空且 <= 0xFFFFFFFF）
offset + 4 <= size
```

### 7.2 **注意 address32 拒绝 nullptr**

**所以 `writePointer(header, X, nullptr)` 会失败** —— 与 §248 里动画的 `emptyStreamSentinel` 必须显式给一个非空指针是同一约束。

## 八、XModel header 的**九个基本偏移 + 三个 LOD**

```cpp
writePointer(storage->header, 0,   storage->name.data());
writePointer(storage->header, 44,  storage->boneNames.data());
writePointer(storage->header, 48,  storage->parentList.data());
writePointer(storage->header, 52,  storage->quaternions.data());
writePointer(storage->header, 56,  storage->translations.data());
writePointer(storage->header, 60,  storage->partClassification.data());
writePointer(storage->header, 64,  storage->baseMatrices.data());
writePointer(storage->header, 68,  storage->materials.data());
writePointer(storage->header, 312, storage->boneInfo.data());
```

### 8.1 九个偏移

```text
0     名字
44    骨名表
48    父列表
52    四元数
56    平移
60    部分分类
64    基矩阵
68    材质表
312   boneInfo
```

### 8.2 **44..68 是六个连续指针**

```text
44, 48, 52, 56, 60, 64, 68    ← 步长 4，共 7 个
```

**等等：44/48/52/56/60/64/68 是七个**（44 + 6×4 = 68）。

**而代码列了：44, 48, 52, 56, 60, 64, 68 → 七个指针** ✓

**所以 `+44` 到 `+68` 是七个指针**，加上 `+0`（名字）与 `+312`（boneInfo）共九个。

### 8.3 **`+312` 很特殊**

**`boneInfo` 在 312** —— 而其他全在 0..68。

**所以在 68 与 312 之间还有 243 个字节是别的东西**（可能是 LOD 数组的起点 72 —— 见下）。

### 8.4 **LOD 从 72 开始，步长 56**

```cpp
writePointer(storage->header, 72 + lod * 56 + 8,  surfs->second->linked);
writePointer(storage->header, 72 + lod * 56 + 12, surfs->second->name.data());
```

```text
LOD[0].surfs  = +80
LOD[0].name   = +84
LOD[1].surfs  = +136
LOD[1].name   = +140
...
```

### 8.5 与 IW4X 的 `XModel` 布局对照

**IW4X 的 `XModel` 里 `LodInfo lods[4]` 通常从某个偏移开始，每项含 `surfs` 与 `name`。**

**这里 `+8`（surfs）与 `+12`（name）在 56 字节的 LOD 里** —— 所以 LOD 结构的前 8 字节是别的东西（可能是 `dist` 与 `numsurfs` 之类）。

**而 `lod * 56` 且 `+8/+12` ⇒ 一个 LOD 从 `72` 开始，`surfs` 在 `+80`。**

**`72 + 4*56 = 296`，而 `boneInfo` 在 `312`** —— 所以 `296..311` 是第 4 个 LOD 的尾部（`296 + 56 = 352 > 312`）。

**矛盾**：如果 LOD 是 56 字节且从 72 开始，4 个 LOD 会占 `72..295`，而 `boneInfo` 在 312，中间 296..311 是 16 字节的空隙。

**除非 LOD 数组不是 4 个** —— `source.resources.size()` 决定。

**这是一处需要核对的布局。**

## 九、`bundle->skeletons` 的**映射**

```cpp
const auto skeleton = bundle->skeletons.find(source.skeletonKey);
if (skeleton == bundle->skeletons.end())
    return failBarrettAssets(InvalidDefinition, "XModel skeleton is missing: " + source.skeletonKey);

storage->parentList = skeleton->second.parentList;
storage->quaternions = skeleton->second.quaternions;
storage->translations = skeleton->second.translations;
storage->partClassification = skeleton->second.partClassification;
storage->baseMatrices = skeleton->second.baseMatrices;
```

### 9.1 五个数组来自**骨架**，两个来自**模型**

```text
骨架（skeletonKey 索引）    parentList / quaternions / translations / partClassification / baseMatrices
模型                        boneInfo / （boneNames 从骨架）
```

### 9.2 这是一次**共享**

**多个模型可以指向同一个 `skeletonKey`** ⇒ 共用五份大数组。

**而 `storage->parentList` 等是 `vector<byte>` 的**拷贝** ⇒ 每个模型都复制一份。**

**所以"共享"在 bundle 层面，而发布层面是每模型一份独立拷贝。**

**这是内存的浪费但保证了地址稳定**（每个模型的 `header` 指向自己的拷贝）。

### 9.3 `boneNames` 从骨架来而 `boneInfo` 从模型来

**这两个是不同的东西**：

```text
boneNames   字符串 id 数组（interned）
boneInfo    每骨骼的附加信息
```

**所以一个模型可以有自己的 boneInfo 但用共享的骨骼结构。**

## 十、XModel 的**五步发布**

```text
① 从 model.resources 收集全部 surf 名 ⇒ resourceNames（set，去重）
② 逐个 surf：构造 header（+0 名字）+ 链接或复用 + 验证
③ 逐个 animation：...（在 ② 之前）
④ 逐个 model：骨架 + 材质 + 九个指针 + LOD + 链接 + 验证
⑤ 全部 model 再跑一遍 XModelStreamQueue
```

### 10.1 **顺序依赖**

```text
surfs 必须在 models 之前（因为 models 的 header 要写 surfs->linked）
animations 在 surfs 之前（顺序上）
images 在最前（因为 materials 要引用 image 地址）
materials 在 models 之前（models 要写 materials.data()）
```

### 10.2 完整依赖图

```text
images
  ↓
materials（引用 image 指针）
  ↓
animations（独立）
surfs（独立）
  ↓
models（引用 surfs->linked、materials）
  ↓
stream queue
```

## 十一、`tryQueueXModelStream(..., storage->linked, 0, queueFault)`

```cpp
for (const auto &storage : publishedBarrettAssets.models)
    if (!tryQueueXModelStream(module_ + XModelStreamQueueRva, storage->linked, 0, queueFault))
```

### 11.1 第三个参数是 0

**`0` 可能是"立即"或"最高优先级"** —— 未标注。

**而 `XModelStreamQueueRva = 0x09A2B0`，前缀 `{ 55, 8B, EC, A1 }`** —— `A1` 读全局。

## 十二、关键结论

1. **`pointerPresence` 是九位掩码**，三种状态（不写 / 写 sentinel / 写真实指针）。
2. **XAnim header 从 bundle 原样拷贝，只覆盖九个指针 + 名字** —— 增量覆盖。
3. **notify 每项 8 字节但只写前 2 字节** —— 其余保持原值。
4. **XAnim 的链接后验证只用 `readableSpan(88)`** —— 放弃了指针相等性，与其他四组不一致。
5. **XModelSurfs 的 `header` 是我们零构造的**（只写 `+0`），不是从 bundle 拷 —— 与其余不同。
6. **材质四级回退链**：retained-cloneSource → 原名 → 子串选名 → 查回退名。
7. **回退名的 if/else-if 优先级**（reticle > lens/screen > acog）无注释说明。
8. **① 分支不检查 `findXAsset` 是否为空**，但调用方会失败且消息说错原因。
9. **`writePointer` 拒绝 nullptr** ⇒ 空数组必须用 sentinel。
10. **XModel 九个基本指针：`0`, `44..68`（七个）, `312`**；LOD 从 `72` 起、步长 `56`、`+8/+12`。
11. **骨架数据共享在 bundle 层但发布层每模型一份拷贝**。
12. **发布顺序是严格依赖链**：images → materials → surfs → models → stream。

## 十三、未闭合点

- `XModelSurfs` 的 48 字节 header 是否足够（surf 列表与计数是否为零导致问题）。
- LOD 步长 56 × N 与 `boneInfo` 在 312 之间的布局空隙。
- `tryQueueXModelStream` 第三参数 `0` 的语义。
- XAnim 与其他四组的验证不一致。
- `EngineBindings.cpp` 12850 行之后未读取。
