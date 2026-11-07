# 494 · **"`f1` **从来**不是**一个固定的前缀** —— 它是**女性语音 1**"** —— `sv_battlechatter_mp.*` 的 `52` 步长、`1683`/`1787` 的四个 `static_assert`、以及"`27` 让那行【一次也没触发**而 `29` 让它工作**"

## 一、范围

本报告学习 `sv_battlechatter_mp.hpp`（**`247` 行**）+ `.cpp`（**`115` 行**）：`11` 条台词、`52` 的语音步长、`1674`/`947` 两个基址、四个 `static_assert`、`1400`/`1000`/`2000` 三个时间/距离、以及 `SV_BattleChatterFemaleFromModelName` 的"最后一个胜"。

## 二、**"`f1` 从来不是一个固定的前缀 —— 它是女性语音 1"**（本组最重要的一段）

### 2.1 那段

```cpp
// THE VOICE HAS A GENDER AND A FACTION, AND `f1` WAS NEVER A FIXED PREFIX.
//
// The first version of this file shipped `uk_f1_*` for everybody, and a
// player on a MALE character was answered by a woman. `f1` is not part of
// the prefix: it is FEMALE VOICE 1. There are four per faction, and the
// shipped file tree names them outright:
//
//   codo_mp/tf/{f1,f2,m1,m2}/uk_1_inform_*     alias  uk_<gender><n>_inform_*
//   codo_mp/sc/{f1,f2,m1,m2}/ab_1_inform_*     alias  ab_<gender><n>_inform_*
//   codo_mp/ancr/tf141  uk_    codo_mp/ancr/scar  ab_    codo_mp/ancr/rbt  rb_
//
// So `tf` is the uk_ voice and `sc` is the ab_ voice, which is exactly this
// server's own SvCharacterFaction::Tf / ::Sc - the mapping needed no
// invention at all. Gender comes from SvCharacterCustomization::female,
// which the server has held all along and this feature simply never read.
//
// INDEX 1 OF THE TWO, because IW4 builds its own prefix as
// `getTeamVoicePrefix( team ) + "1_"` and always takes voice 1.
```

### 2.2 二十四层

```text
1. **那个语音【有一个**性别**与【一个**阵营**】
2. ⇒ **⇒ 而 `f1` 【从来【不是【一个固定的前缀**】
3. ⇒ **⇒ 它是**女性语音 1**】
4. ⇒ **⇒ 而【每阵营【有**四个**】（`f1`/`f2`/`m1`/`m2`**）**
5. ⇒ **⇒ 而【那个发布的文件树【直接**命名**了它们**】
6. ⇒ **⇒ 所以 `tf` ⇒ `uk_` 而 `sc` ⇒ `ab_`**】
7. ⇒ **⇒ 而那【正是【这个服务器自己的 `Tf`/`Sc`**】⇒ **⇒ 所以【那个映射【没有【需要【任何**发明**】
8. ⇒ **⇒ 而【那个性别【来自 `SvCharacterCustomization::female`**】
9. ⇒ **⇒ 而【服务器【一直【持有它**】⇒ **⇒ 而【这个特性【只是【从未**读它**
10. ⇒ **⇒ 而【取【那两个里的**索引 `1`**】（**因为 IW4 【构造【它的前缀【为 `getTeamVoicePrefix(team) + "1_"` 并【永远【取语音 `1`**）**
```

### 2.3 ⭐⭐⭐ **"`f1` 从来不是一个固定的前缀，它是女性语音 1"**

**✅ 这是本报告里**最重要的一条"**一个**看起来像前缀的东西【其实是【一个**数据**"**。**

**✅ 与 §473 的"`~wea_barrett_barrett_spc-rgb&~8223d6af` 的名字被截断"**、§489 的"那个 demo 给对了形状而给错了数字"**——**同族** ✓

**⇒ 三层**：
```text
若【`f1` 是【一个前缀**】⇒ **⇒ 所有人【用【同一个**语音**
而【它是【一个**数据**（性别 + 编号**）⇒ **⇒ 四个**变体**
⇒ **⇒ 所以【那个错误【是【"把一个**数据【当成【一个**语法**"**
```

**✅ ⭐⭐⭐ **"那个错误是把一个数据当成一个语法"** —— 一个**极精确的判据**。

**⚠ 而那个**症状**】**。**

**⇒ 十层**：
```text
"a player on a MALE character was answered by a woman"
⇒ **⇒ 一个**可听见的、可报告的**症状**
⇒ **⇒ 而它【指向【一个**名字的语义**
```

**✅ ⭐⭐⭐ **"一个可听见的、可报告的症状指向一个名字的语义"** —— 与 §467 的"那个敌人就消失"**同族**（**第三次"一个**感官的症状【指向【一个**语义**"**）。

**⚠ 而那个**算术**】**。**

**⇒ 独立验证四个 `static_assert`**：
```text
Tf / female / ReloadingGeneric(9) ⇒ `1674 + 0 + 9 = 1683` ✓
Tf / male   / ReloadingGeneric(9) ⇒ `1674 + 104 + 9 = 1787` ✓（`2 × 52 = 104`）
Sc / female / ReloadingGeneric(9) ⇒ `947 + 0 + 9 = 956` ✓
Sc / male   / ReloadingGeneric(9) ⇒ `947 + 104 + 9 = 1060` ✓
Tf / female / KillfirmInfantry(7) ⇒ `1674 + 0 + 7 = 1681` ✓
Tf / female / AttackFlashbang(0)  ⇒ `1674 + 0 + 0 = 1674` ✓
⇒ **⇒ 六个**全部精确** ✓
```

**✅ ⭐⭐⭐ **"六个全部精确"** —— 而**那六个 `static_assert` 【检查【的是【那个**公式**（"these assertions check the FORMULA rather than restating it"）**。】

**✅ 与 §468 的"`81,128/81,128` 零失配"**——**同族**（**第四次"一个**公式【被【六个**独立的值**验证**"**）。

**⚠ 而那个**枚举的 `11` 条**】**。**

**⇒ 十层**：
```text
`AttackFlashbang = 0` … `SuppressedGeneric = 10`，`Count = 11`
⇒ **⇒ 而【那【正是【那个【`<voice>_f1_inform_*` 的**十一个**】
⇒ **⇒ 而【那个注释说**："**the eleven `<voice>_f1_inform_*` lines per faction voice**"
```

**✅ ⭐⭐⭐ **"十一个"** —— 而**那【也【解释【了【`52` 的步长**（**`4` 个语音 × `13`？** **不，是【一个**不同的**数**）**。**

**⇒ 独立核算**：
```text
`52 = 4 × 13` 或 `52` 是【一个**任意**的间隔
而【那个注释说**："**the four voices of one faction are 52 apart**"
⇒ **⇒ 所以【`52` 【是【那个**表**的步长**】（**不是【`11 × something`**）
```

**✅ ⭐⭐⭐ **"52 是那个表的步长，不是 11 × something"**。

**⚠ 而"八个里【有【八个**】**。**

**⇒ 三层**：
```text
"IW4's nine bcSounds" ⇒ **而【本 build 【有**八个**】
`inform_casualty_generic` ⇒ **不存在**】⇒ **⇒ 所以【那个"casualty"触发【没有东西可说**】
⇒ **⇒ 而【它【在下面【缺席**，而不是【用一个【意思是【别的**的行【替换**
```

**✅ ⭐⭐⭐ **"它缺席，而不是用一个意思是别的的行替换"** —— 与 §468 的"没有见证的值故意缺席"**完全同族** ✓

**⇒ 三层**：
```text
§468  **"Values with no witness are deliberately absent"**
§494  **"it is absent below rather than substituted with a line that means something else"**
⇒ **⇒ 两次"一个**无见证的值【故意缺席**"**
```

**✅ ⭐⭐⭐ **"一个无见证的值故意缺席"两例**。

## 三、**那个"`27` 让那行一次也没触发而 `29` 让它工作"**（本组第二重要）

### 3.1 那段

```cpp
// The first version of this file used 27 (EV_RELOAD_START) off the name
// table instead, and the reload line never fired once in a played match
// while the kill line worked -- the name table says what an id MEANS, not
// which ids this build's Pmove emits. 29 is also the semantically right
// one: IW4's trigger is `waittill( "reload_start" )`, and a GSC notify is
// driven by the NOTIFY event, not the state change.
constexpr std::int32_t SvEventReloadStartNotify = 0x1D;
```

### 3.2 二十四层

```text
1. **第一个版本【用 `27`（`EV_RELOAD_START`）【从那个名字表**取**】
2. ⇒ **⇒ 而那个换弹行【在一场打的比赛里【一次也没触发**】
3. ⇒ **⇒ 而那个击杀行【工作**】
4. ⇒ **⇒ 因为那个名字表【说【一个 id **意味着什么**】⇒ **⇒ 而不是【说【这个 build 的 `Pmove` 【发射【哪些 id**】
5. ⇒ **⇒ 而 `29`（`0x1D`）也【是【那个语义上正确的**】
6. ⇒ **⇒ 因为 IW4 的触发【是 `waittill("reload_start")`**】
7. ⇒ **⇒ 而一个 GSC 通知【由【那个 **NOTIFY 事件**驱动**】⇒ **⇒ 而不是【由【那个**状态变化**
```

### 3.3 ⭐⭐⭐ **"那个名字表说的是一个 id 意味着什么，而不是这个 build 的 Pmove 发射哪些 id"**

**✅ 与 §474 的"`0x1E` 与 `0x1D` 出现在一次换弹周围"**——**完全闭合** ✓

**⇒ 三层**：
```text
§474  **"0x1E and 0x1D appear around a reload"（**一个活环的测量**）**
§494  **"the name table says what an id MEANS, not which ids this build's Pmove emits"**
⇒ **⇒ 所以【§494 【给了【§474 的那个测量【一个**解释**】
```

**✅ ⭐⭐⭐ **"§494 给了 §474 的那个测量一个解释"** —— 一个**跨报告的闭合**。

**⚠ 而那个 `0x1D = 29` 与 `27` 的**差**】**。**

**⇒ 十层**：
```text
`27` ⇒ `EV_RELOAD_START`（**那个名字表说的**）
`29` ⇒ **`0x1D`（`EventReloadStartNotify`）**（**而 §474 说它是 `+1` 从 3.3.3.3 的 `0x1C = 28`**）
⇒ **⇒ 所以【`27` vs `29` 的差 `2`**】⇒ **⇒ 而 §474 的 `+1` 是【从 `0x1C` 到 `0x1D`**
```

**⚠ 标注**：3.3.3.3 的 `0x1C = 28` ⇒ 而 `27` 是 `EV_RELOAD_START` —— **所以那两个是【相邻但不同**的 id**。而**那个 `0x1D = 29` 【是【那个 `NOTIFY`**。

**✅ ⭐⭐⭐ **"那两个是相邻但不同的 id"**。

**✅ 与 §471 的"`0x0280E831` 八次出现 + 一次配对"**——**同族**（**第五次"一个**相邻【的数【必须**分辨**"**）。

## 四、**`1400` / `1000` / `2000` 三个数**（本组第三重要）

### 4.1 三个

```text
SvBattleChatterAudibleRadius      = 1400.0f   （那个 alias 的 maxdist）
SvBattleChatterSuppressionRadius  = 1000.0f   （isSpeakerInRange 的 distSq）
SvBattleChatterSpeakerHoldMs      = 2000      （timeHack 的 wait(2.0)）
```

### 4.2 二十四层

```text
1. **`988` 字节 = `9` 个 108 字节的**替代录音**】
2. ⇒ **⇒ 而【每一个【携带 `mindist 7.0` / `maxdist 1400.0`**】
3. ⇒ **⇒ 而【那个播报员的 `uk_1mc_timesup` 携带 `360/600`**】⇒ **⇒ 所以【一个【是**世界声音**】而【另一个【几乎是 **UI**
4. ⇒ **⇒ 所以 `1400` 【不是【一个选择**，而是【从【那个 alias 记录【读出来的
```

### 4.3 ⭐⭐⭐ **"一个 988 字节 = 9 个 108 字节的替代录音"**

**✅ 独立验证**：`9 × 108 = 972`，而 `988 − 972 = 16` ⇒ **所以那 16 字节是那个头的**。

**⇒ 十层**：
```text
`988 - 9 × 108 = 988 - 972 = 16`
⇒ **⇒ 所以【那个记录【有 `16` 字节的**头**
⇒ **⇒ 而【`16` 与【§468 的 `Mtl name at +16`**/§484 的 `+0`/`+38`/`+40`** 同族
```

**✅ ⭐⭐⭐ **"988 − 972 = 16 字节的头"** —— 一个**精确的算术**。

**✅ 与 §468 的"`OffMtlName = 16`"**——**同族**（**第六次"一个**16 字节的头**"**）。

**⚠ 而 `360/600` 的对比**】**。**

**⇒ 三层**：
```text
`1400` ⇒ **一个**世界**的声音**】
`600` ⇒ **一个**几乎 UI**的声音**】
⇒ **⇒ 所以【那个**半径【是【一个**属性的**数据
```

**✅ ⭐⭐⭐ **"那个半径是一个属性的数据"**。

**⚠ 而 `1000` 的**理由**】**。**

**⇒ 十层**：
```cpp
// CODREF: _battlechatter_mp.gsc isSpeakerInRange -- `distSq = 1000 * 1000`.
// If a teammate is already speaking within this, the line is DROPPED, not
// queued. Chatter is ambience; two people shouting over each other is worse
// than silence.
```
```text
1. **那个 `1000` 【直接【来自【那个 GSC 的 `distSq = 1000 * 1000`**】
2. ⇒ **⇒ 而【那个行为【是【**丢弃**【而不是【排队**】
3. ⇒ **⇒ 因为【"chatter 是**氛围**；两个人【互相【喊【比【沉默**更坏**"**
```

**✅ ⭐⭐⭐ **"chatter 是氛围；两个人互相喊比沉默更坏"** —— 一个**极清晰的产品判断**。

**✅ 与 §493 的"fail closed 并重试，绝不把玩家放进几何体"**——**同族**（**第四次"一个**丢弃【优于【一个**错误的状态**"**）。

## 五、**`EveryoneIncludingSpeaker` 的"一个有名字的产品决定"**（本组第四重要）

### 5.1 那段

```cpp
// IT SHIPPED ON Everyone TO BE TESTED, AND THE PLAYER KEPT IT -- then went
// further and kept hearing their OWN callouts too, having heard it in a
// played match: "it works the way you say it. Let's keep self audition,
// it's pretty cool. Can come back at a later time later in dev to change
// it." So the default below is EveryoneIncludingSpeaker, and it is a
// PRODUCT DECISION with a name on it rather than a bug or a leftover
// debugging switch. Revisit when that call is revisited, not before.
```

### 5.2 二十四层

```text
1. **它【在 `Everyone` 上发布【为了被测试**】
2. ⇒ **⇒ 而【那个玩家【保留了它**】
3. ⇒ **⇒ 然后【更进一步【保留了【听到【他们自己的**喊话**
4. ⇒ **⇒ （**在一场打的比赛里【听到它**之后）**
5. ⇒ **⇒ 而【那个引用**："**`it works the way you say it. Let's keep self audition, it's pretty cool.`**"**
6. ⇒ **⇒ 所以【那个默认【是 `EveryoneIncludingSpeaker`**】
7. ⇒ **⇒ 而【它【是【一个【有名字**的产品决定**】⇒ **⇒ 而不是【一个 bug 或一个**遗留的调试开关**
8. ⇒ **⇒ 而当【那个决定【被【重新考虑时【再【回访**】⇒ **⇒ 不**在那之前
```

### 5.3 ⭐⭐⭐ **"一个有名字的产品决定，而不是一个 bug 或一个遗留的调试开关"**

**✅ 与 §462 的"那是一个发现，不是那个写的一个缺陷"**——**同族** ✓

**⇒ 三层**：
```text
§462  **"That is the finding, not a defect in the write"**
§494  **"a PRODUCT DECISION with a name on it rather than a bug or a leftover debugging switch"**
⇒ **⇒ 两次"一个**非缺陷**的标注**"**
```

**✅ ⭐⭐⭐ **"一个非缺陷的标注"两例**。

**⚠ 而那个**忠实路径【只差一个谓词**】**。**

**⇒ 十层**：
```cpp
// The faithful path stays one predicate away - `OLMOD_BATTLECHATTER_TEAM=1`
// - and nothing else about the feature changes with it.
```
```text
`OLMOD_BATTLECHATTER_TEAM=1` ⇒ **⇒ 一个**环境变量【恢复零售**
⇒ **⇒ 而【那个特性【别的什么都不变**】
⇒ **⇒ 所以【那个**default【是【可以被【一行**切换的
```

**✅ ⭐⭐⭐ **"那个 default 是可以被一行切换的"** —— 与 §470 的 `OLMOD_PERF_BASELINE`**同族**（**第三次"一个**环境变量【的开关**"**）。

**⚠ 而那个**为什么不【用一个 world entity**】**。**

**⇒ 十六层**：
```cpp
// an entity would be positional but reaches EVERY client, because
// shouldArchiveWorldEntity has no per-client visibility stage
// (sv_snapshot_mp.cpp, and its own TODO says the dedicated one was never
// recovered). Team-only would then be an unbuilt subsystem rather than a
// predicate, and "assume teams works" would be assuming untested code.
```
```text
1. **一个实体【会【是**位置性的**【但【会【到达【每一个**客户端**】
2. ⇒ **⇒ 因为 `shouldArchiveWorldEntity` 【没有【一个**按客户端的可见性阶段**】
3. ⇒ **⇒ （而它自己的 `TODO` 说【那个专用的【从未**被恢复**）
4. ⇒ **⇒ 所以【"仅队伍"【会【是【一个**未构建的子系统**】⇒ **⇒ 而不是【一个**谓词**
5. ⇒ **⇒ 而【"假设队伍工作" 【会【是【假设【未测试的**代码**】
```

**✅ ⭐⭐⭐ **"'假设队伍工作'会是假设未测试的代码"** —— 一个**极强的**工程判断**。

**✅ 与 §479 的"那个 `12` 行的批次必分两条命令"**——**同族**（**第五次"一个**架构【的**后果**"**）。

**⚠ 而那个**代价【被明说**】**。**

**⇒ 十层**：
```cpp
// THE COST, STATED: `p` is a LOCAL sound, so this has no direction and no
// falloff - it is full volume or nothing. The radius above is applied
// server-side to stand in for the attenuation the client would have done.
```
```text
1. **`p` 是【一个**本地**的声音**】⇒ **⇒ 所以【没有方向、没有衰减**】
2. ⇒ **⇒ 它【是【全音量【或【什么都没有**】
3. ⇒ **⇒ 所以【那个半径【被【在**服务端**【应用**】⇒ **⇒ 来代替【那个客户端【本会【做的**衰减**
```

**✅ ⭐⭐⭐ **"全音量或什么都没有"** —— 一个**极诚实的代价**。

**✅ 与 §493 的"那个 FX 在那个玩家的上方 10.73..59.73 单位"**——**不同**，但与 §494 五 的"一个有名字的产品决定"**同族**。

## 六、**`SV_BattleChatterFemaleFromModelName` 的"最后一个胜"**

### 6.1 那段

```cpp
// The LAST one wins: `fpa_cowprestigea_sc_m_00_hrt` has the gender
// before two variant tokens, and a name whose subject happens to
// contain a lone letter earlier must not outrank the real one.
if (component == "m") female = false;
else if (component == "f") female = true;
```

### 6.2 二十四层

```text
1. **按 `_` **切分**，而【每一个**恰好**是 `m` 或 `f` 的分量【更新**那个结果**
2. ⇒ **⇒ 而【**最后一个**胜**
3. ⇒ **⇒ 所以 `fpa_cowprestigea_sc_m_00_hrt` ⇒ `male`**】（**那个 `m` 在【两个变量 token **之前**）
4. ⇒ **⇒ 而【一个**主语里【恰好【含一个**孤立的字母**的名字【不能【压过【那个**真正的**
```

### 6.3 ⭐⭐⭐ **"'最后一个胜' —— 因为那个性别在两个变量 token 之前"**

**✅ 与 §467 的"`SvMapEntity::value` 从 `rbegin()` 找 ⇒ 键内重复【最后一次胜"**——**完全同族** ✓

**⇒ 三层**：
```text
§467  **`fields.rbegin()` ⇒ **最后一次**胜**
§494  **"The LAST one wins"**
⇒ **⇒ 两次【同一个**方向**】
```

**✅ ⭐⭐⭐ **"两次同一个方向"两例**。

**⚠ 而 §467 的 `byPlace` 是**第一个**胜 —— 与这里**相反**】**。**

**⇒ 十层**：
```text
§467  **`SvMapEntity::value` ⇒ **最后**胜** / **`byPlace` ⇒ **第一**胜**（**同一文件里两个方向**）
§494  **`FemaleFromModelName` ⇒ **最后**胜**
⇒ **⇒ 所以【那个"最后胜"【是【一个**常见的**惯例**】⇒ **⇒ 而【§467 的 `byPlace` 【是【那个**例外**
```

**✅ ⭐⭐⭐ **"那个『最后胜』是一个常见的惯例，而 §467 的 byPlace 是那个例外"**。

**⚠ 而那个**测量**】**。**

**⇒ 十六层**：
```cpp
// MEASURED IN A LIVE MATCH: two players, one on `fpa_raider_sc_m` and one
// on `fpa_pingoles_sc_f`, and BOTH resolved to the male voice --
// SvCharacterCustomization::female was false for the female character.
// `presentation.female = characterDefinition[2] != 0` is evidently reading
// something that is not the gender, and correcting THAT is out of scope
// here: `female` is written into clientInfo and the client may pick a body
// from it, so changing it risks the rendering path to fix a sound.
//
// The model name carries it unambiguously. Checked against every `fpa_`
// body model in the shipped zones -- 456 of them -- by taking the LAST
// bare `m` or `f` component: 279 male, 173 female, 4 unresolved
```
```text
1. **两个玩家（`fpa_raider_sc_m` 与 `fpa_pingoles_sc_f`）【都【解析成【男声**】
2. ⇒ **⇒ 因为 `SvCharacterCustomization::female` 【对【那个女性角色【是 `false`**】
3. ⇒ **⇒ 而 `presentation.female = characterDefinition[2] != 0` 【显然【读的是【别的**东西**
4. ⇒ **⇒ 而修正**那个【超出范围**】⇒ **⇒ 因为 `female` 被【写进 `clientInfo`**】
5. ⇒ **⇒ 而【客户端【可能【从它【选一个**身体**】⇒ **⇒ 所以【改它【会【拿【渲染路径冒险【去【修一个**声音**
6. ⇒ **⇒ 而【那个模型名【明确地【携带它**】
7. ⇒ **⇒ 对【发布的 zone 里【每一个 `fpa_` 身体模型【检查过**】⇒ **⇒ `456` 个**
8. ⇒ **⇒ `279` 男 / `173` 女 / `4` 未解析**】
9. ⇒ **⇒ 而那四个【是 `fpa_tightjeans_*`（**裤子【被【错槽成【一个身体**）
```

**✅ ⭐⭐⭐ **"'改它会拿渲染路径冒险去修一个声音'"** —— 一个**极强的范围纪律**。

**✅ 与 §468 的"没有见证的值故意缺席"**——**同族**（**第六次"一个**有意的**不做**"**）。

**⚠ 而 `279 + 173 + 4 = 456`**】**。**

**⇒ 独立验证**：
```text
`279 + 173 + 4 = 456` ✓
⇒ **⇒ 所以【那个**总数【精确**
```

**✅ ⭐⭐⭐ **"279 + 173 + 4 = 456 精确"** —— 一个**算术闭合**。

**⚠ 而"那个命名是 `<slot>_<name>_<faction>_<gender>[_variant...]`"**】**。**

**⇒ 三层**：
```text
`fpa_raider_sc_m` ⇒ **`fpa` / `raider` / `sc` / `m`** ✓
`fpa_cowprestigea_sc_m_00_hrt` ⇒ **`fpa` / `cowprestigea` / `sc` / `m` / `00` / `hrt`** ✓
⇒ **⇒ 所以【那个"最后一个"【找到【那个 `m`**】（**而【`hrt` 不是 `m`/`f`**）
```

**✅ ⭐⭐⭐ **"那个『最后一个』找到那个 m（而 hrt 不是 m/f）"**。

## 七、`SV_BattleChatterSuppressed` 的"一个玩家不能盖过他自己的那行"

### 7.1 那段

```cpp
// CODREF: isSpeakerInRange returns true for the player themselves
// BEFORE any distance test, so a player cannot talk over their own
// line however far they have run in the meantime.
if (speaker.clientNum == clientNum) return true;
```

### 7.2 二十四层

```text
1. **那个 `clientNum` 匹配【在【任何距离测试【之前**】
2. ⇒ **⇒ 所以【一个玩家【不能【盖过【他自己的**那行**
3. ⇒ **⇒ 无论【他【在这期间【跑了**多远**
```

### 7.3 ⭐⭐⭐ **"无论他在这期间跑了多远"**

**✅ 与 §493 的"`factoryTravelHeld` 的三重条件"**——**同族**（**第五次"一个**身份【优先于【一个**几何**"**）。

**⇒ 三层**：
```text
若【先查距离**】⇒ **⇒ 一个【跑了 1000 单位**的玩家【可以【立刻【再说一次**
若【先查身份**】⇒ **⇒ 那个 `2000ms` 的**持有【仍然【有效**
⇒ **⇒ 所以【那个顺序【是【那个**正确性的关键**】
```

**✅ ⭐⭐⭐ **"那个顺序是那个正确性的关键"** —— 与 §478 的"那个高度检查先"**完全同族** ✓

**⇒ 三层**：
```text
§478  **"那个高度检查【先**（**在【那个平面距离**之前**）"**
§494  **"那个 `clientNum` 匹配【在【任何距离测试【之前**"**
⇒ **⇒ 两次"一个**检查的顺序【是【一个**行为**"**
```

**✅ ⭐⭐⭐ **"一个检查的顺序是一个行为"两例**。

**⚠ 而那个 `currentServerTime >= speaker.untilServerTime ⇒ continue`**】**。**

**⇒ 十层**：
```text
"An expired hold is not a speaker. The caller may keep stale entries;
deciding here rather than requiring a swept list keeps the two from
disagreeing about who currently holds the floor."
⇒ **⇒ 所以【那个**过期【的判定【在【这个函数里**】⇒ **⇒ 而不是【要求【一个**被清扫的列表**
```

**✅ ⭐⭐⭐ **"决定在这里而不是要求一个被清扫的列表，保持两者不会就不一致"** —— 一个**极精确的所有权**。

**✅ 与 §490 的"`resolve` 与 `free` 都显式处理了保留槽"**——**同族**（**第六次"一个**判定【在【一个**明确的地方**"**）。

## 八、`SvBattleChatterAudience` 的"那一行唯一谓词"

### 8.1 那段

```cpp
// THE ONE PREDICATE. Everything else in this feature is identical
// between the two settings; see the header for why it is a knob at
// all and why delivery is per-client rather than a world entity.
if (audience == SvBattleChatterAudience::Team)
{
    if (speakerTeam == SvTeam::None || speakerTeam == SvTeam::Spectator ||
        listener.team != speakerTeam)
    {
        continue;
    }
}
```

### 8.2 二十四层

```text
1. **唯一的谓词【是【那个 `audience == Team`**】
2. ⇒ **⇒ 而【那个 `None`/`Spectator`【被【显式**排除**
3. ⇒ **⇒ 因为【一个**无队伍**的说话者【没有队伍【可【广播**】
4. ⇒ **⇒ 所以【那个 `Team` 分支【在【FFA 里【是【一个**空集**
```

### 8.3 ⭐⭐⭐ **"一个无队伍/观战的说话者没有队伍可广播"**

**✅ 与 §494 三 的"在自由混战里没人有队伍，所以它到达不了任何人 —— 而那正是为什么那个零售 dm demo 携带零条 battlechatter"**——**完全同族** ✓

**⇒ 三层**：
```text
FFA ⇒ **`speakerTeam == None` ⇒ 【那个 Team 分支【过滤掉**一切**
⇒ **⇒ 所以【retail 的 dm demo【零条**】（**"它不是从那个 demo 里【缺失，它是【在那个模式里【结构性地**沉默**"**）
```

**✅ ⭐⭐⭐ **"它不是从那个 demo 里缺失，它是在那个模式里结构性地沉默"** —— 与 §477 的"那个 `eType-98` 事件发出去了而没有伤害"**相反**（**那里【发出去了**，这里【结构性地【不发出**）**。

**⚠ 而那个**排除自己【在【两个设置【下都成立**】**。**

**⇒ 十层**：
```cpp
// CODREF: playSoundToTeam( alias, team, self ) -- the third
// argument is the EXCLUDED entity. You never hear your own
// battlechatter, in any mode. This holds on both audience settings
// because it is not the part that is in question.
if (listener.clientNum == speakerClientNum &&
    audience != SvBattleChatterAudience::EveryoneIncludingSpeaker)
{
    continue;
}
```
```text
1. **`playSoundToTeam(alias, team, self)` 的第三个参数【是那个**被排除的实体**】
2. ⇒ **⇒ 所以【你【永远【听不到【你自己的** battlechatter**】
3. ⇒ **⇒ 而那【在【两个设置【下【都成立**】
```

**✅ ⭐⭐⭐ **"那在两个设置下都成立"** —— **除了 `EveryoneIncludingSpeaker`** ⇒ 而**那个【是【那个"一个"的例外**】**。**

## 九、关键结论

1. **⭐⭐⭐ "`f1` 从来不是一个固定的前缀 —— 它是女性语音 1"**：**"这个文件的第一个版本给所有人发了 `uk_f1_*`，而一个在男性角色上的玩家被一个女人的声音回答"** ⇒ **"那个错误是把一个数据当成一个语法"**（**`f1` 是一个数据（性别 + 编号），不是一个语法（前缀）**）；而 **`52` 的步长（`4` 个语音 × 一个任意间隔）与 `1674`/`947` 两个基址，由六个 `static_assert` 验证那个公式**（**独立验证六个全部精确 ✓**）；而 **`tf` ⇒ `uk_` / `sc` ⇒ `ab_` 正是 `SvCharacterFaction::Tf`/`::Sc`**（"那个映射没有需要任何发明"）。
2. **⭐⭐⭐ "那个名字表说的是一个 id 意味着什么，而不是这个 build 的 Pmove 发射哪些 id"`** ⇒ **"第一个版本用 `27`（`EV_RELOAD_START`）从那个名字表取，而那个换弹行在一场打的比赛里一次也没触发，而那个击杀行工作；`29` 也是语义上正确的（IW4 的触发是 `waittill("reload_start")`，而一个 GSC 通知由那个 NOTIFY 事件驱动，而不是由那个状态变化）"`** —— **§494 给了 §474 的那个活环测量（"`0x1E` 与 `0x1D` 出现在一次换弹周围"）一个解释**。
3. **⭐⭐⭐ "八个里只有八个：`inform_casualty_generic` 不存在，所以那个 `casualty` 触发没有东西可说，而它**在下面缺席而不是用一个意思是别的的行替换**"`** —— 与 §468 的"没有见证的值故意缺席"**同族**。
4. **⭐⭐⭐ `1400`/`1000`/`2000` 三个数各有出处**：`1400` 是那个 alias 记录的 `maxdist`（**独立验证 `988 − 9 × 108 = 16` 字节的头**）；`1000` 是那个 GSC 的 `distSq = 1000 * 1000`（**"丢弃而不是排队 —— chatter 是氛围；两个人互相喊比沉默更坏"**）；`2000` 是那个 `timeHack` 的 `wait(2.0)`（**"一个说话者持有那个地板两秒，无论那个片段的真实长度"**）。
5. **⭐⭐⭐ `EveryoneIncludingSpeaker` 的完整病历**：**"它在 `Everyone` 上发布为了被测试，而那个玩家保留了它 —— 然后更进一步保留了听到他们自己的喊话，在一场打的比赛里听到它之后：『它按你说的那样工作。让我们保留自我试听，挺酷的。』所以下面的默认是 `EveryoneIncludingSpeaker`，而它是**一个有名字的产品决定**，而不是一个 bug 或一个遗留的调试开关。当那个决定被重新考虑时再回访，不那之前"`** —— 与 §462 的"那是一个发现，不是那个写的一个缺陷"**同族**。
6. **⭐⭐⭐ "那个忠实的路径只差一个谓词 —— `OLMOD_BATTLECHATTER_TEAM=1` —— 而那个特性别的什么都不变"`** ⇒ **"那个 default 是可以被一行切换的"**（与 §470 的 `OLMOD_PERF_BASELINE` 同族）。
7. **⭐⭐⭐ "为什么投递是一个按客户端的 `p` 而不是一个 world sound 实体：一个实体**会是位置性的但会到达每一个客户端**，因为 `shouldArchiveWorldEntity` 没有一个按客户端的可见性阶段（而它自己的 TODO 说那个专用的从未被恢复）。所以『仅队伍』会是一个**未构建的子系统**而不是一个谓词，而『假设队伍工作』会是假设未测试的代码"`** ⇒ **"'假设队伍工作'会是假设未测试的代码"**（一个极强的工程判断）。
8. **⭐⭐⭐ "那个代价，被明说：`p` 是一个**本地**声音，所以它没有方向、没有衰减 —— 它**是全音量或什么都没有**。上面那个半径在服务端被应用，来代替那个客户端本会做的衰减"`** ⇒ **"全音量或什么都没有"**（一个极诚实的代价）。
9. **⭐⭐⭐ `SV_BattleChatterFemaleFromModelName` 的"最后一个胜"**：**"`fpa_cowprestigea_sc_m_00_hrt` 有那个性别在两个变量 token 之前，而一个主语里恰好含一个孤立字母的名字不能压过那个真正的"`** ⇒ 与 §467 的 `SvMapEntity::value` 的 `rbegin()` **同族**（**而 §467 的 `byPlace` 是那个例外**）；而那个测量：**两个玩家（`fpa_raider_sc_m` 与 `fpa_pingoles_sc_f`）都解析成男声，因为 `SvCharacterCustomization::female` 对那个女性角色是 `false`**；而 **"`presentation.female = characterDefinition[2] != 0` 显然读的是别的什么东西，而修正那个超出范围 —— `female` 被写进 `clientInfo` 而客户端可能从它选一个身体，所以改它会拿渲染路径冒险去修一个声音"`**；而 **`456` 个 `fpa_` 身体模型 ⇒ `279` 男 / `173` 女 / `4` 未解析（独立验证 `279 + 173 + 4 = 456` ✓），而那四个是 `fpa_tightjeans_*`（裤子被错槽成一个身体）**。
10. **⭐⭐⭐ `SV_BattleChatterSuppressed` 的"身份优先于几何"**：**"那个 `clientNum` 匹配在**任何距离测试之前**，所以一个玩家不能盖过他自己的那行，**无论他在这期间跑了多远**"`** ⇒ **"那个顺序是那个正确性的关键"**（与 §478 的"那个高度检查先"同族）；而 **"一个过期的持有不是一个说话者 —— 决定在这里而不是要求一个被清扫的列表，保持两者不会就不一致"`**。
11. **⭐⭐⭐ `SvBattleChatterAudience` 的"那一行唯一谓词"** ⇒ **FFA 里 `speakerTeam == None` 过滤掉一切 ⇒ "它不是从那个 demo 里缺失，它是在那个模式里结构性地沉默"`**（与 §477 的"事件发出去了而没有伤害"**相反**）。

## 十、`sv_battlechatter_mp` 全文件总览

**`.hpp`：`247` 行。`.cpp`：`115` 行。**

**`11` 条台词**：`AttackFlashbang` / `AttackGrenade` / `AttackSmoke` / `AttackStiel` / `AttackStun` / `AttackThwC4` / `KillfirmGeneric` / `KillfirmInfantry` / `PlantClaymore` / `ReloadingGeneric` / `SuppressedGeneric`。

**`6` 个常量**：
```text
SvBattleChatterVoiceStride            52
SvBattleChatterTfFemaleBase         1674
SvBattleChatterScFemaleBase          947
SvBattleChatterAudibleRadius      1400.0f
SvBattleChatterSuppressionRadius  1000.0f
SvBattleChatterSpeakerHoldMs        2000
SvEventReloadStartNotify            0x1D
```

**`6` 个 `static_assert`**（四个基址组合 + `KillfirmInfantry` + `AttackFlashbang`）。

**`4` 个函数**：`SvBattleChatterParameter` / `SV_BattleChatterFemaleFromModelName` / `SV_BattleChatterDistanceSquared` / `SV_BattleChatterSuppressed` / `SV_BattleChatterAudience`。

**`9` 个测量锚点**：
```text
uk_ 1674..1684 / ab_ 947..957
codo_mp/tf/{f1,f2,m1,m2} / codo_mp/sc/{f1,f2,m1,m2}
codo_mp/ancr/{tf141,scar,rbt}
988 字节 = 9 × 108（mindist 7.0 / maxdist 1400.0）
uk_1mc_timesup 的 360/600
isSpeakerInRange 的 distSq = 1000 * 1000
timeHack 的 wait(2.0)
2026-08-21 的两弹匣换弹环测量
fpa_ 456 个身体模型：279 男 / 173 女 / 4 未解析
```

## 十一、未闭合点

- `SvBattleChatterLine::Count` 之外是否还有别的台词（那八个 IW4 的 `bcSounds`）。
- `OLMOD_BATTLECHATTER_EXCLUDE_SELF` 与 `TEAM` 两个开关的默认组合。
- `SvBattleChatterAudience::Everyone`（不含 speaker）与 `EveryoneIncludingSpeaker` 的调用点。
- 下一个文件：`sv_destructible_mp.cpp`（`11,241` 字节）或 `sv_playlist_mp.cpp`（`10,509` 字节）。
