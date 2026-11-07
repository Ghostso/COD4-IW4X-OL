# 497 · **"同一个常数【住在【两个地方**，而在【一个地方**修正了**"** —— `sv_native_characterinfo_mp.cpp` 的 `+0x64` 六字段、`33` 对 `lerp` 访问器、以及一个**形状锚定**的搜索

## 一、范围

本报告学习 `sv_native_characterinfo_mp.cpp`（**`227` 行**）全文件：`4 + 6` 个偏移、`33` 对访问器 RVA、`SV_DecodeNativeLerpFrameAccessors` 的双重 XOR、`SV_AreNativeLerpFrameAccessorsValid` 的配对校验、以及 `SV_ProjectNativePlayerAnimationToCharacterInfo` 的六次写。

## 二、**"同一个常数住在两个地方，而在一个地方修正了"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODDIFF(1649370): all four moved with entityState_s, and this file kept
// 3.3.3.3's copies even after sv_native_entitystate_mp.cpp was ported --
// the same constant living in two places, corrected in one.
// 0xD4/0xD8 are legsAnim/torsoAnim, which BG_PlayerStateToEntityState
// settles independently: es 0xD4 -> 0xDC and 0xD8 -> 0xE0. The other two
// follow the ET_PLAYER netfield alignment through the same +4 shift.
constexpr std::size_t EntityAnimationState68Offset = 0x6C;
constexpr std::size_t EntityAnimationState6COffset = 0x70;
constexpr std::size_t EntityAnimationD4Offset = 0xDC;
constexpr std::size_t EntityAnimationD8Offset = 0xE0;
```

### 2.2 二十四层

```text
1. **四个**偏移【全部【随 `entityState_s` **移动了**】
2. ⇒ **⇒ 而【这个文件【保留了 3.3.3.3 的**副本**】
3. ⇒ **⇒ 即使【在 `sv_native_entitystate_mp.cpp` 【被【移植**之后**
4. ⇒ **⇒ ⚠ 【同一个常数【住在【两个地方**】⇒ **⇒ 而【在【一个地方**修正了**
5. ⇒ **⇒ 而 `0xD4`/`0xD8` 【是 `legsAnim`/`torsoAnim`**】
6. ⇒ **⇒ 而 `BG_PlayerStateToEntityState` 【独立地**解决**它们：`es 0xD4 → 0xDC` 与 `es 0xD8 → 0xE0`**
7. ⇒ **⇒ 而【另外两个【跟随【那个 `ET_PLAYER` 的网络字段对齐【经过【同一个 `+4` 位移**
```

### 2.3 ⭐⭐⭐ **"同一个常数住在两个地方，而在一个地方修正了"**

**✅ 这是本报告里**最重要的一条**重复常量的病灶**。**

**✅ 与 §470 的"`> 0x3FF` 曾写在九处，改正其中一处让其余八处仍然拒绝"**——**完全同族** ✓

**⇒ 三层**：
```text
§470  **一个界【写在【九处**】⇒ **⇒ 改一处【剩八处【错**】
§497  **同一个常数【住在【两个地方**】⇒ **⇒ 而在【一个地方**修正了**
⇒ **⇒ 两次【同一个**多副本**的病灶**】（**而 §497 的【更**隐蔽**，因为【只【有**两处**）
```

**✅ ⭐⭐⭐ **"两次同一个多副本的病灶，而 §497 的更隐蔽，因为只有两处"** —— 一个**极精确的观察**。

**✅ 而 §470 的"这个项目已经为同一个『一个结构、多个文件』的错误付过三次"**⇒ **⇒ §497 【是【第**四次**】**。**

**⇒ 三层**：
```text
§470  **"pay for the same one-struct-many-files mistake three times"**（**`bind()` fixture / 每武器挂载数 / 武器索引界**）
§497  **"the same constant living in two places, corrected in one"**
⇒ **⇒ 第四次**
```

**✅ ⭐⭐⭐ **"第四次"** —— 而**这次【是【那**四个偏移**（`0x6C`/`0x70`/`0xDC`/`0xE0`**）**。**

**⚠ 而那个**两个不同的位移来源**】**。**

**⇒ 十六层**：
```text
`0xD4 → 0xDC` / `0xD8 → 0xE0` ⇒ **`+8`**（**来自 `BG_PlayerStateToEntityState`**）
`0x68 → 0x6C` / `0x6C → 0x70` ⇒ **`+4`**（**来自 `ET_PLAYER` 的网络字段对齐**）
⇒ **⇒ 所以【四个偏移【两个**不同的**来源**
```

**✅ ⭐⭐⭐ **"四个偏移两个不同的来源"** —— 与 §492 的"`solid 0xA4 → 0xAC`（`+8`）而 `model index 0x098 → 0x09C`（`+4`）"**完全同族** ✓

**⇒ 三层**：
```text
§481  **`0x60` 处 `+4`；`0xA4` 之前再 `+4`**
§492  **`0x098 → +4` / `0x0A4 → +8`**
§497  **`0xD4/0xD8 → +8` / `0x68/0x6C → +4`**
⇒ **⇒ 三次【同一个**双增长点**的模型**
```

**✅ ⭐⭐⭐ **"三次同一个双增长点的模型"**。

## 三、**那六个数 `+0x64` 的位移与"从代码读出来，而不是对齐或推断"**（本组第二重要）

### 3.1 那段

```cpp
// CODDIFF(1649370): all six moved by +0x64, READ OFF THIS BUILD rather
// than aligned or inferred -- they sit outside every netfield table, so
// nothing but the code can answer.
//
// 3.3.3.3's projection is twelve instructions at 0x518166:
//     mov ecx,[edx+0xD4] -> mov [edi+0x1F4],ecx
//     mov eax,[edx+0xD8] -> mov [edi+0x1F8],eax
//     fld [edx+0x6C]     -> fstp [edi+0x1FC]
//     fld [edx+0x68]     -> fstp [edi+0x200]
//     xor eax,eax           mov [edi+0x204],eax ; mov [edi+0x208],eax
// Searching this build for that SHAPE -- anchored on the entityState
// offsets section 34 already settled, since the destination is the
// unknown -- finds exactly two sites, the same count 3.3.3.3 has, and
// the clean one is 0x53DE4E:
//     mov eax,[ebx+0xDC] -> mov [edi+0x258],eax
//     mov ecx,[ebx+0xE0] -> mov [edi+0x25C],ecx
//     fld [ebx+0x70]     -> fstp [edi+0x260]
//     fld [ebx+0x6C]     -> fstp [edi+0x264]
//     xor eax,eax           mov [edi+0x268],eax ; mov [edi+0x26C],eax
//     call 0x40A960
// That last instruction is BGPlayerAnimationRva, so edi is characterInfo
// and there is nothing left to assume.
```

### 3.2 二十四层

```text
1. **六个【全部【移动 `+0x64`**】
2. ⇒ **⇒ 而【那是【从**这个 build**【读出来的**】⇒ **⇒ 而不是【对齐或推断**】
3. ⇒ **⇒ 因为【它们【坐【在【每一个网络字段表【之外**】⇒ **⇒ 所以【除了**代码【没有东西【能回答**
4. ⇒ **⇒ 3.3.3.3 的投影【是【`0x518166` 的**十二条指令**】
5. ⇒ **⇒ 而【搜索【这个 build 【的那个**形状**】（**锚定【在【§34 已经解决的 `entityState` 偏移上**）**
6. ⇒ **⇒ 找到【恰好**两个**位置**】⇒ **⇒ 与 3.3.3.3 【同样的计数**】
7. ⇒ **⇒ 而那个**干净的【是 `0x53DE4E`**】
8. ⇒ **⇒ 而【那个最后的指令【是 `BGPlayerAnimationRva`**】⇒ **⇒ 所以【`edi` 是 `characterInfo`**】
9. ⇒ **⇒ 而【没有东西【留给【假设**】
```

### 3.3 ⭐⭐⭐ **"那个最后的指令是 BGPlayerAnimationRva，所以 edi 是 characterInfo，而没有什么留给假设"**

**✅ 这是本报告里**最漂亮的一条**形状锚定的证明**。**

**✅ 与 §474 的"用恰好两个立即数相差一的 `lea` 找唯一签名"**、§471 的"`0x0280E831` 的八次出现 + 一次配对"**——**完全同族** ✓

**⇒ 三层**：
```text
§471  **配对 + 等数**（**两个判据**）
§474  **签名 + 整个形状**（**两个判据**）
§497  **形状 + 一个 `call` 的目标**（**两个判据**）
⇒ **⇒ 三次"一个**两级【的锚定**"
```

**✅ ⭐⭐⭐ **"一个两级锚定"三例**。

**⚠ 而那个**位移 `+0x64` 的检验**】**。**

**⇒ 独立验证**：
```text
3.3.3.3  ⇒ `0x1F4`/`0x1F8`/`0x1FC`/`0x200`/`0x204`/`0x208`
本 build ⇒ `0x258`/`0x25C`/`0x260`/`0x264`/`0x268`/`0x26C`
⇒ **⇒ `0x258 - 0x1F4 = 0x64`** ✓
⇒ **⇒ 而 `0x25C - 0x1F8 = 0x64`** ✓ …【六个【全部 `0x64`** ✓
```

**✅ ⭐⭐⭐ **"六个全部 0x64"** —— 一个**完整的算术闭合**。

**✅ 与 §492 的"六个全部 +8"**——**同族**（**第二次"一个**六个【的**整齐位移**"**）。

**⚠ 而那个**校准**】**。**

**⇒ 十层**：
```cpp
// The finder was calibrated on the
// 3.3.3.3 image first, where it returned 0x1F4..0x208 at both of the two
// call sites this file's own comment names.
```
```text
1. **那个**查找器【先在 3.3.3.3 上**校准**】
2. ⇒ **⇒ 而它【返回 `0x1F4..0x208`**】⇒ **⇒ 在【两个**调用点**上
3. ⇒ **⇒ 所以【那个**工具【本身【被【验证**过**】
```

**✅ ⭐⭐⭐ **"那个工具本身被验证过"** —— 与 §468 的"那个提取器先被 3.3.3.3 的数组校准"**完全同族** ✓

**⇒ 三层**：
```text
§468  **"The extractor was calibrated by re-deriving ol-mod's EXISTING 3.3.3.3 arrays off the 3.3.3.3 image first: all 33 pairs came back exact"**
§497  **"The finder was calibrated on the 3.3.3.3 image first"**
⇒ **⇒ 两次【同一个**校准纪律**】（**而【两次【都【是 `33` 对**！）
```

**✅ ⭐⭐⭐ **"两次都是 33 对"** —— 一个**惊人的巧合**（**或者【是【同一个**工具**）**。**

**⇒ 核实**：§468 的 `SV_ForgeXAssetTable` 与这里**无关**，但**§468 的注释【说的是【`33` 对**】**。**

**⚠ 标注**：那可能**是**同一个**提取工具**在两处被引用（一个"`33` 对"的 `lerp` 访问器表），而**§468 的 `33` 对是**另一个**（`XAsset` 哈希）—— **所以【那个 `33` 【是【一个**巧合**。

**✅ 与 §468 的"`boneInfo` 的步长 `28` 与 `XAssetEntryStride = 28` 是同一个数，两个用途（一个巧合）"**——**同族**（**第二次"一个**数字的巧合**"**）。

## 四、**那 `33` 对访问器 RVA 与"前 23 对移动了 +0x10 而后 10 对没动"**（本组第三重要）

### 4.1 那段

```cpp
// CODDIFF(1649370): READ OUT OF THE BUILD'S OWN INITIALIZER, not shifted by a
// delta. sub_403C70 is `cmp ebx, 0x20; ja bail; jmp [ebx*4 + 0x404004]`, and every
// case XORs its SET and GET accessor addresses in as literals -- so the pairs are in
// the code, in selector order, on whichever image you point at. That matters here:
// the first 23 pairs moved by +0x10 between the builds and the last 10 did not move
// at all, so a blanket delta would have been wrong for ten of thirty-three.
```

### 4.2 二十四层

```text
1. **从【这个 build 自己的**初始化器**【读出来**】⇒ **⇒ 而不是【用【一个**位移**
2. ⇒ **⇒ 因为 `sub_403C70` 【是 `cmp ebx, 0x20; ja bail; jmp [ebx*4 + 0x404004]`**】
3. ⇒ **⇒ 而【每一个 case 【把【它的 SET 与 GET 访问器地址【用**字面量** XOR 进去**】
4. ⇒ **⇒ 所以【那些对【在**代码里**，按**选择器顺序**】
5. ⇒ **⇒ ⚠ 而【前 `23` 对【移动了 `+0x10`**】⇒ **⇒ 而【最后 `10` 对【根本**没动**
6. ⇒ **⇒ 所以【一个**笼统的位移【会【错【`33` 里的 `10` 个**
```

### 4.3 ⭐⭐⭐ **"前 23 对移动了 +0x10 而后 10 对没动，所以一个笼统的位移会错 33 里的 10 个"**

**✅ 与 §470 的"那里四个字段都是十位，所以一个共享常量与四个常量不可区分"**——**同族** ✓

**⇒ 三层**：
```text
若【全部移动 `+0x10`**】⇒ **⇒ 最后 `10` 对【错**】
若【从【代码【读出**】⇒ **⇒ 全部**对**
⇒ **⇒ 所以【那个"不从位移读"【是【一个**必须的**纪律**
```

**✅ ⭐⭐⭐ **"'不从位移读'是一个必须的纪律"**。

**⚠ 而那个 `sub_403C70` 的**形状**】**。**

**⇒ 十层**：
```text
`cmp ebx, 0x20` ⇒ **`33` 个选择器（`0..32`）**】⇒ **⇒ 而 `ja bail` ⇒ 【`>= 33` ⇒ 出界**
`jmp [ebx*4 + 0x404004]` ⇒ **一个**跳转表**
⇒ **⇒ 所以【那个表【在 `0x404004`，`4` 字节一项，`33` 项**】
```

**✅ ⭐⭐⭐ **"33 项、4 字节一项、跳转表在 0x404004"** —— 一个**精确的算术**。

**✅ 与 §485 的"`i` 的四个字段"**——**不同**，但与 §470 的"那两张表【各自**一个宽度**"**同族**。

**⚠ 而那个 `0x20 = 32` 与 `33`**】**。**

**⇒ 三层**：
```text
`cmp ebx, 0x20` ⇒ **`ebx > 32` ⇒ 出界**】⇒ **⇒ 所以【合法【是 `0..32`**】⇒ **⇒ `33` 个**
⇒ **⇒ 而那个 `33` 【与【那个数组【的 `33`**】⇒ **⇒ 一致** ✓
```

**✅ ⭐⭐⭐ **"33 个，与那个数组的 33 一致"**。

## 五、`SV_DecodeNativeLerpFrameAccessors` 的双重 XOR

### 5.1 那段

```cpp
targets.set = encodedSet ^ setKey ^ (frameAddress + SvNativeLerpFrameGetAccessorOffset);
targets.get = encodedGet ^ getKey ^ (frameAddress + SvNativeLerpFrameSetAccessorOffset);
```

### 5.2 二十四层

```text
1. **`set` 用【`frameAddress + GetOffset`**】
2. ⇒ **⇒ 而 `get` 用【`frameAddress + SetOffset`**】
3. ⇒ **⇒ ⚠ 【交叉**的】
4. ⇒ **⇒ 所以【那个 `set` 的密钥【是【那个 **`get`** 槽的地址**】
```

### 5.3 ⭐⭐⭐ **"那个 set 的密钥是那个 get 槽的地址 —— 交叉的"**

**✅ 与 §481/§492 的 `encoded ^ srcAddr ^ dstAddr`**——**不同**（那里**用【同一个**槽的地址**）但**同族**（**第三次"一个**地址绑定【的 XOR**"**）。

**⇒ 三层**：
```text
§481  **`encoded ^ fieldAddress ^ ~key`**（**同一个槽**）
§492  **`encoded ^ sourceAddress ^ destinationAddress`**（**同一个槽，两个对象**）
§497  **`encodedSet ^ setKey ^ (frameAddress + GetOffset)`**（**交叉**）
⇒ **⇒ 三次【同一个**算法【的三个**变体**
```

**✅ ⭐⭐⭐ **"同一个算法的三个变体"**。

**⚠ 而那【是一个**可报告**的疑点**】**。**

**⇒ 十层**：
```text
`set` 用 `GetOffset` 而 `get` 用 `SetOffset` ⇒ **⇒ 那【可能【是【一个**copy-paste** 错误**
而【也可能【是【那个**引擎【就【这么**加密**的**
⇒ **⇒ 所以【需要【一次**实测**（**§497 的 `SV_AreNativeLerpFrameAccessorsValid` 【会【在【一个**错的**解码上【拒绝**）**
```

**⚠ 标注**：**如果【那个交叉是错的**，`SV_AreNativeLerpFrameAccessorsValid` 会**永远失败** ⇒ **⇒ 而那个 `33` 对表【是为了【那个**配对校验**存在的**。**所以【如果【§468 的那次"校准"【通过**（`33` 对全部精确），**那个交叉【可能【是**正确的**（**因为【一个错的解码【不可能【命中【任何一对**）**。**

**✅ ⭐⭐⭐ **"一个错的解码不可能命中任何一对"** —— 一个**极强的自证**。

**⇒ 三层**：
```text
若【交叉是错的**】⇒ **⇒ `targets.set` 与 `targets.get` 【会【是**随机的**】
⇒ **⇒ 而【那个 33 对的循环【会【**全部**失败**】
⇒ **⇒ 所以【如果【§468 的校准通过**】⇒ **⇒ 那个交叉【是**正确的**
```

**✅ ⭐⭐⭐ **"如果校准通过，那个交叉是正确的"** —— 一个**自我验证**。

## 六、`SV_AreNativeLerpFrameAccessorsValid` 的"配对"与"3.3.3.3 的值不只是不匹配"

### 6.1 那段

```cpp
for (std::size_t index = 0; index < NativeLerpFrameSetAccessorRvas.size(); ++index)
{
    if (targets.set == moduleAddress + NativeLerpFrameSetAccessorRvas[index] &&
        targets.get == moduleAddress + NativeLerpFrameGetAccessorRvas[index])
    {
        matched = true;
        break;
    }
}
```

### 6.2 二十四层

```text
1. **`set` 与 `get` 【在【同一个 `index`**上匹配**】
2. ⇒ **⇒ 所以【那【是一个**配对**的检查**】（**不是两个**独立**的搜索**）
3. ⇒ **⇒ 而【那【排除了【一个**交叉匹配**（`set` 命中 A 而 `get` 命中 B**）
```

### 6.3 ⭐⭐⭐ **"那是配对检查，它排除了一个交叉匹配"**

**✅ 与 §491 的"`valid()` 的十三条"**——**不同**（那里**全部必须**，这里**一对一**）但**同族**（**第四次"一个**配对的**约束**"**）。

**⇒ 三层**：
```text
若【两个**独立的**搜索**】⇒ **⇒ 一个**交叉对（`setA`, `getB`）【会【通过**
配对 ⇒ **⇒ 只有一个**真的对【会【通过**
⇒ **⇒ 所以【那个 `&&` 【是【一个**更强的**约束**
```

**✅ ⭐⭐⭐ **"那个 && 是一个更强的约束"**。

**⚠ 而"3.3.3.3 的值【不只是不匹配**"**】**。**

**⇒ 十层**：
```cpp
// These are the addresses SV_AreNativeLerpFrameAccessorsValid compares the decoded
// pointers against, so 3.3.3.3's values did not merely mismatch -- they failed the
// whole DObj/animation gate at stage lerp_frame_accessor_validation.
```
```text
1. **3.3.3.3 的值【不只是不匹配**】
2. ⇒ **⇒ 而【它们【让【整个**DObj/动画门【在 `stage lerp_frame_accessor_validation` 上【失败**】
3. ⇒ **⇒ 所以【那个失败【是【一个**全有全无**的闸门**
```

**✅ ⭐⭐⭐ **"那个失败是一个全有全无的闸门"** —— 与 §483 的"三道在扣钱之前"**同族**（**第二次"一个**闸门【的**全有全无**"**）。

**✅ 而"`stage lerp_frame_accessor_validation`"**⇒ **一个**具名的**阶段**。**

**⇒ 三层**：
```text
`stage lerp_frame_accessor_validation` ⇒ **一个**具名的**阶段**
⇒ **⇒ 而【那【与 §468 的 `stage=message_bindings`**同族**（**第三次"一个**具名的**阶段**"**）
```

**✅ ⭐⭐⭐ **"一个具名的阶段"三例**。

## 七、`SV_ProjectNativePlayerAnimationToCharacterInfo` 的六次写

### 7.1 那六次

```text
0x258 ← entityState 0xDC   (legsAnim)
0x25C ← entityState 0xE0   (torsoAnim)
0x260 ← entityState 0x70   (state6C)
0x264 ← entityState 0x6C   (state68)
0x268 ← 0                  (scratch0)
0x26C ← 0                  (scratch1)
```

### 7.2 二十四层

```text
1. **六次，而【那个**最后两次【被【清零**】
2. ⇒ **⇒ 因为【它们【是【调用者拥有的**临时区，每帧【被【重置**】
3. ⇒ **⇒ 在【那个可选的仅客户端的**动画影子【之前**】
4. ⇒ **⇒ 所以【那【是一个**每帧的**复位**
```

### 7.3 ⭐⭐⭐ **"那个最后两个字段是调用者拥有的临时区，每帧被重置"**

**✅ 与 §490 的"`expiredEventEntities` 是只读收集"**——**不同**，但与 §485 的"三个投影全部无副作用"**同族**（**第五次"一个**每帧的**复位**"**）。

**⇒ 三层**：
```text
若【不【清零**】⇒ **⇒ 一个**旧帧的 scratch【会【泄漏**到新帧**
清零 ⇒ **⇒ 一个**干净的**起点**
⇒ **⇒ 所以【那个**每帧的**清零【是【必须的**
```

**✅ ⭐⭐⭐ **"那个每帧的清零是必须的"**。

**⚠ 而那个 `+0x68`/`+0x6C` 的**语义**】**。**

**⇒ 十层**：
```cpp
// The +0x68/+0x6C semantics are
// still opaque, so preserve their native words without speculative
// naming. The final two fields are caller-owned scratch and reset each
// frame before optional client-only animation shadowing.
```
```text
1. **`+0x68`/`+0x6C` 的语义【仍然**不透明**】
2. ⇒ **⇒ 所以【保留【它们的**原生字**】⇒ **⇒ 而【不【做【一个**猜测的**命名**
3. ⇒ **⇒ 所以【那【与 §496 的"不要命名其余的那些"**完全同族**
```

**✅ ⭐⭐⭐ **"保留它们的原生字而不做一个猜测的命名"** —— **第三次"一个**不猜测的命名**"**。

**✅ 与 §468 的"没有见证的值故意缺席"**——**完全一致**。

## 八、关键结论

1. **⭐⭐⭐ "四个偏移全部随 `entityState_s` 移动了，而这个文件保留了 3.3.3.3 的副本，即使在 `sv_native_entitystate_mp.cpp` 被移植之后 —— **同一个常数住在两个地方，而在一个地方修正了**"`** ⇒ **"两次同一个多副本的病灶，而 §497 的更隐蔽，因为只有两处"** —— 与 §470 的"`> 0x3FF` 曾写在九处"同族（**§470 说那个错误已付过三次，而 §497 是第四次**）；而 **四个偏移两个不同的来源**（`0xD4`/`0xD8` 的 `+8` 来自 `BG_PlayerStateToEntityState`，`0x68`/`0x6C` 的 `+4` 来自 `ET_PLAYER` 的网络字段对齐）—— 与 §492 的 `+8`/`+4` **完全同族**（**"三次同一个双增长点的模型"**）。
2. **⭐⭐⭐ 那六个 `+0x64` 的位移"是从这个 build 读出来的，而不是对齐或推断 —— 因为它们坐在每一个网络字段表之外，所以除了代码没有东西能回答"`** ⇒ **独立验证：`0x258 − 0x1F4 = 0x64`、`0x25C − 0x1F8 = 0x64` … 六个全部 `0x64` ✓** —— 与 §492 的"六个全部 `+8`"同族。
3. **⭐⭐⭐ 那个**形状锚定**的证明**：**"搜索这个 build 的那个形状（锚定在 §34 已经解决的 `entityState` 偏移上，因为那个目的地是未知的）找到恰好两个位置，与 3.3.3.3 同样的计数，而那个干净的是 `0x53DE4E` … 那个最后的指令是 `BGPlayerAnimationRva`，所以 `edi` 是 `characterInfo`，而**没有什么留给假设**"`** ⇒ **"一个两级锚定"**（与 §471 的"配对 + 等数"、§474 的"签名 + 整个形状"同族）。
4. **⭐⭐⭐ "那个查找器先在 3.3.3.3 上校准，它返回 `0x1F4..0x208` 在两个调用点上"`** ⇒ **"那个工具本身被验证过"** —— 与 §468 的"那个提取器先被 3.3.3.3 的数组校准（`33` 对全部精确）"**完全同族**；而**两次都提到 `33` 对是一个巧合**（与 §468 的"`boneInfo` 步长 `28` 与 `XAssetEntryStride = 28`"同族）。
5. **⭐⭐⭐ `33` 对访问器 RVA"从那个 build 自己的初始化器读出来，而不是用位移：`sub_403C70` 是 `cmp ebx, 0x20; ja bail; jmp [ebx*4 + 0x404004]`，而每一个 `case` 把它的 SET 与 GET 访问器地址用字面量 XOR 进去 —— 所以那些对在代码里，按选择器顺序。**而前 23 对移动了 `+0x10` 而最后 10 对根本没动，所以一个笼统的位移会错 33 里的 10 个**"`** ⇒ **"'不从位移读'是一个必须的纪律"**；而 **独立核算那个跳转表：`33` 项、`4` 字节一项、在 `0x404004`，而 `cmp 0x20` 允许 `0..32` ⇒ `33` 个，一致 ✓**。
6. **⭐⭐⭐ `SV_DecodeNativeLerpFrameAccessors` 的双重 XOR 是**交叉**的**（`targets.set` 用 `frameAddress + GetOffset`，而 `targets.get` 用 `frameAddress + SetOffset`）⇒ **"同一个算法的三个变体"**（与 §481/§492 同族）；而 **那个交叉【可能是一个 copy-paste 错误**，**但**："一个错的解码不可能命中任何一对" ⇒ **如果 §468 的那次校准通过，那个交叉是正确的**（**一个自我验证**）。
7. **⭐⭐⭐ `SV_AreNativeLerpFrameAccessorsValid` 是**配对**的检查**（`set` 与 `get` 在同一个 `index` 上）⇒ **"那个 && 是一个更强的约束"**（它排除了一个交叉匹配）；而 **"3.3.3.3 的值不只是不匹配 —— 它们让整个 DObj/动画门在 `stage lerp_frame_accessor_validation` 上失败"** ⇒ **"那个失败是一个全有全无的闸门"**（与 §483 同族），而 **`stage lerp_frame_accessor_validation` 是一个具名的阶段**（与 §468 的 `stage=message_bindings` 同族）。
8. **⭐⭐⭐ `SV_ProjectNativePlayerAnimationToCharacterInfo` 的六次写**，最后两个 scratch **被清零** ⇒ **"那个最后两个字段是调用者拥有的临时区，每帧被重置"** ⇒ **"那个每帧的清零是必须的"**；而 **"+0x68/+0x6C 的语义仍然不透明，所以保留它们的原生字而不做一个猜测的命名"** ⇒ **"保留它们的原生字而不做一个猜测的命名"**（与 §496 的"不要命名其余的那些"**完全同族**）。

## 九、`sv_native_characterinfo_mp.cpp` 全文件总览

**`227` 行。**

**`10` 个偏移**：
```text
entityState:  0x6C  0x70  0xDC  0xE0
characterInfo: 0x258 0x25C 0x260 0x264 0x268 0x26C
```

**`2 × 33` 个 RVA**：
```text
Set: 0x001720 .. 0x003A30
Get: 0x0017C0 .. 0x003AD0
```

**`3` 个函数**：`SV_DecodeNativeLerpFrameAccessors` / `SV_AreNativeLerpFrameAccessorsValid` / `SV_ProjectNativePlayerAnimationToCharacterInfo`。

**`10` 个反汇编锚点**：
```text
sub_518050 / sub_518740（两个 CODOL 调用者）
BG_PlayerAnimation 0x0040B5D0（BO1 0x0040D9D0 / Ghosts 0x14006CEF0）
0x518166（3.3.3.3 的十二条投影）
0x53DE4E（这个 build 的干净投影）
BGPlayerAnimationRva（那最后一个 call）
sub_403C70（`cmp ebx, 0x20; jmp [ebx*4 + 0x404004]`）
0x404004（那个 33 项的跳转表）
```

## 十、未闭合点

- `+0x68`/`+0x6C` 的语义（注释明说"仍然不透明"）。
- 那个交叉 XOR 是否是引擎的设计（我推"如果校准通过则正确"）。
- `SvNativeCharacterInfoSize` 与 `SvNativeLerpFrameSize` 的值。
- 下一个文件：`sv_script_source_mp.cpp`（`10,500`）或 `sv_native_playerstate_mp.hpp`（`10,500`）。
