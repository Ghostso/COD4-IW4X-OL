# 322 · **"这个白名单就是僵尸从未绘制的原因"**、四个浮点/角度写入原语、`sortedUniqueInRange` 的二分前提

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 1800–2000 行。

## 二、`validObituaryEventEntity` 的**四个界**（本组第二重要）

```php
const auto parameterBits = EntityEventParameterBits[EventObituary];
return entity.eType == EntityTypeObituary &&
    entity.number >= FirstDynamicServerEntityNum &&
    entity.eventParm < (std::uint32_t{1} << parameterBits) &&
    entity.otherEntityNum < MaximumGameClients &&
    (entity.groundEntityNum < MaximumGameClients ||
        entity.groundEntityNum == EntityNumWorld) &&
    entity.clientNum == 0 && entity.eFlags == 0 &&
    ... (其余 30+ 项全零) ...
    entity.unk00A0 == 0 &&
    ... 轨迹全零 ...
    all_of(entity.origin, == 0.0f) &&        // ← 【origin 必须全零】
    all_of(entity.angles, == 0.0f);
```

### 2.1 而**四项非零约束**

```text
eventParm < (1 << parameterBits)     （12 位 ⇒ < 4096）
otherEntityNum < MaximumGameClients  （18）
groundEntityNum < 18 或 == EntityNumWorld
number >= FirstDynamicServerEntityNum
```

### 2.2 而**`origin` 必须全零**

**⇒ 三层**：

```text
1. 一个 obituary 事件**没有位置**
2. ⇒ 所以 `origin` 全零
3. ⇒ 因为它在 HUD 上显示而不是在世界里
```

**✓ 与 §146 的"`obituary (1700 + MOD)`"配合 —— 一个 UI 事件。**

### 2.3 而 `otherEntityNum < MaximumGameClients` 是**受害者**

**⇒ 与 §321 的"字段 9 / `+0x84` VICTIM"配合。**

**⇒ 而 `groundEntityNum` 是**攻击者**（§321 的字段 13 / `+0x88`）。**

**⚠ 命名是 `groundEntityNum` 但语义是 attacker。**

**✅ 与 §319 的"`EventEntityAttackerField = 13`"配合 —— 而这里用 `groundEntityNum` 存它。**

**⚠ 一处**字段复用**（因为不能加结构成员？）。**

**⇒ 但 §321 说 `movementDir` 等可以加……**

**⇒ 所以这里复用了 `groundEntityNum` 而**没有注释说明**。**

### 2.4 而 `EntityNumWorld` 的**允许**

**⇒ 三层**：

```text
1. 攻击者可以是 0..17（真客户端）
2. ⇒ 或者 `EntityNumWorld`（世界 —— 表示"无攻击者"？）
3. ⇒ 而 §321 说"`if (v39 > 0x12) v39 = 2046`"
```

**⚠ 客户端会把越界攻击者设成 `2046` 而这里允许 `EntityNumWorld`。**

**⇒ 若 `EntityNumWorld == 2046` 则一致。**

**⇒ 而 §264 说 `ENTITYNUM_NONE = 2047`。**

**⚠ 所以 `EntityNumWorld` 可能是 `2046`（与 `ENTITYNUM_NONE` 差一）。**

**✅ 与 §321 的"`2046` 而不是 `2047`"**完全一致** ✓**

## 三、**"这个白名单就是僵尸从未绘制的原因"**（本组最重要的一段）

### 3.1 那段完整因果

```php
// ET_ACTOR. THIS LIST IS WHY A ZOMBIE NEVER DREW. An eType absent
// here is dropped before serialization, so the actor was never on
// the wire at all -- which is also why frames stayed perfectly
// healthy (nothing sent cannot desync), why validActorEntity never
// refused anything (it only sees archived entities), and why the
// client parsed zero agents (the agent elements are built by walking
// the archived entities, and there were none).
//
// The gate is a DESCRIPTOR COVERAGE gate, per this function's own
// comment, not visibility policy -- and eType 19's descriptor is
// recovered: writeChangedActor writes the eighteen fields retail
// sends on frame one, and validActorEntity bounds them.
(SvArchiveActorEntities &&
    isActorEType(entity.networkState.eType)) ||
```

### 3.2 八层

```text
1. **这个列表就是僵尸从未绘制的原因**
2. ⇒ **一个不在这里的 eType 在序列化【之前】被丢弃**
3. ⇒ 所以**那个 actor 根本不在线上**
4. ⇒ **这也是为什么帧保持完全健康** —— **什么都没发就不会失步**
5. ⇒ **为什么 `validActorEntity` 从不拒绝任何东西** —— **它只看到被归档的实体**
6. ⇒ **为什么客户端解析出零个 agent** —— **agent 元素是通过遍历被归档的实体构建的，而没有**
7. ⇒ 门是**一个描述符覆盖门**而不是可见性策略
8. ⇒ 而**eType 19 的描述符是已恢复的**：`writeChangedActor` 写零售第一帧发的十八个字段而 `validActorEntity` 界它们
```

### 3.3 **四个"看起来健康"的连锁**

```text
① 帧健康            ⇒ 因为没发
② validActorEntity 从不拒绝 ⇒ 因为它只看归档的
③ 客户端零 agent    ⇒ 因为没有归档实体
④ 僵尸不绘制        ⇒ 因为不在线上
```

**✅ 这是本文件里**最深的一层"沉默读起来像健康"**。**

**⇒ 与 §305 的"`commitSessionRoster` 从未被调用"、§309 的"`+0x18` 空"同族**（第十八次）。

**⇒ 而这次是**四个指标全部正常而功能全无**。**

### 3.4 而那段 TODO

```php
// TODO(CODOL): split source in-use and svFlags ownership, recover
// the dedicated per-client visibility stage, then remove this
// descriptor allow-list as additional eType writers are closed.
```

**⇒ 三层**：

```text
1. 拆开源 in-use 与 svFlags 的所有权
2. ⇒ 恢复专用服的每客户端可见性阶段
3. ⇒ 然后**随着更多 eType writer 被关闭，移除这个描述符白名单**
```

**✅ 一个**明确的退出条件**。**

### 3.5 而三个 build 的**可见性策略对照**

```php
// CODREF(sv_add_entities_clients_can_see): BO1
// SV_AddEntitiesVisibleFromPoint 0x0071C6C0 applies per-client PVS.
// BO2 0x006FDED0 and Ghosts 0x140202580 instead archive every
// in-use entity whose SVF_NOCLIENT bit is clear and whose
// entityState number is valid. None uses eType as visibility
// policy. CODOL's removed dedicated producer cannot be copied from
// this client binary, so its generation-specific choice is open.
```

**⇒ 五层**：

```text
1. **BO1 `SV_AddEntitiesVisibleFromPoint 0x0071C6C0` 应用每客户端 PVS**
2. ⇒ **BO2 `0x006FDED0` 与 Ghosts `0x140202580` 归档每一个 in-use 且 `SVF_NOCLIENT` 位清零的实体**
3. ⇒ **没有一个用 eType 作为可见性策略**
4. ⇒ **CODOL 被删除的专用服生产者不能从这个客户端二进制复制**
5. ⇒ 所以**它的代际特定的选择是开放的**
```

**✅ 与 §265 的"这个 build 没有 SV_Trace"同族（第六次"生产者在客户端二进制里缺席"）。**

## 四、`ET_GENERAL` 的两个分支

```php
if (entity.networkState.eType == EntityTypeGeneral)
{
    return SV_IsGrenadeExplosionEntityValid(entity.networkState) ||
        (entity.collisionShape == SvCollisionShape::BrushModel &&
            entity.brushModelClipHandle &&
            validGeneralBrushModelEntity(entity.networkState));
}
```

### 4.1 两个

```text
手雷爆炸实体  ⇒ SV_IsGrenadeExplosionEntityValid
brush model   ⇒ collisionShape == BrushModel 且 clipHandle 非零 且 validGeneralBrushModelEntity
```

**⇒ 两种 `ET_GENERAL` 的**不同子类**。**

**✅ 而 §302 说"这个服务器完全不发布 brush model" —— 但这里**有 `validGeneralBrushModelEntity`**。**

**⚠ 所以"不发布"与"有写入器"矛盾。**

**⇒ 但 §319 提到"724 个能工作的 brush model"。**

**⇒ 三次矛盾** ⇒ 需要最后核对。

## 五、`sortedUniqueInRange` 的**前缀条件**

```cpp
template <typename State, typename Number>
bool sortedUniqueInRange(const std::vector<State> &states, Number State::*member, Number upperBound)
{
    Number previous{};
    bool first = true;
    for (const auto &state : states)
    {
        const auto number = state.*member;
        if (number >= upperBound || (!first && number <= previous)) return false;
        previous = number;
        first = false;
    }
    return true;
}
```

### 5.1 三项

```text
number >= upperBound   ⇒ 拒绝
number <= previous     ⇒ 拒绝（必须【严格递增】）
否则 ⇒ 通过
```

**⇒ 所以"排序且唯一且在范围内"。**

### 5.2 而两个 `find` 用 **`std::lower_bound`**

```cpp
const SvPlayerState *findPlayerState(const SvSnapshotFrame &frame, uint32 clientNum)
{
    const auto state = std::lower_bound(frame.playerStates.begin(), frame.playerStates.end(),
        clientNum, [](const SvPlayerState &c, uint32 n) { return c.clientNum < n; });
    return state != frame.playerStates.end() && state->clientNum == clientNum ? &*state : nullptr;
}
```

**⇒ 所以 `sortedUniqueInRange` 是**二分的前提**。**

**✅ 一个**正确的"先验证再用二分"**设计。**

## 六、四个**浮点/角度写入原语**（本组第三重要）

### 6.1 `writeRawFloatDelta`

```cpp
void writeRawFloatDelta(MsgWriter &message, const float value, const float baseline = 0.0f)
{
    const auto bits = std::bit_cast<uint32>(value) ^ std::bit_cast<uint32>(baseline);
    message.MSG_WriteLong(bits);
}
```

**⇒ 三层**：

```text
1. 值 XOR 基线
2. ⇒ 写 32 位
3. ⇒ 所以它**是原始值的 XOR 增量**
```

**✅ 与记忆里"11 个字段我们写 XOR 增量，三份参照全写裸值"**相关**。**

**⚠ 而这里**明确**用 XOR（`baseline` 默认 0 ⇒ 裸值）。**

**✓ 所以默认是裸值而可选 XOR。**

### 6.2 `writeFullFloatDelta`

```cpp
void writeFullFloatDelta(MsgWriter &message, const float value, const float baseline = 0.0f)
{
    // CODOL sub_5A27F0, bits == 0: select non-zero and full-float,
    // then read a 32-bit value XORed with the acknowledged baseline.
    message.MSG_WriteBits(1, 1);     // ← 非零
    message.MSG_WriteBits(1, 1);     // ← 全浮点
    writeRawFloatDelta(message, value, baseline);
}
```

**⇒ 三层**：

```text
1. `sub_5A27F0` 在 `bits == 0` 时：**选非零与全浮点**
2. ⇒ 然后读一个 32 位的值与**确认的基线** XOR
3. ⇒ 所以两个 1 位标志 + 32 位
```

**✅ 一个**自描述的浮点编码**（1 位"非零" + 1 位"全浮点" + 32 位值）。**

### 6.3 `writeAngle16`

```cpp
void writeAngle16(MsgWriter &message, const float angle)
{
    auto normalized = std::fmod(angle, 360.0f);
    if (normalized < 0.0f) normalized += 360.0f;
    const auto packed = (uint16)((uint32)(normalized * (65536.0f / 360.0f)));
    message.MSG_WriteShort(packed);
}
```

**⇒ 四项**：

```text
fmod 归一化到 0..360
负数加 360
× (65536/360) 量化到 16 位
写 16 位
```

**✅ 与 §314 的 `damageDirectionBytes` 的 `× (256/360)` 同族（但这是 16 位）。**

### 6.4 `writeDeltaAngleFull`

```cpp
void writeDeltaAngleFull(MsgWriter &message, const float angle)
{
    // CODOL sub_5A25C0: skip the compact-table and 12-bit delta branches.
    message.MSG_WriteBits(0, 1);
    message.MSG_WriteBits(0, 1);
    writeAngle16(message, angle);
}
```

**⇒ 三层**：

```text
1. `sub_5A25C0`：**跳过紧凑表与 12 位 delta 分支**
2. ⇒ 两个 0 位
3. ⇒ 然后 16 位角度
```

**✅ 与 `writeFullFloatDelta` 的**两个 1 位**对称：**

```text
writeFullFloatDelta   1, 1  全浮点
writeDeltaAngleFull   0, 0  全角度（跳过两个紧凑分支）
```

**✓ 两个"全"编码。**

### 6.5 而四个原语的**三种精度**

```text
32 位浮点     writeRawFloatDelta / writeFullFloatDelta
16 位角度     writeAngle16 / writeDeltaAngleFull
（还有紧凑的 12 位 delta 与"紧凑表" —— 但这里跳过）
```

**✅ 与 §264 的"三个 trace 三种 ABI"同族 —— 这里是**三种精度**。**

## 七、关键结论

1. **`validObituaryEventEntity` 的 `origin`/`angles` 必须全零** —— obituary 是 UI 事件。
2. **`otherEntityNum` 是受害者而 `groundEntityNum` 是攻击者** —— 一处**未注释的字段复用**。
3. **`groundEntityNum == EntityNumWorld` 允许** ⇒ 而 §321 说客户端把越界攻击者设成 `2046`。
4. **⭐ "这个白名单就是僵尸从未绘制的原因"** —— 四个指标全正常而功能全无。
5. **"什么都没发就不会失步"** —— 一个**自我掩盖的失败**。
6. **"`validActorEntity` 从不拒绝任何东西因为它只看归档的实体"**。
7. **"客户端解析出零个 agent 因为 agent 元素通过遍历归档实体构建"**。
8. **门是"描述符覆盖门"而不是可见性策略**，且有明确的退出条件。
9. **BO1 用每客户端 PVS 而 BO2/Ghosts 归档所有 `SVF_NOCLIENT` 清零的** —— **没有一个用 eType 作为可见性策略**。
10. **"CODOL 被删除的专用服生产者不能从这个客户端二进制复制"** —— 第六次。
11. **⚠ `validGeneralBrushModelEntity` 存在而 §302 说"完全不发布 brush model"** —— 第三次矛盾。
12. **`sortedUniqueInRange` 是二分的**前提**。
13. **`writeRawFloatDelta` 是 XOR 增量**（`baseline` 默认 0 ⇒ 裸值）。
14. **`writeFullFloatDelta` 两个 1 位标志 + 32 位** （`sub_5A27F0`）。
15. **`writeDeltaAngleFull` 两个 0 位 + 16 位**（`sub_5A25C0`）。
16. **`writeAngle16` 的 `× (65536/360)` 量化**。

## 八、未闭合点

- `EntityNumWorld` 的具体值（是否 2046）。
- `groundEntityNum` 存攻击者是否有注释。
- brush model 的三次矛盾（§302 vs §319 vs §322）。
- `sv_snapshot_mp.cpp` 2000 行之后未读取（1.47 MB，进度 14%）。
