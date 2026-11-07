# 226 · 骨架高度采样、演员击打姿势的动画别名查找

## 一、范围

本报告学习 `EngineBindings.cpp` 6308–6507 行。

## 二、骨架采样的双重触发

```cpp
constexpr uint32 SkeletonSampleInterval = 300;
const auto sampled = nativeServerDObjSkeletonLogCounter_++ % SkeletonSampleInterval == 0;

const auto heightBucket = (int32)(highest / 8.0f);
auto& lastBucket = entityNum < nativeServerDObjSkeletonHeight_.size()
    ? nativeServerDObjSkeletonHeight_[entityNum]
    : nativeServerDObjSkeletonHeightScratch_;
const auto changed = lastBucket != heightBucket;
lastBucket = heightBucket;
if (!sampled && !changed) return;
```

### 2.1 两个触发

```text
1. 每 300 次重算采样一次
2. 高度桶（highest / 8）变化时立即报
```

### 2.2 为什么用"桶"而不是精确值

**`highest / 8.0f` 取整** —— 所以**只有跨过 8 单位的台阶才算"变化"**。

**避免每帧微小抖动触发**。

### 2.3 为什么"变化"必须立即报

```cpp
// Report a CHANGE in this entity's posed height as well as the
// periodic sample: without the entity number these lines could not be
// attributed at all, and a player whose skeleton collapses after a
// respawn is exactly the case that has to be visible the frame it
// happens rather than whenever the sampler next fires.
```

**"一个重生后骨架坍塌的玩家，正是那种必须在它发生的那一帧可见、而不是等采样器下次触发的东西。"**

### 2.4 溢出保护

```cpp
auto& lastBucket = entityNum < nativeServerDObjSkeletonHeight_.size()
    ? nativeServerDObjSkeletonHeight_[entityNum]
    : nativeServerDObjSkeletonHeightScratch_;
```

**`nativeServerDObjSkeletonHeight_` 是 `array<int32, 64>`**（§190）—— 所以实体号 ≥ 64 落到 `scratch_`。

**但 `scratch_` 是单个值** ⇒ **所有 ≥64 的实体会共享它** ⇒ 会互相干扰。

**这是可以指出的不足**（与 §224 里 `nativeServerAnimationReport_` 的 64 项是同一类）。

## 三、四个统计量

```cpp
auto highest = -inf;
auto lowest = +inf;
size_t highestBone{};
uint32 zeroTranslations{};
std::string tail;

for (bone = 0; bone < boneCount; ++bone)
{
    translation = matrices + bone*32 + 16;    // AnimMatTranslationOffset
    memcpy(position, translation, 12);
    if (!isfinite(position[2])) continue;
    if (position[0]==0 && position[1]==0 && position[2]==0) ++zeroTranslations;
    if (position[2] > highest) { highest = position[2]; highestBone = bone; }
    lowest = min(lowest, position[2]);
    if (bone < 12) { tail += " %zu:%.1f"; }
}
```

### 3.1 四个统计

```text
highest / highestBone     最高 Z 与它所在骨骼
lowest                    最低 Z
zeroTranslations          平移全零的骨骼数
tail                      前 12 根骨骼的 Z
```

### 3.2 `zeroTranslations` 的意义

**"平移全零的骨骼数"** —— 如果**整个骨架都零**，那说明 `DObjCalcSkel` 什么都没算。

**这是一个"骨架是否真的被算过"的判据**。

### 3.3 `AnimMatTranslationOffset = 16`

```text
DObjAnimMat: quat[4] 16 字节 + trans[3] 12 + transWeight 4 = 32
```

**`trans` 在 `+16`** ✓（`quat[4]` 是 4 个 float = 16 字节）

### 3.4 前 12 根骨骼

**为什么是 12** —— 因为日志行长限制。**`tail` 每项 `" %zu:%.1f"` 约 10 字节，12 项 = 120 字节**，加上其它字段在 384 字节内。

## 四、那三个具体数字的解释

```cpp
// CODREF(bg_update_player_dobj): sub_C9AD60 (VA 0x005FAD60) multiplies a
// live player's whole locational box by entityState +0x54 when it is
// not 1.0, and BG_UpdatePlayerDObj carries the same word into DObj_s
// +0xC8 as the model scale. A uniform scale there is the one thing that
// reproduces every measured hit height at once - a 0.7 would put the
// neck at 38.5 against the 36.0 and 38.9 actually measured - so read
// both rather than trusting the source-side value.
```

### 4.1 那个假设被数字支持

```text
若 scale = 0.7：
    脖子在 38.5（= 55 × 0.7，其中 55 是标准脖高）
实测：36.0 与 38.9
```

**"一个 0.7 会一次性复现每一个实测命中高度"**

**这是一个"单一参数解释全部观测"的假设** —— 所以读 `dobjScale` 来验证。

### 4.2 三个偏移

```text
entityState +0x54      model scale 的源
DObj_s +0xC8           模型 scale 的落地
sub_C9AD60 (0x5FAD60)  乘 locational box 的那个函数
```

### 4.3 `DObjModelScaleOffset = 0xC8`

**与 §198 里 `DObjScaleOffset = 200`（0xC8）一致** ✓

**而 §198 说它是三分量向量** —— 但这里只读 X：

```cpp
const auto modelScale = *(const float*)(dobj + DObjModelScaleOffset);
```

**只读 X 分量** —— 因为诊断只需要一个值（而注释说"只写 X 会拉伸"）。

## 五、`releaseActorHitPoses`：两处清理

```cpp
for (size_t i = 0; i < actorHitPoseOwners_.size(); ++i)
{
    auto& owner = actorHitPoseOwners_[i];
    if (owner.tree[0]) clearNativeXAnimTree(xanimFreeInfo_, owner.tree.data());
    if (owner.dobj && serverDObjGetAdapter((int)i) == owner.dobj)
        serverDObjFreeAdapter((int)i, 0);
    owner = {};
}
```

### 5.1 **相同的清理代码出现了两次**

`releaseActorHitPoses` 与 `synchronizeActorHitPoses` 里的 `release` lambda **逐行相同**。

**这是一处明显的重复**。

### 5.2 那条"只有仍是我们的才释放"

```cpp
if (owner.dobj && serverDObjGetAdapter((int)i) == owner.dobj)
    serverDObjFreeAdapter((int)i, 0);
```

**三个条件**：

```text
owner.dobj 非空
该槽当前的 DObj 就是我们的
才释放
```

**"如果槽已被别人占用，不释放"** —— 与 §216 里 `restoreServerAnimConditionStorage` 的带条件 CAS 同一条纪律。

## 六、`synchronizeActorHitPoses` 的完整流程

```cpp
if (!actorHitPosesEnabled_) return;

// 1. 标记哪些实体本帧有 pose
std::array<bool,2048> present{};
for (const auto& entity : entities)
    if (entity.actorHitPose && entity.entityNum < present.size())
        present[entity.entityNum] = true;

// 2. 释放不再有 pose 的
for (i = 0; i < present.size(); ++i)
    if (!present[i] && (owners_[i].dobj || owners_[i].failed))
        release(i);

// 3. 取 anims
void* anims{};
memcpy(&anims, storage + 708228 + 3*20, sizeof(anims));
if (!anims || !readableSpan(anims, 12)) return;
const auto nodeCount = *(const uint32*)anims;
if (nodeCount < 2 || nodeCount > 4096) return;

// 4. 安装存储
std::byte* previousContext{};
if (!installServerAnimConditionStorage(previousContext)) return;

// 5. 逐实体处理
for (const auto& entity : entities) { ... }
```

### 6.1 那个 `708228 + 3*20` 的来历

```cpp
// CODREF(xanim_shared_actor_blend): 40B210 family3 record, populated
// once by the native parser during this level's opt-in load.
memcpy(&anims, storage + 708228 + 3*20, sizeof(anims));
```

**`708228 = 0xACEC4`**？

**验算**：`0xACE70 = 708208`（§198 的 `AnimTreeContextOffset`）

```text
708208 + 20      = 708228   ← 3*20 = 60 之前
708228 + 60      = 708288
```

**`708208 + 20 = 708228`** —— 而 `3*20 = 60` ⇒ **总共 `708208 + 80`**。

**所以是"anim-condition 块 + 0x50"**：

```text
0xACE70 + 0x50 = 0xACEC0
```

**`708228 + 60 = 708288 = 0xACEC0`** ✓

**所以 `family3` 记录在 `anim-condition base + 0x50 + family*20`** —— 而这是第 3 个 family（索引 3）。

**五个 family、每个 20 字节、从 `+0x50` 开始** —— 这是 anim-script 的 family 记录表。

### 6.2 `nodeCount` 的范围

```cpp
if (nodeCount < 2 || nodeCount > 4096) return;
```

**`>= 2`** —— 因为至少要有一个根节点加一个子节点？

**`<= 4096`** —— 与 §143 里 `nodeCount` 上限一致。

## 七、动画别名查找

```cpp
// CODREF(xanim_shared_actor_blend): 785870 alias BST is a u16 key,
// u16 node, two pointers. Validate membership before native calls.
const std::uint8_t *link{};
std::memcpy(&link, (const std::byte*)anims + 4, sizeof(link));
std::uint16_t node{};
for (unsigned depth = 0; link && depth < 64; ++depth)
{
    if (!readableSpan(link, 12)) break;
    std::uint16_t key{};
    std::memcpy(&key, link, 2);
    if (key == pose.animation) { memcpy(&node, link+2, 2); break; }
    memcpy(&link, link + (key > pose.animation ? 4 : 8), sizeof(link));
}
if (!node || node >= nodeCount) { fail("animation-alias"); continue; }
```

### 7.1 二叉搜索树布局

```text
节点 12 字节：
+0  u16 key        （动画号）
+2  u16 node       （对应的节点索引）
+4  指针（key < 目标）  ← 或者反向
+8  指针（key > 目标）
```

**`key > pose.animation ? 4 : 8`**：

```text
若 key > 目标  ⇒ 目标在左子树 ⇒ 走 +4
若 key < 目标  ⇒ 目标在右子树 ⇒ 走 +8
```

**所以 +4 是"小的一侧"、+8 是"大的一侧"。**

### 7.2 `anims + 4` 是树根

**`anims` 结构**（从 §206 的 `createNativeXAnimTree`）：

```text
+0  anims（父指针？）
+4  children  ← BST 根
```

**等等** —— §206 里 `createNativeXAnimTree` 创建的是 `{anims, nullptr}`，其中 `fields[0]=anims`、`fields[1]=children`。

**而这里 `anims` 是已存在的（从存储里读出来的 family3 记录），它的 `+0` 是 `nodeCount`**：

```cpp
const auto nodeCount = *static_cast<const std::uint32_t *>(anims);
```

**所以这个 `anims` 的结构是**：

```text
+0  uint32 nodeCount
+4  指针   ← BST 根
```

**与 §206 的树头 `{anims, children}` 结构【不同】**。

**这是两个不同的东西**：§206 的是"每个 DObj 的树头"（8 字节），这里是"family 的动画记录"（nodeCount + BST）。

### 7.3 `depth < 64` 的界

**BST 深度上限 64** —— 防止环或退化树导致死循环。

### 7.4 `node >= nodeCount` 校验

**"在调用原生之前校验成员资格"** —— 因为后续 `DObjCalcSkel` 会用这个 node 索引节点池。

## 八、`fail` lambda：三件事

```cpp
const auto fail = [&](const char* stage) {
    release(entity.entityNum);         // 1. 释放已有资源
    owner.source = pose;               // 2. 记录失败时的 source
    owner.failed = true;               // 3. 标记失败
    if (actorHitPoseLogCount_++ < 64)  // 4. 封顶日志
        log("ZMPOSE refused entity=N stage=S");
};
```

### 8.1 `owner.source = pose` 的意义

**即使失败也记下 `source`** —— 因为 §226 开头那个条件：

```cpp
if ((owner.dobj || owner.failed) && (owner.source.generation != pose.generation || ...))
    release(entity.entityNum);
```

**所以下次 `pose` 变化时能检测到并重试**。

**这是"失败也记录尝试过的输入"** —— 让失败可重试。

### 8.2 四个失败阶段

```text
"animation-alias"
"foreign-owner"
"models"
"dobj-create"
```

## 九、`nativeConfigString` 取模型名

```cpp
const auto name = readCString(
    nativeConfigString(ModelConfigStringBase + indices[i]), 128);
if (!indices[i] || !name || name->empty()) { resolved = false; break; }
models[i].model = findXAsset(AssetTypeXModel, name->c_str(), false).data;
```

### 9.1 `ModelConfigStringBase + index`

**`ModelConfigStringBase = 2568`**（§`sv_gamestate_mp.hpp`）

**所以模型名来自 configstring 带** —— 与 §187 里 `resolveModelConfigStringIndex` 的机制一致。

### 9.2 三个模型

```cpp
const std::array<uint16_t,3> indices{pose.body, pose.head, pose.lower};
const auto modelCount = pose.lower ? 3u : 2u;
```

**有 lower 则三个，否则两个** —— 因为 `pose.lower` 为零表示没有下肢。

## 十、`ignoreCollision` 的规则

```cpp
// Native agent ignoreCollision bit0 applies to attachment0.
// Empty attachment tag merges shared skeleton bones (52FBE0).
// Agent mask bit0 excludes head/neck-cap; lower body is solid
// to bullets, matching native multipart agent composition.
models[i].ignoreCollision = i == 1 ? 1 : 0;
```

**只有索引 1（head）设 `ignoreCollision = 1`** —— 所以**头/颈帽被排除碰撞而身体对子弹是实心的**。

**"匹配原生多部件 agent 组合"**。

## 十一、关键结论

1. **双重触发**：每 300 次采样 + 高度桶变化立即报。
2. **高度桶 `/8`** 避免微小抖动。
3. **`zeroTranslations` 是"骨架是否真被算过"的判据**。
4. **单一 `scale=0.7` 能一次性复现所有实测命中高度** —— 所以读 `dobjScale` 验证。
5. **清理代码在两处重复**（`releaseActorHitPoses` 与 lambda）。
6. **"只有仍是我们的才释放"** —— 与 `restoreServerAnimConditionStorage` 同一条纪律。
7. **`family3` 记录在 `anim-condition base + 0x50 + family*20`**。
8. **`anims` 的结构是 `{nodeCount, BST root}`，与 §206 的树头 `{anims, children}` 不同**。
9. **BST 查找用 `key > target ? +4 : +8`**，深度上限 64。
10. **失败也记录 `source`** —— 让失败可重试。

## 十二、未闭合点

- `array<int32,64>` 与 `array<string,64>` 对实体号上限 2045 太小，≥64 的实体会共享 `scratch_`。
- `EngineBindings.cpp` 6507 行之后未读取。
