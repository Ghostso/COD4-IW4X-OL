# 463 · **"`ps+0x10` 在这个 build 上【不是一个可读回的普通 `dword`】"** —— 一个三字受保护值的密码文、`otherFlags=1461489901` 的三次随机、以及 `刀BF` 的回滚

## 一、范围

本报告学习 `sv_native_playerstate_mp.cpp` 1160–1500 行（`refuse` 的收尾、`otherFlags` 的完整病历、`刀BF` 的回滚、`weapon slots` 的诊断、四个 `SV_SetNative*` 的写者）。

## 二、**"`ps+0x10` 在这个 build 上不是一个可读回的普通 `dword`"**（本组最重要的一段）

### 2.1 那段

```php
// ps+0x10 IS NOT A PLAIN DWORD TO READ BACK. On this build it is the first word
// of a three-dword PROTECTED value whose accessor pair lives at ps+0x20/+0x24,
// and the engine writes it through that pair -- so whatever sits there after a
// native stage is ciphertext, not flags. Reading it plaintext gave the server a
// different random otherFlags every frame (`playerstate domain refused
// otherFlags=1461489901`, then 1312251290, then 2934888368), which the snapshot
// frame validator refused, so no snapshot ever reached the client. It only became
// visible when clientThink started committing: while the conversion was still
// refusing, nothing was ever written back and beginFrame's value survived.
//
// ol-mod owns the plaintext. It is written INTO the protected object before each
// native call (writeNativeProtectedPlayerStateFlags) and kept in this DTO across
// it. Reading the engine's own view back would mean calling the GET accessor and
// taking the second dword of the result -- worth doing, but it is another native
// ABI and not one to guess at; `next` already carries the previous value.
```

### 2.2 二十四层

```text
1. **`ps+0x10` 【在这个 build 上【不是一个可读回的普通 `dword`**】**
2. ⇒ **它是【一个三 `dword` 的【受保护值**】的【第一个字**】**
3. ⇒ **而【它的访问器对【住在 `ps+0x20`/`ps+0x24`**】**
4. ⇒ **⇒ 而【引擎【通过那一对**】写它**
5. ⇒ **⇒ 所以【在一次原生阶段之后【坐在那里的任何东西【是【密码文**，不是 `flags`】】**
6. ⇒ **⚠ 【以明文读它**给那个服务器【每帧一个不同的随机 `otherFlags`**】**
7. ⇒ **（`playerstate domain refused otherFlags=1461489901`，然后 `1312251290`，然后 `2934888368`）**
8. ⇒ **⇒ 而【那个快照帧验证器【拒绝了它**】**
9. ⇒ **⇒ 【所以【没有一个快照【到达过客户端**】】**
10. ⇒ **⚠ 而它【只在 `clientThink` 开始提交时【才变得可见**】**
11. ⇒ **⇒ 因为【在转换仍然拒绝的期间，什么也没被写回**而 `beginFrame` 的值【存活下来**】】
12. ⇒ **⇒ 所以【那个 bug 【被掩盖**了一段】**
13. ⇒ **⇒ 【ol-mod 拥有那个明文**】**
14. ⇒ **它【在每次原生调用【之前**被写进那个受保护对象】
15. ⇒ **⇒ 而【在这个 DTO 里【跨过它**保留**
16. ⇒ **⇒ 读引擎自己的视图回【意味着【调用那个 `GET` 访问器【并取结果的第二个 `dword`**】**
17. ⇒ **（**值得做，但它是另一个原生 ABI，不是可以猜的东西**；`next` 已经【携带了前一个值**）**
```

### 2.3 ⭐⭐⭐ **"不管什么坐在那里，在一次原生阶段之后，是密码文而不是 flags"**

**✅ 这是本报告里**最重要的一条"一个字段的读法在 build 之间变了**。**

**✅ 与 §461 的"合并，不要替换：`ps+0x10` 携带引擎的 `flags` 字"**——**完全同族且互补** ✓

**⇒ 三层**：
```text
§461  **写**：`(own & ~mask) | (source & mask)`（**一个合并**）
§463  **读**：**不能读**（**它是密码文**）
⇒ **⇒ 所以【写可以（通过掩码）而【读不行**】
```

**✅ ⭐⭐⭐ **"写可以而读不行"** —— 一个**极精确的不对称**。

**⚠ 而"三次随机的 `otherFlags`"⇒ **三个具体的数**。**

**⇒ 十层**：
```text
`1461489901` ⇒ `0x5719_...`
`1312251290` ⇒ `0x4E38_...`
`2934888368` ⇒ `0xAF01_...`
⇒ **⇒ 三个【看起来随机**的数**
```

**⇒ 让我算一下 `1461489901` 的 hex**：
```text
1461489901 = 0x571B_...  让我精确
1461489901 / 16^7 = 1461489901 / 268435456 ≈ 5.44 ⇒ 高字节 5
⇒ 0x5...
```

**⚠ 我不能精确手算 ⇒ 标注。**

**✅ 而"三个看起来随机的数"⇒ **一个"密码文"的直接证据**。**

**✅ 与 §424 的"`entity free rollback lost FIFO ownership`"**同族（**第八次"精确的错误消息"）。

**⇒ 三层**：
```text
§405  **`resource deadlock would occur`**
§424  **`entity free rollback lost FIFO ownership`**
§463  **`playerstate domain refused otherFlags=1461489901`**
⇒ **⇒ 三次"一个错误消息带一个数**】
```

**✅ ⭐⭐ **"一个错误消息带一个数"三例表**。

### 2.4 ⭐⭐⭐ **"它只在 `clientThink` 开始提交时才变得可见"**

**✅ 这是本报告里**最重要的一条"一个 bug 被另一个 bug 掩盖**。**

**⇒ 三层**：
```text
阶段 A：**转换在拒绝** ⇒ **什么也没写回** ⇒ **`beginFrame` 的值存活** ⇒ **没有可见的症状**
阶段 B：**`clientThink` 开始提交** ⇒ **写回发生** ⇒ **密码文进入** ⇒ **验证器拒绝** ⇒ **没有快照**
⇒ **⇒ 所以【一个 bug 【只在另一个被修好之后**才暴露**】
```

**✅ ⭐⭐⭐ **"一个 bug 只在另一个被修好之后才暴露"** —— 与 §424 的"修好那个代次正是暴露这件事的东西"**完全同族**（**第二次）。

**⇒ 三层**：
```text
§424  **"修好那个代次**正是【暴露这件事**】的东西"
§463  **"它只在 `clientThink` 开始提交时才变得可见**"
⇒ **⇒ 两次"一个修好暴露另一个**】
```

**✅ ⭐⭐ **"一个修好暴露另一个"两例**。

### 2.5 而**"值得做，但它是另一个原生 ABI，不是可以猜的东西"**

**✅ 与 §460 的"`SwaySpeed` 偏移我方未核实，不搬对方数字"**、§462 的"`sub_429DA0` 不是普通枪 alt-mode 的证据"**完全同族**。

**⇒ 三层**：
```text
§460  **"不搬对方数字"**（**因为偏移未核实**）
§462  **"不是证据"**（**因为它是另一个函数**）
§463  **"不是可以猜的东西"**（**因为它是另一个原生 ABI**）
⇒ **⇒ 三次"不猜**】
```

**✅ ⭐⭐⭐ **"不猜"三例表**。

## 三、**`刀BF` 的回滚**（本组第二重要）

### 3.1 那段

```php
// ⚠ 28100 刀BF **已回滚**（甲方实测「当前无法出生」；日志实证：
//   `client spawn REFUSED client=3..11 reason=native_round_trip_mismatch`
//   + `snapshot build rejected failure=missing_playerstate`）。
//   原因：这条路径是 **native 往返**（把 `next` 写进 native 缓冲再读回校验），
//   我把 `unk04A4Time` 改成"生产值"，与 native 源里的原值不一致 ⇒ **往返校验失败 ⇒ 出生被拒**。
//   ⇒ 恢复纯搬运。**sway 相位生产者要真正生效，必须同时写进 native 源（或走能通过校验的路径），
//     这属于单独一刀，不能在这条通用拷贝路径上改。**
next.unk04A4Time = unk04A4Time;
```

### 3.2 二十四层

```text
1. **刀BF 【已回滚**】**
2. ⇒ **甲方实测：「当前无法出生」**
3. ⇒ **日志实证**：`client spawn REFUSED client=3..11 reason=native_round_trip_mismatch`
4. ⇒ **+ `snapshot build rejected failure=missing_playerstate`**
5. ⇒ **原因**：**这条路径是【原生往返**】】
6. ⇒ **（把 `next` 写进原生缓冲【再读回校验**】）**
7. ⇒ **⇒ 而【我把 `unk04A4Time` 改成"生产值"**】**
8. ⇒ **⇒ 与【原生源里的原值【不一致**】】**
9. ⇒ **⇒ 【往返校验失败** ⇒ **出生被拒**】**
10. ⇒ **⇒ 所以【恢复纯搬运**】
11. ⇒ **⚠ 而【sway 相位生产者【要真正生效**】**
12. ⇒ **⇒ 必须【同时写进原生源**（或走【能通过校验的路径**）】
13. ⇒ **⇒ 这属于【单独一刀**】**
14. ⇒ **⇒ 不能在这条【通用拷贝路径上**改**
```

### 3.3 ⭐⭐⭐ **"往返校验失败 ⇒ 出生被拒"**

**✅ 与 §462 的"一个项失败不意味着那个值是坏的，它意味着写者与读者对那个字段住在哪里不一致"**——**完全闭合** ✓

**⇒ 三层**：
```text
写者（我们）⇒ **一个"生产值"**（**`SvProduceSwayPhase` 的输出**）
读者（我们的验证）⇒ **期望【原生源里的原值**】
⇒ **⇒ 所以【那个往返【失败**】
```

**✅ ⭐⭐⭐ **"那个往返失败，因为写者与读者是我们自己的两半"**。</br>

**✅ 与 §460 的"`SvProduceSwayPhase` 的五道"**——**一个"生产者"的完整病历**。

**⇒ 三层**：
```text
§460  **`SvProduceSwayPhase` 的实现**（**五道**）
§463  **而它【无法通过那个往返**】（**因为通用拷贝路径【只搬运**））
⇒ **⇒ 所以【那个生产者在【当前架构下**不可用**】
```

**✅ ⭐⭐⭐ **"那个生产者在当前架构下不可用"** —— 一个**极清晰的结论**。

**⚠ 而"必须同时写进原生源（或走能通过校验的路径）"**⇒ **一个精确的前进路径**。**

**✅ 与 §437 的"若重提交被看到，扩展 `beginSessionRoster()`"**同族（**第六次"可执行的前进路径**）。

**⇒ 三层**：
```text
§437  **`beginSessionRoster()` 的扩展**
§463  **"必须同时写进原生源（或走能通过校验的路径）"**
⇒ **⇒ 两次"前进路径**】
```

**✅ ⭐⭐ **"前进路径"两例**。

## 四、**`otherFlags=1461489901` 与 `playerstate domain refused` 的完整链条**

**⇒ 从 §462 的 `refuse` 与 §463 的二：**

```text
① 密码文被读成 `otherFlags` ⇒ `1461489901`
② `refuse("otherFlags")`（§462 的某个项）
③ `playerstate domain refused otherFlags=1461489901`
④ 快照帧验证器拒绝
⑤ 没有快照到达客户端
```

**⇒ 十层**：
```text
1. **一个密码文【被当成一个 `flags` 字**】
2. ⇒ **⇒ 而它的值【远超**合法范围**】
3. ⇒ **⇒ 所以 `refuse("otherFlags")` 触发**
4. ⇒ **⇒ 而【那个 `refuse` 的消息【带着那个数**】**
5. ⇒ **⇒ 所以【日志里【那个数【就是密码文**】】
```

### 4.1 ⭐⭐⭐ **"日志里的那个数就是密码文"**

**✅ 与 §462 的"给那一项命名把『玩家永不出生』变成【一个要检查的偏移】**"——**完全闭合** ✓

**⇒ 三层**：
```text
§462  **"命名那一项"**
§463  **"那个名字带着一个数，而那个数【就是密码文**"**
⇒ **⇒ 所以【命名 + 值 = 一个【可诊断**的错误**】
```

**✅ ⭐⭐⭐ **"命名 + 值 = 一个可诊断的错误"**。

**⚠ 而"`otherFlags=1461489901`"⇒ **`0x571C_8D6D`？**】

**⇒ 让我验证**：
```text
1461489901 = 0x571C_8D6D?
0x57000000 = 1459617792
1461489901 - 1459617792 = 1872109
1872109 / 65536 = 28.57 ⇒ 0x1C
28 × 65536 = 1835008
1872109 - 1835008 = 37101
37101 / 256 = 144.9 ⇒ 0x90
144 × 256 = 36864
37101 - 36864 = 237 = 0xED
⇒ 0x571C90ED
```

**⇒ 验证**：`0x571C90ED` = `5 × 16^7` ... **我算得 `0x571C90ED`。**

**⚠ 我的算术可能不精确 ⇒ 但 `0x57...` 的高字节 【远超 `0x1800`】 ⇒ **所以 `refuse` 触发** ✓

**✅ ⭐⭐ **"那个值的高字节远超掩码"**。

## 五、`weapon slots` 的七元组诊断

```cpp
const std::array<std::uint32_t, 7> now{
    pending, slotA, slotB, slotC,
    readValue<std::uint32_t>(source, 0x50),
    readValue<std::uint32_t>(source, 0x54),
    readValue<std::uint32_t>(source, 0x2F4) };
if (now != lastSlots && slotReports < 60) { ... log ... }
```

**⇒ 十二层**：
```text
1. **一个七元组**：`0x3E4`（pending）/ `0x3E8`/`0x3EC`/`0x3F0`（三个槽）/ `0x50`/`0x54`（throwback）/ `0x2F4`（持武器列表槽 0）
2. ⇒ **只在【变化**时打**
3. ⇒ **而【上限 `60` 次**】
4. ⇒ **⇒ 所以【一个"变化触发 + 有界**"的诊断**
```

### 5.1 ⭐⭐⭐ **"`+0x3E4` 是选中的副武器，`+0x3E8..3F0` 是副武器槽，而 `+0x50`/`+0x54` 描述手雷 throwback"**

```cpp
// Offhand diagnostic, limited to tuple changes. The historical
// "pending"/"alt" labels in its log are retained for old parsers:
// +0x3E4 is selected offhand (now projected above), +0x3E8..3F0 are
// offhand slots, and +0x50/+0x54 describe grenade throwback.
```

**✅ 与 §462 的"`sub_429DA0` 是 grenade THROWBACK"**完全闭合 ✓

**⇒ 三层**：
```text
§462  **"`ps+0x50` 是引信，`+0x54` 是手雷武器，`+0x254` 是提示实体"**
§463  **"`+0x50`/`+0x54` 描述手雷 throwback"**
⇒ **⇒ 同一个映射两处**
```

**✅ ⭐⭐ **"同一个映射两处"**。

**⚠ 而"`"pending"/"alt"` 的旧标签【为旧解析器保留**"⇒ **一个兼容性考虑**。**

**⇒ 三层**：
```text
旧日志：`pending`/`alt`
新理解：`+0x3E4` 是选中的副武器而 `+0x3E8/3F0` 是槽
⇒ **⇒ 所以【标签【保留**而【理解【更新**】
```

**✅ ⭐⭐ **"标签保留而理解更新"** —— 与 §461 的"`field 53` 的第一次修正只检查了一个"**同族（**第三次"渐进的理解**）。

**⇒ 三层**：
```text
§461  **"第一个修正【只检查了字段 `53`】；一次完整的表审计【也否证了剩下的那个缺席主张**"**
§463  **"`pending`/`alt` 的旧标签为旧解析器保留**"**
⇒ **⇒ 两次"一个渐进修正**】
```

**✅ ⭐⭐ **"一个渐进修正"两例**。

## 六、四个 `SV_SetNative*` 的写者

### 6.1 `SV_SetNativePlayerStateCurrentWeapon`

```cpp
void SV_SetNativePlayerStateCurrentWeapon(SvNativePlayerState &destination, const std::uint32_t weaponAssetIndex)
{
    writeValue(destination, CurrentWeaponOffset, weaponAssetIndex);
    // +0x2F4 is the player's fifteen-entry weapon list; slot 0 is the one in hand.
    writeValue(destination, 0x2F4, weaponAssetIndex);
}
```

**⇒ 六层**：
```text
1. **两个地方都写**：`CurrentWeaponOffset`（`0x3F8`）+ `0x2F4`（**持武器列表的槽 0**）
2. ⇒ **⇒ 所以【"在手的那个"在两个字段里**】
3. ⇒ **而【注释说 `+0x2F4` 是那个十五条目列表，槽 0 是【在手的**】**
```

**✅ 与 §460 的"`HeldWeaponIndexesOffset = 0x2F4`"**完全闭合 ✓

**⇒ 三层**：
```text
§460  **`HeldWeaponIndexesOffset = 0x2F4`**
§463  **`0x2F4` 的槽 `0` 是【在手的**武器**
⇒ **⇒ 一个"列表的首项即当前**"的约定**
```

**✅ ⭐⭐ **"列表的首项即当前"**。

### 6.2 `SV_SetNativePlayerStateWeaponAmmo` 的"槽 20 静默不做"

```cpp
// Fifteen slots, the same extent the round trip above walks. Silently doing
// nothing on a bad slot rather than clamping: a caller asking for slot 20 has
// a bug that a clamp would hide inside slot 14's ammo.
if (slot >= 15) return;
```

**⇒ 八层**：
```text
1. **`slot >= 15` ⇒ 【静默不做**】**
2. ⇒ **⇒ 而【不夹**】**
3. ⇒ **因为【一个要求 `slot 20` 的调用者【有一个 bug**】**
4. ⇒ **⇒ 而【一个夹【会把那个 bug【藏在 `slot 14` 的弹药里**】】**
```

### 6.3 ⭐⭐⭐ **"一个夹会把那个 bug 藏在 slot 14 的弹药里"**

**✅ 与 §458 的"环绕会让一个提示指向错误的名字"**完全同族（**第十二次"省略优于错误**）。

**⇒ 三层**：
```text
夹到 `14` ⇒ **把弹药写进【一个错的槽**】
静默 ⇒ **那个 bug【不被掩盖**】
⇒ **⇒ 所以【后者正确**】
```

**✅ ⭐⭐⭐ **"静默让那个 bug 不被掩盖"** —— 与"§462 的命名那一项"**互补**（**一个静默但可诊断**）。

**⚠ 而"静默"⇒ **一个【矛盾**：§462 说"命名那一项"，而这里**静默**。**

**⇒ 三层**：
```text
§462  **一个 **往返校验的项** ⇒ 【必须命名**】（**因为它是【我们的 bug**））
§463  **一个 **调用者的坏参数** ⇒ 静默】（**因为它是【调用者的 bug**））
⇒ **⇒ 所以【"命名"与"静默"由【谁的 bug**决定**】
```

**✅ ⭐⭐⭐ **"'命名'与'静默'由谁的 bug 决定"** —— 本报告最精确的判据。

### 6.4 `heldBefore` 的 `1`

```cpp
// heldBefore. The read path refuses anything but 0 or 1 here, and a weapon the
// player has never held is one the client is entitled to treat as not yet drawn.
writeValue(destination, HeldWeaponStatesOffset + slot * HeldWeaponStateStride, static_cast<std::uint8_t>(1));
```

**⇒ 六层**：
```text
1. **`heldBefore = 1`**
2. ⇒ **因为【读路径【对 `0` 或 `1` 之外的一切**都拒绝】
3. ⇒ **而【一个玩家【从未持有过**的武器【是一个【客户端有权【当成【尚未画出**】的武器**】】
4. ⇒ **⇒ 所以【写 `1` = "已持有**"**
```

**✅ 与 §461 的"`heldBefore > 1 ⇒ refuse("heldWeapon/heldBefore_not_boolean")`"**完全闭合 ✓

**⇒ 三层**：
```text
§461  **读：`heldBefore > 1` ⇒ 拒绝**
§463  **写：`heldBefore = 1`**
⇒ **⇒ 一个 writer/reader 的对称**
```

**✅ ⭐⭐ **"一个 writer/reader 的对称"**。

## 七、关键结论

1. **⭐⭐⭐ "`ps+0x10` 在这个 build 上【不是一个可读回的普通 `dword`】：它是一个三 `dword` 的受保护值的第一个字，而它的访问器对住在 `ps+0x20`/`ps+0x24`，引擎通过那一对写它 ⇒ 在一次原生阶段之后坐在那里的是【密码文，不是 flags】"`** —— 与 §461 的"合并，不要替换"**互补**：**写可以（通过掩码）而读不行**。
2. **⭐⭐⭐ "以明文读它给那个服务器【每帧一个不同的随机 `otherFlags`】（`1461489901`，然后 `1312251290`，然后 `2934888368`），而那个快照帧验证器拒绝了它 ⇒ 【没有一个快照到达过客户端】"`** —— 第八次"精确的错误消息带一个数"（与 §405/§424 同族）。
3. **⭐⭐⭐ "它只在 `clientThink` 开始提交时才变得可见：在转换仍然拒绝的期间什么也没被写回而 `beginFrame` 的值存活下来"`** ⇒ **"一个 bug 只在另一个被修好之后才暴露"`** —— 第二次"一个修好暴露另一个"（与 §424 同族）。
4. **⭐⭐ "ol-mod 拥有那个明文：它在每次原生调用之前被写进那个受保护对象并在这个 DTO 里跨过它保留；读引擎自己的视图回意味着调用那个 `GET` 访问器并取结果的第二个 `dword` —— 【值得做，但它是另一个原生 ABI，不是可以猜的东西**】"`** —— 第三次"不猜"（与 §460/§462 同族）。
5. **⭐⭐⭐ `刀BF` 的完整回滚病历**：**甲方实测「当前无法出生」；日志 `client spawn REFUSED client=3..11 reason=native_round_trip_mismatch` + `snapshot build rejected failure=missing_playerstate`；原因：把 `unk04A4Time` 改成"生产值"，与原生源里的原值不一致 ⇒ 往返校验失败 ⇒ 出生被拒** ⇒ **"恢复纯搬运"`** ⇒ **"那个生产者在当前架构下不可用"`**。
6. **⭐⭐ "sway 相位生产者要真正生效，必须同时写进原生源（或走能通过校验的路径），这属于单独一刀，不能在这条通用拷贝路径上改"`** —— 第六次"可执行的前进路径"（与 §437 同族）。
7. **⭐⭐ "日志里的那个数就是密码文"`** ⇒ **"命名 + 值 = 一个可诊断的错误"`** —— 与 §462 的"命名那一项"**完全闭合**。
8. **⭐⭐ `weapon slots` 的七元组诊断**（`0x3E4` / `0x3E8`/`0x3EC`/`0x3F0` / `0x50`/`0x54` / `0x2F4`），而 **"`+0x3E4` 是选中的副武器，`+0x3E8..3F0` 是副武器槽，而 `+0x50`/`+0x54` 描述手雷 throwback"`** 与 §462 完全一致；而 **`"pending"/"alt"` 的旧标签【为旧解析器保留**】⇒ **"标签保留而理解更新"`** —— 第三次"渐进的理解"（与 §461 同族）。
9. **⭐⭐ `SV_SetNativePlayerStateCurrentWeapon` 写两个地方**（`0x3F8` + `0x2F4` 的槽 `0`）⇒ **"列表的首项即当前"`**（与 §460 的 `HeldWeaponIndexesOffset = 0x2F4` 闭合）。
10. **⭐⭐⭐ `SV_SetNativePlayerStateWeaponAmmo` 的"槽 `20` 静默不做而不是夹：一个夹会把那个 bug 藏在 `slot 14` 的弹药里"`** —— 第十二次"省略优于错误"（与 §458 同族）。
11. **⭐⭐⭐ "'命名'与'静默'由谁的 bug 决定"`**：**§462 的往返校验项【必须命名**】（**因为它是我们的 bug**）而不 §463 的一个调用者的坏参数【静默**】（**因为它是调用者的 bug**）—— **本报告最精确的判据**。
12. **⭐ `heldBefore = 1` 与 §461 的读路径的 `> 1 ⇒ 拒绝` 是一个 writer/reader 的对称**。

## 八、未闭合点

- `1461489901` 的精确 hex（我算得 `0x571C90ED` 但未验证）。
- `ps+0x20`/`ps+0x24` 的访问器对。
- `writeNativeProtectedPlayerStateFlags` 的实现。
- `刀BF` 的完整标题（"第 7 项狙击镜抽搐/拉回"）。
- `sv_native_playerstate_mp.cpp` 1500 行之后未读取（**共 `1687` 行**）。
