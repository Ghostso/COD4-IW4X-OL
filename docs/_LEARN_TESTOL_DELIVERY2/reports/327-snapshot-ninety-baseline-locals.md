# 327 · **约 90 个 `baseline*` 局部**、`changeHint==3` 的四个字段不发变化位、`cursorHint` 的零基线

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 2793–3000 行。

## 二、**`baseline*` 局部的完整清单**（本组最重要的一段）

### 2.1 按组分类

#### ① 武器动画组（`uint16[2]` / `int32[2]` / `uint8[2]`）

```text
baselineWeaponAnim          uint16[2]
baselineWeaponTime          int32[2]
baselineWeaponDelay         int32[2]
baselineWeaponRestrictKickTime  int32[2]
baselineWeaponState         uint8[2]
baselineWeaponHandFlags     uint8[2]
baselineWeaponShotCount     uint8[2]
```

**⇒ 七组 × 2 = 14 个值。**

#### ② 技能 / 弹药 / 目标 / HUD

```text
baselinePerks               uint32[3]
baselineHeldWeapons         SvHeldWeaponState[15]
baselineAmmoClips           SvAmmoClipState[15]
baselineAmmoPools           SvAmmoPoolState[15]
baselineObjectives          SvObjective[32]
baselineHudCurrent          SvHudElem[31]
baselineHudArchival         SvHudElem[31]
```

**⇒ 七组数组。**

#### ③ 伤害 / 血量 / 状态

```text
baselineDamageEvent / DamageYaw / DamagePitch / DamageCount
baselineDamageTimer / DamageDuration
baselineHealth / MaxHealth / DeadYaw
baselineShellshockIndex / Time / Duration
baselineSpawnGeneration
```

**⇒ 十四个标量。**

#### ④ 视线高度 / 趴

```text
baselineViewHeightCurrent / Target / LerpTarget / LerpTime / LerpDown
baselineProneDirection / DirectionPitch / TorsoPitch / TransitionStartTime
```

**⇒ 九个。**

#### ⑤ 冲刺 / 攀爬

```text
baselineSprintButtonUpRequired / SprintDelay / LastSprintStart / LastSprintEnd / SprintStartMaxLength
baselineMantleYaw / Timer / TransitionIndex / Flags
```

**⇒ 九个。**

#### ⑥ 实体引用

```text
baselineGroundEntityNum / ViewEntityNum / MovingPlatformEntityNum
baselineRemoteEyesEntityNum / RemoteControlEntityNum / RemoteTurretEntityNum
baselineRemoteControlTag / LinkEntityNum
```

**⇒ 八个。**

#### ⑦ 事件环

```text
baselineEventSequence / OldEventSequence
baselineEvents            SvEntityEvent[4]
```

#### ⑧ 击杀镜头

```text
baselineKillCamEntityNum / LookAtEntityNum / ClientNum / DeltaTime
```

#### ⑨ 其它

```text
baselineCommandTime / PmType / PmTime / PmFlags / EFlags / OtherFlags
baselineGravity / Speed / MoveSpeedScaleMultiplier / ClientNum
baselineLegsTimer / LegsAnim / TorsoTimer / TorsoAnim
baselineCurrentWeaponAssetIndex / GrenadeEntity / WeaponFlags / GrenadeTime
baselineOffhandWeaponAssetIndex / OffhandSlots[3] / WeaponPositionFraction
baselineAimSpreadScale / SpreadOverride / SpreadOverrideState
baselineViewmodelIndex
baselinePlayerSizeScale / JumpTime / JumpOriginZ
baselineDeltaAngles / ViewAngles
baselineCursorHint / CursorHintString / CursorHintEntityNum
```

### 2.2 **约 90 个**,而这只是基线

**⇒ 三层**：

```text
1. 每个字段一个 `baseline*` 局部
2. ⇒ 而每个都是 `baseline ? baseline->x : 0`
3. ⇒ **所以"无基线"的全部默认是零**
```

**✅ 而 §327 后面有一处**明确的例外注释**（`cursorHint`）。**

## 三、`dualWieldActive` 的**三项**（本组第二重要）

```cpp
const auto dualWieldActive = [](const SvPlayerState &player) {
    const auto held = std::ranges::find_if(player.heldWeapons,
        [&player](const SvHeldWeaponState &weapon) {
            return weapon.weaponAssetIndex == player.currentWeaponAssetIndex;
        });
    return held != player.heldWeapons.end() && held->unknownState[0] != 0;
};
```

### 3.1 三层

```text
① 在 `heldWeapons` 里找**当前武器**那一项
② ⇒ 找到
③ ⇒ 且它的 `unknownState[0] != 0`
```

**⇒ 所以"双持活跃"= "当前武器在 held 列表里且它有某个标志"。**

**⚠ 而 `unknownState[0]` 的语义**未知**（§323 说"五个 `unknownState` 位"）。**

**⇒ 但这里用它推导"双持"。**

**✅ 所以 `unknownState[0]` **就是**双持标志。**

**⚠ 而 §323 的注释说"五个标志"没有命名。**

### 3.2 而 `dualWieldActiveChanged`

```cpp
const auto currentDualWieldActive = dualWieldActive(state);
const auto baselineDualWieldActive = baseline && dualWieldActive(*baseline);
const auto dualWieldActiveChanged = currentDualWieldActive != baselineDualWieldActive;
```

**⚠ `baseline && dualWieldActive(*baseline)` 得到 `bool`（因为 `&&` 短路返回 `bool`）。**

**✓ 所以 `baselineDualWieldActive` 是 `bool`。**

## 四、**"没有 `originChanged` / `velocityChanged` / `bobCycleChanged` / `movementDirChanged`"**（本组第三重要）

### 4.1 那段

```php
// NO originChanged / velocityChanged / bobCycleChanged /
// movementDirChanged HERE ON PURPOSE. They are changeHint==3
```

**（后续待读）**

### 4.2 三层

```text
1. **刻意没有 `originChanged` / `velocityChanged` / `bobCycleChanged` / `movementDirChanged`**
2. ⇒ 因为它们是 **`changeHint == 3`**
3. ⇒ **所以总是发绝对值**（不需要变化位）
```

**✅ 与 §326 的"origin 与 velocity 是 `changeHint == 3`"**完全一致** ✓**

**⇒ 而那四个字段是：**

```text
origin
velocity
bobCycle
movementDir
```

**⇒ 四个"总是发"的字段。**

**✅ 与记忆里"11 个字段我们写 XOR 增量，三份参照全写裸值"**相关 ——**

**⇒ 而 `origin`/`velocity` **在规范上就是裸值**。**

## 五、`cursorHint` 的**零基线特例**（本组第四重要）

### 5.1 那段

```php
// A NULL BASELINE IS A ZEROED playerState, which is what the client
// starts a connection with -- and the idle hint is zero too, which
// is why an idle player emits none of these three and every golden
// snapshot in the tests is byte-identical to before hints existed.
// Retail idles at -1/2047 instead and duly asserts them once per
// connection; SvPlayerState::cursorHintString says why this does not.
const auto baselineCursorHint =
    baseline ? baseline->cursorHint : std::uint16_t{};
const auto baselineCursorHintString =
    baseline ? baseline->cursorHintString : 0;
const auto baselineCursorHintEntityNum =
    baseline ? baseline->cursorHintEntityNum : 0u;
```

### 5.2 六层

```text
1. **一个 NULL 基线是一个零化的 playerState**
2. ⇒ **那是客户端开始一个连接时的状态**
3. ⇒ **而空闲提示也是零**
4. ⇒ **所以一个空闲玩家不发这三个中的任何一个**
5. ⇒ **而测试里每一个黄金快照都与"提示存在之前"逐字节相同**
6. ⇒ **而零售空闲在 `-1/2047` 而相应地每个连接断言它们一次**
7. ⇒ **`SvPlayerState::cursorHintString` 说为什么这个不**
```

### 5.3 而"**与提示存在之前逐字节相同**"

**⇒ 三层**：

```text
1. 空闲时三个提示字段全零
2. ⇒ 所以变化位全零
3. ⇒ **所以输出与"提示不存在"时逐字节相同**
```

**✅ 一个**向后兼容**的设计。**

**⚠ 而"零售空闲在 `-1/2047` 而每个连接断言一次" ⇒ **零售**会发**而我们不。**

**⇒ 所以这是一个**已知的与零售的差异**。**

**✅ 与 §323 的"零值最便宜"配合。**

## 六、`eventChanged` 的**四项数组**

```cpp
const std::array eventChanged{
    state.predictableEvents[0] != baselineEvents[0],
    state.predictableEvents[1] != baselineEvents[1],
    state.predictableEvents[2] != baselineEvents[2],
    state.predictableEvents[3] != baselineEvents[3],
};
```

**⇒ 四个。**

**✅ 与 §317 的 `PlayerStateEventFields{ 21, 22, 23, 24 }`（四个环槽）**完全一致** ✓**

## 七、`weaponFlags()` 与 `offhandWeaponSlots()` 的**方法调用**

```cpp
const auto baselineWeaponFlags = baseline ? baseline->weaponFlags() : 0;
const auto baselineGrenadeTime = baseline ? baseline->grenadeTimeLeft : 0;
...
const auto offhandSlots = state.offhandWeaponSlots();
const auto baselineOffhandSlots = baseline ? baseline->offhandWeaponSlots()
    : std::array<std::uint16_t, 3>{};
```

### 7.1 而**两个方法是"合成字段"**

```cpp
weaponFlags()                ⇒ 单值（从多个字段合成？）
offhandWeaponSlots()         ⇒ array<uint16, 3>
```

**⚠ 而 §317 的 `PlayerStateWeaponFlagsField = 77` 而 `PlayerStateOffhandSlotFirstField = 109`（三个）。**

**✅ 所以：**

```text
weaponFlags()          ⇒ 字段 77
offhandWeaponSlots()   ⇒ 字段 109/110/111
```

**⇒ 而 `offhandWeaponSlots()` 返回三个 ⇒ 与 §317 的"109..111"**完全一致** ✓**

## 八、`SvPlayerState` 的**字段总数**

**⇒ 从本段的 `baseline*` 推导：**

```text
武器动画 7 × 2 元组
技能 3
heldWeapons 15
ammoClips 15
ammoPools 15
objectives 32
hudCurrent 31
hudArchival 31
events 4
（标量约 80 个）
```

**⇒ 所以 `SvPlayerState` 是一个**巨大的结构**（约 80 标量 + 162 数组元素）。**

**⚠ 而 §315 说"增大它会破坏死亡动画"。**

**⇒ 所以它的大小被**钉死**。**

## 九、关键结论

1. **约 90 个 `baseline*` 局部** —— 每个字段一个，且默认全零。
2. **七组武器动画 2 元组**（anim/time/delay/restrictKick/state/handFlags/shotCount）。
3. **七组大数组**（perks 3 / heldWeapons 15 / ammoClips 15 / ammoPools 15 / objectives 32 / hudCurrent 31 / hudArchival 31）。
4. **`dualWieldActive` 用 `unknownState[0]` 作双持标志** —— 而 §323 说那五个标志未命名。
5. **"刻意没有 `originChanged`/`velocityChanged`/`bobCycleChanged`/`movementDirChanged`"** —— 因为 `changeHint == 3`（总是发）。
6. **`cursorHint` 的零基线特例** —— 空闲时三个全零 ⇒ **与"提示存在之前"逐字节相同**。
7. **"零售空闲在 `-1/2047` 而每个连接断言一次"** —— 一个已知的与零售的差异。
8. **`eventChanged` 四项** 与 §317 的四个环槽一致。
9. **`weaponFlags()` 与 `offhandWeaponSlots()` 是合成方法**，对应字段 77 与 109..111。
10. **`SvPlayerState` 是一个巨大结构而大小被钉死**。

## 十、未闭合点

- `unknownState[0]` 的确切语义（双持？）。
- `weaponFlags()` 从哪些字段合成。
- 零售的 `-1/2047` 空闲值为何我们不复制。
- `sv_snapshot_mp.cpp` 3000 行之后未读取（1.47 MB，进度 20%）。
