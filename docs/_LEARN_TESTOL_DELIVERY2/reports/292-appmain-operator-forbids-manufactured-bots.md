# 292 · **操作者禁令"严禁自己造人机"⇒ bot 填充默认关闭**、6v6/9v9 的模式尺寸、bot 必须借真人的角色

## 一、范围

本报告学习 `Appmain.cpp` 4779–5000 行。

## 二、`botDisplayName` 的**地址池日志**

```php
logGameServer("BOTTRACE|name-pool count=" + names.size() + " source=" +
    (value && value[0] ? "OLMOD_BOT_NAMES" : "official21") + " first=" + names.front());
return names;
}();
return pool[index % pool.size()];
```

### 2.1 四个量

```text
count      池大小
source     OLMOD_BOT_NAMES 或 official21
first      第一个名字
```

### 2.2 而 `pool[index % pool.size()]` 是**循环**

**⇒ 与 §291 的"按槽索引循环"一致。**

**⚠ 而 `pool.size()` 为 0 时**除零**。**

**⇒ 但 `pool` 至少有一个（因为 `kCodolOfficialBotNames` 是常数数组）。**

**⇒ 除非 `OLMOD_BOT_NAMES` 提供了**空串** —— 但 `supplied.empty()` 时不覆盖池。** ✓

## 三、**"严禁自己造人机"**（本组最重要的一段）

### 3.1 那段操作者方向

```php
// OLMOD(bot-fill-off-by-default): OFF UNLESS ASKED FOR -- OPERATOR DIRECTION, 2026-10-12.
// Goal statement, same day: "严禁自己造人机。追求官方原生人机进房间再进图" and, in the
// live message that moved this switch, "如果你的人机移动全是自己编的，取消，我们要走官方
// bot，不是让你自己造". These clients ARE ours: createBotClient synthesises them, and the
// official native bot AI is not in this retail engine (an in-memory scan of the client
// engine for the native bot strings returned zero; it lives in codol_dedrun.exe). So a
// manufactured 6v6 no longer appears by default -- an empty lobby does. OLMOD_BOT_FILL=<n>
// turns the fill back on for an experiment.
// POLICY, not native data: 经典爆破 is 6v6, so the opt-in default target is 12
// slots. OLMOD_BOTS keeps its historical job as a floor on the count.
```

### 3.2 六层

```text
1. 操作者方向 2026-10-12："**严禁自己造人机。追求官方原生人机进房间再进图**"
2. 而"如果你的人机移动全是自己编的，取消，我们要走官方 bot，**不是让你自己造**"
3. ⇒ **这些客户端是我们的**：`createBotClient` 合成它们
4. 而**官方原生 bot AI 不在这个零售引擎里**
     （对客户端引擎做内存扫描找原生 bot 串**返回零**；它在 `codol_dedrun.exe` 里）
5. ⇒ 一个**制造的 6v6 默认不再出现** —— 出现的是**一个空大厅**
6. ⇒ `OLMOD_BOT_FILL=<n>` 为实验重新打开填充
```

### 3.3 **这是整个文件里最重要的一条"用户指令"记录**

**⇒ 操作者明确拒绝了"自己造 bot"。**

**⇒ 而实现尊重了它（默认关）。**

**⇒ 与 §283 的"操作者方向 2026-10-13：房间必须显示官方 bot 模型；克隆宿主的模样是禁止的（『谁让你复制我的了』）"**同族** —— 第二条操作者禁令。**

**⇒ 两条禁令**方向一致**：不要自己造，要官方。**
```

### 3.4 而**"官方 bot AI 在 `codol_dedrun.exe` 里"**

**⇒ 一个**关键的技术事实**：**

```text
零售引擎（codoMP_client_shipRetail.exe）  没有原生 bot AI
codol_dedrun.exe                          有（但那是专用服程序，我们没有）
```

**⇒ 与记忆里"launcher 从不启动游戏，卡在外部 tgp_daemon.exe"等无关。**

**⇒ 但这是一个新的模块依赖发现。**

### 3.5 而"内存扫描返回零"

**⇒ 所以**已实测排除**"零售引擎里有 bot 串"。**

**✓ 一个干净的负面结果。**

### 3.6 而"一个空大厅"

**⇒ 所以默认行为是**进一个空房间**。**

**⇒ 与 §291 的"11 个人机"矛盾？**

**⇒ 不 —— §291 说"每局 11 次"是指**开了 `OLMOD_BOT_FILL` 时**。**

## 四、`OLMOD_BOT_FILL` 的**三层**

```php
uint32 fillTarget = 12;
bool fillEnabled = false;
bool fillOverridden = false;
if (const auto *const value = std::getenv("OLMOD_BOT_FILL"); value && value[0])
{
    const auto parsed = (uint32)std::strtoul(value, nullptr, 10);
    fillEnabled = parsed != 0;
    if (fillEnabled) { fillTarget = parsed; fillOverridden = true; }
}
```

### 4.1 三个变量

```text
fillTarget      12（默认）
fillEnabled     false（默认）
fillOverridden  false（默认）
```

### 4.2 而 `"0"` ⇒ `parsed == 0` ⇒ `fillEnabled = false`**

**⇒ 所以 `OLMOD_BOT_FILL=0` 与不设置等价。**

**✓ 一个清晰的语义。**

### 4.3 而 `strtoul` 不检查

**⇒ `"abc"` ⇒ 0 ⇒ 关。**

**⇒ 无害。**

## 五、`OLMOD_BOTS` 作为**下限**

```php
if (const auto *const value = std::getenv("OLMOD_BOTS"); value && value[0])
{
    const auto fromEnvironment = (uint32)std::strtoul(value, nullptr, 10);
    if (fromEnvironment > requested) requested = fromEnvironment;
}
```

**⇒ 与 §291 的"`OLMOD_BOTS` 保留它历史的下限作用"一致** ✓

## 六、**"地图没到之前保持零"**

```php
// HOLD AT ZERO UNTIL THE MAP IS THERE. status() takes the Server lock, so
// this read is also the fence between this thread and that state.
const auto status = Server.status();
if (!status.enabled || !status.gameStateConfigured || !status.worldSpawnConfigured)
    return;
```

### 6.1 三项

```text
enabled
gameStateConfigured
worldSpawnConfigured
```

### 6.2 而"这个读也是这个线程与那个状态之间的栅栏"

**⇒ 所以 `Server.status()` 取锁 ⇒ 提供**内存屏障**。**

**✓ 一个细致的并发论证。**

## 七、**导航图每地图一次**（本组第二重要）

```php
static std::string botNavLoadedMap;
static CodolGameServer::SvBotNavGraph botNavGraph;
static CodolGameServer::SvBotNavLoadReport botNavReport;
if (DedicatedMapGeneration && !DedicatedMapGeneration->mapName.empty() &&
    DedicatedMapGeneration->mapName != botNavLoadedMap)
{
    botNavLoadedMap = DedicatedMapGeneration->mapName;
    botNavGraph = {};
    botNavReport = {};
    SV_BotNavLoadForMap(botNavLoadedMap, botNavGraph, botNavReport);
    logGameServer(SV_BotNavDescribe(botNavLoadedMap, botNavGraph, botNavReport));
    auto routing = SV_BotNavBuildRouting(botNavGraph);
    ...
    SV_BotNavPublishRouting(std::move(routing));
}
```

### 7.1 三层

```text
① 地图变了 ⇒ 重载
② 一次 BOTNAV| 行
③ 构建并发布 routing（per-frame 走零转换）
```

### 7.2 而"空图也发布"

```php
// An empty graph is published too: "this map has no waypoints" is an
// answer, and the steering pass stands still rather than guess.
```

**⇒ 三层**：

```text
1. 空图**也**发布
2. 因为"这张地图没有路点"**是一个答案**
3. ⇒ 而转向通道**站住**而不是猜
```

**⇒ 与 §279 的"参数化而不是枚举"、§288 的"留空是有意的"同族**（第五次"缺失即答案"）。

### 7.3 而**`316 nodes / 956 entries`**

```php
// One shot per map load; the CSR walk is 316 nodes / 956 entries.
```

**⇒ 两个数**：

```text
316 节点
956 边（CSR 条目）
```

**⇒ 所以平均每个节点 3 条边。**

### 7.4 而**垂直边的两个计数**

```cpp
size_t verticalAdmitted{}, verticalRefused{};
const auto limit = routing.verticalWalkMinPlanar;
for (node) for (next : routing.neighbours(node))
{
    if (next <= node) continue;                    // ← 【每对只算一次】
    const auto dz = |a[2] - b[2]|;
    if (dz <= 72.0f) continue;                     // ← 【只算 dz > 72 的】
    const auto dx = a[0]-b[0], dy = a[1]-b[1];
    if (dx*dx + dy*dy >= limit*limit) ++verticalAdmitted;
    else ++verticalRefused;
}
```

### 7.5 四层

```text
1. `next <= node ⇒ continue` ⇒ 每对只算一次（无向图去重）
2. `dz <= 72` ⇒ 跳过 ⇒ 只算"垂直落差 > 72"的边
3. 平面距离 >= limit ⇒ admitted
4. 否则 ⇒ refused
```

**⇒ 而 `72.0f` 与记忆里"A* nav graph with 72-unit height tolerance"**完全一致** ✓**

**⇒ 第三次确认那个数。**

### 7.6 而"**无平方根**"

```php
// No square root: comparing squared planar length against the squared limit
// keeps this free of any new include.
```

**⇒ 三层**：

```text
1. 比较【平方】平面长度与【平方】限制
2. ⇒ 避免 sqrt
3. ⇒ 也避免新的 include（`<cmath>` 已经有了但 sqrt 是额外开销）
```

**✓ 一个细致的优化。**

### 7.7 而"高度门现在容纳多少垂直腿、仍拒绝多少"

**⇒ 所以这是一个**参数调整的验证日志**。**

**⇒ 与 §279 的"测量而不是争论"同族。**

## 八、**模式尺寸策略**（本组第三重要）

### 8.1 那段实测

```php
// OLMOD(bot-fill-mode): THE MATCH SIZE FOLLOWS THE MODE, not one fixed number.
// Measured 2026-10-12 11:15 (mp_nuked/cha): the booking asked for `3265 18`
// and the client-side roster decoded count=18, yet only eleven bots were
// created (host + 11 = 12 slots) because the default target was the 6v6
// twelve -- the 9v9 room stayed six players short, and 甲方 sees an empty
// charge match. 经典爆破 is 6v6 (12 slots) and 冲锋团队竞技 is 9v9 (18 slots);
// both are the publisher's own mode sizes, and `perSide = fillTarget / 2`
// below turns 18 into 9v9 for a 1-human lobby. OLMOD_BOT_FILL still wins
// when an operator pins a count.
if (fillEnabled && !fillOverridden && matchGameType == "cha")
    fillTarget = 18u;
```

### 8.2 六层

```text
1. 实测 2026-10-12 11:15（mp_nuked/cha）：booking 要了 `3265 18`
2. 客户端名册解码 `count=18`
3. 而只创建了 **11 个 bot**（host + 11 = 12 槽）因为默认目标是 6v6 的 12
4. ⇒ 9v9 的房间**少了六个人**，甲方看到一个**空的冲锋比赛**
5. 经典爆破 6v6（12 槽）/ 冲锋团队竞技 9v9（18 槽）—— 都是**出版方的模式尺寸**
6. ⇒ `perSide = fillTarget / 2` 把 18 变成 1 人类大厅的 9v9
```

### 8.3 而 `3265 18` 是**booking 命令串**

**⇒ 与 §151 的"两个预定语法（`mmstart 2486 1; ...; g_gametype war; ... map mp_bloc`）"**不同**。**

**⇒ 这是另一个命令格式（`3265 18`）。**

**⚠ 可能是 `mmstart` 的参数。**

### 8.4 而"甲方看到空的冲锋比赛"

**⇒ 一个**具体的玩家可见症状**。**

### 8.5 而 `!fillOverridden` 的条件

```php
if (fillEnabled && !fillOverridden && matchGameType == "cha")
    fillTarget = 18u;
```

**⇒ 三个条件**：

```text
fillEnabled
!fillOverridden           ← 【操作者没钉数字】
matchGameType == "cha"
```

**⇒ 所以 `OLMOD_BOT_FILL=12` 会覆盖 18。** ✓

### 8.6 而**只处理 `cha`**

**⚠ 其它 9v9 模式（如果有）不会得到 18。**

**⇒ 这是一个**硬编码的模式表**（只有一个条目）。**

**⇒ 与"THE MATCH SIZE FOLLOWS THE MODE"的说法**不完全一致**。**

## 九、`perSide = fillTarget / 2` 与**交错填充**

```cpp
const auto perSide = fillTarget / 2u;
const auto needTf = perSide > realTf ? perSide - realTf : 0u;
const auto needSc = perSide > realSc ? perSide - realSc : 0u;
// Interleaved, so a partially created fill is never lopsided.
for (uint32 i = 0; i < std::max(needTf, needSc); ++i)
{
    if (i < needTf) plan.push_back(SvTeam::Tf);
    if (i < needSc) plan.push_back(SvTeam::Sc);
}
```

### 9.1 三层

```text
① 每侧 = fillTarget / 2
② 缺口 = 每侧 - 当前真人
③ 【交错】填 —— Tf, Sc, Tf, Sc, ...
```

### 9.2 而"交错，所以一个部分完成的填充永远不会偏斜"

**⇒ 三层**：

```text
1. 填充可能跨多帧（§9.4）
2. ⇒ 如果先填完一侧再填另一侧，中途会偏斜
3. ⇒ 交错保证任何时刻两侧差最多 1
```

**✓ 一个细致的设计。**

### 9.3 ⚠ **`fillTarget = 18` 时 `perSide = 9`**

**⇒ 所以 9v9 ✓ 与注释一致。**

**⚠ 而 `fillTarget = 13` 时 `perSide = 6` ⇒ 只填 6v6 = 12 槽，**少于 13**。**

**⇒ 所以奇数目标会浪费一个槽。**

### 9.4 而"这个函数在后续帧再次运行"

```php
// ONCE PER TARGET, NOT ONCE PER CALL. This function runs again on later
// frames (it is how a partially created fill finishes), so an unguarded
// line here is thousands of lines a second -- the exact flood pattern
// removed from the pmove trace earlier today.
```

**⇒ 三层**：

```text
1. 这个函数在后续帧**再次运行**（这是部分创建的填充如何完成的）
2. ⇒ 一个没有守卫的日志行在这里是**每秒数千行**
3. ⇒ 正是今天早些时候从 pmove trace 移除的洪水模式
```

**⇒ 与 §235 的"热日志修复"同族**（第四次）。

### 9.5 而日志的**两个静态量**

```cpp
static uint32 loggedFillTarget = 0;
static std::string loggedFillMode;
if (loggedFillTarget != fillTarget || loggedFillMode != matchGameType)
{ ... 打印 ... }
```

**⇒ 两个值都变才打印。**

**⇒ 所以"目标变"或"模式变"都会打印，但"同一个"不打印。**

## 十、**"等待宿主的一方而不是猜一个"**

```cpp
// WAIT FOR THE HOST'S SIDE INSTEAD OF GUESSING ONE. A bot created
// while the class menu is still open inherits a still-None team and
// then cannot spawn (measured 2026-10-10 33:0x, sv_main_mp.cpp
// :8798-8809). The window closes at class confirmation.
if (realTf + realSc == 0) return;
```

### 10.1 三层

```text
1. 一个在职业菜单还开着时创建的 bot 继承一个仍是 `None` 的队伍
2. ⇒ 然后**不能 spawn**（实测 2026-10-10）
3. ⇒ 那个窗口在**职业确认**时关闭
```

**⇒ 所以"等待宿主选边"。**

**⇒ 与记忆里"`spawn refused ... NO_SPAWN_POINT`"**不同原因但同样症状**。**

## 十一、**"没有任何东西被发明"**（本组第四重要）

```php
// NOTHING IS INVENTED. Both the class and the character come from a
// member the server has already published: the bot's synthetic xuid is
// registered with a COPY of that member's assets. That copy is what
// gives characterCustomizationProvider_ an answer for the bot
// (sv_main_mp.cpp:8515) and what makes validCharacterCustomization true
// in the world's spawn gate (sv_snapshot_mp.cpp:18793) -- without it the
// spawn is refused with CUSTOMIZATION_ABSENT and the bot never appears.
// The class copy is belt-and-braces: ServerCore::createBotClient
// pre-fills resolvedLoadouts_ so the profile getter is not reached.
```

### 11.1 五层

```text
1. 职业与角色**都**来自服务器**已经发布**的一个成员
2. ⇒ bot 的合成 xuid 用一个那个成员资产的**拷贝**注册
3. ⇒ 那个拷贝给 `characterCustomizationProvider_` 一个答案
4. ⇒ 而它让 `validCharacterCustomization` 为真（在世界的 spawn 门里）
5. ⇒ **没有它 spawn 会被 CUSTOMIZATION_ABSENT 拒绝**而 bot 永不出现
```

### 11.2 而"职业拷贝是双保险"

**⇒ 因为 `createBotClient` 预填 `resolvedLoadouts_` ⇒ profile getter 不会被触达。**

### 11.3 **`CUSTOMIZATION_ABSENT` 与 §282 的 spawn 合取式**

**§282**："`validCharacterCustomization` 拒绝清零 ⇒ 合取式静默丢项"

**§292**："没有那个拷贝 ⇒ spawn 被 `CUSTOMIZATION_ABSENT` 拒绝"

**⇒ 同一个校验器的两个后果。**

### 11.4 而 `member.characterPresentation.characterItemId == 0` 的过滤

```php
for (const auto &[xuid, member] : RegisteredSessionAssets.members())
{
    if (member.characterPresentation.characterItemId == 0)
```

**⇒ 只挑**有角色物品 id** 的成员作种子。**

**⇒ 因为 §282/§283 的"零意味着客户端无法解析模型"。**

**✓ 一个正确的过滤。**

## 十二、关键结论

1. **操作者禁令"严禁自己造人机"⇒ bot 填充默认关闭**。
2. **"官方原生 bot AI 不在零售引擎里"**（内存扫描零命中；在 `codol_dedrun.exe`）。
3. **默认行为是一个空大厅**。
4. **`OLMOD_BOT_FILL=0` 与不设置等价**。
5. **`OLMOD_BOTS` 保留"下限"作用**。
6. **`Server.status()` 取锁 ⇒ 也是线程栅栏**。
7. **导航图每地图一次，空图也发布**（"这张地图没有路点"是一个答案）。
8. **`316 nodes / 956 entries`** ≈ 每节点 3 边。
9. **`dz > 72` 的门与记忆里"72-unit height tolerance"**第三次确认**。
10. **无 sqrt 的平方比较**（也避免新 include）。
11. **模式尺寸：6v6 = 12 槽、9v9 = 18 槽**，而 `cha` 特判为 18。
12. **实测 2026-10-12：booking 要 18 而只创建 11 个 bot** ⇒ 9v9 少六人。
13. **只处理 `cha` 一个模式** —— 与"follows the mode"说法不完全一致。
14. **交错填充保证两侧差最多 1**。
15. **奇数 `fillTarget` 会浪费一个槽**（13 ⇒ perSide 6 ⇒ 12 槽）。
16. **"这个函数在后续帧再次运行"** ⇒ 无守卫日志每秒数千行。
17. **"等待宿主选边而不是猜一个"** —— 职业菜单开着时创建的 bot 队伍是 `None` ⇒ 不能 spawn。
18. **"没有任何东西被发明"** —— bot 的职业与角色都来自已发布的成员。
19. **`CUSTOMIZATION_ABSENT`** 是缺那个拷贝的后果。
20. **只挑 `characterItemId != 0` 的成员作种子**。

## 十三、未闭合点

- `3265 18` 的 booking 命令格式。
- 其它 9v9 模式是否需要同样特判。
- `codol_dedrun.exe` 是否可获取。
- `Appmain.cpp` 5000 行之后未读取。
