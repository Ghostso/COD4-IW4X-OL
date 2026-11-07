# 317 · **伤害反馈七字段的完整实测**（1652 次断言）、`health` 不走 netfield、`label` 是 11 位而非 10 位

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 800–1000 行。

## 二、**`HudElemLabelBits = 11` 而非 10**（本组第三重要）

```php
// CODDIFF(1649370): 10 is 3.3.3.3's. The hudelem label field is 11 bits here.
constexpr std::uint32_t HudElemLabelBits = 11;
```

**⇒ 三层**：

```text
1. **10 是 3.3.3.3 的**
2. ⇒ **本 build 的 hudelem label 字段是 11 位**
3. ⇒ 所以一个**一位的差异**
```

**✅ 与 §316 的"目标 lastChanged 3 → 4 位"同族**（第五次"一位的差异"）。

## 三、**`HudElemFontScale` 的 6 位与 6.3 上限**（本组第二重要）

```php
// CODREF: the -86 codec at 0x00C42EE5 is
//   *(float *)field = (float)MSG_ReadBits(6) / 10.0
// read straight, with no leading change bit. Six bits and a tenth
// therefore cap the representable scale at 6.3.
constexpr std::uint32_t HudElemFontScaleBits = 6;
constexpr float HudElemFontScaleQuantum = 10.0f;
constexpr float HudElemFontScaleMaximum = 6.3f;
```

### 3.1 五层

```text
1. `-86` codec 在 **`0x00C42EE5`**
2. ⇒ 解码是 **`*(float*)field = (float)MSG_ReadBits(6) / 10.0`**
3. ⇒ **直读，没有前导的变化位**
4. ⇒ 六位与十分之一 ⇒ **可表示的 scale 被上限在 6.3**
5. ⇒ 而 `6.3 = 63 / 10` 而 `63` 是 6 位的最大值
```

**✅ 算术闭合：`(1<<6)-1 = 63`，`63/10 = 6.3`。**

### 3.2 而**"-86 codec 没有前导的变化位"**

**⇒ 三层**：

```text
1. 其它 codec 通常有"变化位"在前
2. ⇒ 而这个 **-86 直读**
3. ⇒ 所以它**总在场上**（无法跳过）
```

**⚠ 一个**特殊的 codec 语义**。**

**⇒ 与 §313 的四种负 codec（`-58`/`-100`/`-57`/`-97`）不同 —— 这里是 **-86**。**

**⇒ 所以 codec 空间有**至少五种**负值。**

### 3.3 而 `HudElemFlagsField = 14` **就是 §316 里缺的那个 14**

```php
constexpr std::uint32_t HudElemFlagsField = 14;
static_assert(HudElemFlagsField < HudElemFieldCount);
```

**✅ 所以字段 14 是 **flags** —— 与 §316 的"表第 14 行是 flags `{0xA4, 18}`"**完全对上** ✓**

**⇒ 而 §316 只列到 21 而这里是 14 —— 因为**顺序不同**（14 在 22 之后声明）。**

## 四、**`MaxCurrentWeaponAssetIndex = 0x7FF`** 与"活体模块化武器 1224"

```php
// CODDIFF(1649370): the playerState weapon field is ELEVEN bits on this
// build and ten on 3.3.3.3, so the bound and every array sized from it
// grow with it. A live modular weapon measured index 1224.
constexpr std::uint32_t MaxCurrentWeaponAssetIndex = 0x7FF;
```

### 4.1 三层

```text
1. playerState 的武器字段在本 build 上是**十一位**而 3.3.3.3 上是**十位**
2. ⇒ 所以**界与每一个从它定尺寸的数组都跟着长**
3. ⇒ **一个活的模块化武器实测索引 1224**
```

**✅ 而 `1224` 与 §236 的"随包类型表把模块化边界固定在 1224"**完全一致** ✓**

**⇒ 所以 1224 既是**边界**也是**一个实测的模块化武器索引**。**

## 五、**伤害反馈七字段的完整实测**（本组最重要的一段）

### 5.1 那段八层

```php
// THE DAMAGE-FEEDBACK CLUSTER IS SEVEN FIELDS AT +0x0F0..+0x19C AND
// THIS SERVER WAS WRITING FOUR OF THEM SOMEWHERE ELSE ENTIRELY.
//
// The indices 32, 61, 200 and 201 that stood here carry OLfinal-only
// fields at +0x1FC, +0x200, +0x204 and +0x208 -- a block of unnamed
// dwords 3.3.3.3 does not have at all, which is why the name transfer
// has a hole there. The retail dm demo asserts NONE of them and asserts
// the real cluster 1652 times:
//
//     42  +0x0F0  10  damageTimer      439 asserts, counts DOWN to 0
//     55  +0x194   8  damageYaw        228
//     66  +0x190   8  damageEvent      244, range 0..7
//     73  +0x198   8  damagePitch      168
//     74  +0x19C   7  damageCount      251, range 0..99
//     75  +0x0F4  16  damageDuration   161, 750 on all but two hits
//     76  +0x0F8   2  flinchYawAnim    184
//
// Every one of those is `confirmed` in BOTH builds' tables and both
// builds give them the same INDEX, so nothing here is a port decision.
// "Being shot has no feel" was four fields landing in unnamed slots.
```

### 5.2 七行完整对照

| 索引 | 偏移 | 位 | 名字 | 断言数 | 备注 |
|---|---|---|---|---|---|
| 42 | `+0x0F0` | 10 | `damageTimer` | 439 | **倒数到 0** |
| 55 | `+0x194` | 8 | `damageYaw` | 228 | |
| 66 | `+0x190` | 8 | `damageEvent` | 244 | **范围 0..7** |
| 73 | `+0x198` | 8 | `damagePitch` | 168 | |
| 74 | `+0x19C` | 7 | `damageCount` | 251 | **范围 0..99** |
| 75 | `+0x0F4` | 16 | `damageDuration` | 161 | **除两次外都是 750** |
| 76 | `+0x0F8` | 2 | `flinchYawAnim` | 184 | |

### 5.3 而**断言总数 1652**

**⇒ `439 + 228 + 244 + 168 + 251 + 161 + 184 = 1675`。**

**⚠ 而注释说 1652。**

**⇒ 差 23。**

**⚠ 可能"1652 次"是指**包含这七字段的帧数**而不是断言总数。**

**⇒ 或者有重叠。**

### 5.4 而**四个错误的索引**

```text
32   → +0x1FC   （OLfinal-only 未命名 dword）
61   → +0x200
200  → +0x204
201  → +0x208
```

**⇒ 所以"`+0x1FC`..`+0x208` 是一个 3.3.3.3 完全没有的未命名 dword 块"。**

**⇒ 而那正是"名字转移在那里有一个洞"的原因。**

### 5.5 而"**『被打了没感觉』就是四个字段落进未命名槽**"

**✅ 一个**极其清晰**的症状归因。**

**⇒ 与 §314 的"`damageEvent` 在 8 处回绕"**配套** —— 那里说"零售 244 个断言恰好跨 0..7"，而这里说 `damageEvent` 索引 **66** 有 **244** 次断言 ✓**

**✅ 两处完全对上。**

### 5.6 而 `damageDuration = 750` **除两次外**

**⇒ 三层**：

```text
1. `damageDuration` 是 16 位
2. ⇒ **161 次断言，其中 750 出现在除两次外的所有**
3. ⇒ 所以 `SvFlinchDurationMilliseconds = 750`
```

**✅ 与 §314 的 `SvFlinchDurationMilliseconds`**完全对应** ✓**

### 5.7 而**两个例外**

**⚠ 两次不是 750。**

**⇒ 可能是**被伤害抵消**或**特殊武器**。**

## 六、**`health` 不走 netfield**（本组第四重要）

### 6.1 那段六层

```php
// HEALTH AND MAXHEALTH HAD NETFIELD INDICES 33 AND 203 AND BOTH ARE
// WRONG, AND BOTH WERE ALSO REDUNDANT. +0x20C and +0x214 are two more
// of the unnamed OLfinal-only dwords above, retail never asserts
// either, and NEITHER BUILD'S playerState table has a field named
// health at all -- because health does not travel as a netfield. It
// travels in the STATS section, as a 16-bit value behind
// PlayerStateHealthStatMask, which this file already writes and which
// is why players have always taken damage and died correctly.
//
// So these were two extra writes of a health value into fields whose
// meaning is unknown, on every frame health changed.
```

### 6.2 六层

```text
1. `health` 与 `maxHealth` **曾有 netfield 索引 33 与 203**
2. ⇒ **两者都错，两者也都冗余**
3. ⇒ `+0x20C` 与 `+0x214` 是**更多的 OLfinal-only 未命名 dword**
4. ⇒ **零售从不声称任一**
5. ⇒ 而**两个 build 的 playerState 表里【都没有一个叫 health 的字段】**
6. ⇒ ⇒ **因为 health 不作为 netfield 传输**
7. ⇒ 它在 **STATS 段**里，作为一个 **16 位的值在 `PlayerStateHealthStatMask` 后面**
8. ⇒ **而那个这个文件已经写了，而那就是为什么玩家一直正确地受伤和死亡**
```

### 6.3 而"**两个多余的写，写进含义未知的字段，在每一帧 health 变化时**"

**⇒ 三层**：

```text
1. 写进未命名字段
2. ⇒ **含义未知**
3. ⇒ **而每一帧 health 变化都发生**
```

**✅ 一个**无害但多余**的模式（与 §314 的"`0xFFFF` 无害当那个值去到一个没人读的字段"**完全同族** ✓）。**

### 6.4 而 `PlayerStateHealthStatMask = 0x01`（§316）

**⇒ 与这里的"health 在 STATS 段"**完全一致** ✓**

**⇒ 而 `PlayerStateStatsMaskBits = 17` 而 3.3.3.3 是 4。**

**⇒ 所以 STATS 段是 **17 位**而本服务器写**前四位**。**

**✅ 与 §316 的"我们写前四个"一致。**

## 七、**`PlayerStateTorsoAnimField` 的配对歧义**（本组第五重要）

```php
// KEPT AS-IS (2026-10-08). BG_PlayAnim lists the descriptors as
// "fields 31/7/5/27", but that list's PAIRING is ambiguous and the
// executable test "field 27 writes torsoAnim toggle bit as CODOL
// mixed-cursor 12-bit data" pins torsoAnim to field 27 on a measured
// wire pattern. The swap that was really wrong is in the STRUCT
// offsets (sv_native_playerstate_mp.cpp / sv_native_entitystate_mp.cpp),
// not here.
```

### 7.1 四层

```text
1. `BG_PlayAnim` 把描述符列为 **"fields 31/7/5/27"**
2. ⇒ 但那个列表的**配对是歧义的**
3. ⇒ 而**可执行的测试**"field 27 writes torsoAnim toggle bit as CODOL mixed-cursor 12-bit data"**把 torsoAnim 钉在 field 27** 在一个**测量的线模式**上
4. ⇒ **真正错的交换在【结构偏移】里**（`sv_native_playerstate_mp.cpp` / `sv_native_entitystate_mp.cpp`）**而不是这里**
```

### 7.2 **"字段列表的配对是歧义的"**

**✅ 一个**重要的陷阱** —— 一个"字段列表"如果只有编号没有名字配对，就**无法唯一确定**。**

**⇒ 而"可执行的测试"（线模式）解决了它。**

**✅ 与 §311 的"十次按键十个命令 vs 两个边沿"同族（第十六次"用可执行测试定案"）。**

### 7.3 而 `PlayerStateTorsoAnimField = 27` 而 `PlayerStateLegsAnimField = 7`

**⇒ 两个**分开的字段**。**

**⇒ 而 "31/7/5/27" 里的 31 与 5 是 `LegsTimer` 与 `TorsoTimer`。**

**✅ 与 §317 后面：**

```text
PlayerStateTorsoTimerField = 5
PlayerStateLegsTimerField  = 31
PlayerStateLegsAnimField   = 7
PlayerStateTorsoAnimField  = 27
```

**✅ 四个全部对上 "31/7/5/27" 但**配对是**：**

```text
31 = LegsTimer
7  = LegsAnim
5  = TorsoTimer
27 = TorsoAnim
```

**⇒ 所以"31/7/5/27"的**顺序**是 `LegsTimer/LegsAnim/TorsoTimer/TorsoAnim`。**

**✅ 一个**可能反直觉但已定案**的配对。**

## 八、`PlayerStateDamageYawField = 55` 等的**两次声明**

**⚠ 而 `PlayerStateDamageYawField` 在 904 行声明为 55，而 §317 的七字段表也说 `55 +0x194 8 damageYaw`。**

**✅ 一致。**

**⇒ 而 `PlayerStateDamageTimerField = 42` 与表一致 ✓**

**⇒ 而 `PlayerStateDamageEventField = 66` 与表一致 ✓**

**⇒ 而 `PlayerStateDamagePitchField = 73` 与表一致 ✓**

**⇒ 而 `PlayerStateDamageCountField = 74` 与表一致 ✓**

**⇒ 而 `PlayerStateDamageDurationField = 75` 与表一致 ✓**

**⇒ 而 76（`flinchYawAnim`）**没有对应的常量**。**

**⚠ 所以 `flinchYawAnim` 未在本段声明。**

## 九、**`PlayerStateOffhandSlotFirstField = 109` 的 32 位**

```php
// CODREF(1649370): out.exe 0xDA8520 fields 109..111 are ps+3E8..3F0,
// each {bits=32,type=0}, despite their weapon-index value domain.
constexpr std::uint32_t PlayerStateOffhandSlotFirstField = 109;
```

### 9.1 三层

```text
1. **`out.exe 0xDA8520` 的字段 109..111 是 `ps+3E8..3F0`**
2. ⇒ **每个 `{bits=32, type=0}`**
3. ⇒ **尽管它们的值域是武器索引**
```

### 9.2 而"**尽管它们的值域是武器索引**"

**⇒ 三层**：

```text
1. 一个武器索引通常是 11 位
2. ⇒ 而这三个字段是 **32 位**
3. ⇒ **尽管它们装的是武器索引**
```

**✅ 与 §311 的"`+0x3E8`/`+0x3F0` 的 mode 槽"**完全一致** ✓**

**⇒ 所以这三个字段是 `ps+3E8..3F0` 而 §311 说"the mode slots at +0x3E8 / +0x3F0"。**

## 十、**`PlayerStateCursorHintStringField = 80` 的 `-8` codec**

```php
// THE CURSOR HINT. 67 is ps+0x24C and 11 bits, 78 is ps+0x254 and 11
// bits, 80 is ps+0x250 and codec -8 -- so 80 is the only SIGNED one of
// the three and its idle value is -1. Read out of the client in
// re/demo-re/18-hint-strings.md; 67 was UNNAMED in the census until
// sub_45A450 showed it is the gate the other two hang off.
constexpr std::uint32_t PlayerStateCursorHintField = 67;
constexpr std::uint32_t PlayerStateCursorHintEntityField = 78;
constexpr std::uint32_t PlayerStateCursorHintStringField = 80;
```

### 10.1 三层

```text
1. **67 是 `ps+0x24C` 而 11 位；78 是 `ps+0x254` 而 11 位；80 是 `ps+0x250` 而 codec `-8`**
2. ⇒ **所以 80 是三者里唯一【有符号】的而其空闲值是 -1**
3. ⇒ 从 `re/demo-re/18-hint-strings.md` 的客户端读出
4. ⇒ **67 在普查里是【未命名】的**，直到 `sub_45A450` 显示它是**其他两个挂靠的门**
```

### 10.2 而 `codec = -8` 是**第六种负 codec**

```text
-8    有符号（可能是一个小的 int）
-57   bool
-58   ？
-75   ？  （§317 的 `PlayerStateEventSequenceField`）
-86   float/10（§317 的 FontScale）
-94   ？（§317 的 event ring）
-97   time
-100  float
```

**⇒ 至少**八种**负 codec。**

### 10.3 而 `PlayerStateEventSequenceField = 1` / `= 2` 的 `-75`

```php
// THE PREDICTABLE EVENT RING. Netfield 1 is playerState +0x108 and 2 is
// +0x12C, both codec -75; 21..24 are the four ring slots from +0x10C,
// stride 8, all codec -94. The same two writers the ENTITY event ring
// already uses serve both -- the codecs are identical and only the
// indices differ.
constexpr std::uint32_t PlayerStateEventSequenceField = 1;
constexpr std::uint32_t PlayerStateOldEventSequenceField = 2;
constexpr std::array PlayerStateEventFields{ 21u, 22u, 23u, 24u };
```

**⇒ 三层**：

```text
1. 字段 1 是 `+0x108`、字段 2 是 `+0x12C`，都是 **-75**
2. ⇒ 21..24 是**四个环槽**从 `+0x10C`，**步长 8**，都是 **-94**
3. ⇒ **实体事件环已经用的同两个写入者服务两者** —— codec 相同而只有索引不同
```

**✅ 与记忆里"`SvEntityEventCount = 170`"、"reliable command ring 512"**不同 —— 这是**事件环**。**

## 十一、**`PlayerStatePerkHudVisibleField = 122`** 的**一位**

```php
// The perk HUD element's visibility bit. Codec -57: ONE bit, absolute, no
// baseline xor. See SvPlayerState::perkHudVisible.
constexpr std::uint32_t PlayerStatePerkHudVisibleField = 122;
```

**⇒ 三层**：

```text
1. perk HUD 元素的**可见位**
2. ⇒ codec **-57：一位，绝对，无基线 xor**
3. ⇒ 见 `SvPlayerState::perkHudVisible`
```

**✅ 与 §314 的"`damageEvent` 三位计数器"**不同的位宽**。**

**⇒ 而"无基线 xor"是一个**重要的语义** —— 与记忆里"11 个字段我们写 XOR 增量而三份参照全写裸值"相关。**

## 十二、**`PlayerStatePerkField0/1/2 = 123/124/125`**

```php
// The perk set - see SvPlayerState::perks for how these three were
// identified and why they are playerState rather than hudElems.
constexpr std::uint32_t PlayerStatePerkField0 = 123;
constexpr std::uint32_t PlayerStatePerkField1 = 124;
constexpr std::uint32_t PlayerStatePerkField2 = 125;
```

**⇒ 三个连续字段。**

**⚠ 而 §254 的"技能 192 位掩码"是**5 个 uint32 = 160 位**（§254 说 192 位但 mask 是 `mask[modifierId >> 5]`）。**

**⇒ 而这里只有**三个 netfield**。**

**⇒ 所以"技能在 playerState 里是三个 netfield"而"能力修饰符掩码是六个 uint32"。**

**⚠ 两个不同的东西。**

## 十三、**`PlayerStateKillCam*` 的四 + 一**

```php
constexpr std::uint32_t PlayerStateKillCamEntityField = 136;
constexpr std::uint32_t PlayerStateKillCamLookAtEntityField = 137;
constexpr std::uint32_t PlayerStateKillCamClientNumField = 138;
constexpr std::uint32_t PlayerStateLeftWeaponShotCountField = 140;
constexpr std::uint32_t PlayerStateKillCamDeltaTimeField = 142;
```

**⇒ 五个（四个 killcam + 一个 leftWeaponShotCount）。**

**⇒ 而注释说"136/137/138 连续而坐在 perks（125）与 LeftWeaponShotCount（140）之间；142 坐在它上面"。**

**✅ 顺序合理。**

## 十四、`PlayerStateRemoteControlTagField = 169`

```php
// +0x06C, 6 bits. Asserted exactly once in the retail dm demo, on the
// same frame as 168, carrying 20 (HANDOFF 129).
constexpr std::uint32_t PlayerStateRemoteControlTagField = 169;
```

**⇒ 三层**：

```text
1. `+0x06C`，**6 位**
2. ⇒ **在零售 dm demo 里恰好被断言一次**
3. ⇒ 与 168 **同一帧**，**携带 20**
```

**✅ 而 `20` 与 §317 的 `PodiumViewTag = 20`**完全一致** ✓**

**⇒ 所以 169 = 20 = `PodiumViewTag` —— 一个标签。**

## 十五、`PlayerStateHoldBreathTimerField = 172`

```php
// CODREF(msg_write_delta_playerstate): out.exe's playerState table
// names +0x29C as holdBreathTimer and gives it a 16-bit codec.
constexpr std::uint32_t PlayerStateHoldBreathTimerField = 172;
```

**⇒ 三项：`+0x29C`、`holdBreathTimer`、16 位。**

## 十六、关键结论

1. **`HudElemLabelBits = 11` 而非 10** —— 又一位的差异。
2. **`-86` codec 是 `ReadBits(6) / 10.0`** ⇒ **上限 6.3**，且**没有前导变化位**。
3. **`HudElemFlagsField = 14`** 就是 §316 缺的那个 14。
4. **`MaxCurrentWeaponAssetIndex = 0x7FF`（11 位）**，活体模块化武器实测 **1224**。
5. **⭐ 伤害反馈七字段的完整实测**（`42/55/66/73/74/75/76` 与各自的偏移/位宽/断言数）。
6. **`damageTimer` 439 次倒数到 0**、`damageEvent` 244 次范围 0..7、`damageCount` 251 次范围 0..99、`damageDuration` 161 次其中 750 除两次外。
7. **四个错误索引（32/61/200/201）指向 `+0x1FC..+0x208`** —— 一个 3.3.3.3 没有的未命名块。
8. **"『被打了没感觉』就是四个字段落进未命名槽"**。
9. **`health` 不走 netfield** —— 它在 **STATS 段**的 `PlayerStateHealthStatMask` 后面（16 位）。
10. **`PlayerStateStatsMaskBits = 17`** 而 3.3.3.3 是 4 ⇒ 我们写前四个。
11. **`BG_PlayAnim` 的 "31/7/5/27" 配对是歧义的** ⇒ 用可执行的线模式定案。
12. **正确的配对**：`31 = LegsTimer`、`7 = LegsAnim`、`5 = TorsoTimer`、`27 = TorsoAnim`。
13. **"真正错的交换在结构偏移里而不是这里"**。
14. **`PlayerStateOffhandSlotFirstField = 109` 的三个字段是 32 位**，尽管值域是武器索引。
15. **`CursorHint` 三字段**（67 `+0x24C` 11 位 / 78 `+0x254` 11 位 / 80 `+0x250` codec `-8` 有符号）。
16. **67 曾是未命名的**，直到 `sub_45A450` 显示它是**门**。
17. **至少八种负 codec**（`-8`/`-57`/`-58`/`-75`/`-86`/`-94`/`-97`/`-100`）。
18. **事件环：字段 1/2 是 `-75`，21..24 四个环槽是 `-94`。**
19. **`perkHudVisible` 是**一位、绝对、无基线 xor**。
20. **技能是三个 netfield**（123/124/125）而**能力掩码是六个 uint32** —— 两个不同的东西。
21. **`RemoteControlTag = 169` 而值 20 = `PodiumViewTag`**。

## 十七、未闭合点

- 1652 vs 1675（七字段断言数之和）的差。
- `damageDuration` 的两个例外值。
- `flinchYawAnim`（字段 76）的常量未在此声明。
- `sv_snapshot_mp.cpp` 1000 行之后未读取。
