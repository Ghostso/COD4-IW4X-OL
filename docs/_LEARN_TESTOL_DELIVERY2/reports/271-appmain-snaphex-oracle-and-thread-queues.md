# 271 · `SNAPHEX` 的取样预算、`0xFFFFFF ^ 0xFFFFFF = 0` 的黑屏、八个"控制线程排队 → 游戏线程应用"

## 一、范围

本报告学习 `Appmain.cpp` 178–380 行。

## 二、`buildSnapshot` 的失败日志

```php
static std::array<SvSnapshotWriteFailure, MaximumGameClients> lastFailures{};
if (clientNum < lastFailures.size() && lastFailures[clientNum] != failure)
{
    lastFailures[clientNum] = failure;
    logGameServer("snapshot build rejected client=" + clientNum + " failure=" +
        SV_SnapshotWriteFailureName(failure) + " baseline=" + (baseline?1:0) +
        " delta=" + deltaMessageDistance + " init=" + (initializeBaselineCache?1:0));
}
```

### 2.1 **每客户端一个"上次失败值"**

**⇒ 所以"同一个失败重复出现"只打一次，而"失败类型变化"会再打。**

**⇒ 与 §268 的 `lastFailures` 同族（边沿触发）。**

### 2.2 而失败时**仍然记录耗时**

```php
if (clientNum < SnapshotBuildTiming.size())
    SnapshotBuildTiming[clientNum].record(elapsedMicroseconds(timingStart));
return {};
```

**⇒ 所以"失败也计入计时"** ✓

**⇒ 这很重要** —— 因为失败可能正是慢的原因。

### 2.3 `timingStart` 的位置

**⇒ 在 `buildSnapshot` 的最开头（§270 的 170 行）⇒ 所以计时包括 64 KB 分配、写入、hex 转储。**

**⚠ 而 hex 转储只在少数帧发生 ⇒ **计时会被 hex 转储污染**。**

**⇒ 只要 `OLMOD_SNAPSHOT_HEX` 开着，那些帧的耗时就会尖峰。**

**⇒ 注释没提这一点。**

## 三、**`SNAPHEX`：用自己的解码器作预言机**（本组最重要的一段）

### 3.1 那段完整论证

```php
// THE BYTES THIS SERVER ACTUALLY PUT ON THE WIRE, so the demo decoder can be the
// oracle for them.
//
// Tools/demo-re/codol_snapshot.py is a transcription of the client's own reader,
// validated 11,136/11,136 against recorded demos. Feeding it what was really sent
// answers questions that reading the writer cannot: a value XORed against the
// WRONG baseline still has the right framing, so it decodes cleanly to the end
// and is silently wrong. That is not hypothetical -- `0xFFFFFF ^ 0xFFFFFF = 0`
// turned a correct-looking snapshot into a black screen on this project once
// already (codol-snapshot-xor-baseline).
```

### 3.2 五层

```text
1. `codol_snapshot.py` 是客户端自己读取器的转写，在录制的 demo 上验证 11,136/11,136
2. ⇒ 把【真正发出去的】喂给它，能回答"读写入器"回答不了的问题
3. 因为一个用【错基线】XOR 的值仍然框架正确
4. ⇒ 它能干净地解码到底，而【静默地错】
5. 实例：`0xFFFFFF ^ 0xFFFFFF = 0` 曾把一个看起来正确的快照变成黑屏
```

### 3.3 **"11,136/11,136"**

**⇒ 一个完整的验证计数** —— 与 §265 的"319/319"、§258 的"27/27"同族。

### 3.4 而 `0xFFFFFF ^ 0xFFFFFF = 0` 是**精确的算术**

```text
两个相同的值 XOR ⇒ 0
```

**⇒ 而 0 在 COD 的快照里是一个**合法的**值（表示"零位置"或"默认"）。**

**⇒ 所以"XOR 对错基线"会产生"合法但错误"的字节。**

**⇒ 这与记忆里"11 个字段我们写 XOR 增量，三份参照全写裸值"、"首帧基线为零所以看不出来"**完全一致**。**

**⇒ 而记忆里还写着"idx61 恒 2047 ⇒ 永远在空中 ⇒ 悬空/无移动动画/不能跳"** —— 同一类"合法但错"。

### 3.5 这个"预言机"设计的价值

**⇒ 它把"读写入器"这个只能验证**格式**的方法，换成"用客户端的读取器解码"这个能验证**语义**的方法。**

**⇒ 这是本项目里最严谨的自检设计之一。**

## 四、`SNAPHEX` 的**四层开关**

### 4.1 第一层：`OLMOD_SNAPSHOT_HEX` 的数量

```php
static const long snapshotHexLimit = [] {
    const char *const value = std::getenv("OLMOD_SNAPSHOT_HEX");
    if (!value || !value[0]) return 0L;
    const auto parsed = std::strtol(value, nullptr, 10);
    return parsed > 0 ? parsed : 16L;
}();
```

### 4.2 三种情形

```text
未设置 / 空串     ⇒ 0（关闭）
设为正数 N        ⇒ N
设为非正数（如 0） ⇒ 16（默认）
```

**⇒ 所以 `OLMOD_SNAPSHOT_HEX=0` **不等于关闭**，而是"用默认 16"。**

**⚠ 这是一个反直觉的行为** —— 用户可能以为 `=0` 是关。**

**⇒ 要关闭必须**不设置**或设空串。**

### 4.3 ⚠ **`std::strtol` 不检查全消费**

**⇒ `"16abc"` 会得到 16。**

**⇒ 与 §252 里 `std::stoul` 的问题同族。**

**⇒ 而 §243 与 §254 用的是 `from_chars` + `ptr == end`。**

**⇒ 所以这个文件里有三种解析方式。**

### 4.4 第二层：`atomic<long>` 计数

```php
static std::atomic<long> snapshotHexDumped{ 0 };
```

**⇒ 原子** —— 因为 `buildSnapshot` 可能从多个线程调用？**

**⚠ 但从 §265 的 `gameThreadId_` 检查看，快照构建应该在游戏线程。**

**⇒ 所以 `atomic` 可能是**过度保守**。**

**⇒ 或者是为了让 `OLMOD_SNAPSHOT_HEX` 的计数在调试时可以从其他线程读。**

### 4.5 第三层：`OLMOD_SNAPSHOT_HEX_OBITUARY`

```php
// AND A DUMP OF THE FIRST N FRAMES CANNOT SEE A KILL TWO MINUTES IN.
// OLMOD_SNAPSHOT_HEX_OBITUARY=1 spends the same budget on the frames
// that carry an EV_OBITUARY instead, which is what turns "the server
// says it archived one" into "these are the bytes the client was
// handed" -- Tools/demo-re decodes them offline.
static const bool snapshotHexObituaryOnly = [] {
    const char *const value = std::getenv("OLMOD_SNAPSHOT_HEX_OBITUARY");
    return value && value[0] && value[0] != '0';
}();
```

### 4.6 三层

```text
1. 只转储前 N 帧 ⇒ 看不到两分钟后的击杀
2. ⇒ `OLMOD_SNAPSHOT_HEX_OBITUARY=1` 把同样的预算花在【携带 EV_OBITUARY 的帧】上
3. ⇒ 这把"服务器说它归档了一个"变成"这些是客户端拿到的字节"
```

**⇒ 这是一个"按内容筛选取样"的设计** —— 而不是"按时间窗口"。

### 4.7 而 `value[0] != '0'`

**⇒ 所以 `"0"` 关，而任何其它非空值开（包括 `"off"`、`"no"`）。**

**⚠ 与第一个变量的"非正数 ⇒ 默认"**不同**。**

**⇒ 两个相邻的环境变量有不同的语义规则。**

### 4.8 第四层：**`EV_OBITUARY` 的内容判据**

```php
const auto data = message.data();
const auto frameCarriesObituary =
    !snapshotHexObituaryOnly ||
    std::ranges::any_of(frame.entities, [](const auto &entity) {
        return entity.eType == CodEntityTypeObituary;
    });
```

**⇒ 三项**

```text
未开 obituary 模式 ⇒ 任意帧
开了               ⇒ 只有含 EV_OBITUARY 的帧
```

**⇒ `CodEntityTypeObituary`** —— 与记忆里"`obituary (1700 + MOD)`"相关。

## 五、`SNAPHEX` 的**两阶段检查**

```php
if (snapshotHexLimit && frameCarriesObituary &&
    snapshotHexDumped.load(std::memory_order_relaxed) < snapshotHexLimit)
{
    const auto sequence = snapshotHexDumped.fetch_add(1, std::memory_order_relaxed);
    if (sequence < snapshotHexLimit)
    {
        ... 转储 ...
    }
}
```

### 5.1 两阶段

```text
① 检查当前计数 < 上限
② `fetch_add` 返回旧值，再检查
```

**⇒ 两阶段是因为 `fetch_add` 是无条件的。**

**⇒ 所以多个线程可能都通过 ① 但只有前 N 个通过 ②。**

**✓ 正确的原子模式。**

### 5.2 ⚠ **但 `fetch_add` 在 `sequence >= limit` 时也会增加计数**

**⇒ 所以计数会**超过** `limit`（由并发线程数决定）。**

**⇒ 而后面没有"减回"的操作。**

**⇒ 所以计数最终 > limit 是**正常**的。**

**⇒ 这不影响正确性（只是计数不准）。**

### 5.3 而 `sequence` 用于日志的 `seq=` ✓

## 六、`SNAPHEX` 日志的**八个字段**

```php
"SNAPHEX seq=" + sequence + " client=" + clientNum + " serverTime=" + frame.serverTime +
" delta=" + deltaMessageDistance + " baseline=" + (baseline?1:0) +
" init=" + (initializeBaselineCache?1:0) + " len=" + data.size() + " " + hex;
```

```text
seq           取样序号
client        客户端号
serverTime    服务端时间
delta         deltaMessageDistance
baseline      是否有基线
init          是否初始化基线缓存
len           字节数
hex           十六进制
```

**⇒ 七个字段 + hex。**

**⇒ 而 `baseline`/`delta`/`init` 三个正好是"影响 XOR 编码"的三个量** —— 所以这行日志**足够离线重放解码**。

**✓ 一个自给自足的 dump。**

## 七、`ServerCore` 的**五个参数**

```cpp
CodolGameServer::ServerCore Server(
    buildGameState,
    buildSnapshot,
    // 三个名字解析器
    [](modelName) { return Bindings.resolveModelConfigStringIndex(modelName); },
    [](weaponName) { return Bindings.resolveWeaponConfigStringIndex(weaponName); },
    [](aliasName) { return Bindings.resolveSoundAliasEventParameter(aliasName); });
```

### 7.1 两项 + 三个 lambda

```text
buildGameState          gamestate 写入器
buildSnapshot           快照写入器
modelName → 配置串索引
weaponName → 配置串索引
aliasName → 事件参数
```

### 7.2 **依赖注入的完整面**

**⇒ `ServerCore` 不直接依赖 `EngineBindings`** —— 只要五个可调用对象。

**⇒ 与 §242 里 `SV_PlaceCharacterItemsByRecordEntry` 的回调式注入同族。**

### 7.3 而三个 lambda 都是**薄包装**

**⇒ 它们只做 `Bindings.Xxx(...)`。**

**⇒ 所以这里的 lambda 是为了**签名匹配**（`ServerCore` 期望的自由函数）而不是逻辑。**

## 八、**八个"控制线程排队 → 游戏线程应用"**（本组第二重要）

### 8.1 八组队列

```cpp
std::mutex DedicatedControlMutex;
std::deque<std::string> DedicatedBookingCommands;                  // ① 预定命令串
std::deque<QueuedDedicatedSessionStart> DedicatedSessionStarts;    // ② 会话启动
std::deque<QueuedLoadoutUpdate> DedicatedLoadoutUpdates;           // ③ loadout 刷新
std::deque<std::uint16_t> DedicatedAnnouncerAuditions;             // ④ 播音员试听
std::deque<std::vector<std::uint8_t>> DedicatedRawCommands;        // ⑤ 原始命令
std::optional<DedicatedMapGenerationPreparation> DedicatedMapGeneration;  // ⑥ 地图代际
std::optional<PreparedClientLoadouts> PreparedLoadouts;            // ⑦ 预解析 loadout
CodolGameServer::SvPendingBooking PendingBooking;                  // ⑧ 待定预定
```

### 8.2 而三个不同的**锁**

```text
DedicatedControlMutex      ①②③④⑤ 共用？ 还是？
LoadoutMutex               ⑦
BookingMutex               ⑧
WorldAssetMutex            （未列出的第五个）
StartupMutex               （第四个）
```

**⇒ 从代码可见五个 `std::mutex`。**

**⇒ 所以并不是"一把大锁"。**

### 8.3 那句注释

```php
// Live loadout refreshes (§157c). Queued on the control thread, applied on
// the game thread in processDedicatedControlMessages so gameState_ and the
// registry are only touched from the frame loop.
```

**⇒ 三层**

```text
1. 控制线程排队
2. 游戏线程在 `processDedicatedControlMessages` 应用
3. ⇒ `gameState_` 与 registry 只在帧循环里被碰
```

### 8.4 而第二条注释

```php
// Announcer auditions (191n). Same shape and the same reason: queued on the
// control thread, sent on the game thread, because queueLocalSound writes
// into the client reliable rings the frame loop owns.
```

**⇒ "`queueLocalSound` 写进帧循环拥有的客户端可靠环"。**

**⇒ 与记忆里"Reliable command ring capacity 512 (`& 0x1FF`)"**相关**。**

**⇒ 所以"可靠环"是帧循环独占的。**

### 8.5 这是一个**单写者**架构

**⇒ 所有"碰引擎状态"的操作都在游戏线程。**

**⇒ 与 §266/§268 的 `gameThreadId_ != GetCurrentThreadId()` 检查一致。**

**⇒ 所以那些检查是**这个架构的执行者**。**

## 九、`PreparedSessionMember` 的**七个字段**

```cpp
struct PreparedSessionMember
{
    std::uint64_t xuid{};
    std::string username;
    std::uint32_t characterIndex{};
    ClientCharacterPresentation characterPresentation;
    std::map<std::string, ClientWeaponLoadout> loadouts;
    std::map<std::string, SvResolvedPerks> perks;
    std::map<std::string, DedicatedSession::EquipmentRequest> equipment;
    std::map<std::string, SvResolvedEquipment> offhands;
    std::optional<SvResolvedRewards> rewards;
};
```

### 9.1 **九个字段**（我数九）

```text
xuid
username
characterIndex
characterPresentation
loadouts        map<string, ...>    ← 【按 class 键】
perks            map<string, ...>
equipment        map<string, ...>
offhands         map<string, ...>
rewards          optional
```

### 9.2 而四个 `map<std::string, ...>` 的键

**⇒ 大概率是 `"custom1".."custom5"`** —— 与 §257 的 `selectedLoadout` 一致。

**⇒ 所以每个玩家按 class 名索引。**

### 9.3 而 `SvResolvedRewards` 是**单个** optional（不是 map）

**⇒ 因为连杀奖励读 `weaponClasses[0]`（§240）而**不按 class**。

**✓ 与 §240 的"不乘 class 偏移"一致。**

**⇒ 这是一个**结构层面的印证**。**

## 十、`LoadoutPreparationStatus` 的**四个字段**

```php
struct LoadoutPreparationStatus
{
    std::uint32_t attemptCount{};
    std::int32_t currentCharacter{-1};
    std::uint32_t resolvedClassMask{};
    std::uint32_t registeredClassMask{};
};
```

### 10.1 **两个 class 掩码**

```text
resolvedClassMask      解析出的
registeredClassMask    已注册的
```

**⇒ 两个不同的掩码** —— 所以"解析成功"与"注册成功"是两个阶段。

**⇒ 与 §241 的 `classMask` 与 §254 的 `result.bits`/`abilities.mask` 类似的双掩码模式。**

### 10.2 而 `currentCharacter{-1}` 用 -1 表示未知

**⇒ 与 §255 的 `lastCharacterIndexRefusal_ = -2` 不同（-1 vs -2）。**

## 十一、关键结论

1. **失败也计入耗时**，而 `timingStart` 包含 64 KB 分配与 hex 转储 ⇒ **hex 开启时计时被污染**。
2. **`codol_snapshot.py` 验证 11,136/11,136** —— 用自己的解码器作预言机。
3. **"用错基线 XOR 的值仍然框架正确 ⇒ 能干净解码 ⇒ 静默错"** —— `0xFFFFFF ^ 0xFFFFFF = 0` 的黑屏实例。
4. **这解释了为什么"与参照逐字节一致"可以是失败证据**（§253 的第二次应用）。
5. **`OLMOD_SNAPSHOT_HEX=0` 不等于关闭，而是"用默认 16"** —— 反直觉。
6. **`std::strtol` 不检查全消费**（与 §252 同族，而 §243/§254 用 `from_chars`）。
7. **`OLMOD_SNAPSHOT_HEX_OBITUARY` 用 `value[0] != '0'`** ⇒ `"off"` 也开 —— 与相邻变量规则不同。
8. **按内容筛选取样**（只 dump 含 `EV_OBITUARY` 的帧）。
9. **`fetch_add` 双阶段检查正确**，但计数会超 `limit`。
10. **SNAPHEX 的七个字段足够离线重放解码**（含 `baseline`/`delta`/`init`）。
11. **`ServerCore` 通过五个可调用对象注入**，不直接依赖 `EngineBindings`。
12. **八个"控制线程排队 → 游戏线程应用"的队列**，五把锁。
13. **`queueLocalSound` 写进"帧循环拥有的客户端可靠环"**。
14. **`PreparedSessionMember` 的四个 map 按 class 键，而 `rewards` 是单个 optional** —— 印证 §240 的"连杀不按 class"。
15. **两个 class 掩码**（`resolvedClassMask` 与 `registeredClassMask`）。

## 十二、未闭合点

- `OLMOD_SNAPSHOT_HEX=0` 的语义是否有意。
- 四个 `map<string, ...>` 的键是否真是 `custom1..5`。
- `DedicatedControlMutex` 保护哪几个队列。
- `Appmain.cpp` 380 行之后未读取。
