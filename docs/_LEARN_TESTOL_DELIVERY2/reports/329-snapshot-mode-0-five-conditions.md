# 329 · **模式 0 的五个条件**、**"省略 changeHint==3 字段才使它安全可发"**、约 130 个 `!xxxChanged`

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 3189–3400 行。

## 二、**模式 0 的五个条件**（本组最重要的一段）

### 2.1 那段

```php
// THE BIT IS NO LONGER HARDCODED. out.exe's own writer sub_678740
// picks mode 0 when, and only when, all of these hold:
//
//     !ctx[25] && !ctx[30]                 two context flags
//     from != nullptr                      there is a baseline
//     dword_7ACC398                        a global toggle
//     |to->origin - ctx[16]->[1760]|^2 <= 0.0099999998
//     ctx[16]->[1772] == to->commandTime
//
// where ctx[16]->[1760..1772] is the origin and command time the
// CLIENT reported back in its own move packet.
```

### 2.2 五项

```text
① !ctx[25] && !ctx[30]                两个上下文标志
② from != nullptr                     【有基线】
③ dword_7ACC398                       【一个全局开关】
④ |to->origin - ctx[16]->[1760]|² <= 0.0099999998
⑤ ctx[16]->[1772] == to->commandTime
```

### 2.3 而 **`0.0099999998` 是 `0.1²`**

**⇒ `sqrt(0.0099999998) = 0.099999999 ≈ 0.1`。**

**✅ 所以容差是**0.1 单位**。**

**⇒ 而 `SvPredictedOriginToleranceSquared` 应该就是那个值。**

### 2.4 而 `ctx[16]->[1760..1772]` 是**客户端回传的移动包**

**⇒ 三层**：

```text
1. `ctx[16]` 是一个上下文指针
2. ⇒ `+1760` 是 **origin** 而 `+1772` 是 **commandTime**
3. ⇒ **而那是【客户端】在它自己的 move 包里回传的**
```

**✅ 所以模式 0 是"客户端与服务端的预测一致"。**

### 2.5 而 `sub_675E70` 的**那个条件**

```php
// sub_675E70 then answers "unchanged" for every changeHint==3 field
// in that mode (`if (hint == 3 && !ctx[25]) return mode;`), so the
// nine predicted fields are OMITTED rather than re-encoded, and
// sub_671D80's sub_470D30 restores origin, velocity, +0x2C and
// +0x100 on the client from ITS OWN prediction record.
```

### 2.6 五层

```text
1. `sub_675E70` 然后对每一个 `changeHint==3` 字段回答"未变"
2. ⇒ 条件：`if (hint == 3 && !ctx[25]) return mode;`
3. ⇒ 所以**那九个预测字段被【省略】** 而不是被重新编码
4. ⇒ 而 **`sub_671D80` 的 `sub_470D30` 在客户端从【它自己的预测记录】恢复**
5. ⇒ **origin、velocity、`+0x2C` 与 `+0x100`**
```

**✅ 所以"省略"是**规范要求的**。**

### 2.7 而 **`+0x2C` 与 `+0x100`**

**⇒ 两个偏移。**

**⚠ 而 §328 的四个 `changeHint==3` 字段是 `origin`/`velocity`/`bobCycle`/`movementDir`。**

**⇒ 所以 `+0x2C` 与 `+0x100` 可能是 `bobCycle` 与 `movementDir` 的偏移。**

**✅ 四个字段四个恢复点。**

## 三、**"那个省略才使它安全可发"**（本组第二重要）

### 3.1 那段

```php
// AND THAT OMISSION IS WHAT MAKES THIS SAFE TO SHIP. The reader's
// flag for a changeHint==3 field is `mode && hint == 3`, and a
// zero flag switches its codec from raw to XOR-against-baseline --
// a decode path this writer has never emitted a byte for. Writing
// no such field in mode 0 means that path is never reached, so
// mode 0 cannot make a message undecodable. The worst it can do is
// let a client trust a prediction it should not have, which the
// next mode-1 frame corrects.
```

### 3.2 六层

```text
1. **那个省略才使它安全可发**
2. ⇒ **读者对一个 `changeHint==3` 字段的标志是 `mode && hint == 3`**
3. ⇒ **而一个零标志把它的 codec 从 raw 切到 XOR-against-baseline**
4. ⇒ **一个这个写入器【从未发出过字节】的解码路径**
5. ⇒ **在模式 0 写没有这样的字段 ⇒ 那条路径永不被到达**
6. ⇒ **所以模式 0 不能使一个消息不可解码**
7. ⇒ **它能做的最坏的事是让一个客户端信任一个它不该有的预测，而那由下一个模式 1 帧纠正**
```

### 3.3 **"一个这个写入器从未发出过字节的解码路径"**

**✅ 三层**：

```text
1. 零标志 ⇒ XOR codec
2. ⇒ 而**我们从没发过**
3. ⇒ 所以**那条路径未验证**
```

**⇒ 与 §324 的"两个事件写入器不能合并"、§321 的"用一个观测范围作界会拒绝"同族**（第二十六次"未验证的路径"）。

### 3.4 而"**最坏是让客户端信任一个不该有的预测**"

**✅ 与 §244 的"两个方向代价不对称"同族**（第八次）。

## 四、**字段 4 的唯一逃逸**（本组第三重要）

```php
// Field 4 is the one changeHint==3 field that can escape: its
// codec is -70, and sub_675E70 returns 1 for a -70 field whenever
// ps+0x404 is non-zero, whatever the mode. Retail would then emit
// it XOR-encoded. This forces mode 1 for that frame instead. It is
// stricter than retail and costs a handful of mode-1 frames.
//
// TODO(CODOL): retain the +0x4A4 offset-derived name until a
// CODOL producer proves the Ghosts weaponIdleTime analogy.
const auto sendUnk04A4Time = state.weaponPositionFraction != 0.0f;
```

### 4.1 五层

```text
1. **字段 4 是唯一能逃逸的 `changeHint==3` 字段**
2. ⇒ 它的 codec 是 **`-70`**
3. ⇒ 而 **`sub_675E70` 对一个 `-70` 字段在 `ps+0x404` 非零时【无论什么模式】都返回 1**
4. ⇒ **零售那时会 XOR 编码地发出它**
5. ⇒ **所以这强行让那一帧用模式 1**
6. ⇒ **它比零售更严格，而代价是少数几个模式 1 帧**
```

### 4.2 而 `sendUnk04A4Time = state.weaponPositionFraction != 0.0f`

**⇒ 三层**：

```text
1. 字段 4 是 `+0x4A4` 的时间
2. ⇒ 而它的**触发条件是 `weaponPositionFraction != 0`**
3. ⇒ 所以"武器位置分数非零"⇒ 强制模式 1
```

**⚠ 两个不同的量被绑在一起。**

**⇒ 但注释说"保留 `+0x4A4` 这个偏移派生的名字直到一个 CODOL 生产者证明 Ghosts 的 `weaponIdleTime` 类比"。**

**✅ 一个**有意的近似**。**

### 4.3 而 `-70` 是**第十一个负 codec**

```text
-7, -8, -57, -58, -65, -70, -75, -86, -94, -97, -100    （十一个）
```

## 五、`predictionStands` 的**四项**

```cpp
const auto sendUnk04A4Time = state.weaponPositionFraction != 0.0f;
const auto predictionAvailable = clientPrediction != nullptr && clientPrediction->valid;
const auto predictedCommandTimeMatches = predictionAvailable &&
    clientPrediction->commandTime == state.commandTime;
const auto predictedOriginDistanceSquared = [&] {
    if (!predictionAvailable) return -1.0f;
    const auto dx = state.origin[0] - clientPrediction->origin[0];
    const auto dy = state.origin[1] - clientPrediction->origin[1];
    const auto dz = state.origin[2] - clientPrediction->origin[2];
    return dx * dx + dy * dy + dz * dz;
}();
const auto predictionStands = baseline != nullptr &&
    predictedCommandTimeMatches &&
    predictedOriginDistanceSquared >= 0.0f &&
    predictedOriginDistanceSquared <= SvPredictedOriginToleranceSquared;
```

### 5.1 四项

```text
① baseline != nullptr
② predictedCommandTimeMatches
③ distance² >= 0
④ distance² <= 容差²（0.0099999998）
```

**✅ 与 §2 的五个条件**部分对应**（②④⑤）。**

**⚠ 缺 `!ctx[25] && !ctx[30]` 与 `dword_7ACC398`。**

**⇒ 所以**两个上下文条件与一个全局开关没有实现**。**

**✅ 一个**已知的简化**（注释说"服务器还不拥有"）。**

### 5.2 而 `predictedOriginDistanceSquared` 的 **`-1.0f` 哨兵**

**⇒ 当 `!predictionAvailable` 时 `-1.0f`。**

**⇒ 所以 `>= 0` 的检查同时验证了"可用"。**

**✅ 与 §235 的 `INT32_MIN` 同族（第十四次哨兵）。**

### 5.3 而 `AllowPredictedFieldsMode0 = true`

```cpp
constexpr bool AllowPredictedFieldsMode0 = true;
const auto sendPredictedFields = !AllowPredictedFieldsMode0 ||
    !predictionStands || sendUnk04A4Time;
```

**⇒ 三层**：

```text
1. `AllowPredictedFieldsMode0 = true`（编译期）
2. ⇒ 所以 `!AllowPredictedFieldsMode0` 为假
3. ⇒ `sendPredictedFields = !predictionStands || sendUnk04A4Time`
```

**✅ 所以**模式 0 是可达的**（当 predictionStands 且无 weaponPositionFraction）。**

### 5.4 而那段中文注释（前一段）

```php
// Retail mode 0 keeps the client's predicted movement when its
// command time and origin agree with the authoritative state. The
// former stalls that made this unsafe are gone: live frame work is
// inside the 100 ms budget, the queue holds 32 commands, and the
// default now drains the bounded burst. Any mismatch still selects
// mode 1 and corrects the client on this snapshot.
```

**⇒ 五层**：

```text
1. **零售模式 0 保持客户端预测的移动** 当它的命令时间与 origin 与权威状态一致
2. ⇒ **之前使这不安全的停顿都没有了**：
     · **活的帧工作在 100 ms 预算内**
     · **队列持有 32 个命令**
     · **默认现在排空有界的爆发**
3. ⇒ **任何不匹配仍然选择模式 1 并在这个快照上纠正客户端**
```

**✅ 三个"不安全的停顿"已解决。**

**⇒ 与记忆里"`PendingUserCmdCapacity = 32`"、"usercmd per-packet capacity 32"**完全一致** ✓**

## 六、**约 130 个 `!xxxChanged`**（本组第四重要）

### 6.1 那个巨大的 `if`

```cpp
if (!commandTimeChanged && !sendUnk04A4Time && !sendOrigin &&
    !any_of(sendVelocity, identity) &&
    !anyViewAngleChanged && !anyDeltaAngleChanged && !pmFlagsChanged &&
    !grenadeEntityChanged && !weaponFlagsChanged && !grenadeTimeChanged &&
    !pmTimeChanged && !offhandWeaponChanged && !offhandSlotsChanged &&
    !eFlagsChanged && !holdBreathSwayScaleChanged && !holdBreathTimerChanged &&
    !otherFlagsChanged && !killstreakChanged && !rewardsChanged &&
    !radarFlagsChanged && !rewardActionChanged && !gravityChanged && !speedChanged &&
    !moveSpeedScaleMultiplierChanged && !clientNumChanged && !legsTimerChanged &&
    !legsAnimChanged && !torsoTimerChanged && !torsoAnimChanged &&
    !anyWeaponAnimChanged && !anyWeaponStateChanged &&
    !weaponTimeChanged[0] && !weaponTimeChanged[1] && ... )
{
    writeEmptyPlayerState(message);
    return;
}
```

### 6.2 计数

**⇒ 我数到约 **130** 个条件。**

**⇒ 所以"什么都没有变化"的判定需要**130 项 AND**。**

**⚠ 这是一个**极长的条件**（一个维护风险）。**

**✅ 与 §315 的"二十一项"、§317 的"六项"同族 —— 本文件最长的一个。**

### 6.3 而缺项的后果

**⇒ 如果**漏掉一个**字段的 `Changed`：**

```text
1. 那个字段变了而 130 项检查仍全真
2. ⇒ 走 `writeEmptyPlayerState`
3. ⇒ **那个变化永不发出**
```

**⚠ 一个**静默的漏发**。**

**✅ 与 §322 的"漏字段失步"不同 —— 这里**不失步但漏数据**。**

**⚠ 更隐蔽。**

## 七、`includeChangedField` 的**两项**

```cpp
std::uint32_t lastChangedField{};
const auto includeChangedField = [&lastChangedField](bool changed, uint32 fieldIndex) {
    if (changed)
        lastChangedField = std::max(lastChangedField, fieldIndex + 1);
};
```

**⇒ 三层**：

```text
1. 只在变化时更新
2. ⇒ 取 `max`
3. ⇒ 而 `fieldIndex + 1`（【1-based】）
```

**✅ 与 §325 的 `lastField + 1` 同族（第二次 1-based）。**

### 7.1 而**调用顺序不重要**（因为 `max`）

**✅ 所以可以乱序调用 `includeChangedField`。**

**⚠ 但写入时必须**按索引升序**（§319 的教训）。**

## 八、`includeChangedField` 的**前十六个**

```cpp
includeChangedField(commandTimeChanged, 0);
includeChangedField(sendUnk04A4Time, PlayerStateUnk04A4TimeField);   // 4
includeChangedField(weaponTimeChanged[0], PlayerStateRightWeaponTimeField);  // 3
includeChangedField(torsoTimerChanged, PlayerStateTorsoTimerField);  // 5
includeChangedField(aimSpreadScaleChanged, PlayerStateAimSpreadScaleField);  // 6
includeChangedField(legsAnimChanged, PlayerStateLegsAnimField);      // 7
includeChangedField(weaponAnimChanged[0], PlayerStateRightWeaponAnimField);  // 9
includeChangedField(sendOrigin, 11);
includeChangedField(sendBobCycle, PlayerStateBobCycleField);         // 12
includeChangedField(sendVelocity[1], 13);
includeChangedField(sendVelocity[0], 14);
includeChangedField(sendMovementDir, PlayerStateMovementDirField);   // 15
includeChangedField(sendVelocity[2], 16);
includeChangedField(weaponStateChanged[0], PlayerStateRightWeaponStateField);  // 17
includeChangedField(viewAngleChanged[1], 18);
includeChangedField(viewAngleChanged[0], 19);
includeChangedField(eventSequenceChanged, PlayerStateEventSequenceField);  // 1
```

**⚠ 而 `eventSequenceChanged`（字段 1）**在最后而字段号最小**。**

**⇒ 但因为用 `max` 所以无影响** ✓

## 九、关键结论

1. **⭐ 模式 0 的五个条件**：两个上下文标志 / 有基线 / 全局开关 / origin 距离 ≤ 0.1² / commandTime 匹配。
2. **`0.0099999998` = `0.1²`** ⇒ 容差 0.1 单位。
3. **`ctx[16]->[1760..1772]` 是客户端回传的 origin 与 commandTime**。
4. **`sub_675E70` 的 `if (hint == 3 && !ctx[25]) return mode;`** ⇒ 九个预测字段被**省略**。
5. **`sub_470D30` 从客户端自己的预测记录恢复四个字段**（`origin`/`velocity`/`+0x2C`/`+0x100`）。
6. **⭐ "那个省略才使它安全可发"** —— 因为零标志会切到**一个从未发过字节的解码路径**。
7. **"最坏是让客户端信任一个不该有的预测，由下一个模式 1 帧纠正"**。
8. **字段 4 是唯一逃逸的**（codec `-70`，`ps+0x404` 非零时无论模式都返回 1）⇒ 强制模式 1。
9. **`sendUnk04A4Time = weaponPositionFraction != 0`** —— 两个量被绑在一起，且有 TODO。
10. **`predictionStands` 四项**，而**缺两个上下文条件与一个全局开关**（已知简化）。
11. **`-1.0f` 哨兵** 同时表示"不可用"（因为 `>= 0` 的检查）。
12. **`AllowPredictedFieldsMode0 = true`** ⇒ 模式 0 可达。
13. **三个"不安全的停顿"已解决**（100 ms 预算 / 32 命令队列 / 排空爆发）。
14. **约 130 项 AND 的"什么都没变"判定** —— 本文件最长的条件，且**漏一项会静默漏发**。
15. **`includeChangedField` 用 `max` 所以调用顺序不重要**，但写入必须升序。
16. **`eventSequenceChanged`（字段 1）在最后调用** —— 因为 `max` 无影响。

## 十、未闭合点

- `ctx[25]` / `ctx[30]` / `dword_7ACC398` 三个未实现的条件。
- `+0x2C` 与 `+0x100` 对应哪两个字段。
- 130 项里是否有遗漏（无法静态确定）。
- `sv_snapshot_mp.cpp` 3400 行之后未读取（1.47 MB，进度 23%）。
