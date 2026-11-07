# 222 · 五项重建条件、六条被推翻的旧结论、稳定的空串

## 一、范围

本报告学习 `EngineBindings.cpp` 5510–5710 行。

## 二、重建条件：**五项**

```cpp
if (slot.selectionIds != customization.selectionIds ||
    slot.worldModelContext != worldModelContext ||
    slot.spawnGeneration != spawnGeneration ||
    !*(const uint32*)characterInfo ||
    !presentDObj || !tracelineBonesAvailable)
```

### 2.1 前三条是"表现变了"

```text
1. selectionIds 变了
2. worldModelContext 变了
3. spawnGeneration 变了
```

### 2.2 后三条是"状态坏了"

```text
4. characterInfo 的 infoValid 为零
5. presentDObj 为空
6. tracelineBonesAvailable 为假
```

**`!*(const uint32*)characterInfo` 是 `infoValid`** —— 因为 `characterInfo +0` 是 infoValid。

## 三、六条被推翻的旧结论

这是本组最有价值的部分。

### 3.1 第 1 条：`spawnGeneration` 项的两轮反复

```text
e6e64e7 added this term for the wrong reason and 98954f9 removed
it for the wrong reason; both missed that the wipe alone rebuilds
nothing while the DObj persists.
```

**"两次都错过了：在 DObj 持续存在时，单靠擦除什么也重建不了。"**

### 3.2 第 2 条：那次"死亡姿势存活"的诊断是错的

```text
e6e64e7 added a per-LIFE rebuild on the diagnosis that "the death
pose survives the respawn". That diagnosis was wrong. At the time
BG_SetLerpFrameAnimation VA 0x00409BF0 was bailing at 0x00409C2E
on every frame for every player, because the get-DObj callback
read a map this project's DObjs are not in, so NO animation was
ever set and the pose was not animation-driven at all.
```

**四步**：

```text
1. 当时的观测是"死亡姿势存活到重生"
2. 但真相是 BG_SetLerpFrameAnimation 每帧每个玩家都在 0x00409C2E 早退
3. 原因：get-DObj 回调读的项目 DObj 不在的表
4. 所以【根本没有动画被设置】，姿势不是动画驱动的
```

**"没有一个死亡姿势可存活；'正确的第一条命姿势'是两个不同角色以 0.1 单位的一致性产出的默认值。"**

**"两个不同的角色产出的默认值一致到 0.1 单位"** —— 这正是"看起来像正确"的原因。

### 3.3 第 3 条：擦除现在是**纯破坏性的**

```text
With that fixed and the animation clock running, the wipe is
purely destructive. MEASURED 2026-08-17 16:52-16:53: across a
respawn the legs asset and fraction are IDENTICAL (0x55C9C768,
1.000) while the posed height falls 63.87 -> 37.38 and the
highest bone drops from 133 to 71.
```

**五个数字**：

```text
legs asset    0x55C9C768  （不变）
legs fraction 1.000       （不变）
posed height  63.87 → 37.38
highest bone  133 → 71
```

**"腿部资产与分数完全相同，而姿态高度从 63.87 掉到 37.38"** —— 所以问题不在腿。

### 3.4 第 4 条：唯一差异是**躯干** lerp 帧

```text
The single difference is the TORSO lerp frame - alive it holds
populated state at t=13750, after the wipe it is zeroed at t=0 -
and it can never be rebuilt, because torsoAnim is 0 on this server
and 0x0040A2C0 exits to 0x0040A5E7 when the index is zero.
The wipe destroys the only thing holding the upper body up.
```

**"擦除摧毁了唯一支撑上半身的东西。"**

**而 `torsoAnim` 恒为 0 是一个独立缺陷**（§154 里 `SvNativeCharacterInfoTorsoLerpFrameOffset = 0x1BC`）。

### 3.5 第 5 条：`torsoAnim` 缺陷的记录

```text
TODO(CODOL): torsoAnim being permanently 0 is a SEPARATE and
still-open defect - retail carries 10-17 distinct torso values
per life (2d-quindecies) and this build reached 1547 exactly once
before falling to zero, so the machinery works and the selection
does not. Exit when torsoAnim varies with weapon state.
```

**"机制能用而选择不工作"** —— 因为**它曾经达到过 1547 一次**。

**这是"证明能力存在"的证据** —— 一个值只出现过一次，但足以说明路径是通的。

### 3.6 第 6 条：`G_SafeDObjFree` 的顺序

```text
CODREF(client_end_frame): BO1 ClientEndFrame 0x005FD1D0 does, at 0x005FDD2A:

  cmp  [ebp+bChanged], 0
  jz   short loc_5FDD3C
  call G_SafeDObjFree(ent)          <- FREE it
  call Com_GetServerDObj(ent->s.number)   <- now NULL
  call BG_UpdatePlayerDObj(-1, pDObj, es, ci, attachIgnoreCollision)
  call BG_PlayerAnimation(-1, es, ci)
```

**"所以一次改变了的呈现是从一个 NULL DObj 重建的，而不是就地更新。"**

**而本项目从不释放** —— 所以同一个 DObj 在整个关卡生命期里每帧被交回，**带着它的骨架与模型状态跨过每一次死亡**。

**"那才是跨过一次重生存活下来的状态 —— 不是 characterInfo，不是 lerp 帧，也不是躯干动画，那些都被测过并清过。"**

## 四、清理的顺序

```cpp
std::byte *previousTreeContext{};
if (installServerAnimConditionStorage(previousTreeContext))
{
    clearNativeXAnimTree(xanimFreeInfo_, tree);
    restoreServerAnimConditionStorage(previousTreeContext);
}
if (presentDObj)
    serverDObjFreeAdapter((int32)entityNum, 0);
std::ranges::fill(characterInfoBytes, std::byte{});
```

### 4.1 三步

```text
1. 在 [安装我们的 anim-condition 存储] 的作用域内清 XAnim 树
2. 释放 DObj
3. 清 characterInfo 字节
```

### 4.2 为什么清树必须先安装存储

```text
XAnimFreeInfo VA 0x006497C0 dereferences the anim-condition
base at VA 0x07817B80 (0x006497CA) and, when it is non-null,
CALLS the callback at +0x96E10 with the clock at +0x96DD8.
This branch runs long before the install below, so without this scope
the clear would read whichever context the client left in that
global and call a foreign function pointer out of it.
```

**"没有这个作用域，清除会读到客户端留在那个全局里的任何上下文，并从中调用一个外来的函数指针。"**

**"调用一个外来的函数指针"** —— 这是最危险的一类。

### 4.3 顺序的证据

`MEASURED 2026-08-17 17:29`：

```text
treeRoot=10 both before the death and after the respawn,
with a fresh DObj and the correct animation asset,
and the pose still 51.21 against 65.26.
```

**"树根前后都是 10，DObj 是新的，动画资产也对，而姿态仍然是 51.21 对 65.26。"**

**所以清树不是解法** —— 但**它仍是正确的**,因为：

> **`XAnimFreeInfo` 把那些节点还给池并把树的 children 字段留为 0，即正好是一个新建树有的 `{anims, 0}` —— 这才是让第 N 条命的输入与第 1 条命相同的东西。**

**"让第 N 条命的输入与第 1 条命相同"** —— 这是目的，即使当前仍不完美。

## 五、字段初始化：那七个偏移

```cpp
*(uint32*)characterInfo = 1;                       // +0x00 infoValid
*(const char**)(characterInfo + 24) = modelNames[0] ?: EmptyCharacterModelName;
for (index = 0; index < 10; ++index)
{
    *(const char**)(characterInfo + 32 + 4*index) = EmptyCharacterModelName;   // +0x20 十个附件名
    *(const char**)(characterInfo + 72 + 4*index) = EmptyCharacterModelName;   // +0x48 十个附件标签
}
for (index = 1; index < resolvedModelCount && index <= 10; ++index)
{
    if (!modelNames[index]) break;
    *(const char**)(characterInfo + 32 + 4*(index-1)) = modelNames[index];
}
*(uint32*)(characterInfo + 660) = 1;               // DObjDirty
*(void**)(characterInfo + 900) = tree;             // AnimTree
```

### 5.1 七个偏移的对照

```text
+0x00   1                 infoValid
+0x18   modelNames[0]     基础模型名
+0x20   十个附件名
+0x48   十个附件标签
+0x294  1                 DObjDirty（660）
+0x384  tree              AnimTree（900）
```

**与 §198 里 `CharacterInfoDObjDirtyOffset = 660` 与 `CharacterInfoAnimTreeOffset = 900` 一致**，而**注释里仍写 `+0x1C`** —— 那是旧值。

**`+0x20`（32）与 `+0x48`（72）** 与 §198 的 `CharacterInfoAttachmentNamesOffset = 32` / `CharacterInfoAttachmentTagNamesOffset = 72` 一致。

### 5.2 那条"稳定的空字符串"

```cpp
// NEVER A NULL IN THIS ARRAY. resolveCharacterModelNames now compacts, so
// the range is dense at the source -- but the native loop at 0x0040AD5A
// dereferences every slot before testing it, so a null here is an access
// violation inside the engine rather than a bad model, and the stable empty
// string above is the only thing that terminates the walk safely.
// One sparse resolve cost a whole session of `missing_playerstate`;
// this is the last line of defence and it costs a compare.
```

**"一个稀疏解析花了整整一场会话的 `missing_playerstate`；这是最后一道防线，代价是一次比较。"**

### 5.3 为什么是"稳定的"

```cpp
constexpr char EmptyCharacterModelName[] = "";
```

**`constexpr` 数组** —— 所以它的地址在整个进程生命期不变，且**内容永远是空串**。

**"稳定的空字符串"意味着**：

1. 地址不变（所以原生侧可以安全持有）；
2. 内容不变（所以解引用永远读到 `\0`）；
3. **非 null**（所以原生循环的解引用不会崩）。

**三条同时满足** —— 这是"哨兵对象"的正确构造。

### 5.4 附加循环的 `break`

```cpp
if (!modelNames[index]) break;
```

**遇到 null 就停** —— 与原生循环的"遇到空串就 break"对齐。

### 5.5 `index <= 10` 的上界

```cpp
for (index = 1; index < resolvedModelCount && index <= 10; ++index)
```

**`modelNames[1..10]` 共十项** → 写入 `+0x20 + 4*(index-1)` = `+0x20..0x44` ✓（十个指针）

**而 `modelNames[0]` 单独写到 `+0x18`**。

## 六、日志行：六个布尔 + 两个映射

```text
"player DObj rebuild entity=N selectionChanged=S contextChanged=C infoInvalid=I
 dobjMissing=D noTracelineBones=T animMap=A srvMap=SR"
```

### 6.1 六个布尔对应六项条件

```text
selectionChanged   ← 条件 1
contextChanged     ← 条件 2
infoInvalid        ← 条件 4
dobjMissing        ← 条件 5
noTracelineBones   ← 条件 6
（spawnGeneration 未列出）
```

**缺了 `spawnGeneration`** —— 因为它是"总是会变"的（每次重生），所以列出它没有诊断价值？或者是一处遗漏。

### 6.2 那两个映射的用途

```cpp
// TODO(CODOL): the two DObj maps, side by side. animMap is
// the word BG_SetLerpFrameAnimation's callback reads; a
// zero there with a non-zero srvMap means no animation has
// ever been set for this player. Remove once confirmed.
return " animMap=" + word(ServerAnimDObjMapRva) + " srvMap=" + word(ServerDObjMapRva);
```

**"`animMap` 为零而 `srvMap` 非零意味着从未为这个玩家设置过任何动画。"**

**两个映射并排打印** —— 这正是 §183 里"两个表指向同一个池但索引方式不同"的诊断实现。

## 七、关键结论

1. **六项重建条件**：三项"表现变了" + 三项"状态坏了"。
2. **`spawnGeneration` 项被加了两次、删了两次，两次都理由错误**。
3. **当时的"死亡姿势存活"诊断是错的** —— 真相是动画从未被设置。
4. **"两个不同角色产出的默认值一致到 0.1 单位"** 是它看起来正确的原因。
5. **擦除现在是纯破坏性的**，因为唯一差异是躯干 lerp 帧，而 `torsoAnim` 恒零。
6. **`torsoAnim` 曾达到 1547 一次** —— 证明机制可用而选择不工作。
7. **本项目从不释放 DObj**，所以骨架状态跨死亡存活。
8. **清树必须先安装自己的 anim-condition 存储**，否则会调用外来函数指针。
9. **稳定空串同时满足"地址不变/内容不变/非 null"三条**。

## 八、未闭合点

- `torsoAnim` 恒零的成因仍未解决（`TODO(CODOL)`）。
- 日志缺 `spawnGeneration` 一项。
- `EngineBindings.cpp` 5710 行之后未读取。
