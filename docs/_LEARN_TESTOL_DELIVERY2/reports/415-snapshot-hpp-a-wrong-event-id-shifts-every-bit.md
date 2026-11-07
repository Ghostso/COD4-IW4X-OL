# 415 · **"一个错误的事件 id 不是一个错标签，它让客户端【之后每一位都错位】"** —— `sv_snapshot_mp.hpp` 的 `0x10` 旗标、eType 19/21 双写、以及 agent 默认行的七个字段

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 1–670 行（旗标、eType 表、僵尸 actor 常量、事件 id 表、语音参数）。

## 二、**`SnapshotUseEntityBaselinesFlag = 0x10`**（本组最重要的一段）

### 2.1 那段

```cpp
// 0x10 -- A NEW ENTITY RESOLVES AGAINST cl.entityBaselines[num], NOT A ZEROED STRUCT.
//
// This server has never set it, and that is why map geometry is invisible. Retail's static
// ET_SCRIPTMOVERs assert almost nothing on the wire -- measured in the 2021 factory demo,
// entity 43 carries ONE xModelIndex across 349 asserting frames and entity 104 one trBase[2]
// -- because origin, angles and model all come from the baseline the client builds at MAP
// LOAD. Without this bit every one of them is decoded from zeroes, so it has no model and
// renders nothing. re/demo-re/10-snapshot-format.md sec.2:
//
//     0x10 -> sub_470F20 @0x471300 calls sub_470E70(entityNumber, Dst):
//         v2 = dword_77CE488[num];
//         if (v2 > 0 && v2 < dword_7795824) qmemcpy(Dst, &unk_779E6E0 + 280*v2, 0x118);
//         else                              memset(Dst, 0, 0x118);
//
// THE FALLBACK IS WHY THIS IS SAFE TO SET UNCONDITIONALLY: an entity number the client has
// no baseline for still gets a zeroed struct, i.e. exactly today's behaviour.
```

### 2.2 二十层

```text
1. **`0x10` ⇒ 一个新实体【对 `cl.entityBaselines[num]` 解析**】，不是零化结构体**
2. ⇒ **这个服务器【从未设过它**】**
3. ⇒ **⇒ 而那正是【地图几何不可见**】的原因**
4. ⇒ **零售的静态 `ET_SCRIPTMOVER` 在线上【几乎什么都不断言**】**
5. ⇒ **（2021 factory demo 测量：实体 `43` 在 `349` 个断言帧里【只携带一个 `xModelIndex`**）**
6. ⇒ **（实体 `104` 只携带一个 `trBase[2]`）**
7. ⇒ **因为 `origin`、`angles` 与 `model` 【全部来自客户端在地图加载时构建的 baseline**】**
8. ⇒ **没有这一位 ⇒ 它们每一个【都从零解码**】**
9. ⇒ **⇒ 所以它【没有模型并渲染不出任何东西**】**
10. ⇒ **`sub_470F20` @ `0x471300` 调 `sub_470E70(entityNumber, Dst)`**：
      · **`v2 = dword_77CE488[num]`**
      · **`if (v2 > 0 && v2 < dword_7795824) qmemcpy(Dst, &unk_779E6E0 + 280*v2, 0x118)`**
      · **`else memset(Dst, 0, 0x118)`**
11. ⇒ **⇒ 那个回退就是【为什么它无条件可设是安全的**】**
12. ⇒ **一个客户端没有 baseline 的号【仍然得到一个零化结构体 = 今天的行为**】
```

### 2.3 ⭐⭐⭐ **"回退让旗标无条件安全；风险不在旗标而在编号"**

```cpp
// THE FALLBACK IS WHY THIS IS SAFE TO SET UNCONDITIONALLY: ... The risk is not
// the flag, it is the NUMBERING -- the client indexes by entity number, so an entity we place
// at a number the map also uses inherits that map entity's origin and model.
```

**⇒ 三层**：
```text
旗标 `0x10`：**无条件安全**（有回退：零化）
风险：**编号**（错号 ⇒ 继承别人的 origin/model）
⇒ **⇒ 所以【真正的保护是编号正确，不是旗标谨慎**】
```

**✅ 与 §414 的"entity 号就是身份"**完全闭合 ✓

**⇒ 三层**：
```text
§414  数据层：`<map>_const.ff` 就是编号
§415  协议层：`0x10` 只是"用在哪儿解析"，**风险在号**
⇒ **⇒ 两层同一件事**
```

**✅ ⭐⭐ **一个"数据与协议的分工"**。

**⚠ 而"`280*v2` 与 `0x118`"⇒ **`0x118 = 280`** ⇒ **一个 `entityState_t` 正好 `280` 字节**。**

**✅ 与 §414 的"280 字节记录数组"**完全闭合 ✓

**⇒ 三层**：
```text
`qmemcpy(Dst, &unk_779E6E0 + 280*v2, 0x118)`
`0x118 = 280` ⇒ **`entityState_t` 的大小**
⇒ **⇒ 所以【数组是连续的 `entityState_t`**】
```

**✅ ⭐ **一个"同一常量两处"的确认**。

### 2.4 而**"编号现在是定下来的，而它从来不可推导"**

```cpp
// THE NUMBERING IS NOW SETTLED, AND IT WAS NEVER DERIVABLE. `dword_779E6E0` is not built
// from the map -- the client fills it at map load from `<map>_const.ff`, an asset every map
// ships (`mp/constbaselines/bl_pc_<map>_<gametype>.bin`). That file IS the numbering:
// factory's carries 397 entries, entity 37..699, and its 238 brush models are exactly this
// server's 238 script_brushmodels.
```

**✅ 与 §414 二.1 的 `.hpp` 注释**几乎逐字相同 ⇒ **两处互相印证。**

**⇒ 三层**：
```text
`dword_779E6E0` ⇒ **数组成员基址**
`dword_77CE488` ⇒ **索引数组**（每号一个 `v2`）
⇒ **⇒ 两级间接：号 → 索引 → 记录**
```

**✅ ⭐⭐ **一个"两级间接"的精确结构**。**

**⚠ 而"为什么需要索引而不是直接 `280*num`"⇒ **因为记录是【压缩的/只存有意义的**】。**

**⇒ 三层**：
```text
若直接 `280*num` ⇒ **`1000` 个号 × `280` = `280KB` 常驻**
而用索引 ⇒ **只存表里有的 `397` 条**
⇒ **⇒ 所以索引是【稀疏数组的表示**】
```

**✅ ⭐ **一个"为什么用索引数组"的机制解释**（推断，需标注）。

### 2.5 而三个旗标与 `SnapshotSceneBlockFlags`

```cpp
constexpr std::uint8_t SnapshotServerCountFlag = 0x04;
constexpr std::uint8_t SnapshotBaselineFlag = 0x08;
constexpr std::uint8_t SnapshotSceneBlockFlags = 0x0A;
```

**⇒ 四层**：
```text
`0x04` ⇒ **服务器计数**
`0x08` ⇒ **baseline**（第一帧）
`0x0A` = `0x08 | 0x02` ⇒ **场景阻断**（`cgame` 丢弃这种帧）
`0x10` ⇒ **实体 baseline**（§二）
```

**✅ 而 §413 说 `SnapshotSceneBlockFlags (0x0A)` 与 `0x02` 配合**：

```cpp
// Costs nothing on the render side: cgame already discards frames whose flags meet
// SnapshotSceneBlockFlags (0x0A) and this frame carries 0x08 regardless.
```

**⇒ 四层**：
```text
`0x0A` = `0x08 | 0x02`
而"这一帧反正带 `0x08`" ⇒ **所以加 `0x02` 那个帧【本来就会被丢**】
⇒ **⇒ 所以 `0x02` 的入口旗标【在渲染上是免费的**】
```

**✅ ⭐⭐ **"在渲染上是免费的"** —— 一个**利用既有丢弃规则的巧思**。

**⇒ 三层**：
```text
`0x02` ⇒ **让客户端进 `cls.state 10`**
`0x0A` ⇒ **cgame 丢弃这种帧**
⇒ **⇒ 所以【状态推进了而画面不画**】
```

**✅ ⭐ **一个"纯状态、无副作用"的旗标用法**。

## 三、**`ps+0x10` 的共享位**（本组第二重要）

### 3.1 那段

```cpp
// ps+0x10's flags word is SHARED with the engine. BG_PlayerStateToEntityState tests
// (flags & 0x1800) to pick ET_PLAYER over ET_INVISIBLE, and those two bits are the
// only part of it this server owns -- the engine keeps stance and toggle state in the
// rest, and PmoveSingle tests bit 0x10000000 of it. Defined once, here: one number in
// more than one file has already cost this project a live bind() failure and an
// entire weapon catalogue (sec 43d).
constexpr std::uint32_t PlayerOtherFlagPlayer = 1u << 12;
constexpr std::uint32_t PlayerOtherFlagsServerOwnedMask = 0x1800u;
```

### 3.2 十四层

```text
1. **`ps+0x10` 的 flags 字与引擎【共享**】**
2. ⇒ **`BG_PlayerStateToEntityState` 测 `(flags & 0x1800)`**
3. ⇒ **用它选 `ET_PLAYER` 而不是 `ET_INVISIBLE`**
4. ⇒ **而【那两位是这个服务器唯一拥有的部分**】**
5. ⇒ **引擎在其余位里保存【姿态与开关状态**】**
6. ⇒ **而 `PmoveSingle` 测它的【`0x10000000`**】**
7. ⇒ **⇒ 所以【只有 `0x1800` 是本服务器可以动的**】
8. ⇒ **定义一次，在这里**：
9. ⇒ **理由**："一个数字在多于一个文件里【已经花掉了这个项目一次实机 `bind()` 失败与一整个武器目录**】"（第 43d 节）
```

### 3.3 ⭐⭐⭐ **"一个数字在多于一个文件里，已经花掉了一次 bind() 失败与一整个武器目录"**

**✅ 这是本报告里**最重要的一条"为什么定义一次"的论证**。**

**⇒ 三层**：
```text
意图：一个常量两处定义
后果：**一处改了另一处没改** ⇒ **`bind()` 失败** + **整个武器目录丢失**
⇒ **⇒ 所以【一个数字只在一个地方定义**】
```

**✅ 与 §414 的"两处注释互相推翻"**不同（那是**注释**，这是**常量**）。

**⇒ 三层**：
```text
§414  `+3` 的两段注释矛盾 ⇒ **后者对**
§415  同一常量两处定义 ⇒ **实机故障**
⇒ **⇒ 后者更危险**（注释不影响运行）
```

**✅ ⭐ **一个"重复的严重性分级"**。

### 3.4 而**`0x1800` 的两半**

```text
PlayerOtherFlagPlayer = 1u << 12 = 0x1000
PlayerOtherFlagsServerOwnedMask = 0x1800
⇒ 0x0800 也是服务器拥有的
```

**⇒ 四层**：
```text
`0x1000` ⇒ **`PlayerOtherFlagPlayer`**（选 `ET_PLAYER`）
`0x0800` ⇒ **另一个服务器拥有的位**（未命名）
两个合计 `0x1800`
⇒ **⇒ 所以掩码是【一个并集**】
```

**⚠ 而 `0x0800` 的具体语义**⇒ **未在此注释中命名。**

**✅ 而 §413 的 `SvPmFlagsMatchEndFrozen = 0x800`** 是**`pmFlags`**，不是**`otherFlags`** ⇒ **两个不同的字**。

**⇒ 三层**：
```text
`pmFlags`（`playerState+?`）  ⇒ `0x800` = `SvPmFlagsMatchEndFrozen`
`otherFlags`（`ps+0x10`）    ⇒ `0x0800` = 未命名
⇒ **⇒ 两个 `0x800` 在两个不同的字段里**
```

**⚠ 一个**极易混淆的点**。

## 四、**eType 19 vs 21 的双写**（本组第三重要）

### 4.1 那段

```cpp
// 21, AND IT IS WHAT RETAIL ACTUALLY PUBLISHES. Measured across the whole zm
// capture (12.30): ZERO eType-19 entities alive at any sampled time, while et21
// runs 3 -> 36 -> 56 -> 30 -> 16, and at t=26350 the live et21 entities are 723,
// 724, 725 -- exactly the numbers the client's agent array pairs with
// c_zom_garbageman_body_blue / _worker_ / _ger_. demoq labels 21 ET_ACTOR_CORPSE
// and they are plainly not corpses; the NUMBER is what is measured, not the name.
//
// IT IS NOT COSMETIC. sub_540860 switches on the eType and its `case 19: case 21:`
// arm ends with `if (a2 && v14 == 21) sub_530E70(Source)` -- so 21 gets a record
// initialiser that 19 never receives, filling the record from the ENTITY STATE
// (Source+332, Source+352) rather than from the agent element. Publishing 19 opts
// out of that path entirely.
```

### 4.2 二十层

```text
1. **`21` 是【零售实际发布的**】**
2. ⇒ **在整个 zm 捕获里测量**：**任何一个采样时刻【零个 `eType-19` 实体存活**】**
3. ⇒ **而 `et21` 跑 `3 → 36 → 56 → 30 → 16`**
4. ⇒ **而在 `t = 26350` 活的 `et21` 是 `723`/`724`/`725`**
5. ⇒ **⇒ 正是客户端 agent 数组与 `c_zom_garbageman_body_blue`/`_worker_`/`_ger_` 配对的那些号**
6. ⇒ **`demoq` 把 `21` 标为 `ET_ACTOR_CORPSE` 而它们【显然不是尸体**】**
7. ⇒ **⇒ 【被测量的是那个数字，不是那个名字**】**
8. ⇒ **而它【不是装饰性的**】**
9. ⇒ **`sub_540860` 在 eType 上 switch**
10. ⇒ **而它的 `case 19: case 21:` 分支以 `if (a2 && v14 == 21) sub_530E70(Source)` 结束**
11. ⇒ **⇒ 所以 `21` 得到一个【`19` 从不收到的记录初始化器**】**
12. ⇒ **它【从【实体状态】（`Source+332`、`Source+352`）填记录】而不是从 agent 元素**
13. ⇒ **⇒ 发布 `19` 【完全退出那条路径**】**
```

### 4.3 ⭐⭐⭐ **"被测量的是那个数字，不是那个名字"**

**✅ 这是本报告里**最重要的一条"命名可信度"纪律**。**

**⇒ 三层**：
```text
`demoq` 的名字：`ET_ACTOR_CORPSE` ⇒ **一个猜的名字**
实测：`723/724/725` 与 `c_zom_garbageman_body_blue` 配对 ⇒ **它们是活着的僵尸**
⇒ **⇒ 所以【用数字，不用名字**】
```

**✅ 与 §414 的"两段注释互相推翻"**同族（**第四次"两个来源冲突时选哪个"）。

**⇒ 三层**：
```text
§408  `out.exe` vs 线上 ⇒ **一致才信**
§414  `<map>_const.ff` vs demo ⇒ **demo 赢**
§415  `demoq` 名字 vs 实测数 ⇒ **实测数赢**
```
**✅ ⭐ **一个"可信度排序"的三例表**。

### 4.4 而**"18 字段写入器原样迁移"**

```cpp
// The 18-field writer transfers unchanged: the per-eType index -> offset map is
// IDENTICAL for 19 and 21 across every shared index (idx1 +0x040, idx2 +0x018,
// idx3 +0x01C, idx10 +0x08C, idx11 +0x058, idx14 +0x008, idx19 +0x00C, idx20
// +0x030 ...), so only the value and its allow-lists move.
```

**⇒ 五层**：
```text
1. **`19` 与 `21` 的【每 eType 索引 → 偏移映射**】在每一个共享索引上【相同**】**
2. ⇒ **`idx1 → +0x040`、`idx2 → +0x018`、`idx3 → +0x01C`**
3. ⇒ **`idx10 → +0x08C`、`idx11 → +0x058`、`idx14 → +0x008`**
4. ⇒ **`idx19 → +0x00C`、`idx20 → +0x030`**
5. ⇒ **⇒ 所以只有【值与它的白名单】移动**
```

**✅ 与 §360 的"eType 21 杀了客户端（索引→偏移相同但编解码器不同）"**——**这里给出了正面理由**。**

**⇒ 三层**：
```text
§360  观察：`21` 让客户端崩溃
§415  机制：**索引→偏移相同，但 `21` 多一个记录初始化器**
⇒ **⇒ 所以"相同偏移"不足以说明"相同行为**】
```

**✅ ⭐⭐⭐ **一个"半个相同导致误判"的精确解释**。

**⚠ 而"18 字段"⇒ 与 §414 的"`numFields` 恒 `63`"**不同（**`18` 是【writer 写的字段数**】）。**

**⇒ 三层**：
```text
表有 `63` 个字段
`writer` 写 `18` 个
⇒ **⇒ 所以【写的是一个子集**】
```

### 4.5 而**"两个号都是 actor"**

```cpp
// BOTH NUMBERS ARE AN ACTOR. sub_527A70 sends eTypes 19 AND 21 to sub_52FBE0, so
// the client draws either; the allow-lists must accept either or an actor is
// dropped before serialization (the 12.14 failure, three times over).
[[nodiscard]] constexpr bool isActorEType(const std::uint8_t eType)
{
    return eType == EntityTypeActor || eType == EntityTypeActorCorpse;
}
```

**⇒ 六层**：
```text
1. **`sub_527A70` 把 `19` 与 `21` 都发给 `sub_52FBE0`** ⇒ **两个都画**
2. ⇒ **所以白名单必须【接两个**】**
3. ⇒ **否则一个 actor 在【序列化之前就被丢弃**】**
4. ⇒ **（`12.14` 的失败，【三次**）**
5. ⇒ **⇒ 所以 `isActorEType` 是一个【显式的双值判定**】
```

**✅ 与 §410 的"三条白名单"**完全闭合 ✓

**⇒ 三层**：
```text
§410  **三条** eType 白名单（每实体两条 + 帧级一条）
§415  **两个** 号都必须被接受 ⇒ 否则在【序列化前】丢
⇒ **⇒ 所以【白名单的粒度是每站点**】
```

**⚠ 而"`12.14` 的失败，三次"⇒ **第九次"同一 bug 重复"**。**

**⇒ 三层**：
```text
§405  "同一坑第三次"
§409  "同一 bug 第三次"
§415  "三次**"
```

## 五、**agent 默认行的七个字段**（本组第四重要）

### 5.1 那段

```cpp
// THE CLIENT'S DEFAULT AGENT ROW, AND WHY EVERY FIELD BUT ONE WAS WRONG.
//
// A snapshot field is XORed against a baseline (writeUnsignedDelta writes
// `value ^ (baseline & mask)`), so the SERVER'S delta base must equal the
// CLIENT'S or the value decodes to something neither side chose.
//
// When an agent slot appears for the FIRST TIME the client does not start from
// zero. sub_471980 copies an 88-byte template and hands it to the field decoder
// as the baseline:
//     sub_769710(v26, &unk_DA9920, 88);
//     sub_670FF0(v5, a4, v26, v16, 24, &unk_DA63E8, 3);
// and unk_DA9920 (out.exe) reads
//     +0x004 = 345    +0x008 = 2    +0x00C = 1266    +0x010 = 0xFFFFFFFF
//     +0x014 = 1267   +0x018 = 1317 +0x028 = 3       +0x034 = 3    +0x040 = 1
//
// MEASURED CONSEQUENCE (12.27): this server sent modelIndex 310 against a ZERO
// base, so it transmitted 310; the client computed 310 ^ (1266 & 0x3FF) =
// 310 ^ 242 = 452 and stored 452 -- read live out of the client's agent array.
// The model never resolved, record+568 stayed empty and no DObj was built.
//
// THE CONTROL THAT PROVES IT: the team field already used SvTeam::Sc (2) as its
// base -- which is exactly +0x008 -- and that field, alone, landed correctly.
// The comment on it had found this for one field and never generalised it.
```

### 5.2 二十四层

```text
1. **一个快照字段【对一个 baseline 做 XOR**】**
2. ⇒ **（`writeUnsignedDelta` 写 `value ^ (baseline & mask)`）**
3. ⇒ **⇒ 所以【服务器的 delta 基必须等于客户端的**】**
4. ⇒ **否则那个值解码成【两边都没选的东西**】**
5. ⇒ **当一个 agent 槽【第一次出现】时，客户端【不是从零开始**】**
6. ⇒ **`sub_471980` 拷一个 `88` 字节模板并把它作为 baseline 交给字段解码器**
7. ⇒ **`unk_DA9920`（`out.exe`）读**：
      · **`+0x004 = 345`** ⇒ 实体号
      · **`+0x008 = 2`** ⇒ 队伍
      · **`+0x00C = 1266`** ⇒ 模型索引
      · **`+0x010 = 0xFFFFFFFF`**
      · **`+0x014 = 1267`** ⇒ 附件模型 0
      · **`+0x018 = 1317`** ⇒ 附件模型 1
      · **`+0x028 = 3`** ⇒ 附件 tag 1
      · **`+0x034 = 3`**
      · **`+0x040 = 1`**
8. ⇒ **测量后果（`12.27`）**：
      · **这个服务器对【零基】发 `modelIndex 310`** ⇒ **它传输 `310`**
      · **客户端算 `310 ^ (1266 & 0x3FF) = 310 ^ 242 = 452`**
      · **并【存 `452`**】—— **从客户端的 agent 数组实读**
      · ⇒ **模型从未解析，`record+568` 保持空，没有 DObj 被构建**
9. ⇒ **证明它的对照**：**队伍字段【已经】用 `SvTeam::Sc (2)` 作为基**
10. ⇒ **而那【正好是 `+0x008`**】**
11. ⇒ **而那个字段【唯独它**】落得正确**
12. ⇒ **它上面的注释【为一个字段发现了它而【从未一般化**】】**
```

### 5.3 ⭐⭐⭐ **"那个注释为一个字段发现了它，而从未一般化"**

**✅ 这是本报告里**最重要的一条"局部发现 vs 一般规律"的教训**。**

**⇒ 三层**：
```text
发现：队伍字段的基是 `2`
而 `2` 恰好是 `+0x008` 的值
⇒ **⇒ 所以【已经有人发现了"基来自 `unk_DA9920`"**】
而【只在那一处用了**】
```

**✅ 与 §412 的"同一个语义在遮挡门里写的是加，两处不一致"**同族（**第四次"局部正确全局错误"）。

**⇒ 三层**：
```text
§412  `chest[2] +=` 正确而 `dz = ... -` 错 ⇒ **一处对一处错**
§415  team 用对了基而 model 没用 ⇒ **一处对一处错**
```
**✅ ⭐ **同一个失败模式两次**。

**⚠ 而"`310 ^ 242 = 452`"⇒ 让我验证。**

**⇒ 计算**：
```text
310 = 0x136
1266 = 0x4F2; 1266 & 0x3FF = 0x0F2 = 242
0x136 ^ 0x0F2 = 0x1C4 = 452 ✓
```

**✅ **算术精确吻合**。

**✅ ⭐⭐ **一个"注释里的算术被独立复算命中"的实例**。

**⚠ 而"`& 0x3FF`"⇒ **`10` 位掩码**。**

**✅ 与 §414 的"`xmodelIndex` 是 `10` 位"**完全闭合 ✓

**⇒ 三层**：
```text
字段宽 `10` 位
mask = `0x3FF`
⇒ **⇒ 所以【`1266` 只能贡献低 10 位 = `242`**】
```

**✅ ⭐ **一个"位宽决定掩码"的实例**。

### 5.4 而**"88 字节模板与 24 个字段"**

```cpp
sub_769710(v26, &unk_DA9920, 88);
sub_670FF0(v5, a4, v26, v16, 24, &unk_DA63E8, 3);
```

**⇒ 五层**：
```text
1. **模板 `88` 字节**
2. ⇒ **而解码器参数是 `24` 个字段**
3. ⇒ **而字段表是 `&unk_DA63E8`**
4. ⇒ **`3` 可能是一个模式/版本**
5. ⇒ **⇒ 所以【`24` 个字段铺在 `88` 字节上**】（**平均 `3.67` 字节/字段**）
```

**✅ 与 §414 的"`63` 个字段的 `entityState`"**不同（**agent 是 `24`**）。

**⇒ 三层**：
```text
`entityState` ⇒ **`63` 字段 / `280` 字节**
`agent state` ⇒ **`24` 字段 / `88` 字节**
⇒ **⇒ 两个不同的记录族**
```

**✅ 而 §415 五 别处说"`18` 字段写入器"⇒ **writer 写 `18` 个，而解码器读 `24` 个**。**

**⇒ 三层**：
```text
解码器：`24` 个字段
writer：`18` 个
⇒ **⇒ 所以【`6` 个字段从不发送**】（保留在 baseline 里）
```

**✅ ⭐ **一个"更少发送，更多保留"的实例**。

### 5.5 而**`SvAgentDefault*` 五个常量的出处**

```cpp
constexpr std::uint32_t SvAgentDefaultEntityNumber = 345;   // +0x004, idx20
constexpr std::uint32_t SvAgentDefaultModelIndex = 1266;    // +0x00C, idx8
constexpr std::uint32_t SvAgentDefaultAttachModel0 = 1267;  // +0x014, idx13
constexpr std::uint32_t SvAgentDefaultAttachModel1 = 1317;  // +0x018, idx14
constexpr std::uint32_t SvAgentDefaultAttachTag1 = 3;       // +0x028, idx15
constexpr std::uint32_t SvAgentDefaultAttachTag0 = 0;       // +0x024, idx23
```

**⇒ 五层**：
```text
六个常量，各带【偏移 + netfield 索引**】
`+0x004` idx20 / `+0x008` idx2（**队伍，隐含**）/ `+0x00C` idx8
`+0x014` idx13 / `+0x018` idx14 / `+0x024` idx23 / `+0x028` idx15
⇒ **⇒ 所以【偏移与索引是两套编号**】
```

**✅ ⭐ **"偏移"与"netfield 索引"是两个不同的坐标**。**

**✅ 与 §414 的 `SvConstBaselineEntry` 的"netfield + 偏移"双列**完全同族（**第二次**）。

**⚠ 而"`SvAgentDefaultAttachTag0 = 0`"⇒ **注释说"从客户端实读"**。**

```cpp
// ATTACHMENT SLOT 0'S TAG. Read live off the client's default agent row:
// unk_DA9920 + 0x024 = 0, so 0 is the delta base for field 23.
```

**✅ ⭐ **"`0` 是一个【读出来的值**】，不是"没有值"**。**

**⇒ 三层**：
```text
朴素理解：`0` = 未设置 ⇒ **可以省略**
真相：`0` 是【客户端 baseline 里的 `0`**】⇒ **省略会让客户端算 `value ^ 0 = value`**
⇒ **⇒ 而【若我们的 base 也是 `0` 则等价…… 而这里是"客户端 base 是 `0`"**】
```

**✅ ⭐ **一个"零是一个具体的基"的实例**。

**⚠ 而"附件 tag 槽是【`6` 位】**"⇒ **`0..63`**。**

**⇒ 五层**：
```text
四个 10 位槽：idx13/14/16/18（`+0x014/018/01C/020`）⇒ **模型**
四个 6 位槽：idx23/15/17/19（`+0x024/028/02C/030`）⇒ **tag**
⇒ **⇒ 所以【八个附件槽，四模型四 tag，两两配对**】
```

**✅ ⭐ **一个"四对附件"的布局**。

## 六、**事件 id 表与"错位"**（本组第五重要）

### 6.1 那段

```cpp
// EVERY ONE OF THESE IS CHECKED AGAINST OL.exe's OWN NAME ARRAY (0xE5FD38, 185
// const char* slots, dumped to re/olfinal-events.tsv) AND AGAINST THE RETAIL dm
// DEMO. Two of them were wrong and both were 3.3.3.3-shaped guesses:
//
//   was 0x4A -> EV_SWITCH_OFFHAND     is 0x53 -> EV_BULLET_HIT
//   was 0x64 -> EV_GRENADE_LETGO      is 0x6F -> EV_PLAY_FX
//
// The demo settles it independently of the name array. Every event entity a real
// server sends carries eType = 23 + eventId, and across the whole 621-second dm
// match: eType 97 (0x4A) and 123 (0x64) NEVER OCCUR ONCE, while eType 106 (0x53)
// is the busiest event entity in the game at 474 lives and 1419 field
// assertions, and eType 134 (0x6F) has 54. `Tools/demo-re/demoq.py census`
// reproduces those counts.
//
// THE eventId ALSO PICKS THE PARAMETER WIDTH -- EntityEventParameterBits is
// indexed by it -- so a wrong id is not a mislabel, it desynchronises the
// client's bit cursor for the rest of the snapshot. Bullet hits were being sent
// 11 bits wide; the correct entry is 8. Checked the other way too: every event
// eType in the demo carries a parameter that FITS its image-table width.
```

### 6.2 二十四层

```text
1. **每一个都对照 `OL.exe` 自己的名字数组（`0xE5FD38`，`185` 个 `const char*` 槽）**
2. ⇒ **以及【对照零售 dm demo**】**
3. ⇒ **两个是错的，而两个都是【3.3.3.3 形状的猜测**】**
4. ⇒ **`0x4A`（`EV_SWITCH_OFFHAND`）⇒ `0x53`（`EV_BULLET_HIT`）**
5. ⇒ **`0x64`（`EV_GRENADE_LETGO`）⇒ `0x6F`（`EV_PLAY_FX`）**
6. ⇒ **demo 【独立于名字数组**】解决它**
7. ⇒ **一个真实服务器发出的每一个事件实体【携带 `eType = 23 + eventId`**】**
8. ⇒ **而在整个 `621` 秒的 dm 比赛里**：
      · **`eType 97`（`0x4A`）与 `123`（`0x64`）【一次都不出现**】
      · **`eType 106`（`0x53`）是【游戏里最忙的事件实体**】：`474` 条命、`1419` 次字段断言
      · **`eType 134`（`0x6F`）有 `54`**
9. ⇒ **`Tools/demo-re/demoq.py census` 复现那些计数**
10. ⇒ **⚠ 而 `eventId` 也【选参数宽度**】**
11. ⇒ **（`EntityEventParameterBits` 按它索引）**
12. ⇒ **⇒ 所以【一个错的 id 不是一个错标签，它让客户端【之后每一位都错位**】】**
13. ⇒ **子弹命中曾被发成 `11` 位宽而正确的条目是 `8`**
14. ⇒ **反方向也核对过：demo 里每一个事件 eType 【携带一个适合它镜像表宽度的参数**】**
```

### 6.3 ⭐⭐⭐ **"一个错的 id 不是一个错标签，它让客户端之后每一位都错位"**

**✅ 这是本报告里**最重要的一条协议脆弱性**。**

**⇒ 三层**：
```text
错标签 ⇒ **只影响这一个事件**
错宽度 ⇒ **整个快照之后的所有位都错位** ⇒ **整帧作废**
⇒ **⇒ 所以 `eventId` 是【一个双重身份**】
```

**✅ 与 §410 的"一个缺失的 eType 拒收整帧"**同族（**第三次"一个局部错误导致全局后果"）。

**⇒ 三层**：
```text
§409  "一个错误毁掉整段"（`sv_snapshot` 的见证概念）
§410  第三个白名单缺 eType ⇒ **拒收整帧**
§415  错 `eventId` ⇒ **位游标错位**
```
**✅ ⭐ **一个"帧级脆弱性"的三例表**。

### 6.4 而**"反方向也核对过"**

```php
// Checked the other way too: every event eType in the demo carries a parameter that
// FITS its image-table width.
```

**⇒ 四层**：
```text
正向：**我们的 id 表读出的宽度 ⊆ demo 的实测参数范围**
反向：**demo 里每个 eType 的参数【都装得进它的表宽**】
⇒ **⇒ 所以【两个方向都一致**】
```

**✅ ⭐⭐ **"双向核对"** —— 与 §409 的"`scoreBefore`/`scoreAfter` 两两互校"**同族（**第四次"双向验证"）。

**⇒ 三层**：
```text
§407  `24` 个 `N` vs `25` 个（出生假设）⇒ **配对计数排除**
§414  `288/397` -> `238/238` ⇒ **两条独立路径**
§415  **宽度双向核对**
```
**✅ ⭐ **一个"双向验证"的三例表**。

### 6.5 而事件的完整表

```text
EventSoundAlias          = 0x03  ⇒ ET_ENTITY 26
EventSoundAliasAsMaster  = 0x04  ⇒ 27
EventFireMagic           = 0x2C  ⇒ 67
EventMeleeHit            = 0x4B  ⇒ 98
EventBulletHit           = 0x53  ⇒ 106
EventBulletHitClientSmall= 0x56  ⇒ 109
EventPlayFx              = 0x6F  ⇒ 134
EventPlayFxOnTag         = 0x71  ⇒ 136
EventExploder            = 0x82  ⇒ 153
EventPhysicsExplosionSphere = 0x83 ⇒ 154
EventRadiusDamage        = 0x86  ⇒ 157
EventEarthquake          = 0x88  ⇒ 160
EventObituary            = 0x8F  ⇒ 166
EntityTypeEventBase      = 23
```

**⇒ 十三个事件 + 一个基址。**

**✅ 与 §407 的 "`RadiusDamage`(134→`0x004BC960`)/`Earthquake`(136)"**——**注意 §407 说的是"case 134"而这里是 `0x86 = 134 = EntityType`**。

**⇒ 三层**：
```text
§407  "`RadiusDamage`（case 134 → `0x004BC960`）" ⇒ **134 是 eType**
§415  `EventRadiusDamage = 0x86 = 134` ⇒ **eventId 是 `134 - 23 = 111 = 0x6F`？**
```

**⚠ 等等：`0x86 + 23 = 0x86 + 0x17 = 0x9D = 157`。**

**⇒ 所以 `EntityTypeRadiusDamage = 157`，而 §407 说的 `case 134` 是 `eventId`。**

**⇒ 三层**：
```text
`eventId`（`0x86 = 134`）⇒ **用于 `EntityEventParameterBits` 索引**
`eType`（`157`）⇒ **线上实体类型**
⇒ **⇒ 所以 §407 的 "case 134" 是【eventId**】
```

**✅ ⭐ **一个"两个编号"的澄清**。

**⇒ 而 `static_assert(EntityTypeRadiusDamage == 157)` ⇒ **编译期保证。**

**✅ ⭐ **一个"索引与类型必须一致"的静态断言**。

**⚠ 而"`EventExploder = 0x82 = 130`"⇒ **§407 的 "case 130 → 读取 configstring 11990"** —— **完全吻合** ✓

**⇒ 三层**：
```text
§407  "`IDA532910 case130` reads configstring11990+eventParm"
§415  `EventExploder = 0x82 = 130`
⇒ **⇒ 同一个 130**
```

**✅ ⭐⭐ **一个跨报告的精确闭合**。

### 6.6 而**"`SMALL` 每个命中都发，`LARGE` 一个都不发，故意的"**

```cpp
// SMALL IS SENT FOR EVERY HIT AND LARGE IS NOT SENT AT ALL, ON PURPOSE.
// Cases 86, 87 and 88 share one block in CG_EntityEvent and the block never
// reads the event id: it ends in
//     sub_59A5C0(localClient, es+0x84, es+0xD8, surface, tracerStart,
//                impactOrigin, es+0xE4)
// with the id nowhere among the arguments, so the three ids are the same
// behaviour and the effect is chosen from the WEAPON.
```

**⇒ 十层**：
```text
1. **`SMALL` 每个命中都发，而 `LARGE`【一个都不发，故意的**】**
2. ⇒ **case `86`/`87`/`88` 在 `CG_EntityEvent` 里【共享一个块**】**
3. ⇒ **而那个块【从不读 event id**】**
4. ⇒ **它以 `sub_59A5C0(localClient, es+0x84, es+0xD8, surface, tracerStart, impactOrigin, es+0xE4)` 结束**
5. ⇒ **而那个 id 【不在参数之中**】**
6. ⇒ **⇒ 所以【那三个 id 是同一行为**】**
7. ⇒ **而那个效果【由武器选择**】**
8. ⇒ **零售的划分【确实与武器相关**】（`1260/1287/1270` small，`1284/1297/1303` large）
9. ⇒ **⇒ 但决定它的那个 `WeaponDef` 字节【没有被识别**】**
10. ⇒ **而【发明一个规则会是在猜测一个没有可观察差异的契约**】
```

**✅ ⭐⭐⭐ **"发明一个规则会是在猜测一个没有可观察差异的契约"** —— 本报告里最重要的一条克制。**

**✅ 与 §412 的"`ADS` 位未取证 ⇒ 只清 `FIRE`"**完全同族（**第四次"不要发明"）。

**⇒ 三层**：
```text
未知：`WeaponDef` 的哪个字节决定 small/large
已知：**三个 id 的行为完全相同**（块不读 id）
⇒ **⇒ 所以【选哪个都行 ⇒ 不必知道那个字节**】
```

**✅ ⭐⭐ **"一个不可观察的差异不值得逆向"** —— 一个**成本-收益判断**。

**⚠ 而"`es+0x84` / `es+0xD8` / `es+0xE4`"⇒ **三个 `entityState` 偏移**。**

**✅ 与 §414 的"`+0x090` surfType"**不同（**`0x84` 是 surfType？**）。

**⇒ 需要核对**：`surfType` 在 §414 是 `+0x090`，而这里是 `+0x84` 与 `+0xE4`。

**⚠ 一处**偏移差异**（可能是不同的 `entityState` 变体或我的读法有误）。**

## 七、关键结论

1. **⭐⭐⭐ `0x10` 旗标**：新实体对 `cl.entityBaselines[num]` 解析而不是零化；`sub_470E70` 的 `v2 > 0` 守卫 + `else memset(Dst,0,0x118)` 回退 ⇒ **"客户端没有 baseline 的号仍得到零化结构体 = 今天的行为" ⇒ 旗标无条件安全，风险在编号**。
2. **⭐ `0x118 = 280 = sizeof(entityState_t)`**，与 §414 的"280 字节记录数组"闭合。
3. **两级间接**：号 → `dword_77CE488[num]` = `v2` → `unk_779E6E0 + 280*v2`。
4. **⭐⭐ "编号现在是定下来的，而它从来不可推导"** —— 与 §414 二.1 逐字同源，两处互相印证。
5. **⭐ `0x02` 在渲染上是免费的**：`SnapshotSceneBlockFlags = 0x0A = 0x08 | 0x02`，而入口帧反正带 `0x08` ⇒ **cgame 本来就会丢弃它**。
6. **⭐⭐⭐ "`ps+0x10` 的 flags 字与引擎共享：`BG_PlayerStateToEntityState` 测 `(flags & 0x1800)`，而那两位是服务器唯一拥有的部分；引擎在其余位保存姿态，`PmoveSingle` 测 `0x10000000`"** ⇒ **所以掩码是 `0x1800`**。
7. **⭐⭐ "一个数字在多于一个文件里已经花掉了这个项目一次实机 `bind()` 失败与一整个武器目录（第 43d 节）"** ⇒ **定义一次**。
8. **⚠ `0x0800` 在 `otherFlags`（`ps+0x10`）与 `pmFlags`（`0x800 = SvPmFlagsMatchEndFrozen`）两个不同字段里**，极易混淆。
9. **⭐⭐⭐ eType `21` 而不是 `19`**：**整个 zm 捕获里任何采样时刻零个 `eType-19` 存活，而 `et21` 跑 `3→36→56→30→16`**，`t=26350` 的 `723/724/725` 与 `c_zom_garbageman_body_blue`/`_worker_`/`_ger_` 配对。
10. **⭐⭐⭐ "`demoq` 把 `21` 标为 `ET_ACTOR_CORPSE` 而它们显然不是尸体；被测量的是那个数字，不是那个名字"`** —— 第四次"两个来源冲突时选哪个"。
11. **⭐⭐⭐ `21` 不是装饰性的**：`sub_540860` 的 `case 19: case 21:` 分支以 `if (a2 && v14 == 21) sub_530E70(Source)` 结束 ⇒ **`21` 得到一个记录初始化器而从【实体状态】填记录**，`19` 完全退出那条路径。
12. **⭐⭐ "索引→偏移映射在 `19` 与 `21` 上完全相同（`idx1 +0x040`/`idx2 +0x018`/`idx3 +0x01C`/`idx10 +0x08C`/`idx11 +0x058`/`idx14 +0x008`/`idx19 +0x00C`/`idx20 +0x030`），只有值与其白名单移动"`** ⇒ **半个相同导致"行为相同"的误判**，这正是 §360 "eType 21 杀了客户端"的机制解释。
13. **"两个号都是 actor：`sub_527A70` 把 `19` 与 `21` 都发给 `sub_52FBE0`，白名单必须接两个，否则 actor 在序列化前被丢弃（`12.14` 的失败，三次）"`** —— 第三次"同一 bug 三次"。
14. **⭐⭐⭐ agent 默认行的完整值**：`+0x004=345`、`+0x008=2`、`+0x00C=1266`、`+0x010=0xFFFFFFFF`、`+0x014=1267`、`+0x018=1317`、`+0x028=3`、`+0x034=3`、`+0x040=1`，来自 `unk_DA9920`（`88` 字节模板 + `24` 字段解码器）。
15. **⭐⭐⭐ "`12.27` 的本服务器对零基发 `310` ⇒ 客户端算 `310 ^ (1266 & 0x3FF) = 310 ^ 242 = 452` 并存 `452`；模型从未解析，`record+568` 保持空，没有 DObj 被构建"** —— 算术精确吻合（我复算：`0x136 ^ 0x0F2 = 0x1C4 = 452`）。
16. **⭐⭐ "证明它的对照：队伍字段已经用 `SvTeam::Sc (2)` 作基 —— 那正好是 `+0x008` —— 而那个字段唯独它落得正确；它上面的注释为一个字段发现了它而【从未一般化】"`** —— 与 §412 的"一处对一处错"同一模式。
17. **六字段附件布局**：四个 `10` 位槽（`+0x014/018/01C/020`）+ 四个 `6` 位 tag 槽（`+0x024/028/02C/030`）⇒ **四对附件**。
18. **⭐⭐⭐ "一个错的 `eventId` 不是一个错标签，它让客户端之后每一位都错位"**（因为 `EntityEventParameterBits` 按 id 索引 ⇒ 宽度）—— 第三次"帧级脆弱性"（§409/§410/§415）。
19. **⭐ 两个 3.3.3.3 形状的猜测被两边同时推翻**：`0x4A`⇒`0x53`、`0x64`⇒`0x6F`，而 **demo 独立于名字数组**（`eType 97`/`123` 一次都不出现，`106` 是最忙的事件实体 `474` 条命 `1419` 断言）。
20. **⭐⭐ "反方向也核对过：demo 里每一个事件 eType 携带一个适合它镜像表宽度的参数"`** —— 第四次"双向验证"。
21. **⭐⭐⭐ "`SMALL` 每个命中都发而 `LARGE` 一个都不发，故意的：case `86/87/88` 共享一个块而那个块【从不读 event id】，效果由武器选择；零售的划分确实与武器相关但决定它的那个 `WeaponDef` 字节没有被识别 ⇒ 发明一个规则会是在猜测一个没有可观察差异的契约"`** —— 第四次"不要发明"。
22. **⚠ 一处偏移差异**：`CG_EntityEvent` 的 case-86 块读 `es+0x84`/`es+0xD8`/`es+0xE4`，而 §414 的 `surfType` 在 `+0x090`。

## 八、未闭合点

- `0x0800` 在 `ps+0x10`（`otherFlags`）里的语义。
- `unk_DA9920` 的 `+0x010 = 0xFFFFFFFF` 是哪个字段。
- `SvAgentDefaultAttachTag1 = 3` 与 `Tag0 = 0` 为何不同（一个 `+0x024` 一个 `+0x028`）。
- `es+0x84` vs `+0x090` 的偏移差异。
- `WeaponDef` 里决定 small/large 的那个字节。
- `sv_snapshot_mp.hpp` 670 行之后未读取（**共 `4703` 行**）。
