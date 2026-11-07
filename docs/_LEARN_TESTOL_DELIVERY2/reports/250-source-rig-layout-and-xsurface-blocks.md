# 250 · 骨骼审计的 `boneCount-rootCount`、`XSurface` 的 0x54 布局与四种数据块、材质/GfxImage 的两代偏移对照

## 一、范围

本报告学习 `EngineBindings.cpp` 13222–13650 行。

## 二、`auditAlphaWeaponModelPointers` 的十个偏移

```cpp
constexpr std::array<std::size_t, 10> ModelOffsets{ 16, 20, 24, 28, 32, 36, 40, 44, 48, 52 };
```

### 2.1 十个连续偏移

```text
+0x10, +0x14, +0x18, +0x1C, +0x20, +0x24, +0x28, +0x2C, +0x30, +0x34
```

### 2.2 与 §249 的对照

**§249 用的是 `+0x10`（ViewModel）与 `+0x18`（WorldModel）** —— 而这里把 `+0x10` 到 `+0x34` **全部**打印出来。

**所以这十个就是"2 个 view model + 2 个 world model + 6 个辅助模型"**（§249 的 "the alternate element and the six later auxiliary models"）。

```text
+0x10  viewModel[0]      ← 我们替换
+0x14  viewModel[1]      ← 源所有
+0x18  worldModel[0]     ← 我们替换
+0x1C  worldModel[1]     ← 源所有
+0x20 .. +0x34           六个辅助（源所有）
```

**`4 + 6 = 10`** ✓ —— **完全吻合 §249 的"alternate element and the six later auxiliary models"。**

### 2.3 而 §249 说 "OLfinal reduced the two arrays to two entries apiece at +0x10/+0x14 and +0x18/+0x1C"

**所以 `+0x10/+0x14` 是 viewModel[0..1]，`+0x18/+0x1C` 是 worldModel[0..1]。**

**而 `+0x20..+0x34` 是六个辅助模型** —— 这六个不在"两个数组"里，是独立的字段。

**这是一个重要的布局澄清。**

## 三、`PNG` 风格的报告格式

```cpp
std::string report = "alpha weapon model audit weapon=cheytac_mp";
for (const auto offset : ModelOffsets)
{
    const void *model{}; std::memcpy(&model, definition + offset, sizeof(model));
    std::optional<std::string> name;
    if (readableSpan(model, sizeof(const char *)))
    {
        const char *namePointer{}; std::memcpy(&namePointer, model, sizeof(namePointer));
        name = readCString(namePointer, 128);
    }
    field = " +0x%02zX=%s@%p", offset, name ? name : model ? "<unreadable>" : "<null>", model;
}
```

### 3.1 **三态**

```text
name 有值          ⇒ 打印名字
model 非空但读不出 ⇒ "<unreadable>"
model 为空         ⇒ "<null>"
```

### 3.2 **模型名在模型对象的 `+0`**

```cpp
std::memcpy(&namePointer, model, sizeof(namePointer));
```

**所以 XModel 的 `+0` 是名字指针** —— 与 §248 里 `writePointer(header, 0, name.data())` 一致 ✓

**而这个审计**验证**了那个写入是正确的位置。**

## 四、`auditModelTable`：**列 3 是 view 模型名**

```cpp
const auto *const table = readStringTable(..., "mp/coWeapModels/<name>.csv", 4);
const auto row = findStringTableRow(*table, weaponName);
const auto viewName = readStringTableCell((*row)[3]);       // ← 【列 3】
const auto *const model = findXAsset(XModelAssetType, viewName->c_str(), false).data;
if (!readableSpan(model, 360)) return nullopt;              // ← 【360】
```

### 4.1 两个信息

```text
mp/coWeapModels/<weapon>.csv 的【列 3】 = view 模型名
XModel 尺寸 = 360
```

### 4.2 而 `readStringTable(..., 4)` 的 4 是**期望列数**

**`4` 是 "expected columns"** —— 与 §246 里 `readStringTable(..., targetPath, 4)` 同一个数。

## 五、`auditRig`：**骨骼布局的完整解码**（本组最重要的一段）

### 5.1 三个**头部字节**

```cpp
const auto boneCount    = (uint8)model[4];
const auto rootCount    = (uint8)model[5];
const auto surfaceCount = (uint8)model[6];
```

```text
+4   boneCount     uint8
+5   rootCount     uint8
+6   surfaceCount  uint8
```

### 5.2 五个**数组指针**

```cpp
memcpy(&boneNames,   model + 44, 4);
memcpy(&parents,     model + 48, 4);
memcpy(&quaternions, model + 52, 4);
memcpy(&translations,model + 56, 4);
memcpy(&baseMatrices,model + 64, 4);
```

```text
+44  boneNames       uint16*
+48  parents         uint8*
+52  quaternions     int16*
+56  translations    float*
+64  baseMatrices    float*
```

**注意 `+60`（§248 里是 `partClassification`）在这五个里**缺了**。**

### 5.3 **`childCount = boneCount - rootCount`**

```cpp
const auto childCount = boneCount >= rootCount ? boneCount - rootCount : 0;
```

### 5.4 而**数组长度用的是 `childCount` 或 `boneCount`**

```cpp
readableSpan(boneNames, boneCount * sizeof(uint16))           // ← boneCount
(childCount &&
    (!readableSpan(parents, childCount) ||                    // ← childCount
     !readableSpan(quaternions, childCount * 4 * sizeof(int16)) ||   // ← childCount
     !readableSpan(translations, childCount * 3 * sizeof(float))))   // ← childCount
readableSpan(baseMatrices, boneCount * 8 * sizeof(float))     // ← boneCount
```

### 5.5 **五项长度的对应关系**

```text
boneNames      boneCount × 2        每骨骼一个名字
parents        childCount × 1       每个【非根】骨骼一个父索引
quaternions    childCount × 4 × 2   每个非根骨骼 4 个 int16
translations   childCount × 3 × 4   每个非根骨骼 3 个 float
baseMatrices   boneCount × 8 × 4    每骨骼一个 3x4（或 4x4 压缩）
```

### 5.6 这是 **IW4X 的 XModel 骨骼布局**

```text
根骨骼不需要父/四元数/平移（它们就在原点）
⇒ 所以这三个数组是 childCount 长而不是 boneCount 长
```

**而 `baseMatrices` 是 `boneCount × 8 × 4 = 32 字节/骨骼`** —— 即 **8 个 float = 2 行 × 4**（一个 3x4 矩阵的第二与第三行？或压缩的 4x4）。

**`matrix[4], matrix[5], matrix[6]`（在 `bindT` 里）** ⇒ 所以 `matrix[0..3]` 是行 0，`matrix[4..7]` 是行 1。

**只打印 `[4],[5],[6]`** —— 即**第二行的前三个** = 平移分量 ✓

**所以 `baseMatrices` 是 `float[boneCount][8]` 而平移在 `[4..6]`** —— 这是一个 2×4 的仿射压缩（行 0 是 3x3 旋转的压缩，行 1 的第 4 个是平移）。

**等等**：`[4],[5],[6]` 是平移而 `[7]` 未用 —— 这正是 **IW4X `DObj`/`DSkel` 用的 `float[3][4]` 布局的压缩版**（实际只存 2 行因为第 3 行是常量 `0,0,0,1`）。

### 5.7 审计"rig"字符串的两个部分

```cpp
rig += " names=";
for (index < boneCount) {
    rig += name or "#N";
    if (index >= rootCount) rig += "<" + parents[index - rootCount];    // ← 【未闭合的 <】
}
rig += " bindT=";
for (index < boneCount) {
    const auto *matrix = baseMatrices + index * 8;
    transform = "%zu:%.3f,%.3f,%.3f", index, matrix[4], matrix[5], matrix[6];
}
```

### 5.8 那个 `<` **没有闭合**

```cpp
rig += "<" + std::to_string(parents[index - rootCount]);
```

**只写了 `<N` 而没有 `>`** —— 所以输出会是 `boneA<0,boneB<1`。

**这是一个明显的格式缺陷** —— 但不影响语义（仍是可解析的）。

### 5.9 `parents[index - rootCount]` 的**索引平移**

**根骨骼（`index < rootCount`）不参与；非根骨骼的父索引从 `parents[0]` 开始。**

**所以 `parents[]` 的下标是"非根骨骼的序号"。**

**这是一个关键约定** —— 而它导致 `parents` 数组比 `boneNames` 短。

## 六、`auditModelTable` 失败的**双输出**

```cpp
const auto cheytacRig = auditModelTable("cheytac_mp");
const auto barrettRig = auditModelTable("barrett_mp");
if (!cheytacRig || !barrettRig)
{
    write("alpha weapon rig audit waiting cheytac=" + has_value() + " barrett=" + has_value());
    return;                                  // ← 【不置 complete】
}
```

### 6.1 **它不设置 `alphaWeaponModelAuditComplete_`**

**所以下次进入会重试** ✓

**这是一个"等待资产"的语义** —— 与 §250 后面 `auditXModelSurfaces` 的 `!surfaceCount || !surfaces` 直接 `return`（也不置 complete）同族。

### 6.2 与 §246/§247 的 `attempted = true` **相反**

```text
§247  attempted 在尝试【之前】置 true     ⇒ 失败永不重试
§250  只在成功时置 complete               ⇒ 失败重试
```

**同一个文件里两种相反的策略** —— 而 §250 的这个更合理（因为资产可能晚到）。

## 七、`auditXModelSurfaces` 的**十六个常量**

```cpp
XModelLod0ModelSurfsOffset = 0x50
XModelSurfsSize            = 0x30
XModelSurfsNameOffset      = 0x00
XModelSurfsSurfacesOffset  = 0x04
XModelSurfsCountOffset     = 0x08
XSurfaceSize               = 0x54
XSurfaceVertCountOffset    = 0x04
XSurfaceTriCountOffset     = 0x06
XSurfaceBlendCountsOffset  = 0x14
XSurfaceBlendPointerOffset = 0x1C
XSurfaceVertexPointerOffset= 0x20
XSurfaceRigidListCountOffset = 0x28
XSurfaceRigidListPointerOffset = 0x2C
XSurfaceIndexPointerOffset = 0x10
PackedVertexSize           = 0x20
RigidVertListSize          = 0x0C
MaximumSurfaceCount        = 64
```

### 7.1 **`XModelLod0ModelSurfsOffset = 0x50`**

**`0x50 = 80`** —— 而 §248 里 LOD 从 `72` 开始、`surfs` 在 `+8` ⇒ **`72 + 8 = 80 = 0x50`** ✓

**两条独立的计算得到同一个数** —— 这是一次交叉验证。

### 7.2 `XModelSurfsSize = 0x30 = 48`

**与 §248 的 `std::array<std::byte, 48> header` 完全一致** ✓

**而 §249 里 `+4`（surfaces）与 `+8`（count）也被这里确认** ✓

### 7.3 `XSurface` 的 **0x54 = 84 字节**布局

```text
+0x04  vertCount      uint16
+0x06  triCount       uint16
+0x10  indexData      指针
+0x14  blendCounts    4 × uint16 (8 字节)
+0x1C  blendData      指针
+0x20  vertexData     指针
+0x28  rigidListCount uint32
+0x2C  rigidListData  指针
```

**注意 `+0x00` 未列出** —— 所以前 4 字节是别的东西（可能是 flags 或一个指针）。

## 八、`blendWordCount` 的**权重计算**

```cpp
const auto blendWordCount =
    blendCounts[0] + 3u * blendCounts[1] + 5u * blendCounts[2] + 7u * blendCounts[3];
const auto blendBytes = 2u * blendWordCount;
```

### 8.1 四个权重

```text
blendCounts[0]  × 1
blendCounts[1]  × 3
blendCounts[2]  × 5
blendCounts[3]  × 7
```

### 8.2 这是 IW4X 的 `XSurface` 混合权重布局

**`blendCounts[i]` = "有 i+1 个混合影响的顶点数"** —— 而每个这样的顶点需要：

```text
1 个影响   ⇒ 1 个 uint32（打包的骨骼索引+权重）⇒ 2 个 word
2 个影响   ⇒ 3 个 uint32
3 个影响   ⇒ 5 个 uint32
4 个影响   ⇒ 7 个 uint32
```

**所以 `blendWordCount` 是 **uint32 个数**，而 `blendBytes = 2 × blendWordCount`** —— 等等，如果每个是 uint32（4 字节），应该是 4×。

**但 `blendBytes = 2u * blendWordCount`** ⇒ **每个 "word" 是 2 字节**。

**所以 `blendData` 是 `uint16` 数组** —— 即打包的骨骼索引/权重是 16 位。

**这与 IW4X 的 `r.vertexInfo` 打包不同**（那里通常是 uint32）。

**这是一个 build 特有的布局** —— 值得指出。

### 8.3 四个数据块

```text
blendData       blendBytes
vertexData      vertCount × 0x20
rigidListData   rigidListCount × 0x0C
indexData       triCount × 6
```

**`indexBytes = triCount * 6`** ⇒ **每三角 6 字节 = 3 × uint16** ✓

**`PackedVertexSize = 0x20 = 32`** —— 32 字节一个顶点。

**`RigidVertListSize = 0x0C = 12`** —— 12 字节一个刚性顶点列表。

## 九、**"fastfile 占位符"的等待**（本组第二重要）

```cpp
// XModelSurfs is a fastfile placeholder until the loose main/models
// resource streams. Keep waiting instead of consuming the one-shot
// audit before the control has ever been rendered.
if (!surfaceCount || !surfaces) return;
```

### 9.1 三层

```text
1. XModelSurfs 在 fastfile 里是【占位符】
2. 直到松散的 main/models 资源流到达才填上
3. ⇒ 若 count/surfaces 为空，【继续等待】而不是消耗一次性的审计
```

### 9.2 与 §249 的**15 秒等待**同族

**§249**：等 `bit3 at +349` 与 `surfs +4/+8` 非零
**§250**：等 `surfaceCount` 与 `surfaces` 非零

**两个都在等"松散的资源流"，而两个的判据都是"字段非零"。**

### 9.3 "one-shot audit" 的语义

**`xmodelSurfaceAuditComplete_` 是 `atomic<bool>`** —— 置 true 后永不重跑。

**所以如果它在占位符阶段跑，就会消耗掉唯一的一次机会。**

**"在控件被渲染之前"** —— 说明这个审计依赖某个 UI 元素被绘制过（riot shield 的 viewmodel）。

## 十、`OLXSAUD1` 的**二进制格式**

```cpp
output.write("OLXSAUD1", 8);        // ← 魔数
writeU32(1);                        // ← 版本
writeU32(surfaceCount);
writeU32(XSurfaceSize);
writeU32(name->size());
output.write(name->data(), name->size());

for (index < surfaceCount)
{
    writeU32(XSurfaceSize);
    output.write(surface, XSurfaceSize);      // ← 【原始 84 字节】
    writeSpan(blendData, blendBytes);
    writeSpan(vertexData, vertexBytes);
    writeSpan(rigidListData, rigidListBytes);
    writeSpan(indexData, indexBytes);
}
```

### 10.1 结构

```text
头部：魔数 8 + 版本 + count + surfSize + nameSize + name
每 surface：
    u32 = 0x54 （重复的长度，冗余但自描述）
    原始 84 字节 header
    4 个长度前缀的数据块
```

### 10.2 **每块都带长度前缀** ⇒ 自描述

```cpp
writeSpan = [&](data, size) { writeU32(size); if (size) write(data, size); };
```

**空块写 `u32(0)` 且不写数据** ✓

### 10.3 `XSurface` 的 **84 字节**被原样写完

**所以"堆上的指针"被写进文件** —— 下游读的时候这些指针是**无效的**。

**但四个数据块是分开写的**，所以下游可以用四个块重建 ✓

### 10.4 失败时**删除文件**

```cpp
output.close();
std::error_code ignored;
std::filesystem::remove(path, ignored);
fail("unreadable CPU geometry on surface " + N);
```

**"不可读的 CPU 几何" ⇒ 删掉半个文件** —— 避免下游读到截断的数据 ✓

**这个做法比"留一个坏文件"好。**

## 十一、`auditAlphaBarrettAssetTemplates` 的**两代偏移对照**（本组第三重要）

### 11.1 那段 CODREF

```text
CODREF(1649370): Load_Material 0x00488250 reads a 104-byte header,
with its asset name at +0x10, texture count at +0x51, and texture
table at +0x5C. Load_GfxImage 0x00487380 reads a 52-byte header,
resolves its name at +0x30, and Load_GfxImageLoadDef 0x00487300
reads the 16-byte load definition reached through +0. The renderer
initializer 0x00BE7470 clears +0 and retains that definition at
+0x2C. Alpha Load_GfxImage 0x004B2E30 instead reads 32 bytes and
resolves its name at +0x1C. This diagnostic records the exact final
structures so the converter does not infer them from alpha's
incompatible layouts.
```

### 11.2 五个函数地址

```text
Load_Material            0x00488250
Load_GfxImage            0x00487380
Load_GfxImageLoadDef     0x00487300
renderer initializer     0x00BE7470
Alpha Load_GfxImage      0x004B2E30
```

**注意 §247 里 `GfxImageInitializeRva = 0x7E7470`** —— 而这里是 `0x00BE7470`。

**两个不同的地址，相差 `0x400000`** —— 因为 **`0x00BE7470` 是 VA 而 `0x7E7470` 是 RVA** ✓

**所以 §247 的 `tryInitializeGfxImage(module_ + 0x7E7470, ...)` 与这里的 `0xBE7470` 是同一个函数。**

**这是一处交叉验证** —— 而且它确认了 `module_` 基址是 `0x400000`（记忆里的"从 0x400000 起"）。

### 11.3 **材质 104 字节的五个偏移**

```text
+0x10  资产名
+0x51  纹理计数（【单字节】）
+0x5C  纹理表
```

**`+0x51` 是 uint8** —— 所以纹理数最多 255。

**`MaterialTextureRowSize = 12`** ⇒ 与 §247 里 `vector<array<byte,12>> textures` 一致 ✓

### 11.4 **纹理行的两个字段**

```text
+7   semantic（【单字节】）
+8   image 指针
```

**`WaterSemantic = 11`** ⇒ 语义 11 表示水面。

**而 §247 里 `slotHeader` 是 8 字节（`+0..7`）⇒ 所以 `+7` 是 `semantic`** ✓

**这是一处交叉验证** —— 8 字节的 `slotHeader` 里最后一个是语义。

### 11.5 **GfxImage 52 字节的四个偏移**

```text
+0x2C  loadDef 指针
+0x30  名字
（loadDef 的 +0x0C 是 dataSize）
```

**`GfxImageLoadDefSize = 16`** ⇒ 与 §247 里 `std::array<std::byte, 16> loadDef` 一致 ✓

### 11.6 **渲染器初始化器的行为**

**"clears +0 and retains that definition at +0x2C"**

```text
+0 被【清零】（原来是 loadDef 指针）
loadDef 被搬到 +0x2C
```

**所以 `tryInitializeGfxImage` 在调用前 `header[+0]` 是 loadDef 指针，调用后 `+0` 变零、`+0x2C` 得到该指针。**

**而 §247 里 `storage->loadDef` 是独立的 16 字节数组，`SV_BuildOlfinalAlphaBarrettImage(source, loadDefAddress, nameAddress, header, loadDef)`** —— 所以 `loadDefAddress` 被写进 `header[+0]`，然后初始化器把它搬到 `+0x2C`。

**这条链闭合了。**

### 11.7 **alpha 的 GfxImage 完全不同**

```text
alpha：32 字节头，名字在 +0x1C
本 build：52 字节头，名字在 +0x30
```

**"所以转换器不能从 alpha 的不兼容布局推断它们"** —— 这是一个明确的警告。

**`GfxImagePayloadHeadSize = 64`** —— 载荷头部 64 字节。

## 十二、关键结论

1. **`ModelOffsets` 的十个偏移 = 2 view + 2 world + 6 辅助**，与 §249 的 "alternate element and six later auxiliary" 完全吻合。
2. **XModel `+0` 是名字指针** —— 审计验证了 §248 的写入位置。
3. **`childCount = boneCount - rootCount`** 是三个数组（parents/quaternions/translations）的长度，而 `boneNames`/`baseMatrices` 是 `boneCount`。
4. **`parents[]` 的下标是"非根骨骼序号"** —— 所以 `parents[index - rootCount]`。
5. **`baseMatrices` 是 `float[boneCount][8]`，平移在 `[4..6]`** —— 压缩的 2×4 仿射。
6. **`rig` 字符串的 `<N` 未闭合** —— 格式缺陷。
7. **审计失败不置 complete ⇒ 下次重试**，与 §247 的 `attempted` 相反。
8. **`XModelLod0ModelSurfsOffset = 0x50`** 与 §248 的 `72 + 8` 独立吻合。
9. **`XSurface` 的 84 字节布局 + 四个数据块**（blend/vertex/rigidList/index）。
10. **`blendBytes = 2 × blendWordCount`** ⇒ 混合数据是 **uint16** 而非 uint32 —— 这是本 build 特有的。
11. **"XModelSurfs 在 fastfile 里是占位符"** —— 必须等到松散资源流；否则消耗掉一次性审计。
12. **`OLXSAUD1` 的自描述格式**（每块长度前缀）与**失败时删文件**。
13. **`0xBE7470`（VA）与 `0x7E7470`（RVA）是同一个函数** —— 交叉验证了 `module_ = 0x400000`。
14. **材质 `+0x51` 是单字节纹理计数、`+0x5C` 是纹理表、行 12 字节、`+7` 是语义、`+8` 是 image**。
15. **GfxImage 的 `+0 → +0x2C` 搬家链闭合了**（§247 的 `loadDef` 独立的疑问）。

## 十三、未闭合点

- `rig` 字符串的 `<N` 未闭合。
- `XSurface` 的 `+0x00` 未列出（前 4 字节是什么）。
- `blendData` 为 uint16 的依据只在 `2u *` 的乘法里，未与参照核对。
- `EngineBindings.cpp` 13650 行之后未读取。
