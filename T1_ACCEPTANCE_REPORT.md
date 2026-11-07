# T1_ACCEPTANCE_REPORT — 传输生命周期测试的覆盖、实际执行结果与未验证项

**日期**：2026-10-10
**被测对象**：F = `F:\桌面\ol\ol-mod-olfinal` 的 **当前实际文件**
**目标**：`ol_transport_lifecycle_tests`（`xmake.lua` 第 326-337 行，`set_default(false)`）
**依据**：源码逐行核对 + 本机**强制重建并运行**一次
**本轮未启动任何游戏进程、未注入、未读进程内存、未部署、未提交 Git。**

---

## 0. 结论速览

| 维度 | 状态 |
| --- | --- |
| 编译 | ✅ **通过**（强制重建 30.171 s，exit 0） |
| 链接 | ✅ 通过（`ol_transport_lifecycle_tests.exe`，3,826,176 B） |
| 运行 | ✅ **exit 0**，`checks=106 failures=0` |
| 真 socket 行为覆盖 | ⚠️ **部分**：有真实 bind/sendto/recvfrom/getsockname/closesocket，但**无**"OS 层绑定已释放"的证明 |
| close 失败分支 | ⚠️ **仅由伪造失败覆盖**（IAT 重定向），非真实 Windows 失败 |
| 生产调用点兼容 | ✅ 通过（3 处调用点，无参语义不变） |
| **T-1 综合裁定** | **通过（有保留）** —— 保留项见 §5 |

> **本轮不接受"编译通过 = 生命周期语义正确"这一等价。** 编译与运行通过只证明"当前实现与当前测试自洽"；§5 列出的未验证项必须单独保留。

---

## 1. 实际执行（本轮，可复核）

### 1.1 命令与日志

| 步骤 | 命令 | 日志 |
| --- | --- | --- |
| 配置 | `xmake f`（workdir = F） | [_batch10_evidence\T1_rerun.log](_batch10_evidence/T1_rerun.log)（CONFIGURE exit=0） |
| 增量构建 | `xmake build ol_transport_lifecycle_tests` | 同上（BUILD exit=0，0.156 s，产物未变 ⇒ 无陈旧源） |
| **强制重建** | `xmake build -r ol_transport_lifecycle_tests` | [_batch10_evidence\T1_rerun_forced.log](_batch10_evidence/T1_rerun_forced.log)（BUILD exit=0，30.171 s，全量重编 91 条编译/链接行） |
| 运行 | `ol_transport_lifecycle_tests.exe` | 同上（run exit=0，`checks=106 failures=0`） |

**构建边界声明**：全程**显式命名目标**。`ol_deploy`（`set_default(true)`）**未被触发**——`F:\...\build\stage` 的 mtime 仍为 2026-10-09 17:01:07。`ol_transport_lifecycle_tests` 不在 `ol_deploy` 的依赖闭包内，也不链接 9 个插件专属文件。

### 1.2 产物

| 项 | 值 |
| --- | --- |
| 路径 | `F:\桌面\ol\ol-mod-olfinal\build\bin\release\ol_transport_lifecycle_tests.exe` |
| 大小 | 3,826,176 B |
| 构建时间 | 2026-10-10 11:58:29 |
| SHA-256 | `4BE2180D1856DB6A8CF1BBD831001BE8C059E2A519582A5DAED99BE7E5A18468` |
| 重建前 SHA-256 | `F021D17073D4A5A1C2E01FF61DB61394D6290704B6C8396AB97881B7D9D0BD28`（2026-10-09 21:23:26，与 [_a6_build.log](_a6_build.log) 记录一致） |
| 源码依赖证明 | 强制重建 exit 0 ⇒ 该二进制**由当前 F 源码完整重编而来**，非复用缓存 |
| 副产物 | `...\build\bin\release\Ayria\Logs\CodolGameServer.log`（运行后 186,532 B；测试 P1 用例写入） |

> 两次构建的 exe 哈希不同是**预期**的：PE 内含构建时间戳/PDB 路径。两次运行结果相同（106/0）。

### 1.3 逐用例结果（本轮实跑）

| 用例 | 断言数 | 通过 | 失败 | 关键验证内容 |
| --- | --- | --- | --- | --- |
| `[1/8]` loopback ephemeral bind | 3 | 3 | 0 | `start(0, 127.0.0.1)` 成功、`bound`、临时端口 ≠ 0 |
| `[2/8]` repeated start(0) idempotent | 10 | 10 | 0 | 真实 `NET_SendPackets` 使 `packetsSent>0`；重复 `start(0)` 后端口/计数器不变，socket 仍可发 |
| `[3/8]` different port cannot steal binding | 5 | 5 | 0 | 冲突端口被拒、仍 bound、端口不变、`SocketAlreadyBoundError` |
| `[4/8]` stop() clears state | 5 | 5 | 0 | `bound=false`、`port=0`、计数器与时间戳清零 |
| `[5/8]` repeated stop() idempotent | 2 | 2 | 0 | 第二次 `stop()` 后状态仍干净 |
| `[6/8]` rebinding after stop() | 5 | 5 | 0 | 重绑成功、计数器归零、**成功 start 清除粘性错误** |
| `[7/8]` stop() retains sticky error | 4 | 4 | 0 | 冲突错误码跨 `stop()` 保留 |
| `[8/8]` occupied loopback port fails | 6 | 6 | 0 | holder 占位后 bind 失败、保持未绑定、记录真实错误码 |
| `[extra]` default address stays INADDR_ANY | 9 | 9 | 0 | **真实 loopback 收发**：默认地址绑定的 socket 收到 127.0.0.1 数据报，长度/字节逐一致；`start(0)` 默认重载可用 |
| `[A-1]` address must match live binding | 20 | 20 | 0 | 同端口同地址 ⇒ true；同端口异地址 ⇒ false + 哨兵错误；`start(0)` 仍幂等；反向（INADDR_ANY 绑定 vs 指定地址）⇒ false；被拒后 socket 仍可发 |
| `[C-3]` init failure logging | 14 | 14 | 0 | 捕获 `std::clog`，断言 `udp init failed` / `op=bind` / `requested=127.0.0.1:<port>` / `actual=unavailable` / 真实非零 `error=` 且与 `status().lastSocketError` 一致；成功路径日志未被破坏 |
| `[B-1]` stop() return value | 9 | 9 | 0 | 正常 stop / 已停止再 stop / 重绑后再 stop 均返回 true，且状态正确 |
| `[simulated-close-failure]` | 14 | 14 | 0 | IAT 重定向使 `closesocket` 返回 `SOCKET_ERROR`+`WSAENOTSOCK`：`stop()` 返回 false、绑定/端口/发送计数保留、socket 仍可发、日志追加 `udp transport stop failed op=close error=10038`、重试 stop 完成清理并归零 |
| **合计** | **106** | **106** | **0** | `checks=106 failures=0`，exit 0 |

---

## 2. 任务 §三 逐项核对

### §三.1 `SvUdpTransport` 的 `start()`、`stop()` 与状态重置语义

**`start(port, bindAddress)`**（F 的 `sv_network_mp.cpp:20-61`）：

| 前置状态 | 请求 | 结果 | 状态影响 |
| --- | --- | --- | --- |
| socket 已开 | `port == 0` | `true` | **完全不动**（绑定/计数器/时间戳/粘性错误全部保留）；请求的地址**不生效** |
| socket 已开 | 端口 ≠ 当前绑定端口 | `false` | `lastSocketError = SocketAlreadyBoundError`；绑定/计数器/时间戳不动 |
| socket 已开 | 端口相同、`getsockname` 实测地址相同 | `true` | 完全不动 |
| socket 已开 | 端口相同、地址不同 **或** `getsockname` 失败 | `false` | `lastSocketError = SocketAlreadyBoundError` |
| socket 未开 | 任意 | 见下 | `status_ = {}`、`peerStatus_.clear()`，然后 `NET_IPSocket`；失败则 `lastSocketError = socket_.lastError()`，成功则 `bound=true, port=socket_.port()` |

**关键判定**：地址比较基于 `getsockname()` 的**实测**绑定地址（`boundAddress()`，主机字节序），而非"请求过的地址"。`getsockname` 失败返回 `nullopt`，被**拒绝**而不是被当作匹配——这是正确的 fail-closed 选择。

**`stop()`**（F 的 `sv_network_mp.cpp:63-89`）：

| 分支 | 返回 | 状态影响 |
| --- | --- | --- |
| `socket_.close()` 成功（含本已关闭） | `true` | `bound=false`、`port=0`、`packetsReceived/Sent=0`、两个时间戳=0、`peerStatus_.clear()`、`nonce_=0`；**`lastSocketError` 保留** |
| `socket_.close()` 失败 | `false` | `lastSocketError = socket_.lastError()`；写 `udp transport stop failed op=close error=<code>`；**绑定/端口/计数器全部保留**，句柄保持打开以便重试 |

**状态重置**：`stop()` 的重置是**完整的**（除刻意保留的粘性错误码）。这与"失败 stop 不得伪装成成功"的契约一致。

**保留项（FF-3/FF-4）**：`start()` 的两条"已打开 + 成功"早退路径**不清除** `lastSocketError`，但 `sv_network_mp.hpp:66-69` 写的是"cleared by the next successful start()"。**文档与实现不一致，且无测试覆盖。**

### §三.2 IPv4 绑定地址参数与默认 `INADDR_ANY` 行为

| 项 | 核对 |
| --- | --- |
| 常量 | `win_net.hpp:19` `inline constexpr std::uint32_t AnyIpv4Address = 0;`（主机字节序，零 = INADDR_ANY） |
| 编译期保证 | 测试 `static_assert(AnyIpv4Address == 0, "INADDR_ANY must be zero in host byte order")`（测试第 41 行） |
| 默认值 | `SvUdpTransport::start(uint16_t port = 28960, uint32_t bindAddress = AnyIpv4Address)`；`NetUdpSocket::NET_IPSocket(uint16_t port, uint32_t bindAddress = AnyIpv4Address)` |
| 字节序转换 | `win_net.cpp:111` `address.sin_addr.s_addr = htonl(bindAddress);` —— 入参主机序，socket 层网络序 ✅ |
| 改造前行为 | `address.sin_addr.s_addr = htonl(INADDR_ANY);` —— 与 `AnyIpv4Address == 0` 的默认路径**逐位等价** ✅ |
| 运行时证据 | 运行日志出现 `address=127.0.0.1`（显式地址）与 `address=0.0.0.0`（默认重载）两种绑定；`[extra]` 用真实 loopback 收发证明默认绑定**确实**接受 127.0.0.1 的流量 |
| 日志地址打印 | 成功日志按 `bindAddress` 打印点分四段 —— **注意这是"请求值"，不是 `getsockname` 实测值**（见 §5 未验证项 UV-4） |

**结论：默认 `INADDR_ANY` 行为与改造前等价，且被真实收发验证。**

### §三.3 端口 0 / 重复启动 / 冲突端口 / 停止 / 重启 / 占用端口失败

| 场景 | 用例 | 结果 |
| --- | --- | --- |
| 端口 0（临时端口） | `[1/8]`、`[2/8]`、`[6/8]`、`[extra]` | ✅ 通过 |
| 重复启动（同端口幂等） | `[2/8]`、`[A-1]` | ✅ 通过（含计数器不被清零的真实发送路径） |
| 冲突端口（不同端口） | `[3/8]`、`[7/8]` | ✅ 通过 |
| 冲突地址（同端口不同地址） | `[A-1]`（**仅 F**） | ✅ 通过 |
| 停止 / 重复停止 | `[4/8]`、`[5/8]`、`[B-1]` | ✅ 通过 |
| 重启（stop 后重新 start） | `[6/8]`、`[B-1]` | ✅ 通过 |
| 占用端口失败 | `[8/8]`、`[C-3]` | ✅ 通过（实测 OS 返回 `error=10048` = `WSAEADDRINUSE`） |

### §三.4 socket 关闭失败 / 资源清理 / 错误状态保留 / Winsock 初始化与清理路径

**Winsock 生命周期（静态核对 `win_net.cpp`）**：

| 路径 | `WSAStartup` | `WSACleanup` | 判定 |
| --- | --- | --- | --- |
| `NET_IPSocket` 入口 | — | 若 `winsockStarted_`（上一次未清理）则执行 | ✅ 不覆盖未释放句柄：`if (!close()) return false;` |
| `WSAStartup` 失败 | 失败 | 不执行（`winsockStarted_` 仍 false） | ✅ 正确 |
| `socket()`/`ioctlsocket`/`setsockopt`/`bind`/`getsockname` 失败 | 已成功 | `close()` → `WSACleanup()` | ✅ 成对 |
| 绑定成功 | 已成功 | 留给后续 `close()` | ✅ 成对 |
| `close()` 成功 | — | 执行 | ✅ |
| `close()` **失败** | — | **不执行**（提前 return false） | ✅ 正确：句柄未释放，保留 Winsock 引用以便重试 |
| 析构 `~NetUdpSocket()` | — | 经 `close()`，**返回值被忽略** | ⚠️ **FF-7**：析构时 closesocket 失败会泄漏句柄并跳过 WSACleanup |

**socket 关闭失败**：
- 实现 ✅：`close()` 失败时保留 `socket_` 与 `port_`，记录 `lastError_`，返回 `false`；`stop()` 据此保留绑定并返回 `false`。
- 验证 ⚠️：**只由伪造失败覆盖**（[`testStopCloseFailureKeepsBinding`](_batch10_evidence/T1_tests_F.cpp#L556) 改写自身 IAT）。测试注释明确写着"NOT a genuine Windows closesocket failure"。**不得**把它当作真实 OS 失败路径的证据。

**错误状态保留**：
- ✅ 粘性错误跨 `stop()` 保留（`[7/8]` 通过）。
- ✅ 成功 start（真正重绑路径）清除错误（`[6/8]` 通过）。
- ⚠️ **FF-3**：已打开状态下的成功早退**不清除**错误，与头文件措辞冲突（`[A-1]` 未断言该点）。

### §三.5 测试不会使用正式游戏端口，也不依赖客户端/注入器/游戏进程

| 核对项 | 结果 |
| --- | --- |
| 是否出现正式端口 28960 | ❌ 从未出现。全测试所有 bind 只用 `0`、`bound.port`（临时）、`heldPort`（holder 的临时端口）、`differentPort(bound.port)`（仅用于**被拒**的请求，不产生绑定） |
| 是否绑定 0.0.0.0 | 是，但只在 `[extra]` 与 `[A-1]` 用**端口 0**（临时端口）绑定，不占用任何已知端口 |
| 依赖客户端 | ❌ 无。测试是独立控制台 exe |
| 依赖注入器 / Bootstrapper | ❌ 无。全程无 `Injector32`、无 DLL 注入 |
| 依赖游戏进程 / 读进程内存 | ❌ 无 |
| 依赖外网 | ❌ 无。全部地址为 `127.0.0.1`（`LoopbackIpv4 = 0x7F000001`）或 `INADDR_ANY` 的 loopback 回环流量 |
| 副作用 | ⚠️ 在 exe 目录写 `Ayria\Logs\CodolGameServer.log`（`RuntimeLog` 通道）。属构建目录（`build/` 已 gitignore），不触碰游戏目录 |
| 与 `ol_deploy` 的关系 | 目标 `set_default(false)`，且不在 `ol_deploy` 依赖闭包内 ⇒ **不可能**触发部署 |

### §三.6 是否存在"只验证内部状态、未验证真实 socket 行为"的用例

**逐用例分类**：

| 用例 | 真实 socket 行为 | 仅内部状态 |
| --- | --- | --- |
| `[1/8]` | bind + getsockname（端口≠0 隐含） | `bound` 标志 |
| `[2/8]` | ✅ **sendto 真实发送**；重复 start 后**再次真实发送** | 端口/计数器比较 |
| `[3/8]` | — | **全部** |
| `[4/8]` | — | **全部** |
| `[5/8]` | — | **全部** |
| `[6/8]` | bind + getsockname（隐含） | 计数器/错误码 |
| `[7/8]` | — | **全部** |
| `[8/8]` | ✅ 真实 `bind` 冲突（OS 返回 10048） | `bound`/`port` |
| `[extra]` | ✅ **真实 sendto + recvfrom**，逐字节比对 | 默认重载的 bound/port |
| `[A-1]` | ✅ 被拒后**真实发送**成功 | 大部分断言是状态 |
| `[C-3]` | ✅ 真实 `bind` 失败触发日志；真实成功 bind 保留原日志 | 日志文本匹配 |
| `[B-1]` | bind（隐含） | **大部分** |
| `[simulated-close-failure]` | ✅ 真实 `sendto`（失败 stop 后仍能发）、真实 `closesocket`（重试路径）、真实**文件追加**日志 | 绑定/端口/计数保留 |

**结论**：
- **纯内部状态用例**：`[3/8]`、`[4/8]`、`[5/8]`、`[7/8]`，以及 `[B-1]` 的大部分。
- **补偿**：这些内部状态断言的**关键结论**都在别处被真实 socket 行为覆盖——`[3/8]`/`[7/8]` 的"被拒后 socket 仍可用"由 `[A-1]` 用真实发送覆盖；`[4/8]`/`[5/8]` 的"停止后状态干净"由 `[B-1]`/`[simulated-close-failure]` 的真实 `closesocket` + 重试覆盖。
- **真正未被覆盖的缺口**：见 §5 UV-1 —— **没有任何用例证明 OS 层的端口绑定在 `stop()` 后真的被释放**。`[6/8]` 用 `start(0)` 重绑，OS 可能给出另一个临时端口，因此不构成证明。

### §三.7 对照生产调用点，接口变化不改变现有无参数调用语义

**完整调用点清单**（F 的 `src/` 全树）：

| 调用点 | 形式 | 判定 |
| --- | --- | --- |
| `Appmain.cpp:2096` | `Network.start()` | ✅ 无参 ⇒ `port=28960`、`bindAddress=0`，与改造前逐位等价 |
| `Appmain.cpp:8178` | `Network.start()` | ✅ 同上 |
| `Appmain.cpp:8183` | `Network.stop()`（消费返回值） | ⚠️ **唯一语义变化**：失败时上层返回 `false` 并记 `game server disable failed: udp transport is still bound` |

- `NET_IPSocket` 唯一调用者是 `sv_network_mp.cpp:53`，已用双参形式；默认参数保证旧单参调用仍可编译。
- `NetUdpSocket::close()` 的调用者全部在 `win_net.cpp` 内部 + `sv_network_mp.cpp:66`；`void → bool` 对忽略返回值的调用**源码兼容**。
- 同名不同类的 `.start(` / `.stop(`（`ClientSessionBridge`、`SharedRoomHost`、`localnetworking`）与本 T-1 无关，未被改动。

**结论：接口变化不改变任何现有无参数调用语义。** ✅

---

## 3. 历史记录核对（工作区既有日志）

| 日志 | 时间 | 工作树 | 断言 | 结果 | 与当前源码的关系 |
| --- | --- | --- | --- | --- | --- |
| [_t1_build.log](_t1_build.log) | 10-09 17:31 | F（日志内 `cwd=F:\桌面\ol\ol-mod-olfinal`） | `checks=43` | exit 0 | **过期**：当时测试文件是 43 断言的早期版本 |
| [_e1_build.log](_e1_build.log) | 10-09 18:27 | F（未署名 cwd） | `checks=49` | exit 0 | **过期**（E-1 中间版本） |
| [_e1_regression.log](_e1_regression.log) | 10-09 18:28 | D（意图） | `checks=49` | **无效** | `BUILD exit=-1` 后运行了从 F 复制的旧二进制 |
| [_a1c3_build.log](_a1c3_build.log) | 10-09 18:48 | F | `checks=83` | exit 0 | **过期** |
| [_batch1_build.log](_batch1_build.log) | 10-09 19:44 | F | `checks=83` | exit 0 | **过期** |
| [_batch2_build.log](_batch2_build.log) | 10-09 20:05 | F | `checks=92` | exit 0 | **过期** |
| [_p1_build.log](_p1_build.log) | 10-09 20:41 | F | `checks=105 failures=7` | **exit 1** | 7 处失败全在 P1 用例：`the closesocket import can be redirected for the test` 及其级联 |
| [_p1_diag.log](_p1_diag.log) | 10-09 20:42 | F | `checks=105 failures=7` | exit 1 | 同上 |
| [_p1_run2.log](_p1_run2.log) | 10-09 20:43 | F | `checks=105` | exit 0 | IAT 定位修复后通过 |
| [_p1_final.log](_p1_final.log) | 10-09 20:44 | F | `checks=105` | exit 0 | 同版本 |
| [_a6_build.log](_a6_build.log) | 10-09 21:23 | F | `checks=106` | exit 0 | **与当前 F 测试文件一致**（exe `F021D170…`） |
| **[_batch10_evidence\T1_rerun.log](_batch10_evidence/T1_rerun.log)** | **10-10 11:57** | **F** | **106** | **exit 0** | **本轮**：增量构建（0.156 s，无陈旧源） |
| **[_batch10_evidence\T1_rerun_forced.log](_batch10_evidence/T1_rerun_forced.log)** | **10-10 11:58** | **F** | **106** | **exit 0** | **本轮**：强制全量重建（30.171 s）+ 运行 |

**断言数与测试文件版本的对应**（用于判定"某条日志是否仍代表当前源码"）：

| 断言数 | 对应用例数 | 对应文件 |
| --- | --- | --- |
| 43 | — | 已消失的早期版本 |
| 49 | 9 | **D 的当前版本** |
| 83 / 92 / 105 | 11-12 | F 的中间版本 |
| **106** | **13** | **F 的当前版本**（本轮实跑） |

---

## 4. 失败项

| # | 失败项 | 性质 | 处置 |
| --- | --- | --- | --- |
| **FAIL-1** | **D 的 E-1 回归从未成功**。7 次构建全部 `BUILD exit=-1`（根因：`openssl/crypto.h` 不可达，未定位）。[_e1_regression.log](_e1_regression.log) 的"49 断言 0 失败"来自从 F 复制的 T-1 二进制，**不是** pre-T-1 回归结果 | 证据无效（不是代码失败） | 按 R8 不恢复；登记为作废 |
| **FAIL-2** | `_p1_build.log` / `_p1_diag.log` 的 7 处失败 | 已修复的历史失败 | 修复在 `_p1_run2.log`（20:43）；当前 106/0 不受影响 |
| **FAIL-3** | 当前 F 的 T-1 测试**无失败** | — | — |

---

## 5. 未验证项（必须保留，不得以 PASS 代替）

| # | 未验证项 | 为什么未验证 | 解除需要 |
| --- | --- | --- | --- |
| **UV-1** | **`stop()` 后 OS 层的端口绑定确实被释放** | 没有任何用例尝试重新绑定同一端口来反证。`[6/8]` 用 `start(0)`，OS 可给出不同临时端口 | 见 [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) §4.5 的 FF-1 最小修复建议（用 probe socket 重绑原端口） |
| **UV-2** | **真实的 `closesocket` 失败路径** | `stop()` 的失败分支只由 IAT 伪造覆盖；测试自身已披露此限制 | 需在隔离一次性探针中制造真实失败，或在报告中永久保留"仅伪造覆盖"的标注 |
| **UV-3** | **`lastSocketError` 在已打开成功早退路径上的清除语义** | 文档与实现不一致（FF-3），且无断言 | 需先裁定 (a) 改实现还是 (b) 改文档，再补断言 |
| **UV-4** | **`SvUdpTransport::status().port` 与 OS 实测端口的一致性** | `start()` 用 `socket_.port()`（即 `getsockname` 结果）设置，逻辑上一致；但成功日志打印的是**请求地址**而非实测地址，且无独立用例比对 `boundAddress()` 与 `status()` | 建议补一条 `boundAddress() == 请求地址` 的显式断言 |
| **UV-5** | **长时稳定性 / 多线程并发** | 本轮为单线程离线功能测试，无并发 `start/stop` 压力用例 | 需新增并发用例（`mutex_` 已存在，但未被竞争验证） |
| **UV-6** | **Winsock 引用计数在极端路径下的平衡** | 静态核对通过；但"多次失败-重试"的 `WSAStartup/WSACleanup` 计数无运行时断言 | 需注入 `WSAStartup` 失败或计数探针 |
| **UV-7** | **9 个插件专属文件（含 `FrameHook.cpp`）的正确性** | 不在任何测试目标内（Batch 10 报告 §6.2 / R1）。T-1 的通过**不能**外推到它们 | 需新建插件边界测试目标（报告 §4.3 的 T1 方案，未实施） |
| **UV-8** | **宿主身份 / `ComFrameRva` / `UnsignedFastfileVerificationRva`** | 受客户端制品门禁阻塞 | 见 [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md) |

---

## 6. 边界合规机械核对

| 禁止项 | 核对 |
| --- | --- |
| 启动 CODOL 客户端 / 房间 / 专用服务进程 | **未执行**。运行的唯一进程是 `ol_transport_lifecycle_tests.exe`（独立控制台测试） |
| 运行 Injector32 / DLL 注入 | **未执行** |
| 读取或修改游戏进程内存 | **未执行** |
| 运行会自动部署到游戏目录的默认目标 | **未执行**。全程显式命名目标；`build\stage` mtime 未变（17:01:07）；`config/codol-game-dir.txt` 哈希未变 |
| 修改启动链 / RVA / 字节前缀 / ABI / 协议常量 / fixture / S2-S3 默认值 | **未执行**。F 工作区源码零字节改动 |
| 提交 Git commit / 推送远端 | **未执行**。两树 HEAD 与分支未变 |
| 复制 / 覆盖 / 合并 / 清理任一工作树 | **未执行** |

---

## 7. 关联交付

- [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) — 基准裁定与冻结规则
- [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) — 逐项差异与采用版本
- [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md) — 客户端制品门禁
- [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md) — 归属与哈希清单
