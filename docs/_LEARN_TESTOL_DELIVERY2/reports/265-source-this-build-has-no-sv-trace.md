# 265 · **"这个 build 没有 SV_Trace"**、319/319 的叶子相同、客户端数组在专用服为空

## 一、范围

本报告学习 `EngineBindings.cpp` 17650–17850 行。

## 二、摘要日志的**每 4096 次**

```cpp
if ((nativeTraceComparisonCount_ & 0xFFF) == 0)
{
    snprintf(summary, sizeof(summary),
        "native trace comparison summary comparisons=%llu mismatches=%llu "
        "unavailable=%llu owner=source", ...);
    write(summary);
}
```

### 2.1 `& 0xFFF == 0`

**⇒ 每 4096 次比较打印一条摘要。**

**`4096 = 0x1000`** —— 与 `0xFFF` 掩码一致 ✓

### 2.2 三个计数

```text
comparisons    总比较次数
mismatches     不一致次数
unavailable    不可用次数（fault 或解码失败）
```

**⇒ 所以三个数就直接给出"一致性率"。**

**⚠ 但 `nativeTraceComparisonCount_` 只在**成功**路径递增（`++nativeTraceComparisonCount_;` 在 `recovered` 之后）。**

**⇒ 所以 `unavailable` 不计入 `comparisons`。**

**⇒ "comparisons" = 成功完成的比较数。**

## 三、`traceServerCapsule` 的**入口**

```cpp
if (!SV_IsTraceEntityFilterValid(filter)) return nullopt;
```

**⇒ 唯一的前置检查。**

## 四、**"这个 build 没有 SV_Trace"**（本组最重要的一段）

### 4.1 那段断言

```php
// CODREF(sv_trace): THIS BUILD HAS NO SV_Trace. Section 74.
//
// The comment this replaces said CODOL's server Pmove handler owns
// collision through SV_Trace and the linked g_entities tree, and on
// 3.3.3.3 that is true -- SVTrace 0x005FB940 has exactly one caller,
// reaches 0x0058D500 and 0x0058D790, and those reach 0x005FB390 and
// 0x005FB510, which read the gentity at stride 0x2C8. 1649370 has
// none of them.
```

### 4.2 3.3.3.3 的**五个函数链**

```text
SVTrace              0x005FB940   【恰好一个调用者】
  → 0x0058D500
  → 0x0058D790
      → 0x005FB390
      → 0x005FB510          读 gentity stride 0x2C8
```

**⇒ 而 1649370 **一个都没有**。**

### 4.3 而 `SVTraceRva 0x0046E780` 是**另一个函数**

```php
// SVTraceRva 0x0046E780 is the counterpart of
// 3.3.3.3's 0x00459940, the GENERAL trace -- a thin wrapper calls it
// on both builds, it has 37 callers here to that one's 24, and its
// box walker's leaf 0x0046DCF0 is instruction-for-instruction
// identical to 3.3.3.3's CLIENT leaf 0x00458E40 (319 of 319) and 6%
// similar to the server's 0x0058D200.
```

### 4.4 五项

```text
0x0046E780  ↔  3.3.3.3 的 0x00459940      【通用 trace】
调用者数    37（本 build） vs 24（3.3.3.3）
叶子 0x0046DCF0  vs  3.3.3.3 客户端叶子 0x00458E40    【319/319 逐指令相同】
叶子 0x0046DCF0  vs  3.3.3.3 服务端叶子 0x0058D200    【6% 相似】
```

**⇒ 两个**极端**的相似度：319/319（完全相同）与 6%（几乎无关）。**

**⇒ 所以本 build 的通用 trace 读的是**客户端**的代码路径。**

### 4.5 而每实体的 clip **读客户端数组**

```php
// Its per-entity clip 0x0046DAE0
// reads the client centity array through
// dword_1C1D188[dword_82C3B60] ^ 0x2168F672 at stride 0x270 with the
// entityState at +0xF4 -- the SAME array section 73 measured EMPTY on
// a live dedicated, which is why the locational point trace returned
// hitType=0 with a healthy DObj standing in the ray.
```

### 4.6 五项

```text
0x0046DAE0                     每实体 clip
obfuscated slot                 dword_1C1D188[dword_82C3B60] ^ 0x2168F672
stride                          0x270
entityState at                  +0xF4
```

**⇒ 而 §73 实测这个数组在**活着的专用服上是空的**。**

**⇒ 所以"locational point trace 在一个健康的 DObj 站在射线里时返回 `hitType=0`"。**

### 4.7 这是**最强的证据**

```text
1. 客户端数组在专用服上为空（实测）
2. 而每实体 clip 读的正是那个数组
3. ⇒ 返回 hitType=0（没打到任何实体）
```

**⇒ 一个"实体明明在那里但打不到"的实测现象，被代码路径完全解释。**

### 4.8 而 `0x2168F672` 是**第二个 XOR 常量**

**记忆里是 `0xFBB2C97A`（§245 的 `dword_1C1D188 ^ 0xFBB2C97A`）。**

**⚠ 而这里是 `^ 0x2168F672`。**

**⇒ 两个不同的 XOR 常量。**

**可能**：

```text
0xFBB2C97A   用于【另一处】（§245 的模式字）
0x2168F672   用于【dword_1C1D188[dword_82C3B60]】
```

**⇒ 所以有两层混淆：先用 `dword_82C3B60` 索引，再 XOR `0x2168F672`。**

**而 §245 的 `dword_1C1D188 ^ 0xFBB2C97A` 是**同一基址**但直接 XOR。**

**⇒ 所以 `dword_1C1D188` 被用作两种目的：**

```text
dword_1C1D188 ^ 0xFBB2C97A                      单层
dword_1C1D188[dword_82C3B60] ^ 0x2168F672       索引后再 XOR
```

**⇒ 这是一个"地址混淆表"** —— 基址是 `dword_1C1D188`，索引用 `dword_82C3B60`，XOR 用 `0x2168F672`。

### 4.9 而 `client centity array` 的 `stride 0x270`

**与 §255 的 `clientState` stride `0x160` 不同。**

```text
centity      stride 0x270, entityState at +0xF4
clientState  stride 0x160
```

**⇒ 两个不同的数组。**

## 五、**四个调用者 vs 两个调用者**（本组第二重要）

```php
// The two shared
// clip helpers confirm it from the other side: 0x0058B230 and
// 0x0058B330 have FOUR callers each there and 0x00668470 and
// 0x00668560 have TWO here -- the two that are gone are the server
// clips.
```

### 5.1 两组函数

```text
3.3.3.3  0x0058B230（brush）与 0x0058B330（capsule）  各【四个】调用者
1649370  0x00668470（brush）与 0x00668560（capsule）  各【两个】调用者
```

**⇒ 少了两个调用者，而那正是**服务端的 clip**。**

### 5.2 而这两个正是 §263/§264 学的两个函数

```text
§264  0x0058B230 (3.3.3.3) / 0x00668470 (1649370)   brush model
§263  0x0058B330 (3.3.3.3) / 0x00668560 (1649370)   capsule
```

**⇒ 所以这两个函数**存在**，但**少了一半的调用者**。**

**⇒ 服务端不再调它们。**

### 5.3 这是**反向证据**（"从另一侧确认"）

**"共享的 clip 助手从另一侧确认了它"** —— 通过调用者数量的差，证明服务端路径被删除。

**⇒ 这是一个非常巧妙的论证** —— 不需要找到"缺失的函数"，而是数**调用者**。

### 5.4 而 §264 的四个调用点

```text
1649370   0x0046DC2F（box clip）、0x0046E3A1（point clip）
```

**⇒ "TWO here"** ✓ 与 §264 的四个调用点里**两个**是这两个函数的一致。

**等等** —— §264 说"Both call sites on each build agree (0x0046DC2F, 0x0046E3A1 here)"。

**⇒ 而这里是"TWO here"。**

**✓ 两个调用点 = 两个调用者。**

### 5.5 而 3.3.3.3 的四个

```text
§264  0x005FB4A7（server）、0x00458D7B（client）
```

**⇒ 两个。而这里说"FOUR callers each there"。**

**⚠ 矛盾**：§264 列了两个调用点，而这里说四个调用者。

**可能的解释**：

```text
§264 的"Both call sites on each build"只列了【两个代表性的】
而实际有四个（server/client × 两个场景）
```

**⇒ 所以 §264 的"two call sites"是列举而不是穷举。**

**⇒ 这是一处需要留意的表述差异。**

## 六、**"所以这个服务器上每一个胶囊查询的实体半边都是死的"**

```php
// So the entity half of every capsule query on this server was dead.
// The world half was not, because WorldTrace is genuinely shared,
// which is why a player has always stood on the ground and walked.
```

### 6.1 两个半边

```text
实体半边    【死】—— 服务端 clip 被删除
世界半边    【活】—— `WorldTrace` 真的共享
```

### 6.2 而"这就是为什么玩家一直能站在地上走路"

**⇒ 一个极其重要的**症状与解释的对应**：**

```text
能走（世界碰撞活）
但打不到实体（实体碰撞死）
```

**⇒ 这是整个项目里"部分功能工作"的最清晰解释。**

**⇒ 与记忆里"战斗服 world 从未绑定 ⇒ 实体层/真 clipmap 碰撞/伤害/HIT 整条是死的"互补** —— 那说的是服务端自己的实现，这里说的是**原生引擎路径**。

## 七、`nativeCapsuleTraceEnabled()` 分支的**六项前置**

```cpp
if (nativeCapsuleTraceEnabled())
{
    if (!nativeServerEntityMirrorObservedSuccess_ ||
        !nativeServerEntityMirrorFailure_.empty() ||
        entities.empty() ||
        nativeServerEntityMirror_.size() != entities.size() ||
        gameThreadId_.load() != GetCurrentThreadId() ||
        *serverGameEntitiesPointer_ != gEntities_ ||
        *serverGameEntityCount_ <= entities.back().entityNum)
    {
        return nullopt;
    }
    ...
    if (!invokeSVTrace(...)) return nullopt;
    return decodeTraceResult(nativeResult);
}
```

### 7.1 七项（我数七）

```text
① 镜像曾经成功过
② 镜像当前【没有】失败
③ entities 非空
④ 镜像大小 == entities 大小
⑤ 必须在游戏线程
⑥ 【serverGameEntitiesPointer_ 必须等于 gEntities_】
⑦ serverGameEntityCount_ > entities.back().entityNum
```

### 7.2 ⑥ 与 ⑦ 是关键

```text
*serverGameEntitiesPointer_ != gEntities_         ⇒ 拒绝
*serverGameEntityCount_ <= entities.back().entityNum  ⇒ 拒绝
```

**⇒ ⑥ 验证"引擎的 g_entities 指针就是我们以为的那个"。**

**⇒ ⑦ 验证"最后一个实体的编号在服务端实体计数之内"。**

**⇒ 两项都是**"我们的假设与引擎状态一致"** 的检查。**

### 7.3 ⚠ **`entities.back().entityNum` 假设 `entities` 按 entityNum 升序**

**如果 `entities` 不是有序的，`back()` 不是最大编号 ⇒ ⑦ 可能误放行。**

**⇒ 这是一个隐含假设** —— 而没有注释说明。

### 7.4 而 ⑥ 是一个**指针相等**检查

**`*serverGameEntitiesPointer_ != gEntities_`**

**⇒ 所以 `gEntities_` 是我们保存的期望值，而 `*serverGameEntitiesPointer_` 是引擎当前的。**

**⇒ 如果引擎重建了实体数组，指针会变 ⇒ 拒绝。**

**⇒ 这正是 §249/§263 里"代际检测"的同一手法。**

## 八、**回退路径：源实现**

```cpp
auto aggregate = traceWorld(start, end, bounds, contentMask, glassState);
if (!aggregate) return aggregate;

const auto worldFraction = aggregate->fraction;
std::size_t considered{}, improved{};
if (aggregate->fraction != 0.0f)
{
    for (const auto &entity : entities)
    {
        if (!SV_IsCollisionEntityValid(entity)) return nullopt;
        if (!SV_ShouldClipToEntity(entity, filter, contentMask)) continue;
        if (!SV_ShouldBroadphaseClipToEntity(start, end, bounds, entity)) continue;
        if (entity.shape == SvCollisionShape::ScriptModelDObj) continue;
        ++considered;
        const auto entityTrace = entity.shape == SvCollisionShape::BrushModel
            ? traceTransformedBrushModel(*aggregate, start, end, bounds, entity, glassState)
            : traceTransformedCapsule(*aggregate, start, end, bounds, entity);
        if (!entityTrace) return nullopt;
        if (SV_ApplyEntityTraceHit(*aggregate, *entityTrace, entity)) ++improved;
        if (aggregate->fraction == 0.0f) break;
    }
}
```

### 8.1 五层过滤

```text
① aggregate->fraction != 0        世界没打中就跳过全部实体
② SV_IsCollisionEntityValid       任一实体无效 ⇒ 【整个查询失败】
③ SV_ShouldClipToEntity           filter 与 contentMask 过滤
④ SV_ShouldBroadphaseClipToEntity 宽相阶段
⑤ shape == ScriptModelDObj        【跳过】
```

### 8.2 ⑤ 为什么跳过 `ScriptModelDObj`

**⇒ 脚本模型 DObj 没有静态几何 ⇒ 无法用 brush/capsule 表达。**

**⇒ 所以不参与实体 trace。**

### 8.3 而 ② 是**致命的**（`return nullopt`）

**⇒ 一个无效实体让**整个**查询失败。**

**⇒ 这与 §252 里"附件六级全部 continue"**相反**。**

**⇒ 可能是一个过严的选择** —— 但注释可能在其他地方。

### 8.4 `aggregate->fraction == 0.0f` 时 `break`

**⇒ 一旦打中（fraction 0）就停止。**

**⇒ 而 `SV_ApplyEntityTraceHit` 返回"是否改进"，所以 `fraction` 会单调下降。**

### 8.5 而 `worldFraction` 记录了**实体处理前**的值

**⇒ 用于日志的"fraction X → Y"。**

## 九、"改进"的日志

```php
// OLMOD(capsule-entity-collision): SILENT while nothing collides. It
// reports only when an ENTITY beat the world, which is the capability
// this build did not have before section 74 and the one thing a
// one-player map cannot produce. Sampled, because pmove traces run
// many times per frame.
if (improved != 0 && capsuleEntityTraceLogCounter_++ < 12)
{
    snprintf(line, ...,
        "capsule entity trace entities=%zu considered=%zu improved=%zu "
        "fraction %.6f -> %.6f hitType=%u hitId=%u", ...);
}
```

### 9.1 三项条件

```text
improved != 0          有实体赢了世界
counter++ < 12         最多 12 条
```

### 9.2 五个量

```text
entities     总数
considered   通过过滤的
improved     真正改进 fraction 的
fraction X → Y
hitType/hitId
```

### 9.3 那句"单人地图无法产生的一个能力"

**"the one thing a one-player map cannot produce"**

**⇒ 因为单人地图上**没有其他玩家实体**可撞。**

**⇒ 所以这个日志只在**多人**时出现。**

**⇒ 这是一个"测试需要两个玩家"的说明。**

### 9.4 "Sampled" = 最多 12 条

**⇒ 因为 pmove 每帧跑多次。**

## 十、`compareNativeServerCapsuleTrace` 的**位置**

```cpp
compareNativeServerCapsuleTrace(start, end, bounds, contentMask, glassState, entities, filter, *aggregate);
return aggregate;
```

**⇒ 在**最后**调用（在返回前）。**

**⇒ 所以源实现总是跑，原生只是可选对照。**

**⇒ 与 `nativeCapsuleTraceEnabled()` 分支（原生**替代**源）**相反**。**

**⇒ 两种模式**：

```text
nativeCapsuleTraceEnabled()  原生替代                    （生产）
否则                          源实现 + 可选原生对照        （默认）
```

## 十一、`SV_PointTraceToEntity` 的**两 build 对照**（下一段的开头）

```php
// CODREF(sv_trace): 3.3.3.3's SV_PointTraceToEntity 0x005FB510, done here.
//
// WHY IT IS HERE AND NOT A CALL. On 3.3.3.3 the clipmap walker
// CM_PointTraceToEntities 0x0058D790 calls SV_PointTraceToEntity for every
// entity in the SERVER's sector tree, and that function reads the gentity
// at stride 0x2C8 from the pointer at 0x03150048, tests svFlags bit 2 at
// gentity +0x112 to pick the locational pair, builds an orientation from
// the entity's own currentOrigin +0x148 and currentAngles +0x154, carries
// the ray into model space, calls DObjTraceline, and rotates the hit normal
// back out at 0x005FB7DC.
```

### 11.1 六个偏移

```text
gentity          stride 0x2C8          ← 与记忆一致
gentity 指针    0x03150048
svFlags bit 2   gentity +0x112         ← 【§265 后面说 0x11A】
currentOrigin   +0x148
currentAngles   +0x154
法线旋转        0x005FB7DC
```

### 11.2 ⚠ **`+0x112` 与后面的 `+0x11A`**

**记忆里**："`svFlags` offset conflict (still open: `0x112` vs `0x11A` in three places)"

**⇒ 而这里**同一个注释块**里出现两个值**：

```text
"tests svFlags bit 2 at gentity +0x112"
...
"The image has no `test byte [reg + 0x11A], 4` anywhere"
```

### 11.3 两个值的**不同来源**

```text
+0x112    3.3.3.3 的 svFlags（bit 2 ⇒ test 0x04）
+0x11A    本 build 里【不存在】那个指令
```

**⇒ 所以 `+0x11A` 是**搜索的目标**（"本 build 没有这个"），而 `+0x112` 是 **3.3.3.3 的实际偏移**。**

**⇒ 不是矛盾而是两个 build 的两个值。**

**⇒ 而 §265 的开头把这两个值放在同一个段落里，容易误读。**

### 11.4 `svFlags bit 2 = 0x04`

**`test byte [reg + 0x11A], 4`** ⇒ **bit 2** ✓

**⇒ 所以 `svFlags & 4` 选择"locational pair"（定位点对）。**

### 11.5 而 `DObjTraceline` 用 DObj

**⇒ 所以 3.3.3.3 的服务端点 trace 支持**动画模型**（DObj）。**

**⇒ 而本 build 的客户端版本"按一个**全局 vec3** 偏移射线而不是按任何实体"。**

## 十二、关键结论

1. **摘要每 4096 次打印**，`comparisons` 只计成功。
2. **"这个 build 没有 SV_Trace"** —— 3.3.3.3 的五个函数链在 1649370 一个都没有。
3. **`0x0046E780` 是通用 trace（对应 3.3.3.3 的 `0x00459940`）**，叶子与**客户端**叶子 319/319 相同、与服务端 6% 相似。
4. **每实体 clip 读客户端 centity 数组（stride 0x270、entityState +0xF4）**，而 §73 实测那个数组在专用服上是空的。
5. **`0x2168F672` 是第二个 XOR 常量**（§245 是 `0xFBB2C97A`）—— 地址混淆是"索引 + XOR"两层。
6. **四个 vs 两个调用者**是"服务端 clip 被删除"的反向证据。
7. **"实体半边死了、世界半边活着"** —— 解释了"能走但打不到实体"。
8. **七项前置**含两项"我们的假设与引擎状态一致"的检查（`gEntities_` 指针相等、`entities.back().entityNum` 在界内）。
9. **`entities.back()` 假设有序** —— 一个隐含约束。
10. **源实现路径的五层过滤**，其中"无效实体 ⇒ 整个失败"与 §252 的"六级 continue"相反。
11. **`ScriptModelDObj` 被跳过** —— 没有静态几何。
12. **"单人地图无法产生"** —— 实体赢世界需要第二个玩家。
13. **两种模式**：原生替代 vs 源 + 可选对照。
14. **`+0x112` 与 `+0x11A` 不是矛盾** —— 前者是 3.3.3.3 的 svFlags、后者是"本 build 不存在的目标指令"。
15. **`svFlags bit 2 = 0x04`** 选择 locational pair。

## 十三、未闭合点

- 3.3.3.3 的 clip 助手是"四个调用者"还是"两个"（§264 与 §265 表述不同）。
- `entities` 是否保证按 `entityNum` 升序。
- `0x2168F672` 与 `0xFBB2C97A` 两个 XOR 常量的分工。
- `EngineBindings.cpp` 17850 行之后未读取。
