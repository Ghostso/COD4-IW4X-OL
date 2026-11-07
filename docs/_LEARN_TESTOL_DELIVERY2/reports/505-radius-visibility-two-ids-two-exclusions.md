# 505 · **"`w 2 4 0` 两次**"** —— `sv_radius_visibility_mp.cpp` 的双层可见性、`splash` 的 `argv(2)`/`argv(3)` 顺序、以及"那个既有的 `passOwnerEntityNum` 策略【有意**不同**"**

## 一、范围

本报告学习 `sv_radius_visibility_mp.cpp`（**`2,576` 字节**）+ `sv_splash_mp.cpp`（**`485` 字节**）全文：`SV_TestRadiusDamageVisibility` 的两层（世界+静态模型 ⇒ 逐实体）、那个"两个 ID 与两个所有权排除"的 `excluded` lambda、以及 `w <slot> <row> <points>` 的参序。

## 二、**"测试两个实体 ID 与两个所有权排除；那个既有的 `passOwnerEntityNum` 策略有意有不同的语义"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODREF(Ghosts SV_PointSightTraceToEntity 14020ADE0..14020AE0E):
// test both entity IDs and both ownership exclusions. The existing
// passOwnerEntityNum policy deliberately has different semantics.
const auto excluded = [&](std::uint32_t number) {
    return number == request.targetClientNum ||
        request.inflictorEntityNum == number;
};
if (!entity.linked || !(entity.contents & request.contentMask) ||
    excluded(entity.entityNum) ||
    (entity.ownerEntityNum && excluded(*entity.ownerEntityNum)) ||
    !SV_ShouldBroadphaseClipToEntity(request.start, request.end, PointTraceBounds, entity))
    continue;
```

### 2.2 二十四层

```text
1. **测试【两个**实体 ID**（那个 `entity.entityNum` 与那个 `*entity.ownerEntityNum`**）**
2. ⇒ **⇒ 与【两个**所有权排除**（那个 `targetClientNum` 与那个 `inflictorEntityNum`**）**
3. ⇒ **⇒ ⚠ 而【"那个**既有的 `passOwnerEntityNum` 策略【有意【有【不同的**语义**"**
```

### 2.3 ⭐⭐⭐ **"那个既有的 passOwnerEntityNum 策略有意有不同的语义"**

**✅ 这是本报告里**最重要的一条"**两个**同名的参数【两个**不同的**语义**"**。**

**✅ 与 §476 的 `SV_ShouldClipToEntity` 的 `passEntityNum`/`passOwnerEntityNum`**——**一个极精确的对照** ✓

**⇒ 三层**：
```text
§476  **`SV_ShouldClipToEntity`：`!passEntityNum` ⇒ **全部接受**；`entity.entityNum == passEntityNum` ⇒ 拒绝；`*entity.ownerEntityNum == passEntityNum` ⇒ 拒绝；`== passOwnerEntityNum` ⇒ 拒绝**
§505  **`excluded(number) = (number == targetClientNum) || (inflictorEntityNum == number)`**（**⇒ 一个**对**的排除**）
⇒ **⇒ 所以【两个**"排除"【在两个**方向**上**（**那里【是"那个 `pass` 槽【与【那个**实体**"**，这里【是"那个**目标/施加者**"**）**
```

**✅ ⭐⭐⭐ **"两个『排除』在两个方向上"**。

**⚠ 而那个**不对称的来源**】**。**

**⇒ 十六层**：
```text
`excluded(entity.entityNum)` ⇒ **⇒ 那个**实体自己**被排除**】
`entity.ownerEntityNum && excluded(*entity.ownerEntityNum)` ⇒ **⇒ 那个**实体的所有者也【被排除**】
⇒ **⇒ 所以【一个**弹药**（**所有者【是【那个射手**）【也【被**排除**】
```

**✅ ⭐⭐⭐ **"一个弹药（所有者是那个射手）也被排除"** —— 而**那【正是【那个 §477 的"`passOwnerEntityNum` 排除兄弟而不是所有者"** **一个精确的对照**）**。**

**✅ 与 §477 的"`passOwnerEntityNum` excludes siblings, NOT the owner itself; passing the shooter also excludes its missile"**——**完全闭合** ✓

**⇒ 三层**：
```text
§477  **`filter={m.network.owner, nullopt}` ⇒ 排除那个射手【以及【它的投掷物**
§505  **`excluded(entity.entityNum)` 与 `excluded(*entity.ownerEntityNum)`** ⇒ **同一个效果**
⇒ **⇒ 两种**不同的实现**【一个**约定**、一个**显式**】**）**
```

**✅ ⭐⭐⭐ **"两种不同的实现：一个约定、一个显式"**。

## 三、那两层（世界 + 静态模型 ⇒ 逐实体）

### 3.1 两层

```cpp
const auto worldClear = worldAndStaticModels(request);
if (!worldClear || !*worldClear) return worldClear;
for (const auto &entity : entities) { ... entityTrace(request, entity) ... }
return true;
```

### 3.2 二十四层

```text
1. **第一层 ⇒ `worldAndStaticModels`**（**世界 + 静态模型**）
2. ⇒ **⇒ 若 `!worldClear`（**⇒ 那个跑者【缺席**）⇒ 返回 `nullopt`**
3. ⇒ **⇒ 若 `*worldClear == false`（**⇒ 被挡**）⇒ 返回 `false`**
4. ⇒ **⇒ 然后【第二层 ⇒ 逐实体**
5. ⇒ **⇒ 而【那【是一个**短路**的链**】（**⇒ 第一层挡了【就【不【查第二层**）
```

### 3.3 ⭐⭐⭐ **"第一层挡了就不查第二层 —— 一个短路链"**

**✅ 与 §504 的"有限 ⇒ 锥 ⇒ 视线"**——**完全同族** ✓

**⇒ 三层**：
```text
§504  **每个点：有限 ⇒ 锥 ⇒ `tracePassed`**
§505  **整体：世界 ⇒ 逐实体**
⇒ **⇒ 两次【一个**从便宜到贵**的链**】（**而【§504 在**一个点内**，§505 在**一层内**）
```

**✅ ⭐⭐⭐ **"一个从便宜到贵的链"两例**。

**⚠ 而"`return worldClear`" 的那个**返回值**】**。**

**⇒ 十层**：
```cpp
if (!worldClear || !*worldClear)
    return worldClear;
```
```text
1. **若 `!worldClear`（**缺席**）⇒ 返回【那个**空 optional**
2. ⇒ **⇒ 若 `*worldClear == false`（**被挡**）⇒ 返回【那个**装着 `false` 的 optional**
3. ⇒ **⇒ 所以【两层【不同的失败【一个**缺席**、一个**明确的** `false`**
```

**✅ ⭐⭐⭐ **"两层不同的失败：一个缺席、一个明确的 false"** —— 一个**极精确的**三态**。

**✅ 与 §503 的"缺席/失败/部分"**——**同族**（**第三次**）。

## 四、那个 `seen` 数组与 `MaximumServerCollisionEntityNum + 1`

### 4.1 那段

```cpp
if (!SV_IsRadiusDamageTraceRequestValid(request) ||
    entities.size() > MaximumServerCollisionEntityNum + 1 || !worldAndStaticModels)
    return std::nullopt;
std::array<bool, MaximumServerCollisionEntityNum + 1> seen{};
for (const auto &entity : entities)
{
    if (!SV_IsCollisionEntityValid(entity) || seen[entity.entityNum])
        return std::nullopt;
    seen[entity.entityNum] = true;
}
```

### 4.2 二十四层

```text
1. **`MaximumServerCollisionEntityNum + 1`（`2046`**）⇒ **⇒ 那个 `seen` 数组【的大小**
2. ⇒ **⇒ 而【那个 `entities.size() > 2046` ⇒ 拒绝**】（**⇒ 一个**上界**
3. ⇒ **⇒ 而【`seen[entity.entityNum]` ⇒ 一个**越界【是【不可能**的**】（**因为 `SV_IsCollisionEntityValid` 【保证 `entityNum <= 2045`**）
```

### 4.3 ⭐⭐⭐ **"seen[entity.entityNum] 的越界是不可能的，因为 SV_IsCollisionEntityValid 保证它"**

**✅ 与 §476 的 `MaximumServerCollisionEntityNum = 2045`**——**完全闭合** ✓

**⇒ 三层**：
```text
§476  **`entity.entityNum <= MaximumServerCollisionEntityNum`（`2045`）⇒ 拒绝**
§505  **`std::array<bool, 2046> seen`**
⇒ **⇒ 所以【那个 `2045` 【是【那个**最大的合法索引**】（**⇒ `2046` 个元素**）✓
```

**✅ ⭐⭐⭐ **"2045 是最大的合法索引，2046 个元素"** —— 一个**完整的算术闭合**（**§476 与 §505 一致**）。

**✅ 而 §489 的 `std::array<SvEntityLifetime, EntityNumWorld>`（`2046`）** **也【一致**】**。**

**⇒ 三层**：
```text
§489  **`std::array<SvEntityLifetime, EntityNumWorld> entities_`（`EntityNumWorld = 2046`**）
§505  **`std::array<bool, MaximumServerCollisionEntityNum + 1>`（`2046`**）
⇒ **⇒ 两个**数组【同一个大小，【由【两个**不同的**常量【推导**
```

**✅ ⭐⭐⭐ **"两个数组同一个大小，由两个不同的常量推导"** —— 一个**极妙的**观察**（**`EntityNumWorld` vs `MaximumServerCollisionEntityNum + 1`**，**两者【都是 `2046`**）**。**

**⚠ 一个**可报告的一致**：`EntityNumWorld = 2046` 与 `MaximumServerCollisionEntityNum + 1 = 2046` **是【同一个数，两个名字**】**。**

**✅ 与 §497 的"`28` 是同一个数两个用途（一个巧合）"**——**同族**（**第三次"一个**数字的巧合**"**）**。**

## 五、`w <slot> <row> <points>` 的参序

### 5.1 那段

```cpp
// Three arguments, in the order sub_C1C860 reads them: it takes argv(3)
// as the points and argv(2) as the row, and clamps the slot itself.
return "w " + std::to_string(slot) + " " + std::to_string(row) + " " +
    std::to_string(points);
```

### 5.2 二十四层

```text
1. **三个参数，按 `sub_C1C860` 读它们的顺序**】
2. ⇒ **⇒ `argv(3)` ⇒ 那个 `points`**】
3. ⇒ **⇒ `argv(2)` ⇒ 那个 `row`**】
4. ⇒ **⇒ 而【它【自己夹【那个 `slot`**】（`argv(1)`**）**
```

### 5.3 ⭐⭐⭐ **"它取 argv(3) 作为那个 points 而 argv(2) 作为那个 row，并自己夹那个 slot"**

**✅ 与 §474 的 `argv(1)`/`argv(2)` 的 `sub_C1C860` 命名**——**完全同族** ✓

**⇒ 三层**：
```text
§474  **`argv(3)` 与 `argv(2)`**（**一个**命令的参序**）
§505  **同一个 `sub_C1C860`**（**⇒ 同一个**1 基**的 argv**）
⇒ **⇒ 所以【那个 argv【是【1 基**的（**⇒ `argv(0)` 是那个**命令名**）**
```

**✅ ⭐⭐⭐ **"那个 argv 是 1 基的"** —— 与 §499 的"那个 `hitId` 是 1 基的"**同族**（**第二次"一个**1 基【的索引**"**）。

**⚠ 而"`w 2 4 0` 两次"**】**。**

**⇒ 十层**：
```text
`w 2 4 0` ⇒ **slot `2` / row `4` / points `0`**
⇒ **⇒ 而【§404 记过【"`w 2 4 0` 两次"**】
⇒ **⇒ 所以【那【是【一个**两次【出现**的命令**】（**⇒ 一个**幂等**或【一个**重放**
```

**✅ ⭐⭐⭐ **"那是一 个两次出现的命令"** —— 而**那个 `points = 0` 【意味着【那个**计分【归零**）**。**

**⚠ 而"`clamps the slot itself`"**⇒ **⇒ `slot` 被**校验【在【那个消费者【那**】**。**

**⇒ 三层**：
```text
生产者 ⇒ **不校验 `slot`**
消费者 ⇒ **夹它**
⇒ **⇒ 所以【一个**跨层的**契约**（**⇒ 而【那【与 §493 的"一条 trace 不是一个预定"**同族**）
```

**✅ ⭐⭐⭐ **"一个跨层的契约"**。

## 六、`sv_radius_visibility` 的五道 request 检查

### 6.1 五道

```text
① start 有限
② end 有限
③ contentMask 非零
④ targetClientNum < 18
⑤ inflictorEntityNum 缺失 或 < MaximumGameEntities
```

### 6.2 二十四层

```text
1. **五道，而【那个 `targetClientNum < 18`**】⇒ **⇒ 与 §504 的九条【里的【同一条**
2. ⇒ **⇒ 而那个 `inflictor` 是**可选**的（`!request.inflictorEntityNum ||`**）**
3. ⇒ **⇒ 所以【一个**无施加者【的**爆炸【也【合法**
```

### 6.3 ⭐⭐⭐ **"一个无施加者的爆炸也合法"**

**✅ 与 §504 的"`request.ignoreClientNum` 是 `optional`"**——**完全同族** ✓

**⇒ 三层**：
```text
§504  **`request.inflictorEntityNum` 与 `ignoreClientNum` 都是 `optional`**
§505  **`!request.inflictorEntityNum || *... < MaximumGameEntities`**
⇒ **⇒ 所以【两个**optional【的**语义**一致**（**⇒ 一个**世界事件【的**无施加者**
```

**✅ ⭐⭐⭐ **"一个世界事件的无施加者"**。

**⚠ 而"`entities.size() > MaximumServerCollisionEntityNum + 1` ⇒ 拒绝"**】**。**

**⇒ 十层**：
```text
那个数组【有 `2046` 个**元素**】⇒ **⇒ 所以【最多 `2046` 个实体**】
⇒ **⇒ 而 `> 2046` ⇒ 拒绝**
⇒ **⇒ 所以【那个界【是【那个**数组大小**
```

**✅ ⭐⭐⭐ **"那个界是那个数组大小"** —— 与 §498 的"那个界是一个类型的界"**同族**（**第十二次**）。

## 七、关键结论

1. **⭐⭐⭐ "测试两个实体 ID 与两个所有权排除。那个既有的 `passOwnerEntityNum` 策略**有意有不同的语义**"`** ⇒ **"两个『排除』在两个方向上"**（§476 那里是"那个 pass 槽与那个实体"，这里是"那个目标/施加者"）；而那个 `entity.ownerEntityNum && excluded(*entity.ownerEntityNum)` ⇒ **"一个弹药（所有者是那个射手）也被排除"** —— 与 §477 的"`passOwnerEntityNum` 排除兄弟而不是所有者"**一个精确的对照**（**同一个效果，两种实现：一个约定、一个显式**）。
2. **⭐⭐⭐ 那个两层的短路链**（`worldAndStaticModels` ⇒ 逐实体）与 §504 的"有限 ⇒ 锥 ⇒ 视线"**同族**；而 **`return worldClear` 让两层有不同的失败**（**一个缺席 `nullopt`、一个明确的 `false`**）⇒ **"两层不同的失败：一个缺席、一个明确的 false"**（与 §503 的三态同族）。
3. **⭐⭐⭐⭐ `std::array<bool, MaximumServerCollisionEntityNum + 1>`（`2046`）与 §489 的 `std::array<SvEntityLifetime, EntityNumWorld>`（`EntityNumWorld = 2046`）是同一个大小，由两个不同的常量推导** ⇒ **"两个数组同一个大小，由两个不同的常量推导"** —— 而 **那验证了 §476 的 `MaximumServerCollisionEntityNum = 2045` 是最大的合法索引**（`2046` 个元素）。
4. **⚠ 一个可报告的一致**：`EntityNumWorld = 2046` 与 `MaximumServerCollisionEntityNum + 1 = 2046` **是同一个数、两个名字**（与 §497 的"`28` 同一个数两个用途"同族）。
5. **⭐⭐⭐ `w <slot> <row> <points>` 的参序**：**"按 `sub_C1C860` 读它们的顺序：它取 `argv(3)` 作为那个 points 而 `argv(2)` 作为那个 row，并自己夹那个 slot"** ⇒ **"那个 argv 是 1 基的"**（与 §499 的"`hitId` 是 1 基的"同族）；而那个 **`w 2 4 0` 两次** 是一个**两次出现的命令**（§404 记过）。
6. **⭐⭐⭐ "clamps the slot itself"** ⇒ **"一个跨层的契约"**（生产者不校验，消费者夹它）—— 与 §493 的"一条 trace 不是一个预定"同族。
7. **⭐⭐ `sv_radius_visibility` 的五道 request 检查**，而 `inflictorEntityNum` 是**可选**的 ⇒ **"一个无施加者的爆炸也合法"**（与 §504 的 `optional` 同族）。
8. **⭐⭐ `entities.size() > MaximumServerCollisionEntityNum + 1 ⇒ 拒绝`** ⇒ **"那个界是那个数组大小"**（与 §498 的"那个界是一个类型的界"同族）。

## 八、`sv_radius_visibility_mp.cpp` + `sv_splash_mp.cpp` 全文件总览

**`2,576` + `485` 字节。**

**`2` 个函数**：`SV_IsRadiusDamageTraceRequestValid` / `SV_TestRadiusDamageVisibility` / `SV_BuildSplashCommand`。

**两层**：`worldAndStaticModels`（世界 + 静态模型）⇒ `entityTrace`（逐实体）。

**`1` 条命令**：`w <slot> <row> <points>`（`sub_C1C860`）。

**`2` 个反汇编锚点**：Ghosts `SV_PointSightTraceToEntity 14020ADE0..14020AE0E` / `sub_C1C860`。

**`1` 个测量**：`w 2 4 0` 两次（§404）。

## 九、未闭合点

- `MaxRadiusDamageTracesPerFrame`（`.hpp` 里可能有）。
- `w` 命令的 `slot`/`row` 语义。
- 下一个文件：`sv_grenade_detonation_mp.cpp`（`8,550`）+ `sv_grenade_explosion_mp.cpp`（`1,532`）。
