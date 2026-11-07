# 344 · **"一个布告无条件断言它的三个字段"** —— 实体号复用、`CorpseScaleField=29` 在 `CorpseMovementDirField=35` 之前、`actorCorpse` 的两套 `lerpData0058` 解码

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 7198–7598 行。

## 二、`CorpseScaleField = 29` / `CorpseMovementDirField = 35` 的**倒序事故**（本组第二重要）

### 2.1 那段

```php
// SCALE IS FIELD 29 AND MOVEMENTDIR IS FIELD 35, AND THEY WERE EMITTED IN THAT
// ORDER REVERSED. writeSkippedFieldIndex encodes the GAP from the previous index
// and walks FORWARD ONLY -- it cannot go back from 35 to 29 -- so a corpse that
// changed both produced a corrupt entity and took the rest of the snapshot with
// it. Corpses appear on every death.
//
// Found by sweeping every writer for write-order, not by any test: the suite
// checks that particular operations are present, never that the field indices
// ascend. Tools/olfinal/audit-field-write-order.py is that sweep, kept.
```

### 2.2 七层

```text
1. **scale 是字段 29 而 movementDir 是字段 35，而它们以【相反】的顺序被发出**
2. ⇒ `writeSkippedFieldIndex` 编码【从上一个索引的间隔】而**只向前走**
3. ⇒ **它不能从 35 回到 29**
4. ⇒ **所以一个两个都变的尸体产生一个损坏的实体并带走快照的其余部分**
5. ⇒ **尸体在每一次死亡时出现**
6. ⇒ **通过【横扫每一个写入器】找写序找到，不是通过任何测试**
7. ⇒ **套件检查特定的操作存在，从不检查字段索引【递增】。`Tools/olfinal/audit-field-write-order.py` 就是那个横扫，保留**
```

### 2.3 **"套件检查操作存在，从不检查索引递增"**

**✅ 与 §339 的"裸整数索引对 `port-netfield-indices.py` 不可见"**同族（**第六次工具盲区**）。**

**⇒ 三个工具：**

```text
port-netfield-indices.py     扫描 `constexpr XField = N` 声明   ⇒ 漏裸整数
audit-duplicate-constants.py 扫描常量重复                       ⇒ 漏数组初始化器
audit-field-write-order.py   横扫写序（新增，保留）
```

**✅ **一个新工具被创建并保留**。**

### 2.4 而**"一个工具被保留"**

**⇒ 三层**：

```text
1. 事故 → 找到模式 → 写工具
2. ⇒ 工具留在仓库
3. ⇒ **挡下一次同型事故**
```

**✅ 与 §343 的"`bump()` 从约定变结构"同族（**从知识到机制**）。**

## 三、**`movementDir` 的 `& 0xFF`**

```cpp
writeUnsignedDelta(
    message,
    (uint32)entity.movementDir & 0xFFu,
    (uint32)fieldBaseline.movementDir & 0xFFu,
    8);
```

### 3.1 三层

```text
① `movementDir` 转 uint32
② ⇒ **与 `0xFF`**
③ ⇒ **8 位无符号 delta**
```

**✅ 与 §318 的"`movementDir` 被写在了 DObj scale 的位置"**配合 —— 一个 8 位值。**

**⚠ 而 §342 的 `validItemEntity` 要求 `movementDir == 0`。**

**⇒ 所以 `movementDir` 的**唯一合法值**在一个 item 上是 0，而在尸体上是 8 位的。**
**✅ 两个不同约束。**

## 四、**"一个布告无条件断言它的三个字段"**（本组最重要的一段）

### 4.1 那段

```php
// AN OBITUARY ASSERTS ITS THREE FIELDS UNCONDITIONALLY.
//
// A field is normally sent only when it differs from the baseline,
// and ENTITY NUMBERS ARE REUSED: an obituary landing on a number
// whose previous occupant was also an obituary shares its eType, so
// the baseline is NOT zeroed and a victim of client 0 -- whose
// clientNum is 0, which is exactly what an unwritten field already
// decodes to -- would inherit the PREVIOUS victim instead. That is
// the same failure the ET_PLAYER clientNum comment further down
// records, and it is invisible in a match where client 0 never
// dies. Three fields, at most 34 bits, is not worth the ambiguity.
```

### 4.2 十层

```text
1. **一个布告【无条件】断言它的三个字段**
2. ⇒ **一个字段正常只在它与基线不同时才发**
3. ⇒ **而【实体号是被复用的】**
4. ⇒ **一个落在号上的布告，若它的前一个占用者也是一个布告，就共享它的 eType**
5. ⇒ **所以基线【不被清零】**
6. ⇒ **而一个客户端 0 的受害者 —— 他的 `clientNum` 是 0，那正是一个未写字段已经解码成的 —— 会继承【前一个受害者】**
7. ⇒ **那是 ET_PLAYER 的 `clientNum` 注释（在下面更远处）记录的同一个失败**
8. ⇒ **而它在一场客户端 0 从不死亡的比赛里是【不可见的】**
9. ⇒ **三个字段、最多 34 位，不值得那个歧义**
```

### 4.3 而**三个无条件字段**

```cpp
const auto obituary = entity.eType == EntityTypeObituary;
const auto eventParmChanged   = obituary || fieldBaseline.eventParm != entity.eventParm;
const auto otherEntityChanged = obituary || fieldBaseline.otherEntityNum != entity.otherEntityNum;
const auto attackerChanged    = obituary;   // ← 完全无条件
```

**⇒ 三个：**

```text
eventParm        （布告 ⇒ 无条件）
otherEntityNum   （布告 ⇒ 无条件）
attacker         （布告 ⇒ 无条件）
```

**⚠ 而 `surfaceTypeChanged` / `impactFlagsChanged` / `weaponChanged` / `hitEntityChanged` 仍是**条件**。**

**⇒ 所以"三个"精确。**

### 4.4 而 **"最多 34 位"**

**⇒ 算一下：**

```text
eventParm       `EntityEventParameterBits[event]` 变长
otherEntityNum  11 位 + 1
attacker        11 位 + 1
```

**⇒ 若 `eventParm` 是 11 位：**

```text
11+1 + 11+1 + 11+1 = 36
```

**⚠ 而注释说 34。**

**⇒ 若 `eventParm` 是 9 位：**

```text
9+1 + 11+1 + 11+1 = 34  ✓
```

**✅ 所以 `eventParm` 的那一项是**9 位**（含 present 位）。**

**⚠ 一处可精确化的推算。**

### 4.5 而 **"客户端 0 从不死亡的比赛里不可见"**

**✅ 与 §343 的"在 256 以下不可见"同族（**第七次"症状在窄条件下不可见"**）。**

**⇒ 一个**极强的共性**：本文件反复记录"某个 bug 只在很少的情况下显形"。**

### 4.6 而 **`groundEntityNum` 的双角色**

```php
// groundEntityNum is field 13 for an obituary and field 23 for
// everything else -- see its declaration. Exactly one of these two
// is ever true.
const auto attackerChanged = obituary;      // field 13
const auto hitEntityChanged = !obituary &&
    fieldBaseline.groundEntityNum != entity.groundEntityNum;  // field 23
```

### 4.7 四层

```text
1. **同一个成员 `groundEntityNum` 在布告上是字段 13（attacker）**
2. ⇒ **而在其它一切上是字段 23（hitEntity）**
3. ⇒ **两个恰好总有一个为真**
4. ⇒ **所以那个成员在一个 eType 上承载攻击者而在另一个上承载被击中的实体**
```

**✅ 一个**成员按 eType 重载**的实例。**

**⚠ 与 §343 的"`scriptMoverBrushModelIndex` 在 ET_ITEM 上是武器行"同族（**第三次"一个成员两个语义"**）。**

**⇒ 这是本文件的核心模式之一。**

### 4.8 而 `impactSurfaceChanged` 的 `unk00A0`

```php
// Only the flesh hit ever sets this; every other event-entity
// validator pins unk00A0 to zero, so for them it is always false.
const auto impactSurfaceChanged = fieldBaseline.unk00A0 != entity.unk00A0;
```

**⇒ 三层**：

```text
1. **只有肉体命中设置它**
2. ⇒ **其它每一个事件-实体验证器都把 `unk00A0` 钉到零**
3. ⇒ **所以对它们总是 false**
```

**✅ 一个"条件天然为假"的字段（除一个 eType）。**

## 五、`EventEntity*Field` 的**十一项赋值不是 max**

```cpp
auto lastChangedField = EventEntityTypeField;
if (originChanged[0]) lastChangedField = EventEntityOriginXField;
if (originChanged[1]) lastChangedField = EventEntityOriginYField;
...
if (hitEntityChanged) lastChangedField = EventEntityHitEntityField;
```

### 5.1 ⚠ **这里是普通赋值而 §343 的 scriptmover/corpse 是 `bump`/`max`**

**⇒ 三层**：

```text
1. `writeChangedScriptMover` 用 `bump`（max）       ← §343
2. ⇒ `writeChangedPlayerCorpse` 用 `bump`（max）   ← §343
3. ⇒ **`writeChangedEventEntity` 用普通赋值**       ← 这里
```

**⚠ 所以**第三处未修**。**

**⚠ 除非……注释说"FIELD ORDER IS ASCENDING"：**

```php
// FIELD ORDER IS ASCENDING AND THE CLIENT DEPENDS ON IT: the skip
// encoding carries index DELTAS, so 13 has to go out between 10 and
// 16 or every field after it lands on the wrong offset.
```

**⇒ 三层**：

```text
1. 作者**知道**顺序重要
2. ⇒ **而这里用普通赋值 ⇒ 依赖书写顺序**
3. ⇒ **所以只要十一条 `if` 按升序排，`lastChangedField` 就是最大值**
```

**✅ 所以**这里靠纪律而前面靠 `max`**。**

**⚠ **一处不一致**（第三处：本文件已在两处把约定变成结构，这里还没有）。**

**⇒ 一个**真实的、尚未被横扫覆盖的**潜在缺陷。**

**⚠ 而这正是 §344 的"`audit-field-write-order.py` 保留"要做的事。**

**⇒ 也许那个工具**会**抓到这里（取决于它是否检查 `lastChangedField` 的赋值模式）。**

## 六、**"obituary ARCHIVED / 归档不等于发出"**

```php
// ARCHIVED IS NOT SENT. The obituary is in the published frame
// -- `obituary ARCHIVED` proves that much -- and it still has
// to survive validEntity and this writer to reach a client. Six
// lines per kill and none at any other time.
OlMod::RuntimeLog::write(
    OlMod::RuntimeLog::Channel::GameServer,
    "obituary WIRE num=" + std::to_string(entity.number) +
        " victim=" + std::to_string(entity.otherEntityNum) +
        " attacker=" + std::to_string(entity.groundEntityNum) +
        " parm=" + std::to_string(entity.eventParm) +
        " baseline=" + std::to_string(baseline ? 1 : 0) +
        " typeChanged=" + std::to_string(typeChanged ? 1 : 0) +
        " lastChanged=" + std::to_string(lastChangedField));
```

### 6.1 五层

```text
1. **归档不等于发出**
2. ⇒ **布告在已发布的帧里**（`obituary ARCHIVED` 就证明了那么多）
3. ⇒ **而它仍必须活过 `validEntity` 与这个写入器才能到达一个客户端**
4. ⇒ **每次击杀六行，其它任何时候都没有**
5. ⇒ **而日志包含七个字段**（num / victim / attacker / parm / baseline / typeChanged / lastChanged）
```

**✅ 一个**精确的"在哪一层消失"的探针**。**

**⇒ 与 §322 的"allowlist 在序列化前丢掉 eType"**同族（**分层的可观测性**）。**

### 6.2 而 **"每次击杀六行"**

**⇒ 但在代码里只有一次 `write` 调用，字符串有七项。**

**⚠ 可能"六行"是指**日志被切成六行**？**

**⇒ 或者"六行"是**六次调用**（不同位置）？**

**⚠ 而这里只见一处。**

**⇒ 一处需核对（可能是**在本文件的其它位置还有五处**）。**

## 七、`constBaselineState` 的**三个字段必须复制**（本组第三重要）

### 7.1 那段

```php
SvEntityState constBaselineState(const SvConstBaselineEntry &entry)
{
    SvEntityState state = wireZeroBaseline();
    state.number = entry.entityNum;
    state.eType = entry.eType;
    state.eFlags = entry.eFlags;
    state.solid = entry.solid;
    state.modelIndex = entry.xmodelIndex;
    state.scriptMoverBrushModelIndex = entry.brushModelIndex;
    state.lerpData0058 = entry.field0058;
    state.scriptMoverField00E4 = entry.field00E4;
    state.scriptMoverField0098 = entry.field0098;
    state.scriptMoverField0070 = entry.field0070;
    state.positionTrajectoryType = entry.positionTrajectoryType;
    state.angleTrajectoryType = entry.angleTrajectoryType;
    state.modelScale = std::bit_cast<float>(entry.scaleBits);
    // THE TRAJECTORY TOO. A field this copy leaves zero while the row carries a
    // value is a field the writer calls "unchanged" and never sends, so the client
    // keeps the ROW's -- and for a delta that means the entity inherits a velocity.
    state.positionTrajectoryTime = entry.positionTrajectoryTime;
    state.positionTrajectoryDuration = entry.positionTrajectoryDuration;
    state.angleTrajectoryTime = entry.angleTrajectoryTime;
    state.angleTrajectoryDuration = entry.angleTrajectoryDuration;
    state.impactSurfaceType = (uint8)entry.surfType;
    for (axis = 0; axis < 3; ++axis) {
        state.origin[axis] = bit_cast<float>(entry.originBits[axis]);
        state.angles[axis] = bit_cast<float>(entry.anglesBits[axis]);
        state.positionTrajectoryDelta[axis] = bit_cast<float>(entry.positionTrajectoryDeltaBits[axis]);
        state.angleTrajectoryDelta[axis] = bit_cast<float>(entry.angleTrajectoryDeltaBits[axis]);
    }
    return state;
}
```

### 7.2 而那段注释

```php
// The map's shipped baseline for this entity, in this server's own entity-state
// shape. Only the fields the ET_SCRIPTMOVER writer compares are carried; everything
// else is zero in the authentic table for every eType this server publishes, so a
// zero here and a zero there agree.
```

**⇒ 四层**：

```text
1. **地图的已发货基线，在本服务器自己的实体状态形状里**
2. ⇒ **只携带 ET_SCRIPTMOVER 写入器所比较的字段**
3. ⇒ **其它一切在真实表里对本服务器发布的每一个 eType 都是零**
4. ⇒ **所以这里一个零与那里一个零一致**
```

### 7.3 而 **"轨迹也要复制"**

**⇒ 五层**：

```text
1. **一个这个复制留零而行携带值的字段**
2. ⇒ **是写入器称为"未变"而【永不发送】的一个字段**
3. ⇒ **所以客户端保留【行的】**
4. ⇒ **而对一个 delta 那意味着实体继承一个速度**
5. ⇒ **所以必须复制**
```

**✅ 与 §343 的"坐标要对着它被编码时用的基线测"**同一类但更弱**（这里是**其它字段也必须复制**）。**

**⇒ 一个**极微妙的"未变"错误**：不是**跳过字段**，而是**跳过后客户端用了不同的值**。**

**✅ 与 §342 的"跳过字段永不被解码"**相反**（那里跳过的字段用基线，这里基线错了）。**

## 八、`writeChangedMissile` 的**三十一个字段**（本组第四重要）

### 8.1 字段表

```cpp
constexpr std::array fields{0u,1u,2u,3u,4u,5u,6u,7u,8u,9u,10u,11u,
    12u,13u,14u,15u,16u,17u,18u,19u,20u,21u,22u,23u,24u,26u,27u,31u,33u,37u,48u};
```

**⇒ 31 个，而 `0..24` 连续（除 25），然后 26/27/31/33/37/48。**

### 8.2 注释

```php
// CODREF(1649370): 63 descriptors at 0xDA7A20. Explicit field-index
// array and ascending loop prevent an out-of-order last-field bug.
// Retail dm entity482/life2 establishes this grenade field subset.
```

**⇒ 四层**：

```text
1. **`0xDA7A20` 有 63 个描述符**
2. ⇒ **一个显式的字段索引数组与升序循环防止一个乱序 last-field bug**
3. ⇒ **零售 dm `entity482`/`life2` 确立这个手雷字段子集**
4. ⇒ **所以这是从零售样本反推的子集**
```

**✅ **33 个字段被省略（63 - 31 = 32）。**

### 8.3 而 `values` 的**映射**

```cpp
v[0]=eType;  v[1]=origin[1];  v[2]=origin[0];
v[3..5]=positionTrajectoryDelta[0..2];
v[6]=angles[2];  v[7]=angles[0];  v[8]=origin[2];
v[9]=positionTrajectoryTime;  v[10]=angleTrajectoryTime;
v[11]=angleTrajectoryDelta[0];  v[12]=groundEntityNum;
v[13]=impactSurfaceType;  v[14]=modelScale;  v[15]=eventSequence;
v[16]=angles[1];  v[17]=positionTrajectoryType;
v[18]=angleTrajectoryType;  v[19]=angleTrajectoryDelta[2];  v[20]=eFlags;
v[26]=angleTrajectoryDelta[1];  v[27]=positionTrajectoryDuration;
v[31]=lerpData0058;  v[33]=weaponAssetIndex;  v[37]=otherEntityNum;
v[48]=angleTrajectoryDuration;
```

**⇒ 三十一个**非零索引**而 v[21..24] 由事件填。**

### 8.4 而**索引顺序与字段顺序完全错乱**

```text
字段 1  = origin[1]（y）
字段 2  = origin[0]（x）
字段 8  = origin[2]（z）
字段 6  = angles[2]（z）
字段 7  = angles[0]（x）
字段 16 = angles[1]（y）
```

**✅ 与 §343 的"索引顺序 ≠ 轴顺序"**第三次确认**。**

**⇒ 而这里**三个轴有三种不同的散布**：**

```text
origin   1(y)  2(x)  8(z)
angles   6(z)  7(x)  16(y)
```

**⚠ 所以**每一组的索引散布都不同**。**

**⇒ 与 §340 的"五个附件槽的索引顺序是乱的"**第四次**。**

### 8.5 而 `changed` 的特殊处理

```cpp
changed[field] = field >= 21 && field <= 24
    ? entity.events[field-21] != old.events[field-21]
    : current[field] != previous[field];
```

**⇒ 三层**：

```text
1. **`21..24` 是事件槽**（`events[0..3]`）
2. ⇒ 其余用 `values` 比较
3. ⇒ **所以事件槽在 `values` 里没有位置**
```

**✅ 与 §343 的 `eventSlot` 映射不同 —— 这里是**区间**而那里是**四元 switch**。**

### 8.6 而 `default:` 分支

```cpp
default: message.MSG_WriteLong(value); break; // -80/-78/-71/-73 raw words
```

**⇒ 三层**：

```text
1. **未显式处理的字段 ⇒ 裸 32 位**
2. ⇒ 注释标出 `-80/-78/-71/-73`
3. ⇒ **所以那个"裸 long"族在此被用作默认**
```

**✅ 与 §343 的"`-80/-78/-73/-71` 在裸 long 分支"**完全一致 ✓**

**⇒ **第二次确认那四个编解码器。**

### 8.7 而 `writeChangedMissile` **没有 `typeChanged` 处理**

```cpp
const auto &old = baseline && baseline->eType == entity.eType ? *baseline : zero;
```

**⇒ 三层**：

```text
1. **只在 eType 相同时用基线**
2. ⇒ 否则用 `zero`
3. ⇒ **所以 `typeChanged` 的效果由"用零基线"实现**
```

**⚠ 而 field 0（eType）的 `changed` 是 `current[0] != previous[0]`。**

**⇒ eType 变了 ⇒ `changed[0] = true` ⇒ 会写。**

**✅ 所以**隐式处理正确**。**

**⚠ 但 §344 的 `writeChangedActorCorpse` 有显式的 `if (field == 0 && !baseline) changed[field] = true;`。**

**⇒ 两种风格。**

## 九、`writeChangedItem` 的**十八个字段**

```cpp
constexpr std::array fields{0u,1u,2u,3u,4u,5u,6u,7u,9u,10u,11u,12u,13u,14u,19u,20u,29u,31u };
```

### 9.1 而注释

```php
// CODREF(1649370): ET_ITEM has 63 descriptors at 0x00DA6528.
// This is the exact field subset asserted by the retail dm
// scavenger pack: trajectory/base, item weapon row, scale and the
// temporary owner exclusion. Fields are kept in descriptor order
// because their indexes are gap encoded.
```

**⇒ 五层**：

```text
1. **ET_ITEM 在 `0x00DA6528` 有 63 个描述符**
2. ⇒ **这是零售 dm 拾荒包断言的精确字段子集**：
     · 轨迹/基线
     · 物品武器行
     · 缩放
     · 临时所有者排除
3. ⇒ **字段保持描述符顺序因为它们的索引是间隔编码的**
```

### 9.2 而 `+0x9C` 的双语义

```cpp
// +0x9C is the ET_ITEM weapon/item row. The source member is
// shared with ET_SCRIPTMOVER's brush-model owner by eType.
v[19] = e.scriptMoverBrushModelIndex;
```

**⇒ 三层**：

```text
1. **一个成员 `scriptMoverBrushModelIndex`**
2. ⇒ **在 ET_SCRIPTMOVER 上是画笔模型**
3. ⇒ **在 ET_ITEM 上是武器/物品行**
```

**✅ 与 §344 五.7 的 `groundEntityNum` **同一模式（**第四次"一个成员两个语义"**）。**

**⇒ 而 §342 的 `validItemEntity` 要求 `scriptMoverBrushModelIndex > 0` ⇒ **那个"画笔模型"其实是物品行号**。**

**⚠ 所以 `validItemEntity` 里那个命名是**误导性的**。**

**⇒ 一处**命名缺陷**。**

### 9.3 而**索引顺序**

```text
0      eType
1/2/3  angles z/y/x（注意：1 = y？见下）
4/5/6  origin z/y/x
7      positionTrajectoryTime
9/10   positionTrajectoryType / angleTrajectoryType
11     groundEntityNum
12/13/14  positionTrajectoryDelta z/x/y
19     物品行
20     positionTrajectoryDuration
29     modelScale
31     otherEntityNum
```

**⇒ 而 `values`：**

```cpp
v[1]=angles[1]; v[2]=angles[2]; v[3]=angles[0];
v[4]=origin[2]; v[5]=origin[1]; v[6]=origin[0];
```

**⇒ 所以：**

```text
字段 1 = angles[1]（y）
字段 2 = angles[2]（z）
字段 3 = angles[0]（x）
字段 4 = origin[2]（z）
字段 5 = origin[1]（y）
字段 6 = origin[0]（x）
```

**⚠ 而 §342 的 missile 是 `1(y) 2(x) 8(z)` 而这里是 `1(y) 2(z) 3(x)`。**

**⇒ **三个 eType 三套不同的索引映射**。**

**✅ 一个**极清晰的证据：索引映射是逐表的**。**

**⇒ 与 §340 的"按偏移比较在重排表上和按索引一样错"**完全一致 ✓**

### 9.4 而写入 case 的轴映射

```cpp
case 4: case 5: case 6: {
    const auto axis = field == 4 ? 2u : field == 5 ? 1u : 0u;
    writeEntityOrigin(...entity.origin[axis]...);
}
case 1: writeEntityAngle(message, entity.angles[1]); break;
case 2: writeEntityAngle(message, entity.angles[2]); break;
case 3: writeEntityAngle(message, entity.angles[0]); break;
```

**✅ 与 `values` **完全一致** ✓**

## 十、**`ET_ACTOR_CORPSE` 的两套 `lerpData0058` 解码**（本组第五重要）

### 10.1 那段

```cpp
return entity.eType == EntityTypeActorCorpse &&
    (cyborgActorsEnabled
        ? ((entity.lerpData0058 & 0xFFu) < ActorCorpseRingSize &&
           ((entity.lerpData0058 >> 8) & 0xFFu) == 3 &&
           (entity.lerpData0058 >> 16) == entity.scriptMoverBrushModelIndex)
        : ((entity.lerpData0058 & ~0x1Fu) == ActorCorpseLerpPrefix &&
           (entity.lerpData0058 & 0x1Fu) < ActorCorpseRingSize)) &&
    entity.scriptMoverBrushModelIndex > 0 &&
    entity.scriptMoverBrushModelIndex < 0x400 &&
    ...
```

### 10.2 两套解码

```text
cyborgActorsEnabled = true:
    低 8 位    < ActorCorpseRingSize（环槽）
    次 8 位    == 3
    高 16 位   == scriptMoverBrushModelIndex

cyborgActorsEnabled = false:
    低 5 位取反 == ActorCorpseLerpPrefix
    低 5 位    <  ActorCorpseRingSize
```

### 10.3 七层

```text
1. **一个 `lerpData0058` 有两种【互不相同】的位域解码**
2. ⇒ **赛博格模式**：`[环槽:8][3:8][模型:16]`
3. ⇒ **普通模式**：`[前缀:~低5][环槽:低5]`
4. ⇒ 而两套都要求 `scriptMoverBrushModelIndex ∈ (0, 0x400)`
5. ⇒ 以及 `positionTrajectoryType/angleTrajectoryType <= 0xFF`
6. ⇒ 以及 `groundEntityNum/otherEntityNum <= 0x7FF`
7. ⇒ 以及 `legsAnim/torsoAnim <= 0xFFF` 与 `modelScale > 0`
```

**✅ 一个**双模式验证器**。**

**⚠ 而两套解码需要**同一字段在不同模式下不同布局** —— 而客户端是**同一个**。**

**⇒ 所以**客户端必须知道模式**（可能由 `cyborgActorsEnabled` 对应的 mode 传递）。**

### 10.4 而 **"十八个字段零售在僵尸第一帧发"**

```php
// THE EIGHTEEN FIELDS RETAIL SENDS ON A ZOMBIE'S FIRST FRAME, measured on
// zm_factory_sh entity 673 life 4 (re/demo-re/20-zm-actor-lifecycle.md
// section 12.1). This server previously sent about five of them and the
// actor validated, kept frames healthy, and did not draw.
```

**⇒ 六层**：

```text
1. **零售在一个僵尸的【第一帧】发十八个字段**
2. ⇒ 在 `zm_factory_sh` 实体 673 生命 4 上测量（`re/demo-re/20-zm-actor-lifecycle.md` 12.1）
3. ⇒ **这个服务器过去发其中大约五个**
4. ⇒ **而 actor 验证通过了、帧保持健康、而【它不画】**
5. ⇒ **所以"验证通过 + 帧健康"不足以让它出现**
```

**✅ 与 §322 的"allowlist 让僵尸从不画"**同族（第四十二次"沉默的缺席"）。**

**⇒ **第三次确认"不画"的独立原因**：**

```text
§322  allowlist 丢掉 eType
§344  （§343）126/132 script model 不写坐标
§344  十八个字段只发五个
```

**⚠ 三个不同的"不画"根因。**

### 10.5 而 `writeChangedActorCorpse` 的**三十一个字段**

```cpp
constexpr std::array fields{
    0u, 1u, 2u, 3u, 4u, 6u, 7u, 8u, 9u, 10u, 11u,
    17u, 18u, 19u, 20u, 21u, 22u, 24u, 25u, 26u, 27u,
    28u, 29u, 30u, 35u, 36u, 37u, 40u, 41u, 43u, 45u, 49u,
};
```

**⇒ 32 个（数一下：11 + 10 + 11 = 32）。**

**⚠ 上表是 32 个。**

### 10.6 而**四个事件槽**

```cpp
const auto eventSlot = [](uint32 field) -> int {
    switch (field) {
    case 28: return 0; // entityState_s +0xB8
    case 40: return 1; // entityState_s +0xC0
    case 41: return 2; // entityState_s +0xC8
    case 43: return 3; // entityState_s +0xD0
    default: return -1;
    }
};
```

**⇒ 四个，步长 `0x08`（`0xB8`/`0xC0`/`0xC8`/`0xD0`）。**

**✅ 与 §343 的 scriptmover `17/22/23/24` 与 §342 的 general `5/26/27/32`**第三次不同**。**

**⇒ **四个 eType 四套事件槽**。**

### 10.7 而 **"一个类型变化重置标量解码基线但并不清空每一个复制的 union 字"**

```cpp
// A type change resets scalar decode baselines but does not clear
// every copied union word. Explicit zero clears stale actor values.
if (baseline && baseline->eType != entity.eType &&
    (field == 22 || field == 36 || field == 37))
    changed[field] = true;
```

**⇒ 四层**：

```text
1. **一个类型变化重置标量解码基线**
2. ⇒ **但并不清空每一个复制的 union 字**
3. ⇒ **显式的零清掉陈旧的 actor 值**
4. ⇒ **所以字段 22/36/37 在类型变化时【无条件发送】**
```

**✅ 与 §344 四的"布告无条件断言三字段"**同一模式（**第二次"无条件发送"**）。**

**⇒ 而这里理由是**union 字残留**。**

### 10.8 而 `field == 0 && !baseline` 的**无条件**

```cpp
if (field == 0 && !baseline)
    changed[field] = true;
```

**⇒ 三层**：

```text
1. **一个新实体（无基线）⇒ eType 无条件写**
2. ⇒ 而 §344 的 missile/item **没有这一条**
3. ⇒ **靠 `current[0] != previous[0]`（previous 来自零基线）**
```

**⚠ 而零基线的 eType 是**零**而 `EntityTypeActorCorpse` 非零 ⇒ 自然为真。**

**⇒ **所以两种写法等价**（冗余但无害）。**

### 10.9 而 `unk00E0` 是**正向 32 位**

```cpp
value[37] = state.unk00E0;        // native +0xE8, positive 32
```

**⇒ 三层**：

```text
1. `unk00E0` 是字段 37
2. ⇒ 原生 `+0xE8`
3. ⇒ **正向 32 位**
```

**✅ 而 §342 的 `validItemEntity` 要求 `unk00E0 == 0`。**

**⇒ 两个 eType 上它都**存在但只在 actorCorpse 上非零**。**

### 10.10 而 `solid` 的**24 位与类型变化的强制**

```cpp
case 36:
    // CODREF(out.exe46DAE0): centity+1A0 is entityState+AC.
    // Zero returns before capsule/brush collision. A skipped
    // word can retain the live capsule across19->21, so this
    // zero is mandatory on the type transition as well.
    writeUnsignedDelta(message, value, before, 24); break;
```

**⇒ 五层**：

```text
1. **`centity+0x1A0` 是 `entityState+0xAC`**
2. ⇒ **零在胶囊/画笔碰撞之前返回**
3. ⇒ **一个被跳过的字能在 `19→21` 之间保留活的胶囊**
4. ⇒ **所以这个零在类型变化时也是【必须的】**
5. ⇒ `writeUnsignedDelta(..., 24)`
```

**✅ 与 §342 的 `validItemEntity` 要求 `solid == 0`**配合 —— 那里是 item 这里是 corpse。**

**⚠ 而 `19→21` 是**eType 的数值**（`EntityTypeActor = 19`？`EntityTypeActorCorpse = 21`？）。**

**⇒ 所以**一次 actor → actorCorpse 的转换**。**

**✅ 一个**具体的 eType 数值对**。**

## 十一、`writeChangedActor` 的**起点**

```cpp
// NO constBaseline ARM, and that is not an omission. Every ET_ACTOR
// in the five captures is numbered ABOVE the map's last static
// entity (488..815 against factory's 625) -- zombies are spawned at
// runtime and have no row in the shipped const baseline table to
// delta against.
```

### 11.1 六层

```text
1. **没有 constBaseline 分支，而那不是疏漏**
2. ⇒ **五次捕获里的每一个 ET_ACTOR 编号都【高于】地图的最后一个静态实体**
3. ⇒ **（488..815 对 factory 的 625）**
4. ⇒ **僵尸在运行时被生成而没有已发货 const 基线表里的一行可 delta**
5. ⇒ 所以没有那一条
6. ⇒ **坐标取同样的强制零规则**
```

**✅ 一个**用编号区间证明"没有基线"**的手法。**

**⚠ 注意 `488..815` 与 `625` 是**两个区间**而 `625` 在 `488..815` 之内。**
**⇒ 所以注释的意思是"actor 编号范围是 488..815 而 factory 的最后静态实体是 625"。**

**⚠ 那 `488..624` 会**与静态实体重叠**。**

**⇒ 一处**需要核对的数值**。**

### 11.2 而 **"yaw 只有"**

```php
// YAW ONLY. apos.trBase[0] and [2] assert six times in the whole spec
// capture and carry one value between them: zero. A zombie never
// pitches or rolls, and validActorEntity refuses one that tries.
const auto yawChanged = coordinateBaseline.angles[1] != entity.angles[1];
```

**⇒ 五层**：

```text
1. **只有 yaw**
2. ⇒ `apos.trBase[0]` 与 `[2]` 在整个 spec 捕获里断言**六次**
3. ⇒ **而它们之间只携带一个值：零**
4. ⇒ **一个僵尸从不俯仰或翻滚**
5. ⇒ **而 `validActorEntity` 拒绝一个尝试的**
```

**✅ 与 §344 的"零是安全标记"同族（**第四次"零即无效"**）。**

**⇒ 而"六次断言但都是零"是一个**极精确的统计**。**

### 11.3 而 **`SvActorSendUnmeasuredSpawnWords` 的四个门**

```cpp
eventChanged[index] = SvActorSendUnmeasuredSpawnWords &&
    fieldBaseline.events[index] != entity.events[index];
const auto field0058Changed = SvActorSendUnmeasuredSpawnWords &&
    fieldBaseline.actorField0058 != entity.actorField0058;
const auto field00ACChanged = SvActorSendUnmeasuredSpawnWords &&
    fieldBaseline.actorField00AC != entity.actorField00AC;
```

**⇒ 三层**：

```text
1. **一个开关 `SvActorSendUnmeasuredSpawnWords` 门控三类字段**：
     · 四个事件
     · `actorField0058`
     · `actorField00AC`
2. ⇒ **名字里的 "Unmeasured" 说明它们不是从零售测出来的**
3. ⇒ **所以默认关闭**
```

**✅ 与 §343 的"更好的是省略而不是错"同族（**第十一次）。**

**⇒ 而**"未测量 ⇒ 默认不发"** 是一个**明确的原则**。**

## 十二、关键结论

1. **⭐ `CorpseScaleField = 29` 与 `CorpseMovementDirField = 35` 曾以相反顺序发出** ⇒ 尸体破坏快照。
2. **`Tools/olfinal/audit-field-write-order.py` 是那次事故后创建并保留的横扫工具** —— **第六次工具盲区，第一个"新增工具"**。
3. **"套件检查操作存在，从不检查索引递增"**。
4. **⭐ "一个布告无条件断言它的三个字段"**（`eventParm` / `otherEntityNum` / `attacker`）—— **实体号复用 + eType 共享 ⇒ 基线不清零 ⇒ 继承前一个受害者**。
5. **"三个字段、最多 34 位"** ⇒ 推算 `eventParm` 的是 9 位。
6. **"客户端 0 从不死亡的比赛里不可见"** —— 第七次"窄条件下不可见"。
7. **`groundEntityNum` 在布告上是字段 13（attacker）而在其它上是 23（hitEntity）** —— **第三次"一个成员两个语义"**。
8. **`unk00A0` 只有肉体命中设置**（其它验证器钉死为零）。
9. **⚠ `writeChangedEventEntity` 用普通赋值而非 `bump`/`max`** —— **第三处未修**（两处已修）。
10. **"归档不等于发出"** —— 每次击杀六行日志、七个字段。
11. **⭐ `constBaselineState` 的"轨迹也要复制"** —— 留零 ⇒ 写入器称"未变"⇒ 客户端保留行的 ⇒ **继承一个速度**。
12. **`writeChangedMissile` 的 31 字段**（`0xDA7A20` 63 个描述符的子集）。
13. **missile 的轴映射 `1(y) 2(x) 8(z)` / `6(z) 7(x) 16(y)`** —— 第三次确认索引顺序 ≠ 轴顺序。
14. **missile 用 `field >= 21 && <= 24` 表达事件槽** 而 corpse 用四元 switch。
15. **`writeChangedItem` 的 18 字段**（`0x00DA6528` 63 个描述符）。
16. **`scriptMoverBrushModelIndex` 在 ET_ITEM 上是"物品武器行"** —— **第四次"一个成员两个语义"**，而 §342 的 `validItemEntity` 命名**误导**。
17. **item 的轴映射 `1(y) 2(z) 3(x)`** 与 missile 的**完全不同** —— **三个 eType 三套映射**。
18. **⭐ `ET_ACTOR_CORPSE` 的 `lerpData0058` 有两套解码**（赛博格 `[环槽:8][3:8][模型:16]` / 普通 `[前缀:~低5][环槽:低5]`）。
19. **"零售在僵尸第一帧发十八个字段而本服务器只发五个 ⇒ 验证通过、帧健康、**但不画**"** —— 第三次独立的"不画"根因。
20. **corpse 的四个事件槽 `28/40/41/43`（`+0xB8/0xC0/0xC8/0xD0`）** —— 四个 eType 四套事件槽。
21. **"一个类型变化重置标量基线但不清空每一个复制的 union 字"** ⇒ 字段 22/36/37 强制发送（第二次"无条件发送"）。
22. **`solid` 的 24 位与"`19→21` 转换时必须写零"** —— 一个具体的 eType 数值对。
23. **"没有 constBaseline 分支而那不是疏漏"** —— ET_ACTOR 编号高于最后的静态实体。
24. **"yaw only"** —— `apos.trBase[0]/[2]` 断言六次且都是零。
25. **`SvActorSendUnmeasuredSpawnWords` 门控三类未测量字段** —— "未测量 ⇒ 默认不发"。

## 十三、未闭合点

- `writeChangedEventEntity` 的普通赋值是否被 `audit-field-write-order.py` 覆盖。
- "每次击杀六行"与代码里一处 `write` 的矛盾。
- `488..815` vs `625` 的编号区间。
- `EntityTypeActor` / `EntityTypeActorCorpse` 的数值（推测 19 / 21）。
- `ActorCorpseRingSize` 与 `ActorCorpseLerpPrefix` 的值。
- `sv_snapshot_mp.cpp` 7598 行之后未读取（27,016 行，进度 28%）。
