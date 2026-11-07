# 378 · **"`clientInfo` 是【按客户端】而不是【按生命】的 —— 用 `effectivePlaying` 门控它就是让一次死亡【崩掉客户端】"** —— `0xC0000005`、字段 36 的完整汉语定因、标签 28 的"唯一可解析且被接受"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 22800–23200 行。

## 二、**`clientInfo` 的按客户端门控**（本组最重要的一段）

### 2.1 那段

```php
// CLIENTINFO IS PER-CLIENT, NOT PER-LIFE, AND GATING IT ON `effectivePlaying`
// IS WHAT MAKES A DEATH CRASH THE CLIENT.
//
// This is the presentation record the client resolves through sub_53F5F0, whose
// caller sub_59CC70 writes v4[251] through the result WITHOUT a null check
// (HANDOFF 146c). Withholding it for a client that is connected but not currently
// Playing means the record disappears for the length of a death and returns at the
// respawn -- and anything resolving that player in the window gets null.
//
// MEASURED 2026-08-25, and it is what ruled the killcam out. With OLMOD_KILLCAM=0
// and the killcam provably suppressed in the same log, a client still died of
// 0xC0000005 at sub_59CC70 +0x1A5 on the respawn frame:
//     23:16:02 killcam SUPPRESSED client=1 -- OLMOD_KILLCAM=0
//     23:16:05 respawn client=1 via=timed msSinceDeath=3050
//     23:16:05.820 ClientException 0xc0000005  sub_59CC70 +0x1A5
// The same signature killed a REMOTE client on map load, where the other players'
// records had not arrived yet -- one cause, two symptoms.
//
// So the gate is now "do we know what this player looks like", not "are they
// alive". `state.characterCustomization` is still only updated from a valid
// source, and a client whose customization has never resolved still sends nothing:
// this widens WHEN a known record is sent, not WHAT counts as one.
```

### 2.2 二十层

```text
1. **`clientInfo` 是【按客户端】而不是【按生命】的**
2. ⇒ **而用 `effectivePlaying` 门控它【正是让一次死亡崩掉客户端】的东西**
3. ⇒ **这是客户端通过 `sub_53F5F0` 解析的表现记录**
4. ⇒ **而它的调用方 `sub_59CC70` 把 `v4[251]` 写穿那个结果【而没有 null 检查】**（HANDOFF 146c）
5. ⇒ **为一个已连接但【当前不在 Playing】的客户端扣留它**
6. ⇒ **意味着那条记录在一次死亡的时长里【消失】而在重生时回来**
7. ⇒ **而任何在那个窗口里解析那个玩家的东西【拿到 null】**
8. ⇒ **2026-08-25 测量，而它是【排除击杀回放】的那个证据**
9. ⇒ **`OLMOD_KILLCAM=0` 而击杀回放在同一日志里可证明被压制**
10. ⇒ **一个客户端【仍然】死在 `0xC0000005` 的 `sub_59CC70 +0x1A5`，在【重生帧】**
11. ⇒ **三段日志**：
     · `23:16:02 killcam SUPPRESSED client=1 -- OLMOD_KILLCAM=0`
     · `23:16:05 respawn client=1 via=timed msSinceDeath=3050`
     · `23:16:05.820 ClientException 0xc0000005 sub_59CC70 +0x1A5`
12. ⇒ **同一签名在【地图加载时】杀了一个【远端】客户端**
13. ⇒ **在那里其它玩家的记录【还没到】**
14. ⇒ **⇒ 一个原因，两个症状**
15. ⇒ **所以门控现在是"我们知道这个玩家长什么样吗"，不是"他们活着吗"**
16. ⇒ **`state.characterCustomization` 仍只从一个有效源更新**
17. ⇒ **而一个【从未解析过】自定义的客户端仍什么都不发**
18. ⇒ **这拓宽的是【何时】发一条已知记录，不是【什么算】一条**
```

### 2.3 ⭐⭐ **"一个原因，两个症状"**

**✅ 与 §377 的"两者只在重生之前读起来相同"**同族（**第三次"两个症状一个原因"）。**

**⇒ 三层**：

```text
症状 A：重生帧崩溃（`+0x1A5`）
症状 B：远端客户端在地图加载时崩溃
⇒ **两者都是"解析到一个 null 的 clientInfo"**
```

**✅ 与 §360 的"eType 21 杀死客户端"**同族（**第四次"客户端崩溃"）。**

**⚠ 而"三段日志"⇒ **一个完整的时序证据**。**

**✅ 与 §355 的"玩家的判决"**同族（**第八次）**。

### 2.4 而**"这拓宽的是【何时】发一条已知记录，不是【什么算】一条"**

**✅ 与 §345 的"一个从观测范围取的界拒绝第一个未观测值"**不同**。**

**⇒ 三层**：

```text
旧：`effectivePlaying` ⇒ **活着才发** ⇒ 死时缺
新：**有已知记录就发** ⇒ 死时也发
⇒ **而"什么算已知"不变**
```

**✅ 一个**精确的"只拓宽一半"**。**

**⚠ 而"已知"的定义没变 ⇒ **所以仍有一个缺口**（从未解析过的客户端）。**

**✅ 与 §371 的"空手是一个保持状态"**同族（**第四次"分层的保守性"）。**

## 三、**字段 36 的完整汉语定因**（本组第二重要）

### 3.1 那段（原文）

```cpp
// ★★★ 28100 刀I（六轮，单变量）：**client-info 字段 36 在多人模式里必须等于玩家队伍**。
//
// 这是"队友红名 / 小地图无队友标志 / 敌我不分"整条线的**唯一可写输入**，链条已由
// 既有 IDA 定因 + 老外研究文档双向闭合：
//   客户端的 `54BC8E/54BC90`（`54BC50` 处 `ebx` = 该行 +4）把 `[ebx]` 复制进
//   `characterInfo + 0x7C`；`clientInfo` 的 netfield 表是 `0xDA8078`（stride 12），
//   其中 **字段 36 = offset 4 / width 11 / type 0**（老外 `zm-scoreboard-accounting-20260923.md`
//   第 17-22 行逐字："The omitted field is client-info 36 … 54BC8E/54BC90 copy [ebx]
//   into characterInfo+7C … ZM now supplies 2 in this separate record; MP remains 0
//   and therefore emits no new field"）。
//   随后 `6B1010`（myTeam 写入函数，Hex-Rays）读**记分板行 +0x10**：
//       +0x10 == 0 ⇒ myTeam = -1（无效）；1 ⇒ myTeam = 2；2 ⇒ myTeam = 0。
//   即：**+0x7C = 0 ⇒ myTeam 无效 ⇒ 名字色 / 小地图 / UAV 全部不区分敌我**。
//
// 本行原来写 `zmActorNamespaceEnabled_ ? 2u : 0u` —— **只有 ZM 供 2，MP/cha 供 0**，
// 于是 cha 的每一行都落在 myTeam = -1。这同时解释了甲方"老外僵尸模式有正确队伍表现"：
// 老外也只给 ZM 供 2，ZM 里所有人同队 ⇒ myTeam 有效 ⇒ 表现正常；cha 是两队 ⇒ 表现为全错。
//
// 修法：**多人模式里按玩家队伍填**（SvTeam{None=0,Tf=1,Sc=2} ⇒ 有效行值为 1/2，
// 正是客户端 `6B27C5` 接纳的行域）。ZM 分支保持原样（合作模式单一 survivor 侧 = 2）。
clientInfoState.zombieScoreboardTeam = zmActorNamespaceEnabled_
    ? 2u
    : static_cast<std::uint32_t>(client.team);
```

### 3.2 十六层（结构）

```text
1. **`client-info` 字段 36 在多人模式里必须等于玩家队伍**
2. ⇒ **这是"队友红名 / 小地图无队友标志 / 敌我不分"整条线的【唯一可写输入】**
3. ⇒ **链条已由【既有 IDA 定因】+【老外研究文档】双向闭合**
4. ⇒ **客户端 `54BC8E/54BC90`（`54BC50` 处 `ebx` = 该行 +4）把 `[ebx]` 复制进 `characterInfo + 0x7C`**
5. ⇒ **`clientInfo` 的 netfield 表是 `0xDA8078`（**stride 12**）**
6. ⇒ **其中【字段 36 = offset 4 / width 11 / type 0】**
7. ⇒ **（老外 `zm-scoreboard-accounting-20260923.md` 第 17-22 行逐字）**
8. ⇒ **随后 `6B1010`（myTeam 写入函数，Hex-Rays）读记分板行 `+0x10`**：
     · **`+0x10 == 0` ⇒ `myTeam = -1`**（无效）
     · **`1` ⇒ `myTeam = 2`**
     · **`2` ⇒ `myTeam = 0`**
9. ⇒ **即：`+0x7C = 0` ⇒ `myTeam` 无效 ⇒ 名字色/小地图/UAV 全部不区分敌我**
10. ⇒ **本行原来写 `zmActorNamespaceEnabled_ ? 2u : 0u`**
11. ⇒ **只有 ZM 供 `2`，MP/cha 供 `0`**
12. ⇒ **于是 cha 的每一行都落在 `myTeam = -1`**
13. ⇒ **这同时解释了"老外僵尸模式有正确队伍表现"**：
     · **老外也只给 ZM 供 2**
     · **ZM 里所有人同队 ⇒ `myTeam` 有效 ⇒ 表现正常**
     · **cha 是两队 ⇒ 表现为全错**
14. ⇒ **修法：多人模式里按玩家队伍填**
15. ⇒ **（`SvTeam{None=0,Tf=1,Sc=2}` ⇒ 有效行值为 1/2，正是客户端 `6B27C5` 接纳的行域）**
16. ⇒ **ZM 分支保持原样（合作模式单一 survivor 侧 = 2）**
```

### 3.3 ⭐⭐ 一个完整的、可验证的定因链

**⇒ 五个环节**：

```text
① 服务端写 clientInfo 字段 36（offset 4, width 11, type 0）
② 客户端 54BC8E/54BC90 把 [ebx] 复制进 characterInfo + 0x7C
③ 6B1010 读记分板行 +0x10
④ 三值映射：0⇒-1 / 1⇒2 / 2⇒0
⑤ 6B27C5 只接纳 1/2
```

**✅ 与本文件的其他定因**不同的地方：**

**⇒ 有【外部文档逐字引用】**（`zm-scoreboard-accounting-20260923.md` 第 17-22 行）。

**✅ 与 §351 的"238 个间隔方程"**同族（**第二次"交叉验证"）。**

**⚠ 而"唯一可写输入"⇒ **一个强断言**（其它路径都不行）。**

**✅ 与 §370 的"原生 pmove 的两条换武器路径都不可达"**同族（**第三次"排除所有其它路径"）。**

### 3.4 而**`0xDA8078` 与 stride 12**

**✅ 与 §339 的"`0x00DA8078` 87 项"**完全一致 ✓

**⇒ 第三次确认那张表。**

**⚠ 而"stride 12"⇒ **每项 12 字节**（offset 4 + width 1 + type 1 + 6 填充？较合理）。**

**✅ 与 §341 的"字段 20 = offset +0x7C 16 位"**配合（那里是 `+0x7C` 而这里是字段 36 的 offset 4）。

**⚠ 所以**字段 20 与字段 36 都与 `+0x7C` 有关**？**

**⇒ 可能一个是 clientState 的偏移、一个是 clientInfo 的 offset。**

**✅ 一个**需要小心的区分**。

### 3.5 而**三值映射的"我的队伍是别人"**

```text
记分板行 +0x10 == 0  ⇒ myTeam = -1
                   1  ⇒ myTeam = 2
                   2  ⇒ myTeam = 0
```

**⚠ 所以**1 与 2 交换了**。**

**⇒ 三层**：

```text
服务端写 1 ⇒ 客户端 myTeam = 2
⇒ 服务端写 2 ⇒ 客户端 myTeam = 0
```

**✅ 一个**奇偶交换**（可能因为客户端 0 基而服务端 1 基）。**

**⚠ 而注释没解释这个交换的原因。**

**✅ 一处**可补充的地方**。**

## 四、**标签 28 的"唯一可解析且被接受"**（本组第三重要）

### 4.1 那段

```php
// A NON-ZERO MODEL NEEDS A TAG, AND THIS IS THE ONLY TAG WE CAN NAME.
//
// The models now reach the client and resolve (measured: 416 -> cs
// 2984 -> fpa_raider_sc_m), the tags go out ZERO, and nothing draws.
// Retail's players carry tags 13..63 in these same slots, so zero is
// the one thing still different from a working wire.
//
// 28 is the ONLY index with a configstring set in any of the 62
// retail demos -- 5896+28 = cs 5924 = tag_stowed_back -- and it is
// also one of the two tag ids BG_UpdatePlayerDObj 0x0040AB30 tests
// for. So it is the single value that is both RESOLVABLE and
// ACCEPTED, which makes it the right probe even though a jacket does
// not belong on the back.
```

### 4.2 十五层

```text
1. **一个非零模型需要一个标签，而这是【我们唯一能命名的】标签**
2. ⇒ **模型现在到达客户端并解析**（测得：`416 → cs 2984 → fpa_raider_sc_m`）
3. ⇒ **标签发【零】而什么都不画**
4. ⇒ **零售玩家在同样的槽里携带标签 `13..63`**
5. ⇒ **所以零是仍然不同的【那一样】**（与一条工作的线比）
6. ⇒ **`28` 是【任何】62 个零售 demo 里【唯一有 configstring 集】的索引**
7. ⇒ **`5896 + 28 = cs 5924 = tag_stowed_back`**
8. ⇒ **而它也是 `BG_UpdatePlayerDObj 0x0040AB30` 测试的两个 tag id 之一**
9. ⇒ **所以它是【既可解析又被接受】的唯一值**
10. ⇒ **这使它成为正确的探针**
11. ⇒ **即使一件夹克【不属于】背部**
12. ⇒ **两种结果都有用**：
     · **部件出现（即使位置错）⇒ 标签检查是真的，任务是找到身体部件想要的标签**
     · **仍然什么都没有 ⇒ 标签【不是】阻塞点，故障在下游；去 §181m 的 12 个内嵌字段**
```

**✅ 与 §370 的"阳性对照"**同族（**第三次"探针设计"）。**

**⚠ 而"两种结果都有用"⇒ **一个预先声明的判决树**。**

**✅ 与 §346 的"三层命名失败项"**同族（**第六次）。**

### 4.3 而 **`5896 + 28`**

**✅ 与 §310 的"标签块在 5896"、§338 的"`add esi, 1708h = 5896`"**完全一致 ✓

**⇒ **第五次确认 5896。**

**⚠ 而"`cs 5924 = tag_stowed_back`"⇒ **一个具体的 configstring 名**。**

**✅ 与 §340 的"槽 0 是收纳武器（tag 28）"**完全闭合 ✓

**⇒ **第二次确认 tag 28 = 收纳背部。**

### 4.4 而 **`OLMOD_OUTFIT_TAG`**

```cpp
static const std::uint16_t OutfitTag = [] {
    const char *value = std::getenv("OLMOD_OUTFIT_TAG");
    return value ? (uint16_t)std::atoi(value) : (uint16_t)28;
}();
```

**⇒ 三层**：

```text
1. **默认 28**
2. ⇒ **可用环境变量覆盖**
3. ⇒ **所以"下一个候选值花一次重启而不是一次重编"**
```

**✅ 与 §352 的"`OLMOD_DMZ_PICKUP_EVENT` 是一个旋钮"**同族（**第七次环境变量旋钮）。**

## 五、**`clientinfo record` 的十二个字段**

### 5.1 那段

```php
// WHAT WENT INTO THE TWELVE RECORD FIELDS, AND WHAT THE CHARACTER IS.
//
// The record now reaches the client and outfit pieces RENDER (section 181m,
// player-confirmed) -- but they are the WRONG pieces, so this is an ordering
// or content question and it needs the actual array, not a theory about it.
// The document read on the other side shows index=6 slots=2056,10263,11815,
// 14661,10262,2052 and index=4 slots=686,2137,18481,1382,1993,2070,2073;
// if what goes out here does not line up with those, the placer or the copy
// is the fault.
//
// NOTE entry 0 is the CHARACTER ITEM ITSELF and word(3) of the resolver
// request already carries it, so the client may expect the twelve
// overrides to EXCLUDE it -- an off-by-one that would render a shifted,
// wrong-but-plausible outfit, which is exactly the symptom.
```

### 5.2 十二层

```text
1. **什么进入了那十二个记录字段，以及那个角色是什么**
2. ⇒ **记录现在到达客户端而部件【渲染了】**（§181m，玩家确认）
3. ⇒ **但它们是【错的部件】**
4. ⇒ **所以这是一个排序或内容问题，而它需要【实际的数组】而不是一个理论**
5. ⇒ **另一侧读取的文档显示**：
     · `index=6 slots=2056,10263,11815,14661,10262,2052`
     · `index=4 slots=686,2137,18481,1382,1993,2070,2073`
6. ⇒ **若这里出去的东西不与那些对齐，放置器或拷贝是错的**
7. ⇒ **注意条目 0 是【角色物品本身】**
8. ⇒ **而【解析器请求的 word(3)】已经携带它**
9. ⇒ **所以客户端可能期望那十二个覆盖【排除它】**
10. ⇒ **一个 off-by-one 会渲染一个【移位、错但看似合理】的装扮**
11. ⇒ **那【正是】那个症状**
```

### 5.3 ⭐ **"移位、错但看似合理"**

**✅ 与 §351 的"控制台成了僵尸身体"**同族（**第九次具体视觉症状）。**

**⇒ 三层**：

```text
1. off-by-one ⇒ **每一个部件移位一格**
2. ⇒ **所以是"一个真实存在的装扮但属于别的槽"**
3. ⇒ **⇒ 错但看似合理**
```

**✅ **一个极精确的失败分类**（不是"不画"而是"画错"）。**

**⚠ 而"word(3)"⇒ **一个具体的字索引**。**

**✅ 与 §351 的"`word(3)` of the resolver request"**配合。

### 5.4 而 `mask-selects`

```cpp
line += " mask-selects=";
std::size_t bits = 0;
for (word = 0; word < clientInfoState.characterOptionMask.size(); ++word) {
    const auto value = clientInfoState.characterOptionMask[word];
    for (bit = 0; bit != 32; ++bit) {
        if (!(value & (1u << bit))) continue;
        line += (bits++ ? "," : "") + std::to_string(word * 32 + bit);
    }
}
if (!bits) line += "none (the character's own defaults)";
```

**⇒ 六层**：

```text
1. **打印【选项索引】而不是十六进制位模式**
2. ⇒ **因为"十六进制位模式在那些 id 旁边不可读"**
3. ⇒ **而问题总是"哪些选项"**
4. ⇒ **所以 `word * 32 + bit` 展开成索引**
5. ⇒ **零位 ⇒ `none (the character's own defaults)`**
6. ⇒ **一个"零也命名"的细节**
```

**✅ 与 §338 的"`abilities.mask` 六个 word"**同族（**第二次"位集展开成索引"）。**

**⚠ 而 `clientInfoState.characterOptionMask` 与 `abilities.mask`**不同**（§341）。**

**✅ 所以**两个位集**：**

```text
`characterOptionMask`   装扮选项
`abilities.mask`        技能（§341 的字段 2..7）
```

**✅ **第三次确认那个分离。**

### 5.5 而**"每个客户端保留一个先前值"**

```cpp
// Keep one prior value per client. A single shared string
// alternates between client 0 and client 1 every snapshot,
// defeating the dedupe and stalling the server console.
static std::array<std::string, MaximumGameClients> reported;
```

**⇒ 五层**：

```text
1. **按客户端保留一个先前值**
2. ⇒ **因为一个单一的共享字符串会在客户端 0 与 1 之间【每一快照交替】**
3. ⇒ **⇒ 使去重失效**
4. ⇒ **⇒ 并【卡住服务器控制台】**
5. ⇒ **所以必须按客户端**
```

**✅ 与 §372 的"一个服务端级的 `static` 在多客户端时退化成每条 usercmd"**完全同族（**第六次 static 跨客户端问题）。**

**⇒ **而这次作者【明确修了】。**

**✅ 一个**已修复的实例**（对比 §346/§368/§372 的未修）。

## 六、**两条实体装配路径**（本组第四重要）

### 6.1 那段

```php
if (!zmActorNamespaceEnabled_) {
    // Exact pre-zombie-merge multiplayer entity assembly. Static
    // const-baseline rows remain present and a live entity replaces its
    // row by number. Appending the rewritten rows instead changed the DM
    // packet entity set after 8584acf.
    candidateSnapshot.entities.insert(..., staticBaselineEntities_.begin(), staticBaselineEntities_.end());
    const auto publishEntity = [&candidateSnapshot](const SvEntityState &state) {
        const auto existing = std::ranges::find(candidateSnapshot.entities, state.number, &SvEntityState::number);
        if (existing != candidateSnapshot.entities.end()) { *existing = state; return; }
        candidateSnapshot.entities.push_back(state);
    };
    ...
} else {
    for (const auto &[entityNum, entity] : entities_) { ... candidateSnapshot.entities.push_back(candidate.networkState); }
    ...
}
```

### 6.2 七层

```text
1. **非 ZM ⇒ 【精确的 pre-zombie-merge 多人实体装配】**
2. ⇒ **静态 const 基线行【保持存在】**
3. ⇒ **而一个活实体【按号替换它那一行】**
4. ⇒ **改为追加重写的行在 `8584acf` 之后改变了 DM 包实体集**
5. ⇒ 所以 `publishEntity`：**找到同号则替换，否则追加**
6. ⇒ **ZM ⇒ 直接 push**
```

**✅ 与 §337 的"与 `8584acf` 逐字节兼容"**完全一致 ✓

**⇒ **第二次确认那个 commit 基准。**

**⚠ 而"静态 const 基线行保持存在"⇒ **所以客户端看到 373 行静态实体 + 活实体。**

**✅ 与 §350 的"373 个 `ET_SCRIPTMOVER`"**配合。

### 6.3 而**`shouldArchiveWorldEntity(candidate)`**

**⇒ 三层**：

```text
1. **两条路径都用 `shouldArchiveWorldEntity`**
2. ⇒ **所以归档策略是【共享的**】
3. ⇒ **而装配方式不同**
```

**✅ 一个**正确的共享点**。**

### 6.4 而**`stagedMissiles` 的 `lower_bound`**

```cpp
const auto staged = std::ranges::lower_bound(stagedMissiles, entityNum, {},
    [](const auto &entry) { return entry.handle.entityNum; });
const auto hasUpdate = staged != stagedMissiles.end() && staged->handle.entityNum == entityNum;
if (hasUpdate && staged->retire) continue;
const auto &candidate = hasUpdate ? staged->entity : entity;
```

**⇒ 四层**：

```text
1. **`stagedMissiles` 按号排序**（§376 的 `sort(numbers)`）
2. ⇒ **所以 `lower_bound` 可查**
3. ⇒ **`retire` ⇒ 跳过**（不归档）
4. ⇒ **`hasUpdate` ⇒ 用暂存的实体**
```

**✅ 与 §376 的"`sort(numbers)`"**完全闭合 ✓

**⇒ **第二次确认排序的必要性**（不只是 walk 顺序，还有**二分查找**）。

### 6.5 而**`recordedWetworkOpening`**

```cpp
const auto recordedWetworkOpening = wetworkRecordedOpeningUntil_ && snapshot_.serverTime < *wetworkRecordedOpeningUntil_;
if (!recordedWetworkOpening) { for (const auto &[entityNum, entity] : entities_) { ... } }
```

**⇒ 三层**：

```text
1. **一个"录制 Wetwork 开场"的时间窗**
2. ⇒ **窗内 ⇒ 【不归档任何世界实体】**
3. ⇒ **所以与录制的 demo 逐帧对齐**
```

**✅ 与 §342 的 `OLMOD_SNAPSHOT_HEX`**同族（**第三次"录制/回放对齐"）。**

## 七、`deathViewTargets` 的"抑制跟随相机"

### 7.1 那段

```php
// 28800: DO NOT FORCE A FOLLOW-CAMERA ON DEATH.
//
// The previous version published deathViewTargets for every dead player,
// and SV_PlayerSnapshotView sets otherFlags 0x2800 (FOLLOWING) whenever
// that map is hit. The client therefore entered a SPECTATOR view on the
// first dead frame -- the operator's "人死了直接进旁观视角" -- instead
// of 2697's `sessionstate = "dead"` body camera.
//
// 2697 keeps the view local for 1.5 s (`_damage.gsc:857-869`) and only
// then enters the replay. The equivalent here is: leave the four killcam
// fields at zero and do NOT touch the follow flags. That is what this
// window is for now -- it suppresses the follow camera, it does not
// request one.
```

### 7.2 十一层

```text
1. **不要在死亡时强制一个跟随相机**
2. ⇒ **上一版为每一个死玩家发布 `deathViewTargets`**
3. ⇒ **而 `SV_PlayerSnapshotView` 在那个 map 被命中时设 `otherFlags 0x2800`（FOLLOWING）**
4. ⇒ **所以客户端在【第一个死亡帧】就进入一个旁观视角**
5. ⇒ **⇒ 操作员的"人死了直接进旁观视角"**
6. ⇒ **而不是 2697 的 `sessionstate = "dead"` 身体相机**
7. ⇒ **2697 让视角在本地停留 1.5 秒（`_damage.gsc:857-869`）**
8. ⇒ **然后才进入回放**
9. ⇒ **这里的等价物是：把四个击杀回放字段留零而【不碰】跟随标志**
10. ⇒ **那个窗口现在的作用是【抑制】跟随相机**
11. ⇒ **它不是【请求】一个**
```

### 7.3 ⭐ **"它抑制一个跟随相机，它不请求一个"**

**✅ 与 §369 的"命令被中性化而不是跳过 pmove"**同族（**第二次"抑制 vs 请求"）。**

**⇒ 三层**：

```text
一个 map 的存在/不存在 ⇒ **两个不同的语义**
· 存在 ⇒ 请求（并附带 `0x2800`）
· **不存在 ⇒ 不请求**
⇒ **而这里要的是"明确地不请求"**
```

**⚠ 而"`0x2800`（FOLLOWING）"⇒ **一个具体的位**。**

**✅ 与 §369 的 `SvPmFlagsMatchEndFrozen`（`0x800`）**不同（**不同字段**）。**

**⚠ 所以**两个 `0x800` 族**：**

```text
pmFlags |= 0x800        匹配结束冻结（§369）
otherFlags = 0x2800     FOLLOWING（这里）
```

**✅ 一个**容易混淆的地方**。

## 八、关键结论

1. **⭐⭐ "`clientInfo` 是【按客户端】而不是【按生命】的 —— 用 `effectivePlaying` 门控它就是让一次死亡【崩掉客户端】"`**。
2. **`sub_59CC70` 把 `v4[251]` 写穿 `sub_53F5F0` 的结果而【没有 null 检查】**（HANDOFF 146c）。
3. **三段日志证据**：`killcam SUPPRESSED` → `respawn via=timed msSinceDeath=3050` → **`ClientException 0xc0000005 sub_59CC70 +0x1A5`**。
4. **⭐ "同一签名在地图加载时杀了一个【远端】客户端 ⇒ 一个原因，两个症状"`** —— 第三次"两个症状一个原因"。
5. **"这拓宽的是【何时】发一条已知记录，不是【什么算】一条"`** —— 只拓宽一半，而**从未解析过的客户端仍什么都不发**。
6. **⭐⭐ 字段 36 的完整汉语定因链**（`54BC8E/54BC90` → `characterInfo+0x7C` → `6B1010` 读行 `+0x10` → 三值映射 → `6B27C5` 只接纳 1/2）。
7. **`0xDA8078` 的 stride 12，而字段 36 = offset 4 / width 11 / type 0** —— 第三次确认那张表。
8. **三值映射是 1↔2 交换**（服务端 1 ⇒ 客户端 2；服务端 2 ⇒ 客户端 0）—— 而注释没解释原因。
9. **"本行原来写 `zmActorNamespaceEnabled_ ? 2u : 0u` ⇒ cha 的每一行都落在 `myTeam = -1`"`** —— 一个**两行代码覆盖全场景**的错误。
10. **"这同时解释了『老外僵尸模式有正确队伍表现』：老外也只给 ZM 供 2，ZM 里所有人同队"`** —— 一个**外部对照的解释**。
11. **⭐⭐ 标签 28 的"唯一可解析且被接受"`** —— `5896 + 28 = cs 5924 = tag_stowed_back`（**第五次确认 5896**），且是 `BG_UpdatePlayerDObj 0x0040AB30` 测试的两个 tag id 之一。
12. **"即使一件夹克不属于背部"`** —— 一个**明知不匹配的探针**，因为它是唯一同时满足两个条件的值。
13. **判决树**：部件出现（即使错位）⇒ 标签检查是真的；仍无 ⇒ **去 §181m 的 12 个内嵌字段**。
14. **`OLMOD_OUTFIT_TAG` 的默认 28** —— 第七次环境变量旋钮。
15. **⭐ "移位、错但看似合理"`** —— off-by-one 的失败分类（不是"不画"而是"画错"，第九次具体视觉症状）。
16. **`mask-selects` 打印【选项索引】而不是十六进制** —— 第二次"位集展开成索引"，而**零位命名 `none`**。
17. **⭐ "每个客户端保留一个先前值：一个单一共享字符串会在客户端 0 与 1 之间每一快照交替 ⇒ 使去重失效并卡住服务器控制台"`** —— 第六次 static 跨客户端问题，**而这次明确修了**。
18. **两条实体装配路径**：非 ZM（静态行 + 按号替换，**`8584acf` 基准**）vs ZM（直接 push）。
19. **`stagedMissiles` 的 `lower_bound` 依赖 §376 的 `sort`** —— 排序的正确性**不只**为了 walk 顺序。
20. **`wetworkRecordedOpening` 的窗内不归档任何世界实体** —— 第三次"录制/回放对齐"。
21. **⭐ "它抑制一个跟随相机，它不请求一个"`** —— 第二次"抑制 vs 请求"，而 `otherFlags 0x2800`（FOLLOWING）与 `pmFlags 0x800`（冻结）**两个容易混淆的位**。

## 九、未闭合点

- `sub_59CC70` 与 `sub_53F5F0` 的完整签名。
- `v4[251]` 的语义。
- 三值映射 1↔2 交换的原因。
- `BG_UpdatePlayerDObj 0x0040AB30` 的两个 tag id（另一个是什么）。
- `recordItemIds` 的 12 项与 `characterOptionMask` 的关系。
- `sv_snapshot_mp.cpp` 23200 行之后未读取（27,016 行，进度 86%）。
