# 343 · **"坐标的基线必须是它被编码时用的那个"** —— `126/132` 个 scriptmodel 一个位置都没发、`bump()` 从约定变结构、`-80` 是裸 32 位

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 6400–6945 行（`writeChangedScriptMover` 完整）。

## 二、**"新实体的基线是地图的 const 基线，不是零"**（本组第三重要）

```cpp
// A NEW ENTITY'S BASE IS THE MAP'S CONST BASELINE, NOT ZERO -- when the
// snapshot carries flag 0x10, because that is exactly what the client will
// resolve it against. Fields equal to it are then never sent at all, which is
// why retail's static scriptmovers assert almost nothing on the wire.
const auto *const deltaSource = baseline ? baseline : constBaseline;
const auto &source = deltaSource ? *deltaSource : zeroBaseline;
const auto typeChanged = source.eType != entity.eType;
const auto &fieldBaseline = typeChanged ? zeroBaseline : source;
```

### 2.1 五层

```text
1. **一个新实体的基线是地图的 const 基线，不是零** —— 当快照携带 `flag 0x10`
2. ⇒ **因为那正是客户端将要用它解析的对象**
3. ⇒ **等于它的字段于是完全不被发**
4. ⇒ **那就是为什么零售的静态 scriptmover 在线上一句断言都不发**
5. ⇒ 而 `typeChanged` 时退回 `zeroBaseline`
```

### 2.2 而 `flag 0x10`

**⇒ 三层**：

```text
1. 快照携带 `0x10`
2. ⇒ 客户端用地图 const 基线
3. ⇒ 所以我们也必须用它
```

**✅ 与 §341 的"一个未变的客户端完全不提"**同一类"**省略是常态**"（第六次"默认值不进线"）。**

## 三、**"坐标是例外，而那是客户端决定的"**（本组最重要的第一段）

### 3.1 那段

```php
// COORDINATES ARE THE EXCEPTION, AND THE CLIENT IS WHERE THAT COMES FROM.
// MSG_ReadDeltaEntity forces a ZERO baseline for a field when
// `newFlag && (codec + 83) <= 5` -- codecs -83..-78, which is every position,
// angle and trajectory float. So on a new entity those decode ABSOLUTELY no
// matter what baseline the entity has, and encoding them against the const
// baseline would put a delta on the wire that the client reads as an absolute.
const auto newEntity = baseline == nullptr;
const auto &coordinateBaseline =
    (newEntity && !typeChanged) ? zeroBaseline : fieldBaseline;
```

### 3.2 七层

```text
1. **坐标是例外，而那是从【客户端】来的**
2. ⇒ `MSG_ReadDeltaEntity` 在一个字段上强制【零】基线当 `newFlag && (codec + 83) <= 5`
3. ⇒ **即编解码器 `-83..-78`，那是每一个位置、角度和轨迹浮点**
4. ⇒ **所以在一个新实体上那些【绝对】解码，不管实体有什么基线**
5. ⇒ **而用 const 基线编码它们会把一个 delta 放到线上而客户端把它读成绝对**
6. ⇒ 所以 `coordinateBaseline = (newEntity && !typeChanged) ? zeroBaseline : fieldBaseline`
```

### 3.3 **"`codec + 83 <= 5`"是无符号的**

**⇒ 三层**：

```text
codec = -83 ⇒ -83 + 83 = 0  ≤ 5 ✓
codec = -78 ⇒ -78 + 83 = 5  ≤ 5 ✓
codec = -84 ⇒ -1 ⇒ 作为 unsigned 极大 ⇒ 不 ≤ 5 ✓（排除）
codec = -77 ⇒ 6 ⇒ 不 ≤ 5 ✓（排除）
```

**✅ **一个用无符号算术做区间检查的精确手法**。**

**⇒ 与 §265 的"`(unsigned)` 技巧"同族（第二次）。**

### 3.4 而 **`-83..-78` 是六个编解码器**

**⇒ 数一下：**

```text
-83, -82, -81, -80, -79, -78   = 六个
```

**✅ 与 §258 的"`-79` 是全角"、§342 的"`-80` 是裸 32 位"配合。**

**⇒ 而 `-78` 是另一个（可能是轨迹浮点）。**

**⚠ 所以"每一个位置、角度和轨迹浮点" = 六个编解码器 ✓**

## 四、**"坐标要对着它被编码时用的那个基线测"**（本组最重要的第二段）

### 4.1 那段

```php
// COORDINATES ARE TESTED AGAINST THE BASELINE THEY ARE ENCODED AGAINST,
// AND THAT IS THE WHOLE FIX.
//
// The comment above used to end "a coordinate equal to the baseline is
// skipped entirely, and a skipped field is never decoded, so the forced-zero
// rule never applies to it". That is sound ONLY IF the client's entity
// baseline really holds the row's position -- and nothing had ever depended
// on it. Brush models are immune: an inline brush model's geometry is already
// in world space, so a zeroed origin still draws it in the right place, which
// is why 237 of them ship with no coordinate on the wire and look correct.
//
// A script model is NOT immune -- its xmodel is placed BY the origin. MEASURED
// from this server's own wire (OLMOD_SNAPSHOT_HEX, decoded with
// Tools/demo-re/diff-sent-vs-baseline.py): with retail numbering on, 126 of
// 132 script models sent NO position field at all, because their origin equals
// their row's and the test above skipped it. Those are exactly the props that
// come out misplaced, and the six that did send one are the zapper arms, whose
// origins differ from their rows.
//
// So test against coordinateBaseline, which is ZERO on a new entity. The
// coordinate then always goes on the wire as an absolute, which is what the
// client's forced-zero rule reads it as, and it cannot depend on a baseline
// this server cannot see. It costs a few bytes per static entity on its first
// snapshot -- exactly the bytes retail numbering was supposed to save, and
// correctness is worth more than they are.
```

### 4.2 十一层

```text
1. **坐标要对着它们被编码时用的那个基线测，而那就是整个修复**
2. ⇒ 旧注释说"一个等于基线的坐标被跳过，而跳过的字段从不被解码，所以强制零规则永不适用于它"
3. ⇒ **那只有在【客户端的实体基线真的持有那一行的位置】时才成立** —— 而从来没有东西依赖过它
4. ⇒ **画笔模型免疫**：内联画笔模型的几何已经在世界空间，所以一个归零的 origin 仍把它画在对的位置
5. ⇒ **那就是为什么 237 个这样的模型一个坐标都不发而看起来正确**
6. ⇒ **而一个 script model 【不免疫】—— 它的 xmodel 是【被 origin 放置】的**
7. ⇒ **实测（从本服务器自己的线 `OLMOD_SNAPSHOT_HEX`，用 `Tools/demo-re/diff-sent-vs-baseline.py` 解码）：零售编号打开时，132 个 script model 里 126 个【一个位置字段都不发】**
8. ⇒ **因为它们 origin 等于它们行的而上面的测试跳过了它**
9. ⇒ **那些正是出来位置错的道具**
10. ⇒ **而真发了的那个六个是电击臂，它们的 origin 与它们行不同**
11. ⇒ 所以改为对 `coordinateBaseline` 测（新实体上是零）⇒ 坐标总是作为绝对上线
```

### 4.3 **"126/132"**

**⇒ 三层**：

```text
132 个 script model
126 个一个位置都不发（95.5%）
6 个发了（电击臂）
```

**✅ 一个极精确的测量。**

**⚠ 而 `126/132 = 95.45%`。**

**⇒ 而"六个电击臂"是**唯一的例外**。**

### 4.4 **"237 个画笔模型"**

**⇒ 三层**：

```text
1. 237 个画笔模型一个坐标都不发
2. ⇒ **而它们看起来正确**
3. ⇒ **因为它们的几何已经在世界空间**
```

**✅ 所以**同一症状（不写坐标）在两类实体上后果完全不同**。**

**⇒ 一个**教科书级的"沉默的差异"**。**

### 4.5 **"它的 xmodel 是【被 origin 放置】的"**

**⇒ 三层**：

```text
1. 画笔模型：几何在世界空间 ⇒ origin 无关
2. ⇒ script model：**xmodel 由 origin 放置** ⇒ origin 必需
3. ⇒ **同一个"跳过坐标"对前者正确对后者致命**
```

**✅ 与 §318 的"`index 29` 在两个 build 上是不同字段"、§322 的"allowlist 让僵尸从不画"同族**（第四十次"一个通用规则在某一类上错"）。

### 4.6 而**"正确性比那些字节更值钱"**

**⇒ 三层**：

```text
1. 每帧每静态实体多发几个字节
2. ⇒ 正是"零售编号本想省"的字节
3. ⇒ **但正确性比它们更值钱**
```

**✅ 与 §341 的"代价不对称的正确选择"同族（第十次）。**

## 五、`originChanged` / `angleChanged` 用 `coordinateBaseline` 而**其它用 `fieldBaseline`**

```cpp
const std::array originChanged{
    coordinateBaseline.origin[0] != entity.origin[0], ... };
const std::array angleChanged{
    coordinateBaseline.angles[0] != entity.angles[0], ... };
const auto modelChanged = fieldBaseline.modelIndex != entity.modelIndex;
```

### 5.1 三层

```text
坐标（origin / angles）⇒ coordinateBaseline
其它一切               ⇒ fieldBaseline
```

**✅ 一个**精确的分界**。**

**⚠ 而 `positionTrajectoryDelta` 用 `coordinateBaseline`（见下）。**

### 5.2 而 `wirePositionDelta` 的**"镜像 origin"**

```cpp
// Existing static scriptmovers and podium figures predate explicit
// trajectory ownership and intentionally mirror their origin into
// trDelta. A moving producer supplies a nonzero delta and owns the
// actual wire value. This keeps the proven static wire unchanged
// while admitting retail's moving podium camera.
const auto wirePositionDelta = [](const SvEntityState &state) -> const std::array<float,3> & {
    if (any_of(state.positionTrajectoryDelta, [](float v){ return v != 0.0f; }))
        return state.positionTrajectoryDelta;
    return state.origin;
};
```

### 5.3 四层

```text
1. **既有的静态 scriptmover 与领奖台人像早于显式轨迹所有权**
2. ⇒ **而故意把它们的 origin 镜像进 `trDelta`**
3. ⇒ **一个移动的生产者提供一个非零 delta 并拥有真正的线值**
4. ⇒ **这保持已证明的静态线不变，同时接纳零售的移动领奖台相机**
```

**✅ 一个**向后兼容的双语义**。**

**⚠ 但"若 delta 全零则用 origin" ⇒ **一个真实的零轨迹被误读**。**

**⇒ 代价：一个 `trDelta = (0,0,0)` 的移动物体会被当成静态。**

**⚠ 一处已知的妥协。**

## 六、`bump()` 从**约定变结构**（本组第二重要）

### 6.1 那段（scriptmover 侧）

```php
// lastChangedField IS A MAXIMUM. It used to be a run of plain assignments, which is
// only correct while they happen to be listed in ascending field order -- and on
// 2026-08-24 the float-origin trio (5, 7, 8) was inserted AFTER angleZ (9) and
// angleX (10). Any scriptmover that changed both an angle and a float origin then
// announced lastChangedField = 8 while the writer still emitted fields 9 and 10.
//
// The client's field loop is BOUNDED BY THAT NUMBER: it stops at 8, the bits for
// 9 and 10 are left in the stream, and every section after the entity list is read
// at the wrong offset. A MAP SCRIPT MODEL ON ITS FIRST FRAME CHANGES ALL OF THEM,
// so this fired on every map that publishes script models -- mp_rust_long does --
// and the symptom was a client stuck forever on the map-load screen while the
// server happily reported `active=2`. Nothing in the server log named it.
//
// A max cannot be broken by reordering, so the next field inserted here is safe
// wherever it goes.
```

### 6.2 十层

```text
1. **`lastChangedField` 是一个【最大值】**
2. ⇒ **它过去是一串普通赋值**
3. ⇒ **那只有在它们碰巧按升序排列时才正确**
4. ⇒ **而 2026-08-24 浮点 origin 三件套（5, 7, 8）被插在了 `angleZ`(9) 与 `angleX`(10) 之后**
5. ⇒ **任何同时改了一个角度和一个浮点 origin 的 scriptmover 于是宣告 `lastChangedField = 8` 而写入器仍发出字段 9 和 10**
6. ⇒ **客户端的字段循环【被那个数字限界】**：它在 8 停下，9 和 10 的位留在流里
7. ⇒ **而实体列表之后每一个段都在错的偏移上被读**
8. ⇒ **一个地图 script model 在它的【第一帧】改变所有它们**
9. ⇒ **所以这在每一个发布 script model 的地图上触发**（`mp_rust_long` 就是）
10. ⇒ **症状是客户端永远卡在地图加载屏而服务器快乐地报告 `active=2`。服务器日志里没有任何东西命名它**
```

### 6.3 **"`active=2` 而客户端卡在加载屏"**

**✅ 与 §338 的"收盘时 `active=2`"、§329 的"服务端只数自己的发送"同族**（第四十一次"服务端的健康度量看不见客户端的死"）。

**⚠ 而这里说 `mp_rust_long` 是**一个具体的失败地图**。**

### 6.4 而 **"一个 max 不能被重排打破"**

**⇒ 三层**：

```text
1. 普通赋值：依赖【书写顺序】= 索引顺序
2. ⇒ **`std::max` 累积：与书写顺序无关**
3. ⇒ **所以下一个插进来的字段是安全的，无论放哪**
```

**✅ 与 §339 的"运行期严格递增检查"、§337 的"两个 build 的 24 项描述符同序"同族。**

### 6.5 而**写入顺序仍必须递增**

```php
// The WRITE order below still has to ascend; that is a separate
// requirement and writeSkippedFieldIndex enforces it by walking forward only.
```

**⇒ 三层**：

```text
1. `lastChangedField` 用 max ⇒ **顺序无关**
2. ⇒ **但写入顺序仍必须递增**
3. ⇒ **`writeSkippedFieldIndex` 只向前走 ⇒ 强制**
```

**✅ **两个**独立的顺序要求，一个由 `max` 解决一个由 `writeSkippedFieldIndex` 解决。**

**⇒ 一个**极清晰的分离**。**

### 6.6 而 corpse 侧的**同一修复**

```php
// Ascending index order, so the final assignment is the maximum.
// A MAXIMUM, for the reason spelled out in writeChangedScriptMover. This block had
// the same defect and it was found by sweeping every writer for the pattern rather
// than by anything failing: **CorpseScaleField is 29 and it was assigned AFTER
// CorpseMovementDirField, which is 35.** A corpse whose movementDir and scale both
// changed announced lastChangedField = 29 while field 35 went out, and the client
// stopped reading before it.
//
// The trajectory-delta loop below already used std::max, so the hazard was
// understood in one place in this very function and not in the fifteen lines above
// it. That is exactly why this is now structural instead of a convention.
```

### 6.7 七层

```text
1. **这个块有同一个缺陷**
2. ⇒ **而它是通过【横扫每一个写入器找这个模式】找到的，不是通过什么失败**
3. ⇒ **`CorpseScaleField` 是 29 而它在 `CorpseMovementDirField`（是 35）【之后】被赋值**
4. ⇒ **一个 movementDir 与 scale 都变了的尸体宣告 `lastChangedField = 29` 而字段 35 出去了**
5. ⇒ **而客户端在它之前就停止读**
6. ⇒ **下面的轨迹-delta 循环【已经】用 `std::max`**，所以那个危险在这个函数【里面的一处】被理解而在它上面十五行里没有
7. ⇒ **那正是为什么现在是【结构性】而不是一个约定**
```

### 6.8 **"通过横扫找模式而不是等它失败"**

**✅ 这是一个**极高价值的工程手法**。**

**⇒ 与 §331 的"把常数喂进动态逻辑出来还是常数"**不同** —— 那是**运行时推理**而这是**静态横扫**。**

**⚠ 而那个横扫的结果 = 只找到一处（corpse）。**

**⇒ 而 scriptmover 那处是**已知的**（2026-08-24 事故）。**

**✅ 所以两处，一个事故一个横扫。**

### 6.9 而 **"危险在一个函数里被理解而在上面十五行没有"**

**⇒ 三层**：

```text
1. 同一个函数里
2. ⇒ **下面用 `std::max`（已理解）**
3. ⇒ **上面十五行用普通赋值（未理解）**
```

**✅ 一个**极常见的"半修"模式**。**

**⇒ 与 §340 的"`82e` 的诊断错而建议对"同族（局部正确整体错误）。**

## 七、**"一个没什么可说的实体绝不能走这条路"**

```cpp
// AN ENTITY WITH NOTHING TO SAY MUST NOT TAKE THIS PATH. The client reads a
// three-bit skip index unconditionally after lastChangedField (sub_671170), so
// a "changed" entity that writes no field desynchronises the rest of the
// snapshot and the client stops completing frames entirely. The caller encodes
// that case as (0, 0) -- "unchanged, take the baseline" -- and this refuses
// rather than emitting a stream that cannot be read.
//
// Loud on purpose: a rejected frame names itself in the log, a desynchronised
// one looks like a black screen with no error anywhere.
if (lastChangedField == EntityStateTypeField && !typeChanged)
    return false;
```

### 7.1 六层

```text
1. **一个没什么可说的实体绝不能走这条路**
2. ⇒ **客户端在 `lastChangedField` 之后【无条件】读一个三位跳号索引**（`sub_671170`）
3. ⇒ **所以一个"变了"而什么都不写的实体失步快照的其余部分**
4. ⇒ **而客户端完全停止完成帧**
5. ⇒ 调用方把那种情况编码为 `(0, 0)` —— "未变，取基线" —— 而这个函数【拒绝】
6. ⇒ **故意大声：一个被拒的帧在日志里命名自己，一个失步的看起来像黑屏而任何地方都没有错**
```

### 7.2 **"故意大声"**

**✅ 与 §340 的"`SV_PackCharacterCustomization` 留在这里是死的"**相反**（一个**静默 return** 一个**出声拒绝**）。**

**⚠ 而 §341 的运行期顺序检查是**静默 `return`**。**

**⇒ 所以本文件里**两种都有**。**

**⚠ 一处不一致（§341 已标注为可改进点）。**

### 7.3 而 `sub_671170` = `MSG_ReadDeltaEntity`

**✅ 与记忆里的"实体 delta 读取器 0x671170"**完全一致 ✓**

**⇒ 而这里的 `sub_671170` 是**同一个函数**。**

**✅ **第 N 次确认该地址**。**

## 八、**"第 2 位是新实体标志而本服务器一直写 0"**（本组第四重要）

### 8.1 那段

```php
// BIT 2 IS THE NEW-ENTITY FLAG AND THIS SERVER HAS ALWAYS WRITTEN 0.
// MSG_ReadDeltaEntity is sub_671170 on out.exe, and its field loop is
//
//   if (baseline->eType != entity->eType ||
//       newFlag && (unsigned)(field->codec + 83) <= 5)
//       decodeField(..., forceZeroBaseline = 1, ...);
//
// codec + 83 <= 5 is codecs -83..-78, WHICH ARE THE COORDINATE CODECS
// -- corpse table indices 2/3/6 are -83/-82/-81, the origin. So the
// flag means "decode this entity's position ABSOLUTELY, not as a delta
// against the baseline".
//
// The demo shows retail doing exactly that: a corpse spawn carries
// originX 64248 originY 3954 originZ 24, and later frames carry -18,
// 10, -1. Absolute on the first frame, deltas after.
//
// Writing 0 here told the client to delta a BRAND NEW entity's origin
// against a baseline it does not have, so the body was placed
// somewhere other than where it died. It was never invisible.
//
// The walk already knows: it passes a null baseline exactly when the
// entity is not in the last acknowledged snapshot, which IS new.
message.MSG_WriteBits(baseline ? 0 : 1, 1);
```

### 8.2 九层

```text
1. **第 2 位是新实体标志而本服务器一直写 0**
2. ⇒ `MSG_ReadDeltaEntity` 是 `out.exe` 的 `sub_671170`
3. ⇒ 而它的字段循环是 `if (baseline->eType != entity->eType || newFlag && (unsigned)(field->codec + 83) <= 5) decodeField(..., forceZeroBaseline = 1, ...)`
4. ⇒ **`codec + 83 <= 5` 是编解码器 `-83..-78`，那是【坐标编解码器】**
5. ⇒ **尸体表索引 2/3/6 是 `-83/-82/-81`，即 origin**
6. ⇒ **所以这个标志意味着"【绝对】解码这个实体的位置，不是一个对基线的 delta"**
7. ⇒ **demo 显示零售正是这样做**：一个尸体出生携带 `originX 64248 originY 3954 originZ 24` 而之后帧携带 `-18, 10, -1`
8. ⇒ **写 0 在这里告诉客户端把一个【全新】实体的 origin 对它没有的基线 delta**
9. ⇒ **所以身体被放在不是它死的地方。它从来不是不可见的**
```

### 8.3 **"它从来不是不可见的"**

**✅ 一个**极重要的纠正**。**

**⇒ 与 §312 的"玩家模型索引不是模型 configstring 索引"**不同** —— 那是**不可见**而这是**位置错**。**

**⚠ 所以两个不同的症状。**

### 8.4 而 `baseline ? 0 : 1` 的**语义**

**⇒ 三层**：

```text
1. `baseline != nullptr` ⇒ 写 0（不是新实体）
2. ⇒ `baseline == nullptr` ⇒ 写 1（新实体）
3. ⇒ **而 `nullptr` 恰好意味着"不在上一个确认的快照里" = 新的**
```

**✅ 一个**不需要额外状态的推导**。**

## 九、**"`-80` 是一个裸 32 位 long，没有前导也没有基线 XOR"**（本组第五重要）

### 9.1 那段

```php
// CODEC -80 IS A PLAIN 32-BIT LONG WITH NO PROLOGUE AND NO BASELINE XOR.
// sub_670BF5's dispatcher puts -80/-78/-73/-71 in the raw-long arm, which is a
// bare read_ulong(). This lambda originally called writeFullFloatDelta, whose own
// comment says it implements `bits == 0` -- a DIFFERENT codec, which prefixes the
// value with two present bits.
//
// So every scriptmover carrying a float origin emitted TWO EXTRA BITS before the
// value, and from that bit on the client's cursor was wrong for the rest of the
// snapshot. The client could never complete a frame, never went ACTIVE, and sat on
// the map-load screen showing "waiting for player data" -- while the server, which
// only counts its own sends, reported `active=2`. It broke every match from the
// moment the float trio was added (HANDOFF 137).
//
// The right encoder was already in this file: the corpse writer's `writeRawFloat`
// does exactly this for ITS codec -80 trajectory deltas.
```

### 9.2 十层

```text
1. **编解码器 `-80` 是一个裸 32 位 long，没有前导、没有基线 XOR**
2. ⇒ **`sub_670BF5` 的派发器把 `-80/-78/-73/-71` 放进【裸 long】分支**
3. ⇒ **而那是一个裸 `read_ulong()`**
4. ⇒ **这个 lambda 原来调用 `writeFullFloatDelta`**
5. ⇒ **而它自己的注释说它实现 `bits == 0` —— 一个【不同的】编解码器，它以两个 present 位给值加前缀**
6. ⇒ **所以每一个携带浮点 origin 的 scriptmover 在值前发出【两个多余的位】**
7. ⇒ **而从那一位起客户端的游标在快照的其余部分都是错的**
8. ⇒ **客户端永远不能完成一帧、永不 ACTIVE，而坐在加载屏显示 "waiting for player data"**
9. ⇒ **而服务器（只数自己的发送）报告 `active=2`**
10. ⇒ **它从浮点三件套被加进来的那一刻破坏了每一场比赛（HANDOFF 137）**
```

### 9.3 **四个编解码器在同一个分支**

```text
-80  -78  -73  -71    ⇒ 裸 32 位 long（read_ulong）
```

**✅ 与 §342 的 `-83..-78` 区间**部分重叠** —— `-78` 在两者里。**

**⚠ 所以 `-78` 既在"坐标强制零"区间又在"裸 long"分支。**

**⇒ **兼容的**（`-78` 是裸 long 且在新实体上强制零基线 ⇒ 而裸 long 不用基线 ⇒ 无效果）。**

**✅ 一致。**

### 9.4 而 **"waiting for player data"**

**✅ 与记忆里的"快照 run 编码必须 4 位 ⇒ 卡『等待玩家数据』"**完全一致 ✓**

**⇒ 同一个症状的**第二个原因**（第一个是快照 run 编码）。**

**✅ 一个**症状两个根因**。**

### 9.5 而 **"正确的编码器已经在这个文件里"**

**⇒ 三层**：

```text
1. 尸体写入器的 `writeRawFloat` **已经**对它的 `-80` 轨迹 delta 做这件事
2. ⇒ 而 scriptmover 侧却用了 `writeFullFloatDelta`
3. ⇒ **同一个文件里有一个正确的一个错误的一个**
```

**✅ 与 §337 的"两个几乎相同的函数"同族（第六次"复制代码分叉"）。**

### 9.6 而 `writeRawFloat` / `writePositionTrajectoryDelta` / `writeFloatAngle` **三个都是裸 long**

```cpp
const auto writePositionTrajectoryDelta = [&](uint32 fieldIndex, size_t axis) {
    writeSkippedFieldIndex(...);
    message.MSG_WriteLong(std::bit_cast<uint32>(positionTrajectoryDelta[axis]));
};
const auto writeFloatAngle = [&](size_t axis) {
    writeSkippedFieldIndex(...);
    message.MSG_WriteLong(std::bit_cast<uint32>(entity.angleTrajectoryDelta[axis]));
};
```

**⇒ 两处裸 long（而 corpse 那处叫 `writeRawFloat`）。**

**✅ **三个裸 long lambda**。**

## 十、**字段 5/7/8 的插入位置**

```cpp
// 5, 7, 8 GO HERE, between field 4 and field 9. writeSkippedFieldIndex
// walks strictly FORWARD and cannot go back, so putting these after
// the angle writes at 9 and 10 makes the whole snapshot fail to
// serialise -- which is exactly what the suite caught.
//
// Ascending INDEX order is 5, 7, 8; the AXIS order is y, x, z, by
// offset (+0x28, +0x24, +0x2C). Index order is not axis order.
```

### 10.1 五层

```text
1. **5、7、8 放在这里，在字段 4 与字段 9 之间**
2. ⇒ `writeSkippedFieldIndex` **严格向前走**不能回头
3. ⇒ **所以把它们放在 9 和 10 的角度写之后会让整个快照无法序列化**
4. ⇒ **而那正是套件抓到的**
5. ⇒ **索引顺序是 5、7、8；而轴顺序是 y、x、z（按偏移 `+0x28`、`+0x24`、`+0x2C`）。索引顺序不是轴顺序**
```

### 10.2 而**三个偏移**

```text
trDelta.y   +0x28   索引 5
trDelta.x   +0x24   索引 7
trDelta.z   +0x2C   索引 8
```

**⚠ 所以 x 在 `+0x24` 而 y 在 `+0x28`。**

**⇒ 所以**内存顺序是 x、y、z 而索引顺序是 5(y)、7(x)、8(z)。**

**✅ **索引顺序确实与内存顺序不同。** —— 一个关键的实测。

**⇒ 与 §340 的"五个附件槽的索引顺序是乱的"同族（第二次）。**

### 10.3 而**角度侧的同样模式**

```cpp
if (angleChanged[1]) writeAngle(ScriptMoverAngleYField, 1);       // 先 y
...
if (angleChanged[2]) writeAngle(ScriptMoverAngleZField, 2);
if (angleChanged[0]) writeAngle(ScriptMoverAngleXField, 0);
```

**⇒ 三层**：

```text
y 先写（索引 6？）
⇒ 然后 z（索引 9）
⇒ 然后 x（索引 10）
```

**✅ 所以 `ScriptMoverAngleYField < ScriptMoverAngleZField < ScriptMoverAngleXField`。**

**⇒ **又一次索引顺序 ≠ 轴顺序 x,y,z**。**

**✅ **第三次。**

## 十一、**`sequenceChanged` 与四个事件字段**

```cpp
// out.exe ET_SCRIPTMOVER table0xDA6828: sequence16(-75),
// ring17/22/23/24(-94). Original Factory715/716 publish113 here.
const bool sequenceChanged = entity.eventSequence != fieldBaseline.eventSequence;
constexpr std::array<uint32,4> eventFields{17,22,23,24};
```

### 11.1 三层

```text
`0x00DA6828`  本 build 的 ET_SCRIPTMOVER 表
sequence      字段 16（编解码器 -75）
事件环        字段 17/22/23/24（编解码器 -94）
原 Factory    715/716（发布 113）
```

**✅ 与 §342 的"`-75` 是 32 位 / `-94` 是裸字节 id"**完全一致 ✓**

### 11.2 而**四个事件字段不连续（17/22/23/24）**

**⇒ 三层**：

```text
1. 第一个事件在 17
2. ⇒ 而其余在 22/23/24
3. ⇒ **17 与 22 之间空了四个索引**
```

**⚠ 那是**四槽环**的第一个与其余分开。**

**⇒ 所以 18..21 是**别的字段**（可能是其他事件或标量）。**

**⚠ 而 §342 的 `writeChangedGeneralEntity` 的 `eventSlot` 映射是 `5→0, 26→1, 27→2, 32→3`。**

**⇒ 所以 ET_GENERAL 的事件槽在 5/26/27/32。**

**✅ **两个不同的表，两套不同的事件索引**。**

**⇒ 与 §343 的 `0x00DA6828` vs `DA4608`（§342 的 general 表）配合。**

## 十二、字段编码汇总（scriptmover）

| 索引 | 字段 | 编码 | 位宽 |
|---|---|---|---|
| 0 | eType | `writeSkippedFieldIndex` + `WriteByte` | 8 |
| 2/3/4 | origin x/y/z | `writeEntityOrigin` | 8 或 17 |
| 5/7/8 | trDelta y/x/z | **裸 `WriteLong`** | 32 |
| 6 | angleY | `writeEntityAngle` | 18 |
| 9/10 | angleZ/angleX | `writeEntityAngle` | 18 |
| 11 | angleTrajectoryTime | `writeEntityTrajectoryTime` | 9 或 33 |
| 12 | angleTrajectoryType | `writeUnsignedDelta(8)` | 8+1 |
| 13 | trDelta angle y | 裸 `WriteLong` | 32 |
| 14 | positionTrajectoryDuration | **裸 `WriteLong`** | 32 |
| 15 | positionTrajectoryType | `writeUnsignedDelta(8)` | 8+1 |
| 16 | eventSequence | `writeEntityEventSequence` | 4 或 9 |
| 17/22/23/24 | events | `writeEntityEvent` | 变化 |
| 18 | link（parent \| tag<<16） | `writeUnsignedDelta(28)` | 28+1 |
| 19 | modelIndex | `writeUnsignedDelta(10)` | 10+1 |
| 20 | animationTime | `writeEntityTrajectoryTime` | 9 或 33 |
| 21 | field0070 | `writeSignedDelta(7)` | 7+1 |
| 25 | field00E4 | `writeUnsignedDelta(8)` | 8+1 |
| 26 | brushModelIndex | `writeUnsignedDelta(10)` | 10+1 |
| 27 | field0058（lerpData） | `writeUnsignedDelta(11)` | 11+1 |
| 28 | animationIndex | `writeUnsignedDelta(13)` | 13+1 |
| 29 | weaponAssetIndex | `writeUnsignedDelta(11)` | 11+1 |
| 30/31 | trDelta angle x/z | 裸 `WriteLong` | 32 |
| 32 | solid | `writeUnsignedDelta(24)` | 24+1 |
| 33 | eFlags | `write30BitFlagDelta` | 30+1 |
| 34 | angleTrajectoryDuration | **裸 `WriteLong`** | 32 |
| 46 | modelScale | `writeFullFloatDelta` | 2+32 |
| 47 | field0098 | `writeUnsignedDelta(5)` | 5+1 |
| 49 | podiumClientNumPlusOne | `writeUnsignedDelta(7)` | 7+1 |

### 12.1 而**注释列出的升序**是 `19 model, 25 +0x0E4, 26 brush model, 27 +0x058, 32 solid, 33 eFlags, 46 scale, 47, 49 podium`

**✅ 与表**一致 ✓**

**⚠ 但注释漏了 16/17/22/23/24（事件）与 18（link）与 20/21。**

**⇒ 那些在注释行之前写了。**

**✅ 所以注释只描述**"ASCENDING FIELD ORDER IS LOAD-BEARING"那一段之后**的部分。**

### 12.2 而**三个 `writeFullFloatDelta` 之外的浮点都是裸 long**

```text
trDelta y/x/z       裸 long（-80）
trDelta angle y/x/z 裸 long（-80）
positionTrajectoryDuration  裸 long（-80？）
angleTrajectoryDuration     裸 long（-80？）
modelScale          writeFullFloatDelta（bits==0 那个）
```

**⚠ 所以**五个 32 位整数/浮点用裸 long 而只有一个用 `writeFullFloatDelta`。**

**⇒ 而 `positionTrajectoryDuration` 与 `angleTrajectoryDuration` 是**整数**用裸 long 写**（不是 float）。**

**✅ 合理（`WriteLong` 是 32 位，内容无关）。**

## 十三、关键结论

1. **"新实体的基线是地图的 const 基线，不是零"**（当快照携带 `flag 0x10`）。
2. **"坐标是例外，而那是客户端决定的"** —— `codec + 83 <= 5` ⇒ `-83..-78` 六个坐标编解码器强制零基线。
3. **`codec + 83 <= 5` 是无符号区间检查**（`-84` 和 `-77` 都被排除）。
4. **⭐ "坐标要对着它们被编码时用的那个基线测，而那就是整个修复"**。
5. **`126/132` 个 script model 一个位置都没发** ⇒ 位置错（不是不可见）。
6. **`237` 个画笔模型一个坐标都不发而看起来正确** —— 因为几何在世界空间。
7. **"一个 script model 的 xmodel 是被 origin 放置的"** —— 同一症状两类后果。
8. **"正确性比那些字节更值钱"**。
9. **`wirePositionDelta` 的双语义**（非零 trDelta 用它 / 全零用 origin）—— 一处已知妥协。
10. **⭐ `bump()` 从约定变结构** —— `lastChangedField` 必须是 `std::max`。
11. **2026-08-24 事故**：浮点三件套 (5,7,8) 插在 9/10 之后 ⇒ `lastChangedField = 8` ⇒ 客户端卡加载屏而服务器报 `active=2`。
12. **corpse 侧的同一缺陷由"横扫每个写入器找模式"找到**（`CorpseScaleField = 29` 在 `CorpseMovementDirField = 35` 之后）。
13. **"危险在一个函数里被理解而在上面十五行没有"** —— 半修模式。
14. **"一个没什么可说的实体绝不能走这条路"** —— 客户端无条件读三位跳号索引。
15. **"故意大声：被拒的帧命名自己，失步的像黑屏"**。
16. **⭐ "第 2 位是新实体标志而本服务器一直写 0"** —— `MSG_ReadDeltaEntity` = `sub_671170`。
17. **"它从来不是不可见的"** —— 尸体位置错而不是不可见。
18. **⭐ "编解码器 -80 是一个裸 32 位 long，没有前导也没有基线 XOR"** —— `sub_670BF5` 把 `-80/-78/-73/-71` 放进裸 long 分支。
19. **"两个多余的位让客户端永不完一帧"** ⇒ "waiting for player data" 的**第二个根因**（第一个是快照 run 编码）。
20. **"正确的编码器已经在文件里"**（`writeRawFloat`）—— 第六次复制代码分叉。
21. **索引顺序 ≠ 轴顺序**：trDelta 是 5(y)/7(x)/8(z)，角度是 y < z < x（第三、四次）。
22. **`0x00DA6828` 的 ET_SCRIPTMOVER**：sequence 16(-75)、环 17/22/23/24(-94)。
23. **ET_GENERAL 与 ET_SCRIPTMOVER 的事件槽完全不同**（5/26/27/32 vs 17/22/23/24）。
24. **字段编码全表**（34 个索引）。

## 十四、未闭合点

- `flag 0x10` 的确切定义与它在快照头里的位置。
- 18/19/20/21 四个索引在 scriptmover 表里究竟是什么（除 19 model / 20 animTime / 21 field0070）。
- 三个"裸 long"编码器是否可以在 corpse 与 scriptmover 间合并。
- `mp_rust_long` 那次事故的完整日志（是否还在仓库）。
- `sv_snapshot_mp.cpp` 6945 行之后未读取（27,016 行，进度 26%）。
