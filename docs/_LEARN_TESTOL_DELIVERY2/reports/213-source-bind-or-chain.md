# 213 · 40+ 个前缀校验的巨型 OR 链、`ServerDObjGetSuffix` 的实际用法

## 一、范围

本报告学习 `EngineBindings.cpp` 3735–3914 行。

## 二、`ServerDObjGetSuffix` 的真正用法

```cpp
!std::equal(
    ServerDObjGetSuffix.begin(),
    ServerDObjGetSuffix.end(),
    module_ + ServerDObjGetRva + 5)
```

**注意 `+ 5`** —— 而 §197 里那个数组是：

```cpp
constexpr std::array<std::uint8_t, 3> ServerDObjGetSuffix{ 0x8B, 0xC8, 0xB8 };
```

### 2.1 为什么从 `+5` 开始

**因为那个 RVA 指向的是谓词（`sub_74E160`）而不是 getter**（§195/§196）。

**`+5` 处是 `8B C8 B8`**：

```text
8B C8   mov ecx, eax
B8      mov eax, imm32   （opcode 起始）
```

**`sub_74E160` 的谓词体**（§195）：

```text
v1 = word_77E7F20[(a1 - &unk_31437A0) / 712];
return v1 && (&unk_77E9720 + 216 * v1) != 0;
```

**而 `8B C8` = `mov ecx,eax` 是那个函数内部某处的指令** —— 所以 `+5` 是**函数体内一个稳定的特征点**，不是函数入口。

### 2.2 三种校验形态汇总

```text
前缀（绝大多数）    ：从函数入口开始
后缀（唯一一个）    ：从 +5 开始
数据（唯一一个）    ：ByteDirectionsPrefix，比对 12 字节数据
```

## 三、那些链式失败的日志

### 3.1 三条独立的日志

```text
"native entity binding prefix mismatch function=<名字>"
"player DObj binding prefix mismatch function=<名字>"
"message binding prefix mismatch function=<名字>"   （推测，见后）
```

**每条都带"哪一组"与"哪一个函数"**。

### 3.2 与 §`Appmain.cpp` 里 `bind()` 失败的关系

§`Appmain` 曾记录：

> `bind()` 在 `stage=message_bindings` 失败，整个 dedicated 起不来。

**所以这些日志行是"起不来"时的第一诊断线索**。

## 四、那个巨型 OR 链的结构

```cpp
if (!equal(A.begin(), A.end(), module_ + ARva) ||
    !equal(B.begin(), B.end(), module_ + BRva) ||
    ... 40+ 项 ...)
{
    return false;
}
```

### 4.1 它丢失了什么

**这个链只返回 `false`，不返回"哪一个失败了"** —— 与前面两组链式三元**完全不同**。

**所以这 40+ 个校验里任何一个失败，日志只会说"message binding prefix mismatch"（或类似），而不知道是哪一个。**

**这是与 §212 里"链式三元给名字"的一处不一致** —— 前两组精细，这一组粗糙。

### 4.2 为什么可能这样写

**因为这 40+ 项都是"必须全对"的**，而且它们属于同一组（"message / trace / weapon / animation"）。**分组已经提供了大致定位**，而组内不再细分。

**但对照 §212 的精细度，这里是可以改进的。**

## 五、本组覆盖的校验项（按组）

### 5.1 `playerDObjPrefixFailure` 组的剩余项

```text
DObjFree
Com_ServerDObjCreate
Com_GetServerDObj      ← 用 Suffix 且从 +5 开始
```

**注意命名**：`Com_ServerDObjCreate` / `Com_GetServerDObj` —— 带 `Com_` 前缀，而其他是裸函数名。

### 5.2 巨型 OR 链的前 30+ 项（按功能分）

**A. DB / 消息 / 区域装载**（14 项）

```text
ComFrame / DBFindXAssetHeader / DBIsXAssetDefault / DBLinkXAssetEntry
MsgInit / MsgWriteBits / MsgWriteString
LevelZoneLoad / CollisionMapLoad / CollisionWorldLink
CCSClear / CCSInitialize / CCSGetConstantString
```

**B. 碰撞与 trace**（12 项）

```text
Trace / WorldTrace / TransformedBrushModelTrace / TransformedCapsuleTrace
CalcTraceExtents / PointTraceToEntities
DObjGeomTracelinePartBits / DObjContentsTracelinePartBits
DObjTraceline / DObjContentsTraceline
PointTraceStaticModels / DObjCalcSkel
```

**C. 武器与开火**（8 项，本组读到部分）

```text
BGGetPlayerEyePosition / BulletEndpos / ByteDirections
ViewMovementDamageKick / ViewMovementIdleAngles
ViewMovementBobAngles / ViewMovementAdsBob
WeaponMovementBase / WeaponMovementSway
WeaponMovementRecoil / WeaponMovementBob
SetWeaponMovementAngles
AnglesToQuaternion / AngleVectors / MatrixMultiply / AxisToAngles
PmoveSingle / ...
```

**实际计数**：

```text
A 组 13 项
B 组 12 项
C 组 16+ 项（截至 PmoveSingle）
```

## 六、`ByteDirectionsPrefix` 在 OR 链里

```cpp
!std::equal(
    ByteDirectionsPrefix.begin(),
    ByteDirectionsPrefix.end(),
    module_ + ByteDirectionsRva)
```

**这是 40+ 项里唯一一个"数据校验"**：

```text
4F 96 06 BF 00 00 00 00 44 C4 59 3F
```

**而它在同一个 OR 链里与代码前缀混在一起** —— 所以"数据表的内容校验"和"函数前缀校验"用同一个机制。

**这在语义上是一致的**（都是"这个镜像是否仍是那个镜像"），只是**被校验的字节性质不同**。

## 七、`Com_GetServerDObj` 的 `+5` 偏移意味着什么

### 7.1 一个可能的解释

`sub_74E160` 的谓词体（§195）：

```text
v1 = word_77E7F20[(a1 - &unk_31437A0) / 712];
return v1 && (&unk_77E9720 + 216 * v1) != 0;
```

**编译后可能是**：

```asm
mov eax, [esp+4]        ; a1      （0）
sub eax, offset unk_31437A0      （5）
cdq
mov ecx, 712
idiv ecx
movzx eax, word_77E7F20[eax*2]
...
mov ecx, eax            ; ← 8B C8
mov eax, ...            ; ← B8
```

**所以 `+5` 落在"除法之后、取表值之前"** —— 而 `mov ecx,eax; mov eax,...` 是那个位置的自然指令。

### 7.2 为什么这是一个可靠的特征

**因为 `8B C8 B8` 三字节在这个函数的这个位置几乎不可能偶然出现**，且它**不依赖函数入口**（那个入口的前缀已被证明会匹配到错误的函数）。

## 八、关键结论

1. **`ServerDObjGetSuffix` 从 `+5` 开始**，因为那个 RVA 指向谓词而非 getter。
2. **三种校验形态**：前缀（绝大多数）、后缀（唯一）、数据（唯一）。
3. **巨型 OR 链只返回 false 而不给名字**，与前两组的链式三元形成不一致。
4. **40+ 项里有 13 项 DB/消息、12 项碰撞、16+ 项武器/动画**。
5. **`ByteDirectionsPrefix` 是唯一的数据校验，与代码前缀混在同一机制里**。

## 九、未闭合点

- 巨型 OR 链的剩余项（3914 行之后）未读取。
- 那条日志的确切文本未在本组看到（`return false` 之后应该有日志，但本组读到的部分没显示）。

## 十、可以指出的一处改进

**巨型 OR 链应当像前两组一样返回"第一个失败者名字"**。当前的写法在 40+ 项里定位一个失败需要人工逐个排查，而前两组的写法只需要读一行日志。

**这不是"风格问题"** —— §`Appmain` 里记录过 `bind()` 失败导致整个 dedicated 起不来，而在那种情况下"哪个前缀不符"是唯一的线索。
