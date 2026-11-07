# 325 · **`50` vs `0x42480000`** —— "把浮点当整数读"的一次翻车、`writeHudElems` 的 42 项

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 2395–2600 行。

## 二、`writeHudElems` 的**结构**（本组第二重要）

```cpp
bool writeHudElems(MsgWriter &message,
    const std::array<SvHudElem, 31> &elems,
    const std::array<SvHudElem, 31> &baseline,
    const std::array<float, 3> &mapCenter,
    const uint32 serverTime)
{
    const auto count = (size_t)(find(elems, SvHudElemType::Free, &SvHudElem::type) - elems.begin());
    message.MSG_WriteBits((uint32)count, 5);          // ← 【5 位计数】
    for (index = 0; index < count; ++index) { ... }
}
```

### 2.1 而 **31 个槽而 5 位计数**

**⇒ 三层**：

```text
1. 数组是 **31** 个元素
2. ⇒ 而计数用 **5 位**（0..31）
3. ⇒ **恰好够**（31 是 5 位的最大值）
```

**✅ 算术精确。**

### 2.2 而 `find(elems, SvHudElemType::Free, &SvHudElem::type)`

**⇒ 找第一个 `Free` 类型 ⇒ 那就是"末尾"。**

**⇒ 所以 `Free` 是一个**终止哨兵**。**

**⚠ 与 §242 的 `addressable` 哨兵同族但这次是**枚举值**。**

### 2.3 而 `pulse` 的**五项条件**

```cpp
const auto pulse = [](const SvHudElem &value) {
    return (value.type == SvHudElemType::PlayerName || value.type == SvHudElemType::Text) &&
        value.fadeTime == 0 &&
        (value.fadeStartTime || value.materialIndex || value.width ||
            value.scaleStartTime || value.scaleTime);
};
```

**⇒ 三层**：

```text
① 类型是 PlayerName 或 Text
② fadeTime == 0
③ 五个字段【任一非零】
```

**⇒ 所以 `pulse` = "一个用普通字段复用成脉冲的 HUD 元素"。**

### 2.4 而那段注释

```php
// Player names and the outcome title use the five pulse-only
// descriptor rows 28..32. Localized text uses field 22
// for their localized text. Their unused ordinary fields are
// aliased so SvHudElem, and therefore the address-sensitive
// native WorldClientState node, does not grow. Project every
// view by type so a transition also clears the former view.
// OLMOD(factory-entry): fadeTime identifies an ordinary native
// color fade. A birth timestamp alone must not turn it into
// an outcome pulse; native Factory rows use fadeStart+fadeTime.
```

### 2.5 六层

```text
1. **玩家名与结局标题用五行【只用于脉冲】的描述符 28..32**
2. ⇒ **本地化文本用字段 22** 给它们的本地化文本
3. ⇒ **它们未用的普通字段被【别名化】** 以便 `SvHudElem`（以及**因此地址敏感的 `WorldClientState` 节点**）**不增长**
4. ⇒ **按类型投影每一个视图** 所以一个过渡**也会清空前一个视图**
5. ⇒ **`fadeTime` 标识一个普通的原生颜色淡出**
6. ⇒ **一个出生时间戳单独不能把它变成一个结局脉冲** —— **原生 Factory 行用 `fadeStart + fadeTime`**
```

### 2.6 **"字段被别名化以免 `SvHudElem` 增长"**

**✅ 与 §315/§318/§319 的"不能增大地址键控缓冲区"**同族**（第六次）。**

**⇒ 而这次的具体手法是**字段复用**（`fadeStartTime` 既是淡出起点又是脉冲的出生时间）。**

### 2.7 而 **13 个别名 lambda**

```cpp
const auto material      = [&pulse](v) { return pulse(v) ? uint16{} : v.materialIndex; };
const auto width         = [&pulse](v) { return pulse(v) ? uint16{} : v.width; };
const auto fadeStart     = [&pulse](v) { return pulse(v) ? uint32{} : v.fadeStartTime; };
const auto scaleStart    = [&pulse](v) { return pulse(v) || v.hasIconSizeAnimation() || v.isClock() ? uint32{} : v.scaleStartTime; };
const auto scaleDuration = [&pulse](v) { return pulse(v) || v.hasIconSizeAnimation() || v.isClock() ? uint16{} : v.scaleTime; };
const auto text          = [&hasTextField](v) { return hasTextField(v) ? v.label : uint16{}; };
const auto label         = [&hasTextField](v) { return hasTextField(v) || v.hasIconSizeAnimation() ? uint16{} : v.label; };
const auto hudValue      = [](v) { return v.hasIconSizeAnimation() ? 0.0f : v.value; };
const auto sizeStart     = [](v) { return v.hasIconSizeAnimation() ? v.scaleStartTime : 0u; };
const auto sizeTime      = [](v) { return v.hasIconSizeAnimation() ? v.scaleTime : 0u; };
const auto fromWidth     = [](v) { return v.hasIconSizeAnimation() ? (uint32)v.value : 0u; };
const auto fromHeight    = [](v) { return v.hasIconSizeAnimation() ? v.label : 0u; };
const auto fxBirth       = [&pulse](v) { return pulse(v) ? v.fadeStartTime : uint32{}; };
const auto fxSound       = [&pulse](v) { return pulse(v) ? v.materialIndex : uint16{}; };
const auto fxLetter      = [&pulse](v) { return pulse(v) ? v.width : uint16{}; };
const auto fxDecayStart  = [&pulse](v) { return pulse(v) ? v.scaleStartTime : uint32{}; };
const auto fxDecayDuration = [&pulse](v) { return pulse(v) ? v.scaleTime : uint16{}; };
```

**⇒ 十七个别名。**

**⇒ 而三组成员：**

```text
① pulse 组（material/width/fadeStart/scaleStart/scaleDuration/fxBirth/fxSound/fxLetter/fxDecayStart/fxDecayDuration）= 10 个
② hasTextField 组（text/label）= 2 个
③ hasIconSizeAnimation 组（hudValue/sizeStart/sizeTime/fromWidth/fromHeight）= 5 个
```

**✅ 三组复用。**

## 三、**42 项变化位**（本组第三重要）

```cpp
const std::array changed{
    elem.color != old.color,                             // 0
    elem.origin[1] != old.origin[1],                     // 1  ← 【Y 在 X 前】
    elem.origin[0] != old.origin[0],                     // 2
    elem.type != old.type,                               // 3
    material(elem) != material(old),                     // 4
    elem.height != old.height,                           // 5
    width(elem) != width(old),                           // 6
    elem.targetEntNum != old.targetEntNum,               // 7
    elem.origin[2] != old.origin[2],                     // 8
    hudValue(elem) != hudValue(old),                      // 9
    fadeStart(elem) != fadeStart(old),                    // 10
    elem.alignScreen != old.alignScreen,                  // 11
    elem.fromColor != old.fromColor,                      // 12
    elem.fadeTime != old.fadeTime,                        // 13
    elem.flags != old.flags,                              // 14
    elem.alignOrg != old.alignOrg,                        // 15
    elem.fontScale != old.fontScale,                      // 16
    scaleStart(elem) != scaleStart(old),                  // 17
    scaleDuration(elem) != scaleDuration(old),            // 18
    elem.fromFontScale != old.fromFontScale,              // 19
    elem.font != old.font,                                // 20
    elem.sort != old.sort,                                // 21
    text(elem) != text(old),                              // 22
    sizeStart(elem) != sizeStart(old),                    // 23
    sizeTime(elem) != sizeTime(old),                      // 24
    fromWidth(elem) != fromWidth(old),                    // 25
    fromHeight(elem) != fromHeight(old),                  // 26
    elem.glowColor != old.glowColor,                      // 27
    fxBirth(elem) != fxBirth(old),                         // 28
    fxSound(elem) != fxSound(old),                         // 29
    fxLetter(elem) != fxLetter(old),                       // 30
    fxDecayStart(elem) != fxDecayStart(old),               // 31
    fxDecayDuration(elem) != fxDecayDuration(old),         // 32
    label(elem) != label(old),                             // 33
    (elem.isClock()?elem.scaleStartTime:0u) != (old.isClock()?old.scaleStartTime:0u),  // 34
    false,false,false,false,false,false,                   // 35..40
    (elem.isClock()?elem.scaleTime:0u) != (old.isClock()?old.scaleTime:0u),  // 41
};
```

### 3.1 而 **42 项**

**⇒ `sizeof = 42` 与 §316 的 `HudElemFieldCount = 42`**完全一致** ✓**

### 3.2 而 **`elem.origin[1]` 在 `elem.origin[0]` 之前**

```text
索引 1 = origin[1]  (Y)
索引 2 = origin[0]  (X)
索引 8 = origin[2]  (Z)
```

**✅ 与 §316 的 `HudElemYField = 1` / `HudElemXField = 2` / `HudElemZField = 8`**完全一致** ✓**

**⇒ 所以**Y 在 X 前**是那个表的顺序。**

**⚠ 而 §318 的 `ScriptMover` 是 `7 = x, 5 = y, 8 = z`（X 在 Y 前）。**

**⇒ 两个表**不同的轴顺序**。**

**✅ 与 §318 的"§122 的轴陷阱"同族 —— 而这里是**每表自己的顺序**。**

### 3.3 而 **35..40 六项恒 `false`**

```text
35, 36, 37, 38, 39, 40
```

**⇒ 六项**永不变**。**

**⚠ 而 §316 的字段表里**也没有 34..41 的常量**（只有到 33 然后 14）。**

**⇒ 所以 34 与 41 是**后来加的**（`isClock` 的），而 35..40 是**保留未用**。**

### 3.4 而 `lastField + 1`

```cpp
message.MSG_WriteBits(lastField + 1, HudElemLastChangedBits);
```

**⇒ 三层**：

```text
1. 写的是 `lastField + 1` 而不是 `lastField`
2. ⇒ 因为 **0 表示"无变化"**
3. ⇒ 所以**编码是 1-based**
```

**✅ 与 §316 的 `HudElemLastChangedBits = 6`（0..63 而 42 项）配合。**

**⇒ 所以 `lastField + 1` 最多 42 而 6 位到 63。**

## 四、**`50` vs `0x42480000`** —— 把浮点当整数读（本组最重要的一段）

### 4.1 那段

```php
case HudElemValueField:
    // A FLOAT. THIS WAS BRIEFLY CHANGED TO AN INTEGER AND
    // THAT BROKE A WORKING FEATURE, so the reasoning is
    // written down rather than the conclusion.
    //
    // Decoding field 9 out of both demos showed retail's as
    // `50` and ours as `1112014848` (= 0x42480000, the bits
    // of float 50.0), and that was read as "retail sends the
    // integer". It is not: the client renders this field
    // with sprintf("%g", *(float *)&value), so writing the
```

**（后续待读）**

### 4.2 五层

```text
1. **这是一个浮点数**
2. ⇒ **它曾被短暂改成整数而那破坏了一个正在工作的功能**
3. ⇒ 所以**理由被写下来而不是结论**
4. ⇒ 从两个 demo 解码字段 9 显示**零售的 `50` 而我们的 `1112014848`（= `0x42480000`，float 50.0 的位）**
5. ⇒ **而那被读成"零售发的是整数"**
6. ⇒ **它不是**
7. ⇒ 因为**客户端用 `sprintf("%g", *(float *)&value)` 渲染这个字段**
```

### 4.3 **`0x42480000` 的算术**

**⇒ `float 50.0` 的 IEEE 754 位模式：**

```text
50.0 = 1.5625 × 2^5
符号 0
指数 5 + 127 = 132 = 0x84
尾数 1.5625 - 1 = 0.5625 = 0x900000 / 2^23 ... 
⇒ 0x42480000
```

**✅ 正确的 IEEE 754。**

### 4.4 而**"零售的 `50`"是解码器的显示而不是值**

**⇒ 三层**：

```text
1. 解码器把零售的值显示成 `50`
2. ⇒ 而把我们的显示成 `1112014848`
3. ⇒ **因为解码器在两个 demo 上用了【不同的解释】**
```

**⚠ 所以"两个不同的显示"是**解码器的不一致**而不是**编码的不同**。**

**✅ 一个**极隐蔽的误读**。**

### 4.5 而"**理由被写下来而不是结论**"

**✅ 与 §321 的"用测量清除而不是用论证"同族**（第二十三次）。

## 五、`writeUnsignedDelta` 的**五个字段宽度**

```cpp
case HudElemTypeField:       writeUnsignedDelta(..., 4);       // 4 位
case HudElemMaterialField:   writeUnsignedDelta(..., 10);      // 10 位
case HudElemHeightField:     writeUnsignedDelta(..., 10);      // 10 位
case HudElemWidthField:      writeUnsignedDelta(..., 10);      // 10 位
case HudElemTargetEntField:  writeUnsignedDelta(..., 11);      // 11 位
```

**⇒ 五种（其中三种是 10 位）。**

### 5.1 而 `writeEntityOrigin` 用于**三个 origin**

```cpp
case HudElemYField: if (!writeEntityOrigin(message, elem.origin[1], old.origin[1], mapCenter[1])) return false; break;
case HudElemXField: if (!writeEntityOrigin(message, elem.origin[0], old.origin[0], mapCenter[0])) return false; break;
case HudElemZField: if (!writeEntityOrigin(message, elem.origin[2], old.origin[2], mapCenter[2])) return false; break;
```

**⇒ 三项，各用**对应的 `mapCenter` 分量**。**

**⚠ 而 `writeEntityOrigin` 接受 `mapCenter` ⇒ 所以它**相对于地图中心**编码。**

**✅ 与 §318 的"领奖台人偶的 `5142.95, -1396.73, 22.00`"配合 —— 那些是**绝对**坐标而这里可能**相对**。**

**⇒ 待读 `writeEntityOrigin`。**

## 六、`writeSkippedFieldIndex` 的**四参数**

```cpp
writeSkippedFieldIndex(message, field, lastWrittenField, HudElemFieldSkipBits);
```

**⇒ 四项，其中第四个是 `HudElemFieldSkipBits = 3`。**

**⇒ 与 §323 的 `writePlayerStateFieldIndex` 的 4 位不同 —— 这里是**3 位**。**

**✅ 与 §316 的 `HudElemFieldSkipBits = 3` 一致。**

**⇒ 所以三个表三种间隔位宽：**

```text
playerState   4 位
objective     一元
hudElem       3 位
```

## 七、关键结论

1. **`writeHudElems` 的 31 槽而 5 位计数** —— 恰好够。
2. **`Free` 是终止哨兵**（`find` 找第一个 `Free`）。
3. **`pulse` 的五项条件**（类型 + `fadeTime == 0` + 五个字段任一非零）。
4. **"字段被别名化以免 `SvHudElem` 增长"** —— 第六次该约束，而手法是**字段复用**。
5. **17 个别名 lambda 分三组**（pulse 10 / hasTextField 2 / hasIconSizeAnimation 5）。
6. **42 项变化位**，与 `HudElemFieldCount = 42` 一致。
7. **`origin[1]`（Y）在 `origin[0]`（X）之前** —— 与 §318 的 `ScriptMover` **相反**（每表自己的顺序）。
8. **35..40 六项恒 `false`** —— 保留未用。
9. **`lastField + 1` 的 1-based 编码**（0 表示无变化）。
10. **⭐ `50` vs `0x42480000`** —— **把浮点当整数读**，而那**破坏了一个正在工作的功能**。
11. **`0x42480000` 是正确的 IEEE 754 float 50.0**。
12. **"两个不同的显示"是解码器的不一致而不是编码的不同** —— 一个极隐蔽的误读。
13. **"理由被写下来而不是结论"**。
14. **五个 `writeUnsignedDelta` 宽度**（4/10/10/10/11）。
15. **`writeEntityOrigin` 接受 `mapCenter`** ⇒ 可能**相对于地图中心**编码。
16. **三个表三种间隔位宽**（playerState 4 位 / objective 一元 / hudElem 3 位）。

## 八、未闭合点

- `writeEntityOrigin` 的完整实现（相对还是绝对）。
- 35..40 六项保留给什么。
- 34 与 41 的 `isClock` 语义。
- `sv_snapshot_mp.cpp` 2600 行之后未读取（1.47 MB，进度 18%）。
