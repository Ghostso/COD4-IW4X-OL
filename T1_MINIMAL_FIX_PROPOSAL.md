# T1_MINIMAL_FIX_PROPOSAL — T-1 四项缺陷的最小修复与测试方案

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（唯一活动基准）
**状态**：**FIXES PROPOSED, PENDING IMPLEMENTATION APPROVAL**
**本轮对正式源码的修改：0 字节。** 本文档只提交差异方案供审阅。

---

## 0. 复核方式与结论

### 0.1 复核方式：字节同一性（本轮未构建、未运行）

本轮**没有**重新构建或运行 T-1，而是证明"上轮 `checks=106 failures=0` 时的源码状态与当前逐字相同"：

| 文件 | 当前 SHA-256 | 与上轮一致 |
| --- | --- | --- |
| `src/game_server/server_mp/sv_network_mp.cpp` | `AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6` | ✅ |
| `src/game_server/server_mp/sv_network_mp.hpp` | `A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915` | ✅ |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` | ✅ |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` | ✅ |
| `tests/game_server/TransportLifecycleTests.cpp` | `FA6A2760B73BBE52B377178C10BAA64390ADC43522A97D455070DE79DBE7DE94` | ✅ |

⇒ 四项缺陷**全部仍然存在**（同一份字节），且上轮的 `106/0` 结论仍然有效。

### 0.2 缺陷编号对照

| 本任务编号 | 早期编号 | 一句话 |
| --- | --- | --- |
| **FF-1** | FF-1 | `stop()` 后缺少 **OS 层**端口释放证明 |
| **FF-2** | FF-3 | `lastSocketError` 清除行为与公开契约不一致 |
| **FF-3** | FF-6 | 合成错误码与真实 Winsock 错误码共用同一字段 |
| **FF-4** | FF-7 | 析构函数忽略 `close()` 失败 |

### 0.3 汇总

| # | 触及文件 | 触及行 | 是否改变可观察行为 | 是否触及受保护常量 | 断言数变化（预计） |
| --- | --- | --- | --- | --- | --- |
| FF-1 | **仅测试** `TransportLifecycleTests.cpp` | `testStopClearsState` | 否 | 否 | 106 → **108** |
| FF-2 | `sv_network_mp.cpp`（2 行）+ `sv_network_mp.hpp`（注释）+ 测试 | `:30-31`、`:48-49` | 是（**仅诊断字段**） | 否 | → **110** |
| FF-3 | `win_net.hpp`（常量值 + 注释）+ `win_net.cpp`（删 `static_assert`）+ 测试 | `hpp:24-27`、`cpp:13-15` | 是（**导出 API 返回的数值**） | 否（该常量**不是** RVA/前缀/协议常量） | → **113** |
| FF-4 | `win_net.cpp`（析构体）+ 测试 | `:48-51` | 否（只增加一条日志） | 否 | → **115** |

---

## 1. FF-1 — `stop()` 后缺少 OS 层端口释放证明

### 1.1 当前实现证据

`tests/game_server/TransportLifecycleTests.cpp:285-300`：

```cpp
    void testStopClearsState()
    {
        std::cout << "[4/8] stop() clears the state\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        transport.stop();
        const auto stopped = transport.status();
        require(!stopped.bound, "bound is cleared");
        require(stopped.port == 0, "port is cleared");
        require(
            stopped.packetsReceived == 0 && stopped.packetsSent == 0,
            "the counters are zeroed");
        require(
            stopped.lastPacketReceivedTime == 0 && stopped.lastPacketSentTime == 0,
            "the timestamps are zeroed");
    }
```

**问题**：全部断言读的都是 `SvNetworkStatus`（内部记账）。一个"只把状态清零、却不 `closesocket`"的 `stop()` 会让这 5 条断言**全部通过**。

`testRebindAfterStop`（`:313-327`）也不构成证明：它用 `start(0, …)` 重绑，操作系统可以给出**另一个**临时端口。

测试中所有 `NET_IPSocket` 调用都是 `(0, …)`（`:348`、`:366`、`:371`、`:479`、`:520`）——**没有任何一处尝试重新占用一个已知端口**。

### 1.2 最小修改方案（**仅测试文件**）

```diff
--- a/tests/game_server/TransportLifecycleTests.cpp
+++ b/tests/game_server/TransportLifecycleTests.cpp
@@ -285,13 +285,27 @@ namespace
     void testStopClearsState()
     {
         std::cout << "[4/8] stop() clears the state\n";
         SvUdpTransport transport;
         require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
+        const auto boundPort = transport.status().port;
+        require(boundPort != 0, "an ephemeral port was assigned");
         transport.stop();
         const auto stopped = transport.status();
         require(!stopped.bound, "bound is cleared");
         require(stopped.port == 0, "port is cleared");
         require(
             stopped.packetsReceived == 0 && stopped.packetsSent == 0,
             "the counters are zeroed");
         require(
             stopped.lastPacketReceivedTime == 0 && stopped.lastPacketSentTime == 0,
             "the timestamps are zeroed");
+
+        // OS-level release. The status fields above are internal bookkeeping: a
+        // stop() that zeroed them without closing the handle would pass them all.
+        // A fresh socket must be able to take the EXACT port the transport held.
+        // win_net.cpp sets no SO_REUSEADDR anywhere, so a still-live binding makes
+        // this bind fail with WSAEADDRINUSE; success is therefore proof that the
+        // OS released the endpoint.
+        NetUdpSocket probe;
+        require(
+            probe.NET_IPSocket(boundPort, LoopbackIpv4),
+            "the OS released the port the transport held");
     }
```

**为什么这是最小方案**：不新增测试函数、不新增辅助设施，只复用文件里已有的 `NetUdpSocket`（`:23` 已 `using`）与 `LoopbackIpv4`（`:43`）。新增 2 条断言。

**反例校验（关键）**：把 `SvUdpTransport::stop()` 临时改成"只清状态、不 `close()`"，`[4/8]` 的新断言**必须 FAIL**（`probe.NET_IPSocket(boundPort, …)` 会拿到 `WSAEADDRINUSE`）。如果它仍然 PASS，说明探针无效，方案不成立。**这一步是验收的一部分，不得省略。**

### 1.3 兼容性影响

| 维度 | 影响 |
| --- | --- |
| 生产源码 | **无**（只改测试） |
| 无参数调用语义 | 不变 |
| 默认绑定地址 | 不变 |
| 协议常量 / ABI / RVA / 前缀 | 不变 |
| 新增系统资源 | 一个临时 UDP socket，函数结束即析构；端口是该 `stop()` 刚释放的端口，不占用任何正式端口 |
| 断言数 | 106 → 108 |

### 1.4 未覆盖的真实 OS 故障场景

| 场景 | 为什么未覆盖 |
| --- | --- |
| `closesocket` 在 `stop()` 中**真实**失败 | 见 FF-4；只能由 IAT 伪造，非真实 OS 失败 |
| 端口被**另一个进程**抢占后 `stop()` | 本用例占的是自己刚释放的端口，不涉及跨进程竞争 |
| `TIME_WAIT` 导致重绑失败 | UDP 无 `TIME_WAIT`，但该差异本身未被用例显式记录 |
| 端口耗尽（临时端口池枯竭） | 需要制造系统级资源枯竭，禁止 |

---

## 2. FF-2 — `lastSocketError` 清除行为与公开契约不一致

### 2.1 当前实现证据

**契约**（`src/game_server/server_mp/sv_network_mp.hpp:66-69`）：

```cpp
        // Releases the socket and returns the transport to its unbound state:
        // bound=false, port=0, counters and timestamps zeroed, peer and nonce
        // state cleared. lastSocketError is retained (it is the sticky record of
        // the last socket failure, cleared by the next successful start()).
```

**实现**（`src/game_server/server_mp/sv_network_mp.cpp:25-50`）：

```cpp
        if (socket_.open())
        {
            if (port == 0)
                return true;                       // :30-31  <-- 成功，但不清除
            if (socket_.port() != port)
            {
                status_.lastSocketError = SocketAlreadyBoundError;
                return false;
            }
            const auto actualAddress = socket_.boundAddress();
            if (!actualAddress || *actualAddress != bindAddress)
            {
                status_.lastSocketError = SocketAlreadyBoundError;
                return false;
            }
            return true;                           // :49     <-- 成功，但不清除
        }
```

**全函数没有一处 `status_.lastSocketError = 0;`**（`start()` 内 `return true;` 出现在 `:31`、`:49`、`:60`；只有 `:51` 的 `status_ = {}` 会重置它，而那只在"socket 未打开"的分支里）。

⇒ 契约说的 "cleared by the next successful start()" 在**两条幂等成功路径上不成立**。一个把 `true` 解读为"错误状态已清除"的调用方会被误导。**当前无任何用例断言该点。**

### 2.2 最小修改方案

**方案 (a)（推荐）：让实现符合既有契约。** 改动 2 行。

```diff
--- a/src/game_server/server_mp/sv_network_mp.cpp
+++ b/src/game_server/server_mp/sv_network_mp.cpp
@@ -27,8 +27,11 @@ namespace CodolGameServer
             // A live binding is never torn down just because start() was called
             // again. Port 0 means "any port", so an existing binding already
             // satisfies it; the requested address is not applied.
             if (port == 0)
+            {
+                status_.lastSocketError = 0;
                 return true;
+            }
             // A different explicit port is a conflict, not an implicit restart.
             if (socket_.port() != port)
             {
                 status_.lastSocketError = SocketAlreadyBoundError;
                 return false;
             }
@@ -45,6 +48,7 @@ namespace CodolGameServer
                 status_.lastSocketError = SocketAlreadyBoundError;
                 return false;
             }
+            status_.lastSocketError = 0;
             return true;
         }
         status_ = {};
```

**同步把注释写准**（`sv_network_mp.hpp:66-69`）：

```diff
--- a/src/game_server/server_mp/sv_network_mp.hpp
+++ b/src/game_server/server_mp/sv_network_mp.hpp
@@ -66,8 +66,10 @@ namespace CodolGameServer
         // Releases the socket and returns the transport to its unbound state:
         // bound=false, port=0, counters and timestamps zeroed, peer and nonce
         // state cleared. lastSocketError is retained (it is the sticky record of
-        // the last socket failure, cleared by the next successful start()).
+        // the last socket failure). A start() that returns true CLEARS it: on the
+        // fresh-bind path because status_ is reset, and on the already-open
+        // idempotent paths because they clear it explicitly. A start() that
+        // returns false never clears it.
```

**方案 (b)（更小，但语义更弱）**：不改实现，只把契约措辞改为"仅在真正重新绑定成功时清除"。改动 0 行生产代码。

**建议**：采用 (a)。契约已经写出来了，让实现去满足它比降低契约更好；且 (a) 只多 2 行。

### 2.3 对应测试

在 `[A-1]`（`testAddressMustMatchLiveBinding`）中，`start(0, AnyIpv4Address)` 成功之后（当前 `:441-447`）补一条断言：

```diff
--- a/tests/game_server/TransportLifecycleTests.cpp
+++ b/tests/game_server/TransportLifecycleTests.cpp
@@ -444,6 +444,9 @@ namespace
         const auto afterZero = transport.status();
         require(afterZero.port == before.port, "start(0) keeps the port");
         require(afterZero.packetsSent == before.packetsSent, "start(0) keeps the counter");
+        require(
+            afterZero.lastSocketError == 0,
+            "a successful start() clears the sticky error even when idempotent");
```

**这是"先失败"的用例**：在**当前**代码上，前一步 `transport.start(bound.port, AnyIpv4Address)` 已把 `lastSocketError` 置为 `SocketAlreadyBoundError`，而随后的 `start(0, …)` 不清除它 ⇒ 该断言**必然 FAIL**。实施 (a) 之后转为 PASS。**这条断言就是 FF-2 的验收凭据。**

同时**不得回归** `[7/8]`（`:329-342`）的粘性错误断言：`start(0)` → `start(differentPort)` 失败 → `stop()` → 错误必须保留。方案 (a) 不触碰失败路径，因此该断言不受影响。

### 2.4 兼容性影响

| 维度 | 影响 |
| --- | --- |
| 可观察行为 | `start()` 返回 `true` 时 `status().lastSocketError` 由"可能残留旧值"变为"必为 0"。**只影响诊断字段** |
| 失败路径 | 不变（仍写入 `SocketAlreadyBoundError` / 真实 OS 码） |
| 无参数调用语义 / 默认绑定地址 | 不变 |
| 协议常量 / ABI / RVA / 前缀 | 不变 |
| 现有 106 条断言 | 经逐条核对，**无一条**依赖"成功早退后错误残留"，因此无回归 |
| 断言数 | 106 → 110 |

### 2.5 未覆盖的真实 OS 故障场景

| 场景 | 为什么未覆盖 |
| --- | --- |
| `start()` 在"真正重新绑定"时失败并留下错误码 | `[8/8]` 已覆盖（占用端口 ⇒ 真实 `WSAEADDRINUSE`），但**未**断言"随后的成功 start 会清除它"——这正是本项新增断言所补的相邻路径 |
| 并发 `start()`/`stop()` 交错导致错误码竞态 | `mutex_` 已存在，但**无任何并发用例**（见 §5） |

---

## 3. FF-3 — 合成错误码与真实 Winsock 错误码共用同一字段

### 3.1 当前实现证据

**常量**（`src/game_server/win32/win_net.hpp:24-27`）：

```cpp
    // Reported through lastError() by SvUdpTransport::start when a live binding
    // already exists and a different explicit port was requested. Numerically
    // WSAEALREADY; win_net.cpp static_asserts that equality so it cannot drift.
    inline constexpr int SocketAlreadyBoundError = 10037;
```

**编译期锁定**（`src/game_server/win32/win_net.cpp:13-15`）：

```cpp
    static_assert(
        SocketAlreadyBoundError == WSAEALREADY,
        "SocketAlreadyBoundError must mirror WSAEALREADY");
```

**问题**：

1. `10037` 是 **真实的 Winsock 错误码**（`WSAEALREADY`，语义是"非阻塞 connect 正在进行"，与"端口已绑定"**无关**）。它与真实 OS 错误共用 `status_.lastSocketError` 这一个 `int` 字段，调用方**无法区分**"这是我方合成的原因"还是"这是 OS 报的错误"。
2. 真实的端口冲突由 OS 报 `WSAEADDRINUSE (10048)`——**同一字段里现在可能同时出现 10048 与 10037，而后者看起来也像 OS 错误**。既有运行日志已实测到 `error=10048`。
3. 语义错配：`WSAEALREADY` 的字面含义与"已绑定"不符。

**跨边界事实（重要）**：该值经 `Appmain.cpp:9513-9522` 的导出函数 `CODOL_GameServerGetTransportStatus(..., std::uint32_t *lastSocketError)` **以 `uint32_t` 形式暴露给宿主**，并被 `tools/runtime/CodolGameServerControl.py:1665` 读为 `last_socket_error`。因此修改其数值是一个**可观察的数值变化**，必须登记（但不改变任何结构/ABI 布局）。

### 3.2 最小修改方案

```diff
--- a/src/game_server/win32/win_net.hpp
+++ b/src/game_server/win32/win_net.hpp
@@ -22,9 +22,13 @@ namespace CodolGameServer
     inline constexpr std::uint32_t AnyIpv4Address = 0;
 
     // Reported through lastError() by SvUdpTransport::start when a live binding
-    // already exists and a different explicit port was requested. Numerically
-    // WSAEALREADY; win_net.cpp static_asserts that equality so it cannot drift.
-    inline constexpr int SocketAlreadyBoundError = 10037;
+    // already exists and the request cannot be satisfied by it. The value is
+    // DELIBERATELY OUTSIDE the Winsock error range so that a caller can always
+    // tell this synthetic reason from a genuine OS error. It used to be 10037
+    // (WSAEALREADY), which IS a real Winsock code, so status().lastSocketError
+    // could hold either and no consumer could separate them. WSAEADDRINUSE
+    // (10048) remains what the OS itself reports for a real port clash.
+    inline constexpr int SocketAlreadyBoundError = 0x4F4C4D42;  // 'OLMB'
```

```diff
--- a/src/game_server/win32/win_net.cpp
+++ b/src/game_server/win32/win_net.cpp
@@ -10,10 +10,6 @@
 namespace CodolGameServer
 {
-    static_assert(
-        SocketAlreadyBoundError == WSAEALREADY,
-        "SocketAlreadyBoundError must mirror WSAEALREADY");
-
     namespace
     {
```

**为什么选 `0x4F4C4D42`**：ASCII `'OLMB'`（OLMod Binding），**明显不在** Winsock 错误区间（约 10000–11999），因此任何日志/UI 都能一眼区分。

**不改的东西**：`start()` 的拒绝**行为**、拒绝的**时机**、`lastSocketError` 的**类型与字段位置**、`AnyIpv4Address`、以及所有 RVA/前缀/协议常量。

### 3.3 对应测试

现有断言全部使用**符号常量**（`TransportLifecycleTests.cpp:280`、`:340`、`:438`、`:465`），因此改值**不会**破坏它们。新增两条把"可区分性"固化成断言（建议放在 `[3/8]` 之后）：

```diff
--- a/tests/game_server/TransportLifecycleTests.cpp
+++ b/tests/game_server/TransportLifecycleTests.cpp
@@ -279,6 +279,12 @@ namespace
         require(
             conflict.lastSocketError == SocketAlreadyBoundError,
             "the conflict is reported as SocketAlreadyBoundError");
+        require(
+            SocketAlreadyBoundError != WSAEADDRINUSE &&
+            SocketAlreadyBoundError != WSAEALREADY,
+            "the synthetic conflict code is not a real Winsock error code");
+        require(
+            SocketAlreadyBoundError < 10000 || SocketAlreadyBoundError > 11999,
+            "the synthetic conflict code lies outside the Winsock error range");
```

并**加强** `[8/8]` 对真实冲突码的断言（当前只断言 `!= 0`）：

```diff
--- a/tests/game_server/TransportLifecycleTests.cpp
+++ b/tests/game_server/TransportLifecycleTests.cpp
@@ -354,7 +354,9 @@ namespace
         require(failed.port == 0, "a failed start leaves the port at zero");
-        require(failed.lastSocketError != 0, "a failed start records a socket error");
+        require(
+            failed.lastSocketError == WSAEADDRINUSE,
+            "a real port clash is reported with the real Winsock code");
```

**注意**：这条把"真实冲突码 = 10048"变成硬断言。既有运行日志已实测 `error=10048`（`[C-3]` 用例的日志行），因此该断言有实测支撑；但它是**平台行为断言**，若将来在别的 Windows 版本上观察到不同码，应改为记录而非判负——**这一点需要在实施时确认**。

### 3.4 兼容性影响

| 维度 | 影响 |
| --- | --- |
| 可观察行为 | 导出 API `CODOL_GameServerGetTransportStatus` 返回的 `lastSocketError` 在"冲突"情形下由 `10037` 变为 `0x4F4C4D42`。**是数值变化，不是结构变化** |
| 树内消费者 | 已逐处核对：无任何消费者把该值与 `10037` 比较。`Appmain.cpp:6910` 只做"值是否变化"的日志判定；`:6950` 只 `std::to_string`；`CodolGameServerControl.py:1665` 只记录 |
| 树外消费者 | 若有外部脚本对 `10037` 特判，需同步。**本轮未发现此类脚本** |
| `start()` 行为 / 无参语义 / 默认地址 | 不变 |
| 协议常量 / ABI / RVA / 前缀 | 不变（该常量**不是** RVA、**不是**机器码前缀、**不是**协议常量） |
| 断言数 | 106 → 113 |

### 3.5 未覆盖的真实 OS 故障场景

| 场景 | 为什么未覆盖 |
| --- | --- |
| `WSAEALREADY` 作为**真实**错误出现在该 socket 上 | 该 socket 从不做非阻塞 `connect`，因此真实 `WSAEALREADY` 不可达。**这恰好是"用它当哨兵"不合理的进一步证据** |
| `bind()` 返回 `WSAEACCES`（特权端口） | 需绑定 <1024 端口并依赖权限，环境相关 |
| `bind()` 返回 `WSAENETDOWN` / `WSAEADDRNOTAVAIL` | 需要改变本机网络配置，禁止 |

---

## 4. FF-4 — 析构函数忽略 `close()` 失败

### 4.1 当前实现证据

`src/game_server/win32/win_net.cpp:48-51`：

```cpp
    NetUdpSocket::~NetUdpSocket()
    {
        close();
    }
```

而 `close()`（`:149-170`）在失败时**提前返回**：

```cpp
        if (socket_ != InvalidSocket)
        {
            if (closesocket(static_cast<SOCKET>(socket_)) == SOCKET_ERROR)
            {
                // Leave the handle marked open: the caller must be able to see
                // that the socket was not released instead of reporting a clean
                // stop. A later close() retries.
                lastError_ = WSAGetLastError();
                return false;                 // <-- WSACleanup() 被跳过
            }
            socket_ = InvalidSocket;
        }
        port_ = 0;
        if (winsockStarted_)
        {
            WSACleanup();
            winsockStarted_ = false;
        }
        return true;
```

**问题**：析构是"最后一次机会"。若此时 `closesocket` 失败：

1. 句柄**泄漏**（`socket_` 仍有效，但对象即将消失，再无人能重试）；
2. `WSACleanup()` **被跳过** ⇒ 该对象的 Winsock 引用计数永久失衡；
3. 失败**完全静默** —— 没有任何日志，问题不可诊断。

### 4.2 最小修改方案

```diff
--- a/src/game_server/win32/win_net.cpp
+++ b/src/game_server/win32/win_net.cpp
@@ -48,7 +48,18 @@ namespace CodolGameServer
     NetUdpSocket::~NetUdpSocket()
     {
-        close();
+        // A destructor cannot fail, but it must not hide a leak either. close()
+        // returns false when closesocket failed; in that case the handle is
+        // deliberately left open (so a caller could retry) and WSACleanup has NOT
+        // run. There is no retry possible from here, so the only honest action is
+        // to say so. std::clog is already this file's diagnostic channel.
+        if (!close())
+        {
+            std::clog << "[dedicated/game-server] udp socket destructor: "
+                         "close failed error=" << lastError_ << std::endl;
+        }
     }
```

**为什么这是最小方案**：

- **不新增 include**：`std::clog` / `std::endl` 已在本文件使用（`:40-44`、`:140-145`），`<iostream>` 已在 `:6`。
- **不改变清理语义**：仍然不强制 `WSACleanup()`。在"保留句柄以便重试"与"立刻释放 Winsock 引用"之间，本方案选择**保持既有优先级不变**，只增加可观测性。若要改成强制 `WSACleanup()`，那是**语义变更**，需要单独裁定（见 §4.5）。

### 4.3 对应测试

复用文件里已有的 IAT 注入设施（`ScopedCloseSocketFailure`，`:113-158`）：

```diff
--- a/tests/game_server/TransportLifecycleTests.cpp
+++ b/tests/game_server/TransportLifecycleTests.cpp
@@ (new function, before main)
+    // FF-4: destruction is the last chance to release the handle. A failure
+    // there is not recoverable, so it must at least be visible.
+    void testDestructorCloseFailureIsReported()
+    {
+        std::cout << "[destructor-close-failure] a failed release at destruction is reported\n";
+        std::ostringstream captured;
+        auto *const originalClog = std::clog.rdbuf();
+        bool redirected = false;
+        {
+            ScopedCloseSocketFailure failure(WSAENOTSOCK);
+            require(failure.active(), "the closesocket import can be redirected for the test");
+            std::clog.rdbuf(captured.rdbuf());
+            redirected = true;
+            {
+                NetUdpSocket socket;
+                require(socket.NET_IPSocket(0, LoopbackIpv4), "the socket binds");
+            }   // ~NetUdpSocket() runs here, under the injected failure
+            std::clog.rdbuf(originalClog);
+            redirected = false;
+        }
+        if (redirected)
+            std::clog.rdbuf(originalClog);
+        const auto text = captured.str();
+        require(
+            text.find("udp socket destructor: close failed error=") != std::string::npos,
+            "the destructor reports the failed release");
+        require(
+            text.find(std::to_string(WSAENOTSOCK)) != std::string::npos,
+            "the destructor reports the injected error code");
+    }
```

并在 `main()` 的调用列表末尾加入 `testDestructorCloseFailureIsReported();`。

**这是"先失败"的用例**：在当前代码上 `captured` 为空 ⇒ 两条断言**必然 FAIL**；实施后转 PASS。

**为什么用注入而非真实失败**：真实 `closesocket` 失败需要让 OS 拒绝释放一个有效句柄，这无法在不破坏环境的前提下稳定复现。注入路径**明确标注为模拟**，报告与日志中**不得**把它当作真实 OS 失败证据（测试文件 `:45-52` 已有同样的免责说明，新用例沿用同一机制）。

### 4.4 兼容性影响

| 维度 | 影响 |
| --- | --- |
| 可观察行为 | 仅在"析构时 close 失败"这一**新增诊断**上产生一条 `std::clog` 输出；正常路径**零输出** |
| 清理语义 | **不变**（仍不强制 `WSACleanup()`） |
| 无参语义 / 默认地址 / 协议常量 / ABI / RVA / 前缀 | 不变 |
| 断言数 | 106 → 115 |

### 4.5 未覆盖的真实 OS 故障场景

| 场景 | 为什么未覆盖 | 备注 |
| --- | --- | --- |
| **真实** `closesocket` 失败 | 无法在不破坏环境的前提下稳定复现 | 只用 IAT 注入模拟；**必须**在报告中标注为模拟 |
| 析构时 `WSACleanup()` 的引用计数后果 | 无探针；`WSAStartup`/`WSACleanup` 的调用次数不可观测 | 需要 WSA 计数探针或进程级 hook，超出最小修复范围 |
| 句柄泄漏的**可观测**证明 | 需要 `GetProcessHandleCount` 对比 | 可作为后续增强，非最小修复 |
| 多线程并发析构 | 无并发用例 | 见 §5 |
| 进程退出期析构（加载器已开始拆除） | 不可控 | — |

**一个需要单独裁定的开放问题**：析构时 `close()` 失败，是否应当**强制** `WSACleanup()`（放弃"保留句柄以便重试"，因为析构后已无重试者）？

- 支持强制：句柄反正要泄漏，至少让 Winsock 引用计数平衡。
- 反对强制：`WSACleanup()` 在句柄仍活时调用是未定义/不安全的组合，可能影响同进程其它 socket。

**本方案不预设结论**，只增加可观测性；该问题登记为后续裁定项。

---

## 5. 全局未覆盖项（不限于某一项缺陷）

| 未覆盖 | 说明 |
| --- | --- |
| **并发** | `SvUdpTransport` 有 `mutex_`，`NetUdpSocket` **无锁**。测试**全部单线程**，`mutex_` 从未被竞争。`start()`/`stop()` 与 `NET_Frame()` 并发下的行为**完全未验证** |
| **Winsock 引用计数** | `WSAStartup`/`WSACleanup` 成对性只有静态核对，**无运行时断言** |
| **长时稳定性** | 无重复 `start/stop` 压力用例 |
| **`start()` 的真实重绑失败后再次成功** | `[8/8]` 之后没有"释放占用者再 `start()` 成功"的用例（FF-2 的新断言覆盖了相邻路径，但不完整） |
| **x64 / 非 x86 构建** | 与 T-1 无关（项目为 x86） |

---

## 6. 受保护常量清单（本方案**一个都不改**）

| 常量 | 值 | 位置 |
| --- | --- | --- |
| `EngineBindings::ExpectedTimestamp` | `0x6096930A` | `EngineBindings.hpp:438` |
| `EngineBindings::ExpectedImageSize` | `0x0E5D6000` | `EngineBindings.hpp:439` |
| `EngineBindings::ComFrameRva` | `0x0FEA20` | `EngineBindings.hpp:440` |
| `ClientProcessPatches::UnsignedFastfileVerificationRva` | `0x8371A` | `ClientProcessPatches.cpp:207` |
| `ComFramePrefix` | `55 8B EC 56 57` | `EngineBindings.cpp:755-757` |
| `UnsignedFastfileVerification` | `83 7C 24 08 01 0F 94 C0` | `ClientProcessPatches.cpp:208-211` |
| 协议常量（DTLS / netchan / usercmd / gamestate） | — | `qcommon/`、`server_mp/` |
| S2-S3 默认值、fixture、启动链 | — | — |
| `AnyIpv4Address` | `0` | `win_net.hpp:22`（**本方案不改**） |

本方案只触及：一个**测试文件**、`sv_network_mp.{cpp,hpp}` 的 2 行实现 + 注释、`win_net.{cpp,hpp}` 的 1 个常量值 + 1 个 `static_assert` + 1 个析构体。

---

## 7. 验收与授权请求

### 7.1 实施后的验收标准

| 项 | 标准 |
| --- | --- |
| 构建 | `xmake build -r ol_transport_lifecycle_tests` **exit 0**（**必须显式命名目标**；`ol_deploy` 是 `set_default(true)`） |
| 运行 | `checks=115 failures=0`，**exit 0**（预计断言数；以实测为准） |
| 反例校验 FF-1 | 临时破坏 `stop()` 的 `close()` ⇒ 新断言**必须 FAIL** |
| 反例校验 FF-2 | 在未实施 (a) 的代码上 ⇒ 新断言**必须 FAIL** |
| 反例校验 FF-4 | 在未实施析构日志的代码上 ⇒ 新断言**必须 FAIL** |
| 回归 | `[7/8]` 粘性错误、`[8/8]` 占用端口、`[C-3]` 日志、`[simulated-close-failure]` 全部仍 PASS |
| 兼容 | `Appmain.cpp` 的 3 处调用点**不需修改**；无参语义与默认绑定地址不变 |

### 7.2 授权请求（逐项）

| # | 请求 | 触及文件 | 风险 |
| --- | --- | --- | --- |
| A | 批准 FF-1（仅测试） | `tests/game_server/TransportLifecycleTests.cpp` | 最低 |
| B | 批准 FF-2 方案 (a) | `sv_network_mp.cpp` 2 行 + `.hpp` 注释 + 测试 | 低（仅诊断字段） |
| C | 批准 FF-3（哨兵值移出 Winsock 区间） | `win_net.hpp` 常量 + `win_net.cpp` 删 `static_assert` + 测试 | 中（**导出 API 数值变化**，需确认无树外消费者特判 `10037`） |
| D | 批准 FF-4（析构日志） | `win_net.cpp` 析构体 + 测试 | 低 |
| E | 单独裁定 §4.5 的开放问题（析构失败时是否强制 `WSACleanup`） | — | 需先有结论再决定是否扩大范围 |

**建议顺序**：A → B → D → C（C 涉及导出数值，最后做并单独记录）。

---

## 8. 本轮执行边界核对

| 禁止项 | 状态 |
| --- | --- |
| 启动 CODOL 客户端 / 服务进程 | **未执行** |
| 运行 Injector32 / 注入 | **未执行** |
| 读取或修改进程内存 | **未执行** |
| 运行正式部署（含 `ol_deploy`） | **未执行** |
| 修改正式启动链 / ABI / RVA / 机器码前缀 / 协议常量 / S2-S3 默认值 | **未执行**（§6 清单零字节改动） |
| **修改正式源码** | **未执行**（本文档仅为差异方案） |
| Git 提交 / 推送 | **未执行** |
| 构建 / 运行测试 | **未执行**（改用字节同一性证明状态） |

---

## 9. 关联交付

- [OFFLINE_BINDING_REPLAY_REPORT.md](OFFLINE_BINDING_REPLAY_REPORT.md) — P1-4 工具设计与真实运行结果
- [OFFLINE_BINDING_REPLAY_TESTS.md](OFFLINE_BINDING_REPLAY_TESTS.md) — P1-4 测试覆盖与结果
- [FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md](FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md) · [NEXT_PHASE_PLAN.md](NEXT_PHASE_PLAN.md)
- [\_p14_evidence\\SHA256_MANIFEST.txt](_p14_evidence/SHA256_MANIFEST.txt) — 文件哈希清单
