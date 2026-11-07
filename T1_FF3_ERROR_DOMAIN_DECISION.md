# T1_FF3_ERROR_DOMAIN_DECISION — 合成错误码歧义的决策依据

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**
**本阶段性质**：**只读审查 + 决策建议。未修改 FF-3 生产代码；未改变任何数值、结构布局、ABI、协议、RVA、启动链或 S2-S3 默认值。**
**状态**：**RECOMMENDATION ONLY — 任何需要改变数值或导出布局的方案均等待独立审批。**

---

## 0. 结论速览

| 问题 | 答案 |
| --- | --- |
| 能否在**不改变数值、不改变导出布局**的前提下解决歧义？ | **能。** 存在一个**零变更判别器**（§4）：`status_.bound` 的取值不变式 + `10037` 在本 socket 上作为原生错误的**不可达性** |
| 推荐方案 | **A′ = 方案 A（保留 10037）+ 把判别不变式写入文档 + 加回归测试**。**零兼容风险** |
| 若必须改变数值域 | 方案 **B**（私有域 `0x4F4C4D42`）优于方案 **D**（`WSAEADDRINUSE`）；两者都改变可观察数值 ⇒ **需审批 + 外部消费者风险声明** |
| 若必须机器强制判别 | 方案 **C2**（**新增**导出，不改原符号）——**新增接口 ⇒ 需独立 ABI 审批** |
| 方案 **C1**（给原导出加第 6 个出参） | ❌ **ABI 破坏**，不可接受 |
| 树内是否有人比较 `10037` | **没有**——但这**不构成**"外部消费者不存在"的证明（§7 明确声明） |

---

## 1. 只读检查范围

| 对象 | 位置 |
| --- | --- |
| `SocketAlreadyBoundError` | `src/game_server/win32/win_net.hpp:24-27`（定义）· `win_net.cpp:13-15`（`static_assert`） |
| `SvNetworkStatus::lastSocketError` | `src/game_server/server_mp/sv_network_mp.hpp:23` |
| `CODOL_GameServerGetTransportStatus` | `src/game_server/Appmain.cpp:9508-9522` |
| 全部消费者 | 见 §2、§3 |

---

## 2. 引用清单（全树检索）

### 2.1 `SocketAlreadyBoundError` —— 13 处

| 位置 | 用法 | 改数值是否受影响 |
| --- | --- | --- |
| `win_net.hpp:27` | 定义 `= 10037` | 定义处 |
| `win_net.cpp:14` | `static_assert(SocketAlreadyBoundError == WSAEALREADY, …)` | ✅ **必须同步处理**（否则编译失败） |
| `win_net.cpp:15` | 上述断言的消息文本 | ✅ 同上 |
| `sv_network_mp.cpp:35` | `status_.lastSocketError = SocketAlreadyBoundError;`（端口冲突） | 否（符号引用） |
| `sv_network_mp.cpp:46` | 同上（地址冲突） | 否 |
| `sv_network_mp.hpp:56` | 文档注释提及常量名 | 否 |
| `TransportLifecycleTests.cpp:36` | `using` 声明 | 否 |
| `TransportLifecycleTests.cpp:280/281` | 端口冲突断言 + 消息 | 否（符号引用） |
| `TransportLifecycleTests.cpp:340` | 粘性错误断言 | 否 |
| `TransportLifecycleTests.cpp:438/439` | 地址冲突断言 + 消息 | 否 |
| `TransportLifecycleTests.cpp:465` | 反向冲突断言 | 否 |

### 2.2 数值 `10037` —— 全树仅 1 处真引用

| 位置 | 性质 |
| --- | --- |
| `src/game_server/win32/win_net.hpp:27` | **唯一真引用**（常量定义） |
| `assets/backend/1004/Server/sku_tags.info:70`（`60216_9=10037_0`） | ❌ **无关**：游戏 SKU tag 数据 |
| `assets/backend/1004/MarketplaceSkus.json`（`productId:10037` / `itemId:10037` / `sku:10037`，共 5 处） | ❌ **无关**：商城 product/item/sku ID |

### 2.3 `WSAEALREADY` —— 3 处，全部服务于 `static_assert`

`win_net.hpp:26`（注释）· `win_net.cpp:14` · `win_net.cpp:15`。**没有第二处代码依赖"该值 == WSAEALREADY"。**

### 2.4 同名字段的其它对象（防混淆）

`lastSocketError` 全树 40 处，分属至少 **3 个不同对象**：

| 对象 | 类型 | 与本项关系 |
| --- | --- | --- |
| `CodolGameServer::SvNetworkStatus::lastSocketError` | `int`（`sv_network_mp.hpp:23`） | **本项唯一目标** |
| `OlMod::DedicatedControl` 的状态字段 | `std::atomic_int`（`DedicatedControl.cpp:188`） | ❌ 另一个 socket |
| `MatchmakingService::localGameServerEndpoint()` 局部变量 | `std::uint32_t`（`MatchmakingService.cpp:201`） | ❌ 出参暂存，读完即弃 |

---

## 3. 导出面与协议面

### 3.1 导出接口（数值可观察，布局不变）

`src/game_server/Appmain.cpp:9508-9522`：

```cpp
    extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetTransportStatus(
        std::uint32_t *bound,
        std::uint32_t *port,
        std::uint32_t *packetsReceived,
        std::uint32_t *packetsSent,
        std::uint32_t *lastSocketError)
    {
        if (!ensureInstalled() || !bound || !port || !packetsReceived ||
            !packetsSent || !lastSocketError)
            return false;
        const auto status = Network.status();
        *bound = status.bound ? 1u : 0u;
        *port = status.port;
        *packetsReceived = status.packetsReceived;
        *packetsSent = status.packetsSent;
        *lastSocketError = static_cast<std::uint32_t>(status.lastSocketError);
        return true;
    }
```

| 维度 | 结论 |
| --- | --- |
| 函数签名 / 调用约定 / 参数个数与类型 | 改**数值**不影响；**加第 6 个出参**会破坏 |
| 结构体布局 | 无结构体，只有 5 个 `uint32_t*` 出参 |
| 导出符号名 | 不变 |
| 返回**数值** | 方案 B/D 会改变冲突情形下的取值 |

### 3.2 消费者（全树 4 处，**均不比较该值**）

| 消费者 | 位置 | 用法 | 依赖 `10037`？ |
| --- | --- | --- | --- |
| 后端 `MatchmakingService` | `MatchmakingService.cpp:197-207` | 接收出参后只检查 `bound`/`port`；`lastSocketError` **被丢弃** | ❌ |
| 游戏服务器日志（变更检测） | `appmain.cpp:6910` | 只判断"值是否变化"以决定是否打日志 | ❌ |
| 游戏服务器日志（文本） | `appmain.cpp:6949-6950` | `std::to_string` 拼接 | ❌ |
| Frida 工具 | `tools/runtime/CodolGameServerControl.py:1665` | `last_socket_error: lastSocketError.readU32()` —— 仅记录进返回字典（该文件中 `last_socket_error` 只出现这一次） | ❌ |

**补充事实**：`10048` / `WSAEADDRINUSE` 在 `src/` 中 **0 命中** ⇒ 树内也没有代码把"真实冲突码 = 10048"写死。运行日志里出现的 `error=10048` 是 OS 值经 `lastError()` 自然流出。

### 3.3 线上协议（**否**）

| 检查 | 结果 |
| --- | --- |
| `sv_snapshot_mp.cpp` 中 `socketError`/`socket_error` | **0 命中** |
| `lastSocketError` 的 40 处命中中是否有 `qcommon/` 序列化路径 | **无** |
| 结论 | 该字段是**本地诊断量**，**不进入任何线上格式** |

---

## 4. 关键发现：零变更判别器

### 4.1 不变式：`status_.bound == socket_.open()`

`status_.bound` 在**全树只有 2 处写**：

| 位置 | 上下文 |
| --- | --- |
| `sv_network_mp.cpp:67` | `status_.bound = true;` —— **紧接**成功的 `NET_IPSocket` |
| `sv_network_mp.cpp:87` | `status_.bound = false;` —— **紧接**成功的 `close()` |

⇒ 在稳态下 **`status_.bound` 为真 ⟺ `socket_.open()` 为真**。

### 4.2 推论：合成冲突必然伴随 `bound == 1`

合成冲突只在 `start()` 的 `if (socket_.open())` 分支内产生（`:35`、`:46`）。由 §4.1，此时 `status_.bound == 1`。

相反，**真实的 `bind` 失败**发生在 `status_ = {};` 之后（`:51` → `:64`），因此必然伴随 `bound == 0`。

### 4.3 推论：`10037` 在本 socket 上作为**原生错误**不可达

该传输的 socket 从不调用 `connect()` / `WSAConnect()`（`win_net.cpp` 与 `sv_network_mp.cpp` 中 `connect` **0 命中**）。它对 socket 的操作可完整枚举：

`ioctlsocket(FIONBIO)` · `setsockopt(SO_BROADCAST)` · `bind` · `getsockname` · `recvfrom` · `sendto` · `closesocket`

`WSAEALREADY` 的语义是"非阻塞 connect 正在进行"，**这些调用都不会产生它**。

### 4.4 由此得到的判别规则

```text
lastSocketError == SocketAlreadyBoundError (10037)
    => 必然是本项目的合成"已绑定冲突"，不是原生 Winsock 错误

判据一（值域）: 10037 在本 socket 上只由 :35 / :46 两处写入
判据二（不变式）: 该冲突发生时 status_.bound == 1，而真实 bind 失败时 == 0
```

**⇒ 歧义可以在"不改数值、不改布局"的前提下被消除**，代价是它是一个**文档化的约定**，而非类型强制的保证。

### 4.5 该发现的边界（诚实标注）

| 边界 | 说明 |
| --- | --- |
| 依赖 `bound` 被正确维护 | 若将来新增写 `status_.bound` 的路径，不变式需要同步复核。**建议加断言固化** |
| 只覆盖"合成冲突 vs 真实 bind 失败" | 真实错误**在 bound==1 时**也可能出现（`NET_Frame` `:108`、`NET_SendPacket` `:167` 会写该字段），但那些路径不会产出 10037 |
| 属**静态审查结论** | 本轮未在真实客户端上观测；不过 socket API 的使用面可从源码完整枚举 |

---

## 5. 四方案对比

### 方案 A — 继续使用 10037，仅完善命名与文档

| 维度 | 结论 |
| --- | --- |
| **对公开字段与导出接口的影响** | **无**。字段类型/位置、函数签名、符号名、结构布局全不变 |
| **是否改变现有可观察数值** | **否** |
| **现有消费者兼容性** | **完全兼容**（树内 4 处消费者均不比较该值） |
| **测试需求** | ① 断言"合成码不是真实 Winsock 码"；② 断言"合成冲突发生时 `bound == 1`、真实 bind 失败时 `bound == 0`"（固化 §4 不变式）；③ 断言 `static_assert` 仍锁定 `== WSAEALREADY` |
| **迁移方式** | 无迁移：只改注释与常量名（可选），无行为变化 |
| **回滚方式** | 无回滚需求（若仅改注释，`git checkout` 该文件即可） |
| **残留** | 数值域歧义**未在类型层面**消除，只被文档与不变式约束 |

### 方案 A′ — **A + 不变式文档化 + 回归测试**（**推荐**）

在 A 的基础上把 §4 的判别规则写进 `win_net.hpp` / `sv_network_mp.hpp` 的契约注释，并加两条回归断言固化不变式。

| 维度 | 结论 |
| --- | --- |
| **对公开字段与导出接口的影响** | **无** |
| **是否改变现有可观察数值** | **否** |
| **现有消费者兼容性** | **完全兼容**；并且消费者**第一次获得**一个可依据的判别规则 |
| **测试需求** | A 的 3 条 + ④ 一条"冲突路径不得改变 `bound` / `port` / 计数器"的断言 |
| **迁移方式** | 无迁移 |
| **回滚方式** | 注释与测试回滚；无生产行为变化 |
| **风险** | 最低。唯一"代价"是判别依赖约定而非类型 |

### 方案 B — 私有错误域（`0x4F4C4D42`）

| 维度 | 结论 |
| --- | --- |
| **对公开字段与导出接口的影响** | 字段类型/位置、签名、符号名**不变**；但 `static_assert` 必须**删除**（否则编译失败） |
| **是否改变现有可观察数值** | **是**：冲突情形下导出值 `10037` → `0x4F4C4D42` |
| **现有消费者兼容性** | 树内 4 处**均不受影响**（不比较该值）。**树外消费者未知**（见 §7） |
| **测试需求** | 现有 4 处 `SocketAlreadyBoundError` 断言改为符号引用（已如此，无需改）；新增"该值位于 Winsock 区间之外"的断言；`[8/8]` 的真实冲突码断言 |
| **迁移方式** | 一次性改常量 + 删断言 + 更新文档；需与外部消费者协调窗口 |
| **回滚方式** | 恢复 `10037` 与 `static_assert`；但**已发出的日志/已缓存的值无法回收** |
| **风险** | 中。风险全部集中在"树外是否硬编码 `10037`"，**不可在树内证伪** |

### 方案 C — 增加错误来源字段

拆成两个子方案：

**C1 — 给原导出加第 6 个出参** ❌

| 维度 | 结论 |
| --- | --- |
| 对导出接口的影响 | **破坏**：参数个数变化 ⇒ 调用方栈/寄存器约定变化 ⇒ **ABI 破坏** |
| 现有消费者兼容性 | 后端 `MatchmakingService.cpp:191-193` 的 `reinterpret_cast` 函数指针类型会**不匹配**；Frida 工具 `CodolGameServerControl.py:1234-1236` 的 `Memory.alloc(4)` 分配数也不匹配 |
| 结论 | **不可接受**，不进入候选 |

**C2 — 新增独立导出（不改原符号）** ⚠️

| 维度 | 结论 |
| --- | --- |
| **对公开字段与导出接口的影响** | 原函数**完全不变**；**新增**一个符号（例如 `CODOL_GameServerGetTransportStatusV2`）与一个新的出参结构 |
| **是否改变现有可观察数值** | **否**（原函数保持原样） |
| **现有消费者兼容性** | **完全兼容**（老调用方不受影响） |
| **测试需求** | 新旧两个导出的一致性断言（同一时刻两者报告的 `bound`/`port` 必须相同）；新字段的语义断言 |
| **迁移方式** | 消费者可择时迁移；老路径长期保留 |
| **回滚方式** | 删除新导出即可，无副作用 |
| **风险** | 低（技术上），但**新增导出属于接口扩大 ⇒ 需独立 ABI 审批** |

### 方案 D — 改用 `WSAEADDRINUSE`

| 维度 | 结论 |
| --- | --- |
| **对公开字段与导出接口的影响** | 同 B：签名不变，但 `static_assert` 需删除 |
| **是否改变现有可观察数值** | **是**：`10037` → `10048` |
| **现有消费者兼容性** | 树内不受影响；**树外风险与 B 同类**，但方向相反：外部消费者若把 `10048` 理解为"OS 拒绝了 bind"，会把合成冲突误读为原生失败 |
| **测试需求** | 同 B；另需断言"`bound==1` 时出现 10048 只能是合成冲突" |
| **迁移方式** | 同 B |
| **回滚方式** | 同 B |
| **风险** | 中。**语义更"正确"但判别反而更依赖 §4 的不变式**（因为 10048 本身在两种情形下都可能出现） |

---

## 6. 决策建议

### 6.1 分层结论

| 层次 | 建议 | 是否需要审批 |
| --- | --- | --- |
| **第 1 层（立即）** | 采用 **A′**：保留 `10037` 与 `static_assert`，把 §4 的判别不变式写入契约注释，并加 4 条回归断言固化它 | 改注释 + 加测试：**低风险**，但仍属源码改动，建议走同一审批流程 |
| **第 2 层（若需机器强制判别）** | **C2**：新增导出，原符号不动 | **需独立 ABI 审批** |
| **第 3 层（若项目决定必须更换数值域）** | **B** 优于 **D** | **需审批 + 外部消费者风险声明** |
| **不推荐** | **C1**（ABI 破坏）、**D**（判别反而更依赖约定） | — |

### 6.2 为什么 A′ 足以满足本次任务的目标

任务要求"优先评估能否在不破坏既有导出布局和既有数值语义的前提下解决歧义"。A′ 的答案是：**能**。歧义的实质不是"数值不够独特"，而是"**这个数值会不会由 OS 产生**"——而 §4.3 证明它**不会**。把这一事实写进契约并加断言，比更换数值更保守，也**不引入任何外部兼容风险**。

### 6.3 若最终选择 B 或 C2，必须一并记录的风险

| 风险 | 处置 |
| --- | --- |
| 树外消费者可能硬编码 `10037` | 变更前发布通知；在变更说明中标注"导出数值变化"；保留一个过渡期（C2 的加性路径天然满足） |
| `static_assert` 删除后失去"值不会漂移"的编译期保护 | 用一条运行期断言替代（"该值不在 Winsock 区间内"） |
| 日志/历史记录中同时存在新旧数值 | 在变更记录中给出映射表（`10037` → 新值） |

---

## 7. 关于外部消费者的诚实声明

> **本节是本文件的强制免责声明。**

**"树内没有消费者比较 `10037`" 不能、也不得被当作 "外部消费者不存在" 的证明。**

理由：

1. 该值经 `CODOL_GameServerGetTransportStatus` **导出**，任何加载本插件的进程都能读取它；
2. 本仓库无法枚举树外的脚本、日志分析器、监控面板、其它工具链；
3. 该值已经出现在**运行日志文本**中（`appmain.cpp:6949-6950` 的 `socketError=` 字段），因此它已经进入了**可被外部采集的数据面**；
4. 历史日志一旦写出即不可回收。

因此：
- 方案 B / D 的"树内兼容性 = 完全兼容"这一结论，**只覆盖树内**；
- 任何改变该数值的决定，都必须**明确承认**"树外影响未知"，并在变更说明中如实记录；
- 本文件**不主张**外部消费者不存在。

---

## 8. 需要单独审批的变更清单

| # | 变更 | 影响面 | 审批类型 |
| --- | --- | --- | --- |
| 1 | A′ 的注释 + 测试改动 | 无行为变化 | 常规源码改动审批 |
| 2 | **C2 新增导出** | **新增导出符号** | **独立 ABI 审批** |
| 3 | **B / D 更换数值** | **导出数值变化** | 审批 + 外部影响声明 |
| 4 | C1 给原导出加参数 | **ABI 破坏** | **不予建议** |

---

## 9. 测试需求汇总（若采纳 A′）

| # | 断言 | 目的 |
| --- | --- | --- |
| 1 | `SocketAlreadyBoundError == WSAEALREADY`（由既有 `static_assert` 保证） | 值不漂移 |
| 2 | 冲突后 `status().bound == true` 且 `lastSocketError == SocketAlreadyBoundError` | 固化"合成 ⇒ bound==1" |
| 3 | 占用端口导致的真实 bind 失败后 `status().bound == false` 且 `lastSocketError != 0` | 固化"真实 bind 失败 ⇒ bound==0" |
| 4 | 冲突路径不改变 `port` / 计数器 / 时间戳 | 冲突是纯拒绝 |
| 5 | （若采纳 B）`SocketAlreadyBoundError` 落在 Winsock 区间之外 | 值域隔离 |

**预期断言数变化**：124 → 约 130（以实施时实测为准）。**不得删除或弱化既有断言。**

---

## 10. 本阶段执行边界

| 项 | 状态 |
| --- | --- |
| 修改 `SocketAlreadyBoundError` 数值 | **未执行** |
| 删除 `static_assert` | **未执行** |
| 修改任何生产源码 | **未执行** |
| 改变 ABI / 导出布局 / 协议 / RVA / 启动链 / S2-S3 | **未执行** |
| 新增导出 | **未执行** |
| 构建 / 运行 | 未因本项触发（无代码改动） |
| 客户端启动 / 注入 / 内存读取 / 部署 / Git 提交 | **未执行** |

**受保护文件哈希（本轮前后均未变）**：

| 文件 | SHA-256 |
| --- | --- |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` |
| `src/game_server/server_mp/sv_network_mp.cpp` | `EF4E209BDD9EFDCD5A1F7F69B3789E77852FD98C1371D7C1154677EEBFF19B60` |

---

## 关联交付

- [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md) — 已冻结的通过基线
- [NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md) — 卸载生命周期审查
- [T1_FF3_ERROR_CODE_COMPATIBILITY.md](T1_FF3_ERROR_CODE_COMPATIBILITY.md) — 上一轮的兼容性分析（本文件在其基础上给出决策）
