# T2_CALLER_SHUTDOWN_FLOW — 真实调用链、调用顺序与证据等级

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd`，`OLfinal-live`）
**前置**：已读 [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md)、[NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md)、[T1_FF3_ERROR_DOMAIN_DECISION.md](T1_FF3_ERROR_DOMAIN_DECISION.md)、`_t1_fix_evidence/REPRODUCE.ps1`
**本文件性质**：调用链核查。**未启动客户端、未注入、未读进程内存、未部署。**

---

## 0. 结论速览

| 问题 | 答案 | 等级 |
| --- | --- | --- |
| 是否存在可以复用的调用方停止路径？ | **存在一条**：`CodolGameServerControl.py --disable`（Frida 附加后调用导出）。改动前**没有任何调用方使用它** | ✅ 静态可验证 + 代码路径完整 |
| 停止请求是否确定发生在进程终止之前？ | **改动前：否**（`CodolGame.py stop()` 直接 `taskkill /T /F`）。**改动后：是**（在 `terminate_pids` 之前逐个 client PID 请求停止） | ✅ 调用顺序由测试断言 |
| 停止失败能否被调用方观察到？ | **能**。三层可观察：① 导出返回 `false`；② 工具退出码 **2** + JSON `{"ok": false, "error": ...}`；③ 插件日志 `udp transport stop failed op=close error=<code>`。改动后 `CodolGame.stop()` 在**插件明确拒绝**时返回 **4** | ✅ 分支由测试覆盖 |
| 是否有无需新增导出的现有调用路径？ | **有，且只有这一条**。DedicatedControl 控制通道**没有**停止命令；插件**不**监视任何文件；`Server.setEnabled(false)` 没有其它调用者 | ✅ 全树检索 |
| 停止失败后调用方是否继续终止并丢失错误？ | **改动前：是**（既不停、也不报）。**改动后：仍继续终止**（调用方要求的就是停止），但**错误被明确打印且不静默**，且插件拒绝时退出码为 4 | ✅ 分支由测试覆盖 |
| 是否有任何 ABI / 部署 / 游戏运行 / 进程注入行为发生？ | **没有**。未改导出、未部署、未启动游戏、未注入 | ✅ 见 §7 |

---

## 1. 三条路径的完整链路

### P1 — 启动器停止（`CodolGame.py stop`）

**改动前**（HEAD 版本）：

```text
stop(game_directory)
  -> pids = running_pids()                       # tasklist 过滤 TARGET_NAME
  -> room_owner_pid = (读 process state + 校验镜像名)
  -> 若两者皆空: 删除 state 文件, 打印 "CODOL is not running", return 0
  -> stopped = pids + [room_owner_pid?]
  -> failed = terminate_pids(stopped)            # taskkill /PID <pid> /T /F
  -> 等待最多 5 s 直到 running_pids() 为空
  -> failed |= 剩余 pid
  -> 若 failed: 打印 "Could not stop PID(s): ...", return 3
  -> 删除 state 文件, 打印 "Stopped ol-mod PID(s): ...", return 0
```

**关键事实**：**整条路径没有任何一次对插件停止入口的调用**。`CodolGame.py` 全文 **0 处** Frida 引用（`frida|attach|spawn|resume` 检索为空）。

**改动后**：在 `terminate_pids` 之前插入逐 PID 的 `request_graceful_stop(pid)`（见 [T2_IMPLEMENTATION_AND_TEST_REPORT.md](T2_IMPLEMENTATION_AND_TEST_REPORT.md)）。

### P2 — 正常进程退出

```text
用户关闭游戏 -> ExitProcess
  -> 所有已加载 DLL 收到 DLL_PROCESS_DETACH（加载器锁被持有）
  -> CRT 静态析构 -> ~SvUdpTransport Network -> ~NetUdpSocket -> close()
```

**没有任何 loader 驱动的关闭钩子**：插件 `DllMain`（`Appmain.cpp:9538-9546`）**只处理 `DLL_PROCESS_ATTACH`**；`onShutdown` / `onUnload` 全树 **0 命中**。因此 P2 **无法**在加载器锁之外停止传输。

### P3 — Frida 诊断路径（`CodolGameServerControl.py --disable`）

```text
main()
  -> action = "disable"                                   # :104
  -> device = frida.get_local_device()                    # :105
  -> pid = find_pid(device, args.pid)                     # :106, :49-59
  -> session = device.attach(pid)                         # :110   ← 进程内附加
  -> script = session.create_script(source)               # :1707
  -> script.load()                                        # :1758
        JS:
          plugin = Process.getModuleByName(PLUGIN_NAME)
          setEnabled = new NativeFunction(
              plugin.getExportByName('CODOL_GameServerSetEnabled'),
              'bool', ['bool'])                            # :189-193
          if (action === 'disable' && !setEnabled(0))
              throw new Error('CODOL_GameServerSetEnabled(false) failed')  # :1683-1684
          emitStatus()  -> send({ok:true, before, after})  # :1687-1696
        catch -> send({ok:false, error: error.stack})      # :1703-1705
  -> on_message: 若 payload.ok is False -> result.update(payload); done.set()  # :1712-1714, :1728-1731
  -> 超时上限: done.wait(sample_seconds + 10.0)            # :1760
  -> finally: script.unload(); session.detach()            # :1772-1779
  -> print(json.dumps(result)); return 0 if result.ok else 2   # :1781-1782
```

**返回值处理链**：插件 `SetEnabled(false)` 返回 `false` → JS `throw` → `send({ok:false})` → Python `result={"ok":False,...}` → **进程退出码 2**。

### 顺序总览（改动后）

```text
[P1'] stop()
  1. running_pids()                  -> 得到 client PID
  2. request_graceful_stop(pid)      -> 子进程 CodolGameServerControl.py --disable --pid <pid>
                                         -> Frida attach -> CODOL_GameServerSetEnabled(false)
                                         -> 退出码 0 / 2 -> ("confirmed" / "refused" / "unavailable")
  3. terminate_pids(stopped)         -> taskkill /T /F        ← 只有在第 2 步之后才发生
```

---

## 2. `CODOL_GameServerSetEnabled(false)` 的调用约定与调用上下文

| 项 | 值 | 来源 |
| --- | --- | --- |
| 符号 | `CODOL_GameServerSetEnabled`（`extern "C" __declspec(dllexport)`） | `src/game_server/Appmain.cpp:8174` |
| 调用约定 | `bool __cdecl (bool)` —— 单参数、C 链接 | 同上 |
| Frida 绑定 | `new NativeFunction(getExportByName(...), 'bool', ['bool'])` | `CodolGameServerControl.py:189-193` |
| 可用调用上下文 | **必须在目标进程内**（导出函数）。外部进程只能通过注入/附加到达 | 由导出语义决定 |
| 停止语义 | `enabled == false` → `Network.stop()` | `Appmain.cpp:8181-8198` |
| 成功返回 | `true` | 同上 |
| 失败返回 | `false` —— socket 未释放；插件记录 `game server disable failed: udp transport is still bound` | `Appmain.cpp:8188-8198` |
| `lastSocketError` 获取 | `CODOL_GameServerGetTransportStatus(&bound,&port,&recv,&sent,&lastSocketError)`（`Appmain.cpp:9508-9522`），Frida 侧 `getTransportStatus`（`CodolGameServerControl.py:554`） | 同上 |
| 树内其它调用者 | `MatchmakingService.cpp:180-182`，**只传 `true`** | 全树检索 |

**注意**：`--disable` 的失败路径只发出 `ok:false + error 文本`，**不含** `lastSocketError`（因为 `throw` 跳过了 `emitStatus()`）。socket 错误码只在插件日志 `udp transport stop failed op=close error=<code>` 中。**这是一个已记录的诊断信息缺口，未在本次修复范围内。**

---

## 3. 是否存在无需新增导出的现有调用路径

**结论：存在一条，且唯一。**

| 候选机制 | 是否存在 | 证据 |
| --- | --- | --- |
| DedicatedControl 控制通道的停止命令 | ❌ **不存在** | `DedicatedControl.hpp:23-82` 的 `MessageType` 枚举为 `1-12` 与 `16-20`（Booking/CaptureLoadout/SessionStart/ConfigureSession/QueryEndpoint/QueryGameplayStatus/SetNoclip/UpdateLoadout/RunDiagnostic/PlayAnnouncer/SendRawCommand/DebugGrantBattery/RoomConnect/RoomDisconnect/RoomSetReady/RoomFreeze/RoomCanonicalizeSession）——**没有任何停止/禁用/关闭项** |
| 文件 / 哨兵触发 | ❌ **不存在** | 全树检索 `stop-file|shutdown.flag|WatchFile|FindFirstChangeNotification` 在 `src/` 无命中 |
| `Server.setEnabled(false)` 的其它调用者 | ❌ **不存在** | 全树 `setEnabled(` 5 处：`appmain.cpp:2098`（true）、`:8180`（转发形参）、`MatchmakingService.cpp:182`（true）、`sv_main_mp.cpp:1166`（定义）、`sv_main_mp.hpp:721`（声明） |
| loader 关闭钩子 | ❌ **不存在** | 见 §1 P2 |
| Frida 附加调用导出 | ✅ **存在** | `CodolGameServerControl.py --disable` |

**⇒ 结论**：不需要新增导出。`SetEnabled(false)` 就是停止入口；缺的只是**调用方**。

**但不能仅凭函数存在就认定调用方能够安全调用** —— 因此下节记录调用方的安全边界。

---

## 4. 调用方可安全性的核查结果

| 核查项 | 结论 |
| --- | --- |
| 是否有非注入路径 | ❌ **没有**（§3）。到达导出必须进程内执行 |
| 现有工具是否已安全实现该调用 | ✅ `CodolGameServerControl.py` 已完整实现：attach 错误分类处理（`FRIDA_ATTACH_ERRORS`，`:21-31, :111-118`）、返回值检查（`:1683-1684`）、错误传播（`:1703-1705`）、退出码（`:1782`） |
| 直接在 `CodolGame.py` 内 **import** 该工具是否安全 | ❌ **不安全**。该模块在导入期执行 `configure_frida_runtime()`（`:13-15`），而它会改写进程级 `TEMP/TMP/TMPDIR` 与 `tempfile.tempdir`（`CodolFridaRuntime.py:33-36`）并清理 `.runtime/frida` 下超过 24 小时的目录（`:17-26, :45`）。这会污染**启动器**进程。**⇒ 必须以子进程方式调用**（本次实现采用） |
| 声明依赖是否满足 | ⚠️ `requirements-codol.txt` 声明 `frida>=17,<18`；本机实测 **16.5.9**。已核对 `CodolGameServerControl.py` 使用的全部 9 个 frida 异常属性与 `frida.core.Device` **均存在**，故**导入不会失败**；但**运行期附加行为未验证** |
| 目标进程是否会因附加而受影响 | ❓ **未验证**。真实客户端带 TenProtect；附加可能被检测。本轮**未注入**，无法评估 |
| 附加路径在项目中的既有地位 | 📄 **文档记载已多次使用**（`.agents/modules/runtime.md` 记载 Frida session / `.runtime/frida` 临时目录 / Frida detach 恢复；`.agents/modules/game_server.md:428` 记载 `frida-forced` 的实机闭环）。但 `.runtime/` 在本工作区**不存在**，故这些记录在本区**不可复核** |

---

## 5. 停止失败后调用方的行为

| 阶段 | 改动前 | 改动后 |
| --- | --- | --- |
| 是否请求停止 | ❌ 从不 | ✅ 对每个 client PID 请求一次 |
| 失败是否可见 | ❌ 不可见（从未请求） | ✅ stderr 警告 + 插件日志 + 退出码 4（仅"插件明确拒绝"） |
| 是否继续终止 | ✅ 是 | ✅ **是**（调用方要求的就是停止；优雅停止是尽力而为） |
| 是否会把失败报成成功 | —（无失败可言） | ❌ **不会**：拒绝分支打印 `WARNING` 且退出码 4；不可用分支打印 `WARNING` |
| 终止失败时的优先级 | 退出码 3 | 退出码 **3**（终止失败优先于优雅停止结果） |

**退出码语义（改动后，定义于 `stop()`）**：

| 码 | 含义 |
| --- | --- |
| 0 | 所有目标进程已停止；优雅停止被确认，**或**根本无法请求（环境限制，已警告） |
| 3 | 有进程未能停止（既有语义，未变） |
| **4** | 进程已停止，但**插件明确拒绝了**优雅停止（传输可能仍被占用） |

> **设计说明**：把"无法请求"（无 Frida / 无工具）与"插件拒绝"分开，是为了避免"任何没有 Frida 的机器上 `stop` 都返回非零"。只有插件**实际运行并返回 false** 才升级为 4。

---

## 6. 证据分级

### ✅ 已由代码或测试验证

| 结论 | 依据 |
| --- | --- |
| 改动前 `CodolGame.py` 全文无 Frida / 无停止请求 | 全树检索 0 命中 + `stop()` 源码逐行 |
| `CodolGameServerControl.py --disable` 的完整调用与错误传播链 | 源码逐行（§1 P3）+ 静态属性核对（frida 异常类齐全） |
| `CodolGame.stop()` 改动后在 `terminate_pids` **之前**请求停止 | 测试 `test_stop_requests_the_graceful_stop_before_terminating`（断言调用顺序 `["graceful:222", "terminate"]`） |
| 拒绝 → 退出码 4；不可用 → 警告 + 退出码 0；终止失败 → 退出码 3 | 3 条新测试 |
| `request_graceful_stop` 在工具缺失 / 超时 / 无法启动时**不抛异常** | 2 条新测试 |
| T-1 基线未被本次改动破坏 | `REPRODUCE.ps1` 全绿：哈希 7/7 OK、`checks=124 failures=0`、4 个目标 exit 0 |

### 📄 仅静态推断

| 结论 | 说明 |
| --- | --- |
| DedicatedControl 无停止命令 | 由枚举定义完整枚举得出；未运行时验证 |
| `Server.setEnabled(false)` 无其它调用者 | 全树检索；不含树外调用方 |
| Frida 16.5.9 能成功附加到真实客户端 | **未验证**；仅核对导入级属性存在 |
| `--disable` 在真实客户端上会返回 0 | **未验证**（需启动客户端 + 注入，本轮禁止） |

### ❓ 尚未验证的运行时假设

| 假设 | 为什么未验证 |
| --- | --- |
| 真实客户端上 Frida 附加成功 | 需启动客户端并注入 —— 本轮明确禁止 |
| 附加不会触发 TenProtect 的防护/检测 | 同上 |
| `CODOL_GameServerSetEnabled(false)` 在真实客户端上返回 `true` | 同上 |
| `taskkill /F` 之后 OS 回收 socket 的时序 | OS 行为，未观测 |
| 真实客户端进程退出走 `ExitProcess`（P2） | 未观测 |

---

## 7. 本轮边界核对

| 禁止项 | 状态 |
| --- | --- |
| 启动游戏 / 服务进程 | **未执行** |
| 注入进程（Frida attach / Injector32） | **未执行**。新代码**会**在操作者运行 `stop` 时附加，但本轮**未运行**它；测试全部以 mock 替换该调用 |
| 读取游戏进程内存 | **未执行** |
| 运行 `ol_deploy` | **未执行**（`build\stage` mtime 仍为 2026-10-09 17:01:07） |
| 修改 ABI / 导出签名 / 错误码 10037 / DLL 析构 / `DllMain` | **未修改** |
| 操作 D 工作树 | **未操作**（D 仍为 6 条状态） |
| reset / rebase / clean / commit / push | **未执行** |

---

## 8. 关联交付

- [T2_IMPLEMENTATION_AND_TEST_REPORT.md](T2_IMPLEMENTATION_AND_TEST_REPORT.md) — 最小 diff、测试前后结果、失败分支
- [T2_SHA256_MANIFEST.txt](T2_SHA256_MANIFEST.txt) — 哈希清单
- [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md) · [NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md)
