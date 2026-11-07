# 318 · **索引 29 在两个 build 不是同一个字段 ⇒ 所有尸体隐形**、`4.29e9` 的下溢、`0xFFFFFF` 是 24 位

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 1000–1200 行。

## 二、**尸体索引 29 的跨 build 差异**（本组最重要的一段）

### 2.1 那段完整的因果

```php
// CODREF(player_die): index 29 is NOT the same field in the two builds,
// and reading the demo's "idx29" as movementDir is what made every body
// invisible.
//
//     OLfinal corpse table 0x00DA4EF0: index 29 -> offset 0x54, bits 0
//         (0x00DA4F10 in OL.exe, which is what the TSV is named for)
//     3.3.3.3 corpse table 0x00C52E48: index 29 -> offset 0x5C, codec -8
//     3.3.3.3 corpse table 0x00C52E48: index 46 -> offset 0x54, bits 0
//
// So the demo's "every corpse spawn carries idx29 = 1" is a FULL FLOAT
// 1.0 at offset 0x54 - the DObj scale - not movementDir = 1. Porting it
// by index wrote a meaningless movementDir into 3.3.3.3 and left +0x54 at
// zero. BG_UpdatePlayerDObj 0x0040B700 then copies +0x54 into
// DObj_s::scale +0xC8 UNCONDITIONALLY (ida 0xAAB7E5 for an existing DObj,
// 0xAABAFB for a freshly created one - a4 is entityState_s*, a4[21] is
// +0x54, +200 is +0xC8), so the body is built at scale 0 and cannot be
// seen. A live probe measured exactly that: BG_UpdatePlayerDObj running
// every frame for corpse slots with the dead player's real model, and no
// visible body.
```

### 2.2 九层

```text
1. **索引 29 在两个 build 上【不是】同一个字段**
2. ⇒ 把 demo 的 `idx29` 读成 `movementDir` **就是让每一具身体隐形的**原因
3. ⇒ **OLfinal 的尸体表 `0x00DA4EF0`：索引 29 → 偏移 `0x54`，bits 0**
     （`0x00DA4F10` 在 OL.exe 里，而 TSV 是以它命名的）
4. ⇒ **3.3.3.3 的尸体表 `0x00C52E48`：索引 29 → 偏移 `0x5C`，codec `-8`**
5. ⇒ **3.3.3.3 的同一张表：索引 46 → 偏移 `0x54`，bits 0**
6. ⇒ 所以 demo 的"每一次尸体 spawn 都带 `idx29 = 1`"是**偏移 `0x54` 的一个【完整浮点 1.0】** —— **DObj 的 scale** —— 而**不是 `movementDir = 1`**
7. ⇒ **按索引移植把一个无意义的 `movementDir` 写进 3.3.3.3 而把 `+0x54` 留在零**
8. ⇒ **`BG_UpdatePlayerDObj 0x0040B700` 然后【无条件】把 `+0x54` 拷进 `DObj_s::scale +0xC8`**
9. ⇒ **所以身体以 scale 0 被构建而看不见**
```

### 2.3 而两个 `ida` 地址

```text
0xAAB7E5   已存在的 DObj
0xAABAFB   新建的 DObj
```

**⇒ 两条路径都是无条件拷贝。**

### 2.4 而 `a4[21]` 与 `+200` 的算术

**⇒ `a4[21]` = `+0x54`（因为 21 × 4 = 84 = 0x54）✓**

**⇒ `+200` = `+0xC8` ✓（200 = 0xC8）**

**✅ 算术闭合。**

### 2.5 而**活体探针测量的原文**

```text
"BG_UpdatePlayerDObj running every frame for corpse slots with the dead
 player's real model, and no visible body"
```

**✅ 三层**：

```text
1. `BG_UpdatePlayerDObj` **每帧对尸体槽运行**
2. ⇒ **带着死者真实的模型**
3. ⇒ **而没有可见的身体**
```

**⇒ 所以"引擎在做正确的事而结果是不可见的"。**

**✅ 与 §309 的"隐形玩家"**不同的原因**：**

```text
§309  玩家可见：`+0x150 <= 0` ⇒ `characterInfo+0x18` 空 ⇒ 活人不画而尸体通过
§318  尸体不可见：scale = 0 ⇒ DObj 建在 scale 0
```

**⚠ 两个**相反方向**的不可见！**

### 2.6 而 `OLfinal` 的 `movementDir` 是**索引 35** 而 demo **零次断言**

```php
// OLfinal's movementDir is index 35 and the demo asserts it ZERO times,
// so a retail corpse sends no movementDir at all. This writer therefore
// leaves it at the baseline and sends the scale instead.
constexpr std::uint32_t CorpseMovementDirField = 35;      // +0x05C -8
constexpr std::uint32_t CorpseScaleField = 29;            // +0x054 bits 0
```

**⇒ 三层**：

```text
1. OLfinal 的 `movementDir` 是**索引 35**
2. ⇒ demo **零次断言它**
3. ⇒ 所以**一个零售尸体根本不发 `movementDir`**
4. ⇒ 所以这个写入器**把它留在基线而发 scale**
```

**✅ 一个**正确的"不发"决策**。**

## 三、**`4.29e9` 的下溢**（本组第二重要）

### 3.1 那段完整的因果

```php
// CODDIFF(1649370): PORTED BY OFFSET. 3.3.3.3's {41, 40, 44} sit at
// +0x24/+0x28/+0x2C, and those offsets are indexes 43/42/46 here -- every
// ET_PLAYER trajectory index shifted by two. Every SCALAR sibling was
// ported (duration 42 -> 44, time 43 -> 45) and this ARRAY was not, so
// index 44 was claimed by BOTH the duration field and delta[2], and the
// write order ran 44, 45, then back to 44. writeSkippedFieldIndex computes
// `static_cast<std::uint32_t>(delta - 1)` on that, which underflows to
// ~4.29e9 and emits chunks of 7 until the writer overflows -- a desync and
// a hang, not a wrong value. An array initialiser is invisible to both
// port-netfield-indices.py and audit-duplicate-constants.py, which is how
// it survived every sweep.
```

### 3.2 八层

```text
1. **按偏移移植**：3.3.3.3 的 `{41, 40, 44}` 坐在 `+0x24/+0x28/+0x2C`
2. ⇒ 而那些偏移在这里是索引 **`43/42/46`** —— **每一个 ET_PLAYER 轨迹索引都移了两位**
3. ⇒ **每一个标量兄弟都移植了**（`duration 42 → 44`、`time 43 → 45`）**而这个【数组】没有**
4. ⇒ 所以**索引 44 被【两个】字段同时声称**：`duration` 与 `delta[2]`
5. ⇒ 而**写入顺序跑了 44、45、然后回到 44**
6. ⇒ `writeSkippedFieldIndex` 对它计算 `static_cast<uint32>(delta - 1)`
7. ⇒ **那下溢到 ~`4.29e9`** 而**发出 7 个位块直到写入器溢出**
8. ⇒ **一个失步与一个挂起，而不是一个错误的值**
```

### 3.3 而"**一个数组初始化器对两个工具都不可见**"

```text
port-netfield-indices.py
audit-duplicate-constants.py
```

**⇒ 三层**：

```text
1. 一个**数组初始化器**对这两个工具**都不可见**
2. ⇒ 所以**它挺过了每一次扫描**
3. ⇒ 因为工具只看**具名常量**而不看**初始化器里的字面量**
```

**✅ 这是一个**工具盲区**的重要发现。**

**⇒ 与 §305 的"`grep` 匹配不到非限定调用"同族**（第四次"工具盲区"）。

### 3.4 而 `4.29e9` 的算术

**⇒ `0xFFFFFFFF = 4,294,967,295 ≈ 4.29e9`。**

**⇒ 所以 `delta - 1` 其中 `delta == 0` ⇒ `0 - 1 = 0xFFFFFFFF`。**

**✅ 一个**无符号下溢**。**

### 3.5 而"**发出 7 个位块直到写入器溢出**"

**⇒ 三层**：

```text
1. `writeSkippedFieldIndex(4.29e9)` ⇒ 试图写 42 亿的"跳过数"
2. ⇒ 每个跳过用 7 位
3. ⇒ **直到写入器溢出**
4. ⇒ **失步 + 挂起**
```

**✅ 与 §299 的"分块不截断"**相反 —— 这里**溢出**。**

## 四、**`0xFFFFFF` 是 24 位**（本组第三重要）

### 4.1 那段

```php
// +0x0AC, 24 bits, `solid`. The netfield table names this row
// `eventSequence` and names the 13-bit row at +0x0A4 `solid`; the
// shipped const baselines put 0x00FFFFFF here on exactly the 238 brush
// models and leave +0x0A4 zero on all 397 entries. 0xFFFFFF is 24 bits
// exactly, and it is what MSG_ReadDeltaEntity's brush-model consumer
// tests for. See re/demo-re/16-const-baselines.md.
constexpr std::uint32_t ScriptMoverSolidField = 32;
```

### 4.2 六层

```text
1. **`+0x0AC`，24 位，`solid`**
2. ⇒ **netfield 表把这一行叫 `eventSequence`** 而把 `+0x0A4` 的 13 位行叫 `solid`
3. ⇒ **而随包的 const baselines 把 `0x00FFFFFF` 放在这里，恰好在那 238 个 brush model 上**
4. ⇒ 而**在全部 397 个条目上把 `+0x0A4` 留在零**
5. ⇒ **`0xFFFFFF` 恰好是 24 位**，而**它是 `MSG_ReadDeltaEntity` 的 brush-model 消费者所测试的**
6. ⇒ 见 `re/demo-re/16-const-baselines.md`
```

### 4.3 **"表的名字是错的而随包数据是对的"**

**✅ 与 §310 的"信任消费者"、§314 的"那一段描述 3.3.3.3"同族**（第十二次"以实测数据为准而不是表名"）。

**⇒ 三次确认：**

```text
§310  netfield 表的 MW3 移植名字错
§314  76 项表与 clientState 三处矛盾
§318  netfield 表把 solid/eventSequence 弄反
```

### 4.4 而 `238` 与 `397`

**⇒ 与 §294 的"`288/397`"**同一个 397** ✓**

**⇒ 而 238 是**brush model 的数量**。**

**⚠ 而 §302 说"零售发布 **34 / 238**"。**

**✅ 所以 238 是 brush model 总数而 34 是零售发布的。**

**⇒ 三次确认 238。**

### 4.5 而 `ScriptMoverBrushModelIndexField = 26` 的 `10 位`

```php
// +0x09C, 10 bits, the `*N` brush model index. The netfield table names
// this row `clientNum`; the shipped const baselines say otherwise -- see
// SvEntityState::scriptMoverBrushModelIndex.
constexpr std::uint32_t ScriptMoverBrushModelIndexField = 26;
```

**⇒ 三层**：

```text
1. **`+0x09C`，10 位，`*N` 的 brush model 索引**
2. ⇒ **netfield 表把这一行叫 `clientNum`**
3. ⇒ **而随包的 const baselines 说不是**
```

**✅ 又一次"表名错而数据对"。**

**⇒ 而 `10 位` 能表示 0..1023 而 238 个 brush model 够。** ✓

## 五、**`ScriptMover` 的轴顺序陷阱**

```php
// Retail's podium figures are placed with the FLOAT trio: section 122
// decoded exactly these three fields to 5142.95, -1396.73, 22.00, the
// map's own top_players_loc height. Index order is 5, 7, 8 and the AXIS
// order is not the index order -- 7 is x, 5 is y, 8 is z, by OFFSET
// (section 122's axis trap).
constexpr std::uint32_t ScriptMoverPositionTrajectoryDeltaYField = 5;
constexpr std::uint32_t ScriptMoverPositionTrajectoryTimeField = 6;
constexpr std::uint32_t ScriptMoverPositionTrajectoryDeltaXField = 7;
constexpr std::uint32_t ScriptMoverPositionTrajectoryDeltaZField = 8;
```

### 5.1 三层

```text
1. 零售的领奖台人偶用**浮点三元组**放置：§122 精确解码这三个字段为
     5142.95, -1396.73, 22.00  —— 地图自己的 top_players_loc 高度
2. ⇒ **索引顺序是 5、7、8 而轴顺序【不是】索引顺序**
3. ⇒ **7 是 x、5 是 y、8 是 z，按【偏移】**
```

### 5.2 而**三个具体值**

```text
5142.95, -1396.73, 22.00
```

**⇒ 而 22.00 是"地图自己的 `top_players_loc` 高度"。**

**✅ 与 §299 的 `top_players_loc` 与 §300 的 `top_players_camera` 配合。**

### 5.3 而"**§122 的轴陷阱**"

**⇒ 与 §314 的"`31/7/5/27` 的配对歧义"同族（第十六次"配对/顺序歧义"）。**

**⇒ 三次：**

```text
§314  BG_PlayAnim 的 "31/7/5/27"
§318  ScriptMover 的索引 5/7/8 vs 轴 x/y/z
§318  trajectory delta 数组 {43, 42, 46}
```

### 5.4 而 `ScriptMoverFloatAngleFields{30, 13, 31}`

**⚠ 又一个"索引顺序不是轴顺序"的数组。**

**⇒ 三个索引 `30, 13, 31`（不规则）⇒ 所以它们的轴是由**偏移**决定的。**

## 六、**`0xFF` 与 `0x7FF` 的"none"哨兵**

```php
// +0x008, codec -98. Retail sets eFlags 16 on the podium figures -- the
// SAME intermission flag the playerState carries on that frame.
// Every retail ET_SCRIPTMOVER asserts these two and this server sent
// zero: +0xE4 reads 255 on 2377 of 2390 assertions across the dm demo,
// +0x58 reads 2047 on all 2377. 0xFF and 0x7FF, both all-ones -- the
// shape of a "none" sentinel, where a zero means index 0 instead.
constexpr std::uint32_t ScriptMoverField00E4 = 25;   // +0x0E4, 8 bits
constexpr std::uint32_t ScriptMoverField0058 = 27;   // +0x058, 11 bits
```

### 6.1 六层

```text
1. `+0x008, codec -98`
2. ⇒ **零售在人偶上设 `eFlags 16`** —— 与 playerState 在同一帧携带的**同一个中场旗标**
3. ⇒ **每一个零售的 `ET_SCRIPTMOVER` 都断言这两个而本服务器发零**
4. ⇒ **`+0xE4` 在 dm demo 的 2390 个断言里读 255 于 2377 个**
5. ⇒ **`+0x58` 在所有 2377 个里读 2047**
6. ⇒ **`0xFF` 与 `0x7FF`，都是全一** —— **一个 "none" 哨兵的形状**，而**零意味着索引 0**
```

### 6.2 而**两个"全一"哨兵**

```text
0xFF    8 位全一     （+0xE4）
0x7FF  11 位全一     （+0x58）
```

**✅ 与 §264 的 `baseEntity = 2047`（`0x7FF`）**完全一致** ✓**

**⇒ 所以 `0x7FF` = `ENTITYNUM_NONE`。**

### 6.3 而"**零意味着索引 0**"

**⇒ 三层**：

```text
1. 零是**合法的**（索引 0）
2. ⇒ 所以"无"必须用**全一**
3. ⇒ **这就是为什么 0xFF/0x7FF 而不是 0**
```

**✅ 与 §235 的 `INT32_MIN`、§242 的 `addressable`、§278 的 `0xFFFFFFFF` 同族**（第十三次"用不可能的值作哨兵"）。

### 6.4 而 `2377 / 2390`

**⇒ `+0xE4` 在 2390 个断言里 2377 个是 255。**

**⇒ 所以 13 个不是 255。**

**⚠ 13 个例外。**

**⇒ 而 `+0x58` 在**所有** 2377 个里是 2047。**

**⇒ 所以 `+0x58` 的断言论 `+0xE4` 的 2377 个子集。**

**✅ 一个**干净的子集关系**。**

## 七、**`ScriptMover` 的第二帧**

```php
// THE SECOND FRAME OF A RETAIL PODIUM FIGURE. It spawns with an int
// origin and a model, and 400 ms later asserts a float origin, these
// three, an animTime and an animation index. The three below are
// CONSTANT across all three of the demo's figures; the animation index
// is 319/334/349 -- one per place, per map, and unportable without an
// animation-index namespace this build does not expose.
constexpr std::uint32_t ScriptMoverAngleTrajectoryTypeField = 12;
constexpr std::uint32_t ScriptMoverPositionTrajectoryTypeField = 15;
constexpr std::uint32_t ScriptMoverField0070 = 21;   // +0x070, codec -7
```

### 7.1 四层

```text
1. **一个零售领奖台人偶的第二帧**
2. ⇒ 它**以一个整型 origin 和一个模型 spawn**，而**400 ms 后断言一个浮点 origin、这三个、一个 animTime 和一个动画索引**
3. ⇒ **下面三个在 demo 的三个人偶上都是【常量】**
4. ⇒ **而动画索引是 319/334/349** —— **每个名次一个、每张地图一个**，而**不可移植**因为这个 build **不暴露一个动画索引命名空间**
```

### 7.2 而 **`319/334/349` 三个值**

```text
319    第 1 名
334    第 2 名
349    第 3 名
```

**⇒ 每个差 15。**

**⚠ 一个**可能的规律**（但注释说"unportable"）。**

### 7.3 而"**不可移植**"

**⇒ 三层**：

```text
1. 三个索引是**每名次每地图**
2. ⇒ 而本 build **不暴露动画索引命名空间**
3. ⇒ **所以不可移植**
```

**✅ 与 §292 的"索引是加载顺序不是 ABI"**同族（第五次）。

## 八、`EntityStateTime2Field = 24`

```cpp
// ET_PLAYER only: +0x7C, seven bits. See SvEntityState::time2.
constexpr std::uint32_t EntityStateTime2Field = 24;
constexpr std::uint32_t EntityStateTime2BitCount = 7;
```

**⇒ 三项：ET_PLAYER only、`+0x7C`、7 位。**

**⚠ 而 `+0x7C` 与 §255/§309 的 `clientState +0x7C`（character item）**同一个偏移**？**

**⇒ 不 —— 一个是 `clientState` 一个是 `entityState`。**

**✓ 不同的结构。**

## 九、**`EntityStateOffhandWeaponField = 5` / `CoKnifeStatsField = 38`**

```php
// Read directly from out.exe's ET_PLAYER table at 0x00DA4BF8:
// +0x060 is field 5 and +0x064 is field 38. These are the native
// offsets owned by offhandWeaponAssetIndex and coKnifeStatsIndex in
// SvEntityState. The previous 38/39 pair wrote both values one union
// word late, which is especially dangerous on knife/underbarrel deaths.
constexpr std::uint32_t EntityStateOffhandWeaponField = 5;
constexpr std::uint32_t EntityStateCoKnifeStatsField = 38;
```

### 9.1 四层

```text
1. **直接从 out.exe 的 `ET_PLAYER` 表 `0x00DA4BF8` 读出**：`+0x060` 是字段 5 而 `+0x064` 是字段 38
2. ⇒ 它们是 `SvEntityState` 里 `offhandWeaponAssetIndex` 与 `coKnifeStatsIndex` 拥有的原生偏移
3. ⇒ **之前的 38/39 对把两个值写晚了一个 union 字**
4. ⇒ **而那在刀/下挂发射器死亡上尤其危险**
```

### 9.2 而"**写晚了一个 union 字**"

**⇒ 三层**：

```text
1. `38/39` 而非 `5/38`
2. ⇒ 所以两个值**各晚一个 union 字**
3. ⇒ **在刀/下挂死亡上尤其危险**（因为那些路径正好读这两字段）
```

**✅ 与 §294 的"`288/397`"同族（第十四次"一个偏移错位"）。**

## 十、`ScriptMoverField0070` 的 `codec -7`

**⇒ 第六个/第七个负 codec（`-7`）。**

**⇒ 而 §317 已列八个（`-8`/`-57`/`-58`/`-75`/`-86`/`-94`/`-97`/`-100`）。**

**⇒ 现在加 `-7`、`-72`、`-77`、`-79`、`-81`、`-82`、`-83`、`-96`、`-98` ⇒ 十七个。**

**✅ 一个**大的负 codec 集合**。**

## 十一、关键结论

1. **索引 29 在两个 build 不是同一个字段** ⇒ 把 `idx29` 读成 `movementDir` **让每具身体隐形**。
2. **OLfinal：索引 29 → `+0x54` bits 0（DObj scale）；3.3.3.3：索引 29 → `+0x5C` codec -8，索引 46 → `+0x54`**。
3. **`BG_UpdatePlayerDObj` 无条件把 `+0x54` 拷进 `DObj_s::scale +0xC8`** ⇒ scale 0 ⇒ 不可见。
4. **`a4[21]` = `+0x54`、`+200` = `+0xC8`** —— 算术闭合。
5. **活体探针："每帧运行、带真实模型、而没有可见的身体"**。
6. **§309 与 §318 是**相反方向**的不可见**（活人不画 vs 尸体 scale 0）。
7. **OLfinal 的 `movementDir` 是索引 35 而 demo 零次断言** ⇒ retail 根本不发。
8. **⭐ `4.29e9` 的下溢** —— 索引 44 被 duration 与 delta[2] 同时声称 ⇒ `delta - 1` 下溢 ⇒ 失步 + 挂起。
9. **"一个数组初始化器对 `port-netfield-indices.py` 与 `audit-duplicate-constants.py` 都不可见"** —— 工具盲区第四次。
10. **`0xFFFFFF` 是 24 位** ⇒ `ScriptMoverSolidField = 32`，而 netfield 表把它叫 `eventSequence`。
11. **`ScriptMoverBrushModelIndexField = 26` 的 `+0x09C` 10 位** 而表把它叫 `clientNum`。
12. **"表名错而随包数据对"** —— 第三次。
13. **`238` 是 brush model 总数而 `34` 是零售发布的** —— 与 §302 一致。
14. **领奖台人偶的浮点三元组**：`5142.95, -1396.73, 22.00` 而 **索引 5/7/8 vs 轴 x/y/z 不一致**。
15. **`0xFF` 与 `0x7FF` 是 "none" 哨兵**（因为零是合法索引 0）。
16. **`+0xE4` 在 2390 个断言里 2377 个是 255；`+0x58` 在所有 2377 个里是 2047**。
17. **人偶的第二帧：400 ms 后断言浮点 origin**，而**动画索引 319/334/349 不可移植**。
18. **`38/39` → `5/38` 的修正** —— "写晚一个 union 字"。
19. **负 codec 至少 17 种**。

## 十二、未闭合点

- `+0xE4` 的 13 个非 255 值。
- `319/334/349` 是否真有规律。
- `ScriptMoverFloatAngleFields{30,13,31}` 的轴顺序。
- `sv_snapshot_mp.cpp` 1200 行之后未读取（1.47 MB）。
