# 221 · 两个变体都要预载：为什么玩家隐形、为什么尸体还能画

## 一、范围

本报告学习 `EngineBindings.cpp` 5306–5510 行。

## 二、解析结果报告：**故意不沉默**

```cpp
// TODO(CODOL): remove once a resolved character has been confirmed against that
// list on a live run and the DObj it produces has been seen. This is deliberately
// NOT silent-when-healthy (section 44a) because "healthy" is exactly what has not
// been established yet.
```

**与 §220 里那个"健康时必须沉默"的仪器相反** —— 因为**"健康"本身还没被确立**。

**两条原则的对照**：

```text
§220 输入指纹：默认沉默，因为健康是已知的
§221 结果报告：故意不沉默，因为健康尚未确立
```

## 三、那个"外部解码器"才是真正的检查

```cpp
// Those came out of the CLIENT's own tables and share no code with this path, so
// the two agreeing is a real check rather than this file agreeing with itself
// (section 67c, and [[codol-judge-output-with-a-foreign-decoder]]).
```

**黄金值**：

```text
tools/runtime/CodolCharacterCategoryDump.py --resolve
545 cha_infbasea -> fpa_infbasea boo_infbasea fja_infbasea
                    han_infbasea00 hea_socomb
```

**"来自客户端自己的表、与本路径不共享任何代码"** ⇒ **两者一致才是真检查**。

**这与 §201 里"对称往返即使两边都错也会通过"是同一条原则** —— 而这里的解法是**用一个外来解码器做对照**。

## 四、FPGA-1a 指纹（第二个）

```cpp
std::uint32_t hash = 2166136261u;
mix(customization.characterItemId);
for (const auto* name : modelNames)
{
    for (const auto* cursor = name; cursor && *cursor; ++cursor)
        mix((uint8_t)*cursor);
    mix(0u);
}
if (!hash) hash = 1u;
```

### 4.1 与 §220 那个的差别

```text
§220：混入【输入】（selectionIds / modelIndex / faction / colour / female）
§221：混入【输出】（characterItemId + 十一个名字的字符）
```

**一个按输入去重，一个按输出去重。**

### 4.2 名字的混入方式

```cpp
for (const auto* cursor = name; cursor && *cursor; ++cursor)
    mix((uint8_t)*cursor);
mix(0u);            // 【每个名字后混一个 0 作为分隔】
```

**`mix(0u)` 是分隔符** —— 否则 `"ab"+"c"` 与 `"a"+"bc"` 会哈希相同。

**`cursor && *cursor`** —— 同时处理 null 指针与空串。

### 4.3 `if (!hash) hash = 1u`

**零被保留给"未记录"**（因为 `reportedResolutionHash` 初值全零）。

**所以真哈希为零时改成 1** —— 与"零是哨兵"的常见问题。

### 4.4 日志内容

```text
"character models RESOLVED entity=N characterItem=I faction=F variant=V
 count=C record=<filled> names=a,b,c,..."
```

**七个字段** —— `variant` 是 `characterVariantSelector(faction)` 的实际值。

## 五、**缓存与仪器分开**：那段"如何在第二次相同解析时丢值"

```cpp
// KEEP THE NAMES. They cost one small vector per entity and they are
// the exact strings the podium's precache burst needs -- see
// driveMatchEndSequence. Stored unconditionally on a successful
// resolution rather than inside the dedupe above, because the dedupe is
// an INSTRUMENT (one log line per distinct input) and using its
// once-only branch to populate state is how a value goes missing on the
// second identical resolve.
```

**"去重是一个仪器，而用它的只执行一次的分支去填状态，正是'第二次相同解析时值丢失'的方式。"**

**这是"仪器与状态必须分离"的精确表述** —— 一个非常常见的错误模式。

## 六、玩家隐形的完整机制

这是本组最重要的一段。

### 6.1 实测

```text
Measured: this server resolved `fpa_goose_ss_m_11` for a player while that
player's client held `fpa_goose_ss_m_15` in its own characterInfo -- same
character, different variant selector, different model NAME.
```

**同一个角色、不同的变体选择器、不同的模型名**：

```text
服务端：fpa_goose_ss_m_11
客户端：fpa_goose_ss_m_15
```

### 6.2 为什么这导致隐形

```text
That is what made players invisible. BG_UpdatePlayerDObj registers the
base model BY NAME and bails at its first branch when the name registers
to nothing, so precaching the server's variant left the client asking for
an asset nobody had loaded.
```

**三步**：

```text
1. BG_UpdatePlayerDObj 按【名字】注册基础模型
2. 名字注册不到任何东西时，它在【第一个分支】就退出
3. 所以预载服务端的变体，让客户端去请求一个没有人加载过的资产
```

**"客户端请求一个没人加载过的资产"** ⇒ **模型解析为 null ⇒ 玩家不可见**。

### 6.3 为什么尸体还能画

```text
The corpse path is let through that same branch by its `eType == 2` escape,
which is why a dead player still drew -- with a fallback body, the
"completely different model" a player reported seeing.
```

**`eType == 2` 是尸体** —— 它**绕过同一个分支**。

**所以死掉的人还能画（用回退身体），活着的人反而不可见。**

**而"回退身体"正是玩家报告"完全不同的模型"的原因。**

### 6.4 变体空间是 `{1, 2}`

```text
sub_61B6C0's caller at 0x61D81B treats anything that is not 1 or 2 as its
own fallback, so the selector space is exactly {1, 2}:
resolve the other one and keep any name it adds.
Whichever the client picks is then resident.
```

**"解析另一个，保留它添加的任何名字 ⇒ 客户端无论选哪个都在缓存里。"**

**这是一个"覆盖全部可能性"的解法** —— 因为空间只有两个值。

### 6.5 实现

```cpp
static std::array<std::pair<uint16_t, std::vector<std::string>>, 18> AlternateVariantNames{};
auto& [resolvedFor, alternates] = AlternateVariantNames[entityNum];
if (resolvedFor != customization.characterItemId)
{
    resolvedFor = customization.characterItemId;
    alternates.clear();
    const auto otherSelector =
        characterVariantSelector(customization.faction) == 1 ? 2 : 1;
    std::array<const char*, 11> otherNames{};
    size_t otherCount{};
    if (resolveCharacterModelNames(customization, otherNames, otherCount, nullptr, otherSelector))
        for (index = 0; index < otherCount; ++index)
            if (otherNames[index] && *otherNames[index])
                alternates.emplace_back(otherNames[index]);
}
for (const auto& name : alternates)
    if (find(cached, name) == cached.end())
        cached.emplace_back(name);
```

### 6.6 两个关键设计

#### 6.6.1 按 `characterItemId` 缓存

```cpp
if (resolvedFor != customization.characterItemId)
```

**只在角色变化时重解析** —— 注释：

> **每个实体的每个角色一次。`updateNativeServerPlayerDObj` 每次调用都解析，所以这里一个未加保护的第二次解析会把一个已经付得太多的成本翻倍 —— 一个玩家把它测成"极其卡顿"。**

#### 6.6.2 **但每次都要重新附加**

```text
But `cached` is CLEARED and refilled on every call, so guarding
the resolve alone would drop the alternate names on the second call and
quietly undo the fix.
```

**"`cached` 每次调用都被清空并重填，所以只保护解析会在第二次调用时丢掉备用名字并悄悄撤销这个修复。"**

**所以是两层**：

```text
解析：按角色变化时才做（昂贵）
附加：每次都做（廉价，且必需）
```

### 6.6.3 `otherSelector` 的求法

```cpp
characterVariantSelector(customization.faction) == 1 ? 2 : 1
```

**因为空间是 `{1,2}`** —— 所以 `1 → 2`、`2 → 1`（以及任何其它值 → 1）。

## 七、动画树的创建：`irreversibleMutationStarted`

```cpp
auto* tree = *(void**)(characterInfo + CharacterInfoAnimTreeOffset);
if (!tree)
{
    auto* anims = *(void* const*)(storage + AnimTreeContextOffset);
    failureStage = "animation_tree_source";
    if (!anims) return false;
    tree = createNativeXAnimTree(hunkAllocXAnim_, anims);
    failureStage = "animation_tree_allocation";
    if (!tree) return false;
    // HunkAllocXAnim has process/level lifetime and no matching free
    // contract. Any later rejection must not retry this transaction.
    irreversibleMutationStarted = true;
}
```

### 7.1 两个新阶段名

```text
"animation_tree_source"       ← anims 为空
"animation_tree_allocation"   ← 分配失败
```

**加上 §220 的四个，共六个阶段名**。

### 7.2 为什么这里设 `irreversibleMutationStarted = true`

**"`HunkAllocXAnim` 有进程/关卡生命期，而没有匹配的释放契约。任何后续拒绝都不能重试这个事务。"**

**即：一旦分配了树头，它就无法回收** —— 所以调用方必须知道"这个事务不能重试"。

## 八、`worldModelContext` 的三段打包

```cpp
const auto worldModelContext =
    (uint32)customization.faction |
    (customization.female ? 1u << 8 : 0u) |
    ((uint32)customization.color << 16);
```

**三段**：

```text
bit 0    faction（0 或 1）
bit 8    female（0 或 1）
bit 16   color（0..3）
```

**注释**：

> **这个打包值只是源侧缓存标识。它不是 CODOL 的 `characterInfo_t` 字段或线值。**

**"只是源侧缓存标识"** —— 明确声明不是原生布局。

## 九、那个 `DObj` 存在性检查的完整教训

### 9.1 前四项不够

```text
CODREF(bg_update_player_dobj): the fourth term is the DObj's own
existence, and it has to be here. The other three ask whether the
PRESENTATION changed; none of them notices that the server DObj was
freed underneath an otherwise untouched characterInfo.
```

**"另外三项问的是【表现】是否变了；没有一项注意到服务端 DObj 在其它方面未动的 characterInfo 之下被释放了。"**

### 9.2 死亡正好是这个形状

```text
That is exactly what a death does: the corpse hand-off releases the
player's DObj, the respawn re-uses the same character with the same
selection ids and leaves infoValid set, so this test found nothing to do,
the dirty word at +0x1C was never raised, and BG_UpdatePlayerDObj
0x0040B700 was handed a null DObj with no reason to rebuild it.
```

**四步**：

```text
1. 尸体交接释放玩家的 DObj
2. 重生复用同一个角色、同一批 selection ids、infoValid 仍为真
3. 所以这个测试找不到要做的事
4. +0x1C 的脏字从未被举起 ⇒ BG_UpdatePlayerDObj 收到一个 null DObj 而没有理由重建它
```

### 9.3 实测的数字

```text
Measured 2026-08-17: before a death the locational trace poses
`bones=135 highestZ=63.87` and head shots land at hitZ 58-59;
after the respawn that line never appears again,
and every trace reports the capsule as a perfect candidate --
nativeLinked=1, contents=0x02000000, svFlags=0x02,
absZ tracking the new origin, ray 0.8 units off its axis --
then runs 1144 units into a wall,
because CM_PointTraceToEntities admits the entity and DObjTraceline
finds nothing to test.
```

**六个具体数字**：

```text
bones=135            （骨骼数）
highestZ=63.87       （最高点）
hitZ 58-59           （头部命中高度）
contents=0x02000000
svFlags=0x02
ray 0.8 units        （偏离轴）
1144 units           （打进墙里）
```

**"capsule 作为一个完美候选被接受，然后打进墙里 1144 单位"** —— 因为 `CM_PointTraceToEntities` 接受实体而 `DObjTraceline` 找不到东西可测。

### 9.4 第五项：**存在但没有 traceline 骨骼**

```text
CODREF(bg_update_player_dobj): the fifth term. A DObj that still EXISTS but
offers no traceline bones is exactly as useless to the locational trace as a
missing one, and it is what a death actually leaves behind:
measured 2026-08-17, after a respawn this function is called with all four
earlier terms false - no skip, no failure, no rebuild logged, dobjMissing=0 -
while prepareNativeServerDObjPose takes its `requestedBones` early-out,
so the player poses no skeleton and DObjTraceline has nothing to test.
```

**"仍然存在但不提供 traceline 骨骼的 DObj，对定位 trace 和缺失的一样无用"**

### 9.5 隐藏掩码

```text
sub_CE69A0 skips models flagged in DObj_s +0x0C, the hide mask,
which nothing in this project writes and the corpse hand-off sets.
```

**`DObj_s +0x0C` 是隐藏掩码** —— 项目从不写它，而尸体交接会设。

**所以死亡留下的正是这个状态**。

## 十、关键结论

1. **解析结果报告故意不沉默** —— 因为"健康"尚未确立。
2. **外来解码器才构成真检查** —— 自己对自己一致不算。
3. **仪器与状态必须分离** —— 用去重的分支填状态会丢值。
4. **服务端与客户端选不同变体 ⇒ 客户端请求未加载的资产 ⇒ 玩家隐形**。
5. **尸体通过 `eType == 2` 绕过同一分支，所以还能画（用回退身体）**。
6. **变体空间是 `{1,2}`，所以解析两个即可覆盖全部**。
7. **昂贵解析按角色缓存，廉价附加每次都做** —— 只保护前者会撤销修复。
8. **DObj 的"存在性"与"有骨骼"是两个不同的检查** —— 死亡留下的是后者。

## 十一、未闭合点

- `prepareNativeServerDObjPose` 的 `requestedBones` 早退未在本组读取。
- `EngineBindings.cpp` 5510 行之后未读取。
