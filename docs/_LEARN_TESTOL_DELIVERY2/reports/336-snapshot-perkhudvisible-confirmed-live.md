# 336 · **`perkHudVisible` 的 CONFIRMED LIVE**、`-101` 与 `-102` 的两种绝对、**"强制为零 undo 本地 akimbo 预测"**

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 4590–4800 行。

## 二、第二 pass 的**结构**（本组第二重要）

```cpp
for (const auto fieldIndex : PlayerStateSecondPassFields)
{
    if (fieldIndex >= lastChangedFieldIndex)
        break;                                     // ← 【到端点就停】
    if (fieldIndex == PlayerStateRadarFlagsField) { ... }
    else if (fieldIndex == PlayerStateViewHeightLerpDownField) { ... }
    else if (fieldIndex == PlayerStateShellshockDurationField) { ... }
    else if (fieldIndex == PlayerStateSprintDelayField) { ... }
    else if (fieldIndex == PlayerStateSprintButtonUpRequiredField) { ... }
    else if (fieldIndex == PlayerStatePerkHudVisibleField) { ... }
    else { ... 98 与 106 ... }
}
```

### 2.1 三层

```text
① 按 `PlayerStateSecondPassFields` 的**固定顺序**遍历
② ⇒ **`fieldIndex >= lastChangedFieldIndex` ⇒ `break`**
③ ⇒ 所以只有**小于端点**的 hint-2 字段被写
```

**✅ 与 §334 的"一个 hint-2 字段如果它自己是最后一个 ⇒ 在主循环写"**完全配套** ✓**

**⇒ 所以两种路径的分界是 `fieldIndex >= lastChangedFieldIndex`。**

### 2.2 而**八个 hint-2 字段的六个分支 + 一个 `else`**

```text
82    RadarFlags           （单独）
89    ViewHeightLerpDown   （单独）
93    SprintDelay          （单独）
98    CursorHintDualWield  （else）
101   SprintButtonUpRequired（单独）
104   ShellshockDuration   （单独）
106   DualWieldActive      （else）
122   PerkHudVisible       （单独）
```

**⇒ 六个 `else if` + 一个 `else`（覆盖 98 与 106）。**

## 三、`radarFlags` 的 **`-101` codec**（本组第三重要）

```php
if (fieldIndex == PlayerStateRadarFlagsField)
{
    // CODREF(1649370): codec -101 sends an absolute six-bit
    // value, not baseline XOR. Absence retains the secured
    // destination; a changed zero needs six explicit zero bits.
    const bool writeRadar = state.radarFlags || radarFlagsChanged;
    message.MSG_WriteBits(writeRadar ? 1u : 0u, 1);
    if (writeRadar) message.MSG_WriteBits(state.radarFlags, 6);
}
```

### 3.1 四层

```text
1. **codec `-101` 发一个【绝对的】六位值，不是基线 XOR**
2. ⇒ **缺席保留那个被保护的目的地**
3. ⇒ **所以一个变化为零需要六个显式的零位**
4. ⇒ 所以 `writeRadar = state.radarFlags || radarFlagsChanged`
```

### 3.2 而 **`-101` 与 `-102` 的对照**

```text
-101   radarFlags       一位 + 6 位
-102   otherFlags       一位 + 31 位
```

**✅ 与 §333 的"`-102` 与 `-101` 共享一条返回路径，不是一个宽度"**完全一致** ✓**

**⇒ 所以**同一个 codec 族的两个成员，宽度不同**。**

### 3.3 而"**缺席保留那个被保护的目的地**"

**⇒ 三层**：

```text
1. 缺席 ⇒ **目的地保留**
2. ⇒ 所以"不清零"是一个**副作用**
3. ⇒ **所以一个"变化为零"必须显式发六个零位**
```

**✅ 与 §333 的"缺席不调用安全 setter"**同一条**（第二次）。**

### 3.4 而**主循环与第二 pass 的 `radarFlags` 写法不同**

```cpp
// 主循环（§333）
message.MSG_WriteBits(1u, 1);                       // 【总是 1】
message.MSG_WriteBits(state.radarFlags, 6);

// 第二 pass
const bool writeRadar = state.radarFlags || radarFlagsChanged;
message.MSG_WriteBits(writeRadar ? 1u : 0u, 1);
if (writeRadar) message.MSG_WriteBits(state.radarFlags, 6);
```

**⚠ 主循环**总是写**而第二 pass **有条件**。**

**⇒ 因为主循环只在 `radarFlagsChanged` 时进 ⇒ 所以"变化"已保证。**

**✓ 所以两者等价。**

**✅ 而第二 pass 需要 `|| radarFlagsChanged` 因为它可能在**没变化**时也进来（`fieldIndex < lastChangedFieldIndex` 不保证变化）。**

**✓ 正确。**

## 四、**`perkHudVisible` 的 CONFIRMED LIVE**（本组最重要的一段）

### 4.1 那段

```php
else if (fieldIndex == PlayerStatePerkHudVisibleField)
{
    // Codec -57 is a BARE single bit - Bits(1, v != 0) - with no
    // present flag and no baseline xor, which is why this is a
    // raw write and not writeUnsignedDelta like its neighbours
    // (those are codec 1). The client stores it as a byte at
    // ps+0x580. See SvPlayerState::perkHudVisible.
    // CONFIRMED LIVE 2026-08-23: a player reported seeing their
    // perks, and both clients read ps[0x580] = 1 with the element's
    // own gate evaluating true. The instrument that separated
    // "the server never wrote it" from "the client did not take it"
    // has served its purpose and is gone.
    message.MSG_WriteBits(state.perkHudVisible ? 1u : 0u, 1);
}
```

### 4.2 八层

```text
1. **codec `-57` 是一个【裸的一位】** —— `Bits(1, v != 0)`
2. ⇒ **没有存在位也没有基线 XOR**
3. ⇒ 所以这是**一个原始写**而不是像它邻居那样的 `writeUnsignedDelta`（那些是 codec `1`）
4. ⇒ **客户端把它存成一个字节在 `ps+0x580`**
5. **CONFIRMED LIVE 2026-08-23**：**一个玩家报告看到了他的技能**
6. ⇒ **而两个客户端都读到 `ps[0x580] = 1` 且元素自己的门求值为真**
7. ⇒ **那个分开"服务器从未写它"与"客户端没有接受它"的仪器已经完成它的用处而它被移除了**
```

### 4.3 **"那个仪器已经完成它的用处而它被移除"**

**✅ 这是本文件里**最干净的一次"关闭一个诊断"**。**

**⇒ 与 §276 的"如果这永远停止打印，修复是应该删除的死代码"**同族（第二次"诊断的自删除条件"）。**

### 4.4 而 `ps+0x580` 与 §254 的 `ps+0x584`

**§254**："技能位集在 `ps+0x584 + 4*(index>>5)`"

**⇒ 而 `perkHudVisible` 在 `ps+0x580`。**

**✅ 所以 `+0x580`（可见位）与 `+0x584`（位集）**相邻**。**

**⇒ 一个 4 字节的偏移差 = 1 个 uint32。**

**✅ 与 §254 的"`sub_4442E0` sets `ps+0x584 + 4*(index>>5)`"配合。**

## 五、**"强制为零 undo 本地 akimbo 预测"**（本组第四重要）

### 5.1 那段

```php
else
{
    // Fields 98 (+0x258) and 106 (+0x418) are both one-bit,
    // hint-2 dual-wield state in this build. +0x418 is read by
    // PM_Weapon's hand-button selector: hand 1 consumes +attack
    // and hand 0 consumes the secondary-fire button. Forcing it
    // to zero made each authoritative snapshot undo local akimbo
    // prediction and mixed the two mouse buttons.
```

**（后续待读）**

### 5.2 五层

```text
1. **字段 98（`+0x258`）与 106（`+0x418`）都是【一位、hint-2 双持状态】**
2. ⇒ **`+0x418` 被 `PM_Weapon` 的手按钮选择器读**：
     · **手 1 消费 `+attack`**
     · **手 0 消费副开火按钮**
3. ⇒ **强制它为零让每一个权威快照【undo 本地 akimbo 预测】**
4. ⇒ **并混淆两个鼠标按钮**
```

### 5.3 **"混淆两个鼠标按钮"**

**✅ 一个**具体的玩家可见症状**。**

**⇒ 与 §329 的"模式 0 保持客户端预测"**相反**：**

```text
模式 0           ⇒ 保持预测（不发 changeHint==3 字段）
强制 106 为 0    ⇒ undo 预测（发错的权威值）
```

**⚠ 两个都关于**预测**但方向相反。**

**✅ 一个**重要的对照**。**

### 5.4 而 `+0x258` 与 `+0x418`

**⇒ 两个偏移差 `0x1C0` = 448。**

**⚠ 而 §317 说 `CursorHintDualWieldField = 98` 而 `DualWieldActiveField = 106`。**

**⇒ 两个字段两个偏移。**

**✅ 与 §330 的"`dualWieldActiveChanged` 触发两个字段（98 与 106）"配合。**

## 六、`rewardActionType` 的 **2 位**与 `rewardActionWeapon` 的 **11 位**

```cpp
if (state.rewardActionType != oldRewardActionType)
{
    writePlayerStateFieldIndex(message, PlayerStateRewardActionTypeField, lastFieldIndex);
    writeUnsignedDelta(message, state.rewardActionType, oldRewardActionType, 2);
}
...
if (state.rewardActionWeapon != oldRewardActionWeapon)
{
    writePlayerStateFieldIndex(message, PlayerStateRewardActionWeaponField, lastFieldIndex);
    writeUnsignedDelta(message, state.rewardActionWeapon, oldRewardActionWeapon, 11);
}
```

**⇒ 两个：2 位 / 11 位。**

**✅ 与 §307 的"`rewardActionType == 1` 是 UAV"配合 —— 2 位能到 3。**

## 七、`spreadOverride` 的 **6 位**与 `spreadOverrideState` 的 **2 位**

```cpp
writeUnsignedDelta(message, (uint32)state.spreadOverride, (uint32)baselineSpreadOverride, 6);       // 193
writeUnsignedDelta(message, (uint32)state.spreadOverrideState, (uint32)baselineSpreadOverrideState, 2);  // 194
```

**⇒ 两个：6 位 / 2 位。**

**⚠ 而 `spreadOverride` 是 `uint32` 强转 ⇒ 而 6 位只能到 63。**

**✅ 与 §254 的"`spreadOverride`"配合（待核对）。**

## 八、`playerSizeScale` 用 `writeFullFloatDelta`

```cpp
writeFullFloatDelta(message, state.playerSizeScale, baselinePlayerSizeScale);   // 219
```

**⇒ 字段 219，浮点。**

**✅ 与 §313 的 `PlayerSizeScaleBootstrap = 1.0f` 配合。**

**⇒ 而 §313 说"`playerState +0x98 → entityState +0x54 → DObj +0xC8`"。**

**✅ 所以 `playerSizeScale` 在 playerState 的 `+0x98`。**

## 九、`movingPlatformEntity`/`remoteEyesEntity`/`remoteControlEntity`/`linkEntity` 都 **11 位**

```cpp
writeUnsignedDelta(..., state.movingPlatformEntityNum, ..., 11);    // 227
writeUnsignedDelta(..., state.remoteEyesEntityNum, ..., 11);        // 228
writeUnsignedDelta(..., state.remoteControlEntityNum, ..., 11);     // 230
writeUnsignedDelta(..., state.linkEntityNum, ..., 11);              // 231
```

**⇒ 四个 11 位。**

**✅ 与 §317 的"227/228/230/231"一致。**

## 十、`remoteControlTag` 的 **6 位**

```cpp
writeUnsignedDelta(message, state.remoteControlTag, baselineRemoteControlTag, 6);   // 169
```

**⇒ 6 位。**

**✅ 与 §317 的"`+0x06C, 6 bits`，零售 dm demo 里恰好断言一次，携带 20"**完全一致** ✓**

## 十一、`holdBreathTimer` 的 **16 位**

```cpp
writeUnsignedDelta(message, holdBreathTimer, baselineHoldBreathTimer, 16);   // 172
```

**⇒ 16 位。**

**✅ 与 §317 的"`+0x29C` as `holdBreathTimer` 而给一个 16 位 codec"**完全一致** ✓**

## 十二、`weaponRestrictKickTime` 的 **16 位有符号**（两个）

```cpp
writeSignedDelta(message, state.weaponRestrictKickTime[0], ..., 16);   // 189
writeSignedDelta(message, state.weaponRestrictKickTime[1], ..., 16);   // 190
```

**⇒ 两个 16 位有符号。**

**✅ 与 §317 的"189/190"一致。**

## 十三、`deltaAngles[2]` 的 **191**

```cpp
if (deltaAngleChanged[2])
{
    writePlayerStateFieldIndex(message, 191, lastFieldIndex);
    writeDeltaAngleFull(message, state.deltaAngles[2]);
}
```

**⇒ 字段 191（字面量），16 位角度。**

**✅ 与 §330 的"`deltaAngleChanged[2] ⇒ 191`"一致。**

## 十四、关键结论

1. **第二 pass 的 `fieldIndex >= lastChangedFieldIndex ⇒ break`** —— 与主循环的 hint-2 路径互补。
2. **八个 hint-2 字段画六个 `else if` + 一个 `else`（98 与 106）。**
3. **`radarFlags` 的 codec `-101`：一位 + 6 位，**绝对**而非 XOR**。
4. **`-101` 与 `-102` 共享返回路径但宽度不同**（6 vs 31）。
5. **"缺席保留目的地 ⇒ 一个变化为零需要六个显式零位"**。
6. **主循环总是写 `1` 而第二 pass 有条件** —— 因为主循环只在变化时进。
7. **⭐ `perkHudVisible` 的 CONFIRMED LIVE 2026-08-23** —— 两个客户端 `ps[0x580] = 1`。
8. **"那个分开『服务器没写』与『客户端没接受』的仪器已经完成用处而它被移除"**。
9. **`ps+0x580`（可见位）与 `ps+0x584`（位集）相邻**。
10. **⭐ "强制为零 undo 本地 akimbo 预测并混淆两个鼠标按钮"** —— 一个具体的玩家症状。
11. **字段 98（`+0x258`）与 106（`+0x418`），而 `+0x418` 被 `PM_Weapon` 的手按钮选择器读。**
12. **`rewardActionType` 2 位 / `rewardActionWeapon` 11 位。**
13. **`spreadOverride` 6 位 / `spreadOverrideState` 2 位。**
14. **`playerSizeScale` 用 `writeFullFloatDelta`（字段 219）**。
15. **四个实体引用 11 位（227/228/230/231）。**
16. **`remoteControlTag` 6 位、`holdBreathTimer` 16 位、`weaponRestrictKickTime` 16 位有符号（两个）。**

## 十五、未闭合点

- 98 与 106 两个 `else` 分支的完整实现。
- `+0x258` 与 `+0x418` 的两个双持字段的分工。
- `spreadOverride` 6 位是否够。
- `sv_snapshot_mp.cpp` 4800 行之后未读取（1.47 MB，进度 33%）。
