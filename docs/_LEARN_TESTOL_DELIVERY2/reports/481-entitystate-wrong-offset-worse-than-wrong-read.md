# 481 · **"把 3.3.3.3 的偏移写进这个 build 的 entityState 比读一个错的值更糟"** —— `sv_native_entitystate_mp.cpp` 的 `0xD0` 事件槽、二十六项拒绝、以及一个"潜伏的击杀"

## 一、范围

本报告学习 `sv_native_entitystate_mp.cpp`（**`520` 行**）全文件：`entityState_s` 的 `0x110 → 0x118` 两次增长、`26` 个偏移常量、`decodeSecureOrigin` 的地址绑定加密、`readProjection` 的**二十六项拒绝**、`legs/torso` 那个**两次尝试两次回滚**的问题、以及 `SV_SetNativeEntityStateUnknownA0` 的**第四份界**。

## 二、**"把 3.3.3.3 的偏移写进这个 build 的 entityState 比读一个错的值更糟"**（本组最重要的一段）

### 2.1 那段

```cpp
// Writing 3.3.3.3's offsets into this build's entityState is worse than
// reading a wrong value: 0xD0 is an EVENT slot here (codec -94), so the
// weapon index went into an event field and FIRED EVENTS every frame.
// legsAnim and torsoAnim also widened 11 -> 12 bits on the wire.
```

### 2.2 二十四层

```text
1. **把 3.3.3.3 的偏移【写进【这个 build 的 `entityState`**】
2. ⇒ **⇒ 比【读一个错的值【更糟**】
3. ⇒ **⇒ 因为 `0xD0` 【在这里【是【一个事件槽**】（**codec `-94`**）**
4. ⇒ **⇒ 所以【那个武器索引【走进了【一个事件字段**】
5. ⇒ **⇒ 而【每一帧【发射事件**】
6. ⇒ **⇒ 而 `legsAnim`/`torsoAnim` 【也【在线上【从 `11` 位【变宽到 `12` 位**】
```

### 2.3 ⭐⭐⭐ **"那个武器索引走进了【一个事件字段**】而【每一帧发射事件**"**

**✅ 这是本报告里**最重要的一条"一个**错的偏移【产生【一个可见的、持续的副作用**"**。**

**✅ 与 §474 的"`sv_bullet_mp` 从未运行"**——**相反**（那里**静的失败**，这里**动的失败**）。

**⇒ 三层**：
```text
错的读 ⇒ **一个错的值**（**静默**）
错的写 ⇒ **一个事件【每帧发射**（**一个**持续的、可见的**后果**）
⇒ **⇒ 所以【写【比读【更糟**】—— **因为【写【会【产生【新的**行为**】
```

**✅ ⭐⭐⭐ **"写比读更糟，因为写会产生新的行为"** —— 一个**极精确的不对称**。

**⚠ 而"codec `-94`"**⇒ **一个**负的编解码器号**。**

**✅ 与 §476 的"`field0070` 的 netfield 21，codec `-7`"**——**同族**（**第二次"一个**负的 codec**"**）。

**⇒ 三层**：
```text
§476  **`field0070` ⇒ codec `-7`**
§481  **`0xD0` 的事件槽 ⇒ codec `-94`**
⇒ **⇒ 而【§464 记过一串【负的** codec**】（`-7`/`-8`/`-55`/`-57`/…/`-102`）
```

**✅ ⭐⭐⭐ **"§464 记过一串负的 codec"** —— 而**`-94` 【现在【有了【一个**具体的后果**"**。**

**⚠ 而"`legsAnim`/`torsoAnim` 从 `11` 位【变宽到 `12` 位**"**⇒ **一个**位宽的迁移**。**

**⇒ 十层**：
```text
3.3.3.3 ⇒ **`11` 位**（`0..2047`）
1649370 ⇒ **`12` 位**（`0..4095`）
⇒ **⇒ 所以【一个 `2048..4095` 的动画【在旧界上【会【被拒绝**】
```

**✅ ⭐⭐⭐ **"一个 2048..4095 的动画在旧界上会被拒绝"** —— 而**注释【明确说了那个后果**（"**这正是【为什么【这个函数【在【那个十二位的动画界【被修好之后【仍然是【那个未解的问题**"**）。

## 三、**"二十六项，一个 `return std::nullopt`"**（本组第二重要）

### 3.1 那段

```cpp
// TWENTY-SIX TERMS, ONE `return std::nullopt`. Every one of these bounds is a
// claim about THIS build, and a rejection that names none of them is the exact
// shape that cost this project three cycles on the pinned usercmd queue. Make
// the conjunction say which term refused and with what value; a bound that is
// still 3.3.3.3's then identifies itself the first time it fires.
// The reporter is declared HERE, in front of the first refusal, because THREE
// returns in this function sat ahead of the old lambda and said nothing at
// all -- which is why this function was still the open question after the
// twelve-bit animation bound was fixed and its named terms went quiet.
```

### 3.2 二十四层

```text
1. **二十六项**】⇒ **⇒ 而【它们共用一个 `return std::nullopt`**】
2. ⇒ **⇒ 而【每一个界【都是【一个【关于**这个 build** 的主张**】
3. ⇒ **⇒ 而【一个【不命名任何项**的拒绝【正是【那个形状**】
4. ⇒ **⇒ 而【那个形状【在【那个 pinned usercmd 队列上【花掉【这个项目【三个周期**】
5. ⇒ **⇒ 所以【让那个合取【说出【哪一项【拒绝了【以及【用什么值**】
6. ⇒ **⇒ 而一个【仍然是 3.3.3.3 的**界【会【在【它第一次触发时【自报家门**】
7. ⇒ **⚠ 而那个报告器【被声明在【这里**】（**在【第一个拒绝**之前**）**
8. ⇒ **⇒ 因为【三个**返回【坐落在【那个旧 lambda 之前**】⇒ **⇒ 而【什么也没说**】
9. ⇒ **⇒ ⇒ 所以【这个函数【在【那个十二位的界【被修好、它的具名项【静默之后【仍然是【那个未解的问题**】
```

### 3.3 ⭐⭐⭐ **"三个返回坐落在那个旧 lambda 之前，而什么也没说"**

**✅ 这是本报告里**最精确的一条"**一个诊断的**位置**决定它的**覆盖**"**。**

**✅ 与 §462 的"四十个项共用一个 `return false`"**——**完全同族** ✓

**⇒ 三层**：
```text
§462  **四十个项【共用【一个 `return false`**】⇒ **给那一项命名 → 一个指针**
§481  **二十六项 + 三个【在 lambda 之前**的返回**】⇒ **把【报告器【移到【最前面**
⇒ **⇒ 两次"把**一个笼统的拒绝【拆成【一个具名的**"**
```

**✅ ⭐⭐⭐ **"把一个笼统的拒绝拆成一个具名的"两例**。

**⚠ 而"那个报告器【被声明在【第一个拒绝之前**"**⇒ **一个**极小的位置修正**。**

**⇒ 十层**：
```text
若【报告器【在【第一个 `if` 之后**】⇒ **⇒ 那三个【早的**返回【仍然**静默**
若【在【它之前**】⇒ **⇒ 全部二十六项【覆盖**】
⇒ **⇒ 所以【那个位置【是【一个**行为**】
```

**✅ ⭐⭐⭐ **"那个位置是一个行为"** —— 与 §467 的"`++ordinal` 在 `continue` 之前是关键"**同族**（**第三次"一个**语句的位置【是【一个行为**"**）。

### 3.4 而**那个报告器的去重**

```cpp
const auto report = [](const char *const term, const std::string &value) {
    static std::string reported;
    auto details = std::string(term) + "=" + value;
    if (details != reported)
    {
        reported = details;
        OlMod::RuntimeLog::write(..., "entitystate projection refused " + details);
    }
    return std::optional<SvNativeEntityStateProjection>{};
};
```

**⇒ 十层**：
```text
1. **一个 `static std::string` 记住【上一行**】
2. ⇒ **⇒ 只在【变化**时打印**】
3. ⇒ **⇒ 所以【一个【持续**的拒绝【只打印【一次**】
4. ⇒ **⇒ 而【换一个值【会【再打印【一次**】
```

**✅ ⭐⭐⭐ **"一个持续的拒绝只打印一次，而换一个值会再打印一次"** —— 与 §437 的 `LastCommitRefusal`**一个精确的对照** ✓

**⇒ 三层**：
```text
§437  **`LastCommitRefusal` 【全局 `static` 而含 `client=`** ⇒ **两个客户端【交替【击败**那个去重**】⇒ **一个**真实缺陷**
§481  **`reported` 【函数局 `static` 而含 `term=value`** ⇒ **⇒ 正确**（**那个 `term=value` 【是【一个**全局空间**）
⇒ **⇒ 同一模式【两处【由【被追踪的东西是不是每客户端**决定**（**与 §474 的判据【一致**）
```

**✅ ⭐⭐⭐ **"由被追踪的东西是不是每客户端决定"** —— 与 §474 的判据**完全一致**（**第三次**）。

## 四、**`decodeSecureOrigin` 的地址绑定加密**（本组第三重要）

### 4.1 那段

```cpp
float decodeSecureOrigin(const SvNativeEntityState &state, const std::size_t offset, const std::uint32_t key)
{
    const auto encoded = readValue<std::uint32_t>(state, offset);
    const auto fieldAddress = static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(state.bytes.data() + offset));
    return std::bit_cast<float>(encoded ^ fieldAddress ^ ~key);
}
```

### 4.2 二十四层

```text
1. **`encoded ^ fieldAddress ^ ~key`**】
2. ⇒ **⇒ 所以【那个明文【依赖【三个东西**：那个编码值 / 那个**字段自己的地址** / 那个 `key` 的反码**
3. ⇒ **⇒ ⇒ 而【那个字段的地址** ⇒ **⇒ 所以【一个 C++ 的**值拷贝【会【破坏**它**】
```

### 4.3 ⭐⭐⭐ **"一个 C++ 值拷贝会破坏它"**

**✅ 与 §465 的"`DB_LinkXAssetEntry` 复制 88 字节的头但保留里面的每一个指针"**——**同族**（**第四次"一个**结构【携带【一个**地址依赖**"**）。

**⇒ 三层**：
```text
§468  **一个已发布的资产【必须【永不移动**】（**因为【指针**）
§481  **一个 `entityState` 【必须【重绑定**】（**因为它【地址加密**）
⇒ **⇒ 两次"一个**地址依赖【使【拷贝【成为【一个**必须处理的**"**
```

**✅ ⭐⭐⭐ **"一个地址依赖使拷贝成为一个必须处理的"两例**。

**⚠ 而那个**修复**】**。**

```cpp
void relocateSecureOriginWords(SvNativeEntityState &destination, const SvNativeEntityState &source)
{
    if (!source.secureOriginAddressBound) return;
    for (const auto offset : OriginOffsets)
    {
        auto encoded = readValue<std::uint32_t>(source, offset);
        const auto sourceAddress = ...(source.bytes.data() + offset);
        const auto destinationAddress = ...(destination.bytes.data() + offset);
        encoded ^= sourceAddress ^ destinationAddress;
        writeValue(destination, offset, encoded);
    }
}
```

**⇒ 十六层**：
```text
1. **一个编码字【对一个地址【加密**】
2. ⇒ **⇒ 所以【换一个地址【只需【再 XOR【一次【两个地址的差**】
3. ⇒ **⇒ `encoded ^= sourceAddress ^ destinationAddress`**】
4. ⇒ **⇒ 所以【那个明文【保持**不变**】（**而那个编码字【改变**）**
```

**✅ ⭐⭐⭐ **"换一个地址只需再 XOR 一次两个地址的差，所以那个明文保持不变"** —— 一个**极精巧的解法**。

**⚠ 而"`~key`"**⇒ **一个**按位取反**的键**。**

**⇒ 十层**：
```text
`encoded ^ fieldAddress ^ ~key` ⇒ **解码**
`encoded ^ srcAddr ^ dstAddr` ⇒ **重绑定**
⇒ **⇒ 而【`~key` 【在【重绑定【时【被**消掉**（**因为【它【不变**）**
```

**✅ ⭐⭐⭐ **"那个 `~key` 在重绑定时被消掉，因为它不变"** —— 一个**正确的观察**。

**⚠ 而那个**三处使用**】**。**

**⇒ 三层**：
```text
① `decodeSecureOrigin`（**读**）
② `relocateSecureOriginWords`（**拷贝时重绑**）
③ `SV_MarkNativeEntityStateSecureOriginBound`（**标记**）
⇒ **⇒ 所以【那个 `secureOriginAddressBound` 【是一个**显式**的状态**】
```

**✅ ⭐⭐ **"那个 bound 标志是一个显式的状态"** —— 而**`readProjection` 【在【`originKeys && !bound` 时**拒绝**。

## 五、**`0x60`/`0x64`/`0x68` 那个三字段的歧义**（本组第四重要）

### 5.1 那段

```cpp
// CODDIFF(1649370): entityState_s grew TWICE between the builds -- a
// 16-bit field at 0x60 pushes everything from there by +4, and another
// dword before 0xA4 makes it +8 from there on -- and the struct itself
// went 0x110 -> 0x118 bytes. The map is the two builds' extracted
// ET_PLAYER netfield tables aligned on (bits, codec), which agree field
// for field, and BG_PlayerStateToEntityState (A sub_4131A0 <-> C
// sub_411360) settles the one run the tables cannot: three consecutive
// 16-bit fields at 0x60/0x64/0x68 where the aligner cannot tell which
// one this build inserted. It reads es+96 <- ps and es+100 <- ps on the
// A side against es+100 and es+104 here, so 0x60 -> 0x64 and 0x64 -> 0x68
// and the NEW field is the one at 0x60.
```

### 5.2 二十四层

```text
1. **`entityState_s` 【增长【两次**】
2. ⇒ **⇒ 一个 `16` 位的字段【在 `0x60`**】⇒ **⇒ 从那里起【一切【`+4`**】
3. ⇒ **⇒ 而【另一个 `dword` 【在 `0xA4` 之前**】⇒ **⇒ 从那里起【`+8`**】
4. ⇒ **⇒ 而那个结构【自己【`0x110 → 0x118`**】
5. ⇒ **⇒ 所以【`0x118 - 0x110 = 8`** ✓
6. ⇒ **⇒ 而那个映射【是【两张 `ET_PLAYER` 网络字段表【按 `(bits, codec)` 对齐**】
7. ⇒ **⇒ 而 `BG_PlayerStateToEntityState`（`sub_4131A0` ↔ `sub_411360`）【解决【那个表【不能解决**的那一段**
8. ⇒ **⇒ 三个连续的 `16` 位字段【在 `0x60`/`0x64`/`0x68`**】
9. ⇒ **⇒ 而【对齐器【不能【告诉【哪一个【是这个 build 插入的**】
10. ⇒ **⇒ ⇒ 它读 `es+96 <- ps` 与 `es+100 <- ps`（A 侧）对 `es+100` 与 `es+104`（这里**）**
11. ⇒ **⇒ 所以 `0x60 → 0x64` 与 `0x64 → 0x68`**】
12. ⇒ **⇒ 而【那个新的字段【是 `0x60`** 那个**】
```

### 5.3 ⭐⭐⭐ **"对齐器不能告诉哪一个这个 build 插入的 —— 而那个拷贝器解决了它"**

**✅ 与 §470 的"那里四个字段都是十位，所以一个共享常量与四个常量不可区分"**——**完全同族** ✓

**⇒ 三层**：
```text
§470  **四个十位字段【在一个 build 上【退化成一个**】（**一个结构【被【一个 build 掩盖**）
§481  **三个 `16` 位字段【对齐器【不能【分辨【哪一个是新的**】⇒ **⇒ 而【一个**逐指令**的拷贝器【能**】
⇒ **⇒ 两次"一个**结构的歧义【由【一个**更低的层**【解决**"
```

**✅ ⭐⭐⭐ **"一个结构的歧义由一个更低的层解决"两例**。

**⚠ 而那个**算术**】**。**

**⇒ 十层**：
```text
`0x60 → 0x64` ⇒ **`+4`**
`0x64 → 0x68` ⇒ **`+4`**
⇒ **⇒ 而 `0x110 → 0x118 = +8`**】⇒ **⇒ 所以【两次增长**：（`+4` 在 `0x60`）+（`+4` 在 `0xA4` 之前）**
```

**✅ ⭐⭐⭐ **"两次增长：+4 在 0x60，+4 在 0xA4 之前"** —— 一个**算术闭合**。

**✅ 而"`es+96` = `es+0x60`、`es+100` = `es+0x64`、`es+104` = `es+0x68`"**⇒ **三个十进制/十六进制的对应** ✓

## 六、**`+0xA4` 那个"潜伏的击杀"**

### 6.1 那段

```cpp
// 28 bits. At 0x1FFF this REFUSED THE WHOLE ENTITYSTATE PROJECTION the
// moment the engine put a real value at +0xA4 -- a latent kill, not a
// clamped field.
if (unk00A0 > 0x0FFFFFFF) return refuse("unk00A0", unk00A0);
```

### 6.2 二十四层

```text
1. **`28` 位**】
2. ⇒ **⚠ 而【在 `0x1FFF`（`13` 位，3.3.3.3 的值）上【它【拒绝了【整个**投影**】
3. ⇒ **⇒ 而【那【只在【引擎【在 `+0xA4` 上【放了一个**真实**值【那一刻**】
4. ⇒ **⇒ 所以【那【是一个**潜伏的击杀**，不是一个被夹的字段**】
```

### 6.3 ⭐⭐⭐ **"那是一个潜伏的击杀，不是一个被夹的字段"**

**✅ 这是本报告里**最重要的一条"**一个错误的界【只在【一个条件下【致命**"**。**

**✅ 与 §463 的"它只在 `clientThink` 开始提交时才变得可见"**——**完全同族** ✓

**⇒ 三层**：
```text
§463  **一个 bug 【只在【另一个被修好之后**才暴露**
§481  **一个界【只在【引擎【写了一个真实值**之后【才致命**
⇒ **⇒ 两次"一个**潜伏的**缺陷**"**
```

**✅ ⭐⭐⭐ **"一个潜伏的缺陷"两例**。

**⚠ 而"那【是【第四份**界**"**⇒ **一个**极重要的计数**。**

**⇒ 十层**：
```cpp
// The FOURTH copy of this bound, and the last. 28 bits, not 3.3.3.3's
// 13 -- and the uint16_t parameter silently truncated anything wider
// before the check even ran.
```
```text
1. **第四份**拷贝**
2. ⇒ **⇒ 而【那个 `uint16_t` 参数【会【在【检查【之前【静默截断【任何更宽**的值**】
3. ⇒ **⇒ 所以【那个【检查【甚至【不能【看到**那个真值**】
```

**✅ ⭐⭐⭐ **"那个 uint16_t 参数会在检查之前静默截断任何更宽的值"** —— 一个**极精确的**类型缺陷**。

**✅ 与 §470 的"`> 0x3FF` 曾写在九处"**——**完全同族** ✓

**⇒ 三层**：
```text
§470  **一个界【写在【九处**】（**武器索引**）
§481  **一个界【写在【四处**】（**`unk00A0`**）⇒ **⇒ 而【其中一处【参数类型【使得【那个检查【无效**】
⇒ **⇒ 两次"一个**常量【的**多副本**"**
```

**✅ ⭐⭐⭐ **"一个常量的多副本"两例** —— 而**§481 【加了【一个**新的失败模式**"**（**参数类型【使检查【无效**）**。**

## 七、**`legs/torso` 那个两次尝试两次回滚**

### 7.1 三段注释

```text
① "BG_PlayerStateToEntityState 的字段拷贝器 sub_AB31A0 把 playerState +0x0C8 -> entityState +0xD4
    （0x0041321C）与 +0x0D0 -> +0xD8（0x00413228），所以 legs 留在 +0xD4、torso 留在 +0xD8"

② "OPEN QUESTION (2026-10-08)：那个注解集【说【相反的配对】——
    BG_PlayerToEntity_SetMisc '写 torso/legs 动画 +0xD4/+0xD8' 而
    BG_AnimPlayerConditions '在 +0xD8 读 entityState_s::legsAnim'，
    而 BG_PlayAnim 把 playerState 的 torsoAnim 放在 +0xC8、legsAnim 放在 +0xD0。
    与上面那个拷贝器映射合起来 ⇒ 3.3.3.3 是 TORSO +0xD4 / LEGS +0xD8 —— 与上面那句相反，
    而那句【与它自己的前提矛盾】。一次交换【被尝试并回滚**，等一次现场测量。"

③ "OPEN QUESTION (second attempt)：那个注解集说 3.3.3.3 是 torso +0xD4 / legs +0xD8，
    而加上这个 build 在这个区域的 +8 位移（weapon +0xD8 vs 3.3.3.3 的 +0xD0，
    DObj +0xE8 vs +0xE0）⇒ TORSO 在 +0xDC、LEGS 在 +0xE0 —— 与下面的名字相反。
    一次交换【被尝试【两次**并【被【两个模拟原生调用方的测试【阻止**，
    而那个【本该确认它的冲刺签名【不在那个日志窗口里**。等一次【受控**的测量。"
```

### 7.2 二十四层

```text
1. **三个来源【互相矛盾**】
2. ⇒ **（① 拷贝器 ⇒ legs `+0xD4` / torso `+0xD8`**）
3. ⇒ **（② 注解集 + 拷贝器 ⇒ torso `+0xD4` / legs `+0xD8`**）
4. ⇒ **（③ 注解集 + `+8` 位移 ⇒ torso `+0xDC` / legs `+0xE0`**）
5. ⇒ **⇒ 而代码【选了 `LegsAnimOffset = 0xDC` / `TorsoAnimOffset = 0xE0`**】（**即 ③ 的**反相**）**
6. ⇒ **⇒ 而【两次尝试【被【两个测试**阻止**】
7. ⇒ **⇒ 而【那个本该确认它的冲刺签名【不在那个日志窗口里**】
```

### 7.3 ⭐⭐⭐ **"一次交换被尝试两次并被两个模拟原生调用方的测试阻止，而那个本该确认它的冲刺签名不在那个日志窗口里"**

**✅ 这是本报告里**最诚实的一条"**一个未解决的问题【被【一个测试【挡住**"**。**

**✅ 与 §465 的"注释说 REFUSES 而代码不拒绝"**——**不同**（那是一个**缺陷**，这是一个**诚实的待决**）。

**⇒ 三层**：
```text
一个测试【模拟【原生调用方**】⇒ **⇒ 所以【它【编码【一个**假设**】
⇒ **⇒ 而【那个假设【正是【那个未解决的问题**】
⇒ **⇒ 所以【那个测试【阻止【那个修复**，而不是【验证**它**】
```

**✅ ⭐⭐⭐ **"那个测试阻止那个修复，而不是验证它"** —— 一个**极精确的判据**。

**✅ 与 §469 的"刀BF 的回滚（往返校验失败）"**——**同族**（**第四次"一个**测试【挡住【一个**修复**"**）。

**⇒ 三层**：
```text
§463  **`刀BF` 【往返校验失败 ⇒ 恢复纯搬运**】
§481  **两个测试【阻止【一次交换**】
⇒ **⇒ 两次"一个**自检验【挡住【一个**未经证实的改动**"**
```

**✅ ⭐⭐⭐ **"一个自检验挡住一个未经证实的改动"两例**。

**⚠ 而"那个冲刺签名【不在那个日志窗口里**"**⇒ **一个**测量失败**。**

**⇒ 十层**：
```text
若【那个签名【在**】⇒ **⇒ 一个**判决性**的证据**
而【它【不在**】⇒ **⇒ 所以【那个测量【无结论**
⇒ **⇒ 而【代码【保持【一个**有争议**的猜测**
```

**✅ ⭐⭐⭐ **"那个测量无结论，所以代码保持一个有争议的猜测"** —— 一个**诚实的现状**。

**✅ 而"`MaximumEntityAnimationIndex`（十二位）"**⇒ **那个修好了的部分**。**

**⇒ 三层**：
```text
修好的 ⇒ **位宽（`11 → 12`）**
未修的 ⇒ **哪个偏移是 legs、哪个是 torso**
⇒ **⇒ 所以【一个**类型**的问题【解决了，一个**语义**的问题【没有**
```

**✅ ⭐⭐⭐ **"一个类型的问题解决了，一个语义的问题没有"**。

## 八、**那个 `event` 的界："一个字节，不是那个宽度表的长度"**

### 8.1 那段

```cpp
// THE BOUND IS A BYTE, NOT THE WIDTH TABLE'S LENGTH. This refused
// `event=1:180` on a live client -- against SvEntityEventCount, which
// was 3.3.3.3's 162 and is 170 here. Codec -94 writes the id as a raw
// byte, and the client's own decoder answers an id past the width table
// with a zero-width parameter instead of refusing, so refusing here made
// this server stricter than the game it is speaking to and blocked the
// player's entityState outright. Print the SLOT as well as the value:
// 0xD0 is this build's third event slot, so which slot matters.
if (result.events[index].event < 0 || result.events[index].event > SvMaximumEntityEventId)
{
    return report("event", std::to_string(index) + ":" + std::to_string(result.events[index].event));
}
```

### 8.2 二十四层

```text
1. **那个界【是【一个字节**】（`0..255`）**⇒ 不是【那个宽度表的长度**（`170`）**
2. ⇒ **⇒ 而【它【在【一个活的客户端上【拒绝了 `event=1:180`**】
3. ⇒ **⇒ 而【那是【对 `SvEntityEventCount`（3.3.3.3 的 `162`，这里 `170`）**】
4. ⇒ **⇒ 因为 codec `-94` 【把那个 id 【写成一个**原始字节**】
5. ⇒ **⇒ 而【客户端自己的解码器【对一个【超过**宽度表的 id**】】
6. ⇒ **⇒ 【用一个零宽的参数回答**】而不是【拒绝**】
7. ⇒ **⇒ 所以【在这里拒绝【让【这个服务器【比【它说话的那个游戏【更严格**】
8. ⇒ **⇒ 而【把那玩家的 `entityState` 【整个**挡住**】
9. ⇒ **⇒ 所以【打印那个槽【以及【那个值**】（**`0xD0` 是这个 build 的第三个事件槽**）
```

### 8.3 ⭐⭐⭐ **"这个服务器比它说话的那个游戏更严格，而把那玩家的 entityState 整个挡住"**

**✅ 与 §477 的"一个比失败更危险的回落"**——**相反**（那里**太宽松**，这里**太严格**）但**同族**（**第五次"一个**偏离对端**"**）。

**⇒ 三层**：
```text
太松 ⇒ **一个错的值【通过**】（**§477 的回落**）
太严 ⇒ **一个对的值【被拒**】（**§481 的 `180`**）
⇒ **⇒ 所以【两个方向【都是【偏离】
```

**✅ ⭐⭐⭐ **"两个方向都是偏离"** —— 而**那个判据【是【对端的行为**"**（**客户端【用【零宽参数**）。

**⚠ 而"`SvEntityEventCount` 从 `162` 到 `170`"**⇒ **一个**表长了 `8` 条**。**

**⇒ 十层**：
```text
3.3.3.3 ⇒ **`162`**
1649370 ⇒ **`170`**
⇒ **⇒ 所以【`+8`**】⇒ **⇒ 而【那个 `180` 【超过了【两者**】
```

**✅ ⭐⭐⭐ **"180 超过了两者"** —— 而**那【正是【为什么【它【触发了【那个**错误的界**"**。**

**✅ 与 §474 的"`0x3A`/`0x3B` 是这个 build 新增的两条"**——**同族**（**第三次"一个**表【在一个 build 上【增长**"**）。

**⚠ 而"`SvMaximumEntityEventId`"**⇒ **✅ 已核实：`.hpp:17` `SvMaximumEntityEventId = 0xFF`（`255`）**，而 **`.hpp:16` `SvEntityEventCount = 170`**（正是注释说的"这里 170"）**。**

**⇒ 三层**：
```text
`SvMaximumEntityEventId = 0xFF = 255` ⇒ **⇒ 所以【那个 `180` 【会【通过** ✓
`SvEntityEventCount = 170` ⇒ **⇒ 而【旧的界【会【在 `170..255` 上【拒绝**】
⇒ **⇒ 所以【两个常量【相差【`85`**】⇒ **⇒ 而【那【正是【"太严**"的那个区间**】
```

**✅ ⭐⭐⭐ **"两个常量相差 85，而那正是『太严』的那个区间"** —— 一个**精确的算术**。

## 九、`SV_ResetNativeEntityState` 的"那个 bootstrap 相等"

### 9.1 那段

```cpp
// CODDIFF(bg_player_to_entity_set_misc): CODOL 0x004131A0 writes the
// current weapon to +0xD0, then normally mirrors it to the presentation
// selector at +0xD2. For WeaponDef +0x488 (decimal 1160) value 3 it
// instead takes playerState +0x344. This reset helper has no WeaponDef
// or complete playerState context, so equality is only the ordinary
// loadout bootstrap. The retained native conversion must replace it
// before special/alternate weapon presentation is considered restored.
// TODO(CODOL): expose the typed +0x344 owner and special WeaponDef
// classification, then remove this bootstrap equality from any state
// that can reach a client before BG_PlayerStateToEntityState runs.
```

### 9.2 二十四层

```text
1. **`0x004131A0` 【把【当前武器【写到 `+0xD0`**】
2. ⇒ **⇒ 然后【通常【把它【镜像到 `+0xD2` 的展示选择器**】
3. ⇒ **⚠ 而【对【`WeaponDef +0x488`（十进制 `1160`）的值 `3`**】
4. ⇒ **⇒ 它【反而【取【`playerState +0x344`**】
5. ⇒ **⇒ 而这个 reset 助手【没有 `WeaponDef` 也没有【完整的** `playerState` 上下文**
6. ⇒ **⇒ 所以【相等**只是【那个普通的**装备引导**
7. ⇒ **⇒ 而【那个保留的原生转换【必须【替换它**】
8. ⇒ **⇒ 在那个特殊/替代的武器展示【被认为【恢复**之前**
```

### 9.3 ⭐⭐⭐ **"相等只是那个普通的装备引导"**

**✅ 与 §475 的"一个缺表的 MP 手雷仍然会伤害，因为那个回退值是结构体自己的默认值"**——**同族**（**第五次"一个**回退【是【一个【有意的**近似**"**）。

**⇒ 三层**：
```text
`+0xD2 = +0xD0` ⇒ **一个**引导**的近似**
而【真值【依赖【`WeaponDef +0x488 == 3`**】（**`1160`**）⇒ **⇒ 一个**特殊**武器**
⇒ **⇒ 所以【那个相等【在【一个类**上是错的**
```

**✅ ⭐⭐⭐ **"那个相等在一个类上是错的"** —— 而**注释【明确标注了那个范围**。**

**⚠ 而 `0x488 = 1160`**⇒ **十进制换算** ✓

**✅ 与 §462 的"`WeaponDef +0x488`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§462  **"测量 `2026-09-02`：正确 `12 24 ** 306 (csg12ss) -> alt 1225`"**（**一个武器切换**）
§481  **`WeaponDef +0x488` 的值 `3` ⇒ 【取【`playerState +0x344`**】
⇒ **⇒ 所以【那个 `3` 【是【一个**武器类的判别子**】
```

**✅ ⭐⭐⭐ **"那个 3 是一个武器类的判别子"** —— 而**§474 的 `cmp [ecx+0x48C -> 0x598], 5 -> 8`** **同族**（**第四次"一个**武器判别子**"**）。

**⇒ 归纳**：
```text
§474  **`WeaponDef +0x598` 的判别子（`5 → 8`）⇒ 决定【开火事件的两支**】
§481  **`WeaponDef +0x488` 的值 `3` ⇒ 决定【展示武器【取自【`ps+0x344`**】
⇒ **⇒ 两个**不同的判别子【两个不同的**后果**】
```

**✅ ⭐⭐⭐ **"两个不同的判别子两个不同的后果"**。

## 十、**`SvNativeEntityState` 的四个特殊成员**

### 10.1 那段

```cpp
SvNativeEntityState(const SvNativeEntityState &other) { *this = other; }
SvNativeEntityState(SvNativeEntityState &&other) noexcept { *this = other; }
SvNativeEntityState &operator=(const SvNativeEntityState &other)
{
    if (this == &other) return *this;
    bytes = other.bytes;
    secureOriginAddressBound = other.secureOriginAddressBound;
    relocateSecureOriginWords(*this, other);
    return *this;
}
SvNativeEntityState &operator=(SvNativeEntityState &&other) noexcept { return *this = static_cast<const SvNativeEntityState &>(other); }
```

### 10.2 二十四层

```text
1. **四个特殊成员【全部【委托给【那个拷贝赋值**】
2. ⇒ **⇒ 而【那个拷贝赋值【三步**：`bytes` / `bound` / **重绑**
3. ⇒ **⇒ 所以【那个重绑【在【四条路径上【都被执行**】
4. ⇒ **⇒ 而【移动【也【走【拷贝**】（**因为【那个地址【必须**重绑**）
```

### 10.3 ⭐⭐⭐ **"移动也走拷贝，因为那个地址必须重绑"**

**✅ 与 §468 的"`unique_ptr` 保证一个已发布的资产永不移动"**——**相反**（那里**避免移动**，这里**移动【必须【重绑**）但**同族**（**第六次"一个**地址依赖【支配【所有权**"**）。

**⇒ 三层**：
```text
§468  **一个资产的 `storage` 【永不移动**】（**所以【`unique_ptr`**）
§481  **一个 `entityState` 【可以移动，但【重绑**】（**所以【一个自定义的 move**）
⇒ **⇒ 两次"一个**地址依赖【决定【一个**所有权策略**"**
```

**✅ ⭐⭐⭐ **"一个地址依赖决定一个所有权策略"两例**。

**⚠ 而"`operator=(&&)` 委托给【`operator=(const&)`**"**⇒ **一个**正确的**实现**。**

**⇒ 十层**：
```text
若【移动【真的"移动"**（换指针）⇒ **⇒ 那个地址【变了【但没有重绑**】⇒ **⇒ 静默**的错误**
若【移动【拷贝 + 重绑**】⇒ **⇒ 正确**】
⇒ **⇒ 所以【那个委托【是【必须的**】
```

**✅ ⭐⭐⭐ **"那个委托是必须的"**。

## 十一、关键结论

1. **⭐⭐⭐ "把 3.3.3.3 的偏移写进这个 build 的 entityState 比读一个错的值更糟：`0xD0` 在这里是一个事件槽（codec `-94`），所以那个武器索引走进了**一个事件字段**，而**每一帧发射事件**"`** ⇒ **"写比读更糟，因为写会产生新的行为"`** —— 与 §474 的"静默失败"**相反**；而 `legsAnim`/`torsoAnim` **在线上从 `11` 位变宽到 `12` 位**。
2. **⭐⭐⭐ `entityState_s` 的两次增长**：`0x110 → 0x118`（独立验证 `+8`），**一个 `16` 位字段在 `0x60`（`+4`）与一个 `dword` 在 `0xA4` 之前（再 `+4`）**；而那个映射是**两张 `ET_PLAYER` 网络字段表按 `(bits, codec)` 对齐**，三个连续 `16` 位字段在 `0x60`/`0x64`/`0x68` 的歧义**由 `BG_PlayerStateToEntityState`（`sub_4131A0` ↔ `sub_411360`）的逐指令读写解决**（`es+96/es+100` 对 `es+100/es+104` ⇒ `0x60→0x64`、`0x64→0x68`，新的在 `0x60`）—— **"一个结构的歧义由一个更低的层解决"**（与 §470 同族）。
3. **⭐⭐⭐ "二十六项，一个 `return std::nullopt`"：每一个界都是关于**这个 build** 的主张，而"一个不命名任何项的拒绝正是那个形状，而那个形状在这个项目的 pinned usercmd 队列上花掉三个周期"`** ⇒ **"让那个合取说出哪一项拒绝了以及用什么值"`** ⇒ 而**"那个报告器被声明在第一个拒绝之前，因为三个返回坐落在那个旧 lambda 之前而什么也没说"`** —— **"那个位置是一个行为"**（与 §467 的 `++ordinal` 同族）；去重是**一个函数局 `static std::string` 含 `term=value`** ⇒ **正确**（因为那个 `term=value` 是一个**全局空间**），与 §437 的 `LastCommitRefusal`（含 `client=`）**一个精确的对照** —— **"由被追踪的东西是不是每客户端决定"**（与 §474 判据一致）。
4. **⭐⭐⭐ `decodeSecureOrigin` 的地址绑定加密**：`encoded ^ fieldAddress ^ ~key` ⇒ **"一个 C++ 值拷贝会破坏它"**；而修法是 `encoded ^= sourceAddress ^ destinationAddress` ⇒ **"换一个地址只需再 XOR 一次两个地址的差，所以那个明文保持不变"`**（`~key` 在重绑时被消掉）。与 §468 的"一个已发布的资产必须永不移动"同族 —— **"一个地址依赖使拷贝成为一个必须处理的"**。
5. **⭐⭐⭐ `+0xA4` 那个"潜伏的击杀"：28 位（不是 3.3.3.3 的 `0x1FFF`）——"在 `0x1FFF` 上它**拒绝了整个 entityState 投影**，只在引擎在 `+0xA4` 上放了一个真实值那一刻；那是一个**潜伏的击杀**，不是一个被夹的字段"`** —— 与 §463 的"一个 bug 只在另一个被修好之后才暴露"同族。而**"这是那个界的第四份副本，也是最后一份；28 位，不是 3.3.3.3 的 13 —— 而那个 `uint16_t` 参数在检查甚至还没跑之前就静默截断了任何更宽的值"`** —— **一个极精确的类型缺陷**（`> 0x3FF` 写九处 → 这里**多了一个"检查无效"的失败模式**）。
6. **⭐⭐⭐ `legs/torso` 的两次尝试两次回滚**：三个来源**互相矛盾**（① 拷贝器 ⇒ legs `+0xD4`/torso `+0xD8`；② 注解集 + 拷贝器 ⇒ torso `+0xD4`/legs `+0xD8`，**而①与它自己的前提矛盾**；③ 注解集 + `+8` 位移 ⇒ torso `+0xDC`/legs `+0xE0`），代码选的是 **`Legs +0xDC` / `Torso +0xE0`**（③ 的反相）；**"一次交换被尝试两次并被两个模拟原生调用方的测试阻止，而那个本该确认它的冲刺签名不在那个日志窗口里"`** ⇒ **"那个测试阻止那个修复，而不是验证它"`** —— 与 §463 的 `刀BF` 同族；**"一个类型的问题（位宽）解决了，一个语义的问题（哪个偏移）没有"**。
7. **⭐⭐⭐ 那个 `event` 的界**：**"那个界是一个字节（`0..255`），不是那个宽度表的长度"`** —— 它曾在活客户端上**拒绝了 `event=1:180`**（对照 `SvEntityEventCount`，3.3.3.3 的 `162`、这里 `170`）；因为 **codec `-94` 把 id 写成一个原始字节，而客户端自己的解码器对一个超过宽度表的 id 用零宽参数回答而不是拒绝** ⇒ **"在这里拒绝让这个服务器比它说话的那个游戏更严格，而把那玩家的 entityState 整个挡住"`** —— **"两个方向都是偏离"**（太松 §477 / 太严 §481）。
8. **⭐⭐⭐ `SV_ResetNativeEntityState` 的"相等只是那个普通的装备引导"`**：`0x004131A0` 把当前武器写 `+0xD0` 然后通常镜像到 `+0xD2`，**而对 `WeaponDef +0x488`（`1160`）的值 `3` 它反而取 `playerState +0x344`** ⇒ 那个相等**在一个武器类上是错的**；注释**明确标注**了这个范围与 TODO —— 与 §474 的 `WeaponDef +0x598` 的判别子（`5 → 8`）**同族**（两个不同的判别子、两个不同的后果）。
9. **⭐⭐⭐ 四个特殊成员全部委托给拷贝赋值**（`bytes` / `bound` / 重绑）⇒ **"移动也走拷贝，因为那个地址必须重绑"`** —— 与 §468 的 `unique_ptr` **相反但同族**（**"一个地址依赖决定一个所有权策略"**）。
10. **⭐⭐ 那个 `reporter` 的去重是"一个持续的拒绝只打印一次，而换一个值会再打印一次"`**（`if (details != reported)`）。

## 十二、`sv_native_entitystate_mp.cpp` 全文件总览

**`520` 行。**

**`26` 个偏移常量**：
```text
0x00 number          0x04 eType            0x08 eFlags
0x0C/0x10/0x14 pos trajectory type/time/duration
0x18/0x1C/0x20 origin[3]    0x24/0x28/0x2C pos trDelta[3]
0x30/0x34/0x38 ang trajectory type/time/duration
0x3C/0x40/0x44 angles[3]    0x48/0x4C/0x50 ang trDelta[3]
0x54 playerSizeScale 0x5C movementDir      0x64 offhand weapon
0x68 coKnifeStats    0x7C time2 (7 bits)   0x8C groundEntity
0x9C modelIndex      0xA0 clientNum        0xA4 unknownA0 (28 bits)
0xAC solid           0xB4 eventSequence    0xB8 events[]
0xD8 weaponAssetIndex 0xDA presentationWeaponAssetIndex
0xDC legsAnim        0xE0 torsoAnim        0xE8 unknownE0
```

**六个界**：`MaximumEntityNumber = 2047` / `MaximumEntityFlags = 0x3FFFFFFF` / `MaximumWeaponAssetIndex = 0x7FF` / `MaximumTime2 = 0x7F` / `clientNum ≤ 0x3F` / `unk00A0 ≤ 0x0FFFFFFF`。

**`7` 个函数**：`writeValue` / `readValue` / `decodeSecureOrigin` / `relocateSecureOriginWords` / `readProjection` / 四个特殊成员 / `SV_SetNativeEntityStateSolid` / `…ModelIndex` / `…PlayerSizeScale` / `…UnknownA0` / `SV_MarkNativeEntityStateSecureOriginBound` / `SV_ResetNativeEntityState` / 两个 `SV_ReadNativeEntityState`。

**`27` 条具名拒绝**（`26` 项 + `secureOriginAddressUnbound`）。

**`8` 个反汇编锚点**：`sub_4131A0`/`sub_411360`（`BG_PlayerStateToEntityState`）、`0x0041321C`/`0x00413228`（那两个字段拷贝）、`0x00413360`（`BG_PlayerToEntity_SetTrajectory`）、`0x004131A0`（`BG_PlayerToEntity_SetMisc`）、`0x00E60558`（body-part 表）、`sub_AB31A0`。

## 十三、未闭合点

- `legs` 与 `torso` 到底哪个在 `+0xDC`、哪个在 `+0xE0`（注释明确说等一次受控测量）。
- `unk00A0`（`+0xA4`）的语义（28 位）。
- `+0x344` 的 `playerState` 字段（哪个武器类属性）。
- `SvNativeEntityState` 的 `Size` 模板参数值（`alignas(uint32_t) std::array<std::byte, Size>`）。
- 下一个文件：`sv_scoreboard_mp.cpp`（`23,030` 字节）。

**已核实（本轮）**：`SvEntityEventCount = 170`（`.hpp:16`）、`SvMaximumEntityEventId = 0xFF = 255`（`.hpp:17`）⇒ **那个 `180` 恰好落在两者之间的 `170..255` 区间**，正是"太严"的那个窗口。`MaximumEntityAnimationIndex = 0xFFF`（`.hpp:122`）⇒ **`12` 位**，与注释"`legsAnim`/`torsoAnim` 也从 `11` 位变宽到 `12` 位"**精确一致**（`0xFFF = 4095` ⇒ 需要 `12` 位，而 `0x7FF = 2047` 是 `11` 位）。
