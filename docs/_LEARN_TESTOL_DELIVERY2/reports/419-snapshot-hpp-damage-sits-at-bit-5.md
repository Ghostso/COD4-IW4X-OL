# 419 · **"落地的伤害在 bit 5，所以一次 12 点的坠落读成 384"** —— `PM_CrashLand` 的四条指令就是整个规格、`-1` 的实测、以及 `offsetof == 0` 的编译期规则

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 2330–2960 行。

## 二、**落地疼痛的打包字**（本组最重要的一段）

### 2.1 那段

```cpp
// AND THE PARAMETER IS NOT THE DAMAGE. It is a packed word, and reading it
// as a plain number kills the player on any landing that hurts at all: the
// damage sits at bit 5, so a 12-damage fall reads as 384 or more.
//
// PM_CrashLand builds it inline at 0x00416964..0x0041697E, and the four
// instructions are the whole specification:
//
//   mov  eax, ecx        ; ecx = pm->groundTrace.surfaceFlags (pm+0x48,
//   shr  eax, 0Ch        ;       which is groundTrace+0x10 -- the project's
//   and  eax, 1          ;       own trace_t already puts surfaceFlags at
//   shl  eax, 7          ;       +0x10, and sv_bullet_mp reads the surface
//   or   eax, [ebp-4]    ;       type out of >>20 & 0x1F exactly like this)
//   shl  eax, 5          ; [ebp-4] = the damage, from the curve helper at
//   or   eax, esi        ; 0x00416590; esi = (surfaceFlags >> 20) & 0x1F
//
//   bits 0..4   surface type index, for the client's landing sound
//   bits 5..11  THE DAMAGE
//   bit  12     set when surfaceFlags & 0x1000 chose the soft-surface curve
//
// Seven bits is exactly enough because the curve helper's cap is a literal
// 100 (0x64 at 0x004165C6), or 10 (0x0A at 0x004165A5) on the soft-surface
// branch. EV_LANDING_HARD at 0x00416AB4 packs the same way -- an intensity
// clamped to 24 shifted up by 5, over the same surface index -- which is
// what says the layout is a convention and not a coincidence.
```

### 2.2 二十四层

```text
1. **那个参数【不是伤害**】**
2. ⇒ **它是一个【打包的字**】**
3. ⇒ **把它当作一个普通数字读【会让玩家在任何真正疼痛的落地上死掉**】**
4. ⇒ **⇒ 因为伤害坐在【位 `5`**】**
5. ⇒ **所以一次 `12` 点的坠落【读成 `384` 或更多**】**
6. ⇒ **`PM_CrashLand` 在 `0x00416964..0x0041697E` 【内联**】构建它
7. ⇒ **而【那四条指令就是整个规格**】**：
      · **`mov eax, ecx`** ⇒ `ecx = pm->groundTrace.surfaceFlags`（`pm+0x48`，即 `groundTrace+0x10`）
      · **`shr eax, 0Ch`**
      · **`and eax, 1`**
      · **`shl eax, 7`**
      · **`or eax, [ebp-4]`** ⇒ `[ebp-4]` 是**伤害**（来自 `0x00416590` 的曲线助手）
      · **`shl eax, 5`**
      · **`or eax, esi`** ⇒ `esi = (surfaceFlags >> 20) & 0x1F`
8. ⇒ **位 `0..4`** ⇒ **表面类型索引**（客户端的落地音）
9. ⇒ **位 `5..11`** ⇒ **伤害**（`7` 位）
10. ⇒ **位 `12`** ⇒ **当 `surfaceFlags & 0x1000` 选了软表面曲线时置位**
11. ⇒ **⇒ `7` 位**恰好够**，因为曲线助手的【上限是一个字面量 `100`**】（`0x64`）
12. ⇒ **或【软表面分支上的 `10`**】（`0x0A`）
13. ⇒ ⇒ **`100 < 128 = 2^7`** ✓
14. ⇒ **`EV_LANDING_HARD` 在 `0x00416AB4` **同样的打包**】
15. ⇒ **（一个强度夹到 `24`，上移 `5`，在同一个表面索引之上）**
16. ⇒ **⇒ 那就是【说这个布局是一个约定而不是一个巧合**】的东西
```

### 2.3 ⭐⭐⭐ **"那个布局是一个约定而不是一个巧合"**

**✅ 这是本报告里**最重要的一条"约定 vs 巧合"判据**。**

**⇒ 三层**：
```text
一个事件：`EV_LANDING_PAIN` 把伤害放在 bit 5 ⇒ **可能只是这一个实现**
两个事件：`EV_LANDING_HARD` **同样的 `<<5` 与同样的表面索引** ⇒ **是一个约定**
⇒ **⇒ 所以【同一形状出现两次 ⇒ 它是设计**】
```

**✅ 与 §407 的"`L` 的第二个参数就是槽位号"**同族（**第六次"两个数同值 ⇒ 同物"）。

**⇒ 三层**：
```text
§407  `L n 7` 的 `7` ↔ `SetCardDisplaySlot(attacker, 7)`
§418  `predicted=1140621312` ↔ `origin=505.0`
§419  `EV_LANDING_PAIN` 与 `EV_LANDING_HARD` 的同一 `<<5`
⇒ **⇒ 三次"形状匹配 ⇒ 语义匹配**】
```

**✅ ⭐⭐ **一个"用重复的形状证明约定"的三例表**。

**⚠ 而"`12` 读成 `384`"⇒ **`12 << 5 = 384`** ✓

**✅ 算术闭合**。

### 2.4 而**"那四条指令就是整个规格"**

```php
//   mov  eax, ecx        ; ecx = pm->groundTrace.surfaceFlags
//   shr  eax, 0Ch        ; 
//   and  eax, 1          ; 
//   shl  eax, 7          ; 
//   or   eax, [ebp-4]    ; [ebp-4] = the damage
//   shl  eax, 5          ; 
//   or   eax, esi        ; esi = (surfaceFlags >> 20) & 0x1F
```

**⇒ 十六层（逐指令）**：
```text
1. `mov eax, ecx`      ⇒ **`eax = surfaceFlags`**
2. `shr eax, 0Ch`      ⇒ **`eax = surfaceFlags >> 12`**
3. `and eax, 1`        ⇒ **`eax = (surfaceFlags >> 12) & 1 = bit 12`**
4. `shl eax, 7`        ⇒ **`eax = bit12 << 7`** ⇒ **最终落在结果的位 `7`**
5. `or  eax, [ebp-4]`  ⇒ **`eax = (bit12<<7) | damage`**
6. `shl eax, 5`        ⇒ **`eax <<= 5`** ⇒ **damage 移到位 `5..`，而 bit12 移到 `5+7 = 12`** ✓
7. `or  eax, esi`      ⇒ **`eax |= esi`**（`esi` 是 `0..31` 的表面类型）
```

**✅ ⭐⭐⭐ **一个"位 `12` 的来源"的完整推导**。**

**⇒ 三层**：
```text
`bit 12` ⇒ **先被放到 `eax` 的位 `7`**（`shl 7`）
⇒ **然后整体 `shl 5`** ⇒ **位 `7` 到 `12`**（**`7+5 = 12`**）
⇒ **⇒ 所以【那个 `shl 7` 是为了补偿后面的 `shl 5`**】
```

**✅ ⭐⭐ **"两次移位相减"的精确解释**（**`7 + 5 = 12`**）。

**⚠ 而"`7` 位恰好够"⇒ **`100 < 128`**。**

**⇒ 若需要 `7` 位（`0..127`），那么 `damage > 127` 会**溢出到 `bit 12`**（与软表面标志冲突）。

**⇒ 三层**：
```text
曲线上限 `100` ⇒ **`< 128`** ⇒ **安全**
若上限 `128` ⇒ **溢出到 `bit 12`** ⇒ **与软表面标志冲突** ⇒ **bug**
⇒ **⇒ 所以【`7` 位与上限 `100` 是一个【协同的设计**】**
```

**✅ ⭐ **一个"位宽与上限的协同"**。

### 2.5 而**"两个自动抑制"**

```php
// Two suppressions live in the same tail and cost us nothing to honour,
// because pmove applies them before the event exists: surfaceFlags & 0x2000
// raises no event at all, and a surface type of 0 raises no event either.
```

**⇒ 五层**：
```text
1. **`surfaceFlags & 0x2000`** ⇒ **完全不放事件**
2. ⇒ **表面类型 `0`** ⇒ **也不放事件**
3. ⇒ **而 `pmove` 【在事件存在之前**】就应用它们**
4. ⇒ **⇒ 所以【这个服务器【不必检查**】它们**
```

**✅ ⭐⭐ **"在事件存在之前就抑制"** —— **一个"不必重复检查"的实例**。

**✅ 与 §409 的"`scoreBefore`/`scoreAfter` 的差必须为 1"**不同（这是**上游已过滤**）。

### 2.6 而**"零售取走少一点"**

```php
// AND RETAIL TAKES ONE LESS THAN THAT OFF THE PLAYER. Measured, not
// reasoned: Tools/demo-re/landing-pain.py pulls every EV_LANDING_PAIN out of
// the recorder's own playerState ring and reads the STATS health either side
// of it. Fifteen landings moved health at all, across a dm, a dom and a
// zsurv demo, and all fifteen moved it by the packed damage MINUS ONE --
// 34->33, 31->30, 25->24, down to 2->1. The 2->1 one is the load-bearing
// sample: the player was on 71 health, not 100, so "he was really on 101"
// cannot explain the gap.
//
// WHAT IT IS NOT. Neither PM_CrashLand's curve helper (0x00416590, which
// truncates (h-min)/(max-min)*maxDamage) nor the alternate curve that can
// overwrite it (0x0040B950, the same shape times a literal 100.0) adds one
// anywhere, so the difference is on the applying side and not in the packing
// this decodes.
```

**⇒ 二十四层**：
```text
1. **零售【从玩家身上取走的比那个少一**】**
2. ⇒ **测出来的，不是推理的**
3. ⇒ **`Tools/demo-re/landing-pain.py` 从记录器自己的 `playerState` 环里【抽出每一个 `EV_LANDING_PAIN`**】**
4. ⇒ **并读它两边的 STATS 生命值**
5. ⇒ **`15` 次落地【真的移动了生命**】（跨 dm/dom/zsurv 三个 demo）**
6. ⇒ **⇒ 而全部 `15` 次都移动了【打包伤害减一**】**
7. ⇒ **（`34→33`、`31→30`、`25→24`，一直到 `2→1`）**
8. ⇒ **⇒ `2→1` 那一个【是承重的样本**】**
9. ⇒ **因为玩家在 `71` 生命上，不是 `100`**
10. ⇒ **⇒ 所以"他其实在 `101`"【不能解释那个差**】**
11. ⇒ **⚠ 而它【不是】什么**：
      · **`PM_CrashLand` 的曲线助手 `0x00416590`（截断 `(h-min)/(max-min)*maxDamage`）**
      · **与能覆写它的另一条曲线 `0x0040B950`（同形状乘字面量 `100.0`）**
      · **【两处都没有在任何地方加一**】**
12. ⇒ **⇒ 所以【那个差在【应用侧**】而不在这个解码的打包里**】
```

### 2.7 ⭐⭐⭐ **"`2→1` 那个是承重的样本：玩家在 71 生命上，不是 100"**

**✅ 这是本报告里**最漂亮的一个"排除竞争解释"**。**

**⇒ 三层**：
```text
竞争假设：**伤害算出来是 N，而玩家实际掉 N-1 是因为"他其实在 100+N-1"**
⇒ 若玩家在 `100` ⇒ **`2→1` 也能解释为"实际 101 → 99"**
而实测：**玩家在 `71`** ⇒ **`71 → 70`** ⇒ **假设被排除**
⇒ **⇒ 所以【一个偏离常态的样本是【最好的**证据**】
```

**✅ ⭐⭐⭐ **"一个不典型的样本比十五个典型的更有说服力"** —— 一个**极重要的取证原则**。

**✅ 与 §407 的"`24` 个 `r 2` 簇的第一个前面没有 `N`"**同族（**第四次"一个例外是判决性的"）。

**⇒ 三层**：
```text
§407  **第一个簇**（`0:02.5`）前面没有 `N` ⇒ **排除出生假设**
§414  **零售自己的 demo 显示 eType 0 而文件说 6** ⇒ **排除文件假设**
§419  **`2→1` 而玩家在 `71`** ⇒ **排除"其实在 101"假设**
⇒ **⇒ 三次"一个例外定案**】
```

**✅ ⭐⭐ **一个"例外定案"的三例表**。

**⚠ 而"一个略低于 `1` 的乘数也能拟合那 `15` 个样本"⇒ **一个诚实的未闭合**。**

```php
// A multiplier a shade under 1 fits the same fifteen samples
// -- the largest drop measured is 34, which is not enough to separate them
// -- so this is written as the simpler rule that fits, and the corpus is
// named so a bigger fall can settle it later.
```

**⇒ 六层**：
```text
1. **一个略低于 `1` 的乘数【拟合同样那 `15` 个样本**】**
2. ⇒ **（最大的落差是 `34`，【不足以分开它们**】）**
3. ⇒ **⇒ 所以【这个实现写成【拟合的更简单的规则**】**
4. ⇒ **而【那个语料被命名了，所以一个更大的坠落可以在以后定案**】**
```

**✅ ⭐⭐⭐ **"一个更大的坠落可以定案"** —— 一个**明确的"什么能推翻我"**。

**✅ 与 §415 的"如果僵尸仍然保持一个姿势而别名在线上，那个 resolve 因另一个原因失败"**同族（**第二次"可证伪条件"。

**⇒ 三层**：
```text
简化规则：`N - 1`
乘数规则：`N * (1-ε)`
区别：**只在 `N` 大时显现**（`34` 不够）
⇒ **⇒ 所以【"一个更大的坠落"是一个具体的实验**】
```

**✅ ⭐ **一个"判据需要更大样本"的实例**。

## 三、**健康恢复的两个数**（本组第二重要）

### 3.1 那段

```php
// HEALTH REGEN, MEASURED OFF RETAIL RATHER THAN CHOSEN.
//
// Health does not travel as a netfield -- it rides the snapshot stats
// section (ps_trailing T1) as an i16 -- so the curve is readable straight
// off a retail capture with Tools/demo-re/health-timeline.py. Two demos
// eighteen months and one gametype apart agree:
//
//   2021 dm  (the spec demo)   delay 5000 ms x11 (one 1600)  200 hp/s x13
//   2020 war (independent)     delay 5000 ms x2  (one 5050)  200 hp/s x4
//
// The retail steps are +20 health per 100 ms frame, which is where the
// per-second figure comes from; nothing here infers a model beyond those
// two numbers. The rate is expressed in ABSOLUTE health per second and not
// as a fraction of maxHealth: every measured life had maxHealth 100, so the
// two models are indistinguishable in this corpus and the absolute reading
// is the one that does not invent a dependency the evidence cannot support.
```

### 3.2 二十层

```text
1. **健康恢复，从零售测出而不是选定的**
2. ⇒ **健康【不作为 netfield 传输**】**
3. ⇒ **它骑在快照的 stats 节（`ps_trailing T1`）上作为一个 `i16`**
4. ⇒ **⇒ 所以那条曲线【可以直接从一份零售捕获里读**】**
5. ⇒ **两个相距十八个月、一个 gametype 的 demo 一致**：
      · **2021 dm**：**延迟 `5000 ms` ×`11`**（一个 `1600`）、**`200 hp/s` ×`13`**
      · **2020 war**：**延迟 `5000 ms` ×`2`**（一个 `5050`）、**`200 hp/s` ×`4`**
6. ⇒ **零售的步长是【每 `100 ms` 帧 `+20` 生命**】**
7. ⇒ **⇒ 那就是【每秒那个数字的来源**】**
8. ⇒ **这里【不推断超出那两个数字的任何模型**】**
9. ⇒ **⇒ 速率表示为【绝对生命每秒】而不是 `maxHealth` 的一个分数**
10. ⇒ **因为【每一个被测量的生命都是 `maxHealth = 100`**】**
11. ⇒ **⇒ 所以【两个模型在这个语料里不可区分**】**
12. ⇒ **而【绝对读法是【那个不发明一个证据无法支撑的依赖**】的**
```

### 3.3 ⭐⭐⭐ **"那个不发明一个证据无法支撑的依赖"**

**✅ 这是本报告里**最重要的一条"选择更弱的模型"**。**

**⇒ 三层**：
```text
模型 A：`200 hp/s`（绝对） ⇒ **一个数字**
模型 B：`2 × maxHealth/s`（相对） ⇒ **一个数字 + 一个依赖**
证据：**全部样本 `maxHealth = 100`** ⇒ **两者给出相同结果**
⇒ **⇒ 所以【选 A，因为它假设更少**】
```

**✅ ⭐⭐⭐ **"两个模型不可区分时，选假设更少的那个"** —— 一个**奥卡姆剃刀的精确应用**。

**✅ 与 §419 二 的"简化规则"**同族（**第二次"在不可区分时选简单的"）。

**⇒ 三层**：
```text
§419 二  **`N-1` vs 乘数** ⇒ **选 `N-1`**（更简单）
§419 三  **绝对 vs 相对** ⇒ **选绝对**（更少依赖）
⇒ **⇒ 同一原则两次**
```

**✅ ⭐ **一个"最小假设"的两例**。

**⚠ 而"`5000 ms` 延迟"⇒ **两个 demo 一个 `1600` 一个 `5050` 的例外**。**

**⇒ 三层**：
```text
主流：`5000`
例外：`1600`（dm 一次）、`5050`（war 一次）
⇒ **⇒ 所以【`5000` 是模态值而不是常数**】
```

**✅ 与 §404 的"`deltaTime` 跑 `6000..6500`，`5000` 是模态值"**同族（**第二次"模态值**）。

**⇒ 三层**：
```text
§404  回放 `deltaTime` ⇒ **`6000..6500`，`5000` 是模态**
§419  恢复延迟 ⇒ **`5000`，`1600`/`5050` 是例外**
⇒ **⇒ 两次"模态值而不是定值**】
```

**✅ ⭐ **一个"模态 vs 常数"的两例**。

### 3.4 而**"`healthAtDamage` 无符号是为了匹配"**

```cpp
// Unsigned to match SvPlayerState::health exactly. Signed here made the
// damage site's designated initialiser a narrowing conversion in a
// braced-init-list, which is ill-formed, not merely a warning.
std::uint32_t healthAtDamage{};
```

**⇒ 五层**：
```text
1. **无符号，为了【精确匹配**】`SvPlayerState::health`**
2. ⇒ **有符号会让伤害点的【指定初始化器**】成为一个【窄化转换**】**
3. ⇒ **在一个【花括号初始化列表**】里**
4. ⇒ **⇒ 而那是【ill-formed，不只是警告**】**
5. ⇒ **⇒ 所以【类型必须匹配，否则编译失败**】
```

**✅ ⭐ **"ill-formed 不是警告"** —— 一个**C++ 语义的精确说明**。

**✅ 与 §419 二 的"那四条指令就是整个规格"**不同（这是**编译期约束**）。

## 四、**`offsetof == 0` 是一条规则**（本组第三重要）

### 4.1 那段

```cpp
// THE NATIVE BUFFER GOES FIRST SO THAT NOTHING ELSE CAN MOVE IT.
//
// It used to sit AFTER playerState, which means every field added to
// SvPlayerState changed its offset -- and therefore its address, since
// these live in an unordered_map node. CODOL stores a function pointer
// as key ^ function ^ THE PAIRED SLOT'S OWN ADDRESS (see
// rebindNativePlayerStateAccessors), so an address that moves is not a
// detail of layout, it is the thing the obfuscation is keyed to.
//
// 2026-08-24: four playerState members were added for the killcam and
// the death animation stopped selecting -- durationMs went from 2250 to
// -1, "no animation matched", and every death T-posed. The A/B is
// recorded in the handoff: the same match on the previous build
// animates. By elimination it is that commit -- the other three in the
// range only run AFTER match completion, and the FIRST death of a match
// failed too -- and the only part of it that runs before a death is
// this struct getting bigger.
//
// Offset 0 cannot move. The static_assert below is what makes that a
// rule rather than an accident of declaration order.
static_assert(offsetof(SvGameClient, nativePlayerState) == 0);
```

### 4.2 二十四层

```text
1. **原生缓冲放在最前面，这样【没有别的东西能移动它**】**
2. ⇒ **它过去坐在 `playerState` 【之后**】**
3. ⇒ **⇒ 那意味着【每一个加到 `SvPlayerState` 的字段都改变了它的偏移**】**
4. ⇒ **⇒ 以及【它的地址**】（因为它们住在一个 `unordered_map` 节点里）
5. ⇒ **CODOL 把一个函数指针存成【`key ^ function ^ 那个配对槽【自己的地址**】】**】
6. ⇒ **（见 `rebindNativePlayerStateAccessors`）**
7. ⇒ **⇒ 所以【一个移动的地址不是一个布局细节，它是【那个混淆所键控的东西**】】**
8. ⇒ **`2026-08-24`：为 killcam 加了四个 `playerState` 成员**
9. ⇒ **⇒ 而【死亡动画停止选择**】**
10. ⇒ **（`durationMs` 从 `2250` 变成 `-1`，"没有动画匹配"，每一次死亡都 T-pose）**
11. ⇒ **⇒ 那个 A/B 记录在 handoff 里**：**同一场比赛在前一个 build 上会动**
12. ⇒ **⇒ 用排除法【就是那个提交**】**
13. ⇒ **（那个范围内的另外三个【只在比赛完成之后**】跑，**而一场比赛的第一次死亡也失败了**）**
14. ⇒ **⇒ 而它【在死亡之前跑的【唯一部分**】**，就是【这个结构变大**】】
15. ⇒ **⇒ 【偏移 `0` 不能移动**】**
16. ⇒ **而下面的 `static_assert` 就是【让那成为一条规则而不是声明顺序的一个意外**】**
```

### 4.3 ⭐⭐⭐ **"让那成为一条规则而不是声明顺序的一个意外"**

**✅ 这是本报告里**最重要的一条"把约定变成断言"**。**

**⇒ 三层**：
```text
纯靠约定：**"别把东西放到 `nativePlayerState` 前面"**
靠断言：`static_assert(offsetof(...) == 0)` ⇒ **违反 ⇒ 编译失败**
⇒ **⇒ 所以【一条不可违反的规则**】
```

**✅ 与 §418 的"`audit-wire-zero-baseline.py`"**同族（**第三次"规则的可执行化"）。

**⇒ 三层**：
```text
运行时：`audit-wire-zero-baseline.py`（**Python 扫描**）
编译时：`static_assert`（**C++ 断言**）
运行时：`check_perframe_cost.py`（**性能**）
⇒ **⇒ 三个层次的可执行化**
```

**✅ ⭐⭐ **一个"规则可执行化"的三层**。

### 4.4 而**"`key ^ function ^ 那个配对槽自己的地址"`**

**⇒ 六层**：
```text
1. **CODOL 把一个函数指针存成【`key ^ function ^ address`**】**
2. ⇒ **⇒ 所以【`address` 参与加密**】**
3. ⇒ **⇒ 而 `address` 变了 ⇒ 【解密出错误的函数指针**】**
4. ⇒ **⇒ 所以【"布局"不是"性能"而是"正确性**】**
5. ⇒ **而那个 `key` 与 `address` 的配对【让每个槽不同**】**
6. ⇒ **⇒ 所以【一个全局的混淆密钥不足以，必须是每个槽自己的地址**】
```

**✅ ⭐⭐⭐ **"用槽自己的地址作为密钥的一部分"** —— 一个**自定位的混淆**。

**⇒ 三层**：
```text
若密钥是全局的 ⇒ **一份密钥泄露全破**
若密钥含槽地址 ⇒ **每个槽不同 ⇒ 泄露一个只破一个**
⇒ **⇒ 所以【这是一个更强的方案**】
```

**✅ ⭐ **一个"密钥设计"的机制解释**。

**⚠ 而"`durationMs` 从 `2250` 到 `-1`"⇒ **一个精确的数值**。**

**✅ 与 §388 的"`deathAnimMs = -1` ⇒ `max(-1,1)` 塌成 1ms 保持"**完全闭合 ✓

**⇒ 三层**：
```text
§388  `deathAnimMs = -1` ⇒ **`max(-1,1) = 1`** ⇒ **死亡瞬时、静默覆盖 `dm.lua` 的 `3000`**
§419  `durationMs` 从 `2250` 到 `-1` ⇒ **"没有动画匹配"** ⇒ **T-pose**
⇒ **⇒ 同一个 `-1` 在两层上的不同表现**
```

**⚠ 一处**差异**：§388 说 `-1` 导致"死亡瞬时"，§419 说 `-1` 导致"T-pose"。**

**⇒ 三层**：
```text
§388  `-1` ⇒ **塌成 `1ms` 的保持** ⇒ **死亡瞬时**
§419  `-1` ⇒ **"没有动画匹配"** ⇒ **T-pose**
⇒ **⇒ 两个不同的回答** ⇒ **可能取决于路径**
```

**⚠ 一个**需要标注的矛盾**。

### 4.5 而**"用排除法确定它"**

```php
// By elimination it is that commit -- the other three in the
// range only run AFTER match completion, and the FIRST death of a match
// failed too -- and the only part of it that runs before a death is
// this struct getting bigger.
```

**⇒ 八层**：
```text
1. **用排除法【就是那个提交**】**
2. ⇒ **那个范围内的另外三个【只在比赛完成之后**】跑**
3. ⇒ **而【一场比赛的第一次死亡也失败了**】**
4. ⇒ **⇒ 所以【排除那三个**】**
5. ⇒ **⇒ 而它【在死亡之前跑的唯一部分**】就是【这个结构变大**】**
6. ⇒ **⇒ 所以【就是它**】
```

**✅ ⭐⭐ **"排除法"的一个完整实例** —— 与 §407 的"`24` 个 `r 2` 簇的第一个"**同族（**第二次"用排除法定因"）。

**⇒ 三层**：
```text
§407  **第一个簇没有 `N`** ⇒ 排除"出生触发"
§414  **零售 demo 显示 `eType 0`** ⇒ 排除"文件那一行有效"
§419  **第一次死亡也失败 ⇒ 排除"只在比赛后跑的三个提交"**
⇒ **⇒ 三次排除法**
```

**✅ ⭐ **一个"排除法"的三例表**。

## 五、**`SvWorldEventType` 的二十个值**

```text
1  ClientSpawned        11 SdPlantStarted
2  ClientDisconnected   12 SdPlantCancelled
3  WeaponSwitchStarted  13 SdBombPlanted
4  PlayerDamage         14 SdDefuseStarted
5  EntityTouch          15 SdDefuseCancelled
6  PlayerKilled         16 SdBombDefused
7  EntityDamage         17 SdBombExploded
8  EntityKilled         18 SdRoundEnded
9  SdBombPickedUp       19 WeaponChanged
10 SdBombDropped        20 ZmRoundTick
```

**⇒ 而 `ZmRoundTick` 的注释：**

```php
// A ONCE-A-SECOND HEARTBEAT FOR THE ZM ROUND DIRECTOR.
//
// The gametype script owns spawning -- every zm builtin is script-facing --
// but the script had no way to be woken. `codol.on` carries seventeen
// reactive events and no periodic one, so a round loop written in Lua could
// only ever run at map load, which is exactly the one-shot spawn 12.159 is
// about. Raised from stepActorEntities, which already runs every frame.
```

**⇒ 十层**：
```text
1. **给 zm 回合导演的【每秒一次的心跳**】**
2. ⇒ **gametype 脚本【拥有生成**】**
3. ⇒ **而【每一个 zm builtin 都是脚本面向的**】**
4. ⇒ **⇒ 但那个脚本【没办法被唤醒**】**
5. ⇒ **`codol.on` 携带【十七个反应式事件而没有周期性的**】**
6. ⇒ **⇒ 所以一个用 Lua 写的回合循环【只会在【地图加载时**】跑一次**
7. ⇒ **那正是 `12.159` 关于的【一次性生成**】**
8. ⇒ **⇒ 从 `stepActorEntities` 里发出**（**它已经每帧跑了**）
```

### 5.1 ⭐⭐⭐ **"十七个反应式事件而没有一个周期性的"**

**✅ 这是本报告里**最重要的一条"事件面缺一类"的发现**。**

**⇒ 三层**：
```text
`codol.on` ⇒ **十七个【反应式**事件**
缺：**一个周期性的**
⇒ **⇒ 所以【一个"循环"在脚本侧【无法表达**】**
```

**✅ 与 §410 的"`s 0201` 是零售每个模式都发而我们一个都不发"**同族（**第二次"一个缺失的信号"）。

**⇒ 三层**：
```text
§402  缺 `s 0201` ⇒ **dmz 客户端等 46 秒**
§419  缺一个周期性事件 ⇒ **Lua 只能在地图加载时跑一次**
⇒ **⇒ 两次"缺失的一类信号**】
```

**✅ ⭐⭐ **一个"缺一类而不是缺一个"的两例**。

**⚠ 而"从 `stepActorEntities` 里发出"⇒ **复用已有循环**。**

**✅ 与 §411 的"`travelWindow` 复用 `selfPose`"**同族（**第六次"复用已有路径"）。

## 六、**`SvSnapshotFrameValidationFailure` 的二十个值**

```text
None / SceneFlags / MapCenter / PlayerStateOrder / AnimationCommands
ClientOrder / ClientTeam / AgentOrder / AgentDomain / EntityOrder
ClientInfoOrder / Glass / PlayerClientCount / ClientInfoOwner / ClientInfoDomain
PlayerStateClientJoin / PlayerStateDomain / PlayerEntityJoin / PlayerEntityDomain
EntityDomain
```

**⇒ 而 `SvSnapshotWriteFailure` 的十四个值：**

```text
None / InvalidFrame / MissingPlayerState / InvalidBaselineFrame
MissingBaselinePlayerState / MapCenterMismatch / DeltaWithoutBaseline
BaselineInitializationWithBaseline / PlayerState / AnimationCommands
Clients / PacketEntities / ClientInfos / Glass / Overflow
```

**⇒ 五层**：
```text
1. **两套失败枚举**：验证（`20` 个）与写出（`14` 个）
2. ⇒ **而它们【各有 `Name()` 函数**】
3. ⇒ **⇒ 所以【每一个失败都有一个人可读的名字**】**
4. ⇒ **（`SV_SnapshotFrameValidationFailureName` / `SV_SnapshotWriteFailureName`）**
```

**✅ 与 §409 的"名字不是数字"**完全同族（**第三次"名字化"。

**⇒ 三层**：
```text
§409  `sdTeamName`/`sdBombPhaseName`/`sdRoundEndReasonName`
§419  `SV_SnapshotFrameValidationFailureName`/`SV_SnapshotWriteFailureName`/`SV_ClientThinkFailureStageName`
⇒ **⇒ 三处"枚举必须有名字**】
```

**✅ ⭐ **一个"枚举名字化"的三例**。

**⚠ 而 `PlayerClientCount` 正是 §418 的 `frameReject=player_client_count` ✓**

**⇒ 三层**：
```text
§418  `frameReject=player_client_count`
§419  `SvSnapshotFrameValidationFailure::PlayerClientCount`
⇒ **⇒ 同一个具名原因**
```

**✅ ⭐ **一个跨报告的闭合**。

### 6.1 而**`SvClientThinkFailureStage` 的三十五个值**

```text
None / NotPlaying / SpawnedThisFrame / NonIncreasingCommandTime
InvalidInputState / NativePmoveUnavailable / NativePmoveRejected
InvalidPmoveOutput / NativePlayerStateProjection / NativeCommandTimeMismatch
WeaponMovementRejected / InvalidWeaponMovementOutput / EntityStateConversion
PostConversionProjection / EntityStateDecode / PredictableEventDecode
ConvertedStateMismatch / ClientEventsUnsupported / ClientEventsRejected
FinalProjection / FinalStateMismatch / InvalidClientImpacts
NativeEntityMirrorUnavailable / NativePmoveInvalidBinding / NativePmoveInvalidCommand
NativePmoveWrongThread / NativePmoveReentrantCall / NativePmoveHandlerSlotBusy
NativePmoveAnimConditionInstallFailed / NativePmoveNonIncreasingCommandTime
NativePmoveSliceLimitExceeded / NativePmoveCommandTimeNotAdvanced
NativePmoveNativeException / NativePmoveHandlerRestoreFailed
NativePmoveTraceFailed / NativePmoveAnimConditionRestoreFailed
NativePmoveInvalidOutput
```

**⇒ 三十七个值。**

**✅ 与 §404 的"`SV_ShouldDiscardRejectedUserCmd` 列出六种"**完全闭合 ✓

**⇒ 三层**：
```text
§404  六种：`ClientEventsRejected` / `NativePmoveNativeException` / `WeaponMovementRejected` / `NonIncreasingCommandTime` / `NativePmoveNonIncreasingCommandTime` / `NativePmoveInvalidCommand`
§419  全部 `37` 个中有 `6` 个是"可丢弃"
⇒ **⇒ 所以【六比三十七**】
```

**✅ ⭐ **一个"三十七分之六"的精确比例**。

**⚠ 而"`NativePmove*` 有 `15` 个"⇒ **一个子系统占了 `40%`**。**

**⇒ 三层**：
```text
`NativePmove*` ⇒ **`15` 个失败阶段**
其余 ⇒ **`22` 个**
⇒ **⇒ 所以【原生 pmove 是最脆弱的子系统**】
```

**✅ ⭐ **一个"失败阶段分布"的观察**。

## 七、**`SvHealthRegenState` 的"搬出去"理由**

```cpp
// What regen needs to know per client, and it is deliberately NOT on
// SvGameClient -- same reason noclipHoldUntil_ is not: that struct is
// copied whole every think and its offset 0 is load-bearing for the native
// pointer obfuscation, and growing it is already recorded as having broken
// death-animation selection once (2026-08-24, the killcam fields).
```

**⇒ 六层**：
```text
1. **故意【不在 `SvGameClient` 上**】**
2. ⇒ **与 `noclipHoldUntil_` 不是同一个理由**（**等价的理由**）
3. ⇒ **那个结构【每次 think 都被整个拷贝**】**
4. ⇒ **而它的【偏移 `0` 是承重的**】**
5. ⇒ **⇒ 而【增长它已经被记录为破坏过死亡动画选择一次**】（`2026-08-24`，killcam 字段）
6. ⇒ **⇒ 所以【任何新增状态都搬到兄弟结构**】**
```

**✅ 与 §418 的 `SvHoldBreathState`**完全同族（**第二次"搬出去"）。

**⇒ 三层**：
```text
§418  `SvHoldBreathState` ⇒ `playerState +0x298` 的状态
§419  `SvHealthRegenState` ⇒ 恢复状态
§417  `SvKillcamReplayPose` ⇒ 回放位姿
⇒ **⇒ 三次"搬到兄弟结构**】
```

**✅ ⭐⭐ **一个"搬家"的三例表**。

## 八、关键结论

1. **⭐⭐⭐ "那个参数不是伤害：伤害坐在位 `5`，所以一次 `12` 点的坠落读成 `384` 或更多"** —— 而**四条指令就是整个规格**（`shr 12` / `and 1` / `shl 7` / `or damage` / `shl 5` / `or surfaceType`）。
2. **⭐⭐⭐ 位 `12` 的来源**：`bit12 << 7` 然后整体 `shl 5` ⇒ **`7 + 5 = 12`** ⇒ **那个 `shl 7` 是为了补偿后面的 `shl 5`**（我逐指令推导）。
3. **⭐⭐ "`7` 位恰好够，因为曲线助手的上限是一个字面量 `100`"** ⇒ **`100 < 128`**，而**若上限是 `128` 就会溢出到 `bit 12`（与软表面标志冲突）** ⇒ **位宽与上限是一个协同设计**。
4. **⭐⭐⭐ "`EV_LANDING_HARD` 在 `0x00416AB4` 同样的打包（强度夹到 `24`，上移 `5`，在同一个表面索引之上）—— 那就是说这个布局是一个【约定】而不是一个巧合"`** —— 第六次"两个数同值 ⇒ 同物"，也是"用重复的形状证明约定"。
5. **⭐ "两个自动抑制在同一个尾部，而 pmove 在事件存在之前就应用它们 ⇒ 这个服务器不必检查"`** —— 上游已过滤。
6. **⭐⭐⭐ "零售取走的比那少一：`15` 次落地全部移动了【打包伤害减一】（`34→33`、`31→30`、`25→24`、`2→1`），而 `2→1` 那一个是【承重的样本】，因为玩家在 `71` 生命上而不是 `100`，所以『他其实在 `101`』不能解释那个差"`** —— 第四次"例外定案"。
7. **⭐⭐ "那个差在【应用侧】而不在这个解码的打包里"**：`PM_CrashLand` 的曲线助手与另一条覆写曲线**两处都没有加一**。
8. **⭐⭐⭐ "一个略低于 `1` 的乘数拟合同样那 `15` 个样本（最大的落差是 `34`，不足以分开它们）⇒ 所以写成【拟合的更简单的规则】，而那个语料被命名了，所以一个【更大的坠落可以在以后定案】"`** —— 第二次"可证伪条件"。
9. **⭐⭐⭐ 健康恢复的两个数（`delay 5000 ms`、`200 hp/s`）在【两个相距十八个月、一个 gametype 的 demo】上一致**，而**零售的步长是每 `100 ms` 帧 `+20` 生命**（`200 hp/s` 的来源）。
10. **⭐⭐⭐ "速率表示为【绝对生命每秒】而不是 `maxHealth` 的一个分数，因为每一个被测量的生命都是 `maxHealth = 100` ⇒ 两个模型不可区分 ⇒ 选【那个不发明一个证据无法支撑的依赖】的"`** —— 奥卡姆剃刀的精确应用。
11. **⭐ `healthAtDamage` 必须是 `uint32`**：有符号会在指定初始化器里成为**窄化转换**，而在花括号列表里那是 **ill-formed 不是警告**。
12. **⭐⭐⭐ "原生缓冲放在最前面，这样没有别的东西能移动它"**：CODOL 把函数指针存成 **`key ^ function ^ 那个配对槽【自己的地址】`** ⇒ **移动地址就是移动那个混淆所键控的东西**。
13. **⭐⭐⭐ `2026-08-24` 的完整病历**：为 killcam 加了四个 `playerState` 成员 ⇒ **`durationMs` 从 `2250` 到 `-1`，"没有动画匹配"，每一次死亡 T-pose**；**用排除法确定**（范围内的另外三个只在比赛完成之后跑，而**第一次死亡也失败**）⇒ **唯一在死亡之前跑的就是这个结构变大**。
14. **⭐⭐⭐ "偏移 `0` 不能移动；下面的 `static_assert` 就是【让那成为一条规则而不是声明顺序的一个意外】"`** —— 第三次"规则的可执行化"（运行时 Python / 运行时 Python / **编译时 `static_assert`**）。
15. **⭐⭐ `ZmRoundTick` 的"十七个反应式事件而没有一个周期性的"**：**一个用 Lua 写的回合循环只能在地图加载时跑一次** ⇒ **从 `stepActorEntities`（已经每帧跑）里发出** —— 第二次"缺一类而不是缺一个"。
16. **⭐ 两套失败枚举（`20` 个验证 + `14` 个写出）各有 `Name()` 函数**，而 `SvClientThinkFailureStage` 有 **`37` 个值**（其中 **`6` 个是可丢弃的**，与 §404 的 `SV_ShouldDiscardRejectedUserCmd` 闭合）；**`NativePmove*` 占 `15` 个 = `40%`** ⇒ **原生 pmove 是最脆弱的子系统**。
17. **`PlayerClientCount` 与 §418 的 `frameReject=player_client_count` 闭合**（一个具名原因）。
18. **⭐⭐ `SvHealthRegenState` 的"搬出去"**：**`SvGameClient` 每次 think 被整个拷贝，偏移 `0` 承重，而增长它已记录为破坏过死亡动画一次** ⇒ **与 `SvHoldBreathState`/`SvKillcamReplayPose` 同一模式**（第三次"搬家"）。

## 九、未闭合点

- `SvLandingPainDamageMask = 0x7F` 与 `<<5` 的完整解码（`7` 位）。
- `durationMs = -1` 在 §388（"死亡瞬时"）与 §419（"T-pose"）两处的差异。
- `codol.on` 的十七个反应式事件的清单。
- `SvClientPrediction` 的 `3277423512` 精确浮点值（我算得约 `-212`，注释说 `-217.5`）。
- `SvSnapshotFrameValidationFailure::Glass` 与 `SvSnapshotWriteFailure::Glass` 的区别。
- `sv_snapshot_mp.hpp` 2960 行之后未读取（**共 `4703` 行**）。
