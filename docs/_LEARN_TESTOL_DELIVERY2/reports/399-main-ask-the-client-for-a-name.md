# 399 · **"拿名字问客户端，而客户端只有服务器放进去的东西"** —— `79` 条 vs `22` 条、`cs 1413` 的 `typeByte=0xFF/0x04`、`XBOXLIVE_CANTJOINSESSION`

## 一、范围

本报告学习 `sv_main_mp.cpp` 3120–3450 行。

## 二、**音效别名表的完整事故**（本组最重要的一段）

### 2.1 那段

```php
// THE SERVER HANDS THE CLIENT ITS SOUND ALIAS TABLE, and nothing did
// this before, so `p <n>` named an empty slot and every UI sound was
// silent - the hit marker's included, which had been "wired" since the
// damage feedback work and never once made a noise. `grep -c "damage
// feedback sound alias=" is 0 across the whole runtime log.
//
// `p <n>` plays alias INDEX n, and alias n is configstring 3624+n, a
// table the SERVER owns. resolveSoundAliasEventParameters asks the
// CLIENT for a name, and a client only has what a server put there.
// Retail's client could resolve mp_hit_alert because retail's server
// had written it: its gamestate ships 79 alias entries spanning indices
// 9..3628 and its match hands out 45 more live. This server ships 22
// configstrings in total, none in that range.
//
// Assigned once per match and only after a client holds a gamestate:
// SV_SetConfigString stores the value for anyone who connects later AND
// pushes `d` to everyone already past it, so one call covers both.
```

### 2.2 十八层

```text
1. **服务器把手里的音效别名表【交给客户端】**
2. ⇒ **而没有东西做过这个**
3. ⇒ **所以 `p <n>` 命名一个【空的槽】而每一个 UI 音都是【静音的】**
4. ⇒ **包括那个命中标记**（它从伤害反馈工作起就"接好了"而【一次也没响过】）
5. ⇒ **`grep -c "damage feedback sound alias=" 在整个运行时日志里是 `0`**
6. ⇒ **`p <n>` 播别名【索引】 n**
7. ⇒ **而别名 n 是 `configstring 3624 + n`**
8. ⇒ **一个【服务器拥有】的表**
9. ⇒ **`resolveSoundAliasEventParameters` 【问客户端】要一个名字**
10. ⇒ **而一个客户端只有【服务器放进去的**东西**
11. ⇒ **零售的客户端能解析 `mp_hit_alert` 因为零售的服务器【写过它】**
12. ⇒ **它的 gamestate 携带 `79` 条别名条目，跨索引 `9..3628`**
13. ⇒ **而它的比赛【实时】再发 `45` 条**
14. ⇒ **这个服务器总共发布 `22` 个 configstring，【没有一个在那个范围里】**
15. ⇒ **一次每场比赛分配**
16. ⇒ **而只在【一个客户端持有一个 gamestate 之后】**
17. ⇒ **`SV_SetConfigString` 为任何【之后】连接的人存储那个值**
18. ⇒ **并推 `d` 给每一个【已经过了它】的人 ⇒ 所以一次调用覆盖两者**
```

### 2.3 ⭐⭐ **"拿名字问客户端，而客户端只有服务器放进去的东西"**

**✅ 这是本文件里**对"所有权"最清晰的一句**。**

**⇒ 三层**：

```text
`resolveSoundAliasEventParameters` 问客户端
⇒ **而客户端的表【就是服务器写的】**
⇒ **⇒ 所以"解析"实际上是一个【回读】**
```

**✅ 与 §391 的"不要覆盖原生菜单资产"**同族（**第三次"所有权"）。**

**⚠ 而"`79` 条 vs `22` 条"⇒ **一个 3.6 倍的缺口**。**

**✅ 与 §384 的 `73/163`**同族（**第四次"数量对照"）。**

### 2.4 而**"22 个 configstring，没有一个在那个范围里"**

**⇒ 三层**：

```text
零售：79（gamestate）+ 45（实时）= 124
我们：22（**全都不在 3624+ 范围**）
⇒ **⇒ 所以 `p <n>` 全部命名空槽**
```

**✅ ⭐ **一个"范围完全不重叠"的负面**。**

**⚠ 而"`grep -c ... is 0`"⇒ **一个可验证的负面**。**

**✅ 与 §340 的"定向的负面"**第八次。

### 2.5 而**"WAIT FOR EVERY CONNECTED CLIENT TO BE ACTIVE"**

```php
// WAIT FOR EVERY CONNECTED CLIENT TO BE ACTIVE. The first attempt
// required only that a gamestate had been SENT, which is true while the
// client is still loading the map - and a configstring write landing in
// that window is what killed the join. Active means the client is in
// the game and parsing snapshots, which is the earliest moment a `d` is
// safe.
//
// Requiring ALL of them, not any, also stops the write going out at
// clients=1 and leaving the second client to pick the value up from a
// gamestate built at a different instant.
if (soundAliasesAssigned_ || SV_PerfBaseline()) return;
const auto connected = count_if(slots, [](auto &s) { return s.state != Free; });
const auto active = count_if(slots, [](auto &s) { return s.state == Active; });
if (!connected || active != connected) return;
soundAliasesAssigned_ = true;
```

### 2.6 十四层

```text
1. **等每一个已连接客户端都 Active**
2. ⇒ **第一次尝试只要求"一个 gamestate 已【发送】"**
3. ⇒ **而那在客户端【还在加载地图】时为真**
4. ⇒ **而一个 configstring 写落在那个窗口【正是杀死加入的东西】**
5. ⇒ **`Active` 意味着客户端在游戏里并【解析快照】**
6. ⇒ **那是写 `d` 安全的最早时刻**
7. ⇒ **而要求【全部】而不是任何一个**
8. ⇒ **也阻止写在 `clients=1` 时发出**
9. ⇒ **而让第二个客户端从一个【在不同瞬间构建的】 gamestate 里取值**
10. ⇒ **所以 `active != connected ⇒ return`**
11. ⇒ **而 `soundAliasesAssigned_ = true` 在【循环之前】**
12. ⇒ **⇒ 而失败时【重置它】**（见下）
```

**✅ ⭐ **"一个 configstring 写落在那个窗口正是杀死加入的东西"** —— 与 §391 的"`publishActorModelConfigString` 的时机错"**完全同族**（**第三次"configstring 时机"）。**

**⚠ 而"要求全部而不是任何一个"⇒ **一个跨客户端的原子性**。**

**✅ 与 §393 的"会话密钥是比赛共享的"**同族。

### 2.7 而**"一次没到达任何人的写绝不能锁存"**

```php
// A WRITE THAT REACHED NOBODY MUST NOT LATCH. `soundAliasesAssigned_`
// is set before this loop, so a frame where every client had not yet
// passed its gamestate would burn the one and only attempt. Reset it
// and retry on the next frame instead.
if (!sent)
    soundAliasesAssigned_ = false;
else
    EngineBindings::NoteRegisteredSoundAlias(alias.name, (uint16)alias.index);
```

**⇒ 六层**：

```text
1. **一次没到达任何人的写绝不能锁存**
2. ⇒ **`soundAliasesAssigned_` 在循环【之前】被设**
3. ⇒ **所以一个"每个客户端都还没过它的 gamestate"的帧会【烧掉那唯一的一次尝试】**
4. ⇒ **重置它并在下一帧重试**
5. ⇒ **而成功 ⇒ `NoteRegisteredSoundAlias`**（**28800 的记忆**）
6. ⇒ **"所以宣告者解析器【绝不依赖】客户端侧的 CCS 链先被填充"**
```

**✅ ⭐ **"绝不依赖客户端的 CCS 链"** —— 一个**自己的记录**。**

**⇒ 三层**：

```text
解析器：问客户端（**会失败**）
而服务器：**自己记一份**（`NoteRegisteredSoundAlias`）
⇒ **⇒ 所以双保险**
```

**✅ 与 §371 的"两个所有者"**同族（**第五次"双份状态"）。**

## 三、**`cs 1413` 的 `typeByte` 完整事故**（本组第二重要）

### 3.1 那段

```php
// DM ONLY. THIS BAND KICKS ANY MODE WHOSE CCS ASSET ASSIGNS A
// DIFFERENT TYPE TO THE SAME NUMERIC SLOT.
//
// MEASURED 2026-09-05 by hooking the client's own configstring validator
// (sub_514540, which raises XBOXLIVE_CANTJOINSESSION as ERR_SERVERDISCONNECT):
//
//     CS VALIDATE index=2866/2867/3649..3652  typeByte=0xFF   accepted
//     CS VALIDATE index=1413                  typeByte=0x04   REJECTED -> kick
//
// The validator accepts a type byte of 0x15 or >= 0x17 and rejects everything
// else, reading it from the CCS block at `0x77D8250 + index`. Those types come
// from the CLIENT'S OWN loaded asset set, so what an index MEANS moves with the
// gametype -- the same lesson the model band taught. On dm, 1413 is the
// measured obituary format band and this is correct. On dmz AND zm it is
// type 0x04, and writing a localized-string name into it makes the client
// refuse the session about a second after it enters.
```

### 3.2 二十层

```text
1. **只 DM。这个带【踢掉】任何把不同类型分配到同一个数字槽的模式**
2. ⇒ **2026-09-05 通过【钩住客户端自己的 configstring 验证器】测量**
3. ⇒ **（`sub_514540`，它把 `XBOXLIVE_CANTJOINSESSION` 作为 `ERR_SERVERDISCONNECT` 抛出）**
4. ⇒ **`CS VALIDATE index=2866/2867/3649..3652 typeByte=0xFF` ⇒ 【接受】**
5. ⇒ **`CS VALIDATE index=1413 typeByte=0x04` ⇒ 【拒绝 ⇒ 踢】**
6. ⇒ **验证器接受 `0x15` 或 `>= 0x17` 的类型字节而【拒绝其它一切】**
7. ⇒ **从 `0x77D8250 + index` 的 CCS 块读它**
8. ⇒ **那些类型来自【客户端自己的已加载资产集】**
9. ⇒ **所以一个索引【意味着什么】随 gametype 移动**
10. ⇒ **同一个教训是模型带教的**
11. ⇒ **在 dm 上 `1413` 是测量的 obituary 格式带而这是【正确】的**
12. ⇒ **在 `dmz` 与 `zm` 上它是类型 `0x04`**
13. ⇒ **而把一个本地化字符串的名字写进它**
14. ⇒ **让客户端在它进入后【约一秒】拒绝那个会话**
```

### 3.3 ⭐⭐ **"`typeByte` 来自客户端自己的资产集"**

**✅ 这是本文件里**最深的 configstring 洞察**。**

**⇒ 三层**：

```text
configstring 的【索引】是协议
而它的【类型】来自**客户端加载的资产集**
⇒ **⇒ 同一个索引在不同 gametype 上是不同的东西**
```

**✅ 与 §345 的"客户端的基线 xmodel 不是文件的 xmodel"**同族（**第八次"两个 id 空间"）。**

**⚠ 而"`0x15` 或 `>= 0x17`"⇒ **一个具体的接受集**。**

**✅ 与 §346 的"`type == 0x15 || type >= 0x17`"**完全一致 ✓

**⇒ **第二次确认那个接受集。**

### 3.4 而**"约一秒后拒绝会话"**

**✅ 与 §391 的"`无法加入游戏会话`，复现两次"**完全同族（**第四次"`XBOXLIVE_CANTJOINSESSION`"）。**

**⚠ 而 §391 是 **`cs 2876`** 而这里是 **`cs 1413`**。**

**⇒ 三层**：

```text
§391  `cs 2876`（模型带）在会话中途 ⇒ **无法加入**
§399  `cs 1413`（obituary 带）在 zm/dmz ⇒ **一秒后拒绝**
⇒ **⇒ 两个不同的索引、同一个验证器、同一个症状**
```

**✅ **第五次"同一个症状不同索引"。**

### 3.5 而**`coop` 的第三次事故**

```php
// MEASURED 2026-09-09 ON WETWORK: the coop client reaches CA_ACTIVE, consumes
// the live configstring burst, then raises the same
// XBOXLIVE_CANTJOINSESSION error through that same validator and clears
// CA_ACTIVE to CA_DISCONNECTED at sub_5BF3E0+0x2DE. Retail's Wetwork join
// burst contains no 1413..1415 writes. These three names came exclusively
// from the DM capture, so sending them to coop was a cross-mode invention.
```

### 3.6 九层

```text
1. **2026-09-09 在 Wetwork 上测量**
2. ⇒ **coop 客户端【到达 `CA_ACTIVE`】**
3. ⇒ **消费那个实时的 configstring 突发**
4. ⇒ **然后通过【同一个验证器】抛出同一个 `XBOXLIVE_CANTJOINSESSION`**
5. ⇒ **并在 `sub_5BF3E0+0x2DE` 把 `CA_ACTIVE` 清成 `CA_DISCONNECTED`**
6. ⇒ **零售的 Wetwork 加入突发【不包含】 `1413..1415` 的写**
7. ⇒ **这三个名字【只】来自 DM 捕获**
8. ⇒ **所以把它们发给 coop 是【一个跨模式发明**】
```

**✅ ⭐ **"一个跨模式发明"** —— 一个**精确的措辞**。**

**⚠ 而"到达 `CA_ACTIVE` 然后被踢"⇒ **所以验证发生在进入【之后】。**

**✅ 与 §347 的"`CL_FirstSnapshot` 设 `cls.state = 10`"**配合（`CA_ACTIVE` 是 `cls.state` 的一个值）。

**⇒ 三层**：

```text
`CA_ACTIVE`（= cls.state 10？）
⇒ **然后验证 configstring**
⇒ **失败 ⇒ `CA_DISCONNECTED`**
```

**✅ **第二次确认那个握手。** 

### 3.7 而**"跳过而不是搬移"**

```php
// Skipped rather than relocated: where another mode keeps its obituary formats
// (if it has them) is not measured, and inventing an index is how this bug was
// created.
// The kill feed is cosmetic; being able to stay in the match is not.
```

**⇒ 五层**：

```text
1. **跳过而不是搬移**
2. ⇒ **另一个模式把它 的 obituary 格式放在哪里（如果它有）【没有被测量】**
3. ⇒ **而【发明一个索引】正是这个 bug 被创建的方式**
4. ⇒ **击杀信息栏是【装饰性的**】
5. ⇒ **而能留在比赛里【不是】** —— 一个明确的代价判断
```

**✅ ⭐ **"击杀信息栏是装饰性的，而能留在比赛里不是"** —— 一个**极清晰的取舍**。**

**✅ 与 §355 的"更好的是省略而不是错"**同族（**第二十二次）。**

## 四、**二十一 + 三条别名**（本组第三重要）

### 4.1 完整清单

```text
26    mp_hit_alert                  （SvHitAlertSoundAliasIndex）
27?   mp_hit_kill                   （SvKillSoundAliasIndex）
28?   mp_headshot                   （SvHeadshotSoundAliasIndex）
?     mp_last_stand                 （SvSplashSoundAliasIndex）
104   mp_hit_kill                   ← 刀BJ：空槽 60 → 后改 104
105   wpn_kill_tank_special         ← 刀BQ：空槽 62 → 刀CS 外移到 105
32    mp_killstreak_dogs
39    mp_killstreak_hellfire
46    mp_killstreak_mortar
53    mp_killstreak_radar
59    mp_killstreak_sentrygun
64    mp_killstreak_nuclearstrike
68    mp_killstreak_choppergunner
75    mp_killstreak_heli
106   ab_1mc_lead_taken_01
107   uk_1mc_lead_lost_01
108   uk_1mc_respawn_in_base_01
```

**⇒ 十七个（四个符号常量 + 十三个字面索引）。**

### 4.2 而**`104` 的完整来历**

```php
// ★★ 28100 刀BJ（goal 第 ③④ 项「击杀音」的单变量实验）——
//   实测：我方**一直在播**击杀音（日志 `sound alias 26 = mp_hit_kill -> cs 3650`，
//   demo 里 `p 26` 出现 106 次），但甲方听不到。
//   最可能原因：客户端 gamestate **自带 79 条别名**（我方代码注释记过），
//   我方写 cs 3650（alias 26）可能与该槽冲突/被覆盖。
//   ⇒ 在**零售从未用过的空槽 60** 再注册一次同一个名字，
//     击杀时改播 `p 60`：若 60 响而 26 不响 ⇒ 坐实"26 被占用"。
Alias{ 104, "mp_hit_kill" },
```

**⇒ 十一层**：

```text
1. **我方一直在播击杀音**（日志 `sound alias 26 = mp_hit_kill -> cs 3650`）
2. ⇒ **而 demo 里 `p 26` 出现 `106` 次**
3. ⇒ **但甲方【听不到】**
4. ⇒ **最可能原因：客户端 gamestate 自带 `79` 条别名**
5. ⇒ **我方写 `cs 3650`（alias 26）可能与该槽【冲突/被覆盖】**
6. ⇒ **所以在零售从未用过的【空槽 60】再注册一次同一个名字**
7. ⇒ **击杀时改播 `p 60`**
8. ⇒ **若 60 响而 26 不响 ⇒ 【坐实"26 被占用"】**
9. ⇒ **而实际写的是 `104`**（而不是 60）
```

**⚠ 而注释说"空槽 60"而代码是 `104`。**

**⇒ 三层**：

```text
注释：空槽 60
代码：**104**
⇒ **⇒ 一处注释滞后**
```

**✅ 与 §338 的"三条遗留注释"**同族（**第四次"注释滞后"）。**

**⚠ 而 `105` 的注释解释了一个**真实的搬移**：**

```php
// 刀CS：原 62(cs 3686) 与零售 "0.3" 冲突，外移到 105
```

**✅ ⭐ **"原 `62`（`cs 3686`）与零售 `"0.3"` 冲突，外移到 `105`"** —— 一个**精确的冲突记录**。**

**⇒ 三层**：

```text
槽 62 ⇒ `cs 3686`
⇒ **而零售在那里放 `"0.3"`**（**一个数字**而不是一个音效名）
⇒ **所以外移到 `105`**
```

**✅ 与 §398 的"名字带与值带在 +320"**不同（这是**一个槽的真实占用**）。

### 4.3 而**`106`/`107` 的"高带走不通"**

```php
// 这两条不能走高带 p：高带是客户端 ncs_snd 常量表（基址 512），
// 下标由 zone 装载顺序决定，本工程没有那张顺序表（解 zone 需要 out.exe 的 RSA 私钥）。
// ⇒ 走低带自注册：写 cs 3624+n 把名字塞进客户端别名表，再播 p n。
// 这与本文件上面 8 条连杀音用的是同一条已验证路径。
```

**⇒ 八层**：

```text
1. **这两条不能走【高带】 `p`**
2. ⇒ **高带是客户端 `ncs_snd` 常量表（基址 512）**
3. ⇒ **下标由【zone 装载顺序】决定**
4. ⇒ **而本工程没有那张顺序表**
5. ⇒ **（解 zone 需要 `out.exe` 的 RSA 私钥）**
6. ⇒ **所以走【低带自注册】**：写 `cs 3624+n` 把名字塞进客户端别名表，再播 `p n`
7. ⇒ **与上面 8 条连杀音【同一条已验证路径】**
```

**✅ ⭐ **"解 zone 需要 `out.exe` 的 RSA 私钥"** —— 一个**明确的不可行理由**。**

**⚠ 而"高带基址 512"⇒ 一个**第二套别名空间**。**

**⇒ 三层**：

```text
低带：`cs 3624 + n`（服务器写）
高带：**`ncs_snd` 常量表，基址 512**（zone 装载顺序）
⇒ **⇒ 两个别名空间**
```

**✅ **第九次"两个 id 空间"。**

**⚠ 而"RSA 私钥"⇒ 与记忆里的".ifs 载荷确认是加密不是压缩"**配合。**

### 4.4 而**"槽位占用"清单**

```php
// 槽位 106/107：现有占用 0/1/2/15/26/28/32/39/46/53/59/64/68/75/104/105。
```

**⇒ 三层**：

```text
1. **一个显式的占用清单**（十六个）
2. ⇒ **所以新槽必须不在里面**
3. ⇒ **一个手工维护的分配表**
```

**✅ 一个**脆弱的约定**（注释维护）。**

**⚠ 而"0/1/2/15"⇒ **四个未在代码里出现的占用**。**

**⇒ 所以**它们来自客户端 gamestate 或别处**。**

**✅ 与 §399 二.4 的"零售 `79` 条"**配合。

## 五、`registerHintString` 的**线性分配**

```cpp
std::size_t free = hintStrings_.size();
for (std::size_t slot = HintStringFirstServerSlot; slot < hintStrings_.size(); ++slot) {
    if (hintStrings_[slot] == text) return (uint16)slot;      // 已注册
    if (hintStrings_[slot].empty() && free == hintStrings_.size()) free = slot;
}
if (free == hintStrings_.size()) return std::nullopt;          // 满了
hintStrings_[free].assign(text);
const auto sent = clients_.SV_SetConfigString((uint16)(HintStringConfigStringBase + free), text);
```

### 5.1 七层

```text
1. **先查是否已注册**（文本相等 ⇒ 返回既有槽）
2. ⇒ **同时找第一个空的**
3. ⇒ **没空 ⇒ `nullopt`**
4. ⇒ **否则注册**
5. ⇒ **`HintStringConfigStringBase + free`**
6. ⇒ **而 `SV_SetConfigString` 覆盖后来者与已过者**
7. ⇒ **所以**去重 + 首次适配**
```

**✅ 与 §381 的"`registerLootItem` 的按号查找"**不同（这是**按内容去重**）。**

**⚠ 而"`HintStringFirstServerSlot`"⇒ **所以前几个槽是保留的**。**

**✅ 与 §381 的"提示字符串带 `+856`"**配合。

**⇒ 三层**：

```text
`HintStringConfigStringBase`  ⇒ 带基址（856？）
`HintStringFirstServerSlot`   ⇒ **服务器可用的第一个槽**
⇒ **所以前面几个是零售的**
```

## 六、**`driveCursorHints` 的"一个 cursorHint 写入者"**（本组第四重要）

### 6.1 那段

```php
// NO EARLY RETURN ON A MAP WITH NO TRIGGER TABLE ANY MORE. This used to bail
// out immediately when mapTriggers_ was null, which is every map but
// zm_factory_sh -- including mp_battlecity, where the loot lives. The trigger
// half is guarded individually below instead.
//
// ONE WRITER FOR cursorHint, and it has to be this function. Two drivers that
// each only act when THEIR answer changes will leave a stale prompt on screen
// the moment they disagree: loot stops offering, says nothing because it has
// nothing new to say, and the crate's prompt stays up.
```

### 6.2 十一层

```text
1. **在【没有触发器表】的地图上不再早退**
2. ⇒ **这过去在 `mapTriggers_` 为 null 时【立即退出】**
3. ⇒ **而那是【除了 `zm_factory_sh` 之外的每一张地图】**
4. ⇒ **包括 `mp_battlecity` —— 战利品所在的地方**
5. ⇒ **所以现在触发器那一半【在下面单独守卫】**
6. ⇒ **`cursorHint` 只有【一个】写入者**
7. ⇒ **而它【必须】是这个函数**
8. ⇒ **两个驱动各自只在【它们自己的答案】变化时行动**
9. ⇒ **会在它们【不同意】的那一刻在屏幕上留一个【陈旧的提示】**
10. ⇒ **战利品停止提供、什么也不说因为它没有新东西可说**
11. ⇒ **而箱子的提示【留在上面】**
```

### 6.3 ⭐⭐ **"两个驱动各自只在它们自己的答案变化时行动"**

**✅ 这是本文件里**对"多写入者"最清晰的一个反例**。**

**⇒ 三层**：

```text
驱动 A：战利品（无变化 ⇒ 不说话）
驱动 B：箱子（无变化 ⇒ 不说话）
⇒ **而观众看到的是 A 的旧值**
⇒ **⇒ 一个陈旧的 UI**
```

**✅ 与 §346 的"一个标签不能把两个答案塌缩成一个词"**同族（**第四次"多源一致性"）。**

**⚠ 而"单个写入者"⇒ **一个经典的 UI 状态解法**。**

**✅ 与 §391 的"One writer for cursorHint"**完全一致 ✓

**⇒ 第二次确认那个原则。**

### 6.4 而**"战利品停止提供、什么也不说"**

**✅ **一个极具体的症状描述**。**

**⇒ 三层**：

```text
玩家走开 ⇒ 战利品不再提供
⇒ **而驱动"没有新东西可说" ⇒ 什么也不写**
⇒ **⇒ 而 cursorHint 仍是箱子的那个**
```

**✅ 与 §344 的"`obituary ARCHIVED` 而屏幕上没有 feed"**同族（**第九次"正确的沉默产生错误的状态"）。**

## 七、`beginPrematchWindow` 的两阶段

```php
// 28800: two stages, one arithmetic. `_gamelogic.gsc:963-971` runs the
// "waiting" timer for prematchPeriod and then a second "match starting"
// timer for prematchPeriodEnd, while the first counter on screen covers
// the whole span -- that is the 12 -> 5 the operator measured, with the
// swap at t=6.
auto &life = uiClientLife_[clientNum];
life.prematchUntil = serverTime + ChaPrematchWaitMilliseconds + ChaPrematchStartMilliseconds;
life.prematchStageTwoAt = serverTime + ChaPrematchWaitMilliseconds;
```

### 7.1 九层

```text
1. **两个阶段，一个算术**
2. ⇒ **`_gamelogic.gsc:963-971` 跑一个 "waiting" 计时器 `prematchPeriod`**
3. ⇒ **然后一个第二 "match starting" 计时器 `prematchPeriodEnd`**
4. ⇒ **而屏幕上的第一个计数器【覆盖整个跨度】**
5. ⇒ **那就是操作员测到的 `12 → 5`**
6. ⇒ **而交换在 `t=6`**
7. ⇒ **所以 `prematchUntil = now + wait + start`**（**总跨度**）
8. ⇒ **而 `prematchStageTwoAt = now + wait`**（**阶段二**）
```

**✅ 与 §392 的"玩家的判决"**第十一次。**

**⚠ 而"`12 → 5` 而交换在 `t=6`"⇒ **一个极具体的观测**。**

**✅ 与 §391 的"`10:51`"**同族（**第三次"精确到秒的观测"）。**

### 7.2 而**"保持客户端的双手闭合"**

```php
// Keep the client's hands closed for the whole window. This is the
// command-level hold (buttons/moves zeroed, commandTime untouched);
// 28500 removed the pmFlags version because it deadlocked the client's
// own command time.
world_.setPlayerPrematchHold(clientNum, serverTime + wait + start);
```

**⇒ 五层**：

```text
1. **在整个窗口保持客户端的双手闭合**
2. ⇒ **这是【命令级】的保持**（buttons/moves 清零，`commandTime` 不动）
3. ⇒ **`28500` 移除了 `pmFlags` 版本**
4. ⇒ **因为它【死锁了客户端自己的命令时间】**
```

**✅ 与 §369 的"`pmFlags |= 0x800` 让客户端停止推进命令时间"**完全闭合 ✓

**⇒ **第三次确认那个事故。**

**⚠ 而"命令级保持"⇒ **§369 的"中性化命令而不是跳过 pmove"**。**

**✅ **完整闭合。**

### 7.3 而 **`d 2557 "mpIntro" 0`**

```php
// 2697 opens the phase on `mpIntro` (`_gamelogic.gsc:976`). Both names
// are configstring 2557 values; the map one is used at stage two.
clients_.queueReliableCommand(clientNum, "d 2557 \"mpIntro\" 0");
```

**⇒ 四层**：

```text
1. **`2697` 在 `mpIntro` 上打开那个相位**（`_gamelogic.gsc:976`）
2. ⇒ **两个名字都是 `configstring 2557` 的值**
3. ⇒ **而地图那个在【阶段二】用**
4. ⇒ **所以阶段一写 `"mpIntro"`**
```

**✅ 与 §399 二.4 的"configstring 表由服务器拥有"**完全闭合 ✓

**⚠ 而"`d 2557`"⇒ **一个 `d` 命令**（与 `s` 不同）。**

**⇒ 三层**：

```text
`s <dvar> "<value>"`  ⇒ 设 dvar
`d <cs> "<value>" <flags>` ⇒ **设 configstring**
⇒ **两个不同的命令**
```

**✅ 与 §398 的"`s battery_multiplier "1.2"`"**配合（**第二个 `d` 命令**）。

**⚠ 而"`0`"⇒ **一个 flags 参数**。**

**✅ 一处**未解释的第四参数**。

## 八、关键结论

1. **⭐⭐ "服务器把手里的音效别名表交给客户端，而没有东西做过这个 ⇒ `p <n>` 命名一个空槽而每一个 UI 音都是静音的"`** —— 而 **`grep -c "damage feedback sound alias=" 在整个运行时日志里是 `0`**。
2. **⭐⭐ "`resolveSoundAliasEventParameters` 问客户端要一个名字，而客户端【只有服务器放进去的东西】"`**。
3. **⭐ 数量对照：零售 `79`（gamestate）+ `45`（实时）vs 我们 `22` 个 configstring（没有一个在 `3624+`）`**。
4. **⭐⭐ "等每一个已连接客户端都 Active，因为一个 configstring 写落在【还在加载地图】的窗口正是杀死加入的东西"`** —— 第三次"configstring 时机"。
5. **"要求全部而不是任何一个，也阻止写在 `clients=1` 时发出而让第二个客户端从一个在不同瞬间构建的 gamestate 里取值"`**。
6. **⭐ "一次没到达任何人的写绝不能锁存：`soundAliasesAssigned_` 在循环之前被设，所以那一帧会烧掉唯一的一次尝试"`** —— 而成功后 `NoteRegisteredSoundAlias` ⇒ **"宣告者解析器绝不依赖客户端的 CCS 链"**（第五次"双份状态"）。
7. **⭐⭐ "`typeByte` 来自客户端自己的已加载资产集 ⇒ 所以一个索引【意味着什么】随 gametype 移动"`** —— 第八次"两个 id 空间"。
8. **`0x15` 或 `>= 0x17` 接受，其它一切拒绝**，从 `0x77D8250 + index` 读 —— **第二次确认那个接受集**。
9. **`sub_514540` 把 `XBOXLIVE_CANTJOINSESSION` 作为 `ERR_SERVERDISCONNECT` 抛出**。
10. **⭐ 三次 configstring 事故**：`cs 2876`（§391，会话中途）/ `cs 1413`（zm/dmz）/ `cs 1413..1415`（**coop/Wetwork**）。
11. **"零售的 Wetwork 加入突发不包含 `1413..1415` 的写 ⇒ 那三个名字只来自 DM 捕获 ⇒ 把它们发给 coop 是【一个跨模式发明】"`**。
12. **"coop 客户端到达 `CA_ACTIVE`、消费那个突发、然后在 `sub_5BF3E0+0x2DE` 把 `CA_ACTIVE` 清成 `CA_DISCONNECTED`"`**。
13. **⭐ "击杀信息栏是装饰性的，而能留在比赛里不是"`** —— 第二十二次"更好的是省略而不是错"。
14. **⭐ 十七 + 三条别名**，而 **`104` 的注释说"空槽 60"而代码是 `104`** —— 第四次"注释滞后"。
15. **⭐ "原 `62`（`cs 3686`）与零售 `"0.3"` 冲突，外移到 `105`"** —— 一个精确的冲突记录。
16. **⭐⭐ "这两条不能走高带 `p`：高带是客户端 `ncs_snd` 常量表（基址 512），下标由 zone 装载顺序决定，而本工程没有那张顺序表（解 zone 需要 `out.exe` 的 RSA 私钥）"`** —— 第九次"两个 id 空间"。
17. **"槽位 106/107：现有占用 0/1/2/15/26/28/32/39/46/53/59/64/68/75/104/105"`** —— 一个手工维护的分配表。
18. **`registerHintString` 的"去重 + 首次适配"**，而 **`HintStringFirstServerSlot` 保留前面几个槽**。
19. **⭐⭐ "`cursorHint` 只有一个写入者：两个驱动各自只在它们自己的答案变化时行动，会在它们不同意的那一刻在屏幕上留一个陈旧的提示"`** —— 第二次确认那个原则。
20. **"战利品停止提供、什么也不说因为它没有新东西可说，而箱子的提示留在上面"`** —— 第九次"正确的沉默产生错误的状态"。
21. **`beginPrematchWindow` 的两阶段**（`12 → 5` 而交换在 `t=6`）—— 第十一次"玩家的判决"。
22. **"在整个窗口保持客户端的双手闭合，这是【命令级】的保持；`28500` 移除了 `pmFlags` 版本因为它【死锁了客户端自己的命令时间】"`** —— 第三次确认 §369 的事故。

## 九、未闭合点

- `SvHitAlertSoundAliasIndex` 等四个符号常量的值。
- `SoundAliasConfigStringBase` 的确认（3624）。
- `ObituaryConfigStringBase` 的值。
- `HintStringConfigStringBase` 与 `HintStringFirstServerSlot` 的值。
- `ncs_snd` 常量表（基址 512）的完整内容。
- `d <cs> "<value>" <flags>` 的第四个参数语义。
- `sv_main_mp.cpp` 3450 行之后未读取。
