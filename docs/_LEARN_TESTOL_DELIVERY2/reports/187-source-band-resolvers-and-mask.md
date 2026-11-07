# 187 · 三个"按名字查索引"的解析器与一次"成功但是错的"

## 一、范围

本报告学习 `EngineBindings.hpp` 1375–1634 行。

## 二、三个 band 解析器，同一个理由

```cpp
resolveModelConfigStringIndex(modelName)     // 模型带
resolveWeaponConfigStringIndex(weaponName)   // 武器带
resolveAnimConfigStringIndex(animName)       // 动画带
```

注释（动画那个，但三个共用）：

> **形状与模型解析器相同，理由也相同：客户端在地图加载时重建自己的带，所以记录在别处的数字命名的是另一个动画。**
> **当本引擎不持有该 xanim 时返回 nullopt，调用方必须把它当作"什么都不播"而不是替换成邻居。**

武器那个还有一句：

> **这里没有 findXAsset 预检：带【就是】客户端解析的注册表，所以不在里面的名字就不是本场比赛能引用的武器。**

## 三、三个 band 全量枚举（地图加载期）

```cpp
modelConfigStringBand()    // 每一条非空
animConfigStringBand()     // 4096 次读
effectConfigStringBand()   // 事件参数 + 名字，唯一的地面真值来源
```

`animConfigStringBand()` 注释：**"仅在地图加载时——4096 次读"**。

`effectConfigStringBand()` 注释：**"与 animConfigStringBand 同一条单遍规则，而且是地面真值效果名的唯一来源"**。

## 四、`?N` 触发器不能走 cmodel 查询——那次"成功但是错的"

### 4.1 `resolveTriggerModelHulls` 存在的理由

```cpp
// THIS EXISTS BECAUSE resolveBrushModelCollision CANNOT DO IT. `?N` indexes
// MapEnts.trigger; that function indexes the clipmap's cmodel list. Feeding it
// a trigger index returns an unrelated brush and reports SUCCESS -- measured
// 2026-09-01 on zm_factory_sh, where all 32 zone volumes "resolved" and every
// one was wrong (`?2` is half (187.0, 6.5, 67.0) in the map and came back as
// (3.0, 45.5, 57.5)).
```

**三个数字**：`?2` 的真实半尺寸 `(187.0, 6.5, 67.0)`，返回的 `(3.0, 45.5, 57.5)`；**32 个区域体积全部"成功"而每一个都是错的**。

> **不要把触发器体积走 cmodel 查询这条路。**

### 4.2 返回精确 hull 而不是包围盒

> **精确返回 hull，含 slab**，这样调用方可以正确地测试包含关系而**不必退而求其次用它们的包围盒**。

## 五、两个受保护标志的完整契约

```cpp
writeNativeProtectedPlayerStateFlags(state, plaintextFlags)
readNativeProtectedPlayerStateFlags(state, flags)
captureNativeProtectedPlayerStateFlags(state, fallbackPlaintextFlags)
```

注释给出三条关键：

1. **"明文写它们会把每个玩家都发布成 ET_INVISIBLE"** —— 必须通过引擎的 SET 访问器；
2. **"引擎的存储【替换】ol-mod 读 otherFlags 的那个明文字"** ⇒ 调用者必须在原生调用返回后用 `capture...` 交还；
3. **"引擎在那个字里保存状态，所以盲写会丢掉它放在那里的东西"** —— 这是 read 存在的理由。

`captureNativeProtectedPlayerStateFlags` 的注释：

> 原生阶段之后：通过 getter 把引擎更新过的标志取回来，把**它**留在 `ps+0x10` 作为 ol-mod 的明文视图。**读失败就回退到被保护的那个值**，那正是旧行为。

## 六、死亡/出生/通用动画的三个入口

```cpp
runServerDeathAnimation(playerState, randomSeed, conditions)
runServerSpawnAnimation(playerState, randomSeed)
runServerAnimationEvent(playerState, animationEvent, randomSeed, conditions*)
```

出生那个注释：

> **躯干动画是事件驱动的，没有 per-frame 写入者，所以一条新的命必须触发 `RAISEWEAPON` 来重新建立它。**

这解释了为什么"出生"是一个独立的调用而不是状态复位。

## 七、角色模型名的**两条路**与它们的时序差

### 7.1 第一条：从 DObj 缓存读

```cpp
// The names resolveCharacterModelNames last produced for one entity, kept so the
// match-end `|` precache burst does not have to re-run the resolver
```

### 7.2 第二条：从角色记录读（这是本组的关键）

```cpp
// THE CHARACTER'S BODY MODEL NAME, from the character record and NOT from the
// DObj. Section 168: characterModelNames reads what the DObj build cached, and
// that arrives a frame or more after the first customization exists, so anything
// derived from it is zero in the first clientInfo written for a player. This
// answers on the first frame.
```

**时序差**：

```text
DObj 缓存的模型名：第一条 customization 之后【一帧或更多】才到
所以第一个写出的 clientInfo 里，从它派生的任何东西都是零
```

**这正是"玩家隐形"的机制**：第一个 clientInfo 的 modelIndex 为零 ⇒ 客户端没模型。

而第二条路**第一帧就能答**。

## 八、十二个 dword 是 384 位选择掩码

### 8.1 反汇编

```text
80e729  cmp   [eax+24h], edi              ; charDef+36 = option COUNT
80e732  mov   ecx, edi / and ecx, 1Fh
80e737  mov   edx, 1  / shl edx, cl       ; 1 << (i & 31)
80e743  test  [ebx+ecx*4+10h], edx        ; request+0x10 == the twelve dwords
80e74d  mov   edx, [eax+28h]              ; charDef+40 = option LIST
80e750  movzx eax, word ptr [edx+edi*2]   ; optionList[i]，一个 ITEM ID
```

### 8.2 语义

> **所以 `dword[i/32]` 的第 `i` 位选择 `optionList[i]`**，而角色定义——**从 `characterItemId` 到达，它已经作为字段 20 在线上**——提供那个列表。

### 8.3 为什么这块**不需要解码键**

> **双方索引同一张 per-character 表。**

**这是与 profile 那些混淆字段的根本区别**：那些是服务端与客户端各持一份不同的编码，这个不是。

### 8.4 缺席的 id 让位**清零**

> 一个不在选项列表里的已装备 id **让它的位保持清零**，**那是角色自己的默认件，绝不是错的一件**。

**"失败即零 = 默认"** 而不是"失败即错"。

## 九、关键结论

1. **三个 band 解析器共用一个理由**：客户端重建自己的带，所以别处的数字无效。
2. **"解析成功但返回错的"** 是 `?N` 走 cmodel 查询的失败形态——32 个全错而全部报成功。
3. **受保护标志的完整契约是"写 → 调 → 读回"三步**，缺任何一步都会丢掉引擎的状态。
4. **同一个信息有两条获取路径时，要选"最早能答"的那条**——DObj 缓存晚一帧，正是玩家隐形的直接原因。
5. **掩码位为 0 = 用默认件**，不是错误。
6. **不需要解码键的字段意味着双方索引同一张表**——这与混淆字段形成对照。

## 十、未闭合点

- `characterOptionSelectionMask` 的完整签名（1634 行之后）未读取。
- `EngineBindings.hpp` 的剩余部分与 `EngineBindings.cpp` 全部未读取。
