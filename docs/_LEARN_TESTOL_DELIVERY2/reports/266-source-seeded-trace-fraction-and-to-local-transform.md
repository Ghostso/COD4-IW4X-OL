# 266 · `result.fraction` 必须**预置**、`toLocal` 的转置变换、`walkable = normal.z >= 0.7`

## 一、范围

本报告学习 `EngineBindings.cpp` 17850–18050 行。

## 二、`traceServerLocationalEntities` 的三项前置

```cpp
if (!dobjTraceline_ || !angleVectors_ || priorityMap.empty()) return false;
```

```text
dobjTraceline_ 已绑定
angleVectors_  已绑定
priorityMap 非空
```

### 2.1 而 `priorityMap` 的类型

**`std::span<const std::uint8_t>`** —— 所以是每个骨骼/部件一个优先级字节。

### 2.2 四个计数器

```cpp
uint32 considered{}, traced{}, improved{};
const auto entryFraction = aggregate.fraction;
```

**⇒ 三个计数 + 一个入口快照。**

## 三、**每实体的五个过滤**（本组第二重要）

```cpp
for (const auto &entity : entities)
{
    if (entity.shape != SvCollisionShape::Capsule &&
        entity.shape != SvCollisionShape::ScriptModelDObj) continue;      // ① 形状
    if (aggregate.fraction == 0.0f) break;                                // ② 已打中
    if (!SV_ShouldClipToEntity(entity, request.filter, request.contentMask) ||
        !SV_ShouldBroadphaseClipToEntity(request.start, request.end, PointTraceBounds, entity))
        continue;                                                          // ③ 过滤 + 宽相
    ++considered;
    auto *const dobj = serverDObjGetAdapter(entity.entityNum);
    if (!dobj) { ... ④ DObj 不可用 ... }
    ...
}
```

### 3.1 ① **只处理 Capsule 与 ScriptModelDObj**

**⇒ **跳过** BrushModel！**

**⇒ 而 §265 的 `traceServerCapsule` 处理 BrushModel 与 Capsule，跳过 ScriptModelDObj。**

**⇒ 两个函数的分工**：

```text
traceServerCapsule               BrushModel + Capsule，跳过 ScriptModelDObj
traceServerLocationalEntities    Capsule + ScriptModelDObj，跳过 BrushModel
```

**⇒ **只有 Capsule 被两者都处理**。**

**⇒ 而 BrushModel 走几何，ScriptModelDObj 走 DObj 骨骼。**

### 3.2 ② **`break` 而不是 `continue`**

```cpp
if (aggregate.fraction == 0.0f) break;
```

**⇒ 已经打到 0（最近可能）⇒ 停止全部。**

**⇒ 而 §265 里同样的检查在**循环末尾**（`if (aggregate->fraction == 0.0f) break;`）。**

**⇒ 两处位置不同：一个在开头，一个在末尾。**

**⇒ 语义相同但**开头**更早退出。**

### 3.3 ③ `SV_ShouldBroadphaseClipToEntity` 用 **`PointTraceBounds`**

**⇒ 一个固定的"点"边界** —— 而不是调用者的 `bounds`。

**⇒ 因为这是"定位点 trace"（point trace），所以起点/终点是点。**

## 四、**DObj 不可用时的 Actor 回退**

```php
if (!dobj)
{
    // This retail image retains actor presentation but lacks the
    // native SP actor/DObj server setup present in earlier CODOL
    // builds. Keep the authored actor body in the bullet path so
    // campaign enemies can take damage and release their finite
    // agent slots while that native setup remains unavailable.
    if (entity.bodyRole != SvCollisionBodyRole::Actor) continue;
    const auto actorTrace = traceTransformedCapsule(
        aggregate, request.start, request.end, PointTraceBounds, entity);
    if (!actorTrace) return false;
    ++traced;
    if (SV_ApplyEntityTraceHit(aggregate, *actorTrace, entity)) ++improved;
    continue;
}
```

### 4.1 三层

```text
1. 这个零售镜像保留了 actor 的【表现】但缺少原生 SP actor/DObj 服务端设置
2. ⇒ 把编好的 actor 身体留在子弹路径里
3. ⇒ 这样战役敌人能受伤并释放它们有限的 agent 槽
```

### 4.2 而"agent 槽"的语义

**`while that native setup remains unavailable`** —— 所以这是一个**降级**。

**⇒ 剧情模式的敌人有有限的 `agent` 槽** —— 如果他们不能死，槽就不会释放。

**⇒ 所以这个回退是**功能必需**的**（否则战役会卡住）。

### 4.3 而 `bodyRole != Actor` ⇒ `continue`

**⇒ 只有 actor 有回退。**

**⇒ 玩家没有 DObj 时**不**回退** —— 因为玩家应该有 DObj。

## 五、**`result.fraction` 必须预置**（本组最重要的一段）

```php
NativeDObjTraceResult result{};
// SEED IT. The engine's own caller loads the running best fraction
// into this field before the call (0x0046E1FC), so leaving it zero
// asks the traceline to beat zero and it never reports a hit.
result.fraction = aggregate.fraction;
if (!invokeDObjTraceline(dobjTraceline_, dobj, toLocal(request.start), toLocal(request.end),
        priorityMap.data(), result, &exceptionDetails))
{
    return false;
}
```

### 5.1 三层

```text
1. 引擎自己的调用者（0x0046E1FC）在调用前把【当前最佳 fraction】装进这个字段
2. ⇒ 留零意味着要求 traceline 打败零
3. ⇒ 它【永远不会报一个命中】
```

### 5.2 这是一个**极隐蔽**的缺陷模式

**`NativeDObjTraceResult result{};` 是零初始化。**

**⇒ `result.fraction = 0.0f`。**

**⇒ 而 traceline 的判据是 `result.fraction < 当前值` ⇒ 永远不成立（因为没有 fraction < 0）。**

**⇒ 所以"零初始化 + 正确调用"= **永远无命中**。**

### 5.3 而这条注释明确写出了"引擎自己怎么做"

**⇒ 所以修法是**模仿引擎的调用者**，而不是"猜测"。**

**⇒ 这是"读调用点而不是读被调方"的一个好例子** —— 因为契约藏在调用者的准备里。

### 5.4 与 §264 的 `encodeTraceResult(initialTrace)` 同族

**⇒ 那里也是"必须传初始值"。**

**⇒ 两个 trace 变体都需要"初始 best fraction"。**

## 六、`toLocal` 的**转置变换**（本组第三重要）

```php
// AnglesToAxis then `local = axis * (world - origin)`, which is
// what 0x0062C1A0 plus 0x0062A4A0 compute on the A side: the
// orientation there is a 4x3, nine floats of axis followed by the
// entity origin, and the transform is the transpose applied to the
// offset point.
std::array<float, 9> axis{};
invokeAngleVectors(angleVectors_, entity.angles, axis, &exceptionDetails);

const auto toLocal = [&axis, &entity](const std::array<float,3> &world) {
    const std::array<float, 3> offset{
        world[0] - entity.origin[0],
        world[1] - entity.origin[1],
        world[2] - entity.origin[2],
    };
    std::array<float, 3> local{};
    for (std::size_t row{}; row != local.size(); ++row)
    {
        local[row] = offset[0] * axis[row * 3] +
            offset[1] * axis[row * 3 + 1] +
            offset[2] * axis[row * 3 + 2];
    }
    return local;
};
```

### 6.1 `axis` 是 **3×3**（九个浮点）

### 6.2 而变换是 **`offset · axis[row]`**

```text
local[row] = offset[0]*axis[row*3] + offset[1]*axis[row*3+1] + offset[2]*axis[row*3+2]
```

**⇒ 这是 `axis^T · offset`（转置乘法）。**

**⇒ 因为 `axis` 存的是**行**（`axis[row*3 + col]`），而 `local = axis^T · offset` 意味着 `local[row] = Σ_col axis[col][row] * offset[col]`。**

**⚠ 而代码写的是 `offset[0]*axis[row*3] + offset[1]*axis[row*3+1] + offset[2]*axis[row*3+2]`**

**⇒ 即 `local[row] = Σ_c offset[c] * axis[row*3+c]`**

**⇒ 这是 `axis · offset`（正常乘法）而不是 `axis^T · offset`。**

### 6.3 **所以注释说"转置"而代码是正常乘法**

**⚠ 如果 `axis` 存的是**列**（`axis[col*3+row]`），那 `axis · offset` 就是正确的。**

**⇒ 取决于 `invokeAngleVectors` 的输出布局。**

**⇒ 而 `AngleVectors(angles, forward, right, up)` 的标准形式是三个输出向量。**

**⇒ 但这里 `axis` 是九个浮点的连续数组 ⇒ 可能是 `{forward[3], right[3], up[3]}` 或 `{axis[0][3], axis[1][3], axis[2][3]}`。**

**⇒ 无法从这段单独确定** —— 而注释说"转置"，代码看起来是正常乘法。**

**⇒ 这是一个**潜在的正确性问题** —— 值得标记。**

### 6.4 而 §164 学过的 "wrong function + reversed args = three zero vectors"

**记忆**："`AnglesToQuaternion` vs `AngleVectors`（wrong function + reversed args = three zero vectors）"

**⇒ 所以此前在这个项目里 `AngleVectors` 被误用过。**

**⇒ 而这里有 `invokeAngleVectors` 包装 + `isfinite` 检查 ⇒ **三个零向量会通过 `isfinite`**。**

**⇒ 所以"三个零向量"仍然可能通过检查，只是会让所有 `toLocal` 返回零。**

**⇒ 这会让所有 trace 在模型空间的原点。**

**⇒ 一个可能的失效模式。**

### 6.5 而 §265 的 `basis` 旋转回法线的代码

```php
aggregate.normal[component] =
    result.normal[0] * axis[component] +
    result.normal[1] * axis[3 + component] +
    result.normal[2] * axis[6 + component];
```

**⇒ 这是 `axis · normal` 的**列**形式**（`axis[0][component] * n[0] + axis[1][component] * n[1] + axis[2][component] * n[2]`）。**

**⚠ 而 `toLocal` 用的是 `axis[row*3+c] * offset[c]`。**

**⇒ 两处用了**不同的**索引模式：**

```text
toLocal        local[row]  = Σ_c offset[c] * axis[row*3 + c]      【行】
法线旋转        normal[c]  = Σ_r normal[r] * axis[r*3 + c]        【列】
```

**⇒ 所以 `toLocal` 是 `axis · offset`，法线旋转是 `axis^T · normal`。**

**⇒ 这两个**是转置对** ✓ ⇒ 所以"进模型空间用 axis·，出模型空间用 axis^T·"**是**一致**的。**

**⇒ 而注释说 `toLocal` 是"转置" ⇒ **注释是错的**（它实际是正常乘法）。**

**⇒ 但**整体是一致的**。**

### 6.6 那句"orientation 是一个 4×3"

```text
the orientation there is a 4x3, nine floats of axis followed by the entity origin
```

**⇒ 所以服务端的 orientation 结构是 `{axis[9], origin[3]}` = 12 个浮点。**

**⇒ 而 `toLocal` 分开处理 `axis` 与 `entity.origin`** ✓ 等价。

## 七、`result.fraction` 的三项验证

```php
if (!std::isfinite(result.fraction) ||
    result.fraction >= aggregate.fraction ||
    result.fraction < 0.0f)
{
    continue;
}
++improved;
```

### 7.1 三项

```text
有限
< aggregate.fraction      ← 【必须更好】
>= 0
```

**⇒ 与 §266 的"预置"配套** —— 因为预置了 `aggregate.fraction`，所以"不更好"就是"没命中"。

**⇒ 所以 `result.fraction == aggregate.fraction` ⇒ `continue`（没改进）。**

**✓ 逻辑闭合。**

### 7.2 而 `result.fraction < 0.0f` 也拒绝

**⇒ 负的 fraction 是无效的。**

## 八、`hitbox` 诊断的**十六个量**

```php
"hitbox trace entity=%lu partGroup=%u partName=%u "
"modelIndex=%u fraction=%.6f impact=(%.2f %.2f %.2f) "
"local=(%.2f %.2f %.2f) radial=%.2f "
"origin=(%.2f %.2f %.2f) yaw=%.2f boundsZ=%.2f..%.2f "
"scale=%.3f sample=%lu/128"
```

### 8.1 十六个

```text
entity / partGroup / partName / modelIndex
fraction
impact (x3)
local (x3)
radial
origin (x3)
yaw
boundsZ (2 个)
scale
sample
```

### 8.2 而 `radial = sqrt(localX² + localY²)`

**⇒ 水平半径** —— 用于判断"打到了头部还是躯干"。

**⇒ 与记忆里"hit-location partGroup 2 = head confirmed live"相关。**

### 8.3 `yaw = entity.angles[1]`

**⇒ 角度数组的**第二个**是 yaw** ✓（COD 约定：pitch/yaw/roll）

### 8.4 `boundsZ = midpoint[2] ± halfSize[2]`

**⇒ 包围盒的 z 范围。**

### 8.5 三项条件 + 128 上限

```php
if (hitboxDiagnosticsEnabled() &&
    entity.bodyRole == SvCollisionBodyRole::Player &&     // ← 【只对玩家】
    hitboxTraceLogCounter_++ < 128)
```

**⇒ 只记录**玩家**的 hitbox trace，最多 128 条。**

## 九、`aggregate` 的**九项更新**

```php
aggregate.fraction    = result.fraction;
aggregate.surfaceFlags = result.surfaceFlags;
aggregate.modelIndex  = result.modelIndex;
aggregate.partName    = result.partName;
aggregate.partGroup   = result.partGroup;
aggregate.contents    = entity.contents;         // ← 【来自实体而不是 result】
aggregate.hitType     = TraceHitTypeEntity;
aggregate.hitId       = entity.entityNum;
aggregate.normal[3]   = ... 旋转 ...
aggregate.walkable    = aggregate.normal[2] >= 0.7f;
```

**⇒ 十项（含 normal 与 walkable）。**

### 9.1 **`contents` 来自 `entity.contents` 而不是 `result`**

**⚠ 而 `surfaceFlags`/`modelIndex`/`partName`/`partGroup` 来自 `result`。**

**⇒ 一个字段的来源不同。**

**⇒ 可能因为 DObj trace 不返回 contents。**

### 9.2 `walkable = normal[2] >= 0.7`

**⇒ 法线的 z 分量 >= 0.7 ⇒ 约 45° 以内 ⇒ 可站立。**

**`0.7 ≈ cos(45.6°)`。**

**⇒ 这是 COD 的标准"可行走地面"阈值** ✓

### 9.3 法线非有限时**回退到 `{0,0,1}`**

```php
if (!all_of(aggregate.normal, isfinite))
{
    aggregate.normal = { 0.0f, 0.0f, 1.0f };
}
```

**⇒ 一个"向上"的法线** ⇒ `walkable = true`。

**⚠ 所以一个损坏的法线会被当成**可站立的地面**。**

**⇒ 这可能是一个**有意的**选择（"总比 NaN 好"）或一个**错误**（应该 `walkable = false`）。**

**⇒ 值得指出。**

## 十、`locational entity trace` 的**六个量**

```php
"locational entity trace entities=%zu considered=%lu traced=%lu improved=%lu "
"fraction %.6f -> %.6f partGroup=%u"
```

**⇒ 六个量 + 入口/出口 fraction。**

**⇒ 而 `traced` 与 `considered` 分开** —— 因为有些 considered 的实体会因 DObj 不可用而跳过。

**⇒ 所以 `traced <= considered`。**

## 十一、关键结论

1. **只处理 `Capsule` 与 `ScriptModelDObj`，跳过 `BrushModel`** —— 与 §265 的分工不重叠（除 Capsule）。
2. **`break` 在循环**开头**（§265 在末尾）—— 语义相同但更早退出。
3. **`PointTraceBounds` 是一个固定的"点"边界**。
4. **DObj 不可用时 actor 有胶囊回退** —— 否则战役敌人不能死 ⇒ agent 槽不释放。
5. **`result.fraction` 必须预置为 `aggregate.fraction`** —— 留零则 tracemline 永远不报命中。
6. **"读调用者（0x0046E1FC）而不是读被调方"** —— 契约藏在调用者的准备里。
7. **`toLocal` 注释说"转置"而代码是 `axis · offset`** —— 注释错但整体一致（法线旋转是 `axis^T`）。
8. **"进模型空间 axis·、出模型空间 axis^T·"是转置对**。
9. **三个零向量会通过 `isfinite` 检查** ⇒ 所有 `toLocal` 返回零 ⇒ 可能的失效模式（§164 的教训）。
10. **`result.fraction >= aggregate.fraction` ⇒ 没命中**（与预置配套）。
11. **`contents` 来自 `entity` 而其它四个来自 `result`**。
12. **`walkable = normal[2] >= 0.7`** —— COD 标准可行走阈值。
13. **法线非有限时回退 `{0,0,1}` ⇒ `walkable = true`** —— 可疑。
14. **hitbox 诊断只对 `bodyRole == Player`，最多 128 条**。
15. **`traced <= considered`**（DObj 不可用的被跳过）。

## 十二、未闭合点

- `invokeAngleVectors` 的 `axis` 输出布局（行或列）。
- `toLocal` 的"转置"注释与代码的实际关系是否真的等价于引擎行为。
- 法线损坏回退为 `{0,0,1}` 是否应该 `walkable = false`。
- `EngineBindings.cpp` 18050 行之后未读取。
