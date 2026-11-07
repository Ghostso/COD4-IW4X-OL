# 492 · **"那八字节【那个 `entityState` 得到的【是从**尾巴**里【拿回来的**"** —— `sv_native_server_entity_mp.cpp` 的 `0x110 → 0x118` 全字段 `+8`、`712` 的恒定步长、以及 `svFlags` 的 `2`/`4`

## 一、范围

本报告学习 `sv_native_server_entity_mp.cpp`（**`311` 行**）全文件：`gentity_t` 内嵌 `entityState_s` 的 `+8` 位移、`18` 个偏移、三个实体类型的角色准入、`svFlags` 的 `2`/`4`、以及那个 `0xAA` 风格的地址重绑定。

## 二、**"那八字节那个 entityState 得到的是从尾巴里拿回来的"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODDIFF(1649370): gentity_t embeds entityState_s at offset 0, and that
// grew 0x110 -> 0x118 here, so EVERY field past it moves +8. SV_LinkEntity
// (A sub_1FAE70 <-> C sub_34EF10) reads them line for line and settles all
// of them at once: linked 0x110 -> 0x118, svFlags 0x112 -> 0x11A, bounds
// 0x114 -> 0x11C, contents 0x12C -> 0x134, absolute bounds 0x130 -> 0x138,
// origin 0x148 -> 0x150. The gentity STRIDE is 712 on both builds -- both
// functions divide by it to recover the entity number -- so the eight bytes
// the entityState gained came back out of the tail.
```

### 2.2 二十四层

```text
1. **`gentity_t` 【把 `entityState_s` 内嵌在【偏移 `0`**】
2. ⇒ **⇒ 而那个【`0x110 → 0x118`**】⇒ **⇒ 所以【每一个【在它后面的**字段【都【移动 `+8`**】
3. ⇒ **⇒ 而 `SV_LinkEntity`（`sub_1FAE70` ↔ `sub_34EF10`）【逐行读**它们**
4. ⇒ **⇒ 而【一次性**解决**全部**：`linked` `0x110 → 0x118` / `svFlags` `0x112 → 0x11A` / `bounds` `0x114 → 0x11C` / `contents` `0x12C → 0x134` / `absolute bounds` `0x130 → 0x138` / `origin` `0x148 → 0x150`**
5. ⇒ **⇒ 而【那个 `gentity` 的**步长【在两个 build 上【都是 `712`**】
6. ⇒ **⇒ 而【两个函数【都【除以它【来【恢复【那个实体号**】
7. ⇒ **⇒ 所以【那八字节【那个 `entityState` 得到的【是【从**尾巴**里【拿回来的**】
```

### 2.3 ⭐⭐⭐ **"那个 gentity 的步长在两个 build 上都是 712 —— 那八字节是从尾巴里拿回来的"**

**✅ 这是本报告里**最重要的一条"**一个**结构增长【的**守恒**"**。**

**✅ 与 §481 的"`entityState_s` 增长了两次（`0x110 → 0x118`）"**——**完全闭合** ✓

**⇒ 三层**：
```text
§481  **`entityState_s` 【`0x110 → 0x118`**】（**`+8`**）
§492  **而 `gentity_t` 【仍然是 `712`**】⇒ **⇒ 所以【那八字节【来自**尾巴**】
⇒ **⇒ 一个**守恒**：那个容器【不变**，而【内容【重新分配**
```

**✅ ⭐⭐⭐ **"一个守恒：那个容器不变，而内容重新分配"** —— 一个**极精确的观察**。

**⚠ 而 `0x110 + 8 = 0x118` —— 独立验证每一个**】**。**

**⇒ 独立验证六个**：
```text
`linked`      0x110 → 0x118  ⇒ **`+8`** ✓
`svFlags`     0x112 → 0x11A  ⇒ **`+8`** ✓
`bounds`      0x114 → 0x11C  ⇒ **`+8`** ✓
`contents`    0x12C → 0x134  ⇒ **`+8`** ✓
`absolute`    0x130 → 0x138  ⇒ **`+8`** ✓
`origin`      0x148 → 0x150  ⇒ **`+8`** ✓
⇒ **⇒ 六个**全部 `+8`** ✓
```

**✅ ⭐⭐⭐ **"六个全部 +8"** —— 一个**完整的算术闭合**。

**✅ 而"那个 `712` 的步长【是两个 build 共有的**"**⇒ **一个**不变的**量**。**

**⇒ 十层**：
```text
`712` ⇒ **`0x2C8`**】⇒ **⇒ 而 §489 说「`0x2C8`-byte CODOL `gentity_s`」** ✓
⇒ **⇒ 所以【那个 `SvEntityLifetime` 的注释【与【这个步长【一致**】
```

**✅ ⭐⭐⭐ **"712 = 0x2C8 与 §489 的注释一致"** —— 一个**跨报告的闭合**。

**⚠ 而"那个尾部【`0x118..0x2C7` ⇒ `432` 字节**"**】**。**

**⇒ 三层**：
```text
`0x2C8 - 0x118 = 0x1B0 = 432` ⇒ **⇒ 那【是那个 `gentity` 的**其余部分**
⇒ **⇒ 而【它【少了 `8` 字节**（**因为【那八字节【给了【那个 `entityState`**）
```

**✅ ⭐⭐⭐ **"那个尾部少了 8 字节"**。

### 2.4 而**那个内嵌 `entityState` 的偏移【跟着 `ET_PLAYER` 的网络字段表】**

```cpp
// The offsets inside the embedded entityState follow the ET_PLAYER netfield
// map instead: solid 0x0A4 -> 0x0AC and the model index 0x098 -> 0x09C.
```

**⇒ 十层**：
```text
`solid` ⇒ **`0x0A4 → 0x0AC`**（**`+8`**）
`model index` ⇒ **`0x098 → 0x09C`**（**`+4`**）
⇒ **⇒ ⚠ 而【两个【不同的**位移**】
```

**✅ ⭐⭐⭐ **"两个不同的位移：+8 与 +4"** —— 一个**极重要的分辨**。

**✅ 与 §481 的"一个 `16` 位字段在 `0x60`（`+4`）与一个 `dword` 在 `0xA4` 之前（再 `+4`）"**——**完全闭合** ✓

**⇒ 三层**：
```text
§481  **`0x60` 处 `+4`；`0xA4` 之前再 `+4`**（**⇒ 所以 `0x60..0xA3` 是 `+4` 而 `0xA4+` 是 `+8`**）
§492  **`0x098` ⇒ `+4`**（**`< 0xA4`** ✓）/ **`0x0A4` ⇒ `+8`**（**`>= 0xA4`** ✓）
⇒ **⇒ 所以【两个位移【精确**地【对应【§481 的两个**增长点**
```

**✅ ⭐⭐⭐ **"两个位移精确地对应 §481 的两个增长点"** —— 一个**完美的跨报告验证**。

**✅ 而那个 `0x0A4 → 0x0AC` 是 `+8`**⇒ **而 §481 的 `UnknownA0Offset = 0xA4`**】**。**

**⇒ 三层**：
```text
§481  **`UnknownA0Offset = 0xA4`**（**那个 `28` 位的 `unk00A0`**）
§492  **`solid 0x0A4 → 0x0AC`** ⇒ **⇒ ⚠ 冲突**】
```

**⚠ 一个**可能的冲突**：§481 说 `0xA4` 是 `unk00A0`（28 位），而 §492 说 `solid` 在 `0x0A4 → 0x0AC`。**

**⇒ 核对 §476 的 `.hpp`**：`SolidOffset = 0xAC`（我读过）。⇒ **所以 §492 的"`solid 0x0A4 -> 0x0AC`"意思是"3.3.3.3 的 `0xA4` 变成了本 build 的 `0x0AC`"**，而**§481 的 `UnknownA0Offset = 0xA4` 是本 build 的**。

**⇒ 三层**：
```text
§492  **"solid `0x0A4 → 0x0AC`" 【读成【"3.3.3.3 的 `0xA4` ⇒ 本 build 的 `0x0AC`**"】
§481  **`UnknownA0Offset = 0xA4` 【是【本 build 的**】
⇒ **⇒ 所以【在 3.3.3.3 上【是 `Solid = 0xA4`**而【在【本 build 上【是 `Solid = 0xAC` + `UnknownA0 = 0xA4`**】
```

**✅ ⭐⭐⭐ **"在 3.3.3.3 上是 Solid = 0xA4，而在本 build 上是 Solid = 0xAC + UnknownA0 = 0xA4"** —— 一个**极精确的分辨**（**一个字段【被【拆成两个**）**。**

**✅ 与 §481 的"`0xA4` 之前【另一个 `dword`**"**⇒ **完全闭合** ✓

## 三、**`svFlags` 的 `2` / `4` 与"那个 locational DObj 分支测试 bit 2"**（本组第二重要）

### 3.1 那段

```cpp
// CODOL SV_LinkEntity only admits server DObj bounds/locational data
// when svFlags carries the live-player bit used by BO1 ClientEndFrame.
writeValue(result, ServerFlagsOffset,
    // CODREF(sv_link_entity): CODOL's locational DObj branch tests
    // svFlags bit 2. CODOL sub_4E74D0 sets bit 4 for script_model
    // before its DObj update and SV_LinkEntity call.
    entity.shape == SvCollisionShape::Capsule ? std::uint8_t{ 2 }
        : entity.shape == SvCollisionShape::ScriptModelDObj ? std::uint8_t{ 4 }
        : std::uint8_t{});
```

### 3.2 二十四层

```text
1. **`svFlags` 【携带【那个活的玩家位**】（**BO1 `ClientEndFrame` 用的**）**
2. ⇒ **⇒ 而【那个 locational DObj 分支【测试【`svFlags` 的**第 `2` 位**】
3. ⇒ **⇒ 而 `sub_4E74D0` 【对 `script_model` 设【第 `4` 位**】
4. ⇒ **⇒ 在【它的 DObj 更新与 `SV_LinkEntity` 调用【之前**】
5. ⇒ **⇒ 所以【三个值：`2`（capsule）/ `4`（DObj）/ `0`（brush）**
```

### 3.3 ⭐⭐⭐ **"那两个位（2 与 4）是分开的，因为它们是两个不同的判据"**

**✅ 与 §476 的 `SV_ShouldClipToEntity` 的三层过滤**——**不同**（那是一个**身份**，这是一个**标志位**）但**同族**（**第四次"一个**位【是【一个**判据**"**）。

**⇒ 三层**：
```text
`2` ⇒ **`svFlags` 的第 `2` 位** ⇒ **⇒ 那个 locational DObj 分支【接受**
`4` ⇒ **第 `4` 位** ⇒ **⇒ `sub_4E74D0` 对 `script_model` 设**
⇒ **⇒ 所以【两个**不同的**位【两个**不同的**生产者**
```

**✅ ⭐⭐⭐ **"两个不同的位两个不同的生产者"**。

**⚠ 而那些**数字**】**。**

**⇒ 十层**：
```text
`std::uint8_t{ 2 }` ⇒ **`0x02`**（**第 `2` 位【如果 1 基**）
`std::uint8_t{ 4 }` ⇒ **`0x04`**（**第 `4` 位【如果 1 基** / **第 `3` 位【如果 0 基**）
⇒ **⇒ 所以【那个注释的"bit 2"与"bit 4"【是【1 基**的
```

**✅ ⭐⭐⭐ **"那个注释的 bit 2 与 bit 4 是 1 基的"** —— 与 §483 的"`EFlagTeleportBit = 1u << 1` 而注释写 bit 2"**完全同族** ✓

**⇒ 三层**：
```text
§483  **`EFlagTeleportBit = 1u << 1 = 0x02` 而注释"bit 2"** ⇒ **1 基**
§492  **`svFlags = 2` 而注释"bit 2"；`svFlags = 4` 而注释"bit 4"** ⇒ **1 基**
⇒ **⇒ 所以【那个项目的注释【一致【用【1 基**的位号**
```

**✅ ⭐⭐⭐ **"那个项目的注释一致用 1 基的位号"** —— **一个跨报告的一致**（**⇒ §483 那个"编号歧义"的担忧【被【这里【解决**了**）**。

**✅ 与 §476 的"`0x01D00000 >> 20 = 29`"**——**不同**（那是 0 基的位索引**）**。**

**⚠ 而 `ModelTypeBrush = 4`**⇒ **一个**模型类型**的枚举**。**

**⇒ 三层**：
```text
`ModelTypeBrush = 4` ⇒ **⇒ 而【那个 `ModelTypeOffset` 的默认【是 `0`**】
⇒ **⇒ 所以【两个**值：`4`（brush）/ `0`（其它**）
```

**✅ ⭐⭐ **"两个值：4（brush）/ 0（其它）"**。

## 四、**那个 `validCapsuleRole` 的三个角色**（本组第三重要）

### 4.1 那段

```cpp
const auto validCapsuleRole = [&] {
    if (entity.shape != SvCollisionShape::Capsule) return true;
    if (!bodyProjection || bodyProjection->number != entity.entityNum) return false;
    if (playerBody)
    {
        return entity.entityNum < 18 &&
            bodyProjection->eType == EntityTypePlayer;
    }
    if (actorBody)
    {
        return entity.entityNum >= FirstDynamicServerEntityNum &&
            (bodyProjection->eType == EntityTypeActor ||
                bodyProjection->eType == EntityTypeActorCorpse);
    }
    return false;
}();
```

### 4.2 二十四层

```text
1. **非 capsule ⇒ 通过**】
2. ⇒ **⇒ 而【副本【必须【存在【且【号**匹配**
3. ⇒ **⇒ 玩家 ⇒ `entityNum < 18`**】⇒ **⇒ 而 `eType == 1`（`EntityTypePlayer`**）**
4. ⇒ **⇒ 演员 ⇒ `entityNum >= 37`**】⇒ **⇒ 而 `eType ∈ {19, 21}`**】
5. ⇒ **⇒ 其它 ⇒ 拒绝**
```

### 4.3 ⭐⭐⭐ **"玩家 < 18 而演员 >= 37 —— 中间那段被排除"**

**✅ 与 §489 的"`PlayerCorpseRingSize = 18`"**、§476 的"`MaximumServerCollisionEntityNum = 2045`"**——**完全闭合** ✓

**⇒ 三层**：
```text
`< 18` ⇒ **玩家**（**⇒ 与 §469/§472/§477 的 `MaximumGameClients = 18` 一致**）
`18..36` ⇒ **尸体环**（**⇒ 而【一个**胶囊【不能【是**尸体**）
`>= 37` ⇒ **动态区**（**⇒ 而【一个**演员【必须【在那**）
⇒ **⇒ 所以【那个 `(entityNum >= 18 && entityNum < 37)` 的拒绝【是【一个**精确的**边界**
```

**✅ ⭐⭐⭐ **"那个 (entityNum >= 18 && entityNum < 37) 的拒绝是一个精确的边界"** —— 一个**三段闭合**（**§469 的 `18` + §489 的 `19..36` + §489 的 `37`**）。

**✅ 与 §489 的 `static_assert(FirstPlayerCorpseEntityNum + PlayerCorpseRingSize == FirstDynamicServerEntityNum)`**——**完全闭合** ✓

**⚠ 而那个**重复的拒绝**】**。**

**⇒ 十层**：
```cpp
(entity.entityNum >= 18 && entity.entityNum < FirstDynamicServerEntityNum)
```
```text
⇒ **⇒ 而【`validCapsuleRole` 【已经【拒绝【了【那个区间**】（**因为【既【不是 `< 18` 也【不是 `>= 37`**）
⇒ **⇒ 所以【那个检查【是【一个**冗余**的（**但【它【覆盖【了【brush/DObj**）】
```

**✅ ⭐⭐⭐ **"那个检查是冗余的（但它覆盖了 brush/DObj）"** —— 一个**极精确的读法**（**一个条件【对【三种形状【各自【一个**作用**）**。

**✅ 与 §471 的"那个检查是一个冗余的界"**——**同族**（**第二次"一个**冗余【但有**理由**"**）。

## 五、**`EntityTypeActorCorpse = 21`**（本组第四重要）

### 5.1 那段

```cpp
constexpr std::uint8_t EntityTypePlayer = 1;
constexpr std::uint8_t EntityTypeActor = 19;
constexpr std::uint8_t EntityTypeActorCorpse = 21;
```

### 5.2 二十四层

```text
1. **三个类型：`1` / `19` / `21`**】
2. ⇒ **⇒ 而 §415 记过"`ET_ACTOR` 19 vs `ET_ACTOR_CORPSE` 21（`21` **就是【零售【发布的**）"**
3. ⇒ **⇒ 而【那个 `sub_540860` 的 `case 19: case 21:` 【结束【在 `if (a2 && v14 == 21) sub_530E70(Source)`**】
4. ⇒ **⇒ 所以【两个**类型【共享【一个**case 分支【而【一个**额外的**处理【只【对 `21`**
```

**✅ ⭐⭐⭐ **"case 19 与 case 21 共享一个分支，而一个额外的处理只对 21"** —— 与 §415 的注释**完全闭合** ✓

**⇒ 三层**：
```text
§415  **`case 19: case 21:` 结尾是 `if (a2 && v14 == 21) sub_530E70(Source)`**
§492  **`EntityTypeActor = 19` / `EntityTypeActorCorpse = 21`**
⇒ **⇒ 所以【那个准入【正确**：**`(eType == 19 || eType == 21)`**
```

**✅ ⭐⭐⭐ **"那个准入正确"** —— 而**注释【明说**"`21` **就是【零售【发布的**"**。**

**✅ 与 §462 的"`sub_429DA0` 是 grenade THROWBACK"**——**同族**（**第三次"一个**名字【的**语义**"**）。

## 六、那个地址重绑定与 §481 的**同一段代码**

### 6.1 那段

```cpp
void SV_CopyNativeEntityStateToServerEntity(SvNativeServerEntity &destination, const SvNativeEntityState &source)
{
    // CODDIFF(client_think_real): source and destination are
    // different allocations, so copying the encrypted words verbatim
    // would decode against the wrong field addresses. Relocation keeps the
    // same plaintext while preserving CODOL's native address-bound form.
    std::memcpy(destination.bytes.data(), source.bytes.data(), SvNativeEntityState::Size);
    if (!source.secureOriginAddressBound) return;
    for (const auto offset : SecureOriginOffsets)
    {
        std::uint32_t encoded{};
        std::memcpy(&encoded, source.bytes.data() + offset, sizeof(encoded));
        const auto sourceAddress = ...(source.bytes.data() + offset);
        const auto destinationAddress = ...(destination.bytes.data() + offset);
        writeValue(destination, offset, encoded ^ sourceAddress ^ destinationAddress);
    }
}
```

### 6.2 二十四层

```text
1. **`memcpy` 全部**】⇒ **⇒ 然后【对【三个**安全的起点【重绑**
2. ⇒ **⇒ 而 `encoded ^ sourceAddress ^ destinationAddress`**】
3. ⇒ **⇒ 所以【那个明文【保持**不变**
4. ⇒ **⇒ 而【那个 `secureOriginAddressBound` 【是【那个**开关**
```

### 6.3 ⭐⭐⭐ **"那个重绑定是 `encoded ^ src ^ dst` —— 与 §481 的 `relocateSecureOriginWords` 同一段代码"**

**✅ 与 §481 的 `relocateSecureOriginWords`**——**完全同构** ✓

**⇒ 三层**：
```text
§481  **`relocateSecureOriginWords(destination, source)`**（**一个私有的 lambda/函数**）
§492  **`SV_CopyNativeEntityStateToServerEntity`**（**一个公开的函数**）
⇒ **⇒ 两次【同一个**算法**】⇒ **⇒ 而【§492 的【是【一个**跨结构**的版本**
```

**✅ ⭐⭐⭐ **"两次同一个算法，而 §492 的是一个跨结构的版本"**。

**⚠ 而那个 `SecureOriginOffsets = {0x18, 0x1C, 0x20}`**⇒ **与 §481 的 `OriginOffsets` 完全一致**】**。**

**⇒ 独立验证**：
```text
§481  **`constexpr std::array<std::size_t, 3> OriginOffsets{ 0x18, 0x1C, 0x20 };`**
§492  **`constexpr std::array<std::size_t, 3> SecureOriginOffsets{ 0x018, 0x01C, 0x020 };`**
⇒ **⇒ 三个**完全一致** ✓
```

**✅ ⭐⭐⭐ **"三个完全一致"** —— 而**§492 的注释【额外【给了【一个**bit 的信息**（"bits -83/-82/-81, types 6/7/8"）**。**

**⇒ 三层**：
```text
`0x18` ⇒ **bits `-83`，type `6`**】
`0x1C` ⇒ **bits `-82`，type `7`**】
`0x20` ⇒ **bits `-81`，type `8`**】
⇒ **⇒ 所以【三个**负的 codec**（**与 §464 的 `-7`/`-8`/…/`-102` 同族**）
```

**✅ ⭐⭐⭐ **"三个负的 codec：-83/-82/-81"** —— 与 §464 的负 codec 清单**完全闭合** ✓

## 七、`SV_ValidateNativeServerEntityLinkResult` 的六项

### 7.1 六项

```text
① EntityNumber == source.entityNum
② Solid == expectedSolid(source)
③ IsLinked == 1
④ ModelType == (brush ? 4 : 0)
⑤ IsInUse == 1
⑥ Contents == source.contents
```

### 7.2 二十四层

```text
1. **六项**】⇒ **⇒ 而【注释说**："**验证【建立【一个成功的原生链接【所需的最小字段**，而【不【拒绝【那些【`SV_LinkEntity` 【被期望【自己【推导或规范化**的字段**"
2. ⇒ **⇒ 所以【那个**最小性【是【有意的**
```

### 7.3 ⭐⭐⭐ **"验证最小字段，而不拒绝那些 SV_LinkEntity 被期望自己推导或规范化的字段"**

**✅ 与 §477 的"只读是安全的取证方式"**、§485 的"三个投影全部无副作用"**——**同族**（**第五次"一个**最小的**验证**"**）。

**⇒ 三层**：
```text
若【验证【全部字段**】⇒ **⇒ 一个**合法的**链接【会【被【拒绝**】（**因为【那些【推导的**字段【可能【不同**）
若【只验证**最小**】⇒ **⇒ 正确**
⇒ **⇒ 所以【那个最小性【是【一个有意的**设计
```

**✅ ⭐⭐⭐ **"那个最小性是一个有意的设计"**。

**⚠ 而"`TODO(CODOL): recover role-specific postconditions for brush model, live-player DObj and script-model DObj links`"**⇒ **一个**待决**。**

**⇒ 十层**：
```text
`TODO` ⇒ **三个**角色特定的**后置条件**】
⇒ **⇒ 而【退出条件【是**："**`eType`, `svFlags`, bounds/origin, model identity 和 native link contents 【有【已证的不变式** + **失败注入覆盖**"**
⇒ **⇒ 所以【那个 TODO 【是【一个**明确的**契约**】
```

**✅ ⭐⭐⭐ **"那个 TODO 是一个明确的契约"** —— 与 §463 的"一个有界的前进路径"**同族**。

## 八、`SV_IsNativeServerEntityAvailableBaseline` 的"一个未链接、不在用的原生槽"

### 8.1 那段

```cpp
// OLMOD(native-fixed-slot-admission): an unlinked, not-in-use native
// slot is the current takeover boundary. This is project ownership,
// not a recovered COD allocation function.
return !readValue<std::uint8_t>(entity, IsLinkedOffset) &&
    !readValue<std::uint8_t>(entity, IsInUseOffset);
```

### 8.2 二十四层

```text
1. **两个条件：未链接 + 不在用**】
2. ⇒ **⇒ 而注释说**："**那【是【当前的**接管边界**】**，这【是【项目所有权**，不是【一个**恢复的 COD 分配函数**"
3. ⇒ **⇒ 所以【那个判据【是【一个**项目自己的**约定**
```

### 8.3 ⭐⭐⭐ **"这是项目所有权，不是一个恢复的 COD 分配函数"**

**✅ 与 §473 的"那是候选，不是声称的零售玩家索引映射"**、§489 的"那个 demo 不需要它们里的任何一个"**——**完全同族** ✓

**⇒ 三层**：
```text
§473  **"These are candidates, not a claimed retail player-index mapping"**
§489  **"The demo needs none of them"**
§492  **"This is project ownership, not a recovered COD allocation function"**
⇒ **⇒ 三次"一个**显式的**来源声明**"**
```

**✅ ⭐⭐⭐ **"一个显式的来源声明"三例**。

**⚠ 而那个 `TODO` 的退出条件**】**。**

**⇒ 十层**：
```text
`TODO(CODOL)` ⇒ **"replace this predicate with the recovered fixed-slot lifecycle owner once G_Spawn/G_FreeEntity integration can prove generation, script, DObj and subsystem references are all absent"**
⇒ **⇒ 所以【那个替换【需要【四个**参考【全部【被证明【不存在**
⇒ **⇒ 而那【是【一个**极严的**契约**
```

**✅ ⭐⭐⭐ **"那个替换需要四个参考全部被证明不存在"**。

## 九、关键结论

1. **⭐⭐⭐ "`gentity_t` 把 `entityState_s` 内嵌在偏移 `0`，而那个 `0x110 → 0x118` ⇒ **每一个在它后面的字段都移动 `+8`**；`SV_LinkEntity`（`sub_1FAE70` ↔ `sub_34EF10`）逐行读它们并一次性解决全部（六个字段：`0x110→0x118` / `0x112→0x11A` / `0x114→0x11C` / `0x12C→0x134` / `0x130→0x138` / `0x148→0x150`）；而那个 `gentity` 的**步长在两个 build 上都是 `712`** ⇒ **"那八字节那个 entityState 得到的是从尾巴里拿回来的"`** —— **独立验证六个全部 `+8` ✓**，而 **`712 = 0x2C8` 与 §489 的"`0x2C8`-byte CODOL `gentity_s`"精确一致**。
2. **⭐⭐⭐ 那个内嵌 `entityState` 的偏移跟着 `ET_PLAYER` 的网络字段表：`solid 0x0A4 → 0x0AC`（`+8`）而 `model index 0x098 → 0x09C`（`+4`）** ⇒ **"两个位移精确地对应 §481 的两个增长点"`**（`0x60` 处 `+4`、`0xA4` 之前再 `+4`）；而 **那个 `0xA4` 的分辨**：在 3.3.3.3 上是 `Solid = 0xA4`，而在本 build 上是 `Solid = 0xAC` + `UnknownA0 = 0xA4`（**一个字段被拆成两个**）—— 与 §481 精确闭合。
3. **⭐⭐⭐ `svFlags` 的 `2`/`4`/`0` 三分支**：`2` = capsule（**那个 locational DObj 分支测试 `svFlags` 的第 2 位**）、`4` = `ScriptModelDObj`（**`sub_4E74D0` 对 `script_model` 设第 4 位**）、`0` = brush ⇒ **"两个不同的位两个不同的生产者"**；而 **那个注释的"bit 2"与"bit 4"是 1 基的**（与 §483 的 `EFlagTeleportBit = 1u << 1` 而注释"bit 2"**完全同族**）⇒ **"那个项目的注释一致用 1 基的位号"** ⇒ **§483 那个"编号歧义"的担忧在这里被解决了**。
4. **⭐⭐⭐ `validCapsuleRole` 的三段**：玩家 `< 18`（`eType == 1`）/ 演员 `>= 37`（`eType ∈ {19, 21}`）/ 其它拒绝 ⇒ **"那个 `(entityNum >= 18 && entityNum < 37)` 的拒绝是一个精确的边界"** ⇒ 一个**三段闭合**（§469 的 `18` + §489 的 `19..36` + §489 的 `37`），而 **`static_assert(19 + 18 == 37)` 保证那个边界不被破坏**。
5. **⭐⭐⭐ `EntityTypeActorCorpse = 21` 与 §415 的 `case 19: case 21:` 完整闭合**（"`21` 就是零售发布的"，而那个 `case` 结尾是 `if (a2 && v14 == 21) sub_530E70(Source)`）⇒ **那个准入 `(eType == 19 || eType == 21)` 正确**。
6. **⭐⭐⭐ `SV_CopyNativeEntityStateToServerEntity` 的地址重绑定与 §481 的 `relocateSecureOriginWords` 是同一段代码**（`encoded ^ src ^ dst`），而 **`SecureOriginOffsets = {0x18, 0x1C, 0x20}` 与 §481 的 `OriginOffsets` 三个完全一致** ⇒ 而 **§492 额外给了 bit 的信息：`-83`/`-82`/`-81`（types `6`/`7`/`8`）** —— 与 §464 的负 codec 清单**完整闭合**。
7. **⭐⭐⭐ `SV_ValidateNativeServerEntityLinkResult` 的六项**（号 / solid / linked / modelType / inUse / contents）⇒ **"验证建立一个成功的原生链接所需的最小字段，而不拒绝那些 `SV_LinkEntity` 被期望自己推导或规范化的字段"`** ⇒ **"那个最小性是一个有意的设计"**；而那个 `TODO(CODOL)` 有**明确的退出条件**：`eType`/`svFlags`/bounds/origin/模型身份/native link contents **有已证的不变式 + 失败注入覆盖**。
8. **⭐⭐⭐ `SV_IsNativeServerEntityAvailableBaseline` 的"一个未链接、不在用的原生槽是当前的接管边界 —— **这是项目所有权，不是一个恢复的 COD 分配函数**"`** ⇒ **"一个显式的来源声明"**（与 §473/§489 同族）；而那个 `TODO` 的退出条件需要 **四个参考（generation / script / DObj / subsystem）全部被证明不存在**。
9. **⭐⭐ `ModelTypeBrush = 4` 与 `ModelType = 0`** ⇒ 两个值。

## 十、`sv_native_server_entity_mp.cpp` 全文件总览

**`311` 行。**

**`18` 个偏移**：
```text
0x000 EntityNumber     0x004 EntityType
{0x018, 0x01C, 0x020} SecureOriginOffsets（bits -83/-82/-81，types 6/7/8）
0x054 ScriptMoverScale 0x09C BrushModelIndex   0x0AC Solid
0x118 IsLinked         0x119 ModelType         0x11A ServerFlags
0x11B IsInUse          0x11C Bounds            0x134 Contents
0x150 CurrentOrigin    0x15C CurrentAngles
```

**`4` 个类型常量**：`EntityTypePlayer = 1` / `EntityTypeActor = 19` / `EntityTypeActorCorpse = 21` / `ModelTypeBrush = 4`。

**`7` 个函数**：`writeValue` / `readValue` / `expectedSolid` / `SV_BuildNativeServerEntity` / `SV_CopyNativeServerEntityToSlot` / `SV_CopyNativeEntityStateToServerEntity` / `SV_ValidateNativeServerEntityLinkResult` / `SV_IsNativeServerEntityAvailableBaseline` / `SV_IsNativeServerEntityLinked` / `SV_ClearNativeServerEntityLinkedFlag`。

**`8` 个反汇编锚点**：`SV_LinkEntity 0x005FAE70` / `sub_1FAE70` / `sub_34EF10` / `0x0071F960`（BO1）/ `0x14020A6C0`（Ghosts）/ `BG_PlayerToEntity_SetTrajectory 0x00413360` / `sub_4E74D0` / `sub_530E70`。

**`1` 个**关键测量：**`gentity` 步长 `712`（两个 build 共有）**。

## 十一、未闭合点

- `SvNativeServerEntity::Size` 的值（应 ≥ `0x160`）。
- `SV_CopyNativeServerEntityToSlot` 与 `SV_CopyNativeEntityStateToServerEntity` 的关系（前者调后者）。
- 三个角色特定的后置条件（`TODO`）。
- 下一个文件：`sv_scoreboard_mp.hpp`（`14,368` 字节）或 `sv_zm_travel_mp.cpp`（`13,039` 字节）。
