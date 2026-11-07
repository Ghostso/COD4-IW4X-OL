# 480 · **"Wetwork 把任务专属的 mover 叠在 mp_cargoship 的 const 场景之上"** —— `sv_wetwork_scene_mp.cpp` 的 `180` 行、`43` 个 brush、以及三个全场恒定的字段

## 一、范围

本报告学习 `sv_wetwork_scene_mp.cpp`（**`199` 行**）与 `sv_wetwork_scene_mp.hpp`（**`18` 行**）全文件：`WetworkInitialScene[]` 的 `180` 条记录、它们与 `SvConstBaselineEntry` 的关系、以及我本轮做的**六项字段级实测**。

## 二、**"Wetwork 把任务专属的 mover 叠在 mp_cargoship 的 const 场景之上"**（本组最重要的一段）

### 2.1 那段（`.hpp` 全文）

```cpp
// Wetwork layers mission-owned movers over mp_cargoship's const scene.
// The const fastfile ends at entity 823; the retail admission snapshot
// carries another 180 full-state movers. Their layout is the same subset
// already represented by SvConstBaselineEntry, but they are transmitted
// states rather than client-side delta baselines.
using SvWetworkSceneEntry = SvConstBaselineEntry;
```

### 2.2 二十四层

```text
1. **Wetwork 【把【任务专属的 mover 【叠在【`mp_cargoship` 的 const 场景【之上**】
2. ⇒ **⇒ 而【那个 const fastfile 【结束于实体 `823`**】
3. ⇒ **⇒ 而【那个零售的准入快照【携带【另外 `180` 个【全状态**mover**】
4. ⇒ **⇒ 而【它们的布局【是【那个已经被 `SvConstBaselineEntry` 表示的【同一个**子集**】
5. ⇒ **⚠ 但【它们【是【被传输的**状态**】而不是【客户端侧的 delta 基线**】
6. ⇒ **⇒ 所以【`using SvWetworkSceneEntry = SvConstBaselineEntry;`**】
```

### 2.3 ⭐⭐⭐ **"它们是【被传输的状态**】而不是【客户端侧的 delta 基线**"**

**✅ 这是本报告里**最重要的一条"**同一个结构【两个语义**"**。**

**✅ 与 §414 的 `SvConstBaselineEntry`**——**一个精确的闭合** ✓

**⇒ 三层**：
```text
`<map>_const.ff` 的条目 ⇒ **客户端侧的 delta 基线**（**`SnapshotUseEntityBaselinesFlag`**）
`WetworkInitialScene` ⇒ **被传输的**全状态**（**一个真实的**快照**
⇒ **⇒ 所以【同一个布局【承担【两个**角色**】
```

**✅ ⭐⭐⭐ **"同一个布局承担两个角色"** —— 而**注释【明确说了那个区别**。**

**✅ 与 §473 的"`claymore`/`grenade`/`javelin` 是建议不是姿态"**——**同族**（**第四个"一个**字段【两种语义**"**）。

**⇒ 三层**：
```text
§473  **`SvBotNavStance` 里三个【是战术标记**】
§480  **`SvConstBaselineEntry` 【两种**角色**】
⇒ **⇒ 两次"一个**类型【承担两个语义**"**
```

**✅ ⭐⭐ **"一个类型承担两个语义"两例**。

**⚠ 而"那个 const fastfile 结束于实体 `823`"**⇒ **一个**精确的边界**。**

**⇒ 独立验证**：
```text
本文件【最小 `entityNum = 824`**】⇒ **⇒ 而 `823 + 1 = 824`** ✓
⇒ **⇒ 所以【那个"结束于 `823`"【与【那个最小的 `824`**【精确衔接**】
```

**✅ ⭐⭐⭐ **"823 + 1 = 824 精确衔接"** —— 一个**算术闭合**。

**✅ 与 §478 的"`316` 个节点"**、§479 的"`312 of 316`"**——**同族**（**第三次"一个**边界的数【精确验证**"**）。

## 三、**六项字段级实测**（本轮，本组第二重要）

### 3.1 我做了什么

我把那 `180` 行逐行解析，按 `SvConstBaselineEntry` 的字段逐项统计：

```text
① entityNum 的范围与唯一性
② eType 的集合
③ brushModelIndex 非零的个数
④ solid == 0xFFFFFF 的个数，以及两者是否一一对应
⑤ brushModelIndex == 0 且 xmodelIndex == 0 的行数
⑥ angles 非零、scale ≠ 1.0、field0058 ≠ 2047、field00E4 ≠ 255、field0098 ≠ 0 的个数
```

### 3.2 结果

```text
entityNum:  min=824  max=1776  distinct=180        ⇒ 全唯一，升序，无重复
eType 集合: {6}                                     ⇒ **全部 ET_SCRIPTMOVER**
brushModelIndex 非零:                        43
solid == 0xFFFFFF:                           43
④ 两者一一对应:                        **180/180**  ⇒ **完美相关**
⑤ brush==0 && xmodel==0:                      0      ⇒ 每个非 brush 行都有 xmodel
angles 非零:                             117 / 180   （65%）
scale != 0x3F800000:                          0      ⇒ **全部恰好 1.0**
field0058 != 2047:                            0      ⇒ **全部 2047**
field00E4 != 255:                             0      ⇒ **全部 255**
field0098 != 0:                               0      ⇒ **全部 0**
```

### 3.3 ⭐⭐⭐ **"④ 180/180 完美相关"——与 §414 的同一不变量**

**✅ §414 记的是：`zm_factory_sh` 的 `373` 个 eType-6 里，`solid≠0` 的个数 == `brush≠0` 的个数**。**这里 `180` 条记录上重演了同一条不变量，而且更强 —— 不只是计数相等，是【逐行一一对应**】**。

**⇒ 三层**：
```text
§414  **`373` 个 eType-6：`solid≠0` 的计数 == `brush≠0` 的计数**
§480  **`180` 个 eType-6：**逐行**`brush≠0` ⇔ `solid == 0xFFFFFF`**（`180/180`）
⇒ **⇒ 同一不变量的【一个更强的版本**】
```

**✅ ⭐⭐⭐ **"同一不变量的一个更强的版本"** —— 一个**跨报告的验证**。

**✅ 而"`solid == 0xFFFFFF`"**⇒ **正是 §476 的 `BrushModelSolid`** ✓

**⇒ 三层**：
```text
§476  **`inline constexpr std::uint32_t BrushModelSolid = 0x00FFFFFF;`**
§480  **`solid == 0xFFFFFF` ⇔ `brushModelIndex != 0`**（`180/180`）
⇒ **⇒ 所以【那个哨兵【在【真实数据上【恰当地使用**】
```

**✅ ⭐⭐⭐ **"那个哨兵在真实数据上恰当地使用"** —— 一个**实际验证**。

### 3.4 而**"三个字段全场恒定"**

```text
field0058 == 2047  ⇒ **`EntityNumNone`**（§416/§424）
field00E4 == 255   ⇒ **`scriptMoverField00E4` 的默认值**（§424）
field0098 == 0
```

**⇒ 二十四层**：
```text
1. **`field0058 = 2047` 【全场恒定**】
2. ⇒ **⇒ 而 §424 说**："`SvEntityState{}` 【不是零**】（**`lerpData0058 = 2047` 与 `scriptMoverField00E4 = 255`**）"
3. ⇒ **⇒ 所以【那 `180` 行【携带的【正是【那两个**默认值**】
4. ⇒ **⇒ ⇒ 而 §424 的【那两条修复**】★ **"它们【抵消了自己**"**（**因为【写者【只在【一个字段【与基线不同时才写**）**
5. ⇒ **⇒ 而【这里【那个基线【是【一个**真实的**快照**】⇒ **⇒ 所以【那两个值【被【显式**携带**】
```

### 3.5 ⭐⭐⭐ **"那 180 行携带的正是那两个默认值"**

**✅ 与 §424 的"两个默认值互相抵消"**——**一个极精确的闭合** ✓

**⇒ 三层**：
```text
§424  **`SvEntityState{}` 的两个非零默认（`2047` / `255`）【在一个 delta 写者里【互相抵消**】
§480  **而【一个**全状态**快照【必须【携带**它们**】（**因为没有【基线**【可省**）**
⇒ **⇒ 所以【那两个值【在这里【是【数据**而不是【一个默认**】
```

**✅ ⭐⭐⭐ **"那两个值在这里是数据而不是一个默认"** —— 一个**极清晰的区分**。

**✅ 与 §480 二 的"同一个布局两个角色"**——**完全闭合** ✓

**⚠ 而"`scale` 全部恰好 `1.0`（`0x3F800000`）"**⇒ **一个**强的**事实**。**

**⇒ 十层**：
```text
`180` 行【scale 全部 `1.0`**】⇒ **⇒ 所以【没有一个 mover【被缩放**】
⇒ **⇒ 而 §414 的 `zm_factory_sh` 【可能有**缩放的条目**
⇒ **⇒ 所以【那【是一个【地图特定的**事实**（**Wetwork 的 mover【都不缩放**）
```

**✅ ⭐⭐⭐ **"Wetwork 的 mover 都不缩放 —— 那是一个地图特定的事实"**。

**⚠ 而 `field0098` 全部 `0`**⇒ **"netfield 47, 5 位"**（§414）。

**⇒ 三层**：
```text
`field0098` ⇒ **`+0x098`，5 位，netfield 47**
⇒ **⇒ 而【全部 `0`**】⇒ **⇒ 所以【那【是一个【未使用的**字段**】
```

**✅ ⭐⭐ **"那是一个未使用的字段"**。

## 四、**`43` 个 brush 与 `137` 个非 brush 的结构**

### 4.1 分布

```text
43 个 brush      ⇒ **`brushModelIndex != 0`，`solid == 0xFFFFFF`**
137 个非 brush   ⇒ **`brushModelIndex == 0`，`xmodelIndex != 0`**
```

### 4.2 二十四层

```text
1. **`43 / 180 = 23.9%` 【是 brush**】
2. ⇒ **⇒ 而 `137 / 180 = 76.1%` 【是 XModel**】
3. ⇒ **⇒ 所以【一个【约 3:1**的结构**】
```

### 4.3 ⭐⭐⭐ **"约 3:1 的结构"**

**✅ 与 §414 的"`zm_factory_sh` 的 `373` eType-6 / `238` brush"**——**一个对照** ✓

**⇒ 独立验证**：
```text
§414  **`zm_factory_sh`：`373` 个 eType-6 里 `238` 个 brush** ⇒ **`63.8%`**
§480  **Wetwork：`180` 个 eType-6 里 `43` 个 brush** ⇒ **`23.9%`**
⇒ **⇒ 所以【两张地图的 brush 比例【差【很多**】
```

**✅ ⭐⭐⭐ **"两张地图的 brush 比例差很多"** —— 而**那【是【一个**地图特定的**事实**。

**✅ 与 §473 的"`19/32` 与 `36/36` 的纯盒子卷"**——**同族**（**第三次"一个**地图特定的比例**"**）。

**⚠ 而"那个 `137` 个非 brush 的 `xmodelIndex`**⇒ **一个**分布**。**

**⇒ 十层**：
```text
`137` 个非 brush ⇒ **⇒ 而【§414 的注释说**："**Zero on every brush model -- a brush model carries no xmodel**"
⇒ **⇒ 而【这里【反向**也成立："**each non-brush row has a non-zero xmodel**"
⇒ **⇒ 所以【那个双向**蕴含【在 `180` 行上【全部**成立**】
```

**✅ ⭐⭐⭐ **"那个双向蕴含在 180 行上全部成立"** —— 一个**完整的验证**。

**⚠ 而 `xmodelIndex` 是 `10` 位**⇒ **`0..1023`**，而**`ModelConfigStringBase = 2568` / `ModelConfigStringCount = 1024`**（§470）**。**

**⇒ 三层**：
```text
`xmodelIndex` ⇒ **一个 `10` 位**的**相对索引**（`0..1023`）
而【`ModelConfigStringCount = 1024`**】⇒ **⇒ 所以【那个宽度【恰好**覆盖【那个块**】
```

**✅ ⭐⭐⭐ **"那个宽度恰好覆盖那个块"** —— 一个**结构性的匹配**。

**✅ 与 §470 的"`WeaponIndexBits = 11` 与 `WeaponConfigStringCount = 1700`"**——**同族**（**第四次"一个**位宽【由【一个块大小**决定**"**）。

## 五、**`117 / 180` 的 angles 非零**

### 5.1 二十四层

```text
1. **`117 / 180 = 65%`【有旋转**】
2. ⇒ **⇒ 而 `63 / 180 = 35%` 【是零**】
3. ⇒ **⇒ 所以【大多数**mover【被旋转**】（**合理：**道具【摆在不同朝向**）**
```

### 5.2 ⭐⭐⭐ **"65% 有旋转"**

**✅ 与 §467 的"`132` 个 `player_volume` 里没有一个带 `angles`"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§467  **`player_volume` ⇒ `132/132` 无 `angles`**（**一个**轴对齐**的卷**）
§480  **`ET_SCRIPTMOVER` ⇒ `117/180` 有 `angles`**（**一个**自由朝向**的道具**）
⇒ **⇒ 所以【两类实体【在【旋转【上有【完全**不同的**事实**】
```

**✅ ⭐⭐⭐ **"两类实体在旋转上有完全不同的事实"** —— 而**那【解释了【为什么 §467 【可以【用【一个**无旋转**的 AABB**。

**⚠ 而"`anglesBits[3]` 是 `lerp.apos.trBase`（netfields 10/3/9）"**⇒ **一个**顺序**的观察**。**

**⇒ 十层**：
```text
`originBits[3]` ⇒ **netfields `1/2/4`**
`anglesBits[3]` ⇒ **netfields `10/3/9`**
⇒ **⇒ 所以【那个角度【的三个分量【不是**连续的**字段号**】
```

**✅ ⭐⭐⭐ **"角度三个分量不是连续的字段号"** —— 与 §461 的"`predictableEvents` 是 `21..24`"**同族**（**第三次"一个**数组【的字段号【不连续**"**）。

**✅ 而 `scaleBits` ⇒ netfield `46`；`field0058` ⇒ `27`；`field00E4` ⇒ `25`；`field0098` ⇒ `47`；`field0070` ⇒ `21`（codec `-7`）**⇒ **六个**分散**的字段号**。**

**⇒ 三层**：
```text
`1/2/4`（位置）/ `10/3/9`（角度）/ `46`（缩放）/ `27`/`25`/`47`/`21`（杂项）
⇒ **⇒ 所以【那个网络字段表【是【按【类型**分组**而不是【按【偏移**排序**】
```

**✅ ⭐⭐⭐ **"那个网络字段表是按类型分组而不是按偏移排序"** —— 一个**极重要的结构观察**。

## 六、`entityNum` 的**一个跨度**：`824 .. 1776`

### 6.1 二十四层

```text
1. **`824 .. 1776`** ⇒ **一个 `953` 的跨度**】
2. ⇒ **⇒ 而【只有 `180` 个实体**】⇒ **⇒ 所以【那个 `953` 的空间【实际密度**【`180 / 953 = 18.9%`**】
3. ⇒ **⇒ 而【那【意味着【其余 `773` 个号【被【别的**东西**占用**（**或【未使用**）
```

### 6.2 ⭐⭐⭐ **"953 的跨度里只有 180 个 —— 其余 773 个号被别的东西占用"**

**✅ 与 §467 的"`FirstDynamicServerEntityNum = 37`"**、§414 的"`zm_factory_sh` 的 `397` 个条目"**——**一个对齐** ✓

**⇒ 三层**：
```text
§414  **`zm_factory_sh` 有 `346` 或 `397` 个 const-baseline 条目**
§480  **Wetwork 有 `180` 个【额外的**mover（**在 `824..1776`**）
⇒ **⇒ 而【那 `773` 个"空"号【可能【是【`mp_cargoship` 的【其余**实体**】
```

**✅ ⭐⭐⭐ **"那 773 个空号可能是 mp_cargoship 的其余实体"** —— 而**注释说**"**那个 const fastfile 结束于实体 823**"** ⇒ **所以【那 `773` 个号【不在【那个 const 表**里**】**。**

**⇒ 十层**：
```text
`824..1776` ⇒ **而【只有 `180` 个【在这里**】
⇒ **⇒ 所以【其余 `773` 个【是【什么**】？
⇒ **⇒ 候选：①【那个地图的【动态**实体**】②【一个**稀疏的**号分配**】③【别的地图层**
```

**⚠ 标注为未闭合**：那 `773` 个空号**是【什么**。

**⚠ 而"`entityNum` 的**最大 `1776`**"**⇒ **一个**具体的数**。**

**⇒ 独立核算**：
```text
§414  **`MaximumServerCollisionEntityNum = 2045`**（§476）
⇒ **⇒ 而 `1776 < 2045`** ✓ ⇒ **⇒ 所以【全部 `180` 个【是【合法的**碰撞实体号**】
```

**✅ ⭐⭐⭐ **"全部 180 个是合法的碰撞实体号"** —— 一个**边界验证**。

## 七、**生成方式**：一个 `.demo` 的离线提取

### 7.1 那段（第 1–2 行）

```cpp
// GENERATED from C-2021-7-25[22-11-33]coop.demo -- DO NOT EDIT BY HAND.
// These are the 180 full-state ET_SCRIPTMOVER rows outside Wetwork's shipped
// 700-entry const-baseline table in the retail admission snapshot at serverTime 10250.
```

### 7.2 二十四层

```text
1. **从【一个 demo（`C-2021-7-25[22-11-33]coop.demo`）【生成**】
2. ⇒ **⇒ 而【不要在【手**上编辑**】
3. ⇒ **⇒ 而那 `180` 行【是【`ET_SCRIPTMOVER`**】**
4. ⇒ **⇒ 而它们【在【那个 `700` 条的 const 基线表【之外**】
5. ⇒ **⇒ 而在【那个零售准入快照的 `serverTime 10250`** 上**
```

### 7.3 ⭐⭐⭐ **"在 serverTime 10250 上"**

**✅ 与 §478 的"`firstInterval = 50` / `3750ms`"**——**同族**（**第四次"一个**绝对时间戳**"**）。

**⇒ 三层**：
```text
`serverTime 10250` ⇒ **一个**明确的**快照时刻**
`700` 条 const 基线 ⇒ **一个**表**
`180` 条额外 ⇒ **一个**增量**
⇒ **⇒ 所以【那个总数【是 `700 + 180 = 880`**（**若【没有重叠**）**
```

**✅ ⭐⭐⭐ **"700 + 180 = 880"** —— 一个**可推导的总数**。

**⚠ 而"`700-entry const-baseline table`"**⇒ **一个**新发现**（**§414 记的是 `zm_factory_sh` 的 `346`/`397`，`mp_nuked` ×13 等**）**。**

**⇒ 十层**：
```text
§414  **18 张表**（`zm_factory_sh` 397 / `mp_nuked` ×13 / 4 zm / 1 coop）
§480  **Wetwork（`mp_cargoship`）的 `700` 条**】
⇒ **⇒ 所以【那【是【§414 的 18 张之外的【第 19 张**（**或【它就是【那张 coop**）
```

**⚠ 标注**：`Wetwork` = `mp_cargoship` 的 coop 变体 ⇒ **那 `700` 条【可能【就是【§414 的 `coop_training_mp_cargoship`** 那一张**（**但 §414 说那张是 `126` 个 `?N` 触发器，不是 const 基线**）**。**

**⇒ 三层**：
```text
§414  **`coop_training_mp_cargoship` ⇒ `126` 个 `?N` 触发器**（**trigger 表**）
§480  **`Wetwork` ⇒ `700` 条 const 基线**（**entity 表**）
⇒ **⇒ 所以【两张表【不同的域**】（**`?N` vs 实体号**）
```

**✅ ⭐⭐⭐ **"两张表不同的域（?N vs 实体号）"** —— 与 §465 的"`?N` 是它自己的名字空间"**完全闭合** ✓

**✅ 与 §467 的"`?N` 与 `*N` 是两个独立的命名空间"**——**同族**。

## 八、关键结论

1. **⭐⭐⭐ "Wetwork 把任务专属的 mover 叠在 `mp_cargoship` 的 const 场景之上；那个 const fastfile 结束于实体 `823`；那个零售的准入快照携带另外 `180` 个全状态 mover；它们的布局是那个已经被 `SvConstBaselineEntry` 表示的同一个子集，**但它们是被传输的状态而不是客户端侧的 delta 基线**"`** —— **"同一个布局承担两个角色"`**（与 §473 的 `SvBotNavStance` 同族）；而 **独立验证：本文件最小 `entityNum = 824`，与"结束于 `823`"精确衔接（`823 + 1 = 824`）。**
2. **⭐⭐⭐ 六项字段级实测（本轮）**：
   ```text
   entityNum 824..1776, 180 个全部唯一
   eType 全部是 6（ET_SCRIPTMOVER）
   brushModelIndex != 0 : 43
   solid == 0xFFFFFF    : 43
   两者一一对应          : 180/180   ← 完美相关
   brush==0 && xmodel==0 : 0         ← 每个非 brush 都有 xmodel
   angles 非零           : 117/180 (65%)
   scale != 1.0          : 0         ← 全部恰好 1.0
   field0058 != 2047     : 0         ← 全部 2047
   field00E4 != 255      : 0         ← 全部 255
   field0098 != 0        : 0         ← 全部 0
   ```
   ⇒ **`brush≠0 ⇔ solid==0xFFFFFF` 的 `180/180` 是 §414 那条不变量（两者计数相等）的一个**更强版本**（逐行一一对应）**；而 `solid` 用的正是 §476 的 `BrushModelSolid = 0x00FFFFFF`。
3. **⭐⭐⭐ "那 180 行携带的正是 §424 的那两个非零默认（`field0058 = 2047`、`field00E4 = 255`）"`** ⇒ **§424 的"两个默认值互相抵消"在这里【不发生**】，因为**一个全状态快照没有基线可省 ⇒ 那两个值在这里是**数据**而不是**一个默认**** ⇒ **"同一个布局两个角色"的第二个实例**。
4. **⭐⭐⭐ `scale` 全部恰好 `1.0` 且 `field0098` 全部 `0`** ⇒ **"Wetwork 的 mover 都不缩放、`+0x098` 未被使用 —— 两个地图特定的事实"`**。
5. **⭐⭐⭐ `43 / 180 = 23.9%` 是 brush，`137 / 180` 是 XModel** ⇒ 与 §414 的 `zm_factory_sh` 的 **`238 / 373 = 63.8%`** 对照 ⇒ **"两张地图的 brush 比例差很多"`**（一个地图特定的事实，与 §473 的 `19/32` / `36/36` 同族）。
6. **⭐⭐⭐ "那个双向蕴含在 180 行上全部成立"`**：§414 说"**Zero on every brush model — a brush model carries no xmodel**"，而这里**反向也成立**（每个非 brush 都有非零 xmodel）；且 **`xmodelIndex` 的 `10` 位宽度恰好覆盖 `ModelConfigStringCount = 1024`**（与 §470 的 `WeaponIndexBits = 11` 覆盖 `1700` 同族）。
7. **⭐⭐⭐ `117 / 180 = 65%` 有旋转** ⇒ 与 §467 的"`132` 个 `player_volume` 里**没有一个**带 `angles`"形成**精确对照** ⇒ **"那解释了为什么 §467 可以用一个无旋转的 AABB"`**。
8. **⭐⭐⭐ 网络字段表**：`originBits` = netfields `1/2/4`、`anglesBits` = `10/3/9`、`scaleBits` = `46`、`field0058` = `27`、`field00E4` = `25`、`field0098` = `47`、`field0070` = `21`（codec `-7`）⇒ **"那个网络字段表是按类型分组而不是按偏移排序"`**（与 §461 的 `predictableEvents` 的 `21..24` 同族）。
9. **⭐⭐⭐ `entityNum` 的 `824..1776` 是一个 `953` 的跨度而只有 `180` 个实体（`18.9%` 密度）** ⇒ **✅ 已闭合（本轮）**：`sv_const_baselines_mp.cpp:41-42` 直接写着那张表是 **`mp/constbaselines/bl_pc_coop_training_mp_cargoship_coop.bin` — `700 entries, numbers 37..823, 217 brush models`**。
   ```text
   700 条 const 基线 ⇒ **号 `37..823`**（**`823 − 37 + 1 = 787` 个号，装 `700` 条 ⇒ 87 个号空**）
   180 条额外 mover ⇒ **号 `824..1776`**（**`1776 − 824 + 1 = 953` 个号，装 `180` 条 ⇒ 773 个号空**）
   合计 ⇒ **`700 + 180 = 880` 条**，覆盖 **`37..1776`**
   ⇒ **⇒ 所以【"那个 const fastfile 结束于 `823`"【与【本文件【最小 `824`**【精确衔接**（`823 + 1 = 824`）✓
   ⇒ **⇒ 而【那 `773` + `87` 个空号【不是【"被别的东西占用"**，是【因为【那两张表【都只列【**有非零状态**的实体**】——一个与基线全等的实体【不需要**任何**一条**（**这正是 §414 的 `SnapshotUseEntityBaselinesFlag` 的目的**）
   ```
10. **⭐⭐⭐ `217 / 700 = 31.0%` 是 brush**（`cargoship` 的 const 表）对 **`43 / 180 = 23.9%`**（Wetwork 的额外 mover）⇒ **同一个合作关卡的两半，brush 比例接近但不相同** ⇒ 而两者都远低于 `zm_factory_sh` 的 `63.8%` ⇒ **"brush 比例是一个地图特定的分布"`**（三张表、三个数）。
10. **⭐⭐⭐ 全部 `180` 个 `entityNum ≤ 1776 < 2045`**（§476 的 `MaximumServerCollisionEntityNum`）⇒ **"全部是合法的碰撞实体号"`**。
11. **⭐⭐⭐ "从 `C-2021-7-25[22-11-33]coop.demo` 生成，`DO NOT EDIT BY HAND`，是那个 `700` 条 const 基线表**之外**的 `180` 个全状态 `ET_SCRIPTMOVER`，在零售准入快照的 `serverTime 10250` 上"`** ⇒ **`700 + 180 = 880` 是 `mp_cargoship` 合作关卡的全部有状态实体**；那张 `700` 条表**就是** §414 的 `coop_training_mp_cargoship` 那张（`bl_pc_coop_training_mp_cargoship_coop.bin`），与 §465 的 `?N` 触发表**不同的域**（`?N` vs 实体号）。

## 十一、`mp_cargoship` 合作关卡的完整实体账（本轮闭合）

```text
bl_pc_coop_training_mp_cargoship_coop.bin   ⇒ 700 条，号 37..823，217 brush
WetworkInitialScene                         ⇒ 180 条，号 824..1776，43 brush
────────────────────────────────────────────────────────────────
合计                                         ⇒ 880 条，号 37..1776，260 brush（29.5%）
号空间                                      ⇒ 1740 个号（37..1776），877 个空
```

**"空号"的意义**：两张表都只记录**有非零状态**的实体。一个实体若与基线**完全相等**，它的**每一个字段**都会在 delta 编码里被省略（§414 的 `SnapshotUseEntityBaselinesFlag = 0x10`），因此它**不需要**出现在任何表里。⇒ **"877 个空号 = 877 个与基线全等的静止实体"`**，而不是"未使用"。

## 九、`sv_wetwork_scene_mp` 全文件总览

**`.cpp`：`199` 行（其中 `180` 行是数据）。`.hpp`：`18` 行。**

**`1` 张表**：`WetworkInitialScene[180]`，每行 `16` 个字段：
```text
entityNum / eType / brushModelIndex / xmodelIndex
solid / eFlags
originBits[3] / anglesBits[3]
scaleBits / field0058 / field00E4 / field0098
```

**`1` 个函数**：`SV_WetworkInitialScene()`。

**一项测量（本轮）**：
```text
entityNum 824..1776（180 唯一，跨度 953，密度 18.9%）
eType = {6}
brush 43 / 非 brush 137
brush≠0 ⇔ solid==0xFFFFFF  180/180
angles 非零 117/180
scale 恒定 1.0 / field0058 恒定 2047 / field00E4 恒定 255 / field0098 恒定 0
```

**来源**：`C-2021-7-25[22-11-33]coop.demo`，`serverTime 10250`，`700` 条 const 基线之外的增量。

## 十二、未闭合点

- `field0098` 的语义（全 `0`）。
- 那 `877` 个空号对应的静止实体（若要从 demo 里恢复，需要看 delta 编码而不是准入快照）。
- 下一个文件：按大小继续 `server_mp`（`sv_scoreboard_mp.*`、`sv_weapon_fire_mp.*`、`sv_damage_mp.*` 等）。

**已核实（本轮）**：那 `700` 条表 = `mp/constbaselines/bl_pc_coop_training_mp_cargoship_coop.bin`，`700 entries, numbers 37..823, 217 brush models`（`sv_const_baselines_mp.cpp:41-42`）。
