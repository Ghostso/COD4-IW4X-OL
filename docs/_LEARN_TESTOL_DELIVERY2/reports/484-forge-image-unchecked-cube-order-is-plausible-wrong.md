# 484 · **"这个路径里没有任何东西需要一个 cubemap，而一个从未被检查过的 cube 面顺序正是那种会产生一个看似合理的错误答案的东西"** —— `sv_forge_image_mp.cpp` 的 `sub_BE8690` 逐分支、v6 vs v8/v9 的存取序、以及"cursor 必须落在载荷最后一个字节上"

## 一、范围

本报告学习 `sv_forge_image_mp.cpp`（**`544` 行**）全文件：`SV_ForgeImageLevelBytes` 的 `sub_BE8690` 逐分支复现、`iwiLevelBytes` 的七种格式、`SV_ParseForgeIwi` 的 v6/v8/v9 两个布局、mip 计数的**唯一性求解**、`SV_BuildForgeGfxImage` 的层级反转、以及 `SV_VerifyForgeGfxImage` 的十项自检。

## 二、**"一个从未被检查过的 cube 面顺序正是那种会产生一个看似合理的错误答案的东西"**（本组最重要的一段）

### 2.1 那段

```cpp
if (source.cubemap)
{
    // Nothing in this port needs one, and a cube face order that has never
    // been checked is exactly the kind of thing that produces a plausible
    // wrong answer.
    error = "cubemaps are not supported by this path";
    return std::nullopt;
}
```

### 2.2 二十四层

```text
1. **这个移植里【没有任何东西【需要**一个 cubemap**】
2. ⇒ **⇒ 而【一个【从未被检查过的** cube 面顺序**】
3. ⇒ **⇒ 正是【那种【会产生【一个**看似合理的**错误答案**】的东西**
4. ⇒ **⇒ 所以【拒绝**】
```

### 2.3 ⭐⭐⭐ **"一个从未被检查过的顺序正是那种会产生一个看似合理的错误答案的东西"**

**✅ 这是本报告里**最重要的一条"**一个**未验证的顺序【比【一个**明确的失败**更危险**"**。**

**✅ 与 §467 的"一个回落比一个失败更危险"**、§468 的"没有见证的值故意缺席"**——**完全同族** ✓

**⇒ 三层**：
```text
明确的失败 ⇒ **`error = "cubemaps are not supported"`** ⇒ **⇒ 可见**
错的成功 ⇒ **六个面【按【一个错的顺序** ⇒ **⇒ 一个**看似合理的**贴图**
⇒ **⇒ 所以【后者【更坏**】
```

**✅ ⭐⭐⭐ **"错的成功比失败更坏"** —— 第四次"一个**看似合理的**错误**"（与 §467/§468/§471 同族）。

**⚠ 而"`flags & 0x10000` ⇒ cubemap"**⇒ **一个**位的**判据**。**

**⇒ 十层**：
```text
v8/v9 ⇒ **`flags` 是 `u32` 在 `+4`**】⇒ **⇒ 而 `0x10000` 【是【那个** cubemap 位**】
v6 ⇒ **`cubemap = false` 硬编码**】（**因为 v6 的 flags 在 `+5` 而【不是** `u32`**）
⇒ **⇒ 所以【两个版本【各自【一个判据**】
```

**✅ ⭐⭐⭐ **"两个版本各自一个判据"**。

## 三、**`sub_BE8690` 的逐分支**（本组第二重要）

### 3.1 那段

```cpp
std::uint32_t SV_ForgeImageLevelBytes(f, w, h, d) noexcept
{
    // sub_BE8690 out.exe 0xBE8690, branch for branch.
    if (f > 80)
    {
        if (f > FourCcDxt1)
        {
            if (f == FourCcDxt3 || f == FourCcDxt5)
                return 16 * d * ((h + 3) >> 2) * ((w + 3) >> 2);
        }
        else
        {
            if (f == FourCcDxt1)
                return 8 * d * ((h + 3) >> 2) * ((w + 3) >> 2);
            if (f == 112 || f == 114)
                return 4 * d * h * w;
        }
        return 0;
    }
    if (f == 80)
        return 2 * d * h * w;
    switch (f)
    {
    case 21: case 22: case 75: return 4 * d * h * w;
    case 28: case 50: return d * h * w;
    case 51: return 2 * d * h * w;
    default: return 0;
    }
}
```

### 3.2 二十四层

```text
1. **`f > 80` ⇒ 一个【四字码的**外层**】
2. ⇒ **⇒ `f > 0x31545844`（`"DXT1"`**）⇒ **⇒ `DXT3`/`DXT5` ⇒ `16` 字节/块**】
3. ⇒ **⇒ 而 `f <= "DXT1"` ⇒ `== "DXT1"` ⇒ `8` 字节/块**】
4. ⇒ **⇒ ⇒ 或 `112`/`114` ⇒ `4` 字节/像素**】
5. ⇒ **⇒ 其它 ⇒ `0`**】
6. ⇒ **而 `f == 80` ⇒ `2` 字节/像素**】
7. ⇒ **⇒ 而 `21`/`22`/`75` ⇒ `4` / `28`/`50` ⇒ `1` / `51` ⇒ `2`**
```

### 3.3 ⭐⭐⭐ **"逐分支"意味着一个二分的比较树，而不是一个表**

**✅ 与 §476 的"`SV_CompareTraceResults` 的十二个比较项"**——**不同**（那是一个**顺序**，这是一个**树**）但**同族**（**第五次"一个**分支结构【是【一个**行为**"**）。

**⇒ 关键观察**：
```text
`f > 80` ⇒ **一个数字比较**（**而 `80` 【不是【一个四字码**）
⇒ **⇒ 所以【那个比较【混用了【两个域**】（**格式号【与**四字码**）
⇒ **⇒ 而【那【正是【引擎自己的形状**】（**注释说"branch for branch"**）
```

**✅ ⭐⭐⭐ **"那个比较混用了两个域，而那正是引擎自己的形状"** —— 一个**极重要的观察**。

**⚠ 而独立验证那几个四字码**：
```text
`FourCcDxt1 = 0x31545844` ⇒ 小端 ⇒ `"DXT1"` ✓
`FourCcDxt3 = 0x33545844` ⇒ `"DXT3"` ✓
`FourCcDxt5 = 0x35545844` ⇒ `"DXT5"` ✓
⇒ **⇒ 而 `0x31545844 = 826,410,308 > 80`** ✓
⇒ **⇒ 所以【那三个【都会【走【那个 `f > 80` 分支** ✓
```

**✅ ⭐⭐⭐ **"那三个都会走那个 f > 80 分支"**。

**⚠ 而"`f > FourCcDxt1`" 的**含义**】**。**

**⇒ 十层**：
```text
`DXT1 = 0x31545844`
`DXT3 = 0x33545844` ⇒ **`> DXT1`** ✓
`DXT5 = 0x35545844` ⇒ **`> DXT1`** ✓
⇒ **⇒ 所以【那个 `>` 比较【恰好【把【`DXT3`/`DXT5` 【分到【一支**】而【`DXT1` 【到【另一支**】
```

**✅ ⭐⭐⭐ **"那个 > 比较恰好把 DXT3/DXT5 分到一支而 DXT1 到另一支"** —— 一个**巧妙的**编码**。

**✅ 与 §476 的"`& 0x1F` 与 `< 31`"**——**同族**（**第六次"一个**比较【的边界【恰好**对齐**"**）。

### 3.4 而**`(h + 3) >> 2` 的块数**

**⇒ 独立验证**：
```text
`(h + 3) >> 2` ⇒ **`ceil(h / 4)`**
⇒ **⇒ 而对 `h = 4` ⇒ `(4+3)>>2 = 7>>2 = 1`** ✓
     `h = 5` ⇒ `8>>2 = 2` ✓
     `h = 8` ⇒ `11>>2 = 2` ✓
⇒ **⇒ 所以【那是一个【整数**的向上取整**
```

**✅ ⭐⭐⭐ **"那是一个整数的向上取整"** —— 而**`iwiLevelBytes` 里【用的是 `((w + 3) / 4) * ((h + 3) / 4)`**】**。**

**⇒ 三层**：
```text
`SV_ForgeImageLevelBytes` ⇒ **`(h + 3) >> 2`**（**移位**）
`iwiLevelBytes` ⇒ **`((h + 3) / 4)`**（**除法**）
⇒ **⇒ 两种写法【等价**】（**因为【那个 `+3` 保证【非负**）⇒ **⇒ 而【注释说【两者【在【每个接受的格式上【一致**】
```

**✅ ⭐⭐⭐ **"两种写法等价，而注释说两者在每个接受的格式上一致"** —— 一个**双实现的验证**。

**✅ 与 §482 的"两次确认，由共享零代码的解码器"**——**同族**（**第三次"一个**双实现**"**）。

## 四、**v6 vs v8/v9 的两个 IWi 布局**（本组第三重要）

### 4.1 那段

```cpp
if (src.version == 6)
{
    // IW3: format +4, flags +5, dims +6/+8/+10, sizes +12. Largest first.
    src.headerSize = 28;
    src.iwiFormat = file[4];
    src.cubemap = false;
    src.width = readU16(file, 6);
    src.height = readU16(file, 8);
    src.depth = readU16(file, 10);
    src.storedSmallestFirst = false;
}
else if (src.version == 8 || src.version == 9)
{
    // IW5 / CODOL: flags u32 +4, format +8, dims +10/+12/+14. Smallest first.
    src.headerSize = 32;
    const std::uint32_t flags = readU32(file, 4);
    src.iwiFormat = file[8];
    src.cubemap = (flags & 0x10000u) != 0;
    src.width = readU16(file, 10);
    src.height = readU16(file, 12);
    src.depth = readU16(file, 14);
    src.storedSmallestFirst = true;
}
```

### 4.2 二十四层

```text
1. **v6（IW3）⇒ 头 `28` 字节**】⇒ **⇒ 而【format 在 `+4`（一个字节**）**
2. ⇒ **⇒ 而 flags 在 `+5`**】⇒ **⇒ 但【这里【**不用它**】（`cubemap = false` 硬编码**）**
3. ⇒ **⇒ 而 dims 在 `+6`/`+8`/`+10`**】⇒ **⇒ 而 sizes 在 `+12`**】
4. ⇒ **⇒ 而【最大**在**前**】
5. ⇒ **v8/v9（IW5/CODOL）⇒ 头 `32` 字节**】⇒ **⇒ flags 是 `u32` 在 `+4`**】
6. ⇒ **⇒ format 在 `+8`**】⇒ **⇒ dims 在 `+10`/`+12`/`+14`**】
7. ⇒ **⇒ 而【最小**在**前**】
```

### 4.3 ⭐⭐⭐ **"v6 最大在前，v8/v9 最小在前"**

**✅ 与 §473 的"`ImageNames` vs `ImageSourceNames` 的逐项对应"**——**不同**（那是一个**名字**，这是一个**顺序**）但**同族**（**第六次"一个**顺序【是【一个**语义**"**）。

**⇒ 三层**：
```text
v6 ⇒ **largest first** ⇒ **`memcpy(to, from, payloadBytes)` 直拷** ✓
v8/v9 ⇒ **smallest first** ⇒ **必须【逐级【反向**重排**
⇒ **⇒ 所以【那个 `storedSmallestFirst` 【支配【两条**代码路径**】
```

**✅ ⭐⭐⭐ **"那个 storedSmallestFirst 支配两条代码路径"**。

**⚠ 而那个**反转**的算法**】**。**

```cpp
std::size_t readAt = source.payloadBytes;
std::size_t writeAt = 0;
for (std::uint32_t i = 0; i < source.storedLevels; ++i)
{
    const std::uint32_t bytes = iwiLevelBytes(src.iwiFormat, w >> i, h >> i);
    if (bytes > readAt) { error = "reversing the mip chain ran off the start"; return nullopt; }
    readAt -= bytes;
    std::memcpy(to + writeAt, from + readAt, bytes);
    writeAt += bytes;
}
if (readAt != 0 || writeAt != source.payloadBytes)
{
    error = "reversing the mip chain did not consume the payload exactly";
    return std::nullopt;
}
```

**⇒ 十六层**：
```text
1. **`i = 0` ⇒ 【那个**最小的**层级**】（**因为【文件里【最小**在前**）**
2. ⇒ **⇒ 而【它【在文件里的**末尾**】（**从后往前读**）
3. ⇒ **⇒ 所以【`readAt` 【从 `payloadBytes` 【递减**】
4. ⇒ **⇒ 而 `writeAt` 【从 `0` 【递增**】
5. ⇒ **⇒ 所以【那【写入【largest** first 的顺序**】
6. ⇒ **⇒ 而【两个检查**：`readAt == 0` 与 `writeAt == payloadBytes`**】
```

### 4.4 ⭐⭐⭐ **"那是一个恰好用尽的检查（两端）"**

**✅ 与 §468 的"`p == storage.size()`"**、§482 的"`consumed 22940 of 22940 bytes EXACT`"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **一端：`p == size`**
§482  **一端：`consumed == total`**
§484  **两端：`readAt == 0` **且** `writeAt == payloadBytes`**
⇒ **⇒ 三次"一个**恰好用尽【是【一个**可判定的正确性**"**
```

**✅ ⭐⭐⭐ **"一个恰好用尽是唯一的可判定的正确性"三例表**。

**⚠ 而"`bytes > readAt` ⇒ 拒绝"**⇒ **一个**下溢**的守卫**。

**⇒ 十层**：
```text
`readAt -= bytes` ⇒ **若【`bytes > readAt`**】⇒ **⇒ 一个 `size_t` 【下溢**】
⇒ **⇒ 所以【那个检查【防止【一个**巨大的** `readAt`**】
```

**✅ ⭐⭐⭐ **"那个检查防止一个巨大的 readAt（size_t 下溢）"** —— 与 §469 的"`allocator.usedBytes -= min(...)`"**同族**（**第四次"一个**无符号减法【的守卫**"**）。

## 五、**mip 计数的唯一性求解**（本组第四重要）

### 5.1 那段

```cpp
// The stored level count is a property of the FILE, not of the dimensions.
// Take the count whose running total equals the payload exactly; prefix
// sums strictly increase, so at most one can match.
std::uint64_t total = 0;
for (std::uint32_t i = 0; i < src.fullLevels; ++i)
{
    const std::uint32_t bytes = iwiLevelBytes(...);
    if (bytes == 0) { error = "cannot size IWi format ..."; return nullopt; }
    total += static_cast<std::uint64_t>(bytes) * static_cast<std::uint64_t>(faces);
    if (total == src.payloadBytes) { src.storedLevels = i + 1; break; }
    if (total > src.payloadBytes) break;
}
if (src.storedLevels == 0)
{
    error = "no mip count from 1.." + ... + " fills the payload of " + ... + " bytes";
    return std::nullopt;
}
```

### 5.2 二十四层

```text
1. **那个被存下的层级数【是【那个**文件的一个属性**】⇒ 不是【维度的】
2. ⇒ **⇒ 所以【取【那个【运行总和【恰好等于【那个载荷**的计数**】
3. ⇒ **⇒ 而【前缀和【严格递增**】⇒ **⇒ 所以【至多一个【能匹配**】
4. ⇒ **⇒ 而【若【没有一个**⇒ **⇒ 拒绝【并【报出一个【精确的**范围**】
```

### 5.3 ⭐⭐⭐ **"前缀和严格递增，所以至多一个能匹配"**

**✅ 这是本报告里**最漂亮的一条**数学论证**。**

**✅ 与 §482 的"'整体不同'不蕴含'每一部分不同'"**——**同族**（**第五次"一个**推理**的正确性**"**）。

**⇒ 三层**：
```text
若【前缀和【不严格递增**】⇒ **⇒ 多个**计数【可以匹配**
而【`bytes >= 1` （**每个层级【至少一个块**）⇒ **⇒ 严格递增** ✓
⇒ **⇒ 所以【那个"至多一个"【成立**】
```

**✅ ⭐⭐⭐ **"每个层级至少一个块 ⇒ 严格递增 ⇒ 至多一个"** —— 一个**完整的论证**。

**⚠ 而"`fullLevels` 的上界"**⇒ **`fullLevelCount(w,h,d)`**。

**⇒ 独立验证 `fullLevelCount`**：
```cpp
std::uint32_t n = 1;
for (std::uint32_t i = 1; i < w || i < h || i < d; i *= 2) ++n;
return n;
```
```text
`w = h = 256`，`d = 1` ⇒ **`i = 1,2,4,...,128`（8 次）⇒ `n = 9`** ✓
（**`256,128,64,32,16,8,4,2,1` ⇒ 9 级**）
⇒ **⇒ 所以【那个公式【正确**】
```

**✅ ⭐⭐⭐ **"`256×256` ⇒ 9 级"** —— 一个**精确的验证**。

**✅ 与 §471 的"`0.135 / 0.125 = 1.08`"**——**同族**（**第七次"一个**算术的验证**"**）。

**⚠ 而"`total += bytes * faces`"**⇒ **一个**六倍的**乘数（cubemap）**。**

**⇒ 三层**：
```text
`faces = 1` ⇒ **普通**
`faces = 6` ⇒ **cubemap**
⇒ **⇒ 而【这个路径【拒绝 cubemap**】（**§484 二**）⇒ **⇒ 所以【`faces` 【恒为 `1`**】
```

**✅ ⭐⭐ **"`faces` 恒为 1"**。

## 六、**`SV_VerifyForgeGfxImage` 的十项自检**（本组第五重要）

### 6.1 十项

```text
① storage.size() >= OlfinalGfxImageSize
② loadDefOffset + OlfinalGfxImageLoadDefSize <= storage.size()
③ payloadOffset + payloadBytes == storage.size()          ← 恰好用尽
④ payloadOffset == loadDefOffset + OlfinalGfxImageLoadDefSize  ← 紧接
⑤ declared（loadDef+12）== payloadBytes
⑥ depth != 0
⑦ 逐级走：cursor 不越界
⑧ cursor == payloadBytes                                  ← 恰好用尽
⑨ levels（引擎会走的）== image.levels（文件持有的）
⑩ 名字是 storage 里一个 NUL 终止的副本
```

### 6.2 二十四层

```text
1. **十项，而【三项【是【"恰好**用尽**】（③ ⑧ 与【一个隐含的**⑩**）**
2. ⇒ **⇒ 而【两项【是【"紧接**/边界**】（② ④**）**
3. ⇒ **⇒ 一项【是【"一致**"】（⑤）**
4. ⇒ **⇒ 一项【是【"非零**"】（⑥）**
5. ⇒ **⇒ 两项【是【"引擎会走的 == 文件持有的"**（⑦ ⑨**）**
6. ⇒ **⇒ 一项【是【"名字是一个**真实的**副本**"（⑩**）**
```

### 6.3 ⭐⭐⭐ **"⑨ levels（引擎会走的）== image.levels（文件持有的）"**

**✅ 与 §484 五 的"那个被存下的层级数是一个文件的属性"**——**完全闭合** ✓

**⇒ 三层**：
```text
`SV_ForgeImageLevelCount(flags, w, h, d)` ⇒ **引擎【会走的**
`image.levels` ⇒ **文件【持有的**
⇒ **⇒ 而【§484 五 的 `flags` 只有两个形状**：`SingleMip`（`1`）或【全链**】
```

**✅ ⭐⭐⭐ **"flags 只有两个形状"** —— 而**那个 `error` 消息【说**"**引擎只能走一个或全部**"**（`"the engine can only walk one or all"`）**。

**⚠ 而"中间层级数 ⇒ 拒绝"**⇒ **一个**极清晰的**约束**。**

**⇒ 十层**：
```text
若【文件存了【`3` 级【而【全链是 `9`**】⇒ **⇒ 拒绝**】
⇒ **⇒ 因为【`sub_BE8C30` 【只能【回答**"一个"或"全链"**】
⇒ **⇒ 所以【那是一个**引擎的**限制，不是【这个移植的**】
```

**✅ ⭐⭐⭐ **"那是一个引擎的限制，不是这个移植的"** —— 一个**极精确的归因**。

**✅ 与 §468 的"那个发射器拒绝产生两者之一，所以拒绝去搬它"**——**同族**（**第四次"拒绝【一个【引擎**做不到的**"**）。

### 6.4 而**`+38 "no pixels"` 与 `+40` 的双位判据**（绕过自检的第 11 项）

### 6.5 那段

```cpp
// +38 "no pixels" and +40 the byte sub_4999E0 reads. sub_4999E0 returns
// true - and sub_BE7470 then does nothing at all - when (b & 1) is set and
// (b & 2) is not, so zero is the value that lets the upload proceed.
image.storage[OlfinalGfxImageNoPixels] = std::byte{ 0 };
image.storage[OlfinalGfxImageStateByte] = std::byte{ 0 };
```

**⇒ 二十四层**：
```text
1. **`+38` ⇒ "no pixels"**】
2. ⇒ **⇒ 而 `+40` ⇒ 那个 `sub_4999E0` 读的**字节**
3. ⇒ **⇒ 而 `sub_4999E0` 【返回 `true`**】⇒ **⇒ 而 `sub_BE7470` 【然后【什么也不做**】
4. ⇒ **⇒ 当 `(b & 1)` 被设【而 `(b & 2)` 【没有**被设**
5. ⇒ **⇒ 所以【零【是【那个【让上传**继续**的值**】
```

### 6.6 ⭐⭐⭐ **"当 (b & 1) 被设而 (b & 2) 没有被设时，sub_4999E0 返回 true，而 sub_BE7470 然后什么也不做"**

**✅ 与 §475 的"零 ⇒ 不扩张"**——**同族**（**第七次"一个**零【是【一个**正确**的值**）**。

**⇒ 三层**：
```text
`b = 0` ⇒ **`(0 & 1) = 0` ⇒ 那个条件【为假**】⇒ **⇒ 上传**继续**
`b = 1` ⇒ **`(1 & 1) = 1` 且 `(1 & 2) = 0` ⇒ 【为真**】⇒ **⇒ 上传**被跳过**
`b = 3` ⇒ **两个位【都设**】⇒ **⇒ 【为假**】⇒ **⇒ 上传**继续**
⇒ **⇒ 所以【`b ∈ {0, 3, ...}` 【让【上传继续**】而【`b = 1` 【阻止**它**
```

**✅ ⭐⭐⭐ **"`b ∈ {0, 3, …}` 让上传继续，而 `b = 1` 阻止它"** —— 一个**精确的位逻辑**。

**✅ 与 §470 的"`0x03` = `ServerCommandGameState`"**——**不同**，但与 §484 三 的"`(h + 3) >> 2`"**同族**（**第七次"一个**位运算【的**精确语义**"**）。

## 七、**`SV_ForgeIwiFormatToD3D` 的"2 X8R8G8B8 故意缺席"**

### 7.1 那段

```cpp
// 2 X8R8G8B8 is deliberately absent: the file packs three bytes per pixel
// and D3DFMT_X8R8G8B8 is four, so copying it straight through would shear
// the image. Expanding it is possible and is simply not done here.
// 6..10 are the stream-coded variants, which are not plain pixels at all.
default: return 0;
```

### 7.2 二十四层

```text
1. **`2`（`X8R8G8B8`）【故意缺席**】
2. ⇒ **⇒ 因为【那个文件【打包【三个**字节/像素**】
3. ⇒ **⇒ 而 `D3DFMT_X8R8G8B8` 【是四个**】
4. ⇒ **⇒ 所以【直接【拷过去【会【剪切**那个图像**】
5. ⇒ **⇒ 而【扩展它是【可能的**】⇒ **⇒ 而【这里【只是**没有做**
6. ⇒ **⇒ 而 `6..10` 【是【流编码的变体**】⇒ **⇒ 它们【根本【不是**纯像素**
```

### 7.3 ⭐⭐⭐ **"文件打包三个字节每像素而 D3D 是四个，所以直接拷过去会剪切那个图像"**

**✅ 与 §473 的"那个 `~` 前缀的名字被截断"**——**不同**（那是**命名**，这是**布局**）但**同族**（**第五次"一个**格式【的**不匹配**"**）。

**⇒ 三层**：
```text
若【直拷**】⇒ **⇒ 一个【每像素**少一个字节**的图像
⇒ **⇒ 而【那个结果【是【一个**斜切**的图像**】⇒ **⇒ 一个**看似合理的**错误
⇒ **⇒ 所以【拒绝【比【一个斜切的图像**好**
```

**✅ ⭐⭐⭐ **"拒绝比一个斜切的图像好"** —— 与 §484 二 的"一个看似合理的错误答案"**完全同族**（**第五次**）。

**⚠ 而"扩展它是可能的而这里只是没有做"**⇒ **一个**极诚实的**范围声明**。**

**⇒ 十层**：
```text
"可能的" ⇒ **一个**技术上的**可行
"没有做" ⇒ **一个**范围**的决定
⇒ **⇒ 所以【那个注释【区分了【"不可能"与【"不做"**】
```

**✅ ⭐⭐⭐ **"那个注释区分了『不可能』与『不做』"** —— 与 §477 的"一个缺表的 MP 手雷"**同族**（**第六次"一个**诚实的范围**"**）。

### 7.4 而格式号的两套编码

```text
IWi 格式号      D3DFORMAT
    1      →     21    A8R8G8B8
    3      →     51    A8L8
    4      →     50    L8
    5      →     28    A8
   11      →  "DXT1"
   12      →  "DXT3"
   13      →  "DXT5"
```

**⇒ 十层**：
```text
`1 → 21` / `3 → 51` / `4 → 50` / `5 → 28` ⇒ **四个数字到数字**
`11/12/13 → DXT1/DXT3/DXT5` ⇒ **三个数字到四字码**
⇒ **⇒ 所以【那个映射【跨越【两个**不同的编码空间**】
```

**✅ ⭐⭐⭐ **"那个映射跨越两个不同的编码空间"** —— 而**`SV_ForgeImageLevelBytes` 【的 `f > 80` 【正是【那个分界**】**。**

**⇒ 三层**：
```text
`f <= 80` ⇒ **D3DFORMAT（21/22/28/50/51/75/80/112/114**）
`f > 80` ⇒ **四字码（DXT1/3/5**）
⇒ **⇒ 所以【那个 `80` 【是一个**域的分界**】
```

**✅ ⭐⭐⭐ **"那个 80 是一个域的分界"** —— 一个**极重要的结构观察**。

**⚠ 而"`112`/`114`"**⇒ **两个**`f > 80` 但【不是**四字码**的值**。**

**⇒ 十层**：
```text
`112` / `114` ⇒ **`4` 字节/像素**】（**在【那个 `f > 80` 分支里**）
⇒ **⇒ 所以【它们【是【两个**例外**】（**数字号【但【大于 `80`**）
```

**✅ ⭐⭐⭐ **"112/114 是两个例外：数字号但大于 80"**。

## 八、关键结论

1. **⭐⭐⭐ "这个路径里没有任何东西需要一个 cubemap，而**一个从未被检查过的 cube 面顺序正是那种会产生一个看似合理的错误答案的东西**"`** ⇒ **"错的成功比失败更坏"`** —— 第四次"一个看似合理的错误"（与 §467/§468/§471 同族）；而 **v8/v9 的 cubemap 位是 `flags & 0x10000`，v6 硬编码 `false`**（因为 v6 的 flags 在 `+5` 而不是一个 `u32`）。
2. **⭐⭐⭐ `SV_ForgeImageLevelBytes` 是 `sub_BE8690` 的逐分支复现**，而**那个比较树混用了两个域**（`f > 80` 是数字比较，而 `0x31545844` 是四字码）—— **"那正是引擎自己的形状"**；**独立验证三个四字码（`0x31545844 = "DXT1"` 等）全部 `> 80` ⇒ 都走那个分支**，而 **`f > FourCcDxt1` 的那个 `>` 恰好把 `DXT3`/`DXT5` 分到一支、`DXT1` 到另一支**。
3. **⭐⭐⭐ `(h + 3) >> 2` 与 `((h + 3) / 4)` 是等价的向上取整**（独立验证 `h=4⇒1`、`h=5⇒2`、`h=8⇒2`）⇒ **"两种写法等价，而注释说两者在每个接受的格式上一致"`** —— 一个**双实现的验证**（与 §482 同族）。
4. **⭐⭐⭐ v6 与 v8/v9 两个 IWi 布局**：v6 头 `28` 字节（`format +4` / dims `+6/+8/+10` / **largest first**）；v8/v9 头 `32` 字节（`flags u32 +4` / `format +8` / dims `+10/+12/+14` / **smallest first**）⇒ **"那个 storedSmallestFirst 支配两条代码路径"`**。
5. **⭐⭐⭐ 那个 mip 反转的算法**：从 `payloadBytes` 递减 `readAt`、从 `0` 递增 `writeAt` ⇒ **写入 largest-first 的顺序**；而**两个检查 `readAt == 0` **且** `writeAt == payloadBytes`** ⇒ **"一个恰好用尽是唯一的可判定的正确性"**（第三次，与 §468/§482 同族）；而 `bytes > readAt ⇒ 拒绝` 是**一个 `size_t` 下溢的守卫**（与 §469 同族）。
6. **⭐⭐⭐ mip 计数的唯一性求解**：**"那个被存下的层级数是一个**文件的属性**，不是维度的；取那个运行总和恰好等于载荷的计数；而**前缀和严格递增，所以至多一个能匹配**"`** ⇒ **独立论证：因为每个层级至少一个块（`bytes >= 1`）⇒ 严格递增 ✓**；而 `fullLevelCount` 独立验证 `256×256 ⇒ 9 级`。
7. **⭐⭐⭐ `SV_VerifyForgeGfxImage` 的十项自检**，其中 **三项是"恰好用尽"（③ ⑧ ⑩）** ⇒ 而 **⑨ `levels（引擎会走的）== image.levels（文件持有的）` 的约束来自引擎**：**"`sub_BE8C30` 只能回答『一个』或『全链』"`** ⇒ **"那是一个引擎的限制，不是这个移植的"`**（与 §468 的"发射器拒绝产生两者之一"同族）。
8. **⭐⭐⭐ `+38 "no pixels"` 与 `+40` 的双位判据**：**"当 `(b & 1)` 被设而 `(b & 2)` 没有被设时，`sub_4999E0` 返回 `true` 而 `sub_BE7470` 然后什么也不做，所以**零是那个让上传继续的值**"`** ⇒ **独立推得 `b ∈ {0, 3, …}` 让上传继续，而 `b = 1` 阻止它**。
9. **⭐⭐⭐ `2 X8R8G8B8` 故意缺席**：**"那个文件打包三个字节每像素而 `D3DFMT_X8R8G8B8` 是四个，所以直接拷过去会**剪切那个图像**；扩展它是可能的而这里只是没有做"`** ⇒ **"拒绝比一个斜切的图像好"** —— 而那个注释**区分了"不可能"与"不做"**（与 §477 同族）。
10. **⭐⭐⭐ 格式号的两套编码**：**`f <= 80` 是 D3DFORMAT（`21`/`22`/`28`/`50`/`51`/`75`/`80`/`112`/`114`），`f > 80` 是四字码（`DXT1`/`DXT3`/`DXT5`）** ⇒ **"那个 `80` 是一个域的分界"**；而 **`112`/`114` 是两个例外**（数字号但 `> 80`，`4` 字节/像素）。

## 九、`sv_forge_image_mp.cpp` 全文件总览

**`544` 行。**

**`3` 个四字码**：`FourCcDxt1 = 0x31545844` / `FourCcDxt3 = 0x33545844` / `FourCcDxt5 = 0x35545844`。

**`7` 个格式**（`iwiLevelBytes`）：`11 DXT1` / `12 DXT3` / `13 DXT5` / `1 A8R8G8B8` / `3 A8L8` / `4 L8` / `5 A8`。

**`6` 个函数**：`readU16` / `readU32` / `writeU16` / `writeU32` / `iwiLevelBytes` / `fullLevelCount` / `SV_ForgeImageLevelBytes` / `SV_ForgeImageLevelCount` / `SV_ForgeImagePayloadBytes` / `SV_ForgeIwiFormatToD3D` / `SV_ParseForgeIwi` / `SV_BuildForgeGfxImage` / `SV_BuildForgeGfxImageFromIwi` / `SV_VerifyForgeGfxImage`。

**`2` 个 IWi 版本布局**：v6（28 头，largest first）/ v8+9（32 头，smallest first，cubemap 位 `0x10000`）。

**`7` 个反汇编锚点**：`sub_BE8690`（字节计算）/ `sub_BE8C30`（层级计数）/ `sub_BE7470`（上传走）/ `sub_4999E0`（"no pixels"判断）/ `+0x38` / `+0x40` / `OlfinalGfxImageFlagSingleMip`。

**`10` 个自检项**（`SV_VerifyForgeGfxImage`）。

## 十、未闭合点

- `OlfinalGfxImageSize` / `OlfinalGfxImageLoadDefSize` / 各字段偏移的确切值（`.hpp`）。
- `OlfinalGfxImageFlagSingleMip` 的值。
- `fullLevelCount` 的 `d` 参与方式（我按 `w/h/d` 三者取并集算）。
- 下一个文件：`sv_zm_revive_mp.cpp`（`18,739` 字节）。
