# 345 · **"客户端的基线 xmodel 不是文件的 xmodel"** —— `390/387`、`lastFieldIndex == lastChangedField` 的终局守卫、`velocity` 三字段崩溃

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 7998–8820 行（`writeChangedActor` 尾 + `writeChangedEntity` 完整）。

## 二、**`velocity` 三字段的崩溃**（本组第三重要）

### 2.1 那段

```php
// 33, THE HIGHEST OF THE THREE. Omitting this crashed the client the
// moment velocity became the highest changed field: three fields were
// written past lastChangedField, and MSG_ReadDeltaEntity reads a 3-bit
// skip index unconditionally after it, so the cursor desynchronised and
// took the rest of the snapshot with it. Any field added to this writer
// MUST be bumped here.
bump(velocityChanged, ActorVelocityXField + 2);
```

### 2.2 六层

```text
1. **33，三者中最高**
2. ⇒ **省略它会在 velocity 成为最高变化字段的那一刻崩溃客户端**
3. ⇒ **三个字段被写到了 `lastChangedField` 之外**
4. ⇒ **而 `MSG_ReadDeltaEntity` 在它之后【无条件】读一个三位跳号索引**
5. ⇒ **所以游标失步并带走快照的其余部分**
6. ⇒ **任何加到这个写入器的字段【必须】在这里被 bump**
```

### 2.3 而 `ActorVelocityXField + 2` 的**三字段**

```cpp
for (axis = 0; axis < 3; ++axis) {
    writeSkippedFieldIndex(message, ActorVelocityXField + axis, ...);
    writeRawFloatDelta(message, entity.actorVelocity[axis], fieldBaseline.actorVelocity[axis]);
}
```

**⇒ 31 / 32 / 33（`X` / `X+1` / `X+2`）。**

**✅ 与注释的"31, 32, 33"一致。**

**⚠ 而 `ActorVelocityXField + 2` = 33 是**最大值**。**

**⇒ 所以 `bump` 用 33。**

### 2.4 而 **"任何加到这个写入器的字段必须在这里被 bump"**

**✅ 与 §343 的"`bump` 从约定变结构"**第四处**（三处已修 + 这里）。**

**⚠ 但这是**注释要求**而非**结构性保证**。**

**⇒ 所以**仍然靠纪律**。**

**⇒ 而 §345 的终局守卫（见下）是**结构性的**。**

## 三、**`loopSound` 用 `writeEntityGround` 做编码器**

```cpp
// CODEC -96, and writeEntityGround IS its encoder: one bit for
// the 2046 sentinel, else a bit for zero, else Mixed(11) as
// three bits and a byte. Retail's zombie carries 2046 here,
// which is the sentinel arm exactly.
writeEntityGround(message, entity.actorLoopSound);
```

### 3.1 五层

```text
1. **编解码器 -96，而 `writeEntityGround` 就是它的编码器**
2. ⇒ **一位给 `2046` 哨兵**
3. ⇒ **否则一位给零**
4. ⇒ **否则 `Mixed(11)` 作为三位与一个字节**
5. ⇒ **而零售的僵尸在这里携带 `2046`，那正是哨兵分支**
```

### 3.2 而 `writeEntityGround` 的三分支（§342）

```text
groundEntityNum == EntityNumWorld ⇒ 一个 1 位
groundEntityNum == 0             ⇒ 0 + 1（共 2 位）
否则                              ⇒ 0 + 0 + 3 位低 + 8 位高
```

**✅ 所以 `EntityNumWorld == 2046`。**

**⇒ **一个可推算的常数**。**

**⚠ 而 §342 说 `EntityNumWorld` 与 `0` 是**两个不同语义**。**

**⇒ 这里确认：`2046` = 世界/无循环音，`0` = 零值。**

**✅ **完全闭合** ✓**

### 3.3 **"一个编码器服务两个语义"**

**⇒ 三层**：

```text
1. `writeEntityGround` 被用于 `groundEntityNum`（-96）
2. ⇒ **而也被用于 `actorLoopSound`（也是 -96）**
3. ⇒ **因为同一个编解码器**
```

**✅ 与 §343 的"三个裸 long lambda"同族（**一个编码器多处用**）。**

## 四、**"`groundEntityNum` 在 ET_ACTOR 上是裸 11 位，不是 -96"**（本组第四重要）

### 4.1 那段

```php
// PLAIN ELEVEN BITS on this eType, not codec -96. +0x088 is
// codec 11 here and the -96 row is +0x08C, one field over --
// the two swap roles against ET_PLAYER_CORPSE, where +0x08C is
// the -96 ground field. Reading the corpse's layout onto an
// actor puts the wrong encoder on both.
```

### 4.2 六层

```text
1. **在这个 eType 上是【裸十一位】，不是编解码器 -96**
2. ⇒ **`+0x088` 在这里是编解码器 11**
3. ⇒ **而 -96 的那一行是 `+0x08C`，隔一个字段**
4. ⇒ **这两个在 `ET_PLAYER_CORPSE` 上【互换角色】**
5. ⇒ **在那里 `+0x08C` 是 -96 的地面字段**
6. ⇒ **把尸体的布局读到 actor 上会把【两个】编码器都放错**
```

### 4.3 而**两个偏移**

```text
ET_ACTOR           +0x088 = codec 11（裸 11 位）    groundEntityNum
                   +0x08C = codec -96              loopSound

ET_PLAYER_CORPSE   +0x08C = codec -96             groundEntityNum
```

**⚠ 所以同一对偏移在两个表里**角色互换**。**

**✅ 与 §344 的"`groundEntityNum` 在布告上是字段 13 而在其它是 23"同族（**第五次"按 eType 重载"**）。**

**⇒ 而这是**偏移级**的互换（不是索引级）。**

## 五、**"编解码器 0 是一个浮点"** —— 与 demoq 的表示差

### 5.1 那段

```php
// CODEC 0 IS A FLOAT, and writeFullFloatDelta is the `bits == 0`
// arm: two present bits then a 32-bit XOR against the baseline.
// NOT writeUnsignedDelta -- demoq prints this field as a small
// int because it decodes codec 0 raw, and taking the tool's
// number for the field's storage is the representation gap
// section 10 warns about.
```

### 5.2 六层

```text
1. **编解码器 0 是一个浮点**
2. ⇒ **而 `writeFullFloatDelta` 就是 `bits == 0` 那一支**
3. ⇒ **两个 present 位然后一个 32 位 XOR 对基线**
4. ⇒ **不是 `writeUnsignedDelta`**
5. ⇒ **`demoq` 把这个字段打印成一个小整数因为它【裸】解码编解码器 0**
6. ⇒ **而把工具的数字当作字段的存储就是第 10 节警告的那个【表示差】**
```

### 5.3 **"表示差"**

**✅ 与 §340 的"一个表遍历器必须引用那张表"同族 —— 都是**推断链的边界**。**

**⇒ 而这里是"**工具的输出 ≠ 字段的语义**"。**

**⚠ 一个**极重要的工具纪律**：`demoq` 的整数是 `bit_cast<float>` 的低位视图。**

## 六、**`clientNum` 必须无条件断言**（本组第五重要）

### 6.1 那段

```php
// A PLAYER ENTITY MUST ALWAYS ASSERT ITS clientNum, and clientNum ZERO is
// exactly why. `sub_53DF40` picks which clientInfo a player renders from by
// reading entityState +0xA0 -- it is the link between the entity and the
// character -- and a field is only written when it DIFFERS from the
// baseline. Client 0's clientNum is 0, which is what an unwritten field
// already decodes to, so this server has NEVER sent it: measured in the
// client's own demo, `ent 1` carries +0x0A0 = 1 and `ent 0` carries the
// field not at all.
//
// That is harmless only while the client's baseline for the slot is
// genuinely zero. ENTITY NUMBERS ARE REUSED -- the same demo reports entity
// 0 with two lives -- so a player landing on a slot whose previous occupant
// left a non-zero +0xA0 inherits it, reads someone else's clientInfo or
// none, and draws nothing. Intermittent, and it depends on what held the
// slot before, which is exactly the shape of the invisible-player report.
//
// Section 140a is the same failure the other way round: a value equal to
// the baseline is skipped, and "equal to the baseline" is not the same as
// "the client already knows it". On a NEW entity -- no baseline, the case
// where the client has nothing -- assert it unconditionally.
const auto clientNumChanged =
    fieldBaseline.clientNum != entity.clientNum ||
    (!baseline && entity.eType == EntityTypePlayer);
```

### 6.2 十二层

```text
1. **一个玩家实体必须【总是】断言它的 `clientNum`，而 `clientNum` 为零正是原因**
2. ⇒ **`sub_53DF40` 通过读 `entityState +0xA0` 来挑一个玩家从哪个 clientInfo 渲染**
3. ⇒ **那是实体与角色之间的【连接】**
4. ⇒ **而一个字段只在它与基线【不同】时才被写**
5. ⇒ **客户端 0 的 `clientNum` 是 0，那正是一个未写字段已经解码成的**
6. ⇒ **所以这个服务器【从未】发送过它**：在客户端自己的 demo 里测量，`ent 1` 携带 `+0x0A0 = 1` 而 `ent 0` **完全不携带那个字段**
7. ⇒ **那只有在客户端那个槽的基线真的是零时才无害**
8. ⇒ **而【实体号是被复用的】** —— 同一个 demo 报告实体 0 有两条命
9. ⇒ **所以一个玩家落在一个前任留下了非零 `+0xA0` 的槽上就会【继承它】**
10. ⇒ **读到别人的 clientInfo 或一个都没有，而【什么也不画】**
11. ⇒ **间歇的，而它取决于之前什么占据那个槽 —— 那正是【隐形玩家报告】的形状**
12. ⇒ **第 140a 节是同一个失败的【另一个方向】**：一个等于基线的值被跳过，而"等于基线"与"客户端已经知道它"**不是同一件事**
```

### 6.3 **"'等于基线'与'客户端已经知道它'不是同一件事"**

**✅ 这是本文件里**最深刻的一条语义**。**

**⇒ 与 §341 的"它不是『别动这个条目』，它是『从基线重建它』"**同一类**。**

**⇒ 两次"省略 ≠ 正确"。**

### 6.4 而 **`sub_53DF40` 读 `+0xA0` 是"实体↔角色"的连接**

**✅ 与 §312 的"`CG_SetupClientCharacterInfo 0x00541800` 打开时若 `clientState+0x150 <= 0` 就返回"**不同** —— 那是**角色定制**，这是**实体→clientInfo**。**

**⚠ 所以两条**不同的**不可见路径：**

```text
§312  clientState+0x150（4 位）> 0 ⇒ 否则 CG_SetupClientCharacterInfo 不写模型名
§345  entityState+0xA0（clientNum）⇒ 决定从哪个 clientInfo 渲染
```

**✅ **两个不同的偏移、两个不同的函数、同一个症状（隐形）。**

### 6.5 而 `(!baseline && eType == Player)` 的**无条件**

**⇒ 三层**：

```text
1. `clientNum` 变了 ⇒ 写
2. ⇒ **或"无基线且是玩家" ⇒ 写**
3. ⇒ **所以新玩家的 clientNum 总是被断言**
```

**✅ 与 §344 的"布告无条件断言三字段"**同一模式（**第三次"无条件发送"**）。**

## 七、**`roll` 在这个 build 上不是玩家字段**（本组第六重要）

### 7.1 那段

```php
// ROLL IS NOT A PLAYER FIELD ON THIS BUILD. Measured 2026-08-26 against the
// retail dm capture: over 600 seconds a real server asserts ET_PLAYER index 28
// (+0x044, the angle trajectory's Z) exactly ZERO times, while this server
// asserted it 0.67 times a second. A player's roll is not something the client
// is told; it is the one field we send that retail does not.
//
// Suppressed for ET_PLAYER only -- index 28 is a different offset in every
// other type's table, and this writer serves them all.
const auto rollChanged = angleChanged[2] && entity.eType != EntityTypePlayer;
```

### 7.2 八层

```text
1. **roll 在这个 build 上不是玩家字段**
2. ⇒ **2026-08-26 对零售 dm 捕获测量**
3. ⇒ **600 秒里一个真实服务器断言 `ET_PLAYER` 索引 28（`+0x044`，角度轨迹的 Z）【恰好零次】**
4. ⇒ **而本服务器断言它每秒 `0.67` 次**
5. ⇒ **一个玩家的翻滚不是客户端被告知的东西**
6. ⇒ **它是我们发的、零售不发的那【一个】字段**
7. ⇒ **只为 `ET_PLAYER` 压制** —— 索引 28 在其它每个类型的表里是不同偏移
8. ⇒ **而这个写入器服务它们全部**
```

### 7.3 **"0.67 次/秒 vs 零次"**

**✅ 一个**极清晰的定量对照**。**

**⇒ 而"600 秒零次"是一个**定向的负面**（§340 第三次）。**

**⚠ 而**第四次定向的负面**（§265、§314、§340、§345）。**

### 7.4 而 **"那个写入器服务它们全部"**

**⇒ 三层**：

```text
1. `writeChangedEntity` 是**通用回退写入器**
2. ⇒ 服务**所有未专门处理的 eType**
3. ⇒ **所以任何"只对 ET_PLAYER 成立"的规则必须显式按 eType 门控**
```

**✅ 与 §344 的 `time2` 的 `entity.eType == EntityTypePlayer &&` **同族（**第二次**）。**

### 7.5 而 `time2Changed` 的同样门控

```cpp
// ET_PLAYER ONLY. Index 24 is a different offset in every other type's
// table and this writer serves them all, so a non-player must never emit it.
const auto time2Changed = entity.eType == EntityTypePlayer &&
    fieldBaseline.time2 != entity.time2;
```

**✅ **完全同一条理由**（措辞几乎相同）。**

**⚠ 所以**两条规则、同一个理由、两次手写**。**

## 八、**`writeChangedEntity` 的 `bump` 与它的详细理由**（本组第七重要）

### 8.1 那段

```php
// lastChangedField is a maximum, not the index of the last test in
// this block. Player fields are grouped by meaning above, while the
// wire order is different: time2 is field 24 after field 37's
// unknownA0 test, and trajectory delta Z is field 46 before the
// duration/time tests for fields 44/45. Plain assignment therefore
// announced 24 or 45 and still emitted a later field. The client
// stopped at the announced index and parsed that payload as the next
// entity, eventually corrupting player +0xEC and crashing in
// CG_EntityVisibleToPass after a respawn.
```

### 8.2 九层

```text
1. **`lastChangedField` 是一个最大值，不是这个块里最后一个测试的索引**
2. ⇒ **玩家字段【按意义】分组在上面，而线顺序不同**
3. ⇒ **`time2` 是字段 24 而在字段 37 的 `unknownA0` 测试【之后】**
4. ⇒ **而轨迹 delta Z 是字段 46 而在字段 44/45 的 duration/time 测试【之前】**
5. ⇒ **所以普通赋值宣告 24 或 45 而仍发出一个更晚的字段**
6. ⇒ **客户端在宣告的索引处停下并把那个载荷解析成【下一个实体】**
7. ⇒ **最终损坏玩家 `+0xEC`**
8. ⇒ **并在重生后在 `CG_EntityVisibleToPass` 里崩溃**
```

### 8.3 **"按意义分组而线顺序不同"**

**✅ 这是**本文件里最清晰的"两个顺序"陈述**。**

**⇒ 三层**：

```text
代码里：按【意义】分组（origin / angle / anim / event / ...
线顺序：按【索引】升序
⇒ 两者【不同】
```

**✅ 与 §343 的"5、7、8 放在 4 与 9 之间"**同一类**。**

**⇒ 第三、四次确认。**

### 8.4 而 **"损坏 `player +0xEC` 并在 `CG_EntityVisibleToPass` 里崩溃"**

**✅ 一个**完整的因果链**（位失步 → 载荷误读 → 内存损坏 → 崩溃在命名函数）。**

**⇒ 与 §343 的"`mp_rust_long` 卡加载屏"**不同的表现**（那里是卡，这里是崩）。**

**⚠ 而两者**同一个根因**（`lastChangedField` 不是最大值）。**

**⇒ 一个根因两种症状。**

## 九、**终局守卫：`lastFieldIndex == lastChangedField`**（本组最重要的一段）

### 9.1 那段

```cpp
// Refuse a malformed record even if a future field is inserted in
// the wrong lastChanged calculation order. The decoder stops at
// the announced maximum; emitting a field beyond it shifts every
// following entity in the packet.
return lastFieldIndex == static_cast<std::int32_t>(lastChangedField) &&
    !message.overflowed();
```

### 9.2 六层

```text
1. **拒绝一个畸形的记录，即使一个未来的字段被插到错误的 `lastChanged` 计算顺序里**
2. ⇒ **解码器在宣告的最大值处停下**
3. ⇒ **发出一个超过它的字段会移动包里的每一个后续实体**
4. ⇒ **所以返回 `lastFieldIndex == lastChangedField && !overflowed()`**
5. ⇒ **`lastFieldIndex` 是【实际写的最后一个索引】**
6. ⇒ **`lastChangedField` 是【宣告的那个】**
```

### 9.3 **"这是一个结构性保证"**

**✅ 与 §343 的"`bump` 从约定变结构"**第二次**（**这是真正的结构**）。**

**⇒ 三层**：

```text
① `bump`（max）⇒ 防止算错
② `lastFieldIndex == lastChangedField` ⇒ **事后验证**
⇒ **两道防线**
```

**✅ **一个双保险**。**

**⚠ 而只有 `writeChangedEntity` 有这个终局守卫。**

**⇒ `writeChangedScriptMover` / `writeChangedPlayerCorpse` / `writeChangedActor` / `writeChangedActorCorpse` / missile / item / event 都**没有**。**

**⚠ 一处**不对称**。**

**⇒ 而 §343 的"`bump` 已修两处而 `writeChangedEventEntity` 未修"是**另一个不对称**。**

**⚠ 所以本文件里 `lastChangedField` 的正确性有**四种不同的保证强度**：**

```text
最强    writeChangedEntity          bump + 终局守卫
强      scriptMover / corpse        bump
中      actor                       bump（含 velocity 注释警告）
弱      eventEntity / missile / item / actorCorpse   普通赋值
```

**✅ 一个**极清晰的强度谱**。**

**⇒ 而 `actorCorpse` 与 `eventEntity` 用普通赋值 ⇒ **它们依赖书写顺序**。**

**⚠ 一个**真实的、尚未覆盖的风险**。**

## 十、**`OLMOD_LOG_ENTITY_EVENTS` 的无偏计数**（本组第八重要）

### 10.1 那段

```php
// AN UNBIASED COUNT OF WHAT ACTUALLY GOES ON THE WIRE.
//
// The `playerstate->entitystate inputs` line next door is capped
// at 64 reports per entity-state buffer, so it only ever shows
// the first seconds after a spawn -- when nobody is shooting.
// Reading a histogram off it said "this server never sends
// EV_FIRE_WEAPON", and that conclusion was drawn from a sample
// that could not contain one. This counts EVERY event this
// writer emits and reports totals, so a zero here is a real
// zero. SILENT UNLESS ASKED: OLMOD_LOG_ENTITY_EVENTS=1.
```

### 10.2 九层

```text
1. **一个对真正上线的东西的【无偏】计数**
2. ⇒ 隔壁的 `playerstate->entitystate inputs` 行**被限制在每实体状态缓冲区 64 条报告**
3. ⇒ **所以它只显示出生后的最初几秒 —— 那时没人在开枪**
4. ⇒ **从它上面读一个直方图说"这个服务器从不发 `EV_FIRE_WEAPON`"**
5. ⇒ **而那个结论是从一个【不可能包含一个】的样本上得出的**
6. ⇒ **这个计数这个写入器发出的【每一个】事件并报告总数**
7. ⇒ **所以这里的一个零是一个真正的零**
8. ⇒ **除非被要求否则静默：`OLMOD_LOG_ENTITY_EVENTS=1`**
```

### 10.3 **"从一个不可能包含一个的样本得出结论"**

**✅ 与 §340 的"定向的负面"**互为反面**。**

**⇒ 三层**：

```text
定向的负面：按它必须出现的方式找而零命中 ⇒ 确定不存在
采样偏差：一个【不可能】包含它的样本里零命中 ⇒ 什么也不能说
```

**✅ **一对精确区分的证据学概念**。**

**⚠ 而这里正是**被采样偏差骗了**的一次。**

**⇒ 与 §340 的"§82e 的诊断错而建议对"**同族（**自己推翻自己**）。**

### 10.4 而 200 次的批量报告

```cpp
if (++sinceReport >= 200) {
    sinceReport = 0;
    std::string line = "entity-events sent";
    for (candidate = 0; candidate < eventHistogram.size(); ++candidate) {
        if (!eventHistogram[candidate]) continue;
        line += " " + std::to_string(candidate) + ":" + std::to_string(eventHistogram[candidate]);
    }
    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
}
```

**⇒ 四层**：

```text
① 256 个槽的静态直方图
② 每 200 次发一行
③ 只打印非零的
④ ⇒ 格式 "index:count index:count ..."
```

**⚠ 而直方图**从不重置**（`sinceReport` 重置但 `eventHistogram` 不）。**

**⇒ 所以报告的是**累计**。**

**✅ 与注释"报告总数"一致 ✓**

## 十一、**"客户端的基线 xmodel 不是文件的 xmodel"**（本组最重要的第二段）

### 11.1 那段

```php
// THE CLIENT'S BASELINE xmodel IS NOT THE FILE'S xmodel.
//
// The shipped `<map>_const.ff` stores the index RETAIL's
// server assigned. The client does not keep that: it
// re-resolves every model into its OWN configstring band at
// map load, so `cl.entityBaselines[n].xmodelIndex` holds the
// index THIS server published. MEASURED by reading the live
// client (Tools/read-client-entity-baseline.py): entity 42
// holds 390 where the file says 387, 43/44/45 hold 410 for
// 407, 270 holds 388 for 385 -- every non-zero one exactly
// this server's own value, and a zero staying zero.
//
// Deltaing against the FILE's number therefore sends
// `ours ^ file` and the client computes `ours ^ ours ^ file`
// = FILE, landing it three slots away in this server's band
// -- a different model entirely. That is the whole bug: the
// consoles by the first door came out as zombie bodies while
// their positions, their numbering and their other fields
// were all correct.
//
// Using this entity's own model index makes the field equal
// to the baseline, so it is not sent at all and the client
// keeps the value it already resolved -- which is the right
// one. Brush models are unaffected: their xmodel is zero on
// both sides.
```

### 11.2 十四层

```text
1. **客户端的基线 xmodel 【不是】文件的 xmodel**
2. ⇒ **已发货的 `<map>_const.ff` 存储【零售服务器】分配的那个索引**
3. ⇒ **客户端不保留它**：它在地图加载时把每一个模型**重新解析进它自己的 configstring 带**
4. ⇒ **所以 `cl.entityBaselines[n].xmodelIndex` 持有【本服务器】发布的那个索引**
5. ⇒ **通过读活客户端测量**（`Tools/read-client-entity-baseline.py`）：
     · 实体 42 持有 **390** 而文件说 **387**
     · 43/44/45 持有 **410** 而文件 **407**
     · 270 持有 **388** 而文件 **385**
6. ⇒ **每一个非零的恰好是本服务器自己的值，而一个零保持零**
7. ⇒ **所以对着【文件的】数字 delta 会发 `ours ^ file`**
8. ⇒ **而客户端算 `ours ^ ours ^ file` = `file`**
9. ⇒ **落在本服务器带里偏三槽的地方 —— 一个完全不同的模型**
10. ⇒ **那就是整个 bug**：**第一扇门旁边的控制台出来成了僵尸身体**
11. ⇒ **而它们的位置、编号和其它字段都正确**
12. ⇒ **用这个实体自己的模型索引让字段【等于基线】**
13. ⇒ **所以它完全不发而客户端保留它已经解析的值 —— 那是对的**
14. ⇒ **画笔模型不受影响：它们的 xmodel 两边都是零**
```

### 11.3 **三个偏移 = `+3`**

```text
390 - 387 = 3
410 - 407 = 3
388 - 385 = 3
```

**✅ **三个样本都是 +3。** —— 一个**极强的一致性**。**

**⚠ 而"偏三槽"就是这 3。**

**⇒ 所以**本服务器发布的模型比零售分配的晚三个槽**。**

**⚠ 一个**可解释的差值**（可能因为本服务器发布模型的方式不同）。**

**✅ **极其清晰的证据链。**

### 11.4 而 **"控制台出来成了僵尸身体"**

**✅ 一个**具体的、可复查的症状**。**

**⇒ 与 §342 的"僵尸从不画"、§343 的"道具位置错"**第三次具体视觉症状**。**

**⚠ 三个不同 bug 三个可见症状。**

### 11.5 而**修正手法："让字段等于基线所以不发"**

**⇒ 三层**：

```text
1. `constBaselineStorage.modelIndex = entities[currentIndex].modelIndex;`
2. ⇒ **字段等于基线**
3. ⇒ **所以不发**
4. ⇒ **而客户端保留它自己解析的值**
```

**✅ 一个**极优雅的"用省略来保证正确"**。**

**⚠ 与 §341 的"省略是常态"**同族但更强**（这里是**故意**用省略避免错误）。**

**⇒ 与 §344 的"`constBaselineState` 的轨迹必须复制"**相反**：**

```text
§344  留零 ⇒ 字段"未变" ⇒ 客户端保留【行的零】 ⇒ 错（继承速度）
§345  设成本地值 ⇒ 字段"未变" ⇒ 客户端保留【它自己的正确值】 ⇒ 对
```

**✅ **两个方向，同一个"字段等于基线就不发"的机制**。**

**⇒ 而正确性取决于**基线必须等于客户端真正持有的值**。**

**✅ 与 §343 的"坐标要对着它被编码时用的那个基线测"**完全同族。**

**⇒ **第三次确认那条原则。**

## 十二、**`(0, 0)` 是"未变"而"变化但无字段"不可编码**（本组第三重要）

### 12.1 那段

```php
// AN ENTITY IDENTICAL TO ITS BASELINE HAS ITS OWN ENCODING, AND IT IS
// NOT "a changed entity with nothing changed".
//
// MSG_ReadDeltaEntity (sub_671170 on out.exe) reads, in order: a
// removed bit, a CHANGED bit, and only if that is set the new-entity
// flag, six bits of lastChangedField, and then -- UNCONDITIONALLY --
// a three-bit skip index:
//
//     if (readBit()) return 1;               // removed
//     if (!readBit()) { memcpy(ent, baseline, 280); return 0; }
//     v28 = readBit();                       // new-entity flag
//     v26 = readBits(6);                     // lastChangedField
//     v13 = readBits(3) - 1;                 // ALWAYS read
//
// So there is no way to say "changed, but no fields": emitting the
// header and writing no field leaves the client reading three bits of
// the NEXT entity's number as a skip index, and every bit after that is
// misaligned. The client then never completes a frame -- black screen,
// no acks, timeout -- which is what arming this did on 2026-08-31.
```

### 12.2 十层

```text
1. **一个与它基线完全相同的实体有它【自己的】编码**
2. ⇒ **而它不是"一个变化了的而什么都没变的实体"**
3. ⇒ `MSG_ReadDeltaEntity`（`out.exe` 的 `sub_671170`）按顺序读：
     · 一个 removed 位
     · 一个 CHANGED 位
     · **只在它置位时**：新实体标志、六位 `lastChangedField`
     · **然后 —— 【无条件】—— 一个三位跳号索引**
4. ⇒ **所以没有办法说"变了但没有字段"**
5. ⇒ **只发头而不写任何字段让客户端把【下一个实体编号】的三位读成一个跳号索引**
6. ⇒ **而之后的每一位都错位**
7. ⇒ **客户端于是永不完一帧 —— 黑屏、无 ack、超时**
8. ⇒ **而那正是 2026-08-31 武装这个时发生的**
9. ⇒ **正确的答案是第二位**：`(0, 0)` 意思是"未变"
10. ⇒ **而客户端逐字取它的基线**
```

### 12.3 而 **`memcpy(ent, baseline, 280)`**

**⇒ `280` 字节。**

**✅ 与 §341 的 `352`（`0x160`）**不同**。**

**⚠ 所以**两个尺寸：**

```text
280 = 0x118    entityState（这里）
352 = 0x160    clientInfo（§341）
```

**✅ 两个不同的结构。**

**⚠ 而 §255 的 `clientState` stride `0x160` = `352` ✓**

### 12.4 而**"2026-08-31"**

**✅ 一个具体日期（与 §343 的 2026-08-24、§342 的 2026-10-08 同族）。**

**⇒ **第五次具体日期**。**

### 12.5 而 `(0, 0)` 的两个位

```cpp
message.MSG_WriteBits(0, 1);      // ① removed = 0
message.MSG_WriteBits(0, 1);      // ② changed = 0
```

**✅ 而 §345 的 `writeChangedEntity` 开头：**

```cpp
message.MSG_WriteBits(0, 1);      // removed = 0
message.MSG_WriteBits(1, 1);      // changed = 1
message.MSG_WriteBits(baseline ? 0 : 1, 1);   // new-entity
```

**⇒ 所以**每个实体总是以两个位开始**，然后若 changed 则有三个多段。**

**✅ 一个**极简的头**。**

## 十三、`writeEntities` 的**双指针归并与三个分支**

```cpp
while (currentIndex < entities.size() || (baseline && baselineIndex < baseline->size()))
{
    const auto entityNum = std::min(currentNum, baselineNum);
    writeEntityNumber(message, entityNum, lastEntityNum);
    if (baselineNum < currentNum)                        // ① 只在基线里 ⇒ 删除
    {
        message.MSG_WriteBits(1, 1);
        ++baselineIndex;
        continue;
    }
    if (baselineNum == currentNum && (*baseline)[baselineIndex] == entities[currentIndex])
    {                                                     // ② 相同 ⇒ (0,0)
        message.MSG_WriteBits(0, 1);
        message.MSG_WriteBits(0, 1);
        ++baselineIndex;
    }
    else
    {                                                     // ③ 变了
        ...
    }
    ++currentIndex;
}
writeEntityNumber(message, MaxEntityNumber, lastEntityNum);
```

### 13.1 四层

```text
① `baselineNum < currentNum` ⇒ **删除位**（一个 1 位）
② 相同（整条记录比较）⇒ **(0, 0)**
③ 否则 ⇒ **const baseline 查找 + writeChangedEntity**
④ 循环后 `MaxEntityNumber` 终止
```

**✅ 与 §337 的 `writeLegacyClients` **完全同构**（双指针 + `UINT32_MAX` 哨兵 + 终止位）。**

**⇒ **第二次确认那个归并结构。**

### 13.2 而 **`sameActorPacketEntity`**

```cpp
if (baselineNum == currentNum &&
    ((*baseline)[baselineIndex] == entities[currentIndex] ||
     (entities[currentIndex].eType == EntityTypeActor &&
      sameActorPacketEntity((*baseline)[baselineIndex], entities[currentIndex]))))
```

**⇒ 三层**：

```text
1. **整条记录比较**
2. ⇒ **或**（对 `EntityTypeActor`）一个专门的"同一 actor 包实体"比较
3. ⇒ **所以 actor 有一个更宽松的等价**
```

**⚠ 因为 actor 有**未上线的成员**（`SvActorSendUnmeasuredSpawnWords` 门控的那些）。**

**⇒ 所以"相等"必须**只看上线字段**。**

**✅ 与 §341 的"在整个记录上比较"**相反**（那里是**保守**：整条记录不等就发；这里是**宽松**：上线字段相同就跳过）。**

**⚠ 两个不同方向但都正确（因为 actor 的未上线字段**总是零** ⇒ 整条比较会对每个 actor 每帧都发）。**

**⇒ 一个**必要的性能优化**。**

## 十四、`SV_WritePacketEntities` 的**准入**（第六层）

```cpp
const auto validEntity = [](const SvEntityState &entity) {
    if (eType == General) return validGeneralBrushModelEntity(entity) || SV_IsGrenadeExplosionEntityValid(entity);
    if (eType == Missile) return validMissileEntity(entity);
    if (eType == Item) return validItemEntity(entity);
    if (eType == ScriptMover) return validScriptMoverEntity(entity);
    if (eType == ActorCorpse) return validActorCorpseEntity(entity);
    if (eType == Actor) return validActorEntity(entity);
    if (eType == PlayerCorpse) return validPlayerCorpseEntity(entity);
    if (eType == BulletHit || BulletHitClient || MeleeHit) return validBulletImpactEntity(entity);
    if (eType == Obituary) return validObituaryEventEntity(entity);
    if (eType == SoundAlias || SoundAliasAsMaster || PlayFx ||
        eType == EventBase + 117 || eType == Exploder) return validSimpleEventEntity(entity);
    return eType == Player && ...;        // ← 四十项 AND
};
```

### 14.1 三层

```text
1. **十一类 eType 各有验证器**
2. ⇒ **而最后的回退是 `EntityTypePlayer`**（四十项 AND）
3. ⇒ **其它一切 eType ⇒ 返回 false**
```

**✅ 与 §322 的"一个缺席的 eType 在序列化前被丢掉"**完全一致 ✓**

**⇒ 而这里是**那个 allowlist 的实现**。**

**⚠ 所以"僵尸从不画"的机制在此：**

```text
Actor ⇒ validActorEntity    ← 有
但若 validActorEntity 失败 ⇒ 整个实体被丢掉
```

**⇒ 而 §344 的注释说"actor 验证通过、帧健康、但不画"。**

**⇒ 所以**不是准入层** —— 是**字段层**（十八个只发五个）。**

**✅ **两个层次都被穷尽了。** —— 一个**完整的诊断**。**

### 14.2 而 `EventBase + 117` 在 `validSimpleEventEntity` 组里

**✅ 与 §342 的"`EntityTypeEventBase + 117 == 140`"**第二次确认 ✓**

### 14.3 而 `sortedUniqueInRange` 的四道检查

```cpp
if (!sortedUniqueInRange(entities, &SvEntityState::number, MaxEntityNumber) ||
    !all_of(entities, validEntity) ||
    (baseline && !sortedUniqueInRange(*baseline, &SvEntityState::number, MaxEntityNumber)) ||
    (baseline && !all_of(*baseline, validEntity)) ||
    !all_of(mapCenter, isfinite))
    return false;
```

**⇒ 五道**（实体排序/实体验证/基线排序/基线验证/地图中心）。**

**✅ 一个**完整的准入**。**

**⚠ 而基线也被验证** —— **可能因为基线来自客户端确认（可能被篡改）。**

**✅ 一个**防御性输入验证**。**

## 十五、`SV_ValidateSnapshotFrame` 的**十九种失败名**（本组第九重要）

```text
None / SceneFlags / MapCenter / PlayerStateOrder / AnimationCommands /
ClientOrder / ClientTeam / EntityOrder / ClientInfoOrder / Glass /
PlayerClientCount / AgentOrder / ClientInfoOwner / ClientInfoDomain /
PlayerStateClientJoin / PlayerStateDomain / PlayerEntityJoin /
PlayerEntityDomain / EntityDomain
```

### 15.1 **"一个失败名比一个布尔值值钱"**

**✅ 与 §344 的"故意大声"同族（**第二次）。**

**⇒ 一个枚举 + 一个名字函数 ⇒ **可诊断**。**

### 15.2 而**七个 Join/Order/Domain 三分**

```text
Order   排序/唯一性
Join    跨段引用完整性
Domain  值的定义域
```

**✅ 一个**清晰的三分法**。**

**⚠ 而 `PlayerStateClientJoin` 在代码里被**复用四次**（factoryTraveler / zombieReviver / deathViewTargets / killcamReplayPoses）。**

**⇒ 一处**命名略粗**。**

### 15.3 而 `factoryTravelerGenerations` 的检查

```cpp
for (const auto &[recipient, generation] : frame.factoryTravelerGenerations) {
    const auto player = findPlayerState(frame, recipient);
    if (!player || !player->health || player->pmType != SvPmTypeNormal ||
        player->spawnGeneration != generation)
        return reject(PlayerStateClientJoin);
}
```

**⇒ 四项**（存在 / 活着 / 普通模式 / 世代匹配）。**

**✅ 与 §331 的"`spawnGeneration` 是防止跨死亡的引用"**配合。**

## 十六、关键结论

1. **`velocity` 三字段（31/32/33）必须 `bump(..., +2)`** —— 省略 ⇒ 客户端崩溃。
2. **`loopSound` 用 `writeEntityGround` 做 -96 编码器**，而零售僵尸携带 `2046` ⇒ **`EntityNumWorld == 2046`**（可推算常数）。
3. **`groundEntityNum` 在 ET_ACTOR 上是裸 11 位**（`+0x088` = codec 11）而 `loopSound` 是 `+0x08C` 的 -96 —— **两个在 ET_PLAYER_CORPSE 上互换角色**。
4. **"编解码器 0 是一个浮点"而 `demoq` 打印成小整数** —— 第 10 节警告的**表示差**。
5. **⭐ `clientNum` 必须无条件断言** —— `sub_53DF40` 从 `entityState+0xA0` 挑 clientInfo。
6. **"客户端 0 的 `clientNum` 是 0 正是一个未写字段解码成的 ⇒ 从未发送过"**。
7. **"`ent 1` 携带 `+0x0A0 = 1` 而 `ent 0` 完全不携带"** —— demo 实测。
8. **"实体号被复用 ⇒ 继承前一个占用者的 `+0xA0` ⇒ 什么也不画"** —— **隐形玩家的第四个根因**。
9. **⭐ "『等于基线』与『客户端已经知道它』不是同一件事"** —— 本文件最深刻的一条语义。
10. **⭐ "roll 在这个 build 上不是玩家字段"** —— 600 秒零售**零次** vs 我们 0.67 次/秒。
11. **`time2` 与 `roll` 两个"只对 ET_PLAYER"的规则同一条理由两次手写**。
12. **`lastChangedField` 是最大值而玩家字段按意义分组、线序按索引** —— `time2`(24) 在 37 之后测、轨迹 delta Z(46) 在 44/45 之前。
13. **"损坏 `player +0xEC` 并在 `CG_EntityVisibleToPass` 里崩溃"** —— 一个完整的因果链。
14. **⭐ 终局守卫 `lastFieldIndex == lastChangedField && !overflowed()`** —— 结构性保证。
15. **四种不同强度的 `lastChangedField` 保证**（bump+守卫 / bump / bump+注释 / 普通赋值）—— **一个清晰的强度谱**。
16. **`OLMOD_LOG_ENTITY_EVENTS` 的无偏计数** —— 因为 `playerstate->entitystate inputs` **被限制在 64 条**。
17. **"从一个不可能包含一个的样本得出结论"** —— **采样偏差**，与"定向的负面"互为反面。
18. **⭐ "客户端的基线 xmodel 不是文件的 xmodel"** —— 客户端在地图加载时**重新解析进自己的 configstring 带**。
19. **三个样本都是 `+3`**（390/387、410/407、388/385）—— 极强的一致性。
20. **"第一扇门旁边的控制台出来成了僵尸身体而位置/编号/其它字段都正确"**。
21. **"用实体自己的模型索引让字段等于基线所以不发"** —— **故意用省略保证正确**，与 §344 的"留零导致继承速度"**相反**。
22. **⭐ "变化但无字段"不可编码** —— 客户端**无条件**读三位跳号索引 ⇒ "2026-08-31 黑屏"。
23. **`memcpy(ent, baseline, 280)`** —— `entityState` 是 **280** 字节（`clientInfo` 是 352）。
24. **`writeEntities` 的双指针归并与三分支**（删除 / `(0,0)` / 变更）—— 与 `writeLegacyClients` 同构。
25. **`sameActorPacketEntity` 只看上线字段** —— 因为 actor 的未上线字段总是零。
26. **`SV_WritePacketEntities` 的十一类验证器 + 玩家回退** ⇒ 其它 eType **一律丢弃**（allowlist 的实现）。
27. **"僵尸从不画"的机制**：不在准入层而在**字段层**（18 个只发 5 个）。
28. **`SV_ValidateSnapshotFrame` 的十九种失败名**，Order/Join/Domain 三分法。

## 十七、未闭合点

- `MaxEntityNumber` / `EntityNumWorld`(=2046) / `EntityNumNone` 三个常数的关系。
- `sameActorPacketEntity` 的完整实现。
- `writeChangedActorCorpse` / `eventEntity` 的普通赋值是否真的按索引升序排好。
- `CG_EntityVisibleToPass` 的地址。
- `.ff` 文件的模型索引与本服务器索引 +3 的关系（是否由发布顺序决定）。
- `sv_snapshot_mp.cpp` 8820 行之后未读取（27,016 行，进度 33%）。
