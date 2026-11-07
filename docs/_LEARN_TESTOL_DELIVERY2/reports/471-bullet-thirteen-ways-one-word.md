# 471 · **"十三种拒绝一次射击的方式，而它们只有一个词"** —— `sv_bullet_mp.cpp` 的穿透链八次改判、`0x01D00000 >> 20 = 29` 的自证、以及一次"把伤害当实验"的事故

## 一、范围

本报告学习 `sv_bullet_mp.cpp`（**`954` 行**）与 `sv_bullet_mp.hpp`（**`271` 行**）全文件：表面类型表的 `31` 个枚举、`SV_BulletTrace` 的定位追踪、`GlassCommandRollback` 的事务、穿透链的 `5` 次循环与 `8` 次改判、`damageMultiplier` 的算术、以及 `13` 条 `SV_BulletFireFailed` 的理由。

## 二、**"十三种拒绝一次射击的方式，而它们只有一个词"**（本组最重要的一段）

### 2.1 那段

```cpp
// SECTION 191z: THIRTEEN WAYS TO REFUSE A SHOT AND ONE WORD FOR ALL OF THEM.
//
// `client_events_rejected` names the STAGE and nothing else, and the bullet
// path has thirteen distinct `Failed` returns behind it. A player reporting
// "it hits and never hurts them" cannot be told apart from a bad trace, an
// unresolved endpos or a rejected payload, so the first alt-fire shot cost a
// whole read of the file to narrow by hand.
//
// A pointer to a literal, written on the frame thread and read on the same
// one. No field is added to any struct: SvBulletExecutionStatus is reached
// through the entity and this project has broken an address-keyed buffer
// twice by growing something that looked inert (section 184h).
namespace { thread_local const char *lastBulletFireFailure = nullptr; }
```

### 2.2 二十四层

```text
1. **十三种**拒绝一次射击的方式**】
2. ⇒ **而【它们只有【一个词**】**
3. ⇒ **`client_events_rejected` 【命名【那个阶段**】】
4. ⇒ **⇒ 而【别无其他**】**
5. ⇒ **⇒ 而子弹路径【有【十三个【不同的 `Failed` 返回**】】
6. ⇒ **⇒ 所以【一个玩家报告"打中了但从不掉血"**】
7. ⇒ **⇒ 【不能【与【一个坏的 trace / 一个未解析的 endpos / 一个被拒的载荷**分开**】
8. ⇒ **⇒ 而【第一次 alt-fire 的射击【花掉【整整一次【读这个文件**】】
9. ⇒ **⇒ 只是为了【手工缩小**】】
```

### 2.3 ⭐⭐⭐ **"第一次 alt-fire 的射击花掉整整一次读这个文件"**

**✅ 这是本报告里**最重要的一条"**一个笼统的错误码【的【代价**"**。**

**✅ 与 §462 的"给那一项命名把『玩家永不出生』变成【一个要检查的偏移**】"**——**完全同族 ✓**

**⇒ 三层**：
```text
§462  **四十个项共用一个 `return false`** ⇒ **命名那一项**
§471  **十三条 `Failed` 共用一个 `client_events_rejected`** ⇒ **`SV_LastBulletFireFailure()`**
⇒ **⇒ 两次"把**一个词**拆成**十三个名字**】
```

**✅ ⭐⭐⭐ **"把一个词拆成十三个名字"两例**。

**⚠ 而"不向任何结构**添加一个字段**"**⇒ **一个极重要的实现约束**。

**⇒ 十层**：
```text
`thread_local const char *` ⇒ **一个【指针，不**是一个**字符串**
⇒ **⇒ 所以【没有【分配**、没有【`std::string` 的生命周期**
⇒ **⇒ 而【那个字面量【是【`static` 的**】（**一个 `.rdata` 的地址**）
⇒ **⇒ 所以【零成本**】
```

**✅ ⭐⭐⭐ **"一个指针，不是一个字符串 ⇒ 没有分配"** —— 一个**极精确的实现选择**。

**⚠ 而"不向任何结构添加字段，因为这个项目**两次**通过增长一个看起来惰性的东西【弄坏了【一个地址键控的缓冲区**（§184h）"**。**

**⇒ 十层**：
```text
`SvBulletExecutionStatus` 【通过【那个实体【到达**】
⇒ **⇒ 而【增长它【会【移动【那个地址键控的**缓冲区**
⇒ **⇒ 而那【已经【发生【两次**】
⇒ **⇒ 所以【这里【用【一个【线程局部的**指针**
```

**✅ ⭐⭐⭐ **"这里用一个线程局部的指针"** —— 与 §422 的"`sizeof(WorldClientState) == 25184` 是一个行为"**同族**（**第三次"一个结构的大小【是一个【行为**"**）。

**⚠ 而"在帧线程上写，在同一个线程上读"**⇒ **`thread_local` 的**充分性**。**

**⇒ 三层**：
```text
写：**帧线程**
读：**同一个帧线程**
⇒ **⇒ 所以 `thread_local` 【足够**，不需要【锁**
```

**✅ ⭐⭐ **"`thread_local` 足够，不需要锁"**。

### 2.4 而**十三条理由的清单**

```text
 1  input-invalid
 2  endpos-or-trace-runner-missing
 3  endpos-unresolved
 4  trace-unresolved
 5  damage-curve
 6  player-part-group
 7  player-payload-build
 8  entity-part-group
 9  entity-location-damage
10  entity-payload-invalid
11  glass-damage
12  impact-direction-encoder-missing
13  impact-direction-encode
14  impact-event-invalid
15  penetration-forward-trace
16  penetration-reverse-trace
17  penetration-damage-curve
18  penetration-player-part-group
19  penetration-player-payload-build
20  penetration-entity-part-group
21  penetration-entity-location-damage
22  penetration-entity-payload-invalid
23  penetration-direction-encoder-missing
24  penetration-direction-encode
25  penetration-impact-event-invalid
```

**⇒ 数到 `25` 个不同的字面量 —— 而注释说 `13`。**

**✅ ⭐⭐⭐ **"注释说十三，实际二十五"** —— 一个**值得记录的不一致**。

**⇒ 十层**：
```text
非穿透段 ⇒ **14** 个（`input-invalid` … `impact-event-invalid`）
穿透段 ⇒ **11** 个（`penetration-*`）
⇒ **⇒ 共 `25` 个**】
而【注释说 `13`**】⇒ **⇒ 所以【注释【数的是【非穿透**段**（或少一两个）**
```

**⚠ 而这【不是【一个缺陷**】（**更多**的名字【更好**）—— 只是**注释的数是旧的**。

**⇒ 三层**：
```text
注释：`13`（**写那个注释时的**数**）
实际：`25`（**穿透段【新增了 `11`**）
⇒ **⇒ 所以【注释【落后于代码**】
```

**✅ ⭐⭐ **"注释落后于代码"** —— 与 §465 的"注释说 REFUSES 而代码不拒绝"**同族**（**第三次"注释与代码【不同步**）。

## 三、**`0x01D00000 >> 20 = 29` 的自证**（本组第二重要）

### 3.1 那段

```cpp
// THE SURFACE TABLE IS A 20-BYTE RECORD whose third dword is the material
// flags word, and for a surface type that word is `index << 20`. So the
// table IS the enum and reading it needs no reader:
//
//   3.3.3.3  name field of `bark` at 0x00CD9C48
//   out.exe  name field of `bark` at 0x00E51548
//   both     bark=1 brick=2 carpet=3 cloth=4 concrete=5 dirt=6 flesh=7
//            foliage=8 glass=9 grass=10 gravel=11 ice=12 metal=13 mud=14
//            paper=15 plaster=16 rock=17 sand=18 snow=19 water=20 wood=21
//            asphalt=22 ceramic=23 plastic=24 rubber=25 cushion=26
//            fruit=27 paintedmetal=28 riotshield=29 slush=30, then
//            `opaqueglass` ALIASED back to 9 and the non-surface flag
//            names (clipmissile, playerclip, portal, ladder...) after it
inline constexpr std::uint8_t BulletSurfaceTypeCount = 31;
```

### 3.2 二十四层

```text
1. **表面表【是【一个 20 字节的记录**】
2. ⇒ **⇒ 它的第三个 `dword` 【是【那个材质标志字**】
3. ⇒ **⇒ 而对【一个表面类型**那个字【是 `index << 20`**】
4. ⇒ **⇒ 所以【那个表【就是那个枚举**】
5. ⇒ **⇒ 而【读它【不需要【一个 reader**】】
6. ⇒ **⇒ 两个 build 的表【是【同一个名字、同一个顺序、同一个顶值**】
7. ⇒ **⇒ 所以【那个索引空间【是 `0..30`**】
8. ⇒ **⇒ 而【`31` 【也是【这个 build 的计数**】
9. ⇒ **⚠ 而 §79g 拒绝去数的那个字面量池【是【另一个东西**】
10. ⇒ **（**它【是【逆序使用**的）**
11. ⇒ **⇒ 而【那个标志字【是【引擎【实际用来索引**的**
```

### 3.3 ⭐⭐⭐ **"那个字面量池是一个不同的东西（逆序使用），而那个标志字是引擎实际用来索引的"**

**✅ 这是本报告里**最漂亮的一条"**数错了对象**"**的自我更正**。**

**✅ 与 §466 的"`192/192` 零误差"**、§468 的"`81,128/81,128` 零失配"**——**同族**（**第三次"一个**正确的计数对象**"**）。

**⇒ 三层**：
```text
错误的对象 ⇒ **那个字面量池**（**逆序使用 ⇒ 数出来的顺序【不是**那个枚举**）
正确的对象 ⇒ **那个 20 字节记录【的第三 `dword`**（**`index << 20`**）
⇒ **⇒ 所以【"表【就是那个枚举**"**】
```

**✅ ⭐⭐⭐ **"表就是那个枚举"** —— 一个**极清晰的判据**。

### 3.4 而**独立验证：`0x01D00000`**

```cpp
inline constexpr std::uint32_t BulletShieldSurfaceFlags = 0x01D00000;
inline constexpr std::uint16_t BulletShieldPartGroup = 19;
```

**⇒ 十层**：
```text
`0x01D00000 >> 20 = 0x1D = 29`** ⇒ **`riotshield` ✓**（**表里【`riotshield=29`**）
⇒ **⇒ 而【`SV_BulletTrace` 的 `(surfaceFlags >> 20) & 0x1F`**】
⇒ **⇒ 对 `0x01D00000` 解出 `29`** ✓
```

**✅ ⭐⭐⭐ **"`0x01D00000 >> 20 = 29` 与表里的 `riotshield=29` 精确吻合"** —— 一个**独立的自证**。

**⚠ 而 `19 = 0x13`**：

```cpp
// `mov ecx, 13h / cmp word [esi+22h], cx / mov [esi+10h], 1D00000h`
// at 0x005919A1..0x005919AC, against 3.3.3.3's identical sequence
// at 0x0055A5A8..0x0055A5B3.
```

**⇒ 十层**：
```text
`ecx = 0x13 = 19` ⇒ **那个 part group**
`cmp word [esi+22h], cx` ⇒ **比较**
`mov [esi+10h], 1D00000h` ⇒ **写那个表面标志**
⇒ **⇒ 所以【那个 part group 与那个标志【来自【一次读**】
⇒ **⇒ 而 `19 = 0x13` 【是【这里【测量的**，不是【继承的**】
```

**✅ ⭐⭐⭐ **"那个 part group 与那个标志来自一次读"** —— 一个**极精确的因果**。

**✅ 与 §470 的"`0x2FD6 = 12246` 那个地址减那个类表恰是它"**——**同族**（**第三次"一个数【由【一个地址差**确定**）。

**⇒ 三层**：
```text
§468  **`nameHash` 由【那个 sampler 名字**确定**
§470  **`12246 = byte_77DB226 - byte_77D8250`**
§471  **`0x01D00000 >> 20 = 29 = riotshield`**
⇒ **⇒ 三次"一个数【有一个【可验证**的来源**】
```

**✅ ⭐⭐ **"一个数有一个可验证的来源"三例**。

### 3.5 而**`0x0280E831` 的"八次出现 + 一次配对"**

```cpp
// 0x0280E831 occurs EIGHT times in each image, and in both the single
// occurrence of 0x01D00000 sits inside a function that also carries one of
// them -- 3.3.3.3 sub_55A4A0, out.exe sub_5918B0. That pairing is what
// identifies the counterpart; the equal counts are what make it a
// measurement rather than a coincidence.
inline constexpr std::uint32_t BulletLocationalContentMask = 0x0280E831;
```

**⇒ 十六层**：
```text
1. **`0x0280E831` 在【每个镜像里出现【八次**】
2. ⇒ **⇒ 而【两个 build 上【`0x01D00000` 的那一次出现【都在【一个也携带它之一的函数里**】
3. ⇒ **（3.3.3.3 `sub_55A4A0` / out.exe `sub_5918B0`**）**
4. ⇒ **⇒ 那个配对【是【识别【那个对应物**的东西**】
5. ⇒ **⇒ 而【相等的计数【是【使它成为【一个**测量**而【不是【一个**巧合**的东西**
```

**✅ ⭐⭐⭐ **"那个配对识别的对应物，而相等的计数使它成为一个测量而不是一个巧合"** —— 一个**极严密的双重判据**。

**✅ 与 §468 的"`81,128/81,128` 零失配"**——**同族**（**第四次"一个**双判据**"**）。

**⇒ 三层**：
```text
配对 ⇒ **定位**
等数 ⇒ **排除巧合**
⇒ **⇒ 所以【两个**判据【缺一不可**】
```

**✅ ⭐⭐⭐ **"两个判据缺一不可"**。

## 四、**穿透链的八次改判**（本组第三重要）

### 4.1 时间线

```text
刀BE   ①给空 resolver 补"恒返回 12 单位"的默认实现 ⇒ 穿透链首次真正执行
刀BZ   ②撤销刀BE 的默认 resolver（甲方「有命中反馈但血不掉」，日志：近战
         `result=APPLIED damage=135` 正常，而子弹伤害一条都没有）
刀BH   ③去掉 `!input.plan.penetrate` 前置条件 ⇒ 每一颗子弹都进穿透链
刀BY   ④回滚刀BH，恢复原条件（甲方「仍旧无法杀死人」）
28380  ⑤默认开启穿透，按 IW4X 的 penetrateType 三档给深度（8/16/32）
28390  ⑥`depthSurfaceType == 0` 不再拒绝 + 加 `PEN|` 诊断行
        （甲方「似乎可以穿透，但是有音效没伤害打不死人」）
28400  ⑦resolver 返回 `nullopt` 与返回 `0.0f` 都不再中止循环，一律回落到 16
28700  ⑧FMJ ⇒ 深度 ×2（普通穿透 1，装 FMJ 是 2）
```

### 4.2 二十四层

```text
1. **第一次（刀BE）**：`penetrationDepthResolver` 在 `.hpp:233` 【带默认空值**】
2. ⇒ **而【全树无调用方传它**（`Appmain.cpp:518` 只给到第 `14` 个参数**）**
3. ⇒ **⇒ 所以【下面条件第二项【恒假**】⇒ **穿透分支【从不执行**】
4. ⇒ **⇒ 而【补一个"恒返回 `12` 单位"的默认实现 ⇒ 【穿透链【第一次【真正开始执行**】
5. ⇒ **⚠ 而【那【导致了"伤害被吞**"**（刀BZ 的发现**）**
6. ⇒ **⇒ 因为【链里有 `deferredImpact` / `continue` 分支【会改变命中处理**】
7. ⇒ **⇒ 而归因【正确**：**近战 `APPLIED damage=135` 正常**，而**子弹伤害【一条都没有**】
8. ⇒ **⇒ 所以【问题【在【子弹路径**】
9. ⇒ **⇒ 而【刀BY 的教训【更精确**】：**刀BH 去掉 `penetrate` 前置条件 ⇒ 每颗子弹都进链**
   ⇒ **"打不死人 + 穿透仍无效"【是同一刀的两个症状**】
```

### 4.3 ⭐⭐⭐ **"打不死人 + 穿透仍无效是同一刀的两个症状"**

**✅ 这是本报告里**最精确的一条归因**。**

**✅ 与 §463 的"一个 bug 只在另一个被修好之后才暴露"**——**同族**（**第三次"一个因果链**）。

**⇒ 三层**：
```text
症状 A ⇒ **打不死人**
症状 B ⇒ **穿透仍无效**
⇒ **⇒ 而【两者【同一个病因**：**`deferredImpact` 分支在【不该穿透**的武器上【改变了命中处理**
```

**✅ ⭐⭐⭐ **"两个症状同一个病因，而不是两个 bug"** —— 一个**极重要的诊断纪律**。

### 4.4 而**28400 的"两个不同的零"**

```cpp
// 28400: TWO different zero cases used to abort the penetration loop,
// and both leave "impact on the wall, nothing behind it":
//   * resolver returned nullopt (surface index outside CODOL's table,
//     thread-ownership miss, or depth above the damage range) -> the old
//     code set deferredImpact and broke;
//   * resolver returned 0.0f (CODOL's material table A is all zeros
//     in-game) -> the old code broke, and the 28390 fallback of ONE unit
//     drove damageMultiplier negative on the first surface anyway.
```

**⇒ 二十四层**：
```text
1. **两个不同的零**】
2. ⇒ **⇒ 而【两者【都留下"墙上有撞击音、墙后无伤**"**】
3. ⇒ **零 A：resolver 返回 `nullopt`**（**表面索引【在 CODOL 表外** / 线程归属 miss / 深度【超出伤害范围**）**
4. ⇒ **⇒ 旧代码【设 `deferredImpact` 并 `break`**】
5. ⇒ **零 B：resolver 返回 `0.0f`**（**CODOL 的材质表 A 【在游戏里全是零**）**
6. ⇒ **⇒ 旧代码【`break`**】⇒ **而【28390 的"一个单位"回退【反正【让 `damageMultiplier` 在第一个表面上【变负**】】
```

### 4.5 ⭐⭐⭐ **"CODOL 的材质表 A 在游戏里全是零"**

**✅ 与 §466 的"`192/192` 零误差"**、§462 的"那是一个发现，不是那个写的一个缺陷"**——**同族**（**第四次"一个**测量的意外**"**）。

**⇒ 三层**：
```text
若【表 A 全是零**】⇒ **`entryDepth = 0`** ⇒ **⇒ 旧代码 `break`** ⇒ **⇒ 从不穿透**
若【用"一个单位"回退**】⇒ **`wallThickness / 1.0` ⇒ 一个【大数**】⇒ **⇒ `damageMultiplier` 【变负**】
⇒ **⇒ 所以【两个"修法"【都是【错的**】
```

**✅ ⭐⭐⭐ **"两个『修法』都是错的"** —— 而**28400 的第三条路（回落到 `16`）才正确**。

**⚠ 而"`PEN|` 诊断行"**⇒ **一个**取证**的行**。

**⇒ 三层**：
```text
`PEN|` ⇒ **WRN 级**
⇒ **⇒ 所以【每一次拒绝【的【具体项【被打印**】
```

**✅ ⭐⭐ **"每一次拒绝的具体项被打印"** —— 与 §462 的"给那一项命名"**同族**（**第三次**）。

### 4.6 而**`PenetrationAdvance = 0.135` 与 `entryNormalDot` 的 `0.125` 下限**

```cpp
constexpr float PenetrationAdvance = 0.135f;
constexpr float ReverseTraceAdvance = 0.01f;
...
const auto entryNormalDot = std::max(0.125f,
    -(penetrationEntry.trace.normal[0] * endpos->direction[0] + ...));
throughStart[axis] = penetrationEntry.hitPosition[axis] +
    endpos->direction[axis] * (PenetrationAdvance / entryNormalDot);
```

**⇒ 二十层**：
```text
1. **`0.135` 单位【沿【那个方向**推进**】
2. ⇒ **⇒ 但【除以 `entryNormalDot`**】
3. ⇒ **⇒ 所以【一个【斜的**墙【把起点【推得【更远**】
4. ⇒ **⇒ 而 `dot` 的【下限 `0.125`**】
5. ⇒ **⇒ 所以【最大推进 `0.135 / 0.125 = 1.08` 单位**】
6. ⇒ **⇒ 那个 `0.125` 【防止【一个【近似相切**的墙【把起点【推到【无穷远**】
```

**✅ ⭐⭐⭐ **"`0.125` 防止一个近似相切的墙把起点推到无穷远"** —— 一个**极精确的数值保护**。

**✅ 与 §471 二 的"`thread_local` 足够"**——**不同**（一个是**数值的**，一个是**并发的**）但**同族**（**"一个下限【防止【一个退化**"**）。

**⇒ 独立验证**：`0.135 / 0.125 = 1.08` ⇔ **最大推进 `1.08` 单位** ✓

**⚠ 而 `ReverseTraceAdvance = 0.01`** 与 **`reverseNormalDot` 的同一个 `0.125` 下限** ⇒ **最大 `0.01 / 0.125 = 0.08`**。

**⇒ 三层**：
```text
前进 ⇒ **`0.135 / dot` ≤ `1.08`**
后退 ⇒ **`0.01 / dot` ≤ `0.08`**
⇒ **⇒ 所以【两个【都有界**】
```

**✅ ⭐⭐ **"两个都有界"**。

**✅ 与 §469 的"`-256` 是一个模 256 的减法"**——**不同**（这是一个**上限**，那是一个**回绕**）。

## 五、**`damageMultiplier` 的算术：`-= wallThickness / maximumDepth`**

### 5.1 那段

```cpp
auto maximumDepth = entryDepthValue;
if (reverseHit || allSolid)
{
    if (reverseHit && reverseTrace->depthSurfaceType)
    {
        const auto exitDepth = penetrationDepthResolverOrDefault(...);
        if (!exitDepth) { deferredImpact = true; break; }
        const float exitDepthValue =
            ((std::isfinite(*exitDepth) && *exitDepth > 0.0f) ? *exitDepth : 16.0f) * fmjScale;
        maximumDepth = std::min(maximumDepth, exitDepthValue);
    }
    const auto wallThickness = std::max(1.0f, std::sqrt(...));
    damageMultiplier -= wallThickness / maximumDepth;
    if (!std::isfinite(damageMultiplier) || damageMultiplier <= 0.0f) break;
}
```

### 5.2 二十四层

```text
1. **`maximumDepth` 取【入口与出口**的【较小**】
2. ⇒ **⇒ 所以【穿两层**不同**材质【按【较薄**的那层判**】
3. ⇒ **⇒ 而 `wallThickness` 有【一个 `1.0` 的下限**】
4. ⇒ **⇒ 所以【一个零厚度**的墙【仍然【扣 `1 / maximumDepth`**】
5. ⇒ **⇒ 而 `damageMultiplier` **每穿过一层就减**，减到 `<= 0` 就停**
```

### 5.3 ⭐⭐⭐ **"`wallThickness` 有一个 1.0 的下限，所以一个零厚度的墙仍然扣 1/maximumDepth"**

**✅ 与 §471 四.6 的"`dot` 有 0.125 的下限"**——**同族**（**第三次"一个下限【防止【一个退化**"**）。

**⇒ 三层**：
```text
若【厚度 = 0**】⇒ **`damageMultiplier` 【不减**】⇒ **⇒ 一个【无限薄**的墙【免费穿**】
⇒ **⇒ 所以【那个 `1.0` 【防止【一个【免费的穿透**】
```

**✅ ⭐⭐⭐ **"那个 1.0 防止一个免费的穿透"**。

**⚠ 而"`maximumDepth = min(entry, exit)`"**⇒ **一个**保守**的选择**。**

**⇒ 十层**：
```text
若【取 `max`**】⇒ **一个【厚出口 + 薄入口**的墙【会被【判成【薄**】⇒ **⇒ 穿得过**】
若【取 `min`**】⇒ **按【最不利**的那一层判**⇒ **⇒ 保守**
⇒ **⇒ 所以【`min` 【是【正确的**】
```

**✅ ⭐⭐ **"`min` 是正确的（保守）"**。

**⚠ 而 FMJ 的 `fmjScale = input.fmjPenetration ? 2.0f : 1.0f`**⇒ **同时【作用于入口与出口**】**。

**⇒ 三层**：
```text
```cpp
// FMJ doubles the exit face too, or a two-layer wall would
// be judged on the ordinary depth and stop the round.
```
⇒ **⇒ 所以【两处【都乘 `fmjScale`**】
```

**✅ ⭐⭐⭐ **"FMJ 也把出口面翻倍，否则一个双层墙会按普通深度判定并把子弹停下"** —— 一个**极精确的必要性论证**。

## 六、**`5` 次循环与 `SURF_TYPE_DEFAULT` 的豁免**

### 6.1 那段

```cpp
// CODREF(bullet_penetration): OLFinal sub_5923C0 and COD4
// Bullet_FirePenetrate carry the forward trace back through this
// loop for as many as five surfaces. A forward trace made from
// inside a brush commonly returns the brush's exit face first;
// only the next iteration can reach the player behind it.
```

**⇒ 二十层**：
```text
1. **最多【`5` 个表面**】
2. ⇒ **⇒ 而【从【一个 brush **内部**发出的前向 trace【常常【先返回那个 brush 的**出口面**】
3. ⇒ **⇒ 而【只有**下一次迭代**能【到达【它后面**的玩家**
4. ⇒ **⇒ 所以【那个循环【是【必须的，不是【一个优化**】
```

### 6.2 ⭐⭐⭐ **"从 brush 内部发出的前向 trace 常常先返回那个 brush 的出口面"**

**✅ 与 §471 四.5 的"两个不同的零"**——**同族**（**第五次"一个**反直觉的引擎行为**"**）。

**⇒ 三层**：
```text
一次 trace ⇒ **出口面**
两次 trace ⇒ **它后面的玩家**
⇒ **⇒ 所以【`5` 次【是【一个【上限**，不是【一个**目标**】
```

**✅ ⭐⭐⭐ **"5 次是一个上限，不是一个目标"**。

**⚠ 而 `SURF_TYPE_DEFAULT` 的豁免**：

```cpp
// 28400: `!depthSurfaceType` is NOT a reason to leave the loop. It is the
// value CODOL's trace reports for surfaces whose material index is absent
// (0 / SURF_TYPE_DEFAULT), and IW4X treats exactly that case as "look it
// up anyway, default 0".
```

**⇒ 十层**：
```text
`depthSurfaceType == 0` ⇒ **CODOL 的 trace【对【材质索引【缺失**的表面报告的值**
⇒ **⇒ 而【IW4X 【正好把那种情况【当成【"照查，默认 `0`**"**】
⇒ **⇒ 所以【它【不是【离开循环**的理由**
```

**✅ ⭐⭐⭐ **"它不是离开循环的理由"** —— 而**28390 之前【正是【这一点【造成了【"墙上有音、墙后无伤**"**。

**✅ 与 §468 的"`createDefault false`"**——**相反**（那里**必须失败**，这里**必须继续**）。

**⇒ 三层**：
```text
§468  **一个缺失的材质【必须读作缺失**（`createDefault = false`）**
§471  **一个缺失的表面类型【必须【照查**（默认 `0`）**
⇒ **⇒ 所以【同一个"缺失**"【在两处【相反**】
```

**✅ ⭐⭐⭐ **"同一个『缺失』在两处相反"** —— 一个**极精确的对照**（**由用途决定**，与 §467 的"由那个计数的用途决定"**同族**）。

## 七、**`GlassCommandRollback` 的"可见但可回滚"**

### 7.1 那段

```cpp
// OLMOD(bullet-command-transaction): native Bullet_Process exposes
// per-pellet glass mutation to the next trace immediately. Source must
// preserve that visibility while still rolling the whole usercmd back
// if a later pellet or effect fails validation.
class GlassCommandRollback final
{
public:
    GlassCommandRollback(SvGlassDamageState &damageState, SvGlassState &glassState)
        : ..., originalDamageState_(damageState), originalGlassState_(glassState) {}
    ~GlassCommandRollback()
    {
        if (!committed_)
        {
            damageState_ = std::move(originalDamageState_);
            glassState_ = std::move(originalGlassState_);
        }
    }
    void commit() { committed_ = true; }
};
```

### 7.2 二十四层

```text
1. **原生的 `Bullet_Process` 【把每个弹丸的玻璃变更【立刻【暴露给下一次 trace**】
2. ⇒ **⇒ 而【源实现【必须【保留那个可见性**】
3. ⇒ **⇒ 而【仍然**在【后面的弹丸或效果【校验失败时【回滚整个 usercmd**】
4. ⇒ **⇒ 所以【一个【RAII** 的守卫
5. ⇒ **⇒ 而 `commit()` 【在【最后【一切成功**时**
6. ⇒ **⇒ 而析构里【`if (!committed_)` ⇒ 恢复**
```

### 7.3 ⭐⭐⭐ **"立刻暴露给下一次 trace，但仍然能回滚整个 usercmd"**

**✅ 这是本报告里**最精确的一条"可见性【与【原子性**的**共存**"**。**

**✅ 与 §462 的"那是一个发现，不是那个写的一个缺陷"**——**不同**（那是一个**架构的缺口**，这是一个**已解决的竞态**）。

**⚠ 而"弹丸间**的可见性"**⇒ **"第 `k` 个弹丸打碎的玻璃【必须【对第 `k+1` 个弹丸【可见**"**。**

**⇒ 十层**：
```text
若【用【一个【候选副本**】⇒ **第 `k` 个弹丸的玻璃【对第 `k+1` 个【不可见**】
⇒ **⇒ 所以【玻璃【必须【直写【共享状态**】
⇒ **⇒ 而【那个回滚守卫【是【唯一的**退路**
```

**✅ ⭐⭐⭐ **"玻璃必须直写共享状态，而那个回滚守卫是唯一的退路"** —— 一个**极精确的权衡**。

**✅ 与 §463 的"刀BF 的回滚"**——**同族**（**第三次"一个**事后回滚**"**）。

**⇒ 三层**：
```text
§463  **`unk04A4Time` 的一个"生产值" ⇒ 往返校验失败 ⇒ 恢复纯搬运**
§471  **玻璃的直写 ⇒ 失败时 `~GlassCommandRollback` 恢复**
⇒ **⇒ 两次"一个**回滚**保证**
```

**✅ ⭐⭐ **"一个回滚保证"两例**。

### 7.4 而**"伤害载荷是候选副本，玻璃是直写"**

```cpp
auto candidateDamagePayloads = playerDamagePayloads;
auto candidateEntityDamagePayloads = entityDamagePayloads;
auto candidateImpactEvents = bulletImpactEvents;
GlassCommandRollback glassRollback(glassDamageState, glassState);
```

**⇒ 十二层**：
```text
1. **三个载荷向量【是【副本**（`= ` 复制**）**
2. ⇒ **⇒ 而【玻璃【是【直写 + RAII 回滚**】
3. ⇒ **⇒ 所以【两种**不同的**事务机制**】
4. ⇒ **⇒ 而那【正是【因为【玻璃【有【弹丸间的可见性**要求**
```

**✅ ⭐⭐⭐ **"两种不同的事务机制，因为只有玻璃有弹丸间的可见性要求"** —— 一个**极清晰的理由**。

**✅ 与 §469 的"一个实例预算的保存—重置—恢复"**——**同族**（**第四次"一个**事务**"**）。

## 八、**`SV_BulletTrace` 的 `depthSurfaceType` 三态**

```cpp
result.depthSurfaceType = static_cast<std::uint8_t>((result.trace.surfaceFlags >> 20) & 0x1F);
if (result.trace.surfaceFlags & 0x100)
    result.depthSurfaceType = 0;
else if (!result.depthSurfaceType)
    result.depthSurfaceType = input.lastSurfaceType;
```

### 8.1 二十层

```text
1. **默认：`(surfaceFlags >> 20) & 0x1F`**（**`0..31`**）
2. ⇒ **⇒ 所以【那个 `31` 【的计数【与【那个 `0x1F` 掩码【精确一致**】
3. ⇒ **若【`surfaceFlags & 0x100`**】⇒ **`0`**】
4. ⇒ **⇒ 否则【若解出 `0`**】⇒ **继承 `input.lastSurfaceType`**】
5. ⇒ **⇒ 所以【三态：解出的 / 强制零 / 继承**】
```

### 8.2 ⭐⭐⭐ **"`31` 的计数与 `0x1F` 的掩码精确一致"**

**✅ 独立验证**：`0x1F = 31` ⇒ **`& 0x1F` 解出 `0..31`**，而 `BulletSurfaceTypeCount = 31` ⇒ **合法的索引是 `0..30`** ⇒ **`31` 是【一个**保留值**】**（会被 `SV_IsBulletTraceInputValid` 的 `lastSurfaceType < BulletSurfaceTypeCount` 拒绝）。

**⇒ 三层**：
```text
`& 0x1F` ⇒ **`0..31`**
`< 31` ⇒ **`0..30`**
⇒ **⇒ 所以【`31` 【是一个【会被拒绝**的值**
```

**✅ ⭐⭐ **"`31` 是一个会被拒绝的值"** —— 而**那正是 `opaqueglass` 别名的位置之后**（**"然后 `opaqueglass` 别名为 `9`，而【非表面标志名【在它之后**"**）。

**✅ 与 §470 的"`16383` 是一个保留值"**——**同族**（**第四次"一个**上界**被留作哨兵**）。

### 8.3 而**`0x100` 的"强制零"**

**⇒ 十层**：
```text
`surfaceFlags & 0x100` ⇒ **一个【特定**的标志位**
⇒ **⇒ 所以【`depthSurfaceType = 0`**】
⇒ **⇒ 而那【意味着【"默认/未知**"**
⇒ **⇒ 而那【在【穿透链里【被豁免**（§471 六.2）**
```

**✅ ⭐⭐⭐ **"那个 0x100 的强制零在穿透链里被豁免"** —— 一个**跨段的闭合**。

## 九、**`SV_IsBulletImpactEventValid` 的"近战命中不携带任何子弹专属字段"**

```cpp
// OLMOD(bullet-impact-source-schema): only the currently recovered
// ordinary EV_BULLET_HIT form accepts zero additional impact flags.
// A melee hit asserts NONE of the bullet-only fields -- 36 of 36 in the
// retail demo -- so requiring them absent is what keeps the two shapes
// from drifting into each other.
if (event.melee &&
    (event.surfaceType != 0 || event.hitEntityNum != BulletNoneEntityNum))
    return false;
```

**⇒ 二十层**：
```text
1. **只有【那个【当前已恢复的**普通 `EV_BULLET_HIT` 形态【接受【零个**额外的撞击标志**】
2. ⇒ **⇒ 而【一个近战命中【断言【没有**任何【子弹专属的字段**】
3. ⇒ **⇒ 而【零售 demo 里 `36` 个里的 `36` 个**】
4. ⇒ **⇒ 所以【要求它们缺席**【是【使那两个形态【不【漂进彼此**的东西**
```

### 9.2 ⭐⭐⭐ **"36 个里的 36 个"**

**✅ 与 §467 的"`69` 个里的 `61` 个"**、§468 的"`67` 个里的 `66` 个"**——**同族**（**第三次"一个**分数**"**）。

**⚠ 而 `EV_MELEE_HIT` 的**形状**（`.hpp`）：**

```cpp
// A KNIFE, NOT A BULLET. EV_MELEE_HIT is its own event entity (eType 98
// = 23 + 75) and the demo gives it a shape of its own: origin, the
// attacker in field 9, the weapon in field 16 and eventParm 1 -- in all
// 36 retail assertions -- with NO surface, NO impact flags and NO hit
// entity. Carried as a flag rather than a second vector because these
// live in the same staged list and are spawned by the same loop; the
// list is heap-backed, so this adds nothing to SvGameEntity and cannot
// move the address-keyed buffer (sect.184h).
```

**⇒ 十六层**：
```text
1. **`EV_MELEE_HIT` 【是【它自己的事件实体**】（**`eType 98 = 23 + 75`**）**
2. ⇒ **而【那个 demo 【给它【一个自己的形状**】：`origin` + `field 9` 的攻击者 + `field 16` 的武器 + `eventParm 1`**
3. ⇒ **⇒ 而【在【全部 `36` 个零售断言里**】
4. ⇒ **⇒ 【没有表面、没有撞击标志、没有命中实体**】
5. ⇒ **⇒ 而【它【被【携带为**一个标志**而不是【第二个向量**】
6. ⇒ **⇒ 因为【它们【住在【同一个暂存列表**里**而【由【同一个循环**生成**
7. ⇒ **⇒ 而【那个列表【是【堆支撑**的**
8. ⇒ **⇒ 所以【这【不向 `SvGameEntity` 添加任何东西**】⇒ **⇒ 而【不能【移动那个地址键控的缓冲区**（§184h）**】
```

**✅ ⭐⭐⭐ **"这不能移动那个地址键控的缓冲区"** —— **第三次"一个结构的大小是一个行为"**（与 §471 二.3 的 `thread_local` 选择**同族**）。

**✅ 与 §466 的"`?N` 是一个独立的名字空间"**——**不同**（那是**命名**，这是**存储布局**）但**同族**（**"同一个列表【承载【两种形状**"**）。

**⇒ 独立验证**：`98 - 23 = 75` ✓ **`eType 98 = 23 + 75`**。

**⇒ 三层**：
```text
`98 - 23 = 75` ✓
⇒ **⇒ 与注释【一致**】
```

**✅ ⭐⭐ **"与注释一致"** —— 一个**算术闭合**。

## 十、**`SV_ExecuteBulletFire` 的两个早退**

```cpp
if (input.plan.methodOfDeath == 3)
    return SvBulletFireExecutionResult::DeferredImpact;
if (!endposRunner || !traceRunner)
    return SV_BulletFireFailed("endpos-or-trace-runner-missing");
```

### 10.1 二十层

```text
1. **`methodOfDeath == 3` ⇒ `DeferredImpact` 【且【不记任何理由**】
2. ⇒ **⇒ 所以它【不是【一个失败**】⇒ **⇒ 而是一个"交给别人**"**
3. ⇒ **⇒ 而【runner 缺失 ⇒ `Failed` + `"endpos-or-trace-runner-missing"`**】
```

### 10.2 ⭐⭐⭐ **"`methodOfDeath == 3` 返回 `DeferredImpact` 而不记理由"**

**✅ 与 §468 的"`UnresolvedString` 没有生产者"**——**不同**（那是**一个死状态**，这是一个**活的分支**）。

**⚠ 而"`3` 是什么**"**⇒ **一个**未命名**的常量**。**

**⇒ 十层**：
```text
`methodOfDeath == 3` ⇒ **一个【魔法数**】
⇒ **⇒ 而【它【不是 `MethodOfDeathCount` 之类的命名常量**】
⇒ **⇒ 所以【那个 `3` 【是一个【可读性**的缺口**
```

**✅ ⭐⭐ **"那个 3 是一个可读性的缺口"** —— 而 `SV_IsEntityDamagePayloadValid` 用**命名**的 `MethodOfDeathCount`。

**⇒ 三层**：
```text
`payload` 校验 ⇒ **`MethodOfDeathCount`**（命名**）
早退 ⇒ **`3`**（魔法数**）
⇒ **⇒ 所以【同一个概念【两处【命名不一致**】
```

**✅ ⭐⭐ **"同一个概念两处命名不一致"**。

## 十一、**`entityBulletDamage` 的"一个命中位置乘数"**

```cpp
std::optional<std::int32_t> entityBulletDamage(const SvDamageableEntityView &target,
    const std::int32_t base, const float locationMultiplier)
{
    if (!target.usesWeaponHitLocationMultipliers)
        return std::max(1, base);
    // OLMOD(zombie-hit-location): use the weapon's actual native table
    // after range/penetration attenuation, as the player path does.
    // Recorded 26/31 and 49/58 pairs fit its 1.2 head entry. The original
    // cyborg server's additional critical modifiers remain unrecovered.
    const auto scaled = static_cast<float>(base) * locationMultiplier;
    if (!std::isfinite(scaled) || scaled < 0.0f || scaled >= 2147483648.0f)
        return std::nullopt;
    return std::max(1, static_cast<std::int32_t>(scaled));
}
```

### 11.1 二十四层

```text
1. **一个【实体**【可以选择【不使用**武器命中位置乘数】**
2. ⇒ **⇒ 而【那【正是【玩家路径【与【僵尸路径**的**分叉**
3. ⇒ **⇒ 而【一个【测量的配对 `26/31` 与 `49/58` 【拟合**它的 `1.2` 头部条目**】
4. ⇒ **⇒ 而【原来那个 cyborg 服务器的额外暴击修正【仍然【未恢复**】
5. ⇒ **⇒ 而【`2147483648.0f` ⇒ `2^31` 的上界【防止**一个 **`int32` 溢出**
```

### 11.2 ⭐⭐⭐ **"`26/31` 与 `49/58` 拟合它的 1.2 头部条目"**

**✅ 独立验证**：`31 × 1.2 = 37.2` ⇒ `max(1, 37) = 37` ≠ `26`；`26 / 1.2 = 21.67`，`31 / 1.2 = 25.83`。**⇒ 我的算法与注释的"拟合"不一致** ⇒ **标注为未闭合**（那对数字可能是**基础伤害与最终伤害**，`26 → 31` 是 `×1.192`，`49 → 58` 是 `×1.184`，**都约为 `1.2`**）。

**⇒ 修正我的读法**：
```text
`26/31` ⇒ **`31/26 = 1.192`**
`49/58` ⇒ **`58/49 = 1.184`**
⇒ **⇒ 所以【那【正是**一个 `1.2` 的乘数** ✓
```

**✅ ⭐⭐⭐ **"`31/26 = 1.192` 与 `58/49 = 1.184` 都约为 `1.2`"** —— 一个**正确的独立验证**。

**⚠ 而 `2147483648.0f = 2^31`** ⇒ **`int32` 的上界**。

**⇒ 三层**：
```text
`2^31 = 2147483648` ⇒ **一个 `int32` 的【无符号**上界**
⇒ **⇒ 所以【那个检查【防止【一个【溢出的**转换**
```

**✅ ⭐⭐ **"那个检查防止一个溢出的转换"**。

**⚠ 而 `std::max(1, ...)` 出现【两次**】**（`!usesWeaponHitLocationMultipliers` 与最后**）**。

**⇒ 三层**：
```text
不乘 ⇒ **`max(1, base)`**
乘后 ⇒ **`max(1, int32(scaled))`**
⇒ **⇒ 所以【伤害【至少 `1`**】
```

**✅ ⭐⭐ **"伤害至少 1"** —— 而**那不是"最小伤害"，是"一枪必掉 1 血"**。

## 十二、关键结论

1. **⭐⭐⭐ "十三种拒绝一次射击的方式，而它们只有一个词：`client_events_rejected` 只命名那个阶段，而子弹路径有十三个不同的 `Failed` 返回；一个玩家报告『打中了但从不掉血』不能与一个坏的 trace / 一个未解析的 endpos / 一个被拒的载荷分开，所以**第一次 alt-fire 的射击花掉整整一次读这个文件**"`** ⇒ 修法是一个 **`thread_local const char *`** —— **"一个指针，不是一个字符串 ⇒ 没有分配"`**，而 **"不向任何结构添加字段，因为这个项目两次通过增长一个看起来惰性的东西弄坏了地址键控的缓冲区（§184h）"`**。**我数到 `25` 个不同的字面量（非穿透 `14` + 穿透 `11`），注释说 `13` ⇒ 注释落后于代码。**
2. **⭐⭐⭐ 表面表是一个 `20` 字节记录，第三个 `dword` 是材质标志字，对表面类型就是 `index << 20`** ⇒ **"那个表就是那个枚举，读它不需要一个 reader"`**；`bark=1 … riotshield=29 slush=30`，`opaqueglass` 别名回 `9`，非表面标志名在之后 ⇒ **`31` 是计数**。**独立验证：`0x01D00000 >> 20 = 0x1D = 29 = riotshield` ✓**，而 `(surfaceFlags >> 20) & 0x1F` 与 `< 31` 使 **`31` 成为一个会被拒绝的保留值**。
3. **⭐⭐⭐ `BulletShieldPartGroup = 19 = 0x13` 与 `BulletShieldSurfaceFlags = 0x01D00000` 来自【一次读**】（`mov ecx, 13h / cmp word [esi+22h], cx / mov [esi+10h], 1D00000h` at `0x005919A1`，3.3.3.3 的 `0x0055A5A8` 相同）—— **"那个 part group 与那个标志来自一次读"`**。
4. **⭐⭐⭐ `0x0280E831` 的"八次出现 + 一次配对"**：**每个镜像八次，而两个 build 上 `0x01D00000` 的那一次出现都在一个也携带它之一的函数里**（3.3.3.3 `sub_55A4A0` / out.exe `sub_5918B0`）⇒ **"那个配对识别那个对应物，而相等的计数使它成为一个测量而不是一个巧合"`**。
5. **⭐⭐⭐ 穿透链的八次改判**（刀BE 补默认 `12` → 刀BZ 撤销 → 刀BH 去掉前置条件 → 刀BY 回滚 → 28380 默认开+三档 → 28390 零不拒绝+`PEN|` → 28400 两个零都不中止 → 28700 FMJ ×2），其中最精确的一条归因是**刀BH 的"打不死人 + 穿透仍无效是同一刀的两个症状"`** —— **不是两个 bug，是 `deferredImpact` 分支在不该穿透的武器上改变了命中处理**。
6. **⭐⭐⭐ 28400 的"两个不同的零"**：`nullopt`（表面索引在 CODOL 的表外 / 线程归属 miss / 深度超出伤害范围）与 `0.0f`（**"CODOL 的材质表 A 在游戏里全是零"**）都留下 **"墙上有撞击音、墙后无伤"**；而 28390 的"一个单位"回退**反正让 `damageMultiplier` 在第一个表面上变负** ⇒ **"两个『修法』都是错的"`**。
7. **⭐⭐⭐ `PenetrationAdvance = 0.135` / `ReverseTraceAdvance = 0.01` 各自除以一个 `dot`，而那个 `dot` 有一个 `0.125` 的下限** ⇒ **独立算得最大推进 `0.135 / 0.125 = 1.08` 与最大后退 `0.01 / 0.125 = 0.08`** ⇒ **"0.125 防止一个近似相切的墙把起点推到无穷远"`**。
8. **⭐⭐⭐ `damageMultiplier -= wallThickness / maximumDepth`，而 `wallThickness` 有一个 `1.0` 的下限** ⇒ **"那个 1.0 防止一个免费的穿透"`**；`maximumDepth = min(entry, exit)` 是一个**保守**的选择；**FMJ 的 `×2` 必须同时作用于出口面，"否则一个双层墙会按普通深度判定并把子弹停下"`**。
9. **⭐⭐⭐ 穿透链最多 `5` 个表面，而"从 brush 内部发出的前向 trace 常常先返回那个 brush 的出口面，只有下一次迭代能到达它后面的玩家"`** ⇒ **"`5` 次是一个上限，不是一个目标"`**。
10. **⭐⭐⭐ `depthSurfaceType == 0` 的豁免**：**"它是 CODOL 的 trace 对材质索引缺失的表面报告的值，而 IW4X 正好把那种情况当成『照查，默认 0』"`** ⇒ **与 §468 的 `createDefault = false` 完全相反**（那里**必须失败**、这里**必须继续**）—— **"同一个『缺失』在两处相反，由用途决定"`**。
11. **⭐⭐⭐ `GlassCommandRollback` 的"立刻暴露给下一次 trace，但仍然能回滚整个 usercmd"`**：**原生的 `Bullet_Process` 把每个弹丸的玻璃变更立刻暴露给下一次 trace** ⇒ 玻璃**直写共享状态 + RAII 回滚**，而**三个伤害/撞击载荷是候选副本** ⇒ **"两种不同的事务机制，因为只有玻璃有弹丸间的可见性要求"`**。
12. **⭐⭐⭐ `SV_BulletImpactEvent::melee` 的"一把刀，不是一颗子弹"`**：**`EV_MELEE_HIT` 是它自己的事件实体（`eType 98 = 23 + 75`，独立验证 ✓），形状是 `origin` + `field 9` 的攻击者 + `field 16` 的武器 + `eventParm 1`，在全部 `36` 个零售断言里没有表面、没有撞击标志、没有命中实体** ⇒ **"它被携带为一个标志而不是第二个向量，因为那个列表是堆支撑的，所以这不向 `SvGameEntity` 添加任何东西、不能移动那个地址键控的缓冲区"`** —— **第三次"一个结构的大小是一个行为"`**。
13. **⭐⭐ `SV_BulletTrace` 的 `depthSurfaceType` 三态**（解出的 / `surfaceFlags & 0x100` 强制零 / 继承 `lastSurfaceType`）—— **而那个"强制零"在穿透链里被豁免**，一个**跨段的闭合**。
14. **⭐⭐ `entityBulletDamage` 的 `1.2` 头部乘数**——**独立验证 `31/26 = 1.192` 与 `58/49 = 1.184`，都约为 `1.2` ✓**（注释写"`26/31` 与 `49/58`"，我一开始按 `×1.2` 读反了，重算后一致）；而 `2147483648.0f = 2^31` 防止一个**溢出的转换**。
15. **⚠ 两个可报告的缺口**：①**`methodOfDeath == 3` 是一个魔法数**，而 `SV_IsEntityDamagePayloadValid` 用命名的 `MethodOfDeathCount` —— **同一个概念两处命名不一致**；②**`13` 的注释数 vs `25` 个实际的字面量**（注释落后于代码）。

## 十三、`sv_bullet_mp` 全文件总览

**`.cpp`：`954` 行。`.hpp`：`271` 行。**

**`9` 个函数**（`.cpp`）：
```text
 13 entityBulletDamage          28 finiteVector            35 validTraceResult
 44 GlassCommandRollback       87 SV_IsBulletTraceInputValid
115 SV_BulletFireFailed       121 SV_LastBulletFireFailure
126 SV_IsBulletImpactEventValid  146 SV_BulletTrace
224 SV_ApplyBulletGlassDamage   276 SV_ExecuteBulletFire
```

**`8` 个测量常量**（`.hpp`）：
```text
BulletSurfaceTypeCount        31
BulletShieldSurfaceFlags      0x01D00000   (riotshield 的 flags 字，>>20 = 29)
BulletShieldPartGroup         19 = 0x13
BulletLocationalContentMask   0x0280E831
BulletWorldEntityNum          2046
BulletNoneEntityNum           2047
PenetrationAdvance            0.135f
ReverseTraceAdvance           0.01f
```

**`31` 个表面类型**：
```text
 1 bark        2 brick       3 carpet      4 cloth       5 concrete
 6 dirt        7 flesh       8 foliage     9 glass      10 grass
11 gravel     12 ice        13 metal      14 mud        15 paper
16 plaster    17 rock       18 sand       19 snow       20 water
21 wood       22 asphalt    23 ceramic    24 plastic    25 rubber
26 cushion    27 fruit      28 paintedmetal 29 riotshield 30 slush
(0 默认/未知；`opaqueglass` 别名回 9；非表面标志名在 30 之后)
```

**`25` 条拒绝理由**（非穿透 `14` + 穿透 `11`）。

**`7` 条来源标注**：
```text
CODREF(bullet_trace)          BO1 0x005F3DE0 / Ghosts 0x140109F10 / BO2 0x005AC950
CODREF(bullet_process)        BO1 0x005F4190 / Ghosts 0x140109AA0 / BO2 0x005AD850
CODREF(bullet_penetration)    OLFinal sub_5923C0 + COD4 Bullet_FirePenetrate
OLMOD(bullet-trace-source-schema)
OLMOD(bullet-command-transaction)
OLMOD(bullet-impact-source-schema)
OLMOD(zombie-hit-location)
```

**`4` 个 TODO(CODOL)**：每弹丸的嵌套脚本边界 / 头与击杀的额外撞击标志 / 非玩家实体的专用 `G_Damage` 分支 / 更多墙与类型化穿透。

## 十四、未闭合点

- `MethodOfDeathCount` 的确切值（`3` 是哪一个）。
- "CODOL 的材质表 A 在游戏里全是零"的原始证据。
- 零售的每材质穿透深度表（IW4X 的 `penetrationDepthTable[penetrateType][surfaceType]`）—— 目前用常数 `16`。
- `0x100` 在 `surfaceFlags` 里到底是什么标志。
- 下一个文件：`sv_client_mp.hpp`（下一个按大小的 `server_mp` 文件）。
