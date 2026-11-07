# T1_FF1_PORT_RELEASE_REPORT — FF-1 OS 层端口释放回归测试

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（唯一活动基准；D 只读冻结）
**授权范围**：本阶段只修改测试文件。**生产 socket 代码零字节改动。**
**结果**：**已实施 · 构建 exit 0 · 运行 exit 0 · `checks=112 failures=0`**

---

## 0. 阶段 0 基线（实施前记录）

| 项 | 值 |
| --- | --- |
| HEAD | `2a75bdd8872bb9f54006382a924c3006ec9affc2` |
| 分支 | `OLfinal-live` |
| 与上游 | `0 behind / 8 ahead` |
| `git status --porcelain` 条数 | **11**（8 M + 3 ??：T-1 测试 + 2 个 P1-4 工具） |
| `git diff --check` | exit **0** |
| D 工作树 | HEAD 同 F，6 条状态，**未触碰** |

**五个 T-1 文件（实施前）**：

| 文件 | SHA-256 |
| --- | --- |
| `src/game_server/server_mp/sv_network_mp.cpp` | `AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6` |
| `src/game_server/server_mp/sv_network_mp.hpp` | `A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915` |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` |
| `tests/game_server/TransportLifecycleTests.cpp` | `FA6A2760B73BBE52B377178C10BAA64390ADC43522A97D455070DE79DBE7DE94` |

**测试可执行文件（实施前）**：3,826,176 B · 2026-10-10 11:58:29 · `4BE2180D1856DB6A8CF1BBD831001BE8C059E2A519582A5DAED99BE7E5A18468`

**原始测试日志与退出码**：`_batch10_evidence/T1_rerun_forced.log` → `BUILD exit=0` · `checks=106 failures=0` · `run exit=0`

**生产调用点与接口声明（实施前核对，未变）**：

| 项 | 位置 |
| --- | --- |
| `Network.start()`（无参） | `src/game_server/Appmain.cpp:2096`（ConfigureSession 路径） |
| `Network.start()`（无参） | `src/game_server/Appmain.cpp:8178`（`CODOL_GameServerSetEnabled(true)`） |
| `Network.stop()`（消费返回值） | `src/game_server/Appmain.cpp:8183` |
| `bool start(std::uint16_t port = 28960, std::uint32_t bindAddress = AnyIpv4Address)` | `src/game_server/server_mp/sv_network_mp.hpp` |
| `bool stop()` | 同上 |
| `NetUdpSocket` 唯一长生命周期实例 | `SvUdpTransport::socket_`（`sv_network_mp.hpp:93`） |

**一致性核对**：实际工作树与既有报告**完全一致**（HEAD、状态条数、五个哈希、exe 哈希、日志断言数全部吻合）。**无需停止。**

---

## 1. 缺陷与修复目标

**缺陷**：`stop()` 的 5 条断言全部读 `SvNetworkStatus`（内部记账）。一个"只把状态清零、却不 `closesocket`"的 `stop()` 会让它们**全部通过**——测试从未证明操作系统真的释放了端口。

**目标**：增加一条**真实 socket 行为**的回归测试，使"未释放"必然导致失败。

---

## 2. 实施内容（仅测试文件）

### 2.1 在 `testStopClearsState` 中记录端口并做重绑探针

```diff
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
+        // OS-level release. Everything above reads SvNetworkStatus, which is
+        // internal bookkeeping: a stop() that zeroed those fields without
+        // closing the handle would pass every one of them. A fresh socket must
+        // be able to take the EXACT port the transport held. This transport's
+        // socket never sets SO_REUSEADDR (win_net.cpp sets only SO_BROADCAST),
+        // so a still-live binding makes this bind fail with WSAEADDRINUSE and
+        // success is proof that the OS released the endpoint.
+        // probe is a local: every exit path from here releases it via
+        // ~NetUdpSocket, and a failed NET_IPSocket has already closed its own
+        // handle internally.
+        NetUdpSocket probe;
+        require(
+            probe.NET_IPSocket(boundPort, LoopbackIpv4),
+            "the OS released the port the transport held");
     }
```

**逐条对应任务要求**：

| 要求 | 实现 |
| --- | --- |
| 1. 通过 loopback 绑定一个测试独占的端口 | `transport.start(0, LoopbackIpv4)` —— 端口 0 + 127.0.0.1，端口由 OS 独占分配 |
| 2. 记录实际绑定端口 | `const auto boundPort = transport.status().port;`（该值来自 `getsockname`） |
| 3. 调用 `stop()` | `transport.stop();` |
| 4. 新 socket 在相同地址、相同端口重绑 | `NetUdpSocket probe; probe.NET_IPSocket(boundPort, LoopbackIpv4)` |
| 5. 清理所有 socket，所有退出路径释放资源 | 全部为**局部对象**（`transport`、`probe`），由 `~NetUdpSocket` → `close()` 释放；`NET_IPSocket` 的每条失败路径内部已 `close()` 自己的句柄。**无裸句柄、无手动分支清理、无早期 `return`** |
| 6. 不依赖 `SO_REUSEADDR` 掩盖未释放 | 见 §3 —— 该 socket 上**从未设置** `SO_REUSEADDR` |
| 7. 反例校验 | 见 §4 |

### 2.2 新增探针自检用例（反例校验）

```cpp
    // FF-1 counter-example. The probe above is only meaningful if a socket that
    // is STILL HELD really does block a rebind. This test double binds a port and
    // deliberately never releases it, so the same probe must FAIL here. Without
    // this check a passing probe could mean "the OS always allows it" rather than
    // "stop() released the endpoint".
    void testProbeRejectsAStillHeldPort()
    {
        std::cout << "[probe-self-check] a still-held port cannot be taken\n";
        NetUdpSocket holder;
        require(holder.NET_IPSocket(0, LoopbackIpv4), "the holder binds an ephemeral port");
        const auto heldPort = holder.port();
        require(heldPort != 0, "the holder has a non-zero port");

        NetUdpSocket probe;
        const auto stolen = probe.NET_IPSocket(heldPort, LoopbackIpv4);
        require(
            !stolen,
            "a still-held port refuses a second bind, so the release probe discriminates");
        require(
            probe.lastError() != 0,
            "the refusal carries a real socket error");
        std::cout << "       holder port=" << heldPort
                  << " second bind refused=" << (stolen ? "no" : "yes")
                  << " lastError=" << probe.lastError() << '\n';
        // holder and probe go out of scope here; each releases its own handle
        // through ~NetUdpSocket, including on the early-return path.
    }
```

并在 `main()` 中于 `testStopClearsState();` 之后注册 `testProbeRejectsAStillHeldPort();`。

**设计说明**：任务要求的"测试替身故意保留原 socket"由 `holder` 承担——它绑定端口后**不做任何释放**，因此**同一个探针机制**在这里必须失败。这在不修改任何生产代码的前提下证明了探针的判别力（授权明确要求本阶段不得改动生产 socket 代码）。

---

## 3. 为什么该探针有效（`SO_REUSEADDR` 核查）

任务要求"不依赖 `SO_REUSEADDR` 掩盖旧 socket 未释放的问题"。实测核查：

| 位置 | 是否设置 `SO_REUSEADDR` |
| --- | --- |
| `src/game_server/win32/win_net.cpp`（`NetUdpSocket::NET_IPSocket`） | **否**。唯一 `setsockopt` 是 `SO_BROADCAST`（`:92-105`） |
| `src/backend/Demonware/LanDiscovery.cpp:99` | **是**，但那是**后端 LAN 发现 socket**，与 `NetUdpSocket` 无关 |
| 其余 `src/` | 0 命中 |

⇒ T-1 传输的 socket **不共享端口**，所以"活着的旧绑定"必然使第二次 `bind` 失败。**探针结论不依赖任何复用标志。**

**运行时的独立确认**：本轮日志出现两次 `udp init failed op=bind ... error=10048`（`WSAEADDRINUSE`）——一次来自既有 `[8/8]`，一次来自新增自检用例。这与 `C-3` 用例的既有记录一致。

---

## 4. 反例校验结果

| 校验 | 手段 | 结果 |
| --- | --- | --- |
| 探针能识别"仍被持有"的端口 | 新增 `[probe-self-check]` 用例：`holder` 故意不释放，第二个 socket 尝试同端口 | ✅ `a still-held port refuses a second bind, so the release probe discriminates` **通过**；`lastError=10048` |
| 探针在 `stop()` 真正释放后成功 | `[4/8]` 新断言 | ✅ `the OS released the port the transport held` **通过** |

**注意（诚实标注）**：任务描述的另一种反例形式——"临时把生产 `stop()` 改成不 `close()`，测试必须失败"——本轮**未执行**，因为授权明确写了"此阶段不得修改生产 socket 代码"。上面用**同一探针机制 + 一个故意不释放的测试替身**达成了等价判别力证明，且完全没有触碰生产代码。若审阅者仍要求生产代码变异验证，需**单独授权一次临时变异**（变异后必须逐字节恢复并核对哈希）。

---

## 5. 构建与运行结果

| 项 | 值 |
| --- | --- |
| 命令 | `xmake f` → `xmake build ol_transport_lifecycle_tests`（**显式命名目标**，未触发 `ol_deploy`） |
| 构建 | `CONFIGURE exit=0` · `BUILD exit=0` · 15.39 s |
| 编译单位 | `tests\game_server\TransportLifecycleTests.cpp`（**仅此一个**；生产源码未被本阶段重编） |
| 产物 | 3,827,712 B · 2026-10-10 12:49:04 · `E33E706AA452020CBAA9AFBE1D4813665AEAF8A7E1D1FEFCC1CD059F1C254C88` |
| 运行 | `run exit=0` · **`checks=112 failures=0`** |
| 日志 | `_t1_fix_evidence/phase1_ff1_build_run.log` |

**断言数变化**：106 → **112**（+6）

| 来源 | 新增断言 |
| --- | --- |
| `[4/8]` | `an ephemeral port was assigned` · `the OS released the port the transport held` |
| `[probe-self-check]` | `the holder binds an ephemeral port` · `the holder has a non-zero port` · `a still-held port refuses a second bind…` · `the refusal carries a real socket error` |

---

## 6. 兼容性影响

| 维度 | 影响 |
| --- | --- |
| 生产源码 | **零字节改动**（本阶段只改测试文件） |
| 无参数调用语义 | 不变（`Network.start()` ≡ `start(28960, 0)`） |
| 默认绑定地址 | 不变（`AnyIpv4Address == 0 == INADDR_ANY`） |
| 协议常量 / ABI / RVA / 机器码前缀 / 启动链 / S2-S3 默认值 | **不变**（见 §8 哈希核对） |
| 新增系统资源 | 两个临时 UDP socket（`probe` 与 `holder`），函数结束即析构；端口均为临时端口，**不占用任何正式端口** |
| 副作用 | 在 exe 目录追加一行 `CodolGameServer.log`（既有 `RuntimeLog` 行为，非本阶段引入） |

---

## 7. 未覆盖的真实 OS 故障场景

| 场景 | 为什么未覆盖 |
| --- | --- |
| `closesocket` 在 `stop()` 中**真实**失败 | 无法在不破坏环境的前提下稳定复现；只能用 IAT 注入模拟（既有 `[simulated-close-failure]` 用例，**非真实 OS 失败**） |
| 端口被**另一个进程**抢占后 `stop()` | 本用例占的是自己刚释放的端口，不涉及跨进程竞争 |
| 临时端口池耗尽 | 需要制造系统级资源枯竭，禁止 |
| 并发 `start()`/`stop()` 与 `NET_Frame()` | `mutex_` 存在但从未被竞争；无并发用例 |
| 本机是否曾出现 `SO_REUSEADDR` 被**其它**组件间接设置 | 已静态核查（§3）；无运行时断言 |

---

## 8. 阶段验收核对

| 验收项 | 结果 |
| --- | --- |
| 运行相关测试并记录退出码 | ✅ `run exit=0` · `checks=112 failures=0` |
| `git diff --check` | ✅ exit **0** |
| 检查修改文件及差异 | ✅ 本阶段唯一修改：`tests/game_server/TransportLifecycleTests.cpp`（未跟踪文件）；差异见 `_t1_fix_evidence/ff1_ff2_tests.diff` |
| 正式协议常量 / RVA / ABI / 启动链 / S2-S3 默认值未变 | ✅ 见下表 |
| 记录文件哈希与日志路径 | ✅ 见 §9 |
| 未触发 `ol_deploy` | ✅ `build\stage` mtime 仍为 2026-10-09 17:01:07 |
| 未提交 Git | ✅ HEAD 未变，无提交、无推送 |

**受保护文件哈希（本阶段前后均未变）**：

| 文件 | SHA-256 |
| --- | --- |
| `src/game_server/EngineBindings.hpp` | `9ACE87313419DB58DC41EE6F4F38612A0970525BAF24CBF924462AD1BA88C72E` |
| `src/game_server/EngineBindings.cpp` | `E624A8A1AFF2BB59F57CCD1D37BF1FD609D0573FFD505DB5BD6CD32C3E07465B` |
| `src/game_server/ClientProcessPatches.cpp` | `E81D760A6B362076C346471EAC89F6841BF43B369BDA360E5E9180378C09B885` |
| `src/game_server/Appmain.cpp` | `407B6F9896A5F0354625B9D0724A3519BA4ACEDDFC36BA34CE879F79100BE7B1` |
| `xmake.lua` | `5C54E3585817E908AD32F7D2A36FD69A6130B8964591C25775A48A23605B6FE8` |

---

## 9. 文件哈希与日志

| 文件 | 字节 | SHA-256 |
| --- | --- | --- |
| `tests/game_server/TransportLifecycleTests.cpp`（阶段 1 后） | 32,859 | `FA67AE5B9C6D222CB3B8630D0EEA3D143A860A5E4C55753EB0951A7650A4C8AD` |
| 测试 exe（阶段 1 后） | 3,827,712 | `E33E706AA452020CBAA9AFBE1D4813665AEAF8A7E1D1FEFCC1CD059F1C254C88` |

> 阶段 2 又修改了同一测试文件，因此**当前**哈希为 `FA67AE5B…`（见 [T1_FF2_ERROR_STATE_REPORT.md](T1_FF2_ERROR_STATE_REPORT.md)）。上表记录的是**阶段 1 结束时刻**的值。

| 日志 | 路径 |
| --- | --- |
| 阶段 1 构建 + 运行 | [\_t1_fix_evidence\\phase1_ff1_build_run.log](_t1_fix_evidence/phase1_ff1_build_run.log) |
| 测试文件差异（FF-1 + FF-2，对比阶段 0 基线副本） | [\_t1_fix_evidence\\ff1_ff2_tests.diff](_t1_fix_evidence/ff1_ff2_tests.diff) |

---

## 10. 关联交付

- [T1_FF2_ERROR_STATE_REPORT.md](T1_FF2_ERROR_STATE_REPORT.md) — FF-2 实施结果（含失败前证据）
- [T1_FF4_DESTRUCTOR_REVIEW.md](T1_FF4_DESTRUCTOR_REVIEW.md) — FF-4 可行性审查（**未实施**）
- [T1_FF3_ERROR_CODE_COMPATIBILITY.md](T1_FF3_ERROR_CODE_COMPATIBILITY.md) — FF-3 兼容性分析（**未实施**）
