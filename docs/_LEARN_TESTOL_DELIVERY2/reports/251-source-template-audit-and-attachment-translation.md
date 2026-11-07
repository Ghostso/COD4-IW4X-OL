# 251 · 模板审计的四类行、`0x51/0x52/0x53` 的 alpha 镜头三字节、附件的 `(id, model)` 配对表

## 一、范围

本报告学习 `EngineBindings.cpp` 13597–14050 行。

## 二、`hex` 与 `safeName` 的两个 lambda

### 2.1 `hex` 的五个分支

```cpp
const auto hex = [](const void *address, std::size_t length) {
    if (!address || !readableSpan(address, length)) return std::string{ "<unreadable>" };
    static constexpr char Digits[] = "0123456789abcdef";
    std::string result(length * 2, '0');
    for (i) { result[2i] = Digits[bytes[i]>>4]; result[2i+1] = Digits[bytes[i]&0xF]; }
    return result;
};
```

**`nullptr` 与"不可读"合并为 `<unreadable>`** —— 与 `safeName` 的三分不同。

### 2.2 `pointerText` 是 `0x%08X`

```cpp
snprintf(value, sizeof(value), "0x%08X", (unsigned)(uintptr_t)address);
```

**`reinterpret_cast<uintptr_t>` 再 `static_cast<unsigned>`** —— 在 32 位进程里无损。

### 2.3 `safeName` 的**三态**

```text
nullptr       ⇒ "<null>"
不可读         ⇒ "<unreadable>"
首字节为 0     ⇒ "<empty>"
其它           ⇒ readCString(name, 256)
```

**四种（含正常）** —— 而 `readCString` 自己可能失败 ⇒ `value_or("<unreadable>")` 是第五种。**但那样与"不可读"同名**。

## 三、**TSV 的八列**

```cpp
output << "kind\towner\tindex\tname\taddress\theader_hex\tdata\n";
```

```text
kind        行类别
owner       归属（材质名/直接名）
index       pool 下标或纹理序号
name        名字
address     指针
header_hex  头部十六进制
data        附加信息
```

**七列**（我数错了）——`kind / owner / index / name / address / header_hex / data`。

### 3.1 **五种 `kind`**

```text
material-candidate    池扫描发现的疑似瞄具材质
image                 GfxImage
material              五个控制材质的本体
texture-table         纹理表不可读
texture               单个纹理行
```

## 四、**池扫描的 `<unreadable>` 与 `break`**

```cpp
for (index = 0; index < 120000; ++index)
{
    const auto *const entry = assetEntries + index * 28;
    if (!readableSpan(entry, 28)) break;       // ← 【break 不是 continue】
    ...
}
```

### 4.1 `break` 的理由

**池是连续的 120,000 × 28 = 3,360,000 字节**。**一旦某一行不可读，后面都不可读** ⇒ 可以停。

**而 §247/§249 的 `assetZoneForHeader` 用 `return nullopt`** —— 那里也在第一个不可读处停止 ✓ 一致。

## 五、`alphaLensCounts` 的三字节（本组最重要的一段）

```cpp
const auto alphaLensCounts =
    material[0x51] == 3 && material[0x52] == 2 && material[0x53] == 4;
```

### 5.1 三个字节

```text
+0x51 = 3
+0x52 = 2
+0x53 = 4
```

### 5.2 而 §250 说 `+0x51` 是**纹理计数**

**"texture count at +0x51"**

**所以 `+0x51 = 3` 意味着"这个材质有 3 个纹理"。**

**而 `+0x52 = 2` 与 `+0x53 = 4` 是什么？**

**`MaterialTextureRowSize = 12`** 且**纹理表在 `+0x5C`**（指针，4 字节）。

**所以 `+0x52` 与 `+0x53` 在指针（`+0x5C..0x5F`）之前，是别的单字节字段。**

### 5.3 一个可能：**它们是 alpha 版材质的三个计数**

**`alphaLensCounts` 这个名字说明"alpha 的镜头计数"** —— 所以这是一个**用 alpha 布局的字节模式**来识别"这是 alpha 格式的材质"。

**三个连续字节 `3, 2, 4`** —— 一个足够特殊的模式（1/16M 的随机概率）。

### 5.4 而它用于**池扫描的候选筛选**

```cpp
if (name 不含 scope/lens/optic/thermal/acog  &&  !alphaLensCounts) continue;
```

**所以一个材质即使名字不含关键词，只要三字节匹配也会被列入候选。**

**这是一个"名字之外的第二条识别路径"** —— 因为：

```text
// several alpha/IW4 material names are absent from OLfinal common_mp.
```

**"若干 alpha/IW4 的材质名在 OLfinal 的 common_mp 里不存在"** ⇒ 所以按名字找不到，只能按形状找。

## 六、五个控制材质

```cpp
static constexpr std::array<const char *, 5> Materials{
    "mc/mtl_weapon_m16",                      // 普通不透明武器材质
    "mc/mtl_weapon_acog_2_alpha",             // 瞄具本体
    "mc/mtl_ret_acog02_acota31ncm_alpha",     // 分划
    "mc/mtl_weapon_lens_eot_exps",            // 半透明镜片
    "mc/mtl_wea_javelin_javelin_lens",        // 世界镜片（对照）
};
```

### 6.1 三类 + 一个对照

```text
// These are the three final rendering categories the alpha bundle needs:
// ordinary opaque weapon material, scope body, and translucent lens.
// The world lens is a control for a view/world technique split.
```

```text
mtl_weapon_m16               普通不透明
acog_2_alpha                 瞄具本体
ret_acog02_..._alpha         分划
lens_eot_exps                半透明镜片
javelin_lens                 世界镜片 —— 【对照】
```

### 6.2 这四个名字**正是 §248 的四级回退链里的**

```text
mc/mtl_weapon_m16                    ← 默认回退
mc/mtl_ret_acog02_acota31ncm_alpha   ← reticle 回退
mc/mtl_weapon_lens_eot_exps          ← lens/screen 回退
mc/mtl_weapon_acog_2_alpha           ← acog 回退
```

**完全一致** ✓ —— 而第五个（`javelin_lens`）只在这里出现（审计用），不在回退链里。

**这是一个干净的双向印证** —— 审计脚本查的正是回退链要用的东西。

## 七、**水面语义 `11` 的特殊处理**

```cpp
const auto semantic = row[MaterialTextureSemanticOffset];      // row[7]
const auto *const image = semantic == WaterSemantic(11)
    ? nullptr
    : *(const void *const *)(row + MaterialTextureImageOffset);  // row + 8
```

### 7.1 为什么"水面"跳过 image

**`semantic == 11` ⇒ 不读 image 指针** —— 因为：

**在这个 build 里，水面语义的纹理行的 `+8` 不是 GfxImage 指针**（可能是 water 参数）。

**这是一个"按语义分派"的设计** —— 而不是"总是当成指针"。

### 7.2 三处一致

```text
§250  WaterSemantic = 11
§251  同一个 11
§251  imageName = "<water>"
```

**而 §247 里 `slotHeader` 是 8 字节（`+0..7`）、`+8` 是 image** —— 所以 `+7` 的语义值 11 会改变 `+8` 的解释。

## 八、`writeImage` 的**去重**

```cpp
std::set<const void *> writtenImages;
const auto writeImage = [&](std::string_view owner, const void *image) {
    if (!image || !writtenImages.insert(image).second) return;
    ...
    ++imageCount;                  // ← 【只在真正写入时加】
};
```

### 8.1 `insert().second` 是"首次插入"

**所以同一张图被多个材质引用只写一次** ✓

**而 `imageCount` 是"唯一图片数"** ✓ 日志里叫 `uniqueImages` ✓

### 8.2 而 `missingCount` 在 `detail_gray_01` 缺失时 `++`

```cpp
const auto *const detailImage = findXAsset(GfxImageAssetType, "detail_gray_01", false).data;
if (detailImage) writeImage("direct:detail_gray_01", detailImage);
else ++missingCount;
```

**为什么特别记录 `detail_gray_01`**：

```text
// The alpha bundle reuses this final image by name. Record it even if
// none of the four material controls happens to reference it.
```

**"alpha bundle 按名字复用这张最终图片"** —— 所以它是**独立于材质引用**的依赖。

**这是一个"隐藏依赖"的发现** —— 只有真的跑起来才会知道需要它。

## 九、GfxImage 的**两段十六进制**

```cpp
loadDefHex    = hex(loadDef, 16);
memcpy(&dataSize, loadDef + 0x0C, 4);
payloadHeadHex = hex(loadDef + 16, min(dataSize, 64));
```

### 9.1 三个量

```text
loadDef 的 16 字节
loadDef + 0x0C 处的 dataSize
loadDef + 16 起的 64 字节载荷头
```

### 9.2 **`loadDef + 0x0C` 是 dataSize 而载荷从 `+16` 开始**

**⇒ `loadDef` 是 `{ ...12 字节..., dataSize(4), payload[...] }`**

**而 `dataSize` 描述的是 `+16` 之后的载荷长度。**

**这与 §247 里 `loadDef` 是 `std::array<std::byte,16>` 就**矛盾**了** —— 如果载荷从 `+16` 开始而 `loadDef` 只有 16 字节，那载荷必然在 `loadDef` **之外**。

**所以 `SV_BuildOlfinalAlphaBarrettImage` 的 `loadDef` 参数（16 字节数组）只是**头部**，而载荷是它后面紧跟的内存。**

**这是一处推测** —— 但 `hex(loadDef + GfxImageLoadDefSize, payloadHeadSize)` 的写法明确地**越过了 16 字节**。

**所以 `loadDef` 实际是一个**更大的块**的前 16 字节。**

## 十、`attachmentModelResolutionAvailable`：**五个条件的读**

```cpp
if (!baseWeaponAssetIndex || baseWeaponAssetIndex >= BaseWeaponCount || !attachmentIndex)
    return false;
const auto *mappingCount   = module_ + PerWeaponAttachmentCountsRva + baseWeaponAssetIndex;
const auto *mappings       = (const uint32*)(module_ + AttachmentMappingsRva) + baseWeaponAssetIndex * 64;
const auto *attachmentModelCount = (const uint16*)(module_ + AttachmentModelCountRva);
const auto *noneModel      = (const uint16*)(module_ + NoneAttachmentModelIndexRva);
if (!readableSpan(mappingCount, 1) || !readableSpan(attachmentModelCount, 2) ||
    !readableSpan(noneModel, 2) || *mappingCount > 64 ||
    !readableSpan(mappings, *mappingCount * 4))
    return false;
```

### 10.1 **`64` 是每武器最大附件数**

**而 §248 里 `AttachmentCount = 6`** —— 两个不同的数：

```text
64  映射表容量（每武器 64 对，128 个 u16）
6   线格式里的附件槽数
```

### 10.2 **`mappings` 是 `uint32[64]` 的视图**

**而 §251 后面的注释说："128 u16 per weapon is 64 (attachment, model) pairs"**

**所以一个 `uint32` = 两个 `uint16` = `(attachment, model)`。**

**低 16 位是 `attachment`，高 16 位是 `model`。**

### 10.3 查找

```cpp
const auto mapping = find_if(mappings, mappings + *mappingCount, [attachmentIndex](uint32 v) {
    return (uint16)v == attachmentIndex;                     // ← 【低 16 位】
});
auto modelIndex = *noneModel;
if (mapping != end) modelIndex = (uint16)(*mapping >> 16);   // ← 【高 16 位】
if (modelIndex >= *attachmentModelCount) return false;
const auto *model = (const void *const *)(module_ + AttachmentModelDefinitionsRva) + modelIndex;
return readableSpan(model, 4) && *model;
```

### 10.4 **"找不到 ⇒ 用 `noneModel`"**

**这是一个重要语义**：**"不支持"与"支持但用 none 模型"通过 `modelIndex` 是否等于 `noneModel` 区分？**

**不** —— 代码**不**区分。**无论找到与否，最后都检查 `modelIndex < *attachmentModelCount` 且 `*model` 非空。**

**所以：如果 `noneModel` 有效，那么"不支持的附件"也会返回 true。**

### 10.5 这与函数名 **`attachmentModelResolutionAvailable`** 一致

**"这个附件的【模型】能否解析"** —— 而不是"这个附件是否被支持"。

**而 `attachmentSupportedByWeapon`（后面）才有"是否是 none 模型"的判断。**

**两个函数问的问题不同** ✓ —— 而 §248 里"§187l 的失败"就是混淆了这两者。

## 十一、`internedAttachmentName` 的 `0x3FFD` 上界

```cpp
if (!module_ || !attachmentId || attachmentId >= 0x3FFD) return nullopt;
const auto *const slot = (const char *const *)(module_ + InternedStringTableRva) + attachmentId;
```

### 11.1 `0x3FFD = 16381`

**而 `0x3FFF = 16383`、`0x3FFE = 16382`。**

**所以上界是 `16381`** —— 一个**奇怪的精确值**。

**注释没有解释**。这可能是"最大 id + 1"，而 `0x3FFD`/`0x3FFE`/`0x3FFF` 是保留值。

### 11.2 而 `attachmentId == 0` 被拒绝

**"0 = 无效"** ✓ 与 §239 的 `weaponId` 三重判据一致。

### 11.3 名字读 128 字节

```cpp
return readCString(*slot, 128);
```

**与 §248 里 `readCString(namePointer, 128)` 一致** —— 128 是本文件里字符串的默认上限。

## 十二、`attachmentIdForWeapon`：**两遍扫描**（本组第二重要）

```cpp
// Section 187h. Two passes over word_198C0A0[128 * weapon], the same
// (nameId, modelIndex) pair table sub_42F9B0 walks:
//   1. find the MODEL the canonical id names, anywhere it is registered;
//   2. find the entry in the TARGET weapon carrying that same model.
// Both RMRs are model 17, both extended magazines model 10, so the model is
// what survives the change of weapon while the id does not.
```

### 12.1 核心洞察

**"两个 RMR 都是模型 17，两个扩容弹匣都是模型 10。"**

**"所以**模型**在换武器时存活，而**id**不存活。"**

### 12.2 两个实测对

```text
RMR            model 17
扩容弹匣        model 10
```

### 12.3 两遍

```cpp
// 遍 1：全表扫，找 canonicalAttachmentId 对应的 model
std::optional<uint16> model;
for (weapon = 1; weapon < BaseWeaponAssetCount && !model; ++weapon)
    for (row : entriesFor(weapon))
        if ((uint16)row == canonicalAttachmentId) { model = (uint16)(row >> 16); break; }

// 遍 2：在目标武器里找同一个 model
for (row : entriesFor(targetWeaponAssetIndex))
    if ((uint16)(row >> 16) == *model) return (uint16)row;
return nullopt;
```

### 12.4 这是一个**按语义换编号**的解析

**同一个"红点瞄准镜"在不同武器上有不同的附件 id，但共用同一个模型。**

**所以"翻译 id"的正确做法是：id → model → 目标武器上该 model 的 id。**

**这与 §240 里"翻译后的 id 造出一个客户端不共享索引的变体 ⇒ 拒绝每颗子弹"是**同一个问题的解**。**

### 12.5 而遍 1 是**全表 1300 武器 × 最多 64 行**

**最坏 83,200 次比较** —— 而这是**每次解析附件都做**。

**这是一个性能热点** —— 但没有缓存。

## 十三、`attachmentTableCountForWeapon` 的**零语义**

```cpp
// byte_1988638[weapon] -- the per-weapon attachment count sub_42F9B0 bounds its
// walk with and sub_42F910 increments as it registers. Zero means the weapon has
// registered nothing, which is a very different statement from "this attachment
// is not supported". Section 187.
```

### 13.1 两个断言

```text
0  = 这个武器【什么附件都没注册】
≠  "这个附件不被支持"
```

### 13.2 两个 RVA 的名字

```text
PerWeaponAttachmentCountsRva  ← 注释叫 byte_1988638
AttachmentMappingsRva         ← 注释叫 word_198C0A0
```

**注意 `0x1988638` 与 `0x198C0A0`** —— 相差 `0x39A68`。

## 十四、`attachmentSupportedByWeapon` 的**反汇编对照**

```text
out.exe sub_42F9B0, the engine's own lookup, exactly:
    v2 = byte_1988638[weapon];                       per-weapon COUNT
    if (!v2) return dword_198B8A0[word_19DDECC];     NONE model
    for (i = &word_198C0A0[128*weapon]; *i != attachment; i += 2)
        if (++v3 >= v2) return dword_198B8A0[word_19DDECC];   NOT FOUND
    return dword_198B8A0[i[1]];                      FOUND
```

### 14.1 五个要点

```text
1. byte_1988638[weapon]   每武器计数
2. 计数为 0 ⇒ 返回 none model
3. word_198C0A0[128*weapon]  起点（128 个 u16）
4. i += 2                    步长【2 个 u16】= 一对
5. i[1]                      模型在第二个 u16
```

### 14.2 **与 `uint32[64]` 视图完全一致**

```text
`i += 2` 的 u16 步长  =  `uint32` 步长 1
`i[1]`（第二个 u16）  =  `row >> 16`（高 16 位）
`*i`（第一个 u16）    =  低 16 位
```

**✓ 三种表达同一个布局。**

### 14.3 那句关键推论

```text
// sub_42F910 never registers a pair whose model is the none model, so anything
// present here is genuinely supported.
```

**"`sub_42F910` 从不注册一对模型等于 none 模型的项，所以这里存在的任何项都是真正被支持的。"**

**这是 `attachmentSupportedByWeapon` 与 `attachmentModelResolutionAvailable` 的区别所在**：

```text
attachmentModelResolutionAvailable   找不到 ⇒ 用 noneModel ⇒ 可能返回 true
attachmentSupportedByWeapon          找不到 ⇒ 【返回 false】
```

## 十五、关键结论

1. **`hex` 把 `nullptr` 与不可读合并**，而 `safeName` 分三种。
2. **池扫描在第一个不可读处 `break`** —— 因为池是连续的。
3. **`alphaLensCounts` 用 `+0x51/+0x52/+0x53` 的 `3/2/4` 作第二识别路径** —— 因为 alpha 材质名在 OLfinal 里不存在。
4. **五个控制材质与 §248 的四级回退链完全一致**（第 5 个是对照，不在回退链）。
5. **水面语义 11 ⇒ 不读 image 指针** —— `+8` 有两种解释。
6. **`writeImage` 按指针去重**，`imageCount` 是唯一图片数。
7. **`detail_gray_01` 是独立于材质引用的隐藏依赖**。
8. **`loadDef` 实际是一个更大块的前 16 字节** —— 载荷从 `+16` 开始，`+0x0C` 是载荷长度。
9. **`attachmentModelResolutionAvailable` 与 `attachmentSupportedByWeapon` 问的是不同问题** —— 前者"模型能否解析"，后者"是否被支持"。
10. **附件翻译的正确做法是 id → model → 目标武器上该 model 的 id** —— 因为"模型在换武器时存活，id 不存活"。
11. **`RMR = model 17`、`扩容弹匣 = model 10`** 两个实测对。
12. **`uint32[64]` 视图与 `u16` 对表是同一布局的三种表达**。
13. **遍 1 最坏 83,200 次比较且无缓存** —— 性能热点。

## 十六、未闭合点

- `internedAttachmentName` 的上界 `0x3FFD` 无解释。
- `attachmentIdForWeapon` 遍 1 的全表扫描无缓存。
- `loadDef` 是"更大块的前 16 字节"这一推测未直接证实。
- `EngineBindings.cpp` 14050 行之后未读取。
