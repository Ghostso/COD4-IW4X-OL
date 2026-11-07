# 407 · **"唯一的 OLfinal 独有增量"** —— vision 只拒 `black_bw` 一个名字、死亡时补 `N "<map>" 0` 与 `L <n> 7`（槽位 7 是"看击杀者"卡）、`d 792` 写两次要换 `mat`/`offmat`

## 一、范围

本报告学习 `sv_main_mp.cpp` 5900–6278 行。

## 二、**vision 只拒一个名字**（本组最重要的一段）

### 2.1 那段

```php
// `N "mp_mountain" 0`, `N "mp_mideast" 0`, `N "mp_fav_tropical" 0` --
// the plain map name with a zero blend, which is what stock CoD's
// maps/mp/_load::main() produces with visionSetNaked(mapname, 0). The
// same corpus carries the named sets on the same verb (`N "zm_begin"
// 100`, `N "coup_sunblind" 400`) and type 5's overlays under '3'
// (`3 "grayscale" 1000`, `3 "near_death" 20000`), which is the
// independent confirmation that the verb letters mean what the
// disassembly says.
//
// ONE NAME IS REFUSED: case 'N' compares argv(1) against "black_bw" and
// drops the command when two no-argument predicates on one global
// (0x005AB9A0 tests it == 1, 0x005ABA00 tests it == 2) say the client is
// in either of those states. No other name is filtered.
//
// CODDIFF(vision): dest1yo's 3.3.3.3 server does not send this either,
// so this is not a port gap being closed (section 98a) -- it is a
// deliberate OLfinal-only addition, and the only one in this path.
//
// Sent per client on the frame it becomes active, the same shape as
// announceMatchRules, so a late join is graded too.
```

### 2.2 二十层

```text
1. **`N "mp_mountain" 0` / `N "mp_mideast" 0` / `N "mp_fav_tropical" 0`**
2. ⇒ **地图原名 + 零混合**
3. ⇒ **正是原版 CoD `maps/mp/_load::main()` 用 `visionSetNaked(mapname, 0)` 产生的**
4. ⇒ **同一语料在同一动词上还有命名集**（`N "zm_begin" 100`、`N "coup_sunblind" 400`）
5. ⇒ **而类型 5 的叠加在 `'3'` 下**（`3 "grayscale" 1000`、`3 "near_death" 20000`）
6. ⇒ **⇒ 那是【动词字母的含义正如反汇编所说】的独立确认**
7. ⇒ **一个名字被拒**：**case `'N'` 把 `argv(1)` 与 `"black_bw"` 比对**
8. ⇒ **当两个无参谓词在一个全局上**（`0x005AB9A0` 测它 `== 1`、`0x005ABA00` 测它 `== 2`）
9. ⇒ **说客户端在两种状态之一时，就丢弃那条命令**
10. ⇒ **没有别的名字被过滤**
11. ⇒ **`CODDIFF`：dest1yo 的 3.3.3.3 服务器也不发这个**
12. ⇒ **所以这不是一个被补上的移植缺口**（第 98a 节）
13. ⇒ **它是【一个刻意的 OLfinal 独有增量】**
14. ⇒ **而它是这条路径上【唯一的一个】**
15. ⇒ **按客户端发，在它变成活跃的那一帧**
16. ⇒ **与 `announceMatchRules` 同形** ⇒ **所以一个晚加入的也被调色**
```

### 2.3 ⭐⭐⭐ **"刻意的 OLfinal 独有增量，而它是这条路径上唯一的一个"**

**✅ 这是本报告里**最重要的一条血统判定**。**

**⇒ 三层**：
```text
dest1yo 3.3.3.3 不发 ⇒ 不是"补移植缺口"
而零售 OLfinal 发 ⇒ 【本 build 自己的行为】
⇒ ⇒ 所以这是【本 build 独有】而不是【跨 build 通用】
```

**✅ 与 §406 的"`'3'` 打破了字母顺序"**完全闭合 ✓

**⇒ 三层**：
```text
`N O P Q R` ⇒ 3.3.3.3 与 OLfinal 【共有】
`3`        ⇒ 零售 dm 也不发，只 cha/zm 有
`black_bw` 过滤 ⇒ 【OLfinal 唯一】
```

**✅ 一个**三层血统分类**。

### 2.4 而**"两个无参谓词在一个全局上"**

```php
// 0x005AB9A0 tests it == 1, 0x005ABA00 tests it == 2
```

**⇒ 四层**：
```text
`0x005AB9A0()` ⇒ `global == 1`
`0x005ABA00()` ⇒ `global == 2`
⇒ **而 `case 'N'` 在【两者之一】为真时丢弃 `black_bw`**
⇒ ⇒ 所以 `black_bw` 在【两个特定状态下】被拒
```

**✅ ⭐ **一个"名字级的拒绝"** —— 本文件里唯一的实例。

**⚠ 而"两个不同的值 `1`/`2`"⇒ **所以是【两种不同的客户端状态**】。**

**✅ 与 §402 的"`0x800` 一个位三个语义"**不同（那是**同一个值三个语义**，这是**两个值同一后果**）。

**⇒ **第三次确认"一值多义/多值一义"。**

### 2.5 而**"按客户端发、与 `announceMatchRules` 同形"**

**⇒ 三层的"晚加入"处理**：
```text
`visionAnnounced_.contains(clientNum)` ⇒ 已发过就跳过
`visionAnnounced_.insert(clientNum)`   ⇒ **立刻标记**
⇒ **⇒ 所以一个晚加入的客户端在它变 Active 的那一帧收到调色**
```

**✅ 与 §402 的"限定到 dmz"**同族（**第二次"按客户端而不是按全局"）。**

## 三、**Factory entry 的三阶段 FX 时间表**（本组第二重要）

### 3.1 那段

```php
// CODREF(g_run_frame): exact client0x46CEF0/46CE80 and three original
// Factory recordings agree: zm_begin100, then400ms later map2000.
// OLMOD(factory-entry): first Playing is our readiness adapter. It
// keeps stationary FX/camera separate from the generation-owned native
// arrival movement hold established at ClientSpawn. MP is unchanged.
```

### 3.2 二十层

```text
1. **`zm_begin 100`，然后 `400ms` 之后 `map 2000`**
2. ⇒ **三个原始 Factory 录像一致**
3. ⇒ **而 `first Playing` 是【我们的就绪适配器**】**
4. ⇒ **它把静止 FX/相机与【generation 拥有的原生到达移动保持】分开**
5. ⇒ **后者在 `ClientSpawn` 建立**
6. ⇒ **MP 不变**
7. ⇒ **两个出生载体 `715`/`716` 固定在出生点**
8. ⇒ **而 FX `147`/`174` 然后 `173` 在 `500ms` 之后**
9. ⇒ **解析后的名字/根替换【录制的索引】**
10. ⇒ **`first Playing` 是【我们的时钟**】**
11. ⇒ **载体位置**：`portal = origin + (0,0,52)`
12. ⇒ **`flash`：沿 yaw 前 20 单位 + 62 高度**
13. ⇒ **三个 FX 阶段**：`fx==2` ⇒ `600ms`，否则 `100ms`
14. ⇒ **窗口 `age < 1100`**
15. ⇒ **两个载体的释放**：`carrier 0` @ `6100`、`carrier 1` @ `3600`
16. ⇒ **`4100ms` 时发 `N "zm_begin" 100`**
17. ⇒ **`flashAt` 从【实际入队】起算**（不是从 `birth`）
18. ⇒ **`+400ms` 后发 `N "zm_factory_sh" 2000`**
```

### 3.3 ⭐⭐ **"从实际入队起算，所以一个晚帧不能把两条命令塌成一个未渲染的闪"**

```php
// Measure from the actual enqueue so a late frame cannot
// collapse both commands into one unrendered flash.
```

**⇒ 五层**：
```text
测量起点：**`entry.flashAt = now`（入队那一刻）**
⇒ ⚠ 而**不是** `entry.birth`
⇒ **理由**：一个**晚帧**会同时满足 `age >= 4100` 与 `>= 4500`
⇒ ⇒ 两条 `N` 在**同一帧**发出 ⇒ **客户端只渲染最后一个** ⇒ **闪看不见**
```

**✅ ⭐ **一个极精确的"时间基准选择"论证**。**

**✅ 与 §404 的"延迟是常数；选择是那个竞赛"**同族（**第三次"时间的基准决定结果"）。**

**⚠ 而"塌成一个未渲染的闪"⇒ **一个可见的症状**。**

**✅ 与 §406 的"平光外观"**同族（**第五次"静默的失败产生可见的缺陷"）。**

### 3.4 而**"`portal` / `flash` 两个载体的几何"**

```text
portal = player->origin, z += 52
flash  = player->origin
         x += 20*cos(yaw)
         y += 20*sin(yaw)
         z += 62
```

**⇒ 四层**：
```text
`portal` ⇒ **正上方 52**
`flash`  ⇒ **前方 20、上方 62**（沿 **yaw** 的方向）
⇒ **⇒ 所以 flash 是"在玩家面前闪光"**
```

**✅ ⭐ 一个**从游戏语义反推的几何**（不是随机常数）。

**⚠ 而"`viewAngles[1] * 0.017453292519943295f`"⇒ **弧度转换**（`π/180`）。**

**✅ 与 §390 的"`+3` 的模型带偏移"**不同（这是**精确的数学**）。

### 3.5 而**"槽释放时释放实体"**

```cpp
if (slots[n].state == ClientState::Free) {
    if (const auto old = factoryEntries_.find(n); old != factoryEntries_.end())
        for (const auto &carrier : old->second.arrivalCarriers)
            if (carrier) static_cast<void>(world_.freeEntity(*carrier));
    factoryEntries_.erase(n);
    continue;
}
```

**⇒ 四层**：
```text
槽变 Free ⇒ **释放它的两个载体实体**
⇒ **并 `factoryEntries_.erase(n)`**
⇒ **⇒ 所以一个槽复用【不带旧载体的实体**】
```

**✅ 与 §404/§405 的"槽复用要清状态"**完全同族（**第三次）。**

**⇒ 三层**：
```text
§404  `uiClientLife_`     ⇒ 清 life 状态
§405  `announcerDialog_`  ⇒ 清队列
§407  `factoryEntries_`   ⇒ 清实体
```

**✅ **第八次确认"号复用"。**

## 四、**`projectDeathVision`：三个命令同时发**（本组第三重要）

### 4.1 那段

```php
// ★ 2026-10-18（会话 28330 / 第 3 项）：**比赛中每死一条 `L <victim> 7`**。
//   实测（`Observed`）：零售 cha 每死一条 `L <victimNum> 7`（28 条/局），
//   我方 19:22 那局只有 4 条（podium 的 `L x 1/2/3` + 一条 `L 0 7`）。
//   语义锚（`Observed`，2697 `_damage.gsc:114/138/141/199/202`）：
//     死者 `SetCardDisplaySlot(attacker, 7)`、击杀者 `SetCardDisplaySlot(victim, 8)`
//   7 = killed-by 卡、8 = you-killed 卡 ⇒ 槽位号 7 是"看击杀者"那张卡。
//   我方 `L` 的第二个参数与这个槽位号同值（零售 28 条全是 7），本行只补 7。
```

### 4.2 二十层

```text
1. **比赛每死一条 `L <victim> 7`**
2. ⇒ **实测零售 cha：每死一条 `L <victimNum> 7`**（**`28` 条/局**）
3. ⇒ **我方 19:22 那局只有 `4` 条**：
      · **podium 的 `L x 1/2/3`**（三条）
      · **一条 `L 0 7`**
4. ⇒ **语义锚（2697 `_damage.gsc:114/138/141/199/202`）**：
      · **死者 `SetCardDisplaySlot(attacker, 7)`**
      · **击杀者 `SetCardDisplaySlot(victim, 8)`**
5. ⇒ **`7` = killed-by 卡**
6. ⇒ **`8` = you-killed 卡**
7. ⇒ **所以槽位号 `7` 是"看击杀者"那张卡**
8. ⇒ **我方 `L` 的第二个参数与这个槽位号同值**
9. ⇒ **（零售 `28` 条全是 `7`）**
10. ⇒ **所以本行只补 `7`**
```

### 4.3 ⭐⭐⭐ **"`L` 的第二个参数【就是】那个槽位号"**

**✅ 这是本报告里**最清晰的一个"两个数同值所以是同物"的论证**。**

**⇒ 三层**：
```text
`L <clientNum> <slot>` ⇒ §406 说"绑定一个客户端到十九个展示槽之一"
2697 ⇒ `SetCardDisplaySlot(attacker, 7)` = "把 attacker 放进槽 7"
⇒ **⇒ 两者【同值同义】：`L n 7` = 把客户端 n 放进槽 7**
```

**✅ 与 §406 的"`L 6 1`/`L 3 2`/`L 1 3` 是 podium 的三个位置"**完全闭合 ✓

**⇒ **第二次确认 `L` 的语义**（而**这一次有脚本侧语义锚**）。

**⚠ 而"`28` 条 vs 我方 `4` 条"⇒ **一个 `7:1` 的差距**。**

**✅ 与 §341 的"零售零次而我们 11,048 次"**相反**（这次是**我们太少**）。**

**⇒ 三层**：
```text
perkSlot：**我们太多**（210 vs 0）
L 死亡卡：**我们太少**（4 vs 28）
⇒ **⇒ 两种相反的过量/不足**
```

**✅ 一个**完整的双向覆盖**。

### 4.4 而**`d 792` 要写两次且 `mat`/`offmat` 换位**

```php
// ★ 2026-10-18（会话 28330 / 第 4 项）：**每死一条 `d 792 \ent\<n>...`**。
//   实测（`Observed`，零售 cha）：每有一人死亡就写两次 792 ——
//     ① `\ent\<n>\offs\0 0 0\mat\-1\offmat\-1\flags\0`
//     ② `\ent\<n>\offs\0 0 0\offmat\-1\mat\154\flags\0`
//   （`mat` 与 `offmat` 换位），随后不久出现 `d 792`（空值=清除）。
//   我方此前**只在 podium 清一次**、从没写过 ⇒ 尸体/死亡点标记一直是空的。
```

**⇒ 十二层**：
```text
1. **每死一条 `d 792 \ent\<n>...`**
2. ⇒ **每有一人死亡就【写两次 792**】**
3. ⇒ **①  `\ent\<n>\offs\0 0 0\mat\-1\offmat\-1\flags\0`**
4. ⇒ **②  `\ent\<n>\offs\0 0 0\offmat\-1\mat\154\flags\0`**
5. ⇒ **（`mat` 与 `offmat` **换位**）**
6. ⇒ **随后不久出现 `d 792`（空值=清除）**
7. ⇒ **我方此前只在 podium 清一次、从没写过**
8. ⇒ **⇒ 所以尸体/死亡点标记【一直是空的**】**
9. ⇒ **`<n>` 用【实体号】**（零售 `270/421/278/434/303/297/458/432` 全是实体号）
10. ⇒ **拿不到实体就跳过（不猜数）**
```

### 4.5 ⭐⭐ **"`mat` 与 `offmat` 换位"**

**✅ 一个**极精细的字节级复现**。**

**⇒ 三层**：
```text
① `mat -1` `offmat -1` ⇒ **两个都是 -1**
② `offmat -1` `mat 154` ⇒ **换了位，且 mat 变成 154**
⇒ **⇒ 所以第二次是【真正设置材质 154**】
```

**✅ ⭐ **一个"先清后设"的两步**（`-1` 是清，`154` 是设）。

**⚠ 而"键的【顺序】也变了"⇒ **所以那份字典是有序的**。**

**⇒ 三层**：
```text
若顺序无关 ⇒ 两次只需一次（`mat 154` `offmat -1`）
而实际两次且顺序不同 ⇒ **⇒ 说明【客户端按顺序解析**，或【服务端严格复现零售】
```

**✅ 一个**需要标注的开放点**（顺序是否有语义）。

**✅ 与 §402 的"`d` 命令可以有额外浮点参数"**同族（**第二次"`d` 的值格式有结构"）。**

### 4.6 而**"拿不到实体就跳过（不猜数）"**

```cpp
const auto victimEntity = world_.playerEntity(*clientNum);
if (victimEntity) { ... }
// `number` 不在 SvGameEntity 上（那是网络实体号，见 sv_snapshot_mp.hpp:2047）。
// 零售 792 的 `\ent\<n>` 是**实体索引**，本工程对应 `world_.playerEntity(n)` 的 n。
```

**⇒ 五层**：
```text
1. **`number` 不在 `SvGameEntity` 上**（那是**网络实体号**）
2. ⇒ **零售 `792` 的 `\ent\<n>` 是【实体索引**】
3. ⇒ **本工程对应 `world_.playerEntity(n)` 的 `n`**
4. ⇒ **所以本行用的是 `std::to_string(*clientNum)`**
5. ⇒ **而拿不到实体 ⇒ 保持沉默，不发一个猜的数**
```

**✅ ⭐ **"不猜数"** —— 与 §399 的"跳过而不是搬移"**完全同族（**第二十四次"不要发明"）。**

**⚠ 而"实体号 vs 实体索引"⇒ **一个精确的术语区分**。**

**✅ 与 §406 的"`+0x58` 记录槽 vs `+0x59` 指针索引"**同族（**第二次"两个号的区分"）。**

### 4.7 而**"灰度是发明的，`N` 是零售真发的"**

```php
// WHETHER THIS IS SENT HAS NEVER BEEN MEASURED. The `3` trigger is an
// INVENTION (see the OLMOD note above) and retail dm sends no `3` at
// all, so nothing in this project's record shows the grayscale death
// effect working live -- section 99's live verification was type 0
// and the six configstrings, not this. On 2026-08-23 a player
// reported not seeing it, and there was no instrument that could
// separate "never queued" from "queued and not applied" from
// "applied but nobody was looking at that client's window".
```

**⇒ 七层**：
```text
1. **`3 "grayscale"` 的触发是【发 明 的**】
2. ⇒ **零售 dm 【一条 `3` 都不发**】**
3. ⇒ **所以项目记录里没有"灰度死亡效果在实机上工作过"的证据**
4. ⇒ **第 99 节的实机验证是【类型 0 + 六个 configstring**，不是这个**
5. ⇒ **2026-08-23 一个玩家报告看不见它**
6. ⇒ **而【没有仪器能分开**】三个可能：
      · **从未入队**
      · **入队但未应用**
      · **已应用但【没人在看那个客户端的窗口**】
7. ⇒ **所以 Deaths 罕见 ⇒ 【每次死亡记一行**，而不是采样**
```

**✅ ⭐⭐ **"三个可能，而没有一个仪器能分开"** —— 与 §405 的"『领先/失去是静默的』有三个可能的所有者"**完全同族（**第七次"多因歧义"）。**

**⚠ 而"已应用但没人在看那个客户端的窗口"⇒ **一个特别隐蔽的第三可能**。**

**✅ 与 §403 的"错位取证"**同族（**第三次"观测位置决定结论"）。**

### 4.8 而**`N` 的二十五个**

```php
// MEASURED (dm demo, re/demo-re/12-dm-timeline.txt) -- and this one
// IS the retail trigger, not an inference. A ten-minute retail
// free-for-all sends `N "mp_cross_fire" 0` twenty-five times:
//
//   24 mid-match, each followed by an `r 2` spawn cluster 1.5-2.2 s
//      later -- 24 consecutive pairs, no exceptions
//   1  in the end-of-match sequence at 9:59.8
//
// DEATH, not spawn, and the demo proves which. There are 24 `r 2`
// clusters; the FIRST is at 0:02.5 and has no `N` before it, which
// is exactly the initial spawn.
```

**⇒ 十四层**：
```text
1. **十分钟零售自由混战发 `N "mp_cross_fire" 0` 【二十五次**】**
2. ⇒ **`24` 次在比赛中，每一次后面 `1.5–2.2` 秒跟一个 `r 2` 重生簇**
3. ⇒ **`24` 个连续配对，无例外**
4. ⇒ **`1` 次在 `9:59.8` 的结束序列里**
5. ⇒ **是【死亡】不是【出生】**，而 demo 证明是哪个
6. ⇒ **有 `24` 个 `r 2` 簇**
7. ⇒ **第一个在 `0:02.5` 且【前面没有 `N`**】
8. ⇒ **那正是【初始出生**】
9. ⇒ **所以计数读作 `24` 次死亡**
10. ⇒ **而 `1` 次初始出生 + `23` 次之后的重生**
11. ⇒ **一个出生触发会在那个第一簇前面放一个 `N`**
12. ⇒ **⇒ 所以触发是死亡**
```

**✅ ⭐⭐⭐ **一个"用配对计数排除出生假设"的证明** —— 本报告里最漂亮的一处取证。**

**⇒ 三层**：
```text
假设 A：出生触发 ⇒ 应该有 **25 个 `N`（24 重生 + 1 初始）**
假设 B：死亡触发 ⇒ 应该有 **24 个 `N`（24 死亡）**
观察：**24 个 `N` + 1 个比赛末**
⇒ **⇒ 所以是死亡触发**
```

**✅ 与 §370 的"去问键盘不要问镜像"**同族（**第十一次"用一个可判定的差异区分两个假设"）。**

**⚠ 而"为什么一个服务器在死亡的那一刻重申地图自己的 type-0 调色【没有确立】**"**

**✅ 一个**诚实的边界**。

## 五、**`announceMatchCompletion` 的"四条路径设 `completed`"**

```php
// Four different paths set matchStatus_.completed, so the transition is
// watched here rather than announced at each of them.
```

**⇒ 四层**：
```text
四条路径都设 `completed`
⇒ **所以在【一处处】观察这个转移，而不是在四条各自宣告**
⇒ **⇒ 一个"边沿触发集中在一点"的设计**
```

**✅ 与 §404 的"四个周期"**不同（这是**四个入口一个出口**）。

**⚠ 而"`matchCompletionAnnounced_` 一个旗标【就是整个守卫】**"（§406 提到 `elapsed >= 0` 是无符号上的恒真）。

**✅ 与 §406 的"`elapsed >= 0` 在上是无符号恒真、读起来像一个阈值"**完全闭合 ✓

**⇒ **第二次确认。**

## 六、**"没有人在这之后重生"**

```php
// NOBODY RESPAWNS AFTER THIS POINT. The kill that ends a match still
// arms a respawn three seconds out, so without this the loser stands
// back up in the middle of the end-of-match hold -- reported by a
// player as "after the kill and then freeze, the player respawned in
// front of me where he died".
world_.setMatchCompleted(true);
```

**⇒ 七层**：
```text
1. **在这之后【没有人重生**】**
2. ⇒ **结束比赛的那一杀【仍然武装一个三秒后的重生**】**
3. ⇒ **没有这一行 ⇒ 输家在【结束保持的中途】站起来**
4. ⇒ **玩家报告："在击杀然后冻结之后，那个玩家【就在他死的地方】在我面前重生了"**
5. ⇒ **所以 `setMatchCompleted(true)`**
```

**✅ ⭐ **一个精确的、有玩家原话的症状描述**。**

**✅ 与 §404 的"最终击杀得不到私有回放"**同族（**第二次"最后一杀的时间线问题"）。**

**⇒ 三层**：
```text
§404  最后一杀的**回放**：武装 + outro 开始 ⇒ 1500ms 后孤立触发
§407  最后一杀的**重生**：武装 + match 完成 ⇒ 3 秒后站起来
⇒ **⇒ 两条都是【同一个根的两次发作**】
```

**✅ ⭐ **一个"同一个根因的两个症状"** 的完整图景。**

## 七、**`zm` 团灭的结算路径**

```php
if (matchGameType_=="zm" && world_.zombieTeamWiped())
{
    // CODREF(factory-zombie-results): five original zm recordings close
    // menus and assert479 at outcome, then ui_match_complete at+1500ms.
    // No victory music, reward grants or FFA podium on this defeat path.
    SV_SetConfigString(MatchEndTimeConfigStringIndex,"0");
    SV_SetConfigString(UiTimeLimitConfigStringIndex,"0");
    SV_SetConfigString(MatchEndUiConfigStringIndex,"1");
    for (n) for (command : {"r","H","m 0"}) queueReliableCommand(n,command);
    pushScoreboardToConnected("zm_wipe");
    return;
}
```

**⇒ 九层**：
```text
1. **`zm` 且 `zombieTeamWiped()`**
2. ⇒ **五份原始 zm 录像：关菜单、在结束时断言 `479`、然后 `+1500ms` 的 `ui_match_complete`**
3. ⇒ **这条失败路径上【没有胜利音乐、没有奖励授予、没有 FFA podium**】**
4. ⇒ **清 `d 15 0`**（HUD 倒计时）
5. ⇒ **清 `d 464 0`**（`ui_timelimit`）
6. ⇒ **`d 479 1`**（`MatchEndUiConfigStringIndex`）
7. ⇒ **逐客户端发 `{"r", "H", "m 0"}`**
8. ⇒ **`pushScoreboardToConnected("zm_wipe")`**
9. ⇒ **`return`**（**不进竞争性 outro**）
```

**✅ 与 §391 的"僵尸在玩家死光时结束"**完全闭合 ✓

**⇒ **第二次确认。**

**⚠ 而"`m 0`"⇒ **一个新模式动词**（本文件第一次见）。

**✅ 与 §402 的五套序列**同族（**第六套命令**）。

## 八、**`coop` 的 Wetwork 结算**

```php
// MEASURED (C-2021-7-25[22-11-33]coop.demo, 480850): Wetwork
// does not enter the competitive 32.7-second outro. On its completion
// frame retail clears the clock, closes the current menu, selects the
// mpOutro vision, and arms the rewards transition. The final localized
// command follows exactly one second later in driveMatchEndSequence.
if (matchGameType_ == "coop")
{
    SV_SetConfigString(MatchEndTimeConfigStringIndex, "0");
    for (n) { queueReliableCommand(n,"r"); queueReliableCommand(n,"H"); }
    SV_SetConfigString(VisionNakedConfigStringIndex, "\"mpOutro\" 500");
    for (n) {
        queueReliableCommand(n, "s show_random_rewards_screen \"1\"");
        queueReliableCommand(n, "s dw_roomJoin \"nohotjoin\"");
        queueReliableCommand(n, "s ui_match_complete \"1\"");
    }
    SV_SetConfigString(MatchEndUiConfigStringIndex, "1");
    SV_SetConfigString(UiTimeLimitConfigStringIndex, "0");
}
```

**⇒ 十二层**：
```text
1. **Wetwork 【不进】竞争性的 `32.7` 秒 outro**
2. ⇒ **在它的完成帧零售：清时钟、关当前菜单、选 `mpOutro` 调色、武装奖励转移**
3. ⇒ **最后的本地化命令在 `driveMatchEndSequence` 里【正好一秒之后】跟随**
4. ⇒ **`d 15 0`**
5. ⇒ **逐客户端 `r` + `H`**
6. ⇒ **`d 2557 "mpOutro" 500`** ⇒ **一个 500ms 混合**
7. ⇒ **三条 `s`**：
      · **`show_random_rewards_screen "1"`**
      · **`dw_roomJoin "nohotjoin"`**
      · **`ui_match_complete "1"`**
8. ⇒ **`d 479 1`** + **`d 464 0`**
9. ⇒ **`return`**
```

**✅ ⭐ **`mpOutro` 是【唯一一个出现在源码字面量里的 vision 名**】**（其余都是 `<map>` 或 `zm_begin` 等）。

**⚠ 而"`dw_roomJoin "nohotjoin"`"⇒ **与 `dwRoom*` 族**配合（记忆：Demonware 层）。

**✅ 与 §373 的"`d 15 0` 清零 vs `d 15 <time>` 设起点"**完全闭合 ✓

**⇒ **第三次确认 `cs 15`。**

## 九、关键结论

1. **⭐⭐⭐ vision 家族只拒【一个名字 `black_bw`】**，而拒的条件是**两个无参谓词在一个全局上**（`0x005AB9A0` 测 `==1`、`0x005ABA00` 测 `==2`），**没有别的名字被过滤**。
2. **⭐⭐⭐ "这是一个【刻意的 OLfinal 独有增量】，而它是这条路径上【唯一的一个】"** —— 因为 **dest1yo 的 3.3.3.3 服务器也不发它**，所以它不是补移植缺口。
3. **"同一语料在同一动词上还有命名集"**（`N "zm_begin" 100`、`N "coup_sunblind" 400`）与 **`'3'` 下的类型 5 叠加** —— **动词字母的含义正如反汇编所说的独立确认**。
4. **⭐ "测量从【实际入队】起算，所以一个晚帧不能把两条命令塌成一个未渲染的闪"`** —— 第三次"时间的基准决定结果"。
5. **Factory entry 的几何**：`portal = origin + z52`、`flash = origin + 前方 20（沿 yaw）+ z62`；**三阶段 FX（`600`/`100`ms，窗口 `<1100`）**；**载体 `0` @ `6100`、`1` @ `3600` 释放**；**`4100` 发 `zm_begin 100`、`+400` 发 `zm_factory_sh 2000`**。
6. **槽变 `Free` ⇒ 释放它的两个载体实体并 `erase`** —— 第八次确认"号复用"。
7. **⭐⭐⭐ `L` 的第二个参数【就是】那个展示槽位号** —— `L n 7` = "看击杀者"卡，而 **2697 `_damage.gsc` 的 `SetCardDisplaySlot(attacker, 7)` 是语义锚**；`7` = killed-by、`8` = you-killed。
8. **⭐ 零售每死一条 `L <victim> 7`（`28` 条/局）而我方只有 `4` 条** —— 与 `perkSlot` 的"我们太多（210 vs 0）"**相反**，所以是**一个双向覆盖**。
9. **⭐⭐ `d 792` 每死写【两次】且 `mat`/`offmat` 【换位】**：① `mat -1` `offmat -1`；② `offmat -1` `mat 154`；随后空值清除。**我方此前只在 podium 清一次、从没写过 ⇒ 尸体/死亡点标记一直是空的**。
10. **⭐ "拿不到实体就跳过（不猜数）"**，而 **`number`（网络实体号）与 `\ent\<n>`（实体索引）是两个号** —— 第二十四次"不要发明"，第二次"两个号的区分"。
11. **⭐⭐⭐ "`3 "grayscale"` 的触发是【发明的】，而零售 dm 一条 `3` 都不发"`**，且 **"没有仪器能分开『从未入队』『入队但未应用』『已应用但没人在看那个客户端的窗口』三个可能"`** —— 第七次"多因歧义"，第三个可能尤其隐蔽。
12. **⭐⭐⭐ `N "mp_cross_fire" 0` 的 `25` 次与死亡触发**：**`24` 次比赛内（后面紧跟 `1.5–2.2` 秒的 `r 2`）+ `1` 次比赛末**；**而 `24` 个 `r 2` 簇的第一个（`0:02.5`）【前面没有 `N`】** ⇒ **所以是死亡不是出生**（出生触发应该是 25 个 `N`）。一个用配对计数排除竞争假设的漂亮证明。
13. **⭐ "四条不同路径都设 `matchStatus_.completed`，所以在【一处处】观察这个转移"`** —— 四个入口一个出口。
14. **⭐⭐ "没有人在这之后重生：结束比赛的那一杀仍然武装一个三秒后的重生 ⇒ 没有它在输家会在结束保持的中途站起来 —— 玩家报告『在击杀然后冻结之后，那个玩家就在他死的地方在我面前重生了』"`** —— 与 §404 的"最后一杀的私有回放"是**同一个根的两次发作**。
15. **`zm` 团灭路径**：**"五份原始 zm 录像：关菜单、在结束时断言 `479`、然后 `+1500ms` 的 `ui_match_complete`；这条失败路径上没有胜利音乐、没有奖励授予、没有 FFA podium"`** ⇒ 清 `d 15`/`d 464`、设 `d 479 1`、逐客户端 `{"r","H","m 0"}`、`pushScoreboardToConnected("zm_wipe")`。
16. **`coop` 的 Wetwork 结算**：**`mpOutro` 是唯一出现在源码字面量里的 vision 名**（`d 2557 "mpOutro" 500`），三条 `s` 含 `dw_roomJoin "nohotjoin"`。

## 十、未闭合点

- `black_bw` 被拒的两种客户端状态是什么（两个全局值 `1`/`2`）。
- `d 792` 的键顺序（`mat`/`offmat` 换位）是否有语义。
- `mat 154` 是什么材质。
- `m 0` 这个动词的语义。
- `> 161` / `s 2972` 的语义。
- `post_game_*` 动画名在 CCS 命名空间的完整表。
- `sv_main_mp.cpp` 6278 行之后未读取。
