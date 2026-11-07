# NETWORK_UNLOAD_LIFECYCLE_REVIEW — DLL 卸载前停止网络传输的生命周期审查

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**
**本阶段性质**：**只读审查 + 建议。未修改任何源码，未新增导出，未改动 ABI/启动链。**
**审查对象**：全局 `Network` · `DLL_PROCESS_DETACH` 路径 · `Network.stop()` · `SvUdpTransport` 资源所有权

---

## 0. 结论速览

| # | 问题 | 答案 |
| --- | --- | --- |
| 1 | 是否存在宿主可调用的显式停止入口？ | **存在**：`CODOL_GameServerSetEnabled(false)`（导出，`Appmain.cpp:8174-8201`）。**但没有任何树内正常卸载路径调用它** |
| 2 | `Network.stop()` 能否报告 socket 关闭失败？ | **能**。返回 `bool`，失败时写 `lastSocketError` + 记日志；`SetEnabled` 消费该返回值并**返回 false** |
| 3 | 能否在正常卸载路径中、**加载器锁之外**执行停止？ | **现状不能。** 插件没有 loader 驱动的关闭钩子（无 `onShutdown`/`onUnload`，`DllMain` 只处理 `ATTACH`） |
| 4 | 最小架构改进是什么？ | **调用方侧**：把停止序列改成"先 `SetEnabled(false)`，再终止"。**无需改插件、无需改 ABI**（§4） |
| 5 | 是否应新增导出函数？ | **不需要**。`SetEnabled(false)` **已经**是停止入口；再加一个会重复既有能力并扩大 ABI。若将来确需"关闭专用语义"，属**新导出 ⇒ 独立 ABI 审批**（**未实施**） |

**一句话**：缺失的不是一个 API，而是**一个调用者**。加导出而不改调用方，等于什么都没做。

---

## 1. 资源所有权与生命周期事实

| 项 | 事实 | 来源 |
| --- | --- | --- |
| 传输实例 | `CodolGameServer::SvUdpTransport Network;` —— **命名空间作用域全局**，位于插件 DLL 内 | `src/game_server/Appmain.cpp:288` |
| socket 所有权 | `NetUdpSocket socket_` 是 `SvUdpTransport` 的**成员**；生产中没有第二个 `SvUdpTransport`，也没有第二个长生命周期 `NetUdpSocket` | `sv_network_mp.hpp:93` |
| 成员析构顺序 | 逆声明序，`socket_` **最后**析构（先 `mutex_`/`nonce_`/`peerStatus_`/`status_`/`receiveBuffer_`） | `sv_network_mp.hpp:93-98` |
| 插件 `DllMain` | **只处理 `DLL_PROCESS_ATTACH`**（`DisableThreadLibraryCalls` + `initialize()`）；`DLL_PROCESS_DETACH` 不做任何事 | `src/game_server/Appmain.cpp:9538-9546` |
| 关闭钩子 | **不存在**。全树 `onStartup`/`onInitialized` 有 3 个插件实现；`onShutdown` / `onUnload` **0 命中** | 全树检索 |
| 仓库对该窗口的既有纪律 | `"The plugin remains loaded for the process lifetime. Avoid joining a control thread from DLL teardown while the Windows loader lock is held."` | `src/game_server/Appmain.cpp:289-290` |
| 显式停止入口 | `CODOL_GameServerSetEnabled(false)` → `Network.stop()` | `src/game_server/Appmain.cpp:8174-8201` |

**`stop()` 的失败可报告性**（`sv_network_mp.cpp:72-86`）：

```cpp
    bool SvUdpTransport::stop()
    {
        const std::lock_guard lock(mutex_);
        if (!socket_.close())
        {
            const auto error = socket_.lastError();
            status_.lastSocketError = error;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("udp transport stop failed op=close error=") +
                    std::to_string(error));
            return false;
        }
        status_.bound = false;
        …
        return true;
    }
```

**上层消费**（`Appmain.cpp:8181-8199`）：`SetEnabled(false)` 捕获 `transportStopped`，失败时记录 `game server disable failed: udp transport is still bound` 并 **返回 false**（不再假装已停止）。

---

## 2. 五问逐条回答

### Q1 — 是否存在宿主可调用的显式停止入口？

**存在，且只有一个。**

| 项 | 内容 |
| --- | --- |
| 符号 | `CODOL_GameServerSetEnabled`（`extern "C" __declspec(dllexport) bool __cdecl`） |
| 停止语义 | `enabled == false` ⇒ `Network.stop()` |
| 返回值 | 成功 `true`；socket 未能释放时 **`false`** |
| 文档化 | 是（`Appmain.cpp:8190-8194` 的注释解释了为何要报失败） |
| 树内调用方 | **无**。`MatchmakingService.cpp:180-182` 只调用 `setEnabled(true)` |
| 树外调用方 | Frida 工具 `tools/runtime/CodolGameServerControl.py:1681-1684`（`action === 'disable'` ⇒ `setEnabled(0)`） |

**⇒ 入口存在，但缺调用者。**

### Q2 — `Network.stop()` 是否能够报告 socket 关闭失败？

**能，而且这条链路已经完整。**

```text
NetUdpSocket::close() 失败
   -> 保留句柄、设置 lastError_、返回 false
SvUdpTransport::stop() 失败
   -> status_.lastSocketError = error
   -> RuntimeLog: "udp transport stop failed op=close error=<code>"
   -> 返回 false（且**不**清 bound/port/计数器）
CODOL_GameServerSetEnabled(false)
   -> transportStopped == false
   -> logGameServer("game server disable failed: udp transport is still bound")
   -> 返回 false
```

**这是 FF-4 未实施的关键前提**：正确的诊断通道**已经存在**，只是需要有人调用它。

### Q3 — 能否在正常卸载路径中、加载器锁之外执行停止操作？

**现状：不能。** 逐路径核对：

| 路径 | 触发方式 | `DLL_PROCESS_DETACH` 是否运行 | 是否优雅停止 | 是否处于加载器锁 |
| --- | --- | --- | --- | --- |
| **P1** 启动器停止 | `CodolGame.py stop()` → `terminate_pids()` → `taskkill /PID <pid> /T /F`（`CodolGame.py:577-581`） | **否**（`/F` 走 `TerminateProcess`，不运行 DETACH） | **否**（OS 回收） | **否**（析构根本不运行） |
| **P2** 正常进程退出 | 用户关闭游戏 → `ExitProcess` | **是** | **否**（仅析构） | **是** ⇒ `~Network` → `~NetUdpSocket` → `close()` 在加载器锁下执行 |
| **P3** Frida 诊断 | `CodolGameServerControl.py` `action='disable'` | 进程仍存活 | **是**（`SetEnabled(false)`） | **否**（正常执行期） |

**结论**：P3 证明"在加载器锁之外优雅停止"在技术上**可行**；但 P3 是**树外诊断工具**，不是正常卸载路径。P1/P2 都没有优雅停止：P1 直接杀进程，P2 把释放留给了析构。

**⇒ 缺口是明确的：没有任何 *正常* 路径在卸载前调用 P3 的能力。**

### Q4 — 最小架构改进是什么？

**调用方侧改造（推荐，零插件改动、零 ABI 改动）：**

把停止序列从"直接终止"改为 **"先 `SetEnabled(false)`，再终止"**：

```text
现状 P1:  taskkill /F            -> 无优雅停止
建议 P1': SetEnabled(false)      -> 优雅停止（可报告失败）
          ; 检查返回值
          ; 再 taskkill /F
```

| 维度 | 评价 |
| --- | --- |
| 插件改动 | **0** |
| ABI / 导出布局改动 | **0** |
| 需要的既有能力 | `CODOL_GameServerSetEnabled(false)`（已存在）· Frida 控制工具（已存在 `disable` 动作） |
| 失败可观测 | ✅ 返回值 + `udp transport stop failed op=close error=<code>` + `game server disable failed: udp transport is still bound` |
| 与既有纪律一致 | ✅ 停止发生在**正常执行期**，不在加载器锁下 |
| 风险 | 低。若 `SetEnabled(false)` 失败，仍可回落到 `taskkill /F`（行为不劣于现状） |

**为什么不是"在 `DllMain` 里调 `stop()`"？** 因为 `DLL_PROCESS_DETACH` **同样持有加载器锁**——把工作从析构挪到 `DllMain` **不改变危险上下文**，只是换个位置。这属于**未改进**，且违反本阶段"不在 `DllMain` 或析构函数中添加复杂日志、线程同步、网络操作"的约束。

**为什么不是 `atexit`？** 静态析构/`atexit` 回调在 DLL 拆卸期运行，与 P2 同上下文，同样不改进。

**P2（正常进程退出）怎么办？** 在没有 loader 关闭钩子的前提下，**无法**在 P2 中保证"加载器锁之外"停止。可选项只有：
- 接受 P2 由析构释放（现状），并把它登记为**已知限制**；
- 或者让宿主在 `ExitProcess` 之前主动调用 `SetEnabled(false)`——这需要宿主配合，属 Q5 范畴。

### Q5 — 是否应增加新的导出函数？

**不需要，且不建议。**

| 理由 | 说明 |
| --- | --- |
| 能力已存在 | `SetEnabled(false)` 已提供"停止 + 报告失败" |
| 重复即膨胀 | 新增 `Shutdown` 只会与 `SetEnabled(false)` 语义重叠，扩大 ABI 面而无新增能力 |
| 加导出不解决根本问题 | 缺的是**调用者**，不是 API。新增导出若仍无人调用，P2 依旧不变 |
| 成本 | 新增导出属**接口扩大 ⇒ 需独立 ABI 审批** |

**若将来确需一个"关闭专用语义"**（例如"停止并拒绝后续 `enable`"/"幂等且不可逆的 teardown"），那是一个**新的设计决定**，需要：① 独立 ABI 审批；② 明确宿主侧的调用时机；③ 明确与 `SetEnabled` 的关系（是否废弃后者）。**本阶段不实施。**

---

## 3. 资源所有权审查（补充）

| 问题 | 结论 |
| --- | --- |
| 谁拥有 socket 句柄？ | `SvUdpTransport::socket_` 独占（RAII） |
| 谁负责释放？ | 三条路径：① `stop()`（显式，可报告失败）；② `~NetUdpSocket`（隐式，失败静默）；③ 进程终止（OS 回收） |
| 是否存在裸句柄？ | **否**。`NET_IPSocket` 的每条失败路径都自行 `close()`；所有实例都是 RAII 局部/成员 |
| `WSAStartup`/`WSACleanup` 配对 | 静态核对成对（`NET_IPSocket` 每次 `WSAStartup`；`close()` 成功时 `WSACleanup`）。**失败路径刻意跳过 `WSACleanup`**（见 [T1_FF4_DESTRUCTOR_REVIEW.md](T1_FF4_DESTRUCTOR_REVIEW.md) Q5）。**无运行时断言** |
| 析构失败可观测性 | **不可观测**（FF-4 未实施） |

---

## 4. 明确不做的事（边界遵从）

| 不做 | 原因 |
| --- | --- |
| 在 `DllMain` 中添加停止调用 | `DLL_PROCESS_DETACH` 持有加载器锁，与析构同上下文，**不改进** |
| 在析构中添加日志 / 线程同步 / 网络操作 | 本阶段明确禁止；且见 FF-4 审查结论 |
| 新增导出函数 | 需独立 ABI 审批；且**未实施** |
| 修改 `SetEnabled` 的语义或签名 | 会破坏既有调用方（后端 + Frida 工具） |
| 让插件自行注册 loader 回调 | 会引入新的 ABI/生命周期契约，且无法避免加载器锁 |

---

## 5. 建议（按优先级）

| 优先级 | 建议 | 类型 |
| --- | --- | --- |
| **P-1** | 把正常停止序列改为"先 `SetEnabled(false)`，再终止"（§4 的 P1′） | **调用方/工具改动**，零插件改动 |
| **P-2** | 把 P2（正常进程退出时由析构在加载器锁下释放）登记为**已知限制**，并写明"失败不可观测" | 文档 |
| **P-3** | 若要覆盖 P2，需先决定宿主侧协议（谁在 `ExitProcess` 前调用停止），再评估是否需要新导出 ⇒ **独立 ABI 审批** | 待审批 |

---

## 6. 证据分级

### ✅ 已验证行为

| 行为 | 证据 |
| --- | --- |
| `stop()` 失败时会返回 false 并保留绑定 | 测试 `[simulated-close-failure]`（`checks=124 failures=0`） |
| `stop()` 成功后释放 OS 端口 | 测试 `[4/8]` 的 OS 层探针（FF-1） |
| `stop()` 后 `bound=false / port=0`、计数器与时间戳清零 | 测试 `[4/8]` |
| 全部 4 个相关目标构建/运行通过 | [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md) §A4 |

### 📄 仅由静态审查支持的结论

| 结论 | 依据 |
| --- | --- |
| `CODOL_GameServerSetEnabled(false)` 是唯一显式停止入口 | 全树 `SetEnabled` 5 处引用（导出定义 + 后端 `GetProcAddress` + Frida 3 处） |
| 插件没有 loader 驱动的关闭钩子 | `onShutdown`/`onUnload` 全树 0 命中；`DllMain` 只处理 `ATTACH` |
| `CodolGame.py stop()` 走 `taskkill /T /F`，因此不运行 `DLL_PROCESS_DETACH` | `CodolGame.py:577-581` + `:910-943` |
| 树内无调用方以 `false` 调用 `SetEnabled` | `MatchmakingService.cpp:180-182` 只传 `true` |

### ❓ 尚未验证的运行时假设

| 假设 | 说明 |
| --- | --- |
| 真实客户端进程退出时确实走 `ExitProcess`（而非被强杀） | 未观测 |
| 在加载器锁下 `closesocket`/`WSACleanup` 的实际行为 | 未观测；FF-4 因此未实施 |
| Frida `disable` 路径在真实客户端上可稳定调用 | 未在真实客户端上验证（需授权启动） |
| `taskkill /F` 后 OS 回收 socket 的时序 | 未观测（属 OS 行为） |

### ⚠️ 需要单独审批的接口变更

| 变更 | 状态 |
| --- | --- |
| 新增关闭专用导出函数 | **未实施 · 需独立 ABI 审批** |
| 修改 `SetEnabled` 签名/语义 | **未实施 · 会破坏既有调用方** |

---

## 7. 关联交付

- [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md) — 已冻结的通过基线
- [T1_FF3_ERROR_DOMAIN_DECISION.md](T1_FF3_ERROR_DOMAIN_DECISION.md) — 错误码决策依据
- [T1_FF4_DESTRUCTOR_REVIEW.md](T1_FF4_DESTRUCTOR_REVIEW.md) — 析构可观测性审查（未实施）
