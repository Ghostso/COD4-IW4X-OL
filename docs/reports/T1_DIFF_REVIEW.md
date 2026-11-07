# T1_DIFF_REVIEW — 两份 T-1 实现与测试的逐项差异及采用裁定

**日期**：2026-10-10
**比较对象**：F = `F:\桌面\ol\ol-mod-olfinal`（活动基准） vs D = `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal`（冻结副本）
**共同 HEAD**：`2a75bdd8872bb9f54006382a924c3006ec9affc2`（`OLfinal-live`）
**依据**：仅以两树**当前实际文件**为准，不以任何报告描述代替源码验证。
**本轮未修改、未复制、未覆盖任何被比较文件。**

---

## 1. 采用版本裁定

| 范围 | 采用 | 理由（一句话） |
| --- | --- | --- |
| `src/game_server/server_mp/sv_network_mp.{hpp,cpp}` | **F** | D 的 `start()` 是**人工回退**的 pre-T-1 体，且被 D 自己的注释标为"REGRESSION HARNESS (isolated copy only)" |
| `src/game_server/win32/win_net.{hpp,cpp}` | **F** | D 缺少 `boundAddress()` 与初始化失败日志，且 F 的差异是 D 的超集 |
| `xmake.lua` | **两树相同** | 逐字节同一哈希，无需裁定 |
| `src/game_server/Appmain.cpp` | **F** | D 完全未跟进；F 的改动是 T-1 契约的上层接线 |
| `src/game_server/FrameHook.{hpp,cpp}` | **F** | D 完全未跟进；F 的改动**独立于 T-1**（帧钩子可观测性） |
| `tests/game_server/TransportLifecycleTests.cpp` | **F** | F 是 D 的**严格超集**：新增 349 行、删除 0 行、新增 4 个用例 |

**总裁定：以 F 为唯一 T-1 实现与测试基准；D 只保留为只读历史副本。**

---

## 2. 逐文件差异

索引 blob（HEAD 版本）在两树完全一致，因此下列差异**全部**来自未提交工作区。

### 2.1 `src/game_server/server_mp/sv_network_mp.cpp`

| | F | D |
| --- | --- | --- |
| 工作区 SHA-256 | `AF93F7C8…EEC58AA6` | `CA34DAF5…E22E15324` |
| 字节 / 行 | 6,941 / 196 | 5,705 / 169 |
| HEAD 索引 blob | `60505309651af0a23d710070085333cec925b088` | 同 F |
| `git diff` 规模 | +55 / −? | +22 / −? |

**F 的 `start(port, bindAddress)` 语义（唯一权威实现）**：

```text
socket 已打开时：
  port == 0                      -> return true，绑定/计数器/时间戳原样不动；请求的地址不生效
  socket_.port() != port         -> return false，lastSocketError = SocketAlreadyBoundError
  port 相同、地址相同(getsockname 实测) -> return true
  port 相同、地址不同 或 getsockname 失败 -> return false，lastSocketError = SocketAlreadyBoundError
socket 未打开时：
  status_ = {}; peerStatus_.clear(); NET_IPSocket(port, bindAddress)
  失败 -> status_.lastSocketError = socket_.lastError(); return false
  成功 -> bound = true; port = socket_.port(); return true
```

**D 的 `start()`（回退体）语义**：

```text
socket 已打开 且 socket_.port() == port -> return true
否则（含 port == 0、含端口不同）：
  socket_.close();          // 无条件拆掉活绑定
  status_ = {}; peerStatus_.clear();
  NET_IPSocket(port, bindAddress)   // 重新绑定到新端口/新地址
```

D 文件内自带免责注释（D 的 `sv_network_mp.cpp` 第 20-22 行）：

> `// REGRESSION HARNESS (isolated copy only): this is the pre-T-1 start() body,`
> `// kept with the new two-argument signature so the E-1 test compiles.`

**差异后果**：D 的 `start(不同端口)` 会**静默拆掉活绑定并重新绑定**，因此对 D 自己的测试 [3/8] 与 [7/8] 必然返回 `true`，与测试期望相反。即 **D 当前状态是"必然失败的组合"**，不是"可用的 pre-T-1 基线"。

### 2.2 `src/game_server/server_mp/sv_network_mp.hpp`

| | F | D |
| --- | --- | --- |
| 工作区 SHA-256 | `A5BBE547…47F40915` | `3AF3104E…C9F9B1B6` |
| 字节 / 行 | 4,357 / 105 | 3,291 / — |

| 项 | F | D |
| --- | --- | --- |
| `start()` 签名 | `bool start(uint16_t port = 28960, uint32_t bindAddress = AnyIpv4Address)` | 同签名 |
| `stop()` 返回 | `bool stop()`（显式标注**故意不加** `[[nodiscard]]`） | `void stop()` |
| 契约文档 | 明确写出 port==0 / 同端口同地址 / 冲突 三分支 + 地址按 getsockname 实测 + `lastSocketError` 保留语义 | 只写 port==0 / 同端口 / 其他非零端口；**未写地址维度** |
| 失败 stop 语义 | 文档化：句柄仍活，bound/port/计数器原样，`lastSocketError` 承载失败 | 只有一句简述，无返回值 |

**差异后果**：D 的头文件**无法表达**"同端口不同地址"这一冲突类别，这正是 F 的 A-1 用例所覆盖的语义。

### 2.3 `src/game_server/win32/win_net.cpp`

| | F | D |
| --- | --- | --- |
| 工作区 SHA-256 | `3A34D953…EABAA9A14` | `B4850F93…0F8413EB` |
| 字节 / 行 | 9,054 / 274 | 6,811 / 222 |

| 能力 | F | D |
| --- | --- | --- |
| `static_assert(SocketAlreadyBoundError == WSAEALREADY)` | ✅ | ✅ |
| `writeIpv4()` / `logInitializationFailure()`（C-3） | ✅ | ❌ |
| `WSAStartup` / `socket` / `ioctlsocket` / `setsockopt` / `bind` / `getsockname` 六处失败日志 | ✅ | ❌ |
| `NET_IPSocket` 入口 `if (!close()) return false;` | ✅ | ✅ |
| `bindAddress` 主机字节序 → `htonl` | ✅ | ✅ |
| 成功日志打印实际绑定地址 | ✅ | ✅ |
| `close()` 返回 `bool`，失败保留句柄 | ✅ | ✅ |
| `boundAddress()`（getsockname → `std::optional<uint32_t>`） | ✅ | ❌ |

**差异后果**：D 的 `start()` **无法**做地址比对（没有 `boundAddress()`），且初始化失败只能靠 `lastError()` 数字，无操作名/请求地址/端口（F 的 C-3 用例针对此点）。

### 2.4 `src/game_server/win32/win_net.hpp`

| | F | D |
| --- | --- | --- |
| 工作区 SHA-256 | `8F0FF318…451F5FBC1` | `9F4A5058…58AB8851` |

| 项 | F | D |
| --- | --- | --- |
| `AnyIpv4Address = 0` | ✅ | ✅ |
| `SocketAlreadyBoundError = 10037` | ✅ | ✅ |
| `NET_IPSocket(port, bindAddress = AnyIpv4Address)` | ✅ | ✅ |
| `bool close()` | ✅ | ✅ |
| `std::optional<uint32_t> boundAddress() const` | ✅ | ❌ |
| `#include <optional>` | ✅ | ❌ |

### 2.5 `xmake.lua`

| | F | D |
| --- | --- | --- |
| SHA-256 | `5C54E3585817E908AD32F7D2A36FD69A6130B8964591C25775A48A23605B6FE8` | **同一哈希** |
| 字节 / 行 | 14,179 / — | 14,179 / — |

两树新增同一目标（`xmake.lua` 第 326-337 行，注释在 324-325）：

```lua
target("ol_transport_lifecycle_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)          -- 不进入默认构建
    set_rundir(os.projectdir())
    add_files(table.unpack(game_server_core))
    add_headerfiles(table.unpack(game_server_headers))
    add_files("tests/game_server/TransportLifecycleTests.cpp")
    add_includedirs("src/game_server")
    add_packages("openssl", "lua", "nlohmann_json")
    add_links("ws2_32")
    add_tests("default", {rundir = os.projectdir()})
```

**边界核对**：
- `set_default(false)` ⇒ 不会随默认构建触发；`ol_deploy`（第 214-217 行，`set_default(true)`）不在其依赖闭包内。
- 目标只链接 `game_server_core`，**不含** `Appmain.cpp` / `EngineBindings.cpp` / `FrameHook.cpp` 等 9 个插件专属文件，因此**不会**触发任何 RVA/前缀校验或宿主身份门禁。

### 2.6 `src/game_server/Appmain.cpp`（仅 F 修改）

| | F | D |
| --- | --- | --- |
| SHA-256 | `407B6F98…100BE7B1` | `69FDC488…D11C43CC`（**= HEAD，未修改**） |
| 字节 / 行 | 481,281 / 9,546 | 479,827 / 9,519 |
| 索引 blob | `c1f6f39fb46c58cdfae45ab65dc90e43d4ee34fc` | 同 F |

F 的三处修改：

| 位置（F） | 内容 | 与 T-1 的关系 |
| --- | --- | --- |
| 约 7152-7169 | 客户端分支：`installFrameHook()` 返回 `false` 不再等同失败；新增 `isFrameHookInstalled()` 作为真相来源；日志区分 `installed` / `already-installed` / `failed` | **间接**：只影响帧钩子上层状态报告，不改变 socket 生命周期 |
| 约 8132-8147 | 专用服分支：同样的三态修正 | 同上 |
| 约 8180-8201 | `CODOL_GameServerSetEnabled(false)`：捕获 `Network.stop()` 的布尔返回；若为 `false`（socket 未能释放）则记录 `game server disable failed: udp transport is still bound` 并 **返回 false**，不再假装已停止 | **直接**：这是 T-1 的 `stop()→bool` 契约在唯一生产调用点的接线 |

**关键**：第三处是**唯一**依赖 T-1 新返回值的生产代码。它把"关闭失败"从"静默成功"改为"显式失败"，是 T-1 语义变化唯一被生产侧消费的地方。

### 2.7 `src/game_server/FrameHook.hpp` / `FrameHook.cpp`（仅 F 修改）

| 文件 | F SHA-256 | D SHA-256 | F 行 / D 行 |
| --- | --- | --- | --- |
| `FrameHook.hpp` | `6EDF4F9A…EF5ACF5` | `EAD8A036…EBEA6B4F`（= HEAD） | 27 / 12 |
| `FrameHook.cpp` | `1CA962D7…BE8008D8A` | `D7E39818…184B2DCF26`（= HEAD） | 117 / 74 |

F 的修改内容：

1. 新增只读访问器 `bool isFrameHookInstalled()`，实现为 `OriginalComFrame != nullptr`。
2. `installFrameHook()` 的**守卫顺序不变**（`!bindings.valid()` → `!callback` → `OriginalComFrame`），但每条拒绝路径改为**具名原因**：`invalid-bindings` / `null-callback` / `already-installed` / `trampoline-allocation-failed` / `protect-failed`，并保留系统原始错误码（`VirtualProtect` 失败前先捕获 `GetLastError()`，避免被 `VirtualFree` 覆盖）。
3. `FrameHook.hpp` 新增进程级契约注释：钩子**每进程至多安装一次**；失败可重试（闩锁保持清空）；成功**永不撤销**（无 uninstall）；**禁止**通过重置 `Appmain` 的 `Installed` 标志或清空 `OriginalComFrame` 来"模拟重试"——已打补丁的 `Com_Frame` 入口仍会穿过该闩锁，清空它会调用空指针。

**与 T-1 的关系：无直接关系。** 两者共享"区分失败与幂等成功"的设计动机（D1 的帧钩子三态 与 T-1 的 start() 三态），但：
- 不共享任何数据结构、常量或调用点；
- `FrameHook` 触及 `ComFrameRva = 0x0FEA20` 的**实际打补丁**路径，属于受保护边界；T-1 完全不碰 RVA/字节前缀/ABI；
- 两者的测试归属不同：T-1 有独立测试目标，`FrameHook` 属于**零直接测试**的 9 个插件专属文件之一（Batch 10 报告 §6.2 的 R1 风险）。

**裁定**：`FrameHook` 的三处修改与 T-1 一并保留在 F，但**必须分开记录、分开验收**，不得用 T-1 的通过结果推断 `FrameHook` 正确。

---

## 3. 生产调用点核对（对应任务 §三.7）

在 F 的 `src/` 全树检索：

| 调用点 | 形式 | 语义是否变化 |
| --- | --- | --- |
| `Appmain.cpp:2096` | `Network.start()`（ConfigureSession 路径） | **否**。无参 ⇒ `port=28960`、`bindAddress=AnyIpv4Address=0`，与改造前的 `start(28960)` + 硬编码 `htonl(INADDR_ANY)` 完全一致 |
| `Appmain.cpp:8178` | `Network.start()`（`CODOL_GameServerSetEnabled(true)`） | **否**。同上 |
| `Appmain.cpp:8183` | `const auto transportStopped = Network.stop();` | **是（唯一一处）**。由忽略返回值改为消费返回值；失败时上层返回 `false` |

其它核对：
- `SvUdpTransport` 的 `start` / `stop` 在整个 `src/` 中**只有上述 3 个调用点**（其余 `\.start(` / `\.stop(` 命中属于 `ClientSessionBridge` / `SharedRoomHost` / `localnetworking` 的**同名不同类**，不相关）。
- `NET_IPSocket` 只有 1 个调用者（`sv_network_mp.cpp:53`），且已改为双参调用。
- `NetUdpSocket::close()` 的调用者全部在 `win_net.cpp` 内部（析构、`NET_IPSocket` 入口、各失败清理路径）与 `sv_network_mp.cpp:66`。`void → bool` 对忽略返回值的旧调用**源码兼容**。

**结论**：接口变化**不改变**任何现有无参数调用语义；唯一行为变化是 `SetEnabled(false)` 在 socket 释放失败时改为返回 `false`。

---

## 4. 两份 `TransportLifecycleTests.cpp` 的逐项差异

### 4.1 规模与结构

| | F | D |
| --- | --- | --- |
| 路径 | `tests/game_server/TransportLifecycleTests.cpp`（**未跟踪**） | 同名同路径（**未跟踪**） |
| SHA-256 | `FA6A2760B73BBE52B377178C10BAA64390ADC43522A97D455070DE79DBE7DE94` | `00EBDB2C48065A3CEEC96C1A442774DCCC7BDD62634B57445D813230458D96CA` |
| 字节 / 行 | 27,504 / 639 | 10,662 / 255 |
| 用例函数 | **13** | **9** |
| `require(...)` 断言 | **106** | **49** |
| F vs D 行级差异 | **+349 / −0** | — |

**关键事实：F 是 D 的严格超集。** 差异补丁的 `removed=0`，即 D 的每一行都原样存在于 F 中；F 只在 3 个位置插入内容（`@@ -5,6 +5,11 @@`、`@@ -12,7 +17,13 @@`、`@@ -31,6 +42,157 @@`、`@@ -236,6 +398,224 @@`、`@@ -250,6 +630,10 @@`）。因此**不存在"两版互有取舍"的情况**——采用 F 不会丢失 D 的任何断言。

### 4.2 用例级对照

| # | 用例 | D | F | 说明 |
| --- | --- | --- | --- | --- |
| 1 | `testLoopbackEphemeralBinding` | ✅ | ✅ | 逐字相同 |
| 2 | `testRepeatedStartKeepsBinding` | ✅ | ✅ | 逐字相同；含真实 `NET_SendPackets` |
| 3 | `testDifferentPortDoesNotDisturbBinding` | ✅ | ✅ | 逐字相同 |
| 4 | `testStopClearsState` | ✅ | ✅ | 逐字相同 |
| 5 | `testRepeatedStop` | ✅ | ✅ | 逐字相同 |
| 6 | `testRebindAfterStop` | ✅ | ✅ | 逐字相同 |
| 7 | `testStickyErrorAcrossStop` | ✅ | ✅ | 逐字相同 |
| 8 | `testOccupiedPortFails` | ✅ | ✅ | 逐字相同 |
| 9 | `testDefaultAddressStaysInaddrAny` | ✅ | ✅ | 逐字相同；含真实 loopback 收发 |
| A-1 | `testAddressMustMatchLiveBinding` | ❌ | ✅ | **仅 F**：同端口不同地址必须被拒；反向（INADDR_ANY 绑定 vs 指定地址）也要拒 |
| C-3 | `testInitializationFailureLogging` | ❌ | ✅ | **仅 F**：失败日志须含 `op=bind` / `requested=127.0.0.1:<port>` / `actual=unavailable` / 真实 `error=` 码，且与 `status().lastSocketError` 一致 |
| B-1 | `testStopReturnValue` | ❌ | ✅ | **仅 F**：`stop()` 正常/重复均返回 `true` |
| P1 | `testStopCloseFailureKeepsBinding` | ❌ | ✅ | **仅 F**：受控 `closesocket` 失败（IAT 重定向）后，stop 返回 false、绑定/端口/计数器保留、socket 仍可发、日志追加 `udp transport stop failed op=close error=<code>`、重试 stop 完成清理 |

F 另外新增的**测试脚手架**（不产生断言，但为上述用例所必需）：
- `#define WIN32_LEAN_AND_MEAN` / `NOMINMAX` + `<WinSock2.h>` / `<Windows.h>`（IAT 遍历需要 PE 结构）
- `findCloseSocketIatSlot()`：**按地址**（`iat[i].u1.Function == GetProcAddress(ws2_32,"closesocket")`）定位导入槽，不依赖导入名表布局
- `ScopedCloseSocketFailure`：临时 `VirtualProtect` 改写本模块 IAT，析构时恢复
- `gameServerLogPath()` / `logFileSizeOrZero()` / `readAppendedBytes()`：读取 `<exe>\Ayria\Logs\CodolGameServer.log` 的**追加段**

### 4.3 D 版测试的覆盖与缺陷（静态裁定）

**D 覆盖到的**（9 个用例）：loopback 临时端口绑定、`start(0)` 重复幂等且不丢计数器、不同端口冲突被拒、`stop()` 清零、重复 `stop()` 幂等、`stop()` 后重绑、粘性错误跨 `stop()` 保留、占用端口失败、默认地址仍为 INADDR_ANY（含真实 loopback 收发）。

**D 的缺陷**：

| # | 缺陷 | 证据 |
| --- | --- | --- |
| **DD-1** | **测试与自身源码不自洽**。D 的 [3/8] 与 [7/8] 断言 `!transport.start(differentPort(...))` 且 `lastSocketError == SocketAlreadyBoundError`；但 D 的 `start()` 会无条件 `close()` 后重绑，必然返回 `true`。**D 当前状态若真被构建运行，这两处必然 FAIL** | D 的 `sv_network_mp.cpp` 第 20-40 行（`socket_.close()` 在 :29）vs 测试第 113、173 行 |
| **DD-2** | **完全缺失地址维度**。无"同端口不同地址"用例；因为 D 根本没有 `boundAddress()`，无法实现 | D 的 `win_net.hpp` 无 `boundAddress()` |
| **DD-3** | **完全缺失 `stop()` 返回值用例**。D 的 `stop()` 是 `void`，无法断言释放结果 | D 的 `sv_network_mp.hpp` `void stop();` |
| **DD-4** | **完全缺失 close 失败分支**。`NetUdpSocket::close()` 在 D 中已返回 `bool` 且有失败保留句柄逻辑，但 D 的测试**一次都没触发**该分支 | D 测试全 255 行无 IAT 注入、无失败模拟 |
| **DD-5** | **完全缺失初始化失败日志断言**。D 的 `win_net.cpp` 在该轮次**尚未**加入 `logInitializationFailure` | D 的 `win_net.cpp` 无 `udp init failed` 字符串 |
| **DD-6** | **无"失败 stop 后 socket 仍可用"验证** | 同上 |
| **DD-7** | **9 处 `transport.stop();` 忽略返回值**（`bareStop=9`）。在 D 的 `void stop()` 下无害；但一旦采用 T-1 的 `bool stop()`，这些调用点全部静默忽略失败 | D 测试行 62/104/120/128/145/146/154/164/195 |
| **DD-8** | **D 从未成功构建/运行**（见 [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) §4）。D 的"49 断言 0 失败"记录来自**从 F 复制来的 T-1 二进制** | [_e1_regression.log](_e1_regression.log) 中 `BUILD exit=-1` 紧跟运行；[_e1_regression2.log](_e1_regression2.log) `removed stale copied exe` |

**结论**：D 的测试版本**既不能作为有效基线，也没有产生有效证据**。它唯一的价值是"F 测试的前身"这一历史定位。

### 4.4 F 版测试的覆盖、断言与缺陷

**F 覆盖到的**：D 的全部 9 项 + 地址匹配（A-1）+ 初始化失败日志（C-3）+ `stop()` 返回值（B-1）+ 受控 close 失败（P1）。

**F 版测试的缺陷（可修复项）**：

| # | 缺陷 | 严重度 | 证据 |
| --- | --- | --- | --- |
| **FF-1** | **没有任何用例证明 socket 在 OS 层面真的被释放**。`stop()` 后只断言 `status_.bound == false` / `port == 0`（纯内部状态）。[`testRebindAfterStop`](_batch10_evidence/T1_tests_F.cpp#L313) 用 `start(0)` 重绑，操作系统可能给出**另一个**临时端口，因此不能证明旧绑定已释放 | 中 | F 测试第 313-327 行 |
| **FF-2** | **close 失败分支只由伪造失败覆盖**。[`testStopCloseFailureKeepsBinding`](_batch10_evidence/T1_tests_F.cpp#L556) 通过改写自身 IAT 伪造 `SOCKET_ERROR`，**不是**真实 Windows `closesocket` 失败。测试注释已诚实标注（"It is NOT a genuine Windows closesocket failure"），但报告中不得把它当作真实失败路径证据 | 低（已披露） | F 测试第 45-52、555-556 行 |
| **FF-3** | **`lastSocketError` 契约文档与实现不一致**。头文件写"cleared by the next successful start()"，但 `start()` 在**已打开**时的两条成功早退路径（`port == 0`；同端口同地址）都直接 `return true`，**不清除** `status_.lastSocketError` | 中 | F 的 `sv_network_mp.cpp` 第 30-31、49 行 vs `sv_network_mp.hpp` 第 66-69 行 |
| **FF-4** | **无任何测试覆盖 FF-3 这条路径**。[`testAddressMustMatchLiveBinding`](_batch10_evidence/T1_tests_F.cpp#L442) 调用了 `start(0, AnyIpv4Address)` 并返回 true，但只断言 port/counter，未断言 `lastSocketError` | 中 | F 测试第 441-447 行 |
| **FF-5** | **测试会在 exe 目录下写入真实文件**。P1 用例读取/追加 `<exe>\Ayria\Logs\CodolGameServer.log`（本轮运行后该文件 186,532 B）。这是设计所需，但会污染构建目录，且断言依赖 `RuntimeLog` 的路径约定 | 低 | 运行结果：`game-server log existed-before=true bytes-before=186346` |
| **FF-6** | **`lastSocketError` 混装两类语义**。`SocketAlreadyBoundError = 10037 = WSAEALREADY`（"非阻塞 connect 正在进行"）被用作"已绑定"哨兵，与真实 Winsock 错误共用一个 `int` 字段。`WSAEADDRINUSE(10048)` 才是 OS 对真实端口冲突的答复（[`testOccupiedPortFails`](_batch10_evidence/T1_tests_F.cpp#L344) / C-3 实测到 10048）。调用方无法区分"10037 = 我方合成原因"与"10037 = OS 真实错误" | 低-中 | F 的 `win_net.hpp` 第 24-27 行；运行日志 `error=10048` |
| **FF-7** | **`~NetUdpSocket()` 忽略 `close()` 的失败返回**。析构时若 `closesocket` 失败，句柄泄漏且 `WSACleanup()` 被跳过（`close()` 失败路径提前 return） | 低 | F 的 `win_net.cpp` 第 48-51、153-160 行 |

### 4.5 最小修复建议（**本轮未实施**，仅建议）

> 下列改动**均未执行**。任何一条都要求先获得对 F 源码的修改授权。

| 针对 | 建议 | 影响面 |
| --- | --- | --- |
| **FF-1** | 在 [`testStopClearsState`](_batch10_evidence/T1_tests_F.cpp#L285) 中记录 `stop()` 前的 `status().port`，`stop()` 后用一个新的 `NetUdpSocket` 尝试 `NET_IPSocket(该端口, LoopbackIpv4)`；若旧绑定未释放，该 bind 会以 `WSAEADDRINUSE` 失败。断言 probe 成功 ⇒ 直接证明 OS 级释放 | 仅测试文件；新增 1 个 socket + 3-4 条断言 |
| **FF-3 / FF-4** | 二选一：(a) 在 `start()` 的两条早退成功路径上补 `status_.lastSocketError = 0;`，使实现符合既有文档；或 (b) 修改头文件措辞为"仅在真正重新绑定成功时清除"。并在 A-1 用例中补一条 `lastSocketError` 断言 | (a) 改生产源 2 行 + 测试 1 条；(b) 只改注释 |
| **FF-6** | 把合成哨兵移出 Winsock 错误空间（例如 `0x4F4C4D42` 之类的私有值），或新增独立字段 `lastConflict`。需同步修改 `win_net.hpp` 常量与 A-1/[3/8]/[7/8] 的断言 | 生产源 2 处 + 测试 3 处 |
| **FF-7** | 在析构中显式忽略并记录：`if (!close()) { /* 记录泄漏 */ }`；或在 `close()` 失败路径上仍执行 `WSACleanup()`（但那样会与"保留句柄以便重试"的语义冲突，需先裁定优先级） | 生产源 1-4 行 |
| **FF-2** | 保持现状（已诚实披露）。若将来需要真实失败证据，须在**隔离的一次性探针**中制造，不得在正式测试中伪装 | — |
| **DD-1..DD-8** | **不修复**。按 [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) R2/R8，D 冻结且 E-1 不恢复 | — |

### 4.6 其它跨文件发现（仅登记，未修改）

| # | 发现 | 位置 |
| --- | --- | --- |
| **X-1** | `EngineBindings.hpp` 的注释与常量自相矛盾：注释写"for the `0x57611E31`, `0x0C72A000` CODOL executable only"，紧随其后的常量却是 `ExpectedTimestamp = 0x6096930A` / `ExpectedImageSize = 0x0E5D6000` | F 的 `src/game_server/EngineBindings.hpp:434-439` |
| **X-2** | `ol_deploy` 目标为 `set_default(true)`，而 `config/codol-game-dir.txt` **非空**（`D:\codo_3.19.26.13_fresh\CoD Online`，该目录**不存在**）。任何裸 `xmake` / `xmake build` 都会尝试调用 `tools/distribution/InstallCodolRuntime.ps1` | F 的 `xmake.lua:214-240` |
| **X-3** | 本轮未能找到 `AGENTS.md` 引用的 `../ACTIVE_STATE.md`。在 `F:\桌面\ol`、`D:\BaiduNetdiskDownload\使命召唤OL`、`_e1_regression` 及其两层子目录内检索为 0 命中 | `_e1_regression\ol-mod-olfinal\AGENTS.md` 工作规则段 |

---

## 5. 关联交付

- [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) — 基准裁定与冻结规则
- [T1_ACCEPTANCE_REPORT.md](T1_ACCEPTANCE_REPORT.md) — 实际执行结果
- [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md) — 客户端制品门禁
- [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md) — 归属与哈希清单
- [_batch10_evidence\diff_F_git.patch](_batch10_evidence/diff_F_git.patch) · [_batch10_evidence\diff_D_git.patch](_batch10_evidence/diff_D_git.patch) · [_batch10_evidence\diff_F_vs_D_src.patch](_batch10_evidence/diff_F_vs_D_src.patch) · [_batch10_evidence\diff_T1tests_F_vs_D.patch](_batch10_evidence/diff_T1tests_F_vs_D.patch)
