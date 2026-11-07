# 460 · **`sv_native_playerstate_mp.cpp` 的偏移体系** —— "`0x3564 → 0x3BBC` 的八处增长"、`105` 个偏移、以及"零生产者 ⇒ 客户端每个快照被种零 ⇒ 摆动锯齿化"

## 一、范围

本报告学习 `sv_native_playerstate_mp.cpp`（**`1,687` 行，`89,189` 字节**）的偏移体系与 `SvSwayPhase` 的生产者，以及 `writeValue`/`readValue`/`finite`/`validEntity` 的模板助手。

## 二、**"`0x3564 → 0x3BBC` 的八处增长"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODREF(pmove): CODOL playerState_s is exactly 0x3564 bytes; Pmove
// 0x0041E860 and its retained helpers mutate this caller-owned image.
// BO1 Pmove 0x004385F0 and Ghosts 0x140082BE0 confirm ownership and
// control-flow responsibility, but their field layouts are not used.
// CODDIFF(1649370): EVERY OFFSET BELOW WAS 3.3.3.3's. playerState_s
// grew in eight places between the builds -- +0 at the head, then +20,
// +72, +80, +184, +192, +196, +224 and on out to +1048 in the tail --
// and the whole per-client image went 0x3564 -> 0x3BBC bytes. The map
// came from aligning the two builds' EXTRACTED NETFIELD TABLES, which
// are a byte-exact description of both layouts, and every offset the
// alignment could not place on its own was then read out of out.exe:
//
//   BG_PlayerStateToEntityState  A sub_4131A0 <-> C sub_411360, line
//     for line, gives clientNum 0x144 -> 0x158, legs 0x0C8 -> 0x0DC,
//     torso 0x0D0 -> 0x0E4, health 0x190 -> 0x1A4, maxHealth 0x198 ->
//     0x1AC and eFlags 0x0F0 -> 0x104.
//   the held-weapon walker  A sub_55CFE0 <-> C sub_594840, identical
//     `(v + 16) % 15` loop, gives heldWeapons 0x2A4 -> 0x2F4.
//   the ammo-pool inserter  A sub_42F820 <-> C sub_4331A0, identical
//     fifteen-entry stride-8 scan, gives ammoPools 0x364 -> 0x41C, and
//     the clip base 0x3DC -> 0x494 falls out of the same +0x78.
//   the objective block is 32 records on both builds: 32 * 0x24 fills
//     A's gap exactly and 32 * 0x2C fills this one, so the stride grew
//     with the two fields the objective netfield table gained.
```

### 2.2 二十四层

```text
1. **CODOL 的 `playerState_s` 恰好 `0x3564` 字节**
2. ⇒ **`Pmove`（`0x0041E860`）与它的保留助手【变异这个调用者拥有的镜像**】**
3. ⇒ **BO1 的 `Pmove` 与 Ghosts 的【确认所有权与控制流责任】，而【它们的字段布局【不被使用**】】**
4. ⇒ **⇒ 【每一个偏移【都曾是 3.3.3.3 的**】**
5. ⇒ **`playerState_s` 在【八处**增长**：
      · **`+0`（头部**）
      · **`+20` / `+72` / `+80` / `+184` / `+192` / `+196` / `+224`**
      · **而【在尾部一直到 `+1048`**】
6. ⇒ **⇒ 整个每客户端镜像从 `0x3564` **到 `0x3BBC`**】**
7. ⇒ **⇒ 而【那张映射【来自【对齐两个 build 的【解出的网络字段表**】】**
8. ⇒ **（它们是两个布局的【一个逐字节精确的描述**））
9. ⇒ **⇒ 而【每一个【那个对齐【无法自行放置**】的偏移**
10. ⇒ **⇒ 然后【从 `out.exe` 读出**】
```

### 2.3 ⭐⭐⭐ **"来自对齐两个 build 的解出的网络字段表，然后每一个对齐无法放置的偏移从 `out.exe` 读出"**

**✅ 这是本报告里**最重要的方法论**。**

**⇒ 三层**：
```text
方法 A：**对齐两个 build 的网络字段表**（**逐字节精确**）
方法 B：**对无法对齐的，读 `out.exe` 的可执行代码**
⇒ **⇒ 所以【一个两级方法：表对齐 + 代码读出**】
```

**✅ 与 §414 的"`<map>_const.ff` 是数据"**、§451 的"BO1 是一个供体参照"**完全同族**。

**⇒ 三层**：
```text
§414  **表（`<map>_const.ff`）是权威**
§460  **表（网络字段表）是权威，对无法对齐的读代码**
⇒ **⇒ 两次"表优先，代码兜底**】
```

**✅ ⭐⭐⭐ **"表优先，代码兜底"**。

**⚠ 而"四个对齐的具体例子"⇒ **每一个都是【一个函数的逐行对照**】**

**⇒ 十层**：
```text
① **`BG_PlayerStateToEntityState`：A `sub_4131A0` <-> C `sub_411360`，逐行**
② **持武器遍历器：A `sub_55CFE0` <-> C `sub_594840`，同一个 `(v + 16) % 15` 循环**
③ **弹药池插入器：A `sub_42F820` <-> C `sub_4331A0`，同一个十五条目步长 `8` 扫描**
④ **目标块：`32` 条记录在两边**（`32 × 0x24` vs `32 × 0x2C`）
⇒ **⇒ 四个"同形"的证据**
```

**✅ ⭐⭐⭐ **"四个同形的证据"** —— 与 §419 的"`EV_LANDING_PAIN` 与 `EV_LANDING_HARD` 的同一 `<<5`"**同族（**第七次"用重复的形状证明语义"）。

**⇒ 三层**：
```text
§415  **`19` 与 `21` 的索引→偏移映射相同**
§419  **两个落地事件的同一 `<<5`**
§460  **四条 `A <-> C` 的逐行对照**
⇒ **⇒ 三次"同形的证据**】
```

**✅ ⭐⭐ **一个"同形"的三例表**。

### 2.4 而**"六个偏移的精确对照"**

```text
clientNum  0x144 → 0x158  (+0x14)
legs       0x0C8 → 0x0DC  (+0x14)
torso      0x0D0 → 0x0E4  (+0x14)
health     0x190 → 0x1A4  (+0x14)
maxHealth  0x198 → 0x1AC  (+0x14)
eFlags     0x0F0 → 0x104  (+0x14)
heldWeapons 0x2A4 → 0x2F4 (+0x50)
ammoPools   0x364 → 0x41C  (+0xB8)
clips       0x3DC → 0x494  (+0xB8)
```

**⇒ 十层**：
```text
1. **六个字段【同一个 `+0x14`**】**
2. ⇒ **`heldWeapons` ⇒ `+0x50`**
3. ⇒ **`ammoPools`/`clips` ⇒ `+0xB8`**
4. ⇒ **⇒ 所以【三个不同的增量**】
5. ⇒ **⇒ 而【六个字段共享 `+0x14`** ⇒ **它们【在同一个"之前的增长"里**】
```

**✅ ⭐⭐⭐ **"六个字段共享 `+0x14`，所以它们在同一个『之前的增长』里"** —— 一个**极精确的推断**。</br>

**✅ 与 §460 二.2 的"八处增长"**配合：**`+0x14 = 20`** ⇒ **正是那个 `+20`**。

**⇒ 三层**：
```text
注释：**"`+0` 在头部，然后 `+20`、`+72`、`+80`、`+184`、`+192`、`+196`、`+224`"**
而【六个字段 ⇒ `+0x14 = 20`**】⇒ **正是那个 `+20`** ✓
而【`heldWeapons` ⇒ `+0x50 = 80`**】⇒ **正是那个 `+80`** ✓
⇒ **⇒ 所以【两个增量【精确对应**】
```

**✅ ⭐⭐⭐ **"两个增量精确对应"** —— 一个**可验证的算术闭合**。

**⚠ 而"`ammoPools` 的 `+0xB8 = 184`"**⇒ **正是那个 `+184`** ✓

**⇒ 三层**：
```text
`+0xB8 = 184` ⇒ **正是第八个增长点 `+184`** ✓
⇒ **⇒ 所以【三个增量【全部对应**】
```

**✅ ⭐⭐⭐ **"三个增量全部对应"** —— 一个**完整的闭合**（`20` / `80` / `184`）。

## 三、**`SvSwayPhase` 的"零生产者 ⇒ 摆动锯齿化"**（本组第二重要）

### 3.1 那段

```php
// ★★★ 28100 刀BF（第 7 项「狙击镜抽搐/拉回」）——
//   **wire field 4（`ps+0x4a0` / hint 3 / `unk04A4Time`）是客户端 sway 相位种子**：
//   客户端每个快照拿它**整体改写**累加器，再叠加本地 usercmd 重放的推进；
//   **我方零生产者 ⇒ 客户端每快照被种 0 ⇒ 摆动按快照率锯齿化 = 拉回/抽搐**。
//   （demo 回放没有本地预测环，所以录不到这个抖动 —— 甲方看到的"demo 正常、实机抽搐"就是这条。）
```

### 3.2 二十层

```text
1. **wire field `4`（`ps+0x4a0` / hint `3` / `unk04A4Time`）是【客户端 sway 相位种子**】**
2. ⇒ **客户端【每个快照【拿它【整体改写**】那个累加器**
3. ⇒ **⇒ 然后【叠加【本地 usercmd 重放**的推进**】
4. ⇒ **⚠ 我方【零生产者**】**
5. ⇒ **⇒ 所以【客户端【每个快照被种 0**】】
6. ⇒ **⇒ 而【摆动【按快照率【锯齿化**】】】
7. ⇒ **⇒ ⇒ 【拉回 / 抽搐**】
8. ⇒ **⚠ 而【demo 回放【没有本地预测环**】**
9. ⇒ **⇒ 所以【录不到这个抖动**】**
10. ⇒ **⇒ 甲方看到的"demo 正常、实机抽搐"【就是这条**】**
```

### 3.3 ⭐⭐⭐ **"demo 回放没有本地预测环，所以录不到这个抖动 —— 甲方看到的『demo 正常、实机抽搐』就是这条"**

**✅ 这是本报告里**最重要的一条"一个缺失的生产者 + 一个录不到的合成**。**

**✅ 与 §416 的"`predictableEvents` 被读了、被服务端用了、并在线上之前被丢掉"**——**同族** ✓

**⇒ 三层**：
```text
§416  **可预测事件环【有数据而没发**】
§460  **sway 相位【零生产者**】
⇒ **⇒ 两次"一个字段的缺失**】
```

**✅ ⭐⭐⭐ **"一个字段的缺失"两例**。

**⚠ 而"demo 回放没有本地预测环"⇒ **一个极重要的取证限制**。**

**⇒ 三层**：
```text
demo ⇒ **一个服务器发出的录制** ⇒ **无客户端预测**
而【那个抖动【来自【客户端预测与服务器种子的交互**】
⇒ **⇒ 所以【demo 【不可能**录到它】
```

**✅ ⭐⭐⭐ **"demo 不可能录到它"** —— 与 §427 的"一个 demo 记录一个服务器发什么而完全不含 usercmd"**同族（**第二次"一个方向的信息 demo 没有**）。

**⇒ 三层**：
```text
§427  **demo 不含 usercmd**（**客户端→服务器**）
§460  **demo 不含客户端预测的抖动**（**一个交互效应**）
⇒ **⇒ 两次"demo 的一个盲区**】
```

**✅ ⭐⭐ **"demo 的一个盲区"两例**。

### 3.4 而**`SvProduceSwayPhase` 的五道**

```cpp
if (!SvSwayPhaseEnabled()) return carried;
auto &entry = g_swayPhases[clientNum];
if (!entry.valid || commandTime < entry.lastCommandTime) {
    entry.valid = true; entry.lastCommandTime = commandTime;
    entry.phase = static_cast<float>(commandTime);
    return static_cast<std::uint32_t>(entry.phase);
}
const auto delta = commandTime - entry.lastCommandTime;
entry.lastCommandTime = commandTime;
if (delta == 0 || delta > 1'000) return static_cast<std::uint32_t>(entry.phase);
constexpr float SwaySpeed = 1.0f;
entry.phase += static_cast<float>(delta) * SwaySpeed;
return static_cast<std::uint32_t>(entry.phase);
```

**⇒ 十四层**：
```text
1. **关闭 ⇒ 返回 `carried`**（**纯搬运，可回退**）
2. ⇒ **首帧 或 `commandTime` 回退** ⇒ **用 `commandTime` 作种子重新起播**
3. ⇒ **`delta = commandTime - lastCommandTime`**
4. ⇒ **`delta == 0` 或 `delta > 1'000`** ⇒ **返回当前相位**（**不推进**）
5. ⇒ **否则 `phase += delta * SwaySpeed`**
6. ⇒ **⇒ 所以【五道**】
```

### 3.5 ⭐⭐⭐ **"`delta == 0 || delta > 1'000` ⇒ 返回当前相位（不推进）"**

**✅ 与 §444 的"`setgroundtilttrajectory` 的 `duration = 0` 合法"**不同（这是**一个"暂停推进"的处置**）。

**⇒ 三层**：
```text
`delta == 0` ⇒ **同一 `commandTime` 两次** ⇒ **不推进**
`delta > 1'000` ⇒ **一个大跳**（**可能一个地图加载/卡顿**）⇒ **不推进**
⇒ **⇒ 所以【两个"不推进"的边界**】
```

**✅ ⭐⭐⭐ **"两个不推进的边界"** —— 一个**极精确的数值选择**。

**⚠ 而"`SwaySpeed = 1.0f`"⇒ **一个占位**。**

```php
// speed 暂用 1.0（零售的三种 speed 分支依赖武器 def 的 sway 字段，偏移我方未核实，**不搬对方数字**）
constexpr float SwaySpeed = 1.0f;
```

**✅ 与 §450 的"`5000` 是同一个引擎家族的数字而不是这个项目的一个猜测"**相反**（那里**用了一个外部的数**，这里**明确不使用**）**。

**⇒ 三层**：
```text
§450  **一个外部的数（`5000`）【被用**，因为【同一个引擎家族**】
§460  **一个外部的数【不被用**，因为【偏移未核实**】
⇒ **⇒ 所以【"用"与"不用"都有理由**】
```

**✅ ⭐⭐⭐ **"用与不用都有理由"**。</br>

**✅ 与 `AGENTS.md` 的"不得引用 ol-mod 的常量"**完全一致 **（`**不搬对方数字**`）**。

**⇒ 三层**：
```text
`AGENTS.md`：**"Never copy its constants"**
§460：**"零售的三种 speed 分支依赖武器 def 的 sway 字段，偏移我方未核实，**不搬对方数字**"**
⇒ **⇒ 一个显式的合规**
```

**✅ ⭐⭐ **"一个显式的合规"**。

## 四、**`MaximumViewmodelIndex = 0x3FF` vs `MaximumWeaponIndex = 0x7FF`**（本组第三重要）

### 4.1 那段

```cpp
constexpr std::uint32_t MaximumClientNum = 63;
constexpr std::uint32_t MaximumEntityNum = 2047;
constexpr std::uint32_t MaximumWeaponIndex = 0x7FF;
// CODDIFF(1649370): THE VIEWMODEL INDEX DID NOT WIDEN WITH THE WEAPON
// INDEX. On 3.3.3.3 both fields are ten bits, so one constant served
// both and nothing distinguished them. Here the weapon index is eleven
// bits (playerState field 39, `currentWeapon`) and the viewmodel index
// is still TEN (field 56, offset 0x15C). Validating the viewmodel
// against 0x7FF admits values the snapshot writer then refuses under
// `playerstate domain refused: viewmodelIndex`, which reports the
// failure a whole stage away from the field that caused it.
constexpr std::uint32_t MaximumViewmodelIndex = 0x3FF;
```

### 4.2 二十层

```text
1. **`MaximumClientNum = 63`**（`6` 位）
2. ⇒ **`MaximumEntityNum = 2047`**（`11` 位）
3. ⇒ **`MaximumWeaponIndex = 0x7FF`**（`11` 位）
4. ⇒ **⚠ 而 `MaximumViewmodelIndex = 0x3FF`**（`10` 位）
5. ⇒ **⇒ 因为在 3.3.3.3 上【两个字段【都是 `10` 位**】**
6. ⇒ **⇒ 所以【一个常量【服务两个**而【没有东西区分它们**】
7. ⇒ **而在这里【武器索引【是 `11` 位**】（**`playerState` 字段 `39`**）
8. ⇒ **而【viewmodel 索引【仍然是 `10` 位**】（**字段 `56`，偏移 `0x15C`**）
9. ⇒ **⇒ 用 `0x7FF` 验证 viewmodel ⇒ 【允许**snapshot 写者【然后拒绝**的值**
10. ⇒ **（`playerstate domain refused: viewmodelIndex`）**
11. ⇒ **⇒ 而它【把失败【报告在【整整一个阶段之外**的地方**
```

### 4.3 ⭐⭐⭐ **"它把失败报告在整整一个阶段之外的地方"**

**✅ 这是本报告里**最重要的一条"一个错误的验证域**。**

**✅ 与 §413 的"`missing_playerstate` 命名了错误的嫌疑"**、§431 的"`181` 是一个 GAMESTATE 对齐问题"**完全同族**（**第七次"症状的位置与根因的位置无关**）。

**⇒ 三层**：
```text
验证域错 ⇒ **一个合法的值通过**
⇒ **而 snapshot 写者【拒绝它**】
⇒ **⇒ 所以【错误【在【下游**】报告
```

**✅ ⭐⭐⭐ **"错误在下游报告"** —— 而**`0x3FF` 修正了那个验证域**。

**⚠ 而"字段 `39` 是 `11` 位而字段 `56` 是 `10` 位"⇒ **两个不同的宽**。**

**✅ 与 §416 的"`currentWeaponAssetIndex` 是 netfield `39`"**完全闭合 ✓

**⇒ 三层**：
```text
§416  **"`currentWeaponAssetIndex` 是 netfield `39`"**
§460  **"字段 `39`，`11` 位"**
⇒ **⇒ 一个精确的位宽**
```

**✅ ⭐⭐ **"一个精确的位宽"**。

## 五、`ObjectiveStride = 0x2C` vs `0x24`

```cpp
constexpr std::size_t ObjectivesOffset = 0x6C8;
constexpr std::size_t ObjectiveStride = 0x2C;
constexpr std::size_t ObjectiveOriginOffset = 0x04;
constexpr std::size_t ObjectiveEntityNumOffset = 0x10;
constexpr std::size_t ObjectiveTeamNumOffset = 0x14;
constexpr std::size_t ObjectiveIconOffset = 0x20;
```

**⇒ 十层**：
```text
1. **`32` 条目标，步长 `0x2C`**（`44` 字节/条）
2. ⇒ **而 3.3.3.3 是 `0x24`**（`36` 字节）
3. ⇒ **⇒ 所以【每条【长了 `8` 字节**】
4. ⇒ **而【那个增长【是因为【目标网络字段表【多了两个字段**】】**
```

**✅ 与 §460 二.2 的"`32 × 0x24` 恰好填满 A 的间隙而 `32 × 0x2C` 填满这个"**完全闭合 ✓

**⇒ 三层**：
```text
`32 × 0x24 = 1152`（`0x480`）
`32 × 0x2C = 1408`（`0x580`）
⇒ **差 `256`** ⇒ **每条 `8` 字节 × `32`**
```

**✅ ⭐⭐ **一个"`32 × 8 = 256`"的算术**。

## 六、`writeValue`/`readValue` 的"只访问固定偏移"

```cpp
// OLMOD(native-playerstate-typed-overlay): these helpers access only
// fixed offsets in the CODOL byte image catalog above. They do not
// claim that SvNativePlayerState is a complete native structure.
template <typename Value>
void writeValue(SvNativePlayerState &state, const std::size_t offset, const Value &value)
{
    static_assert(std::is_trivially_copyable_v<Value>);
    std::memcpy(state.bytes.data() + offset, &value, sizeof(value));
}
```

**⇒ 八层**：
```text
1. **只访问【固定偏移**】
2. ⇒ **【不声称**`SvNativePlayerState` 是一个【完整的**原生结构**
3. ⇒ **`static_assert(is_trivially_copyable_v<Value>)`** ⇒ **一个编译期保证**
4. ⇒ **⇒ 所以【`memcpy` 是安全的**
```

**✅ 与 §421 的"`svOriginText` 是模板 on purpose"**同族（**第四次"模板的用途**）。

**⇒ 三层**：
```text
§409  **`sdOriginText` 是模板**（**因为三类 origin 别名不同**）
§460  **`writeValue`/`readValue` 是模板**（**因为任何 trivially copyable 类型**）
⇒ **⇒ 两次"模板的用途**】
```

**✅ ⭐ **一个"模板"的两例**。

**⚠ 而"不声称它是一个完整的原生结构"**⇒ **一个极重要的声明**。**

**✅ 与 §424 的"`WorldClientState` 的大小是一个行为"**不同（这是**一个"类型不是原生布局"的声明**）。

**⇒ 三层**：
```text
`SvNativePlayerState` ⇒ **一个字节镜像**（**一个"catalog of offsets"**）
而【原生 `playerState_s` ⇒ **`0x3BBC` 字节**
⇒ **⇒ 所以【一个【命名视图**而不是【一个结构**】
```

**✅ ⭐⭐⭐ **"一个命名视图而不是一个结构"**。

## 七、关键结论

1. **⭐⭐⭐ "CODOL 的 `playerState_s` 恰好 `0x3564` 字节"而为 3.3.3.3 的偏移【每一个都曾是 3.3.3.3 的】，它在【八处增长**（`+0`/`+20`/`+72`/`+80`/`+184`/`+192`/`+196`/`+224`/尾到 `+1048`）**从 `0x3564` 到 `0x3BBC`**。
2. **⭐⭐⭐ 两级重建方法**：**"那张映射来自【对齐两个 build 的【解出的网络字段表】**（它们是两个布局的**逐字节精确的描述**），而**每一个对齐无法自行放置的偏移【从 `out.exe` 读出**】"` —— **"表优先，代码兜底"**。
3. **⭐⭐⭐ 四条"同形"的证据**：`BG_PlayerStateToEntityState`（A `sub_4131A0` <-> C `sub_411360` 逐行）、持武器遍历器（同一个 `(v+16)%15` 循环）、弹药池插入器（同一个十五条目步长 `8` 扫描）、目标块（`32 × 0x24` vs `32 × 0x2C`）—— 第七次"用重复的形状证明语义"。
4. **⭐⭐⭐ 三个增量精确对应八个增长点**：`clientNum`/`legs`/`torso`/`health`/`maxHealth`/`eFlags` **六个字段共享 `+0x14 = 20`**（**正是那个 `+20`**）/ `heldWeapons` 的 `+0x50 = 80`（**正是那个 `+80`**）/ `ammoPools`+`clips` 的 `+0xB8 = 184`（**正是那个 `+184`**）—— **一个可验证的算术闭合**。
5. **⭐⭐⭐ `SvSwayPhase` 的"零生产者 ⇒ 客户端每个快照被种 `0` ⇒ 摆动按快照率锯齿化 = 拉回/抽搐"**，而 **"demo 回放没有本地预测环，所以录不到这个抖动 —— 甲方看到的『demo 正常、实机抽搐』就是这条"`** —— 第二次"demo 的一个盲区"（与 §427 的"demo 不含 usercmd"同族）。
6. **⭐⭐ `SvProduceSwayPhase` 的五道**（关闭 ⇒ `carried` / 首帧或回退 ⇒ 重播种 / `delta == 0` / `delta > 1'000` / 否则推进）⇒ **"两个不推进的边界"**。
7. **⭐⭐⭐ "`SwaySpeed = 1.0f` 是一个占位：零售的三种 speed 分支依赖武器 def 的 sway 字段，偏移我方未核实，【不搬对方数字**】"`** —— 与 §450 的"用了一个外部的数（`5000`）因为同一个引擎家族"**相反**（这里**明确不使用**）⇒ **"用与不用都有理由"**；也是**一个显式的 `AGENTS.md` 合规**（"Never copy its constants"）。
8. **⭐⭐⭐ `MaximumViewmodelIndex = 0x3FF`（`10` 位）vs `MaximumWeaponIndex = 0x7FF`（`11` 位）**：**"在 3.3.3.3 上两个字段都是 `10` 位，所以一个常量服务两个而没有东西区分它们；在这里武器索引是 `11` 位（字段 `39`）而 viewmodel 仍是 `10` 位（字段 `56`，偏移 `0x15C`）⇒ 用 `0x7FF` 验证 viewmodel 允许 snapshot 写者然后拒绝的值，【它把失败报告在整整一个阶段之外的地方**】"`** —— 第七次"症状的位置与根因的位置无关"。
9. **⭐ `ObjectiveStride = 0x2C`（`44`）vs 3.3.3.3 的 `0x24`（`36`）⇒ 每条长 `8` 字节 ⇒ `32 × 8 = 256`**。
10. **⭐⭐ `writeValue`/`readValue` 的"只访问固定偏移，不声称 `SvNativePlayerState` 是一个完整的原生结构"`** ⇒ **"一个命名视图而不是一个结构"** —— 第四次"模板的用途"。

## 八、未闭合点

- `CommandTimeOffset = 0x000` 与 `+0x10`（`OtherFlags`）的混淆 getter（`dword_E60B78 ^ ps[36] ^ (ps+32)`）。
- `Unk04A4TimeOffset = 0x568` 的名字（`+0x4A4` 偏移 vs `0x568` 常量——**两个数不同**，需核对）。
- `SwaySpeed` 的三种零售 speed 分支。
- `0x3564` 与 `0x3BBC` 的完整八处增长。
- `sv_native_playerstate_mp.cpp` 480 行之后未读取（**共 `1687` 行**）。
