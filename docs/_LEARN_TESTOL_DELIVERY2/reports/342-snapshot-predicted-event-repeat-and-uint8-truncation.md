# 342 · **"uint8_t 就是预测事件重复 bug"** —— `567` 次回跳、`629/642` 次整环重播、玻璃 2 位状态机、`itemEntity` 的四十项 AND

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 5800–6000 行。

## 二、玻璃片的三段写（本组第三重要）

### 2.1 三段

```cpp
void writeGlassPiece(MsgWriter &message, const SvGlassPieceStateRecord &piece)
{
    message.MSG_WriteBits((uint8)piece.state, 2);          // ① 2 位状态
    if (piece.state != SvGlassPieceState::Destroyed) return;
    message.MSG_WriteBits(piece.impact ? 1 : 0, 1);        // ② 1 位有冲击
    if (!piece.impact) return;
    message.MSG_WriteByte(piece.impact->direction);        // ③ 8 位方向
    message.MSG_WriteBits(piece.impact->positionX, 6);     // ④ 6 位 X
    message.MSG_WriteBits(piece.impact->positionY, 6);     // ⑤ 6 位 Y
}
```

### 2.2 五层

```text
1. **2 位状态**（必写）
2. ⇒ 非 `Destroyed` ⇒ **返回**
3. ⇒ **1 位有冲击标志**
4. ⇒ 无冲击 ⇒ **返回**
5. ⇒ 8 + 6 + 6 = **20 位**
```

**✅ 所以三个尺寸：**

```text
非 Destroyed        2 位
Destroyed 无冲击    3 位
Destroyed 有冲击   23 位
```

**⚠ 而 §341 的 `glassImpactBitCount` 给的是 `0 / 1 / 21`。**

**⇒ 那个函数数的是**impact 部分**：**

```text
非 Destroyed        ⇒ 0（没有 impact 部分）
Destroyed 无 impact ⇒ 1（那个 1 位标志）
Destroyed 有 impact ⇒ 21 = 1 + 20
```

**✅ **完全吻合** ✓ —— `21 = 1 + 8 + 6 + 6`。**

### 2.3 而 `20 = 8 + 6 + 6`

**⇒ 与 §341 的 `positionX/Y <= 0x3F`（6 位）**一致** ✓**

## 三、`writeEntityNumber` 的**两分支**（本组第四重要）

```cpp
void writeEntityNumber(MsgWriter &message, uint32 number, int32 &lastEntityNum)
{
    if (number == (uint32)(lastEntityNum + 1))
        message.MSG_WriteBits(1, 1);                        // 连续 ⇒ 1 位
    else {
        message.MSG_WriteBits(0, 1);
        message.MSG_WriteBits(1, 1);                        // 【两个位：0 然后 1】
        message.MSG_WriteBits(number, 11);                  // 11 位绝对
    }
    lastEntityNum = (int32)number;
}
```

### 3.1 四层

```text
① 连续 ⇒ 一个 1 位
② 否则 ⇒ `0` 然后 `1` 然后 11 位绝对
③ 共 13 位
④ `lastEntityNum` 更新
```

### 3.2 **⚠ 为什么"跳跃"要写 `0` 然后 `1` 两个位？**

**⇒ 对比 §337 的 `writeClientNumber`：**

```cpp
writeClientNumber:  1（有客户端）+ 1（连续）/ 0 + 5 位
writeEntityNumber:  1（连续）/ 0 + 1 + 11 位
```

**⇒ 两个结构**不同**。**

**⚠ 而 §337 的 `writeClientNumber` 第一个 `1` 是"有客户端"。**

**⇒ 所以 `writeEntityNumber` 的 `0 + 1` 可能也是"类型"：**

```text
1       = "下一个号"（delta 编码）
0 1     = "绝对号"
0 0     = ？（终止？）
```

**✅ **与 §338 的"这一节的第三位"、"终止要用 0"**配合 —— `0 0` 可能是终止。**

**⚠ 但这里没有处理 `0 0` 的分支 ⇒ 所以终止可能在**调用方**。**

### 3.3 而 `11` 位

**⇒ 与 §341 的 `entityNumber` 字段 20 的宽 **11** 一致** ✓**

**⚠ 而 §338 的 agentState 索引 20（`entityNumber`）也是 **11** 位。**

**✅ **第三次确认 11 位**。**

## 四、`packEntityWeapon` 的**16 位打包**

```cpp
uint32 packEntityWeapon(const SvEntityState &entity)
{
    return entity.weaponAssetIndex |
        ((uint32)entity.presentationWeaponAssetIndex << 16);
}
```

**⇒ 三层**：

```text
1. `weaponAssetIndex` 在低 16 位
2. ⇒ `presentationWeaponAssetIndex` 在高 16 位
3. ⇒ **一个 32 位字装两个 16 位索引**
```

**⚠ 而 §239 的 `MaximumWeaponAssetIndex = 0x7FF`（11 位）。**

**⇒ 所以 16 位槽装 11 位值 ⇒ **浪费 5 位但安全**。**

## 五、**"一个超过宽度表的事件 id 不是一个无效事件"**（本组第二重要）

### 5.1 那段

```cpp
// AN EVENT ID PAST THE WIDTH TABLE IS NOT AN INVALID EVENT. Codec -94 writes
// the id as a raw BYTE, and this build's own client answers an id at or past
// dword_DA9410's 170 entries with a zero-width parameter -- it does not refuse
// the snapshot. A live client's playerState carried event 180 in two ring slots,
// and treating that as invalid refused the player's whole entityState. Mirror
// the decoder instead: the id is a byte, and anything without a declared width
// simply carries no parameter.
uint8 entityEventParameterBits(int32 event)
{
    if (event < 0 || (size_t)event >= EntityEventParameterBits.size()) return 0;
    return EntityEventParameterBits[event];
}
```

### 5.2 七层

```text
1. **一个超过宽度表的事件 id 【不是】一个无效事件**
2. ⇒ **编解码器 -94 把 id 写成裸字节**
3. ⇒ **而这个 build 自己的客户端对 `dword_DA9410` 的 170 项处或之后的 id 用一个零宽参数回答**
4. ⇒ **它不拒绝快照**
5. ⇒ **一个活客户端的 playerState 在两个环槽里携带事件 `180`**
6. ⇒ **而把它当作无效拒绝了玩家的【整个 entityState】**
7. ⇒ **镜像解码器：id 是一个字节，任何没有声明宽度的就是一个没有参数的**
```

### 5.3 **"170 项"而事件 180**

**⇒ 三层**：

```text
dword_DA9410 有 170 项（索引 0..169）
事件 180 > 169 ⇒ 越界
⇒ 而客户端【不拒绝】
```

**✅ 与"`SvMaximumEntityEventId`"配合 —— 那个常量必须是 **≥ 180**。**

### 5.4 **"拒绝了玩家的整个 entityState"**

**✅ 与 §241 的"一个错拒丢掉整条链"、§322 的"allowlist 丢 eType"同族**（第三十九次"一个错杀掉全体"）。

### 5.5 而 `validEntityEvent` 的三分支

```cpp
bool validEntityEvent(const SvEntityEvent &event)
{
    if (event.event < 0 || event.event > SvMaximumEntityEventId) return false;
    const auto bits = entityEventParameterBits(event.event);
    if (!bits) return event.parameter == 0;              // ← 无宽度 ⇒ 参数必须为 0
    if (bits == 32) return true;
    return event.parameter >= 0 && (uint32)event.parameter < (1u << bits);
}
```

**⇒ 四层**：

```text
① 越 `SvMaximumEntityEventId` ⇒ 拒绝
② 无宽度 ⇒ 参数【必须为 0】
③ 32 位 ⇒ 总是接受
④ 否则 ⇒ 参数必须落在 `[0, 2^bits)`
```

**✅ ② 是"没有声明宽度就是一个没有参数的"的**写入侧对应**。**

### 5.6 而 `validItemEntity` 的**四十项 AND**

```cpp
return entity.eType == EntityTypeItem &&
    entity.number >= FirstDynamicServerEntityNum &&
    entity.number < EntityNumWorld &&
    entity.scriptMoverBrushModelIndex > 0 &&
    entity.scriptMoverBrushModelIndex <= 0xFFF &&
    entity.otherEntityNum <= EntityNumNone &&
    entity.groundEntityNum == EntityNumWorld &&
    entity.positionTrajectoryType == 3 &&
    entity.positionTrajectoryDuration == 50 &&
    entity.angleTrajectoryType == 0 &&
    entity.angleTrajectoryTime == 0 &&
    entity.angleTrajectoryDuration == 0 &&
    entity.modelScale == 1.0f &&
    finite(entity.origin) && finite(entity.angles) &&
    finite(entity.positionTrajectoryDelta) &&
    allZero(entity.angleTrajectoryDelta) &&
    entity.clientNum == 0 && entity.eFlags == 0 &&
    entity.eventParm == 0 && entity.impactSurfaceType == 0 &&
    entity.impactFlags == 0 && entity.movementDir == 0 &&
    entity.playerSizeScale == 0.0f && entity.modelIndex == 0 &&
    entity.scriptMoverAnimationIndex == 0 && entity.scriptMoverField0098 == 0 &&
    entity.scriptMoverField0070 == 0 && entity.scriptMoverAnimationStartTime == 0 &&
    entity.podiumClientNumPlusOne == 0 && entity.solid == 0 &&
    entity.eventSequence == 0 && entity.weaponAssetIndex == 0 &&
    entity.presentationWeaponAssetIndex == 0 &&
    entity.offhandWeaponAssetIndex == 0 && entity.coKnifeStatsIndex == 0 &&
    entity.unk00E0 == 0 && entity.legsAnim == 0 && entity.torsoAnim == 0 &&
    entity.time2 == 0 && entity.scriptMoverTagIndex == 0 &&
    entity.scriptMoverParentNumPlusOne == 0;
```

### 5.7 而**两个 `== 3` 与 `== 50`**

```text
positionTrajectoryType     == 3
positionTrajectoryDuration == 50
```

**⇒ 两个**魔法常数**。**

**⚠ 而 §318 的"`index 29` 在两个 build 上是不同字段" —— 那里有 `movementDir`。**

**⇒ 这里 `movementDir == 0`。**

**⚠ 所以 `validItemEntity` **要求** `movementDir` 为零。**
**⇒ 而 §318 说 `movementDir` 被写在了 DObj scale 的位置 ⇒ 那个 bug 会让 `validItemEntity` 失败。**

**✅ **两个事实互相印证**。**

### 5.8 而**四十项里绝大多数是 `== 0`**

**⇒ 数一下非零要求：**

```text
eType == EntityTypeItem              1
scriptMoverBrushModelIndex > 0       1（且 <= 0xFFF）
positionTrajectoryType == 3          1
positionTrajectoryDuration == 50     1
modelScale == 1.0f                   1
number 范围                          1
otherEntityNum <= EntityNumNone      1
groundEntityNum == EntityNumWorld    1
finite × 3                           3
```

**⇒ 约 12 项"正面"而 28 项"零"。**

**✅ 所以 `EntityTypeItem` 是一个**极窄的模板**。**

**⚠ 与 §240 的"`work` 分支必须有 `work`"、§319 的"`spawnZombieActor` 拒绝零模型"同族** —— **一个显式的完整形状检查**。

## 六、**"`uint8_t` 就是预测事件重复 bug"**（本组最重要的一段）

### 6.1 那段（第一部分）

```php
// THIS TOOK uint8_t AND THAT WAS THE PREDICTED-EVENT REPEAT BUG.
//
// Codec -75 declares a THIRTY-TWO BIT field. Eight bits is the width of
// its FALLBACK, not of the value: the primary arm is a delta of 1..8
// against the client's own baseline, which carries an absolute cursor of
// any size. Truncating here (and at the two playerstate call sites, and
// again with a `& 0xFF` where the cursor is filled in) meant the client's
// SNAPSHOT cursor ran 0..255 while its PREDICTED cursor ran free, so
// every snapshot rebase yanked pe.eventSequence back by a multiple of 256
// and the client re-walked its 4-slot event ring.
```

### 6.2 十层

```text
1. **这个函数曾取 `uint8_t` 而那就是预测事件重复 bug**
2. ⇒ **编解码器 -75 声明一个【三十二位】字段**
3. ⇒ **八位是它的【回退】的宽度，不是值的宽度**
4. ⇒ **主分支是一个 1..8 的增量对一个客户端自己的基线，而携带一个任意尺寸的绝对游标**
5. ⇒ **在这里截断（以及在两个 playerState 调用点，又一次用 `& 0xFF` 填游标时）**
6. ⇒ **意味着客户端的【快照】游标跑 0..255 而它的【预测】游标跑自由**
7. ⇒ **所以每一次快照 rebase 都把 `pe.eventSequence` 往回拽 256 的倍数**
8. ⇒ **而客户端重新走它那个四槽事件环**
```

### 6.3 **"三个截断点"**

```text
① writeEntityEventSequence 的 uint8_t 参数
② 两个 playerState 调用点
③ 填游标时的 `& 0xFF`
```

**✅ 三处。**

### 6.4 而**实测数据**

```text
94% 的 567 次向后跳落在 (previous & 0xFF) 的 2 以内
每一个增量都是 256 的倍数：±255, ±511, ±767, ±1023
两个游标【交替】而不是一起动，所以 eventSequence - oldEventSequence
  在 602 个样本里超过四槽环而在 774 个里变成【负】
629/642 次回绕 >= 4 个事件，所以客户端的钳制总是触发【整个环】
90% 的环槽写重新装入一个槽已经持有的值
```

**⇒ 六层，全部实测。**

### 6.5 **"±255 而不是 ±256"**

**⇒ 三层**：

```text
1. 增量为 256 的倍数
2. ⇒ 但测量是 ±255
3. ⇒ **因为它是 `uint8` 的模算术**
```

**⚠ 而 `-255` 与 `+1` 在模 256 下等价。**

**⇒ 所以"±255"实际是**模算术的 ±1**。**

**✅ **一个极精细的测量**。**

### 6.6 而 **"629/642 次回绕 >= 4"**

**⇒ 三层**：

```text
1. 642 次回绕
2. ⇒ 629 次 >= 4 个事件
3. ⇒ **所以客户端的钳制总是触发整个环**
```

**⇒ 这解释了"一个真实事件 + 三个重复"。**

**✅ 一个**症状的精确解释**。**

### 6.7 而 **"90% 的环槽写重新装入一个槽已经持有的值"**

**⇒ 所以重播是**空操作**90% 的时间（但会重新触发音效）。**

### 6.8 而**"在 256 以下是不可见的"**

```php
// and it is invisible below 256, where the truncation is a no-op. That
// is the player's "it doesn't happen until later into the match", which
// no server-side metric could ever have shown.
```

**⇒ 四层**：

```text
1. **在 256 以下不可见**（截断是空操作）
2. ⇒ **那就是玩家的"它直到比赛后期才发生"**
3. ⇒ **而那是任何【服务端】度量都永远显示不出来的**
4. ⇒ **必须从客户端读**
```

**✅ 一个**决定性的方法论结论**：需要客户端侧仪器。**

**⇒ 与 §333 的"客户端自身运行中的测量"同族。**

### 6.9 而 `writeEntityEventSequence` 的**两分支**

```cpp
void writeEntityEventSequence(MsgWriter &m, const uint8_t value, const uint8_t baseline)
{
    const auto delta = (uint8_t)(value - baseline);      // ← 【模算术】
    if (delta >= 1 && delta <= 8) {
        m.MSG_WriteBits(1, 1);
        m.MSG_WriteBits(delta - 1, 3);                   // 1 + 3 = 4 位
        return;
    }
    m.MSG_WriteBits(0, 1);
    m.MSG_WriteByte(value ^ baseline);                   // 1 + 8 = 9 位
}
```

**⇒ 三层**：

```text
① 模算术的 delta（因为 `uint8_t` 相减）
② delta 1..8 ⇒ 1 位 + 3 位（`delta - 1`）
③ 否则 ⇒ 1 位 + 8 位 XOR
```

**✅ 与 §323 的 `writePlayerStateFieldIndex` 的"1 位若 delta==1"**不同**（那里是精确 1 而这里是 1..8）。**

### 6.10 而**注释说"fixture 把 0xFF → 0 钉在紧凑分支上，要求模算术"**

```php
// The entity fixture pins 0xFF -> 0 onto the compact branch, which
// requires modular byte arithmetic.
```

**⇒ 三层**：

```text
1. `0xFF → 0`（即 255 → 0）
2. ⇒ 非模算术下 `delta = -255` ⇒ 走回退
3. ⇒ **模算术下 `delta = 1` ⇒ 走紧凑**
4. ⇒ **而 fixture 要求紧凑**
```

**✅ 所以**模算术是线格式的一部分**。**

## 七、`writePlayerStateEventSequence` 的**非模算术**（本组第五重要）

### 7.1 那段

```php
// TREATING THE PLAYERSTATE CURSOR LIKE THE ENTITY ONE WAS THE
// PREDICTED-EVENT REPEAT BUG. The exact reason is now instruction-level
// evidence rather than the earlier, incorrect "32-bit free-running" story:
//
//   * BG_AddEvent at 0x426B9F..0x426BAC increments ps+0x108, ANDs it
//     with 0xFF and stores the dword: the native producer wraps.
//   * CG_CheckPlayerstateEvents at 0x462741 repairs the previous cursor
//     with -256 when it crosses the current byte-domain value.
//   * MSG_ReadDeltaField's compact -75 arm at 0x67042C computes
//     baseline + ReadBits(3) + 1 without a byte mask. At baseline 255,
//     modular delta 1 therefore decodes to 256, not 0.
//   * The fallback at 0x670448 reads the eight-bit XOR payload and
//     reconstructs 0. A non-modular unsigned delta deliberately selects
//     that fallback at the wrap.
// The uint32 parameters below preserve that non-modular subtraction;
// they do not claim that the logical cursor is wider than a byte.
```

### 7.2 九层

```text
1. **把 playerState 游标当 entity 游标处理就是预测事件重复 bug**
2. ⇒ **`BG_AddEvent` 在 `0x426B9F..0x426BAC` 自增 `ps+0x108`、与 `0xFF`、存 dword：原生生产者【回绕】**
3. ⇒ **`CG_CheckPlayerstateEvents` 在 `0x462741` 当它越过当前字节域值时用 `-256` 修复【前一个】游标**
4. ⇒ **`MSG_ReadDeltaField` 的紧凑 -75 分支在 `0x67042C` 算 `baseline + ReadBits(3) + 1`【不带字节掩码】**
5. ⇒ **所以在基线 255，模 delta 1 解码成 256 而不是 0**
6. ⇒ **回退在 `0x670448` 读八位 XOR 载荷并重建 0**
7. ⇒ **一个非模的无符号 delta 故意在回绕处选择那个回退**
8. ⇒ **下面的 `uint32` 参数保留那个非模减法**
9. ⇒ **它们不声称逻辑游标比一个字节宽**
```

### 7.3 **"255 + 1 = 256 而不是 0"**

**✅ 一个**极精确的指令级事实**。**

**⇒ 而 256 会**超出字节域** ⇒ 所以编码器必须在回绕处选回退。**

### 7.4 而 `writePlayerStateEventSequence` 用 `uint32`

```cpp
void writePlayerStateEventSequence(MsgWriter &m, const uint32 value, const uint32 baseline)
{
    const auto delta = value - baseline;                 // ← 非模
    if (delta >= 1 && delta <= 8) { ... }                // 255→0 时 delta = 0xFFFFFF01 ⇒ 不进
    m.MSG_WriteBits(0, 1);
    m.MSG_WriteByte((value ^ baseline) & 0xFFu);         // ← XOR 回退
}
```

**⇒ 三层**：

```text
① `value - baseline` 是【uint32 非模】
② 255 → 0 ⇒ delta = 0xFFFFFF01 ⇒ 不走紧凑
③ ⇒ 走回退写 `(0 ^ 255) & 0xFF = 0xFF` ⇒ 客户端重建 0 ✓
```

**✅ 完全正确。**

### 7.5 而**两个函数的 `delta` 类型不同**

```text
writeEntityEventSequence       uint8_t（模）
writePlayerStateEventSequence  uint32（非模）
```

**✅ 而两者都是"正确"的 —— 因为**客户端的两条读路径不同**。**

**⇒ 与 §337 的"`writeLegacyClients` 与 `writeClients` 各一份"同族（代码重复但是不同语义）。**

## 八、`writeEntityEvent` 的**三分支**

```cpp
void writeEntityEvent(MsgWriter &m, const SvEntityEvent &event, const SvEntityEvent &baseline)
{
    const auto bits = entityEventParameterBits(event.event);
    if (event.event == baseline.event) {
        m.MSG_WriteBits(0, 1);                           // ① 同 id
        if (bits) m.MSG_WriteBits(event.parameter, bits); // 【仍写参数】
        return;
    }
    m.MSG_WriteBits(1, 1);                               // ② 不同 id
    m.MSG_WriteByte((uint8)event.event);
    if (!bits) return;
    const auto mask = bits == 32 ? UINT32_MAX : (1u << bits) - 1;
    if (((uint32)baseline.parameter & mask) == ((uint32)event.parameter & mask)) {
        m.MSG_WriteBits(0, 1);                           // ③ 参数相同
        return;
    }
    m.MSG_WriteBits(1, 1);                               // ④ 参数不同
    m.MSG_WriteBits(event.parameter, bits);
}
```

### 8.1 四层

```text
① id 相同 ⇒ 0 位 + **仍然写参数**（若有权重）
② id 不同 ⇒ 1 位 + 8 位 id
③ 参数（掩码后）相同 ⇒ 0 位
④ 否则 ⇒ 1 位 + bits 位参数
```

### 8.2 **⚠ "id 相同仍写参数"**

**⇒ 三层**：

```text
1. id 相同 ⇒ 只写一个 0 位
2. ⇒ **但仍写参数**
3. ⇒ **所以参数【没有】"相同"的省略**
```

**✅ 与 §323 的"字段索引可以跳过但值必须写"同族。**

### 8.3 而 ③ 用 `mask` 比较

**⇒ 三层**：

```text
1. 参数比较【应用 mask】
2. ⇒ 所以高位差异被忽略
3. ⇒ 因为客户端只读 `bits` 位
```

**✅ 一个**精确的、与线宽一致的比较**。**

**⚠ 而 §341 的"在整个记录上比较"是**保守**；这里是**精确**。**

**⇒ 两个不同的策略，各有理由。**

## 九、`isOwnerPredictedEvent` 的**28 个 id**（本组第六重要）

### 9.1 完整清单

```text
0x19 EV_RELOAD
0x1A EV_RELOAD_FROM_EMPTY
0x1B EV_RELOAD_START
0x1C EV_RELOAD_END
0x1D EV_RELOAD_START_NOTIFY
0x1E EV_RELOAD_ADDAMMO
0x1F EV_RAISE_WEAPON
0x20 EV_FIRST_RAISE_WEAPON
0x21 EV_PUTAWAY_WEAPON
0x22 EV_WEAPON_ALT
0x23 EV_WEAPON_SWITCH_STARTED
0x24 EV_PULLBACK_WEAPON
0x29 EV_FIRE_WEAPON
0x2A EV_FIRE_WEAPON_LASTSHOT
0x2D EV_RECHAMBER_WEAPON
0x2E EV_EJECT_BRASS
0x2F EV_FIRE_WEAPON_LEFT
0x30 EV_FIRE_WEAPON_LASTSHOT_LEFT
0x31 EV_EJECT_BRASS_LEFT
0x98 EV_FOOTSTEP_SPRINT
0x99 EV_FOOTSTEP_RUN
0x9A EV_FOOTSTEP_WALK
0x9B EV_FOOTSTEP_PRONE
0x9C EV_JUMP
0x9D EV_LANDING_HARD
0x9E EV_LANDING_PAIN
0x9F EV_MANTLE
0xA0 EV_SCOPE_ZOOM
```

**⇒ 28 个。**

### 9.2 而那段

```php
// EVENTS THE OWNER'S OWN CLIENT ALREADY PLAYS FROM ITS OWN PREDICTION.
//
// MEASURED 2026-10-08: the owner was hearing its footsteps and its
// reload twice. The ring-advance probe showed advance=1 on every frame
// (so nothing is being replayed) and the slot ids are exactly the
// client-predicted set -- 0x19..0x1E reload, 0x1F..0x24 weapon
// handling, 0x2D/0x2E rechamber/brass, 0x98..0x9F footsteps / jump /
// landing / mantle, 0xA0 scope zoom. This server was publishing those
// back to the very client that predicted them, so the local player got
// its own reload and footstep sounds twice. The fire event was already
// suppressed here for the same reason; the rest of the predicted set
// was simply missed.
//
// Ids are the client's own eventnames table (163 entries, VA
// 0x00E5FD38, extracted 2026-10-08), not a guess.
```

### 9.3 八层

```text
1. **是所有者自己的客户端已经从它自己的预测播放的事件**
2. ⇒ **实测 2026-10-08：所有者在【两次】听到自己的脚步声和换弹**
3. ⇒ **环推探针显示每帧 `advance=1`**（所以没有东西被重播）
4. ⇒ **而槽 id 正好是客户端预测集**：
     · `0x19..0x1E` 换弹
     · `0x1F..0x24` 武器处理
     · `0x2D/0x2E` 重新上膛/抛壳
     · `0x98..0x9F` 脚步/跳/落地/翻越
     · `0xA0` 开镜变焦
5. ⇒ **这个服务器把这些发布回【预测它们的那同一个客户端】**
6. ⇒ **所以本地玩家得到自己的换弹与脚步声两次**
7. ⇒ **开火事件已经因为同样理由在这里被压制；预测集的其余部分只是被漏掉了**
8. ⇒ **id 是客户端自己的 eventnames 表（`163` 项，VA `0x00E5FD38`，2026-10-08 提取），不是猜的**
```

### 9.4 而 **`163` 项**

**⚠ 而 §5.3 的 `dword_DA9410` 是 **170** 项。**
**⇒ 两张表**不同**。**

```text
0x00E5FD38   163 项   eventnames（名字）
dword_DA9410 170 项   宽度表
```

**✅ 一个**关键的区分**。**

### 9.5 而`filterOwnerPredictedEvents` 的**两个过滤**

```cpp
const auto owner = find_if(source, [clientNum](e) {
    return e.eType == EntityTypePlayer && e.number == clientNum && e.clientNum == clientNum;
});
const bool suppressOwnerEvents = owner != source.end() &&
    any_of(owner->events, isOwnerPredictedEvent);
const auto excluded = [&](const SvEntityState &e) {
    if (e.eType != EntityTypeEventBase + 117) return false;
    const auto r = viewFxRecipients.find(e.number);
    return r == viewFxRecipients.end() || r->second != clientNum;
};
if (!suppressOwnerEvents && !any_of(source, excluded)) return &source;
filtered = source;
if (suppressOwnerEvents) for (auto &event : filtered[owner - source.begin()].events)
    if (isOwnerPredictedEvent(event)) event = {};
erase_if(filtered, excluded);
return &filtered;
```

### 9.6 四层

```text
① 找到 owner（`eType == Player` 且 `number == clientNum` 且 `clientNum == clientNum`）
② 若它有任一预测事件 ⇒ `suppressOwnerEvents`
③ `excluded`：`eType == EntityTypeEventBase + 117` 且（无收件人记录 或 收件人不是本客户端）
④ 若两者都不触发 ⇒ **返回原向量**（零拷贝）
```

### 9.7 而 **`EntityTypeEventBase + 117`**

```php
// CODREF(sv_build_client_snapshot): original Factory eType140 is
// first-person only; IDA532910 case117 always targets local DObj2048.
```

**⇒ 四层**：

```text
1. 原 Factory 的 **eType 140**
2. ⇒ **它是第一人称独有的**
3. ⇒ `IDA532910` 的 **`case 117`** 总是以**本地 `DObj2048`** 为目标
4. ⇒ 所以 `EntityTypeEventBase + 117` = 那个 eType
```

**✅ 所以 `EntityTypeEventBase + 117 == 140`。**

**⇒ 所以 `EntityTypeEventBase == 23`。**

**✅ **一个可推算的常数**。

### 9.8 而 `viewFxRecipients` 的**代际**

```php
// OLMOD(factory_view_fx): recipient metadata is archived so filtering
// the baseline uses its own generation, never today's entity owner.
```

**⇒ 三层**：

```text
1. 收件人元数据被【归档】
2. ⇒ 所以**过滤基线用它自己的代际**
3. ⇒ **绝不是今天的实体所有者**
```

**✅ 一个**避免跨帧错误归因**的设计。**

**✅ 与 §341 的"在整个记录上比较"同族（**记录自身的状态**）。**

## 十、`roundedOrigin` / `writeEntityOrigin`（本组第七重要）

### 10.1 `roundedOrigin`

```cpp
std::optional<int32> roundedOrigin(const float value)
{
    if (!std::isfinite(value)) return std::nullopt;
    const auto rounded = std::floor((double)value + 0.5);
    if (rounded < INT32_MIN || rounded > INT32_MAX) return std::nullopt;
    return (int32)rounded;
}
```

**⇒ 三层**：

```text
① 非有限 ⇒ 失败
② **`floor(value + 0.5)`** ⇒ 四舍五入（对负数是**向零**）
③ 越 int32 ⇒ 失败
```

**⚠ `floor(-1.5 + 0.5) = floor(-1.0) = -1`。**

**⇒ 所以 `-1.5 → -1` 而 `-2.5 → -2`。**

**✅ 那是**"四舍五入远离零"的对称形式**（不是向零）。**

**⇒ 标准 ICU/Java 的 `Math.round` 也是这个。**

### 10.2 `writeEntityOrigin` 的**六层**

```cpp
bool writeEntityOrigin(MsgWriter &m, float value, float baseline, float mapCenter)
{
    const auto rv = roundedOrigin(value), rb = roundedOrigin(baseline), rc = roundedOrigin(mapCenter);
    if (!rv || !rb || !rc) return false;

    const auto cv = (int64)*rv - *rc + 0x8000;         // ① 以地图中心为中心
    const auto cb = (int64)*rb - *rc + 0x8000;
    if (cv < 0 || cv > 0xFFFF || cb < 0 || cb > 0xFFFF) return false;   // ② 16 位窗口

    const auto delta = (int64)*rv - *rb;               // ③ 用【原始值】的增量
    if (delta >= -64 && delta <= 63) {                 // ④ 7 位增量
        m.MSG_WriteBits(0, 1);
        m.MSG_WriteBits((int32)(delta + 64), 7);
    } else {
        m.MSG_WriteBits(1, 1);
        m.MSG_WriteBits((int32)(cv ^ cb), 16);         // ⑤ 16 位中心化 XOR
    }
    return !m.overflowed();                            // ⑥
}
```

### 10.3 **"中心化"是一个 ±32K 的窗口**

**⇒ 三层**：

```text
1. `value - mapCenter + 0x8000`
2. ⇒ 所以**相对地图中心在 ±32768 之内**
3. ⇒ 超出 ⇒ **失败**（不是截断）
```

**✅ 与 §321 的"界是【线宽】不是观测范围"**不同** —— 这里是**真实的坐标窗口**（±32K 是 16 位有符号的量程）。**

**⚠ 而 ±32K 单位 = 一个巨大的地图。**

**⇒ 合理。**

### 10.4 而 ④ **7 位增量**

**⇒ `[-64, 63]` ⇒ 128 个值 ⇒ 7 位 ✓**

**✅ 与 §323 的"`delta + 64`"同族。**

**⚠ 而 §321 的 `delta >= -16 && delta <= 15` 是 5 位（`movementDir` 在下面）。**

**⇒ 两个宽度。**

### 10.5 而 ⑤ **16 位 `cv ^ cb`**

**⇒ 三层**：

```text
1. XOR 两个【中心化】值
2. ⇒ 16 位
3. ⇒ 客户端 `cb ^ 载荷` 重建 `cv`
```

**✅ 而注意 ③ 用的是**原始值**的 delta 而 ⑤ 用的是**中心化**值的 XOR。**

**⇒ 两个不同基准。**

**⚠ 这是**故意的**：③ 测"有多近"而 ⑤ 编码"在哪里"。**

**✅ 一个**正确的设计**（因为绝对值必须在中心化域里）。**

## 十一、`writeEntityAngle` 的**双零位 + 16 位**

```cpp
void writeEntityAngle(MsgWriter &m, const float value)
{
    m.MSG_WriteBits(0, 1);                              // ①
    m.MSG_WriteBits(0, 1);                              // ②
    const auto normalized = std::fmod(value, 360.0f);
    m.MSG_WriteShort((uint16)(int32)(normalized * (65536.0f / 360.0f)));
}
```

**⇒ 三层**：

```text
① 两个 0 位（"不全角" + "无压缩增量"？）
② `fmod(value, 360)`
③ `value * 65536/360` ⇒ 16 位
```

### 11.1 而那段注释

```php
// CODOL -79 supports compressed deltas and this canonical full
// branch. Full angle16 keeps this first recovery independent of
// the still-unmapped client delta lookup table.
```

**⇒ 四层**：

```text
1. **CODOL -79 支持压缩增量**
2. ⇒ **而这（两个 0）是那个规范的全量分支**
3. ⇒ **全量 angle16 让这个首次恢复不依赖仍未映射的客户端增量查找表**
4. ⇒ **一个诚实的"故意不走增量"**
```

**✅ 与 §322 的"更好的是省略而不是错"同族（第十次）。**

### 11.2 而**两个位是两条路**

```text
第 1 位  0 = 全量
第 2 位  0 = ？（可能"无增量"）
```

**⚠ 两个位都写 0 ⇒ 全量。**

**⇒ 所以 -79 有**两级的压缩**。**

### 11.3 而 `fmod` 的**符号**

**⇒ `fmod(-90, 360) = -90`。**

**⇒ 而 `-90 * 65536/360 = -16384` ⇒ 转 `uint16` ⇒ `49152`。**

**✅ 模 65536 ⇒ 正确（-90° = 270°）。**

**⚠ 但 `-16384` 转 `uint16` 是**实现定义**在 C++20 之前，现在是**模**。**

**✅ C++20 起明确定义。**

## 十二、`writeEntityGround` 的**三级**

```cpp
void writeEntityGround(MsgWriter &m, uint32 groundEntityNum)
{
    if (groundEntityNum == EntityNumWorld) { m.MSG_WriteBits(1, 1); return; }   // ①
    m.MSG_WriteBits(0, 1);
    if (!groundEntityNum) { m.MSG_WriteBits(1, 1); return; }                    // ②
    m.MSG_WriteBits(0, 1);
    m.MSG_WriteBits(groundEntityNum & 7, 3);                                    // ③
    m.MSG_WriteByte((uint8)(groundEntityNum >> 3));                             // ④
}
```

**⇒ 四层**：

```text
① `EntityNumWorld` ⇒ 一个 1 位
② 零 ⇒ 0 + 1（共 2 位）
③ 否则 ⇒ 0 + 0 + 3 位低 + 8 位高（共 13 位）
```

### 12.1 **"3 + 8 = 11 位"**

**⇒ `groundEntityNum & 7`（3 位）与 `>> 3`（8 位）= **11 位**。**

**✅ **第五次确认 11 位实体号**。**

### 12.2 而 `EntityNumWorld` 与**零**是**不同的**

**⇒ 三层**：

```text
`EntityNumWorld`（世界/无地面）⇒ 1 位
`0`（实体 0）⇒ 2 位
其它 ⇒ 13 位
```

**✅ 所以**世界与零是两个不同的语义**。**

**⚠ 而 §338 的 `isAgent = modelIndex != 0`**同族（零有特殊含义）。

## 十三、`writeEntityTrajectoryTime` 的**两分支**

```cpp
void writeEntityTrajectoryTime(MsgWriter &m, uint32 value, uint32 serverTime)
{
    if (value <= serverTime && serverTime - value <= 0xFF) {
        m.MSG_WriteBits(0, 1);
        m.MSG_WriteBits(serverTime - value, 8);      // 1 + 8
        return;
    }
    m.MSG_WriteBits(1, 1);
    m.MSG_WriteLong(value);                          // 1 + 32
}
```

**⇒ 三层**：

```text
① 若 `value` 在过去 255ms 内 ⇒ 1 + 8 位"多久之前"
② 否则 ⇒ 1 + 32 位绝对
```

**✅ 与 §341/-97 的 `writeCommandTime`（"1 位 + 8 位回退计数 或 32 位全量"）**完全同族 ✓**

**⇒ **第二次确认那个编码**。**

## 十四、`writeEntityMovementDir` 的**两分支**

```cpp
void writeEntityMovementDir(MsgWriter &m, int32 value, int32 baseline)
{
    const auto delta = (int64)value - baseline;
    if (delta >= -16 && delta <= 15) {
        m.MSG_WriteBits(1, 1);
        m.MSG_WriteBits((int32)(delta + 16), 5);     // 1 + 5 = 6 位
        return;
    }
    m.MSG_WriteBits(0, 1);
    m.MSG_WriteByte((uint8)(value ^ baseline));      // 1 + 8 = 9 位
}
```

**⇒ 三层**：

```text
① `[-16, 15]` ⇒ 1 + 5 位（6 位）
② 否则 ⇒ 1 + 8 位 XOR（9 位）
```

**✅ 与 §323 的 `writeSkippedFieldIndex` 的"1 位若 delta==1"不同 —— 这里**第一位是"紧凑与否"的反向**（1 = 紧凑）。**

**⚠ 而 §337 的 `writeClientNumber` 也是 1 = 连续。**

**⇒ 所以两种位极性在同文件里都存在：**

```text
writeSkippedFieldIndex   1 = 相邻（紧凑），0 = 跳号
writeEntityOrigin        0 = 7 位增量，1 = 16 位全量     ← 【反向】
writeEntityMovementDir   1 = 5 位增量，0 = 8 位 XOR
writeEntityEvent         0 = 同 id，1 = 不同 id
writeEntityTrajectoryTime 0 = 相对，1 = 绝对              ← 【反向】
writeEntityEventSequence 1 = 紧凑，0 = 回退
```

**✅ 所以**六处，四正两反**。**

**⚠ 这是一个**极高风险的细节**：读错一个极性就让整段失步。**

**⇒ 与 §337 的"写 3 而客户端读 11"同族。**

## 十五、关键结论

1. **玻璃片三段（2 / 3 / 23 位），而 `glassImpactBitCount` 的 21 = 1+8+6+6** —— 两个函数**完全吻合**。
2. **`writeEntityNumber` 的两分支**（连续 1 位 / 跳跃 2+11 = 13 位），而 `0 1` 可能编码"绝对"。
3. **`packEntityWeapon` 把两个 16 位索引装进一个 32 位字**。
4. **⭐ "一个超过宽度表的事件 id 不是无效事件"** —— `dword_DA9410` 170 项而客户端接受 180。
5. **`validEntityEvent` 的三分支**，而**无宽度 ⇒ 参数必须为 0**。
6. **`validItemEntity` 的四十项 AND**（约 12 正面 / 28 零），而 **`positionTrajectoryType == 3` 与 `positionTrajectoryDuration == 50` 是两个魔法常数**。
7. **`movementDir == 0` 与 §318 的"`movementDir` 写在了 DObj scale 位置"互相印证**。
8. **⭐ "`uint8_t` 就是预测事件重复 bug"** —— 编解码器 -75 是**32 位**，八位是**回退**的宽度。
9. **三个截断点**（entity 函数 / 两个 playerState 调用点 / `& 0xFF` 填游标）。
10. **实测六条**（567 次回跳、±255 是模算术的 ±1、802/774 环溢出、629/642 整环、90% 空写）。
11. **⭐ "在 256 以下不可见 ⇒ 任何服务端度量都显示不出来 ⇒ 必须从客户端读"**。
12. **`writePlayerStateEventSequence` 用 `uint32` 非模**（回绕处故意选回退）**而 `writeEntityEventSequence` 用 `uint8` 模**（fixture 要求）—— 两个都正确。
13. **`isOwnerPredictedEvent` 的 28 个 id**，来自 `0x00E5FD38` 的 **163 项** eventnames 表。
14. **`EntityTypeEventBase + 117 == 140`** ⇒ **`EntityTypeEventBase == 23`**。
15. **`viewFxRecipients` 归档元数据以保证"过滤基线用基线自己的代际"**。
16. **`writeEntityOrigin` 的六层**（四舍五入 / ±32K 窗口 / 7 位增量 / 16 位中心化 XOR），而**③ 用原始 delta 而 ⑤ 用中心化 XOR** —— 故意的两个基准。
17. **`writeEntityAngle` 双零位 + `fmod 360` + `×65536/360`**，而注释诚实说明"故意不走增量"。
18. **`writeEntityGround` 的三级**，3+8 = **第五次确认 11 位**，而 `EntityNumWorld` 与 `0` 是**两个不同语义**。
19. **`writeEntityTrajectoryTime` 与 -97 完全同族（第二次确认）**。
20. **⭐ 六处位极性，四正两反** —— 读错一个极性整段失步。

## 十六、未闭合点

- `writeEntityNumber` 的 `0 0` 分支（终止在哪里）。
- `writeEntityAngle` 第二位的确切语义。
- `dword_DA9410` 的 170 项宽度表内容。
- `163` 项 eventnames 表的完整清单。
- `EntityTypeEventBase == 23` 是否另有独立证据。
- `sv_snapshot_mp.cpp` 6000 行之后未读取（27,016 行，进度 22%）。
