# 414 · **"entity 号就是身份"** —— `sv_const_baselines_mp` 18 张表全解析：slot 0 不可达、`+3` 的带偏移不是常数、以及"一个 brush 不符就废掉整帧的 `0x10`"

## 一、范围

本报告学习：
- `sv_const_baselines_mp.hpp`（228 行，完整）
- `sv_const_baselines_mp.cpp`（3,673 行，生成的数据表，逐表统计 + 关键注释）
- 消费方：`sv_snapshot_mp.cpp` 的 7498（`constBaselineState`）、8866–8948（新实体的 const baseline 分支）、11890–12370（编号与校验）、10414–10525（`0x10` / `0x02` 旗标）

## 二、**"entity 号就是身份"**（本组最重要的一段）

### 2.1 那段

```cpp
// RETAIL'S STATIC ENTITY NUMBERS ARE DATA, NOT A RULE THIS SERVER GETS TO INVENT.
//
// Every map ships a `<map>_const.ff` next to `<map>.ff`, holding one rawfile:
// `mp/constbaselines/bl_pc_<map>_<gametype>.bin`. It is an array of full 280-byte
// entityState_t records -- the client loads it at map load (sub_515340 ->
// sub_6613E0), indexes it by entity number into `dword_77CE488`, and resolves any
// entity arriving with snapshot flag 0x10 against it (sub_470F60).
//
// So the entity number IS the identity: publish a door at the wrong number and the
// client gives it an unrelated entity's origin, model and solid. This project spent
// a long time trying to reproduce the numbering by walking the map entity string and
// plateaued at 288/397 -- because the gaps encode which entities take a slot, which
// is not recoverable from the entity list alone. The table below ends that: it is
// read straight out of the shipped asset.
```

### 2.2 二十层

```text
1. **零售的静态实体号是【数据**】，不是这个服务器可以发明的规则**
2. ⇒ **每张地图在 `<map>.ff` 旁边发运一个 `<map>_const.ff`**
3. ⇒ **里面【一个 rawfile**】：`mp/constbaselines/bl_pc_<map>_<gametype>.bin`
4. ⇒ **它是一个【完整的 `280` 字节 `entityState_t` 记录的数组**】**
5. ⇒ **客户端在**地图加载**时加载它**（`sub_515340` → `sub_6613E0`）
6. ⇒ **按实体号索引它进 `dword_77CE488`**
7. ⇒ **并对【任何携带快照旗标 `0x10` 到达的实体**】对它解析**（`sub_470F60`）
8. ⇒ **⇒ 所以【实体号就是身份**】**
9. ⇒ **在一个错误的号上发布一扇门 ⇒ 客户端给它【一个无关实体的 origin、model 与 solid**】**
10. ⇒ **这个项目【花了很长时间】**试图通过走地图实体串**复现编号**
11. ⇒ **而【在 `288/397` 处平台化**】**
12. ⇒ **因为【那些空隙编码了哪些实体占一个槽**】**
13. ⇒ **而那个【从实体列表本身不可恢复**】**
14. ⇒ **下面这张表【结束了那件事】：它【直接从随货资产读出**】**
```

### 2.3 ⭐⭐⭐ **"288/397 的平台化，因为空隙编码了哪些实体占槽"**

**✅ 这是本报告里**最重要的一条方法论结论**。**

**⇒ 三层**：
```text
可恢复的：实体串里【有】的实体（名字/模型/坐标）
不可恢复的：**哪些号被占用而【没有出现在实体串里**】（空隙）
⇒ **⇒ 所以走实体串的上限是 `288/397`（72.5%）**
```

**✅ 与 §409 的"一个 HUD 需要身体而不是什么先解出"**不同（这是**信息本身不可得**）。

**⇒ 三层**：
```text
§409  **可恢复但选错了**（取了头当身体）
§414  **结构性不可恢复**（空隙不在实体串里）
⇒ **⇒ 两种不同的"做不到"**
```

**✅ ⭐ **一个"不可能 vs 选错了"的区分**。

**⚠ 而"`288/397 = 72.5%`"⇒ **一个精确的覆盖率数字**。**

**✅ 与 §388 的"`373` 个 `ET_SCRIPTMOVER`"**配合。

### 2.4 而**"`0x10` 只对【新实体】有效"**

```cpp
// A NEW entity -- one the client has no acknowledged copy of -- is the
// only one the const baseline applies to, because bit 0x10 only steers
// where a NEW entity resolves from. An entity being delta'd against a
// previous snapshot already has a base both sides agree on.
```

**⇒ 六层**：
```text
1. **`0x10` 只引导【一个新实体从哪里解析**】**
2. ⇒ **一个新实体 = 客户端【没有已确认副本】的那个**
3. ⇒ **一个正在【对上一份快照做增量】的实体【已经有双方都同意的一个基准**】**
4. ⇒ **所以 const baseline 【只对 `baselineNum != currentNum` 的分支**】用
5. ⇒ **（见 `sv_snapshot_mp.cpp:8872` 的 `if (baselineNum != currentNum)`）**
```

**✅ ⭐ **一个"旗标的适用域"的精确界定**。

**⚠ 而"`0x10` 是【每快照】而不是每实体"⇒ **所以一处不符就废掉整帧**（§二.5）。

### 2.5 而**"一个 brush 不符就废掉整帧的 `0x10`"**

```cpp
// ONE BRUSH MODEL OFF THE TABLE DISQUALIFIES THE WHOLE FRAME'S FLAG.
// Bit 0x10 is set per snapshot, not per entity, so it cannot be right
// for the 237 that matched and harmless for the one that did not -- the
// odd one out would resolve against whichever entity retail put on its
// invented number.
auto everyBrushModelOnRetailNumber = constBaselines != nullptr;
```

**⇒ 十层**：
```text
1. **一个 brush 模型不在表上 ⇒ 【废掉整帧的旗标**】**
2. ⇒ **`0x10` 是【每快照设的，不是每实体**】**
3. ⇒ **所以它【不可能对匹配的 `237` 个是对的而对那一个不符的是无害的**】**
4. ⇒ **那个例外者会【对零售放在它的发明号上的那个实体解析**】**
5. ⇒ **⇒ 所以【全有或全无**】**
```

**✅ ⭐⭐⭐ **"一个每快照的旗标不能对 237 个对而对 1 个无害"** —— 与 §410 的"一个缺失的 eType 拒收整帧"**完全同族（**第二次"一个全局开关的不可分割性"）。**

**⇒ 三层**：
```text
§410  eType 白名单（帧级）⇒ **一个缺失 ⇒ 拒收整帧**
§414  `0x10` 旗标（帧级）  ⇒ **一个不符 ⇒ 整帧不用 baseline**
⇒ **⇒ 同一结构两处**
```

**✅ 而"script model 是【计数，不是要求】"⇒ **一个不对称的严格度**。**

```cpp
// Script models are counted, not required. Unlike brush models -- whose `*N` keys
// the table exactly -- some props cannot be resolved to a single row, and those
// stay on sequential numbers OUTSIDE the table, where the client resolves a zeroed
// baseline and this server deltas against zero. The two still agree, so the flag
// stays valid; only the wire cost is higher for those few.
```

**⇒ 九层**：
```text
1. **script model【计数，不要求**】**
2. ⇒ **理由：有些 prop 【不能解析到唯一的行**】**
3. ⇒ **而那些【留在表外的顺序号上**】**
4. ⇒ **在那里客户端解析【一个零化的基准**】**
5. ⇒ **而这个服务器【对零做增量**】**
6. ⇒ **⇒ 两者【仍然一致**】**
7. ⇒ **所以【旗标仍然有效**】**
8. ⇒ **只有那几个的【线路成本更高**】**
```

### 2.6 ⭐⭐⭐ **"留在表外 ⇒ 双方都解析零 ⇒ 仍然一致"**

**✅ 这是本报告里**最精妙的一处协议推理**。**

**⇒ 三层**：
```text
表内：客户端解析【零售的行】 而我们【也知道那一行】 ⇒ 一致
表外：客户端解析【零】       而我们【也对零增量】 ⇒ 一致
⇒ **⇒ 所以【两条路都自洽，只是成本不同**】
```

**✅ 与 §413 的"自定义提供者的缓存"**不同（这是**协议层的两路自洽**）。

**⚠ 而"brush model 没有这个余地"⇒ **因为 `*N` 精确键控表**。**

**⇒ 三层**：
```text
brush：`*N` ⇒ **表精确匹配** ⇒ 一缺失就【不知道零售放在哪】
script：origin ⇒ **可能多行同名** ⇒ **不匹配就退到表外（安全）**
⇒ **⇒ 所以【两个不同的失败模式**】
```

**✅ ⭐ **一个"为什么一个严格一个宽松"的机制解释**。

### 2.7 而**"`288/397` → 现在 `238/238`"**

```cpp
// The numbering underneath is the entity-string walk, not the old origin match:
// 238/238 brush models agree with the table by construction and every script
// model lands on a row, re-checked on every load by the gate below.
```

**⇒ 五层**：
```text
1. **底下的编号【是实体串走**】，不是旧的 origin 匹配**
2. ⇒ **`238/238` brush 模型【按构造**】与表一致**
3. ⇒ **而【每一个 script model 都落在一行上**】**
4. ⇒ **在【每次加载时**】由下面的门重新核对**
5. ⇒ **⇒ 所以【每次加载都验一次，不是一次性**】**
```

**✅ ⭐ **"按构造一致" vs "每次加载核对"** —— 一个**双保险**。

**⇒ 三层**：
```text
`SV_ConstBaselineBrushModelEntityNum(clipHandle)` ⇒ **按 `*N` 查表**
`definition.walkEntityNum` ⇒ **走实体串得到的号**
两者相等 ⇒ **`brushAgree`**
⇒ **⇒ 所以【两条独立路径的交叉验证**】
```

**✅ 与 §408 的"`d 15 0` 从 `out.exe` 与线上两条独立路径"**同族（**第三次"两条独立路径一致**）。

## 三、**18 张表的完整统计**（本组第二重要）

### 3.1 逐表计数

| 表 | 条目 | 号范围 | eType 6 | eType 8 | eType 11 | 其它 | brush | xmodel | solid≠0 | eFlags≠0 | 非单位 scale |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `zm_factory_sh` | 397 | 37–699 | 373 | 20 | 3 | **1** | 238 | 135 | 238 | 21 | 6 |
| `zm_asylum_sh` | 346 | 43–673 | 340 | 1 | 4 | **1** | 193 | 147 | 193 | 2 | 3 |
| `zm_prototype_sh` | 234 | 38–451 | 215 | 19 | 0 | 0 | 121 | 94 | 121 | 23 | 3 |
| `zm_sumpf_sh` | 275 | 37–670 | 274 | 0 | 0 | **1** | 172 | 102 | 172 | 1 | 7 |
| `mp_nuked_dd` | 108 | 79–689 | 104 | 4 | 0 | 0 | 38 | 57 | 38 | 4 | 1 |
| `mp_nuked_dm` | 100 | 177–685 | 96 | 4 | 0 | 0 | 37 | 52 | 37 | 4 | 1 |
| `mp_nuked_dom` | 130 | 174–688 | 126 | 4 | 0 | 0 | 50 | 69 | 50 | 4 | 1 |
| `mp_nuked_sd` | 137 | 174–689 | 133 | 4 | 0 | 0 | 53 | 71 | 53 | 4 | 1 |
| `mp_nuked_sr` | 137 | 174–689 | 133 | 4 | 0 | 0 | 53 | 71 | 53 | 4 | 1 |
| `mp_nuked_war` | 99 | 177–685 | 95 | 4 | 0 | 0 | 36 | 52 | 36 | 4 | 1 |
| `mp_nuked_cha` | 99 | 177–685 | 95 | 4 | 0 | 0 | 36 | 52 | 36 | 4 | 1 |
| `mp_nuked_tjugg` | 99 | 177–685 | 95 | 4 | 0 | 0 | 36 | 52 | 36 | 4 | 1 |
| `mp_nuked_conf` | 103 | 177–692 | 99 | 4 | 0 | 0 | 36 | 56 | 36 | 4 | 1 |
| `mp_nuked_tag` | 103 | 177–692 | 99 | 4 | 0 | 0 | 36 | 56 | 36 | 4 | 1 |
| `mp_nuked_hp` | 265 | 57–853 | 261 | 4 | 0 | 0 | 54 | 200 | 54 | 4 | 1 |
| `mp_nuked_borg` | 99 | 182–754 | 95 | 4 | 0 | 0 | 36 | 52 | 36 | 4 | 1 |
| `mp_nuked_chicken` | 99 | 177–685 | 95 | 4 | 0 | 0 | 36 | 52 | 36 | 4 | 1 |
| `coop_…_cargoship_coop` | 700 | 37–823 | 697 | 0 | 3 | 0 | 217 | 480 | 217 | 140 | 0 |

**⇒ 十八张表。**

### 3.2 ⭐⭐⭐ **三个不变式（全部十八张表都满足）**

```
① 号【升序无重复】
② brush 索引【无重复】
③ solid≠0 的条目数【恰好等于】brush≠0 的条目数
```

**✅ 而 ③ 与 `sv_snapshot_mp.cpp:11983` 的注释完全闭合**：

```cpp
// Retail agrees: all 373 ET_SCRIPTMOVER entries in factory's shipped
// const-baseline table are eType 6, and the 238 with a brush model
// index are exactly the 238 carrying 0x00FFFFFF.
```

**⇒ 三层**：
```text
`373` 个 `ET_SCRIPTMOVER` ⇒ **全部 `eType 6`** ✓（我的统计 `e6 = 373`）
`238` 个带 brush 索引 ⇒ **恰好是那 `238` 个携带 `0x00FFFFFF`** ✓（我的 `solid = 238`）
⇒ **⇒ 两个数字都精确吻合**
```

**✅ ⭐⭐⭐ **一个"注释里的三个数被独立复算全部命中"的验证**。**

### 3.3 而**三个 `eType 0` 的条目（唯一不在 `6/8/11` 里的）**

```
zm_factory_sh 号 567  eType=0  eFlags=0x11  field0058=0
zm_asylum_sh  号 576  eType=0  eFlags=0x11  field0058=0
zm_sumpf_sh   号 621  eType=0  eFlags=0x11  field0058=0
```

**⇒ 六层**：
```text
1. **三张 zm 图各有一个 `eType = 0` 的条目**
2. ⇒ **而 `eFlags = 0x11`**（`0x10 | 0x01`）
3. ⇒ **而 `field0058 = 0`**（**其余条目全是 `2047`**）
4. ⇒ **⇒ 所以它是一个【不同种类的静态实体**】**
5. ⇒ **`0x10`** 可能是 `EF_NODRAW` 或类似
6. ⇒ **`0x01`** 可能是 `EF_...`
```

**⚠ 而 `.hpp` 注释只列了 `6` / `8` / `11`** ⇒ **实际还有第四个值**。

**✅ 一个**需要标注的清单缺项**。

**⇒ 三层**：
```text
.hpp 注释："`ET_SCRIPTMOVER (6)`, `ET_FX (8)`, `ET_LIGHT (11)`. Every brush model is 6."
实测：**还有 `eType 0` 三条**
⇒ **⇒ 所以那个列表【不完整**】
```

### 3.4 而**`field0058` 的 `2047` 默认值**

**绝大多数条目 `field0058 = 2047`**（**`EntityNumNone`**），少数不是 `2047`：

| 表 | 非 2047 的条数 |
|---|---|
| `zm_factory_sh` | 24 |
| `zm_asylum_sh` | 6 |
| `zm_prototype_sh` | 19 |
| `zm_sumpf_sh` | 1 |
| `mp_nuked_*` | 4（每张） |
| `coop` | 3 |

**⇒ 而 `.hpp` 说 `field0058` 是「netfield 27, `+0x058`, 11 bits」。**

**⇒ `11` 位 ⇒ `0..2047` ⇒ **`2047` 是满值** ⇒ **正好 `EntityNumNone`。**

**✅ 与 §388 的"`EntityNumNone = 2047`"**完全闭合 ✓

**⇒ 三层**：
```text
`11` 位 ⇒ **`2047 = 最大**
`2047 = EntityNumNone` ⇒ **"没有"的哨兵**
⇒ **⇒ 所以【11 位正好为了容纳这个哨兵**】
```

**✅ ⭐ **一个"位宽由哨兵决定"的实例**。

**⚠ 而 `field00E4` 是 `255`（`8` 位满值）** ⇒ **同族**。

**✅ 与 §413 的"`0` 是一个哨兵"**不同（这是**满值作哨兵**）。

**⇒ 三层**：
```text
`0` 作哨兵     ⇒ §411 `BotLoadoutSequence = 1`（0 = 未初始化）
满值作哨兵     ⇒ §414 `2047`/`255`（= "无"）
⇒ **⇒ 两个相反的选择**
```

### 3.5 而**`mp_nuked` 十三张表的实体号差集**

```
dm (100) ⊂ cha (99)+{184}
cha = war = tjugg = chicken（99 条，号完全同集）
conf = tag（103，多 686/687/688 里的一部分）
dd（108，多 79/83/84/85/88/89/90 + 686..689）
dom（130，多 174/188/191/219..237/268..272/279/686..688）
sd = sr（137，多 291/296/297/298/338/339/340/689）
hp（265，多 57..75 + 174..237 + 268..279 + 686..853 的大段）
borg（99，号范围 182..754，与 dm 同集但号不同？）
```

**⇒ 而 `cha`/`war`/`tjugg`/`chicken` 四张表【号的集合完全相同**（99 条，`177..685`）。**

**⇒ 三层**：
```text
四个不同的 gametype ⇒ **同一份静态几何**
⇒ **⇒ 所以【静态实体集由地图决定，gametype 只影响少部分**】
```

**⚠ 而他们是否【逐字节相同**】？**需要核对。**

**⇒ 而 `conf`/`tag` 是 `103` 条（多 4 条）**，`dom`/`sd` 多出【占领点/炸弹点的实体**】。

**✅ ⭐ **一个"gametype 差异 = 目标点实体"的图景**。

**⇒ 三层**：
```text
`dom` 多 `219..237`（**一个连续段**）⇒ **占领点**
`sd`/`sr` 多 `291/296..298/338..340` ⇒ **炸弹点**
`dd` 多 `79..90`（**开始段**）⇒ **dd 的布局不同**
⇒ **⇒ 所以【号的集合编码了模式专属的几何**】
```

**✅ ⭐⭐ **"号集合编码模式专属几何"** —— 与 §2.2 的"空隙编码哪些实体占槽"**完全同族（**第二次"号本身携带信息"）。

## 四、**slot 0 不可达**（本组第三重要）

### 4.1 那段

```cpp
// SLOT 0 IS DELIBERATELY UNREACHABLE, because it is unreachable in the client. The
// index array `dword_77CE488` is zero-filled and the guard in sub_470F60 is
// `v2 > 0`, so "slot 0" and "not in the table" are the same answer there and the
// entity falls back to a zeroed struct. Factory's slot 0 is entity 37 -- which the
// retail demo duly shows arriving with eType 0 while the file says 6. Returning the
// real record here would make this server the only one of the two using it.
```

### 4.2 十八层

```text
1. **slot `0` 被【刻意地】设成不可达**，因为【它在客户端就是不可达**
2. ⇒ **索引数组 `dword_77CE488` 是【零填充的**】**
3. ⇒ **而 `sub_470F60` 的守卫是【`v2 > 0`**】**
4. ⇒ **⇒ 所以"slot `0`"与"不在表里"在那里是【同一个答案**】**
5. ⇒ **而那个实体【回退到一个零化的结构体**】**
6. ⇒ **Factory 的 slot `0` 是实体 `37`**
7. ⇒ **而零售 demo 【确实**显示它以 `eType 0` 到达】而文件说 `6`**
8. ⇒ **⇒ 所以【在这里返回真的记录会让这个服务器成为两者中唯一用它的那个**】
```

### 4.3 ⭐⭐⭐ **"零售 demo 显示 eType 0 而文件说 6"**

**✅ 这是本报告里**最重要的一个自证**。**

**⇒ 三层**：
```text
文件（`_const.ff`）：实体 37 是 `eType 6`（scriptmover）
零售 demo（线上）：**实体 37 以 `eType 0` 到达**
⇒ **⇒ 所以【零售自己也没用那一行**】
```

**✅ ⭐⭐ **"用零售自己的线上行为证明它自己的文件那一行不用"** —— 一个**判决性的证据**。

**✅ 与 §408 的"从 `out.exe` 读出而不是从线上读出"**相反**（这里**用线上行为否证文件**）。

**⇒ 三层**：
```text
两个来源冲突 ⇒ **线上（demo）优先**
⇒ **⇒ 这与项目的可信度阶梯一致**（**本地逆向 > 外部参照**）
```

**✅ ⭐ **一个"两个来源冲突时选哪个"的实例**。

**⚠ 而"`v2 > 0`"⇒ **一个 `>` 而不是 `>=`**。**

**⇒ 四层**：
```text
`v2 >= 0` ⇒ **slot 0 可用**
`v2 > 0`  ⇒ **slot 0 不可用**
⇒ **⇒ 所以【一个比较符的严格度决定了整个 slot 0 的命运**】
```

**✅ 与 §412 的"符号写反就偏 90°"**同族（**第三次"一个符号决定一切"）。

### 4.4 而**"skip slot 0 的遍历"**

四个查找函数全都从 `slot = 1` 开始：

```cpp
for (std::size_t slot = 1; slot < table->entries.size(); ++slot)
```

**⇒ 而 `SV_ConstBaselineScriptModelRowByOrigin` 的注释说：**

```cpp
// Slot 0 is skipped for the same reason as everywhere else: the client cannot
// reach it, so this server must not claim it.
```

**⇒ 五层**：
```text
1. **四个查找函数全都从 `slot = 1` 开始**
2. ⇒ **理由：客户端【到达不了它**】**
3. ⇒ **所以这个服务器【不能认领它**】**
4. ⇒ **⇒ 一个"向客户端的行为对齐"的纪律**
```

**✅ ⭐⭐ **"客户端到达不了 ⇒ 我们也不认领"** —— 与 §411 的"`faction` 匹配 `team`"**同族（**第三次"向既有的正确行为对齐"）。**

**⇒ 三层**：
```text
§409  人类路径的 team/faction 已对 ⇒ bot 对齐它
§412  yaw 公式的三个既有位置已对 ⇒ 这处对齐它们
§414  **客户端的 slot 0 不可达 ⇒ 服务器也不认领**
```
**✅ ⭐ **一个"对齐既有正确行为"的三例表**。

**⚠ 而 `brushDefinitions` 的循环【没有 skip slot 0**】—— 它按 `clipHandle` 查，**不遍历索引**。**

**⇒ 三层**：
```text
`SV_ConstBaselineBrushModelEntityNum` ⇒ **按 brush 索引查，`slot 0` 天然被排除**（因为 `slot0` 的 brush 索引可能非零！）
```

**⚠ 需要核对**：`zm_factory_sh` 的 `slot 0` 是 `{37, 6, 0, 388}` ⇒ **`brushModelIndex = 0`** ⇒ **不会被 brush 查找命中**（因为 `if (!table || !brushModelIndex) return nullopt;`）。

**✅ 但 `zm_asylum_sh` 的 `slot 0` 是 `{43, 6, 1, 0}`** ⇒ **`brushModelIndex = 1`** ⇒ **会被 `SV_ConstBaselineBrushModelEntityNum(1)` 命中并返回 `43`**！

**⇒ 三层**：
```text
`zm_factory_sh`  slot0 = {37, 6, brush=0,  xm=388} ⇒ **brush 查找不命中**（正确跳过）
`zm_asylum_sh`   slot0 = {43, 6, brush=1,  xm=0}   ⇒ **brush 查找会返回 43** ⚠
`zm_prototype`   slot0 = {38, 6, brush=1,  xm=0}   ⇒ **同上** ⚠
`zm_sumpf_sh`    slot0 = {37, 6, brush=1,  xm=0}   ⇒ **同上** ⚠
`coop_cargoship` slot0 = {37, 6, brush=1,  xm=0}   ⇒ **同上** ⚠
`mp_nuked_dom`   slot0 = {174, 6, brush=12, xm=0}  ⇒ **同上** ⚠
`mp_nuked_sd/sr` slot0 = {174, 6, brush=12, xm=0}  ⇒ **同上** ⚠
```

**⇒ ⭐⭐⭐ **一个真实的缺口**：`SV_ConstBaselineBrushModelEntityNum` **没有 skip `slot 0`**，而 `zm_asylum_sh` 等五张表的 `slot 0` 携带 `brushModelIndex = 1`/`12` ⇒ **会被命中。**

**⇒ 五层**：
```text
`SV_ConstBaselineBrushModelEntityNum` 的循环：`for (entry : table->entries)` ⇒ **从 0 开始**
而 `slot 0` 在 `zm_asylum_sh`/`zm_prototype`/`zm_sumpf_sh`/`coop`/`dom`/`sd`/`sr` 上 `brushModelIndex != 0`
⇒ **⇒ 所以那些地图的 brush `*1`（或 `*12`）会解析到【客户端不可达的那个号**】
```

**⚠ 但 §414 二.7 说 `238/238 brush 模型按构造一致` ⇒ **说明这个缺口在 `zm_factory_sh` 上不触发**（`slot 0` 的 `brush = 0`）。**

**⇒ 三层**：
```text
`zm_factory_sh`：slot0 brush=0 ⇒ **不触发**
其它 zm 图：slot0 brush=1 ⇒ **触发**（若该图有 brush `*1`）
⇒ **⇒ 一处【可能只在部分地图发作的缺陷**】
```

**✅ ⭐⭐⭐ **一个"注释声称的规则与实现不完全一致"的发现**。

**⇒ 建议**：`SV_ConstBaselineBrushModelEntityNum` 也应 `for (slot = 1; ...)`。

### 4.5 而**`walkEntityNum` 的校验如何处理 slot 0**

```cpp
const auto unreachableSlotZero = constBaselines->entries.empty()
    ? 0u
    : constBaselines->entries.front().entityNum;
std::size_t scriptAtSlotZero = 0;
for (const auto &definition : scriptModelDefinitions)
{
    if (definition.walkEntityNum && definition.walkEntityNum == unreachableSlotZero)
    {
        ++scriptAtSlotZero;
        continue;   // ← 不算失败
    }
    if (definition.walkEntityNum &&
        SV_ConstBaselineEntityState(constBaselines, definition.walkEntityNum))
        ++scriptOnRows;
}
```

**⇒ 六层**：
```text
1. **`unreachableSlotZero = entries.front().entityNum`**
2. ⇒ **走实体串得到该号的 script model ⇒ `scriptAtSlotZero++`** 并 **`continue`**（**不算失败**）
3. ⇒ **而 `SV_ConstBaselineEntityState` skip `slot 0` ⇒ 该号返回 `nullptr`**
4. ⇒ **⇒ 所以【那条 script model 保留顺序号**】**
5. ⇒ **（`walkAgrees` 只要求 brush 全对**）**
```

**✅ 而"zm_sumpf_sh 有三个 `zombie_power_lever_handle_arm03_off` 在那种状态"⇒ **一个具体的例子**。**

**✅ 与 §409 的"回退梯子"**同族（**第七次"部分功能优于无功能"）。

## 五、**`+3` 的带偏移【不是常数】**（本组第四重要）

### 5.1 那段

```cpp
// THIS SERVER'S MODEL CONFIGSTRING BAND IS NOT RETAIL'S, AND THE DIFFERENCE IS A
// CONSTANT. Measured on zm_factory_sh: `codo_treasure_chest_box2` is 392 here and
// 389 in the shipped baselines, `..._lid` 393 vs 390, `codo_zm_production_line_
// rack03_a` 394 vs 391, `_b` 395 vs 392 -- every one exactly +3.
//
// ... every prop that resolved to exactly ONE row by origin alone contributes a vote,
// and the offset is used only if the votes agree overwhelmingly. If this server's
// band is ever aligned to retail's the measurement simply reads zero ...
```

**⇒ 而 `+3` 立刻被后一段推翻**：

```cpp
// WHAT THE CLIENT WILL ACTUALLY RESOLVE THE MODEL FROM. A prop takes its row's
// xmodel unless this server SENDS a different one, and the two sides index
// different configstring bands -- retail's perk machines sit at 248..279 while
// the rest of the map's props are at 384..407, so the offset is not the uniform
// +3 measured on one cluster.
```

### 5.2 十六层

```text
1. **这个服务器的模型 configstring 带【不是零售的**】**
2. ⇒ **在 `zm_factory_sh` 上测：四个 prop 【全部恰好 `+3`**】**
3. ⇒ **⇒ 所以第一版结论是"一个常数"**
4. ⇒ **而下一段推翻它**：
      · **零售的 perk 机器在 `248..279`**
      · **而地图其余 prop 在 `384..407`**
      · **⇒ 所以那个偏移【不是在一个群集上测到的统一 `+3`**】**
```

### 5.3 ⭐⭐⭐ **"一个群集上的常数，在另一个群集上不成立"**

**✅ 与 §398 的"`cs 189` 在 zm 是 `battery_multiplier` 而在 dm 是 `ui_bossBodyDestroyedInfo`"**同族（**第七次"索引逐 gametype/逐群集"）。**

**⇒ 三层**：
```text
群集 A（地图道具 `384..407`）⇒ **偏移 `+3`**
群集 B（perk 机器 `248..279`）⇒ **偏移不是 `+3`**
⇒ **⇒ 所以【两段注释互相矛盾，而后者是对的**】
```

**✅ ⭐⭐ **"一段注释推翻自己上一段"** —— 一个**自我修正的完整记录**。

**⚠ 而代码用的是【投票**】而不是常数**。**

**⇒ 六层**：
```text
`modelIndexOffset` ⇒ **从"按 origin 唯一匹配"的 prop **投票** 得到**
⇒ **而只用【压倒性一致**】时接受：`best->second * 10 >= voters * 9`（**≥ 90%**）
⇒ **理由**："一个只大体一致的带不是一个带偏移，是噪声，而对噪声行动会把 prop 放到**别的 prop 的实体号**上"
```

**✅ ⭐⭐⭐ **"≥ 90% 才接受，否则当成噪声"** —— 一个**防止用噪声改编号**的门**。**

**✅ 与 §411 的"队满 ⇒ 丢弃并记一行"**同族（**第五次"有界 + 明确阈值"）。**

**⇒ 三层**：
```text
§411  splash 队满 ⇒ **丢弃 + 日志**
§413  `initialized = (tag != 0) || !emptyTag` ⇒ **不可恢复的失败标为已初始化**
§414  `votes 90%` ⇒ **不过阈值 ⇒ 用 `0`（不退化为噪声）**
```
**✅ ⭐ **一个"阈值决定是否采用推测量"的三例**。

### 5.4 而**"`modelIndexOffset` 在代码里【被计算但不被使用**】"**

**⇒ 检查**：`modelIndexOffset` 只在日志里出现。

**⇒ `grep` `modelIndexOffset`：**
```text
定义 + 赋 + 日志
```
**⇒ 没有下游消费者。**

**⇒ 五层**：
```text
1. **它被计算（投票 + 90% 门）**
2. ⇒ **被打印（`model band offset=… agreement=…/… distinctOffsets=…`）**
3. ⇒ **而【没有被使用**】**
4. ⇒ **⇒ 所以它是一个【纯仪器**】**
5. ⇒ **（因为真正的解法是"从不发 xmodel，让客户端保留它自己解析的"）**
```

**✅ 与 §407 的"三个 announcer id 打进日志便于替换"**同族（**第十四次"可替换的推断值"）。**

**⚠ 而"真正的解法"⇒ `constBaselineStorage.modelIndex = entities[currentIndex].modelIndex;`**

**⇒ 五层**：
```text
**不发送 xmodel** ⇒ 客户端保留它【自己解析的那个】
而**如果发送了** ⇒ 客户端算 `ours ^ ours ^ file = file` ⇒ **落在服务器带上差了 `offset`**
⇒ **⇒ 所以【把 baseline 的 xmodel 改成"我们的值"** ⇒ **该字段相等 ⇒ 不发送** ⇒ 客户端保留正确值
```

**✅ ⭐⭐⭐ **"用『不发』来避免『算错』"** —— 与 §410 的"eType 白名单"**不同（这是**用不发送来规避错误），而**这是一个极精妙的修法**。

**⇒ 三层**：
```text
错误：`base = file` ⇒ 发送 `ours ^ file` ⇒ 客户端得 `file`（**错 3 格**）
正确：**`base = ours` ⇒ 不发送** ⇒ 客户端保留 `ours`（**对**）
⇒ **⇒ 所以【把错误的值换成"正确的值"来让等式成立**】
```

**✅ **这是本报告里最精巧的一处**。

## 六、**`0x02` 的一进一出**（本组第五重要）

### 6.1 那段

```cpp
// BIT 0x02 IS THE CLIENT'S TICKET OUT OF CA_PRIMED, AND THIS SERVER HAS NEVER
// SET IT.
// ...
// MEASURED on mp_battlecity 2026-09-04: the dedicated logs the 2-byte keepalive
// as `netchan packet too short: 2 bytes, minimum 5`, the client sends ~65 packets
// and then stops, produces no `pmove-slice`, never acks (`cacheAcked=0` forever,
// so every frame stays `source=none(FULL)`), and times out on
// XBOXLIVE_CANTJOINSESSION after 46 s. All of that is one client stuck at 9.
```

### 6.2 二十层

```text
1. **`0x02` 是客户端【离开 `CA_PRIMED`】的门票**，而这个服务器【从未设过它**】
2. ⇒ **`sub_515C90` = `CL_FirstSnapshot`，它在 `0x515DAE` 把 `cls.state` 设成 `10`**
3. ⇒ **而它【仅由 `snap.snapFlags & 2` 门控**】**
4. ⇒ **而 `snapshot_.flags` 被赋 `0` 而【再也没被碰过**】**
5. ⇒ **⇒ 所以这个服务器放上线的只有 `0x08`（baseline）与 `0x10`（entity baselines）**
6. ⇒ **一个【从未收到 `0x02` 的客户端永远停在 `cls.state 9`**】**
7. ⇒ **而那就是第 3a 节描述的**："完全没有 netchan 包，只有 `1 Hz` 的 `2` 字节 keepalive，因为一个 `CA_PRIMED` 客户端在等它的第一份快照"
8. ⇒ **⚠ 在 `mp_battlecity` 上 2026-09-04 测量**：
      · **专用服把它记成 `netchan packet too short: 2 bytes, minimum 5`**
      · **客户端发约 `65` 个包然后停止**
      · **不产生 `pmove-slice`**
      · **从不 ack（`cacheAcked=0` 永远，所以每一帧都是 `source=none(FULL)`）**
      · **在 `XBOXLIVE_CANTJOINSESSION` 上 `46` 秒超时**
9. ⇒ **⇒ 那全部是【一个卡在 `9` 的客户端**】**
```

### 6.3 ⭐⭐⭐ **"`0x02` 只在【第一帧】设，且【重复到它进入为止，然后停**】"**

```cpp
// REPEAT UNTIL IT TAKES, THEN STOP. Both extremes were measured on mp_battlecity
// and both are wrong:
//
//   every FULL frame   the client ACKED for the first time ever (cacheAcked 0->1)
//                      but then oscillated rearm/FULL with deltaMessage frozen --
//                      each repeat restarts CL_FirstSnapshot instead of finishing
//   exactly once       the client never acked at all (cacheAcked=0), because the
//                      one announcement lands while it is still loading the map
//                      and there is no second chance
//
// So the flag has to persist until the client demonstrably enters, and then stop.
// `baseline != nullptr` IS that demonstration ...
```

**⇒ 十六层**：
```text
1. **重复到它生效，然后停**
2. ⇒ **【两个极端都测过**】，**两个都错**：
      · **每一 FULL 帧**：客户端【第一次** ack 了**（`cacheAcked 0→1`）
        但【然后**在 `rearm`/`FULL` 之间振荡而 `deltaMessage` 冻在 `64`**】
        ——**每次重复【重启 `CL_FirstSnapshot`】而不是完成**
      · **恰好一次**：客户端【根本不 ack**】（`cacheAcked=0`）
        因为**那一次宣告落在【它还在加载地图**】的时候而【没有第二次机会**】
3. ⇒ **所以旗标必须【持续到客户端可证明地进入**】，然后停**
4. ⇒ **`baseline != nullptr` **就是那个证明**】
5. ⇒ **（`cacheAcked=1` 只对 `rearm(flagged-baseline)` 与 `acked` 打印）**
```

### 6.4 ⭐⭐⭐ **"两个极端都错 ⇒ 必须有一个『可观测的终止条件』"**

**✅ 这是本报告里**最重要的一个控制律**。**

**⇒ 三层**：
```text
永远设 ⇒ **客户端 ack 了但振荡**（因为 `CL_FirstSnapshot` 每次重跑）
设一次 ⇒ **客户端根本没 ack**（因为那一次落在地图加载中）
⇒ **⇒ 所以【必须有第三个选项：重复到某个可观测信号出现**】
```

**✅ 与 §405 的"STILL NOT SENT 每个都有一个理由"**不同（这是**一个二元选择的两端都错）。**

**⇒ 三层**：
```text
§412  "远处 3.5° 看不出，贴脸 65° 才看见" ⇒ **一个参数的两端**
§414  "永远设 vs 设一次" ⇒ **两个策略都错 ⇒ 需要第三个**
```
**✅ ⭐⭐ **一个"两难必须有第三解"的实例**。

**⚠ 而"`baseline != nullptr` 是那个证明"⇒ **一个来自系统内部的可观测信号**。**

**⇒ 四层**：
```text
**不是**"等 N 帧"（**一个发明的时间常数**）
**不是**"等某条日志"（**一个间接的猜测**）
**而是**【一个本来就存在于协议里的状态**】（**有 baseline ⇔ 已 ack 过**）
```

**✅ ⭐⭐⭐ **"用协议里本来就存在的信号，而不是发明一个超时"** —— 与 §404 的"demo 的 3.0 秒间隔是那个队列，不是我发明的延迟"**完全同族（**第二次"用机制而不是发明"）。

**✅ 与 §409 的"`travel` 的位移硬读数"**配合。

## 七、**`<map>_const.ff` 的资产血统**

**⇒ 六个来源层次**：

```text
① `<map>_const.ff`（**加密的 fastfile，随地图发运**）
② `Tools/codol_ff_decrypt_olfinal.py`（**解密器**）
③ `Tools/gen-const-baselines.py`（**表生成器**）
④ `sv_const_baselines_mp.cpp`（**生成物**，`DO NOT EDIT BY HAND`）
⑤ `SV_ConstBaselineTable(map, gameType)`（**运行时查找**）
⑥ `sv_snapshot_mp.cpp` 的编号与校验（**消费者**）
```

**⇒ 而生成器的头部说：**

```cpp
// GENERATED by Tools/gen-const-baselines.py -- DO NOT EDIT BY HAND.
//
// Source: each map's shipped `<map>_const.ff`, decrypted with
// Tools/codol_ff_decrypt_olfinal.py. Every number here is retail's, read out of
// the game's own asset; nothing is derived. See re/demo-re/16-const-baselines.md.
```

**⇒ 五层**：
```text
1. **`DO NOT EDIT BY HAND`**
2. ⇒ **每一个数字都是【零售的**】，从游戏自己的资产读出**
3. ⇒ **【没有东西是推导的**】**
4. ⇒ **⇒ 所以这是【可信度阶梯的第 1 级**】（**本地逆向**）
```

**✅ 与本项目 `AGENTS.md` 的**「本地逆向 — 从真实客户端捕获的字节，从随货游戏文件解包的数据。不可辩驳；在与其它来源冲突时凌驾一切」完全一致 ✓

**⇒ 三层**：
```text
`AGENTS.md` 第 1 级：**本地逆向**
`sv_const_baselines_mp.cpp`：**从 `<map>_const.ff` 解出的原始字节**
⇒ **⇒ 所以它是【本项目最高可信度的数据**】
```

**✅ ⭐ **一个"数据血统"的确认**。

### 7.1 而**"`OLMOD_CONST_BASELINES=0` 的默认开"**

```cpp
// AN OFF SWITCH, BECAUSE THIS CHANGES WHAT THE CLIENT DRAWS.
// ...
// OLMOD_CONST_BASELINES=0 falls back to sequential numbering with the
// flag off, which is what every build before this one did.
static const auto enabled = [] {
    const auto *const value = std::getenv("OLMOD_CONST_BASELINES");
    return !value || !*value || *value != '0';
}();
```

**⇒ 七层**：
```text
1. **一个关闭开关，因为它【改变客户端画什么**】**
2. ⇒ **理由**：`0x10` 不只是省带宽
3. ⇒ **客户端对每个静态实体【按 baseline 解析**】**
4. ⇒ **所以这个服务器【不建模的每一个字段】现在【继承零售的值**】而以前得到 `0`**
5. ⇒ **那就是重点 —— 而它【也是一个渲染变化**】**
6. ⇒ **所以它需要一个【能撤回的方法**】**
7. ⇒ **没有它，"这是新的吗"就要花【一次重建与一个周期】而不是一个环境变量**
```

**✅ ⭐⭐ **"一个渲染变化需要一个环境变量的撤回开关"** —— 与 §404 的"窄回退"**同族（**第六次"可回退"）。

**⇒ 三层**：
```text
§404  **回退一个命令**（`a <weapon>`）
§410  **`OLMOD_KILL_FEED` 开关**
§414  **`OLMOD_CONST_BASELINES` 开关**
⇒ **⇒ 三次"先能关再开**
```

**✅ ⭐ **一个"可逆性"的三例表**。

**⚠ 而 `return !value || !*value || *value != '0';` ⇒ **逻辑**。**

**⇒ 四层**：
```text
未设 ⇒ `!value` 真 ⇒ **`true`（开）**
设为 `""` ⇒ `!*value` 真 ⇒ **`true`**
设为 `"0"` ⇒ **`false`**
设为 `"1"`/`"anything"` ⇒ `*value != '0'` 真 ⇒ **`true`**
⇒ **⇒ 只认恰好 `"0"`** ⇒ 与 §410 的 `OLMOD_KILL_FEED` **完全同形**
```

**✅ 而 §410 的写法是 `!(value && value[0]=='0' && !value[1])` ⇒ **只认恰好 `"0"`（`"00"` 会开）。**

**⇒ 这里是 `*value != '0'` ⇒ **`"00"` 也会关**（因为第一个字符是 `'0'`）。

**⚠ 一个**细微的差异**：两种写法对 `"00"` 的处理不同。

**⇒ 三层**：
```text
§410 `OLMOD_KILL_FEED`：`!(v && v[0]=='0' && !v[1])` ⇒ `"00"` ⇒ **开**
§414 `OLMOD_CONST_BASELINES`：`*v != '0'` ⇒ `"00"` ⇒ **关**
⇒ **⇒ 两个开关对 `"00"` 的语义相反**
```

**✅ 一个**值得记录的不一致**（`"00"` 这种输入不现实，但两处写法确实不同）。

## 八、`SvConstBaselineEntry` 的完整布局

```text
字段                         类型         netfield  偏移       说明
─────────────────────────────────────────────────────────────────────────
entityNum                    u16         —         —          零售的实体号，升序无重
eType                        u8          —         —          6/8/11（+ 实测的 0）
brushModelIndex              u16         26        +0x09C     10 位，`*N`（netfield 表误名为 clientNum）
xmodelIndex                  u16         19        +0x05C     10 位，brush 上恒 0
solid                        u32         —         —          0x00FFFFFF = brush 可见
eFlags                       u32         —         —          
originBits[3]                u32×3       1/2/4     —          lerp.pos.trBase
anglesBits[3]                u32×3       10/3/9    —          lerp.apos.trBase
scaleBits                    u32         46        +0x054
field0058                    u16         27        +0x058     11 位，2047 = None
field00E4                    u16         25        +0x0E4     8 位，255 = 满
field0098                    u16         47        +0x098     5 位
field0070                    i32         21        +0x070     codec -7
positionTrajectoryType       u8          15        +0x00C
angleTrajectoryType          u8          12        +0x030
positionTrajectoryTime       u32         —         +0x010
positionTrajectoryDuration   u32         —         +0x014
angleTrajectoryTime          u32         —         +0x034
angleTrajectoryDuration      u32         —         +0x038
positionTrajectoryDeltaBits[3] u32×3     —         +0x024/028/02C
angleTrajectoryDeltaBits[3]  u32×3       —         +0x048/04C/050
surfType                     u32         —         +0x090
```

**⇒ 而 `.hpp` 的注释解释了为什么连轨迹都要抄：**

```cpp
// THE TRAJECTORY, WHICH IS WHERE AN UNMODELLED FIELD STOPS BEING HARMLESS.
//
// An entity published on a table number inherits every field the server does not
// override, and the server can only override what it MODELS. Leaving these out
// meant a prop could take a VELOCITY (`pos.trDelta`) and an angular velocity
// (`apos.trDelta`) from its row and quietly drift and spin. Six of factory's
// script-model rows carry exactly that -- entities 475..480, the zapper arms, at
// trType 1 with deltas like (-141, 0, -79) and a -180 spin.
```

### 8.1 ⭐⭐⭐ **"一个不建模的字段就不再是无害的"**

**✅ 这是本报告里**最重要的一条"为什么必须抄全"的论证**。**

**⇒ 十二层**：
```text
1. **一个发布在表号上的实体【继承服务器不覆写的每一个字段**】**
2. ⇒ **而服务器【只能覆写它建模的东西**】**
3. ⇒ **把这些落下 ⇒ 一个 prop 【从它的行里拿到一个速度（`pos.trDelta`）与一个角速度（`apos.trDelta`）**】**
4. ⇒ **并【安静地漂移并旋转**】**
5. ⇒ **Factory 的六个 script-model 行【恰好携带那个**】**：
      · **实体 `475..480`**
      · **`trType 1`**
      · **以 `(-141, 0, -79)` 这样的 delta 与一个 `-180` 自旋**
```

### 8.2 而我复算的六行完全吻合

```
475: trpos=1 trang=1   deltaPos = (0xC30D0000, 0, 0xC29E0000) = (-141, 0, -79)
476: trpos=1 trang=1   deltaPos = (0x42B80000, 0, 0xC21C0000) = (+92, 0, -39)
477: trpos=1 trang=1   deltaPos = (0xC2B80000, 0, 0xC29E0000) = (-92, 0, -79)
478: trpos=1 trang=1   deltaPos = (0x430D0000, 0, 0xC21C0000) = (+141, 0, -39)
479: trpos=1 trang=1   deltaPos = (0x422C0000, 0, 0xC21C0000) = (+43, 0, -39)
480: trpos=1 trang=1   deltaPos = (0xC2300000, 0, 0xC29E0000) = (-44, 0, -79)
而 six 行的 deltaAng = (0, 0, 0xC3340000) = **(0, 0, -180)**
```

**✅ ⭐⭐⭐ **"`-141, 0, -79` 与 `-180` 自旋"在数据里逐字节命中**。**

**⇒ 三层**：
```text
注释：`(-141, 0, -79)` 与一个 `-180` 自旋，实体 `475..480`
数据：`475` 的 `deltaPos[0] = 0xC30D0000 = -141.0f`
      六行的 `deltaAng[2] = 0xC3340000 = -180.0f`
⇒ **⇒ 完全吻合**
```

**✅ ⭐ **一个"注释里的三个数值在表里全部命中"的验证**。

**⚠ 而 `trpos = 6` 而非 `2`** ⇒ **我的统计口径**（只数了 `positionTrajectoryTime` 与 `positionTrajectoryType` 的**或**）。

**⇒ 精确说是 `484?` 不，是 `6` 行有 `trType != 0`，`8` 行有 `trTime != 0`。**

**⇒ 而 `.hpp` 说"六行"⇒ **`6` 是 `trType` 的行数**。**

**✅ 而 `477/478/479/480` 的 `trTime` 也是非零**（我的统计 `trpos=6` 与此一致 —— 这六行确实是 475..480）。

**⚠ 一处**：我的 `trpos` 计数是 6，`trang` 计数是 8 —— **八个 `trang`**，而注释只提六个。

**⇒ 那些额外的两行需要标注**（可能是 `trType` 非零而 `trTime` 为零的情况）。

**⇒ 三层**：
```text
`trType != 0` ⇒ **6 行**（475..480，与注释一致）
`trTime != 0` ⇒ **8 行**（多 2 行）
⇒ **⇒ 所以【有 2 行携带时间但没有类型**】—— 一个需要核对的边界
```

### 8.3 而**"浮点以位模式携带，不转十进制"**

```cpp
// Floats are carried as their raw bit patterns and bit_cast back, not as
// decimal literals. These are compared for EXACT equality against the
// server's own map parse to decide whether a field is sent at all, and a
// lossy round trip through a decimal literal would turn a silent entity
// into a chatty one.
```

**⇒ 八层**：
```text
1. **浮点以【原始位模式】携带，`bit_cast` 回来，不是【十进制字面量**】**
2. ⇒ **它们被【按精确相等比较**】**
3. ⇒ **对这个服务器自己的地图解析**
4. ⇒ **以便决定一个字段【是否发送**】**
5. ⇒ **而一个经过十进制字面量的【有损往返**】**
6. ⇒ **会【把一个安静的实体变成多话的实体**】**
7. ⇒ **⇒ 所以位模式是【正确性要求**】不是风格**
```

**✅ ⭐⭐⭐ **"一个安静的实体变成一个多话的实体"** —— 一个**极精确的成本描述**。

**✅ 与 §409 的"`6/5` 整数而不是 `1.2` 浮点"**同族（**第三次"精确算术"）。

**⇒ 三层**：
```text
§409  整数 `6/5` ⇒ **消除浮点误差**
§412  `atan2` 的参数顺序 ⇒ **消除 90° 偏差**
§414  `bit_cast` 位模式 ⇒ **消除有损往返**
```
**✅ ⭐ **一个"三个精度问题"的表**。

## 九、**`SvConstBaselineTable` 的 map/gametype 键**

```cpp
// Null when this build ships no extracted table for the map, which is the
// normal case for every map whose `_const.ff` is still packed inside an
// `.ifs`. Callers must degrade to sequential numbering rather than fail.
// KEYED ON THE PAIR. A zombie map has one gametype, so map alone was a unique
// key and this took only a map. mp_nuked ships THIRTEEN tables and `dd` is laid
// out first, so a map-only lookup hands a deathmatch server domination's entity
// numbering -- and the numbering IS the identity (see the note above): a door
// published on the wrong number becomes some other entity's origin, model and
// solid on the client. Falls back to the map's first table when the pair is
// unknown, which is what a one-gametype map wants.
```

### 9.1 十二层

```text
1. **当这个 build 【不为某张地图发运解出的表】时返回空** ⇒ **正常情况**（`_const.ff` 还打包在 `.ifs` 里）
2. ⇒ **调用者必须【退化到顺序编号**】而不是失败**
3. ⇒ **【按对（map, gametype）键控**】**
4. ⇒ **一个 zm 地图【只有一个 gametype**】 ⇒ 所以只用 map 曾是一个唯一键**
5. ⇒ **而 `mp_nuked` 发运【十三张表**】而 `dd` 排第一**
6. ⇒ **⇒ 一个【只用 map 的查找会给一个死斗服务器【domination 的实体编号**】**
7. ⇒ **而【编号就是身份**】**
8. ⇒ **⇒ 一扇在错号上发布的门【在客户端变成某个别的实体的 origin、model 与 solid**】**
9. ⇒ **当对未知时【回退到地图的第一张表**】**
10. ⇒ **而那是【一个单 gametype 地图想要的**】**
```

### 9.2 ⭐⭐⭐ **"只用 map 查找会给死斗服务器 domination 的编号"**

**✅ 这是本报告里**最重要的一次键设计事故**。**

**⇒ 三层**：
```text
旧键：`map`  ⇒ **一个 zm 地图只有一个 gametype ⇒ 唯一**
`mp_nuked` 有 13 张 ⇒ **`map` 不唯一 ⇒ 拿到 `dd`（表数组第一个）**
⇒ **⇒ 而 `AGENTS.md` 的分级**：**编号就是身份 ⇒ 错号 = 错实体**
```

**✅ 与 §409 的"`BotLoadoutSequence = 1` 区分首次与变化"**同族（**第四次"一个键必须包含足够的信息"）。

**⇒ 三层**：
```text
§400  **缓存键必须含那个状态**
§413  `lastCharacterCustomizations_` 的键含 `xuid`
§414  `SvConstBaselineTable` 的键含 `gameType`
⇒ **⇒ 三次"键不足**】
```

**✅ ⭐ **一个"键设计"的三例表**。

**⚠ 而"回退到地图的第一张表"⇒ **一个明确的降级，而 `dd` 是 `mp_nuked` 的第一张**。**

**⇒ 三层**：
```text
`mp_nuked` + 未知 gametype ⇒ **回退到 `dd`**
而 `dd` 是【不是 `dm`】
⇒ **⇒ 所以【一个未知 gametype 会拿到 `dd` 的编号**】
```

**⚠ 一个**真实的危险**（但**如果没有 `_const.ff` 就更糟** —— 至少编号在同一张地图内是一致的）。

**✅ 与 §409 的"一个错的人偶仍然胜过一个没有人偶"**同族（**第八次"部分正确优于无"）。**

## 十、关键结论

1. **⭐⭐⭐ "entity 号就是身份"**：`<map>_const.ff` 是 280 字节 `entityState_t` 的数组，客户端按号索引进 `dword_77CE488`，`sub_470F60` 对 `0x10` 旗标的实体解析它 ⇒ **在错号上发布一扇门 ⇒ 客户端给它一个无关实体的 origin/model/solid**。
2. **⭐⭐⭐ "走实体串在 288/397 处平台化，因为空隙编码了哪些实体占槽"** —— **结构性的不可恢复**（不是"选错了"）。
3. **⭐⭐⭐ "一个 brush 模型不在表上 ⇒ 废掉整帧的 `0x10`"**（因为 bit 是**每快照**而不是每实体，"不可能对 237 个对而对那一个无害"）—— 与 §410 的帧级 eType 白名单**完全同族**。
4. **⭐⭐ "script model 是计数不是要求"**：解不出唯一行的 prop **留在表外**，客户端解析**零化基准**而服务器**也对零增量** ⇒ **两者仍一致，只是成本更高** —— 一个协议层的两路自洽。
5. **⭐ 三个不变式在全部 18 张表成立**：号**升序无重复**、brush 索引**无重复**、**`solid≠0` 的条数恰好等于 `brush≠0` 的条数**。
6. **⭐⭐ 注释里的三个数被独立复算全部命中**：`373` 个 `ET_SCRIPTMOVER`、`238` 个带 brush 索引、`238` 个携带 `0x00FFFFFF`，以及 **`475..480` 六行的 `deltaPos ≈ (-141,0,-79)` 与 `deltaAng[2] = -180`**。
7. **⚠ `.hpp` 的 eType 清单（`6`/`8`/`11`）不完整**：实测还有 **三个 `eType 0`**（`zm_factory_sh` 号 567、`zm_asylum_sh` 号 576、`zm_sumpf_sh` 号 621），均 `eFlags = 0x11`、`field0058 = 0`。
8. **`field0058 = 2047` 与 `field00E4 = 255` 是"满值作哨兵"**（`11` 位 / `8` 位的最大值 = `EntityNumNone` / "无"），与 §411 的"`0` 作哨兵"相反。
9. **⭐⭐⭐ slot 0 在客户端【不可达】**：索引数组零填充 + 守卫是 `v2 > 0` ⇒ **"slot 0"与"不在表里"同一答案**；而**零售 demo 自己显示 Factory 的 slot 0（实体 37）以 `eType 0` 到达而文件说 `6`** ⇒ **用线上行为否证文件那一行**。
10. **⚠ 发现一处真实缺口**：`SV_ConstBaselineBrushModelEntityNum` **没有 skip `slot 0`**，而 `zm_asylum_sh`/`zm_prototype_sh`/`zm_sumpf_sh`/`coop`/`dom`/`sd`/`sr` 七张表的 `slot 0` 携带 `brushModelIndex = 1` 或 `12` ⇒ **会返回一个客户端不可达的号**（`zm_factory_sh` 的 slot 0 `brush=0` 所以不触发）。
11. **⭐⭐⭐ `+3` 的带偏移不是常数**：`zm_factory_sh` 的一个群集上恰好 `+3`，而**零售的 perk 机器在 `248..279` 而其余 prop 在 `384..407`** ⇒ **两段注释互相推翻，后者是对的**。
12. **⭐⭐ "投票 ≥ 90% 才接受偏移，否则当成噪声"**（`best->second * 10 >= voters * 9`）："一个只大体一致的带不是一个带偏移，是噪声，而对噪声行动会把 prop 放到别的 prop 的实体号上"。
13. **⭐⭐⭐ `modelIndexOffset` 被计算、被打印、【没被使用**】** —— 它是一个纯仪器。**真正的解法是"把 baseline 的 xmodel 改成我们自己的值，让那个字段相等 ⇒ 不发送 ⇒ 客户端保留它自己解析的正确值"** —— **用一个恒等式让错误消失**。
14. **⭐⭐⭐ `0x02` 的两难**：**每一 FULL 帧都设 ⇒ 客户端第一次 ack 但在 `rearm`/`FULL` 间振荡（每次重复重启 `CL_FirstSnapshot`）**；**恰好一次 ⇒ 客户端根本不 ack（那一次落在地图加载中）** ⇒ **需要第三解：重复到 `baseline != nullptr` 这个协议内本来就有的信号出现，然后停**。
15. **⭐⭐ "用协议里本来就存在的信号，而不是发明一个超时"** —— 与 §404 的"demo 的 3.0 秒间隔是那个队列"**同族**。
16. **⭐⭐⭐ "一个不建模的字段就不再是无害的"**：不覆写 ⇒ 从表行继承 ⇒ **一个 prop 拿到速度与角速度 ⇒ 安静地漂移并旋转**（`475..480`）。
17. **⭐⭐⭐ "浮点以原始位模式携带，因为按精确相等比较；一个经过十进制字面量的有损往返会把一个安静的实体变成一个多话的实体"** —— 第三次精度问题。
18. **⭐⭐⭐ `SvConstBaselineTable` 必须按 `(map, gameType)` 键控**：`mp_nuked` 有 13 张表且 `dd` 排第一 ⇒ **只用 map 会给死斗服务器 domination 的编号**，而**编号就是身份**。
19. **"`_const.ff` 还在 `.ifs` 里 ⇒ 返回空 ⇒ 调用者必须退化到顺序编号而不是失败"** —— `AGENTS.md` 可信度第 1 级的数据，但覆盖不完整。
20. **`OLMOD_CONST_BASELINES=0` 的默认开 + 撤回开关**："`0x10` 不只是省带宽，它改变客户端画什么" —— 第三次"先能关再开"。

## 十一、未闭合点

- `mp_nuked` 的 `cha`/`war`/`tjugg`/`chicken` 四张表是否**逐字节相同**（号的集合相同）。
- `trang` 计数是 `8` 而注释只提 `6` —— 多出的两行是 `trType == 0` 但 `trTime != 0` 吗？
- `eType 0` 三条的实际语义（`eFlags = 0x11`）。
- `SV_ConstBaselineBrushModelEntityNum` 的 slot-0 缺口在哪些地图上实际发作。
- `modelIndexOffset` 是否应当被消费（当前是死值）。
- `PublishScriptModelsOnRetailNumbers = true` 是编译期常量而非开关。
- **下一步**：`sv_snapshot_mp.hpp`（266KB）。
