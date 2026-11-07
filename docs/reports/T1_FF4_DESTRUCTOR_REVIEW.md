# T1_FF4_DESTRUCTOR_REVIEW — 析构函数 `close()` 失败可观测性审查

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**
**结论**：**NOT IMPLEMENTED — 只提交分析，未修改 FF-4。**
**理由（一句话）**：析构函数在生产中**只在 DLL 拆卸窗口可达**，该窗口持有加载器锁且 iostream 生命周期不保证；在唯一可达的调用点上，日志既可能不安全又会被误读为资源泄漏。授权的实施条件不满足。

---

## 1. 现状证据

### 1.1 析构函数

`src/game_server/win32/win_net.cpp:48-51`：

```cpp
    NetUdpSocket::~NetUdpSocket()
    {
        close();
    }
```

`close()` 的返回值被丢弃。

### 1.2 `close()` 的失败路径

`src/game_server/win32/win_net.cpp:149-170`：

```cpp
    bool NetUdpSocket::close()
    {
        if (socket_ != InvalidSocket)
        {
            if (closesocket(static_cast<SOCKET>(socket_)) == SOCKET_ERROR)
            {
                // Leave the handle marked open: the caller must be able to see
                // that the socket was not released instead of reporting a clean
                // stop. A later close() retries.
                lastError_ = WSAGetLastError();
                return false;                 // <-- 在 socket_ = InvalidSocket 之前返回
            }
            socket_ = InvalidSocket;
        }
        port_ = 0;
        if (winsockStarted_)
        {
            WSACleanup();                     // <-- 失败路径会跳过它
            winsockStarted_ = false;
        }
        return true;
    }
```

### 1.3 资源所有权与调用顺序

| 项 | 事实 | 来源 |
| --- | --- | --- |
| 生产中的 `SvUdpTransport` 实例数 | **1**（全局 `CodolGameServer::SvUdpTransport Network;`） | `src/game_server/Appmain.cpp:288` |
| `Network` 的存储期 | **命名空间作用域（静态存储期）**，位于 DLL 内 | 同上；紧邻其它命名空间级全局（`Server`、`DedicatedControlServer` 等） |
| `NetUdpSocket` 实例 | 只作为 `SvUdpTransport::socket_` 成员 | `src/game_server/server_mp/sv_network_mp.hpp:93` |
| `SvUdpTransport` 成员析构顺序 | 逆声明序：`mutex_` → `nonce_` → `peerStatus_` → `status_` → `receiveBuffer_` → **`socket_`（最后）** | `sv_network_mp.hpp:93-98` |
| 插件 `DllMain` | 只处理 `DLL_PROCESS_ATTACH`；`DLL_PROCESS_DETACH` 不做任何事 | `src/game_server/Appmain.cpp:9538-9546` |
| 因此 `Network` 的析构时机 | **DLL_PROCESS_DETACH 期间**，由 CRT 静态析构机制执行（此时加载器锁被持有） | 由上述两项推出 |
| 仓库对该窗口的既有立场 | `"The plugin remains loaded for the process lifetime. Avoid joining a control thread from DLL teardown while the Windows loader lock is held."` | `src/game_server/Appmain.cpp:289-290` |
| `std::clog` 的声明来源 | `win_net.cpp:6` 直接 `#include <iostream>` | `win_net.cpp` 的 include 列表 |
| `win_net.hpp` 是否含 `<iostream>` | **否**（只有 `qcommon/net_types.hpp` + `<cstddef>/<cstdint>/<optional>/<span>`） | `win_net.hpp:3-8` |

---

## 2. 五个必答问题

### Q1 — `close()` 失败时 socket 句柄处于什么可验证状态？

**答：状态明确、自洽、可验证。** 失败分支在 `socket_ = InvalidSocket;` **之前**返回，因此失败后：

| 可观测项 | 值 | 含义 |
| --- | --- | --- |
| `open()` | `true` | 句柄仍有效（未被清空） |
| `port()` | 原端口（未清零） | 绑定信息未丢 |
| `lastError()` | `closesocket` 的原始错误码 | 原因可读 |
| `winsockStarted_` | 仍为 `true` | `WSACleanup()` 未执行 |
| `SvUdpTransport::status_`（若经 `stop()`） | 未被触碰 | 绑定/计数器原样保留 |

⇒ 这一层设计本身是**正确**的：调用方**可以**发现"句柄没释放"。**FF-4 要解决的只是"析构时这个事实无人知晓"。**

### Q2 — 析构期间记录日志是否安全？

**答：不保证安全。** 三条相互独立的理由：

1. **加载器锁**：`Network` 是 DLL 内的静态存储期全局，其析构在 `DLL_PROCESS_DETACH` 期间执行，**此时 Windows 加载器锁被持有**。在持有加载器锁时执行流 I/O（可能分配内存、获取流锁、写控制台/文件）属于经典的危险操作类别。
2. **仓库自己已经记录过这个窗口的危险**：`Appmain.cpp:289-290` 明确写着要**避免**在 DLL 拆卸窗口做非平凡工作（原文针对"join 控制线程"，理由是加载器锁）。在同一个窗口新增 `std::clog` 写入，与该既有纪律方向相反。
3. **iostream 生命周期不保证**：`std::clog` 由 `<iostream>` 注入的 `std::ios_base::Init` 静态对象构造。`Network`（`Appmain.cpp` 的 TU）与 `clog` 的 `Init`（`win_net.cpp` 的 TU）之间的**析构顺序取决于链接顺序，标准不保证**。若 `clog` 先析构，写入是**未定义行为**。

### Q3 — `std::clog` 是否已经通过现有头文件可靠声明？

**答：编译期是，运行期不是；且该"是"很脆弱。**

| 维度 | 结论 |
| --- | --- |
| 编译期 | ✅ `win_net.cpp:6` 直接 `#include <iostream>`，析构函数定义在同一个 TU |
| 脆弱性 | ⚠️ `win_net.hpp` **不含** `<iostream>`。若将来把析构体内联到头文件，会立刻编译失败 |
| 运行期 | ❌ 见 Q2。编译期可见**不能**推出运行期有效 |

⇒ **仅凭"头文件已声明"不足以判定可实施。**

### Q4 — 增加日志能否准确反映失败，还是会造成误导？

**答：在唯一可达的调用点上，会误导。**

- 生产中 `SvUdpTransport` 只有**一个**实例（全局 `Network`），`NetUdpSocket` 只是它的成员。⇒ `~NetUdpSocket` 在生产中**只在 DLL 拆卸 / 进程退出时**被调用。
- 在该窗口，`closesocket` 失败的最可能原因是 **Winsock 已被拆除**（`WSANOTINITIALISED` 等），而**不是**句柄泄漏。把它写成 "close failed" 会把**环境性失败**读成**资源泄漏**。
- 而且此刻进程正在结束，句柄无论如何都会被 OS 回收 ⇒ 日志的**可行动价值接近 0**，误读风险非零。
- 相反，在**测试**里（局部 `NetUdpSocket` 正常析构）失败是真实且可诊断的——但那正是测试自己控制的路径，**不需要生产日志**。

### Q5 — Winsock 清理失败或引用计数异常是否可能导致更严重的问题？

**答：是，而且当前设计是在刻意回避它。**

- `close()` 的失败路径**跳过** `WSACleanup()`。这是**有意**的：在句柄仍活时调用 `WSACleanup()` 是未定义/不安全的组合，可能影响同进程其它 socket。
- 因此"析构时强制 `WSACleanup()` 以平衡引用计数"**不是**一个安全的最小改动，而是一次**语义变更**：它要在"保留句柄以便重试"与"立刻平衡 Winsock 引用计数"之间取舍，而析构时已无重试者。这需要单独裁定与设计。
- `WSAStartup`/`WSACleanup` 是进程级引用计数；某次 `close()` 失败会使该对象的计数永久失衡。**增加一条日志不会改变这一点。**

> ### 明确声明
> **本审查不主张、也不允许任何人主张"加日志修复了资源泄漏"。**
> 日志最多是**可观测性**，它与句柄泄漏、Winsock 引用计数失衡是**两件独立的事**。FF-4 若实施，其唯一效果是"让失败可见"，**不是**"让失败不发生"。

---

## 3. 裁定

授权规定的实施条件：

> 只有在**日志行为明确**、**无需扩大重构**且**不会吞掉清理错误**时，才实施最小日志修改。否则只提交分析，不修改 FF-4。

逐条核对：

| 条件 | 是否满足 | 依据 |
| --- | --- | --- |
| 日志行为明确 | ❌ **不满足** | Q2：加载器锁 + iostream 析构顺序不保证 |
| 无需扩大重构 | ⚠️ **部分不满足** | 要安全落地需引入生命周期安全通道或显式关闭阶段（§4 的 (a)/(b)），均超出"最小日志修改" |
| 不会吞掉清理错误 | ✅ 满足 | 只增加输出，不改变清理路径 |
| （附加）不误导 | ❌ **不满足** | Q4：唯一可达调用点上，环境性失败会被读成泄漏 |

**⇒ 结论：NOT IMPLEMENTED。**

---

## 4. 安全的替代方案（**均需单独授权**，本轮未实施）

| 方案 | 内容 | 评价 |
| --- | --- | --- |
| **(b) 显式关闭阶段**（**推荐**） | 让释放发生在正常执行期而非拆卸期：由宿主在 `DLL_PROCESS_DETACH` 之前调用 `Network.stop()`。`stop()` **已经**返回 `bool`，并且**已经**记录 `udp transport stop failed op=close error=<code>`（`sv_network_mp.cpp:72-76`） | **最小且最安全**：正确的诊断通道**已经存在**，缺的只是"被调用"。无需新增日志代码，无需触碰析构函数 |
| **(c) 登记为已知限制** | 明确记录：`Network` 的析构发生在加载器锁下，其 `close()` 失败不可观测；正常路径由 (b) 覆盖 | 零代码，零风险 |
| **(a) 生命周期安全通道** | 用 `OutputDebugStringA`（不依赖 CRT 与 iostream）替代 `std::clog`。但构造消息文本本身需要分配，需预格式化或固定缓冲区 | 仍是新增代码；且该通道**不被**测试的 `std::clog` 重定向捕获，需要另一套测试机制 |
| **(d) 强制 `WSACleanup()`** | 析构失败时强制清理 | ❌ **不推荐**。见 Q5：语义变更 + 在句柄仍活时调用不安全 |

**建议的下一步**：先做 (b)+(c)。它们不修改 `win_net.cpp`，而是把责任放回**调用方**——这正是 `stop()` 的返回值与日志已经准备好的用途。

---

## 5. 阶段验收

FF-4 **未修改任何文件**，因此没有新增构建需求。为满足"每阶段完成后必须运行相关测试并记录退出码"的要求，仍对 T-1 目标做了一次运行并记录（与阶段 2 结束状态一致，因为源码未变）：

| 验收项 | 结果 |
| --- | --- |
| 相关测试运行 | `run exit=0` · `checks=124 failures=0`（见 §6 日志） |
| `git diff --check` | exit **0** |
| 修改文件 | **无**（`win_net.cpp` 哈希仍为 `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14`） |
| 正式协议常量 / RVA / ABI / 启动链 / S2-S3 | **未变** |
| 未触发 `ol_deploy` | ✅ `build\stage` mtime 未变 |
| 未提交 Git | ✅ HEAD 仍为 `2a75bdd` |

---

## 6. 文件哈希与日志

| 文件 | 字节 | SHA-256 | 本阶段 |
| --- | --- | --- | --- |
| `src/game_server/win32/win_net.cpp` | 9,054 | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` | **未改** |
| `src/game_server/win32/win_net.hpp` | 2,642 | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` | **未改** |
| `src/game_server/Appmain.cpp` | 481,281 | `407B6F9896A5F0354625B9D0724A3519BA4ACEDDFC36BA34CE879F79100BE7B1` | **未改** |

| 日志 | 路径 |
| --- | --- |
| 本阶段测试运行 | [\_t1_fix_evidence\\phase3_ff4_tests.log](_t1_fix_evidence/phase3_ff4_tests.log) |
| FF-2 修复后基线（对比参照） | [\_t1_fix_evidence\\phase2b_ff2_after_fix.log](_t1_fix_evidence/phase2b_ff2_after_fix.log) |

---

## 7. 关联交付

- [T1_FF1_PORT_RELEASE_REPORT.md](T1_FF1_PORT_RELEASE_REPORT.md) — FF-1 实施结果
- [T1_FF2_ERROR_STATE_REPORT.md](T1_FF2_ERROR_STATE_REPORT.md) — FF-2 实施结果
- [T1_FF3_ERROR_CODE_COMPATIBILITY.md](T1_FF3_ERROR_CODE_COMPATIBILITY.md) — FF-3 兼容性分析（**未实施**）
