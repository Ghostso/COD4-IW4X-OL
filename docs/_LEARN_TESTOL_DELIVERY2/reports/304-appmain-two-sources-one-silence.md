# 304 · **看门狗只在第 6 阶段报**、**"两个来源，一个沉默"**、`DuplicateHandle` 的三权限

## 一、范围

本报告学习 `Appmain.cpp` 7420–7640 行。

## 二、`markFramePhase` 的**两项**

```cpp
void markFramePhase(const std::uint32_t phase)
{
    FramePhase.store(phase, std::memory_order_release);
    FrameTick.fetch_add(1, std::memory_order_acq_rel);
}
```

**⇒ 一个 `release` 存 + 一个 `acq_rel` 加。**

### 2.1 而 `acq_rel` 在 `fetch_add` 上是**正确的**

**⇒ 因为它同时读与写。**

**✓ 而 `store(release)` 保证"阶段值先于 tick 可见"。**

## 三、**看门狗的五个条件**（本组最重要的一段）

```cpp
void startFrameWatchdog()
{
    if (FrameWatchdogRunning.exchange(true)) return;
    std::thread([] {
        std::uint64_t lastTick = 0;
        std::uint32_t stalledFor = 0;
        bool reported = false;
        for (;;)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            const auto tick = FrameTick.load(acquire);
            if (tick != lastTick)
            {
                lastTick = tick;
                stalledFor = 0;
                reported = false;                 // ← 【重置】
                continue;
            }
            if (!tick) continue;                  // ① 帧线程从未跑过 ⇒ 不是停顿
            stalledFor += 100;
            if (stalledFor < 300 || reported ||
                FramePhase.load(acquire) != 6)     // ②③④
                continue;
            reported = true;
            logGameServer("FRAME THREAD STALLED for " + stalledFor + "ms in phase=" +
                framePhaseName(FramePhase.load(acquire)) + " tick=" + tick + " " +
                describeFrameThreadStall());
        }
    }).detach();
}
```

### 3.1 五个条件

```text
① tick != 0        帧线程至少跑过一次
② stalledFor >= 300  至少 300 ms
③ !reported          本次停顿还没报过
④ FramePhase == 6    【只在第 6 阶段报】
```

**⇒ 四个条件（我数四）。**

### 3.2 ⚠ **只在第 6 阶段报**

```cpp
FramePhase.load(acquire) != 6
```

**⇒ 所以第 0–5、7、8 阶段的停顿**不会报**。**

**⚠ 这是一个**窄化** —— 因为 §303 说"专用服的帧线程在 gamestate 配置后几秒停止"，而那在第 6 阶段（`Server.onComFrame`）。**

**⇒ 所以这是**针对那个具体问题**的窄化。**

**⇒ 但它会**漏掉**其它阶段的停顿。**

**⚠ 值得指出 —— 与 §303 的"九个阶段"的通用设计**不一致**。**

### 3.3 而 `reported` 在 `tick != lastTick` 时**重置**

**⇒ 所以"帧恢复后再停"会**再报一次**。**

**✓ 与 §303 的"一次每次停顿"一致（`reported` 是"本次停顿"的一次性标志）。**

### 3.4 而 `stalledFor += 100` 的**累积**

**⇒ 所以 `stalledFor` 是"连续无 tick 的毫秒数"。**

### 3.5 而 `sleep_for(100ms)` 的**粒度**

**⇒ 所以报出的时间粒度是 100 ms。**

**⚠ 而 Windows 的 `sleep_for` 精度约 15-16 ms ⇒ 所以实际可能是 100-116 ms。**

**⇒ 累积误差会漂移。**

## 四、`DuplicateHandle` 的**三个权限**

```cpp
if (!FrameThreadHandle.load(acquire))
{
    HANDLE duplicate{};
    if (DuplicateHandle(
            GetCurrentProcess(), GetCurrentThread(),
            GetCurrentProcess(), &duplicate,
            THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION,
            FALSE, 0))
    {
        HANDLE expected{};
        if (!FrameThreadHandle.compare_exchange_strong(expected, duplicate))
            CloseHandle(duplicate);           // ← 【CAS 失败则关掉】
    }
}
```

### 4.1 三个权限

```text
THREAD_SUSPEND_RESUME        挂起/恢复
THREAD_GET_CONTEXT           读上下文
THREAD_QUERY_INFORMATION     查询
```

### 4.2 而**三个权限正好对应 §303 的三个操作**

```text
SuspendThread / ResumeThread  ⇒ THREAD_SUSPEND_RESUME
GetThreadContext              ⇒ THREAD_GET_CONTEXT
（ReadProcessMemory 不需要线程权限，只需进程 VM_READ）
```

**✓ 最小权限。**

### 4.3 而 `compare_exchange_strong` 的**双检**

**⇒ 两层**：

```text
① 外层 `if (!FrameThreadHandle.load())`
② 内层 CAS
```

**⇒ 所以并发的两个 `onServerFrame` 只有一个成功（另一个关掉自己的句柄）。**

**✓ 正确的双重检查锁定。**

**⚠ 但 `onServerFrame` 只在帧线程上跑 ⇒ 所以并发**不可能**。**

**⇒ 所以这是一个**过度防御**。**

**⇒ 也可能因为 `markFramePhase` 之外还调用了 `onServerFrame`。**

## 五、`onServerFrame` 的**八段**（本组第二重要）

```cpp
void onServerFrame(uint32 nowMilliseconds)
{
    // ① 开句柄 + 启动看门狗
    ...DuplicatedHandle...; startFrameWatchdog();
    markFramePhase(1);
    if (!Bindings.observeGameThread()) return;

    // ② 客户端专用路径
    markFramePhase(2);
    Bindings.auditXModelSurfaces();
    const auto alphaWeaponPortStatus = Bindings.installAlphaWeaponPorts();
    Bindings.auditAlphaWeaponModelPointers();
    ...status log...
    const auto role = OlMod::processRole();
    if (role != ProcessRole::Dedicated)
    {
        ...SetThreadExecutionState / rawInput / maintainClientGametypeDvarCache /
           ensureClientSessionBridge / process(...)...
    }
    if (!OlMod::runsGameServer(role)) return;

    // ③ 专用服控制
    markFramePhase(3);
    ensureDedicatedControlServer();
    processDedicatedControlMessages();

    // ④ loadout 刷新
    markFramePhase(4);
    ...
}
```

### 5.1 而阶段 1 与 2 之间的**分流**

```text
markFramePhase(1)              entry
observeGameThread()            【可能 return】
markFramePhase(2)              role_and_client_patches
（客户端路径）
runsGameServer(role)           【可能 return】
markFramePhase(3)              dedicated_control
```

**⚠ 所以 `markFramePhase(2)` 在**客户端与专用服都跑**。**

**⇒ 而 §303 的名字是 `role_and_client_patches` ⇒ 所以它覆盖两者。**

**✓ 名字准确。**

### 5.2 ⚠ **两条 `return` 路径不更新阶段**

```cpp
if (!Bindings.observeGameThread()) return;    // ← 阶段停在 1
...
if (!OlMod::runsGameServer(role)) return;      // ← 阶段停在 2
```

**⇒ 所以一个**正常结束**的客户端帧会让 `FramePhase` 停在 2。**

**⚠ 而看门狗只在第 6 阶段报 ⇒ 所以客户端永远不会触发。**

**✓ 但这也意味着"阶段 2 的停顿无法被发现"。**

## 六、**"两个来源，一个沉默"**（本组最重要的一段）

### 6.1 那段完整论证

```php
const auto loadout = Bindings.captureClientLoadoutRequest();
const auto selection = Bindings.readClientBookingSelection();
// TWO SOURCES, ONE SILENCE. Returning nullopt here makes the
// bridge time out, and configure-session reports status=3 with a
// stock explanation -- "the client has no loadout to report yet,
// capture AFTER it has picked a class". That explanation has now
// been wrong twice: the capture still times out with a class
// picked and the player standing in the map. It cannot say which
// of the two reads came back empty, and they fail for completely
// different reasons -- the loadout needs the client character
// resolver (unported on OLfinal, section 16a), while the booking
// selection needs the client to still be holding a lobby booking,
// which it may well drop once the match starts.
// THE LOADOUT IS THE HALF THAT MATTERS. The booking selection
// is reported when the client is holding one and left empty when
// it is not -- a client at the menu has a perfectly good loadout
// and no booking, and refusing both because of the second is why
// this reported nothing for so long. configure-session takes the
// map and gametype from its own arguments anyway.
```

### 6.2 七层

```text
1. **两个来源，一个沉默**
2. 返回 nullopt ⇒ 桥超时 ⇒ configure-session 报 `status=3` 配一个**套话解释**
3. 套话："客户端还没有 loadout 可报，**挑完职业之后再捕获**"
4. ⇒ **那个解释已经被错了两次**：挑完职业、玩家站在图里，捕获**仍然超时**
5. ⇒ 它**不能说出两个读里哪个空了**，而它们**因为完全不同的原因失败**：
     · loadout 需要**客户端角色解析器**（在 OLfinal 上未移植，§16a）
     · booking selection 需要客户端**仍然持有大厅预定**，而它**在比赛开始后很可能丢掉**
6. ⇒ **loadout 是重要的那一半**
7. ⇒ booking selection **有就报、没有就留空**
```

### 6.3 而"一个在菜单的客户端有一个完全好的 loadout 而没有 booking"

**⇒ 三层**：

```text
1. 菜单客户端：loadout 好、booking 无
2. ⇒ 因为第二个而拒绝两个 ⇒ **这就是为什么它这么久什么都没报**
3. ⇒ configure-session 反正从**自己的参数**取 map 与 gametype
```

**✅ 一个完整的"过度严格导致完全不工作"的因果链。**

### 6.4 实现

```cpp
const auto haveSelection = selection && selection->rotationIndex >= 0;    // ①
if (!loadout)
{
    static std::string LastCaptureRefusal;
    auto why = std::string("client capture empty:") +
        (loadout ? "" : " NO_LOADOUT") +
        (selection ? "" : " NO_BOOKING_SELECTION") +
        (selection && selection->rotationIndex < 0 ? " ROTATION_INDEX_NEGATIVE" : "");
    if (loadout) { why += " characterIndex=" + ... + " classMask=" + ...; }
    if (why != LastCaptureRefusal) { logGameServer(why); LastCaptureRefusal = why; }
    return optional<ClientSessionCapture>{};
}
BookingSelection booking{};
if (haveSelection)
{
    booking = { .playlistId = selection->playlistSlot,
                .rotationIndex = (uint32)selection->rotationIndex,
                .mapName = selection->mapName,
                .gameType = selection->gameType };
}
return optional{ClientSessionCapture{ .booking = booking, .loadout = *loadout }};
```

### 6.5 而 `why` 的**三个标记**

```text
NO_LOADOUT
NO_BOOKING_SELECTION
ROTATION_INDEX_NEGATIVE
```

**⇒ 三项。**

### 6.6 ⚠ **而 `(loadout ? "" : " NO_LOADOUT")` 恒为真**

**⇒ 因为在 `if (!loadout)` 分支里 ⇒ **`loadout` 必然为假**。**

**⇒ 所以 `why` **总是**含 `NO_LOADOUT`。**

**⇒ 而 `if (loadout) { why += ... }` 是**死代码**。**

**⚠ 一处已失效的代码** —— 因为重构后 `if (!loadout)` 让这两个分支不可能。**

**⇒ 与 §235 的"注释滞后"同族。**

### 6.7 而 `haveSelection` 与 `booking = {}`

**⇒ 所以"无 booking"⇒ 空的 `BookingSelection{}`。**

**⇒ 与 §280 的"用客户端自己 booked 的 gametype"**配合** —— 空的则 configure-session 用自己的参数。**

### 6.8 而四个**变更触发**的日志

```cpp
static std::string LastRosterReport;
static std::string LastCharacterInfoReport;
static std::string LastSlotReport;
static std::string LastCaptureRefusal;
```

**⇒ 四个静态字符串 —— 都是"变化才打印"。**

**✓ 与 §276 的"整元组去重"同族（第五次"变化触发"）。**

### 6.9 而 `reportProfileCharacterSlots` 的**空返回**

```cpp
auto slotReport = Bindings.reportProfileCharacterSlots();
if (!slotReport.empty() && slotReport != LastSlotReport) { ... }
```

**⇒ 空返回 ⇒ **不打印**。**

**⇒ 因为 §255 的 `profileSlotProbeEnabled()` 默认关 ⇒ 返回空。**

**✓ 所以探针关闭时静默。**

## 七、`"client-side "` 前缀

```cpp
logGameServer("client-side " + rosterReport);
logGameServer("client-side " + slotReport);
```

**⇒ 与 §255 的"日志携带 `session member roster`（专用服）与 `client-side session member roster`（客户端）"一致** ✓

**⇒ 而 `reportClientCharacterInfo` 没有前缀（因为它自带 `client characterInfo: pid=`）。**

**⚠ 一处不一致。**

## 八、"这个探针在客户端进程里跑，而那正是要点"

```php
// OLMOD(section-48-input-probe): THIS RUNS IN THE CLIENT PROCESS, and
// that is the whole point. The first version of this probe fired on
// the session-start path, which is the DEDICATED process, and
// reported count=0 -- true, and useless, because the dedicated
// out.exe never joins a lobby room. The roster and the public profile
// both live over here.
```

**⇒ 五层**：

```text
1. **这在客户端进程里跑，而那正是要点**
2. 第一版在**会话启动路径**上触发，那是**专用服进程**
3. ⇒ 报 `count=0` —— **真的，但无用**
4. 因为**专用服的 out.exe 从不加入大厅房间**
5. ⇒ **名册与公共 profile 都在这边**
```

**✅ 与 §243 的"686 对照"、§255 的"探针在错误进程"**同族**（第二次）。**

## 九、`SetThreadExecutionState(ES_DISPLAY_REQUIRED)`

```cpp
if (ClientProcessPatch && (Patched || AlreadyPatched))
{
    SetThreadExecutionState(ES_DISPLAY_REQUIRED);
}
```

**⇒ 只有客户端补丁成功后**才阻止显示休眠**。**

**⇒ 因为一个休眠的显示屏在客户端上是可观测的（用户在看）。**

**⚠ 每帧调用 —— 但如果状态已设，成本极小。**

**⇒ 而 `ES_DISPLAY_REQUIRED` 是"保持显示"而不是"保持系统唤醒"。**

## 十、关键结论

1. **`markFramePhase` 用 `store(release)` + `fetch_add(acq_rel)`** 正确。
2. **看门狗只在第 6 阶段报** —— 针对"gamestate 配置后停止"的窄化，但**会漏掉其它阶段**。
3. **`reported` 在 tick 变化时重置** ⇒ "再停再报"。
4. **`sleep_for(100ms)` 的实际精度约 15-16 ms** ⇒ 累积漂移。
5. **`DuplicateHandle` 的三个权限**正好对应三个操作（最小权限）。
6. **双检 + CAS 是过度防御**（因为 `onServerFrame` 只在帧线程上跑）。
7. **两条 `return` 路径不更新阶段** ⇒ 正常的客户端帧让阶段停在 2。
8. **"两个来源，一个沉默"** —— 套话解释"挑完职业再捕获"**已经错过两次**。
9. **两个读失败的原因完全不同**（角色解析器未移植 vs 大厅预定丢失）。
10. **"loadout 是重要的那一半"** —— 所以 booking 有就报没有就留空。
11. **"因为第二个而拒绝两个 ⇒ 这就是为什么它这么久什么都没报"** —— 过度严格导致完全不工作。
12. **⚠ `(loadout ? "" : " NO_LOADOUT")` 与 `if (loadout)` 在 `if (!loadout)` 分支里是死代码**。
13. **`why` 总有 `NO_LOADOUT` 而另两个标记有条件**。
14. **四个"变化才打印"的静态字符串**（第五次）。
15. **`reportProfileCharacterSlots` 空返回 ⇒ 不打印**（探针默认关）。
16. **`"client-side "` 前缀只有两处** —— 第三处（`reportClientCharacterInfo`）自带前缀，不一致。
17. **"这在客户端进程里跑，而那正是要点"** —— 第一版在专用服上跑，报 `count=0` 真的但无用。
18. **`SetThreadExecutionState(ES_DISPLAY_REQUIRED)` 只在补丁成功后**。

## 十一、未闭合点

- `onServerFrame` 是否可能从多个线程调用（决定 CAS 是否多余）。
- `why` 的死代码是否已知。
- `ES_DISPLAY_REQUIRED` 每帧调用的实际开销。
- `Appmain.cpp` 7640 行之后未读取。
