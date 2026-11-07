# 338 · **agentState 的十个字段**、**"头在槽 0 所以它的 tag 是 23 而我们一直发槽 1 的 15"**、`unk_DA9920` 的四个非零默认

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 4981–5200 行。

## 二、**agentState 的十个字段**（本组最重要的一段）

### 2.1 完整清单

```text
索引  偏移      位宽    名字                    默认（unk_DA9920）
8     +0x00C    10      modelIndex              【1266】
9     ?         12      animIndex               0
10    ?         -97     animStartTime           0
12    +0x034    32      attachmentIgnoreCollision  3
13    +0x014    10      attachModelIndex0       【1267】
14    +0x018    10      attachModelIndex1       【1317】
15    +0x028    6       attachTagIndex1         【3】
20    +0x004    11      entityNumber            【345】
21    +0x008    【11】   team                    【Sc = 2】
23    +0x024    6       attachTagIndex0         0
```

### 2.2 **五个非零默认**

```text
modelIndex              1266
attachModelIndex0       1267
attachModelIndex1       1317
attachTagIndex1          3
entityNumber            345
```

**⇒ 五个非零而其余为零。**

### 2.3 而那段**关键的注释**

```php
// NOT ZERO. The client bases a first-time agent row on unk_DA9920,
// whose +0x00C is 1266; a zero base here made 310 decode as 452.
// See SvAgentDefaultModelIndex.
const auto oldModelIndex = oldState
    ? oldState->modelIndex
    : static_cast<std::uint16_t>(SvAgentDefaultModelIndex);
```

**⇒ 四层**：

```text
1. **不是零**
2. ⇒ 客户端基于 **`unk_DA9920`** 来初始化一个首次的 agent 行
3. ⇒ **它的 `+0x00C` 是 1266**
4. ⇒ **这里一个零基让 310 解码成 452**
```

### 2.4 **"310 解码成 452"** 的算术

**⇒ 因为它是 **XOR 增量**：**

```text
实际值 = 基线 XOR 增量
310 = 1266 XOR 增量
⇒ 增量 = 1266 XOR 310
```

**⇒ 而基线用 0 时：**

```text
实际值 = 0 XOR 310 = 310
```

**⚠ 所以"零基"应该给出 310 而"正确基"给出 310。**

**⇒ 所以"310 解码成 452"是**另一个方向**：**

```text
发送值 = state.modelIndex = 310
基线 = 0 ⇒ 写 310
客户端基线 = 1266 ⇒ 读 1266 XOR 310 = ？
```

**算：`1266 XOR 310`。**

```text
1266 = 0x4F2
 310 = 0x136
XOR  = 0x5C4 = 1476
```

**⚠ 得 1476 而不是 452。**

**⇒ 所以"452"可能来自**另一个值**。**

**⇒ 或者我算错了。**

**让我验证 452：`1266 XOR 452`。**

```text
1266 = 0x04F2
 452 = 0x01C4
XOR  = 0x0536 = 1334
```

**⚠ 不是 310。**

**⇒ 所以"310 解码成 452"的算术不闭合。**

**⚠ 可能"452"是**另一个场景**的值。**

**✅ 与 §309 的"310^242=452"**相关！**

**§147**："agent default template `unk_DA9920`（`+0x00C = 1266`, modelIndex 310 → `310^242=452`）"

**⇒ **`310 ^ 242 = 452`** ✓**

**算：`310 = 0x136`, `242 = 0x0F2`, XOR = `0x1C4` = 452** ✓

**✅ 所以 **452 = 310 XOR 242**。**

**⇒ 而 242 是**某个**值。**

**⚠ 而 `1266 - 1024 = 242`。**

**✅ **`1266 = 1024 + 242`** ✓**

**⇒ 所以 `242 = 1266 - 1024` = 1266 减去 `ModelConfigStringCount`?**

**⇒ 而 `ModelConfigStringCount = 1024`（§301）。**

**✅ 所以 `242 = 1266 - 1024`。**

**⇒ 所以那个算术是 `1266 & 0x3FF = 242`（10 位掩码）。**

**✅ **`1266 & 0x3FF = 242`** ✓**

**⇒ 所以"452 = 310 XOR 242"来自"10 位掩码后的基线 XOR 310"。**

**✅ 完全闭合 —— 这是 §316 的 `writeUnsignedDelta` 的 `mask` 的效果。**

## 三、**"头在槽 0 所以它的 tag 是 23 而我们一直发槽 1 的 15"**（本组第二重要）

### 3.1 那段

```php
// ATTACHMENT SLOT 0'S TAG, field 23, +0x024, SIX bits, default 0.
// MEASURED: the client pairs each attachment's model with its own
// tag, and sub_530C90 reads the tag from the cursor that starts at
// agentState+0x24 and steps 4 (0x530df8 `mov esi,[edx]` then
// `add esi, 1708h` = band base 5896, the TAG band):
//   slot 0  model +0x14 idx13   tag +0x24 idx23
//   slot 1  model +0x18 idx14   tag +0x28 idx15
//   slot 2  model +0x1C idx16   tag +0x2C idx17
//   slot 3  model +0x20 idx18   tag +0x30 idx19
// THE HEAD IS IN SLOT 0, so its tag is 23 -- and this server was
// sending slot 1's tag (15) and never slot 0's. MEASURED LIVE in the
// client's actor record: model landed as `c_zom_ger_head` and
// record+308 (the tag name) was EMPTY, so sub_52FBE0 hashed an empty
// string for the bone and the part had nothing to attach to.
```

### 3.2 九层

```text
1. **附件槽 0 的 tag：字段 23，`+0x024`，六位，默认 0**
2. ⇒ **实测：客户端把每一个附件的模型与它自己的 tag 配对**
3. ⇒ **而 `sub_530C90` 从一个游标读 tag**：**从 `agentState + 0x24` 开始，步长 4**
4. ⇒ 汇编：`0x530df8 mov esi,[edx]` 然后 `add esi, 1708h` = **带基址 5896**（**TAG 带**）
5. **四个槽的完整对照**：
     · **槽 0：model `+0x14` idx13 / tag `+0x24` idx23**
     · **槽 1：model `+0x18` idx14 / tag `+0x28` idx15**
     · **槽 2：model `+0x1C` idx16 / tag `+0x2C` idx17**
     · **槽 3：model `+0x20` idx18 / tag `+0x30` idx19**
6. ⇒ **头在槽 0 ⇒ 所以它的 tag 是 23**
7. ⇒ **而这个服务器一直在发槽 1 的 tag（15）而【从未】发槽 0 的**
8. ⇒ **客户端 actor 记录实测：model 落地为 `c_zom_ger_head` 而 `record+308`（tag 名字）是【空】**
9. ⇒ **所以 `sub_52FBE0` 为骨骼哈希了一个【空字符串】而那部分没有东西可挂**
```

### 3.3 **"头在槽 0 用 idx23 而我们发 idx15"**

**✅ 一个**精确的索引错位**。**

**⇒ 与 §240 的"附件在武器**之前**"、§318 的"索引 29 不是同一个字段"同族**（第三十四次）。

### 3.4 而 `1708h = 5896`

**⇒ 三层**：

```text
1. `add esi, 1708h`
2. ⇒ `0x1708 = 5896`
3. ⇒ **那是 TAG 带的基址**
```

**✅ 与 §310 的"标签块在 5896"**完全一致** ✓**

**⇒ **第四次确认 5896**。**

### 3.5 而 `record+308` 是**tag 名字**

**⇒ 三层**：

```text
1. 客户端的 actor 记录在 `+308` 存 tag 名字
2. ⇒ **而它是空的**
3. ⇒ 所以**哈希得到空字符串**
```

### 3.6 而**四个槽的完整对照表**

| 槽 | model 偏移 | model 索引 | tag 偏移 | tag 索引 |
|---|---|---|---|---|
| 0 | `+0x14` | 13 | `+0x24` | **23** |
| 1 | `+0x18` | 14 | `+0x28` | 15 |
| 2 | `+0x1C` | 16 | `+0x2C` | 17 |
| 3 | `+0x20` | 18 | `+0x30` | 19 |

**⚠ 而 model 索引是 13/14/16/18（跳过 15 与 17）而 tag 是 23/15/17/19。**

**⇒ 所以**两列的编号不平行**。**

**⇒ model 13、14、**16**、18 而 tag 23、15、17、19。**

**⚠ 若 model 索引本该是 13/14/15/16 而**实际是 13/14/16/18** ——**

**⇒ 说明**model 索引跳了 2** 而**tag 索引跳了 1**。**

**⇒ 符合"model +0x14/0x18/0x1C/0x20 步长 4 = 索引 13/14/15/16" ⇒ **但注释说 13/14/16/18**。**

**⚠ 所以注释里的 model 索引与偏移**不吻合**。**

**⇒ 偏移 `+0x14`/`+0x18`/`+0x1C`/`+0x20` 步长 4 ⇒ 索引应连续（13、14、15、16）。**

**⇒ 而注释说 13、14、**16**、18。**

**⚠ 一处矛盾**（可能因为表里有非连续项）。

## 四、`lastChangedField` 的**十个分支**

```cpp
const auto lastChangedField = attachTag0Changed
    ? AttachTag0FieldIndex          // 23
    : value != oldValue
    ? TeamFieldIndex                // 21
    : entityNumberChanged ? EntityNumberFieldIndex   // 20
    : attachTag1Changed   ? AttachTag1FieldIndex     // 15
    : attach1Changed      ? AttachModel1FieldIndex   // 14
    : attach0Changed      ? AttachModel0FieldIndex   // 13
    : attachmentMaskChanged ? AttachmentMaskFieldIndex  // 12
    : animStartChanged    ? AnimStartFieldIndex      // 10
    : animChanged         ? AnimIndexFieldIndex      // 9
                          : ModelIndexFieldIndex;    // 8
```

### 4.1 而**十项按索引降序**

```text
23, 21, 20, 15, 14, 13, 12, 10, 9, 8
```

**✅ 严格降序。**

**⇒ 所以"最后一个变化的字段" = **最大的索引**。**

### 4.2 而那段注释

```php
// THE HIGHEST INDEX WRITTEN. 8 < 13 < 14 < 20 < 21, and the writes
// below must ascend -- writeSkippedFieldIndex only walks forward.
// 23 IS NOW THE HIGHEST INDEX, above team 21, so it is tested
// FIRST. Getting this wrong is not cosmetic -- an understated
// lastChangedField desynchronises the reader exactly like the
// missing bump() that closed the client on the velocity fields.
```

**⇒ 六层**：

```text
1. **最高索引**：`8 < 13 < 14 < 20 < 21`
2. ⇒ 而**下面的写必须递增**（`writeSkippedFieldIndex` 只向前走）
3. ⇒ **而 23 现在是最高索引，在 team 21 之上，所以它【先被测试】**
4. ⇒ **搞错这个不是装饰性的**
5. ⇒ **一个低估的 `lastChangedField` 会失步读者**
6. ⇒ **正像那个在 velocity 字段上关闭客户端的【缺失的 `bump()`】**
```

### 4.3 **"那个在 velocity 字段上关闭客户端的缺失 `bump()`"**

**✅ 与 §334 的"86 不在线上导致跑出缓冲区"**同一类**（第三十五次）。**

### 4.4 而**三条声明**的遗留

```text
// THE HIGHEST INDEX WRITTEN, and the writes below must ascend: 8, then 20, then 21.
// THE HIGHEST INDEX WRITTEN. 8 < 13 < 14 < 20 < 21, and the writes below must ascend
// 23 IS NOW THE HIGHEST INDEX, above team 21, so it is tested FIRST.
```

**⇒ 三条注释记录**三次扩展**：**

```text
第一版  8, 20, 21
第二版  8, 13, 14, 20, 21
第三版  8, 13, 14, 20, 21, 23
```

**✅ 三个版本的遗留注释。**

## 五、`isAgent` 的**"零模型是安全标记"**

```php
// ONLY AN AGENT CARRIES THE ACTOR FIELDS. Players share this
// section (SvEmitPlayersInActorsSection) and leave modelIndex 0;
// baselining THEM on the actor default row would emit deltas that
// drive a player's model and entity number to zero. A zero model is
// exactly what spawnZombieActor refuses, so it is a safe marker.
const auto isAgent = state.modelIndex != 0;
```

### 5.1 五层

```text
1. **只有 agent 携带 actor 字段**
2. ⇒ **玩家共享这一节（`SvEmitPlayersInActorsSection`）而留 `modelIndex = 0`**
3. ⇒ **把他们基线到 actor 默认行会发出 delta 把玩家的模型与实体号驱到零**
4. ⇒ **一个零模型正是 `spawnZombieActor` 拒绝的**
5. ⇒ **所以它是一个安全的标记**
```

**✅ 与 §319 的"`actorModelIndex > 0` 拒绝零"**完全一致** ✓**

**⇒ 所以"零"在两个地方都是**明确的无效**。**

## 六、**"没有东西可说就整个跳过 delta -- 这一节的第三位"**

```php
// NOTHING TO SAY SKIPS THE DELTA ENTIRELY -- the section's third
// bit. This used to test the team alone; with a second field in
// the element it has to consider both, or a model change on a
// client whose team is unchanged would be silently dropped.
```

### 6.1 四层

```text
1. **没有东西可说就整个跳过 delta** —— 这一节的第三位
2. ⇒ **这过去只测 team 一个**
3. ⇒ **而一个元素里有了第二个字段就必须考虑两者**
4. ⇒ **否则一个 team 未变的客户端上的模型变化会被静默丢掉**
```

**✅ 与 §334 的"漏字段静默丢数据"同族**（第三次）。

### 6.2 而那个**巨大的 `if`**

```php
if (value == oldValue &&
    (!SvSendActorAgentElements || !isAgent ||
     (state.modelIndex == (oldState ? oldState->modelIndex : SvAgentDefaultModelIndex) &&
      state.entityNumber == (oldState ? oldState->entityNumber : SvAgentDefaultEntityNumber) &&
      state.attachModelIndex0 == ... &&
      state.attachTagIndex0 == ... &&
      state.attachModelIndex1 == ... &&
      state.attachTagIndex1 == ... &&
      state.attachmentIgnoreCollision == (oldState ? ... : 3u) &&
      state.animIndex == (oldState ? ... : 0) &&
      state.animStartTime == (oldState ? ... : 0))))
{
    message.MSG_WriteBits(0, 1);
    return;
}
```

**⇒ 九项 AND（含 `value == oldValue`）。**

**✓ 所以"没有东西可说"需要**九项**。**

## 七、关键结论

1. **agentState 的十个字段**（8/9/10/12/13/14/15/20/21/23）。
2. **五个非零默认**（1266 / 1267 / 1317 / 3 / 345）而其余为零。
3. **`unk_DA9920` 的 `+0x00C = 1266`** ⇒ 一个零基让模型索引错。
4. **⭐ `310 ^ 242 = 452`** 而 **`242 = 1266 & 0x3FF`** ⇒ 算术**完全闭合**（10 位掩码的效果）。
5. **⭐ "头在槽 0 所以它的 tag 是 23 而我们一直发槽 1 的 15"**。
6. **`add esi, 1708h` = 5896 = TAG 带基址** —— 第四次确认。
7. **`record+308` 是 tag 名字而它是空的 ⇒ 哈希空字符串 ⇒ 无东西可挂**。
8. **四个槽的对照表**，而 **model 索引 13/14/16/18 与偏移步长 4 不吻合**（一处矛盾）。
9. **`lastChangedField` 的十个分支严格降序**（23/21/20/15/14/13/12/10/9/8）。
10. **"低估 `lastChangedField` 会失步读者，正像那个关闭客户端的缺失 `bump()`"**。
11. **三条遗留注释记录三次扩展**（8,20,21 → +13,14 → +23）。
12. **`isAgent = modelIndex != 0`** —— 零是**安全标记**（`spawnZombieActor` 拒绝零）。
13. **"没有东西可说"需要九项 AND**。

## 八、未闭合点

- 四槽 model 索引 13/14/16/18 与偏移步长的矛盾。
- `unk_DA9920` 的完整默认行。
- 那条"关闭客户端的缺失 `bump()`" 的具体位置。
- `sv_snapshot_mp.cpp` 5200 行之后未读取（1.47 MB，进度 35%）。
