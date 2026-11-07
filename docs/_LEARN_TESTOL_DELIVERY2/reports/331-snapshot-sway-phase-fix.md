# 331 · **`OLMOD_SWAY_PHASE` —— "狙击镜抽搐"的真正修复**、`3.0` 的两次推进、`2.5` 的甲方折中

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 3586–3790 行。

## 二、**`lastChangedField` 的两次编码**（本组第二重要）

```cpp
message.MSG_WriteBits(lastChangedField, PlayerStateLastChangedBits);   // 写【1-based】
const auto lastChangedFieldIndex = lastChangedField ? lastChangedField - 1 : 0;  // 【转 0-based】
```

### 2.1 三项

```text
① 写 `lastChangedField`（1-based）
② 而内部用 `lastChangedField - 1`（0-based）
③ `lastChangedField == 0` 时用 0
```

**✅ 与 §325/§330 的 1-based 编码一致。**

## 三、**`OLMOD_SWAY_PHASE` —— "狙击镜抽搐"的真正修复**（本组最重要的一段）

### 3.1 那段八层

```php
// ★★★ 28100 刀BI（第 7 项「狙击镜抽搐/拉回」，**改到快照写入处**）——
//   上一版（刀BF）我改在 `sv_native_playerstate_mp.cpp` 的 **native 往返校验**路径上，
//   导致 `client spawn REFUSED reason=native_round_trip_mismatch` ⇒ **无法出生**（P0，已回滚）。
//   正确落点是**这里**：这是"发给客户端的字段"，不参与 native 往返比对。
//   语义（既有结论）：field 4 是客户端 sway 相位种子；我方零生产者 ⇒ 每快照被种 0
//   ⇒ 摆动按快照率锯齿化 = 拉回/抽搐。这里给它一个**连续推进**的值：
//     每 client 记 `{lastCommandTime, phase}`；commandTime 回退 ⇒ 重播种为 commandTime；
//     dt∈(0,1000] 时 phase += dt × speed（speed 暂 1.0，武器 def 的 sway 字段未核实，不搬对方数字）。
//   开关 `OLMOD_SWAY_PHASE`，`=0` 恢复"原样直发"（A/B 判据：抽搐应复现）。
```

### 3.2 八层

```text
1. **刀BI（第 7 项「狙击镜抽搐/拉回」）改到快照写入处**
2. ⇒ 上一版（刀BF）改在 `sv_native_playerstate_mp.cpp` 的 **native 往返校验**路径上
3. ⇒ 导致 `client spawn REFUSED reason=native_round_trip_mismatch` ⇒ **无法出生**（**P0，已回滚**）
4. ⇒ **正确落点是这里**：这是"**发给客户端的字段**"，**不参与 native 往返比对**
5. **语义（既有结论）：field 4 是客户端 sway 相位种子**
6. ⇒ **我方零生产者 ⇒ 每快照被种 0 ⇒ 摆动按快照率锯齿化 = 拉回/抽搐**
7. ⇒ 这里给它一个**连续推进**的值：
     · 每 client 记 `{lastCommandTime, phase}`
     · `commandTime` 回退 ⇒ **重播种为 `commandTime`**
     · `dt ∈ (0, 1000]` ⇒ `phase += dt × speed`
8. ⇒ 开关 `OLMOD_SWAY_PHASE`，`=0` 恢复"原样直发"（**A/B 判据：抽搐应复现**）
```

### 3.3 **"field 4 是客户端 sway 相位种子"**

**✅ 与 §329 的"字段 4 是唯一能逃逸的 `changeHint==3` 字段，它的 codec 是 `-70`"**完全一致** ✓**

**⇒ 所以"字段 4"既是一个 `changeHint==3` 逃逸又是 sway 相位种子。**

### 3.4 而**"零生产者 ⇒ 每快照被种 0 ⇒ 按快照率锯齿化"**

**⇒ 三层**：

```text
1. 我们从不产出一个相位
2. ⇒ 每快照它被种 0
3. ⇒ **客户端每帧从 0 重新开始 ⇒ 锯齿 ⇒ 拉回/抽搐**
```

**✅ 一个**精确的机制**。**

**⇒ 与 §324 的"两个事件写入器不能合并"、§328 的"`changeHint==3` 从不到达值比较"同族**（第二十七次）。

### 3.5 而**"改在 native 往返校验路径上导致 P0 无法出生"**

**⇒ 三层**：

```text
1. 上一版改在 `sv_native_playerstate_mp.cpp` 的**往返校验**路径
2. ⇒ `client spawn REFUSED reason=native_round_trip_mismatch`
3. ⇒ **无法出生**（**P0**）
4. ⇒ 已回滚
```

**✅ 与 §326 的"把一个浮点当整数写破坏了一个正在工作的功能"同族**（第二十八次"改错地方"）。

### 3.6 而**"正确落点是这里：这是发给客户端的字段"**

**✅ 一个**精确的层次区分**：**

```text
native 往返校验路径    ⇒ 【内部一致性】检查
快照写入处              ⇒ 【发给客户端】的字段
```

**⇒ 所以"内部值"与"发出值"可以不同。**

**✅ 与 §315 的"`recordItemIds[0] = characterItemId` 的强制在两处"同族。**

## 四、**`produceSwayPhase` 的完整实现**（本组核心）

```cpp
static const auto produceSwayPhase = [](const auto &st) -> uint32
{
    static const bool enabled = [] {
        const auto *value = std::getenv("OLMOD_SWAY_PHASE");
        return !(value && std::string_view(value) == "0");
    }();
    if (!enabled) return st.unk04A4Time;              // ← 【原样直发】

    static std::unordered_map<uint32, uint32> lastCmd;
    static std::unordered_map<uint32, float> phase;
    const auto clientNum = (uint32)st.clientNum;
    auto &last = lastCmd[clientNum];
    auto &ph = phase[clientNum];

    if (last == 0 || st.commandTime < last)            // ← 【重播种】
    {
        last = st.commandTime;
        ph = (float)st.commandTime;
        return (uint32)ph;
    }
    const auto delta = st.commandTime - last;
    last = st.commandTime;
    if (delta == 0 || delta > 1000)                    // ← 【不推进】
        return (uint32)ph;

    constexpr float SwaySpeed = 2.5f;
    ph += (float)delta * SwaySpeed;
    return (uint32)ph;
};
```

### 4.1 六层

```text
① 开关（默认开）
② 关闭 ⇒ 原样直发 `st.unk04A4Time`
③ 两个按 clientNum 的静态 map（`lastCmd` / `phase`）
④ `last == 0` 或 `commandTime` 回退 ⇒ **重播种为 `commandTime`**
⑤ `delta == 0` 或 `delta > 1000` ⇒ **不推进**
⑥ 否则 `ph += delta * 2.5`
```

### 4.2 而**"重播种为 `commandTime`"**

**⇒ 三层**：

```text
1. 一个会话开始时（`last == 0`）⇒ 相位 = `commandTime`
2. ⇒ **所以相位从一个绝对时间开始**
3. ⇒ 而 `commandTime` 回退（重生）时也重播种
```

**✅ 一个**确定性的起点**。**

### 4.3 而 `delta > 1000` 的**上界**

**⇒ 三层**：

```text
1. 一个超过 1 秒的间隔 ⇒ **不推进**
2. ⇒ 防止一个卡顿后的**巨大跳变**
3. ⇒ 但相位保持（不重播种）
```

**⚠ 而"保持"与"重播种"不同。**

### 4.4 而 `SwaySpeed = 2.5f`

**⇒ 而 §331 后面的注释说从 1.0 到 3.0 再到 2.0 再到 2.5。**

## 五、**`3.0` 的两次推进**（本组第三重要）

### 5.1 那段

```php
// ★★ 2026-10-18（会话 28360 / 第 1 项）——**速率 1.0 -> 3.0**。
//   2697 原生 `codol_sway_phase.c` 实测：C1 每个重放 usercmd 推进**两次**，
//     第一次 `phase += breath*dt*speed`（需要 def[0x694]!=0 且 posFrac!=0）
//     第二次 `phase += dt*speed`（**无门、无 breath 缩放**）
//   ⇒ 开镜且不屏息时有效速率 = speed*(1+1)=3.0/ms（speed=1.5）。
//   我方原来用 1.0 ⇒ 幅度只有 1/3、周期 3 倍 ⇒ 看得见"在动"但仍是慢速抽搐。
//   这里取 3.0（实测值），屏息分支未做（需要 holdBreathScale，客户端侧量）。
```

### 5.2 七层

```text
1. **速率 1.0 → 3.0**
2. ⇒ 2697 原生 `codol_sway_phase.c` 实测：**C1 每个重放 usercmd 推进两次**
3. ⇒ 第一次 `phase += breath*dt*speed`（**需要 `def[0x694] != 0` 且 `posFrac != 0`**）
4. ⇒ 第二次 `phase += dt*speed`（**无门、无 breath 缩放**）
5. ⇒ **开镜且不屏息时有效速率 = `speed × (1+1) = 3.0/ms`（`speed = 1.5`）**
6. ⇒ 我方原本用 1.0 ⇒ **幅度只有 1/3、周期 3 倍** ⇒ **看得见"在动"但仍是慢速抽搐**
7. ⇒ 这里取 **3.0**（实测值），**屏息分支未做**（需要 `holdBreathScale`，客户端侧量）
```

### 5.3 **"两次推进"是关键**

**⇒ 三层**：

```text
1. 每个重放 usercmd 推进**两次**
2. ⇒ 第一次带 breath 缩放，第二次无
3. ⇒ **所以有效速率是 `speed × 2`**
```

**✅ 一个**精确的机制**。**

### 5.4 而"**我方原来 1.0 ⇒ 幅度 1/3、周期 3 倍**"

**⇒ 三层**：

```text
1. 1.0 vs 3.0
2. ⇒ **幅度只有 1/3**
3. ⇒ **周期 3 倍**
4. ⇒ **看得见"在动"但仍是慢速抽搐**
```

**✅ 与本文件反复的"看起来对但实际错"同族。**

## 六、**`2.0` 与 `2.5` 的甲方折中**（本组第四重要）

### 6.1 那段

```php
// ★ 2026-10-18（会话 28380）：甲方要求试 2.0（3.0 仍偏快/偏抽）。
//   2697 实测开镜 3.0/ms，但那是 speed=1.5 的武器；我方拿不到每武器 sway speed，
//   2.0 是"两次加"折中（等于 speed≈1.0 档），由甲方实机定夺。
// 28500: 2.0 -> 2.5 at the operator's request. `float`, so the
// fraction is carried exactly; the phase is a float internally and
// only truncates on the wire cast, which happens once per frame.
constexpr float SwaySpeed = 2.5f;
```

### 6.2 五层

```text
1. **甲方要求试 2.0**（3.0 仍偏快/偏抽）
2. ⇒ 2697 实测开镜 **3.0/ms**，但**那是 `speed = 1.5` 的武器**
3. ⇒ **我方拿不到每武器 sway speed**
4. ⇒ **2.0 是"两次加"折中**（等于 `speed ≈ 1.0` 档），**由甲方实机定夺**
5. **28500：2.0 → 2.5 按甲方要求**
```

### 6.3 而**四个速率的完整历史**

```text
1.0     初始（幅度 1/3）
3.0     按 2697 实测
2.0     甲方说 3.0 仍偏快
2.5     甲方再调
```

**✅ 四次调整 —— 与 §237 的"同一个常量被改了三次"同族。**

### 6.4 而"**`float`，所以分数被精确携带**"

**⇒ 三层**：

```text
1. `phase` 内部是 `float`
2. ⇒ **所以分数被精确携带**（不会每次截断累积误差）
3. ⇒ **只在线的 cast 时截断，而那是每帧一次**
```

**✅ 一个**正确的精度处理**。**

**⇒ 与 §259 的"`definition` 的 `std::trunc`"不同 —— 那里每次截断。**

## 七、`writePlayerStateFieldIndex` 的**首项用 `-1`**

```cpp
std::int32_t lastFieldIndex = -1;
if (commandTimeChanged)
{
    writePlayerStateFieldIndex(message, 0, lastFieldIndex);
    writeCommandTime(message, state.commandTime, serverTime);
}
```

**⇒ 三层**：

```text
1. `lastFieldIndex` 初值 **-1**
2. ⇒ 所以写字段 0 时 `delta = 0 - (-1) = 1`
3. ⇒ **走"连续"分支（一个 1 位）**
```

**✅ 一个**精确的初始化**（使第 0 个字段最便宜）。**

## 八、**字段 8/10/11 是 origin 的三个分量**

```cpp
if (sendOrigin)
{
    writePlayerStateFieldIndex(message, 8, lastFieldIndex);
    writeRawFloatDelta(message, state.origin[0]);
}
...
if (sendOrigin)
{
    writePlayerStateFieldIndex(message, 10, lastFieldIndex);
    writeRawFloatDelta(message, state.origin[2]);
    writePlayerStateFieldIndex(message, 11, lastFieldIndex);
    writeRawFloatDelta(message, state.origin[1]);
}
```

### 8.1 而**三个索引是 8、10、11**

```text
8    origin[0]   （X）
10   origin[2]   （Z）
11   origin[1]   （Y）
```

**⚠ **Y 是 11 而 X 是 8** ⇒ **Y 在最后**。**

**⚠ 与 §330 的"velocity 的 Y(13) 在 X(14) 前"**不同**。**

**⇒ 所以 `origin` 的顺序是 X、Z、Y 而 `velocity` 是 Y、X、Z。**

**✅ 两个不同的顺序（每字段自己的）。**

### 8.2 而 `writeRawFloatDelta(message, state.origin[0])` **无基线**

**⇒ 三层**：

```text
1. 三个 origin 都用 `writeRawFloatDelta`（**无 baseline 参数**）
2. ⇒ 所以 `baseline = 0.0f`（默认）
3. ⇒ **所以是裸值**
```

**✅ 与 §327 的"`origin` 是 `changeHint==3` ⇒ 发裸值"**完全一致** ✓**

## 九、`writeUnsignedDelta(..., 32)` 与 `writeSignedDelta(..., 8)`

```cpp
if (pmFlagsChanged)
    writeUnsignedDelta(message, state.pmFlags, baselinePmFlags, 32);    // 32 位

if (sendMovementDir)
    writeSignedDelta(message, state.movementDir, 0, 8);                 // 8 位，基线 0
```

### 9.1 而 `pmFlags` 用 **32 位**

**✅ 与 §254 的"`pm_flags=aiming?0x10:0`"配合 —— 32 位掩码。**

### 9.2 而 `movementDir` 用 `writeSignedDelta(..., 0, 8)`

**⇒ 三层**：

```text
1. `writeSignedDelta`（**有符号**）
2. ⇒ 8 位
3. ⇒ 基线 **0**
```

**⚠ 而 `movementDir` 是**角度**（0..255 或 -128..127）？**

**⇒ 用有符号 ⇒ 所以它是**-128..127**。**

**✅ 与 §318 的"`CorpseMovementDirField = 35; // +0x05C -8`"（codec -8）配合 —— 8 位有符号。**

## 十、**`writeUnsignedDelta(..., 6)` 与 `12`**

```cpp
if (weaponStateChanged[0])
    writeUnsignedDelta(message, state.weaponState[0], baselineWeaponState[0], 6);   // 6 位

if (legsAnimChanged)
    writeUnsignedDelta(message, state.legsAnim, baselineLegsAnim, 12);               // 12 位

if (weaponAnimChanged[0])
    writeUnsignedDelta(message, state.weaponAnim[0], baselineWeaponAnim[0], 12);     // 12 位
```

### 10.1 而 **`weaponState` 6 位而 `anim` 12 位**

**✅ 与 §318 的"`CorpseLegsAnimField = 9; // +0x0DC 12`"（**12 位**）配合。**

**⇒ 所以动画索引是 12 位（0..4095）。**

## 十一、`writeAngle16` 用于**两个视角分量**

```cpp
if (viewAngleChanged[1]) { ... writeAngle16(message, state.viewAngles[1]); }   // yaw
if (viewAngleChanged[0]) { ... writeAngle16(message, state.viewAngles[0]); }   // pitch
```

**⇒ 两个用 16 位角度。**

**⚠ 而 `viewAngleChanged[2]`（roll，字段 29）**不在本段**。**

**⇒ 待读。**

## 十二、关键结论

1. **`lastChangedField` 的 1-based 写与 0-based 内部用量。**
2. **⭐ `OLMOD_SWAY_PHASE` —— "狙击镜抽搐"的真正修复**：field 4 是 sway 相位种子。
3. **"零生产者 ⇒ 每快照被种 0 ⇒ 按快照率锯齿化 = 拉回/抽搐"**。
4. **"改在 native 往返校验路径导致 P0 无法出生"** —— 一次已回滚的错误落点。
5. **"正确落点是这里：这是发给客户端的字段，不参与 native 往返比对"** —— 一个层次区分。
6. **`produceSwayPhase` 六层**（开关 / 原样直发 / 两个静态 map / 重播种 / 不推进 / 推进）。
7. **"重播种为 `commandTime`"** —— 确定性的起点。
8. **`delta > 1000` ⇒ 不推进但不重播种。**
9. **⭐ `3.0` 的来源：C1 每个重放 usercmd 推进**两次**（一次带 breath、一次无）。**
10. **"我方原来 1.0 ⇒ 幅度 1/3、周期 3 倍 ⇒ 看得见在动但仍是慢速抽搐"**。
11. **四个速率的历史 1.0 → 3.0 → 2.0 → 2.5**（三次甲方调整）。
12. **"`float` 所以分数被精确携带，只在线的 cast 时截断"**。
13. **`lastFieldIndex` 初值 `-1` 使第 0 个字段最便宜。**
14. **`origin` 的三索引是 8(X)、10(Z)、11(Y)** —— 而 `velocity` 是 13(Y)、14(X)、16(Z)，**两个不同顺序**。
15. **三个 `origin` 用 `writeRawFloatDelta` 无基线** ⇒ 裸值。
16. **`pmFlags` 32 位**；**`movementDir` 用 `writeSignedDelta(..., 0, 8)`** 有符号。
17. **`weaponState` 6 位而 `anim` 12 位**。
18. **`writeAngle16` 用于 yaw 与 pitch**。

## 十三、未闭合点

- `viewAngleChanged[2]`（roll，字段 29）的写入。
- `def[0x694]` 的确切语义。
- `holdBreathScale` 的来源（客户端侧）。
- `sv_snapshot_mp.cpp` 3790 行之后未读取（1.47 MB，进度 26%）。
