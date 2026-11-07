# 389 · **`sv_main_mp.cpp` 开篇** —— "一个具名正确嫌疑人的仪器"、六项"必须丢弃命令"的失败阶段、`battery_multiplier = 1.2`

## 一、范围

本报告学习 `sv_main_mp.cpp` 1–300 行（文件共 657,426 字节）。

## 二、**`reportWorldFrameRejection`：一个具名正确嫌疑人的仪器**（本组最重要的一段）

### 2.1 那段

```cpp
// AN INSTRUMENT THAT NAMES THE RIGHT SUSPECT, AND IS SILENT WHEN HEALTHY.
//
// beginFrame and endFrame both refuse by returning false, and both call sites
// simply returned. A refusal publishes no playerStates, so the ONLY thing that
// ever appeared in the log was the snapshot writer's
// `failure=missing_playerstate` -- which is two layers downstream of the fault
// and reads as "the snapshot is malformed" when the truth is "the world never
// ran". Four hypotheses were built on that reading and all four died.
//
// Edge-triggered on the phase name: one line when a healthy server starts
// refusing, one line when it recovers, nothing at 20 Hz in between. Pass an
// empty name for "the frame completed".
void reportWorldFrameRejection(const std::string_view phase)
{
    static std::string current;
    if (current == phase) return;
    current = phase;
    if (phase.empty()) {
        OlMod::RuntimeLog::write(..., "world frame publishing again");
        return;
    }
    OlMod::RuntimeLog::write(..., "WORLD FRAME REJECTED in " + std::string(phase) +
        " - nothing is published, so every snapshot will report "
        "missing_playerstate. The fault is upstream: look for a native "
        "entity mirror failure on the lines above.");
}
```

### 2.2 十五层

```text
1. **一个【命名正确嫌疑人】的仪器，而在健康时【静默】**
2. ⇒ **`beginFrame` 与 `endFrame` 都用【返回 false】拒绝**
3. ⇒ **而两个调用点【只是 `return`】**
4. ⇒ **一次拒绝【不发布任何 `playerState`】**
5. ⇒ **所以日志里唯一出现过的东西是快照写入器的 `failure=missing_playerstate`**
6. ⇒ **而它在故障【下游两层】**
7. ⇒ **并读起来像"快照畸形"而真相是"世界从未跑"**
8. ⇒ **【四个假设】建在那个读法上而【四个全死了】**
9. ⇒ **按阶段名边沿触发**：
     · **健康服务器开始拒绝时一行**
     · **恢复时一行**
     · **中间 20Hz 时【什么都没有】**
10. ⇒ **传空名表示"帧完成了"**
11. ⇒ **而恢复时的日志说 `world frame publishing again`**
12. ⇒ **而拒绝时的日志说 `WORLD FRAME REJECTED in <phase>`**
13. ⇒ **并【主动指出下游症状】**（`every snapshot will report missing_playerstate`）
14. ⇒ **并【主动指出方向】**（`The fault is upstream: look for a native entity mirror failure on the lines above`）
```

### 2.3 ⭐⭐ **"四个假设建在那个读法上而四个全死了"**

**✅ 这是本文件里**对"错误诊断代价"最直白的记录**。**

**⇒ 三层**：

```text
错误的下游症状（`missing_playerstate`）
⇒ **四个假设都建在它上面**
⇒ **而四个全死**
⇒ **⇒ 因为故障在上游两层**
```

**✅ 与 §377 的"那个读法在 `mp_battlecity` 上花了【一个长会话】"**完全同族（**第二次"下游症状误导"）。**

**⇒ 而这里是 **四个假设** 的量级。**

**⚠ 而"主动指出下游症状"⇒ **一个极成熟的仪器设计**（不只是命名自己，还说明**别人会看到什么**）。**

**✅ 与 §348 的"`clientinfo WIRE baseline=empty(UNFLAGGED)`"、§377 的"`NO WORLD STATE` 的六级死锁链"**同族（**第三次"前瞻性诊断"）。**

## 三、**六项"必须丢弃命令"的失败阶段**（本组第二重要）

### 3.1 那段

```cpp
// A NON-FATAL THINK FAILURE MUST NOT PIN THE QUEUE. When clientThink fails and the
// stage is not listed here, the caller BREAKS without discarding, so the same
// command is retried forever, commitExecutedUserCmd is never reached,
// lastExecutedUserCmd stays empty (`cmdAge=-1`), pending stops draining and the
// server's authoritative position can never follow the player -- which on screen is
// a permanent snap back to the spawn point.
//
// This is also why fixing the pmove looked like it changed nothing.
// NativePmoveNativeException was already listed, so while the pmove crashed on every
// command the queue still drained. With the pmove working, the next failure in line
// -- WeaponMovementRejected -- took over the jam instead, and the symptom was
// identical.
//
// THE THREE BELOW ARE PINS BY CONSTRUCTION, not by policy. Each compares the
// command against something that cannot move while that command sits at the front
// of the queue, so retrying it is a guaranteed infinite loop:
//
//   NonIncreasingCommandTime             cmd.commandTime <= ps.commandTime, and
//   NativePmoveNonIncreasingCommandTime  ps.commandTime only advances when a
//                                        command executes -- which this one cannot
//   NativePmoveInvalidCommand            validNativeCommand() reads the command and
//                                        nothing else
//
// This is also the reference behaviour, not a workaround. ClientThink_real clamps
// cmd.serverTime into [level.time - 1000, level.time + 200] and then RETURNS when
// `cmd.serverTime - ps.commandTime < 1`: the stale command was already consumed by
// SV_ClientThink and is never replayed. The native pmove already carries the clamp
// (MaximumBacklog); this is the consume half of the same contract.
return stage == SvClientThinkFailureStage::ClientEventsRejected ||
    stage == SvClientThinkFailureStage::NativePmoveNativeException ||
    stage == SvClientThinkFailureStage::WeaponMovementRejected ||
    stage == SvClientThinkFailureStage::NonIncreasingCommandTime ||
    stage == SvClientThinkFailureStage::NativePmoveNonIncreasingCommandTime ||
    stage == SvClientThinkFailureStage::NativePmoveInvalidCommand;
```

### 3.2 二十层

```text
1. **一个非致命的 think 失败【绝不能钉住队列】**
2. ⇒ **当 `clientThink` 失败而这个阶段不在列表里**
3. ⇒ **调用方【`break` 而不丢弃】**
4. ⇒ **所以同一条命令【永远重试】**
5. ⇒ **`commitExecutedUserCmd` 永不到达**
6. ⇒ **`lastExecutedUserCmd` 保持空（`cmdAge=-1`）**
7. ⇒ **`pending` 停止排空**
8. ⇒ **而服务器的权威位置【永远不能跟上玩家】**
9. ⇒ **而屏幕上那是【永久回弹到出生点】**
10. ⇒ **这也是为什么【修好 pmove 看起来什么也没改变】**
11. ⇒ **`NativePmoveNativeException` 已经列在里面**
12. ⇒ **所以当 pmove 对每一条命令都崩溃时队列【仍在排空】**
13. ⇒ **而 pmove 修好后，下一个失败在队列里 —— `WeaponMovementRejected` —— 接管了那个卡住**
14. ⇒ **而症状【完全相同】**
15. ⇒ **下面三个是【构造性的钉住】，不是策略性的**
16. ⇒ **每一个把命令与一个【无法移动】的东西比较**
17. ⇒ **所以重试它是【一个保证的无限循环】**
18. ⇒ **而这也是【参照的行为，不是一个绕路】**
19. ⇒ **`ClientThink_real` 把 `cmd.serverTime` 夹到 `[level.time - 1000, level.time + 200]` 然后当 `< 1` 时【返回】**
20. ⇒ **所以陈旧命令已被 `SV_ClientThink` 消费而【永不重放】**
21. ⇒ **而原生 pmove 已携带那个夹紧（`MaximumBacklog`）**
22. ⇒ **这是同一契约的【消费那一半】**
```

### 3.3 ⭐⭐ **"修好 pmove 看起来什么也没改变"**

**✅ 与 §355 的"两个极端都试过而两个都错"**不同**（这是**一个修好而另一个接管**）。**

**⇒ 三层**：

```text
阶段 A：`NativePmoveNativeException` 钉住队列（已处理）
⇒ 修好 pmove ⇒ **阶段 B：`WeaponMovementRejected` 接管**
⇒ **症状【完全相同】**
⇒ **⇒ 所以"修好一个"看不出来**
```

**✅ **一个极精准的"掩盖"机制**。**

**⚠ 而"症状完全相同"⇒ **所以必须逐阶段排查**。**

**✅ 与 §349 的"四十个阶段名"**完全闭合 ✓

**⇒ **第三次确认那四十个阶段的必要性。**

### 3.4 而**"三个构造性的钉住"**

```text
NonIncreasingCommandTime
NativePmoveNonIncreasingCommandTime
NativePmoveInvalidCommand
```

**⇒ 三层**：

```text
1. **三者都【比较命令与一个无法移动的东西】**
2. ⇒ **所以重试是【保证的无限循环】**
3. ⇒ **所以【必须丢弃】而不是重试**
```

**✅ 一个**精确的分类**（构造性的 vs 策略性的）。**

**⚠ 而 `ClientEventsRejected` 与 `WeaponMovementRejected` 是**策略性的**（"一个未完成的子系统可以拒绝"）。**

**✅ 与 §349 的"十九种 frame failure"**配合。

### 3.5 而**参照行为**

```text
`ClientThink_real` 把 `cmd.serverTime` 夹到 `[level.time - 1000, level.time + 200]`
⇒ 然后当 `cmd.serverTime - ps.commandTime < 1` 时【返回】
⇒ 所以陈旧命令已被 `SV_ClientThink` 消费
```

**✅ 一个**精确的"参照行为"引用**。**

**⚠ 而"200"与"1000"⇒ **两个不对称的界**。**

**✅ 与 §375 的"`clipIndex` 的 `[-88, +18]`"**同族（**第二次"不对称的界"）。**

## 四、**`SV_ChargeClientThinkTime`**（本组第三重要）

```cpp
// CODREF(sv_process_client_thinks): Ghosts charges max(cmd.serverTime
// - ps.commandTime, 0). Com_ServerPacketEvent 0x14019AE70 drains the
// network packets and then invokes SV_ProcessClientThinks 0x1401F4450;
// SV_BuildSnapshots 0x140205FB0 resets client_t.cumulThinkTime before
// that client's snapshot cycle. The default budget is 100 ms.
const auto delta = commandTime >= playerCommandTime ? commandTime - playerCommandTime : 0;
return cumulativeThinkTime > max - delta ? max : cumulativeThinkTime + delta;
```

### 4.1 七层

```text
1. **Ghosts 计 `max(cmd.serverTime - ps.commandTime, 0)`**
2. ⇒ **`Com_ServerPacketEvent 0x14019AE70` 排空网络包**
3. ⇒ **然后调用 `SV_ProcessClientThinks 0x1401F4450`**
4. ⇒ **`SV_BuildSnapshots 0x140205FB0` 在那个客户端的快照周期之前重置 `client_t.cumulThinkTime`**
5. ⇒ **默认预算是 `100ms`**
6. ⇒ **饱和加法（防溢出）**
7. ⇒ **所以是一个"时间预算"模型**
```

**✅ 与 §369 的"两个极端都错"**不同**（这是**一个预算**）。**

**⚠ 而"默认预算 `100ms`"⇒ **与 §377 的"`SvPmFlagsMatchEndFrozen` 的 `0x800`"**不同。

**✅ 而与 §374 的"「每帧成本门 §3.3b」"**配合 —— **一个显式的成本模型。**

## 五、**`SV_ShouldDiscardRejectedUserCmd` 的六项清单**（本组第四重要）

| 阶段 | 性质 |
|---|---|
| `ClientEventsRejected` | **策略性**（未完成的子系统） |
| `NativePmoveNativeException` | **策略性**（pmove 崩溃） |
| `WeaponMovementRejected` | **策略性**（未完成） |
| `NonIncreasingCommandTime` | **构造性钉住** |
| `NativePmoveNonIncreasingCommandTime` | **构造性钉住** |
| `NativePmoveInvalidCommand` | **构造性钉住** |

**✅ 三 + 三。**

**⚠ 而"移除它一旦武器移动停止拒绝"⇒ **一个明确的 TODO**。**

**✅ 与 §350 的"`SvActorSendUnmeasuredSpawnWords` 默认关闭"**同族（**一个临时措施标记）。**

## 六、**ZM 特手机的四条实测**（本组第五重要）

### 6.1 那段

```cpp
// MEASURED FROM FACTORY, NOT COPIED FROM ANOTHER BUILD. In the retail
// 7-31 Factory demo, use of trigger entities 259/256/263 adds bits
// 23/24/22 respectively. mp_coperkstatstable rows 21..24 are the same
// four specialties in armor/quick/fast/rof order, establishing rof as
// the consecutive bit 25. The prompt literals are the battery prices.
constexpr SvZmPerkMachine ZmPerkMachines[] = {
    { "specialty_armorvest",  0, 1u << 22u, 4 },
    { "specialty_quickrevive",0, 1u << 23u, 2 },
    { "specialty_fastreload", 0, 1u << 24u, 3 },
    { "specialty_rof",        0, 1u << 25u, 2 },
};
```

### 6.2 十一层

```text
1. **从 Factory 测量，【不】从另一个 build 抄**
2. ⇒ **在零售 `7-31` Factory demo 里，使用触发器实体 `259/256/263`**
3. ⇒ **分别加位 `23`/`24`/`22`**
4. ⇒ **`mp_coperkstatstable` 的行 `21..24` 是同样的四个专长**
5. ⇒ **按 `armor`/`quick`/`fast`/`rof` 的顺序**
6. ⇒ **确立 `rof` 是连续的位 `25`**
7. ⇒ **而提示字面量是电池价格**
8. ⇒ **所以四个**：`armorvest`（位 22，价 4）/ `quickrevive`（位 23，价 2）/ `fastreload`（位 24，价 3）/ `rof`（位 25，价 2）
```

### 6.3 ⭐ **"从 Factory 测量，不从另一个 build 抄"**

**✅ 与 §360 的"`64/8` 与 `19/18` 都不能移植"**完全同族（**第五次"逐 build 常数"）。**

**⇒ 三层**：

```text
触发器 259 → 位 23
触发器 256 → 位 24
触发器 263 → 位 22
⇒ **三个直接对应，而第四个（25）由 `mp_coperkstatstable` 的【连续顺序】推**
```

**✅ ⭐ **一个"三实测 + 一推理"的混合**。**

**⚠ 而"位 25 由连续顺序确立"⇒ **一个合理的推断，而不是猜测**。**

**✅ 与 §351 的"237 个间隔方程"**同族（**第四次"由结构定结论"）。**

### 6.4 而 **`zmRawBatteryCost`**

```cpp
constexpr std::uint32_t zmRawBatteryCost(const std::uint32_t displayUnits)
{
    // battery_multiplier=1.2 in the retail demo. The client divides its
    // raw numerator by 1200 when it paints the battery counter.
    return displayUnits * 1200u;
}
```

**⇒ 四层**：

```text
1. **`battery_multiplier = 1.2`**
2. ⇒ **客户端在画电池计数器时把它的【原始分子除以 1200】**
3. ⇒ **所以 `displayUnits * 1200`**
4. ⇒ **一个"显示单位 → 原始单位"的转换**
```

**✅ 与 §341 的"`clientInfo` 的字段 1 是电池"**完全闭合 ✓

**⇒ **第三次确认电池的编码**（`zombieBattery` 存的是**原始值**，客户端除以 1200）。

**⚠ 而"1.2"⇒ 所以**显示 4 单位 = 4800 原始**。**

**✅ 与 §366 的"`zombieBattery_` 的上限 `120000`"**配合（**100 显示单位**）。

**⇒ **第四次确认那个上限。**

## 七、**`SV_BuildSdObjectives` 的"两个站点"**

```cpp
if (!visible || sites.size() != 2 || (viewerTeam != SvTeam::Tf && viewerTeam != SvTeam::Sc))
    return objectives;
const auto attacker = viewerTeam == SvTeam::Tf;
objectives[0] = { .state = Active, .origin = sites[0].origin,
    .icon = attacker ? materials.targetA : materials.defendA, .entityNum = EntityNumNone };
objectives[1] = { ... targetB / defendB ... };
```

**⇒ 五层**：

```text
1. **必须 `visible` 且恰好【两个站点】且队伍是 Tf 或 Sc**
2. ⇒ **攻方（Tf）⇒ `targetA`/`targetB`**
3. ⇒ **守方（Sc）⇒ `defendA`/`defendB`**
4. ⇒ **`entityNum = EntityNumNone`**
5. ⇒ **所以四个材料索引**
```

**✅ 与 §347 的"`SV_PresentableTeam` 只 1 与 2 解析"**配合。**

**⚠ 而"`sites.size() != 2`"⇒ **恰好两个**（不是"至多"）。**

**✅ 与 §346 的"`objectives` 的 `state <= 5`"**配合。

### 7.1 而 `SV_BuildSdPlantedObjectives` 的**四个分支**

```text
Sc 且 _a ⇒ `defuseA`
Sc 且 _b ⇒ `defuseB`
Tf 且 _a ⇒ `defendA`
Tf 且 _b ⇒ `defendB`
```

**✅ 与 `SV_BuildSdObjectives` 的**两个**对比（这是**两个**：队伍 × 站点）。**

**⚠ 而"`siteLabel != "_a" && != "_b"` ⇒ 拒绝"⇒ **严格的两个标签**。**

**✅ 与 §388 的"`std::from_chars` 必须消耗整个字符串"**同族（**第三次"严格"）。**

## 八、`SV_AddSdBombObjective` 的**三个 phase**

```cpp
if (!visible || viewerTeam != SvTeam::Tf ||
    (phase != Available && phase != Dropped && phase != Carried) ||
    !all_of(origin, isfinite)) return false;
const auto empty = std::ranges::find(objectives, SvObjectiveState::Empty, &SvObjective::state);
if (empty == objectives.end()) return false;
*empty = { .state = Active, .origin = origin,
    .icon = phase == Carried ? materials.escort : materials.bomb, .entityNum = EntityNumNone };
```

**⇒ 六层**：

```text
1. **只给攻方（Tf）**
2. ⇒ **三个 phase**：`Available` / `Dropped` / `Carried`
3. ⇒ **找第一个 `Empty` 槽**
4. ⇒ **没有 ⇒ 拒绝**
5. ⇒ **`Carried` ⇒ `escort` 而其它 ⇒ `bomb`**
6. ⇒ **所以两个材料**
```

**✅ 与 §346 的"`objectives` 是 32 项数组"**配合。**

**⚠ 而"第一个 `Empty`"⇒ **一个简单的填充策略**。**

## 九、`SV_BuildObjectiveHudElems` 的"实测的 10×10"（本组第六重要）

### 9.1 那段

```cpp
// MEASURED, not ported. The dm demo's only world-coordinate
// element with a material - which is what a waypoint is - reads
// complete as:
//
//   TYPE=14  x=7924 y=2161 z=50  w=10 h=10  material=151
//            targetEnt=2047  color=alpha25  flags=0x4000
//
// 10x10, not 8x8.
.width = 10,
.height = 10,
```

### 9.2 九层

```text
1. **测量，不是移植**
2. ⇒ **dm demo 里唯一一个【带材质的世界坐标元素】**（那正是一个 waypoint）
3. ⇒ **完整读作**：
     · `TYPE=14`
     · `x=7924 y=2161 z=50`
     · **`w=10 h=10`**
     · `material=151`
     · `targetEnt=2047`
     · `color=alpha25`
     · **`flags=0x4000`**
4. ⇒ **`10x10`，【不是 8x8】**
```

**✅ 与 §346 的"`flags` 的 `16384`（即 `0x4000`）在【一个】里是置位的 —— 那个 waypoint"**完全闭合 ✓

**⇒ **第二次确认 `0x4000`（bit 14）= waypoint。**

**⚠ 而"`10x10` 不是 `8x8`"⇒ **一个具体的实测纠正**。**

**✅ 与 §355 的"`0.079` 不是 `0.385`"**同族（**第四次"一个数值错整个行为错"）。**

## 十、关键结论

1. **⭐⭐ `reportWorldFrameRejection`：一个"命名正确嫌疑人"的仪器**，而 **"四个假设建在那个读法上而四个全死了"`** —— 第二次"下游症状误导"（`missing_playerstate` 是在故障下游两层）。
2. **"按阶段名边沿触发：健康服务器开始拒绝时一行、恢复时一行、中间 20Hz 时什么都没有"`**。
3. **⭐ 而拒绝日志【主动指出下游症状】（`every snapshot will report missing_playerstate`）与【方向】（`The fault is upstream: look for a native entity mirror failure on the lines above`）** —— 第三次"前瞻性诊断"。
4. **⭐⭐ "一个非致命的 think 失败绝不能钉住队列 ⇒ 同一条命令永远重试 ⇒ `cmdAge=-1` ⇒ `pending` 停止排空 ⇒ 永久回弹到出生点"`**。
5. **⭐⭐ "这也是为什么【修好 pmove 看起来什么也没改变】—— `WeaponMovementRejected` 接管了那个卡住，而症状完全相同"`** —— 第三次确认 §349 的四十个阶段的必要性。
6. **⭐ 六项清单分两类**：三个**策略性**（未完成的子系统可以拒绝）+ 三个**构造性钉住**（比较命令与一个无法移动的东西 ⇒ 保证的无限循环）。
7. **"而这也是参照的行为，不是一个绕路：`ClientThink_real` 把 `cmd.serverTime` 夹到 `[level.time - 1000, level.time + 200]` 然后当 `< 1` 时返回"`** —— 第二次"不对称的界"。
8. **`SV_ChargeClientThinkTime` 的"默认预算 100ms"** 与 **"`SV_BuildSnapshots` 在那个客户端的快照周期之前重置 `cumulThinkTime`"`** —— 一个显式的成本模型（配 §374 的 `§3.3b`）。
9. **⭐ ZM 特手机的四条**：**三个实测**（触发器 `259/256/263` → 位 `23/24/22`）+ **一个推理**（`rof` = 位 `25`，由 `mp_coperkstatstable` 的连续顺序）。
10. **"从 Factory 测量，不从另一个 build 抄"`** —— 第五次"逐 build 常数"。
11. **⭐ `battery_multiplier = 1.2` 而"客户端把它的原始分子除以 1200"`** —— 第三次确认电池的编码（`displayUnits * 1200`）。
12. **`SV_BuildSdObjectives` 需要【恰好两个站点】**，而攻方（`Tf`）用 `targetA/B`、守方（`Sc`）用 `defendA/B`。
13. **`SV_BuildSdPlantedObjectives` 的四个分支**（队伍 × 站点），而**严格的两个标签 `_a`/`_b`**。
14. **`SV_AddSdBombObjective` 的三个 phase**（`Available`/`Dropped`/`Carried`）而 **`Carried` ⇒ `escort`，其它 ⇒ `bomb`**。
15. **⭐ `SV_BuildObjectiveHudElems` 的"`10x10` 不是 `8x8`"`** —— 一个实测纠正，而 **`flags=0x4000`** 第二次确认 waypoint 的位。

## 十一、未闭合点

- `MaximumBacklog` 的确切值。
- `commitExecutedUserCmd` / `cmdAge` 的实现。
- `mp_coperkstatstable` 的完整 24 行。
- `SvSdObjectiveMaterials` 的七个材料索引。
- `sv_main_mp.cpp` 300 行之后未读取（657,426 字节）。
