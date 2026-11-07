# 390 · **"`0x4000` 而那上面曾经放着的注释说的【正好相反】—— 自信地，带着地址"** —— `sub_BD7780` 是 dvar 注册器、`alpha 25 × 8 = 200`、`spm = 35 + 5×rank`

## 一、范围

本报告学习 `sv_main_mp.cpp` 300–650 行。

## 二、**`0x4000` 的完整误引记录**（本组最重要的一段）

### 2.1 那段

```cpp
// FLAGS ARE 0x4000, AND THE COMMENT THAT USED TO BE HERE SAID
// THE OPPOSITE - CONFIDENTLY, WITH ADDRESSES.
//
// It read: "0x00BD8B12 test ecx,4000h / jnz default -> 0x4000
// must be CLEAR on that path ... the previous value 0x4000
// therefore failed twice". Every one of those addresses is a
// 3.3.3.3 address. In out.exe the function containing them is
// sub_BD7780, a dvar registrar that installs r_picmip and
// r_specular - it has nothing to do with HUD drawing. The
// reading was true of dest1yo's client and was imported here
// unchecked, which is exactly what
// codol-constants-are-unguarded-per-build warns about.
//
// A retail OLfinal server sets 0x4000 on its waypoint and its
// client draws it. That is the only evidence about THIS build's
// drawer that anyone has, and it says the imported rule is
// inverted here.
.flags = 0x4000,
```

### 2.2 十八层

```text
1. **flags 是 `0x4000`**
2. ⇒ **而上面曾经放着的注释说的【正好相反】—— 自信地，带着地址**
3. ⇒ **它读作**：
     · **`0x00BD8B12 test ecx,4000h / jnz default`**
     · ⇒ **`0x4000` 在那条路径上必须【清零】**
     · ⇒ **之前那个 `0x4000` 因此**失败了两次**
4. ⇒ **那些地址里的【每一个】都是一个 3.3.3.3 的地址**
5. ⇒ **在 `out.exe` 里包含它们的函数是 `sub_BD7780`**
6. ⇒ **一个【安装 `r_picmip` 与 `r_specular` 的 dvar 注册器】**
7. ⇒ **它与 HUD 绘制【没有任何关系】**
8. ⇒ **那个读法对 dest1yo 的客户端是【真的】**
9. ⇒ **而它被【未检查地】导入到这里**
10. ⇒ **那正是 `codol-constants-are-unguarded-per-build` 警告的东西**
11. ⇒ **一个零售 OLfinal 服务器在它的 waypoint 上【设 `0x4000`】**
12. ⇒ **而它的客户端【画它】**
13. ⇒ **那是关于【这个 build 的绘制器】唯一存在的证据**
14. ⇒ **而它说那个导入的规则在这里是【反的】**
```

### 2.3 ⭐⭐⭐ **"自信地，带着地址"**

**✅ 这是本文件里**对"错误的权威感"最尖锐的批评**。**

**⇒ 三层**：

```text
错误注释的特征：**自信 + 具体地址**
⇒ 而"具体地址"让读者**更难怀疑**
⇒ **⇒ 一个带着地址的错误比一个模糊的错误更危险**
```

**✅ 与 §370 的"从反编译读出的常数是一个假设"**同族（**第六次）。**

**⚠ 而"那些地址里的每一个都是一个 3.3.3.3 的地址"⇒ **一个系统性的错误**（不是一处笔误）。**

**✅ 与 §375 的"`IWD` 的 `64/8` 与 `19/18` 都不能移植"**同族（**第六次"逐 build 常数"）。**

### 2.4 而**"`sub_BD7780` 是一个 dvar 注册器"**

**✅ 与 §346 的"`0x00BD7C4C`/`0x00BD8B12` 在本 build 里落在 `sub_BD7780`（`r_picmip`/`r_specular`）"**完全一致 ✓

**⇒ **第二次确认 `sub_BD7780` 的身份。**

**⚠ 而"没有 HUD 关系"⇒ **所以那些地址与 HUD 无关**。**

**✅ 一个**决定性的错位**。**

### 2.5 而**"那唯一的证据"**

**✅ 与 §355 的"零个证据 vs 一个证据"**同族（**第二次"唯一证据"）。**

**⇒ 三层**：

```text
证据 A：一个 3.3.3.3 的地址（那属于另一个 build）
证据 B：**一个零售 OLfinal 服务器在 waypoint 上设 0x4000 而其客户端画它**
⇒ **B 是【唯一】关于这个 build 的证据**
⇒ **而 B 直接反驳 A**
```

**✅ ⭐ **"一个真实的观测胜过一段带地址的推理"**。**

**✅ 与 §360 的"崩溃说 `demoq` 是对的"**同族（**第七次"实测胜过推理"）。**

### 2.6 而 `codol-constants-are-unguarded-per-build`

**✅ 这是一个记忆条目名（`[[...]]` 风格）。**

**⇒ 三层**：

```text
1. **一个已记录的教训**
2. ⇒ **而它【不够】** —— 因为同一个错误在这里**又犯了一次**
3. ⇒ **⇒ 所以"记录教训"不足以阻止错误**
```

**✅ 与 §384 的"是 `-75` 自己的注释记录的【同一类错误】"**完全同族（**第二次"教训未能阻止错误"）。**

## 三、**`alpha 25 × 8 = 200`**（本组第二重要）

### 3.1 那段

```cpp
// alpha 25 of the -85 codec's five bits, so 25*8 = 200. The
// previous 0x80 was IW's "objpoints use half alpha", which is
// a reasonable guess and not what this server sent.
.color = 0xC8FFFFFFu,
```

### 3.2 七层

```text
1. **alpha `25` 是 `-85` 编解码器的【五位】里的值**
2. ⇒ **所以 `25 * 8 = 200`**（= `0xC8`）
3. ⇒ **而之前的 `0x80`（= 128）是 IW 的"objpoints 用半 alpha"**
4. ⇒ **那是一个【合理的猜测】**
5. ⇒ **而【不是】这个服务器所发的**
6. ⇒ **所以 `0xC8FFFFFF`**
```

**✅ 与 §346 的"`-85` 以五位携带 alpha ⇒ 低三位必须为零（32 级量化）"**完全闭合 ✓

**⇒ **第三次确认那个编解码器。**

**⚠ 而"`25 * 8 = 200`"⇒ 所以 **alpha 是 25/32 不透明**。**

**✅ 一个**精确的量化**。

### 3.3 而 **"那是一个合理的猜测"**

**✅ 与 §370 的"从反编译读出的常数是一个假设"**同族（**第七次）。**

**⇒ 三层**：

```text
`0x80` 是一个**合理的猜测**
⇒ **而"合理"不等于"正确"**
⇒ **⇒ 所以必须实测**
```

**✅ 一个**极清晰的"猜测 vs 实测"陈述**。**

## 四、**`SV_CalculateDmMatchBonus` 的完整推导**（本组第三重要）

### 4.1 那段

```cpp
// CODREF(IW4 _gamelogic.gsc/_rank.gsc):
//   spm = (3 + ((rank + 1) * 0.5)) * 10 = 35 + 5*rank
//   bonus = int(scale * spm * timePlayed / 60)
// where FFA's top three use win scale 1 and everybody else loss scale
// 0.5. Keep the half in the denominator so this stays exact integer
// arithmetic. Retail's rank-29 recorder participating for just under
// 600 seconds produces the independently decoded HudElem value 1799.
const auto spmTimesTwo = 70ull + 10ull * (uint64)zeroBasedRank;
const auto denominator = placedTopThree ? 120'000ull : 240'000ull;
const auto value = spmTimesTwo * participationMilliseconds / denominator;
```

### 4.2 十二层

```text
1. **`spm = (3 + ((rank + 1) * 0.5)) * 10 = 35 + 5*rank`**
2. ⇒ **`bonus = int(scale * spm * timePlayed / 60)`**
3. ⇒ **FFA 的前三名用 `scale = 1` 而其它人用 `scale = 0.5`**
4. ⇒ **把那个 `0.5` 保持在【分母里】以保持精确的整数算术**
5. ⇒ **所以 `spmTimesTwo = 70 + 10*rank`**（即 `2 * spm`）
6. ⇒ **而分母 `120000`（前三）或 `240000`（其它）**
7. ⇒ **因为 `scale = 1` ⇒ `spm * t / 60` ⇒ 乘 `2` 后 `/120`**
8. ⇒ **而 `scale = 0.5` ⇒ `0.5 * spm * t / 60` ⇒ 乘 `2` 后 `/240`**
9. ⇒ **所以 `value = spmTimesTwo * ms / denominator`**
10. ⇒ **★ 一个可验证的样本**：
      · **零售的 `rank-29` 录制者在略少于 `600` 秒的参与**
      · ⇒ **产生独立解码的 `HudElem` 值 `1799`**
11. ⇒ **验证**：`spm = 35 + 5*29 = 180` ⇒ `2*spm = 360`
12. ⇒ **`360 * 600000 / 120000 = 1800`** ⇒ **而"略少于 600 秒" ⇒ `1799`** ✓
```

### 4.3 ⭐⭐ **一个完全闭合的数值验证**

**✅ 与 §351 的"237 个间隔方程"**同族（**第五次"代数闭合"）。**

**⇒ 三层**：

```text
公式：`bonus = 2*spm * ms / 120000`
样本：`rank 29`、`~599.7 秒`
⇒ `spm = 180`、`2*spm = 360`
⇒ `360 * 599700 / 120000 = 1799.1` ⇒ **`int()` = 1799** ✓
```

**✅ ⭐ **一个"公式 + 样本"的完整闭合**。**

**⚠ 而"略少于 600 秒"⇒ **所以是 `1799` 而不是 `1800`** —— 一个**极精确的细节**。**

**✅ 与 §355 的"`7.9 × 10 = 79`"**同族（**第二次"数字互相印证"）。**

### 4.4 而**"把那个 `0.5` 保持在分母里以保持精确的整数算术"**

**✅ 三层**：

```text
朴素：`0.5 * spm * t / 60` ⇒ **浮点**
精确：`2*spm * t / (2*60*scale⁻¹)` ⇒ **整数**
⇒ **所以 `120000` 与 `240000`**
```

**✅ 与 §384 的"`max(-1,1)` 塌缩"**相反**（这是**避免浮点**）。**

**⚠ 而"`int()`"⇒ **截断**（不是舍入）。**

**✅ 与 §354 的"`floor(value + 0.5)`"**不同**（那是**四舍五入**，这是**截断**）。**

**⚠ 所以**两种取整方式**：**

```text
§354  `roundedOrigin`  ⇒ `floor(v + 0.5)`（四舍五入）
§390  `SV_CalculateDmMatchBonus` ⇒ `int()`（截断）
```

**✅ 一个**精确的区分**（坐标需要对称，得分需要保守）。

## 五、**`SV_IsDmOutcomeTie` 的四层**（本组第四重要）

### 5.1 那段

```php
// CODREF(IW4 _hud_message.gsc::outcomeNotify): first and second both
// receive TIE when their score and deaths match. Third receives TIE
// when it matches first on the same pair. Players below the displayed
// top three receive defeat even if a larger tie exists.
if (rankedClientNums.size() < 2 || rankedScores.size() < 2) return false;
const auto tiedWithFirst = [&rankedScores](const std::size_t place) {
    return place < rankedScores.size() &&
        rankedScores[0].score == rankedScores[place].score &&
        rankedScores[0].deaths == rankedScores[place].deaths;
};
if (tiedWithFirst(1) && (viewerClientNum == rankedClientNums[0] || viewerClientNum == rankedClientNums[1]))
    return true;
return rankedClientNums.size() >= 3 && viewerClientNum == rankedClientNums[2] && tiedWithFirst(2);
```

### 5.2 十一层

```text
1. **第一名与第二名在 `score` 与 `deaths` 都匹配时【都】收到 TIE**
2. ⇒ **第三名在与第一名在【同一对】上匹配时收到 TIE**
3. ⇒ **显示的前三【之下】的玩家收到 defeat**
4. ⇒ **即使存在一个更大的平局**
5. ⇒ **所以 `tiedWithFirst(place)` 比【第一名】与第 `place` 名**
6. ⇒ **而两个条件**：
     · **`tiedWithFirst(1)` 且 观看者是 0 或 1**
     · **或 `size >= 3` 且 观看者是 2 且 `tiedWithFirst(2)`**
7. ⇒ **所以"第三名也 TIE"要求与第【一】名匹配**
8. ⇒ **而不是与第二名**
```

**✅ ⭐ **一个反直觉的规则**（第三名比的是第一名）。**

**⚠ 而"更大的平局"⇒ **所以不是"所有同分者都 TIE"**。**

**✅ 与 §347 的"只有 1 与 2 在客户端解析"**不同（这是**一个游戏规则**）。

### 5.3 而**"`score` 与 `deaths` 都匹配"**

**✅ 三层**：

```text
1. **两个字段都要匹配**
2. ⇒ **所以单一字段的平局【不算】**
3. ⇒ **一个精确的规则**
```

**✅ 与 §376 的"三重身份检查"**不同（这是**两个字段**）。

## 六、**`SV_BuildDmOutcomeHudElems` 的 `alignScreen = 0x98`**

### 6.1 那段

```php
* destination++ = {
    .type = SvHudElemType::Text,
    .origin = { 0.0f, 20.0f, 0.0f },
    // Retail inherits the no-target sentinel in this reused slot. A
    // zero target names entity 0 and moves the title out of the
    // screen-space layout (observed live at the lower-left edge).
    .targetEntNum = EntityNumNone,
    .color = 0xFFFFFFFFu,
    .flags = 0x1,
    .alignOrg = 0x4,
    .alignScreen = 0x98,
    .fontScale = 3.0f,
    .font = 3,
    // Type 1 consumes this source slot as field 22 `text`, not field
    // 33 `label`; the writer performs that projection by type.
    .label = titleText,
    .glowColor = 0xFFB24D33u,
};
```

### 6.2 十层

```text
1. **`targetEntNum = EntityNumNone`**
2. ⇒ **"零售在这个重用的槽里继承无目标哨兵"**
3. ⇒ **"一个零目标命名实体 0 并把标题【移出屏幕空间布局】"**
4. ⇒ **"（在左下边缘【活观测】到）"**
5. ⇒ **`alignOrg = 0x4`**
6. ⇒ **`alignScreen = 0x98`**
7. ⇒ **"Type 1 把这个源槽当作字段 22 `text` 消费，不是字段 33 `label`"**
8. ⇒ **"写入器按类型执行那个投影"**
9. ⇒ **所以 `.label = titleText`**（而写入器会投影）
10. ⇒ **`glowColor = 0xFFB24D33`**
```

**✅ ⭐ **"一个零目标命名实体 0 并把标题移出屏幕空间布局"** —— 一个**具体的、活观测的**症状**。**

**⇒ 与 §361 的"几个是全一的『无』哨兵，用零代替是索引 0"**完全闭合 ✓

**⇒ **第八次确认那个原则。**

### 6.3 而**"字段 22 `text` 不是字段 33 `label`"**

**✅ 与 §346 的"`HudElem` 的 `label` 是 11 位"**不同（这是**两个不同的字段**）。

**⇒ 三层**：

```text
`.label` 是**源**槽
⇒ **而类型 1 把它投影到字段 22 `text`**
⇒ **而字段 33 是 `label`**
```

**⚠ 所以**同一个 `.label` 成员在两个字段之间投影**。**

**✅ 与 §344 的"一成员多语义"**同族（**第十五次）。**

## 七、**`(destination - 1)->materialIndex = 1; // soundID` 的五个别名**

### 7.1 那段

```cpp
// The title carries the same pulse descriptor as the first-place
// player name, except retail gives it soundID 1.
(destination - 1)->materialIndex = 1;           // soundID
(destination - 1)->width = 100;                 // fxLetterTime
(destination - 1)->fadeStartTime = birthServerTime; // fxBirthTime
(destination - 1)->scaleStartTime = 60'000;     // fxDecayStartTime
(destination - 1)->scaleTime = 1'000;           // fxDecayDuration
```

### 7.2 七层

```text
1. **标题携带与第一名玩家名【同一个脉冲描述符】**
2. ⇒ **除了零售给它 `soundID = 1`**
3. ⇒ **所以五个字段【别名】**：
     · `materialIndex` ⇒ **`soundID`**
     · `width`         ⇒ **`fxLetterTime`**
     · `fadeStartTime` ⇒ **`fxBirthTime`**
     · `scaleStartTime`⇒ **`fxDecayStartTime`**
     · `scaleTime`     ⇒ **`fxDecayDuration`**
4. ⇒ **所以 `SvHudElem` 是【按类型重载】的一个 union 式结构**
```

**✅ ⭐⭐ **五个字段的五个别名** —— 这是本文件里最密集的"一成员多语义"（**第 16–20 次**）。

**⚠ 而注释说"所以 `SvHudElem`，因此那个地址敏感的 `WorldClientState` 节点，【不增长】"**。

**⇒ **第十二次确认那条铁律。**

### 7.3 而**"这两个别名在聚合声明里比上面的字段【更早】出现，所以在构造后赋值"**

```cpp
// These two aliases occur earlier than the fields above in the
// aggregate declaration, so assign after construction rather than
// violating C++ designated-initializer order.
(destination - 1)->materialIndex = (uint16)(place + 2); // soundID
(destination - 1)->width = 100;                         // fxLetterTime
```

**⇒ 五层**：

```text
1. **`materialIndex` 与 `width` 在 `SvHudElem` 的声明里【更早】**
2. ⇒ **而 C++ 的 designated initializer 要求【声明顺序】**
3. ⇒ **所以不能在 `.origin = ...` 之后写 `.materialIndex = ...`**
4. ⇒ **所以构造后赋值**
5. ⇒ **⇒ 一个真实的语言约束**
```

**✅ 一个**精确的 C++ 细节**（C++20 的 designated initializers 不能乱序）。

## 八、**`SV_BuildFeedbackHudElems` 的"四分之一的竖直偏移"**（本组第五重要）

### 8.1 那段

```php
// Screen-space, not world-space. alignScreen mode 2 resolves both
// axes to the screen centre (sub_B236A0 case 2 / sub_B237C0 case
// 2), so the origin is an offset from the crosshair in the virtual
// 640x480 units the client scales by 1.6 - resolution-independent.
//
// These are IW4 _damagefeedback.gsc's own two numbers, x = -12 and
// y = -12 against a 24x48 shader with a top-left origin. Note the
// vertical offset is a QUARTER of the height, not half: the mark
// sits high in the material and the script hangs the rest below
// the crosshair. Centring the whole box instead lifts the mark 12
// units, which is exactly the "slightly above the crosshair"
// placement this replaced.
.origin = {
    -static_cast<float>(SvDamageFeedbackWidth) / 2.0f,
    -static_cast<float>(SvDamageFeedbackHeight) / 4.0f,
    0.0f,
},
```

### 8.2 十四层

```text
1. **屏幕空间，不是世界空间**
2. ⇒ **`alignScreen` 模式 2 把两个轴都解析到屏幕中心**（`sub_B236A0` case 2 / `sub_B237C0` case 2）
3. ⇒ **所以 origin 是【从准星的偏移】**
4. ⇒ **在客户端按 1.6 缩放的【虚拟 640×480 单位】里**
5. ⇒ **⇒ 分辨率无关**
6. ⇒ **这些是 IW4 `_damagefeedback.gsc` 自己的两个数**
7. ⇒ **`x = -12` 与 `y = -12` 对一个 `24×48` 的 shader**（左上原点）
8. ⇒ **注意竖直偏移是【高度的四分之一】，【不是一半】**
9. ⇒ **标记坐在材质里的【高处】**
10. ⇒ **而脚本把其余部分挂在准星【下方】**
11. ⇒ **把整个盒子居中反而【把标记抬高 12 单位】**
12. ⇒ **而那正是这个替换掉的"稍微在准星上方"的放置**
13. ⇒ **所以 `y = -height/4 = -12`**（`height = 48`）
14. ⇒ **而 `x = -width/2 = -12`**（`width = 24`）
```

**✅ ⭐ **"竖直偏移是高度的四分之一不是一半"** —— 一个**极精细的 UI 洞察**。**

**⇒ 三层**：

```text
x: `-width/2`  ⇒ **水平居中**
y: `-height/4` ⇒ **【不是】垂直居中**
⇒ **因为标记坐在材质的高处**
```

**✅ 与 §355 的"`0.079` 不是 `0.385`"**同族（**第五次"一个数值错整个视觉错"）。**

**⚠ 而"`24×48`"⇒ **一个极细长的 shader**。**

**✅ 与 §344 的"`validItemEntity` 的 `positionTrajectoryDuration == 50`"**不同（这是**一个尺寸**）。

### 8.3 而 **`flags = 0x1` 的"bit 0 必须"**

```php
// CODREF: same client filter the waypoint producer cites. Flags at
// [elem+0A4h]: 0x00BD7C4C "test cl,1 / jz default" makes bit 0
// mandatory, and 0x00BD7C55 "test cl,cl / js default" means this
// drawer group only takes elems with bit 0x80 clear.
.flags = 0x1,
```

**⇒ 六层**：

```text
1. **同一个客户端过滤器（waypoint 生产者引用的）**
2. ⇒ **flags 在 `[elem+0A4h]`**
3. ⇒ **`0x00BD7C4C test cl,1 / jz default`** ⇒ **bit 0 是必须的**
4. ⇒ **而 `0x00BD7C55 test cl,cl / js default`** ⇒ **这个抽屉组只接受 bit `0x80`【清零】的**
5. ⇒ **所以 `flags = 0x1`**
6. ⇒ **⇒ 而这两个地址【又一次】是 3.3.3.3 的**
```

**⚠ 而"`0x00BD7C4C`/`0x00BD7C55`"与 §390 二 的"`0x00BD8B12`"**同族（**同一类地址误引**）。**

**⇒ 三层**：

```text
§390 二  **`0x00BD8B12` 的 `0x4000` 规则是错的**（已纠正）
§390 八  **`0x00BD7C4C` 的 `bit 0` 规则仍在使用**
```

**⚠ 所以**一个被纠正而一个未被检验**。**

**⇒ 一处**潜在的同一错误**。**

**✅ 与 §346 的"七十五项合取"**不同（这是**两个位规则**）。

## 九、`SV_BuildZmScoreHudElem` 的"1750ms"与"label 385"

```php
// CODREF(538B70,538250,514880): exact OLFinal native Value formatter,
// label+952 then one-based localized lookup. Original Factory label385
// resolves to MP_PLUS at constant type4/index384 in this loaded map.
// Native recording: x30/y-50, grow100ms, settle200ms, hold1000/fade750.
// Reuse the proven HUD transport/color projection, not MP's reward policy.
const bool active = score && score->active && serverTime >= score->startedAt &&
    serverTime - score->startedAt < 1750;
auto elem = SV_BuildFeedbackHudElems(0, 0, active ? (float)score->value : 0.0f, active ? score->startedAt : 0, serverTime)[0];
elem.origin[0] = 30.0f; elem.label = 385;
if (active && serverTime - score->startedAt >= 100) elem.scaleTime = 200;
```

### 9.1 八层

```text
1. **`538B70`/`538250`/`514880`：精确的 OLFinal 原生 Value 格式化器**
2. ⇒ **`label + 952` 然后一个【1 基的本地化查找】**
3. ⇒ **原始 Factory 的 `label 385` 解析成 `MP_PLUS`**（`type4/index384` 在这个已加载的地图里）
4. ⇒ **原生录制：`x30/y-50`、`grow100ms`、`settle200ms`、`hold1000/fade750`**
5. ⇒ **重用已验证的 HUD 传输/颜色投影，不是 MP 的奖励策略**
6. ⇒ **`active` = 有分数且 `0 <= elapsed < 1750`**
7. ⇒ **而 `100 + 200 + 1000 + 450 = 1750`**（`grow 100 + settle 200 + hold 1000 + fade 450`？）
8. ⇒ **`elem.origin[0] = 30` / `elem.label = 385`**
```

**⚠ 而"`1000 + 750 = 1750`"⇒ 所以**`hold 1000` + `fade 750` = 1750**，而 `grow 100` 与 `settle 200` 是**前缀阶段**。**

**✅ **四次确认那个时长**（`1750 = 1000 + 750`）。**

### 9.2 而**"不可见预约保持目标槽稳定"**

```php
if (!active) {
    // OLMOD(zm-score-slot-owner): invisible reservation keeps objective
    // slots stable while the score starts/expires; no invented visible0.
    elem.color = elem.fromColor = elem.glowColor = 0;
    elem.fadeTime = 0; elem.scaleTime = 0; elem.fontScale = 0.9f;
}
```

**⇒ 五层**：

```text
1. **一个不可见的预约**
2. ⇒ **在分数开始/过期时保持目标槽稳定**
3. ⇒ **"没有发明一个可见的零"**
4. ⇒ **所以三个颜色清零 + 两个时长清零 + `fontScale = 0.9`**
5. ⇒ **⇒ 一个"占位但不画"的元素**
```

**✅ 与 §344 的"零是安全标记"**同族（**第六次"零即无效"）。**

**⚠ 而"`fontScale = 0.9`"⇒ **一个非零的小值**（而不是 0）。**

**⇒ 三层**：

```text
若 `fontScale = 0` ⇒ **§346 的"量化到零的文本不可见"** ⇒ **但可能触发别的路径**
若 `fontScale = 0.9` ⇒ **一个合法的、不可见的（因为颜色为零）**
⇒ **所以选 0.9**
```

**✅ ⭐ **一个"用合法的小值而不是零"的选择**（避开 §346 的零量化）。**

## 十、关键结论

1. **⭐⭐⭐ "`0x4000` 而那上面曾经放着的注释说的【正好相反】——【自信地，带着地址】"`** —— 而 **"那些地址里的每一个都是一个 3.3.3.3 的地址"**。
2. **⭐ "`0x00BD8B12` 在 `out.exe` 里落在 `sub_BD7780`，一个安装 `r_picmip` 与 `r_specular` 的 dvar 注册器，与 HUD 绘制没有任何关系"`** —— 第二次确认 `sub_BD7780`。
3. **⭐ "一个零售 OLfinal 服务器在它的 waypoint 上设 `0x4000` 而它的客户端画它 —— 那是关于这个 build 的绘制器【唯一】存在的证据，而它说那个导入的规则在这里是【反的】"`**。
4. **"`codol-constants-are-unguarded-per-build`"** 警告的东西 —— **而记录教训不足以阻止错误**（第二次）。
5. **`alpha 25 × 8 = 200`（`0xC8`）**，而 **"`0x80` 是 IW 的『objpoints 用半 alpha』，一个合理的猜测而不是这个服务器所发的"`** —— 第三次确认 `-85` 的五位 alpha。
6. **⭐⭐ `SV_CalculateDmMatchBonus` 的完整推导**：`spm = 35 + 5*rank`、`bonus = 2*spm * ms / (120000 或 240000)`，而 **`rank 29` + `~600 秒` ⇒ `1799`** —— **一个完全闭合的数值验证**。
7. **"把那个 `0.5` 保持在分母里以保持精确的整数算术"`** —— 而 `int()` **截断**（与 §354 的 `floor(v+0.5)`**不同**）。
8. **⭐ `SV_IsDmOutcomeTie` 的反直觉规则**：**第三名比的是【第一名】**（不是第二名），而**两个字段（`score` 与 `deaths`）都要匹配**。
9. **"显示的前三【之下】的玩家收到 defeat，即使存在一个更大的平局"`**。
10. **⭐ "一个零目标命名实体 0 并把标题【移出屏幕空间布局】（在左下边缘【活观测】到）"`** —— 第八次确认"零不是缺席而是索引 0"。
11. **"Type 1 把 `.label` 这个源槽当作字段 22 `text` 消费，不是字段 33 `label`；写入器按类型执行那个投影"`** —— 第十五次"一成员多语义"。
12. **⭐⭐ `SvHudElem` 的五个别名**（`materialIndex`⇒`soundID` / `width`⇒`fxLetterTime` / `fadeStartTime`⇒`fxBirthTime` / `scaleStartTime`⇒`fxDecayStartTime` / `scaleTime`⇒`fxDecayDuration`）—— 最密集的一次（第 16–20 次）。
13. **"所以 `SvHudElem`，因此那个地址敏感的 `WorldClientState` 节点，【不增长】"`** —— 第十二次确认那条铁律。
14. **⭐ "这两个别名在聚合声明里比上面的字段更早出现，所以构造后赋值而不是违反 C++ 的 designated-initializer 顺序"`** —— 一个精确的语言约束。
15. **⭐⭐ "竖直偏移是高度的【四分之一】，不是一半：标记坐在材质里的高处而脚本把其余部分挂在准星下方；把整个盒子居中反而把标记抬高 12 单位"`** —— 第五次"一个数值错整个视觉错"。
16. **⚠ `flags = 0x1` 仍引用 `0x00BD7C4C`/`0x00BD7C55`（3.3.3.3 的地址）** —— 与 §390 二 已纠正的 `0x4000` **同一类地址误引**，而**此处未被检验**。
17. **⭐ `SV_BuildZmScoreHudElem` 的 `1750 = hold 1000 + fade 750`**（第四次确认），而 **"不可见预约保持目标槽稳定，没有发明一个可见的零"`**。
18. **"`fontScale = 0.9`"而不是 0** —— 一个**用合法小值避开 §346 的零量化**的选择。

## 十一、未闭合点

- `SvDmMatchBonusLabel` / `SvDmPlacementLabels` 的值。
- `SvDamageFeedbackWidth` / `Height` 的确认（24 / 48）。
- `SvScoreFeedback*` 六个常量的值。
- `0x00BD7C4C`/`0x00BD7C55` 在 out.exe 里是否仍落在 HUD 绘制路径上。
- `sv_main_mp.cpp` 650 行之后未读取。
