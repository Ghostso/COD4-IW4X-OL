# 416 · **"线缆上没有『无队伍』这个值，发一个就杀死客户端"** —— `SvPlayerState` 的实测字段、色带的**方向反了**、以及 `HUD` 只承认六个类型

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 1010–1650 行。

## 二、**`SvTeam::None` 在客户端是一个空指针**（本组最重要的一段）

### 2.1 那段

```cpp
// THE WIRE HAS NO TEAMLESS VALUE, AND SENDING ONE KILLS THE CLIENT.
//
// Free-for-all represents "no team" as SvTeam::None, which is 0, and that is
// a sound SERVER-side choice -- onSameTeam is false whenever either side is
// None, so everyone damages everyone with no special case. The client cannot
// hold it. CODOL's presentation lookup sub_53F5F0 is:
//
//     v1 = 624 * clientNum + <table>;
//     if (v1[62] == 1) return <tf slot>;
//     if (v1[62] == 2) return <sc slot>;
//     return 0;
//
// and its caller sub_59CC70 writes v4[251] through the result without
// checking it. So a player whose team is anything but 1 or 2 makes every
// OTHER client fault at +0x3EC the moment it has to present them.
//
// MEASURED with a hook on that lookup, both clients, one null return each:
//     client A  index=1 kind=0        client B  index=0 kind=0
// Each crashed resolving the other, and kind is the team. Four of the last
// five cycles lost a client to it; it is free-for-all only, which is the
// mode this project exists to ship.
```

### 2.2 二十四层

```text
1. **线缆上【没有"无队伍"这个值】，发一个【就杀死客户端**】**
2. ⇒ **自由混战把"无队伍"表示为 `SvTeam::None` = `0`**
3. ⇒ **而那是【一个健全的服务器侧选择**】**
4. ⇒ **（`onSameTeam` 在任一侧为 `None` 时都是假 ⇒ 所有人伤害所有人，无特例）**
5. ⇒ **而【客户端无法持有它**】**
6. ⇒ **`sub_53F5F0`**：
      · **`v1 = 624 * clientNum + <table>`**
      · **`if (v1[62] == 1) return <tf slot>`**
      · **`if (v1[62] == 2) return <sc slot>`**
      · **`return 0`**
7. ⇒ **而它的调用方 `sub_59CC70` 【通过那个结果写 `v4[251]` 而不检查它**】**
8. ⇒ **⇒ 所以【队伍不是 `1` 或 `2` 的一个玩家会让【每一个其它客户端**】在 `+0x3EC` 出错**】
9. ⇒ **就在它必须呈现他们的那一刻**
10. ⇒ **用钩子测量那个查找，两个客户端，各一次空返回**：
      · **客户端 A `index=1 kind=0`**
      · **客户端 B `index=0 kind=0`**
11. ⇒ **各自在解析对方时崩溃，而 `kind` 就是队伍**
12. ⇒ **五轮里【四轮】因此丢了一个客户端**
13. ⇒ **而它【只在自由混战**】** ⇒ 而那正是这个项目存在的模式**
```

### 2.3 ⭐⭐⭐ **"一个健全的服务器侧选择在客户端是一个空指针解引用"**

**✅ 这是本报告里**最重要的一条"两端语义不对称"**。**

**⇒ 三层**：
```text
服务器侧：`None` = `0` ⇒ **一个健全的哨兵**
客户端：`0` ⇒ **`sub_53F5F0` 返回 `0`，而 `sub_59CC70` 【不检查地写穿它**】
⇒ **⇒ 所以【同一个值在一端是设计，在另一端是崩溃**】
```

**✅ 与 §413 的"零 viewmodel ⇒ `sub_53F5F0` 返回 null，`sub_59CC70` 不检查地写 ⇒ AV"**——**完全同一条链**。

**⇒ 三层**：
```text
§413  `viewmodelIndex = 0` ⇒ **`sub_53F5F0` 返回 null** ⇒ **AV**
§416  `team = 0` ⇒ **`sub_53F5F0` 返回 null** ⇒ **AV**
⇒ **⇒ 同一个函数、同一个调用方、同一个崩溃**
```

**✅ ⭐⭐⭐ **一个"同一个失败点在两个输入上发作"的完美闭合**。

**⇒ 而 §413 说 `viewmodelIndex` 是"没有武器"，这里是"没有队伍" ⇒ **两个不同的"没有"都走同一条路**。**

**⚠ 而"`v4[251]` 与 `+0x3EC`"⇒ **`0x3EC = 1004`，`251*4 = 1004`** ⇒ **同一个地址**。**

**✅ **算术闭合**（`v4` 是 `int*` ⇒ `v4[251]` = `v4 + 1004` = `+0x3EC`）。

**✅ ⭐⭐ **一个"`v4[251]` 与 `+0x3EC` 是同一地址"的算术验证**。

### 2.4 而**"钩子测量的两个客户端"**

```text
客户端 A  index=1 kind=0
客户端 B  index=0 kind=0
```

**⇒ 五层**：
```text
1. **A 在 `index=1` 处得 `kind=0`** ⇒ **`v1[62]` 读到 `0`**
2. ⇒ **B 在 `index=0` 处得 `kind=0`**
3. ⇒ **⇒ 所以【A 崩在呈现 B（index=0），B 崩在呈现 A（index=1）**】**
4. ⇒ **两个互相解析，各得一次空返回**
5. ⇒ **⇒ 所以【它是对称的、必然的**】
```

**✅ ⭐ **"各自在解析对方时崩溃"** —— 一个**必然性论证**。

### 2.5 而**"分派给 faction"**

```cpp
// The faction already picks the model, so it is the honest presentation
// team for a player who has none. Spectator (3) is folded in too -- it is
// no more representable than 0 is.
[[nodiscard]] SvTeam SV_PresentableTeam(
    SvTeam team,
    const std::optional<SvCharacterCustomization> &customization);
```

**⇒ 六层**：
```text
1. **`faction` 已经选模型** ⇒ **所以它是一个没有队伍的玩家的【诚实的呈现队伍**】**
2. ⇒ **`Spectator (3)` 也被折进来** ⇒ **它不比 `0` 更可表示**
3. ⇒ **⇒ 所以 `SV_PresentableTeam(None, customization) = customization->faction`**
4. ⇒ **（而 `Spectator` 也走同一条）**
```

**✅ ⭐⭐ **"一个已经存在的信息（faction）是一个诚实的替代"** —— 与 §411 的"`plan.valid` 作为可得信号"**同族（**第八次"用一个既有的代理信号"）。

**⇒ 三层**：
```text
§411  蹲/趴位未知 ⇒ **用 `plan.valid`**
§416  队伍不可表示 ⇒ **用 `faction`**
⇒ **⇒ 两次"用一个既有的代理**】
```

**✅ 而 §415 说 "clientState field 20 `+0x7C` IS `characterItemId`" ⇒ **同一个字段族。**
## 三、**色带的方向反了**（本组第二重要）

### 3.1 那段

```cpp
// CODREF: the colour fade. sub_AB4490 resolves an elem's drawn colour
// as lerp(fromColor, color, (serverTime - fadeStartTime) / fadeTime),
// holding at colour once the window closes (0x00AB44B0). So `color` is
// the END of the fade and `fromColor` its START - the opposite of the
// reading the names invite. The four live at 0x30/0x34/0x38/0x3C as
// descriptors 0, 12, 10 and 13.
```

### 3.2 十二层

```text
1. **`sub_AB4490` 把一个元件的绘制颜色解析为**：
2. ⇒ **`lerp(fromColor, color, (serverTime - fadeStartTime) / fadeTime)`**
3. ⇒ **一旦那个窗口关闭就【保持在 `color`**】（`0x00AB44B0`）
4. ⇒ **⇒ 所以【`color` 是淡出的【终点**】而 `fromColor` 是它的【起点**】**
5. ⇒ **⇒ 那是【名字所邀请的读法的【反面**】】**
6. ⇒ **四个字段在 `0x30`/`0x34`/`0x38`/`0x3C`**
7. ⇒ **作为描述符 `0`/`12`/`10`/`13`**
```

### 3.3 ⭐⭐⭐ **"那是名字所邀请的读法的反面"**

**✅ 这是本报告里**最重要的一次命名陷阱**。**

**⇒ 三层**：
```text
名字：`color` ⇒ **直觉："当前/基础颜色"**
名字：`fromColor` ⇒ **直觉："从哪个颜色来（起点）"**
真相：**`fromColor` 是起点，`color` 是终点** ⇒ **名字其实是对的！**
```

**⚠ 等等 —— 注释说"`color` 是终点而 `fromColor` 是起点，那是名字所邀请的读法的反面"。**

**⇒ 但 `fromColor` = "从" ⇒ 起点；`color` ⇒ 终点。这**其实符合直觉**。

**⇒ 那"反面"指的是什么？**

**⇒ 可能是**「`color` 通常被理解为"元件的颜色"（恒定），而实际上它是**渐变的终点**」**。**

**⇒ 三层**：
```text
直觉：`color` = 元件【恒定的颜色】，`fromColor` = 淡入的起点
真相：`color` = **淡出的终点**，而【淡出后保持它】
⇒ **⇒ 所以"`color` 是元件的颜色"这个读法【只在淡出之后成立**】
```

**✅ ⭐ **一个更精确的重新表述**（而注释的措辞有点绕）。

**⚠ 而同样的形状在 `fontScale`/`fromFontScale` 上**：

```cpp
// CODREF: the scale animation, the same shape one struct earlier.
// sub_BB4B70 lerps [elem+18h] to [elem+14h] across
// [elem+1Ch, elem+1Ch + elem+20h] at 0x00BB4C3A, so fromFontScale is
// the start and fontScale the end. Descriptors 19, 16, 17 and 18.
```

**⇒ 四层**：
```text
`fromFontScale`（`+0x18`）⇒ **起点**
`fontScale`（`+0x14`）⇒ **终点**
窗口：`[+0x1C, +0x1C + +0x20]`
⇒ **⇒ 与颜色族【完全同形，但偏移顺序相反**】**
```

**✅ ⭐⭐ **"颜色在 `0x30/34/38/3C`，缩放在 `0x18/14/1C/20`"** —— **一个递增一个递减。**

**⚠ 一个**容易搞反的地方**（`+0x14` 是终点而 `+0x18` 是起点）。

### 3.4 而**`fontScale` 的"零就不画"**

```cpp
// CODREF: descriptor 16, [elem+14h], bits -86. sub_BB4B70 reads it at
// 0x00BB4C60 as the text height before the 0.25/0.33/0.5 font-family
// factor and the screen scale, so a zero here draws nothing. Its wire
// codec is at 0x00C42EE5 in the generic field reader: SIX RAW BITS
// divided by 10.0 with no change prefix, i.e. 0.0 to 6.3 in tenths.
```

**⇒ 十层**：
```text
1. **`sub_BB4B70` 在 `0x00BB4C60` 把它读作【文字高度**】**
2. ⇒ **在 `0.25`/`0.33`/`0.5` 的字族因子与屏幕缩放之前**
3. ⇒ **⇒ 所以【这里一个零就什么也不画**】**
4. ⇒ **它的线缆编解码器在 `0x00C42EE5`**
5. ⇒ **【六个原始位**】**
6. ⇒ **【除以 `10.0`**】**
7. ⇒ **【没有变化前缀**】**
8. ⇒ **⇒ 所以范围 `0.0 .. 6.3`，以十分之一为单位**
```

**✅ ⭐⭐ **"六个原始位 / 除以 10 / 无变化前缀"** —— 一个**极精确的编解码器描述**。

**✅ 与 §384 的"一个编解码器不是一个类型"**同族（**第二次"编解码器细节"）。

**⇒ 三层**：
```text
"six RAW bits" ⇒ **不是 delta，是绝对值**（所以**没有变化前缀**）
"divided by 10.0" ⇒ **一位小数**
⇒ **⇒ 所以 `6.3` 是最大值**
```

**✅ ⭐ **一个"原始位 vs delta"的区分**。

**⚠ 而"`0.0..6.3`"⇒ **`63` 个可能值**（`6` 位 = `0..63`）。**

**✅ 算术闭合**。

### 3.5 而**`font` 的"第一个 switch"**

```cpp
// CODREF: descriptor 20, [elem+24h], 4 bits. sub_BB4B70's FIRST switch
// maps it to a font handle and a size factor - 1 and 6 give 0.5, 2 and
// 7 give 1/3, everything else 0.25.
```

**⇒ 六层**：
```text
1. **`4` 位** ⇒ **`0..15`**
2. ⇒ **`1` 与 `6` ⇒ `0.5`**
3. ⇒ **`2` 与 `7` ⇒ `1/3`**
4. ⇒ **其它一律 `0.25`**
5. ⇒ **⇒ 所以【`4` 位域只用了 `0..7` 的语义**】**
```

**⚠ 而"`1`/`6` 同值，`2`/`7` 同值"⇒ **一个周期 `5` 的模式**。**

**⇒ 三层**：
```text
`1` ⇒ `0.5`   `6` ⇒ `0.5`  （**差 5**）
`2` ⇒ `1/3`   `7` ⇒ `1/3`  （**差 5**）
⇒ **⇒ 所以【`+5` 是一个同义偏移**】
```

**✅ ⭐ **一个"`+5` 同义"的发现**（可能是 `small`/`large` 两族）。

## 四、**`SvHudElemType` 的六个承认值**（本组第三重要）

### 4.1 那段

```cpp
// THESE NUMBERS ARE OLfinal's, READ OFF A RETAIL OLfinal SERVER, AND
// THEY ARE NOT 3.3.3.3's. That distinction cost this file real bugs.
//
// Everything here used to be justified by addresses in the 0x00BB..0xBF
// range - 0x00BD81C3, 0x00BD8AF8, sub_BB5680, sub_BB4B70, sub_AB4490.
// NONE OF THEM MEAN ANYTHING IN out.exe. They are dest1yo's 3.3.3.3
// client's addresses, and they land in unrelated out.exe code: the
// function containing 0x00BD81C3 here is sub_BD7780, which registers
// r_picmip, r_specular and r_displayMode. It is a dvar registrar, not a
// HUD drawer.
```

### 4.2 二十层

```text
1. **这些数字是 OLfinal 的，从一台零售 OLfinal 服务器读出，【不是 3.3.3.3 的**】**
2. ⇒ **那个区分【让这个文件付出过真实的 bug**】**
3. ⇒ **这里的一切【过去都由 `0x00BB..0xBF` 范围的地址辩护**】**
4. ⇒ **`0x00BD81C3` / `0x00BD8AF8` / `sub_BB5680` / `sub_BB4B70` / `sub_AB4490`**
5. ⇒ **它们【在 `out.exe` 里毫无意义**】**
6. ⇒ **它们是 dest1yo 的 3.3.3.3 客户端的地址**
7. ⇒ **而它们【落在无关的 `out.exe` 代码上**】**
8. ⇒ **⇒ `0x00BD81C3` 在这里所属的函数是 `sub_BD7780`**
9. ⇒ **它注册 `r_picmip`、`r_specular` 与 `r_displayMode`**
10. ⇒ **⇒ 它是【一个 dvar 注册器，不是 HUD 绘制器**】**
11. ⇒ **3.3.3.3 的读法【对 3.3.3.3 是正确的**】**
12. ⇒ **而【把它的类型编号进口到一棵 OLfinal 树里则不是**】**
```

### 4.3 ⭐⭐⭐ **"那个读法对 3.3.3.3 是正确的；把它的编号进口到 OLfinal 树里则不是"**

**✅ 这是本报告里**最重要的一条参照血统纪律**。**

**✅ 与 `AGENTS.md` 的**「ol-mod 仅同类参考、非权威、不得引用其常量」完全一致 ✓

**⇒ 三层**：
```text
地址：`sub_BD7780`【在 `out.exe` 里存在】
但它做的是：**注册 `r_picmip`/`r_specular`/`r_displayMode`**
⇒ **⇒ 所以【一个地址在两边都有效时，可能指向【完全不同的功能**】】
```

**✅ ⭐⭐⭐ **"一个地址在两边都存在，但做的是完全不同的事"** —— 一个**最危险的参照错误**。

**⇒ 三层**：
```text
安全：地址在目标 build 里**不存在** ⇒ **立即发现**
危险：地址在目标 build 里**存在但功能不同** ⇒ **看起来对而完全错**
```
**✅ ⭐⭐ **"一个存在但错位的地址比一个不存在的地址更危险"**。</br>

**✅ 与 §397 的"一个结果在两种假设下都成立 ⇒ 零信息"**同族（**第八次"看起来对的错误"）。

### 4.4 而**实测的四个类型**

```text
TYPE 5   x=-12 y=-12 w=24 h=48 alignScreen=0x22 target=2047
         fromColor=alpha31 color=alpha0 fadeTime=1000
         -> 命中标记（几何完全吻合，只有 TYPE 是 3.3.3.3 的）
TYPE 2   y=-50 alignOrg=5 alignScreen=0x22 value=50 label=397
         fontScale=0.9 fromFontScale=3.0 scaleTime=200/100
         fadeTime=750  -> 分数弹出（Type 2 未变）
TYPE 14  x=7924 y=2161 w=10 h=10 material=151
         -> 唯一的世界坐标 + 材质的元件
TYPE 4   640x480 material=1 -> 全屏背景（在 OLfinal 上）
```

**⇒ 五层**：
```text
1. **`TYPE 5`** ⇒ **命中标记**（`x=-12 y=-12 w=24 h=48`）
2. ⇒ **`TYPE 2`** ⇒ **分数弹出**（`value=50 label=397`，两种字体缩放 `0.9` 与 `3.0`）
3. ⇒ **`TYPE 14`** ⇒ **唯一的世界坐标元件**（`x=7924 y=2161` ⇒ **世界坐标**）
4. ⇒ **`TYPE 4`** ⇒ **全屏背景**（`640x480 material=1`）
5. ⇒ **⇒ 所以【"Icon 与 Waypoint 各移动一位"**】**
```

**⚠ 而枚举里 `Icon = 5`、`Waypoint = 14`。**

**⇒ 三层**：
```text
3.3.3.3：`Icon = 4`、`Waypoint = 13`
OLfinal：`Icon = 5`、`Waypoint = 14`
⇒ **⇒ 各 `+1`**
```

**✅ ⭐⭐ **"一个版本插入了一个类型 ⇒ 之后所有编号 `+1`"** —— 与 §415 的"`ET_EVENTS` 是 23 而 3.3.3.3 是 22"**完全同族**。

**⇒ 三层**：
```text
§415  本 build 在 `22` 插入一个未命名 eType ⇒ **`ET_EVENTS` 22 → 23**
§416  本 build 在某个位置插入一个 hudElem 类型 ⇒ **`Icon`/`Waypoint` +1**
⇒ **⇒ 同一个"插入导致全体位移"的模式**
```

**✅ ⭐⭐⭐ **一个"版本插队导致偏移"的两例**。

**⚠ 而"`TYPE 4` 在 OLfinal 上是全屏背景"⇒ **所以一个按 3.3.3.3 发 `Icon = 4` 的服务器会画一个全屏黑幕**。**

**✅ **一个可推导的、极其显眼的故障**（而注释说"Which is what an icon elem sent as type 4 would become"）。

**✅ ⭐ **"一个图标元件被当类型 4 发送会变成什么"** —— 一个**精确的灾难预测**。

### 4.5 而**枚举的六个值**

```text
Free      = 0
Text      = 1
Value     = 2
PlayerName= 3
Icon      = 5
ClockDown = 12
Waypoint  = 14
```

**⚠ 注意：`4`、`6`、`7`、`8`、`9`、`10`、`11`、`13` **全部缺失**。**

**⇒ 而注释说：**

```cpp
// CODREF(1649370): sub_538360/sub_538430 prove the OLfinal timer
// families are 6..8 (seconds) and 9..11 (tenths). They remain outside
// the server's admitted producer set until a feature needs them.
```

**⇒ 五层**：
```text
`6..8`   ⇒ **秒计时器族**
`9..11`  ⇒ **十分之一秒计时器族**
`4`      ⇒ **图标/特殊路径**（§411 的"outcome aliases 4 与 8 是原始 XOR 载荷"）
`8`      ⇒ **固定秒计时器**
`13`     ⇒ **未知**
⇒ **⇒ 所以【十一个未承认的值各有归属**】
```

**✅ 与 §411 的"`fadeTime == 0` 且（五个任一）⇒ 被当成脉冲字幕 ⇒ `label` 清零"**——**而 `Text = 1` 的注释说"former outcome aliases 4 and 8 were raw XOR payloads"** ⇒ **另一个历史错误**。

**⇒ 三层**：
```text
`Text = 1` ⇒ **正确**（`sub_538B70` case 1 从 `hudelem+0x8C` 读本地化串索引）
而曾经用过 `4` 与 `8` ⇒ **它们是【原始 XOR 载荷**】⇒ **不是类型编号**
⇒ **⇒ 所以【把"解码后的原始值"当成"类型编号"是一个错误**】
```

**✅ ⭐⭐ **一次"混淆了编码层与语义层"的错误**。

## 五、**`SvPlayerState` 的实测字段密度**（本组第四重要）

### 5.1 **最密的一段：可预测事件环**

```cpp
// THE PREDICTABLE EVENT RING, WHICH THIS SERVER ALREADY HAD AND NEVER
// SENT. It is the single largest thing missing from the playerState:
// the retail dm demo asserts pe.eventSequence and pe.oldEventSequence
// 4225 times EACH and the four ring slots about 1200 times each --
// roughly eleven thousand assertions in one match, and none of them
// was ours. This is footsteps, landings, weapon fire, reloads and
// pickups: everything that happens between the kills.
//
// AND THE EVENTS ARE NOT NEW WORK. The native engine's own Pmove
// produces them, SV_ReadNativePredictableEvents already pulls them out
// of the native playerState after every think, and the bullet path
// already consumes them. They were read, used server-side, and dropped
// before the wire.
//
// The native offsets and the netfield offsets are the same numbers:
// PredictableEventSequenceOffset is 0x108, which is netfield index 1,
// and PredictableEventsOffset is 0x10C, which is index 21. The ring is
// indexed by `sequence & 3`, so it is copied SLOT FOR SLOT rather than
// in the order the batch reader returns.
```

**⇒ 十八层**：
```text
1. **可预测事件环【这个服务器早就有而从未发送**】**
2. ⇒ **它是 playerState 里【缺失的单个最大的东西**】**
3. ⇒ **零售 dm demo 断言 `pe.eventSequence` 与 `pe.oldEventSequence` **各 `4225` 次**】**
4. ⇒ **而四个环槽【各约 `1200` 次**】**
5. ⇒ **⇒ 一场比赛里【大约一万一千次断言**】，而没有一次是我们的**
6. ⇒ **那是脚步、落地、开火、换弹与拾取：【击杀之间发生的一切**】**
7. ⇒ **而那些事件【不是新工作**】**
8. ⇒ **原生引擎自己的 `Pmove` 产生它们**
9. ⇒ **`SV_ReadNativePredictableEvents` 已经在每次 think 之后把它们从原生 playerState 拉出**
10. ⇒ **而子弹路径【已经在消费它们**】**
11. ⇒ **它们【被读了、被服务端用了、并在线上之前被丢掉**】**
12. ⇒ **原生偏移与 netfield 偏移【是同一个数字**】**
13. ⇒ **`PredictableEventSequenceOffset = 0x108` ⇒ netfield 索引 `1`**
14. ⇒ **`PredictableEventsOffset = 0x10C` ⇒ 索引 `21`**
15. ⇒ **环按 `sequence & 3` 索引**
16. ⇒ **⇒ 所以它【逐槽**】拷贝而不是按 `batch reader` 返回的顺序**
```

### 5.2 ⭐⭐⭐ **"被读了、被服务端用了、并在线上之前被丢掉"**

**✅ 与 §413 的"定义了但没接线"**同族（**第八次"，但这里是【读到了而丢弃"而不是"没写"**）。

**⇒ 三层**：
```text
§413  `MatchEndTimeConfigStringIndex` 定义了而【写通道不存在】
§416  `predictableEvents` **读到了、服务端用了**而【线上之前丢掉】
⇒ **⇒ 后者更隐蔽**（**数据在手上而没发**）
```

**✅ ⭐⭐ **"最后一公里的丢失"** —— 比"没有数据"更难发现。

**⚠ 而"`0x108` = netfield `1`，`0x10C` = 索引 `21`"⇒ **两个偏移与两个索引是两套编号**。】

**⇒ 三层**：
```text
`0x108` ⇒ **原生结构偏移**
索引 `1` ⇒ **netfield 表位置**
⇒ **⇒ 所以【`0x108` 会不会等于 `1`？不会】
```

**⚠ 而注释说**"原生偏移与 netfield 偏移是同一个数字"** ⇒ **矛盾。**

**⇒ 三层**：
```text
注释：**"native offsets and the netfield offsets are the same numbers"**
而：`0x108` 与 `1` 【不是同一个数字**】
⇒ **⇒ 所以【注释的措辞可能指的是"字段对应"而不是"数值相等**】
```

**⚠ 一个**需要标注的措辞歧义**。

**✅ 但"`0x108` → 索引 `1`"与"`0x10C` → 索引 `21`"给出了一对**（偏移, 索引）映射**。

### 5.3 而**`perks` 的三个 `32` 位**

```cpp
// THE PERK SET. Three consecutive 32-bit netfields, indices 123/124/125
// at offsets 0x584/0x588/0x58C, and this server has never written any of
// them - which is why no perk icon has ever appeared.
//
// PERKS ARE NOT A hudElem, and that was worth measuring before building
// one. Every material-bearing element in the retail dm demo is the hit
// marker (24x48), a 120x9 bar, a 640x480 backdrop or a waypoint (10x10);
// there is no small repeated icon and nothing that looks like a perk
// row. The client instead ships `loadoutPerk1/2/3` and a
// `perk_sidebar_hud`, and draws the row from playerState.
//
// MEASURED (Tools/olfinal/mine-perk-bits.py over all 6160 snapshots):
// tracked as a TRIPLE rather than three histograms, because the question
// is what they hold together at one instant. The dominant live state is
//
//     (132, 16777216, 0)   4078 of 6160 frames, EXACTLY THREE SET BITS
//                          field 123 bits 2 and 7, field 124 bit 24
//
// Three bits, three perks, three icons. Field 125 is zero while a player
// is alive and only carries anything before the first spawn and during
// the outro, so the live mask is 123 and 124.
```

**⇒ 二十四层**：
```text
1. **三个连续的 32 位 netfield**：索引 `123`/`124`/`125`，偏移 `0x584`/`0x588`/`0x58C`
2. ⇒ **而这个服务器【从未写过任何一个**】**
3. ⇒ **⇒ 那就是【为什么从来没有一个 perk 图标出现过**】**
4. ⇒ **perk 【不是**一个 hudElem**】
5. ⇒ **而那件事【在造它之前**】值得测量**
6. ⇒ **零售 dm demo 里【每一个带材质的元件】是**：
      · **命中标记（`24x48`）**
      · **一个 `120x9` 的条**
      · **一个 `640x480` 的背景**
      · **或者一个 waypoint（`10x10`）**
7. ⇒ **⇒ 【没有小的重复图标，也没有任何看起来像 perk 行的东西**】**
8. ⇒ **客户端【改为发运 `loadoutPerk1/2/3` 与一个 `perk_sidebar_hud`**】**
9. ⇒ **并从 playerState 画那一行**
10. ⇒ **测量（`mine-perk-bits.py` 覆盖全部 `6160` 个快照）**：
      · **作为一个【三元组】追踪而不是三个直方图**
      · **因为问题是【它们在一个瞬间一起持有什么**】
11. ⇒ **主导的活体状态是 `(132, 16777216, 0)`，占 `6160` 帧里的 `4078`**
12. ⇒ **【恰好三个置位**】：
      · **字段 `123` 的位 `2` 与 `7`**
      · **字段 `124` 的位 `24`**
13. ⇒ **三个位、三个 perk、三个图标**
14. ⇒ **字段 `125` 在一个玩家活着时是零**
15. ⇒ **只在首生前与 outro 期间携带任何东西**
16. ⇒ **⇒ 所以【活体掩码是 `123` 与 `124`**】**
```

### 5.4 ⭐⭐⭐ **"作为一个三元组追踪而不是三个直方图，因为问题是它们在一个瞬间一起持有什么"**

**✅ 这是本报告里**最重要的一条统计方法**。**

**⇒ 三层**：
```text
错误方法：**三个独立直方图** ⇒ **知道每个字段的分布，不知道它们的关系**
正确方法：**三元组联合** ⇒ **知道它们【在同一瞬间**】的样子
⇒ **⇒ 所以【相关字段必须联合统计**】
```

**✅ 与 §404 的"按次数统计定的，不是按位置猜"**同族（**第四次"统计方法决定结论"）。

**⇒ 三层**：
```text
§403  **位置不可靠** ⇒ 按时间轴取证
§404  **位置不可靠** ⇒ 按条件频次统计
§416  **单字段分布不可靠** ⇒ 按三元组联合统计
```
**✅ ⭐ **一个"统计粒度"的三级递进**。

**⚠ 而"`(132, 16777216, 0)`"⇒ **让我验证是三个置位**。**

**⇒ 计算**：
```text
132      = 0b10000100        ⇒ 位 2 与 7 ✓ (两个)
16777216 = 0x1000000 = 2^24  ⇒ 位 24 ✓ (一个)
0        ⇒ 零
合计 3 个置位 ✓
```

**✅ **精确吻合**。

**✅ ⭐⭐ **一个"注释里的位计数被独立复算命中"的实例**。

**⚠ 而"`4078 / 6160 = 66.2%`"⇒ **主导但不绝对是**。**

**⇒ 而 `SvRetailLivePerks{ 132u, 16777216u, 0u }` 就是那个值。**

**⇒ 三层**：
```text
常量：`{132, 16777216, 0}`
实测：**`4078/6160` 帧**
⇒ **⇒ 所以【它是"最常见的状态"而不是"唯一的状态"**】
```

**✅ 而 `9.2` 说"同一 demo 也携带 `4`/`5`/`6` 位置位"⇒ **所以 `three is a default, not a bound`**。**

**⇒ 三层**：
```text
`(268, 16777216, 0)` ⇒ **`268 = 0b100001100`** ⇒ **3 位**（位 2/3/8）
`(896, 16777216, 0)` ⇒ **`896 = 0b1110000000`** ⇒ **3 位**（位 7/8/9）
`(300, 16777216, 0)` ⇒ **`300 = 0b100101100`** ⇒ **4 位**（位 2/3/5/8）
`(420, 17039360, 0)`  ⇒ **`420 = 0b110100100`**（3 位）+ **`17039360 = 0x1040000`**（2 位）⇒ **5 位**
```

**✅ 所以"4/5/6 位置位"的注释是**正确的**（我复算了四个样本）。**

**✅ ⭐⭐⭐ **"三个是默认值，不是界限"** —— 一个**极精确的措辞纠正**（注释自己记录了早先的错误）。

**⇒ 三层**：
```text
早先的注释："恰好三个置位，正好三个 perk" ⇒ **当成一个界限**
真相：**三个是【默认**】，而更宽的状态是【配装**】而不是解码噪声
⇒ **⇒ 所以【这里什么都不应该假设一个计数**】
```

**✅ ⭐ **一个"从界限到默认"的语义降级**。

### 5.5 而**`perkHudVisible` 的"玩家已接受"**

```cpp
// PLAYER-ACCEPTED 2026-08-23: with this set whenever a living player holds
// perks, the sidebar comes up and STAYS up, and a player looking at it called
// that right. So this is finished as a feature and what follows is a PARITY
// note, not a defect - do not "fix" it into a flash on somebody's guess.
//
// TODO(CODOL): the retail TRIGGER is still not established. The dm demo asserts
// index 122 nine times (0x7, 1x2) in 621 seconds while perks[0] is asserted 169
// times in the same match, so "the player has perks" is NOT what retail keys it
// on, and a demo replay would diff here. Exit condition: decode WHEN the demo's
// two 1s occur and what changed alongside them.
```

**⇒ 十六层**：
```text
1. **玩家已接受 2026-08-23**：**这个设上之后侧栏出现并【保持**】**
2. ⇒ **一个看着它的玩家说那是对的**
3. ⇒ **⇒ 所以这个【作为一个特性已完成**】**
4. ⇒ **而接下来的是一份【对等性说明，不是一个缺陷**】**
5. ⇒ **【不要】在某人的猜测上把它"修"成一次闪烁**
6. ⇒ **TODO：零售的【触发**】仍未确立**
7. ⇒ **dm demo 断言索引 `122` **九次**（`0x7`，`1` 两次）
8. ⇒ **而 `perks[0]` 在【同一场比赛**】断言 `169` 次**
9. ⇒ **⇒ 所以"这个玩家有 perk"【不是**零售的判据**
10. ⇒ **而一次 demo 重放会在这里出差异**
11. ⇒ **退出条件：解出 demo 的那两个 `1` **何时**发生以及什么同时变了**
```

### 5.6 ⭐⭐⭐ **"不要在某人的猜测上把它修成一次闪烁"**

**✅ 这是本报告里**最重要的一条"特性已完成"的判据**。**

**⇒ 三层**：
```text
观察：**我们的行为与零售不同**（我们恒真，零售九次）
而：**玩家说我们的行为对**
⇒ **⇒ 所以【这不叫缺陷，叫对等性说明**】
```

**✅ 与 §410 的"一个交付不了任何东西的特性对一场活的比赛没有主张"**完全同族（**第二次"什么算完成"）。

**⇒ 三层**：
```text
§410  交付不了 ⇒ **关掉**
§416  交付了且玩家认可 ⇒ **保留，即使与零售不同**
⇒ **⇒ 判据是【交付 vs 不交付**】，不是【与零售一致**】
```

**✅ ⭐⭐⭐ **一个"完成"的判据：玩家能用**，而不是**逐字节还原**。

## 六、**`cursorHint` 的三字段与"零而不是 -1"**

### 6.1 那段

```cpp
// The RELATIVE index into configstring band 856. SIGNED -- codec -8,
// sign-extended from bit 7 by the client -- which is the only thing
// that makes retail's idle value of -1 expressible.
//
// ZERO HERE, NOT -1, AND THAT IS A DELIBERATE DEPARTURE. Retail idles
// these two at -1 and 2047; this server idles them at 0. The client
// cannot tell, because sub_45A450 reads cursorHint FIRST and returns
// before touching either of them, and its own fade-out path writes
// (0, -1) into the HUD cache regardless of what the playerState says.
// What the departure buys is that a player who never looks at anything
// usable pays no bits at all: a null delta baseline is a ZEROED
// playerState, so retail's sentinels would be sent to every client on
// its first snapshot forever, to say nothing.
```

### 6.2 十六层

```text
1. **`cursorHintString` 是 configstring 带 `856` 的【相对索引**】**
2. ⇒ **【有符号**】—— **codec `-8`，由客户端从位 `7` 符号扩展**】
3. ⇒ **⇒ 那是【唯一让零售的 `-1` 空闲值可表达**】的东西**
4. ⇒ **这里用【零而不是 `-1`，而那是一次刻意的偏离**】**
5. ⇒ **零售把这两个空闲在 `-1` 与 `2047`**；**这个服务器空闲在 `0`**
6. ⇒ **【客户端分辨不出**】**
7. ⇒ **因为 `sub_45A450` 【先读 `cursorHint`**】**
8. ⇒ **并在【触及它们任何一个之前返回**】**
9. ⇒ **而它自己的淡出路径【无论如何都往 HUD 缓存写 `(0, -1)`**】**
10. ⇒ **那个偏离【买到了什么**】**
11. ⇒ **一个【从不看任何可用东西**】的玩家【**一点位都不付**】**
12. ⇒ **因为一个【空的 delta 基准是一个零化的 playerState**】
13. ⇒ **所以零售的哨兵会【永远在每一份第一快照上发给每一个客户端**】**
14. ⇒ **只为说"没有"**
```

### 6.3 ⭐⭐⭐ **"零化基准 ⇒ 零售的哨兵永远要发"**

**✅ 这是本报告里**最实用的一个优化推理**。**

**⇒ 三层**：
```text
我们的 base：**零化 playerState**
零售的值：`-1` 与 `2047`
⇒ **⇒ 所以【若我们用零售的值，每一份第一快照都要发送它们**】
而【用 `0` ⇒ 等于 base ⇒ 永不发送**】
```

**✅ 与 §414 的"把 baseline 的 xmodel 改成我们的值 ⇒ 不发送"**完全同族（**第二次"用相等来消除发送"）。

**⇒ 三层**：
```text
§414  `base = ours` ⇒ **字段相等 ⇒ 不发**
§416  **值 = `0` = base** ⇒ **字段相等 ⇒ 不发**
⇒ **⇒ 同一手法两处**
```

**✅ ⭐⭐ **"用『与基准相等』来消除发送"** —— 一个**反复出现的优化模式**。

**⚠ 而"客户端分辨不出"⇒ **一个三点论证**：**
```text
① `sub_45A450` **先读 `cursorHint`** ⇒ 零 ⇒ **立即返回**
② 它自己的淡出路径**写 `(0, -1)`** ⇒ **不看 playerState**
③ ⇒ **所以两个值在任何可观察路径上都等价**
```

**✅ ⭐ **"一个三点论证"** —— 一个**完整的"不可观察"证明**。

### 6.4 而**`cursorHint` 的枚举与 `5..1704`**

```cpp
enum class SvCursorHint : std::uint16_t
{
    None = 0, NoIcon = 1, Activate = 2, Health = 3, Friendly = 4,
};
inline constexpr std::uint16_t SvCursorHintWeaponBase = 4;
inline constexpr std::uint16_t SvCursorHintMaximum = 1704;
```

**⇒ 六层**：
```text
1. **五个枚举值 `0..4`**
2. ⇒ **而 `5..1704` 是"武器（值 `- 4`）**"**
3. ⇒ **并从 `PLATFORM_PICKUPNEWWEAPON` 取文本【而不是从下面的字符串**】**
4. ⇒ **⇒ 所以【一个值域承载两种语义**】**
5. ⇒ **`1704 + 4 = 1708`？不，`maximum = 1704`**
6. ⇒ **⇒ 所以 `5..1704` 是 `1700` 个武器槽**
```

**✅ ⭐ **一个"值域分两段"的实例**（**`0..4` 枚举，`5..1704` 武器**）。

**⚠ 而"`SvCursorHintWeaponBase = 4`"⇒ **所以 `value - 4` 得武器号，`5-4=1`**。**

**⇒ 三层**：
```text
`cursorHint = 5` ⇒ **武器 `1`**
`cursorHint = 1704` ⇒ **武器 `1700`**
⇒ **⇒ 所以【`1700` 个武器槽**】
```

**✅ 与 §403 的"`a 1198`"**不同（**那是武器**资产索引**，这是**hint 值**）。

**⚠ 一个**需注意的编号空间差异**。

## 七、关键结论

1. **⭐⭐⭐ "线缆上没有『无队伍』这个值，发一个就杀死客户端"**：`sub_53F5F0` 在 `v1[62] != 1 && != 2` 时**返回 `0`**，而 `sub_59CC70` **通过它写 `v4[251]` 不检查** ⇒ 任何队伍不是 `1`/`2` 的玩家让**其它每一个客户端**在 `+0x3EC` 出错。
2. **⭐⭐ "五轮里四轮因此丢了一个客户端，而它只在自由混战"**，用钩子测得 **A 在 `index=1` 处 `kind=0`，B 在 `index=0` 处 `kind=0`** ⇒ **两个互相解析，各得一次空返回**（对称必然）。
3. **⭐⭐⭐ 与 §413 的"零 viewmodel ⇒ AV"完全同一条链**：**`sub_53F5F0` + `sub_59CC70` 不检查写入** ⇒ "没有武器"与"没有队伍"两个不同的"没有"走同一个崩溃点。
4. **⭐ `v4[251]` 与 `+0x3EC` 是同一地址**（`251 × 4 = 1004 = 0x3EC`）。
5. **⭐⭐ `SV_PresentableTeam` 用 `faction`**：**"faction 已经选模型，所以它是一个没有队伍的玩家的诚实的呈现队伍"**；`Spectator (3)` 折算同路（"它不比 `0` 更可表示"）—— 第八次"用一个既有的代理信号"。
6. **⭐⭐⭐ 色带的方向**：`sub_AB4490` 解析为 `lerp(fromColor, color, (now - fadeStartTime)/fadeTime)`，**保持在 `color`** ⇒ **`color` 是终点、`fromColor` 是起点**，四个字段在 `0x30/34/38/3C`（描述符 `0/12/10/13`）。
7. **⚠ 缩放的四个字段【偏移顺序相反】**：`fromFontScale +0x18`（起点）→ `fontScale +0x14`（终点），窗口 `[+0x1C, +0x1C+0x20]`。
8. **⭐ `fontScale` 的编解码器**：**六个原始位 / 除以 `10.0` / 无变化前缀** ⇒ **`0.0..6.3`**（`63` 个值，与 `6` 位闭合）。
9. **⭐ `font` 的 `4` 位**：`1`/`6` ⇒ `0.5`，`2`/`7` ⇒ `1/3`，其余 `0.25` ⇒ **`+5` 同义**（两族）。
10. **⭐⭐⭐ "那个读法对 3.3.3.3 是正确的；把它的编号进口到 OLfinal 树里则不是"**：`0x00BD81C3` 在 `out.exe` 里属于 `sub_BD7780`，那是一个 **dvar 注册器（`r_picmip`/`r_specular`/`r_displayMode`）而不是 HUD 绘制器** ⇒ **"一个在目标 build 里存在但做别的事的地址比一个不存在的地址更危险"**。</br>
11. **⭐⭐ 实测的四个 hudElem 类型**：`TYPE 5` = 命中标记（`-12,-12,24,48`）、`TYPE 2` = 分数弹出（`value=50 label=397`，`0.9`→`3.0`）、`TYPE 14` = 唯一的世界坐标元件、`TYPE 4` = 全屏背景 ⇒ **`Icon`/`Waypoint` 各 `+1`**。
12. **⭐⭐⭐ "一个版本插入了一个类型 ⇒ 之后所有编号 `+1`"** —— 与 §415 的"`ET_EVENTS` 22 → 23"**同一个模式**。
13. **⭐ "一个图标元件被当类型 4 发送会变成一个全屏黑幕"`** —— 一个可推导的灾难预测。
14. **⭐⭐ 枚举只承认六个值**（`Free 0`/`Text 1`/`Value 2`/`PlayerName 3`/`Icon 5`/`ClockDown 12`/`Waypoint 14`），而 **`6..8` 是秒计时器族、`9..11` 是十分之一秒族**；**`Text = 1` 的注释记录了"曾经用 `4` 与 `8`，而它们是原始 XOR 载荷而不是类型编号"** ⇒ 一次"混淆编码层与语义层"的错误。
15. **⭐⭐⭐ "可预测事件环，这个服务器早就有而从未发送"**：零售一场比赛断言 `pe.eventSequence` 与 `pe.oldEventSequence` **各 `4225` 次**，四个环槽各约 `1200` 次 ⇒ **约一万一千次断言没有一次是我们的**；**脚步、落地、开火、换弹与拾取**。
16. **⭐⭐ "它们被读了、被服务端用了、并在线上之前被丢掉"`** —— **"最后一公里的丢失"**比"没有数据"更隐蔽。
17. **⭐ 两个偏移**：`PredictableEventSequenceOffset = 0x108`（netfield `1`）、`PredictableEventsOffset = 0x10C`（索引 `21`），环按 `sequence & 3` 索引 ⇒ **逐槽拷贝**。
18. **⭐⭐⭐ "perk 不是 hudElem：零售 demo 里每一个带材质的元件是命中标记（`24x48`）、一个 `120x9` 条、`640x480` 背景或 waypoint（`10x10`），没有小的重复图标"`** ⇒ 客户端从 playerState 画 perk 行。
19. **⭐⭐⭐ `(132, 16777216, 0)` 在 `6160` 帧里占 `4078`，恰好三个置位**（字段 `123` 位 `2`+`7`，字段 `124` 位 `24`）—— 我复算：`132 = 0b10000100`、`16777216 = 2^24` ⇒ **三位 ✓**。</br>
20. **⭐⭐⭐ "作为一个三元组追踪而不是三个直方图，因为问题是它们在一个瞬间一起持有什么"`** —— 第四次"统计方法决定结论"。
21. **⭐⭐ "三个是默认值，不是界限"**（同一 demo 还有 `(268,...)`/`(896,...)`/`(300,...)`/`(420, 17039360, 0)` 的更宽状态）—— **PERK GREED 通配符正是让一个玩家超过三个的东西**；"Nothing here should assume a count"。
22. **⭐⭐⭐ `perkHudVisible` 的"玩家已接受 ⇒ 这是一个已完成特性，不是缺陷 —— 不要在某人的猜测上把它『修』成一次闪烁"**，尽管**零售九次而我们恒真**（`perks[0]` 同场断言 `169` 次 ⇒ "有 perk"不是零售的判据）—— 第二次"什么算完成"。
23. **⭐⭐⭐ `cursorHintString` 用 `0` 而不是 `-1` 的四层论证**：① 客户端先读 `cursorHint` 并立即返回；② 它自己的淡出路径写 `(0, -1)`；③ 零化基准 ⇒ **零售的哨兵会永远在每一份第一快照上发给每一个客户端，只为说"没有"** ⇒ **用 `0` 一点位都不付**。第二次"用『与基准相等』消除发送"。
24. **⭐ `cursorHint` 的值域分两段**：`0..4` 是枚举，`5..1704` 是"武器（值 `- 4`）"⇒ **`1700` 个武器槽**，文本来自 `PLATFORM_PICKUPNEWWEAPON`。

## 八、未闭合点

- `0x00AB44B0` 的"窗口关闭后保持"是否有例外。
- `TYPE 13` 在图示里缺失（`ClockDown = 12` 而 `Waypoint = 14`）。
- `perkHudVisible` 的零售触发（demo 的两个 `1` 何时发生）。
- `SvPlayerState` 的 `hudCurrent`/`hudArchival` 各 `31` 槽（与 §411 的"31 槽"一致）。
- `SvCharacterCustomization` 的 `recordItemIds` 是"服务器 DObj 读它而 clientInfo 只有一个字符字段"。
- `sv_snapshot_mp.hpp` 1650 行之后未读取（**共 `4703` 行**）。
