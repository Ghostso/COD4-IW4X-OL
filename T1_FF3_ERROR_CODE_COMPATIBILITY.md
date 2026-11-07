# T1_FF3_ERROR_CODE_COMPATIBILITY — `SocketAlreadyBoundError` 数值变更兼容性分析

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**
**状态**：**NOT IMPLEMENTED — 待独立批准。** 本轮**未**修改 `SocketAlreadyBoundError` 的数值，**未**删除 `static_assert`。
**授权依据**："FF-3 暂不实施。先输出单独的兼容性分析……等待独立批准后再处理。"

---

## 0. 结论速览

| 问题 | 答案 |
| --- | --- |
| 该常量是否被源码多处引用？ | **是，13 处**，但**全部**在 4 个文件内（`win_net.{hpp,cpp}`、`sv_network_mp.{hpp,cpp}`、测试文件） |
| 是否有任何代码/脚本/配置/文档把 **10037** 当作错误码使用？ | **否**。数值 `10037` 在整棵树中只出现在**定义处**；另有 `assets/` 下 3 处 `10037` 是**游戏 SKU/product ID 的巧合数字**，与本常量无关 |
| 该字段是否属于公开 ABI？ | **是（部分）**：它以 `uint32_t` 出参形式经**导出函数** `CODOL_GameServerGetTransportStatus` 暴露。**函数签名/结构布局不变**，但**数值可观察** |
| 是否属于外部协议 / 线上格式？ | **否**。它不是网络协议常量，**不进入任何序列化结构**（快照/gamestate/netchan 中 0 命中） |
| 改数值的兼容性影响 | 树内 **0 处**依赖旧值；**导出 API 的数值会变**；树外消费者**未知** |
| 建议 | 见 §5。**推荐 (B)**（私有错误域）或零风险的 **(D)**（仅改名/加文档）；若要保留数值不变又消除歧义，用 **(A)/(E)** 的加性方案 |

---

## 1. 常量定义与编译期锁定

**定义**（`src/game_server/win32/win_net.hpp:24-27`）：

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

---

## 2. 所有引用（全树检索）

### 2.1 `SocketAlreadyBoundError` —— 13 处，全部在 4 个文件内

| # | 位置 | 用法 | 受数值变更影响？ |
| --- | --- | --- | --- |
| 1 | `win_net.hpp:27` | **定义** `= 10037` | 定义处 |
| 2 | `win_net.cpp:14` | `static_assert(SocketAlreadyBoundError == WSAEALREADY, …)` | ✅ **必须同步删除或改写** |
| 3 | `win_net.cpp:15` | 上述 `static_assert` 的消息文本 | ✅ 同上 |
| 4 | `sv_network_mp.cpp:35` | `status_.lastSocketError = SocketAlreadyBoundError;`（端口冲突） | 否（符号引用） |
| 5 | `sv_network_mp.cpp:46` | 同上（地址冲突） | 否 |
| 6 | `sv_network_mp.hpp:56` | 文档注释中提及该常量名 | 否 |
| 7 | `TransportLifecycleTests.cpp:36` | `using CodolGameServer::SocketAlreadyBoundError;` | 否 |
| 8 | 同上 `:280` | `conflict.lastSocketError == SocketAlreadyBoundError` | 否（符号引用） |
| 9 | 同上 `:281` | 断言消息文本 | 否 |
| 10 | 同上 `:340` | 粘性错误断言 | 否 |
| 11 | 同上 `:438` | 地址冲突断言 | 否 |
| 12 | 同上 `:439` | 断言消息文本 | 否 |
| 13 | 同上 `:465` | 反向冲突断言 | 否 |

⇒ **除 `static_assert` 外，所有引用都是符号引用**，改数值不会破坏编译或断言逻辑。

### 2.2 数值 `10037` —— 全树仅 1 处真引用

| 位置 | 性质 |
| --- | --- |
| `src/game_server/win32/win_net.hpp:27` | **唯一真引用**（常量定义） |
| `assets/backend/1004/Server/sku_tags.info:70`（`60216_9=10037_0`） | ❌ **无关**：游戏 SKU tag 数据 |
| `assets/backend/1004/MarketplaceSkus.json`（`productId:10037` / `itemId:10037` / `sku:10037`，共 5 处） | ❌ **无关**：商城 product/item/sku ID |

⇒ **没有任何测试、脚本、配置或文档把 `10037` 当作 socket 错误码使用。**

### 2.3 `WSAEALREADY` —— 3 处，全部与 `static_assert` 相关

`win_net.hpp:26`（注释）、`win_net.cpp:14`、`win_net.cpp:15`。**没有第二处代码依赖"该值 == WSAEALREADY"这一事实。**

### 2.4 相关但**不同对象**的同名字段（避免混淆）

`lastSocketError` 在树中有 **40 处**，但至少分属 **3 个不同对象**：

| 对象 | 类型/位置 | 与本项的关系 |
| --- | --- | --- |
| `CodolGameServer::SvNetworkStatus::lastSocketError` | `int` · `sv_network_mp.hpp:23` | **本项唯一目标** |
| `OlMod::DedicatedControl::Server` 的状态字段 | `std::atomic_int` · `DedicatedControl.cpp:188` | ❌ 另一个 socket（独立 `WSAStartup` 族），**不受影响** |
| `MatchmakingService::localGameServerEndpoint()` 的局部变量 | `std::uint32_t` · `MatchmakingService.cpp:201` | ❌ 只是接收出参的局部变量，**读完即弃** |

---

## 3. 是否属于公开 ABI / 外部协议

### 3.1 导出面（**是** —— 但只是数值，不是布局）

`src/game_server/Appmain.cpp:9508-9522`：

```cpp
    extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetTransportStatus(
        std::uint32_t *bound,
        std::uint32_t *port,
        std::uint32_t *packetsReceived,
        std::uint32_t *packetsSent,
        std::uint32_t *lastSocketError)
    {
        …
        *lastSocketError = static_cast<std::uint32_t>(status.lastSocketError);
        return true;
    }
```

| 维度 | 结论 |
| --- | --- |
| 函数签名 / 调用约定 / 参数个数与类型 | **不变**（改常量值不影响） |
| 结构体布局 | **不变**（没有结构体，只有 5 个 `uint32_t*` 出参） |
| 导出符号名 | **不变** |
| 返回**数值** | **会变**（冲突情形下由 `10037` 变为新值） |

⇒ **这不是 ABI 破坏，而是"可观察数值变化"。** 二者必须分开记录。

### 3.2 消费者（全树 3 处，均**不比较**该值）

| 消费者 | 位置 | 用法 | 是否依赖 10037 |
| --- | --- | --- | --- |
| 后端 `MatchmakingService` | `MatchmakingService.cpp:197-207` | 接收出参后**只检查 `bound`/`port`**；`lastSocketError` **被丢弃** | ❌ 否 |
| 游戏服务器自身日志 | `Appmain.cpp:6910` | 只做"值是否变化"的判定，用于决定要不要打日志 | ❌ 否 |
| 游戏服务器自身日志 | `Appmain.cpp:6949-6950` | `std::to_string` 后拼进文本 | ❌ 否 |
| Frida 工具 | `tools/runtime/CodolGameServerControl.py:1665` | `last_socket_error: lastSocketError.readU32()` —— **仅记录进返回字典**，该文件内 `last_socket_error` 只出现这一次 | ❌ 否 |

**注意**：`10048` / `WSAEADDRINUSE` 在 `src/` 中 **0 命中** ⇒ 树内**也没有**任何代码依赖"真实冲突码 = 10048"。运行日志里出现的 `error=10048` 是 OS 值经 `lastError()` 自然流出的，不是被代码写死的。

### 3.3 外部协议 / 线上格式（**否**）

| 检查 | 结果 |
| --- | --- |
| `sv_snapshot_mp.cpp` 中 `socketError`/`socket_error` | **0 命中** ⇒ 不进入快照 |
| gamestate / netchan / DTLS 写入 | 全树 `lastSocketError` 的 40 处命中中，**无一处**位于 `qcommon/` 的序列化路径 |
| 协议常量 / 消息布局 | 无关（该字段是**本地诊断量**） |

⇒ **它不在线上，不属于外部协议。**

---

## 4. 更换数值的兼容性影响

| 维度 | 影响 | 证据 |
| --- | --- | --- |
| 树内源码 | **无**（除必须同步的 `static_assert`） | §2.1 |
| 树内测试 | **无**（全部符号引用） | §2.1 #7-#13 |
| 树内脚本 | **无**（Frida 工具只记录） | §3.2 |
| 树内配置 / 文档 | **无**（`10037` 只出现在定义处） | §2.2 |
| 导出 API 数值 | **变**（冲突情形） | §3.1 |
| ABI 布局 / 符号 / 调用约定 | **不变** | §3.1 |
| 线上协议 | **不变** | §3.3 |
| 树外消费者 | **未知**。若存在硬编码 `10037` 的外部脚本，会失效 | 无法在树内证明不存在 |
| 编译 | 若保留 `static_assert` 则**编译失败**；必须同步处理 | `win_net.cpp:13-15` |

**风险评级**：**中**。树内风险为零，风险全部集中在"树外是否存在硬编码消费者"这一**不可在树内证伪**的命题上。

---

## 5. 替代方案对比

| 方案 | 做法 | 数值是否变 | 导出数值是否变 | 歧义是否消除 | 工作量 | 评价 |
| --- | --- | --- | --- | --- | --- | --- |
| **(A) 保留数值 + 新增合成标志** | 保持 `10037`；另加一个字段/新导出表示"该码是合成的" | 否 | **是**（新增出参 ⇒ 若改原函数签名则为 ABI 破坏） | ✅ | 中 | 若改原签名则 **ABI 破坏**，不可取；须走**新增导出**（见 (E)） |
| **(B) 私有错误域**（推荐） | `SocketAlreadyBoundError = 0x4F4C4D42`（`'OLMB'`，明显不在 Winsock 区间）；删除 `static_assert` | ✅ 变 | ✅ 变 | ✅ | **低**（2 个文件、约 6 行） | 一次改动彻底消除"合成码伪装成 OS 码"的问题；代价是导出数值变化 |
| **(C) 改用真实语义码** | 把冲突也报成 `WSAEADDRINUSE (10048)` | ✅ 变 | ✅ 变 | ❌ **反而丢失**区分度（"我方拒绝"与"OS 拒绝"合并） | 低 | 字段语义最统一，但诊断能力下降。**不推荐** |
| **(D) 零数值变更**（最低风险） | 保留 `10037` 与 `static_assert`；仅**改名 + 注释**（如 `SyntheticAlreadyBoundDiagnostic`）并明确记录"该值与真实 `WSAEALREADY` 不可区分" | 否 | 否 | ❌ 否（歧义仍在，但**已文档化**） | 最低（改名 + 注释） | **零兼容风险**；只把已知歧义写清楚，不消除它 |
| **(E) 加性扩展导出** | 保留原函数不变；**新增** `CODOL_GameServerGetTransportStatusEx` 返回扩展结构（含 `lastSocketErrorSynthetic` 布尔） | 否 | 否（原函数不动） | ✅ | 高（新增导出 + 结构 + 消费者接线） | 唯一"既不变数值又消除歧义"的方案；但**新增导出属于接口扩大**，需单独批准 |

### 5.1 建议

1. **首选 (B)**：如果目标是"调用方永远能区分合成原因与 OS 错误"，(B) 用最小改动达成，且树内零回归。
2. **次选 (D)**：如果"不改变任何可观察数值"是硬约束，(D) 是唯一零风险选项——但它**只是把歧义写清楚，不消除歧义**。
3. **(E)** 仅在"必须保留原数值 **且** 必须消除歧义"时才值得做；它会**扩大接口**，按授权纪律需单独审批。
4. **不推荐 (C)**。

### 5.2 若采纳 (B)，必须同步处理的事项

| # | 事项 | 位置 |
| --- | --- | --- |
| 1 | 改常量值并重写注释（说明为何不再镜像 `WSAEALREADY`） | `win_net.hpp:24-27` |
| 2 | **删除** `static_assert`（它会阻止新值编译） | `win_net.cpp:13-15` |
| 3 | 更新 `sv_network_mp.hpp` 中对 `SocketAlreadyBoundError` 的文档描述（"Numerically WSAEALREADY" 之类的表述若存在） | `sv_network_mp.hpp:54-58` |
| 4 | 新增断言：合成码不是真实 Winsock 码、且位于 Winsock 区间之外 | `TransportLifecycleTests.cpp` |
| 5 | 在变更记录中显式登记"导出 API 数值变化" | 本系列报告 |
| 6 | 强制重建并运行**全部** 4 个相关目标 | `ol_transport_lifecycle_tests` / `ol_game_server_tests` / `ol_lua_runtime_tests` / `ol_game_server` |

---

## 6. 本轮执行边界

| 项 | 状态 |
| --- | --- |
| 修改 `SocketAlreadyBoundError` 数值 | **未执行** |
| 删除 `static_assert` | **未执行** |
| 修改任何源码 | **未执行** |
| 构建 / 运行 | 未因本项触发（FF-3 无代码改动） |
| 客户端启动 / 注入 / 内存读取 / 部署 / Git 提交 | **未执行** |

**受保护文件哈希（本轮前后均未变）**：

| 文件 | SHA-256 |
| --- | --- |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` |

---

## 7. 关联交付

- [T1_FF1_PORT_RELEASE_REPORT.md](T1_FF1_PORT_RELEASE_REPORT.md) — FF-1 实施结果
- [T1_FF2_ERROR_STATE_REPORT.md](T1_FF2_ERROR_STATE_REPORT.md) — FF-2 实施结果
- [T1_FF4_DESTRUCTOR_REVIEW.md](T1_FF4_DESTRUCTOR_REVIEW.md) — FF-4 可行性审查（**未实施**）
