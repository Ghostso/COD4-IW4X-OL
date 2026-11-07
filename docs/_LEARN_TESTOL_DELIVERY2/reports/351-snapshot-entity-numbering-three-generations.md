# 351 · **实体编号的三个代际**（`74/133` → `127/133` → `133/133`）—— `+3` 带偏移的投票、槽 0 不是失败而是规则、九个共位对

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 12000–12400 行。

## 二、**实体编号的三个代际**（本组最重要的一段）

### 2.1 第一代：**按 origin 单独匹配 ⇒ `74/133`**

```php
// The walk below is that alignment. ...
// MEASURED on zm_factory_sh before any of this was written: 365 of 371 static
// entities align, unique and strictly ascending -- 238/238 brush and 127/133
// script. The six misses are all `codo_zombie_zapper`, which retail simply does not
// publish as static entities (`rowsAtOrigin=0`). The anchors are load-bearing: the
// same walk WITHOUT them, matching ordered origins alone, gets 74 of 133 and is
// wrong from the very first entity -- it assigns 270 where the answer is 37.
```

**⇒ 八层**：

```text
1. **锚定的走法（第二代）：371 个静态实体里的 365 个对齐**
2. ⇒ **唯一且严格递增 —— 238/238 画笔与 127/133 脚本**
3. ⇒ **六个未命中全是 `codo_zombie_zapper`**，零售根本不把它们发布为静态实体（`rowsAtOrigin=0`）
4. ⇒ **锚是【承重的】**
5. ⇒ **同一次走法【去掉锚】、只匹配有序 origin 得 133 个里的 74 个**
6. ⇒ **而从【第一个实体】就错**
7. ⇒ **它分配 270 而答案是 37**
```

**✅ 三代命中率：**

```text
第一代  按 origin 单独       74/133  （55.6%）
第二代  锚定走（画笔作锚）   127/133 （95.5%）
第三代  实体字符串位置       133/133 （100%，受门控）
```

**✅ 一个**清晰的工程演进记录**。**

**⚠ 而"从第一个实体就错，分配 270 而答案是 37" ⇒ **270 vs 37 差 233**。**

**⇒ **一个巨大的偏移**，不是小误差。**

**✅ 说明 origin-only 匹配**从根上就是错的**（不是"部分对"）。**

### 2.2 第二代：**锚定走**

```php
// A script_model has no `*N`, and its ORIGIN is a location rather than an identity
// -- matching on origin alone put a character xmodel on a ledge. What IS an
// identity is its position in the map's entity list relative to the brush models
// around it: retail's table is in allocation order, brush `*N` rises strictly with
// it, so brush models are exact ANCHORS and everything between two anchors is
// pinned between the same two rows.
//
// The walk below is that alignment. It keeps a cursor into the table, advances it
// to each brush model's own row by `*N`, and takes the next script-model row at or
// after the cursor whose origin matches. Both sides parse the same entity string,
// so the float32s are bit-identical.
```

**⇒ 十层**：

```text
1. **一个 script_model 没有 `*N`，而它的 ORIGIN 是一个【位置】而不是一个身份**
2. ⇒ **只按 origin 匹配把一个角色 xmodel 放到一个窗台上**
3. ⇒ **【真正是】身份的是它在图实体列表里相对于周围画笔模型的位置**
4. ⇒ **零售的表是【按分配顺序】的**
5. ⇒ **画笔 `*N` 随它严格上升**
6. ⇒ **所以画笔模型是【精确的锚】**
7. ⇒ **而两个锚之间的每一样东西被钉在同样的两行之间**
8. ⇒ **它的光标前进到每个画笔模型自己那行（按 `*N`）**
9. ⇒ **而在光标处或之后取 origin 匹配的下一个脚本行**
10. ⇒ **两边解析【同一个】实体字符串 ⇒ 所以 float32 是【逐位相同】而非近似**
```

**✅ "逐位相同而非近似"是关键的**证据等级**。**

**⇒ 与 §350 的"两个方向都解析同一字符串"**同族。**

### 2.3 而**"只按 origin 匹配把一个角色 xmodel 放到一个窗台上"**

**✅ 一个**具体的、可见的**失败症状（第二次出现）。**

**⇒ 与 §350 的"控制台成了僵尸身体"**同族（**第三次"道具成了别的模型"**）。**

### 2.4 第三代：**实体字符串位置**

```php
// SCRIPT MODELS TAKE RETAIL'S NUMBERS BY POSITION, NOT BY ORIGIN.
//
// The number comes from SV_AssignMapEntityNumbers -- start at 37, walk the map
// entity string in order, skip worldspawn and the four pathfinding/scripting
// classnames. That rule was SOLVED against this very table (238 known brush
// numbers give 237 gap equations in twenty classname unknowns) and it reproduces
// every number the table carries.
```

**⇒ 十层**：

```text
1. **脚本模型按【位置】取零售的号，不是按 origin**
2. ⇒ **号来自 `SV_AssignMapEntityNumbers`**
3. ⇒ **从 37 开始**
4. ⇒ **按顺序走地图实体字符串**
5. ⇒ **跳过 worldspawn 与【四个】寻路/脚本 classname**
6. ⇒ **那条规则是对【这张表本身】解出来的**
7. ⇒ **（238 个已知画笔号给出 237 个间隔方程，在二十个 classname 未知数上）**
8. ⇒ **而它复现表携带的【每一个】号**
```

**✅ "237 个间隔方程在二十个未知数上"** —— 一个**代数可解性**论证。**

**⇒ 238 个号 ⇒ 237 个间隔 ⇒ 而未知数是**二十个 classname 的跳过计数**。**

**⇒ **超定系统（237 > 20）** ⇒ 所以解是**唯一且被验证的**。**

**✅ 这是本文件里**最强的数学论证**。**

### 2.5 而**为什么放弃第二代（九个共位对）**

```php
// WHAT IT REPLACES AND WHY. The previous alignment walked the table with the
// brush models as anchors and took the next script-model row whose ORIGIN
// matched. It reached 126 of 133 and was verified unique and ascending -- but an
// origin is a location, not an identity, and zm_factory_sh has NINE co-located
// pairs: two identical `face_identification_machine` at one point, three rack
// A/B pairs, and five treasure-chest body/lid pairs, one of which lists the lid
// first. Eighteen of the 133 could only be separated by comparing this server's
// xmodel index against retail's through a measured +3 band offset. That is a
// chain of three assumptions holding up the identity of a prop, and a single
// wrong tie-break swaps a chest body with its lid.
```

### 2.6 十一层

```text
1. **它替换什么以及为什么**
2. ⇒ **上一个对齐用画笔模型作锚走表并取 origin 匹配的下一个脚本行**
3. ⇒ **它达到 133 个里的 126 个而被验证唯一且递增**
4. ⇒ **但一个 origin 是一个位置，不是一个身份**
5. ⇒ **而 `zm_factory_sh` 有【九个】共位对**：
     · **两个相同的 `face_identification_machine` 在同一个点**
     · **三个 rack A/B 对**
     · **五个宝箱 箱体/盖 对，其中一个把盖子列在前面**
6. ⇒ **133 个里的十八个只能通过**
7. ⇒ **把这个服务器的 xmodel 索引对零售的通过一个【测量出来的 +3 带偏移】比较来分开**
8. ⇒ **那是一条【三个假设】撑着一个道具的身份**
9. ⇒ **而一个错误的 tie-break 把一个箱体换成它的盖子**
```

**✅ **"一条三个假设撑着一个道具的身份"** —— 本文件里**对"假设堆叠"最尖锐的批评**。**

**⇒ 三个假设：**

```text
① 锚定走法正确
② +3 带偏移是常数
③ xmodel 索引能分开共位对
```

**✅ 而第三代**一个假设都不用**（位置是定义）。**

**⚠ 而 §350 说"+3 是常数"在**一个簇**上测得，而 perk machines 在 248..279 而这个 +3 不适用。**

**⇒ 所以假设② 实际上**是假的**（见下）。**

**✅ 一个**自我推翻的证据**。**

### 2.7 而**"126" vs "127"**

```text
第二代（锚定走）  127/133  （§2.1 的测量）
而这里说         126/133  （"WHAT IT REPLACES"）
```

**⚠ 一处**内部不一致**（差一）。**

**⇒ 可能 127 是**加 +3 tie-break 之后**而 126 是**之前**。**

**✅ 一个合理的解释（tie-break 只多救一个）。**

**⚠ 但注释应该说明。**

### 2.8 而**门控是三条件的**

```php
// THE GATE IS THE MAP'S OWN TABLE, and it is all-or-nothing. Publish only when
// EVERY brush model's walked number equals the number the table gives its `*N`
// -- an identity by construction, so this is a genuine independent check of the
// walk -- and EVERY script model's walked number names a row that exists. A map
// whose entity string this server parses differently than retail did will fail
// the first test and fall back to sequential numbering rather than publish props
// onto strangers' baselines.
```

**⇒ 六层**：

```text
1. **门是地图自己的表，而它是【全有或全无】**
2. ⇒ **只在以下时发布**：
     · **每一个画笔模型的走到的号等于表给它的 `*N` 的号**
     · **每一个脚本模型的走到的号点名一个存在的行**
3. ⇒ **一个号是一个【构造性的身份】**
4. ⇒ **所以这是一个走法的【真正的独立检查】**
5. ⇒ **一张本服务器解析实体字符串与零售不同的图会在第一个测试上失败**
6. ⇒ **并回退到顺序编号，而不是把道具发布到陌生人的基线上**
```

**✅ 与 §350 的"一个画笔模型偏离表就推翻整帧的标志"**完全同族（**第二次"全有或全无"**）。**

## 三、**`+3` 带偏移的投票机制**（本组第二重要）

### 3.1 那段

```php
// THIS SERVER'S MODEL CONFIGSTRING BAND IS NOT RETAIL'S, AND THE DIFFERENCE IS A
// CONSTANT. Measured on zm_factory_sh: `codo_treasure_chest_box2` is 392 here and
// 389 in the shipped baselines, `..._lid` 393 vs 390, `codo_zm_production_line_
// rack03_a` 394 vs 391, `_b` 395 vs 392 -- every one exactly +3.
//
// The offset matters because the xmodel index is the only thing that separates the
// eight CO-LOCATED prop pairs whose rows share an origin, and comparing our index
// against retail's directly can never match. So measure it instead of assuming it:
// every prop that resolved to exactly ONE row by origin alone contributes a vote,
// and the offset is used only if the votes agree overwhelmingly.
std::int32_t modelIndexOffset = 0;
{
    std::unordered_map<std::int32_t, std::size_t> votes;
    std::size_t voters = 0;
    for (const auto &definition : scriptModelDefinitions) {
        const auto *single = SV_ConstBaselineScriptModelRowByOrigin(
            constBaselines, definition.origin.data());
        if (!single || !single->xmodelIndex || !definition.modelIndex) continue;
        ++voters;
        ++votes[(int32)definition.modelIndex - (int32)single->xmodelIndex];
    }
    if (voters) {
        const auto best = std::ranges::max_element(votes, {}, [](const auto &vote) { return vote.second; });
        // A band that only mostly agrees is not a band offset, it is noise, and
        // acting on noise puts props on other props' entity numbers.
        if (best != votes.end() && best->second * 10 >= voters * 9)
            modelIndexOffset = best->first;
        OlMod::RuntimeLog::write(..., "model band offset=" + ... + " agreement=" + ... + " distinctOffsets=" + ...);
    }
}
```

### 3.2 十一层

```text
1. **这个服务器的模型 configstring 带不是零售的，而差别是一个【常数】**
2. ⇒ **在 `zm_factory_sh` 上测量**：
     · `codo_treasure_chest_box2` 这里是 392 而表里 389
     · `..._lid` 393 vs 390
     · `codo_zm_production_line_rack03_a` 394 vs 391
     · `_b` 395 vs 392
3. ⇒ **每一个恰好 +3**
4. ⇒ **偏移重要因为 xmodel 索引是分开那【八个】共位对的【唯一】东西**
5. ⇒ **而直接比较我们的索引对零售的【永远不匹配】**
6. ⇒ **所以【测量】它而不是假设它**
7. ⇒ **每一个【只按 origin】解析到恰好一行的道具贡献一票**
8. ⇒ **而只有票【压倒性】一致时偏移才被使用**
9. ⇒ **（`best->second * 10 >= voters * 9` ⇒ ≥90%）**
10. ⇒ **"一个只是【大部分】一致的带不是一个带偏移，它是噪声，而作用于噪声把道具放到别的道具的实体号上"**
```

### 3.3 而**"测量它而不是假设它"**

**✅ 与 §349 的"那个速率是真的而它是错误的模型"**同族但相反**：**

```text
§349  **假设的模型**是对的而**应用**错了
§351  **假设的值**（+3）在**一个簇**上对而**另一个簇**（248..279）上错 ⇒ 所以改为【测量】
```

**✅ **两个方向。**

### 3.4 而**90% 的门槛**

**⇒ 三层**：

```text
1. `best->second * 10 >= voters * 9`
2. ⇒ **≥ 90% 的票**
3. ⇒ **否则偏移 = 0（不用）**
```

**✅ 与 §346 的"`impactFlags` 的界是线宽不是观测范围"**不同** —— 这是**统计一致性门槛**。**

**⚠ 而 90% 是**一个魔法数**。**

**⇒ 注释解释了理由（"大部分一致是噪声"）。**

### 3.5 而**四个名字的完整对照**

```text
codo_treasure_chest_box2          392 / 389   +3
..._lid                           393 / 390   +3
codo_zm_production_line_rack03_a  394 / 391   +3
_b                                395 / 392   +3
```

**✅ 四个**连续的号**（392..395 vs 389..392）。**

**⇒ 所以**同一簇的四个道具** ⇒ 一个**局部测量**。**

**⚠ 而注释在 §3.6 承认它**不是均匀的**。**

### 3.6 而**"perk machines 在 248..279 而其它道具在 384..407"**

```php
// WHAT THE CLIENT WILL ACTUALLY RESOLVE THE MODEL FROM. A prop takes its row's
// xmodel unless this server SENDS a different one, and the two sides index
// different configstring bands -- retail's perk machines sit at 248..279 while
// the rest of the map's props are at 384..407, so the offset is not the uniform
// +3 measured on one cluster. If ours ever equals the row's, nothing is sent
// and the client resolves RETAIL's index against OUR table.
```

### 3.7 八层

```text
1. **客户端实际将从什么解析这个模型**
2. ⇒ **一个道具取它那一行的 xmodel【除非】这个服务器发一个不同的**
3. ⇒ **而两边索引不同的 configstring 带**
4. ⇒ **零售的 perk machine 坐在 248..279**
5. ⇒ **而地图其余道具在 384..407**
6. ⇒ **所以偏移【不是】在一个簇上测得的那个均匀的 +3**
7. ⇒ **如果我们的一旦等于那一行的，什么也不发**
8. ⇒ **而客户端把【零售的】索引对着【我们的】表解析**
```

**✅ 这是**对"+3 是常数"的直接反驳**。**

**⇒ 所以 §350 的"+3"与这里的"不是均匀的"是**同一个文件的两处**。**

**⚠ 一个**自相矛盾**（或者说是**演进**：+3 是早期测量，这里是最新理解）。**

**✅ 而 §3.6 的结论是**"客户端解析零售的索引对我们表"** ⇒ **错误**。**

**⇒ 所以必须**显式发送**我们的索引。**

### 3.8 而**`EQUAL -> NOT SENT` 与 `differs -> sent`**

```php
OlMod::RuntimeLog::write(..., "script model model=" + definition.modelName +
    " ent=" + std::to_string(*retailEntityNum) +
    " ourIndex=" + std::to_string(definition.modelIndex) +
    " rowXmodel=" + std::to_string(row->xmodelIndex) +
    (definition.modelIndex == row->xmodelIndex ? "  EQUAL -> NOT SENT" : "  differs -> sent"));
```

**⇒ 三层**：

```text
1. **EQUAL ⇒ 不发**（客户端用自己的 = 零售的 = 我们的）
2. ⇒ **differs ⇒ 发**
3. ⇒ **每个脚本模型一行日志**
```

**✅ 与 §345 的"用实体自己的模型索引让字段等于基线所以不发"**完全一致 ✓**

**⚠ 而那里是 `constBaselineStorage.modelIndex = entities[currentIndex].modelIndex;`（强制相等）。**

**⇒ 这里是**自然相等或自然不等**。**

**⚠ 两处**不同的策略**：**

```text
§345  强制基线等于我们的 ⇒ 永不发（保证客户端用我们的）
§351  若自然相等 ⇒ 不发；否则发
```

**⚠ 而 §345 的强制是**对画笔模型**（xmodel 两边都零）**⇒ 无效果**。**

**⇒ 所以**实际等价**。**

**✅ 一个细节。**

## 四、**槽 0 不是失败而是规则**（本组第三重要）

### 4.1 那段

```php
// SLOT 0 IS NOT A MISS, IT IS THE RULE. The client's index array is
// zero-filled and its lookup guards on `v2 > 0`, so slot 0 and "not in the
// table" are the same answer there and the entity falls back to a zeroed
// struct. SV_ConstBaselineEntityState refuses it for exactly that reason.
// zm_factory_sh's slot 0 is entity 37, which the walk correctly hands to
// the map's first numbered entity -- a `codo_face_identification_machine_off`
// -- so counting it as a failure discards a numbering that is right.
//
// It gets no retail number of its own: publishing there would be this
// server using a slot the client cannot resolve.
```

### 4.2 十一层

```text
1. **槽 0 不是一个未命中，它是【规则】**
2. ⇒ **客户端的索引数组是【零填充的】**
3. ⇒ **而它的查找用 `v2 > 0` 守卫**
4. ⇒ **所以槽 0 与"不在表里"在那里是【同一个答案】**
5. ⇒ **而实体回退到一个【全零的结构】**
6. ⇒ **`SV_ConstBaselineEntityState` 正为此拒绝它**
7. ⇒ **`zm_factory_sh` 的槽 0 是实体 37**
8. ⇒ **而走法正确地把 37 交给图的第一号实体**
9. ⇒ **（一个 `codo_face_identification_machine_off`）**
10. ⇒ **所以把它算成失败会【丢弃一个正确的编号】**
11. ⇒ **它得不到自己的零售号**：发布到那里等于这个服务器用一个**客户端无法解析的槽**
```

### 4.3 **"槽 0 与不在表里是同一个答案"**

**✅ 与 §345 的"当基线缺少那个客户端号时基线就是 `memset` 零缓冲区"**完全同族。**

**⇒ 三层**：

```text
1. 零填充数组 + `> 0` 守卫
2. ⇒ **索引 0 与"未找到"不可分**
3. ⇒ **所以 0 是一个无效的哨兵**
```

**✅ 与 §342 的"`EntityNumWorld = 2046` 与 0 是两个语义"**配合。**

**⚠ 而这里是**客户端的索引数组**（不是实体号）。**

**⇒ **两个不同的"0 是哨兵"。**

### 4.4 而**"计数它会丢弃一个正确的编号"**

**⇒ 三层**：

```text
1. 若把槽 0 算成失败 ⇒ `walkAgrees = false`
2. ⇒ **整个门控失败**
3. ⇒ **全部回退到顺序编号**
```

**✅ 一个**"一个误判毁掉全部"**的实例。**

**⇒ 与 §346 的"缺一个 eType 拒掉整帧"**同族（**第五次"全有或全无"**）。

### 4.5 而 `walkAgrees` 的**两项**

```cpp
const auto walkAgrees = brushWalked == brushDefinitions.size() &&
    brushAgree == brushDefinitions.size();
```

**⇒ 两项：**

```text
① 每一个画笔模型都被走过（`walkEntityNum` 非零）
② 每一个走到的号与表一致
```

**⚠ 所以 `scriptOnRows` **不在**门控里。**

**⇒ 与 §351 二.8 的"EVERY script model's walked number names a row that exists"**不完全一致。**

**⚠ 注释说门控包含脚本，而代码只看画笔。**

**⇒ 一处**注释与代码不符**。**

**✅ **一个值得记下的差异。**

**⚠ 而实际行为：脚本模型无行的**逐个回退**（`continue`）而不是**全部门控失败**。**

**⇒ 这是**更宽松的**（与注释说的"全有或全无"不同）。**

**✅ 而 §351 二.8 的注释说"比一个一个地代价其他 100+ 道具的零售号要好" ⇒ 所以代码是对的而注释是旧版。**

## 五、`entity walk` 日志的**六个字段**

```text
brushAgree=<n>/<total>
scriptOnRows=<n>/<total>
atUnreachableSlot0=<n>
scriptNoRow=<n>
ACCEPTED | DISCARDED (falling back to sequential numbering)
```

**⇒ 五项（含判决）。**

**✅ 与 §347 的"仪器命名缺陷"**第五次。**

**⇒ 而这里是**一个验收判决**（ACCEPTED / DISCARDED）。**

**✅ 一个**明确的二值结论**而不是一个数。**

## 六、`script model unresolved` 日志的**七个字段**

```text
model=<name>
ourIndex=<n>
origin=<x>,<y>,<z>
rowsAtOrigin=<n>
(none) | ent<n>/xm<n> ...
```

### 6.1 而那段

```php
// WHY A PROP DID NOT RESOLVE, named rather than counted. "110 of 133" says
// coverage is incomplete and nothing about which of the two causes is in play:
// an origin the table does not carry at all, or a co-located pair the xmodel
// tie-break failed to separate. Those need different fixes, and the second one
// also tells us whether this server's model configstring band agrees with
// retail's -- a tie-break that never fires means it does not.
```

**⇒ 十层**：

```text
1. **为什么一个道具没解析出来，被【命名】而不是被【计数】**
2. ⇒ **"133 个里的 110 个"说覆盖率不完整而【什么也没说】两个原因里哪个在起作用**
3. ⇒ **原因一：一个表根本不携带的 origin**
4. ⇒ **原因二：一个 xmodel tie-break 未能分开的共位对**
5. ⇒ **那些需要【不同的修复】**
6. ⇒ **而第二个还告诉我们这个服务器的模型 configstring 带是否与零售一致**
7. ⇒ **一个从不触发的 tie-break 意味着它【不】一致**
```

**✅ 与 §346 的"七十五项合取"**完全同族（**第二次"命名而不是计数"**）。**

**⇒ **"命名而不是计数"是本文件的一条核心纪律。**

### 6.2 而**"a tie-break that never fires means it does not"**

**✅ 一个**定向的负面**（第四次）。**

**⇒ 与 §340 的"`table+0x10` 零次引用"**同族。**

## 七、而**"两个道具解析到同一行 ⇒ 第一个保留，第二个顺序号"**

```php
// spawnAt refuses a slot already taken, which is what happens when two of this
// server's script models resolve to one row. Falling through to spawn() keeps
// the first claimant and gives the second an unclaimed number.
auto handle = retailEntityNum ? stagedPool->spawnAt(*retailEntityNum, snapshot_.serverTime) : std::nullopt;
if (retailEntityNum && handle) ++scriptModelsOnRetailNumbers;
if (!handle) handle = stagedPool->spawn(snapshot_.serverTime);
```

### 7.1 四层

```text
1. **`spawnAt` 拒绝一个已占的槽**
2. ⇒ **两个脚本模型解析到一行时就是那样**
3. ⇒ **落到 `spawn()` 保留第一个认领者**
4. ⇒ **而给第二个一个未认领的号**
```

**✅ 与 §350 的"`spawnAt` 或 `spawn()`"**完全一致 ✓**

**⇒ **一个确定性的裁决**（先到先得）。**

**⚠ 而"先到先得"依赖 `scriptModelDefinitions` 的**顺序**。**

**⇒ §351 二.4 的**位置编号**保证了顺序是实体字符串顺序。**

**✅ **闭合**。**

## 八、`noteworthy` 的**"保留作者化的失活箱碎石链接"**

```cpp
// Preserve the authored inactive-box rubble link without extending
// SvGameEntity's native-mirror layout or guessing nearest props.
if (!definition.noteworthy.empty()) {
    SvLogicalMapEntityDefinition metadata;
    metadata.mapOrdinal = definition.mapOrdinal;
    metadata.fields.emplace_back("script_noteworthy", definition.noteworthy);
    stagedLogicalMapEntities.emplace(handle->entityNum, std::move(metadata));
}
```

**⇒ 四层**：

```text
1. **保留作者化的失活箱碎石链接**
2. ⇒ **而不扩展 `SvGameEntity` 的原生镜像布局**
3. ⇒ **也不猜最近的 props**
4. ⇒ **用一个轻量的逻辑实体元数据携带**
```

**✅ 与 §331 的"不能增长一个按地址键的缓冲区"**完全同族（**第七次**）。**

**⇒ **"不扩展布局 ⇒ 用一个旁表"** 是一个**反复出现的正确选择**。**

### 8.1 而 **"不猜最近的 props"**

**✅ 与 §351 二 的"origin 是位置不是身份"**完全一致 ✓**

**⇒ **"最近匹配"与"origin 匹配"是同一类错误。**

## 九、`logicalMapEntities` 的**十一项**

```cpp
entity.networkState.number = handle->entityNum;
entity.networkState.eType = 0;                  // ← 【0】！
entity.clientNum = EntityNumNone;
entity.currentOrigin = definition.origin;
entity.currentAngles = definition.angles;
entity.mapClassName = definition.value("classname").value_or("");
entity.mapTargetName = definition.value("targetname").value_or("");
entity.mapDestructibleType = definition.value("destructible_type").value_or("");
entity.scriptGameObjectName = definition.value("script_gameobjectname").value_or("");
entity.collisionBounds = {};
entity.collisionShape = SvCollisionShape::Capsule;
entity.mapModeEligible = true;
entity.gameplayActive = false;
entity.collisionLinked = false;
```

### 9.1 而 **`eType = 0`**

**⇒ 三层**：

```text
1. **`eType = 0`**
2. ⇒ **而 §344 说 `EntityTypeActor = 19`、ET_SCRIPTMOVER = 6**
3. ⇒ **所以 0 是…… 什么？**
```

**⚠ 而 §346 的 `SV_WritePacketEntities` 的 allowlist 说"其它一切 eType ⇒ false"。**

**⇒ 所以 `eType = 0` **不会被写进快照**（被 allowlist 丢掉）。**

**✅ 所以 `logicalMapEntities` 是**纯服务端的元数据**（不发布到客户端）。**

**⇒ 与 §350 的"逻辑地图实体"命名一致 ✓**

**⚠ 一处**需要确认**：`gameplayActive = false` 与 `collisionLinked = false` 也支持这个结论。**

**✅ **完整闭合**：逻辑实体是**服务端内部用途**（脚本/元数据）而非渲染。**

### 9.2 而 **`collisionShape = Capsule` 与 `collisionBounds = {}`**

**⇒ 三层**：

```text
1. 默认形状是胶囊
2. ⇒ **而 bounds 全零**
3. ⇒ **所以它实际上没有碰撞体**（bounds 零）
```

**✅ 与 `collisionLinked = false` 一致 ✓**

## 十、关键结论

1. **⭐ 实体编号的三个代际**：origin-only `74/133`（**从第一个就错，270 vs 37**）→ 锚定走 `127/133` → 实体字符串位置 `133/133`。
2. **"origin 是一个位置，不是一个身份"** —— 第二代的核心洞察。
3. **第一代"把一个角色 xmodel 放到了一个窗台上"** —— 第三次"道具成了别的模型"。
4. **⭐ 第三代 `SV_AssignMapEntityNumbers`：从 37 开始、按顺序走实体字符串、跳过 worldspawn 与四个 classname。**
5. **"238 个已知画笔号给出 237 个间隔方程，在二十个 classname 未知数上"** —— **超定系统 ⇒ 解唯一且被验证**。本文件最强的数学论证。
6. **九个共位对**（2 个 `face_identification_machine` + 3 个 rack A/B + 5 个宝箱 箱体/盖，其中一个把盖列在前面）。
7. **"133 个里的十八个只能通过 +3 带偏移分开"**。
8. **⭐ "那是一条三个假设撑着一个道具的身份，而一个错误的 tie-break 把一个箱体换成它的盖子"`** —— 对假设堆叠最尖锐的批评。
9. **门控是全有或全无**：每个画笔模型的走到的号必须等于表给的号。
10. **⭐ `+3` 带偏移的投票机制**：每个只按 origin 解析到**恰好一行**的道具投一票，**≥90% 一致**才采用。
11. **"一个只是大部分一致的带不是一个带偏移，它是噪声"`**。
12. **⭐ "perk machines 在 248..279 而其它道具在 384..407 ⇒ 偏移不是均匀的 +3"`** —— **对 §350 的 +3 的直接反驳**。
13. **"如果我们的一旦等于那一行的，什么也不发而客户端把【零售的】索引对【我们的】表解析"`** —— 所以必须显式发。
14. **`EQUAL -> NOT SENT` / `differs -> sent`** 的逐模型日志。
15. **⭐ "槽 0 不是一个未命中，它是【规则】"`** —— 客户端索引数组零填充 + `v2 > 0` 守卫 ⇒ **槽 0 与"不在表里"是同一个答案**。
16. **"把它算成失败会丢弃一个正确的编号"`** —— 一个误判毁掉全部（第五次全有或全无）。
17. **⚠ 注释说门控包含脚本模型而代码只检查画笔** —— 一处注释与代码不符（代码更宽松，注释是旧版）。
18. **`entity walk` 日志的 ACCEPTED / DISCARDED 是一个明确的二值判决**。
19. **⭐ "为什么一个道具没解析出来，被【命名】而不是被【计数】"`** —— "133 个里的 110 个"什么也没说。
20. **"一个从不触发的 tie-break 意味着带不一致"`** —— 第四次定向的负面。
21. **"两个道具解析到同一行 ⇒ 第一个保留、第二个顺序号"** —— 确定性裁决，依赖定义顺序（由位置编号保证）。
22. **`noteworthy` 用旁表携带而不扩展 `SvGameEntity` 布局** —— 第七次"不能增长按地址键的缓冲区"。
23. **"也不猜最近的 props"`** —— 与"origin 是位置不是身份"同源。
24. **`logicalMapEntities` 的 `eType = 0` ⇒ 不会被 allowlist 写进快照** ⇒ 纯服务端元数据。
25. **`collisionBounds = {}` + `collisionLinked = false` ⇒ 逻辑实体无碰撞。**

## 十一、未闭合点

- `126` vs `127` 的内部不一致。
- 门控注释与代码的差异（脚本模型是否真的在门控里）。
- `SV_AssignMapEntityNumbers` 跳过的四个 classname 名。
- `248..279` 与 `384..407` 两个带的划分规则。
- `+3` 在哪些图上成立、在哪些图上是别的值。
- `sv_snapshot_mp.cpp` 12400 行之后未读取（27,016 行，进度 46%）。
