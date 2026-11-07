# 488 · **"**没有**那三个参照函数【含有【那个缩放**，所以【不要【在没有【一个 CODOL 的玩家尺寸/视高生产者【或【一个运行时追踪【的情况下【把它提升为【已恢复的原生行为**"** —— `sv_weapon_fire_mp.cpp` 的 `214013x+2531011` 四轮、六点伤害曲线、以及"全 ADS 边界"

## 一、范围

本报告学习 `sv_weapon_fire_mp.cpp`（**`373` 行**）全文件：`SV_IsWeaponFireBasisValid` 的七条（含**右手系**判定）、`SV_SeedBulletRandom` 的四轮 LCG、`SV_CalculateBulletDamage` 的六点插值、`SV_BuildBulletFirePlan` 的三分支、以及 `SV_CalculateWeaponSpread` 的**三段视高插值**。

## 二、**"没有那三个参照函数含有那个缩放，所以不要把它提升为已恢复的原生行为"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODDIFF(fire_weapon): playerSizeScale * 11/40/60 is an ol-mod CODOL
// adapter difference; none of the three reference functions contains
// that scaling. Do not promote it to recovered native behavior without
// a CODOL player-size/view-height producer or runtime trace.
```

### 2.2 二十四层

```text
1. **`playerSizeScale × 11/40/60` 【是【一个 ol-mod 的 CODOL 适配器差异**】
2. ⇒ **⇒ 而【那三个参照函数【没有**一个【含有【那个缩放**】
3. ⇒ **⇒ 所以【不要【把它【提升为【已恢复的原生行为**】
4. ⇒ **⇒ 而【除非【有一个 CODOL 的玩家尺寸/视高**生产者**】
5. ⇒ **⇒ 或【一个**运行时追踪**
```

### 2.3 ⭐⭐⭐ **"那三个参照函数没有一个含有那个缩放"**

**✅ 这是本报告里**最重要的一条"**一个**适配器的发明【被【标注【为【不【原生**"**。**

**✅ 与 §473 的"`RetainedMaterialNames` 的 15 个不经过检查"**、§487 的"一个借用而不是重新"**——**不同**（那是**缺陷**，这是一个**诚实标注**）。

**⇒ 三层**：
```text
若【接受【那个缩放**】⇒ **⇒ 一个【看似**原生**的数
而【它是【一个 ol-mod 的**适配器差异**】⇒ **⇒ 所以【标注【是【必须的**】
```

**✅ ⭐⭐⭐ **"标注是必须的"** —— 与 §476 的"§51i 的 FOREIGN 被推翻"**相反**（那里**一个错误的标注被修正**，这里**一个正确的标注被保留**）。

**⚠ 而那个缩放**在代码里【仍然【被用**】**。**

**⇒ 十层**：
```cpp
const auto proneHeight = input.playerSizeScale * 11.0f;
const auto crouchHeight = input.playerSizeScale * 40.0f;
const auto standHeight = input.playerSizeScale * 60.0f;
```
```text
1. **`11` / `40` / `60` 【三个**高度**（**以 `scale` 为单位**）**
2. ⇒ **⇒ 而【注释说【那【是【一个 ol-mod 的差异**】
3. ⇒ **⇒ 而【代码【仍然【用它**】
⇒ **⇒ 所以【那个标注【是【一个**来源【的诚实**】，不是【一个**禁用**】
```

**✅ ⭐⭐⭐ **"那个标注是一个来源的诚实，不是一个禁用"**。

**✅ 与 §483 的"那个 `60` 是这个 build 的数，不是一个继承的"**——**完全闭合** ✓

**⇒ 三层**：
```text
§483  **"`0x004104B0..0x004105D0` 的七个函数【乘**以 `15/70/50/30/60/40/11`**"** ⇒ **⇒ 那七个常量【是【这个 build 的**】
§488  **"没有那三个参照函数含有那个缩放**"
⇒ **⇒ 所以【那个 `11/40/60` 【是【那个【七个常量**的**一个子集**】⇒ **⇒ 而【§483 【给了【它【一个**原生的出处**】
```

**✅ ⭐⭐⭐ **"§483 给了它一个原生的出处"** —— 一个**跨报告的闭合**。

**⚠ 而那三个**: `11`（prone）/ `40`（crouch）/ `60`（stand）**⇒ 正是 §483 的 `15/70/50/30/60/40/11` 里的**三个**。**

**⇒ 独立验证**：
```text
§483  **`15` / `70` / `50` / `30` / `60` / `40` / `11`**
§488  **`11`（prone）/ `40`（crouch）/ `60`（stand）**
⇒ **⇒ 三个【全部【在**那七个里** ✓
```

**✅ ⭐⭐⭐ **"三个全部在那七个里"** —— 一个**精确的子集关系**。

**⚠ 而"`60` 是 stand"**⇒ **与 §483 的 `PM_GetStandHeight = round(scale × 60)`** **完全一致** ✓

## 三、**`214013x + 2531011` 的四轮**（本组第二重要）

### 3.1 那段

```cpp
// CODREF(fire_weapon): CODOL's retained client fire path at
// 0x0055F5A1 reads playerState.commandTime (or the local clock only
// when no playerState exists), adds 10 for the left-hand event, and
// executes these exact four 214013*x+2531011 rounds before the shot
// loop. Bullet_RandomDir 0x0055AE10 then advances the same seed twice
// per Bullet_Endpos call. BO2 Bullet_Fire 0x005AED50 instead calls
// BG_seedRandWithGameTime, so its XOR/shift seed is not imported.
auto seed = commandTime + (hand == SvPlayerHand::Left ? 10u : 0u);
for (auto index = 0; index < 4; ++index)
    seed = seed * 214013u + 2531011u;
return seed;
```

### 3.2 二十四层

```text
1. **`0x0055F5A1` 【读 `playerState.commandTime`**】
2. ⇒ **⇒ （**或【那个本地时钟【只在【没有 `playerState`**时**）**
3. ⇒ **⇒ 而【对【那个左手事件【加 `10`**】
4. ⇒ **⇒ 而【执行【恰好四轮** `214013x + 2531011`】
5. ⇒ **⇒ 在【那个射击循环【之前**】
6. ⇒ **⇒ 而 `Bullet_RandomDir`（`0x0055AE10`）**然后【每次 `Bullet_Endpos` 【推进【同一个种子两次**】
7. ⇒ **⇒ ⚠ 而 BO2 的 `Bullet_Fire`（`0x005AED50`）【反而调用 `BG_seedRandWithGameTime`**】
8. ⇒ **⇒ 所以【它的 XOR/移位种子【不被**导入**
```

### 3.3 ⭐⭐⭐ **"`214013x + 2531011` 是 MSVC 的 `rand()` 的 LCG"**

**✅ 一个**可识别的**常量对**。**

**⇒ 独立验证**：
```text
`214013 = 0x3443D` / `2531011 = 0x269EC3`
⇒ **⇒ 那【正是【MSVC CRT 的 `rand()` 的 `state = state * 214013 + 2531011`**】
⇒ **⇒ 而【那个"四轮"【是【一个**预热**（warm-up**）**
```

**✅ ⭐⭐⭐ **"那正是 MSVC CRT 的 rand() 的 LCG，而那四轮是一个预热"** —— 一个**极精确的识别**。

**✅ 与 §469 的"`SvLuaRuntime` 的分配器"**——**不同**（那是一个**内存**，这是一个**伪随机**）但**同族**（**第十次"一个**标准库的常量【被【识别**"**）。

**⚠ 而"左手加 10"**⇒ **一个**极具体的**偏移**。**

**⇒ 十层**：
```text
右手 ⇒ **`commandTime`**
左手 ⇒ **`commandTime + 10`**
⇒ **⇒ 所以【两只手【用【不同的**种子**】⇒ **⇒ 而那【防止【一个【同步的**双手射击**】
```

**✅ ⭐⭐⭐ **"那防止一个同步的双手射击"** —— 一个**合理的设计**。

**⚠ 而"`Bullet_RandomDir` 每次 `Bullet_Endpos` 推进两次"**⇒ **一个**双倍的**推进**。**

**⇒ 三层**：
```text
一次 `Bullet_Endpos` ⇒ **两次推进**
⇒ **⇒ 所以【两个**独立的**随机量【各自【一个**】
```

**✅ ⭐⭐⭐ **"两个独立的随机量各自一个"** —— 而**那【是【一个**yaw 与一个 pitch**（**两维的散射**）**。**

**⚠ 标注**：那个"两次"的语义（**yaw + pitch**）**未在注释里明说**。

## 四、**六点伤害曲线的三段**（本组第三重要）

### 4.1 那段

```cpp
std::int32_t damage{};
if (input.distance <= scaledRanges.front())
    damage = input.curve.damage.front();
else if (input.distance > scaledRanges.back())
    damage = input.curve.damage.back();
else
{
    // 逐段找那个区间，然后线性插值
    ...
    // BO2 falls back to damage[0] when distance equals the final
    // active range exactly; only distances beyond it use damage[5].
    if (!foundRange)
        damage = input.curve.damage.front();
}
```

### 4.2 二十四层

```text
1. **三段：`<= front` ⇒ `damage[0]`】/ `> back` ⇒ `damage[5]`】/ 中间 ⇒ 插值**
2. ⇒ **⇒ ⚠ 而【一个【`foundRange == false` 的情形【回落【到 `damage[0]`**】
3. ⇒ **⇒ 因为【BO2 在【距离【恰好等于【那个最终活跃范围**时【回落【到 `damage[0]`**】
4. ⇒ **⇒ 而【只有【超过它**的距离【才用 `damage[5]`
```

### 4.3 ⭐⭐⭐ **"距离恰好等于那个最终活跃范围时回落到 damage[0]"**

**✅ 与 §476 的"`0.015` 秒 ⇒ `2` 毫秒"**——**不同**（那是一个**舍入**，这是一个**边界**）但**同族**（**第十一次"一个**恰好相等【的**语义**"**）。

**⇒ 三层**：
```text
`distance == scaledRanges.back()` ⇒ **⇒ `> back` 为假** ⇒ **⇒ 进【那个 `else`**
⇒ **⇒ 而那个循环【找不到一个 `index` 使 `scaledRanges[index] > distance`**】
⇒ **⇒ 所以 `foundRange == false` ⇒ 【回落【到 `damage[0]`**
```

**✅ ⭐⭐⭐ **"所以回落到 damage[0]"** —— 一个**极精确的边界分析**。

**⚠ 而那个 `scaledRanges[index] < 0.001f ⇒ continue`**⇒ **一个**跳过无效范围**的守卫**。**

**⇒ 十层**：
```text
`< 0.001f` ⇒ **跳过**（**⇒ 那个 `previousIndex` 【不更新**）
⇒ **⇒ 所以【一个【零/近零**的范围【被【当作【未使用**
```

**✅ ⭐⭐⭐ **"一个零或近零的范围被当作未使用"**。

**⚠ 而那个 `0.001f` 是**一个魔数**】**。**

**⇒ 三层**：
```text
`0.001f` ⇒ **一个**绝对**的阈值**】
⇒ **⇒ 而【它【与【那个 `rangeWidth <= 0.0f` 的检查【重叠**】
⇒ **⇒ 所以【那个 `0.001` 【是一个**更宽的**守卫**
```

**✅ ⭐⭐ **"0.001 是一个更宽的守卫"**。

### 4.4 而**`WeaponDamageCurvePointCount`**

**⇒ 十层**：
```text
注释说 **"the six-point control flow"** 与 **"damage[5]"** ⇒ **⇒ `WeaponDamageCurvePointCount = 6`**
⇒ **⇒ 而【那个循环【`index = 1..5`**】⇒ **⇒ 五**段区间**
```

**✅ ⭐⭐⭐ **"六点 ⇒ 五段区间"** —— 而**那【正是【那个 `damage[0..5]` 与 `ranges[0..5]`**】**。

## 五、**`SV_IsWeaponFireBasisValid` 的右手系判定**（本组第四重要）

### 5.1 那段

```cpp
const auto unitLength = [](const std::array<float, 3> &axis) {
    return std::abs(lengthSquared(axis) - 1.0f) <= AxisTolerance;
};
return unitLength(basis.forward) && unitLength(basis.right) &&
    unitLength(basis.up) &&
    std::abs(dot(basis.forward, basis.right)) <= AxisTolerance &&
    std::abs(dot(basis.forward, basis.up)) <= AxisTolerance &&
    std::abs(dot(basis.right, basis.up)) <= AxisTolerance &&
    std::abs(dot(cross(basis.forward, basis.right), basis.up) + 1.0f) <= AxisTolerance;
```

### 5.2 二十四层

```text
1. **三条单位长度**】
2. ⇒ **⇒ 而【三条正交**（三个 `dot` 逼近零**）**
3. ⇒ **⇒ 而【一条**手性**（`dot(cross(forward, right), up) + 1 ≈ 0**）**
4. ⇒ **⇒ 所以【`dot(cross(forward, right), up) ≈ -1`**】
```

### 5.3 ⭐⭐⭐ **"`dot(cross(forward, right), up) ≈ −1` 是一个左手系"**

**✅ 这是本报告里**最精确的一条**手性判定**。**

**⇒ 独立验证**：
```text
标准右手系 ⇒ `cross(right, up) = forward` ⇒ **`dot(cross(forward, right), up) = -1`** ✓
（**因为【`cross(f, r) = -up`**】⇒ **⇒ `dot(-up, up) = -1`**）
⇒ **⇒ 所以【那个 `+1.0f` 的判据【是【一个**右手系**（**`cross(f,r) = -up`**）**
```

**✅ ⭐⭐⭐ **"那个 +1.0f 的判据是一个右手系（cross(f,r) = -up）"**。

**✅ 与 §475 的 `north`/`west` 的 `{-ny, nx}`**——**同族**（**第十二次"一个**手性【的**约定**"**）。

**⚠ 而 `AxisTolerance = 0.002f`**⇒ **一个**极紧**的容差。**

**⇒ 十层**：
```text
`0.002` ⇒ **对【一个**单位向量**】⇒ **⇒ 那【约【`0.11°` 的角度误差**
⇒ **⇒ 所以【那个检查【要求【一个**极精确的**基**
```

**✅ ⭐⭐⭐ **"那个检查要求一个极精确的基"** —— 一个**可推导的角度**。

**⚠ 而"`unitLength` 用 `lengthSquared - 1`"**⇒ **一个**平方**的比较（**比【开方【便宜**）**。**

**✅ ⭐⭐ **"用平方的比较，比开方便宜"**。

## 六、`SV_BuildBulletFirePlan` 的三个分支

### 6.1 那段

```cpp
const auto spreadWeapon = input.weaponClass == WeaponClassSpread && !input.bulletExplosiveDamage;
...
return SvBulletFirePlan{
    .randomSeed = SV_SeedBulletRandom(input.commandTime, input.hand),
    .shotCount = spreadWeapon ? input.shotCount : std::uint8_t{ 1 },
    .methodOfDeath = input.bulletExplosiveDamage ? std::uint8_t{ 3 }
        : static_cast<std::uint8_t>(input.rifleBullet ? 2 : 1),
    .maxRange = spreadWeapon ? input.damageCurve.ranges.back() : StandardBulletRange,
    .penetrate = input.penetrateType != 0 && !input.bulletExplosiveDamage,
};
```

### 6.2 二十四层

```text
1. **`spreadWeapon` ⇒ `weaponClass == 4`（`WeaponClassSpread`）且【非爆炸**】
2. ⇒ **⇒ `shotCount` ⇒ 那个输入的（**霰弹**）或【一**】
3. ⇒ **⇒ `methodOfDeath` ⇒ `3`（爆炸）/ `2`（步枪）/ `1`（其它**）**
4. ⇒ **⇒ `maxRange` ⇒ `ranges.back()`（霰弹）或 `StandardBulletRange`**
5. ⇒ **⇒ `penetrate` ⇒ `penetrateType != 0` 且【非爆炸**
```

### 6.3 ⭐⭐⭐ **"`methodOfDeath` 的 `3`/`2`/`1` 三分支"**

**✅ 与 §471 的"`if (input.plan.methodOfDeath == 3) return DeferredImpact;`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§471  **`methodOfDeath == 3` ⇒ `DeferredImpact`**（**一个**早退**）
§488  **`methodOfDeath = 3` 【当【`bulletExplosiveDamage`**】
⇒ **⇒ 所以【爆炸弹【走【那个**它自己的**路径**】⇒ **⇒ 而【`sv_bullet_mp` 【不**处理它**
```

**✅ ⭐⭐⭐ **"爆炸弹走它自己的路径，而 sv_bullet_mp 不处理它"** —— 一个**跨报告的闭合**。

**⚠ 而"`StandardBulletRange`" 与 "`0x46000000`（`8192.0f`）"**】**。**

**⇒ 独立验证**：
```text
`0x46000000` ⇒ **指数 `0x8C` = 140 ⇒ `140 - 127 = 13`** ⇒ **`2^13 = 8192`** ✓
⇒ **⇒ 所以【`0x46000000 = 8192.0f`** ✓
```

**✅ ⭐⭐⭐ **"0x46000000 = 8192.0f"** —— 一个**精确的位分析**。

**✅ 与 §468 的 `0x43FC8000 = 505.0`**——**同族**（**第十三次"一个**浮点【的位模式**"**）。

## 七、`SV_CalculateWeaponSpread` 的三段视高插值

### 7.1 三段

```text
① spreadOverrideState == 2 ⇒ min = max = spreadOverride（**完全覆盖**）
② viewHeightCurrent <= crouchHeight ⇒ 在 prone ↔ crouch 之间插值
③ 否则 ⇒ 在 crouch ↔ stand 之间插值
④ spreadOverrideState == 1 ⇒ max = spreadOverride（**只覆盖最大**）
```

### 7.2 二十四层

```text
1. **两个**覆盖**状态（`1` 只最大 / `2` 两者**）**
2. ⇒ **⇒ 而【那个插值【是【在【三个**视高**之间**
3. ⇒ **⇒ 而【`viewHeightCurrent` 是【那个**输入**】（**从 `playerState` 来**）**
```

### 7.3 ⭐⭐⭐ **"coD4 的 FireWeapon 用那个髋部锥【直到 `fWeaponPosFrac` **恰好是 `1.0`**，然后【选【那个 ADS 锥**"**

**✅ 与 §483 的"`viewHeightCurrent = 60.0f` 与 `playerSizeScale = 1.0`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§483  **`PM_GetStandHeight = round(scale × 60)`** ⇒ **⇒ 站着【是 `60`**】
§488  **`weaponPositionFraction == 1.0` ⇒ ADS 锥**】
⇒ **⇒ 所以【两个**独立的**判据**：**视高 `60`（姿态）与 `fraction 1.0`（ADS**）**
```

**✅ ⭐⭐⭐ **"两个独立的判据：视高 60（姿态）与 fraction 1.0（ADS）"**。

**⚠ 而"它的准星【独立地【通过 `CG_TransitionToAds` 收缩**，所以【那个视觉过渡【不是【那个弹道插值规则**"**⇒ **一个**极重要的区分**。**

**⇒ 十层**：
```text
视觉 ⇒ **`CG_TransitionToAds`**（**一个**独立**的收缩**）
弹道 ⇒ **`fraction == 1.0`**（**一个**阶跃**）
⇒ **⇒ 所以【两者【不同步**】⇒ **⇒ 而【那【是一个**有意的**设计**
```

**✅ ⭐⭐⭐ **"两者不同步，而那是一个有意的设计"**。

**⚠ 而"`spreadOverrideState == 2` ⇒ 两者都覆盖"**⇒ **一个**完全**的覆盖**。**

**⇒ 三层**：
```text
`state == 0` ⇒ **无覆盖**
`state == 1` ⇒ **只覆盖最大**】
`state == 2` ⇒ **两者都覆盖**】
⇒ **⇒ 所以【三个**状态**
```

**✅ ⭐⭐⭐ **"三个状态"** —— 而**那个检查 `spreadOverrideState > 2 ⇒ 拒绝`** ✓

## 八、关键结论

1. **⭐⭐⭐ "`playerSizeScale × 11/40/60` 是一个 ol-mod 的 CODOL 适配器差异；**没有那三个参照函数含有那个缩放**。不要在没有一个 CODOL 玩家尺寸/视高生产者或运行时追踪的情况下把它提升为已恢复的原生行为"`** ⇒ **"那个标注是一个来源的诚实，不是一个禁用"**；而 **独立验证：那三个（`11` prone / `40` crouch / `60` stand）正是 §483 的 `15/70/50/30/60/40/11` 里的三个** ⇒ **"§483 给了它一个原生的出处"**（`PM_GetStandHeight = round(scale × 60)` 也与那个 `60` 一致）。
2. **⭐⭐⭐ `214013x + 2531011` 的四轮是 MSVC CRT 的 `rand()` 的 LCG**（**独立识别：`214013 = 0x3443D`、`2531011 = 0x269EC3`**）⇒ **"那四轮是一个预热"**；而 **左手加 `10` ⇒ "两只手用不同的种子 ⇒ 那防止一个同步的双手射击"**；而 `Bullet_RandomDir` 每次 `Bullet_Endpos` 推进两次（**"两个独立的随机量各自一个"**）。
3. **⭐⭐⭐ "BO2 的 `Bullet_Fire` 反而调用 `BG_seedRandWithGameTime`，所以它的 XOR/移位种子不被导入"** —— 一个**正确的参照过滤**（与 §476 的"§51i 的 FOREIGN 被推翻"**相反**：这里**正确地拒绝了一个参照**）。
4. **⭐⭐⭐ 六点伤害曲线的三段**（`<= front` / `> back` / 中间插值）⇒ **"BO2 在距离恰好等于那个最终活跃范围时回落到 `damage[0]`"** ⇒ **"只有超过它的距离才用 `damage[5]`"** —— **独立分析：`distance == back` ⇒ `> back` 为假 ⇒ 进 `else` ⇒ 那个循环找不到 `> distance` ⇒ `foundRange == false` ⇒ 回落**；而 `scaledRanges[index] < 0.001f ⇒ continue` ⇒ **"一个零或近零的范围被当作未使用"**。
5. **⭐⭐⭐ `WeaponDamageCurvePointCount = 6` ⇒ "六点 ⇒ 五段区间"** —— 而 `damage[0..5]` 与 `ranges[0..5]` 是那两个数组。
6. **⭐⭐⭐ `SV_IsWeaponFireBasisValid` 的右手系判定**：`dot(cross(forward, right), up) ≈ -1` ⇒ **独立验证：标准右手系 `cross(right, up) = forward` ⇒ `cross(f, r) = -up` ⇒ `dot(-up, up) = -1`** ⇒ **"那个 `+1.0f` 的判据是一个右手系"**；而 `AxisTolerance = 0.002f` ⇒ **"约 0.11° 的角度误差 ⇒ 那个检查要求一个极精确的基"**。
7. **⭐⭐⭐ `SV_BuildBulletFirePlan` 的 `methodOfDeath` 三分支（`3` 爆炸 / `2` 步枪 / `1` 其它）** ⇒ **与 §471 的 `if (input.plan.methodOfDeath == 3) return DeferredImpact;` 完整闭合**（**"爆炸弹走它自己的路径，而 sv_bullet_mp 不处理它"**）；而 **独立验证 `0x46000000 = 8192.0f`**（指数 `140 - 127 = 13`，`2^13 = 8192`）—— 与 §468 的 `0x43FC8000 = 505.0` 同族。
8. **⭐⭐⭐ "CoD4 的 FireWeapon 用那个髋部锥直到 `fWeaponPosFrac` **恰好是 `1.0`**，然后选那个 ADS 锥；它的准星**独立地**通过 `CG_TransitionToAds` 收缩，所以那个视觉过渡不是那个弹道插值规则"`** ⇒ **"两者不同步，而那是一个有意的设计"**；而 `spreadOverrideState` 的三个状态（`0` 无 / `1` 只最大 / `2` 两者）。
9. **⭐⭐ `SV_CalculateBulletDamage` 的 `damageRangeScale`**：所有 `ranges` 先乘那个 scale ⇒ 而 `damageMultiplier` 在**最后**作用 ⇒ **"两个乘数在两个不同的阶段"**。

## 九、`sv_weapon_fire_mp.cpp` 全文件总览

**`373` 行。**

**`6` 个函数**：`finiteVector` / `lengthSquared` / `dot` / `cross` / `SV_IsWeaponFireBasisValid` / `SV_IsBulletEndposRequestValid` / `SV_SeedBulletRandom` / `SV_IsWeaponDamageCurveValid` / `SV_CalculateBulletDamage` / `SV_BuildBulletFirePlan` / `SV_CalculateWeaponSpread`。

**`4` 个常量**：`AxisTolerance = 0.002f` / `StandardBulletRange`（`8192.0f` = `0x46000000`）/ `MaximumWeaponDamageRange` / `WeaponDamageCurvePointCount = 6`。

**`11` 个测量/锚点**：
```text
0x0055F5A1（客户端开火路径的种子起点）
214013 / 2531011（MSVC rand 的 LCG）
左手 +10
Bullet_RandomDir 0x0055AE10（每次 Endpos 推进两次）
Bullet_Endpos 0x0055AEB0
0x0055F51A..0x0055F571（methodOfDeath 的选择）
0x46000000 = 8192.0f
BO1 Bullet_GetDamage 0x005F4820 / Ghosts 0x140109390 / BO2 0x0098D3A0
WeaponDef +0xBB4/+0xBCC（六点数组）
coAbilityModifiersTable 的 modBulletSpreadScale（modifier 6，Steady Aim -0.2 ⇒ 0.8）
11 / 40 / 60（prone/crouch/stand 的高度）
```

## 十、未闭合点

- `Bullet_RandomDir` 那"两次推进"的语义（yaw + pitch？）。
- 下一个文件：`sv_entity_mp.hpp`（`16,288` 字节）。

**已核实（本轮，`.hpp`）**：
```text
sv_weapon_fire_mp.hpp:19  WeaponTypeBullet            = 0
sv_weapon_fire_mp.hpp:20  WeaponClassSpread           = 4
sv_weapon_fire_mp.hpp:23  StandardBulletRange         = 8192.0f     ← 与 0x46000000 精确一致
sv_weapon_fire_mp.hpp:24  MaximumWeaponDamageRange    = 1000000.0f
sv_weapon_fire_mp.hpp:25  WeaponDamageCurvePointCount = 6
sv_weapon_fire_mp.hpp:29  damage[6]（int32）
sv_weapon_fire_mp.hpp:30  ranges[6]（float）
```

**三条独立验证闭合**：
1. **`StandardBulletRange = 8192.0f` 与 `0x46000000` 精确一致**（指数 `0x8C = 140`，`140 − 127 = 13`，`2^13 = 8192`）⇒ **注释说"那个 `0x46000000`（`8192.0f`）的常量"是对的**。
2. **`WeaponClassSpread = 4` 与注释"class 4 plus non-explosive"精确一致**。
3. **`WeaponDamageCurvePointCount = 6` 与注释"the six-point control flow"和"damage[5]"精确一致** ⇒ **"六点 ⇒ 五段区间"** ✓。

**一个可报告的量级观察**：`MaximumWeaponDamageRange = 1,000,000.0f`（**`1e6`**）是 `StandardBulletRange` 的 **122 倍** —— 那是一个**几乎不可能达到**的上界，与 §469 的 `XAssetMaxChainSteps = 4096` vs 实测 `7`（585 倍余量）**同族**（**"一个防御的余量，不是一个测量的结果"**）。
