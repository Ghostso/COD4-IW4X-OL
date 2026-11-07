# 324 · **两个事件序列写入器不能合并**、`writeHudColor` 的三个特例、`8 → 0xFF` 的回绕分歧

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 2196–2400 行。

## 二、`writeAmmoClips` 的**六层**（本组第二重要）

```cpp
// ① 收集变化索引
std::array<size_t, 15> changedIndexes{}; size_t changedCount{};
for (index) if (ammoClips[index] != baseline[index]) changedIndexes[changedCount++] = index;

message.MSG_WriteBits(changedCount ? 1 : 0, 1);           // ② 任何变化位
for (changedIndex = 0; changedIndex < changedCount; ++changedIndex)
{
    const auto index = changedIndexes[changedIndex];
    message.MSG_WriteBits((int32)index, 4);              // ③ 【4 位索引】
    message.MSG_WriteBits(clip.clipIndex == -1 ? 0x7FF : clip.clipIndex, AmmoClipIndexBits);  // ④ 11 位
    for (hand = 0; hand < clip.count.size(); ++hand)     // ⑤ 【双手计数】
    {
        const auto countChanged = clip.count[hand] != baselineClip.count[hand];
        message.MSG_WriteBits(countChanged ? 1 : 0, 1);
        if (countChanged) message.MSG_WriteBits(clip.count[hand], 9);   // 【9 位】
    }
    message.MSG_WriteBits(changedIndex + 1 < changedCount ? 1 : 0, 1);  // ⑥ 继续位
}
```

### 2.1 六层

```text
① 收集变化索引（最多 15 个）
② 一个"有任何变化"位
③ 每项 【4 位索引】
④ 【11 位】clipIndex
⑤ 【双手计数】各一个变化位 + 9 位值
⑥ 一个"还有下一个"位
```

### 2.2 而 **`clip.clipIndex == -1 ? 0x7FF : clip.clipIndex`**

```php
// CODDIFF(1649370): eleven bits, not 3.3.3.3's ten. MEASURED
// on the wire rather than transcribed: mining this field out
// of 6160/6160 real retail snapshots gives values up to 1297,
// which ten bits cannot express at all. The absent-clip
// sentinel is all-ones at the field width, so it widens with
// it (3.3.3.3 reads 1023 back as -1). That last part is by
// symmetry, not measurement -- no real server in the corpus
// ever sends the sentinel, because it simply omits the slot.
```

### 2.3 七层

```text
1. **十一位而不是 3.3.3.3 的十位**
2. ⇒ **在线上测量而不是转写**：从 6160/6160 个真实零售快照挖出这个字段**给出值高达 1297**，而**十位根本无法表达**
3. ⇒ **无弹匣哨兵是字段宽度上的全一** ⇒ **所以它跟着变宽**
4. ⇒ **（3.3.3.3 把 1023 读回为 -1）**
5. ⇒ **那最后一部分是【由对称性】而不是【由测量】**
6. ⇒ 因为**语料里没有一个真实服务器曾发过那个哨兵**
7. ⇒ 因为**它干脆省略那个槽**
```

### 2.4 **"由对称性而不是由测量"**

**✅ 一个**精确的知识来源标注**。**

**⇒ 与本文件反复的"测量 vs 推断"区分一致**（第二十次）。

### 2.5 而 `1297` 与 `1188`

**⇒ 与 §240 的"ammo indexes up to 1188 and clip indexes up to 1297"**完全一致** ✓**

**⇒ 所以 `clipIndex` 最大 1297 而 `ammoIndex` 最大 1188。**

### 2.6 而"**语料里没有一个真实服务器曾发过那个哨兵**"

**⇒ 三层**：

```text
1. 哨兵是 `0x7FF`（全一）
2. ⇒ 而**没有一个真实服务器发过**
3. ⇒ 因为**它省略那个槽**
```

**✅ 所以 `0x7FF` 是一个**从未被观测到**的值。**

**⚠ 而它是**由对称性**推导的。**

## 三、`writeAmmoPools` 的**三处差异**

```php
message.MSG_WriteBits((int32)index, 4);
// CODDIFF(1649370): 11 and 12 bits, not 3.3.3.3's 10 and 11.
// The index width is MEASURED -- real snapshots carry ammo
// indexes up to 1188. The count width is transcribed from
// this build's reader; the corpus only reaches 225, so the
// wire does not pin it on its own, but the whole section
// decodes to the exact endpoint 6160/6160 times with it.
message.MSG_WriteBits(pool.ammoIndex, AmmoPoolIndexBits);     // 11 位
message.MSG_WriteBits(pool.count, AmmoPoolCountBits);         // 12 位
```

### 3.1 三层

```text
1. **11 与 12 位，不是 3.3.3.3 的 10 与 11**
2. ⇒ **索引宽度是【测量过的】** —— 真实快照携带 ammo 索引**高达 1188**
3. ⇒ **而计数宽度是从这个 build 的读取器【转写】的**
4. ⇒ 因为**语料只达到 225** ⇒ **所以线本身不能钉住它**
5. ⇒ **但整段用它能精确解码到端点 6160/6160 次**
```

### 3.2 **"线本身不能钉住它但 6160/6160 的解码能"**

**✅ 一个**间接的验证**（通过完整解码而不是单个字段的值域）。**

**⇒ 与 §321 的"界是线的宽度"**互补 —— 那里用宽度而这里用**整段解码成功**。

### 3.3 而 `225` 是**语料里的最大计数**

**⇒ 而 12 位能到 4095。**

**⚠ 所以 225 与 4095 差了 18 倍。**

## 四、`writeObjectives` 的**六层**（本组第三重要）

```cpp
if (objectives == baseline) { message.MSG_WriteBits(0, 1); return; }
message.MSG_WriteBits(1, 1);
for (index = 0; index < 32; ++index)                       // ← 【32 个目标】
{
    message.MSG_WriteBits(objective.state, ObjectiveStateBits);   // 【3 位】
    const std::array<bool, ObjectiveProducedFieldCount> changed{   // 【六个】
        objective.origin[0] != old.origin[0],
        objective.origin[1] != old.origin[1],
        objective.origin[2] != old.origin[2],
        objective.icon != old.icon,
        objective.entityNum != old.entityNum,
        objective.teamNum != old.teamNum,
    };
    const auto lastChanged = std::ranges::find_last(changed, true);
    if (lastChanged.empty()) { message.MSG_WriteBits(0, 1); continue; }
    message.MSG_WriteBits(1, 1);
    message.MSG_WriteBits((uint32)(lastChanged.begin() - changed.begin()), ObjectiveLastChangedBits);  // 4 位
    std::int32_t lastFieldIndex = -1;
    for (field = 0; field < changed.size(); ++field)
    {
        if (!changed[field]) continue;
        writeObjectiveFieldIndex(message, field, lastFieldIndex);      // 一元编码
        switch (field) { ... }
    }
}
```

### 4.1 六层

```text
① 整体相等 ⇒ 一个 0 位
② 否则 ⇒ 一个 1 位
③ 每个目标【3 位 state】
④ 【六个变化位】
⑤ `find_last` ⇒ 【4 位 lastChanged】
⑥ 一元索引 + 字段值
```

### 4.2 而**目标数 32 而字段 6**

```text
32 个目标槽
6 个产出字段
```

**⚠ 而 §316 的 `ObjectiveFieldCount = 9`**（表有 9 个）。**

**⇒ 三个数：`32`（槽）、`9`（表字段）、`6`（产出字段）。**

**✅ 与 §316 的 `ObjectiveProducedFieldCount = 6` 一致。**

### 4.3 而 `ObjectiveStateBits = 3`

**⇒ 与 §316 的 `ObjectiveStateBits = 3`**一致** ✓**

### 4.4 而 `writeFullFloatDelta` 用于**三个 origin**

```cpp
case ObjectiveOriginXField:
case ObjectiveOriginYField:
case ObjectiveOriginZField:
    writeFullFloatDelta(message, objective.origin[field], old.origin[field]);
    break;
```

**⇒ 三个都用**全浮点**（33 位每个）。**

**⇒ 所以一个 origin 变化是 `3 × 33 = 99` 位。**

**⚠ 昂贵但精确。**

### 4.5 而 `writeUnsignedDelta` 的**三个不同宽度**

```text
icon         12 位
entityNum    11 位
teamNum       4 位
```

**✅ 与 §316 的 `ObjectiveIconField`（12 位？）/ `entityNum`（11）/ `teamNum`（4）配合。**

**⚠ 而 §316 只说 `ObjectiveIconField = 3` 而没说宽度。**

**⇒ 这里给出了 `12`。**

## 五、`writeHudColor` 的**三个特例**（本组第四重要）

### 5.1 那段

```cpp
void writeHudColor(MsgWriter &message, uint32 value, uint32 baseline)
{
    const auto rgb = value & 0x00FFFFFFu;
    const auto baselineRgb = baseline & 0x00FFFFFFu;
    const auto alpha = (uint8)(value >> 24);
    const auto baselineAlpha = (uint8)(baseline >> 24);
    if (rgb == baselineRgb &&
        ((alpha == 0 && baselineAlpha != 0) ||
            (alpha == 0xFF && baselineAlpha == 0)))
    {
        message.MSG_WriteBits(1, 1);      // ← 【特例：一个 1 位】
        return;
    }

    message.MSG_WriteBits(0, 1);
    const auto rgbUnchanged = rgb == baselineRgb;
    message.MSG_WriteBits(rgbUnchanged ? 1 : 0, 1);
    if (!rgbUnchanged)
    {
        message.MSG_WriteBits(1, 1);
        message.MSG_WriteByte((uint8)value);
        message.MSG_WriteByte((uint8)(value >> 8));
        message.MSG_WriteByte((uint8)(value >> 16));
    }
    message.MSG_WriteBits(alpha == 0xFF ? 31 : alpha / 8, 5);   // ← 【5 位 alpha】
}
```

### 5.2 五层

```text
① 【RGB 相同】且【alpha 从非零变 0】⇒ 一个 1 位（【全透明】特例）
② 或【RGB 相同】且【alpha 从 0 变 0xFF】⇒ 一个 1 位（【全不透明】特例）
③ 否则 ⇒ 一个 0 位
④ 然后 RGB 变化位（1 位）+ 若变化则三个字节
⑤ 【5 位 alpha】：`0xFF` ⇒ `31`，否则 `alpha / 8`
```

### 5.3 而**两个特例的语义**

```text
alpha: 非零 → 0        ⇒ 一个 1 位
alpha: 0 → 0xFF        ⇒ 一个 1 位
```

**⇒ 所以它们是**"完全透明"与"完全不透明"的捷径**。**

**⚠ 而其它 alpha 值都走 `alpha / 8`（量化到 5 位）。**

**⇒ 所以 `alpha == 0` 与 `alpha == 0xFF` 有**专位**。**

**✅ 一个**巧妙的压缩**（两个最常见的 alpha 值各占一个专用码）。**

### 5.4 而 `alpha / 8` 的**量化**

```text
alpha 0..255 ⇒ alpha/8 ⇒ 0..31
但 alpha == 0xFF ⇒ 31（与 alpha/8 = 31 相同！）
```

**⚠ `255 / 8 = 31` 而 `0xFF` 也映射到 31。**

**⇒ 所以 `alpha = 248..255` 都映射到 31。**

**⚠ 而 `alpha == 0xFF` 的**特例**路径只在内层的 `if` 里，与 `alpha/8` 的 31 的**结果相同**。**

**⇒ 所以 `alpha == 0xFF` 的特例只在**第一个 `if`**（RGB 相同时）有意义。**

**✓ 正确。**

### 5.5 而三个字节的**顺序**

```cpp
message.MSG_WriteByte((uint8)value);           // R
message.MSG_WriteByte((uint8)(value >> 8));    // G
message.MSG_WriteByte((uint8)(value >> 16));   // B
```

**⇒ 所以是**R、G、B**（低字节到高字节）。**

**✅ 与 `value & 0x00FFFFFF` 的 RGB 布局一致（低 24 位）。**

### 5.6 而 `(uint8)(value >> 24)` 是 **alpha**

**⇒ 所以 `0xAARRGGBB` 的布局。**

## 六、`writeHudFontScale` 的**"无变化前缀"**

```cpp
// CODREF: the -86 reader at 0x00C42EE5 takes six raw bits and divides
// by ten - no change prefix and no baseline, unlike every unsigned
// field around it. Writing a prefix bit here would desynchronise the
// rest of the elem.
void writeHudFontScale(MsgWriter &message, const float value)
{
    const auto clamped = std::clamp(value, 0.0f, HudElemFontScaleMaximum);
    const auto raw = (uint32)std::lround(clamped * HudElemFontScaleQuantum);
    message.MSG_WriteBits((int32)raw, HudElemFontScaleBits);
}
```

### 6.1 四层

```text
1. **`-86` 读取器在 `0x00C42EE5` 取六个原始位并除以十**
2. ⇒ **没有变化前缀也没有基线** —— **不同于它周围的每一个无符号字段**
3. ⇒ **在这里写一个前缀位会失步 elem 的其余部分**
4. ⇒ 所以只写 6 位
```

### 6.2 而**"会失步 elem 的其余部分"**

**✅ 与 §319 的"乱序字段失步整个快照"、§322 的"漏字段失步每一个槽"同族**（第二十一次）。

### 6.3 而 `lround` 与 `clamp`

```text
先 clamp 到 [0, 6.3]
然后 × 10 并 lround 到整数
⇒ 0..63
⇒ 6 位
```

**✅ 与 §317 的"6 位与十分之一 ⇒ 上限 6.3"**完全一致** ✓**

## 七、**两个事件序列写入器不能合并**（本组最重要的一段）

### 7.1 那段

```php
// The event-ring codecs. THE TWO CURSOR WRITERS ARE NOT THE SAME
// FUNCTION AND MUST NOT BE MERGED AGAIN. Both native cursors wrap at
// 256, but their proven wire arithmetic differs at 0xFF -> 0. The
// entity fixture takes codec -75's compact arm with modular byte
// subtraction. The playerstate reader at 0x67042C does not byte-mask
// that arm, so the same payload decodes as 256; its writer must use a
// non-modular delta and take the byte fallback at a wrap. Sharing the
// entity writer caused the live predicted-event repeat.
void writeEntityEventSequence(MsgWriter &message, uint8 value, uint8 baseline);
void writePlayerStateEventSequence(MsgWriter &message, uint32 value, uint32 baseline);
```

### 7.2 八层

```text
1. **两个游标写入器【不是】同一个函数而【绝不能】再被合并**
2. ⇒ **两个原生游标都在 256 处回绕**
3. ⇒ **但它们在 `0xFF -> 0` 处的【已证明的线算术】不同**
4. ⇒ **实体 fixture 取 codec `-75` 的紧凑分支用【模字节减法】**
5. ⇒ **而 `0x67042C` 的 playerstate 读取器【不】字节掩那个分支**
6. ⇒ **所以同一个载荷解码为 256**
7. ⇒ **它的写入器必须用【非模】delta 并在回绕时取字节回退**
8. ⇒ **共享实体写入器造成了实机的预测事件重复**
```

### 7.3 **"共享实体写入器造成了实机的预测事件重复"** —— 一个具体的后果**

**✅ 与 §319 的"`sameActorPacketEntity` 拒绝整个快照"、§324 的"失步 elem"同族**（第二十二次）。

### 7.4 而 `0xFF -> 0` 的**算术分歧**

```text
实体     delta = 0 - 0xFF = 1（模字节）
         ⇒ 1 位"连续"
player    delta = 0 - 0xFF = -255（非模）
         ⇒ 走"跳跃"或字节回退
```

**⚠ 所以同一个"1 变 0"在两个通道上编码**不同**。**

**⇒ 而解码端也各自不同 ⇒ 所以**必须两个写入器**。**

### 7.5 而 `writePlayerStateEventSequence` 用 **`uint32`** 而实体用 **`uint8`**

**⇒ 三层**：

```text
实体       uint8（0..255）
player     uint32（0..4G）
```

**⇒ 所以 player 的序列**不回绕**而实体的**回绕 256**。**

**⚠ 但注释说"两个原生游标都在 256 处回绕"。**

**⇒ 所以 `width` 是写入类型而**语义**仍回绕。**

## 八、关键结论

1. **`writeAmmoClips` 六层**：4 位索引 / 11 位 clipIndex / 双手计数 9 位 / 继续位。
2. **`clipIndex == -1 ⇒ 0x7FF`** —— 全一哨兵**跟宽度变宽**，而**那部分是"由对称性而非测量"**。
3. **"语料里没有一个真实服务器曾发过那个哨兵"** —— 它省略那个槽。
4. **`1297`（clip）与 `1188`（ammo）** 两个最大值。
5. **`writeAmmoPools` 的"11 与 12 位"**，而**计数宽度是转写的**（语料只到 225）。
6. **"线本身不能钉住它但 6160/6160 的整段解码能"** —— 一个间接验证。
7. **`writeObjectives` 的 32 槽 / 9 表字段 / 6 产出字段。**
8. **三个 origin 用 `writeFullFloatDelta`（33 位每个 ⇒ 99 位）。**
9. **三个标量的宽度**：icon 12 / entityNum 11 / teamNum 4。
10. **`writeHudColor` 的两个 alpha 特例**（非零→0 与 0→0xFF 各一个专用位）。
11. **`alpha / 8` 的量化到 5 位**，而 `alpha == 0xFF` 也映射到 31。
12. **RGB 的三个字节顺序是 R、G、B**（低字节到高字节），alpha 在高字节。
13. **`writeHudFontScale` 无变化前缀** —— 因为 `-86` 读取器直读 6 位。
14. **⭐ 两个事件序列写入器绝不能合并** —— `0xFF -> 0` 处的算术分歧（模字节 vs 非模）。
15. **"共享实体写入器造成了实机的预测事件重复"** —— 一个具体的后果。
16. **实体用 `uint8` 而 player 用 `uint32`。**

## 九、未闭合点

- `0x67042C` 的 playerstate 读取器的完整算术。
- `ObjectiveIconField` 的 12 位是否与 §316 一致。
- `writeSkippedFieldIndex` 与 `writeEntityOrigin` 的完整实现（前向声明）。
- `sv_snapshot_mp.cpp` 2400 行之后未读取。
