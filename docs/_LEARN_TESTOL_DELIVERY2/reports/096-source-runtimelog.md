# 学习报告 096（重开）— `shared\RuntimeLog`（398 行）：一份带精确测量的性能修复史

**学习范围**：`RuntimeLog.hpp`（2,018 B / 49 行）+ `RuntimeLog.cpp`（18,359 B / 426 行）
**性质**：全实测（**两文件逐行读完**）
**★★★★★ 本报告收录六段带精确测量数据的性能修复史**（132/135 µs · 67 MB/h · 89% 四族 · QuickEdit 阻塞 · FRAME THREAD STALLED）

---

## 一、★★★★★ 五级日志分层（甲方 2026-10-14 令）

### 1.1 ★★★ 完整定义（`RuntimeLog.hpp:25-48`，逐字）

```cpp
/// 日志分级（2026-10-14 甲方令：「日志分层：ERR INFO DEBUG等，方便定位和快速分类阅读」）。
///
/// 每行在 `[角色/通道]` 之后带一个**固定三字母标签** ⇒ 分类就是一条 grep：
///     `[ERR]` 错误/拒绝/失败/异常      —— 最高优先级，任何级别下都不过滤掉
///     `[WRN]` 警告/降级/丢包/超时/卡顿
///     `[INF]` 正常状态与结论（**默认级别**）
///     `[DBG]` 逐帧/逐命令/逐实体诊断（默认关）
///     `[TRC]` 更细的追踪（默认关）
///
/// 过滤：`OLMOD_LOG_LEVEL=err|warn|info|debug|trace`（默认 `info`）。
/// 兼容：`OLMOD_VERBOSE_LOG=1` 等价 `debug`，既有 `verbose()` 即 `levelEnabled(Debug)`。
enum class Level : std::uint8_t
{
    Error = 0,
    Warn  = 1,
    Info  = 2,
    Debug = 3,
    Trace = 4,
};
```

★★★ **⇒ 五级,数值**越小越重要**（`Error = 0`）。**

### ★★★★★ 完整的行格式（第 164–175 行）

```cpp
line.append(stamp.data());            // [YYYY-MM-DD HH:MM:SS] 
line.push_back('[');
line.append(roleName(processRole()));  // client / dedicated / combined
line.push_back('/');
line.append(channelName(channel));     // backend / game-server
line.append("] ");
line.append(tag);                      // [ERR] / [WRN] / [INF] / [DBG] / [TRC]
line.append(message);
line.append("\r\n");
```

### ★★★★★ 实测的日志行格式

```
[2026-10-25 13:12:49] [dedicated/game-server] [ERR] <message>\r\n
        ↓
★ 三部分：**时间戳** + **[角色/通道]** + **[级别标签]** + 消息
```

### ★★★ 六个角色/通道组合

| `roleName()` | `channelName()` |
|---|---|
| **`client`** | **`backend`** |
| **`dedicated`** | **`game-server`** |
| **`combined`** | — |

★★ **⇒ 与报告 095 的 `ProcessRole` 三值完全对应。**

### ★★★★★ 自动分级的关键词表（第 327–335 行，完整）

```cpp
constexpr std::string_view errorWords[] = {
    "refused", "failed", "failure", "fatal", "error", "ERROR",
    "denied", "invalid", "mismatch", "rejected", "unavailable",
    "no_free_slot", "cannot", "unable", "corrupt", "assert",
};                                            // ★ 16 个

constexpr std::string_view warnWords[] = {
    "warn", "WARN", "timeout", "timed out", "dropped", "stall",
    "STALL", "retry", "fallback", "skipped", "missing", "delay",
};                                            // ★ 12 个
```

★★★ **⇒ 28 个关键词（16 ERR + 12 WRN）。**

★★ **⇒ 设计原则（逐字）："关键词表**刻意短且向'严重'倾斜**（**误判成 ERR 比漏判安全**）"。**

### ★★★★★ `zeroValued`：一个实测误判的修复（第 304–321 行，逐字）

```cpp
/// 计数型关键词的 **0 值不算异常**：`pmove-trace calls=834000 hits=482678 failed=0` 曾被自动分级标成 `[ERR]`
/// （因为消息里出现了 `failed`），`dropped=0` 同理。判据是"关键词后紧跟 `0` 且再往后不是数字"。
```

★★★★★ **⇒ 一条带实测数据的教训：**
```
**`pmove-trace calls=834000 hits=482678 failed=0`**
        ↓
★★★ 曾被自动分级标成 **`[ERR]`**（因为消息里出现了 `failed`）
        ↓
★★★ 修复：**`failed=0` / `dropped=0` 不算异常**（V1.203 ⑥）
   ⇒ 判据："关键词后紧跟 `0` 且**再往后不是数字**"
   ⇒ 即 `failed=0` 是零,但 `failed=01` 或 `failed=0x` 不是
```

★ **⇒ 这是**"零值不是错误"的精确实现**（且 `834000`/`482678` 是真实计数）。**

---

## 二、★★★★★ **五段带精确测量的性能修复史**

### 2.1 ★★★★★ 修复 1：每行 open+close ⇒ 每通道一个常开句柄

```cpp
// ONE OPEN HANDLE PER CHANNEL, INSTEAD OF AN open+close PER LINE.
//
// What was here before: a named mutex, std::filesystem::create_directories, and an
// std::ofstream constructed and destroyed for EVERY line -- **132 us of the 135 us a line cost**,
// measured, and **180 lines a second**. The average was survivable. The tail was not: reopening a
// **224 MB** file that often, from **three processes**, is the shape of the
// **2-to-6 second frame stalls** that showed up in think, begin and end indiscriminately,
// which is to say **not in any one of them**.
```

### ★★★★★ 五个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | ★★★ 每行成本 | **135 µs**（其中 **132 µs** 是 open+close） |
| **2** | 日志速率 | **180 行/秒** |
| **3** | 日志文件大小 | **224 MB** |
| **4** | 写日志的进程数 | ★★ **三个** |
| **5** | ★★★ 卡顿时长 | **2–6 秒的帧卡顿** |

★★★ **⇒ 第 1 条的算式：**132 / 135 = **97.8%** 的成本花在 open+close 上。****

★★★ **⇒ 第 5 条的现象学（逐字）："showed up in think, begin and end **indiscriminately**,
which is to say **not in any one of them**" ⇒ 卡顿**不归属于任何单一阶段** ⇒ 典型的**共享资源争用**。**

### 2.2 ★★★★★ 修复 2：命名互斥量的**错误**（第 34–38 行，逐字）

```cpp
// The named mutex it replaces was keyed by GetCurrentProcessId(), so each process took its
// OWN mutex and it never excluded anything -- the client and the dedicated both write this
// same file. FILE_APPEND_DATA is what actually makes that safe: a handle opened with append
// access and no FILE_WRITE_DATA gets **atomic appends from the filesystem, across processes,
// with no lock of ours involved**. The std::mutex below is only for our own threads.
```

★★★★★ **⇒ 一个经典的**命名互斥量误用**：**
```
命名互斥量的名字里含 **`GetCurrentProcessId()`**
        ↓
★★★ ⇒ 每个进程拿到的是**自己的互斥量** ⇒ **从未排除任何东西**
   （而客户端与专服**写同一个文件**）
        ↓
★★★★★ 修复：靠 **`FILE_APPEND_DATA`**（不带 `FILE_WRITE_DATA`）
   ⇒ **文件系统层面保证跨进程原子追加** ⇒ **不需要我们的锁**
   ⇒ `std::mutex` 只用于**本进程的线程**
```

★ **⇒ 这是一个**"锁的名字里含 PID ⇒ 锁失效"的精确陷阱**（值得单独记住）。**

### 2.3 ★★★ 修复 3：无用户态缓冲 ⇒ 崩溃后仍存活

```cpp
// Nothing is buffered in user space, so a line that WriteFile returned from survives a crash
// of this process -- the old ofstream buffered, which is worse for exactly the case these
// logs exist to diagnose.
```

★★ **⇒ "日志存在的目的就是诊断崩溃" ⇒ 所以**不能缓冲**（缓冲会在崩溃时丢最后几行）。**

### 2.4 ★★★★★ 修复 4：**四族逐帧日志占 89% 字节**

```cpp
// OLMOD(log-tick-gate): THE PER-TICK FAMILIES LEAVE AT THE SINK, NOT AT 40 CALL SITES.
//
// Measured on the live dedicated server **2026-10-12 12:26:32..12:33:42** (**430 s** window,
// **8 MB** tail): the log grew **67 MB/hour**, i.e. **1.6 GB/day**, and FOUR families of
// per-client lines were **89%** of those bytes --
//     **player-kinematics 31.3%** (one line per client per second, ADSR-capped),
//     **dead-body         25.6%** (emitted "every frame it is dead", by its own comment),
//     **weapon-movement   19.3%** (one line per client per second),
//     **player-entity     12.8%** (one line per client per second).
// A filled **12-slot** match therefore writes **~46 lines a second** for a whole round, and
// the file it writes into is already **a quarter of a gigabyte**.
```

### ★★★★★ 完整的测量数据表

| # | 项 | 值 |
|---|---|---|
| **1** | 测量窗口 | **2026-10-12 12:26:32 – 12:33:42**（**430 秒**） |
| **2** | 样本 | **8 MB** 尾部 |
| **3** | 增长速度 | ★★★ **67 MB/小时 = 1.6 GB/天** |
| **4** | ★★★ **四族占比** | **89%** |
| **5** | `player-kinematics` | **31.3%**（每客户端每秒 1 行,ADSR 限流） |
| **6** | `dead-body` | **25.6%**（"every frame it is dead"） |
| **7** | `weapon-movement` | **19.3%**（每客户端每秒 1 行） |
| **8** | `player-entity` | **12.8%**（每客户端每秒 1 行） |
| **9** | 满员比赛 | **12 槽** ⇒ **约 46 行/秒**（整回合） |
| **10** | 文件大小 | **四分之一 GB**（约 250 MB） |

★★★ **⇒ 四族占比之和：31.3 + 25.6 + 19.3 + 12.8 = **89.0%** ✓ 精确自洽。**

### ★★★★★ "故意不列入"的清单（第 80–84 行，逐字）

```cpp
// WHAT IS DELIBERATELY NOT LISTED: anything that reports a state change, a refusal or
// a stall is evidence and stays unconditional -- **FRAMESTALL, FRAME THREAD STALLED,
// LOGSTALL, BOTTRACE|fill-target, BOTTRACE|routing-vertical, BOTTRACE|create-refused,
// pmove-trace, CLIENTTHINK**, the runtime/runtime-perf/frame summaries and every error.
// The list below is the four families the measurement named, and nothing else.
```

★★★ **⇒ 七个被明确保留的无条件日志标签：**
```
**`FRAMESTALL`** / **`FRAME THREAD STALLED`** / **`LOGSTALL`**
**`BOTTRACE|fill-target`** / **`BOTTRACE|routing-vertical`** / **`BOTTRACE|create-refused`**
**`pmove-trace`** / **`CLIENTTHINK`**
（★ 实际是 8 个）
        ↓
★★★ 原则（逐字）："anything that reports a **state change, a refusal or a stall**
   is **evidence** and **stays unconditional**"
```

### 2.5 ★★★★★ 修复 5：**QuickEdit 会让点击停止游戏**

```cpp
// TURN QUICKEDIT OFF, OR A CLICK IN THIS WINDOW STOPS THE GAME.
//
// QuickEdit is on by default. Clicking in the window enters selection mode, and every
// WriteFile to the console then **BLOCKS until the selection is dismissed** -- including the
// ones this function's caller makes from the frame thread. Measured as
// **FRAME THREAD STALLED for seconds at a time**, appearing in whichever frame phase happened
// to log when the click landed, and healing on its own the moment the window was dismissed.
// **A server must not be stoppable by a mouse.**
```

★★★★★ **⇒ 一个极其具体的 Windows 陷阱：**
```
控制台默认开 **QuickEdit**
        ↓
★★★ 在窗口里点一下 ⇒ 进入**选择模式**
   ⇒ **每次 WriteFile 到控制台都会 BLOCK** 直到取消选择
   ⇒ ★★★ 包括**帧线程**的写入
        ↓
★★★ 实测现象：**FRAME THREAD STALLED 持续数秒**
   且出现在"**恰好点击时正在写日志的那个帧阶段**"
   取消选择后**自行痊愈**
        ↓
★★★★★ 结论（逐字）："**A server must not be stoppable by a mouse.**"
```

★★ **⇒ 修复（第 215–230 行）：**
```cpp
constexpr DWORD QuickEdit = 0x0040;   // ENABLE_QUICK_EDIT_MODE
constexpr DWORD Extended = 0x0080;    // ENABLE_EXTENDED_FLAGS, required to apply it
SetConsoleMode(input, (mode & ~QuickEdit) | Extended);
```

★★ **⇒ 两个精确的常量：`0x0040`（QuickEdit）/ `0x0080`（Extended,必须同时设）。**

### 2.6 ★★★ 修复 6：`OutputDebugStringA` 只在有调试器时调用

```cpp
// Only when somebody is listening. With no debugger attached this still takes a global
// system lock and walks the DBWIN buffer, and it was unconditional.
if (IsDebuggerPresent())
    OutputDebugStringA(line.c_str());
```

★★ **⇒ `OutputDebugStringA` 在**无调试器时仍取全局系统锁并遍历 DBWIN 缓冲区** ⇒ 所以必须门控。**

### 2.7 ★★★ 修复 7：环境变量只读一次

```cpp
// Read the environment ONCE. This was a GetEnvironmentVariableA per line, and the answer
// cannot change inside a process.
static const bool console = consoleEnabled();
```

★★ **⇒ `static const` 缓存 ⇒ 每行不再调 `GetEnvironmentVariableA`。**

### 2.8 ★★★★★ `LOGSTALL` 自诊断（第 407–424 行）

```cpp
static Clock::time_point lastStall{}; // guarded by LogMutex
if (done-began >= std::chrono::milliseconds(20) &&
    done-lastStall >= std::chrono::seconds(1) && file != INVALID_HANDLE_VALUE)
{
    lastStall = done;
    const auto us = [](auto a, auto b) {
        return std::chrono::duration_cast<std::chrono::microseconds>(b-a).count();
    };
    // File-only and nonrecursive: never diagnose a blocked console by
    // writing the diagnostic back into that same console.
    const auto diagnostic = formatLine(channel, Level::Warn, "LOGSTALL lockUs=" +
        std::to_string(us(began, locked)) + " fileUs=" + std::to_string(us(locked, filed)) +
        " consoleDebugUs=" + std::to_string(us(filed, done)) +
        " prefix=" + std::string(message.substr(0, 96)));
    WriteFile(file, diagnostic.data(), ...);
}
```

★★★★★ **⇒ 三个精确设计：**
```
① **触发阈值**：单行 ≥ **20 ms**,且距上次 ≥ **1 秒**（避免刷屏）
② ★★★ **三段计时**：`lockUs`（取锁）+ `fileUs`（写文件）+ `consoleDebugUs`（控制台+调试器）
③ ★★★★★ **只写文件,不递归**："never diagnose a blocked console by
   **writing the diagnostic back into that same console**"
        ↓
★★★ ⇒ 第 ③ 条是**防止自死锁**的关键（若控制台被 QuickEdit 阻塞,再往控制台写就永远卡住）
```

★ **⇒ 且 `prefix=` 只取**前 96 字节**（截断,避免诊断本身过长）。**

---

## 三、★★★★★ **日志文件路径**

```cpp
const auto fileName = channel == Channel::Backend
    ? L"**AlwaysofflineRe.Localnet32.log**"
    : L"**CodolGameServer.log**";
return executableDirectory() / L"Ayria" / L"Logs" / fileName;
```

★★★ **⇒ 两个精确的日志路径：**
```
<exe目录>\Ayria\Logs\**AlwaysofflineRe.Localnet32.log**   （backend 通道）
<exe目录>\Ayria\Logs\**CodolGameServer.log**              （game-server 通道）
        ↓
★★★ 注意：backend 的日志名用的是 **`AlwaysofflineRe.Localnet32`**
   ⇒ ★ 与交付包里的 **`Alwaysoffline.Localnet32`**（**无 `Re`**）不同！
```

★★ **⇒ 这印证了既有 memory 的"`Re` 后缀 = Reimplementation"：**
```
交付包里的二进制：**`Alwaysoffline.Localnet32`**（无 Re）
日志文件名：      **`AlwaysofflineRe.Localnet32.log`**（有 Re）
        ↓
★★★ ⇒ 说明**源码内部的模块名是 `AlwaysofflineRe`**
   ⇒ 而**发布的二进制名去掉了 `Re`**
        ↓
★ 与报告 090 的 RTTI 吻合：`@AlwaysofflineRe@@`（**182 条**）
   ⇒ ★★ **命名空间是 `AlwaysofflineRe`**,而导出文件名是 `Alwaysoffline`
```

### ★★★ 控制台标题（第 196–201 行）

```cpp
SetConsoleTitleW(role == ProcessRole::Dedicated
    ? L"**CODOL Dedicated Server**"
    : role == ProcessRole::Client
        ? L"**CODOL Client / Backend**"
        : L"**CODOL Combined Runtime**");
```

★★ **⇒ 三个窗口标题,与 `ProcessRole` 三值对应。**

---

## 四、★★★★ `OLMOD_LOG_LEVEL` 的解析（第 260–285 行）

```cpp
static const Level threshold = [] {
    // 读 OLMOD_LOG_LEVEL
    if (normalized == "err"  || normalized == "error")   return Level::Error;
    if (normalized == "warn" || normalized == "warning") return Level::Warn;
    if (normalized == "debug"|| normalized == "dbg")     return Level::Debug;
    if (normalized == "trace"|| normalized == "trc")     return Level::Trace;
    if (normalized == "info" || normalized == "inf")     return Level::Info;
    // 兼容旧开关：OLMOD_VERBOSE_LOG=1 ⇒ debug
    return verboseLegacy() ? Level::Debug : Level::Info;
}();
return static_cast<std::uint8_t>(level) <= static_cast<std::uint8_t>(threshold);
```

★★★ **⇒ 10 个可接受的值（每级 2 个拼写）+ 1 个兼容回退。**

★★ **⇒ 判定是 **`level <= threshold`**（数值越小越重要）。**

### ★★★ 两个日志环境变量

| 变量 | 值 | 默认 |
|---|---|---|
| **`OLMOD_LOG_LEVEL`** | `err`/`warn`/`info`/`debug`/`trace`（各 2 种拼写） | ★ **`info`** |
| **`OLMOD_VERBOSE_LOG`** | `1`/`true`/`yes`/`on` | ★★ **等价 `debug`** |
| **`OLMOD_CONSOLE_LOG`** | `1`/`true`/`yes`/`on` | 关 |

★★ **⇒ 布尔变量接受 **4 种**写法（`1`/`true`/`yes`/`on`）,且**不区分大小写**。**

★★ **⇒ `OLMOD_*` 累计已达 **13 个**（本报告新增 3 个）。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ **五级日志** | **`Error=0` / `Warn=1` / `Info=2` / `Debug=3` / `Trace=4`**（数值越小越重要） |
| 2 | ★★★ **行格式** | `[YYYY-MM-DD HH:MM:SS] [角色/通道] [级别标签] 消息\r\n` |
| 3 | ★★ 角色/通道 | `client`/`backend` · `dedicated`/`game-server` · `combined` |
| 4 | ★★★ **16 个 ERR 关键词** | `refused` `failed` `failure` `fatal` `error` `ERROR` `denied` `invalid` `mismatch` `rejected` `unavailable` `no_free_slot` `cannot` `unable` `corrupt` `assert` |
| 5 | ★★★ **12 个 WRN 关键词** | `warn` `WARN` `timeout` `timed out` `dropped` `stall` `STALL` `retry` `fallback` `skipped` `missing` `delay` |
| 6 | ★★ 设计原则 | "关键词表**刻意短且向严重倾斜**（**误判成 ERR 比漏判安全**）" |
| 7 | ★★★★★ **`zeroValued` 的实测教训** | **`pmove-trace calls=834000 hits=482678 failed=0`** 曾被标成 `[ERR]` ⇒ **`failed=0`/`dropped=0` 不算异常**（V1.203 ⑥） |
| 8 | ★★★★★ **修复 1 的测量** | 每行 **135 µs**,其中 **132 µs** 是 open+close（**97.8%**）；**180 行/秒**；**224 MB** 文件；**三个进程**；**2–6 秒帧卡顿** |
| 9 | ★★★★★ **卡顿现象学** | "showed up in think, begin and end **indiscriminately**, which is to say **not in any one of them**" ⇒ **共享资源争用** |
| 10 | ★★★★★ **命名互斥量误用** | 名字含 **`GetCurrentProcessId()`** ⇒ **每进程各拿自己的锁 ⇒ 从未排除任何东西** |
| 11 | ★★★★ **正确做法** | **`FILE_APPEND_DATA`**（不带 `FILE_WRITE_DATA`）⇒ **文件系统保证跨进程原子追加** |
| 12 | ★★★ 无缓冲 | "a line that WriteFile returned from **survives a crash**"（旧 `ofstream` 会缓冲） |
| 13 | ★★★★★ **四族占 89%** | `player-kinematics` **31.3%** / `dead-body` **25.6%** / `weapon-movement` **19.3%** / `player-entity` **12.8%** = **89.0%** ✓ |
| 14 | ★★★ 测量窗口 | **2026-10-12 12:26:32–12:33:42**（**430 秒**）/ **8 MB** 尾部 |
| 15 | ★★★ 增长速率 | **67 MB/小时 = 1.6 GB/天**；满员 **12 槽** ⇒ **约 46 行/秒**；文件 **~250 MB** |
| 16 | ★★★★ **8 个无条件保留的标签** | `FRAMESTALL` / `FRAME THREAD STALLED` / `LOGSTALL` / `BOTTRACE\|fill-target` / `BOTTRACE\|routing-vertical` / `BOTTRACE\|create-refused` / `pmove-trace` / `CLIENTTHINK` |
| 17 | ★★ 保留原则 | "anything that reports a **state change, a refusal or a stall** is **evidence**" |
| 18 | ★★★★★ **QuickEdit 陷阱** | 控制台点击 ⇒ 选择模式 ⇒ **每次 WriteFile BLOCK** ⇒ **FRAME THREAD STALLED 数秒** |
| 19 | ★★★★★ 结论 | **"A server must not be stoppable by a mouse."** |
| 20 | ★★ QuickEdit 常量 | **`0x0040`**（`ENABLE_QUICK_EDIT_MODE`）+ **`0x0080`**（`ENABLE_EXTENDED_FLAGS`,必须同时设） |
| 21 | ★★ `OutputDebugStringA` | 无调试器时仍取**全局系统锁**并遍历 DBWIN ⇒ 必须 `IsDebuggerPresent()` 门控 |
| 22 | ★★ 环境变量缓存 | `static const bool console = consoleEnabled();` ⇒ 不再每行调 |
| 23 | ★★★★★ **`LOGSTALL` 自诊断** | 阈值 **≥20 ms** + 距上次 **≥1 s**；三段计时 **`lockUs` / `fileUs` / `consoleDebugUs`**；★ **只写文件不递归**（"never diagnose a blocked console by writing the diagnostic back into that same console"）；`prefix=` 截断 **96 字节** |
| 24 | ★★★★★ **两个日志路径** | `<exe>\Ayria\Logs\`**`AlwaysofflineRe.Localnet32.log`** / **`CodolGameServer.log`** |
| 25 | ★★★★ **`Re` 后缀的又一证据** | 日志名用 **`Alwaysoffline**Re**.Localnet32`**,而发布二进制是 **`Alwaysoffline.Localnet32`**（无 `Re`）⇒ 与 RTTI 的 `@AlwaysofflineRe@@`（**182 条**）一致 |
| 26 | ★★ 三个控制台标题 | **`CODOL Dedicated Server`** / **`CODOL Client / Backend`** / **`CODOL Combined Runtime`** |
| 27 | ★★ `OLMOD_LOG_LEVEL` | **10 个值**（每级 2 种拼写）+ 回退到 `OLMOD_VERBOSE_LOG` |
| 28 | ★★ 布尔变量 4 种写法 | `1` / `true` / `yes` / `on`（不区分大小写） |
| 29 | ★★ `OLMOD_*` 累计 | 本报告新增 3 个（`LOG_LEVEL` / `VERBOSE_LOG` / `CONSOLE_LOG`）⇒ 总计 **13 个** |

---

## 六、结论

### 1. ★★★★★ **这份文件是一本"带精确测量的性能修复日志"**

```
修复 1：每行 open+close（**132/135 µs = 97.8%**）⇒ 每通道一个常开句柄
修复 2：命名互斥量名字含 **PID** ⇒ 从未排除任何东西 ⇒ 改用 **`FILE_APPEND_DATA`**
修复 3：无用户态缓冲 ⇒ 崩溃后仍存活
修复 4：**四族逐帧日志占 89%**（67 MB/h = 1.6 GB/天）⇒ 走 verbose 档
修复 5：**QuickEdit 让鼠标点击停住帧线程** ⇒ "A server must not be stoppable by a mouse."
修复 6：`OutputDebugStringA` 无调试器时仍取全局锁 ⇒ 加门控
修复 7：环境变量每行读一次 ⇒ `static const` 缓存
```

### 2. ★★★★★ **两个"测量驱动的设计"范例**

```
① ★★★ **四族日志的判定来自一次 430 秒的实测**
   （`player-kinematics 31.3% + dead-body 25.6% + weapon-movement 19.3% + player-entity 12.8% = 89.0%`）
   ⇒ 且明确列出**8 个故意不列入**的标签（状态变化/拒绝/卡顿都是证据）
        ↓
② ★★★ **`LOGSTALL` 自诊断本身是"三段计时"**
   （`lockUs` / `fileUs` / `consoleDebugUs`）
   ⇒ 且**只写文件不递归**（否则会自死锁）
```

### 3. ★★★★★ **`zeroValued` 是一条"零值不是错误"的精确实现**

★ **⇒ `pmove-trace calls=834000 hits=482678 failed=0` 曾被误判成 `[ERR]`。**

### 4. ★★★★ **`Re` 后缀的又一处证据**（日志名 `Alwaysoffline**Re**.Localnet32` vs 发布名 `Alwaysoffline.Localnet32`）

### 5. ★★★ **`OLMOD_*` 环境变量已达 13 个**

### 6. ★★ **`QuickEdit` 是 Windows 控制台的一个真实陷阱**（`0x0040` + `0x0080`）

---

## 七、下一步

- `shared\DedicatedControl.cpp`（36,106 B / 844 行）—— `shared\` 的最后一个大文件
- 然后 `game_server\qcommon\`（8 文件 / 103,413 B）—— `net_chan_mp` / `net_dtls_cod`
