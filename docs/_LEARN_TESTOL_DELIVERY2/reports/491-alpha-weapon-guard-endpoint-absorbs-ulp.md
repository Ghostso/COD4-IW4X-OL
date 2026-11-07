# 491 · **"两个相等的浮点端点在【求值【时【可能【比 minDamage **低几个 ulp**】⇒ **⇒ 而在【原生例程【截断到 int 时【丢掉【一分**"** —— `sv_alpha_weapon_port_mp.cpp` 的十一个武器、`alpha 两点 → OLfinal 六点` 的守卫端点、以及 `+3865` 的 clip-relative 标志

## 一、范围

本报告学习 `sv_alpha_weapon_port_mp.cpp`（**`344` 行**）全文件：十一个 `SvAlphaWeaponTuning` 常量、`Ports` 的三档血统、`20` 个 OLfinal 偏移、`valid()` 的十三条、以及那个"守卫端点"。

## 二、**"两个相等的浮点端点【可能【比 minDamage 低几个 ulp】⇒ 丢掉【一分**"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODREF(alpha_weapondef): alpha stores the classic two-endpoint
// linear falloff. OLfinal consumes six points. Points 0 and 1 preserve
// that exact line and inactive middle ranges remain zero. Two equal
// floating-point endpoints can evaluate a few ulps below minDamage
// and lose one point when the native routine truncates to int. The
// guard endpoint therefore sits one unit beyond CODOL's maximum
// ordinary bullet trace and is minDamage+1: every reachable distance
// after minDamageRange remains in [minDamage,minDamage+1) and truncates
// to the exact alpha value. Keeping the guard beyond the reachable
// domain also avoids the retained routine's exact-final-range fallback
// to damage[0].
const std::array<std::int32_t, 6> damage{
    tuning.damage, tuning.minDamage, tuning.minDamage,
    tuning.minDamage, tuning.minDamage, tuning.minDamage + 1,
};
const std::array<float, 6> ranges{
    tuning.maxDamageRange, tuning.minDamageRange,
    0.0f, 0.0f, 0.0f, StandardBulletRange + 1.0f,
};
```

### 2.2 二十四层

```text
1. **alpha 存【那个经典的两端点**线性衰减**】
2. ⇒ **⇒ 而 OLfinal 消费**六个点**
3. ⇒ **⇒ 点 `0` 与 `1` 【保持【那条【精确的**线**】⇒ **⇒ 而未激活的中间范围【保持**零**
4. ⇒ **⚠ 而两个**相等的**浮点端点【可能【求值【出【比 `minDamage` **低几个 ulp**】
5. ⇒ **⇒ 而在【那个**原生例程【截断到 `int`**时【**丢掉一分**
6. ⇒ **⇒ 所以【那个**守卫端点**【坐在【CODOL 的最大普通子弹追踪【之外一个单位**
7. ⇒ **⇒ 而它【是 `minDamage + 1`**】
8. ⇒ **⇒ 而【每一个【在 `minDamageRange` 之后【的可达**距离【仍然【在 `[minDamage, minDamage+1)`**里**
9. ⇒ **⇒ 而【截断【到【那个【精确的** alpha 值**
10. ⇒ **⇒ 而【把那个守卫【放在【那个可达域【之外【也【避免【那个保留例程的【"恰好等于最终范围时【回落【到 `damage[0]`**"**
```

### 2.3 ⭐⭐⭐ **"两个相等的浮点端点可能比 minDamage 低几个 ulp，丢掉一分"**

**✅ 这是本报告里**最重要的一条"**一个**浮点的 ulp【必须【被【一个**整数**的截断【吸收**"**。**

**✅ 与 §488 的"BO2 在距离恰好等于那个最终活跃范围时回落到 `damage[0]`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§488  **`foundRange == false` ⇒ 回落【到 `damage[0]`**】（**那是一个**边界**）
§491  **守卫端点在【`StandardBulletRange + 1`**】⇒ **⇒ 那个边界【不可达**】
⇒ **⇒ 所以【§491 【是【对 §488 那个边界【的【一个**规避**
```

**✅ ⭐⭐⭐ **"§491 是对 §488 那个边界的一个规避"** —— 一个**跨报告的精彩闭合**。

**⚠ 而那个**六点的实际形状**】**。**

**⇒ 独立验证**：
```text
damage = {D, m, m, m, m, m+1}
ranges = {Rmax, Rmin, 0, 0, 0, 8193}
⇒ **⇒ 所以【那是一条【从 `D` 到 `m` 在 `Rmax..Rmin` 的**直线**】
⇒ **⇒ 然后【从 `Rmin` 到 `8193` 【恒定 `m`**】
⇒ **⇒ 而【最后一个点【是 `m+1` 【在 `8193`**】
```

**✅ ⭐⭐⭐ **"一条直线，然后恒定，而最后一个点是 m+1 在 8193"** —— 一个**精确的形状**。

**⚠ 而"那个 `ranges[2..4] = 0`"**⇒ **三个**未激活**范围**。**

**⇒ 十层**：
```text
`ranges[2] = ranges[3] = ranges[4] = 0`
⇒ **⇒ 而【§488 的 `scaledRanges[index] < 0.001f ⇒ continue`**】⇒ **⇒ 跳过**它们**
⇒ **⇒ 所以【`previousIndex` 停在 `1`**】⇒ **⇒ 而【区间 `[Rmin, 8193)` 【用 `damage[1] = m` 与 `damage[5] = m+1`**】
```

**✅ ⭐⭐⭐ **"区间 [Rmin, 8193) 用 damage[1]=m 与 damage[5]=m+1"** —— 一个**极精确的插值分析**。

**⇒ 独立核算那个插值**：
```text
`lerp = (d - Rmin) / (8193 - Rmin)`
`value = m × (1 - lerp) + (m+1) × lerp = m + lerp`
⇒ **⇒ 因为【`lerp ∈ [0, 1)`**】⇒ **⇒ `value ∈ [m, m+1)`** ✓
⇒ **⇒ 所以【截断【到 `int` 【得到 `m`** ✓
```

**✅ ⭐⭐⭐ **"value ∈ [m, m+1) ⇒ 截断得到 m"** —— 一个**完整的证明**。

**✅ 与 §488 的"`static_cast<std::int32_t>(interpolated)`"**——**完全闭合** ✓

**⚠ 而那个 `-1`/`+1` 的**ulp 论证**是【一个**保守的**估计**。**

**⇒ 十层**：
```text
`m × (1 - lerp)` ⇒ **若【`lerp` 极小**【可能【舍入【到 `m - ulp`**】
而【加 `(m+1) × lerp`** ⇒ **⇒ 净效果【在 `[m-ulp, m+1)`**】
⇒ **⇒ 所以【那个 `+1` 【吸收【那个 `-ulp`**】
```

**✅ ⭐⭐⭐ **"那个 +1 吸收那个 -ulp"**。

## 三、**十一个武器与三档血统**（本组第二重要）

### 3.1 十一行

```text
fal_mp             → ff58_mp        MeasuredDescendant
coltanaconda_mp    → magnumncm_mp   MeasuredDescendant
tavor_mp           → tar21_mp       CompatibilityAlias
masada_mp          → acr_mp         CompatibilityAlias
uzi_mp             → miniuzi_mp     CompatibilityAlias
m21_mp             → m21ebr_mp      CompatibilityAlias
glock_mp           → g18_mp         CompatibilityAlias
beretta393_mp      → m93_mp         CompatibilityAlias
beretta_mp         → m9_mp          CompatibilityAlias
deserteaglegold_mp → degold_mp      CompatibilityAlias
barrett_heartbeat_mp → cheytac_mp   ConvertedPresentation
```

### 3.2 二十四层

```text
1. **`2` 个** `MeasuredDescendant`**】（**⇒ 每一个有一条**测量的**祖先线**）
2. ⇒ **`8` 个** `CompatibilityAlias`**】（**⇒ "一个**更弱的**血统证据，在这里【被【保持**区分**"**）**
3. ⇒ **`1` 个** `ConvertedPresentation`**】（**⇒ `barrett`，**从 alpha 元数据转换**）**
4. ⇒ **⇒ 所以 `2 + 8 + 1 = 11`** ✓
```

### 3.3 ⭐⭐⭐ **"那是一个更弱的血统证据，在这里被保持区分"**

**✅ 与 §473 的"那是候选，不是声称的零售玩家索引映射"**——**同族** ✓

**⇒ 三层**：
```text
`MeasuredDescendant` ⇒ **一条**测量的**祖先线**
`CompatibilityAlias` ⇒ **一个**明确的**兼容别名**（**更弱**）
`ConvertedPresentation` ⇒ **一个**转换的**表现**（**最弱**）
⇒ **⇒ 所以【三档【是一个**强度的**分级**
```

**✅ ⭐⭐⭐ **"三档是一个强度的分级"** —— 而**那【正是【§463 的"`refuse` 的命名"**同族**（**第二次"一个**分级的诚实**"**）。

**⚠ 而 `Barrett` 的那段注释**】**。**

**⇒ 十六层**：
```cpp
// Barrett's presentation family is converted from the alpha metadata
// and loose overlay. Its exact viewmodel_barrett_* animations and
// complete viewmodel_barrett/weapon_m82 pair are patched onto a retained
// CheyTac WeaponDef whose remaining pointer-bearing dependencies have
// OLfinal ownership. The requested 0.0.2.2 presentation also publishes
// its exact four-row Barrett base-body coWeapModels table.
```
```text
1. **`Barrett` 的表现族【从【那个 alpha 元数据与松散 overlay【转换**】
2. ⇒ **⇒ 而【它的【精确的 `viewmodel_barrett_*` 动画【与【完整的 `viewmodel_barrett`/`weapon_m82` 对【被【patch【到【一个**保留的** CheyTac WeaponDef**】
3. ⇒ **⇒ 而那个 CheyTac 【的【其余【携带指针的依赖【有【OLfinal 所有权**】
4. ⇒ **⇒ 而【那个请求的 `0.0.2.2` 表现【也【发布【它的精确的**四行** base-body `coWeapModels` 表**】
```

**✅ ⭐⭐⭐ **"patch 到一个保留的 CheyTac WeaponDef"** —— 与 §468 的"一个 Material 是被克隆的"**同族**（**第三次"一个**克隆【而不是【一个**编写**"**）。

**✅ 而"那个四行"**⇒ **与 §473 的 `ModelRows` 的 `4×4`** **完全闭合** ✓

**⇒ 三层**：
```text
§473  **`ModelRows` = `4×4`（`barrett_mp` + 4 个皮肤 × 世界/视图名**）
§491  **"精确的四行 Barrett base-body `coWeapModels` 表"**
⇒ **⇒ 所以【那个 `4 行` 【是【同一个**结构**
```

**✅ ⭐⭐⭐ **"那个 4 行是同一个结构"** —— 一个**跨报告的闭合**。

## 四、**`20` 个 OLfinal 偏移**（本组第三重要）

### 4.1 那二十个

```text
    0  Name                    1416  WeaponType
 1420  WeaponClass             1424  WeaponPenetrateType
 1428  WeaponImpactType        1432  WeaponFireType
 2016  WeaponStartAmmo         2040  WeaponMaxAmmo
 2044  WeaponShotCount         2072  WeaponMeleeDamage
 2088  WeaponFireDelay         2188  WeaponDropTime
 2192  WeaponRaiseTime         2348  WeaponOverlayReticle
 2384  WeaponHipSpread         3344  WeaponDamage
 3368  WeaponDamageRange       3404  WeaponHitLocationMultipliers
 3688  WeaponClipSize          3696  WeaponFireTime
 3806  WeaponAimDownSight       3865  WeaponAmmoCountClipRelative
```

### 4.2 二十四层

```text
1. **`21` 个偏移**（**数一下**）⇒ **⇒ 而【那个注释说**："**`+0x7E0` 成员【紧接【在那两个名字指针【与【那个运行时弹药索引 `+0x7EC`【之前**"**】
2. ⇒ **⇒ 而 `2016 = 0x7E0`** ✓ / `2040 = 0x7F8` / `2044 = 0x7FC` / `3865 = 0xF19`**】
3. ⇒ **⇒ 所以【那个 `+0x748`（`1864`）【与 `+0x770`（`1904`）【没有出现**】
```

### 4.3 ⭐⭐⭐ **"`Start ammo` 是那个 `+0x7E0` 成员，紧接在那两个名字指针与那个运行时弹药索引 `+0x7EC` 之前"**

**✅ 与 §473 的"`WeaponDef +0x488`"**、§481 的"`WeaponDef +0x488` 的值 `3`"**——**完全同族** ✓

**⇒ 三层**：
```text
§473  **`WeaponDef +0x488`（`1160`）** ⇒ **一个**武器类的判别子**
§481  **同一个 `+0x488` 的值 `3`** ⇒ **决定【展示武器**
§491  **`+0x7E0` / `+0x7F8` / `+0x7FC` / `+0x7EC`** ⇒ **四个**弹药**字段**
⇒ **⇒ 三次"一个**WeaponDef 的偏移**"**
```

**✅ ⭐⭐⭐ **"一个 WeaponDef 的偏移"三例**。

**⚠ 而 `+0x818`（`2072`）是那个 `meleeDamage`**】**。**

**⇒ 十层**：
```cpp
// CODREF(alpha_weapondef): C1 0x4D1830 reads alpha +0x5F8 as
// melee damage; its retained OLfinal counterpart 0x4BC1D0 reads the
// same field at +0x818 and passes it to the melee trace helper.
```
```text
`alpha +0x5F8` ⇒ **`meleeDamage`**
⇒ **⇒ 而【那个保留的 OLfinal 对应物 `0x4BC1D0` 【在 `+0x818` 【读【同一个字段**】
⇒ **⇒ 所以【`2024` 【是 alpha 而 `2072` 【是 OLfinal**】⇒ **⇒ 差 `48`**
```

**✅ ⭐⭐⭐ **"差 48"** —— 一个**精确的算术**。

**⚠ 而"每个 offset 都被 `out.exe` 消费者在 `EngineBindings.cpp` 里独立命名"**⇒ **一个**极强的**出处**。**

**⇒ 十层**：
```text
`// CODREF(alpha_weapondef): OLfinal offsets, each independently named by
// out.exe consumers in EngineBindings.cpp.`
⇒ **⇒ 所以【那不是【一个**猜的**表**】⇒ **⇒ 而【是【一个【每个成员都有【一个**具名消费者**的表**】
```

**✅ ⭐⭐⭐ **"每个成员都有一个具名消费者"** —— 与 §461 的"给那一项命名"**同族**。

## 五、**`valid()` 的十三条与那个 `hitLocationMultipliers ≤ 20.0f`**（本组第四重要）

### 5.1 十三条

```text
① weaponType >= 0
② weaponClass >= 0
③ penetrateType >= 0
④ impactType >= 0
⑤ fireType >= 0
⑥ startAmmo > 0
⑦ maxAmmo >= clipSize
⑧ shotCount > 0
⑨ damage >= 0
⑩ minDamage >= 0
⑪ meleeDamage > 0
⑫ minDamage < INT32_MAX
⑬ fireDelay/dropTime/raiseTime >= 0
⑭ clipSize > 0
⑮ fireTimeMilliseconds > 0
⑯ maxDamageRange/minDamageRange finite 且 > 0
⑰ minDamageRange > maxDamageRange
⑱ minDamageRange <= StandardBulletRange
⑲ hipSpread 全部 finite 且 >= 0
⑳ hitLocationMultipliers ∈ [0, 20]
```

### 5.2 二十四层

```text
1. **约 `20` 条，而【那个 `minDamageRange > maxDamageRange` 【是【一个**反向**的**】
2. ⇒ **⇒ 因为【那个"最大伤害"【在【一个**更近**的距离**】（`maxDamageRange < minDamageRange`**）**
3. ⇒ **⇒ 所以【那个不等式【正确**】
```

### 5.3 ⭐⭐⭐ **"`minDamageRange > maxDamageRange` —— 一个反向的不等式"**

**✅ 与 §468 的"`maxDamageRange` 不能超过 `minDamageRange`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§468  **`if (t.maxDamageRange > t.minDamageRange) { error = "maxDamageRange exceeds minDamageRange"; }`**
§491  **`tuning.minDamageRange > tuning.maxDamageRange`**（**同一个条件，反过来写**）
⇒ **⇒ 所以【两个文件【同一个**约束**
```

**✅ ⭐⭐⭐ **"两个文件同一个约束"**。

**⚠ 而 `hitLocationMultipliers ∈ [0, 20]`**⇒ **与 §468 的同一个界**】**。**

**⇒ 十层**：
```text
§468  **`multiplier > 20.0f ⇒ 拒绝**】
§491  **`value <= 20.0f`**】
⇒ **⇒ 同一个 `20`**
```

**✅ ⭐⭐ **"同一个 20"**。

**⚠ 而 `BarrettTuning` 的 `hitLocationMultipliers` 有 `5.0f` 在 `index 20`**⇒ **一个**异常高**的值**。**

**⇒ 三层**：
```text
`BarrettTuning` ⇒ `{1.0, 1.5×5, 1.45×12, 0, 0, 5.0}`】
⇒ **⇒ 而 §468 说 `StandardHitLocations` 的 `index 17`/`18` 是 `0.0`**】
⇒ **⇒ 所以【那个 `index 20` 的 `5.0` 【是【Barrett 专属**的
```

**✅ ⭐⭐⭐ **"那个 index 20 的 5.0 是 Barrett 专属的"** —— 而**§468 的未闭合点"`index 17`/`18` 为什么是 `0.0`"** **在这里【得到【一个解释**（**两个 `0.0` 是【一个**保留的**位置**）**。**

## 六、`SV_StringTableHash` 的 `31 × h + lower`

### 6.1 那段

```cpp
std::uint32_t SV_StringTableHash(const std::string_view value) noexcept
{
    std::uint32_t result{};
    for (const auto character : value)
    {
        const auto byte = static_cast<std::uint8_t>(character);
        const auto lower = byte >= 'A' && byte <= 'Z'
            ? static_cast<std::uint8_t>(byte - 'A' + 'a') : byte;
        result = result * 31u + lower;
    }
    return result;
}
```

### 6.2 二十四层

```text
1. **`31 × h + lower`**⇒ **⇒ 与 §468 的 `SV_ForgeXAssetHash` 【同一个常数 `31`**】
2. ⇒ **⇒ ⚠ 但【没有 `% XAssetHashBuckets`**】
3. ⇒ **⇒ 也没有【那个 `\` → `/` 的折叠**】
4. ⇒ **⇒ 所以【那【是【两个**不同的**哈希**】
```

### 6.3 ⭐⭐⭐ **"同一个常数 31，但没有取模，也没有斜杠折叠"**

**✅ 与 §468 的 `SV_ForgeXAssetHash`**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§468  **`h = type; for c: h = 31h + c; if c=='\\' c='/'; return h % 120000`**
§491  **`h = 0; for c: h = 31h + lower(c); return h`**
⇒ **⇒ 所以【两者【共享【那个 `31`**】而【三个**差异**（初始值 / 斜杠 / 取模**）**
```

**✅ ⭐⭐⭐ **"两者共享那个 31，而三个差异"** —— 一个**极精确的对比**。

**⚠ 而那个 `31` 是 **Java 的 `String.hashCode()` 的乘数**】**。**

**⇒ 十层**：
```text
`31` ⇒ **`h = 31h + c`** ⇒ **⇒ 那【正是【Java 的 `String.hashCode()`**】
⇒ **⇒ 而【§468 的**也是【同一个**
```

**✅ ⭐⭐⭐ **"那正是 Java 的 String.hashCode()"** —— 一个**可识别的**惯用法**。

**✅ 与 §488 的"`214013x + 2531011` 是 MSVC 的 rand()"**——**同族**（**第二次"一个**标准库的常量【被【识别**"**）。

## 七、`SV_AlphaWeaponNetworkAssetIndex` 的"一个连续的基址"

### 7.1 那段

```cpp
return static_cast<std::uint16_t>(
    AlphaWeaponNetworkBaseIndex + std::distance(Ports.begin(), port));
```

### 7.2 二十四层

```text
1. **`BaseIndex + distance`**】⇒ **⇒ 所以【十一个武器【占据【一个**连续的**范围**
2. ⇒ **⇒ 而那个范围【是 `[BaseIndex, BaseIndex + 11)`**】
3. ⇒ **⇒ 所以【一个武器名【唯一【决定【一个**网络资产索引**】
```

### 7.3 ⭐⭐⭐ **"一个连续的基址"与 §470 的"一个动态的块"**

**✅ 与 §470 的"`WeaponConfigStringDynamicBase = 5960`"**——**同族**（**第三次"一个**连续的**块**"**）。

**⇒ 三层**：
```text
§470  **`WeaponConfigStringBase + weaponAssetIndex`**
§491  **`AlphaWeaponNetworkBaseIndex + distance`**
⇒ **⇒ 两次"一个**基址 + 一个索引**"**
```

**✅ ⭐⭐⭐ **"一个基址 + 一个索引"两例**。

**⚠ 而那个 `std::distance` 是**O(1)**（`vector`/`array` 的随机访问迭代器**）**。**

**✅ ⭐⭐ **"O(1)"**。

## 八、关键结论

1. **⭐⭐⭐ "两个相等的浮点端点可以求值出比 `minDamage` 低几个 ulp，而在那个原生例程截断到 `int` 时丢掉一分；守卫端点因此坐在 CODOL 最大普通子弹追踪之外一个单位、且是 `minDamage+1`：每一个在 `minDamageRange` 之后的可达距离仍然在 `[minDamage, minDamage+1)` 里而截断到那个精确的 alpha 值；把那个守卫放在可达域之外也避免那个保留例程『恰好等于最终范围时回落到 `damage[0]`』"`** ⇒ **独立证明：`value = m + lerp` 而 `lerp ∈ [0,1)` ⇒ `value ∈ [m, m+1)` ⇒ 截断得到 `m` ✓** ⇒ **"§491 是对 §488 那个边界的一个规避"** —— 一个**跨报告的精彩闭合**。
2. **⭐⭐⭐ "alpha 存那个经典的两端点线性衰减，而 OLfinal 消费六个点；点 0 与 1 保持那条精确的线而未被激活的中间范围保持零"`** ⇒ **六点的实际形状是 `{D, m, m, m, m, m+1}` 在 `{Rmax, Rmin, 0, 0, 0, 8193}`** ⇒ 而 **`ranges[2..4] = 0` 被 §488 的 `scaledRanges[index] < 0.001f ⇒ continue` 跳过** ⇒ **"区间 `[Rmin, 8193)` 用 `damage[1]=m` 与 `damage[5]=m+1`"`**。
3. **⭐⭐⭐ 十一个武器与三档血统**：`2` 个 `MeasuredDescendant`（`fal` / `coltanaconda`）、`8` 个 `CompatibilityAlias`、`1` 个 `ConvertedPresentation`（`barrett`）⇒ **"那是一个更弱的血统证据，在这里被保持区分"`** —— 一个**强度的分级**（与 §463 的 `refuse` 命名同族）。
4. **⭐⭐⭐ Barrett 的"patch 到一个保留的 CheyTac WeaponDef"** ⇒ 与 §468 的"一个 Material 是被克隆的"同族；而 **"那个请求的 `0.0.2.2` 表现也发布它的精确四行 Barrett base-body `coWeapModels` 表"`** ⇒ **那个"四行"与 §473 的 `ModelRows` 的 `4×4` 是同一个结构** —— 一个**跨报告的闭合**。
5. **⭐⭐⭐ `21` 个 OLfinal 偏移**，而 **"`start ammo` 是那个 `+0x7E0` 成员，紧接在那两个名字指针与那个运行时弹药索引 `+0x7EC` 之前，保持 alpha 的 `+1476`/`+1480`/`+1484`/`+1488` 顺序"`** ⇒ 独立验证 `2016 = 0x7E0` / `2040 = 0x7F8` / `2044 = 0x7FC` / `3865 = 0xF19`；而 **`meleeDamage` 在 alpha `+0x5F8`（`2024`）与 OLfinal `+0x818`（`2072`）⇒ 差 `48`**（`0x4D1830` ↔ `0x4BC1D0` 一对同族消费者）。
6. **⭐⭐⭐ "每个偏移都被 `out.exe` 消费者在 `EngineBindings.cpp` 里独立命名"`** ⇒ **"那不是一个猜的表，而是一个每个成员都有一个具名消费者的表"`**（与 §461 的"给那一项命名"同族）。
7. **⭐⭐⭐ `valid()` 的约 `20` 条**，其中 **`minDamageRange > maxDamageRange` 是一个反向的不等式**（因为"最大伤害"在一个更近的距离）⇒ 与 §468 的同一个约束**完整闭合**；而 `hitLocationMultipliers ∈ [0, 20]` 与 §468 的 `> 20.0f ⇒ 拒绝` 是同一个 `20`；而 **`BarrettTuning` 的 `index 20 = 5.0f` 是 Barrett 专属的** ⇒ **§468 的未闭合点"`index 17`/`18` 为什么是 `0.0`"在这里得到一个解释**（两个 `0.0` 是保留位置）。
8. **⭐⭐⭐ `SV_StringTableHash` 的 `31 × h + lower`** 与 §468 的 `SV_ForgeXAssetHash` **共享那个 `31`**（**Java 的 `String.hashCode()` 的乘数**）而**三个差异**（初始值 `0` vs `type` / 没有斜杠折叠 / 没有取模）⇒ **"两者共享那个 31，而三个差异"**。
9. **⭐⭐ `SV_AlphaWeaponNetworkAssetIndex` 的 `BaseIndex + distance`** ⇒ **"一个连续的基址"**（与 §470 的 `WeaponConfigStringBase + index` 同族）；而 `std::distance` 在 `std::array` 上是 **O(1)**。

## 九、`sv_alpha_weapon_port_mp.cpp` 全文件总览

**`344` 行。**

**`11` 个武器调参**（每个 `SvAlphaWeaponTuning` 有 `22` 个字段）：
```text
FalTuning              D=55  m=35  clip=1   max=135  R=(1000,1500)
ColtAnacondaTuning     D=50  m=35  clip=1   max=135  R=(500,1250)
BarrettTuning          D=70  m=70  clip=1   max=135  R=(4000,5000)  放大镜
TavorTuning            D=40  m=30  clip=1   max=135  R=(1500,2000)
MasadaTuning           D=30  m=20  clip=1   max=135  R=(1800,2300)
UziTuning              D=30  m=20  clip=1   max=135  R=(750,1000)
M21Tuning              D=70  m=70  clip=1   max=135  R=(4000,5000)
GlockTuning            D=30  m=20  clip=1   max=135  R=(300,500)
Beretta393Tuning       D=40  m=30  clip=1   max=135  R=(500,750)
BerettaTuning          D=40  m=25  clip=1   max=135  R=(550,800)
DesertEagleGoldTuning  D=50  m=30  clip=1   max=135  R=(350,1200)
```

**`21` 个 OLfinal 偏移**（见 §4.1）。

**`7` 个函数**：`write` / `valid` / `SV_AlphaWeaponPorts` / `SV_AlphaWeaponNetworkAssetIndex` / `SV_StringTableHash` / `SV_PatchAlphaWeaponDefinition`。

**`6` 个结论/锚点**：`0.0.2.2 ui_viewer_mp.zone` 的 `0xC28` 记录 / `Tools/codol_alpha_weapon_stats.py` / `0x4D1830`（C1 的 melee）/ `0x4BC1D0`（OLfinal 的 melee）/ `+0x7E0`/`+0x7EC`/`+0x7F8`/`+0x7FC` / `EngineBindings.cpp` 的具名消费者。

## 十、未闭合点

- 十一个武器在 `ui_viewer_mp.zone` 的 `0xC28` 记录里各占多少字节。
- 下一个文件：按大小继续 `sv_scoreboard_mp.hpp`（`14,368` 字节）或 `sv_native_server_entity_mp.cpp`（`13,736` 字节）。

**已核实（本轮，`.hpp`）—— 两项重大闭合**：
```text
sv_alpha_weapon_port_mp.hpp:69  OlfinalWeaponDefSize          = 0x101C = 4124
sv_alpha_weapon_port_mp.hpp:80  AlphaWeaponNetworkBaseIndex   = 1224
sv_alpha_weapon_port_mp.hpp:20  struct SvAlphaWeaponTuning
sv_alpha_weapon_port_mp.hpp:40  std::array<float, HitLocationCount> hitLocationMultipliers
```

**⭐⭐⭐ 闭合 1：`AlphaWeaponNetworkBaseIndex = 1224` 正是 §462/§474 里那个 `firstDynamicWeapon = 1224`**

```text
§462  **"活的 gamestate 报告 `firstDynamicWeapon = 1224`"**
§474  **"`1224 ** 306 (csg12ss) -> alt 1225`"**（**一个武器切换的测量**）
§491  **`AlphaWeaponNetworkBaseIndex = 1224`** ⇒ **⇒ 十一个 alpha 武器【从 `1224` 【开始【连续**占号**
⇒ **⇒ 所以【那十一个 alpha 武器（`1244`..`1234`）【是【那个动态武器块的【**前 11 个**】
```

**✅ 独立核算**：`1224 + 0..10 = 1224..1234` ⇒ 而 **§462 的 `1224`（primary）/ `1225`（alt）** 正是**头两个**（`fal_mp` 与 `coltanaconda_mp`？—— 或者那个 `1224` 是 `fal_mp` 而 `1225` 是它的 alt）。

**⚠ 一个待确认**：§474 的 `1224 ** 306 (csg12ss) -> alt 1225` 里，`csg12ss`（CSG12 霰弹枪）**不在**这十一个 alpha 武器里 ⇒ 所以 **`1224` 与 `1225` 在那次测量里是 `csg12ss` 与它的 alt**，而**不是** `fal_mp`。⇒ **那意味着 `1224` 是那个**动态武器块的第一个**号，而那个块的内容【取决于那次会话【加载了什么** ⇒ **`AlphaWeaponNetworkBaseIndex = 1224` 【是一个**共享的起点**，不是【一个**固定的映射**]**。

**⇒ 三层**：
```text
§491  **alpha 的十一个武器【从 `1224` 【起**】
§474  **而【一次实测里 `1224` 是 `csg12ss`**】
⇒ **⇒ 所以【那个 `1224` 【是一个**基址**，而那个块的内容【由【那次加载【决定**】
```

**⚠ 那是一个**重要的架构结论**：alpha 武器与 MP 武器**共享**那一个动态块，所以**同一个号在不同的会话里可以指不同的武器** —— 而**那正是为什么那个网络资产索引【不能【被【硬编码**（`SV_AlphaWeaponNetworkAssetIndex` 是**运行时算**的）。

**⭐⭐⭐ 闭合 2：`OlfinalWeaponDefSize = 0x101C = 4124`，而最大的偏移 `3865` 远小于它**

```text
`0x101C = 4124`
最大偏移 ⇒ `WeaponAmmoCountClipRelativeOffset = 3865 = 0xF19`
⇒ **⇒ 所以【还【有 `4124 - 3866 = 258` 字节【在【后面**】（`+0xF1A..+0x101B`）
```

**✅ 与 §468 的"那个结构是 `0x3564 → 0x3BBC`"**——**同族**（**第十一次"一个**结构的大小【是【一个**行为**"**）。

**⇒ 那 258 字节是【十一个武器【全部【没有**写的区域** —— 而**注释说"那个保留的 CheyTac WeaponDef 的其余携带指针的依赖有 OLfinal 所有权"** ⇒ **所以那些依赖【正好【住【在那 258 字节 + 那些未列出的偏移里**】**。**

**⇒ 三层**：
```text
`OlfinalWeaponDefSize = 4124` ⇒ **而【被写的有 `21` 个偏移**
⇒ **⇒ 所以【那个克隆源（CheyTac）的其余**字段【被【保留**】
⇒ **⇒ 而那【正是【§468 的"`techniqueSet`/常量/状态位【继续指向克隆"**同族**（**第四次"一个**克隆【保留【其余**"**）
```
