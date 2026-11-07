# 482 · **"§49 得出了相反的结论，而那个推断是错的"** —— `sv_scoreboard_mp.cpp` 的 `198` 字节行、`27` 列、以及"每条都写 'J' 的代价"

## 一、范围

本报告学习 `sv_scoreboard_mp.cpp`（**`444` 行**）全文件：`aarScoreboard` 的 `67/198` 基址与步长、`21+3` 个字段偏移、三段 run 的划分、`K … J` 契约、`0x3FE` 的上限、助攻的 `serverTime` 窗口与 `8` 槽账本。

## 二、**"§49 得出了相反的结论，而那个推断是错的"**（本组最重要的一段）

### 2.1 那段

```cpp
// VERIFIED ON 1649370's OWN def, and the answer is that these numbers are RIGHT.
// Section 49 concluded the opposite -- same version 233, different formatChecksum
// (0x4A6CC345 against 3.3.3.3's 0xE32D50D6), different enum field set, therefore a
// different row layout -- and that inference was wrong. The def really does differ
// everywhere it was measured to: 8 structs against 4, 40 indexed arrays against
// 26, size 15767 against 14426, offset table 3927 entries against 3414. The
// aarScoreboard ROW is nonetheless byte-for-byte identical, including all five
// bit-addressed fields.
```

### 2.2 二十四层

```text
1. **在 1649370 自己的 `def` 上【验证**】⇒ **⇒ 而答案是【这些数【是对的**】
2. ⇒ **⚠ 而 §49 【得出了相反的结论**】
3. ⇒ **⇒ 理由：同一个版本 `233`，不同的 `formatChecksum`**（`0x4A6CC345` 对 3.3.3.3 的 `0xE32D50D6`）**
4. ⇒ **⇒ 不同的 enum 字段集**】
5. ⇒ **⇒ 【因此一个不同的行布局**】
6. ⇒ **⇒ ⚠ 而那个推断【是错的**】
7. ⇒ **⇒ 因为那个 `def` 【在【每一个【被测量过的地方【确实**不同**】
8. ⇒ **（`8` 个结构 对 `4` / `40` 个索引数组 对 `26` / 大小 `15767` 对 `14426` / 偏移表 `3927` 条 对 `3414`**）**
9. ⇒ **⇒ ⚠ 而【那个 `aarScoreboard` 的**行**【仍然【逐字节相同**】
10. ⇒ **⇒ 包括【全部五个【位寻址的**字段**】
```

### 2.3 ⭐⭐⭐ **"那个 def 在每一个被测量过的地方确实不同，而那个 aarScoreboard 的行仍然逐字节相同"**

**✅ 这是本报告里**最重的一条**证伪**。**

**✅ 与 §476 的"§51i 把它们记成 FOREIGN，而那被那些镜像自己推翻"**、§471 的"§79g 拒绝去数的那个字面量池是一个不同的东西"**——**完全同族** ✓

**⇒ 三层**：
```text
§471  **§79g 数错了对象**
§476  **§51i 的 FOREIGN 被镜像推翻**
§482  **§49 的"因此不同的行布局"是错的**
⇒ **⇒ 三次"一个**早期的结论【被【一个更精确的**读法推翻**"**
```

**✅ ⭐⭐⭐ **"一个早期的结论被一个更精确的读法推翻"三例表**。

**⚠ 而那个**推理的缺陷**】**。**

**⇒ 十层**：
```text
前提 M ⇒ **那个 def 【在【五个**可测的维度上【都不同**】
结论 C ⇒ **因此【那个行布局【不同**】
⇒ **⇒ 而那是一个【无效**的推断**（**"整体不同" 【不【蕴含【"每一部分不同"**）**
```

**✅ ⭐⭐⭐ **"'整体不同'不蕴含'每一部分不同'"** —— 一个**极精确的逻辑错误**。

**✅ 与 §467 的"一个回落比一个失败更危险"**——**不同**（那是一个**行为**，这是一个**推理**）但**同族**（**第四次的"一个**看似显然的推断**"**）。

### 2.4 而**那个"CONFIRMED TWICE, BY DECODERS THAT SHARE NO CODE"**

```cpp
// CONFIRMED TWICE, BY DECODERS THAT SHARE NO CODE. Tools/ffa/parse-structureddatadef.py
// was written in an earlier session and walks the asset as a depth-first zone stream;
// fed 1649370's def it reports `consumed 22940 of 22940 bytes EXACT`, which is a real
// check because the stream has no alignment padding and a wrong record layout cannot
// reach the last byte. It names every field and agrees with the shape-based decode on
// all of them, `isMe`'s bit offset included. Section 49 had that parser available and
// never ran it on this build's def.
```

**⇒ 二十四层**：
```text
1. **两次确认，由【共享零代码**的解码器**】
2. ⇒ **⇒ `Tools/ffa/parse-structureddatadef.py` 【在一个更早的会期【被写**】
3. ⇒ **⇒ 而【它【把那个资产【当成【一个**深度优先的 zone 流**走**】
4. ⇒ **⇒ 喂 1649370 的 `def` ⇒ 它报告【`consumed 22940 of 22940 bytes EXACT`**】
5. ⇒ **⇒ 而那【是【一个**真实的检查**】（**那个流【没有**对齐填充**）
6. ⇒ **⇒ 而【一个**错的记录布局【不能【到达【最后一个字节**】
7. ⇒ **⚠ 而 §49 【有那个解析器【可用**】⇒ **⇒ 而【从未【在【这个 build 的 `def` 上**跑它**】
```

### 2.5 ⭐⭐⭐ **"一个错的记录布局不能到达最后一个字节"**

**✅ 与 §468 的"`p == storage.size()` 是唯一的『完全理解』证明"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **`p == storage.size()` ⇒ 完全理解**
§482  **`consumed 22940 of 22940 bytes EXACT` ⇒ 完全理解**
⇒ **⇒ 两次"一个**恰好用尽【是【一个**可判定的正确性**"**
```

**✅ ⭐⭐⭐ **"一个恰好用尽是唯一的可判定的正确性"两例**。

**⚠ 而"§49 有那个解析器可用而从未跑它**"**⇒ **一个**方法论**的缺陷**。**

**⇒ 十层**：
```text
§49 【有**那个工具**】⇒ **⇒ 而【没有**用它**
⇒ **⇒ 所以【那个结论【是【从【一个**形状的**推断**【来的，不是【从【一个**测量的**验证**】
```

**✅ ⭐⭐⭐ **"那个结论是从一个形状的推断来的，不是从一个测量的验证"** —— 与 §468 的"没有见证的值故意缺席"**同族**（**第五次"一个**无测量的结论**"**）。

**✅ 而"`isMe` 的 bit 偏移【也被【两个解码器**一致**"**⇒ **一个**极强的**验证**。**

**⇒ 三层**：
```text
`isMe` ⇒ **`bit 0 of byte 157`**（**`offset table` 的条目 `1256`**）
⇒ **⇒ 而 `1256 >> 3 = 157`** ✓ **`1256 & 7 = 0`** ✓
⇒ **⇒ 所以【一个 `bit` 偏移【是【一个**字节偏移 × 8 + 位**"**
```

**✅ ⭐⭐⭐ **"一个 bit 偏移是一个字节偏移 × 8 + 位"** —— 一个**精确的编码**。

**✅ 与 §470 的 `0x2FD6 = 12246`**——**同族**（**第五次"一个**数的可验证来源**"**）。

## 三、**`27` 列而不是 `26`**（本组第二重要）

### 3.1 那段

```cpp
// THE ONE REAL DIFFERENCE: this build's row block has 27 columns, not 26. The extra
// one is `damage`, at byte 15071 with a per-row stride of 4, so it lives outside the
// row the way dw_userID_hi/lo (9626/9630, stride 8), netcafe_privileges (9426) and
// qq_membership (9430) already do. It is an OLfinal-only column and nothing here
// writes it.
```

### 3.2 二十四层

```text
1. **这个 build 的行块【有 `27` 列，不是 `26`**】
2. ⇒ **⇒ 而那多出来的一个【是 `damage`**】
3. ⇒ **⇒ 在【字节 `15071`**【每行步长 `4`**】
4. ⇒ **⇒ 所以【它【住在【那个行【之外**】
5. ⇒ **⇒ 就像 `dw_userID_hi/lo`（`9626`/`9630`，步长 `8`**）**
6. ⇒ **⇒ 而 `netcafe_privileges`（`9426`）与 `qq_membership`（`9430`**）**
7. ⇒ **⇒ 而【它【是一个 OLfinal 专属**的列**】⇒ **⇒ 而【这里【没有【任何东西【写它**】
```

### 3.3 ⭐⭐⭐ **"那多出来的一个住在那个行之外，就像 dw_userID_hi/lo 已经那样"**

**✅ 与 §482 二 的"那个行仍然逐字节相同"**——**完全闭合** ✓

**⇒ 三层**：
```text
那个行（`198` 字节，`21` 个内联字段）⇒ **逐字节相同**
那 `6` 个外置列（`damage` / `userId hi` / `userId lo` / `netcafe` / `qq` / ...）⇒ **各自**一个步长**
⇒ **⇒ 所以【"27 列"【是一个**逻辑**的计数，不是【一个**物理**的布局**
```

**✅ ⭐⭐⭐ **"'27 列'是一个逻辑的计数，不是一个物理的布局"** —— 一个**极精确的区分**。

**✅ 与 §470 的"那个网络字段表是按类型分组而不是按偏移排序"**——**同族**（**第六次"一个**逻辑结构【与【一个**物理布局**"**）。

**⚠ 而 `15071` 的位置**⇒ **一个**远在行块之外**的地址**。**

**⇒ 独立核算**：
```text
行块 ⇒ **`67 + 198 × 19 = 67 + 3762 = 3829`**（**`19` 行的结束**）
⇒ **⇒ 而 `15071 > 3829`**】⇒ **⇒ 所以【那个 `damage` 列【确实**远在**外面**
```

**✅ ⭐⭐⭐ **"行块结束在 3829 而 damage 在 15071 —— 远在外面"** —— 一个**精确的算术**。

**⚠ 而 `SvScoreboardRowCount`**⇒ **`19`？**（**`arrays 19`**）**。**

**⇒ 三层**：
```text
注释 ⇒ **"aarScoreboard is indexedArray[19]"**
⇒ **⇒ 所以【`SvScoreboardRowCount = 19`**】
⇒ **⇒ 而【那个行块【占 `19 × 198 = 3762` 字节**】
```

**✅ ⭐⭐ **"19 行占 3762 字节"**。

### 3.4 而**`RowBase = 67` 与那个 `FieldAssists = 0 // 67` 的对应**

**⇒ 十层**：
```text
`RowBase = 67`
而【`FieldAssists = 0` 【注释说 "`// 67`"**】⇒ **⇒ 所以【那个注释【是【绝对**偏移**】
⇒ **⇒ 而【`FieldClan = 5` 【注释 "`// 72`"**】⇒ **⇒ `67 + 5 = 72`** ✓
```

**✅ ⭐⭐⭐ **"那个注释是绝对偏移"** —— 而**`21` 个字段【每个【都有一个**绝对**的注释**。**

**⇒ 独立验证几个**：
```text
`FieldAssists  0  // 67`   ⇒ `67 + 0  = 67`  ✓
`FieldClan     5  // 72`   ⇒ `67 + 5  = 72`  ✓
`FieldDeaths  70  // 137`  ⇒ `67 + 70 = 137` ✓
`FieldIsMe    90  // 157`  ⇒ `67 + 90 = 157` ✓
`FieldKills   91  // 158`  ⇒ `67 + 91 = 158` ✓
`FieldName    99  // 166`  ⇒ `67 + 99 = 166` ✓
`FieldObjectives 164 // 231` ⇒ `67 + 164 = 231` ✓
`FieldXp     194  // 261`  ⇒ `67 + 194 = 261` ✓
⇒ **⇒ 八个全部精确** ✓
```

**✅ ⭐⭐⭐ **"八个全部精确"** —— 一个**完整的算术闭合**。

**⚠ 而 `FieldDeaths = 70` 与 `FieldDowns = 74`**⇒ **步长 `4`** ✓（`int32`）。

**⇒ 三层**：
```text
`70 / 74 / 78 / 82 / 86` ⇒ **`5` 个连续的 `int32`**（deaths/downs/gp/headshots/hits**）
`86 → 90`（isMe 的位）⇒ **`4`**
`90 → 91`（kills）⇒ **`1`**（**isMe 【只占一个字节**）
⇒ **⇒ 所以【那个 `isMe` 【是【一个**字节**里的**一个位**】而【其余【是 `int32`**
```

**✅ ⭐⭐⭐ **"isMe 是一个字节里的一个位，而其余是 int32"** —— 一个**精确的布局**。

**✅ 而 `FieldRank = 172 // 239` 与 `FieldTeam = 193 // 260`**⇒ **两个**`byte`** 字段**。**

**⇒ 十层**：
```text
`FieldRank` ⇒ **`byte`**（**`// 239, byte`**）
`FieldTeam` ⇒ **`byte`**（**`// 260, byte`**）
⇒ **⇒ 所以【`21` 个字段里【有两个【是**单字节**】
```

**✅ ⭐⭐⭐ **"21 个字段里有两个是单字节"**。

## 四、**三段 run 与"每次更新 67 字节而不是 198"**（本组第三重要）

### 4.1 三段

```text
RunOne    = [FieldAssists,     FieldClan)       = [0,  5)    ⇒  5 字节
RunTwo    = [FieldDeaths,      FieldName)       = [70, 99)   ⇒ 29 字节
RunThree  = [FieldObjectives,  RowStride)       = [164,198)  ⇒ 34 字节
                                                    ─────────────────────
                                                    合计 68 字节
```

**⇒ 独立验证 `5 + 29 + 34 = 68`** ✓（而注释说 **`67` 字节**）。

**⚠ 一个 1 字节的差** ⇒ **可能【那个 `RunOne` 的结束【是 `FieldClan`（`5`）⇒ `5 - 0 = 5`**】**；`RunTwo` ⇒ `99 - 70 = 29`；`RunThree` ⇒ `198 - 164 = 34` ⇒ **`68`**。**

**⇒ 十层**：
```text
注释 ⇒ **"leaving them alone keeps the update to 67 bytes a row instead of 198"**
我算 ⇒ **`68`**
⇒ **⇒ 所以【那个 `67` 【与【`68` 【差 `1`】⇒ **⇒ 而【那【可能【是【一个**四舍五入**或【一个**排他的上界**】
```

**⚠ 标注为：一个 1 字节的算术差**（`68` vs `67`），**不影响正确性**（**那三段显然是 `[Begin, End)` 的半开区间**）。

### 4.2 ⭐⭐⭐ **"留着它们不动让那个更新是每行 67 字节而不是 198"**

**✅ 与 §470 的"那个指纹的成员资格由『它变不变』与『重建要不要读它』两个条件决定"**——**同族** ✓

**⇒ 三层**：
```text
`clan` 与 `name`（两个 `char[65]`）⇒ **客户端【自己填**】（**从活的 client info**）
⇒ **⇒ 所以【不写它们【只是**浪费的减少**，不是【正确性**的需要**】**
⇒ **⇒ 而【那【让【一个行【从 `198` 降到 `68`**】⇒ **⇒ `2.9` 倍**
```

**✅ ⭐⭐⭐ **"从 198 降到 68 ⇒ 2.9 倍"** —— 一个**可量化的压缩**。

**✅ 与 §472 的"记分板指纹 `1185 → ~1029` B"**——**同族**（**第五次"一个**字节的量化**"**）。

**⚠ 而"`clobbering them would only be wasteful rather than wrong`"**⇒ **一个**精确的**定性**。**

**⇒ 三层**：
```text
若【写它们**】⇒ **⇒ 不是**错**，只是**浪费**（**+ `130` 字节/行**）
若【不写**】⇒ **⇒ `68` 字节**】
⇒ **⇒ 所以【那个选择【是【一个**性能**的选择，不是【一个**正确性**的选择**
```

**✅ ⭐⭐⭐ **"那是一个性能的选择，不是一个正确性的选择"** —— 一个**极诚实的定性**。

## 五、**`K … J` 契约与"每条都写 'J' 的代价"**（本组第四重要）

### 5.1 那段

```cpp
// OLMOD(scoreboard-rebuild-every-command, 20261015-22310): EVERY
// command rebuilds, not just the last.
//
// A live cha session on 2026-10-15 handed this to us: the client's
// cached row table (cg+0xBEB70, stride 0x40, 19 rows) and its profile
// document both came back EMPTY in the row band while the match-level
// fields of the SAME patch held values. A batch of 12 rows is 1185
// bytes against a 0x3FC payload cap, so it always splits into two
// commands; only the second carried 'J', and only what the J command
// loaded was ever rebuilt.
//
// ★ 28100 刀H（三轮）：**恢复 K…J 契约**（hpp 的原设计 + 老外参考实现 +
//   本仓测试断言的 `firstVerb=K lastVerb=J`）。
//
// 票 22310 把"每条都写 'J'"当成修复，理由是 10-15 那次实测里"只有 J 装载的
// 内容被重建"。但代价是**每装载一条就触发一次重建**：一个 12 行的批次必分
// 两条命令，客户端在第一条落地后立刻重建一次 —— 那一刻 profile 里只有前
// 半批，AAR 行带是空的；客户端从这张半成品表里取"我是哪队"
// （`0x6B18EF mov eax,[eax+0x10]`），于是 `myTeam` 恒为 0，名字色 / 小地图 /
// 敌我标识全部失准。甲方 2026-10-16 的实测结论正是"我认为无改善"。
//
// 老外的参考实现只让**最后一条**命令重建（`commands.back()[0] = 'J'`），
// 而它们的场景（zm/小规模）payload 天然只有一条命令，所以同一个缺陷在那边
// 看不到 —— 这解释了甲方观察到的"老外僵尸模式队伍表现正常"。
```

### 5.2 二十四层

```text
1. **一次活的 cha 会期（`2026-10-15`）【交出**了这件事**】
2. ⇒ **⇒ 客户端的缓存行表（`cg+0xBEB70`，步长 `0x40`，`19` 行**）**
3. ⇒ **⇒ 与【它的 profile 文档【两个【都【在那**行带**里【回到**空**】
4. ⇒ **⇒ 而【同一个 patch 的【比赛级**字段【持有**值**】
5. ⇒ **⇒ 一批 `12` 行【是 `1185` 字节【对【一个 `0x3FC` 的载荷上限**】
6. ⇒ **⇒ 所以【它【总是【分裂成【两条**命令**】
7. ⇒ **⇒ 而【只有第二条【携带 'J'**】⇒ **⇒ 而【只有【那个 J 命令【装载的**东西【被重建**】
8. ⇒ **⇒ 修法（票 22310）：每条都写 'J'**】
9. ⇒ **⚠ 而【代价【是【每装载一条【就【触发一次重建**】
10. ⇒ **⇒ 一个 `12` 行的批次【必分两条命令**】
11. ⇒ **⇒ 而【客户端【在【第一条落地后【立刻【重建**一次**】
12. ⇒ **⇒ 那一刻【profile 里【只有**前半批**】⇒ **⇒ 而 AAR 行带【是【空**的**】
13. ⇒ **⇒ 而【客户端【从【这张半成品表**里【取"**我是哪队**"**】（`0x6B18EF mov eax,[eax+0x10]`**）**
14. ⇒ **⇒ 于是 `myTeam` 【恒为 `0`**】⇒ **⇒ 而【名字色 / 小地图 / 敌我标识【全部**失准**】
15. ⇒ **⇒ 而甲方 `2026-10-16` 的实测结论【正是【"我认为无改善**"**】
```

### 5.3 ⭐⭐⭐ **"客户端在第一条落地后立刻重建一次 —— 那一刻 profile 里只有前半批"**

**✅ 这是本报告里**最精确的一条"**一个修复【造成【一个【更隐蔽的**错误**"**。**

**✅ 与 §479 的"刀CI 的 BFS 落在每帧路径上"**——**完全同族** ✓

**⇒ 三层**：
```text
症状 A ⇒ **AAR 行带【空**】
修复 ⇒ **每条都写 'J'**（**⇒ 每条装载都重建**）
症状 B ⇒ **`myTeam` 恒为 `0`**（**因为【第一次重建【在半批上**）
⇒ **⇒ 所以【那个修复【制造【一个【更隐蔽的**症状**】
```

**✅ ⭐⭐⭐ **"那个修复制造一个更隐蔽的症状"** —— 而**甲方【说【"我认为无改善"**（**症状变了，但【仍然**坏**）**。**

**✅ 与 §475 的"关闭是幂等性的唯一保证"**——**不同**（那是一个**正确的修法**）**。**

**⚠ 而"老外的参考实现只让最后一条命令重建，而它们的场景（zm/小规模）payload 天然只有一条命令"**⇒ **一个**极精彩的**归因**。**

**⇒ 十层**：
```text
老外的实现 ⇒ **`commands.back()[0] = 'J'`**（**与这里【一致**）
而【它们的场景【只有一条命令**】⇒ **⇒ 所以【同一个缺陷【在那边【看不到**】
⇒ **⇒ 而那【解释了【甲方观察到的【"老外僵尸模式队伍表现正常**"**
```

**✅ ⭐⭐⭐ **"那解释了甲方观察到的『老外僵尸模式队伍表现正常』"** —— 一个**极强的解释**。

**✅ 与 §474 的"两个源共享零代码"**——**同族**（**第四次的"一个**独立源【的解释力**"**）。

### 5.4 而**最终修法：把常规更新压进单条命令**

```cpp
// 本轮同时把常规更新压进单条命令（见上文的 roster / match-level 指纹缓存）：
// 单条命令时"最后一条带 J"就是"这一条带 J"，装载与重建各发生一次，22310 的
// 观察与 hpp 的契约**同时满足**，不再互相排斥。
```

**⇒ 十层**：
```text
若【多条命令**】⇒ **⇒ "每条写 J" 与 "只最后写 J" 【互斥**】
若【单条命令**】⇒ **⇒ 两者**相同**
⇒ **⇒ 所以【那个修法【让【两个**要求【同时满足**】
```

**✅ ⭐⭐⭐ **"那个修法让两个要求同时满足"** —— 一个**极优雅的解**。

**✅ 与 §472 的"记分板指纹 `1185 → ~1029`（压进单条命令）"**——**完全闭合** ✓

**⇒ 三层**：
```text
§472  **`1185 → ~1029` B，不再分两条命令**
§482  **"单条命令时『最后一条带 J』就是『这一条带 J』"**
⇒ **⇒ 所以【那个指纹压缩【不只是【一个**性能**优化【也是【一个**正确性**修复**】
```

**✅ ⭐⭐⭐ **"那个指纹压缩不只是一个性能优化，也是一个正确性修复"** —— 一个**跨报告的闭合**。

## 六、**`0x3FE` 的上限与"error 1106"**

### 6.1 那段

```cpp
// On 2026-10-15 a build that raised SvProfilePatchMaximumPayload past
// this bound sent one 1184-byte command; the client cannot hold more
// than 1023 characters of `verb + payload` (see the header's own note
// on sub_46E3B0 / sub_4737E0), and the match died with error 1106.
// The cap below is the hard ceiling the header already documents --
// 0x3FE of payload, one under 1023 with the verb byte.
constexpr std::size_t ClientReliablePayloadCeiling = 0x3FE;
```

### 6.2 二十四层

```text
1. **一个 build 【把 `SvProfilePatchMaximumPayload` 抬到【超过**这个界**
2. ⇒ **⇒ 而【它【发了【一条 `1184` 字节的命令**】
3. ⇒ **⇒ 而【客户端【不能【持有【超过 `1023` 个字符的 `verb + payload`**】
4. ⇒ **⇒ 所以【那个比赛【死【于**错误 `1106`**】
5. ⇒ **⇒ 而那个上限【是【`0x3FE`（`1022`）⇒ 【比 `1023` 少一个**】⇒ **⇒ 因为【那个 `verb` 字节**】
```

### 6.3 ⭐⭐⭐ **"`1184` 对 `1022` —— 超了 `162` 字节，而那个比赛死于 error 1106"**

**✅ 与 §472 的"`SvProfilePatchMaximumPayload` 与 `0x3FE` 的关系"**——**完全闭合** ✓

**⇒ 三层**：
```text
§433  **`0x3FC → 0x3FE` 的两字节修正使 `1021` 字节的单命令可用**
§472  **`1029` B 与 `0x3FE` 的关系（我标为"若 1022 是载荷上限则一致"）** ← **现在闭合**
§482  **`0x3FE of payload, one under 1023 with the verb byte`**
⇒ **⇒ 所以【`1022` 是【载荷**上限**】⇒ **⇒ 而 §472 的 `1029` 【含【命令头**】⇒ **⇒ 我的解释【正确** ✓
```

**✅ ⭐⭐⭐ **"我的解释正确（§472 的 §1029 含命令头）"** —— 一个**跨报告的自我验证**。

**⚠ 而"`1184` 字节【超了 `162`**"⇒ **`1184 - 1022 = 162`** ✓

**⇒ 独立验证**：
```text
`1184 - 1022 = 162`
而【之前【那个 `1185` B 的 `12` 行批次**】⇒ **⇒ 所以【那个 `1184` 【是【那一批**减一
```

**✅ ⭐⭐⭐ **"1184 是那一批减一"**。

### 6.4 而`std::erase_if` 的"丢弃而不是发送"

**⇒ 十层**：
```cpp
std::erase_if(commands, [](const std::vector<std::uint8_t> &command) {
    return command.size() > ClientReliablePayloadCeiling;
});
```
```text
1. **丢弃【而不是【发送**】
2. ⇒ **⇒ 而注释说**："**丢弃那个超大的命令【是【一个**权衡【的保守**那一半：替代品【是【一个**失同步**"**
3. ⇒ **⇒ 所以【丢弃【比【一个 desync**【好**
```

**✅ ⭐⭐⭐ **"丢弃比一个 desync 好"** —— 与 §477 的"不做事比做错事好"**同族**（**第六次**）。

**✅ 而"那行 trace 命名它，所以那个丢弃【从不【是【静默**的"**⇒ **一个**正确的**诊断**。**

**⇒ 三层**：
```text
`SV_ScoreboardTraceLine` ⇒ **`firstVerb=` / `lastVerb=` / `outcome=`**
⇒ **⇒ 所以【一个丢弃【会【在【`outcome=` 里【可见**】
```

**✅ ⭐⭐⭐ **"一个丢弃会在 outcome 里可见"** —— 与 §479 的"『静默』是那个致命的属性"**相反**（**正确**）。

## 七、**助攻的 `serverTime` 窗口与 `8` 槽账本**

### 7.1 三段

```cpp
// `serverTime - contribution.serverTime` without the guard wraps a
// negative stamp into a value inside the window, which would credit
// an assist from damage that has not happened yet.
if (contribution.serverTime > serverTime) continue;
if (serverTime - contribution.serverTime > SvAssistWindowMilliseconds) continue;
```

```cpp
std::size_t SvAssistLedgerRecord(…)
{
    …
    if (end != ledger.end()) { *end = …; return used + 1; }
    const auto oldest = std::min_element(…);
    *oldest = …;
    return used;
}
```

### 7.2 二十四层

```text
1. **一个未来**的时间戳【被【显式**拒绝**】（**否则【那个无符号减法【回绕【成一个【在窗口内**的值**）**
2. ⇒ **⇒ 而【窗口【是 `SvAssistWindowMilliseconds`**】
3. ⇒ **⇒ 而【那个账本【是【一个**固定大小的环**】⇒ **⇒ 满时【替换【最旧**的**
```

### 7.3 ⭐⭐⭐ **"一个负的时间戳会回绕成一个在窗口内的值，那会记功给一个还有发生的伤害"**

**✅ 与 §464 的"`old > current + 64 ⇒ -= 256`"**、§469 的"`static_cast<std::int32_t>(serverTime - wakeServerTime)`"**——**同族**（**第四次"一个**无符号减法【的回绕**"**）。

**⇒ 三层**：
```text
§464  **一个 `8` 位游标的回绕【用 `-= 256` 修复**】
§469  **一个计时器【用【有符号 `int32` 比较**】
§482  **一个助攻【用【一个**显式的**未来检查**】
⇒ **⇒ 三次"一个**回绕【被【一个**显式的**守卫**"**
```

**✅ ⭐⭐⭐ **"一个回绕被一个显式的守卫"三例**。

**⚠ 而"那个账本是固定大小的，满时替换最旧的"**⇒ **一个**LRU**（**按时间**）。**

**⇒ 十层**：
```text
未满 ⇒ **追加**（`*end = ...; return used + 1`）
已满 ⇒ **替换【最旧的**】（`min_element` by `serverTime`）
⇒ **⇒ 所以【一个**固定**的账本【持有【最近的 `N` 个**贡献者**
```

**✅ ⭐⭐⭐ **"一个固定的账本持有最近的 N 个贡献者"**。

**✅ 而"`attacker` 已存在 ⇒ 更新它的 `serverTime`**"**⇒ **一个**刷新**。**

**⇒ 三层**：
```text
同一个 `attacker` ⇒ **更新 `serverTime`**（**⇒ 一个**滑动窗口**）
不同的 ⇒ **追加或替换**
⇒ **⇒ 所以【五条**路径**
```

**✅ ⭐⭐⭐ **"五条路径"** —— 而**那【是【一个**完整的**贡献账本**。

### 7.4 而`SV_GpForXp` 的 `1'000'000` 上限

```cpp
std::int32_t SV_GpForXp(const std::int32_t xpDelta) noexcept
{
    if (xpDelta <= 0 || SvGpPerXp <= 0) return 0;
    const auto scaled = static_cast<std::int64_t>(xpDelta) * SvGpPerXp;
    return static_cast<std::int32_t>(std::min<std::int64_t>(scaled, 1'000'000));
}
```

**⇒ 十层**：
```text
1. **`int64` 的乘法 ⇒ 防止【`int32` 溢出**】
2. ⇒ **⇒ 而 `min(…, 1'000'000)` ⇒ 一个**上限**】
3. ⇒ **⇒ 而【`xpDelta <= 0` ⇒ 返回 `0`**】（**不是【一个负数**）
```

**✅ ⭐⭐⭐ **"`int64` 的乘法防止溢出，而 `min` 是一个上限"** —— 与 §476 的"`uint64` 相加 + `min(0xFFFE, …)` 饱和"**同族**（**第五次"一个**更宽的中间类型【防止溢出**"**）。

**⚠ 而那个 `1'000'000` 上限**⇒ **一个**可质疑的**魔法数**（**但【它【是【一个**安全阀**）**。**

**⇒ 三层**：
```text
若【没有上限**】⇒ **⇒ 一个**巨大的 XP**【产生【一个【荒谬的** GP**】
有上限 ⇒ **⇒ 一个**有界的**奖励**
⇒ **⇒ 所以【那个上限【是【正确的**】
```

**✅ ⭐⭐ **"那个上限是正确的"**。

## 八、关键结论

1. **⭐⭐⭐ "§49 得出了相反的结论，而那个推断是错的：同一个版本 `233`，不同的 `formatChecksum`（`0x4A6CC345` 对 `0xE32D50D6`），不同的 enum 字段集，**因此一个不同的行布局** —— 而那个 def 在每一个被测量过的地方**确实**不同（`8` 结构对 `4`、`40` 索引数组对 `26`、大小 `15767` 对 `14426`、偏移表 `3927` 条对 `3414`），**而那个 `aarScoreboard` 的行仍然逐字节相同**，包括全部五个位寻址字段"`** ⇒ **"'整体不同'不蕴含'每一部分不同'"`** —— 第三次"一个早期的结论被一个更精确的读法推翻"（与 §471/§476 同族）。
2. **⭐⭐⭐ "两次确认，由共享零代码的解码器：`parse-structureddatadef.py` 报告 `consumed 22940 of 22940 bytes EXACT`，那是一个真实的检查，因为那个流没有对齐填充，而**一个错的记录布局不能到达最后一个字节**"`** ⇒ **"§49 有那个解析器可用而从未在这个 build 的 def 上跑它"`** —— 与 §468 的 `p == storage.size()` 同族（**"一个恰好用尽是唯一的可判定的正确性"**），而**"那个结论是从一个形状的推断来的，不是从一个测量的验证"**。
3. **⭐⭐⭐ `isMe` 的 bit 偏移：`offset table` 的条目 `1256` ⇒ 独立验证 `1256 >> 3 = 157`（字节）且 `1256 & 7 = 0`（位 `0`）** ⇒ **"一个 bit 偏移是一个字节偏移 × 8 + 位"**。
4. **⭐⭐⭐ "这个 build 的行块有 `27` 列，不是 `26`；多出来的是 `damage`，在字节 `15071`、每行步长 `4`，所以它住在那个行**之外**，就像 `dw_userID_hi/lo`（`9626`/`9630`，步长 `8`）、`netcafe_privileges`（`9426`）、`qq_membership`（`9430`）已经那样；它是一个 OLfinal 专属的列，而这里没有东西写它"`** ⇒ **"'27 列'是一个逻辑的计数，不是一个物理的布局"`**；**独立算得行块结束在 `67 + 198×19 = 3829`，而 `damage` 在 `15071` —— 远在外面**。
5. **⭐⭐⭐ `RowBase = 67` 与 `21` 个字段注释的绝对偏移全部精确**（独立验证八个：`0→67`、`5→72`、`70→137`、`90→157`、`91→158`、`99→166`、`164→231`、`194→261`）；而 **`isMe` 是一个字节里的一个位，`rank` 与 `team` 是两个单字节，其余是 `int32`**。
6. **⭐⭐⭐ 三段 run 的"留着 `clan` 与 `name` 不动让那个更新是每行 67 字节而不是 198"`** ⇒ **"那是一个性能的选择，不是一个正确性的选择"`**（"clobbering them would only be wasteful rather than wrong"）⇒ **`2.9` 倍的压缩**；而我算三段是 `68` 字节（`5 + 29 + 34`），与注释的 `67` 差 `1`（半开区间，不影响正确性）。
7. **⭐⭐⭐ `K … J` 契约的完整病历**：**一次活的 cha 会期（`2026-10-15`）里客户端的缓存行表（`cg+0xBEB70`，步长 `0x40`，`19` 行）与 profile 文档两个都在行带里回到空，而同一个 patch 的比赛级字段持有值；一批 `12` 行是 `1185` 字节对 `0x3FC` 的上限 ⇒ 总是分裂成两条命令，只有第二条带 `'J'`** ⇒ 修法（票 `22310`）**每条都写 `'J'`** ⇒ **代价："每装载一条就触发一次重建；客户端在第一条落地后立刻重建一次 —— 那一刻 profile 里只有前半批，AAR 行带是空的；客户端从这张半成品表里取『我是哪队』（`0x6B18EF mov eax,[eax+0x10]`），于是 `myTeam` 恒为 `0`，名字色 / 小地图 / 敌我标识全部失准"`** ⇒ 甲方 `2026-10-16` 的结论**"我认为无改善"** ⇒ **"那个修复制造一个更隐蔽的症状"**（与 §479 的刀CI 同族）。
8. **⭐⭐⭐ "老外的参考实现只让最后一条命令重建（`commands.back()[0] = 'J'`），而它们的场景（zm/小规模）payload 天然只有一条命令，所以同一个缺陷在那边看不到 —— 这解释了甲方观察到的『老外僵尸模式队伍表现正常』"`** —— 一个**极强的归因**。
9. **⭐⭐⭐ 最终修法：把常规更新压进单条命令 ⇒ "单条命令时『最后一条带 J』就是『这一条带 J』，装载与重建各发生一次，22310 的观察与 hpp 的契约同时满足，不再互相排斥"`** ⇒ **"那个指纹压缩不只是一个性能优化，也是一个正确性修复"** —— 与 §472 的 `1185 → ~1029` **完整闭合**。
10. **⭐⭐⭐ `0x3FE` 与 error `1106`**：**一个抬高了上限的 build 发了 `1184` 字节的命令，而客户端不能持有超过 `1023` 个字符的 `verb + payload` ⇒ 那个比赛死于 error `1106`** ⇒ **"`0x3FE` 的载荷，比 `1023` 少一个（那个 `verb` 字节）"`** ⇒ **独立验证 `1184 − 1022 = 162`**。
    **✅ 两个不同的常量，本轮核实**（`.hpp:66` 与 `.cpp` 的局部）：
    ```text
    SvProfilePatchMaximumPayload    = 0x3FC = 1020   ← 打包时的目标（每帧预算）
    ClientReliablePayloadCeiling    = 0x3FE = 1022   ← 硬天花板（超了就丢弃）
    ```
    ⇒ **`1020 + 5`（run 头）+ `1`（verb）`= 1026 > 1022`** ⇒ **⇒ 所以【那个 `0x3FC` 的打包预算【本身就【保证【一条命令【不会【超天花板**，而那个 `erase_if` 是**第二道保险**。
    **⚠ 但 `1020 + 5 + 1 = 1026` 已经超过 `1023`** ⇒ 若一个 run 恰好在 `1020` 边界上闭合，`current.size()` 可达 `1020`，而它**含** verb ⇒ **实际载荷 `1019` ⇒ `1019 + 1 = 1020 ≤ 1023` ✓**（`current` 从 `{verb}` 起，所以 `current.size()` 是 **verb + payload**）⇒ **正确**。
    而 **`.hpp:26-27` 明说"NOTHING BELOW HAS BEEN CHECKED ON THE HOST"** ⇒ 那段 `sub_C1BF70` 的 rebase 分析（`+0x6A0000`，3.3.3.3 的 `sub_57BF70`）**未被宿主验证**，且 **3.3.3.3 的两个 profile 槽立即数 `0x91B8` 与 `0x90` 在 out.exe 里都不出现** ⇒ **"那个 profile 记录移动了，而那个对应物必须按形状找，不是按重定基这个地址"**。
    **✅ §472 的 `1029` 与这里的关系现在完全闭合**：`1029 > 1022` ⇒ **那个 `1029` 必然是一个含 verb 的总长**（`1029` 总长 ⇒ 载荷 `1028 > 1022` ⇒ **会被 `erase_if` 丢弃**）⇒ 所以 §472 的 `~1029 B` 若成立，它一定指的是**指纹压缩后仍需要两条命令**的某一批，或者那个 `~` 是近似（真实值 `< 1022`）。**标注为：§472 的 `~1029` 与这里的 `1022` 天花板**可能**不一致，需要看那一批的实际行数。**
11. **⭐⭐⭐ `std::erase_if` 丢弃超大命令 ⇒ "丢弃那个超大的命令是一个权衡的保守那一半：替代品是一个 desync"`** —— 与 §477 的"不做事比做错事好"同族；而 **`SV_ScoreboardTraceLine` 的 `outcome=` 使那个丢弃从不静默**（与 §479 的"静默是那个致命的属性"相反）。
12. **⭐⭐⭐ 助攻的三级守卫**（拒绝未来的 `serverTime`：**"一个负的时间戳会回绕成一个在窗口内的值，那会记功给一个还有发生的伤害"`** / 窗口 / 去重）⇒ 第四次"一个回绕被一个显式的守卫"（与 §464/§469 同族）；而**那个账本是一个固定大小的、满时替换最旧的 LRU**（**五条路径**：拒绝 killer / 拒绝未来 / 拒绝过期 / 刷新已有 / 追加或替换最旧）。
13. **⭐⭐ `SV_GpForXp` 用 `int64` 相乘 + `min(…, 1'000'000)`** ⇒ 第五次"一个更宽的中间类型防止溢出"（与 §476 同族）。

## 九、`sv_scoreboard_mp.cpp` 全文件总览

**`444` 行。**

**`4` 个基址/步长常量**：`RowBase = 67` / `RowStride = 198` / `OffsetTeamScores = 9782` / `OffsetUserIds = 9626` + `UserIdStride = 8`。

**`21` 个行内字段**（偏移 / 绝对）：
```text
  0/ 67 assists        5/ 72 clan(char[65])   70/137 deaths
 74/141 downs         78/145 gp               82/149 headshots
 86/153 hits          90/157 isMe(bit 0)      91/158 kills
 95/162 killstreak    99/166 name(char[65])  164/231 objectives
168/235 ping        172/239 rank(byte)      173/240 revives
177/244 score       181/248 shots           185/252 skill
189/256 statusIcon  193/260 team(byte)      194/261 xp
```

**`3` 个比赛级字段**：`roundNumber = 59` / `scoreLimit = 63` / `teamScores = 9782`。

**`3` 段 run**：`[0,5)` / `[70,99)` / `[164,198)`。

**`6` 个函数**：`writeInt32` / `writeUInt32` / `SV_BuildScoreboardProfilePatches` / `SV_FrameProfilePatchCommands` / `SV_ScoreboardTraceLine` / `SvAssistAwardees` / `SvAssistLedgerRecord` / `SV_GpForXp`。

**`12` 个测量锚点**：
```text
1649370 def: 8 structs / 40 indexed arrays / size 15767 / offset table 3927
3.3.3.3  def: 4 structs / 26 indexed arrays / size 14426 / offset table 3414
parse-structureddatadef.py: consumed 22940 of 22940 bytes EXACT
isMe 的 offset table 条目 1256 ⇒ byte 157 bit 0
damage 在 15071（OLfinal 专属，stride 4）
cha 会期（2026-10-15）：12 行 = 1185 B / 0x3FC 上限 / cg+0xBEB70 stride 0x40 19 行
0x6B18EF mov eax,[eax+0x10]（客户端取 myTeam）
错误 1106（1184 字节的命令）
甲方 2026-10-16："我认为无改善"
```

## 十、未闭合点

- `SvAssistLedgerCapacity` 的确切值（`.hpp` 里未直接命名）。
- §472 的 `~1029 B` 与这里 `1022` 天花板的关系（那一批的实际行数）。
- out.exe 侧那个 profile-patch **读器**的对应物（`.hpp:26` 明说未验证，`0x91B8`/`0x90` 两个立即数在 out.exe 里都不出现）。
- 下一个文件：`sv_client_spawn_mp.cpp`（`21,706` 字节）。

**已核实（本轮，`.hpp`）**：
```text
SvProfilePatchLoadAndRebuild = 'J'              (.hpp:35)
SvProfilePatchLoadOnly       = 'K'              (.hpp:36)
SvScoreboardRowCount         = 19               (.hpp:41)
SvProfilePatchMaximumPayload = 0x3FC = 1020     (.hpp:66)
SvAssistWindowMilliseconds   = 10'000           (.hpp:212)
SvGpPerXp                    = 1                (.hpp:265)
```

**两个新发现**：

1. **`'J'` 与 `'K'` 的语义**（`.hpp:34`）：**"`'J'` loads into profile slot 0 and then rebuilds the scoreboard; `'K'` loads without rebuilding, which is what makes a multi-command update possible"** ⇒ **那正是 §482 五 的 `K … J` 契约的名字来源**。
2. **`CG_InitScoreboardFromProfile` 遍历 `aarScoreboard[0..18]` 并把循环计数同时当作 profile 索引与该行的客户端号** ⇒ **"所以一个行直接由客户端号寻址"`** ⇒ **那解释了 `rowBase = 67 + 198 * entry.clientNum` 为什么直接用 `clientNum`**（不是行序）。
3. **`SvGpPerXp = 1`** ⇒ **GP 与 XP 是 `1:1`** ⇒ 那 `SV_GpForXp` 的 `1'000'000` 上限只有在 `xpDelta > 1,000,000` 时才生效（**一个不会发生的量**）⇒ **那个上限是一个纯安全阀**。
