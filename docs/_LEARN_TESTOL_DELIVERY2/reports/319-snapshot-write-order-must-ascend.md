# 319 · **写序必须递增**（否则毁掉 724 个 brush model）、`ET_ACTOR` 的 18 字段、`sameActorPacketEntity` 的四段因果

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 1199–1400 行。

## 二、**写序必须递增**（本组最重要的一段）

### 2.1 那段

```php
// ---- ET_ACTOR, table 0x00DA5DE8, 63 fields, eType dispatch entry 19 ----
//
// EVERY INDEX BELOW IS READ OFF THAT TABLE, and the demo census matches
// it entry-for-entry (re/demo-re/netfields-ol-named/
// entity-et19-ET_ACTOR-0x00DA5E08.tsv). 3.3.3.3's actor table has 61
// fields; NEVER index across builds.
//
// THE WRITE ORDER BELOW MUST ASCEND. writeSkippedFieldIndex walks
// strictly forward and cannot go back, and a field emitted out of order
// does not make a wrong zombie -- it desynchronises the client's bit
// cursor for the rest of the snapshot and takes the 724 working brush
// models with it.
```

### 2.2 七层

```text
1. `ET_ACTOR` 表在 **`0x00DA5DE8`**，**63 个字段**，eType 分派入口 **19**
2. ⇒ **下面每一个索引都是从那张表读出的**，而 demo 普查**逐条匹配**
3. ⇒ **3.3.3.3 的 actor 表有 61 个字段 ⇒ 绝不跨 build 索引**
4. ⇒ **下面的写序必须【递增】**
5. ⇒ `writeSkippedFieldIndex` **严格向前走而不能回头**
6. ⇒ 而**一个乱序发出的字段不会造出一个错的僵尸** ——
7. ⇒ **它会失步客户端的位游标，对快照的其余部分，并带走那 724 个能工作的 brush model**
```

### 2.3 **"带走 724 个能工作的 brush model"**

**⇒ 三层**：

```text
1. 一个乱序字段 ⇒ 位游标失步
2. ⇒ 快照的**其余部分全错**
3. ⇒ 包括**724 个能工作的 brush model**
```

**⚠ 而 §302 说"这个服务器完全不发布 brush model"。**

**⇒ 所以 724 是**能工作但没发布的**？**

**⇒ 或者 724 是**另一个上下文**（actor 所在的快照）。**

**⚠ 一个需要核对的矛盾。**

## 三、`ET_ACTOR` 的**十八个字段**（本组第二重要）

```php
constexpr std::uint32_t ActorAngleYField = 1;            // +0x040 -79
constexpr std::uint32_t ActorOriginXField = 2;           // +0x018 -83
constexpr std::uint32_t ActorOriginYField = 3;           // +0x01C -82
constexpr std::uint32_t ActorOriginZField = 4;           // +0x020 -81
constexpr std::uint32_t ActorEventCounterField = 5;      // +0x0B4 -75
constexpr std::uint32_t ActorFirstEventField = 6;        // 四槽 +0x0B8/+0xC0/+0xC8/+0xD0
constexpr std::uint32_t ActorLoopSoundField = 10;        // +0x08C -96
constexpr std::uint32_t ActorField0058 = 11;             // +0x058 32
constexpr std::uint32_t ActorField005C = 12;             // +0x05C 32
constexpr std::uint32_t ActorEFlagsField = 14;           // +0x008 -98
constexpr std::uint32_t ActorGroundEntityField = 16;     // +0x088 11
constexpr std::uint32_t ActorPositionTrajectoryTypeField = 19;  // +0x00C 8
constexpr std::uint32_t ActorAngleTrajectoryTypeField = 20;     // +0x030 8
constexpr std::uint32_t ActorField00AC = 28;             // +0x0AC 24
constexpr std::uint32_t ActorAppearanceField = 29;       // +0x09C 10
constexpr std::uint32_t ActorField0054 = 30;             // +0x054 codec 0
constexpr std::uint32_t ActorVelocityXField = 31;        // +0x024/028/02C codec -80
constexpr std::uint32_t ActorAttackerEntityField = 39;   // +0x084 11
constexpr std::uint32_t ActorPartBits0Field = 53;        // +0x0E8 32
```

### 3.1 十九个（含 `ActorFirstEventField` 代表四槽）

```text
1, 2, 3, 4, 5, [6..9], 10, 11, 12, 14, 16, 19, 20, 28, 29, 30, 31, 39, 53
```

**⇒ 19 个常量但代表 22 个字段（`6..9` 是四个）。**

### 3.2 而**四个事件槽 + 一个"第五候选被排除"**

```php
// Four slots, 8-byte stride, fields 6..9 -> +0x0B8/+0xC0/+0xC8/+0xD0.
// The table's fifth candidate at +0x0B0 (field 15, codec -93) is NEVER
// asserted on an ET_ACTOR anywhere in the census, so it is not sent.
constexpr std::uint32_t ActorFirstEventField = 6;
```

**⇒ 三层**：

```text
1. **四个槽，8 字节步长**，字段 6..9 → `+0x0B8/+0xC0/+0xC8/+0xD0`
2. ⇒ 表的**第五候选**在 `+0x0B0`（字段 15，codec `-93`）
3. ⇒ **在普查的任何地方都从未在 ET_ACTOR 上被断言 ⇒ 所以不发**
```

**✅ 一个**"未断言就不发"**的决策。**

**⇒ 与 §318 的"`movementDir` 零次断言 ⇒ 不发"同族（第五次"零断言即不发"）。**

### 3.3 而三个**未解释的字段**

```php
// GATE, ALL-OR-NOTHING, with the evidence in the comment.
//
// Three of the eighteen fields retail sends on a zombie's first frame
// are values this project has NOT explained: +0x058 is a packed
// animation word whose layout changes over the life (12.2), +0x0AC is
// 24 bits with nine distinct values and a name the const baselines
// disproved at that offset on another eType, and the event slots carry
// ids whose meaning is unread. They are sent because the capture sends
// them and an actor that validates without them does not draw -- but
// they are the three most likely to be wrong, so they turn off together.
//
// Turning this off leaves the fifteen MEASURED fields on the wire.
constexpr bool SvActorSendUnmeasuredSpawnWords = true;
```

### 3.4 七层

```text
1. **十八个字段里的三个是本项目【没有解释】的**
2. ⇒ `+0x058` 是一个**打包的动画字**而其布局在生命期内变化（12.2）
3. ⇒ `+0x0AC` 是 **24 位有九个不同值**而**const baselines 在另一个 eType 的那个偏移上 disproved 了一个名字**
4. ⇒ 而**事件槽携带的 id 含义未读**
5. ⇒ **它们被发是因为捕获发了它们**而**一个不带它们就 validate 的 actor 不绘制**
6. ⇒ 但它们**是最可能错的那三个** ⇒ **所以它们一起关掉**
7. ⇒ 关掉**留下十五个【测量过的】字段在线**
```

### 3.5 **"验证而不带它们就不绘制"**

**⇒ 三层**：

```text
1. 不带那三个 ⇒ actor 不绘制
2. ⇒ 所以**必须发**
3. ⇒ 而**它们最可能错**
```

**✅ 一个**有意的权衡**（宁可发可能错的也不要不绘制）。**

**⇒ 而"一起关掉"意味着**全有或全无**。**

### 3.6 而 **`SvActorSendUnmeasuredSpawnWords = true`** 是**编译期**

**⇒ 所以当前**发**那三个。**

## 四、`EventEntityImpactSurfaceField = 15` 的**六位**（本组第三重要）

### 4.1 那段八层

```php
// ET_EVENTS field 15 (es+0x00A0, SIX BITS). The client clamps it to 18
// and indexes a 19-entry table with it -- `v310 = es+0xA0; if (v310 >
// 0x12) v310 = 0` in CG_EntityEvent's prologue -- so it is a surface
// kind, and the retail dm demo asserts it on the flesh hit and NOWHERE
// ELSE: 6 on 202 of 204 EV_BULLET_HIT_CLIENT_SMALL and on all 90 LARGE,
// never once on the 1419 EV_BULLET_HIT. It rides in `unk00A0`, which
// every other event-entity validator here pins to zero, rather than in
// a new struct member -- growing SvEntityState moves the address-keyed
// native buffer WorldClientState is sized against (sect.184h).
constexpr std::uint32_t EventEntityImpactSurfaceField = 15;
```

### 4.2 八层

```text
1. **`ET_EVENTS` 字段 15（`es+0x00A0`，六位）**
2. ⇒ 客户端**把它夹到 18** 并用它索引一个**19 项的表** —— `v310 = es+0xA0; if (v310 > 0x12) v310 = 0`
3. ⇒ 所以它**是一个表面种类**
4. ⇒ 而零售 dm demo **只在肉质命中上断言它，其它任何地方都没有**：
     · **204 次 `EV_BULLET_HIT_CLIENT_SMALL` 里 202 次是 6**
     · **90 次 LARGE 全部是 6**
     · **1419 次 `EV_BULLET_HIT` 里从未有一次**
5. ⇒ **它骑在 `unk00A0` 里**，而**这里每一个其它的事件实体验证器都把它钉到零**
6. ⇒ 而**不是放进一个新的结构成员** —— 因为**增大 `SvEntityState` 会移动那个地址键控的原生缓冲区**（§184h）
7. ⇒ **而 `WorldClientState` 是按它定尺寸的**
```

### 4.3 而**六个数字**

```text
0x12 = 18        夹紧上界
19 项            表的长度
204               SMALL 总数
202               SMALL 里是 6 的
90                LARGE 总数（全部是 6）
1419              EV_BULLET_HIT 总数（零次）
```

**✅ 算术：`204 - 202 = 2` 个例外。**

### 4.4 而"**骑在 `unk00A0` 里**"

**⇒ 三层**：

```text
1. 定义**记录**的字段存在，但
2. ⇒ **代码里用 `unk00A0` 这个既有成员**而不是新加一个
3. ⇒ 因为**加成员会移动地址键控缓冲区**
```

**✅ 与 §315 的"增大 `SvResolvedLoadout` 两次破坏死亡动画"、§318 的"§184h"同族**（第五次该约束）。

### 4.5 而 `EventEntityAttackerField = 13` vs `HitEntityField = 23`

```php
// ET_EVENTS field 13, entityState_s +0x88, 11 bits. Only the obituary
// uses it, and it is NOT EventEntityHitEntityField below -- that one is
// field 23 / +0x8C. re/demo-re/netfields-ol-named/entity-et23 names
// both, and the retail dm demo asserts 13 on every one of its 145
// obituary entities and 23 on every one of its bullet impacts.
constexpr std::uint32_t EventEntityAttackerField = 13;
```

**⇒ 四层**：

```text
1. 字段 13 是 `entityState_s +0x88`，11 位
2. ⇒ **只有 obituary 用它**，而它**不是** `HitEntityField`（那是字段 23 / `+0x8C`）
3. ⇒ demo **在它的 145 个 obituary 实体上每一个都断言 13** 而**在每一个子弹撞击上断言 23**
4. ⇒ 所以两个不同的字段两个不同的用途
```

**✅ 与 §146 的"`obituary (1700 + MOD)`"**相关。**

## 五、**`EntityEventParameterBits` 的 170 项**（本组第四重要）

### 5.1 那段

```php
// CODDIFF(1649370): dword_DA9410, 170 entries. The carried table was
// 3.3.3.3's dword_C56D70, 162 entries, and its VALUES differ as well as its
// length -- index 16 is 3 here and 10 there, 17/18 are 11/11 here and 10/0
// there. This is the only baseline-dependent width in the whole codec set
// (codec -94 inherits the id, and the id picks the width), so a wrong entry
// desynchronises the client's bit cursor for the rest of the snapshot rather
// than corrupting one field. Transcribed from the image and cross-checked by
// Tools/demo-re, which decodes 6160/6160 retail snapshots with it.
constexpr std::array<std::uint8_t, SvEntityEventCount>
    EntityEventParameterBits{
    11, 0, 6, 14, 14, 32, 32, 32, 32, 0, 14, 6, 2, 2, 2, 2,
    3, 11, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    ...
    0, 5, 5, 11, 11, 11, 0, 0, 0, 0,
};
```

### 5.2 六层

```text
1. **`dword_DA9410`，170 项**
2. ⇒ 携带的表是 3.3.3.3 的 `dword_C56D70`，**162 项**
3. ⇒ 而**它的值也不同于它的长度**：**索引 16 这里是 3 而那里是 10**，**17/18 这里是 11/11 而那里是 10/0**
4. ⇒ **这是整个 codec 集合里唯一 baseline 依赖的宽度**
5. ⇒ 因为 **codec `-94` 继承 id 而 id 选宽度**
6. ⇒ 所以**一个错的条目会失步客户端的位游标对快照的其余部分**
7. ⇒ **而不是损坏一个字段**
8. ⇒ 从映像转写并由 `Tools/demo-re` 交叉检查，它用这个解码 **6160/6160 个零售快照**
```

### 5.3 **"唯一 baseline 依赖的宽度"**

**⇒ 三层**：

```text
1. 大部分 codec 的宽度是**固定的**
2. ⇒ 而 **`-94` 的宽度来自那个 id 索引的表**
3. ⇒ 所以**它是唯一 baseline 依赖的**
```

**✅ 与 §313 的 `AgentStateFieldCodecs` 的 `-94`**同族。**

### 5.4 而那三个差异

```text
索引 16     本 build 3      3.3.3.3 10
索引 17     本 build 11     3.3.3.3 10
索引 18     本 build 11     3.3.3.3 0
```

**⇒ 所以 17/18 从 `10/0` 变成 `11/11`。**

**⚠ 一个**具体的三个差异**。**

### 5.5 而 `SvEntityEventCount = 170`

**⇒ 与记忆里"`SvEntityEventCount = 170` is the parameter-width table length, not an event-id bound (`0xFF` is the id bound)"**完全一致** ✓**

**✅ 三次确认。**

## 六、`validActorEntity` 的**十三项**（本组第五重要）

```php
bool validActorEntity(const SvEntityState &entity)
{
    const auto finiteVector = [](const auto &v) { return all_of(v, isfinite); };
    return entity.eType == EntityTypeActor &&
        entity.number >= FirstDynamicServerEntityNum &&
        finiteVector(entity.origin) && finiteVector(entity.angles) &&
        (entity.positionTrajectoryType == 1 || entity.positionTrajectoryType == 13) &&
        (entity.angleTrajectoryType == 1 || entity.angleTrajectoryType == 13) &&
        entity.angles[0] == 0.0f && entity.angles[2] == 0.0f &&
        entity.actorModelIndex > 0 && entity.actorModelIndex < ModelConfigStringCount &&
        entity.actorAgentSlot < SvAgentSlotCount &&
        (entity.actorField0058 & 0xFFu) == entity.actorAgentSlot &&
        entity.actorAttackerEntityNum <= 0x7FF &&
        entity.groundEntityNum <= 0x7FF &&
        entity.actorLoopSound <= 0x7FF &&
        entity.actorField00AC < (1u << 24) &&
        std::isfinite(entity.actorField0054) &&
        all_of(entity.events, validEntityEvent) &&
        entity.eventParm == 0 && entity.otherEntityNum == 0 &&
        entity.impactSurfaceType == 0 && entity.impactFlags == 0;
}
```

### 6.1 而**那段开头的原则**

```php
// EVERY BOUND HERE IS ONE THE RETAIL CAPTURES MEASURED, not a guess at what
// an actor "should" look like. 64 ET_ACTOR lives across five zm demos,
// re/demo-re/20-zm-actor-lifecycle.md section 1.
//
// An entity that fails this does not get dropped -- it rejects the WHOLE FRAME
// for EVERY client -- so the bounds are the measured WIDTHS, and anything this
// server cannot yet prove is left unconstrained rather than guessed narrow.
```

### 6.2 五层

```text
1. **这里的每一个界都是零售捕获【测量过的】**
2. ⇒ **不是对"一个 actor 应该看起来像什么"的猜测**
3. ⇒ **五个 zm demo 里 64 个 `ET_ACTOR` 生命**
4. ⇒ **一个失败于此的实体【不会被丢弃】—— 它【对所有客户端拒绝整个帧】**
5. ⇒ 所以**界是测量过的【宽度】**，而**这个服务器还不能证明的任何东西都【不约束】** 而不是**猜一个窄的**
```

### 6.3 **"一个失败于此的实体拒绝整个帧对所有客户端"**

**✅ 与 §318 的"乱序字段失步整个快照"同族（第十五次"一个错毁掉整帧"）。**

**⇒ 而**这解释了为什么界是**宽度**而不是**值域**。**

### 6.4 而两个 `== 1 || == 13` 的**trajectory type**

```php
// TWO MOVEMENT STATES AND NO OTHERS. Not one of the 64 lives ever
// carried a third value in either trajectory type.
(entity.positionTrajectoryType == 1 || entity.positionTrajectoryType == 13) &&
(entity.angleTrajectoryType == 1 || entity.angleTrajectoryType == 13)
```

**⇒ 三层**：

```text
1. **两个移动状态而没有第三个**
2. ⇒ **64 个生命里没有一个曾在任一轨迹类型上携带第三个值**
3. ⇒ 所以两个值的白名单
```

### 6.5 而**"pitch 与 roll 恒零"**

```php
// PITCH AND ROLL ARE ALWAYS ZERO. apos.trBase[0] and [2] assert six
// times across the whole spec capture and carry a single value: 0.
// A zombie that leans is this server inventing something.
entity.angles[0] == 0.0f && entity.angles[2] == 0.0f
```

**⇒ 三层**：

```text
1. **pitch 与 roll 【恒为零】**
2. ⇒ `apos.trBase[0]` 与 `[2]` 在整个 spec 捕获里**断言六次而携带单一值 0**
3. ⇒ **一个倾斜的僵尸是这个服务器在发明东西**
```

**✅ 与 §314 的"`currentAngles` 只有 yaw"**完全一致** ✓**

### 6.6 而 `actorModelIndex > 0` 的**拒绝零而不是默认**

```php
// THE APPEARANCE INDEX MUST BE PRESENT AND IN BAND. Ten bits, and
// the band is 1024 wide. Zero is refused rather than defaulted:
// index 0 is a model, not "no model", and a zombie shaped like
// whatever sits at 0 would hide the real fault -- that nothing
// resolved the name. zmspawnactor already refuses there too.
entity.actorModelIndex > 0 && entity.actorModelIndex < ModelConfigStringCount
```

**⇒ 四层**：

```text
1. **外观索引必须存在且在带内**（10 位而带 1024 宽）
2. ⇒ **零被拒绝而不是被默认**
3. ⇒ 因为**索引 0 是一个模型，不是"无模型"**
4. ⇒ 而**一个形状像 0 号那里任何东西的僵尸会掩盖真正的缺陷 —— 即没有东西解析了那个名字**
```

**✅ 与 §318 的"零意味着索引 0"**完全一致** ✓**

### 6.7 而"**两个必须命名同一个槽**"

```php
// THE TWO MUST NAME THE SAME SLOT (12.8.1).
(entity.actorField0058 & 0xFFu) == entity.actorAgentSlot
```

**⇒ 三层**：

```text
1. `actorField0058` 的低 8 位
2. ⇒ **必须等于 `actorAgentSlot`**
3. ⇒ 所以两个字段必须一致
```

**✅ 与 §319 的"`+0x058` 是打包的动画字"配合 —— 低 8 位是 agent slot。**

## 七、`sameActorPacketEntity` 的**四段因果**（本组第六重要）

### 7.1 那段

```php
// ONLY THE FIELDS OWNED BY ET_ACTOR'S ENTITY TABLE.
//
// SvEntityState also carries the actor's agent-list presentation state
// (actorAnimIndex/actorAnimStartTime and model attachments). Those values are
// serialized by writeClients, not writeChangedActor. Comparing the whole C++
// struct here made an attack-animation change look like a packet-entity delta;
// writeChangedActor then correctly found no ET_ACTOR entity field to write and
// rejected the entire snapshot. The live round-one failure was exactly that:
// all 25 actors reached the player, their attack commands changed, and snapshots
// stopped with failure=packet_entities.
bool sameActorPacketEntity(const SvEntityState &left, const SvEntityState &right)
{
    return left.eType == right.eType && left.origin == right.origin &&
        left.angles[1] == right.angles[1] && left.actorField00B4 == right.actorField00B4 && ...
}
```

### 7.2 七层

```text
1. **只比较 `ET_ACTOR` 的实体表所拥有的字段**
2. ⇒ `SvEntityState` 也携带 actor 的 **agent 列表表现状态**（`actorAnimIndex`/`actorAnimStartTime` 与模型附件）
3. ⇒ 那些值**由 `writeClients` 序列化，不是 `writeChangedActor`**
4. ⇒ **在这里比较整个 C++ 结构让一个攻击动画变化看起来像 packet-entity delta**
5. ⇒ 而 **`writeChangedActor` 然后正确地找到没有 ET_ACTOR 实体字段可写【并拒绝了整个快照】**
6. ⇒ **实机的第一轮失败正是那个**：
     · **全部 25 个 actor 到达玩家**
     · **它们的攻击命令变了**
     · **而快照以 `failure=packet_entities` 停止**
```

### 7.3 而"**全部 25 个 actor 到达玩家而命令变了而快照停了**"

**✅ 一个**极其具体**的失败链。**

**⇒ 与 §319 的"一个失败于此的实体拒绝整个帧"**同一个机制**。**

## 八、关键结论

1. **`ET_ACTOR` 表在 `0x00DA5DE8`，63 字段，eType 入口 19**；3.3.3.3 是 **61**。
2. **⭐ 写序必须递增** —— `writeSkippedFieldIndex` 严格向前，乱序**失步整个快照并带走 724 个 brush model**。
3. **⚠ 724 与 §302 的"完全不发布 brush model"矛盾** —— 需核对。
4. **四个事件槽（6..9）+ 第五候选（15 在 `+0x0B0`）从不被断言 ⇒ 不发**。
5. **三个未解释字段**（`+0x058` 打包动画字 / `+0x0AC` 24 位九值 / 事件 id）—— **必须发否则不绘制**，所以"全有或全无"。
6. **`EventEntityImpactSurfaceField = 15`**：六位，客户端夹到 18 索引 19 项表。
7. **`204 → 202`、`90 → 90`、`1419 → 0`** 三个断言计数。
8. **"骑在 `unk00A0` 里"** 而不是加结构成员 —— **第五次"不能增大地址键控缓冲区"**。
9. **`EventEntityAttackerField = 13`（obituary）与 `HitEntityField = 23`（撞击）** 两个不同字段。
10. **`EntityEventParameterBits` 170 项** vs 3.3.3.3 的 162 项，三个值不同（16/17/18）。
11. **"唯一 baseline 依赖的宽度"** —— codec `-94` 继承 id 而 id 选宽度。
12. **`validActorEntity` 的"界是测量的【宽度】不是值域"** —— 因为失败会**拒绝整个帧对所有客户端**。
13. **"两个移动状态而没有第三个"**（64 个生命从未有第三值）。
14. **"pitch 与 roll 恒零"** —— "一个倾斜的僵尸是这个服务器在发明东西"。
15. **`actorModelIndex > 0` 拒绝零** —— "索引 0 是一个模型"。
16. **`(actorField0058 & 0xFF) == actorAgentSlot`** —— 两个字段必须一致。
17. **`sameActorPacketEntity` 只比实体表字段** —— 否则**攻击动画变化会被当成 delta 并拒绝整个快照**。
18. **实机失败链**：25 个 actor 到达、命令变了、`failure=packet_entities`。

## 九、未闭合点

- 724 个 brush model vs §302 的"零发布"。
- `+0x0AC` 的九个值。
- 事件 id 的语义。
- `sv_snapshot_mp.cpp` 1400 行之后未读取。
