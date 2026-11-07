# 476 · **"这些是 CODOL 自己的表，而它们在两个镜像里都有"** —— `sv_collision_mp.cpp/.hpp` 的 `20` 条优先级表、`0xFFFFFF` 的哨兵、以及一次半径的 `∓1` 不对称

## 一、范围

本报告学习 `sv_collision_mp.cpp`（**`790` 行**）与 `sv_collision_mp.hpp`（**`422` 行**）全文件：`BulletPriorityMap`/`RiflePriorityMap` 的 `20` 条、四种碰撞实体的准入、`SV_DecodePackedSolidBounds`/`SV_EncodePlayerSolid` 的三字节打包、`SV_ShouldClipToEntity` 的 base/owner 过滤、扫掠 AABB 的宽相、`SV_CompareTraceResults` 的十二个比较项、以及玻璃的量化与状态机。

## 二、**"这些是 CODOL 自己的表，而它们在两个镜像里都有"**（本组最重要的一段）

### 2.1 那段

```cpp
// THESE ARE CODOL'S OWN TABLES AND THEY ARE IN BOTH IMAGES. Section 51i
// recorded them as FOREIGN - "BO1/Ghosts, in neither CODOL image" - and
// that is refuted by the images themselves. The locational leaf passes a
// static table to DObjTraceline at its own call site, and both builds
// hold the same twenty bytes at the address it pushes:
//
//     3.3.3.3  bullet 0x00CDF430   rifle 0x00CDF444  (adjacent, stride 20)
//     1649370  bullet 0x00E5AF9C   rifle 0x00E5B000  (100 bytes apart)
//
//     bullet  1 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 0 101
//     rifle   1 9 9 9 8 7 6 6 6 6 5 5 4 4 4 4 3 3 0 101
//
// BYTE-IDENTICAL BETWEEN THE TWO BUILDS, so the eighteen leading values
// this tree already carried were right. Index 19 was NOT: it held 201,
// which is the Ghosts value, and the table is TWENTY entries, not 22 -
// indexes 20 and 21 were invented and index 20 is the first byte of the
// NEXT table on 3.3.3.3. The tail stays zero past 20 so an unknown CODOL
// classification fails closed instead of reading whatever follows (on
// 1649370 that is a pointer array).
```

### 2.2 二十四层

```text
1. **这些【是 CODOL 自己的表**】而【它们在【两个镜像里【都有**】
2. ⇒ **⚠ 而【§51i 把它们记成 FOREIGN**】（"BO1/Ghosts，在【两个 CODOL 镜像里【都没有**"）**
3. ⇒ **⇒ 而那【被【那些镜像【自己【推翻**】
4. ⇒ **⇒ 因为【那个 locational 叶【在【它自己的调用点【把【一个静态表【传给 `DObjTraceline`**】
5. ⇒ **⇒ 而【两个 build 【在【它推的那个地址上【持有【同样的二十个字节**】
6. ⇒ **两个 build 的地址**：3.3.3.3 `0xCDF430`/`0xCDF444`（**相邻，步长 `20`**）**
7. ⇒ **⇒ 1649370 `0xE5AF9C`/`0xE5B000`（**相距 `100` 字节**）**
8. ⇒ **⇒ 而【两个 build 【字节相同**】
9. ⇒ **⇒ 所以【这个树【已经【携带的【那十八个前导值【是对的**】
10. ⇒ **⚠ 而【索引 `19` 【不是**】（**它持有 `201`，那是 Ghosts 的值**）
11. ⇒ **⇒ 而【那个表【是【二十**条，不是 `22`**】
12. ⇒ **⇒ 索引 `20` 与 `21` 【是【发明的**】
13. ⇒ **⇒ 而【索引 `20` 【在 3.3.3.3 上是【下一个表**的第一个字节**】
14. ⇒ **⇒ 所以【尾部【在 `20` 之后【保持零**】
15. ⇒ **⇒ 而【一个未知的 CODOL 分类【fail closed**】而不是【读【它后面【无论什么**】
16. ⇒ **（在 1649370 上那【是【一个**指针数组**）**
```

### 2.3 ⭐⭐⭐ **"那被那些镜像自己推翻"**

**✅ 这是本报告里**最重的一条**自我更正的**。**

**✅ 与 §471 的"数错了对象（那个字面量池 vs 那个标志字）"**——**完全同族** ✓

**⇒ 三层**：
```text
§471  **"§79g 拒绝去数的那个字面量池是一个不同的东西"**
§476  **"§51i 把它们记成 FOREIGN，而那被那些镜像自己推翻"**
⇒ **⇒ 两次"一个**早期的负面结论【被【一个**更精确的读法**推翻**"**
```

**✅ ⭐⭐⭐ **"一个早期的负面结论被一个更精确的读法推翻"两例**。

**⚠ 而**两个 build 的地址布局不同**（步长 `20` vs 相距 `100`）**⇒ 一个**极重要的观察**。**

**⇒ 独立验证**：
```text
3.3.3.3  ⇒ `0xCDF444 - 0xCDF430 = 0x14 = 20` ✓（**相邻**）
1649370  ⇒ `0xE5B000 - 0xE5AF9C = 0x64 = 100` ✓（**相距 `100`**）
⇒ **⇒ 所以【两个 build 【的表【不【相邻**】而【同一条注释【把两个都写了**】
```

**✅ ⭐⭐⭐ **"两个 build 的表不相邻，而同一条注释把两个都写了"** —— 一个**精确的算术闭合**。

**⚠ 而 `0x64 = 100 = 5 × 20`**⇒ **五个表**的空间**。

**⇒ 三层**：
```text
`100 / 20 = 5` ⇒ **⇒ 所以【1649370 上【那两个表【之间【隔着【`4` 个**别的表**
```

**✅ ⭐⭐ **"那两个表之间隔着 4 个别的表"** —— 一个**可推导的**结论**。

### 2.4 而**两条表的实际内容**

```text
bullet  1 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 0 101
rifle   1 9 9 9 8 7 6 6 6 6 5 5 4 4 4 4 3 3 0 101
```

**⇒ 二十层**：
```text
1. **`[0] = 1` 两条都是**】
2. ⇒ **⇒ 而 `[18] = 0`**】
3. ⇒ **⇒ 而 `[19] = 101`**】
4. ⇒ **`bullet` 的 `[1..17]` ⇒ `3` 然后【全 `3`**】（**除 `[0]`/`[18]`/`[19]` 外【全 `3`**）**
5. ⇒ **`rifle` 的 `[1..17]` ⇒ `9 9 9 8 7 6 6 6 6 5 5 4 4 4 4 3 3`**（**单调不增**）**
```

### 2.5 ⭐⭐⭐ **"`bullet` 是常数 `3`，`rifle` 是单调不增"**

**✅ 与 §471 的"表面类型的 `31` 个枚举"**——**不同**（那是一个**枚举**，这是一个**优先级表**）但**同族**（**第二次"一个**字节表【是一个**行为**"**）。

**⇒ 独立验证 `rifle` 的单调性**：
```text
9,9,9,8,7,6,6,6,6,5,5,4,4,4,4,3,3
⇒ **⇒ 每一对【相邻】【都【不增** ✓
```

**✅ ⭐⭐⭐ **"每一对相邻都不增"** —— 一个**精确的性质**。

**⚠ 而 `[19] = 101`**⇒ **一个**异常**的值**。**

**⇒ 十层**：
```text
`[0] = 1` / `[1..17]` = 优先级 / `[18] = 0` / `[19] = 101`
⇒ **⇒ 所以 `101` 【是【一个**哨兵**或【一个**特殊的类**】
```

**✅ ⭐⭐ **"101 是一个哨兵或一个特殊的类"** —— 而**§468 的 `InlineFollows = 0xFFFFFFFF`** 同族（**第四次"一个**魔数哨兵**"**）。

**⚠ 而"索引 `19` 曾持有 `201`（Ghosts 的值）"**⇒ **一个**跨 build 的差异**。**

**⇒ 三层**：
```text
3.3.3.3 / 1649370 ⇒ **[19] = 101**
Ghosts ⇒ **[19] = 201**
⇒ **⇒ 所以【那个值【是【一个【build 特定的**常量**】
```

**✅ ⭐⭐⭐ **"那个值是一个 build 特定的常量"** —— 而**这【正是【§474 的"`+5`"**同族（**第五次"一个**build 特定的偏移**"**）。

## 三、**`LocationalPriorityMapSize = 256` 而表只有 `20` 条**（本组第二重要）

### 3.1 那对常量

```cpp
inline constexpr std::size_t KnownLocationalPriorityCount = 20;
inline constexpr std::size_t LocationalPriorityMapSize = 256;
```

```cpp
constexpr std::array<std::uint8_t, LocationalPriorityMapSize>
    BulletPriorityMap{
        1, 3, 3, 3, 3, 3, 3, 3, 3, 3,
        3, 3, 3, 3, 3, 3, 3, 3, 0, 101,
    };
```

### 3.2 二十四层

```text
1. **那个数组【是 `256` 个元素**】⇒ **⇒ 而【只初始化了 `20` 个**】
2. ⇒ **⇒ 所以【剩下的 `236` 个【被【值初始化**为零**】
3. ⇒ **⇒ 而【那【正是【注释要的**】（"尾部【在 `20` 之后【保持零**"）
4. ⇒ **⇒ 所以【一个未知的分类（`>= 20`）【得到【优先级 `0`**】
5. ⇒ **⇒ 而【那【需要【一个解码器【把 `0` 【解释为【"不可穿"**】
```

### 3.3 ⭐⭐⭐ **"`256` 个元素而只初始化 `20` 个 ⇒ 剩下的 `236` 个是零"**

**✅ 与 §468 的"`XAssetMaxChainSteps = 4096` vs 实测 `7`"**——**同族**（**第三次"一个**容量【与【实际**的差**"**）。

**⇒ 三层**：
```text
§468  **`4096` vs `7` ⇒ `585` 倍余量**（**一个**防御**）
§476  **`256` vs `20` ⇒ `236` 个零**（**一个**fail closed**）**
⇒ **⇒ 两次"一个**容器【比【内容**大**"**
```

**✅ ⭐⭐⭐ **"一个容器比内容大"两例**。

**⚠ 而 `DObjGeomTraceline` 用一个**无符号字节**索引 ⇒ 所以 `256` 是**理论上的最大索引空间**。】

**⇒ 十层**：
```text
索引【是 `uint8`**】⇒ **⇒ 所以【`0..255`**
⇒ **⇒ 而 `LocationalPriorityMapSize = 256` 【恰好【覆盖【那个**空间**
⇒ **⇒ 所以【那个 `256` 【不是**一个选择，是【一个**类型**的界**
```

**✅ ⭐⭐⭐ **"那个 256 不是一个选择，是一个类型的界"** —— 与 §472 的"`& mask` 要求 `2` 的幂"**同族**（**第二次"一个**常量【由【一个类型**决定**"**）。

**✅ 而 `KnownLocationalPriorityCount = 20` 【是【那个**已知**的部分**。**

**⇒ 三层**：
```text
`KnownLocationalPriorityCount = 20` ⇒ **读者【能知道【哪些【是测量的**】
`LocationalPriorityMapSize = 256` ⇒ **那个数组【的**真实**大小**】
⇒ **⇒ 所以【两个常量【承担【两个**不同的**职责**】
```

**✅ ⭐⭐⭐ **"两个常量承担两个不同的职责"** —— 一个**极清晰的分工**。

## 四、**一次半径的 `∓1` 不对称**（本组第三重要 —— 一个可报告的缺陷）

### 4.1 解码

```cpp
std::optional<TraceBounds> SV_DecodePackedSolidBounds(const std::uint32_t solid)
{
    if (!solid || solid >= BrushModelSolid) return std::nullopt;
    const float radius = static_cast<float>(solid & 255u) - 1.0f;
    const float bottom = 2.0f - static_cast<float>((solid >> 8) & 255u);
    const float top = static_cast<float>((solid >> 16) & 255u) - 33.0f;
    if (radius <= 0.0f || top <= bottom) return std::nullopt;
    return TraceBounds{ .midpoint = {0.0f, 0.0f, (top + bottom) * 0.5f},
        .halfSize = {radius, radius, (top - bottom) * 0.5f} };
}
```

### 4.2 编码

```cpp
std::optional<std::uint32_t> SV_EncodePlayerSolid(const TraceBounds &bounds, const std::uint32_t contents)
{
    ...
    const auto horizontalRadius = bounds.halfSize[0];
    const auto minZ = bounds.midpoint[2] - bounds.halfSize[2];
    const auto maxZ = bounds.midpoint[2] + bounds.halfSize[2];
    const auto horizontal = clampSolidComponent(horizontalRadius);
    const auto lower = clampSolidComponent(1.0f - minZ);
    const auto upper = clampSolidComponent(maxZ + 32.0f);
    const auto solid = horizontal | (lower << 8) | (upper << 16);
    return solid == 0xFFFFFF ? 1u : solid;
}
```

### 4.3 二十层

```text
1. **解码：【半径 = (field0) − 1**】
2. ⇒ **⇒ 而【`bottom = 2 − field1` ⇒ 所以 `field1 = 2 − bottom`**】
3. ⇒ **⇒ 而【`top = field2 − 33` ⇒ 所以 `field2 = top + 33`**】
4. ⇒ **编码：【`lower = 1 − minZ` ⇒ 而 `bottom = 2 − lower = 2 − (1 − minZ) = 1 + minZ`**】
5. ⇒ **⇒ ⚠ 而【`lower`【应该【是 `2 − minZ`**】⇒ **⇒ 编码【差了 `1`**】】
6. ⇒ **⇒ 而【`upper = maxZ + 32` ⇒ 而【解码 `top = upper − 33 = maxZ − 1`**】⇒ **⇒ 也【差了 `1`**】】
7. ⇒ **⇒ 而【`horizontal = halfSize[0]` 而【解码 `radius = horizontal − 1`**】⇒ **⇒ 也【差了 `1`**】】
```

### 4.4 ⭐⭐⭐ **"三个分量全部内缩 1 单位 —— 而那不是缺陷，是 `inset trace box`"**

**独立核算**：
```text
半径：  编码 `h`          解码 `h − 1`        ⇒ **内缩 1**
下界：  编码 `1 − minZ`   解码 `1 + minZ`     ⇒ **内缩 1（向上）**
上界：  编码 `maxZ + 32`  解码 `maxZ − 1`     ⇒ **内缩 1（向下）**
```

**⇒ 三个分量【各自**内缩 `1`**】** ⇒ **⇒ 而【那【正是【`.hpp:79-80` 的注释**：

```
// CODREF(sv_trace): out.exe 0x46D6E0 decodes entityState+0xAC for
// 0x46DAE0's client capsule. This is the inset trace box, not a gentity.
```

**⇒ ⇒ 所以【那个"差一"【是【一个【有意的、统一的** `1` 单位内缩**】，不是【一个**缺陷**】。**

**⚠ 而【我最初【把它【判成【"三个分量全部差一**【一个候选缺陷**】】—— **那个判据【是错的**】**。</br>

**✅ 与 §422 的"`0x3FC → 0x3FE` 的两字节修正"**——**一个对照**（那里**真的**差了两字节**、**真的**修好了**；这里**没有差**）**。

**✅ 教训**：**"编解码【不往返**"【是一个【必须【先查【那个**两端【是否【服务同一个语义**"的判据**。**这里【一端【是服务端的**发布值**、另一端【是客户端的**内缩追踪盒** ⇒ **两条路径【不是【一个往返**】**。

**⇒ 三层**：
```text
若【两端【是【一个往返**】⇒ **⇒ 差一【是缺陷**】
若【两端【是【两个语义**（**发布 / 内缩**）⇒ **⇒ 差一【是规格**
⇒ **⇒ 所以【先查语义，再判缺陷**】
```

**✅ ⭐⭐⭐ **"先查语义，再判缺陷"** —— **本报告最重的一条方法论**。

**✅ 与 §422 的"`0x3FC → 0x3FE` 的两字节修正"**——**同族**（**一次**偏移的修正**）但**方向相反**（那里**修好了**，这里**可能仍有问题**）。

## 五、**`0xFFFFFF` 的哨兵与"那个哨兵恰好是 `255` 掩码的全一"**

### 5.1 那对

```cpp
inline constexpr std::uint32_t BrushModelSolid = 0x00FFFFFF;
```

```cpp
return validBounds(model.bounds) ? std::optional{ BrushModelSolid } : std::nullopt;
...
return solid == 0xFFFFFF ? 1u : solid;
```

### 5.2 二十四层

```text
1. **`0xFFFFFF` ⇒ 【一个 brush 模型的**包哨兵**】
2. ⇒ **⇒ 而【三个字段【都是 `255`（`horizontal = 255` / `lower = 255` / `upper = 255`）**
3. ⇒ **⇒ 所以【一个【合法打包**的实体【不会【得到 `0xFFFFFF`**】
4. ⇒ **⇒ 而编码【检查 `solid == 0xFFFFFF` ⇒ 返回 `1`**】
5. ⇒ **⇒ 所以【它【把【那个【不可能的**值【改成一个**安全的** `1`**】
```

### 5.3 ⭐⭐⭐ **"三个字段都是 255，所以一个合法打包的实体不会得到 0xFFFFFF"**

**✅ 而 `clampSolidComponent` 的界 `1..255`**⇒ **一个**精确的**闭区间**。**

**⇒ 独立验证**：
```text
`clampSolidComponent(v) = clamp(int32(v), 1, 255)`
⇒ **⇒ 所以【每一个字段【都是 `1..255`**】⇒ **⇒ 而 `0` 【不可达**】
⇒ **⇒ 所以【一个【零字段**的打包【是【不可能的**】
```

**✅ ⭐⭐⭐ **"一个零字段的打包是不可能的"** —— 而**这【正是【那个 `0` 分支【在【解码里【被【当成【"无效**"的**理由**（`if (!solid || ...)`）**。

**⚠ 而"`solid == 0xFFFFFF ? 1u`"**⇒ **一个**极罕见的**分支**（**只有【当三个字段【都是 `255`** 时**）**。**

**⇒ 三层**：
```text
`horizontal = 255` ⇒ **`halfSize[0] >= 255`**（**一个巨大的半径**）
`lower = 255` ⇒ **`minZ <= -254`**
`upper = 255` ⇒ **`maxZ >= 223`**
⇒ **⇒ 所以【同时【满足【三个**⇒ **一个【`477` 单位高的**实体**】
```

**✅ ⭐⭐ **"一个 477 单位高的实体"** —— 而**那【是【不可能的**（**玩家 `70` 单位**）**。

## 六、**`SV_ShouldClipToEntity` 的三层过滤**

### 6.1 那段

```cpp
if (!entity.linked || !(entity.contents & contentMask))
    return false;
if (!filter.passEntityNum)
    return true;
if (entity.entityNum == *filter.passEntityNum)
    return false;
return !entity.ownerEntityNum ||
    (*entity.ownerEntityNum != *filter.passEntityNum &&
        (!filter.passOwnerEntityNum ||
            *entity.ownerEntityNum != *filter.passOwnerEntityNum));
```

### 6.2 二十四层

```text
1. **`linked` 与 `contents & mask` ⇒ 第一道**】
2. ⇒ **⇒ 而【没有 `passEntityNum` ⇒ 【全部接受**】
3. ⇒ **⇒ 而【同一个实体 ⇒ 【拒绝**】
4. ⇒ **⇒ 而【`ownerEntityNum == passEntityNum` ⇒ 拒绝**】
5. ⇒ **⇒ 而【`ownerEntityNum == passOwnerEntityNum` ⇒ 拒绝**】
```

### 6.3 ⭐⭐⭐ **"自/子/兄弟过滤，而父保留"**

**✅ 与 §465 的"`SV_MapTriggerTouches` 是一个精确的 SAT"**——**不同**（那是一个**几何**，这是一个**身份**）但**同族**（**第三次"一个**精确的**过滤器**"**）。

**⚠ 而 `!entity.ownerEntityNum`**⇒ **一个"没有 owner ⇒ 接受**"**的短路**。**

**⇒ 十层**：
```text
若【`ownerEntityNum` 不存在**】⇒ **⇒ `!ownerEntityNum` 【为真**】⇒ **⇒ 接受**】
⇒ **⇒ 所以【一个【世界几何**（**无 owner**）【总【被【接受**】
```

**✅ ⭐⭐⭐ **"一个世界几何总被接受"**。

**⚠ 而 `filter.passOwnerEntityNum` 的**嵌套**条件**⇒ **"`passOwnerEntityNum` 【只【在【`passEntityNum` 存在**时【有效**"**。**

**⇒ 十层**：
```cpp
return (!filter.passEntityNum || *filter.passEntityNum <= MaximumServerCollisionEntityNum) &&
    (!filter.passOwnerEntityNum ||
        (filter.passEntityNum && *filter.passOwnerEntityNum <= MaximumServerCollisionEntityNum));
```
```text
`passOwnerEntityNum` 存在 ⇒ **⇒ 而 `passEntityNum` 【必须【也**存在**
⇒ **⇒ 所以【一个孤立的 `passOwnerEntityNum` 【是【无效**的**
```

**✅ ⭐⭐⭐ **"一个孤立的 passOwnerEntityNum 是无效的"** —— 一个**精确的前提**。

**✅ 与 §465 的"`rule.cost = 0` ⇒ 忽略"**——**同族**（**第四次"一个**前提【使【一个字段【无效**"**）。

## 七、**`MaximumServerCollisionEntityNum = 2045`**

**⇒ 十层**：
```text
`2045` ⇒ **`0..2045` 合法**】
`2046` ⇒ **`BulletWorldEntityNum` / `EntityNumWorld`**
`2047` ⇒ **`BulletNoneEntityNum` / `EntityNumNone`**
⇒ **⇒ 所以【`2045` 【是【那个【`2048` 空间**的【最后**一个真实实体号**】
```

**✅ ⭐⭐⭐ **"2045 是那个 2048 空间的最后一个真实实体号"** —— 与 §416 的 `EntityNumWorld = 2046`/`EntityNumNone = 2047`**完全闭合** ✓

**⇒ 独立验证**：
```text
`2048 - 2 = 2046`（**两个哨兵**）
而 `MaximumServerCollisionEntityNum = 2045` ⇒ **⇒ 所以【哨兵 【是 `2046` 与 `2047`**】
⇒ **⇒ 而 `2045` 【是【那个【最大的真实**号**】
```

**✅ ⭐⭐⭐ **"2045 是最大真实号，2046/2047 是两个哨兵"** —— 一个**三段闭合**（**§416 的 `2046`/`2047` + §476 的 `2045`**）。

## 八、**`SV_CompareTraceResults` 的十二个比较项**

```text
1  Fraction       （|Δ| > tolerance ⇒ 差异）
2  Normal         （三个分量，每个 |Δ| > tolerance）
3  SurfaceFlags
4  Contents
5  HitType
6  HitId
7  ModelIndex
8  PartName
9  PartGroup
10 AllSolid
11 StartSolid
12 Walkable
```

### 8.1 二十四层

```text
1. **一项【比一项**严格**】——从【连续的浮点**到【离散的标量**】
2. ⇒ **⇒ 而【两个浮点**项【有【`tolerance`**】而【十个离散**项【精确相等**】
3. ⇒ **⇒ 所以【那个比较【是【分级**的**
```

### 8.2 ⭐⭐⭐ **"两个浮点项有 tolerance 而十个离散项精确相等"**

**✅ 与 §476 四 的"三个分量全部差一"**——**一个对照**（那里**没有容差**，这里**有**）。

**⇒ 三层**：
```text
浮点 ⇒ **容差**（**因为【计算不可重复**）
离散 ⇒ **精确**（**因为【同一个**引擎**）
⇒ **⇒ 所以【两级**判据**】
```

**✅ ⭐⭐⭐ **"两级判据"**。

**⚠ 而"fail closed on non-finite"**⇒ **一个**最重要的**守卫**。**

**⇒ 十层**：
```cpp
if (!std::isfinite(floatTolerance) || floatTolerance < 0.0f ||
    !std::isfinite(source.fraction) || !std::isfinite(native.fraction) || ...)
    return SvTraceComparisonDifference::Fraction;
```
```text
`NaN` ⇒ **`abs(NaN - x) > tol` 【为假**】⇒ **⇒ 会【被【当成**【相等**】**
⇒ **⇒ 所以【那个 `isfinite` 【是【必须的**】
```

**✅ ⭐⭐⭐ **"NaN 会让 `abs(NaN - x) > tol` 为假 ⇒ 会被当成相等"** —— 一个**极精确的防御理由**（与 §467 的"`from_chars` 对 `nan` 会成功"**同族**：**第二次"一个 `isfinite` 防止【一个**假的相等**"**）。

## 九、**玻璃的六比特量化与那个 `63/512`**

### 9.1 那段

```cpp
std::uint8_t packGlassImpactPosition(const float position)
{
    const auto packed = std::round(position * (63.0f / 512.0f) + 31.5f);
    return static_cast<std::uint8_t>(std::clamp(packed, 0.0f, 63.0f));
}
```

### 9.2 二十四层

```text
1. **`63 / 512`** ⇒ **一个【缩放**（**`±256` 世界单位 ⇒ `0..63`**）**
2. ⇒ **⇒ 而 `+ 31.5` ⇒ **把【`0` 映射到【`31.5`**（**那个中点**）**
3. ⇒ **⇒ 而 `round` ⇒ 一个**最近**的整数**
4. ⇒ **⇒ 而 `clamp(0, 63)` ⇒ 六个**位**
```

### 9.3 ⭐⭐⭐ **"`±256` 世界单位映射到 `0..63`，`0` 落在 `31.5`"**

**✅ 独立验证**：
```text
`position = 0` ⇒ `0 + 31.5 = 31.5` ⇒ `round = 32`（**或 31，取决于【舍入模式**）
`position = +256` ⇒ `256 × 63/512 = 31.5` ⇒ `31.5 + 31.5 = 63` ✓
`position = −256` ⇒ `−31.5 + 31.5 = 0` ✓
⇒ **⇒ 所以【那个范围【是 `±256` 世界单位** ✓
```

**✅ ⭐⭐⭐ **"那个范围是 ±256 世界单位"** —— 一个**精确的推导**。

**⚠ 而 `round(31.5)` ⇒ **`32`**（`std::round` 是**half away from zero**）**⇒ 所以【零点【落在 `32` 而不是 `31.5`**】**。**

**⇒ 十层**：
```text
`round(31.5) = 32` ⇒ **⇒ 所以【那个中点【是 `32` 而不是 `31`**】
⇒ **⇒ 而【那【是【一个【半个 LSB**的偏置**（**`64` 个值，中点【在 `31.5` ⇒ 无法精确表示**）
```

**✅ ⭐⭐⭐ **"那是一个半个 LSB 的偏置，64 个值的中点无法精确表示"** —— 一个**精确的量化观察**。

**✅ 与 §476 八 的"两个浮点项有 tolerance"**——**同族**（**第三次"一个**量化的误差**"**）。

### 9.4 而**`SV_ShouldSendGlassImpact` 的"含一秒钟的窗口"**

```cpp
return static_cast<std::int64_t>(lastStateChangeTime) + 1000 >=
    static_cast<std::int64_t>(snapshotTime);
```

**⇒ 十层**：
```text
`lastStateChange + 1000 >= snapshotTime`
⇒ **⇒ 而 `int64` 的强制转换 ⇒ 防止【`int32` 溢出**】
⇒ **⇒ 所以【一个【一秒钟的**窗口】（**含两端**）
```

**✅ ⭐⭐⭐ **"`int64` 的强制转换防止 `int32` 溢出"** —— 与 §475 的 "`allSolid` 的 `startSolid`"**不同**，但与 §469 的 "`static_cast<std::int32_t>(serverTime - wake)`"**同族**（**第三次"一个有符号的强制转换【处理**回绕/溢出**"**）。

**⚠ 而"含两端（`>=`）"**⇒ **一个**闭区间**。**

**⇒ 三层**：
```text
`>=` ⇒ **闭区间**（`lastStateChange + 1000` **本身【被【接受**）
⇒ **⇒ 所以【那个窗口【是 `1001ms` 宽**】
```

**✅ ⭐⭐ **"那个窗口是 1001ms 宽"** —— 一个**精确的观察**（**如果【端点【算【在内**）**。

## 十、**`SvGlassDamageState::configure` 的"`0xFFFF` 是保留的"**

```cpp
// CODREF(bullet_process): 0xFFFF is reserved for the deleted sentinel;
// a destroy threshold at that value is unreachable by accumulated
// damage.
if (pieceCount > SvGlassPieceCount || !thresholds.weaken ||
    thresholds.destroy == std::numeric_limits<std::uint16_t>::max() ||
    thresholds.weaken > thresholds.destroy)
    return false;
```

### 10.1 二十四层

```text
1. **`0xFFFF` 【为那个 deleted 哨兵**保留**】
2. ⇒ **⇒ 所以【一个【在【那个值**上的 destroy 阈值【是【不可达的**】
3. ⇒ **⇒ 因为【累积伤害【饱和在** `0xFFFE`**（`MaximumAccumulatedDamage`）**
4. ⇒ **⇒ 而 `weaken` 【不能【为 `0`**】
5. ⇒ **⇒ 而 `weaken > destroy` ⇒ 拒绝**】
```

### 10.2 ⭐⭐⭐ **"一个在 0xFFFF 上的 destroy 阈值是不可达的"**

**✅ 与 §470 的"`16383` 是一个保留值"**——**同族**（**第五次"一个**上界【被留作【一个**哨兵**"**）。

**⇒ 三层**：
```text
§468  **`InlineFollows = 0xFFFFFFFF`**（**`32` 位顶**）
§470  **`AttachmentIndex >= 16383` ⇒ 拒绝**（**`14` 位顶**）
§476  **`destroy == 0xFFFF` ⇒ 拒绝**（**`16` 位顶**）
⇒ **⇒ 三次"一个**顶值【是【一个【哨兵**"**
```

**✅ ⭐⭐⭐ **"一个顶值是一个哨兵"三例表**。

**⚠ 而 `piece.damageTaken` 的**饱和**】**。**

**⇒ 十层**：
```cpp
constexpr auto MaximumAccumulatedDamage = std::numeric_limits<std::uint16_t>::max() - 1u;
piece.damageTaken = static_cast<std::uint16_t>(std::min<std::uint64_t>(
    MaximumAccumulatedDamage, static_cast<std::uint64_t>(piece.damageTaken) + damage));
```
```text
`damageTaken + damage` 用 `uint64` 加**】⇒ **⇒ 防止【`uint16` 溢出**】
⇒ **⇒ 而 `min(0xFFFE, ...)` ⇒ **饱和**
```

**✅ ⭐⭐⭐ **"用 uint64 相加防止 uint16 溢出，而 min 饱和"** —— 与 §476 八 的"`int64` 强制转换"**同族**（**第四次"一个**更宽的中间类型【防止溢出**"**）。

## 十一、关键结论

1. **⭐⭐⭐ "这些是 CODOL 自己的表，而它们在两个镜像里都有；§51i 把它们记成 FOREIGN，而那被那些镜像自己推翻"`** —— 而 **两个 build 的地址布局不同（3.3.3.3 相邻步长 `20`；1649370 相距 `100`，独立验证 `0x64 = 0x64` ✓）**，**字节相同** ⇒ **"那个表是二十条，不是 22；索引 20 与 21 是发明的，而索引 20 在 3.3.3.3 上是下一个表的第一个字节"`** ⇒ **"尾部在 20 之后保持零，所以一个未知的 CODOL 分类 fail closed"`**。
2. **⭐⭐⭐ `[19] = 101` 而 Ghosts 是 `201`** ⇒ **"那个值是一个 build 特定的常量"`**（与 §474 的 `+5` 同族）；而 `bullet` 的 `[1..17]` 全是常数 `3`，`rifle` 的 `[1..17]` 是 `9 9 9 8 7 6 6 6 6 5 5 4 4 4 4 3 3` —— **独立验证：每一对相邻都不增**。
3. **⭐⭐⭐ `LocationalPriorityMapSize = 256` 而 `KnownLocationalPriorityCount = 20`，只初始化 `20` 个 ⇒ 剩下 `236` 个是零** ⇒ **"那个 256 不是一个选择，是一个类型的界"`**（索引是 `uint8`，与 §472 的 `& mask` 同族），而**两个常量承担两个不同的职责**（一个说"哪些是测量的"，一个说数组的真实大小）。
4. **⭐⭐⭐ 三个分量的"差一"是【一个统一的 1 单位内缩**】，而**那正是 `.hpp:79-80` 的 `inset trace box`**（`out.exe 0x46D6E0` 解码 `entityState+0xAC` 给 `0x46DAE0` 的客户端胶囊）⇒ **"那不是缺陷，是规格"`**。**我最初把它判成一个候选缺陷 —— 那个判据是错的**：**"编解码不往返是一个必须先查『两端是否服务同一个语义』的判据"`**（这里一端是服务端的**发布值**、另一端是客户端的**内缩追踪盒** ⇒ **不是往返**）—— **"先查语义，再判缺陷"`**。
5. **⭐⭐⭐ `clampSolidComponent` 的界 `1..255` ⇒ "一个零字段的打包是不可能的"`** ⇒ **"这正是一个 `0` 分支在解码里被当成『无效』的理由"`**；而 `solid == 0xFFFFFF ? 1u` 的分支只在**三个字段全是 `255`** 时触发 ⇒ **独立算得那需要一个 `477` 单位高的实体**（不可能，玩家 `70`）。
6. **⭐⭐⭐ `SV_ShouldClipToEntity` 的三层过滤**（`linked` + `contents` / `passEntityNum` 的自/owner / `passOwnerEntityNum`）⇒ **"自/子/兄弟过滤，而父保留"`**；而 **"没有 owner ⇒ 接受"** ⇒ **"一个世界几何总被接受"`**；而 **`passOwnerEntityNum` 必须与 `passEntityNum` 同时存在** ⇒ **"一个孤立的 passOwnerEntityNum 是无效的"`**。
7. **⭐⭐⭐ `MaximumServerCollisionEntityNum = 2045`** ⇒ **"2045 是最大真实号，2046/2047 是两个哨兵"`** —— 与 §416 的 `EntityNumWorld = 2046` / `EntityNumNone = 2047` 构成**三段闭合**。
8. **⭐⭐⭐ `SV_CompareTraceResults` 的十二项**（浮点 `Fraction`/`Normal` 用容差，其余十项精确）⇒ **"两级判据"`**；而那个 `isfinite` 守卫的理由是 **"NaN 会让 `abs(NaN - x) > tol` 为假 ⇒ 会被当成相等"`** —— 与 §467 的"`from_chars` 对 `nan` 会成功"同族（**一个 `isfinite` 防止一个假的相等**）。
9. **⭐⭐⭐ `packGlassImpactPosition` 的 `63/512`** ⇒ **独立推导：`±256` 世界单位映射到 `0..63`**（`+256 ⇒ 63` ✓、`−256 ⇒ 0` ✓）；而 **`round(31.5) = 32` ⇒ "一个半个 LSB 的偏置（64 个值的中点无法精确表示）"`**。
10. **⭐⭐ `SV_ShouldSendGlassImpact` 的 `int64` 强制转换**（防止 `int32` 溢出）与 **`>=`（闭区间）⇒ "那个窗口是 1001ms 宽"`** —— 与 §469 的有符号强制转换同族。
11. **⭐⭐ `configure` 的"`0xFFFF` 为 deleted 哨兵保留 ⇒ 一个在它上面的 destroy 阈值不可达"`** —— **第三次"一个顶值是一个哨兵"**（与 §468/§470 同族）；而 `damagePiece` 的 **`uint64` 相加 + `min(0xFFFE, …)` 饱和** —— 第四次"一个更宽的中间类型防止溢出"。

## 十二、`sv_collision_mp` 全文件总览

**`.cpp`：`790` 行。`.hpp`：`422` 行。**

**`10` 个常量**（`.hpp`）：
```text
StandingPlayerTraceBounds                 （70 高 × 30 宽）
DeadPlayerTraceBounds
PlayerCollisionContentMask        0x02814011
PlayerCollisionContents           0x02000000
DeadPlayerCollisionContents       0x04000000
PlayerSolidEncodingContents       0x02004001
MaximumServerCollisionEntityNum   2045
TraceHitTypeEntity                1
TraceHitTypeGlass                 4
BrushModelSolid                   0x00FFFFFF
KnownLocationalPriorityCount      20
LocationalPriorityMapSize         256
SvGlassPieceCount                 1024
```

**`14` 个函数**：`finiteVector` / `quatToAxis` / `packGlassImpactPosition` / `validBounds` / `clampSolidComponent` / `linkedPlayerBounds` / `linkedBrushBounds` / `SV_IsCollisionEntityValid` / `SV_LinkPlayerCollisionEntity` / `SV_LinkActorCollisionEntity` / `SV_LinkBrushModelCollisionEntity` / `SV_LinkScriptModelCollisionEntity` / `SV_DecodePackedSolidBounds` / `SV_EncodePlayerSolid` / `SV_EncodeBrushModelSolid` / `SV_IsTraceEntityFilterValid` / `SV_IsPointTraceRequestValid` / `SV_GetLocationalPriorityMap` / `SV_ShouldClipToEntity` / `SV_ShouldBroadphaseClipToEntity` / `SV_ApplyEntityTraceHit` / `SV_CompareTraceResults` / `SV_IsGlassMapMetadataValid` / `SV_QuantizeGlassImpact` / `SV_ShouldSendGlassImpact`；以及 `SvGlassState` 的五个方法与 `SvGlassDamageState` 的五个方法。

**`6` 个碰撞形状 / 角色**：`BrushModel` / `Capsule` / `ScriptModelDObj`（+ 默认）；`None` / `Player` / `Actor`。

**`8` 个来源锚点**：`0x005FAE70`（`SV_LinkEntity`）/ `0x005FAEC9` / `0x005FAED5` / `0x005FB510`（`SV_PointTraceToEntity`）/ `0x005FB940`（`SV_Trace`）/ `0x005FAAAE` / `0x005FAAE7` / `0x0046D738..0x46D7AC`（打包边界）。而 BO1 的 `0x00721F40`（`SV_SetupIgnoreEntParams`）。

## 十三、未闭合点

- `StandingPlayerTraceBounds` 的精确数值（`.hpp:61`，未逐字读）。
- `0x02814011` / `0x02004001` 的位语义。
- `SvGlassPieceState` 的四个值（`Pristine`/`Weakened`/`Destroyed`/`Deleted`）。
- `0x46D6E0`（那个 `inset trace box` 的解码器）与 `SY_DecodePackedSolidBounds` 的常数项是否一致。
- 下一个文件：`sv_zm_special_world_mp.cpp`（`33,019` 字节）。
