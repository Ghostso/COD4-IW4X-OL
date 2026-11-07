# 267 · `result.fraction = 1.0f` 的两种预置、`dobjContentsTraceline` 的动画条件存取、`traceServerPoint` 的七个拒绝

## 一、范围

本报告学习 `EngineBindings.cpp` 18050–18250 行。

## 二、`traceTransformedDObjContentsPassed`：**结果预置为 1.0**

```cpp
NativeDObjTraceResult result{ .fraction = 1.0f };
```

### 2.1 与 §266 的**对比**

```text
§266  traceServerLocationalEntities   result.fraction = aggregate.fraction    【当前最佳】
§267  traceTransformedDObjContentsPassed   result = { .fraction = 1.0f }       【满值】
```

**⇒ 两种预置、两种语义。**

### 2.2 为什么这里用 1.0

**⇒ 因为这里问的是"这条射线是否能通过"（`fraction == 1.0`）而不是"谁最近"。**

**⇒ 满值 = "没有被挡住"。**

**⇒ 所以 `result.fraction == 1.0f` 就是"通过"。**

**⇒ 语义**

```text
§266  预置当前最佳 ⇒ 找更好的命中
§267  预置 1.0      ⇒ 找任何阻挡
```

**✓ 两个都对，但预置值由**用途**决定。**

## 三、**动画条件存储的三段**

```cpp
std::byte *previousAnimConditionBase{};
if (!installServerAnimConditionStorage(previousAnimConditionBase))
    return nullopt;
...
const auto restored = restoreServerAnimConditionStorage(previousAnimConditionBase);
if (!invoked || !restored || ...) return nullopt;
```

### 3.1 三段

```text
① 安装（并保存前一个）
② 调用
③ 恢复（并验证）
```

### 3.2 而 §235 学过 `installServerAnimConditionStorage` **只装第二个基址**

**记忆**："`installServerAnimConditionStorage` 只装第二个（`0x827F730`）；第一个（`0x827F734`）持有本进程里最后一次 `sub_407530` 留在那里的任何东西"

**⇒ 所以这里安装的是 `characterInfo` 基址。**

**⇒ 而 `dobjContentsTraceline` 需要 `characterInfo` 来摆姿态。**

### 3.3 **而 `restored` 是返回值**

```cpp
const auto restored = restoreServerAnimConditionStorage(previousAnimConditionBase);
if (!invoked || !restored || ...) return nullopt;
```

**⇒ 所以"恢复失败"⇒ 整个函数失败。**

**⇒ 这是一个正确的资源管理** —— 如果恢复失败，全局基址可能被污染。

### 3.4 ⚠ **但 `restored` 在 `invoked` 之前求值**

```cpp
const auto restored = restoreServerAnimConditionStorage(previousAnimConditionBase);
```

**⇒ 而 `restoreServerAnimConditionStorage` 在这个位置**总是**被调用（无论 `prepared` 是否为真）。**

**✓ 正确** —— 因为 `install` 已经成功。

### 3.5 而 `previousAnimConditionBase` 是 `std::byte*`

**⇒ 所以 `restore` 接收前一个基址。**

**⇒ 一个"保存/恢复"的 RAII 的手写版。**

**⚠ 而如果 `restore` 抛异常（不太可能），基址会泄漏。**

## 四、`prepared` 的**三项串联**

```cpp
const auto prepared =
    prepareNativeServerDObjPoses(std::span(&entity, 1), request.contentMask, exceptionDetails) &&
    invokeAngleVectors(angleVectors_, entity.angles, axis, &exceptionDetails) &&
    std::ranges::all_of(axis, [](float v) { return std::isfinite(v); });
```

### 4.1 三项

```text
摆 DObj 姿态（单个实体）
算角度轴
轴全有限
```

### 4.2 **`std::span(&entity, 1)` —— 一个元素的临时 span**

**⇒ 所以 `prepareNativeServerDObjPoses` 接受一个实体数组。**

**⇒ 而这里只有一个。**

### 4.3 而 `&&` 的短路

**⇒ 如果 `prepare` 失败，`invokeAngleVectors` 不跑 ⇒ `axis` 保持零。**

**⇒ 而 `prepared = false` ⇒ `invoked = false`。**

**✓ 正确。**

## 五、`local` 的**与 §266 相同的变换**

```php
const auto local = [&](const std::array<float, 3> &point) {
    std::array<float, 3> output{};
    for (row = 0; row < 3; ++row)
        for (column = 0; column < 3; ++column)
            output[row] += (point[column] - entity.origin[column]) * axis[row * 3 + column];
    return output;
};
```

### 5.1 **与 §266 的 `toLocal` 数学完全相同**

```text
§266  local[row] = Σ_c offset[c] * axis[row*3 + c]
§267  output[row] += Σ_c (point[c] - origin[c]) * axis[row*3 + c]
```

**⇒ 完全一致** ✓

**⇒ 两处独立实现同一变换** —— 而**都没有转置**（尽管 §266 的注释说是转置）。

**⇒ 所以"§266 的注释错"这个判断被 §267 的独立实现**加强**了。**

## 六、**`dobjContentsTraceline` 与 `dobjTraceline` 的区别**

```php
invokeDObjContentsTraceline(dobjContentsTraceline_, dobj, start, end, request.contentMask, result, &exceptionDetails);
```

### 6.1 与 `invokeDObjTraceline` 的参数对比

```text
§266  invokeDObjTraceline(dobjTraceline_, dobj, start, end, priorityMap.data(), result, &details)
§267  invokeDObjContentsTraceline(dobjContentsTraceline_, dobj, start, end, contentMask, result, &details)
```

**⇒ 五个相同 + 一个不同：**

```text
§266  priorityMap.data()   【每部件优先级图】
§267  contentMask          【内容掩码】
```

### 6.2 而那段注释

```php
// CODREF(Ghosts SV_PointSightTraceToEntity 14020AFF8..14020B022):
// script models pose contents-selected bones and trace model geometry.
// No player hit-location priority map is involved in this branch.
```

**⇒ "脚本模型按内容选择骨骼并追踪模型几何。这个分支不涉及玩家命中位置优先级图。"**

**⇒ 所以两个函数是**两种 trace 模式**：**

```text
priorityMap   按命中位置（头/躯干/四肢）优先
contentMask   按内容（只看特定材质类型）
```

**⇒ 与 §266 的 `entity.bodyRole == Player` 相关** —— 玩家有命中位置，脚本模型没有。

## 七、`traceRadiusDamageVisibility`：**两个回调**

```php
return SV_TestRadiusDamageVisibility(request, entities,
    // 世界回调
    [this, &glassState](const SvRadiusDamageTraceRequest &ray) -> optional<bool> {
        const auto world = traceWorld(ray.start, ray.end, PointTraceBounds, ray.contentMask, glassState);
        if (!world) return nullopt;
        if (world->fraction < 1.0f || world->startSolid || world->allSolid) return false;

        // CODREF(out.exe 46E7C2 / 46E80D): WorldTrace does not itself
        // trace static map models. Keep the second retained stage.
        auto native = encodeTraceResult(*world);
        if (!invokePointTraceStaticModels(pointTraceStaticModels_, ray.start, ray.end, ray.contentMask, native, &exceptionDetails))
            return nullopt;
        const auto models = decodeTraceResult(native);
        if (!models) return nullopt;
        return models->fraction == 1.0f && !models->startSolid && !models->allSolid;
    },
    // 实体回调
    [this, &glassState](const SvRadiusDamageTraceRequest &ray, const SvCollisionEntity &entity) -> optional<bool> {
        if (entity.shape == SvCollisionShape::ScriptModelDObj)
            return traceTransformedDObjContentsPassed(ray, entity);
        // CODREF(Ghosts 14020AE30..14020AE56 / 14020B07E): with the
        // radius caller's NULL priority map, player entities take
        // collision geometry rather than player locational bones.
        const TraceResult initial{ .fraction = 1.0f };
        const auto trace = entity.shape == SvCollisionShape::BrushModel
            ? traceTransformedBrushModel(initial, ray.start, ray.end, PointTraceBounds, entity, glassState)
            : traceTransformedCapsule(initial, ray.start, ray.end, PointTraceBounds, entity);
        if (!trace) return nullopt;
        return trace->fraction == 1.0f && !trace->startSolid && !trace->allSolid;
    });
```

### 7.1 **两个回调的分工**

```text
世界回调    BSP 世界 + 静态模型两段
实体回调    ScriptModelDObj → DObj 内容 trace
            其它 → brush/capsule 几何 trace
```

### 7.2 **两段世界 trace**

```php
const auto world = traceWorld(...);
if (world->fraction < 1.0f || world->startSolid || world->allSolid) return false;

// 第二段
invokePointTraceStaticModels(pointTraceStaticModels_, ...);
return models->fraction == 1.0f && !models->startSolid && !models->allSolid;
```

**⇒ 三项判据**：

```text
fraction == 1.0    没有被挡住
!startSolid        起点不在实心内
!allSolid          不全在实心内
```

### 7.3 而"WorldTrace 自己不追静态地图模型"

```php
// CODREF(out.exe 46E7C2 / 46E80D): WorldTrace does not itself
// trace static map models. Keep the second retained stage.
```

**⇒ 所以必须**两段**：BSP + 静态模型。**

**⇒ 与 §265 的"世界半边活着"不完全一样** —— 世界半边也只是 BSP，静态模型要第二段。

### 7.4 而"半径调用者的 NULL 优先级图 ⇒ 玩家实体用碰撞几何而不是定位骨骼"

```php
// CODREF(Ghosts 14020AE30..14020AE56 / 14020B07E): with the
// radius caller's NULL priority map, player entities take
// collision geometry rather than player locational bones.
```

**⇒ 三层**：

```text
1. 半径伤害的调用者传 NULL priority map
2. ⇒ 玩家实体用【碰撞几何】（胶囊）
3. 而不是【定位骨骼】（DObj）
```

**⇒ 所以半径伤害（爆炸）用胶囊，而子弹用 DObj 骨骼。**

**⇒ 这解释了为什么爆炸伤害打不到头部。**

**✓ 一个重要的语义区分。**

### 7.5 而 `initial = { .fraction = 1.0f }` 与 §267 开头的预置一致

## 八、`traceServerPoint` 的**七个具名拒绝**（本组第二重要）

```php
// OLMOD(point-trace-refusal-reasons): this function had FOUR silent
// `return std::nullopt` paths and a caller that can only print
// "unavailable". Section 36g's rule - an instrument that cannot fire is
// worse than none - applies to a refusal as much as to a fault, and the
// first time one of them fired it cost a whole cycle to learn which.
// Sampled, so a burst of bullets cannot flood the log.
const auto refuse = [this](const char *const reason) {
    if (pointTraceRefusalLogCounter_++ < 12)
        write("server point trace REFUSED reason=" + reason);
    return optional<TraceResult>{};
};
if (!SV_IsPointTraceRequestValid(request)) return refuse("request-invalid");
if (request.mode != CollisionOnly)
{
    if (gameThreadId_ != GetCurrentThreadId()) return refuse("not-game-thread");
    if (!nativeServerEntityMirrorMatches(entities)) return refuse("entity-mirror-mismatch");
}
if (request.mode == CollisionOnly) return traceServerCapsule(...);

const auto priorityMap = SV_GetLocationalPriorityMap(request.mode);
if (priorityMap.empty()) return refuse("no-priority-map");

const auto worldTrace = request.entitiesOnly ? ... : traceStaticWorld();
if (!worldTrace) return refuse("world-trace-failed");
if (request.worldOnly) return worldTrace;
if (!request.entitiesOnly && worldTrace->fraction == 0.0f) return worldTrace;
...
if (!installServerAnimConditionStorage(previousAnimConditionBase))
    return refuse("anim-condition-storage");
```

### 8.1 七个具名原因（从代码可见）

```text
"request-invalid"
"not-game-thread"
"entity-mirror-mismatch"
"no-priority-map"
"world-trace-failed"
"anim-condition-storage"
（后面可能还有）
```

### 8.2 **"四个静默路径"的修复**

**⇒ 与 §236/§256/§244 的 `refuse` 同族。**

**⇒ 第五次出现。**

### 8.3 而 `pointTraceRefusalLogCounter_++ < 12`

**⇒ 最多 12 条。**

**⇒ 与 §266 的 `hitboxTraceLogCounter_ < 128`、§265 的 12 条不同上限。**

## 九、`traceServerPoint` 的**四种 mode**

```text
CollisionOnly        ⇒ 直接 traceServerCapsule（跳过一切实体镜像检查）
worldOnly            ⇒ 只做世界
entitiesOnly         ⇒ 跳过世界（fraction = 1.0）
（默认）              ⇒ 世界 + 实体
```

### 9.1 **`CollisionOnly` 跳过游戏线程检查**

```php
if (request.mode != CollisionOnly)
{
    if (gameThreadId_ != GetCurrentThreadId()) return refuse("not-game-thread");
    if (!nativeServerEntityMirrorMatches(entities)) return refuse("entity-mirror-mismatch");
}
if (request.mode == CollisionOnly) return traceServerCapsule(...);
```

**⇒ 两处**都检查 `mode`**，所以 `CollisionOnly` 完全跳过这两项。**

**⚠ 这可能是一个缺陷** —— 因为 `traceServerCapsule` 也可能需要游戏线程。

**⇒ 但 `traceServerCapsule` 自己可能有检查**（§265 里没看到）。

**⇒ 待确认。**

### 9.2 `entitiesOnly` 的**短路**

```php
const auto worldTrace = request.entitiesOnly
    ? std::optional{ TraceResult{ .fraction = 1.0f } }
    : traceStaticWorld();
```

**⇒ 不跑世界 trace，直接给"满值"** ✓

### 9.3 `worldTrace->fraction == 0.0f` 的**短路**

```php
if (!request.entitiesOnly && worldTrace->fraction == 0.0f)
    return worldTrace;
```

**⇒ 世界已经打到 0 ⇒ 不可能有更近的实体 ⇒ 直接返回。**

**✓ 一个正确的优化。**

## 十、`traceStaticWorld` 的**两段**

```php
const auto traceStaticWorld = [&]() -> optional<TraceResult> {
    const auto world = traceWorld(request.start, request.end, PointTraceBounds, request.contentMask, glassState);
    if (!world || world->fraction == 0.0f) return world;    // ← 【0 就返回】

    // CODREF(out.exe sub_46E780): bullet traces set bStaticModels=1.
    // WorldTrace covers BSP only; CM_PointTraceStaticModels is a
    // separate retained stage and can replace the aggregate with a
    // nearer model hit carrying the material surface flags required by
    // penetration. Apply it to both the forward aggregate and the
    // reverse world-only thickness trace.
    auto native = encodeTraceResult(*world);
    if (!invokePointTraceStaticModels(pointTraceStaticModels_, request.start, request.end,
            request.contentMask, native, &exceptionDetails))
        return nullopt;
    return decodeTraceResult(native);
};
```

### 10.1 三项

```text
① BSP 世界 trace
② 若 fraction == 0 ⇒ 直接返回（不需要静态模型）
③ 否则跑静态模型段并【替换】聚合结果
```

### 10.2 **而"替换"意味着可能是**更远**的结果**

```php
// can replace the aggregate with a nearer model hit
```

**⇒ 注释说"更近的模型命中"，但代码没有任何比较。**

**⚠ `invokePointTraceStaticModels` 内部可能做了 `min`（因为 `encodeTraceResult(*world)` 传入了当前最佳）。**

**⇒ 与 §266 的"预置 fraction"同族。**

**✓ 所以**应该**是更近的（如果内部遵守预置契约）。**

### 10.3 而"表面标志"是穿透必需的

```php
// carrying the material surface flags required by penetration
```

**⇒ 所以静态模型段不只是几何，还提供材质表面标志。**

## 十一、**"引擎自己的遍历器在这里不可用"**

```php
// THE ENGINE'S OWN WALKER IS NOT USABLE HERE. calcTraceExtents_ and
// pointTraceToEntities_ stay bound and guarded because both addresses
// are real and verified, but 0x0046E6D0 is out.exe's CLIENT
// trace-to-entities: it enumerates a heap centity array the dedicated
// never fills and offsets the ray by a global rather than by an entity.
// 1649370 has no server-side twin, so the per-entity work is this
// project's - see traceServerLocationalEntities above and section 73.
```

### 11.1 三个绑定

```text
calcTraceExtents_        保留并保护
pointTraceToEntities_    保留并保护
0x0046E6D0               客户的 trace-to-entities ⇒ 【不可用】
```

### 11.2 "两个地址都是真的且已验证"

**⇒ 所以不是"没找到"而是"找到了但用不了"。**

### 11.3 而"本 build 没有服务端孪生"

**⇒ 与 §265 的"这个 build 没有 SV_Trace"一致。**

## 十二、**"DObj 姿态计算是昂贵部分"**

```php
// DObj pose calculation is the expensive part of locational tracing.
// The old path posed every live DObj before the trace's own broadphase
// rejected almost all of them. Build the exact same candidate set first
```

### 12.1 三层

```text
1. DObj 姿态计算是定位 trace 的昂贵部分
2. 旧路径先摆了【每一个活着的 DObj】
3. 而 trace 自己的宽相随后拒绝了【几乎全部】
```

**⇒ 顺序反了 ⇒ 先宽相再摆姿态。**

**⇒ 与 §259 的"扫描先建表"、§260 的"扫一次建名表"是同一族**（把昂贵操作放在过滤之后）。

**⇒ 这是本文件里"先把昂贵的放在最窄的集合上"的第三次。**

## 十三、关键结论

1. **两种 `fraction` 预置**：`aggregate.fraction`（找更好）与 `1.0`（找阻挡）。
2. **动画条件存储三段**：安装 → 调用 → 恢复，且"恢复失败 ⇒ 整个失败"。
3. **`prepared` 的三项 `&&` 短路**。
4. **§266 与 §267 的 `local`/`toLocal` 数学完全相同** ⇒ 加强"注释说转置而实际不是"的判断。
5. **`dobjContentsTraceline` 用 `contentMask` 而 `dobjTraceline` 用 `priorityMap`** —— 两种 trace 模式。
6. **半径伤害用胶囊（碰撞几何）而子弹用 DObj 骨骼** —— 因为半径调用者传 NULL priority map。
7. **世界 trace 必须两段**（BSP + 静态模型），而静态模型段还提供穿透所需的表面标志。
8. **`traceServerPoint` 的七个具名拒绝**取代四个静默 nullopt。
9. **`CollisionOnly` 跳过游戏线程与实体镜像检查** —— 可能是一个缺陷。
10. **`entitiesOnly` 短路世界 trace 为 `fraction = 1.0`**。
11. **`worldTrace->fraction == 0` 短路实体遍历** ✓ 正确优化。
12. **`traceStaticWorld` 的"替换"依赖 `invokePointTraceStaticModels` 遵守预置契约**（无本地比较）。
13. **`calcTraceExtents_`/`pointTraceToEntities_` 保留但不可用** —— 地址真实但行为是客户端的。
14. **"先宽相再摆 DObj 姿态"** —— 第三次"昂贵操作放在最窄集合上"。

## 十四、未闭合点

- `traceServerCapsule` 自己是否有游戏线程检查（`CollisionOnly` 跳过外层检查后）。
- `invokePointTraceStaticModels` 是否做 `min`（否则"替换"可能变远）。
- `restoreServerAnimConditionStorage` 失败的具体后果。
- `EngineBindings.cpp` 18250 行之后未读取。
