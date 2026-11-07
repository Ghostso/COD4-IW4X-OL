# 337 · **`statsMask` 从 4 位变 17 位**、**`team` 从 3 位变 11 位**、"写窄了会让之后每个客户端解码垃圾"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 4782–5000 行。

## 二、**`statsMask` 从 4 位变 17 位**（本组最重要的一段）

### 2.1 那段

```php
const uint32 statsMask =
    (healthChanged ? PlayerStateHealthStatMask : 0) |
    (deadYawChanged ? PlayerStateDeadYawStatMask : 0) |
    (maxHealthChanged ? PlayerStateMaxHealthStatMask : 0) |
    (spawnGenerationChanged ? PlayerStateSpawnGenerationStatMask : 0);
message.MSG_WriteBits(statsMask ? 1 : 0, 1);
if (statsMask)
{
    // CODDIFF(1649370): the mask is SEVENTEEN bits here, not
    // 3.3.3.3's four. Same first four items in the same order --
    // i16 health, i16 deadYaw, i16 maxHealth, u8 spawnGeneration --
    // and thirteen more 2-byte items after them that this server
    // does not produce, so their mask bits stay 0 and they cost
    // nothing but the width. 3.3.3.3's four-bit form is in
    // CODOL-main re/demo-re/02-snapshot-wire-spec.md sec 5 T1;
    // this build's is Tools/demo-re/codol_snapshot.py ps_trailing
    // T1, `bits(17)` then seventeen conditional raw reads sized
    // 2,2,2,1 then thirteen more 2s. Writing four bits here left
    // the following thirteen out of the stream, which moved every
    // later section -- and the entity list -- out of phase.
    message.MSG_WriteBits(statsMask, PlayerStateStatsMaskBits);
    if (healthChanged) message.MSG_WriteShort((uint16)state.health);
    if (deadYawChanged) message.MSG_WriteShort((uint16)state.deadYaw);
    if (maxHealthChanged) message.MSG_WriteShort((uint16)state.maxHealth);
    if (spawnGenerationChanged) message.MSG_WriteByte(state.spawnGeneration);
}
```

### 2.2 九层

```text
1. **这里的掩码是【十七位】，不是 3.3.3.3 的四位**
2. ⇒ **同样的前四项同样的顺序**：
     · `i16 health`
     · `i16 deadYaw`
     · `i16 maxHealth`
     · `u8 spawnGeneration`
3. ⇒ **而它们之后还有十三个 2 字节项而这个服务器不产出**
4. ⇒ 所以**它们的掩码位保持 0 而它们只花宽度不花数据**
5. ⇒ 3.3.3.3 的四位形式在 `CODOL-main re/demo-re/02-snapshot-wire-spec.md` 第 5 节 T1
6. ⇒ 本 build 的写在 `Tools/demo-re/codol_snapshot.py` 的 `ps_trailing` T1
7. ⇒ **`bits(17)` 然后十七个条件原始读，尺寸是 `2,2,2,1` 然后十三个 2**
8. ⇒ **在这里写四位会让后面那十三位掉出流**
9. ⇒ **而那移动了每一个后续段 —— 以及实体列表 —— 失相位**
```

### 2.3 **"写四位会让后面十三位掉出流"**

**✅ 三层**：

```text
1. 客户端读 17 位掩码
2. ⇒ 我们只写 4 位
3. ⇒ **客户端多读 13 位 ⇒ 但那 13 位是【下一个字段的数据】**
4. ⇒ **所以整个流失相位**
```

**✅ 与 §334 的"86 不在线上导致跑出缓冲区"、§321 的"`impactFlags` 的界"同族**（第三十二次）。

### 2.4 而 `PlayerStateStatsMaskBits = 17`（§316）

**✅ 与 §316 的"`PlayerStateStatsMaskBits = 17`"**完全一致** ✓**

### 2.5 而四个 `StatMask`

```text
0x01   health
0x02   deadYaw
0x04   maxHealth
0x08   spawnGeneration
```

**✅ 与 §316 的四个**完全一致** ✓**

### 2.6 而**数据类型**

```text
health           i16（写 `MSG_WriteShort`）
deadYaw          i16
maxHealth        i16
spawnGeneration  u8（写 `MSG_WriteByte`）
```

**✅ 与 §316 的"`PlayerStateHealthStatMask = 0x01`"等配合。**

**⚠ 而 §317 说"`health` 不走 netfield 而在 STATS 段作为 16 位的值"** ✓

## 三、**`team` 从 3 位变 11 位**（本组第二重要）

### 3.1 那段

```php
constexpr uint32 TeamFieldIndex = 21;
// 1649370 WIDENED THIS FIELD, 3 bits -> 11. Both builds' 24-entry
// 0x58 descriptors carry the same 24 offsets in the same order --
// 0x00C54298 on 3.3.3.3, 0x00DA63E8 here (section 87; 0x00DA6408 is
// OL.exe's, which is what this line used to say) -- so index 21 is the same
// field at the same offset 0x08, and only its width moved. Writing
// 3 where the client reads 11 does not merely lose the value: it
// leaves eight bits of the NEXT field in the stream, so every client
// after this one in the section decodes garbage.
constexpr uint32 TeamBitCount = 11;
```

### 3.2 八层

```text
1. **1649370 加宽了这个字段，3 位 → 11 位**
2. ⇒ **两个 build 的 24 项 `0x58` 描述符携带同样的 24 个偏移同样的顺序** ——
     · **`0x00C54298` 在 3.3.3.3**
     · **`0x00DA63E8` 在这里**（§87；**`0x00DA6408` 是 OL.exe 的，而这行过去说的就是它**）
3. ⇒ 所以**索引 21 是同一个字段在同一个偏移 `0x08`，而只有它的宽度移动了**
4. ⇒ **写 3 而客户端读 11 不只是丢值**
5. ⇒ **它把下一个字段的八位留在流里**
6. ⇒ **所以本节里这个之后的每一个客户端都解码垃圾**
```

### 3.3 **"每一个客户端之后解码垃圾"**

**✅ 三层**：

```text
1. 少写 8 位
2. ⇒ 客户端多读 8 位
3. ⇒ **而那 8 位是下一个客户端的数据**
4. ⇒ **所以之后每一个客户端都错**
```

**✅ 与 §334/§337 的"失相位"同族（第三十三次）。**

**⇒ 而这是**一个段内的连锁**而不是跨段。**

### 3.4 而三个地址

```text
0x00C54298   3.3.3.3 的 0x58 描述符（24 项）
0x00DA63E8   本 build 的
0x00DA6408   OL.exe 的（而这行过去说的是它）
```

**⚠ `0x00DA63E8` 与 `0x00DA6408` 差 `0x20`。**

**✅ 与 §316 的"每一个 25 张表在 out.exe 上均匀低 `0x20`"**完全一致** ✓**

**⇒ 所以 `0x00DA6408 - 0x20 = 0x00DA63E8`。**

**✅ **第三次确认那个 `-0x20` 位移**。**

### 3.5 而 `0x58` 是**clientState 的 24 项描述符**

**⇒ 三层**：

```text
1. 一个 24 项的描述符表
2. ⇒ 每项指向 clientState 的一个字段
3. ⇒ 而索引 21 在偏移 `0x08`（`team`）
```

**✅ 与 §255 的 `clientState` stride `0x160` 不同的表。**

### 3.6 而**"新行从 `0x00C57218` 的原生默认初始化"**

```php
: static_cast<std::uint32_t>(SvTeam::Sc);
// CL_ParsePacketClients initializes a new 0x58-byte row
// from CODOL's native default at 0x00C57218. Its team
// field (+0x08) is Sc (2), not the zero enum value.
```

**⇒ 四层**：

```text
1. `CL_ParsePacketClients` 从一个 **`0x58` 字节行**初始化
2. ⇒ 而那是从 **`0x00C57218`** 的原生默认
3. ⇒ **它的 team 字段（`+0x08`）是 `Sc`（2）**
4. ⇒ **不是零枚举值**
```

**✅ 一个**非零的默认**。**

**⚠ 而 §336 的 `cursorHint` 默认零 ⇒ 而这里 `team` 默认 2。**

**⇒ 两个不同的默认来源。**

## 四、`writeClientNumber` 的**两分支**

```cpp
void writeClientNumber(MsgWriter &message, uint32 clientNum, int32 &lastClientNum)
{
    message.MSG_WriteBits(1, 1);                                   // ① 有客户端
    if (clientNum == (uint32)(lastClientNum + 1))
        message.MSG_WriteBits(1, 1);                               // ② 连续
    else
    {
        message.MSG_WriteBits(0, 1);                               // ③ 跳跃
        message.MSG_WriteBits(clientNum, 5);                       // 【5 位，绝对】
    }
    lastClientNum = (int32)clientNum;
}
```

**⇒ 三层**：

```text
① 一个 1 位
② 连续 ⇒ 一个 1 位（共 2 位）
③ 跳跃 ⇒ 一个 0 位 + 5 位绝对（共 7 位）
```

**✅ 与 §323 的 `writePlayerStateFieldIndex` 的"连续最便宜"同族。**

**⚠ 但这里连续是**2 位**而字段索引是**1 位+0位=1 位**。**

**⇒ 两个不同的编码。**

## 五、`writeLegacyClients` 与 `writeClients` 的**两个几乎相同的函数**

### 5.1 `writeLegacyClients`（878 行）

```cpp
// Preserve the pre-zombie-merge clientState wire for ordinary multiplayer.
// The actor writer below owns Zombie Siege's combined agent namespace; DM
// has only the measured team field and must remain byte-for-byte compatible
// with the last live-validated build (8584acf).
void writeLegacyClients(MsgWriter &message,
    const std::vector<SvClientState> &clients,
    const std::vector<SvClientState> *baseline)
{
    const auto writeClientStateDelta = [&message](state, oldState) {
        constexpr uint32 TeamFieldIndex = 21;
        constexpr uint32 TeamBitCount = 11;
        ...
    };
    // 双指针归并
}
```

### 5.2 而那段注释

**⇒ 四层**：

```text
1. **为普通多人保留 pre-zombie-merge 的 clientState 线**
2. ⇒ actor 写入器拥有 **Zombie Siege 的合并 agent 命名空间**
3. ⇒ **DM 只有那个测量过的 `team` 字段**
4. ⇒ **必须与最后一个实机验证的 build（`8584acf`）逐字节兼容**
```

### 5.3 而**两个函数的 `writeClientStateDelta` 内容相同**

**⚠ `writeLegacyClients` 与 `writeClients` 各有一个 `writeClientStateDelta` lambda，都是 `TeamFieldIndex = 21` / `TeamBitCount = 11` / `writeSkippedFieldIndex(..., 3)` / `writeUnsignedDelta(..., 11)`。**

**⇒ 一份代码两处拷贝。**

**✅ 与 §337 的"两个几乎相同的函数"同族。**

### 5.4 而"**与 `8584acf` 逐字节兼容**"

**✅ 一个**具体的 commit 作为兼容基准**。**

**⇒ 与 §290 的"`99d66d1` 起就是这样"、§348 的"`2d-quindecies`"同族。**

## 六、**双指针归并**的五层

```cpp
size_t currentIndex{}, baselineIndex{};
int32 lastClientNum = -1;
while (currentIndex < clients.size() ||
    (baseline && baselineIndex < baseline->size()))
{
    const auto currentNum = currentIndex < clients.size()
        ? clients[currentIndex].clientNum : UINT32_MAX;
    const auto baselineNum = baseline && baselineIndex < baseline->size()
        ? (*baseline)[baselineIndex].clientNum : UINT32_MAX;
    const auto clientNum = min(currentNum, baselineNum);
    writeClientNumber(message, clientNum, lastClientNum);
    if (baselineNum < currentNum)
    {
        message.MSG_WriteBits(1, 1);    // ← 【删除标记】
        ++baselineIndex;
        continue;
    }
    message.MSG_WriteBits(0, 1);        // ← 【存在】
    writeClientStateDelta(clients[currentIndex],
        baselineNum == currentNum ? &(*baseline)[baselineIndex] : nullptr);
    ++currentIndex;
    if (baselineNum == currentNum) ++baselineIndex;
}
message.MSG_WriteBits(0, 1);            // ← 【终止】
```

### 6.1 五层

```text
① 两个指针 `currentIndex` / `baselineIndex`
② 取两个编号的 **`min`**
③ **`baselineNum < currentNum` ⇒ 删除标记**（只在基线里有）
④ 否则 ⇒ 存在标记 + delta
⑤ 循环后一个 0 位终止
```

**✅ 一个**经典的"两个有序列表的归并"**。**

### 6.2 而 `UINT32_MAX` 作为**哨兵**

**⇒ 三层**：

```text
1. 当一个列表耗尽 ⇒ 用 `UINT32_MAX`
2. ⇒ **所以 `min` 总是取另一个**
3. ⇒ 而 `baselineNum < currentNum` 在 current 耗尽时**恒真** ⇒ 走删除分支
```

**✅ 一个**干净的哨兵**。**

**✅ 与 §235 的 `INT32_MIN` 同族（第十五次）。**

### 6.3 而 `lastClientNum` 初值 **-1**

**⇒ 三层**：

```text
1. `lastClientNum = -1`
2. ⇒ 所以第一个客户端 0 时 `clientNum == (uint32)(-1 + 1)` = 0 ⇒ **连续**
3. ⇒ **所以第一个总是"连续"编码（2 位）**
```

**✅ 与 §331 的 `lastFieldIndex = -1` 同族（第二次）。**

## 七、`index 21` 的**两个 build 的一致性**

**⇒ 三层**：

```text
1. 两个 build 的 24 项描述符**携带同样的 24 个偏移同样的顺序**
2. ⇒ 所以**索引 21 是同一个字段在同一个偏移 `0x08`**
3. ⇒ **只有宽度移动了（3 → 11）**
```

**✅ 与 §316 的"数据区在 `-0x20` 上逐字节相同"**部分一致（但那里是**数据**而这里是**偏移表**）。**

**⇒ 所以**偏移表也相同** ⇒ 只有宽度变。**

**✅ 强一致。**

## 八、关键结论

1. **⭐ `statsMask` 从 4 位变 17 位** —— 十三个额外项"不产出但花宽度"。
2. **四个数据类型**：`i16`、`i16`、`i16`、`u8`。
3. **"写四位会让后面十三位掉出流 ⇒ 移动每一个后续段以及实体列表"**。
4. **⭐ `team` 从 3 位变 11 位** —— "写 3 而客户端读 11 会把下一个字段的八位留在流里 ⇒ 每个客户端之后解码垃圾"。
5. **三个描述符地址**（`0x00C54298` / `0x00DA63E8` / `0x00DA6408`），而 `0x00DA6408 - 0x20 = 0x00DA63E8` —— **第三次确认 `-0x20`**。
6. **`CL_ParsePacketClients` 从 `0x00C57218` 初始化，而 `team` 默认是 `Sc`(2) 不是 0**。
7. **`writeClientNumber` 的两分支**（连续 2 位 / 跳跃 7 位）。
8. **`writeLegacyClients` 与 `writeClients` 各有一份相同的 `writeClientStateDelta`** —— 代码重复。
9. **"与最后一个实机验证的 build `8584acf` 逐字节兼容"**。
10. **双指针归并的五层**，用 `UINT32_MAX` 作哨兵。
11. **`lastClientNum = -1` 使第一个客户端总是"连续"**。
12. **两个 build 的 24 项描述符**偏移与顺序相同** ⇒ 只有宽度变。**

## 九、未闭合点

- 那十三个未产出的 stat 项是什么。
- `0x00C57218` 的完整默认行。
- `8584acf` 是哪次提交。
- `sv_snapshot_mp.cpp` 5000 行之后未读取（1.47 MB，进度 34%）。
