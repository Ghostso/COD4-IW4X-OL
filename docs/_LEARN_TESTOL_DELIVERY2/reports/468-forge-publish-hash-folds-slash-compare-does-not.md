# 468 · **"哈希把反斜杠折成正斜杠，比较不折"** —— `sv_forge_publish_mp.cpp/.hpp` 的四种资产、`81,128/81,128` 的哈希复算、以及一个"按位置绑定"的失败

## 一、范围

本报告学习 `sv_forge_publish_mp.cpp`（**`1,459` 行**）与 `sv_forge_publish_mp.hpp`（**`564` 行**）全文件：XAnimParts 的 `88` 头 + 重定位、XModel 的 `360` 头 + 构建、XAsset 哈希表的只读遍历、WeaponDef 的枚举映射、Material 的克隆与 `104` 头、CoD4 材质文件的解析。

## 二、**"哈希把反斜杠折成正斜杠，比较不折"**（本组最重要的一段）

### 2.1 那段

```cpp
std::uint32_t SV_ForgeXAssetHash(const std::uint32_t type, const std::string &name) noexcept
{
    // sub_49C870 out.exe 0x49C870, seeded with the asset type.
    std::uint32_t h = type;
    for (const char raw : name)
    {
        int c = static_cast<unsigned char>(raw);
        if (c >= 'A' && c <= 'Z') c += 32;
        // The hash folds a backslash to a forward slash. The COMPARE does not.
        if (c == '\\') c = '/';
        h = 31u * h + static_cast<std::uint32_t>(c);
    }
    return h % XAssetHashBuckets;
}
```

```cpp
bool SV_ForgeXAssetNamesEqual(const char *const stored, const std::string &wanted) noexcept
{
    // sub_49CA70's own comparison: byte for byte, lowering only A-Z, and no
    // slash folding. A name with no terminator inside the cap fails closed.
```

### 2.2 二十四层

```text
1. **哈希【把 `\` 折成 `/`**】
2. ⇒ **⚠ 而【那个比较【不折**】】
3. ⇒ **⇒ 所以【两个【只在斜杠方向**不同的名字】
4. ⇒ **⇒ 【共享**一个桶**】
5. ⇒ **⇒ 而【仍然【比较不等**】】
6. ⇒ **⇒ 所以【一个【一致**的哈希【配一个【不一致**的比较】
7. ⇒ **⇒ 而【这个不对称【是【引擎的**，是【被精确镜像的**】
8. ⇒ **⇒ 而【不是【这里的一个 bug**】
```

### 2.3 ⭐⭐⭐ **"两个只在斜杠方向不同的名字共享一个桶，而仍然比较不等"**

**✅ 这是本报告里**最重要的一条"一个引擎级的**故意的**不对称**。**

**✅ 与 §467 的"`quotedString` 只转义 `\\` 与 `\"`"**——**不同**（那是一个解析器的选择，这是一个**设计上的对称破缺**）。

**⇒ 三层**：
```text
哈希：**折** ⇒ **桶一致** ⇒ **一个链上找到**
比较：**不折** ⇒ **不等** ⇒ **继续下一个**
⇒ **⇒ 所以【结果正确，只是【多走一步链**】
```

**✅ ⭐⭐⭐ **"结果正确，只是多走一步链"** —— 一个**极精确的性能观察**。

**⚠ 而"若【比较也折**"⇒ **一个可能的错误**。**

**⇒ 三层**：
```text
若【比较也折**】⇒ **`a\b` 与 `a/b` 【会相等**】⇒ **⇒ 一个【假的命中**】
⇒ **⇒ 所以【那个不对称【是一个正确性**的要求**】
```

**✅ ⭐⭐⭐ **"那个不对称是一个正确性的要求"** —— 而 **注释把它写下来**（"The hash folds a backslash to a forward slash. **The COMPARE does not.**"）**。

**✅ 与 §465 的"`SV_MapTriggerTouches` 的注释说 REFUSES 但代码仍循环"**——**一个对照**（那里**注释与代码不符**，这里**注释正好解释了代码**）。

**⇒ 三层**：
```text
§465  **注释与代码【矛盾**】（**一个缺陷**）
§468  **注释与代码【互补**】（**一个解释**）
⇒ **⇒ 所以【同一个文件里的注释【有两种**读法**】
```

**✅ ⭐⭐ **"注释有两种读法"**。

### 2.4 而**"`81,128/81,128` 的零失配"**

```cpp
// MEASURED against a live client on 2026-09-09: walking all 120,000 buckets
// and recomputing each entry's hash from its own name reproduced the bucket it
// was found in for **81,128 of 81,128** assets whose type has a name accessor,
// with zero mismatches. The remaining 18,882 entries are type 27, whose
// accessor is none of the three below and which is therefore refused rather
// than read at a guessed offset. The longest chain in the whole table is 7,
// and `mc/mtl_t6_wpn_pda` resolves in ONE step - against the 200,000-entry
// linear scan the runtime probes used before this was decoded.
```

**⇒ 二十四层**：
```text
1. **`120,000` 个桶【全部走了一遍**】
2. ⇒ **从【每个条目自己的名字**重算**它的哈希**
3. ⇒ **⇒ 【复现了它被找到的那个桶**】**
4. ⇒ **⇒ 对 `81,128` 个里的 `81,128` 个**
5. ⇒ **⇒ 【零失配**】
6. ⇒ **⚠ 而【剩下的 `18,882` 个是 type `27`**】
7. ⇒ **⇒ 它的访问器【不是那三个之一**】
8. ⇒ **⇒ 所以【被拒绝【而不是在一个猜的偏移上读**】】
9. ⇒ **⇒ 而【全表最长的链是 `7`**】
10. ⇒ **⇒ 而 `mc/mtl_t6_wpn_pda` 【一步**解析**】
11. ⇒ **⇒ 而那【对比**了**之前用的【`200,000` 条目的线性扫描**】
```

### 2.5 ⭐⭐⭐ **"`81,128` 个里的 `81,128` 个，零失配"**

**✅ 这是本报告里**最重的一条验证**。**

**✅ 与 §466 的"`192` 个里的 `192` 个间隙，零误差"**——**一个同族的"零失配** ✓

**⇒ 三层**：
```text
§466  **`192/192` 零误差**（**一个编号规则**）
§468  **`81,128/81,128` 零失配**（**一个哈希函数**）
§468  **`55/68` 纯盒子**（**一个几何分类**）
⇒ **⇒ 三次"零失配**】
```

**✅ ⭐⭐ **"零失配"三例表**。</br>

**✅ 而"`81,128 + 18,882 = 100,010`"⇒ **不是 `120,000`**。**

**⇒ 十层**：
```text
`81,128 + 18,882 = 100,010`
而【桶数是 `120,000`】
⇒ **⇒ 所以【`120,000 - 100,010 = 19,990` 个桶【是空的**】
⇒ **⇒ 而【`100,010` 个条目【分布在【`120,000` 个桶里**】
```

**✅ ⭐⭐ **"`19,990` 个桶是空的"** —— 一个**可推导的数**。

**⚠ 而"平均链长 `100,010/120,000 = 0.83`"⇒ **"最长 `7`"** 是**一个合理的分布**。

**⇒ 三层**：
```text
平均 **`0.83`**
最长 **`7`**
⇒ **⇒ 所以【一个【均匀分布**的哈希**
```

**✅ ⭐⭐ **"一个均匀分布的哈希"**。</br>

**✅ 而"`200,000` 条目的线性扫描"⇒ **一个对比**。

**⇒ 十层**：
```text
旧：**线性扫描 `200,000`** ⇒ **平均 `100,000` 次比较**
新：**一次哈希 + 一步链** ⇒ **`1` 次**
⇒ **⇒ 所以【`10^5` 倍的加速**】
```

**✅ ⭐⭐⭐ **"`10^5` 倍的加速"** —— 一个**极精确的量化**。

### 2.6 而**"type `27` 被拒绝而不是在一个猜的偏移上读"**

**✅ 与 §463 的"不是可以猜的东西"**、§460 的"不搬对方数字"**同族**（**第四次"不猜**）。

**⇒ 三层**：
```text
§460  **`SwaySpeed` 偏移未核实 ⇒ 不搬**
§463  **另一个原生 ABI ⇒ 不猜**
§468  **type `27` 的访问器不在三个里 ⇒ 拒绝**
⇒ **⇒ 三次"不猜就是拒绝**】
```

**✅ ⭐⭐⭐ **"不猜就是拒绝"** —— 而不是**"猜一个默认"**。

**⚠ 而"三个 thunk"⇒ **一个精确的枚举**。**

```cpp
0x483390  **(DWORD **)p         name at header +0   (XAnimParts, XModel)
0x4833A0  *(DWORD *)(*p + 16)   Material at +16
0x4833C0  *(DWORD *)(*p + 48)   GfxImage at +48
```

**⇒ 十层**：
```text
三个**【偏移**：`0` / `16` / `48`
⇒ **⇒ 而从【引擎自己的 thunk 地址【读出**那个偏移**
⇒ **⇒ 而不是【从样本推断**】
```

**✅ 与 §463 的"三个 `refuse` 的命名"**——**一个对照**（那里**给项命名**，这里**给 thunk 映射**）。

**⇒ 三层**：
```text
§462  **给那一项命名**
§468  **给那个 thunk 一个偏移**
⇒ **⇒ 两次"把不透明变成可查**】
```

**✅ ⭐⭐ **"把不透明变成可查"两例**。

## 三、**`DB_FindXAssetHeader` 是"错误的门"**（本组第二重要）

### 3.1 那段

```cpp
// PREFER THESE over SV_ForgeMaterialResolver / SV_ForgeImageResolver, for the
// same reason SV_ForgeStringTableResolver is preferred over the intern call:
// no critical section, no allocation, no calling convention to get wrong, and
// nothing that can block.
//
// `DB_FindXAssetHeader` (0x49CF30) is the wrong door for anything driven from
// outside the engine's own threads. It takes a critical section, waits on a
// streaming event, and branches on `GetCurrentThreadId` against three
// different thread ids - and on a live client it did exactly that.
```

**⇒ 二十四层**：
```text
1. **优先**那些只读的表遍历**】
2. ⇒ **理由【与 `SV_ForgeStringTableResolver` 优先于那个 intern 调用**一样**】
3. ⇒ **⇒ 没有临界区**】
4. ⇒ **⇒ 没有分配**】
5. ⇒ **⇒ 没有【一个会搞错的调用约定**】**
6. ⇒ **⇒ 也【没有【会阻塞**的东西**】
7. ⇒ **⚠ 而 `DB_FindXAssetHeader`（`0x49CF30`）【是【错误的门**】】
8. ⇒ **对【任何【从引擎自己的线程之外**驱动**的东西**
9. ⇒ **⇒ 它【取一个临界区**】
10. ⇒ **⇒ 【等一个流式事件**】
11. ⇒ **⇒ 而【按 `GetCurrentThreadId` 【对三个不同的线程 id**分支**】
12. ⇒ **⇒ 而【在一个活的客户端上【它【确实那样做了**】】
```

### 3.2 ⭐⭐⭐ **"没有临界区、没有分配、没有一个会搞错的调用约定、没有会阻塞的东西"**

**✅ 这是本报告里**最重要的一条"四条只读纪律**。**

**✅ 与 §463 的"值得做，但它是另一个原生 ABI，不是可以猜的东西"**——**同族** ✓

**⇒ 三层**：
```text
调用引擎 ⇒ **四条风险**（临界区 / 分配 / 调用约定 / 阻塞）
表遍历 ⇒ **零风险**
⇒ **⇒ 所以【后者【是【唯一**可行的路径**
```

**✅ ⭐⭐⭐ **"后者是唯一可行的路径"** —— 而 **"在一个活的客户端上它确实那样做了"** 是**实测证据**。

**⚠ 而"按 `GetCurrentThreadId` 对三个不同的线程 id 分支"**⇒ **一个具体的行为**。**

**⇒ 十层**：
```text
`DB_FindXAssetHeader` 【按线程 id 分支**】
⇒ **⇒ 所以【它的行为【取决于【谁在调**】】
⇒ **⇒ 所以【在【我们的线程上**它【可能【阻塞 / 走上一个错误的分支**】
```

**✅ ⭐⭐⭐ **"它的行为取决于谁在调"** —— 一个**极精确的判断**。

**✅ 与 §465 的"`SV_MapTriggerTouches` 的 REFUSES"**——**不同**（这里**注释与实测一致**）。

### 3.3 而**"`createDefault false`"**

```cpp
// createDefault false: a missing material must read as missing, not
// as the default one, or every surface would silently draw wrong.
return find(OlfinalMaterialAssetType, name.c_str(), false);
```

**⇒ 十层**：
```text
1. **`createDefault = false`**
2. ⇒ **因为【一个缺失的材质【必须【读作缺失**】】
3. ⇒ **⇒ 而【不是【读作默认的那个**】】
4. ⇒ **⇒ 否则【每一个表面【会【静默地画错**】】
```

**✅ ⭐⭐⭐ **"每一个表面会静默地画错"** —— 与 §467 的"一个回落比一个失败更危险"**同族**（**第二次"静默的错误比失败坏**）。

**⇒ 三层**：
```text
§467  **回落到 `info_player_start` ⇒ 在地图下面**
§468  **回落到默认材质 ⇒ 每个表面画错**
⇒ **⇒ 两次"一个默认值【是【陷阱**】
```

**✅ ⭐⭐ **"一个默认值是陷阱"两例**。

**✅ 而"表遍历【不可能创造一个默认**"⇒ **一个结构上的优势**。

**⇒ 三层**：
```text
`DB_FindXAssetHeader` ⇒ **能造默认**（`createDefault = true`）
表遍历 ⇒ **只能找到或找不到**
⇒ **⇒ 所以【表遍历【天然【没有那个陷阱**】
```

**✅ ⭐⭐⭐ **"表遍历天然没有那个陷阱"**。

## 四、**XAnimParts 的重定位：一个"必须恰好铺满"的走**（本组第三重要）

### 4.1 那段

```cpp
if (p != asset.storage.size())
{
    // The same standard the decoder holds itself to: a walk that does not
    // tile the blob has not understood it.
    error = "arrays tile " + std::to_string(p) + " of " +
        std::to_string(asset.storage.size()) + " bytes";
    return std::nullopt;
}
```

**⇒ 二十四层**：
```text
1. **一个走【必须【恰好铺满**那个 blob】
2. ⇒ **⇒ 否则【它【没有理解它**】】
3. ⇒ **⇒ 而【那是【解码器【对自己【持有的同一个标准**】】
```

### 4.2 ⭐⭐⭐ **"一个不铺满 blob 的走没有理解它"**

**✅ 这是本报告里**最重的一条"理解的可判定判据**。**

**✅ 与 §466 的"`192/192` 零误差"**——**一个同族的"零余量** ✓

**⇒ 三层**：
```text
数据结构 ⇒ **一个字节序列**
走 ⇒ **一个游标**
⇒ **⇒ 所以【`p == size` 【是【唯一**的"完全理解**"证明**
```

**✅ ⭐⭐⭐ **"`p == size` 是唯一的『完全理解』证明"** —— 一个**极精确的判据**。

**⚠ 而"`blob.size() < XAnimPartsSize` ⇒ 拒绝"**⇒ **第一个守卫**。

**⇒ 三层**：
```text
`< 88` ⇒ **"shorter than the 88-byte header"**
⇒ **⇒ 所以【一个【前缀**的守卫**
```

**✅ ⭐⭐ **"一个前缀的守卫"**。

### 4.3 而**`claim` 的三态**

```cpp
const auto claim = [&](const std::size_t offset, const std::size_t bytes,
                       const char *const what) -> bool {
    const auto placeholder = readU32(d, offset);
    if (placeholder == 0)
    {
        // A NULL array must be empty; a non-empty one must be present.
        if (bytes != 0) { error = ...; return false; }
        return true;
    }
    if (placeholder != InlineFollows) { error = ...; return false; }
    if (p + bytes > asset.storage.size()) { error = ...; return false; }
    writePointer(d, offset, d + p);
    p += bytes;
    return true;
};
```

**⇒ 十六层**：
```text
1. **`0` ⇒ NULL** ⇒ **⇒ 而【那个 `bytes` 【必须为 `0`**】】
2. ⇒ **`0xFFFFFFFF`（`InlineFollows`）⇒ 【载荷在【内联之后**】】
3. ⇒ **其它 ⇒ 【拒绝**】**
4. ⇒ **⇒ 而【`p + bytes > size` ⇒ 拒绝**】**
5. ⇒ **⇒ 而【通过 ⇒ 【写一个指针【到我们自己的存储**】】
```

**✅ ⭐⭐⭐ **"一个 NULL 数组必须是空的；一个非空的必须是存在的"** —— 一个**双向一致性**检查。

**✅ 与 §466 的"`claim` 与 `Skipped`"**——**不同**（-个**关于字节**，一个**关于编号**）—— 但都是**"双向"**。

**⇒ 三层**：
```text
§466  **`Skipped` 五个不消耗号 ⇒ 其余都消耗**（**一个划分**）
§468  **NULL ⇔ `bytes == 0`**（**一个双向蕴含**）
⇒ **⇒ 两个方向性检查**
```

**✅ ⭐⭐ **"两个方向性检查"**。

**⚠ 而 `InlineFollows = 0xFFFFFFFF`**——**与 `StreamedModelSurfs = 0xFFFFFFFE`** 是一个**同族的哨兵**。

**⇒ 三层**：
```text
`XAnimParts` ⇒ **`0xFFFFFFFF` = 载荷内联**
`XModel` ⇒ **`0xFFFFFFFE` = 流式表面**
⇒ **⇒ 所以【两个【相邻**的哨兵，两个不同的含义**
```

**✅ ⭐⭐⭐ **"两个相邻的哨兵，两个不同的含义"** —— 一个**极精确的观察**。

**⚠ 而"`0xFFFFFFFE` 比 `0xFFFFFFFF` 少一"**⇒ **可能是【故意的，以区分**。

**⇒ 三层**：
```text
`0xFFFFFFFF` = `-1` ⇒ **内联**
`0xFFFFFFFE` = `-2` ⇒ **流式**
⇒ **⇒ 所以【两个负数【区分两种"不是指针**"**
```

**✅ ⭐⭐ **"两个负数区分两种『不是指针』"**。

### 4.4 而**"脚本字符串最后，所以一个解析器失败不能留下一个半重定位的资产"**

```cpp
// Script strings last, so a resolver failure cannot leave a half-relocated
// asset that still looks structurally sound.
```

**⇒ 十层**：
```text
1. **脚本字符串【放在最后**】
2. ⇒ **⇒ 所以【一个解析器失败【不能留下【一个半重定位的**资产**】
3. ⇒ **⇒ 那个资产【仍然【看起来【结构上健全**】】
```

**✅ ⭐⭐⭐ **"一个半重定位的资产仍然看起来结构上健全"** —— 一个**极精确的危险**。

**✅ 与 §463 的"一个 bug 只在另一个被修好之后才暴露"**——**不同**（一个**掩盖**，一个**暴露**）但**同族**（**"一个伪装成好的坏"**）。

**⇒ 三层**：
```text
§463  **密码文被当成 flags** ⇒ **看起来合法**
§468  **半重定位的资产** ⇒ **看起来结构上健全**
⇒ **⇒ 两次"一个伪装的坏**】
```

**✅ ⭐⭐ **"一个伪装的坏"两例**。

**✅ ⭐⭐ **"顺序【可以【变成一个安全性属性**"** —— 本报告的一条**设计原则**。

## 五、**`XModelSize = 360` 与"一个说谎的骨骼数是一个崩溃而不是一个视觉故障"**

### 5.1 那段

```cpp
// Pure apart from the two resolvers. Refuses on any disagreement between the
// header's scalars and the arrays it was given, because a published XModel
// whose bone count lies is a crash rather than a visual glitch.
```

**⇒ 十层**：
```text
1. **拒绝【头部的标量与它被给的数组【之间的任何不一致**】】
2. ⇒ **因为【一个【骨骼数说谎**的已发布 XModel】
3. ⇒ **是【一个崩溃**，而不是【一个视觉故障**】
```

### 5.2 ⭐⭐⭐ **"一个说谎的骨骼数是一个崩溃而不是一个视觉故障"**

**✅ 与 §422 的"`static_assert(sizeof(WorldClientState) == 25184)` 是【一个行为，不是一个细节**】"**同族**（**第三次"一个数是一个行为**）。

**⇒ 三层**：
```text
§381  **`WorldClientState` 的 `48` 字节 ⇒ 腿部动画在 5.3% 帧丢失**
§463  **`unk04A4Time` 的"生产值" ⇒ 出生被拒**
§468  **`numBones` 说谎 ⇒ 崩溃**
⇒ **⇒ 三次"一个数【不是细节**】
```

**✅ ⭐⭐ **"一个数不是细节"三例表**。

**⚠ 而六条 `expect` 的长度**：
```text
parentList            nonRoot
quats                 8 * nonRoot
trans                 12 * nonRoot
partClassification    bones
baseMat               32 * bones
```

**⇒ 十六层**：
```text
1. **`parentList` ⇒ `1` 字节 × `nonRoot`**
2. ⇒ **`quats` ⇒ `8` 字节 × `nonRoot`**（**`i16` × `4`**）
3. ⇒ **`trans` ⇒ `12` 字节 × `nonRoot`**（**`float` × `3`**）
4. ⇒ **`partClassification` ⇒ `1` 字节 × `bones`**
5. ⇒ **`baseMat` ⇒ `32` 字节 × `bones`**
6. ⇒ **⇒ 所以【`nonRoot` 与 `bones` 【是两个不同的**分母**】
```

**✅ ⭐⭐⭐ **"`nonRoot` 与 `bones` 是两个不同的分母"** —— 一个**极容易写错的地方**。

**⚠ 而 `nonRoot = bones - roots`** 而**`roots > bones` ⇒ 拒绝**。**

**⇒ 三层**：
```text
`roots > bones` ⇒ **一个不可能的**头 ⇒ **拒绝**
⇒ **⇒ 所以【`nonRoot` 【不会【下溢**】
```

**✅ ⭐⭐ **"`nonRoot` 不会下溢"**。

### 5.3 而**"`lodInfo[0].modelSurfs` 是 `0xFFFFFFFE`"与"`lodInfo[0].name` 是【松散的资源名**"**

```cpp
// lodInfo[0].modelSurfs carries the streamed sentinel 0xFFFFFFFE and
// lodInfo[0].name is the LOOSE resource name - `models/%s` is one of the three
// channels out.exe still honours, so the surfaces arrive from the overlay
// rather than from the zone.
```

**⇒ 十二层**：
```text
1. **表面【从【overlay 到达，而不是从【zone**】】
2. ⇒ **原因：`models/%s` 是 `out.exe` 仍然【承认的三个通道之一**】
3. ⇒ **⇒ 所以【`lodInfo[0].name` 【是一个【松散的资源名**】
4. ⇒ **⇒ 而【`modelSurfs` 【是那个【流式哨兵**】
```

**✅ ⭐⭐⭐ **"`models/%s` 是 `out.exe` 仍然承认的三个通道之一"** —— 一个**极具体的引擎事实**。

**⚠ 而"三个通道"⇒ **另外两个是什么？** **⇒ 一个未闭合点。**

**⇒ 三层**：
```text
本文件：`models/%s`
其它：**未列出**
⇒ **⇒ 所以【另外两个【未闭合**】
```

## 六、**`SV_BuildForgeXModel` 的"一次布局，所以一个指针被取走之后什么也不能动"**

```cpp
// Lay the payload out once, so nothing can move after a pointer is taken.
std::size_t p = XModelSize;
const std::size_t nameAt = p;              p += model.name.size() + 1;
p = alignUp(p, 2);
const std::size_t boneNamesAt = p;         p += 2u * bones;
const std::size_t parentListAt = p;        p += nonRoot;
p = alignUp(p, 4);
const std::size_t quatsAt = p;             p += model.quaternions.size();
...
asset.storage.assign(p, std::byte{0});
```

**⇒ 二十层**：
```text
1. **先【算完整个布局**】（**一个 `p` 游标**）
2. ⇒ **⇒ 然后【一次 `assign(p)` 分配**】**
3. ⇒ **⇒ 然后【才【写**】
4. ⇒ **⇒ 所以【一个指针【被取走之后【什么也不能动**】】
5. ⇒ **两处 `alignUp`**（`2` 与 `4`）
6. ⇒ **⇒ 所以【`boneNames` 是 `2` 对齐，`quats` 是 `4` 对齐**】
```

### 6.1 ⭐⭐⭐ **"一次布局，所以一个指针被取走之后什么也不能动"**

**✅ 与 §415 的"`storage` 必须【越过客户端**存活**"**——**完全同族** ✓

**⇒ 三层**：
```text
§415  **`DB_LinkXAssetEntry` 【复制 `88` 字节的头但【保留【里面的每一个指针**】**
§468  **"一次布局，所以一个指针被取走之后什么也不能动"**
⇒ **⇒ 所以【`storage` 【是一个【被引擎持有的**字节序列**】
```

**✅ ⭐⭐⭐ **"`storage` 是一个被引擎持有的字节序列"** —— 一个**极重要的所有权事实**。

**⚠ 而 `std::vector<std::byte>` 的【重新分配**会移动**⇒ **注释明说**。**

```cpp
// Published assets are never released: DB_LinkXAssetEntry copies the
// 88-byte header but keeps the pointers inside it, so the engine holds
// references into this storage for the life of the process. unique_ptr so
// that growing the list can never move an asset that has been published.
static std::vector<std::unique_ptr<SvForgeXAnimAsset>> published;
```

**⇒ 十层**：
```text
1. **`published` 是 `vector<unique_ptr<...>>`**
2. ⇒ **⇒ 所以【`vector` 增长【只会移动【那个 `unique_ptr`**，不会移动【那个资产**】
3. ⇒ **⇒ 所以【一个已发布的资产【永远不会移动**】
4. ⇒ **⇒ 而【`unique_ptr` 【正是**那个保证**
```

**✅ ⭐⭐⭐ **"`unique_ptr` 正是那个保证"** —— 一个**极精确的容器选择理由**。

**✅ 与 §429 的"`slot->baselineFrame.reset()`"**——**一个对照**（那里**重置**，这里**永不释放**）。

**⇒ 三层**：
```text
§426  **`baselineCacheAcknowledged` 与 `deltaMessage` 必须一起清**
§468  **已发布的资产【永不释放**】
⇒ **⇒ 所以【生命周期【由【谁能看到它**决定**
```

**✅ ⭐⭐ **"生命周期由谁能看到它决定"**。

## 七、**Material 的克隆：`nameHash` 作为一个跨材质的键**

### 7.1 那段

```cpp
// A Material is CLONED, never authored. `MaterialTextureDef.nameHash` is
// produced by the asset pipeline and appears nowhere in the client, so it
// cannot be recomputed - but it does not have to be. The hash covers the
// SAMPLER NAME, so the same slot carries the same hash in every material that
// has it, which makes it a usable key for matching a clone's slots to a port's.
//
// Measured across 2,849 shipped materials (nameStart/nameEnd are literally the
// first and last characters of the sampler name):
//
//   colorMap     'c'..'p'   0xa0ab1041   semantic 2   2920 uses
//   normalMap    'n'..'p'   0x59d30d0f   semantic 5   2575
//   specularMap  's'..'p'   0x34ecccb3   semantic 8   2251
//   detailMap    'd'..'p'   0xeb529b4d   semantic 5     92
```

**⇒ 二十四层**：
```text
1. **一个 Material 【是【被克隆的，从不被编写**】**
2. ⇒ **`nameHash` 【由资产管线产生【而【在客户端里【不出现**】】
3. ⇒ **⇒ 所以【它【不能被重算**】】
4. ⇒ **⇒ 但它【不必**【被重算**】**
5. ⇒ **⇒ 因为那个哈希【覆盖【那个 sampler 名字**】】
6. ⇒ **⇒ 所以【同一个槽【在【每一个有它的材质里【携带同一个哈希**】】
7. ⇒ **⇒ 所以【它【是一个【可用的键**】，用来【把克隆的槽【匹配到【移植的槽**】
8. ⇒ **⇒ 而【这个键【在 `2,849` 个已发布的材质上【被测量**】
9. ⇒ **⇒ 而【`nameStart`/`nameEnd` 【字面上【是那个 sampler 名字的第一个和最后一个字符**】
```

### 7.2 ⭐⭐⭐ **"它不能被重算，但它不必被重算"**

**✅ 这是本报告里**最漂亮的一条"一个无法重算的值的可用性**。**

**✅ 与 §466 的"规则是一个近似而表是精确"**——**同族**（**一个值**不可推导**但**可复用**）。

**⇒ 三条**：
```text
不可重算 ⇒ 所以【不能【生成一个哈希**】
但可复用 ⇒ 所以【可以【读一个哈希**】
⇒ **⇒ 所以【`nameHash` 【是一个【键**而不是【一个值**】
```

**✅ ⭐⭐⭐ **"`nameHash` 是一个键而不是一个值"**。

**⚠ 而"`nameStart`/`nameEnd` 字面上是第一个和最后一个字符"**⇒ **一个极精确的测量方法**。

**⇒ 三层**：
```text
`colorMap` ⇒ **`'c'`..`'p'`**（**`nameStart = OffTexNameStart = 4`，`nameEnd = OffTexNameEnd = 5`**）
⇒ **⇒ 所以【那两个字节【就是【一个名字的**范围**】
```

**✅ ⭐⭐⭐ **"那两个字节就是一个名字的范围"** —— 一个**极精巧的布局**。

**⚠ 而四个 `semantic`**：`2` / `5` / `8` / `5`**（**`normalMap` 与 `detailMap` 都是 `5`**）。

**⇒ 十层**：
```text
`colorMap` ⇒ **`2`**
`normalMap` ⇒ **`5`**
`specularMap` ⇒ **`8`**
`detailMap` ⇒ **`5`**
⇒ **⇒ 所以【`semantic` 【不能区分** `normalMap` 与 `detailMap`】
```

**✅ ⭐⭐⭐ **"`semantic` 不能区分 normalMap 与 detailMap"** —— 一个**极重要的观察**。

**⇒ 三层**：
```text
`semantic` ⇒ **一个【粗粒度**的类**
`nameHash` ⇒ **一个【精确**的键**
⇒ **⇒ 所以【必须用 `nameHash`**】
```

**✅ ⭐⭐⭐ **"必须用 nameHash"** —— 这正是**代码的选择**（`if (readU32(...) == hash)`）。

### 7.3 而**"按位置匹配的失败"**

```cpp
// Match by nameHash rather than by position: writing an image into the
// wrong slot draws a normal map as diffuse instead of failing.
```

**⇒ 十层**：
```text
1. **按 `nameHash` 匹配【而不是按位置**】
2. ⇒ **因为【把一个图像写进【错的槽**】】
3. ⇒ **画出一个法线贴图【当作漫反射**】
4. ⇒ **⇒ 【而不是【失败**】
```

**✅ ⭐⭐⭐ **"一个法线贴图画成漫反射，而不是失败"** —— 与 §467 的"一个回落到 `info_player_start` 在地图下面"**同族**（**第三次"静默的错误比失败坏**）。

**⇒ 三层**：
```text
§467  **回落 ⇒ 在地图下面**
§468  **默认材质 ⇒ 每个表面画错**
§468  **按位置绑定 ⇒ 法线当漫反射**
⇒ **⇒ 三次"一个错的**成功**比一个失败坏**】
```

**✅ ⭐⭐ **"一个错的『成功』比一个失败坏"三例表**。

**⚠ 而"`filled[at]` ⇒ 同一个槽被给两次 ⇒ 拒绝"**⇒ **一个"双重赋值**的检查**。

**⇒ 三层**：
```text
一个槽【被给两次**】⇒ **`error = "slot '...' was given twice"`**
⇒ **⇒ 所以【一个【明确**的拒绝**
```

**✅ ⭐⭐ **"一个明确的拒绝"**。

### 7.4 而**"`techniqueSet`、常量和状态位【继续指向克隆的引擎持有的内存**"**

```cpp
// Everything else - techniqueSet, constants, state bits - keeps pointing at
// the clone's engine-owned memory, which is the point of cloning.
```

**⇒ 十层**：
```text
1. **只替换【纹理表和名字**】
2. ⇒ **其余【保持【指向【克隆的引擎持有的内存**】】
3. ⇒ **⇒ 所以【一个【浅拷贝**的克隆**
```

**✅ ⭐⭐ **"一个浅拷贝的克隆"** —— 而 **"那是克隆的作用**"。

**✅ 与 §462 的"`altForceTest` 用一个武器的 alt 资产"**——**同族**（**第三次"浅拷贝**）。

## 八、**CoD4 材质文件的"每一个指针都是一个文件偏移"**

### 8.1 那段

```cpp
// Every pointer field in the file is a FILE OFFSET - the package was dumped
// with its pointers rebased - so the whole thing is self-contained.
```

**⇒ 十层**：
```text
1. **每一个指针字段【是一个【文件偏移**】
2. ⇒ **（那个包【是【把它的指针【重定基**后导出的）**
3. ⇒ **⇒ 所以【整个东西【是【自包含**的**
```

### 8.2 ⭐⭐⭐ **"整个东西是自包含的"**

**✅ 与 §468 三 的"`claim` 的 `InlineFollows`"**——**一个同族**（**一个"载荷内联**"与一个"偏移重定基**"）。

**⇒ 三层**：
```text
`XAnimParts` ⇒ **`0xFFFFFFFF` ⇒ 载荷【在内联之后**】
CoD4 材质 ⇒ **`u32` 偏移 ⇒ 载荷【在文件内**】
⇒ **⇒ 两种"自包含**的表示**
```

**✅ ⭐⭐ **"两种自包含的表示"**。

**⚠ 而 `stringAt` 的"必须【在文件内终止**"**⇒ **一个"封闭性**的检查**。

**⇒ 十层**：
```cpp
const auto stringAt = [&file](const std::uint32_t at, std::string &out) -> bool {
    if (at == 0 || at >= file.size()) return false;
    for (std::size_t i = at; i < file.size(); ++i)
        if (file[i] == std::byte{0}) { out.assign(...); return !out.empty(); }
    return false;
};
```
```text
1. **`at == 0 ⇒ 拒绝**（**偏移 `0` 是【那个名字自己的偏移位置**，不是【一个字符串**）
2. ⇒ **`at >= size ⇒ 拒绝**】
3. ⇒ **没有终止符 ⇒ 拒绝**】
4. ⇒ **空字符串 ⇒ 拒绝**（`!out.empty()`）**
5. ⇒ **⇒ 所以【四道封闭性**】
```

**✅ ⭐⭐⭐ **"偏移 0 是那个名字自己的偏移位置，不是一个字符串"** —— 一个**极精确的辩解**。

**⚠ 而 §467 的 `parseVector` 的"`cursor == end`"**——**一个同族的"完全用尽**"**。

**⇒ 三层**：
```text
§467  **`parseVector` ⇒ `cursor == end`**
§468  **`stringAt` ⇒ 必须在 `file.size()` 内终止**
§468  **`SV_RelocateForgeXAnim` ⇒ `p == storage.size()`**
⇒ **⇒ 三次"必须【在边界内【恰好用尽**】
```

**✅ ⭐⭐⭐ **"必须在边界内恰好用尽"三例表** —— 本报告的**一条贯穿的纪律**。

### 8.3 而**"一个没有测量 nameHash 的 sampler 不能被匹配"**

```cpp
// A sampler with no measured nameHash cannot be matched against a
// clone's slots, and matching by position is the mistake this whole
// path exists to avoid. Refuse rather than bind it somewhere.
if (SV_ForgeSamplerHash(slot.semantic) == 0)
{
    error = "sampler '" + slot.semantic +
        "' has no measured nameHash, so it cannot be matched by hash";
    return std::nullopt;
}
```

**⇒ 十层**：
```text
1. **一个【没有测过 nameHash** 的 sampler【不能被匹配**】
2. ⇒ **⇒ 而【按位置匹配【是【这条路径【整个存在的理由【要避免**的那个错误**】
3. ⇒ **⇒ 拒绝**而不是【绑到某个地方**】
```

**✅ ⭐⭐⭐ **"按位置匹配是这条路径整个存在的理由要避免的那个错误"** —— 一个**极强的自述**。

**✅ 与 §466 的"`Skipped` 的五个 classname【是【这个文件存在的理由**"**——**一个同族**（**第四次"一个文件的自述理由**）。

**⇒ 三层**：
```text
§466  **`Skipped` ⇒ 一个近似的规则 ⇒ §414 的 `288/397` 平台化的解法**
§468  **`SV_ParseForgeCod4Material` ⇒ 避免按位置绑定**
§468  **`SV_ForgeXAssetTable` ⇒ 避免 `DB_FindXAssetHeader` 的阻塞**
⇒ **⇒ 三个"一个结构【为了避免**一个具体的错误**】
```

**✅ ⭐⭐ **"一个结构为了避免一个具体的错误"三例**。

## 九、**WeaponDef 的枚举表："没有见证的值【故意缺席**"**

### 9.1 那段

```cpp
// CODREF(alpha_weapondef): every enum value below is read off a port in
// SV_AlphaWeaponPorts(), each of which was decoded from a shipped weapon
// rather than inferred. The Uzi (weaponClass 3, penetrateType 1, fireType
// 0) is the SMG witness and the one this mapping leans on hardest.
//
// Values with no witness are deliberately absent: an unmapped string is
// rejected rather than defaulted, because a wrong weaponClass is a
// gameplay change that would look like a port bug for weeks.
```

**⇒ 二十四层**：
```text
1. **每一个枚举值【都【从一个 port【读出来**】
2. ⇒ **而【那个 port 【从【一个已发布的武器【解码**】】
3. ⇒ **⇒ 而【不是【从推断**】
4. ⇒ **⇒ `Uzi`（`weaponClass 3` / `penetrateType 1` / `fireType 0`）【是【SMG 见证**】
5. ⇒ **⚠ 【没有见证的值【故意缺席**】】
6. ⇒ **⇒ 因为【一个未映射的字符串【被拒绝**而不是【取默认**】
7. ⇒ **⇒ 因为【一个错的 `weaponClass` 【是一个玩法变更**】
8. ⇒ **⇒ 而【那个【会【看起来像一个移植的 bug【好几周**】】
```

### 9.2 ⭐⭐⭐ **"一个错的 weaponClass 会看起来像一个移植的 bug 好几周"**

**✅ 这是本报告里**最重要的一条"一个错的枚举值的**可诊断性**。**

**✅ 与 §467 的"一个静默的解析失败会把第三名放上冠军的台座"**——**同族**（**第四次"宽容是掩盖**）。

**⇒ 三层**：
```text
拒绝 ⇒ **`"weaponClass 'xxx' has no measured OLfinal value"`** ⇒ **一个清晰的日志**
默认 ⇒ **一个错的类** ⇒ **一个"移植 bug"** ⇒ **几周的误诊**
⇒ **⇒ 所以【拒绝**永远**比默认**好**
```

**✅ ⭐⭐⭐ **"拒绝永远比默认好"** —— 而 **"几周的误诊"** 是**代价的量化**。</br>

**✅ 与 §463 的"命名 + 值 = 一个可诊断的错误"**——**一个同族**（**第二次**）。

### 9.3 而**五张表的实际内容**

```cpp
constexpr EnumEntry WeaponTypes[]{ {"bullet", 0} };
constexpr EnumEntry WeaponClasses[]{
    {"rifle", 0}, {"assault", 0},     // Fal, Tavor, Masada
    {"sniper", 1},                    // Barrett
    {"smg", 3},                       // Uzi
    {"pistol", 5},                    // Colt Anaconda
};
constexpr EnumEntry PenetrateTypes[]{
    {"small", 1}, {"medium", 2}, {"large", 3},
};
constexpr EnumEntry ImpactTypes[]{
    {"bullet_small", 0}, {"bullet_large", 0},
};
constexpr EnumEntry FireTypes[]{
    {"full auto", 0}, {"single shot", 1},
};
```

**⇒ 十六层**：
```text
1. **`WeaponTypes` ⇒ 一个**（`bullet` → `0`）
2. ⇒ **`WeaponClasses` ⇒ 五个**，**而 `rifle` 与 `assault` 【都是 `0`**】
3. ⇒ **⇒ 所以【两个名字【一个值**】
4. ⇒ **`PenetrateTypes` ⇒ 三个**（`1`/`2`/`3`）
5. ⇒ **`ImpactTypes` ⇒ 两个**，**而【都是 `0`**】
6. ⇒ **⇒ 所以【两个名字【一个值**】
7. ⇒ **`FireTypes` ⇒ 两个**（`0`/`1`）
8. ⇒ **⇒ 所以【五张表【共 `13` 个条目，`8` 个不同的值**】
```

**✅ ⭐⭐⭐ **"五张表共 13 个条目，8 个不同的值"** —— 一个**极小的覆盖面**。

**⚠ 而"`rifle` 与 `assault` 都是 `0`，`bullet_small` 与 `bullet_large` 都是 `0`"**⇒ **两个"同值异名**"**。

**⇒ 三层**：
```text
同值异名 ⇒ **一个"多个源名字 ⇒ 同一个目标值**"的映射**
⇒ **⇒ 所以【不是【一个恒等映射**】
```

**✅ ⭐⭐ **"不是恒等映射"**。

**⚠ 而"`WeaponClasses` 的 `5` 个值：`0`/`1`/`3`/`5`"⇒ **缺 `2` 与 `4`**。**

**⇒ 十层**：
```text
`0` ⇒ `rifle`/`assault`
`1` ⇒ `sniper`
`3` ⇒ `smg`
`5` ⇒ `pistol`
⇒ **⇒ 所以【`2` 与 `4` 【没有见证**】⇒ **缺席**
```

**✅ ⭐⭐⭐ **"`2` 与 `4` 没有见证 ⇒ 缺席"** —— 一个**极精确的覆盖缺口**。

**⚠ 而 §460 的"`MaximumViewmodelIndex = 0x3FF` vs `MaximumWeaponIndex = 0x7FF`"**——**一个对照**（那里**两个数**，这里**五张表**）。

### 9.4 而**`HitLocationKeys` 的"索引 0 是 none，1..5 是头与躯干组"**

```cpp
// CoD4's hit-location keys, in the order the first six entries of
// SvAlphaWeaponTuning::hitLocationMultipliers carry them. Both the
// Standard set (1.0 then 1.4, 1.4, 1.0, 1.0, 1.0) and the Barrett's
// (1.0 then 1.5 x5) agree that index 0 is `none` and 1..5 are the head and
// torso group. Beyond index 5 the order has NO witness, so the remaining
// entries keep their Standard values and CoD4's `locGun` is not mapped.
constexpr const char *HitLocationKeys[]{
    "locNone", "locHelmet", "locHead", "locNeck",
    "locTorsoUpper", "locTorsoLower",
};
```

**⇒ 二十四层**：
```text
1. **`StandardHitLocations` ⇒ `{1.0, 1.4, 1.4, 1.0, 1.0, 1.0}` 然后【全 `1.0`，除了两个 `0.0`**】
2. ⇒ **`Barrett` ⇒ `{1.0, 1.5×5}`**
3. ⇒ **⇒ 两套**都同意 `index 0` 是 `none` 而 `1..5` 是【头与躯干组**】
4. ⇒ **⇒ 而在 `index 5` 之后【那个顺序【没有见证**】】
5. ⇒ **⇒ 所以【剩下的条目【保持 `Standard` 的值**】
6. ⇒ **⇒ 而 CoD4 的 `locGun` 【不被映射**】
```

**✅ ⭐⭐⭐ **"在 index 5 之后那个顺序没有见证"** —— 一个**极精确的边界**。

**✅ 与 §468 九 的"没有见证的值故意缺席"**——**完全同族**（**第二次"没有见证 ⇒ 缺席**）。

**⇒ 三层**：
```text
`WeaponClasses` ⇒ **没有见证的名字 ⇒ 不在表里**
`HitLocationKeys` ⇒ **没有见证的顺序 ⇒ 不映射**
⇒ **⇒ 两次"没有见证 ⇒ 缺席**】
```

**✅ ⭐⭐ **"没有见证 ⇒ 缺席"两例**。

**⚠ 而 `StandardHitLocations` 有两个 `0.0`**：`index 17` 与 `index 18`。

```cpp
1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f,   // 0..6
1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f,   // 7..13
1.0f, 1.0f, 1.0f, 1.0f, 0.0f, 0.0f, 1.0f,   // 14..20
```

**⇒ 十层**：
```text
`index 0..5` ⇒ **`1.0, 1.4, 1.4, 1.0, 1.0, 1.0`**
`index 6..16` ⇒ **`1.0`**
`index 17..18` ⇒ **`0.0`**
`index 19` ⇒ **`1.0`**
`index 20` ⇒ **`1.0`**
⇒ **⇒ 所以【`21` 个条目，`2` 个零**】
```

**✅ ⭐⭐ **"`21` 个条目，`2` 个零"** —— 而 `index 17`/`18` 是**什么**？**未闭合**。

**⚠ 而 `HitLocationCount`** 可能是 `21`——**与 `StandardHitLocations` 的大小一致**。

**⇒ 三层**：
```text
`std::array<float, HitLocationCount> StandardHitLocations{...}` ⇒ **`21` 个初值**
⇒ **⇒ 所以【`HitLocationCount = 21`**】
```

**✅ ⭐⭐ **"`HitLocationCount = 21`"** —— 一个**可推导的常量**。

### 9.5 而**"CoD4 存秒；目标存毫秒"**

```cpp
// CoD4 stores durations in SECONDS; the target stores milliseconds.
const auto milliseconds = [&](const char *k, std::int32_t &out) {
    double v{};
    if (!number(k, v)) return false;
    if (v < 0.0 || v > 60.0) { error = ...; return false; }
    out = static_cast<std::int32_t>(v * 1000.0 + 0.5);
    return true;
};
```

**⇒ 十层**：
```text
1. **一个单位转换**（秒 ⇒ 毫秒）
2. ⇒ **`0..60` 的范围**
3. ⇒ **⇒ 而 `+ 0.5` 【一个四舍五入**】
4. ⇒ **⇒ 所以【`0.0015` 秒 ⇒ `2` 毫秒**】
```

**✅ ⭐⭐ **"`0.0015` 秒 ⇒ `2` 毫秒"** —— 一个**精确的舍入**。

**⚠ 而"`fireTimeMilliseconds <= 0` ⇒ 拒绝"**⇒ **一个"零**的检查**。

**⇒ 三层**：
```text
`fireTime` ⇒ **必须 > `0`**
⇒ **⇒ 所以【`0.0004` 秒【会【四舍五入到 `0`** ⇒ **拒绝**】
```

**✅ ⭐⭐⭐ **"`0.0004` 秒会四舍五入到 0 ⇒ 拒绝"** —— 与 §464 的"appender 只能走一步"**同族**（**第二次"一个零是危险的**）。

**⚠ 而六条交叉校验**：
```text
minDamage <= damage
maxDamageRange <= minDamageRange
startAmmo <= maxAmmo
fireTime > 0
hipSpreadStandMin <= hipSpreadMax
```

**⇒ 十层**：
```text
1. **五条不等式**（**上面列了五条**）
2. ⇒ **⇒ 而【每一条【都是一个【物理**约束**】
3. ⇒ **（弹道的最小伤害【不能超过最大伤害**）**
4. ⇒ **（最大伤害的距离【不能超过最小伤害的距离**）**
5. ⇒ **（起始弹药【不能超过上限**）**
6. ⇒ **（站立的最小散布【不能超过最大散布**）**
```

**✅ ⭐⭐⭐ **"每一条都是一个物理约束"**。

**⚠ 而"`SpreadKeys` 的六元组：`{standMin, duckedMin, proneMin, max, duckedMax, proneMax}`"**⇒ **一个**极具体的顺序**。

**⇒ 十二层**：
```text
`hipSpreadStandMin` ⇒ `[0]`
`hipSpreadDuckedMin` ⇒ `[1]`
`hipSpreadProneMin` ⇒ `[2]`
`hipSpreadMax` ⇒ `[3]`
`hipSpreadDuckedMax` ⇒ `[4]`
`hipSpreadProneMax` ⇒ `[5]`
⇒ **⇒ 而【Uzi 的已发布值 `{2.0, 1.75, 1.5, 5.0, 4.5, 4.0}`**】
```

**✅ ⭐⭐⭐ **"Uzi 的 `{2.0, 1.75, 1.5, 5.0, 4.5, 4.0}`"** —— 一个**极具体的验证**。

**⚠ 而"PPSh 的 CoD4 键【恰好带着那六个数【以那个顺序**"]"⇒ **"那【正是【固定**那个映射【并【说明**那些单位【已经一致**】的东西**"**。

**⇒ 三层**：
```text
若【单位不一致**】⇒ **`{2.0, ...}` 会【变成别的数**】
而【它【恰好**一致**⇒ **⇒ 所以【单位【已经一致**】
```

**✅ ⭐⭐⭐ **"单位已经一致"** —— 一个**极强的"巧合**"论证**。

## 十、**`SV_ForgeStringTableResolver` 的"索引是【每进程】的"**

### 10.1 那段

```cpp
// The index it returns is PER PROCESS. Two clients on one machine give the
// same bone different indices, which is why an emitted asset cannot carry them.
```

**⇒ 十层**：
```text
1. **那个索引【是【每进程**的**】
2. ⇒ **⇒ 所以【同一台机器上的两个客户端【给同一个骨骼【不同的索引**】】
3. ⇒ **⇒ 而【那【正是【为什么【一个已发布的资产【不能【携带它们**】】
```

### 10.2 ⭐⭐⭐ **"索引是每进程的，所以一个已发布的资产不能携带它们"**

**✅ 与 §468 六 的"`storage` 被引擎持有"**——**互补**（那里**必须携带**，这里**不能携带**）。

**⇒ 三层**：
```text
指针 ⇒ **必须【在一个进程里【携带**】（**`storage`**）
脚本字符串索引 ⇒ **不能【跨进程携带**】（**每进程**）
⇒ **⇒ 所以【一个【运行时的重定位**是必须的**
```

**✅ ⭐⭐⭐ **"一个运行时的重定位是必须的"** —— 而 **这正是 `SV_RelocateForgeXAnim` 的作用**。

**✅ 与 §468 四 的"`p == storage.size()`"**——**完全闭合** ✓

**⚠ 而表布局**：
```cpp
// out.exe 0x789C524 holds the script-string table base. Entries are 20 bytes:
//   +0 u16 refcount   +2 u8 kind   +3 u8 length (INCLUDING the NUL)
//   +4.. the name, inline
```

**⇒ 十层**：
```text
`+0` ⇒ `u16 refcount`（**`2` 字节**）
`+2` ⇒ `u8 kind`（`1` 字节）
`+3` ⇒ `u8 length`（**包括 NUL**）
`+4..` ⇒ **名字【内联**】
⇒ **⇒ 而 `stride = 20`** ⇒ **所以【名字【最多 `16` 字节**】
```

**✅ ⭐⭐⭐ **"名字最多 16 字节"** —— 而 **`name.size() > 15` ⇒ 拒绝**。

**⇒ 三层**：
```text
`stride = 20`，名字从 `+4` ⇒ **`20 - 4 = 16` 字节**
而【`length` 包括 NUL**】⇒ **所以【名字【最长 `15`**】
⇒ **⇒ 所以 `if (name.size() > 15) return 0;`** ✓
```

**✅ ⭐⭐⭐ **"`20 - 4 - 1 = 15`"** —— 一个**精确的算术闭合**。

**⚠ 而"`ScriptStringMaxIndex = 0xFFFF`"⇒ **`65,535` 个条目**。**

**⇒ 三层**：
```text
`0xFFFF` ⇒ **`65,535` 个条目**
而【索引 `0` 是【空串**】⇒ **所以【有效索引 `1..65535`**】
```

**✅ ⭐⭐ **"有效索引 `1..65535`"** —— 而 **`SV_ForgeStringResolver` 的 `id <= 0 || id > 0xFFFF` ⇒ 拒绝** ✓

### 10.3 而**"`66` 个里的 `1` 个"**

```cpp
// It cannot intern a name the client does not already have. A port never needs
// that: of the 67 bone names the PPSh animations bind, 66 are already OLfinal
// script strings, and the one that is not is the gun model's own.
```

**⇒ 十层**：
```text
1. **它【不能【intern 一个客户端【没有的**名字**】
2. ⇒ **⇒ 而【一个移植【从不【需要**那个**】
3. ⇒ **因为【PPSh 动画绑定的 `67` 个骨骼名里的 `66` 个【已经是 OLfinal 脚本字符串**】
4. ⇒ **⇒ 而【那一个不是的【是那个枪模型的自己的**】
```

**✅ ⭐⭐⭐ **"67 个里的 66 个已经是 OLfinal 脚本字符串"** —— 一个**极强的测量**。

**✅ 与 §467 的"`69` 个里的 `61` 个带 target"**——**一个同族**（**第二次"`N` 个里的 `M` 个**）。

**⇒ 三层**：
```text
§467  **`69` 个 `zombie_spawner` 里的 `61` 个带 `target`**
§468  **`67` 个骨骼名里的 `66` 个已 intern**
⇒ **⇒ 两次"一个【分数**的完整性**"]
```

**✅ ⭐⭐ **"一个分数的完整性"两例**。

## 十一、**`XAssetMaxChainSteps = 4096` 的"只须阻止一个损坏的 next 空转"**

```cpp
// The measured longest chain is 7. This cap only has to stop a corrupt `next`
// from spinning; it is not a size the table is expected to approach.
inline constexpr std::uint32_t XAssetMaxChainSteps = 4096;
```

**⇒ 十层**：
```text
1. **实测最长的链是 `7`**
2. ⇒ **⇒ 而这个上限【只须【阻止一个损坏的 `next` 【空转**】】
3. ⇒ **⇒ 而它【不是一个【表【被期望【接近**的大小**】
```

**✅ ⭐⭐⭐ **"这个上限只须阻止一个损坏的 next 空转"** —— 一个**极精确的意图声明**。

**✅ 与 §462 的"四十个项共用一个 `return false`"**——**不同**（那里**一个名字**，这里**一个上限**）但**同族**（**"一个防御【只需要【够用**"**）。

**⇒ 三条**：
```text
`XAssetMaxChainSteps = 4096` vs 实测 `7` ⇒ **`585` 倍的余量**
⇒ **⇒ 所以【那个数【不是【一个测量的结果，是一个【防御的选择**】
```

**✅ ⭐⭐⭐ **"585 倍的余量"** —— 而 **"不是一个测量的结果"** 是**一个诚实的标注**。

**⚠ 而"`XAssetMaxNameLength = 1024`"**⇒ **"一个更长的名字【被当成不匹配【而不是【继续读**"**。

**⇒ 三层**：
```text
`1024` ⇒ **一个上限**
超过 ⇒ **不匹配**（**不是截断，不是继续读**）
⇒ **⇒ 所以【fail closed**
```

**✅ ⭐⭐ **"fail closed"** —— 与 §467 的"在第一处空隙停"**同族**（**第三次"fail closed**）。

## 十二、**`SvForgeXAnimStatus` 的 `7` 个状态**

```cpp
enum class SvForgeXAnimStatus : std::uint32_t
{
    Disabled,
    InvalidBlob,        // the blob's arrays do not tile it
    UnresolvedString,   // a bone or notify name did not intern
    MissingBinding,     // an engine function was not supplied
    WrongThread,
    LinkFailed,         // DB_LinkXAssetEntry faulted or refused
    Ready,
};
```

**⇒ 十层**：
```text
1. **`Disabled` ⇒ 闸门关闭**
2. ⇒ **`InvalidBlob` ⇒ 数组【不铺满**那个 blob**】
3. ⇒ **`UnresolvedString` ⇒ 一个骨骼或通知名【没有 intern**】
4. ⇒ **`MissingBinding` ⇒ 一个引擎函数【没有被提供**】
5. ⇒ **`WrongThread` ⇒ 【从未被返回**（**无生产者**）**
6. ⇒ **`LinkFailed` ⇒ `DB_LinkXAssetEntry` 故障或拒绝**
7. ⇒ **`Ready` ⇒ 【成功**】
```

### 12.1 ⭐⭐⭐ **`WrongThread` 是一个【没有生产者】的状态**

**✅ 全文件搜 `WrongThread` ⇒ 只在 `SV_ForgeXAnimStatusName` 的 `case` 里出现。**

**⇒ 十层**：
```text
`WrongThread` 【只在 `SV_ForgeXAnimStatusName` 的一个 `case` 里**】
⇒ **⇒ 所以【它【永远【不会被返回**】
⇒ **⇒ 而【那是【一个【值得注意**的缺口**
```

**✅ ⭐⭐⭐ **"`WrongThread` 永远不会被返回"** —— 一个**真实的不一致**。</br>

**✅ 与 §465 的"`SV_MapTriggerTouches` 的 REFUSES"**——**同族**（**第二次"一个状态【没有生产者**）。

**⇒ 三层**：
```text
§465  **注释说 REFUSES 而代码【不拒绝**】
§468  **`WrongThread` 【没有生产者**】
⇒ **⇒ 两次"一个声明【没有实现**】
```

**✅ ⭐⭐ **"一个声明没有实现"两例** —— **本报告的两个可报告的缺陷**。

**⚠ 而"`DB_FindXAssetHeader` 【按线程 id 分支**"**⇒ **"`WrongThread` 【应该**在那里发生**"**。

**⇒ 三层**：
```text
`DB_FindXAssetHeader` ⇒ **按线程 id 分支**
而 `WrongThread` ⇒ **没有生产者**
⇒ **⇒ 所以【那个状态【可能【本来是为了**那里**】
```

**✅ ⭐⭐⭐ **"那个状态可能本来是为了那里"** —— 一个**合理的推断**。

## 十三、关键结论

1. **⭐⭐⭐ "哈希【把反斜杠折成正斜杠**】，而【那个比较【不折**】"** ⇒ **"两个只在斜杠方向不同的名字共享一个桶，而仍然比较不等"`** —— 一个**引擎级的故意不对称**，而**注释正好解释了它**（与 §465 的注释矛盾**对照**）：**"那个不对称是一个正确性的要求，因为若比较也折就会造出一个假的命中"`**。
2. **⭐⭐⭐ 实测 `2026-09-09`：`120,000` 个桶全部走过，从每个条目自己的名字重算哈希，复现了它被找到的桶，对 `81,128` 个里的 `81,128` 个，零失配**；**剩下 `18,882` 个是 type `27`，它的访问器不是那三个之一，所以被拒绝而不是在一个猜的偏移上读**；**全表最长链 `7`，`mc/mtl_t6_wpn_pda` 一步解析，对比之前的 `200,000` 条目线性扫描 ⇒ `10^5` 倍加速**。**独立推导：`81,128 + 18,882 = 100,010` ⇒ `19,990` 个桶是空的，平均链长 `0.83`**。
3. **⭐⭐⭐ `DB_FindXAssetHeader` 是【错误的门**】：**它取一个临界区、等一个流式事件、按 `GetCurrentThreadId` 对三个不同的线程 id 分支，而在一个活的客户端上它确实那样做了**；而**表遍历"没有临界区、没有分配、没有一个会搞错的调用约定、没有会阻塞的东西"`** ⇒ **"它的行为取决于谁在调"`**。
4. **⭐⭐⭐ "一个缺失的材质必须读作缺失而不是默认的，否则每一个表面会静默地画错"`**（`createDefault = false`），而 **"表遍历天然没有那个陷阱"`**（**它不能造默认**）—— 第二次"一个默认值是陷阱"（与 §467 同族）。
5. **⭐⭐⭐ "一个不铺满 blob 的走没有理解它"`**（`p != storage.size()` ⇒ 拒绝 ⇒ `"arrays tile N of M bytes"`）—— **"字面上是解码器对自己持有的同一个标准"`** ⇒ **"`p == size` 是唯一的『完全理解』证明"`**；而 `claim` 的三态（`0` ⇒ 必须空 / `0xFFFFFFFF` ⇒ 内联 / 其它 ⇒ 拒绝）**是一个双向蕴含**。
6. **⭐⭐⭐ "`0xFFFFFFFF`（`InlineFollows`）与 `0xFFFFFFFE`（`StreamedModelSurfs`）是两个相邻的哨兵，两个不同的含义"`** —— 两个负数区分两种"不是指针"。
7. **⭐⭐⭐ "脚本字符串放在最后，所以一个解析器失败不能留下一个半重定位的资产，而那个资产仍然看起来结构上健全"`** ⇒ **"顺序可以变成一个安全性属性"`**。
8. **⭐⭐⭐ "一个已发布的骨架数说谎的 XModel 是一个崩溃而不是一个视觉故障"`**（六条 `expect`：`parentList` = `nonRoot` / `quats` = `8×nonRoot` / `trans` = `12×nonRoot` / `partClassification` = `bones` / `baseMat` = `32×bones`）—— **"`nonRoot` 与 `bones` 是两个不同的分母"`**（`nonRoot = bones - roots`，而 `roots > bones` ⇒ 拒绝 ⇒ 不下溢）。
9. **⭐⭐⭐ "一次布局，所以一个指针被取走之后什么也不能动"`** ⇒ **`std::vector<std::unique_ptr<...>> published` 的理由：`vector` 增长只会移动那个 `unique_ptr`，不会移动那个资产** ⇒ **"`unique_ptr` 正是那个保证"`**。
10. **⭐⭐⭐ `MaterialTextureDef.nameHash` 的"它不能被重算，但它不必被重算"`**：**哈希覆盖那个 sampler 名字，所以同一个槽在每一个有它的材质里携带同一个哈希**（实测 `2,849` 个材质：`colorMap 0xA0AB1041` semantic `2` `2920` 次 / `normalMap 0x59D30D0F` semantic `5` `2575` / `specularMap 0x34ECCCB3` semantic `8` `2251` / `detailMap 0xEB529B4D` semantic `5` `92`）⇒ **"`nameHash` 是一个键而不是一个值"`**；**独立发现：`semantic` 不能区分 `normalMap`（`5`）与 `detailMap`（`5`）⇒ 所以必须用 `nameHash`**。
11. **⭐⭐⭐ "按 nameHash 匹配而不是按位置：把一个图像写进错的槽会画出法线贴图当作漫反射，而不是失败"`** —— 第三次"一个错的『成功』比一个失败坏"（与 §467 的两例同族）；而 **"按位置匹配是这条路径整个存在的理由要避免的那个错误"`**。
12. **⭐⭐⭐ "每一个枚举值都从一个 port 读出来，而那个 port 从一个已发布的武器解码，而不是推断"`**；**"没有见证的值故意缺席：一个未映射的字符串被拒绝而不是取默认，因为一个错的 `weaponClass` 是一个玩法变更，而那个会看起来像一个移植的 bug 好几周"`** ⇒ **"拒绝永远比默认好"`** —— 第四次"宽容是掩盖"。覆盖缺口：`WeaponClasses` 只有 `0`/`1`/`3`/`5`（**`2` 与 `4` 缺席**），`rifle`≡`assault`≡`0`，`bullet_small`≡`bullet_large`≡`0`。
13. **⭐⭐⭐ `HitLocationKeys` 的"两套都同意 index 0 是 `none` 而 1..5 是头与躯干组；在 index 5 之后那个顺序【没有见证】，所以剩下的条目保持 Standard 的值而 CoD4 的 `locGun` 不被映射"`** —— 第二次"没有见证 ⇒ 缺席"；`StandardHitLocations` 有 **`21`** 个初值（⇒ `HitLocationCount = 21`），其中 `index 17`/`18` 是 `0.0`。
14. **⭐⭐ `milliseconds` 的 `+0.5` 四舍五入 + `fireTimeMilliseconds <= 0` ⇒ 拒绝** ⇒ **"`0.0004` 秒会四舍五入到 0 ⇒ 拒绝"`**（第二次"一个零是危险的"）；而 `SpreadKeys` 的六元组 `{standMin, duckedMin, proneMin, max, duckedMax, proneMax}` 被 **Uzi 的 `{2.0, 1.75, 1.5, 5.0, 4.5, 4.0}` 与 PPSh 的 CoD4 六键"恰好那六个数以那个顺序"** 固定 ⇒ **"那正是固定那个映射并说明那些单位已经一致的东西"`**。
15. **⭐⭐⭐ "那个索引是【每进程】的，所以同一台机器上的两个客户端给同一个骨骼不同的索引，而那正是为什么一个已发布的资产不能携带它们"`** ⇒ **"一个运行时的重定位是必须的"`**；表布局 `+0 u16 refcount / +2 u8 kind / +3 u8 length（含 NUL）/ +4 名字内联`，`stride = 20` ⇒ **`20 − 4 − 1 = 15`** 与 `if (name.size() > 15) return 0;` **精确闭合**。
16. **⭐⭐⭐ "PPSh 动画绑定的 67 个骨骼名里的 66 个已经是 OLfinal 脚本字符串，而那不是的一个是那个枪模型自己的"`** —— 第二次"一个分数的完整性"（与 §467 的 `61/69` 同族）。
17. **⭐⭐ "`XAssetMaxChainSteps = 4096` 只须阻止一个损坏的 `next` 空转，它不是一个表被期望接近的大小"`**（实测最长链 `7` ⇒ `585` 倍余量）—— **"不是一个测量的结果，是一个防御的选择"`**。
18. **⚠ 两个可报告的缺陷**：①**`SvForgeXAnimStatus::WrongThread` 全文件【没有生产者】**（只在 `SV_ForgeXAnimStatusName` 的 `case` 里出现）—— 而 `DB_FindXAssetHeader` 的"按线程 id 分支"暗示它本来应该有；②**`SV_ForgeXAnimStatus::UnresolvedString` 同样没有被 `SV_RelocateForgeXAnim` 返回**（它返回 `nullopt` + `error` 字符串，状态由 `SV_PublishForgeBundleXAnims` 统一写成 `relocate: ...`，不是 `UnresolvedString`）。

## 十四、`sv_forge_publish_mp` 全文件总览

**`sv_forge_publish_mp.cpp`：`1,459` 行。`sv_forge_publish_mp.hpp`：`564` 行。**

**四种资产类型**：
```text
 2  XAnimParts   88 字节头   重定位（数组必须恰好铺满）
 4  XModel      360 字节头   构建（六条长度必须一致）
 5  Material    104 字节头   克隆（只替换名字与纹理表）
28  WeaponDef   —— 由 sv_alpha_weapon_port_mp 克隆，本文件只做键映射
10  GfxImage    —— 只解析不构建
```

**`29` 个函数**（.cpp）：
```text
 55 readU16          61 readU32          68 writeU16         73 writePointer
 81 SV_ForgeXAnimStatusName
 96 SV_RelocateForgeXAnim
274 SV_ForgeStringResolver          305 SV_ForgeStringTableResolver
343 SV_PublishForgeXAnim            387 SV_PublishForgeBundleXAnims
493 alignUp          497 writeU32
504 SV_BuildForgeXModel
682 SV_ForgeXAssetHash              700 SV_ForgeXAssetNameOffsetForThunk
711 SV_ForgeXAssetNamesEqual        736 SV_ForgeXAssetTableFor
751 SV_ForgeFindXAsset
806 SV_ForgeMaterialTableResolver   817 SV_ForgeImageTableResolver
828 SV_ForgeMaterialResolver        855 SV_PublishForgeXModel
939 lowercase        948 mapEnum
965 SV_ForgeWeaponTuning
1166 SV_ForgeSamplerHash            1176 SV_BuildForgeMaterial
1291 SV_ParseForgeCod4Material      1395 SV_ForgeImageResolver
1421 SV_PublishForgeMaterial
```

**一个 `static_assert`**：
```cpp
static_assert(sizeof(void *) == 4, "the forge publication path targets the 32-bit client");
```
—— **"在 64 位构建上那些写会静默截断而引擎会跟一个半地址，所以让构建失败"**（§468 五的"一个数是一个行为"同族）。

**十六个 RVA**（全部相对 `0x400000`）：
```text
DBLinkXAssetEntryRva        0x09DA10  → 0x0049DA10
ScriptStringGetRva          0x34BD10  → 0x0074BD10
ScriptStringTablePtrRva     0x749C524 → 0x0789C524
DBFindXAssetHeaderRva       0x09CF30  → 0x0049CF30   （更正自 0x09D3B0）
XAssetEntriesRva            0x1F9B120 → 0x0239B120
XAssetHashHeadsRva          0x1A2D338 → 0x01E2D338
XAssetNameThunksRva         0x0A5C8C0 → 0x00E5C8C0
XAssetNameThunkAt0Rva       0x83390   → 0x00483390
XAssetNameThunkAt16Rva      0x833A0   → 0x004833A0
XAssetNameThunkAt48Rva      0x833C0   → 0x004833C0
```

**八条测量锚点**：
```text
81,128 / 81,128  哈希复算零失配（2026-09-09 活客户端）
    18,882       type 27（无访问器 ⇒ 拒）
       7         全表最长链
 2,849           已发布材质（nameHash 四例）
   2920 / 2575 / 2251 / 92  四个 sampler 的使用次数
      67 / 66    PPSh 骨骼名的已 intern 比例
       21        StandardHitLocations 的条目
      88        XAnimParts 头
     360        XModel 头
     104        Material 头
      64        CoD4 材质头
      20        script-string 条目步长
```

## 十五、未闭合点

- `0x09D3B0` 的更正病历（`ClientAnimtreeHook.cpp` 的 `FindAssetRva`）——一个**已修复的真实 bug**（"调用它会运行任意代码"）。
- `models/%s` 的**另外两个通道**。
- `StandardHitLocations` 的 `index 17`/`18` 为什么是 `0.0`。
- `HitLocationCount` 的确切值（我推 `21`）。
- `SvAlphaWeaponTuning` 的字段布局（在 `sv_alpha_weapon_port_mp.hpp` 里）。
- 下一个文件：`sv_script_lua_mp.cpp`（`56,426` 字节）。
