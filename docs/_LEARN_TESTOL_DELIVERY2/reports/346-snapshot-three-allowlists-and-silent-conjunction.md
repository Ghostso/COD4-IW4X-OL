# 346 · **"这个 allowlist 是独立的：缺一个 eType 不是丢掉实体而是拒掉【整帧】"** —— 三处 allowlist、`0x800` 的半个端口、七十五项合取取名、flags 的两条 3.3.3.3 规则被实测推翻

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 9198–9998 行。

## 二、**`0x400 → 0x800` 的"半个端口"**（本组第三重要）

### 2.1 那段

```php
// CODDIFF(1649370): 0x800 entries, was 0x400. These are indexed BY the
// clip and ammo indexes whose bounds this build widened to 0x7FE and 0x7FF
// (11 and 12 bits, was 10 and 11) -- leaving them at 3.3.3.3's 0x400 wrote
// up to 1023 bools past the end of a stack array on every frame carrying a
// real modular clip index, and this project has measured those at 1188 and
// 1297. A widened bound is only half a port; the table it indexes is the
// other half.
std::array<bool, MaxCurrentWeaponAssetIndex + 1> heldWeaponAssets{};
std::array<bool, 0x800> clipIndexes{};
std::array<bool, 0x800> ammoIndexes{};
```

### 2.2 八层

```text
1. **`0x800` 项，原来是 `0x400`**
2. ⇒ **这些被 clip 与 ammo 索引【索引】**
3. ⇒ **而这个 build 把它们的界加宽到 `0x7FE` 与 `0x7FF`（11 与 12 位，原为 10 与 11）**
4. ⇒ **把它们留在 3.3.3.3 的 `0x400` 会在每一个携带真实模 clip 索引的帧上写【1023 个 bool 越过一个栈数组的末尾】**
5. ⇒ **而本项目已在 `1188` 与 `1297` 处测得那些**
6. ⇒ **一个加宽的界只是端口的一半；它索引的表是另一半**
```

### 2.3 **"一个加宽的界只是端口的一半；它索引的表是另一半"**

**✅ 这是本文件里**最重要的一条移植纪律**。**

**⇒ 与 §318 的"一个从观测范围取的界拒绝第一个未观测值"**不同** —— 那是**界**，这是**界所索引的表**。**

**⚠ 所以**两个独立的移植陷阱**：**

```text
① 界必须是【线宽】不是观测范围        §318
② 界加宽后它索引的表也必须加宽          §346
```

**✅ **两条互补。**

### 2.4 而**"栈数组越界 1023 个 bool"**

**⇒ 三层**：

```text
1. `0x400` 项而索引可达 `0x7FE`
2. ⇒ 越界 1023 项
3. ⇒ **在栈上 ⇒ 静默损坏**
```

**⚠ 而**实测的索引是 1188 与 1297。**

**⇒ 两者都 > `0x400`（1024）。**

**✅ 所以**越界是必然的**。**

### 2.5 而 `MaxCurrentWeaponAssetIndex + 1`

**⇒ 与 §239 的 `MaximumWeaponAssetIndex = 0x7FF` 配合。**

**⇒ 所以 `heldWeaponAssets` 是 **2048** 项。**

**✅ 而 clip/ammo 是 **2048** 项（`0x800`）。**

**⇒ 三个表**同尺寸**。**

## 三、**七十五项合取却只有一个 `return reject`**（本组第二重要）

### 3.1 那段

```php
// SEVENTY-FIVE TERMS, ONE `return reject(...)`. This is the same silent
// conjunction that hid the pinned usercmd queue and then the animation bound,
// and it became the top frameReject the moment snapshots actually started
// flowing. Every one of these limits is a claim about THIS build's wire, so a
// rejection has to say which limit and with what value -- otherwise a bound
// that is still 3.3.3.3's is indistinguishable from a genuinely bad frame.
```

### 3.2 八层

```text
1. **七十五项，一个 `return reject(...)`**
2. ⇒ **这是同一个沉默的合取，它先藏起了被钉住的 usercmd 队列、然后又藏起了动画界**
3. ⇒ **而它在快照真正开始流动的那一刻成了【头号 frameReject】**
4. ⇒ **这里的每一个限制都是关于【这个 build 的线】的一个断言**
5. ⇒ **所以一个拒绝必须说【哪一个限制】以及【用什么值】**
6. ⇒ **否则一个仍然是 3.3.3.3 的界与一个真正坏的帧【无法区分】**
```

### 3.3 **"沉默的合取"**

**✅ 与记忆里的"沉默读起来像健康"**完全同族（**第五次？**）。**

**⇒ 而这在 §345 的"无偏计数"里有**反面**：**

```text
沉默的合取      ⇒ 一个布尔假而不知哪一项
无偏计数        ⇒ 一个零是真正的零
```

**✅ **一对互补**。

### 3.4 而 `psDomainValue` / `psDomain` / `psDomainBad` 的三层

```cpp
const auto psDomainBad = [](const char *const term, const std::string &value) {
    static std::string reported;
    auto details = std::string(term) + "=" + value;
    if (details != reported) { reported = details; OlMod::RuntimeLog::write(..., "playerstate domain refused " + details); }
    return true;
};
const auto psDomain = [&psDomainBad](const char *const term, const bool bad) {
    return bad ? psDomainBad(term, "1") : false;
};
const auto psDomainValue = [&psDomainBad](const char *const term, const bool bad, const auto value) {
    return bad ? psDomainBad(term, std::to_string(value)) : false;
};
```

### 3.5 四层

```text
① `psDomainBad` ⇒ 写日志并返回 true
② ⇒ **`static std::string reported`** ⇒ 只在【变化】时写
③ `psDomain` ⇒ 只给名字（值固定 "1"）
④ `psDomainValue` ⇒ 名字 + 值
```

**✅ 一个**"每个不同的失败只报一次"**的手法。**

**⚠ 而 `static` 在 lambda 里 ⇒ **整个进程共享一个 `reported`**。**

**⇒ 所以**两个不同客户端/两次不同失败会互相覆盖**。**

**⚠ 一处**细小缺陷**（但符合"不要日志洪水"的意图）。**

### 3.6 而**七十五项的分类**

**⇒ 按主题分组：**

```text
伤害/生命      damageEvent damageYaw damagePitch damageCount health maxHealth deadYaw
震荡           shellshockIndex shellshockDuration
物理           gravity speed eFlags
动画           legsTimer torsoTimer legsAnim torsoAnim weaponAnim[2]
武器时间        weaponTime weaponDelay weaponRestrictKickTime
武器状态        weaponState[2] weaponHandFlags[2] weaponShotCount[2]
武器索引        currentWeaponAssetIndex offhandWeaponAssetIndex offhandWeaponSlots
手雷           offhandPredictionState（grenadeEntityNum + grenadeTimeLeft）
奖励           rewardTargets rewardActionType rewardActionWeapon
雷达           radarFlags
视图           viewmodelIndex otherFlags
聚合           heldWeaponsValid ammoClipsValid ammoPoolsValid objectivesValid hudValid
视角高度        viewHeightTarget viewHeightLerpTarget viewHeightCurrent
趴下           proneDirection proneDirectionPitch proneTorsoPitch
梯子           ladderVector
冲刺           sprintButtonUpRequired sprintDelay sprintStartMaxLength
翻越           mantleYaw mantleTransitionIndex
武器位置        weaponPositionFraction aimSpreadScale
散布           spreadOverride spreadOverrideState
尺寸           playerSizeScale moveSpeedScaleMultiplier
实体号          groundEntityNum viewEntityNum movingPlatformEntityNum remoteEyesEntityNum
               remoteControlEntityNum remoteTurretEntityNum linkEntityNum
向量            origin velocity deltaAngles viewAngles
```

**⇒ 约 75 项 ✓**

### 3.7 而**七类实体号的 `> EntityNumNone`**

**⇒ 七个：**

```text
groundEntityNum / viewEntityNum / movingPlatformEntityNum /
remoteEyesEntityNum / remoteControlEntityNum / remoteTurretEntityNum /
linkEntityNum
```

**✅ 与 §344 的 `EntityNumNone` 一致。**

**⚠ 而 §345 的 `EntityNumWorld == 2046` ⇒ 所以 `EntityNumNone` 可能是 **2047**。**

**⇒ 一个**可推算的常数**（11 位全一）。**

**✅ **闭合** ✓**

### 3.8 而 `radarFlags > 63`

**⇒ 三层**：

```text
1. `radarFlags` 的界是 63
2. ⇒ **6 位**
3. ⇒ 与 §258 的"`-101` = 1 位 + 6 位"**完全一致 ✓**
```

**✅ **第二次确认 `-101` 的 6 位。**

### 3.9 而 `otherFlags > 0x7FFFFFFF`

**⇒ 31 位。**

**✅ 与 §258 的"`-102` = 1 位 + 31 位"**完全一致 ✓**

**⇒ **第二次确认。**

### 3.10 而 `viewmodelIndex > 0x3FF` 与 `rewardActionWeapon > 2047`

**⇒ 都是 10 位 / 11 位。**

**⚠ 而 `0x3FF` = 1023（10 位）而 `2047` = `0x7FF`（11 位）。**

**⇒ 两个不同的界。**

**✅ 与 §239 的 `MaximumWeaponAssetIndex = 0x7FF` 配合（`rewardActionWeapon` 是武器索引）。**

**⚠ 而 `viewmodelIndex` 是 10 位 ⇒ **一个不同的带**。**

## 四、**HUD 元素准入的十一项**（本组第四重要）

### 4.1 那段（部分）

```php
const auto hudElemsValid = [&frame](const std::array<SvHudElem, 31> &elems) {
    auto foundFree = false;
    for (const auto &elem : elems) {
        if (elem.type == SvHudElemType::Free) {
            foundFree = true;
            if (elem != SvHudElem{}) return false;
            continue;
        }
        const auto drawsMaterial = elem.type == Waypoint || elem.type == Icon || elem.isClock();
        const auto drawsText = elem.type == Value || elem.type == PlayerName || elem.type == Text;
        const auto pulse = (elem.type == PlayerName || elem.type == Text) && elem.fadeTime == 0 && (...);
        if (foundFree || (!drawsMaterial && !drawsText) || ...) return false;
        ...
    }
    return true;
};
```

### 4.2 **"`foundFree` ⇒ 之后一切必须空"**

```cpp
if (elem.type == SvHudElemType::Free) {
    foundFree = true;
    if (elem != SvHudElem{}) return false;
    continue;
}
...
if (foundFree || ...) return false;
```

**⇒ 三层**：

```text
1. **遇到一个 Free ⇒ 设标志**
2. ⇒ **而若那个 Free 项不是全零 ⇒ 拒绝**
3. ⇒ **而之后任何非 Free 项 ⇒ 拒绝**
```

**✅ 一个**"Free 是终止哨兵"**的语义。**

**⇒ 与 §342 的 `writeEntityNumber` 的"终止"、§337 的归并终止位同族。**

### 4.3 而**两个抽屉（material / text）的互斥**

```php
// The material types and the text types have disjoint
// requirements: sub_BB5680 will not draw an icon without a
// material, and sub_BB4B70 will not size text without a
// font scale, while neither reads the other's fields.
const auto drawsMaterial = Waypoint || Icon || isClock();
const auto drawsText = Value || PlayerName || Text;
```

**⇒ 五层**：

```text
1. **材质类型与文本类型有【不相交】的要求**
2. ⇒ **`sub_BB5680` 不会在没有材质的情况下画一个图标**
3. ⇒ **而 `sub_BB4B70` 不会在没有字体缩放下调整文本尺寸**
4. ⇒ **而两者都不读对方的字段**
5. ⇒ **所以 `drawsMaterial` 与 `drawsText` 是两个不相交集**
```

**✅ 两个集**共 6 个类型**（3 + 3）。**

**⚠ 而 `isClock()` 在 `drawsMaterial` 里 ⇒ 所以**时钟是一个材质类型**。**

### 4.4 而**"一个量化到零的文本元素是不可见的"**

```php
// A text elem whose scale quantises to zero six-bit
// tenths is invisible: sub_BB4B70 multiplies it into
// the glyph height at 0x00BB4C6F. Reject that here
// rather than ship an elem the client cannot show.
(drawsText && (!(elem.fontScale >= 0.1f) || elem.fontScale > HudElemFontScaleMaximum || ...))
```

**⇒ 五层**：

```text
1. **一个缩放量化到零个六位十分位的文本元素是【不可见的】**
2. ⇒ **`sub_BB4B70` 在 `0x00BB4C6F` 把它乘进字形高度**
3. ⇒ **六位十分位 ⇒ 最小非零是 0.1**
4. ⇒ **所以 `fontScale >= 0.1f`**
5. ⇒ **在这里拒绝而不是发一个客户端不能显示的元素**
```

**✅ 与 §343 的"`-86` = `ReadBits(6) / 10.0`"**完全一致 ✓**

**⇒ **第二次确认那个编解码器。**

**⚠ 而 §258 说 `-86` 的 max 是 6.3 ⇒ 所以 `HudElemFontScaleMaximum = 6.3`。**

**✅ **闭合** ✓**

### 4.5 而 **`(materialIndex - 1) > 0x3FE` 的汇编证据**

```php
// CODREF: both material drawers admit exactly this
// domain. sub_BB5680 (icon) rejects with
// "(materialIndex - 1) > 0x3FE" at 0x00BB56A5 before
// resolving configstring materialIndex+4355, and the
// waypoint path tests material > 0 at 0x00BD8B7A.
(drawsMaterial && (!elem.materialIndex || elem.materialIndex > 0x3FF || !elem.width || elem.width > 0x3FF || !elem.height || elem.height > 0x3FF))
```

### 4.6 六层

```text
1. **两个材质抽屉恰好接受这个域**
2. ⇒ **`sub_BB5680`（图标）在 `0x00BB56A5` 用 "(materialIndex - 1) > 0x3FE" 拒绝**
3. ⇒ **在解析 configstring `materialIndex + 4355` 之前**
4. ⇒ **而 waypoint 路径在 `0x00BD8B7A` 测 `material > 0`**
5. ⇒ **所以 `materialIndex ∈ [1, 0x3FF]`**
6. ⇒ **而 width/height 同样 `[1, 0x3FF]`**
```

**✅ 而 **`materialIndex + 4355`** ⇒ 与 §310 的"材质带在 4872"**不同**。**

**⚠ 所以**两个不同的材质基址**：**

```text
4355   HUD 图标
4872   材质 configstring 带
```

**⚠ 一处**需要核对的差异**。**

**⇒ 可能 4355 是**另一个带**（HUD 专用）。**

**✅ 与 §310 的"材质私有非公共"配合。**

### 4.7 而 **`alignOrg > 0xF`**

```php
// CODREF: descriptor 15 is a 4-bit field (0x012F6AC0
// row 15 = {0x28, 4}); a wider value would not survive
// the wire. alignScreen is the full 8 bits of its
// descriptor, so std::uint8_t already bounds it.
elem.alignOrg > 0xF ||
```

**⇒ 五层**：

```text
1. **描述符 15 是 4 位字段（`0x012F6AC0` 行 15 = `{0x28, 4}`）**
2. ⇒ **一个更宽的值不会活过线**
3. ⇒ **`alignScreen` 是它描述符的完整 8 位**
4. ⇒ **所以 `std::uint8_t` 已经界定了它**
5. ⇒ **所以只检查 `alignOrg`**
```

**✅ 一个**"成员类型本身就是界"**的论证。**

### 4.8 而 **`label > 0x7FF` 的 `10 → 11`**

```php
// CODDIFF(1649370): the hudElem label is 11 bits
// here, 10 on 3.3.3.3 -- table index 33 moved from
// `bits 10` to `bits 11`. The writer already uses
// HudElemLabelBits = 11; only this bound lagged.
elem.label > 0x7FF ||
```

**⇒ 五层**：

```text
1. **`hudElem label` 这里是 11 位，3.3.3.3 是 10 位**
2. ⇒ **表索引 33 从 `bits 10` 移到 `bits 11`**
3. ⇒ **写入器【已经】用 `HudElemLabelBits = 11`**
4. ⇒ **只有这个界【滞后】了**
5. ⇒ 改成 `> 0x7FF`
```

**✅ 与 §346 二 的"一个加宽的界只是端口的一半"**同族（**第二次**）。**

**⇒ 而这里是**界滞后于写入器**（与 clip 表相反，那是**表滞后于界**）。**

**✅ **两个方向都被记录。**

### 4.9 而 **两条 3.3.3.3 的 flags 规则被实测推翻**（本组第五重要）

```php
// THE TWO FLAG RULES THAT USED TO BE HERE WERE 3.3.3.3's,
// AND THIS BUILD'S OWN TRAFFIC CONTRADICTS BOTH.
//
// They required bit 0 and forbade 0x4000, citing
// 0x00BD7C4C "test cl,1 / jz default" and 0x00BD8B12
// "test ecx,4000h / jnz default". Those addresses are
// dest1yo's client's; in out.exe they fall inside
// sub_BD7780, which registers r_picmip and r_specular.
//
// MEASURED, every flags value a retail OLfinal server
// put on the wire in C-2021-7-25[1-19-26]dm.demo:
//
//     1 x9    65536 x3   65537 x2   0 x2   257 x1
//     16384 x1
//
// Bit 0 is CLEAR in six of the eighteen elements (0,
// 65536, 16384) and 0x4000 is SET in one - the
// waypoint. So these two conditions between them
// rejected a third of what a real server of this build
// sends, including its own waypoint. The 25-bit bound
// below is kept: it is the descriptor's own width.
```

### 4.10 十三层

```text
1. **曾在这里的两条 flags 规则是 3.3.3.3 的，而这个 build 自己的流量【两条都反驳】**
2. ⇒ **它们要求 bit 0 而禁止 `0x4000`**
3. ⇒ 引用 `0x00BD7C4C` 的 `test cl,1 / jz default`
4. ⇒ 与 `0x00BD8B12` 的 `test ecx,4000h / jnz default`
5. ⇒ **那些地址是 dest1yo 的客户端的**
6. ⇒ **在 `out.exe` 里它们落在 `sub_BD7780` 里，那注册 `r_picmip` 与 `r_specular`**
7. ⇒ **实测：一个零售 OLfinal 服务器在 `C-2021-7-25[1-19-26]dm.demo` 里放到线上的每一个 flags 值**：
     · `1` ×9
     · `65536` ×3
     · `65537` ×2
     · `0` ×2
     · `257` ×1
     · `16384` ×1
     · （共 18 个）
8. ⇒ **bit 0 在十八个元素里的【六个】是【清零】的**（`0`、`65536`、`16384`）
9. ⇒ **而 `0x4000` 在【一个】里是【置位】的 —— 那个 waypoint**
10. ⇒ **所以这两条条件在它们之间拒掉了【一个真实服务器所发内容的三分之一】，包括它自己的 waypoint**
11. ⇒ **下面的 25 位界被保留：那是描述符自己的宽度**
12. ⇒ **`hudElem flags` 这里是 25 位，3.3.3.3 是 18 位**
```

### 4.11 **"那些地址是 dest1yo 的客户端的"**

**✅ 与 §340 的"§82e 的诊断错而建议对"、§345 的"`demoq` 的表示差"**第三次同类**。**

**⇒ 核三层**：

```text
1. 从另一个 build 的地址推规则
2. ⇒ **而那个地址在这个 build 里落在完全不同的函数**
3. ⇒ **所以规则是凭空来的**
```

**✅ 与 AGENTS.md 的"ol-mod 不是权威"**完全同族。**

**⇒ **第四次"跨 build 引用失败"。**

### 4.12 而**六个 flags 值的分布**

```text
1        ×9    （bit 0 置位）
65536    ×3    （bit 16）
65537    ×2    （bit 0 + bit 16）
0        ×2    （无位）
257      ×1    （bit 0 + bit 8）
16384    ×1    （bit 14）
```

**⇒ 合计 18。**

**✅ 而 `0x4000 = 16384` ⇒ **bit 14**。**

**⇒ 所以 waypoint 用 bit 14。**

**⚠ 而 `1 = bit 0`、`65536 = bit 16`、`257 = bit 0 | bit 8`。**

**⇒ 四个不同的位。**

### 4.13 而 **`alphaValid` 的五位 alpha**

```php
// Both ends of the fade travel through the same -85 codec,
// which carries alpha in five bits, so both must land on a
// representable value.
const auto alphaValid = [](const std::uint32_t color) {
    const auto alpha = static_cast<std::uint8_t>(color >> 24);
    return alpha == 0xFF || !(alpha & 7);
};
```

**⇒ 四层**：

```text
1. **fade 的两端都走同一个 `-85` 编解码器**
2. ⇒ **它以【五位】携带 alpha**
3. ⇒ **所以两端都必须落在一个可表示的值上**
4. ⇒ **`alpha == 0xFF || (alpha & 7) == 0`**
```

**⚠ 而"五位" ⇒ 所以 alpha 的**低三位必须为零**（32 级量化）。**

**✅ 而 `0xFF` 是**全不透明**的特例（不是 32 的倍数）。**

**⇒ 一个**精确的哨兵例外**。**

### 4.14 而 **HUD 的坐标窗口 `[-0x8000, 0x7FFF]`**

```php
const auto value = roundedOrigin(elem.origin[axis]);
const auto center = roundedOrigin(frame.mapCenter[axis]);
if (!value || !center ||
    (int64)*value - *center < -0x8000 || (int64)*value - *center > 0x7FFF)
    return false;
```

**⇒ 三层**：

```text
1. **`value - center` 在 `[-0x8000, 0x7FFF]`**
2. ⇒ **16 位有符号**
3. ⇒ **而 §342 的 `writeEntityOrigin` 是 `[-0x8000, 0x7FFF]` 减去 `0x8000` 的窗口**
```

**⚠ 所以**两个不同的窗口**：**

```text
HUD        value - center ∈ [-0x8000, 0x7FFF]     （有符号 16 位）
entity     value - center + 0x8000 ∈ [0, 0xFFFF]  （无符号 16 位）
```

**✅ **等价**（都是 65536 个值）。**

**⚠ 所以**同一个窗口的两种表述**。**

## 五、**"这个 allowlist 是独立的"—— 三处必须同时改**（本组最重要的一段）

### 5.1 那段

```php
// This allow-list is INDEPENDENT of the one in the entity walk and
// of the per-eType validator dispatch. An eType missing here does
// not drop the entity - it rejects the WHOLE FRAME, so a single
// unlisted entity stops every snapshot for every client and the
// match dies. Adding an eType means touching all three.
//
// AND THE OBITUARY WAS MISSING FROM IT. sect.191q added
// EntityTypeObituary to the entity-walk allow-list and to the
// validator dispatch, and not to this one -- exactly the omission
// the paragraph above warns about. The consequence is not a
// dropped obituary: it is `entity_domain`, a WHOLE FRAME rejected,
// for every snapshot carrying a kill. That is a candidate
// explanation for "obituary ARCHIVED, no feed on screen", and it
// is fixed here whether or not it turns out to be the whole story.
// The feed itself stays default-OFF; this only means that turning
// it on can no longer stop the match.
```

### 5.2 十四层

```text
1. **这个 allowlist 是【独立的】** —— 与实体遍历里的那个、与逐 eType 验证器派发都独立
2. ⇒ **一个在这里缺失的 eType【不】丢掉那个实体**
3. ⇒ **它拒掉【整帧】**
4. ⇒ **所以一个未列出的实体停掉每一个客户端的每一个快照而比赛死掉**
5. ⇒ **加一个 eType 意味着碰【全部三处】**
6. ⇒ **而布告曾在这里缺失**
7. ⇒ **第 191q 节把 `EntityTypeObituary` 加到了实体遍历 allowlist 与验证器派发，而没有加到这一个**
8. ⇒ **正是上面那一段警告的遗漏**
9. ⇒ **后果不是一个被丢掉的布告：它是 `entity_domain`，一个【整帧】被拒**
10. ⇒ **对每一个携带一次击杀的快照**
11. ⇒ **那是"`obituary ARCHIVED` 而屏幕上没有 feed"的一个候选解释**
12. ⇒ **而它在这里被修了，无论它是否最终证明是全部真相**
13. ⇒ **feed 本身保持默认关闭**
14. ⇒ **这只意味着打开它不再能停掉比赛**
```

### 5.3 **"三处 allowlist"**

```text
① 实体遍历（`writeEntities` 里的 `validEntity`）   §345
② 逐 eType 验证器派发（`SV_WritePacketEntities` 里的 `validEntity`）  §345
③ **这一处（`SV_ValidateSnapshotFrame` 的实体循环）**  §346
```

**✅ 三处，**两个语义**：**

```text
①②  缺一个 ⇒ 丢掉那个实体（静默）
③    缺一个 ⇒ 拒掉整帧（致命）
```

**⚠ 所以"三处"的名字相同而后果**完全不同**。**

**✅ 与 §344 的"`writeChangedEventEntity` 用普通赋值"**同族（**三处同型代码，强度不同**）。**

**⇒ **第五次"三处同型"。**

### 5.4 而**"`obituary ARCHIVED` 而屏幕上没有 feed"**

**✅ 与 §344 的"归档不等于发出"**完全一致 ✓**

**⇒ 而 §344 的代码里有 `obituary WIRE` 日志（六行/击杀）。**

**⚠ 所以**两个探针**：**

```text
§344  "obituary WIRE num=..."   ⇒ 到达写入器
§346  "entity_domain reject"    ⇒ 在验证处被拒
```

**✅ **两个层次都被仪器化了。**

**⇒ 一个**完整的可观测链**：ARCHIVED → (验证) → WIRE → 客户端。**

### 5.5 而 **`entity_domain reject num=700 eType=19`**

```php
// ET_ACTOR. THE THIRD OF THE THREE this comment names, and the one
// that was missed: the archive allow-list and the writer's dispatch
// were updated, this was not, and every frame was rejected with
// `entity_domain` -- snapshots=0, client on the map-load screen.
// The built-in offender line named it exactly: `entity_domain
// reject num=700 eType=19`.
```

**⇒ 七层**：

```text
1. **ET_ACTOR —— 这个注释点名的三者里的第三个，而它是被漏掉的那个**
2. ⇒ **归档 allowlist 与写入器派发被更新了，这里没有**
3. ⇒ **而每一帧都被 `entity_domain` 拒掉**
4. ⇒ **`snapshots=0`，客户端在加载屏**
5. ⇒ **内建的 offender 行精确点名它：`entity_domain reject num=700 eType=19`**
```

**✅ 与 §344 的**两次**（布告 + actor）**同一个漏**。**

**⇒ 所以**两次独立发生**（布告与 actor）。**

**⚠ 而**第一次（布告）没被发现，第二次（actor）靠 offender 行定位。**

**⇒ 所以 offender 行是**那次事故的产物**。**

### 5.6 而 **`eType = 19`**

**⇒ 所以 `EntityTypeActor == 19`。**

**✅ 与 §344 的推算"`19→21`"**完全一致 ✓**

**⇒ **第二次确认 `EntityTypeActor = 19` 与 `EntityTypeActorCorpse = 21`。**

### 5.7 而 **`reported.insert(entity.number).second`**

```cpp
static std::set<std::uint32_t> reported;
if (reported.insert(entity.number).second) { /* log */ }
```

**⇒ 三层**：

```text
1. **一个静态集合记录已报告的实体号**
2. ⇒ **只在首次插入成功时记日志**
3. ⇒ **所以每个实体号只报一次**
```

**✅ 与 `psDomainBad` 的 `static reported` **同一个意图**（避免洪水）。**

**⚠ 而这里是 `std::set` 而那里是 `std::string` ⇒ **两个不同的实现**。**

### 5.8 而 offender 行的**二十三个字段**

```text
num / eType / clientNum / eFlags / solid / brushIdx / modelIndex / weapon /
parentPlusOne / tag / scale / f0058 / f00E4 / f0098 / f0070 /
posTr / aposTr / eventSeq / otherEnt / podium
+ actor{ model / slot / field0058 / attacker / ground / loop / field00AC /
         field0054 / org / ang / eventParm / impactSurface / impactFlags }
```

**⇒ 二十个通用 + 十三个 actor 专用 = 三十三个。**

**✅ 一个**极详尽的诊断行**。**

**⚠ 而 `isActorEType(entity.eType)` 决定是否附 actor 段。**

**⇒ 所以**按 eType 定制诊断**。**

## 六、**玻璃的稀疏/稠密二选一**（本组第六重要）

```cpp
const auto prefixCount = (uint32)changedPieces.back().pieceIndex + 1;
auto sparseBitCount = 13u;
for (const auto &piece : changedPieces)
    sparseBitCount += 13 + glassImpactBitCount(piece);
auto fullBitCount = 13u + 2 * prefixCount;
for (pieceIndex = 0; pieceIndex < prefixCount; ++pieceIndex)
    fullBitCount += glassImpactBitCount(glassPieceAt(glassPieces, pieceIndex));
const auto useSparse = sparseBitCount <= fullBitCount;

message.MSG_WriteBits(1, 1);            // 有变化
message.MSG_WriteBits(useSparse ? 1 : 0, 1);
if (useSparse) {
    for (piece : changedPieces) { message.MSG_WriteBits(piece.pieceIndex, 11); writeGlassPiece(message, piece); }
    message.MSG_WriteBits(SvGlassPieceCount, 11);   // 终止哨兵
} else {
    message.MSG_WriteBits(prefixCount, 11);
    for (i < prefixCount) writeGlassPiece(message, glassPieceAt(glassPieces, i));
}
```

### 6.1 六层

```text
① 空前缀 ⇒ 一个 0 位（"无变化"）
② 否则 ⇒ 1 位 + 1 位 `useSparse`
③ **稀疏**：每个变化片 11 位索引 + 体，11 位 `SvGlassPieceCount` 终止
④ **稠密**：11 位 `prefixCount` + 每个 0..prefixCount 的体（无索引）
⑤ **两个位计数都在发之前算好**
⑥ **选更便宜的**
```

**✅ 一个**运行期的自适应编码**（本文件里唯一）。**

### 6.2 而**两个位计数的算术**

**⇒ 稀疏：**

```text
13 + Σ(13 + impactBits(piece))
= 13 + 13*N + Σ impactBits
```

**⇒ 第一个 13 是**头**（1 + 1 + 11 终止？）。**

**⚠ 让我核对：**

```text
头            1（有变化）+ 1（useSparse）= 2
每片          11（索引）+ 2（状态）+ [1 + 8 + 6 + 6]（impact）= 34 或 13
终止          11
```

**⇒ 所以：**

```text
2 + Σ(11 + 2 + impactBits) + 11
= 13 + Σ(13 + impactBits)    ✓
```

**✅ 因为 `11 + 2 = 13` ✓**

**⇒ 而稠密：**

```text
2 + 11（prefixCount）+ Σ(2 + impactBits)
= 13 + 2*prefixCount + Σ impactBits  ✓
```

**✅ 因为 `11 + 2 = 13` ✓**

**✅ **两个公式都对。**

### 6.3 而**`SvGlassPieceCount` 作为终止哨兵**

**⇒ 三层**：

```text
1. 稀疏模式没有显式计数
2. ⇒ **用 `SvGlassPieceCount`（1024）作哨兵**
3. ⇒ **而 1024 需要 11 位**（`2^11 = 2048`）
```

**✅ 与 §341 的"`SvGlassPieceCount = 1024`"**一致 ✓**

**⚠ 而 11 位能表达 `[0, 2047]` ⇒ **1024 是一个合法的"越界"值**。**

**✅ 一个**干净的哨兵**。**

### 6.4 而**两种模式的选择依据**

**⇒ 三层**：

```text
稀疏：N 个变化片，每片 13 位开销
稠密：prefixCount 个片，每片 2 位开销 + 11 位计数
⇒ 交叉点：13*N ≈ 11 + 2*P  ⇒ 当变化片很稀疏时 P >> N ⇒ 稠密更便宜
```

**✅ 逻辑正确。**

**⚠ 但**没有为"均匀分布"的情况优化**（那时两者接近）。**

**✅ 合理。**

## 七、`writeAnimationCommandSelector` 的**四级前缀码**

```cpp
void writeAnimationCommandSelector(MsgWriter &message, uint8 selector)
{
    if (selector <= 4)      { 1; (selector-1) 2位 }
    else if (selector <= 8) { 0; 1; (selector-5) 2位 }
    else if (selector <= 12){ 0; 0; 1; (selector-9) 2位 }
    else                    { 0; 0; 0; (selector-13) 2位 }
}
```

### 7.1 四层

```text
selector 1..4    1 + 2 = 3 位
selector 5..8    0 1 + 2 = 4 位
selector 9..12   0 0 1 + 2 = 5 位
selector 13..     0 0 0 + 2 = 5 位
```

**⚠ 而 selector 0 与 13+ 的编码？**

**⇒ `selector <= 4` ⇒ `selector - 1` 对 0 是 **-1**（在 uint8 下是 255）⇒ **2 位截断成 3**。**

**⚠ 所以 selector 0 是**未定义行为**（编码成 selector 4）。**

**⇒ 而 selector 13 与 16 都编码成 `0 0 0 (selector-13)` ⇒ 2 位只能表达 0..3。**

**⚠ 所以 selector 16 会**溢出**（`16-13 = 3` OK，而 17 是 4 ⇒ 2 位截断成 0）。**

**⇒ 所以**有效 selector ∈ [1, 16]**。**

**⚠ 一处**未声明的上界**。**

### 7.2 而**这是一个"一元前缀 + 2 位"码**

**✅ 与 §323 的 `writePlayerStateFieldIndex`（1 位若 delta==1 否则 4 位分块）**不同的前缀码**。**

**⇒ 而 §342 的 `writeEntityNumber`（连续 1 位 / 跳 2+11）**第四次**。**

### 7.3 而 `writeExplicitAnimationCommand` 的**"这两个 sticky 字段"**

```cpp
// CODREF(cl_parse_packet_anims): 0x671700/0x6717E0 retain entity and
// time across selectors. Both callers supply an already admitted
// command and alias table; explicitly restore both sticky fields.
message.MSG_WriteBits(0, 1); // explicit record, not baseline reuse
writeAnimationCommandSelector(message, 3);
message.MSG_WriteBits(command.entityNum, 11);
```

**⇒ 五层**：

```text
1. **`0x671700`/`0x6717E0` 在 selector 之间【保留】实体与时间**
2. ⇒ **两个 sticky 字段**
3. ⇒ **两个调用方都提供一个已准入的命令与别名表**
4. ⇒ **所以显式恢复两个 sticky 字段**
5. ⇒ `0` 位（显式记录）+ selector 3 + 11 位 entityNum
```

**✅ 与 §342 的"省略要有理由"同族（**sticky 字段必须显式恢复**）。**

**⚠ 而 selector **3** 是**一个固定的值**（可能意味着"SetGoalWeight 带显式实体"）。**

## 八、关键结论

1. **⭐ `0x400 → 0x800` 的"半个端口"** —— clip/ammo 界加宽到 `0x7FE`/`0x7FF` 而表留在 `0x400` ⇒ **1023 个 bool 越过栈数组**，实测索引 1188/1297。
2. **"一个加宽的界只是端口的一半；它索引的表是另一半"** —— 与 §318 的两条互补移植纪律。
3. **⭐ 七十五项合取却只有一个 `return reject`** —— "沉默的合取"成了**头号 frameReject**。
4. **"每一个限制都是关于【这个 build 的线】的断言 ⇒ 拒绝必须说哪一个限制以及什么值"**。
5. **`psDomain` / `psDomainValue` / `psDomainBad` 的三层** —— **只在不同时写日志**（`static std::string`）。
6. **七十五项按主题分成约二十组**。
7. **`radarFlags > 63`（6 位）与 `otherFlags > 0x7FFFFFFF`（31 位）—— 第二次确认 `-101`/`-102` 的宽度**。
8. **`EntityNumNone` 推为 2047**（11 位全一，配 §345 的 `EntityNumWorld = 2046`）。
9. **HUD 的 `foundFree` 是终止哨兵**（Free 之后一切必须零）。
10. **"材质类型与文本类型有不相交的要求"** —— `sub_BB5680` 需材质、`sub_BB4B70` 需字体缩放。
11. **"一个量化到零个六位十分位的文本元素是不可见的"** —— 第二次确认 `-86 = ReadBits(6)/10.0`。
12. **`materialIndex + 4355`（HUD）vs `4872`（材质带）—— 两个不同的基址**。
13. **`alignOrg` 的"成员类型本身就是界"**（`uint8_t` 已是 8 位）。
14. **`label` 的 `10 → 11` 位：写入器已改而界滞后** —— 与 clip 表的**相反方向**。
15. **⭐ 两条 3.3.3.3 的 flags 规则被实测推翻** —— `0x00BD7C4C`/`0x00BD8B12` **在本 build 里落在 `sub_BD7780`（`r_picmip`/`r_specular`）**。
16. **十八个 flags 值的完整分布**（`1`×9、`65536`×3、`65537`×2、`0`×2、`257`×1、`16384`×1）。
17. **"这两条条件拒掉了一个真实服务器所发内容的三分之一，包括它自己的 waypoint"**。
18. **`-85` 以五位携带 alpha ⇒ 低三位必须为零（32 级量化）而 `0xFF` 是例外**。
19. **HUD 与实体的坐标窗口等价**（有符号/无符号两种表述，都是 65536 个值）。
20. **⭐⭐ "这个 allowlist 是独立的：一个在这里缺失的 eType 不丢掉实体而是【拒掉整帧】"** —— **加一个 eType 要碰三处**。
21. **布告与 actor 两次独立漏掉这第三处** —— 布告那次靠"候选解释"，actor 那次靠 `entity_domain reject num=700 eType=19`。
22. **`eType = 19` 确认 `EntityTypeActor == 19`**（第二次，配 §344 的 `19→21`）。
23. **"`obituary ARCHIVED` 而屏幕上没有 feed"** —— 与 §344 的"归档不等于发出"合起来给出完整可观测链。
24. **`static std::set<uint32> reported`** ⇒ 每个实体号只报一次。
25. **offender 行的三十三个字段**（二十通用 + 十三 actor 专用）。
26. **玻璃的稀疏/稠密二选一** —— 运行期自适应编码，两个位计数公式 `13 + Σ(13+impact)` 与 `13 + 2P + Σ impact`。
27. **`SvGlassPieceCount = 1024` 作稀疏终止哨兵**（11 位能表达 2047 所以 1024 合法）。
28. **`writeAnimationCommandSelector` 的四级一元前缀码**（3/4/5/5 位），有效 selector ∈ [1,16] 而 0 与 17+ 是**未定义**。
29. **`0x671700`/`0x6717E0` 的"实体与时间跨 selector 保留"** —— sticky 字段必须显式恢复。

## 九、未闭合点

- `psDomainBad` 的 `static reported` 在多个客户端间的互相覆盖。
- `materialIndex + 4355` 与材质带 4872 的关系。
- `writeAnimationCommandSelector` 的 selector 0 与 17+ 是否有调用方。
- `EntityNumNone` 的确切值（推为 2047）。
- `HudElemFontScaleMaximum` 是否 == 6.3。
- `sv_snapshot_mp.cpp` 9998 行之后未读取（27,016 行，进度 37%）。
