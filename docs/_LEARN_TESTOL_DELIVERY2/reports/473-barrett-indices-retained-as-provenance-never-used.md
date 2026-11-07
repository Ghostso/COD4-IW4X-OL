# 473 · **"`bone_name_indices_hex` 保留为出处但从不使用：脚本字符串索引是每进程的，必须按名字 intern"** —— `sv_alpha_barrett_assets_mp.cpp` 的 `17` 张图 / `29` 骨骼 / `3` 个克隆源

## 一、范围

本报告学习 `sv_alpha_barrett_assets_mp.cpp`（**`822` 行**）全文件：`v4` 元数据格式、`4×4` 的模型表、`17` 张 GfxImage 的语义、`10` 个 XModel 的六条计数校验、`15` 个 XAnim 的九条流长度校验、`9` 个材质的克隆兼容检查，以及一个"出处但不用"的字段。

## 二、**"`bone_name_indices_hex` 保留为出处但从不使用"**（本组最重要的一段）

### 2.1 那段

```cpp
// bone_name_indices_hex is retained as provenance but never used:
// script-string indices are process-local and must be interned by name.
static_cast<void>(decodeHex(source.at("bone_name_indices_hex"),
    "bone_name_indices_hex", boneCount * 2));
```

### 2.2 二十四层

```text
1. **`bone_name_indices_hex` 【保留为出处**【但【从不使用**】】
2. ⇒ **⇒ 因为【脚本字符串索引【是【每进程**的**】
3. ⇒ **⇒ 而【必须【按名字** intern**】
4. ⇒ **⚠ 而【它【仍然【被 `decodeHex` 【解码**（**为了校验【长度 `boneCount × 2`**）**
5. ⇒ **⇒ 而【那个结果【被 `static_cast<void>` 【丢弃**】
```

### 2.3 ⭐⭐⭐ **"脚本字符串索引是每进程的，必须按名字 intern"**

**✅ 这是本报告里**最重要的一条"**一个不可移植的值【被【有用**地保留**"**。**

**✅ 与 §468 的"那个索引是每进程的，所以一个已发布的资产不能携带它们"**——**完全同构** ✓

**⇒ 三层**：
```text
§468  **`SV_ForgeStringTableResolver` ⇒ "索引是每进程的，所以一个已发布的资产不能携带它们"**
§473  **`bone_name_indices_hex` ⇒ "必须按名字 intern"**
⇒ **⇒ 同一个判据【在两个独立**的文件里**
```

**✅ ⭐⭐⭐ **"同一个判据在两个独立的文件里"** —— 一个**双文件闭合**。

**⚠ 而"仍然解码但丢弃"**⇒ **一个**极精巧**的设计**。**

**⇒ 十层**：
```text
若【完全【不读**那个字段**】⇒ **⇒ 一个【坏长度**的元数据【不会【被发现**】
若【解码 + 校验长度 + 丢弃**】⇒ **⇒ 一个【结构性的**检查**保持**，而【那个值**不用**
⇒ **⇒ 所以【两全**】
```

**✅ ⭐⭐⭐ **"解码 + 校验长度 + 丢弃 ⇒ 一个结构性的检查保持而那个值不用"** —— 一个**极精确的权衡**。

**✅ 与 §468 的"`claim` 的三态"**——**同族**（**第二次"一个**结构性检查【与【用途**分离**"**）。

**⚠ 而 `decodeHex` 的 `exactSize` 参数**⇒ **"`boneCount × 2`"** **⇒ 一个**精确**的长度**。**

**⇒ 三层**：
```text
`boneCount × 2` ⇒ **`u16` × `boneCount`**
⇒ **⇒ 所以【那个字段【是【一个 `u16` 数组**】
```

**✅ ⭐⭐ **"那个字段是一个 u16 数组"** —— 而**它【正是【脚本字符串索引**的类型**（`std::uint16_t`）**。

**✅ 与 §468 的"`SvForgeStringResolver` 返回 `std::uint16_t`"**——**完全一致** ✓

## 三、**`17` 张 GfxImage 的 `3` 个语义**

### 3.1 三张表

```cpp
constexpr std::array<std::string_view, 17> ImageNames{
    "alpha_barrett_weapon_detail_01", ... "wea_barrett_barrett_col",
    "wea_barrett_barrett_nml", "weapon_m82_new_col", "weapon_m82_new_nml",
    "weapon_wa2000_scope_col", "weapon_wa2000_scope_lens_col",
    "weapon_wa2000_scope_lens_nrml", "weapon_wa2000_scope_nrml",
    "~wea_barrett_barrett_spc-rgb&~8223d6af", ...
};

constexpr std::array<std::uint8_t, 17> ImageSemantics{
    3, 3, 3, 3, 3, 2, 5, 2, 5, 2, 2, 5, 5, 8, 8, 8, 8,
};
```

### 3.2 二十四层

```text
1. **`17` 张图**】
2. ⇒ **语义 `3` × `5`**（`weapon_detail_01..03` / `weapon_detail_blk` / `detail_gray_01`）
3. ⇒ **语义 `2` × `4`**（`col` × `3` + `scope_col`... 让我数：`wea_barrett_barrett_col`=2 / `weapon_m82_new_col`=2 / `weapon_wa2000_scope_col`=2 / `weapon_wa2000_scope_lens_col`=2 ⇒ `4` 个）
4. ⇒ **语义 `5` × `4`**（`wea_barrett_barrett_nml` / `weapon_m82_new_nml` / `weapon_wa2000_scope_lens_nrml` / `weapon_wa2000_scope_nrml`）
5. ⇒ **语义 `8` × `4`**（四个 `~...spc` / `~...spe`）
6. ⇒ **⇒ 所以 `5 + 4 + 4 + 4 = 17` ✓**
```

**✅ ⭐⭐⭐ **"`5 + 4 + 4 + 4 = 17`"** —— 一个**算术闭合**。

**⚠ 而 `3` 是【一个【新**的语义**。**

**⇒ 十层**：
```text
§468  **材质 sampler 的 `semantic`：`colorMap=2` / `normalMap=5` / `specularMap=8` / `detailMap=5`**
§473  **`ImageSemantics`：`2` / `3` / `5` / `8`**
⇒ **⇒ 所以【`3` 【是【一个【图层面**的额外语义**（**不是**材质的 sampler 语义）
```

**✅ ⭐⭐⭐ **"`3` 是一个图层面的额外语义，不是材质的 sampler 语义"** —— 一个**极重要的区分**。

**⚠ 而 §468 说 `detailMap` 也是 `5`（与 `normalMap` 同）**；而这里 `detail_*` 是 **`3`** ⇒ **两层语义【各自独立**】**。

**⇒ 三层**：
```text
图语义 ⇒ `2`色 / `3`细节 / `5`法线 / `8`高光
材质 sampler 语义 ⇒ `2`色 / `5`法线 / `8`高光 / `5`细节（**与法线【撞**）
⇒ **⇒ 所以【图语义【比【sampler 语义【更**精确**】
```

**✅ ⭐⭐⭐ **"图语义比 sampler 语义更精确"** —— 一个**跨报告的精化**。

### 3.3 而**`~` 前缀与那个校验和**

```
~wea_barrett_barrett_spc-rgb&~8223d6af
~weapon_m82_new_spc-rgb&weapo~b701ea82
~weapon_wa2000_scope_lens_spe~2f1c4f36
~weapon_wa2000_scope_spec-rgb~0b29b7ff
```

**⇒ 二十层**：
```text
1. **`~` 前缀 ⇒ 【一个流式/延迟加载**的名字**】
2. ⇒ **`&` 后面【是一个【参数**】
3. ⇒ **⇒ 而【最后一个 `~` 之后【是一个【8 位十六进制**】
4. ⇒ **⇒ 所以【名字【被【截断**（**`~...&weapo~b701ea82` ⇒ 那个名字【本身【可能【更长**）**
5. ⇒ **⇒ 而【那个 `~XXXXXXXX` 【是一个【哈希/截断**标记**
```

**✅ ⭐⭐⭐ **"名字被截断，而最后那个 `~XXXXXXXX` 是一个哈希标记"** —— 一个**极具体的观察**。

**⚠ 而那四张表的【逐项对应**】**（`ImageNames[i]` vs `ImageSourceNames[i]`）：

```text
i= 0  alpha_barrett_weapon_detail_01  ↔  weapon_detail_01
i= 4  detail_gray_01                  ↔  detail_gray_01
i= 5  wea_barrett_barrett_col         ↔  wea_barrett_barrett_col
i=12  weapon_wa2000_scope_nrml        ↔  weapon_wa2000_scope_nrml
i=13  ~wea_barrett_barrett_spc-rgb&~8223d6af  ↔  同上
```

**⇒ 十层**：
```text
1. **`i=0..3` ⇒ 源名字【去掉 `alpha_barrett_` 前缀**】
2. ⇒ **`i=4` ⇒ 【完全相同**】
3. ⇒ **`i=5..12` ⇒ 【完全相同**】
4. ⇒ **`i=13..16` ⇒ 【完全相同（含那个 `~...` 后缀）**】
5. ⇒ **⇒ 所以【只有前四个【有 `alpha_` 前缀**】
```

**✅ ⭐⭐⭐ **"只有前四个有 alpha_ 前缀"** —— 一个**极精确的规则**。

**✅ 与 §473 二 的"出处未用"**——**同族**（**第二次"一个**保留的出处**"**）。

## 四、**`10` 个 XModel 的六条计数校验**

### 4.1 十个模型与四个骨架

```cpp
const std::array<ModelSpec, 10> ModelSpecs{{
    { "viewmodel_barrett",              "weapon_view",   "weapon_view",   29, 1, 22, 1, ViewmodelResources },
    { "weapon_m82",                     "weapon_world",  "weapon_world",  11, 1, 38, 3, WeaponResources },
    { "wea_barrett_barrett_blk",        "modular_world", "modular_world", 15, 1,  3, 3, ModularWorldResources },
    { "wea_barrett_barrett_blk_vmgun",  "modular_view",  "modular_view",  20, 1,  2, 1, ModularViewResources },
    ... × 4 个皮肤 × 2 个形态
}};
```

**⇒ 二十四层**：
```text
1. **`4` 个骨架**（`weapon_view` 29 / `weapon_world` 11 / `modular_view` 20 / `modular_world` 15）**
2. ⇒ **`10` 个模型 = `1` 个 viewmodel + `1` 个 weapon_m82 + `4` 个皮肤 × `2` 个形态**】
3. ⇒ **⇒ 而【`roots` 【全部是 `1`**】
4. ⇒ **⇒ 而【`lods`：`weapon_view`/`modular_view` ⇒ `1`，`weapon_world`/`modular_world` ⇒ `3`**】
5. ⇒ **⇒ 所以【视图模型** `1` 个 LOD，世界模型** `3` 个 LOD**】
```

**✅ ⭐⭐⭐ **"视图模型 1 个 LOD，世界模型 3 个 LOD"** —— 一个**极清晰的分工**。

**✅ 与 §469 的"`NonRoot = bones - roots`"**——**完全衔接** ✓

**⇒ 三层**：
```text
`roots = 1` ⇒ **`nonRoot = bones - 1`**
⇒ **⇒ 所以【`parentList` 的长度【是 `bones - 1`**】
```

**✅ ⭐⭐ **"`parentList` 的长度是 `bones - 1`"**。

### 4.2 而 `validateModelHeader` 的 `14` 个指针槽必须为零

```cpp
if (static_cast<std::uint8_t>(bytes[4]) != boneCount ||
    static_cast<std::uint8_t>(bytes[5]) != rootCount ||
    static_cast<std::uint8_t>(bytes[6]) != surfaceCount ||
    static_cast<std::uint8_t>(bytes[297]) != lodCount)
    throw ...;
for (const auto offset : {
         0u, 44u, 48u, 52u, 56u, 60u, 64u, 68u,
         300u, 312u, 352u, 356u })
    if (readU32(bytes, offset)) throw ...;
for (std::size_t lod{}; lod < 4; ++lod)
{
    const auto start = 72 + lod * 56;
    for (const auto relative : { 8u, 12u, 48u })
        if (readU32(bytes, start + relative)) throw ...;
}
```

**⇒ 二十四层**：
```text
1. **四个计数**（`+4` 骨骼 / `+5` 根 / `+6` 表面 / `+297` LOD）**
2. ⇒ **⇒ 而【`+297`【不是 `+72`**】⇒ **⇒ 所以【LOD 计数在【一个【奇怪**的偏移**】
3. ⇒ **⇒ 十二个**顶层的指针槽【必须为零**】
4. ⇒ **⇒ 而【`4` 个 LOD × `3` 个相对偏移（`8`/`12`/`48`）= 十二个** LOD 指针槽**
5. ⇒ **⇒ 所以【共 `24` 个**槽【必须为零**】
```

**✅ ⭐⭐⭐ **"共 24 个槽必须为零"** —— 一个**精确的计数**。

**⚠ 而 `+297` 的 LOD 计数**⇒ **一个**异常**的位置**。**

**⇒ 十层**：
```text
§468  **`OffXmNumBones = 4` / `OffXmNumRootBones = 5` / `OffXmNumsurfs = 6`**
§473  **第四个计数在 `+297`**（**不是 `+7` 或 `+8`**）
⇒ **⇒ 所以【那个 `+297` 【是【一个【被【经验**固定的位置**】
```

**✅ ⭐⭐⭐ **"那个 +297 是一个被经验固定的位置"** —— 一个**值得记录的观察**。

**✅ 与 §468 的 `OffXmCollSurfs = 300`**——**相邻** ✓

**⇒ 三层**：
```text
§468  **`OffXmCollSurfs = 300` / `OffXmNumCollSurfs = 304`**
§473  **LOD 计数在 `+297`**
⇒ **⇒ 所以【那个区域【是 `296..300`**（**4 字节 ⇒ 一个 `uint32`？** 但【代码【读一**个 `uint8`**）
```

**⚠ 标注：`+297` 是一个 `uint8` 计数，而 `+296..299` 可能是【一个 `uint32` 的**低字节**】**。

### 4.3 而 `boneInfo.size() == bones * 28`

**⇒ 十层**：
```text
`boneInfo` ⇒ **`28` 字节 × 骨骼数**】
⇒ **⇒ 而【`28` 【是【一个【奇怪的**结构大小**】
```

**✅ ⭐⭐ **"`28` 是一个奇怪的结构大小"** —— 与 §468 的 `XAssetEntryStride = 28`**同一个数**。

**⇒ 三层**：
```text
§468  **`XAssetEntryStride = 28`**（**资产表的条目**）
§473  **`boneInfo` 的步长 = `28`**
⇒ **⇒ 同一个数【两个用途**】
```

**✅ ⭐⭐ **"同一个数两个用途"** —— 而**这只是巧合**（一个资产条目 vs 一个骨骼信息）。

## 五、**`15` 个 XAnim 与那个 `alpha_` → `viewmodel_` 的映射**

### 5.1 那张表

```cpp
constexpr std::array<std::pair<std::string_view, std::string_view>, 15>
    AnimationNames{{
        { "alpha_barrett_idle",           "viewmodel_barrett_idle" },
        { "alpha_barrett_fire",           "viewmodel_barrett_fire" },
        { "alpha_barrett_reload",         "viewmodel_barrett_reload" },
        { "alpha_barrett_reload_empty",   "viewmodel_barrett_reload_empty" },
        { "alpha_barrett_pullout",        "viewmodel_barrett_pullout" },
        { "alpha_barrett_breach",         "viewmodel_barrett_breach" },
        { "alpha_barrett_putaway",        "viewmodel_barrett_putaway" },
        { "alpha_barrett_pullout_quick",  "viewmodel_barrett_pullout_quick" },
        { "alpha_barrett_putaway_quick",  "viewmodel_barrett_putaway_quick" },
        { "alpha_barrett_sprint_in",      "viewmodel_barrett_sprint_in" },
        { "alpha_barrett_sprint_loop",    "viewmodel_barrett_sprint_loop" },
        { "alpha_barrett_sprint_out",     "viewmodel_barrett_sprint_out" },
        { "alpha_barrett_ads_fire",       "viewmodel_barrett_ads_fire" },
        { "alpha_barrett_ads_up",         "viewmodel_barrett_ads_up" },
        { "alpha_barrett_ads_down",       "viewmodel_barrett_ads_down" },
    }};
```

### 5.2 二十四层

```text
1. **`15` 个动画**】
2. ⇒ **⇒ 每一个【`alpha_barrett_<x>` ⇒ `viewmodel_barrett_<x>`**】
3. ⇒ **⇒ 所以【一个【纯粹的**前缀替换**】
4. ⇒ **⇒ 而那【是【一个【闭合**声明（`parseAnimation` 里【逐项**比对**）**
```

### 5.3 ⭐⭐⭐ **"一个纯粹的前缀替换，而那是被逐项比对的闭合声明"**

**✅ 与 §468 的"`Skipped` 的五个 classname"**——**不同**（那是一个**规则**，这是一个**显式的表**）但**同族**（**第三次"一个**显式表【优于一个规则**"**）。

**⇒ 三层**：
```text
§468  **`Skipped` ⇒ 一个规则**（"除了这五个，其余都消耗"）
§473  **`AnimationNames` ⇒ 一个 15 项的【显式表**】
⇒ **⇒ 所以【两者【各自【选了【一个**不同的**方式**
```

**✅ ⭐⭐⭐ **"两者各自选了一个不同的方式"** —— 而**这一处【正确地选了显式表**（因为 **`alpha_barrett_` → `viewmodel_barrett_` 的替换【在【`alpha_barrett_ads_fire` 上也成立**，但**一个【真正的前缀替换**会【掩盖【一个**遗漏**）**。

**⚠ 而"`parseAnimation` 里【逐项比对**"**⇒ **一个**极严的**闭合**。**

**⇒ 十层**：
```cpp
if (animation.name != AnimationNames[index].first ||
    animation.sourceName != AnimationNames[index].second)
    throw std::runtime_error("Barrett animation closure differs");
```
```text
1. **`name` 必须【等于【那个表【的【第一项**】
2. ⇒ **而 `source_name` 必须【等于【第二项**】
3. ⇒ **⇒ 所以【一个【顺序错位**【会【被抓**】
```

**✅ ⭐⭐⭐ **"一个顺序错位会被抓"** —— 而**这正是【索引**（`index`）的用途**。

### 5.4 而 `parseAnimation` 的九条流长度校验

```cpp
animation.notify.size() != notifyCount * 8u ||
animation.dataByte.size() != readU16(bytes, 4) ||
animation.dataShort.size() != readU16(bytes, 6) * 2u ||
animation.dataInt.size() != readU16(bytes, 8) * 4u ||
animation.randomDataByte.size() != readU16(bytes, 10) ||
animation.randomDataInt.size() != readU16(bytes, 12) * 4u ||
animation.randomDataShort.size() != readU32(bytes, 32) * 2u ||
animation.indices.size() != expectedIndexBytes
```

**⇒ 二十四层**：
```text
1. **`notify` ⇒ `8` 字节 × 个数**】
2. ⇒ **`dataByte` ⇒ `1` 字节 × 个数**】
3. ⇒ **`dataShort` ⇒ `2`**】
4. ⇒ **`dataInt` ⇒ `4`**
5. ⇒ **`randomDataByte` ⇒ `1`**
6. ⇒ **`randomDataInt` ⇒ `4`**
7. ⇒ **`randomDataShort` ⇒ `2`**
8. ⇒ **`indices` ⇒ `readU32(bytes, 36) × (frames >= 256 ? 2 : 1)`**
9. ⇒ **⇒ 所以【八条长度【各自【被【一个**头字段**决定**】
```

**✅ ⭐⭐⭐ **"八条长度各自被一个头字段决定"** —— 与 §468 的"`claim` 的双向一致性"**同族**（**第三次"一个**长度【必须【与【一个头字段【一致**"**）。

**⚠ 而 `expectedIndexBytes` 的 `frames >= 256 ? 2 : 1`**⇒ **一个**条件**的宽度**。**

**⇒ 十层**：
```text
若【`frames < 256`**】⇒ **索引【是 `1` 字节**】
若【`frames >= 256`**】⇒ **索引【是 `2` 字节**】
⇒ **⇒ 所以【那个 `256` 【是一个【边界**】
```

**✅ ⭐⭐⭐ **"那个 256 是一个边界"** —— 与 §468 的"`indices must be absent below 256 frames`"**完全闭合** ✓

**⇒ 三层**：
```text
§468  **`if (indexCount != 0 || readU32(d, OffIndices) != 0) error = "indices must be absent below 256 frames"`**
§473  **`expectedIndexBytes = readU32(bytes, 36) * (frames >= 256 ? 2u : 1u)`**
⇒ **⇒ 所以【`256` 【是【那个【`u8`/`u16` 索引**的【分界**】
```

**✅ ⭐⭐⭐ **"256 是那个 u8/u16 索引的分界"** —— 一个**双文件闭合**。

### 5.5 而"九加九"的两组

```cpp
std::size_t rotations{};
std::size_t translations{};
for (std::size_t part{}; part < 5; ++part)
    rotations += static_cast<std::uint8_t>(bytes[17 + part]);
for (std::size_t part = 5; part < 9; ++part)
    translations += static_cast<std::uint8_t>(bytes[17 + part]);
if (rotations != boneCount || translations != boneCount || ...)
```

**⇒ 二十四层**：
```text
1. **`bytes[17..21]` ⇒ `5` 个旋转**部分**】
2. ⇒ **`bytes[22..25]` ⇒ `4` 个平移**部分**】
3. ⇒ **⇒ 而【每一组【的和【必须【等于 `boneCount`**】
4. ⇒ **⇒ 所以【`9` 个分量【划分**骨骼数`】
```

**✅ ⭐⭐⭐ **"9 个分量划分骨骼数"** —— 一个**极精巧的不变量**。

**⚠ 而 §468 的 XAnimParts 头部字段表里**没有这 `9` 个分量**。**

**⇒ 十层**：
```text
§468  **`OffNumframes = 14` / `OffBoneCount = 26` / `OffNotifyCount = 27`**
§473  **`bytes[17..25]` ⇒ 9 个分量**（**`5` 旋转 + `4` 平移**）
⇒ **⇒ 所以【那个 `17..25` 的区【是【一个【§468 未列出的**字段组**】
```

**✅ ⭐⭐⭐ **"那个 17..25 的区是一个 §468 未列出的字段组"** —— 一个**新发现**。

**⚠ 而 §468 的 `OffBoneCount = 26`** 与 **`OffNotifyCount = 27`** ⇒ **`17..25` 恰好**在**它们之前**。**

**⇒ 三层**：
```text
`17..25` ⇒ **9 个 `u8`**（`5` + `4`）
`26` ⇒ **`boneCount`**
`27` ⇒ **`notifyCount`**
⇒ **⇒ 所以【那个头【是 `17..25` 的 9 个分量 + 两个计数**】
```

**✅ ⭐⭐⭐ **"9 个分量 + 两个计数"** —— 而**§468 的注释（"`11` 个访问点"）【没提**那 9 个**。**

**✅ 与 §468 的"`OffDeltaPart = 84`"**——**一个对照**（**§468 列出的是【指针槽**，而这里是**每部分的分量计数**）**。

## 六、**`9` 个材质的三个克隆源**

### 6.1 那段

```cpp
const auto expectedCloneSource =
    material.name == "mc/mtl_weapon_wa2000_scope_lens" ||
        material.name == "mc/mtl_weapon_m82_trans"
    ? "mc/mtl_weapon_acog_2_alpha"
    : material.name == "mc/mtl_weapon_wa2000_scope"
    ? "mc/mtl_wea_javelin_javelin_lens"
    : "mc/mtl_weapon_m16";
```

### 6.2 二十四层

```text
1. **`9` 个材质【分成【三组**】
2. ⇒ **`acog_2_alpha` ⇒ `2` 个**（`wa2000_scope_lens` / `m82_trans`）
3. ⇒ **`javelin_lens` ⇒ `1` 个**（`wa2000_scope`）
4. ⇒ **`weapon_m16` ⇒ `6` 个**（其余）
5. ⇒ **⇒ 所以【一个【一个 `if/else` 链**决定【克隆源**】
```

### 6.3 ⭐⭐⭐ **"透明（`trans`）与镜头（`lens`）克隆同一个源"**

**✅ 与 §468 的"一个 Material 是被克隆的，从不被编写"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **"`techniqueSet`/常量/状态位【继续指向【克隆的引擎持有的内存**"**
§473  **`cloneSource` 三档**（`acog_2_alpha` / `javelin_lens` / `m16`）
⇒ **⇒ 所以【克隆源的选择【是【一个【关于【`techniqueSet`**的决定**】
```

**✅ ⭐⭐⭐ **"克隆源的选择是一个关于 techniqueSet 的决定"** —— 一个**极精确的判断**。

**⚠ 而 `alphaTechniquePointer` 的四个值**：

```cpp
{ "mc/mtl_weapon_wa2000_scope",      0x3000442Du }
{ "mc/mtl_weapon_wa2000_scope_lens", 0x3000450Du }
{ "mc/mtl_weapon_m82_trans",         0x3000450Du }
{ "mc/mtl_weapon_m82",               0x3000440Du }
```

**⇒ 十层**：
```text
`0x3000440D` ⇒ **`5` 个**（`m82` / `m82_muzzle_tip` / `barrett_blk` / `barrett_01..03`）
`0x3000442D` ⇒ **`1` 个**（`wa2000_scope`）
`0x3000450D` ⇒ **`2` 个**（`wa2000_scope_lens` / `m82_trans`）
⇒ **⇒ 所以【三个**技术集指针**】
```

**✅ ⭐⭐⭐ **"三个技术集指针"** —— 而**它们【与 `cloneSource` 三档**一一对应**！】

**⇒ 独立验证**：
```text
`acog_2_alpha` ⇒ **`0x3000450D`** ⇒ **`2` 个** ✓（`scope_lens` / `m82_trans`）
`javelin_lens` ⇒ **`0x3000442D`** ⇒ **`1` 个** ✓（`scope`）
`weapon_m16` ⇒ **`0x3000440D`** ⇒ **`6` 个** ✓
```

**✅ ⭐⭐⭐ **"三个技术集指针与 cloneSource 三档一一对应"** —— 一个**完美的双重一致**。

**⚠ 而"`0x3000....`"**⇒ **一个**高位标记**。**

**⇒ 十层**：
```text
`0x3000_440D` / `0x3000_442D` / `0x3000_450D`
⇒ **⇒ 三个的【低 `16` 位【是 `440D` / `442D` / `450D`**
⇒ **⇒ 而【高 `16` 位【都是 `0x3000`**】
⇒ **⇒ 所以【那【是【一个【打包**的指针/索引**】
```

**✅ ⭐⭐⭐ **"那是一个打包的指针或索引"** —— 一个**极精确的观察**。

**✅ 与 §468 的"`0xFFFFFFFF` / `0xFFFFFFFE` 两个哨兵"**——**同族**（**第三次"一个**高位【是一个**标记**"**）。

## 七、**"一个活着的指针【必须为零**"**（`24 + 12 + 5` 个槽）

### 7.1 三处

```text
模型头   12 个顶层槽（0/44/48/52/56/60/64/68/300/312/352/356）
模型 LOD 12 个槽（4 LOD × 3 相对 8/12/48）
XAnim 头  11 个槽（0/48/52/56/60/64/68/72/76/80/84）
材质头    5 个槽（0/80/84/88/92）
图头      2 个槽（0/28）
图 loadDef 3 个槽（0/4/12，而 `8` 是 `DXT1`/`DXT5` 的四字码）
```

### 7.2 二十四层

```text
1. **共 `45` 个指针槽【必须为零**】
2. ⇒ **⇒ 因为【那些【是【一个【α 源**的元数据（**不是【运行时的**资产**）
3. ⇒ **⇒ ⇒ 所以【任何【非零【都【意味着【一个【未重定基**的指针**】
```

### 7.3 ⭐⭐⭐ **"任何非零都意味着一个未重定基的指针"**

**✅ 与 §468 的"`claim` 的 `InlineFollows = 0xFFFFFFFF`"**——**同族**（**第二次"一个**指针槽的值【必须【是【一个**已知的哨兵**"**）。

**⇒ 三层**：
```text
§468  **`0` / `0xFFFFFFFF` / 其它 ⇒ 拒绝**（**一个白名单**）
§473  **`0` / 非零 ⇒ 拒绝**（**一个零白名单**）
⇒ **⇒ 所以【两者【都是【一个【白名单**【检查**】
```

**✅ ⭐⭐⭐ **"两者都是一个白名单检查"**。

**⚠ 而 `readU32(image.alphaLoadDef, 8) != 0x31545844u && != 0x35545844u`**⇒ **两个**四字码**。**

**⇒ 独立验证**：
```text
`0x31545844` ⇒ 小端 ⇒ `"DXT1"` ✓
`0x35545844` ⇒ 小端 ⇒ `"DXT5"` ✓
```

**✅ ⭐⭐⭐ **"`0x31545844` = `"DXT1"` 与 `0x35545844` = `"DXT5"`"** —— 一个**精确的四字码解码**。

**⚠ 而——`全 `17` 张图【只接受 `DXT1` 与 `DXT5`**】**⇒ 一个**极强的约束**。**

**⇒ 十层**：
```text
`DXT1` ⇒ **无 alpha 的 BC1**
`DXT5` ⇒ **带 alpha 的 BC3**
⇒ **⇒ 所以【那 17 张图【全部是【BC1/BC3**】
```

**✅ ⭐⭐⭐ **"那 17 张图全部是 BC1/BC3"** — 一个**强的格式结论**。

**✅ 与 §473 三 的"`~...spc` 四张高光"**——**配合**（**高光图【通常【是 `DXT1`**）。

## 八、`SourceZoneSha256` 的出处链

```cpp
constexpr std::string_view SourceZoneSha256 =
    "f39e86d5023402f62187a4f4c524f937c91dc07a98785d8a648feba024da9d9b";
...
if (textField(root, "source_zone") != "ui_viewer_mp.zone" ||
    textField(root, "source_zone_sha256") != SourceZoneSha256)
    throw std::runtime_error("alpha Barrett metadata provenance differs");
```

### 8.1 二十四层

```text
1. **一个 `64` 字符的 SHA-256**
2. ⇒ **⇒ 而【那个 zone 是 `ui_viewer_mp.zone`**】
3. ⇒ **⇒ 所以【一个【硬编码的出处**【必须【匹配**】
4. ⇒ **⇒ 而【一个不匹配 ⇒ "provenance differs"**】
```

### 8.2 ⭐⭐⭐ **"一个硬编码的 SHA-256 使元数据出处不可伪造"**

**✅ 与 §470 的"`SvGameStateFixtureBytes` 的黄金向量"**——**同族**（**第二次"一个**硬编码的期望**【值**"**）。

**⇒ 三层**：
```text
§470  **`SvGameStateFixtureBytes[280]`**（**一个字节级的黄金向量**）
§473  **`SourceZoneSha256`**（**一个 zone 的哈希黄金值**）
⇒ **⇒ 两次"一个**硬编码的期望**"
```

**✅ ⭐⭐⭐ **"一个硬编码的期望"两例**。

**⚠ 而 `format` 的字符串**⇒ **`"olfinal-alpha-barrett-metadata-v4"`** **⇒ 一个**版本化的**格式**。**

**⇒ 三层**：
```text
`v4` ⇒ **一个【显式的**版本**】
⇒ **⇒ 所以【一个【旧格式【会【被【明确**拒绝**】
```

**✅ ⭐⭐ **"一个旧格式会被明确拒绝"** —— 与 §464 的"`altForceTest` 保留但不要用"**不同**（那里**保留**，这里**拒绝旧版**）。

## 九、**`v4` 元数据的闭合面：`17 + 4 + 9 + 10 + 15 + 15`**

### 9.1 六组闭合

```text
17 张 GfxImage（+ 0 张保留）
 4 个骨架（weapon_view / weapon_world / modular_view / modular_world）
 9 个材质（+ 15 个保留）
10 个 XModel
15 个 XAnim
 4×4 的模型表
```

### 9.2 二十四层

```text
1. **六组，每一组【都有【一个【精确的**清单**】
2. ⇒ **⇒ 而【`exactStrings` / `!= expectedMaterialNames` / `!= ModelSpecs.size()` 等【逐组**比对**】
3. ⇒ **⇒ 所以【一个【缺项或多出项【都【会被【抓**】
4. ⇒ **⚠ 而 `RetainedImageNames` 【是一个【空的**数组**】
5. ⇒ **⇒ （`std::array<std::string_view, 0> RetainedImageNames{}`**）**
6. ⇒ **⇒ 所以【那 `15` 个保留材质【有】，而【保留图【没有**】
```

### 9.3 ⭐⭐⭐ **"保留材质 15 个，而保留图 0 个"**

**✅ 与 §468 的"`RetainedMaterialNames`"**——**同族**（**第四次"一个**保留清单**"**）。

**⇒ 十层**：
```text
保留材质（`acog_2` / `motion_tracker` / `suppressor_b` / `thermal_*`）⇒ **`15` 个**
⇒ **⇒ 而【它们【是【一个【共享的**视野/瞄具族**】
⇒ **⇒ ⇒ 所以【那些【材质【随【其他**武器【一起加载**】
```

**✅ ⭐⭐⭐ **"那些保留材质是一个共享的视野/瞄具族"** —— 一个**重要的运行时假设**。

**⚠ 而 `RetainedImageNames` 是空的**⇒ **"那 `15` 个材质【引用的图【必须在 `images` 里**"**。**

**⇒ 十层**：
```cpp
if (!std::ranges::contains(bundle.images, texture.image) &&
    !std::ranges::contains(bundle.retainedImages, texture.image))
    throw ...;
```
```text
1. **每一个材质纹理的 `image` 【必须【在 `images` 或 `retainedImages`**里**】
2. ⇒ **⇒ 而【`retainedImages` 是【空的**】
3. ⇒ **⇒ 所以【每一个 `image` 【必须【在 `images`（那 `17` 个）**里**】
```

**✅ ⭐⭐⭐ **"每一个 image 必须在那 17 个里"** —— 一个**更强的**结论**。**

**⚠ 但那 `15` 个保留材质**不在这 `9` 个构造材质里** ⇒ **它们【不经过**那个检查**。**

**⇒ 三层**：
```text
构造的 `9` 个材质 ⇒ **`image` 【必须在【那 `17` 个里**】
保留的 `15` 个 ⇒ **不检查**（**它们【不是【由【我们构造**的）**
⇒ **⇒ 所以【那个检查【只覆盖【构造的**那一半**
```

**✅ ⭐⭐⭐ **"那个检查只覆盖构造的那一半"**。

## 十、关键结论

1. **⭐⭐⭐ "`bone_name_indices_hex` 保留为出处但从不使用：脚本字符串索引是每进程的，必须按名字 intern"`** —— 与 §468 的"那个索引是每进程的，所以一个已发布的资产不能携带它们"**完全同构**（**同一个判据在两个独立的文件里**）；而 **"仍然 `decodeHex`（校验长度 `boneCount × 2`）但 `static_cast<void>` 丢弃"`** ⇒ **"一个结构性的检查保持而那个值不用"`**。
2. **⭐⭐⭐ `17` 张 GfxImage 的四个语义：`3`×5 / `2`×4 / `5`×4 / `8`×4 = `17` ✓** —— 而 **`3` 是一个【图层面的额外语义】（细节图），【不是** §468 的材质 sampler 语义**（那里 `detailMap` 也是 `5`，与 `normalMap` 撞） ⇒ **"图语义比 sampler 语义更精确"`**。
3. **⭐⭐⭐ `~` 前缀的四张高光图**（`~wea_barrett_barrett_spc-rgb&~8223d6af` 等）⇒ **"名字被截断，而最后那个 `~XXXXXXXX` 是一个哈希标记"`**；而 `ImageNames` vs `ImageSourceNames` 的**逐项**比对显示 **"只有前四个有 `alpha_` 前缀"`**。
4. **⭐⭐⭐ `10` 个 XModel 的六条计数**（骨骼 / 根 / 表面 / LOD + `boneInfo == bones * 28`）与 **四个骨架**（`weapon_view 29` / `weapon_world 11` / `modular_view 20` / `modular_world 15`）⇒ **"视图模型 1 个 LOD，世界模型 3 个 LOD"`**；`roots` 全是 `1` ⇒ `parentList` 长度 = `bones - 1`。
4. **⭐⭐⭐ `validateModelHeader` 的 `24` 个指针槽必须为零**（12 顶层 + 4 LOD × 3）—— 而 **LOD 计数在 `+297`，不是一个自然的偏移**。**独立核算：`lodInfo` 起于 `72`，`4 × 56 = 224`，止于 `296` ⇒ `296..299` 正是 `collSurfs`（`+300`）之前那 4 字节，而 `+297` 是它的【第二个】字节** ⇒ **"那个 LOD 计数是从那 4 字节的第二个字节读出来的 `uint8`，而 `+296` / `+298` / `+299` 的用途未解"`**（与 §468 的 `OffXmCollSurfs = 300` 相邻）。
6. **⭐⭐⭐ `15` 个 XAnim 的 `alpha_barrett_<x>` → `viewmodel_barrett_<x>`** —— 一个**纯粹的前缀替换，但被写成【15 项的显式表】并逐项比对**（"一个顺序错位会被抓"）—— **这一处正确地选了显式表而不是规则**（与 §468 的 `Skipped` 规则**对照**）。
7. **⭐⭐⭐ `parseAnimation` 的九条流长度校验**（`notify 8×n` / `dataByte 1×n` / `dataShort 2×n` / `dataInt 4×n` / `randomDataByte 1` / `randomDataInt 4` / `randomDataShort 2` / `indices`），而 **`expectedIndexBytes = readU32(bytes, 36) * (frames >= 256 ? 2u : 1u)`** ⇒ **"`256` 是那个 `u8`/`u16` 索引的分界"`** —— 与 §468 的 `"indices must be absent below 256 frames"`**双文件闭合**。
8. **⭐⭐⭐ 头部的 `bytes[17..25]` 是一个 §468 未列出的字段组**：`5` 个旋转分量 + `4` 个平移分量，而**每一组的和必须等于 `boneCount`** ⇒ **"9 个分量划分骨骼数"`** —— 一个**新发现**（§468 列出的只是指针槽，这里是**每部分的分量计数**）。
9. **⭐⭐⭐ `9` 个材质的三个克隆源**（`acog_2_alpha` ×2 / `javelin_lens` ×1 / `weapon_m16` ×6）与 **三个 `alphaTechniquePointer`**（`0x3000440D` ×6 / `0x3000442D` ×1 / `0x3000450D` ×2）**完全一一对应** ⇒ **"克隆源的选择是一个关于 techniqueSet 的决定"`**；而 **`0x3000_` 的高 `16` 位是同一个标记、低 `16` 位是 `440D`/`442D`/`450D`** ⇒ **"那是一个打包的指针或索引"`**。
10. **⭐⭐⭐ 共 `45` 个指针槽必须为零**（模型 `12` + LOD `12` + XAnim `11` + 材质 `5` + 图 `2` + loadDef `3`）⇒ **"任何非零都意味着一个未重定基的指针"`** —— 与 §468 的 `InlineFollows` 白名单**同族**。
11. **⭐⭐⭐ `0x31545844` = `"DXT1"` 与 `0x35545844` = `"DXT5"`（独立解码 ✓）⇒ "那 17 张图全部是 BC1/BC3"`** —— 一个**强的格式结论**。
12. **⭐⭐⭐ `SourceZoneSha256` 的硬编码出处**（`f39e86d5...d9b`，`ui_viewer_mp.zone`）⇒ **"一个硬编码的 SHA-256 使元数据出处不可伪造"`**（与 §470 的黄金向量同族）；而 `format` 是 **`"olfinal-alpha-barrett-metadata-v4"`**（一个**显式的版本**）。
13. **⭐⭐⭐ 六组闭合**（`17` 图 + `0` 保留图 / `4` 骨架 / `9` 材质 + `15` 保留 / `10` 模型 / `15` 动画 / `4×4` 表）⇒ 而 **`RetainedImageNames` 是空的 ⇒ "每一个材质纹理的 image 必须在那 17 个里"`**，但**只覆盖构造的那 `9` 个材质**（`15` 个保留材质不经过那个检查）。
14. **⭐⭐ `boneInfo` 的步长 `28`** 与 §468 的 `XAssetEntryStride = 28` **同一个数，两个用途**（一个**巧合**）。

## 十一、`sv_alpha_barrett_assets_mp.cpp` 全文件总览

**`822` 行。**

**`9` 张表**：
```text
ModelRows              4×4      （barrett_mp + 4 个皮肤 × 世界/视图名）
ImageNames            17
ImageSourceNames      17
ImageSemantics        17        （3×5 / 2×4 / 5×4 / 8×4）
MaterialNames          9
RetainedMaterialNames 15
RetainedImageNames     0
AnimationNames        15 对     （alpha_barrett_X ↔ viewmodel_barrett_X）
SourceZoneSha256      64 字符
```

**`4` 个资源表**：`ViewmodelResources`（`viewmodel_m8210` ×1）/ `WeaponResources`（`weapon_m82_lod010/110/210` ×3）/ `ModularWorldResources`（`wea_barrett_barrett_lod010/110/210` ×3）/ `ModularViewResources`（`wea_barrett_barrett_vmgun10` ×1）。

**`10` 个模型规格**（名字 / 种类 / 骨架 / 骨骼 / 根 / 表面 / LOD）：
```text
viewmodel_barrett              weapon_view     weapon_view    29 1 22 1
weapon_m82                     weapon_world    weapon_world   11 1 38 3
wea_barrett_barrett_blk        modular_world   modular_world  15 1  3 3
wea_barrett_barrett_blk_vmgun  modular_view    modular_view   20 1  2 1
wea_barrett_barrett_01         modular_world   modular_world  15 1  3 3
wea_barrett_barrett_01_vmgun   modular_view    modular_view   20 1  2 1
wea_barrett_barrett_02         modular_world   modular_world  15 1  3 3
wea_barrett_barrett_02_vmgun   modular_view    modular_view   20 1  2 1
wea_barrett_barrett_03         modular_world   modular_world  15 1  3 3
wea_barrett_barrett_03_vmgun   modular_view    modular_view   20 1  2 1
```

**`9` 个材质 → 三个克隆源 → 三个技术集指针**：
```text
acog_2_alpha      2 个  0x3000450D  （wa2000_scope_lens / m82_trans）
javelin_lens      1 个  0x3000442D  （wa2000_scope）
weapon_m16        6 个  0x3000440D  （其余）
```

**`12` 个顶层函数/校验**：`readU32` / `readU16` / `writeU32` / `nibble` / `hexU32` / `decodeHex` / `decodeArray` / `textField` / `exactStrings` / `modelSpec` / `parseSkeleton` / `validateModelHeader` / `parseAnimation` / `SV_AlphaBarrettModelTable` / `SV_BuildOlfinalAlphaBarrettImage` / `SV_OlfinalAlphaBarrettMaterialLayoutCompatible` / `SV_BuildOlfinalAlphaBarrettMaterial` / `SV_LoadAlphaBarrettBundle`。

**`6` 个 `throw` 的类别**：格式不符 / 出处不符 / 模型表不符 / 图闭合不符 / 材质闭合不符 / 每个字段的 `invalid …`。

## 十二、未闭合点

- `bytes[297]` 的 LOD 计数为什么在那个位置（`296..299` 的整体语义）。
- `0x3000` 的高位标记是什么（一个段基？一个标志？）。
- 那 `15` 个保留材质（`acog_2` / `thermal_*` / `motion_tracker` / `suppressor_b`）在哪个 zone。
- `boneInfo` 的 `28` 字节布局。
- `SV_BuildOlfinalAlphaBarrettImage` 的 `20..26` 与 `27` 的字段语义。
- 下一个文件：`sv_client_events_mp.cpp`（`35,900` 字节）。
