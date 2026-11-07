# 330 · **约 120 个 `includeChangedField`**、六处**字面量字段号**、"`max` 所以列表顺序只是文档"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 3387–3600 行。

## 二、`includeChangedField` 的**约 120 次调用**

### 2.1 分组

#### ① 前 20（§329 已列）

```text
0     commandTime
4     Unk04A4Time
3     RightWeaponTime
5     TorsoTimer
6     AimSpreadScale
7     LegsAnim
9     RightWeaponAnim
11    origin（字面量）
12    BobCycle
13    Velocity[1]（字面量）
14    Velocity[0]（字面量）
15    MovementDir
16    Velocity[2]（字面量）
17    RightWeaponState
18    viewAngle[1]（字面量）
19    viewAngle[0]（字面量）
（事件环 1/2/21..24）
```

#### ② 中部（本节）

```text
20    pmFlags（字面量）
27    TorsoAnim
28    EFlags
29    viewAngle[2]（字面量）
30    HoldBreathScale
31    LegsTimer
35    LastSprintStart
36    LastSprintEnd
34    viewHeightCurrent（字面量）
38    viewHeightTarget（字面量）
39    CurrentWeapon
41    WeaponPositionFraction
43    SprintStartMaxLength
44    RightWeaponDelay
45    deltaAngle[1]（字面量）
47    GroundEntity
51    LeftWeaponAnim
52    PmTime
53    OffhandWeapon
57    GrenadeEntity
77    WeaponFlags
79    GrenadeTime
109..111  OffhandSlots（3 个）
54    OtherFlags
56    ViewmodelIndex
58    MoveSpeedScaleMultiplier
59    ClientNum
60    Speed
62    LeftWeaponState
63    Gravity
67    CursorHint
78    CursorHintEntity
80    CursorHintString
68    ViewEntity
70    deltaAngle[0]（字面量）
81    viewHeightLerpTarget
83    PmType
87    RightWeaponShotCount
89    viewHeightLerpDown
92    viewHeightLerpTime
93    SprintDelay
94/95/96/97  Prone（4 个）
98    CursorHintDualWield
99    MantleFlags
101   SprintButtonUpRequired
102   JumpTime
103/104/105  Shellshock（3 个）
106   DualWieldActive
107   LeftWeaponDelay
108   MantleTimer
113   MantleTransitionIndex
114   JumpOrigin
115   MantleYaw
121   RightWeaponHandFlags
122   PerkHudVisible
86    CompassRadar
88    Killstreak
82    RadarFlags
187   RewardActionType
204   RewardActionWeapon
123/124/125  Perks（3 个）
126..130  RewardIds（5 个）
131..135  RewardTargets（5 个）
136/137/138  KillCam（3 个）
140   LeftWeaponShotCount
142   KillCamDeltaTime
161   LadderVectorX
162   LeftWeaponTime
163   LeftWeaponHandFlags
168   RemoteTurretEntity
169   RemoteControlTag
172   HoldBreathTimer
177   LadderVectorY
188   LadderVectorZ
189/190  RestrictKickTime（2 个）
191   deltaAngle[2]（字面量）
193/194  SpreadOverride（2 个）
42/55/66/73/74/75  伤害簇（6 个）
219   PlayerSizeScale
227   MovingPlatformEntity
228   RemoteEyesEntity
```

### 2.2 **六个字面量字段号**

```text
11    origin
13    Velocity[1]
14    Velocity[0]
16    Velocity[2]
18    viewAngle[1]
19    viewAngle[0]
20    pmFlags
29    viewAngle[2]
34    viewHeightCurrent
38    viewHeightTarget
45    deltaAngle[1]
70    deltaAngle[0]
191   deltaAngle[2]
```

**⇒ **十三个**字面量而其余用具名常量。**

**⚠ 而其中 `11/13/14/16/18/19/20/29/34/38/45/70/191` 都是**没有具名常量**的字段。**

**⇒ 所以它们是**表里有而未命名的**字段。**

**⚠ 一处显著的不一致（§317 的表里**也没有** 11/13/14/16/18/19/20/29/34/38/45/70/191）。**

**⇒ 所以那十三个是**未命名的 netfield**。**

**✅ 一个重要的观察。**

### 2.3 而 **velocity 的三个索引是 13/14/16**

```text
sendVelocity[1]  ⇒ 13
sendVelocity[0]  ⇒ 14
sendVelocity[2]  ⇒ 16
```

**⚠ **Y 在 X 前**（与 §325 的 `HudElem` 一致）而 **Z 跳过了 15**（那是 `movementDir`）。**

**✅ 所以顺序是 Y(13)、X(14)、movementDir(15)、Z(16)。**

### 2.4 而 **`viewAngle` 的三个索引是 18/19/29**

```text
viewAngleChanged[1]  ⇒ 18   （yaw）
viewAngleChanged[0]  ⇒ 19   （pitch）
viewAngleChanged[2]  ⇒ 29   （roll）
```

**⇒ 三个**不连续**（18、19、29）。**

**✅ 与 §318 的"`ScriptMover` 的索引 5/7/8 不连续"同族。**

### 2.5 而 **`deltaAngle` 的 45/70/191**

```text
deltaAngleChanged[1]  ⇒ 45
deltaAngleChanged[0]  ⇒ 70
deltaAngleChanged[2]  ⇒ 191
```

**⇒ 三个**极不连续**（45、70、191）。**

**⚠ 而 191 与 190（LeftWeaponRestrictKickTime）相邻。**

**✅ 所以 `deltaAngle[2]` 在表里靠近 `restrictKickTime`。**

### 2.6 而 **`viewHeightCurrent = 34` 与 `viewHeightTarget = 38`**

**⚠ 而 §317 的 `PlayerStateViewHeightLerpTargetField = 81`。**

**⇒ 所以 `viewHeight` 有**四个**字段：34、38、81、89、92。**

```text
34    viewHeightCurrent
38    viewHeightTarget
81    viewHeightLerpTarget
89    viewHeightLerpDown
92    viewHeightLerpTime
```

**✅ 五个。**

**⚠ 而 §317 只列了 81/89/92 三个。**

**⇒ 所以 34 与 38 是**未命名的**（用字面量）。**

## 三、**"`max` 所以列表顺序只是文档"**（本组第二重要）

### 3.1 那段

```php
// The three cursor-hint fields. This list only takes a maximum, so
// the position here is cosmetic; the ORDER THAT MATTERS is in the
// writer, where 67 goes between damageEvent (66) and viewEntity
// (68) and 78/80 go between damageDuration (75) and
// viewHeightLerpTarget (81), because the gap coding is ascending.
```

### 3.2 五层

```text
1. **这个列表只取一个最大值 ⇒ 这里的位置只是装饰性的**
2. ⇒ **真正重要的顺序在【写入器】里**
3. ⇒ 那里 **67 在 `damageEvent`（66）与 `viewEntity`（68）之间**
4. ⇒ 而 **78/80 在 `damageDuration`（75）与 `viewHeightLerpTarget`（81）之间**
5. ⇒ **因为间隔编码是递增的**
```

**✅ 与 §319 的"写序必须递增"**完全一致** ✓**

**⇒ 第三次强调。**

### 3.3 而第二处

```php
// The whole damage cluster, in table order. includeChangedField
// takes a maximum, so this list's order is documentation; the WRITE
// order below is what has to ascend.
```

**⇒ 三层**：

```text
1. **整个伤害簇，按表顺序**
2. ⇒ **`includeChangedField` 取最大值 ⇒ 这个列表的顺序是文档**
3. ⇒ **而下面的【写入顺序】才是必须递增的**
```

**✅ 第二次明确的"两处顺序不同"。**

### 3.4 而 **两条"顺序"的概念**

```text
① includeChangedField 的调用顺序  ⇒ 【无关】（取 max）
② write 的调用顺序                ⇒ 【必须递增】
```

**⚠ 两个不同的顺序。**

**✅ 一个**容易混淆的区分**。**

## 四、`Field 122` 的**双重角色**（本组第三重要）

```php
// 122/123/124/125 sit between RightWeaponHandFlags (121) and
// LeftWeaponShotCount (140). Field 122 is a type-2 field, but it still
// contributes its REAL index to the native last-changed scan. When it
// is the highest changed field native writes it in the indexed pass;
// otherwise it is emitted positionally in the second pass below.
includeChangedField(perkHudVisibleChanged, PlayerStatePerkHudVisibleField);
```

### 4.1 四层

```text
1. **122/123/124/125 在 `RightWeaponHandFlags`(121) 与 `LeftWeaponShotCount`(140) 之间**
2. ⇒ **字段 122 是一个 `type 2` 字段**
3. ⇒ **但它仍然把它的【真实索引】贡献给原生 last-changed 扫描**
4. ⇒ 当它**是最高变化字段**时原生在**索引 pass** 里写它
5. ⇒ 否则它在**下面的第二 pass** 里被**按位置**发出
```

### 4.2 而"**type 2 字段**"

**⇒ 与 §317 的"`perkHudVisible` 是 codec `-57`：一位、绝对、无基线 xor"配合。**

**⚠ 而"type 2"与"codec -57"是两个描述。**

**⇒ 可能"type 2"是**netfield 的类型字段**（`{offset, bits, type}`）。**

**✅ 与 §317 的 `PlayerStateOffhandSlotFirstField` 的 `{bits=32, type=0}` 同族。**

### 4.3 而"**两个 pass**"

**⇒ 三层**：

```text
1. 有【索引 pass】（按 lastChanged 索引）
2. ⇒ 与【位置 pass】（第二 pass）
3. ⇒ 所以一个字段可能在**两者之一**被写
```

**✅ 一个**双 pass 的写入架构**。

## 五、`rewardIds` / `rewardTargets` 的**两个循环**

```php
for (uint32 slot = 0; slot < 5; ++slot)
{
    includeChangedField(rewardIds[slot] != oldRewardIds[slot],
        PlayerStateRewardIdFirstField + slot);        // 126..130
    includeChangedField(rewardTargets[slot] != oldRewardTargets[slot],
        PlayerStateRewardTargetFirstField + slot);    // 131..135
}
```

**⇒ 两个循环，各 5 个。**

**✅ 与 §328 的"`rewardIds` 五个"完全一致。**

## 六、`offhandSlots` 的**循环**

```php
for (uint32 slot = 0; slot < offhandSlots.size(); ++slot)
    includeChangedField(offhandSlots[slot] != baselineOffhandSlots[slot],
        PlayerStateOffhandSlotFirstField + slot);     // 109..111
```

**⇒ 三个。**

**✅ 与 §317 的"109..111"**完全一致** ✓**

## 七、**`dualWieldActiveChanged` 出现在两处**

```php
includeChangedField(dualWieldActiveChanged, PlayerStateCursorHintDualWieldField);   // 98
includeChangedField(dualWieldActiveChanged, PlayerStateDualWieldActiveField);       // 106
```

**⇒ 同一个 `bool` 触发**两个字段**（98 与 106）。**

**✅ 与 §317 的"`CursorHintDualWieldField = 98` 与 `DualWieldActiveField = 106`"配合。**

**⇒ 所以"双持"被**编码两次**（98 与 106）。**

**⚠ 可能一个是"提示"而一个是"状态"。**

**✅ 与 §328 的 `dualWieldActive` 从 `unknownState[0]` 推导配合。**

## 八、`compassRadar` 的**字段 86 与 82**

```php
includeChangedField(compassRadarChanged, PlayerStateCompassRadarField);   // 86
includeChangedField(radarFlagsChanged, PlayerStateRadarFlagsField);       // 82
```

**⇒ 两个雷达相关字段：82（`radarFlags`）与 86（`compassRadar`）。**

**✅ 与 §317 的 `PlayerStateRadarFlagsField = 82` 与 `PlayerStateCompassRadarField = 86` 一致。**

## 九、关键结论

1. **约 120 个 `includeChangedField`** 调用。
2. **十三个字面量字段号**（11/13/14/16/18/19/20/29/34/38/45/70/191）—— **表里有而未命名**。
3. **`velocity` 的三个索引 13/14/16**（Y、X、movementDir(15)、Z）。
4. **`viewAngle` 的三个索引 18/19/29**（不连续）。
5. **`deltaAngle` 的三个索引 45/70/191**（极不连续）。
6. **`viewHeight` 有五个字段（34/38/81/89/92）**，而 §317 只列了三个。
7. **⭐ "`max` 所以列表顺序只是文档"** —— 两个顺序的概念（`includeChangedField` 无关 / write 必须递增）。
8. **"67 在 66 与 68 之间，78/80 在 75 与 81 之间"** —— 因为间隔编码递增。
9. **字段 122 是 `type 2` 但贡献真实索引给 last-changed 扫描**。
10. **"两个 pass"**（索引 pass 与位置 pass）。
11. **`rewardIds`/`rewardTargets` 各 5 个，`offhandSlots` 3 个。**
12. **`dualWieldActiveChanged` 触发两个字段（98 与 106）。**
13. **`compassRadar` 是 86 而 `radarFlags` 是 82。**

## 十、未闭合点

- 十三个未命名字段的语义。
- `type 2` 与 codec `-57` 的关系。
- 两个 pass 的完整实现。
- `sv_snapshot_mp.cpp` 3600 行之后未读取（1.47 MB，进度 24%）。
