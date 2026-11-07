# 225 · 闩锁要能释放、`0x118..0x168` 的九个偏移、七兄弟高度函数

## 一、范围

本报告学习 `EngineBindings.cpp` 6109–6308 行。

## 二、那个"31 次全中"的闩锁缺陷

### 2.1 问题

```cpp
// AND THE LATCH HAS TO BE RELEASED, or the first transient blinds the rest
// of the match. MEASURED 2026-08-19 over all 31 sessions in
// CodolGameServer.log: entity 0 reports `customization_absent` exactly once
// per session and the model-resolution failure follows IN THE SAME SECOND,
// 31 times out of 31 - the very next mirror pass already has the
// customization. One mirror pass runs before the snapshot publishes it, so
// every match opens with a one-frame gap that is not a failure at all.
```

**五个要点**：

```text
1. 31 个会话里 entity 0 每次都报 customization_absent 一次
2. 模型解析失败在同一秒跟着来
3. 31/31 —— 即每次都这样
4. 但下一次镜像 pass 就已经有 customization 了
5. ⇒ 一个镜像 pass 在快照发布它之前运行 ⇒ 每场比赛开头的单帧间隙【根本不是失败】
```

### 2.2 后果

```text
Because the slot is shared by four states, that single transient latched
it for the whole session and `dobj_absent`, `no_traceline_bones` and
`healthy` COULD NOT FIRE FOR ENTITY 0 IN ANY SESSION EVER RECORDED.
None of the three has ever appeared in the log, and that silence was the
instrument being blind, not the server being well.
```

**"那个沉默是仪器瞎了，不是服务器健康。"**

**这是本项目最核心的方法论之一**：**"日志里没有" ≠ "没发生"**。

### 2.3 `releasePlayerDObjReportedState` 的带条件清除

```cpp
// Only clear the state we are contradicting. Clearing unconditionally
// would let a stale report re-print every time the condition it
// describes was re-entered from a DIFFERENT state.
if (playerDObjReportedState_[entityNum] != state)
    return;
playerDObjReportedState_[entityNum] = PlayerDObjState::Unknown;
```

**"只清除我们在反驳的那个状态。无条件清除会让一个陈旧报告在它所描述的条件从【另一个状态】重新进入时每次都重打。"**

**两级语义**：

```text
无条件清除 → 陈旧报告会重复
带条件清除 → 只有真的"否定了它"才清
```

### 2.4 `reportPlayerDObjState` 的四态

```cpp
if (playerDObjReportedState_[entityNum] == state) return;    // 同态不重报
playerDObjReportedState_[entityNum] = state;

switch (state)
{
case CustomizationAbsent: name = "customization_absent"; break;
case DObjAbsent:          name = "dobj_absent"; break;
case NoTracelineBones:    name = "no_traceline_bones"; break;
case Healthy:             name = "healthy"; break;
}
```

**`Unknown` 是初值**，四个具名状态各自可报**一次**（从 `Unknown` 或其他状态转入时）。

**所以四个状态在实体 0 上从来没出现过** —— 因为一直卡在 `CustomizationAbsent`。

## 三、`logNativeCapsuleCandidacy`：那九个偏移中的四个曾是错的

### 3.1 问题

```cpp
// FOUR OF THE NINE OFFSETS IN THIS BLOCK WERE STILL 3.3.3.3's, sitting
// either side of a comment that states the rule refuting them. Whoever
// ported the middle five did not port the ends: isLinked 0x110,
// svFlags 0x112, inUse 0x113 and ownerNum 0x160 all stayed.
// 0x110..0x117 is the LAST EIGHT BYTES OF THE EMBEDDED entityState on this
// build, so three of the four were reading entityState tail bytes and
// printing them as link state, and this diagnostic reported plausible
// garbage on every line it ever wrote.
```

**"移植中间五个的人没有移植两端"** —— 这是最典型的局部移植缺陷。

**三个读的是 `entityState` 的尾部字节** —— 而**第四个 `ownerNum 0x160` 读的是 `currentAngles` 的 YAW**（一个 float，被当 signed int 打印）。

### 3.2 九个正确偏移

```cpp
IsLinkedOffset         = 0x118
ServerFlagsOffset      = 0x11A
BoundsOffset           = 0x11C
ContentsOffset         = 0x134
AbsoluteBoundsOffset   = 0x138
CurrentOriginOffset    = 0x150
OwnerNumOffset         = 0x168
IsInUseOffset          = 0x11B
EntityTypeOffset       = 0x04
```

### 3.3 `entityShared_t` 的完整布局

```
isLinked/modelType/svFlags/inUse  0x118..0x11B
box                               0x11C
contents                          0x134
absBox                            0x138
currentOrigin                     0x150
currentAngles                     0x15C
ownerNum                          0x168
```

**`SV_LinkEntity 0x0074EF10` 每一个都写**：

```text
*(BYTE*)(a1+280) = 1          ← 0x118 isLinked
*(BYTE*)(a1+282) & 6          ← 0x11A svFlags
a1+284  bounds                ← 0x11C
a1+308  contents              ← 0x134
a1+312  absBox                ← 0x138
a1+336  origin                ← 0x150
```

**验算**：

```text
280 = 0x118 ✓
282 = 0x11A ✓
284 = 0x11C ✓
308 = 0x134 ✓
312 = 0x138 ✓
336 = 0x150 ✓
```

### 3.4 `currentAngles` 在 `0x15C..0x167`

```text
currentAngles therefore occupies 0x15C..0x167 and 0x160 is its YAW
-- a float, printed here as a signed int.
```

**`0x15C + 4 = 0x160` 是 `currentAngles[1]`（yaw）** —— 因为 `currentAngles` 是 `float[3]`。

**所以旧的 `ownerNum = 0x160` 读的是 yaw 的位模式** —— **一个很小的 float（比如 90.0f = 0x42B40000 = 1119092736）被当 int 打印**。

**"在它写过的每一行上都报告了貌似合理的垃圾"** —— 因为读出来的数字看起来"像个实体号"（如果 yaw 很小，比如 `0.0f` = 0）。

### 3.5 `AbsoluteBoundsOffset` 的意义

```cpp
// CODREF(sv_link_entity): the ABSOLUTE box. Nothing in this project
// writes it - SV_LinkEntity owns it and recomputes it from origin plus
// bounds - so it is the one word that goes stale when an entity moves
// or changes size without being relinked, and CM_CalcTraceExtents
// decides candidacy on it.
```

**"本项目没有任何东西写它"** —— 所以**它是唯一的"实体移动或改变大小却没重新链接时变陈旧的那个字"**，而 `CM_CalcTraceExtents` **用它决定候选性**。

**这是一个很精确的诊断点**。

### 3.6 `ownerNum` 的固定槽问题

```cpp
// CODREF(sv_trace): the trace's ignore filter is the last thing that
// can drop a correctly linked, correctly boxed entity. traceServerPoint
// passes ignoreSelf/ignoreParent/ignoreSiblings all set, and the native
// resolves those against gentity ownerNum - which
// SV_ToNativeServerEntity never writes. In a fixed-slot mirror that
// word therefore carries whatever the slot's previous occupant left,
// and a value that happens to match the shooter or its parent makes the
// entity a "sibling" and excludes it silently.
```

**"在一个固定槽镜像里，那个字因此携带该槽前一个占用者留下的任何东西"**

**如果它恰好匹配射手或其父，实体就成为"兄弟"并被静默排除。**

**这是"固定槽复用导致跨生命污染"的又一个实例**。

## 四、采样策略：每 8 次一次

```cpp
if (!gEntities_ || nativeCapsuleCandidacyLogCounter_++ % 8 != 0)
    return;
```

### 4.1 那次"过滤掉了要紧的那个"

```cpp
// Report unconditionally, sampled. The first attempt gated on
// `hitType == TraceHitTypeEntity` to keep only the misses, and that
// suppressed every line: a trace that reaches nothing but world still
// reports hitType 1, so the interesting case was the one filtered out
// (measured 2026-08-17: `hitType=1 hitEntity=none`).
```

**"一个只到达世界的 trace 仍然报 hitType 1，所以有趣的那个正是被过滤掉的。"**

### 4.2 没有可靠的"是否解析到实体"标志

```text
There is no reliable did-it-resolve-an-entity flag on this side -
hitId 0 is a legitimate entity - so take every eighth trace and let
the hits serve as the control for the misses.
```

**"hitId 0 是一个合法实体"** —— 所以 `hitId == 0` 不能当"未命中"。

**解法：不区分，全采样，让命中作为未命中的对照。**

## 五、`logNativeServerDObjSkeleton`：七兄弟高度函数

### 5.1 `PM_GetStandHeight` 的定义

```text
A standing CODOL player's eye is at
PM_GetStandHeight = round(playerSizeScale * 60)
```

**"站立 CODOL 玩家的眼睛在 `round(playerSizeScale * 60)`"**

### 5.2 七个高度常量与两个 build 的地址

```text
3.3.3.3 0x00412410..0x00412530   out.exe 0x004104B0..0x004105D0
15  70  50  30  60  40  11       15  70  50  30  60  40  11
```

**七个值、同样顺序、两个 build 相同** ⇒ `PM_GetStandHeight` 在本 build 是 `sub_410570`，而 **60 沿用**。

### 5.3 扫描方法

```text
The height family is SEVEN adjacent functions with one shape --
`fld1` or `fld [playerState + sizeScale]`, `fmul qword [k]`, round --
so scanning that prologue finds all of them at once and the multipliers
ARE the heights
```

**"扫描那个序言一次找到全部七个，而乘数【就是】高度"**

**这是一个"签名扫描找到一族函数"的范例**：**七个相邻函数共享同一形状，只有常量不同**。

### 5.4 顺带读出的 size-scale 偏移

```text
The scan also reads the size-scale offset straight off the engine:
`fld [eax+98h]` on 3.3.3.3 against `fld [eax+0ACh]` here, which is
what sv_native_playerstate_mp.cpp's PlayerSizeScaleOffset already says.
```

**`+0x98`（3.3.3.3）vs `+0xAC`（本 build）** —— 与 §`sv_client_spawn_mp.cpp` 里"`+0x98` 是 3.3.3.3 的、在这 build 是 `+0xAC`"完全一致。

**三条独立证据链**：

```text
1. sv_client_spawn_mp.cpp 的注释（七个函数 × 15/70/50/30/60/40/11）
2. 本段的扫描
3. sv_native_playerstate_mp.cpp 的 PlayerSizeScaleOffset
```

### 5.5 一个具体症状

```text
Measured hits put confirmed-standing chests at 31-40 where they belong
at 44-56; this says whether the bones themselves are there, and if not,
which one breaks the chain.
```

**"确认站立的胸部在 31-40，而它们本该在 44-56"**

**所以骨骼高度是"低 ~13 单位"** —— 这正是"打不到头"的量化。

### 5.6 `DObjAnimMat` 的 32 字节布局

```text
DObjCalcSkel writes one DObjAnimMat per bone - quat[4], trans[3],
transWeight, 32 bytes - into the frame-scoped matrix block this
function just handed it, in the model space whose origin is the
entity origin.
```

**四个字段**：

```text
quat[4]       16
trans[3]      12
transWeight    4
= 32 ✓
```

**与 §184 里 `OlfinalDObjAnimMatSize = 32` 一致。**

**"在模型空间，其原点是实体原点"** —— 所以对比时要用 `+0x150 currentOrigin`。

## 六、关键结论

1. **"日志里没有" ≠ "没发生"** —— 一个闩锁让三个状态在 31 个会话里从未出现过。
2. **带条件清除**：只清除"我们在反驳的那个状态"。
3. **九个偏移里有四个曾是 3.3.3.3 的** —— "移植中间五个的人没有移植两端"。
4. **`ownerNum = 0x160` 读的是 `currentAngles` 的 yaw** —— 一个 float 被当 signed int 打印。
5. **`absBox` 是唯一"移动而未重链时变陈旧"的字**，而 `CM_CalcTraceExtents` 用它。
6. **`ownerNum` 在固定槽里携带前一个占用者的值** —— 可能被当"兄弟"静默排除。
7. **`hitId 0` 是合法实体**，所以不能当"未命中"标志。
8. **七个相邻高度函数共享同一形状，乘数就是高度** —— 一次扫描全部找到。
9. **确认站立的胸部在 31-40，本该 44-56** —— "低 13 单位"是"打不到头"的量化。

## 七、未闭合点

- `logNativeServerDObjSkeleton` 的完整实现（6308 行之后）未读取。
- `nativeServerDObjSkelEpoch_` 的递增点未在本组。
- `EngineBindings.cpp` 6308 行之后未读取。
