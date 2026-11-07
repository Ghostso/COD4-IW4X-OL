# 227 · 三段时钟推进、part-bit 的两个来源、一次"整本弹匣被吞"

## 一、范围

本报告学习 `EngineBindings.cpp` 6507–6706 行。

## 二、`synchronizeActorHitPoses` 的三段时钟

### 2.1 完整序列

```cpp
if (serverDObjGetAdapter((int)entity.entityNum) != owner.dobj)
    { fail("owner-changed"); continue; }

const auto changed = fresh ||
    owner.source.animation != pose.animation ||
    owner.source.animationStartTime != pose.animationStartTime;

const auto commandTime = changed && !fresh
    ? std::clamp(pose.animationStartTime, owner.updatedTime, serverTime)
    : owner.updatedTime;

if (commandTime > owner.updatedTime &&
    !advanceActorHitAnimation(module_, owner.dobj, (commandTime-owner.updatedTime)*0.001f))
    { fail("previous-clock"); continue; }

if (changed && !setActorHitAnimation(module_, owner.dobj, node))
    { fail("goal"); continue; }

if (serverTime > commandTime &&
    !advanceActorHitAnimation(module_, owner.dobj, (serverTime-commandTime)*0.001f))
    { fail("clock"); continue; }

owner.updatedTime = serverTime;
owner.source = pose;
```

### 2.2 三段

```text
1. 推进到 commandTime（新 clip 的开始时刻）—— 把【旧】clip 推进到那里
2. 若有 change ⇒ 装新 goal（node）
3. 从 commandTime 推进到 serverTime —— 推进【新】clip
```

**注释**：

```cpp
// Advance the previous clip before its successor's goal is installed.
```

**"在它的后继者的 goal 被装上之前推进前一个 clip。"**

### 2.3 `commandTime` 的三元条件

```cpp
changed && !fresh
    ? clamp(pose.animationStartTime, owner.updatedTime, serverTime)
    : owner.updatedTime
```

**两种情形**：

```text
changed && !fresh  ⇒ commandTime = clamp(动画起始时刻, 上次更新, 服务器时间)
否则                ⇒ commandTime = owner.updatedTime（不推进第一段）
```

**`clamp` 的原因**：动画起始时刻可能早于上次更新（快照延迟）或晚于当前时间。

### 2.4 为什么 `fresh` 不推进第一段

**新建的 DObj 没有"前一个 clip"** —— 所以直接从 `updatedTime` 开始。

### 2.5 三段共用的 `advanceActorHitAnimation`

**三个调用**：

```text
"previous-clock"  第一次推进
"goal"            装 goal
"clock"           第二次推进
```

**加上 `"owner-changed"` 共四个新阶段名** —— **总计到 6507 行有 22 个阶段名**。

### 2.6 `entity.modelScale` 的三分量填充

```cpp
std::fill_n((float*)((std::byte*)owner.dobj + DObjScaleOffset),
            DObjScaleComponentCount, entity.modelScale);
```

**`DObjScaleOffset = 200`（0xC8）、`DObjScaleComponentCount = 3`** —— 与 §198 一致。

**所以这里填的是三个分量** —— 修正了 §198 里"只写 X 会拉伸"的问题。

**注意 `entity.modelScale`** —— 但 `SvCollisionEntity` 有 `modelScale` 字段吗？§`sv_collision_mp.hpp` 里有 `float modelScale{1.0f}` ✓

### 2.7 `owner.updatedTime` 的初值

```cpp
owner.updatedTime = pose.animationStartTime <= serverTime
    ? pose.animationStartTime : serverTime;
```

**取两者较小** —— 防止未来时间戳导致负的 elapsed。

## 三、`prepareNativeServerDObjPoses`：代际与 arena 重置

```cpp
nativeServerDObjSkelArenaUsed_ = 0;
if (++nativeServerDObjSkelEpoch_ == 0)
    ++nativeServerDObjSkelEpoch_;
```

### 3.1 两行

```text
1. arena 用量归零
2. 代际自增；若回绕到 0 则跳过 0
```

**"若回绕到 0 则跳过 0"** —— 因为 **0 可能被用作"无代际"哨兵**。

**而 §224 里 `currentEpoch = epoch == nativeServerDObjSkelEpoch_ && matrices`** —— 所以只要代际不同就重新分配。

### 3.2 每次 `prepareNativeServerDObjPoses` 都递增代际

**所以 arena 每帧归零、所有 DObj 每帧重新分配** —— 除非 `invokeDObjCalcSkel` 有内部缓存。

**这意味着 arena 的"只增不减"只在【单帧内】** —— 跨帧会重置。

## 四、两个 part-bit 来源的选择

### 4.1 `svFlags` 的 bit 2

```cpp
// CODREF(sv_trace): pose the bones the trace will actually read.
// SV_PointTraceToEntity 0x005FB510 chooses its part-bit source at
// 0x005FB717 on `test byte ptr [gentity + 0x112], 4` - svFlags bit 2
// - and this project sets exactly that bit for every ScriptModelDObj
// and clears it for player capsules.
```

**`+0x112` 是 `svFlags`** —— 与 §225 里 `ServerFlagsOffset = 0x11A` **不一致**！

**§225 说 `svFlags = 0x11A`，而这里是 `+0x112`。**

**这是一处需要指出的矛盾** —— 而 §225 的注释说"0x110..0x117 是嵌入式 entityState 的最后八个字节"，那 `0x112` 就在那段里。

**所以这里 `entity + 0x112` 读的是 `entityState` 的字段，而不是 `entityShared` 的 `svFlags`。**

**但 `logNativeServerDObjGeomDiagnostics` 里也读 `entity + 0x112`**（见下）—— 两处一致。

**而 §225 的 `logNativeCapsuleCandidacy` 读 `0x11A`** —— 三处里两处用 `0x112`、一处用 `0x11A`。

**这是一个真实的矛盾，需要记为未闭合点。**

### 4.2 两个变体的选择

```cpp
const auto partBitsRecovered =
    entity.shape == SvCollisionShape::ScriptModelDObj
    ? invokeDObjContentsTracelinePartBits(dobjContentsTracelinePartBits_,
          dobj, contentMask, partBits, &exceptionDetails)
    : invokeDObjGeomTracelinePartBits(dobjGeomTracelinePartBits_,
          dobj, partBits, &exceptionDetails);
```

**按 shape 选，而不是按 `svFlags`** —— 虽然注释用 `svFlags` 解释理由。

**因为本项目自己设那个 bit**（`sv_native_server_entity_mp.cpp`）—— 所以 shape 与 bit 应当一致。

### 4.3 那次"骨架塌到模型原点"

```text
Asking the locational variant for a script model's bones leaves every bone
the contents trace reads uncomputed, and an uncomputed bone keeps the zeroed
matrix this function just allocated - so the whole skeleton collapses onto
the model origin and becomes one large volume that swallows bullets and
reports hit location 0.
```

**四步**：

```text
1. 用 locational 变体问 script model 的骨骼
2. contents trace 读的那批骨骼没被算
3. 未算的骨骼保留刚分配的零矩阵
4. ⇒ 整个骨架塌到模型原点，变成一个吞子弹的大体积，命中位置报 0
```

### 4.4 实测数字

```text
Measured on 2026-08-17: 36-bone script models posed with every translation
at zero, and a respawned player behind one absorbed a full magazine at
entity 324 with group=0 while the same weapon had just scored 59-unit
head shots.
```

```text
36 骨 script model，每个平移都为零
重生的玩家躲在它后面，在实体 324 上吸收整本弹匣，group=0
而同一把武器刚刚打出 59 单位的爆头
```

**"整本弹匣被吞"** —— 这是一个非常具体的症状。

## 五、`reportEmptyPartBits`：那条"名字要叫出来"

```cpp
const auto reportEmptyPartBits = [&](const std::array<uint32,8>& bits) {
    // OLMOD(player-dobj-lifecycle-diagnostics): a live player whose
    // DObj yields no traceline bones is invisible to the bone test
    // while remaining a perfect broadphase candidate, and
    // prepareNativeServerDObjPose returns true without posing or
    // logging anything. Name it.
    if (entity.bodyRole != SvCollisionBodyRole::Player) return;
    if (any_of(bits, v != 0)) return;
    
    snprintf(line, sizeof(line), " models=%u hideMask=0x%08lX",
        *(const uint8*)((const std::byte*)dobj + DObjModelCountOffset),
        *(const uint32*)((const std::byte*)dobj + DObjModelHideMaskOffset));
    reportPlayerDObjState(entity.entityNum, PlayerDObjState::NoTracelineBones, line);
};
```

### 5.1 三个条件

```text
1. 必须是 Player（不是演员）
2. partBits 全零
3. 才报
```

### 5.2 为什么必须叫出来

**"一个 DObj 不产出任何 traceline 骨骼的活玩家，对骨骼测试不可见，却仍然是一个完美的 broadphase 候选，而 `prepareNativeServerDObjPose` 返回 true 却不摆姿也不记录任何东西。"**

**这是 §225 里"仪器瞎了"的另一面** —— 一个返回 true 但什么都没做的函数。

### 5.3 两个诊断字段

```text
models        ← DObjModelCountOffset (+9)
hideMask      ← DObjModelHideMaskOffset (+12)
```

**`hideMask`** —— 与 §221 里"`sub_CE69A0` 跳过 `DObj_s +0x0C` 标志的模型"一致。

## 六、`Healthy` 的判断

```cpp
if (entity.bodyRole == SvCollisionBodyRole::Player &&
    any_of(partBits, bits != 0))
{
    reportPlayerDObjState(entity.entityNum, PlayerDObjState::Healthy);
}
```

**"玩家 + partBits 非零 = 健康"**

**注意 `Healthy` 是无条件的**（只要满足两个条件）—— **而 `reportPlayerDObjState` 内部有三态去重**，所以只在状态变化时记录。

**这是四态收敛的完整路径**：

```text
DObj 不存在      ⇒ DObjAbsent
partBits 全零    ⇒ NoTracelineBones
partBits 非零    ⇒ Healthy
（customization 缺失由上层报）
```

## 七、`logNativeServerDObjGeomDiagnostics`：一次性诊断

```cpp
if (!dobjGeomDiagnosticsEnabled() ||
    entityNum >= nativeServerDObjGeomDiagnosticsLogged_.size() ||
    nativeServerDObjGeomDiagnosticsLogged_[entityNum])
    return;
nativeServerDObjGeomDiagnosticsLogged_[entityNum] = true;
```

**三个条件**：开关、范围、**已记过**。

**`nativeServerDObjGeomDiagnosticsLogged_` 是 `array<bool, 18>`**（§190）—— 所以只覆盖前 18 个实体。

### 7.1 它读的字段

```text
entity + 0x112              svFlags
dobj + DObjModelCountOffset (+9)      models
dobj + DObjModelHideMaskOffset (+12)  modelHideMask
dobj + DObjPoseMatricesOffset (+152)  poseMatrices
dobj + DObjModelPointersOffset (+192) modelArray
priorityMap.size() 与 KnownLocationalPriorityCount (20)
```

**六个字段** —— 而 `svFlags` 又用了 `0x112`（与 §225 的 `0x11A` 矛盾）。

### 7.2 日志格式

```text
"DObj geom diagnostics entity=%lu svFlags=0x%02X dobj=%p
 models=%u modelHideMask=0x%08lX poseMatrices=%p
 modelArray=%p priorityBytes=%zu knownPriorityBytes=%zu"
```

**九个字段** —— 把"指针值"也打印出来，因为这些都是该被填好的。

## 八、关键结论

1. **三段时钟**：推进到 commandTime → 装新 goal → 推进到 serverTime。
2. **`clamp(动画起始, 上次更新, 当前时间)`** 防止时间戳异常。
3. **`fresh` 不推进第一段**，因为新建 DObj 没有"前一个 clip"。
4. **`modelScale` 填三个分量**，修正了"只写 X"的问题。
5. **代际每次递增、arena 每帧归零** —— "只增不减"只在单帧内成立。
6. **`svFlags` 在三处用了两个不同偏移**（`0x112` vs `0x11A`）—— 一处矛盾。
7. **用错 part-bit 变体 ⇒ 骨架塌到模型原点 ⇒ 吞整本弹匣、命中位置报 0**。
8. **四态收敛**：DObjAbsent / NoTracelineBones / Healthy / CustomizationAbsent。

## 九、未闭合点

- **`svFlags` 的偏移矛盾（`0x112` vs `0x11A`）需要核对**。
- `array<int32,64>` / `array<string,64>` / `array<bool,18>` 三种诊断数组的容量不一致。
- `EngineBindings.cpp` 6706 行之后未读取。
