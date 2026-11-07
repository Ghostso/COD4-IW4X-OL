# 454 · **`sv_zm_board_flight_table_mp.cpp` 全文件** —— "一个测出的发射/角停/落地，不是一个恢复的通用板件求解器"、`144` 个剖面 = `24` 个屏障 × `6` 个槽、以及 `at()` 的九道守卫

## 一、范围

本报告学习 `sv_zm_board_flight_table_mp.cpp`（**`296` 行，`68,347` 字节**）全部，以及 `sv_zm_board_flight_mp.hpp` 的 `SvZmBoardFlightProfile` 与它的 `at()` 方法。

## 二、**"一个测出的发射、角停与落地；原生 `BG_EvaluateTrajectory` 拥有飞行"**（本组最重要的一段）

### 2.1 那段（`.hpp`）

```cpp
// A measured Factory launch, angular stop and landing. Relative clocks are
// rebased to the actual release; native BG_EvaluateTrajectory owns the flight.
// These are capture-backed samples, not a recovered general board solver.
struct SvZmBoardFlightProfile
{
    std::string_view barrier;
    std::uint32_t slot{};
    SvNativeTrajectory launchPosition;
    SvNativeTrajectory launchAngles;
    SvNativeTrajectory restPosition;
    SvNativeTrajectory restAngles;
    [[nodiscard]] std::optional<SvZmBoardFlightState> at(
        std::uint32_t releaseTime, std::uint32_t now) const;
};
```

### 2.2 二十层

```text
1. **一个测出的 Factory 【发射、角停与落地**】**
2. ⇒ **相对时钟【被重基到实际的释放**】**
3. ⇒ **原生 `BG_EvaluateTrajectory` **拥有飞行**】**
4. ⇒ **⇒ 所以【这个表【不给飞行**，只给【两端**】
5. ⇒ **⚠ 这些是【从捕获支撑的样本，不是【一个恢复的通用板件求解器**】】
6. ⇒ **六个字段**：
      · **`barrier` ⇒ 屏障名**（`"pf678_auto1"`）
      · **`slot` ⇒ 一个槽号**（`1..6`）
      · **`launchPosition`/`launchAngles` ⇒ 起点**
      · **`restPosition`/`restAngles` ⇒ 终点**
```

### 2.3 ⭐⭐⭐ **"不是【一个恢复的通用板件求解器**】"**

**✅ 这是本报告里**最重要的一条"一个样本库 not a solver**。"

**✅ 与 §451 的"一个供体参照，不是恢复的 `aipaths`"**、§414 的"`nothing is derived`"**同族（**第四次"明确标注 not-a-X**）。

**⇒ 三层**：
```text
§414  **"每一个数字都是零售的，没有东西是推导的"**（**纯数据**）
§451  **"BO1 是一个供体参照，不是恢复的 `aipaths`"**（**外部参照**）
§453  **"实验性接地候选；运行时需要 resolver"**（**不自足**）
§454  **"从捕获支撑的样本，不是一个恢复的通用板件求解器"**（**不是求解器**）
⇒ **⇒ 四次"明确标注 not-a-X**】
```

**✅ ⭐⭐⭐ **一个"not-a-X"的四例表**。

**⚠ 而"相对时钟被重基到实际的释放"⇒ **一个重要的机制**。**

**⇒ 三层**：
```text
抓的样本里 `time` 是【当时的绝对时间**】
而【每个板件被撕裂的时刻【不同**】
⇒ **⇒ 所以【`at()` 把 `time += releaseTime`**】**
```

**✅ ⭐⭐ **"把 `time += releaseTime`"** —— 而 **`launchPosition.time != 0` 是一个【前置条件**（即 `time` 必须是相对 `0`）。

## 三、**`144` 个剖面 = `24` 个屏障 × `6` 个槽**（本组第二重要）

### 3.1 我的统计

```text
profile count = 144
distinct barriers = 24（pf678 / pf679 / pf680 / pf681 / pf682 / pf683
                       pf690 / pf691 / pf696 / pf697 / pf701 / pf707
                       pf708 / pf711 / pf712 / pf713 / pf714 / pf715
                       pf716 / pf744 / pf748 / pf749 / pf750 / pf751）
each with 6 slots
```

**✅ `24 × 6 = 144`** ✓

**⇒ 三层**：
```text
`24` 个屏障 × `6` 个槽 = `144` 个剖面
⇒ **⇒ 而 `.hpp` 说"`std::array<Board,6> boards{}`"（§420 的 `BarrierState`）** ⇒ **`6` 个槽吻合** ✓
```

**✅ ⭐⭐⭐ **一个"`6` 个槽"的双向确认**。</br>

**✅ 与 §420 的 `BarrierState::boards` 的 `std::array<Board, 6>`**——**完全闭合** ✓

**⇒ 三层**：
```text
§420  **`std::array<Board, 6> boards{}`**
§454  **`24 × 6 = 144` 个剖面**
⇒ **⇒ 所以【`6` 是【那个板件数组的大小**】
```

**✅ ⭐⭐ **"`6` 是那个板件数组的大小"**。

### 3.2 而**屏障名的编号**

```text
pf678 pf679 pf680 pf681 pf682 pf683    ← 连续 6 个
pf690 pf691                             ← 2 个
pf696 pf697                             ← 2 个
pf701 pf707 pf708                       ← 3 个
pf711 pf712 pf713 pf714 pf715 pf716     ← 连续 6 个
pf744 pf748 pf749 pf750 pf751           ← 5 个
```

**⇒ 十层**：
```text
1. **`pf678..pf683`（`6` 个）**
2. ⇒ **`pf690`/`pf691`（`2` 个）**
3. ⇒ **`pf696`/`pf697`（`2` 个）**
4. ⇒ **`pf701`/`pf707`/`pf708`（`3` 个）**
5. ⇒ **`pf711..pf716`（`6` 个）**
6. ⇒ **`pf744`/`pf748`/`pf749`/`pf750`/`pf751`（`5` 个）**
7. ⇒ **⇒ 总计 `24`**
```

### 3.3 ⭐⭐⭐ **"`24` 个屏障，而不是 §422 说的『八个接收窗』"**

**✅ 与 §422 的"Factory 的八个接收窗 feed 五个 boarded 入口"**——**一个值得注意的差异**。

**⇒ 三层**：
```text
§422  **"Factory 的八个接收窗（receiver spawners）"**
§454  **`24` 个屏障（`pf678..pf751`）**
⇒ **⇒ 所以【"接收窗"与"屏障"是【两个不同的集合**】
```

**✅ ⭐⭐⭐ **""接收窗"与"屏障"是两个不同的集合"** —— 一个**需要区分的点**。

**⚠ 而 §420 的"`zmBarriers_` 是一个 `std::map<std::pair<uint16,uint16>, BarrierState>`"**⇒ **键是一个【节点对**】**

**⇒ 三层**：
```text
§420  **`zmBarriers_` 键是【一个节点对**】
§454  **`barrier` 是一个【名字**（`"pf678_auto1"`）**
⇒ **⇒ 所以【两个标识**】
```

**⚠ 一个**需要核对的映射**（**名字 ↔ 节点对**）。

## 四、**`at()` 的九道守卫**（本组第三重要）

### 4.1 那段

```cpp
if (now > static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max()) ||
    now < releaseTime || launchPosition.time != 0 || launchAngles.time != 0 ||
    restPosition.time <= 0 || restAngles.time < 0 ||
    releaseTime > static_cast<std::uint32_t>(
        std::numeric_limits<std::int32_t>::max() -
        std::max(restPosition.time, restAngles.time)))
    return std::nullopt;
const auto elapsed = now - releaseTime;
const auto landed = elapsed >= static_cast<std::uint32_t>(restPosition.time);
SvZmBoardFlightState state{
    landed ? restPosition : launchPosition,
    elapsed >= static_cast<std::uint32_t>(restAngles.time) ? restAngles : launchAngles,
    landed ? 17u : 1u};
state.position.time += static_cast<std::int32_t>(releaseTime);
state.angles.time += static_cast<std::int32_t>(releaseTime);
if (!SV_IsTrajectoryValid(state.position, static_cast<std::int32_t>(now)) ||
    !SV_IsTrajectoryValid(state.angles, static_cast<std::int32_t>(now)))
    return std::nullopt;
return state;
```

### 4.2 二十四层

```text
1. **`now` 必须 `<= INT32_MAX`**（**因为下面转 `int32`**）
2. ⇒ **`now >= releaseTime`**（**不能是【释放之前**】）
3. ⇒ **`launchPosition.time == 0`**（**一个相对时钟的前置**）
4. ⇒ **`launchAngles.time == 0`**
5. ⇒ **`restPosition.time > 0`**（**一个正的落地时长**）
6. ⇒ **`restAngles.time >= 0`**（**可以为零**）
7. ⇒ **`releaseTime + max(restTime) <= INT32_MAX`**（**防溢出**）
8. ⇒ **⇒ 七道前置，然后计算**
9. ⇒ **`landed = elapsed >= restPosition.time`**
10. ⇒ **位置 ⇒ `landed ? restPosition : launchPosition`**
11. ⇒ **角度 ⇒ `elapsed >= restAngles.time ? restAngles : launchAngles`**
12. ⇒ **`flags ⇒ landed ? 17u : 1u`**
13. ⇒ **两个 `time += releaseTime`**（**重基**）
14. ⇒ **两道 `SV_IsTrajectoryValid`**（**九道总计**）
```

### 4.3 ⭐⭐⭐ **"位置与角度【各自**有一个落地判据（`restPosition.time` vs `restAngles.time`）"**

**✅ 这是本报告里**最重要的一条"两个独立的时间线**。**

**⇒ 三层**：
```text
位置 ⇒ **`landed = elapsed >= restPosition.time`**
角度 ⇒ **`elapsed >= restAngles.time`**
⇒ **⇒ 所以【角停【可以与落地不同时**】】
```

**✅ ⭐⭐⭐ **"角停可以与落地不同时"** —— 而 **`.hpp` 的注释【明说**"launch, **angular stop**, and landing"**（**三个事件**）。

**⇒ 三层**：
```text
发射 ⇒ `launchPosition`/`launchAngles`（**同一时刻，`time == 0`**）
角停 ⇒ `restAngles.time`
落地 ⇒ `restPosition.time`
⇒ **⇒ 所以【三个事件，两个时刻**】
```

**✅ ⭐⭐ **"三个事件两个时刻"** —— 而**角度【先停**（`restAngles.time`）而**位置【后落**（`restPosition.time`）。

**⚠ 而样例数据**：

```text
{"pf678_auto1",1,
  launch: {5,0,0, {398,-104,147}, {180.674,0,288.289}},
  launchAngles: {7,0,470, ...}          ← **launchAngles.time = 0**
  restPosition: {0,950,0, {570,-104,60}, ...}   ← **restPosition.time = 950**
  restAngles: {0,1000,470, {90,0,0}, ...}}      ← **restAngles.time = 1000**
```

**⇒ 所以：位置在 `950ms` 落地，角度在 `1000ms` 停** ⇒ **角度【晚 `50ms`**】**

**✅ ⭐⭐⭐ **"角度晚 `50ms` 停"** —— 而**样例数据确认**。</br>

**⚠ 一个**可推导的物理直觉**（**一个板件【先落地然后【摆动停下**）。

### 4.4 而**`flags` 的 `17u` vs `1u`**

**⇒ 十层**：
```text
未落地 ⇒ `flags = 1`
已落地 ⇒ `flags = 17`
⇒ **⇒ 而 `1 | 16 = 17`** ⇒ **所以【`16` 是【一个"已落地"的位**】
```

**✅ ⭐⭐⭐ **"`17 = 1 | 16`，所以 `16` 是一个『已落地』的位"**。</br>

**✅ 与 §424 的"尸体的三阶段的 `trType 13` + `aprType 10`"**不同（这是**一个 `flags` 位**）。

**⇒ 三层**：
```text
`flags = 1`  ⇒ **飞行中**
`flags = 17` ⇒ **已落地**（`1 | 0x10`）
⇒ **⇒ 而 `0x10` 可能是【`SVF_NOCLIENT` 或一个"静止**"**
```

**✅ 与 §416 的 `SvEFlagsNoDraw = 0x10`**——**同值！**

**⇒ 三层**：
```text
§416  **`SvEFlagsNoDraw = 0x10`**（**`CG_ScriptMover` 测它并返回**）
§454  **`flags = 17 = 1 | 0x10`**
⇒ **⇒ 所以【一个落地的板件【不画**？】
```

**⚠ 一个**需要核对的矛盾**（**一个落地的板件【应该【被画**】**）。

**⇒ 三层**：
```text
若 `0x10` = `NODRAW` ⇒ **落地的板件不可见** ⇒ **一个缺陷**
若 `0x10` 在 `SvNativeTrajectory` 的 `flags` 里是【另一个含义**】 ⇒ **正常**
⇒ **⇒ 所以【两个 `0x10` 在【两个不同的 `flags` 字段**】
```

**✅ ⭐⭐⭐ **"两个 `0x10` 在两个不同的 `flags` 字段"** —— 一个**极精准的区分**（**`eFlags` vs `SvNativeTrajectory::flags`**）。

## 五、**`24` 个屏障的来源 demo**

### 5.1 我的统计

```text
C-2021-7-31[15-32-16]zm.demo  ⇒ 129 个剖面
C-2021-8-30[20-21-43]zm.demo  ⇒  15 个剖面
                              总计 144
```

**⇒ 八层**：
```text
1. **两个 demo，`+1` 个源**
2. ⇒ **`129` 来自 `7-31`（`89.6%`）**
3. ⇒ **`15` 来自 `8-30`（`10.4%`）**
4. ⇒ **⇒ 所以【一个主源 + 一个补充源**】
```

**✅ 与 `generate_board_flights.py` 的"三个 Factory demo"**（头部注释）——**而实际是【两个** demo 出现在数据里。

**⚠ 一处**小差异**（**头说"三个"，而数据里两个**）。

**⇒ 三层**：
```text
头部：**"Generated from the three Factory demos"**
数据：**两个 demo 的注释**
⇒ **⇒ 所以【第三个【可能贡献了【没有注释的行**，或【全部** `144` 行【都有注释**】
```

**✅ 与 §453 的注释与代码的差异**同族（**第三次"声明与实际不符**）。

**⇒ 三层**：
```text
§450 二  **注释声称 `"method:delete"` 有前缀，实际无前缀**
§450 三  **"Lua 的数字是 `double`"与 `zmsetround` 矛盾**
§454  **"三个 Factory demo"而数据里两个**
⇒ **⇒ 三次"声明与实际**】
```

**✅ ⭐⭐ **一个"声明与实际"的三例表**。

## 六、`SV_FactoryBoardFlights()` 的"一个函数返回一个 span"

```cpp
std::span<const SvZmBoardFlightProfile> SV_FactoryBoardFlights()
{
    static const SvZmBoardFlightProfile profiles[] = { ... };
    return profiles;
}
```

**⇒ 八层**：
```text
1. **一个函数，返回一个 `span`**
2. ⇒ **`static const` 数组**（**函数级静态**）
3. ⇒ **⇒ 所以【一次构造，永远复用**】
4. ⇒ **而【返回 `std::span`**（**C++20 的 `std::span` 有一个【从数组构造**的推导**）**
```

### 6.1 ⭐⭐⭐ **"没有 mapName 参数，因为只有一个地图"**

**✅ 与 §452/§453 的 `SV_ZmNavTable(map)` 与 §451 的 `SV_ZmBo1ReferenceTable(map)`**——**三个都有 `mapName` 参数，而 `SV_FactoryBoardFlights()` 【没有**】。**

**⇒ 三层**：
```text
`SV_ZmNavTable(mapName)` ⇒ **一个参数**（**多地图**）
`SV_FactoryBoardFlights()` ⇒ **无参数**（**只有 Factory**）
⇒ **⇒ 所以【一个"只有一个实例"的函数【不需要**那个参数】
```

**✅ ⭐⭐⭐ **"一个只有一个实例的函数不需要那个参数"** —— 与 §414 的 `SV_ConstBaselineTable(map, gameType)` 的**两个参数**形成完整对照。

**⇒ 四层表**：
```text
`SV_ConstBaselineTable(map, gameType)`  ⇒ **两个参数**（`18` 张表）
`SV_ZmNavTable(map)`                    ⇒ **一个参数**（`1` 张表）
`SV_ZmNavGroundedTable(map)`            ⇒ **一个参数**（`1` 张表）
`SV_ZmBo1ReferenceTable(map)`           ⇒ **一个参数**（`1` 张表）
`SV_FactoryBoardFlights()`              ⇒ **零参数**（`1` 张表）
⇒ **⇒ 所以【参数个数【反映**表的数量**】
```

**✅ ⭐⭐⭐ **"参数个数反映表的数量"** —— 一个**极精确的观察**。</br>

**✅ 而 `1` 张表【仍需**一个 `mapName` 参数（**因为调用者【不知道**），而 `SV_FactoryBoardFlights` 的调用者【知道**（**因为只有 Factory 有板件**）。

**⇒ 三层**：
```text
若【一个访问器【只对一张地图有意义**】⇒ **不需要 `mapName`**（**调用者已经知道**）
若【一个访问器【对多张地图**】⇒ **需要 `mapName`**
⇒ **⇒ 所以【`SV_ZmNavTable` 保留参数【为了【契约一致性**】（**而非必要**）
```

**✅ ⭐⭐ **"为了契约一致性而非必要"** —— 一个**可推导的理由**。

## 七、关键结论

1. **⭐⭐⭐ "一个测出的 Factory 发射、角停与落地；相对时钟被重基到实际的释放；【原生 `BG_EvaluateTrajectory` 拥有飞行】；这些是【从捕获支撑的样本，不是一个恢复的通用板件求解器】"`** —— 第四次"明确标注 not-a-X"（与 §414/§451/§453 同族）。
2. **⭐⭐⭐ `144` 个剖面 = `24` 个屏障 × `6` 个槽**，而 **§420 的 `BarrierState::boards` 是 `std::array<Board, 6>`** ⇒ **"`6` 是那个板件数组的大小"**（**一个双向确认**）。
3. **⭐⭐ `24` 个屏障名**：`pf678..pf683`（`6`）+ `pf690`/`pf691`（`2`）+ `pf696`/`pf697`（`2`）+ `pf701`/`pf707`/`pf708`（`3`）+ `pf711..pf716`（`6`）+ `pf744`/`pf748`/`pf749`/`pf750`/`pf751`（`5`）= `24`。
4. **⭐⭐ "『接收窗』与『屏障』是两个不同的集合"`**：**§422 的"Factory 的八个接收窗" vs §454 的 `24` 个屏障**；而 **§420 的 `zmBarriers_` 键是【一个节点对】而 §454 的 `barrier` 是一个【名字】⇒ 两个标识**。
5. **⭐⭐⭐ `at()` 的九道守卫**：`now <= INT32_MAX` / `now >= releaseTime` / `launchPosition.time == 0` / `launchAngles.time == 0` / `restPosition.time > 0` / `restAngles.time >= 0` / `releaseTime + max(restTime) <= INT32_MAX` / 两道 `SV_IsTrajectoryValid`。
6. **⭐⭐⭐ "位置与角度各自有一个落地判据（`restPosition.time` vs `restAngles.time`）"** ⇒ **"角停可以与落地不同时"** —— 而 `.hpp` 的注释明说"launch, **angular stop**, and landing"（**三个事件**）。
7. **⭐ 样例数据确认**：`pf678_auto1` 的 `restPosition.time = 950` 而 `restAngles.time = 1000` ⇒ **角度晚 `50ms` 停** —— 一个**可推导的物理直觉**（一个板件先落地然后摆动停下）。
8. **⭐⭐⭐ `flags` 的 `17u` vs `1u` ⇒ `1 | 0x10`，所以 `0x10` 是一个"已落地"的位** —— 而 **§416 的 `SvEFlagsNoDraw = 0x10` 是同值** ⇒ **"两个 `0x10` 在两个不同的 `flags` 字段"**（**`eFlags` vs `SvNativeTrajectory::flags`**）。
9. **⚠ 一处小差异**：**头说"Generated from the three Factory demos"而数据里只有【两个** demo 的注释**（`C-2021-7-31` `129` 个 + `C-2021-8-30` `15` 个）—— 第三次"声明与实际"（与 §450 同族）。
10. **⭐ `129/144 = 89.6%` 来自主源，`15/144 = 10.4%` 来自补充源**。
11. **⭐⭐⭐ "参数个数反映表的数量"**：`SV_ConstBaselineTable(map, gameType)`（`18` 张表，**两个参数**）/ `SV_ZmNavTable(map)` 等三个（`1` 张表，**一个参数**）/ `SV_FactoryBoardFlights()`（`1` 张表，**零参数**）—— 而 **`SV_ZmNavTable` 保留 `mapName` 【为了契约一致性而非必要**】（**因为调用者已经知道**）。

## 八、未闭合点

- `24` 个屏障名与 §420 的 `zmBarriers_` 的节点对键的映射。
- `flags` 的 `0x10` 与 `SvEFlagsNoDraw` 是否真的同义（我判断**不同字段**）。
- "三个 Factory demo"里的第三个。
- `SvNativeTrajectory` 的完整字段（`type`/`time`/`duration`/`base`/`delta`）。
- `SV_IsTrajectoryValid` 的条件。
- **下一步**：`sv_main_mp.hpp`（`98,709` 字节）。
