# 504 · **"那个横向向量【是**水平的、`15` 单位宽**；**不要【用【那个碰撞的半宽【或【一个站立的**高度常量【代替它**"** —— `sv_radius_damage_mp.cpp` 的 `5` 个可见性点、`3` 点即全暴露、以及"`24` 单位的向上偏移"

## 一、范围

本报告学习 `sv_radius_damage_mp.cpp`（**`7,955` 字节**）全文：`request` 的九条准入、`target` 的八条、`separation` 的**最近点**距离、`5` 个可见性点、`3/3` 的 exposure、以及 `+24` 的伤害方向。

## 二、**"那个横向向量是水平的、15 单位宽；不要用那个碰撞的半宽或一个站立的高度常量代替它"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODREF(CanDamage): center, lateral+ eye/feet, lateral- eye/feet.
// The lateral vector is horizontal and 15 units wide; do not use
// the collision half-width or a standing-height constant instead.
const Vector lateral{ -horizontal[1] * 15.0f,
    horizontal[0] * 15.0f, 0.0f };
std::array<Vector, 5> points{ midpoint, midpoint, midpoint, midpoint, midpoint };
for (std::size_t index = 1; index < points.size(); ++index)
{
    const auto sign = index < 3 ? 1.0f : -1.0f;
    for (std::size_t axis = 0; axis < 3; ++axis)
        points[index][axis] += sign * lateral[axis];
    points[index][2] += index % 2 ? halfHeight : -halfHeight;
}
```

### 2.2 二十四层

```text
1. **`5` 个点：`midpoint`（**中心**）+ 那个横向的**两边** × 那个**眼/脚**的高度**
2. ⇒ **⇒ 而【那个横向向量【是**水平的**，`15` 单位宽**
3. ⇒ **⇒ 而【它【是【从 `horizontal`（那个**从爆炸【到【玩家的水平方向**）旋转 `-90°`** 得到的**
4. ⇒ **⇒ ⚠ 而【"**不要【用【那个碰撞的半宽【或【一个站立的**高度常量【代替它**"**
```

### 2.3 ⭐⭐⭐ **"不要用那个碰撞的半宽或一个站立的高度常量代替它"**

**✅ 这是本报告里**最重要的一条**反诱惑纪律**。**

**✅ 与 §476 的"那个横向向量【来自【一次读"**、§467 的"那个 marker 是居中在那个盒子上的"**——**同族** ✓

**⇒ 三层**：
```text
可用的近似 ⇒ **那个**碰撞半宽**（一个**可得的**数**）
可用的近似 ⇒ **一个**站立的高度常量**（`60`？**）
正确的 ⇒ **一个**水平的 `15` 单位**（**⇒ 那个 `CanDamage` 的**真实**形状）
⇒ **⇒ 所以【后者【是【那个**必须**的**
```

**✅ ⭐⭐⭐ **"后者是那个必须的"** —— 而**注释【明确【点名了两个**诱惑**）**。**

**⚠ 而那个 `15` 与 `30`（**站立的宽**）的**关系**】**。**

**⇒ 十层**：
```text
那 `5` 个点【跨度 ⇒ `±15` ⇒ **一个 `30` 的宽**
⇒ **⇒ 而 §476 的 `StandingPlayerTraceBounds` 是 `70` 高 × `30` 宽**
⇒ **⇒ 所以【那个 `15` 【正是【`30 / 2`**】（**⇒ 一个**半宽**）**】⇒ **⇒ 而【那【是【那个**碰撞盒的半宽**
```

**⚠ 但【注释说**"**不要【用【那个碰撞的半宽**"** ⇒ **一个**表面矛盾**。】

**⇒ 十层**：
```text
注释 ⇒ **"do not use the collision half-width"**
而那个 `15` ⇒ **恰好【是【`30 / 2`**
⇒ **⇒ 所以【那个**禁止【的是**"**取那个**运行时的**碰撞半宽**"— **而【那个 `15` 【是一个**常量**（**`CanDamage` 自己的数**）
```

**✅ ⭐⭐⭐ **"那个禁止的是取那个运行时的碰撞半宽，而那个 15 是一个常量"** —— 一个**极精确的读法**。

**✅ 而**那【正是【那个**为什么**注释【强调（**因为【那个运行时的半宽【会【随那个**玩家尺寸**变（`playerSizeScale`）而**这个 `15` 【不**）**。**

**⇒ 三层**：
```text
`target.absoluteBounds.halfSize` ⇒ **一个**运行时的**数**】（**⇒ 随 `playerSizeScale` 变**）
`15.0f` ⇒ **一个**常量**】（**⇒ `CanDamage` 的**形状**）
⇒ **⇒ 所以【两者【在【一个**缩放**的玩家上【会**不同**
```

**✅ ⭐⭐⭐ **"两者在一个缩放的玩家上会不同"** —— 而**那【正是【§483 的 `playerSizeScale`** 的地方**）**。**

**✅ 与 §483 的"`PM_GetStandHeight = round(playerSizeScale × 60)`"**——**完全同族**（**第三次"一个**尺寸【的来源**"**）。

## 三、**`5` 个点与 `3` 点即全暴露**（本组第二重要）

### 3.1 那段

```cpp
// CODREF(CanDamage): three visible points already give full
// exposure. G_RadiusDamage truncates AFTER shield and cover scaling.
const auto exposure = std::min(1.0f, static_cast<float>(visible) / 3.0f);
const auto scaled = damage * (exposure * (1.0f - target.shieldProtection));
```

### 3.2 二十四层

```text
1. **`5` 个点，而【`3` 个**可见【就【给出**全暴露**】
2. ⇒ **⇒ 所以【那个 `min(1, visible / 3)` ⇒ `{0, 1/3, 2/3, 1, 1}`**
3. ⇒ **⇒ 而【那个**截断【在【shield 与 cover 的**缩放【之后**
```

### 3.3 ⭐⭐⭐ **"`G_RadiusDamage` 在那个 shield 与 cover 缩放之后才截断"**

**✅ 与 §491 的"那个守卫端点【吸收【那个 `-ulp`"**——**同族**（**第四次"一个**截断【的位置**"**）。

**⇒ 三层**：
```text
错误 ⇒ **先【截断【再**缩放**】⇒ **⇒ 一个**有损的**中间值**
正确 ⇒ **先【缩放【再**截断**】⇒ **⇒ 那个**精确**的结果
⇒ **⇒ 所以【那个顺序【是【一个**正确性** */
```

**✅ ⭐⭐⭐ **"那个顺序是正确性"** —— 与 §478 的"那个高度检查先"**同族**。

**⚠ 而那个**五个点的 `sign` 与 `index % 2`**】**。**

**⇒ 独立核算**：
```text
index 1 ⇒ `sign = +1`（`index < 3`），`index % 2 = 1` ⇒ `+halfHeight`
index 2 ⇒ `sign = +1`，`index % 2 = 0` ⇒ `-halfHeight`
index 3 ⇒ `sign = -1`，`index % 2 = 1` ⇒ `+halfHeight`
index 4 ⇒ `sign = -1`，`index % 2 = 0` ⇒ `-halfHeight`
⇒ **⇒ 所以【`+lateral/+eye`、`+lateral/-feet`、`-lateral/+eye`、`-lateral/-feet`** ✓
```

**✅ ⭐⭐⭐ **"四个角：+lat/+eye、+lat/-feet、-lat/+eye、-lat/-feet"** —— 一个**精确的枚举**。

**✅ 与 §476 的"`(h + 3) >> 2`"**——**不同**，但与 §504 六 的"那个 `separation` 的最近点"**同族**。

**⚠ 而那个 `halfHeight`**】**。**

**⇒ 十层**：
```text
`halfHeight = (eyePosition[2] - origin[2]) * 0.5f` ⇒ **⇒ 而从【§485 的"那个 `eyePosition` = `origin[2] + 60`**】
⇒ **⇒ 所以 `halfHeight = 60 × 0.5 = 30`**】⇒ **⇒ 而 `midpoint[2] = (origin + eye) / 2 = origin + 30`**
```

**✅ ⭐⭐⭐ **"halfHeight = 30 而 midpoint[2] = origin + 30"** —— 与 §485 的"那个 `eyePosition` 是 `origin + 60`"**完全闭合** ✓

**✅ 而"`midpoint` 与 `+halfHeight`/`-halfHeight`"**⇒ **`origin + 30 ± 30` ⇒ `origin` 与 `origin + 60`**】**。**

**⇒ 三层**：
```text
`midpoint + halfHeight` ⇒ **`origin + 60`**（**那个**眼**）
`midpoint - halfHeight` ⇒ **`origin`**（**那个**脚**）
⇒ **⇒ 所以【那个"眼/脚"【正是【`origin` 与 `origin + 60`** ✓
```

**✅ ⭐⭐⭐ **"眼/脚正是 origin 与 origin + 60"**。

## 四、**"那个 `separation` 是从爆炸到 `absBox` 的最近点"**（本组第三重要）

### 4.1 那段

```cpp
// CODREF(G_RadiusDamage): clamp radius to one, measure from the blast
// to the closest point of r.absBox, and exclude the exact outer edge.
const auto radius = std::max(1.0f, request.radius);
...
Vector separation{};
for (std::size_t axis = 0; axis < 3; ++axis)
    separation[axis] = std::max(0.0f,
        std::abs(request.origin[axis] - target.absoluteBounds.midpoint[axis]) -
        target.absoluteBounds.halfSize[axis]);
const auto distanceSquared = squaredLength(separation);
...
if (distanceSquared >= radiusSquared)
    continue;
```

### 4.2 二十四层

```text
1. **那个 `radius` 【被夹到**至少 `1`**】
2. ⇒ **⇒ 而【那个距离【是从**爆炸【到【那个 `absBox` 的**最近点**】
3. ⇒ **⇒ 而【那个"**恰好等于**那个外缘"【被**排除**】（`>=`**）
4. ⇒ **⇒ 而那个 `separation` 的公式【是【一个**每轴的最近点**：
      `max(0, |origin - midpoint| - halfSize)`
```

### 4.3 ⭐⭐⭐ **"每轴的最近点，而这个公式就是那个 AABB 距离的精确形式"**

**✅ 与 §476 的"`SV_ShouldBroadphaseClipToEntity` 的扫掠 AABB"**——**同族** ✓

**✅ 而"那个 `>=` 排除那个恰好等于外缘"** ⇒ **与 §488 的"距离恰好等于那个范围 ⇒ 回落"** **一个精确的对照**（**那里【包含**，这里【排除**）**。**

**⇒ 三层**：
```text
§488  **`distance == back` ⇒ 进【那个 `else`（**包含**）**
§504  **`distanceSquared >= radiusSquared` ⇒ `continue`（**排除**）**
⇒ **⇒ 所以【两个**边界【两个**方向**
```

**✅ ⭐⭐⭐ **"两个边界两个方向"**。

**⚠ 而"`radius = max(1, request.radius)`"**】**。**

**⇒ 十层**：
```text
`radius = max(1, request.radius)` ⇒ **⇒ 所以【一个 `0` 或【负的**半径【变成 `1`**】
⇒ **⇒ 而【那【是【一个**有意的**夹**（**⇒ 不是【一个**拒绝**）
```

**✅ ⭐⭐⭐ **"那是一个有意的夹，不是一个拒绝"** —— 而**注释【说**"**clamp radius to one**"**。**

**⚠ 而"那个 `outerDamage` 可以【为 `0`"**】**。**

**⇒ 三层**：
```text
`outerDamage >= 0` ⇒ **允许 `0`**
而【那个 `innerDamage` 也【`>= 0`**】⇒ **⇒ 所以【一个**纯外**的伤害【也【合法**
```

**✅ ⭐⭐ **"一个纯外的伤害也合法"**。

## 五、`+24` 的伤害方向

### 5.1 那段

```cpp
Vector direction{};
for (std::size_t axis = 0; axis < 3; ++axis)
    direction[axis] = target.origin[axis] - request.origin[axis];
direction[2] += 24.0f;
```

### 5.2 二十四层

```text
1. **那个方向 = `target.origin - origin`**】
2. ⇒ **⇒ 而【那个 `+24` 【是【那个**z**分量**】
3. ⇒ **⇒ 所以【那个方向【指向【那个**目标【腰以上**】（**`origin + 24`**）
```

### 5.3 ⭐⭐⭐ **"那个 +24 让那个方向指向目标腰以上"**

**✅ 与 §485 的"那个 `eyePosition = origin + 60`"**——**同族**（**第四次"一个**垂直的**偏移**"**）。

**⇒ 三层**：
```text
`+60` ⇒ **那个**眼**（§485**）
`+30` ⇒ **那个**中点**（§504 三**）
`+24` ⇒ **那个**伤害方向**（§504 五**）
⇒ **⇒ 所以【三个**不同的**高度【三个不同的**用途**
```

**✅ ⭐⭐⭐ **"三个不同的高度三个不同的用途"**。

**⚠ 而"那个 `24` 与 `origin`"**⇒ **一个**近**的偏移**。**

**⇒ 十层**：
```text
`origin + 24` ⇒ **在【那个**膝盖【到【腰**之间**
⇒ **⇒ 所以【那个**击退/受击方向【是【一个**中低的**方向**
```

**✅ ⭐⭐⭐ **"那个击退/受击方向是一个中低的方向"**。

**✅ 与 §477 的"那个 `damageFlags = 5`"**——**同族**。

## 六、那**九条 request 准入 + 八条 target 准入 + `cone` 的三条**

### 6.1 合计

```text
request（9）：origin 有限 / radius 有限 / innerDamage 有限且 [0, 2^31) / outerDamage 同 / contentMask 非零 / targets.size() <= 18 / inflictor < MaximumGameEntities / ignoreClientNum < 18
cone（3）：angleCos 有限且 [-1,1] / direction 有限 / angleCos != -1 ⇒ |direction|² ≈ 1
target（8）：clientNum < 18 / 不重复 / origin 有限 / eyePosition 有限 / midpoint 有限 / halfSize 有限且 >= 0 / shieldProtection 有限且 [0,1]
```

### 6.2 二十四层

```text
1. **约 `20` 条**】⇒ **⇒ 而【那个 `targets.size() <= MaximumGameClients`（`18`**）
2. ⇒ **⇒ 而【那个 `cone` 的第三道【是【有条件的**】（**`angleCos != -1` 才查**）
3. ⇒ **⇒ 所以【`-1` 【是【一个**禁用**的锥**
```

### 6.3 ⭐⭐⭐ **"`angleCos == -1` 是一个禁用的锥"**

**✅ 与 §467 的"`requiredMapAspectRatio = 0` ⇒ 不扩张"**、§479 的"`verticalWalkMinPlanar = 0` ⇒ 不生效"**——**完全同族** ✓

**⇒ 三层**：
```text
`angleCos = -1` ⇒ **⇒ 那个锥【被**禁用**】（**⇒ 一个**全向**的爆炸**）
`angleCos != -1` ⇒ **⇒ 那个锥【生效**
⇒ **⇒ 所以【`-1` 【是【那个**自然的**禁用值**】（**因为【`dot ∈ [-1, 1]` ⇒ `-1` 意味着【全向**））
```

**✅ ⭐⭐⭐ **"`-1` 是那个自然的禁用值（因为 dot ∈ [-1,1] ⇒ -1 意味着全向）"** —— 一个**极精巧的观察**。

**✅ 与 §475 的"零=禁用"**——**同族**（**第九次"一个**哨兵【的**禁用**"**，而**这个是 `-1` 而不是 `0`**）**。**

**⚠ 而"那个 `0.0001f` 的容差"**】**。**

**⇒ 十层**：
```text
`|squaredLength(direction) - 1| > 0.0001f ⇒ 拒绝`
⇒ **⇒ 所以【那个方向【必须【是一个**单位向量**】（**容差 `1e-4`**）
```

**✅ ⭐⭐⭐ **"那个方向必须是一个单位向量（容差 1e-4）"** —— 而**§488 的 `AxisTolerance = 0.002f`** **比它【松 `20` 倍**】**。**

**⇒ 三层**：
```text
§488  **`AxisTolerance = 0.002`**（**一个**基**的容差**）
§504  **`0.0001f`**（**一个**方向**的容差**）
⇒ **⇒ 所以【两个**不同的**容差**】⇒ **⇒ 而【后者【更**紧 `20` 倍**
```

**✅ ⭐⭐⭐ **"后者更紧 20 倍"**。

## 七、那 `5` 个点的 `visible` 累计与 `tracePassed` 的三态

### 7.1 那段

```cpp
if (!tracePassed)
    return std::nullopt;
const auto passed = tracePassed({ request.origin, point, target.clientNum, request.inflictorEntityNum, request.contentMask });
if (!passed)
    return std::nullopt;
visible += *passed ? 1u : 0u;
```

### 7.2 二十四层

```text
1. **`!tracePassed` ⇒ 拒绝**】（**⇒ 一个缺席的**跑者**）
2. ⇒ **⇒ `!passed` ⇒ 拒绝**】（**⇒ 一个**失败的**跑者**）
3. ⇒ **⇒ `*passed ? 1 : 0` ⇒ 一个**布尔**的**可见性**
4. ⇒ **⇒ 所以【三态**：缺席 ⇒ 拒绝 / 失败 ⇒ 拒绝 / `true`/`false` ⇒ 累计**
```

### 7.3 ⭐⭐⭐ **"缺席与失败都拒绝，而 true/false 累计 —— 三态"**

**✅ 与 §503 的"一个缺席/失败/部分的原生调用从不发布一个点"**——**完全同族** ✓

**⇒ 三层**：
```text
§503  **`!evaluate || !evaluate(...) || !isfinite` ⇒ 拒绝**
§504  **`!tracePassed || !tracePassed(...)` ⇒ 拒绝，而 `*passed` 累计**
⇒ **⇒ 两次【同一个**三态【的**跑者**"**
```

**✅ ⭐⭐⭐ **"同一个三态的跑者"两例**。

**⚠ 而"那个 `point` 的 `finiteVector` 检查【在【那个 `tracePassed` 之前**】**。**

**⇒ 十层**：
```cpp
for (const auto &point : points)
{
    if (!finiteVector(point))
        return std::nullopt;
    if (request.cone && ...) { ... }
    if (!tracePassed) return std::nullopt;
    ...
}
```
```text
1. **有限性【先查**】⇒ **⇒ 然后【那个锥**
2. ⇒ **⇒ 然后【那个 `tracePassed`**
3. ⇒ **⇒ 所以【那个顺序【是【"**有限 ⇒ 锥 ⇒ 视线**"**
```

**✅ ⭐⭐⭐ **"那个顺序是『有限 ⇒ 锥 ⇒ 视线』"** —— 而**那【是【一个**从便宜到贵**的顺序**（**⇒ 一个**短路**的优化**）**。**

**✅ 与 §478 的"那个高度检查先"**——**同族**（**第六次"一个**检查的顺序**"**）。

## 八、关键结论

1. **⭐⭐⭐ "那个横向向量是**水平的、`15` 单位宽**；**不要用那个碰撞的半宽或一个站立的高度常量代替它**"`** ⇒ **"后者是那个必须的"**；而 **那个 `15` 恰好是 `30 / 2`** ⇒ **"那个禁止的是取那个运行时的碰撞半宽，而那个 `15` 是一个常量"** —— 而**那【正是【§483 的 `playerSizeScale` 的地方**（**⇒ 两者【在【一个**缩放的**玩家上【会**不同**）**。
2. **⭐⭐⭐ `5` 个可见性点**（`midpoint` + 四个角）⇒ **独立验证 `index 1..4` 是 `+lat/+eye`、`+lat/-feet`、`-lat/+eye`、`-lat/-feet`** ✓；而 **`halfHeight = 30` 与 `midpoint[2] = origin + 30`** ⇒ **"眼/脚正是 origin 与 origin + 60"**（与 §485 的 `eyePosition = origin + 60` **完整闭合**）。
3. **⭐⭐⭐ "`3` 个可见点已经给出全暴露。`G_RadiusDamage` 在那个 shield 与 cover 缩放**之后**才截断"`** ⇒ **"那个顺序是正确性"**（与 §478 同族）—— 而 `exposure = min(1, visible/3)` 给出 `{0, 1/3, 2/3, 1, 1}`。
4. **⭐⭐⭐ "夹那个 radius 到至少 `1`，从爆炸量到 `r.absBox` 的**最近点**，并**排除那个恰好等于外缘**"`** ⇒ **每轴的 `max(0, |origin − midpoint| − halfSize)` 是一个精确的 AABB 距离**；而 **`>=` 排除那个外缘** 与 §488 的"距离恰好等于那个范围 ⇒ 落入插值"**一个精确的对照**（**那里包含，这里排除**）。
5. **⭐⭐⭐ "clamp radius to one" 是一个有意的夹，不是一个拒绝**；而 **`outerDamage >= 0` 允许 `0`** ⇒ **"一个纯外的伤害也合法"**。
6. **⭐⭐⭐ 那个 `+24` 的伤害方向**（`direction[2] += 24`）⇒ **"那个击退/受击方向是一个中低的方向"** —— 与 §485 的 `+60`（眼）、§504 三 的 `+30`（中点）构成 **"三个不同的高度三个不同的用途"**。
7. **⭐⭐⭐ `angleCos == -1` 是一个禁用的锥**（那个第三道检查**只在 `angleCos != -1` 时跑**）⇒ **"`-1` 是那个自然的禁用值（因为 `dot ∈ [-1,1]` ⇒ `-1` 意味着全向）"** —— 与 §467/§479 的"零=禁用"同族（**而这个是 `-1`**）；而那个 `0.0001f` 的方向容差比 §488 的 `AxisTolerance = 0.002` **紧 20 倍**。
8. **⭐⭐⭐ `tracePassed` 的三态**（缺席 ⇒ 拒绝 / 失败 ⇒ 拒绝 / `true`/`false` ⇒ 累计）与 §503 的 `evaluate` **完全同族**；而那个**检查顺序**（有限 ⇒ 锥 ⇒ 视线）是 **"从便宜到贵"**（与 §478 同族）。

## 九、`sv_radius_damage_mp.cpp` 全文件总览

**`7,955` 字节。**

**`1` 个函数**：`SV_ComputePlayerRadiusDamage`。

**`4` 个内部助手**：`finiteVector` / `squaredLength` / `normalize` / `Int32UpperExclusive`。

**`5` 个可见性点**：`midpoint` + 四个角（`±lateral × ±halfHeight`）。

**`8` 个反汇编锚点**：`G_RadiusDamage`（两处 CODREF）/ `CanDamage`（两处）/ `Vec3Normalize`。

**`20+` 条准入**（request 9 + cone 3 + target 8）。

## 十、未闭合点

- `MaximumGameEntities` 的值。
- `SvPlayerRadiusDamageResult` 的字段表（`.hpp`）。
- 那个 `normalize` 的"两个重合点保持零向量"的消费者。
- 下一个文件：`sv_radius_visibility_mp.cpp`（`2,576`）+ `sv_radius_damage_mp.hpp`（`4,047`）。
