# T1_FF2_ERROR_STATE_REPORT — FF-2 `lastSocketError` 契约实施

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**
**授权范围**：先加回归断言并复现问题，再实施最小源码修改。
**结果**：**已实施 · 修复前 `checks=124 failures=2` (exit 1) · 修复后 `checks=124 failures=0` (exit 0)**

---

## 1. 缺陷定义

**契约**（`sv_network_mp.hpp:66-69`，实施前原文）：

```cpp
        // Releases the socket and returns the transport to its unbound state:
        // bound=false, port=0, counters and timestamps zeroed, peer and nonce
        // state cleared. lastSocketError is retained (it is the sticky record of
        // the last socket failure, cleared by the next successful start()).
```

**实现**（`sv_network_mp.cpp:25-50`，实施前）：`start()` 有三条返回 `true` 的路径，但**只有一条**真正清除了 `lastSocketError`：

| 路径 | 返回 true 的位置 | 实施前是否清除 |
| --- | --- | --- |
| 1. 新绑定（socket 未打开） | `:60` | ✅ 经 `:51` 的 `status_ = {}` |
| 2. 已打开 + `port == 0` 早退 | `:31` | ❌ **不清除** |
| 3. 已打开 + 同端口同地址早退 | `:49` | ❌ **不清除** |

⇒ 一个把 `true` 读作"错误状态已清除"的调用方会被路径 2/3 误导。**实施前无任何断言覆盖该点。**

---

## 2. 步骤 1：先添加回归断言（未改源码）

新增用例 `testSuccessfulStartClearsStickyError`，**三条成功路径各覆盖一次**。每条都用一次**真实冲突**先把 `lastSocketError` 污染成非零，因此断言通过不可能是"字段本来就是 0"的巧合。

```cpp
    void testSuccessfulStartClearsStickyError()
    {
        std::cout << "[FF-2] a successful start() clears the sticky error\n";

        // Path 1: fresh bind (socket not open). status_ is reset here, so this
        // path is expected to hold even before the fix; it is asserted so the
        // other two cannot pass by inheriting an untouched field.
        {
            SvUdpTransport transport;
            require(transport.start(0, LoopbackIpv4), "fresh start(0) succeeds");
            require(
                transport.status().lastSocketError == 0,
                "path 1 fresh bind: a successful start() reports no socket error");
            transport.stop();
        }

        // Path 2: the early return for port == 0 against a live binding.
        {
            SvUdpTransport transport;
            require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
            const auto bound = transport.status();
            require(
                !transport.start(differentPort(bound.port), LoopbackIpv4),
                "path 2: a conflicting port is refused");
            require(
                transport.status().lastSocketError == SocketAlreadyBoundError,
                "path 2: the refusal poisons lastSocketError");
            require(
                transport.start(0, LoopbackIpv4),
                "path 2: start(0) against the live binding succeeds");
            require(
                transport.status().lastSocketError == 0,
                "path 2 idempotent start(0): the successful start() cleared the sticky error");
            transport.stop();
        }

        // Path 3: the early return for the same port AND the same bound address.
        {
            SvUdpTransport transport;
            require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
            const auto bound = transport.status();
            require(
                !transport.start(bound.port, AnyIpv4Address),
                "path 3: a conflicting address is refused");
            require(
                transport.status().lastSocketError == SocketAlreadyBoundError,
                "path 3: the refusal poisons lastSocketError");
            require(
                transport.start(bound.port, LoopbackIpv4),
                "path 3: the exact same port and address succeeds");
            require(
                transport.status().lastSocketError == 0,
                "path 3 same-port same-address: the successful start() cleared the sticky error");
            transport.stop();
        }
    }
```

---

## 3. 步骤 2：确认新断言在原实现上复现问题

**修复前**（`sv_network_mp.cpp` = `AF93F7C8…`）：

| 项 | 值 |
| --- | --- |
| 构建 | `BUILD exit=0` |
| 运行 | **`run exit=1`** · **`checks=124 failures=2`** |
| 失败断言 1 | `path 2 idempotent start(0): the successful start() cleared the sticky error` |
| 失败断言 2 | `path 3 same-port same-address: the successful start() cleared the sticky error` |
| 路径 1 | `ok path 1 fresh bind: a successful start() reports no socket error`（符合预期：该路径本来就正确） |
| 日志 | [\_t1_fix_evidence\\phase2a_ff2_assertions_before_fix.log](_t1_fix_evidence/phase2a_ff2_assertions_before_fix.log) |

**失败状态行计数**：`^\s+FAIL ` 精确匹配 = **2**（其余含 "fail" 字样的行都是 `ok` 断言，例如 `udp init failed` 日志与 `start(other) fails` 消息）。

> **这两条失败断言被保留，没有被删除或弱化。** 它们在修复后转为 PASS，构成本项修复的直接验收凭据。

---

## 4. 步骤 3：最小源码修改

### 4.1 `sv_network_mp.cpp`（+9 行，其中 2 行是赋值）

```diff
@@ -24,11 +24,19 @@ namespace CodolGameServer
         const std::lock_guard lock(mutex_);
         if (socket_.open())
         {
+            // lastSocketError contract: every path below that returns true
+            // CLEARS the sticky error, and every path that returns false leaves
+            // it carrying the reason. A caller can therefore read a true result
+            // as "no outstanding socket failure". See sv_network_mp.hpp.
+            //
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
@@ -46,6 +54,7 @@ namespace CodolGameServer
                 status_.lastSocketError = SocketAlreadyBoundError;
                 return false;
             }
+            status_.lastSocketError = 0;
             return true;
         }
         status_ = {};
```

### 4.2 `sv_network_mp.hpp`（契约措辞与实现对齐）

```diff
@@ -44,12 +44,19 @@ namespace CodolGameServer
         // (the PeerAddress::ipv4 convention); the default is every interface,
         // which is what production callers already used.
         //
+        // lastSocketError contract: every path that returns true CLEARS it to 0,
+        // and every path that returns false leaves it carrying the reason. A true
+        // result therefore means "no outstanding socket failure", on the fresh
+        // bind path and on both idempotent early returns alike.
+        //
         // Idempotent while a socket is already open:
         //   port == 0                        -> the live binding already
         //                                       satisfies an ephemeral request;
-        //                                       return true, unchanged, and the
-        //                                       requested address is not applied
-        //   same port, same bound address    -> return true, unchanged
+        //                                       return true with the binding
+        //                                       untouched, and the requested
+        //                                       address is not applied
+        //   same port, same bound address    -> return true with the binding
+        //                                       untouched
         //   same port, different address, or
         //   any other non-zero port          -> return false with
         //                                       lastSocketError ==
```

**为什么改措辞**：原文的 `return true, unchanged` 只说明"绑定未变"，对 `lastSocketError` 是**歧义**的——这正是缺陷得以存在的语言土壤。现在三处表述（`start()` 契约、`stop()` 契约、实现）完全一致：

| 位置 | 表述 |
| --- | --- |
| `start()` 契约 | "every path that returns true CLEARS it to 0, and every path that returns false leaves it carrying the reason" |
| `stop()` 契约（未改，现已成立） | "lastSocketError is retained (… cleared by the next successful start())" |
| 实现 | 三条 `return true` 路径全部清除；两条 `return false` 路径全部写入原因 |

### 4.3 差异隔离的可验证性

为证明"改动**只有**这些"，我把当前文件按上述差异**反向还原**，还原结果的 SHA-256 与阶段 0 基线**逐字节相等**：

| 文件 | 还原后 SHA-256 | 阶段 0 基线 | 相等 |
| --- | --- | --- | --- |
| `sv_network_mp.cpp` | `AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6` | 同 | ✅ |
| `sv_network_mp.hpp` | `A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915` | 同 | ✅ |

还原脚本：`_t1_fix_evidence/_reconstruct_pre_ff2.py`；还原副本：`_t1_fix_evidence/pre_ff2_sv_network_mp.{cpp,hpp}`；**仅 FF-2 的差异**：[\_t1_fix_evidence\\ff2_only.diff](_t1_fix_evidence/ff2_only.diff) 与 [\_t1_fix_evidence\\ff2_only_hpp.diff](_t1_fix_evidence/ff2_only_hpp.diff)。

---

## 5. 步骤 4：强制重建并运行全部相关测试

### 5.1 `ol_transport_lifecycle_tests`（强制重建）

| 项 | 值 |
| --- | --- |
| 命令 | `xmake build -r ol_transport_lifecycle_tests`（**显式命名目标**） |
| 构建 | `BUILD exit=0` |
| 产物 | 3,830,272 B · 2026-10-10 12:50:50 · `14C13963223F3E3361A8D691DA6D6E742A4DF75A286EBB1FDC4130141E482DEB` |
| 运行 | **`run exit=0`** · **`checks=124 failures=0`** |
| 失败状态行 | `^\s+FAIL ` 精确匹配 = **0** |
| 日志 | [\_t1_fix_evidence\\phase2b_ff2_after_fix.log](_t1_fix_evidence/phase2b_ff2_after_fix.log) |

### 5.2 其它链接 `game_server_core` 的目标

`sv_network_mp.cpp` 属于 `game_server_core`，因此**所有**链接它的目标都必须重编并通过：

| 目标 | 是否重编 `sv_network_mp.cpp` | 构建 | 运行 | 产物 SHA-256 |
| --- | --- | --- | --- | --- |
| `ol_transport_lifecycle_tests` | ✅ | exit 0 | exit 0 | `14C13963223F3E3361A8D691DA6D6E742A4DF75A286EBB1FDC4130141E482DEB` |
| `ol_game_server_tests` | ✅ | exit 0 | **exit 0** | `706CAE920707DA8976F047E14878BB3CCC546915C566B9BAFDF66DE68D09CCEB` |
| `ol_lua_runtime_tests` | ✅ | exit 0 | **exit 0** | `9205E4BBE39EB9F5C5B24D483ED2245E8C93B0168385312D27560743D7DEC151` |
| `ol_game_server`（生产插件） | ✅ | exit 0 | —（插件不单独运行） | `DBA7273A0C9DD31CDD5619DD47B11C01EDC21AE17EEFC18FDD71F43B992097BC`（6,559,232 B） |

日志：[\_t1_fix_evidence\\phase2c_related_targets.log](_t1_fix_evidence/phase2c_related_targets.log)

`ol_game_server_tests` 末行断言示例：`BATTERY_CG selector-vs-player identity and refusal paths PASS`；`ol_lua_runtime_tests` 末行：`CodolGameServer Lua runtime tests passed`。

### 5.3 断言数轨迹

| 阶段 | 断言数 | 失败 | 退出码 |
| --- | --- | --- | --- |
| 阶段 0 基线 | 106 | 0 | 0 |
| 阶段 1（FF-1） | 112 | 0 | 0 |
| 阶段 2 步骤 1（仅加 FF-2 断言） | **124** | **2** | **1** |
| 阶段 2 步骤 3（加 FF-2 源码修复） | **124** | **0** | **0** |

**断言只增不减**：106 → 112 → 124。**没有任何失败断言被删除或弱化。**

---

## 6. 兼容性影响

| 维度 | 影响 |
| --- | --- |
| 可观察行为 | `start()` 返回 `true` 时 `status().lastSocketError` 由"可能残留旧值"变为"必为 0"。**只影响诊断字段**；`bound` / `port` / 计数器 / 时间戳 / 绑定本身**均不变** |
| 失败路径 | **完全不变**：两条 `return false` 路径仍写入 `SocketAlreadyBoundError`；`stop()` 仍保留粘性错误 |
| 生产调用点 | **无需修改**。`Appmain.cpp:2096` / `:8178` 的 `Network.start()` 无参语义不变；`:8183` 的 `Network.stop()` 未受影响 |
| 无参数调用语义 | 不变（`start(28960, 0)`） |
| 默认绑定地址 | 不变（`INADDR_ANY`） |
| 协议常量 / ABI / RVA / 机器码前缀 / 启动链 / S2-S3 | **不变** |
| 既有断言回归 | `[7/8]` 粘性错误、`[8/8]` 占用端口、`[C-3]` 日志、`[simulated-close-failure]` **全部仍 PASS**（见 124/0） |
| 接口签名 | **未变**（仍是 `bool start(std::uint16_t, std::uint32_t)`；未新增/删除任何参数或成员） |

**无接口扩大、无 ABI 变更、未触碰客户端运行时。**

---

## 7. 未覆盖的真实 OS 故障场景

| 场景 | 为什么未覆盖 |
| --- | --- |
| 真正重绑（`stop()` 后 `start()`）成功时清除粘性错误 | `[6/8]` 已覆盖该路径并断言 `lastSocketError == 0`；但它走的是 `status_ = {}`，与本项修复的两条早退路径不同源 |
| 并发 `start()`/`stop()` 交错下的错误码竞态 | `mutex_` 保护了 `start()`/`stop()`，但**无并发用例** |
| `NET_Frame()` / `NET_SendPacket()` 并发写入 `lastSocketError` | 这两条路径会在每次收发时覆盖该字段（`:108`、`:167`）。**本修复不改变该行为**，但也**未验证**并发下"成功 start 清除"的可见性——严格说这是"最后写入者获胜"的既有语义 |
| `getsockname` 失败导致地址无法确认时的错误码 | 该分支写入 `SocketAlreadyBoundError`（`:46`），但 `getsockname` 在有效 socket 上失败**不可稳定复现** |

> 最后一条值得单列：`NET_SendPacket()` 每次发送都会把 `status_.lastSocketError` 设为 `peerStatus.lastSendError`（成功时为 0，失败时为真实错误）。因此"成功 start 清除"这一保证在**后续收发之后**会被再次覆盖。这是**既有设计**（粘性错误 = 最近一次 socket 操作的结果），本修复**未改变**它，但契约措辞现在只描述 `start()` 自身的返回语义，不再暗示该字段长期保持 0。

---

## 8. 阶段验收核对

| 验收项 | 结果 |
| --- | --- |
| 运行相关测试并记录退出码 | ✅ 4 个目标全部 exit 0（见 §5） |
| `git diff --check` | ✅ exit **0** |
| 检查修改文件及差异 | ✅ 本阶段修改 2 个文件（`sv_network_mp.{cpp,hpp}`）+ 1 个测试文件；差异见 `ff2_only.diff` / `ff2_only_hpp.diff` |
| 受保护常量 / ABI / 启动链 / S2-S3 未变 | ✅ 见 [T1_FF1_PORT_RELEASE_REPORT.md](T1_FF1_PORT_RELEASE_REPORT.md) §8 的哈希表（本轮复核仍全部相等） |
| 记录文件哈希与日志路径 | ✅ 见 §9 |
| 未触发 `ol_deploy` | ✅ `build\stage` mtime 仍为 2026-10-09 17:01:07 |
| 未提交 Git | ✅ HEAD 仍为 `2a75bdd` |

---

## 9. 文件哈希与日志（阶段 2 结束后）

| 文件 | 字节 | SHA-256 |
| --- | --- | --- |
| `src/game_server/server_mp/sv_network_mp.cpp` | 7,382 | `EF4E209BDD9EFDCD5A1F7F69B3789E77852FD98C1371D7C1154677EEBFF19B60` |
| `src/game_server/server_mp/sv_network_mp.hpp` | 4,808 | `53E5907AE4AFD9251A2192DB2634D88223F6037DB57D772DCC7A081D4E8612C1` |
| `tests/game_server/TransportLifecycleTests.cpp` | 32,859 | `FA67AE5B9C6D222CB3B8630D0EEA3D143A860A5E4C55753EB0951A7650A4C8AD` |
| `src/game_server/win32/win_net.cpp`（**未改**） | 9,054 | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` |
| `src/game_server/win32/win_net.hpp`（**未改**） | 2,642 | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` |
| 测试 exe（最终） | 3,830,272 | `14C13963223F3E3361A8D691DA6D6E742A4DF75A286EBB1FDC4130141E482DEB` |

| 日志 | 路径 |
| --- | --- |
| FF-2 断言在**未修复**实现上的失败证据 | [\_t1_fix_evidence\\phase2a_ff2_assertions_before_fix.log](_t1_fix_evidence/phase2a_ff2_assertions_before_fix.log) |
| FF-2 修复后的强制重建 + 运行 | [\_t1_fix_evidence\\phase2b_ff2_after_fix.log](_t1_fix_evidence/phase2b_ff2_after_fix.log) |
| 相关目标构建与运行 | [\_t1_fix_evidence\\phase2c_related_targets.log](_t1_fix_evidence/phase2c_related_targets.log) |
| 仅 FF-2 的源码差异 | [\_t1_fix_evidence\\ff2_only.diff](_t1_fix_evidence/ff2_only.diff) · [\_t1_fix_evidence\\ff2_only_hpp.diff](_t1_fix_evidence/ff2_only_hpp.diff) |
| 差异隔离验证脚本 | [\_t1_fix_evidence\\_reconstruct_pre_ff2.py](_t1_fix_evidence/_reconstruct_pre_ff2.py) |

---

## 10. 关联交付

- [T1_FF1_PORT_RELEASE_REPORT.md](T1_FF1_PORT_RELEASE_REPORT.md) — FF-1 实施结果
- [T1_FF4_DESTRUCTOR_REVIEW.md](T1_FF4_DESTRUCTOR_REVIEW.md) — FF-4 可行性审查（**未实施**）
- [T1_FF3_ERROR_CODE_COMPATIBILITY.md](T1_FF3_ERROR_CODE_COMPATIBILITY.md) — FF-3 兼容性分析（**未实施**）
