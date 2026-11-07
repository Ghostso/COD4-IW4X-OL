# 00 — 轮次报告 / ROUND REPORT — CODOL 最终版战斗服务器：连接生命周期 001

**任务**：`CODOL-COMBAT-LIFECYCLE-001` — 把"连接生命周期"从文档缺口变成**正式服务器代码 + 可复现测试**
**目标版本**：CODOL 3.9.9.7 / 2.6.9.7（本地逆向事实源不变；本轮**未**引入任何未验证的版本字段）
**日期**：2026-10-13（Asia/Shanghai）
**本轮性质**：**正式服务器代码实现 + 构建 + 自动化测试**（非研究文档）
**工程基准**：`CODOL-Combat-Server-v0.1`（可 `csc` 构建的最小战斗服底座，唯一工程主线）
**上游依据**：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001`（M1/M5；P0 缺口 G-06/G-07 之外的 **G-23 = BQ-09 = T-24 断线/退出/关闭清理：无实现**）
**冻结基线**：未触碰任何冻结物（`GOLDEN-LOBBY-001`、`REF_LOBBY_KIT`、`_e1_regression/ol-mod-olfinal`、`tests/golden_*.hex` 原文全未修改）

---

## 1. 实际修改了哪些代码

| 文件 | 变更 | 类型 |
|---|---|---|
| `CODOL-Combat-Server-v0.1/src/Engine/ServerConfig.cs` | 新增配置项 `handshake_timeout_ms`(默认 5000) 与 `sv_timeout_ms`(默认 15000) 及其解析 | 配置 |
| `CODOL-Combat-Server-v0.1/src/Engine/ClientLogic.cs` | 会话槽位分配/复用、`sv_maxclients` 硬上限、重发 DTLS init 保护、握手/静默超时扫描、`cancelConnect` 真实释放、`Shutdown()`、生命周期计数、快照静默门限改用配置值 | **核心功能** |
| `CODOL-Combat-Server-v0.1/src/Engine/GameWorld.cs` | 新增 `OnPlayerRemoved(PlayerState)` 与 `PlayersRemoved` 计数（会话释放时摘除权威实体） | 功能 |
| `CODOL-Combat-Server-v0.1/src/Engine/ServerHost.cs` | 初始化阶段校验两个新超时；CFG 日志打印；`Dispose()` 调 `_logic.Shutdown()` 做优雅清理 | 生命周期 |
| `CODOL-Combat-Server-v0.1/src/SelfTest.cs` | 新增第 9 节"连接生命周期"(14 项断言)；`Harness.FeedFrom()` / `Handshake()` 夹具；`ScratchRoot()` 修复自测临时目录 | **测试** |
| `CODOL-Combat-Server-v0.1/config/combat_server.cfg` | 文档化两个新键（默认值 = 实机可用基线） | 配置 |

> 变更前基线：源码指纹 `61982c96…e16bbdd`（22 源文件）。
> 变更后：源码指纹 `4738710b…b448248f`，未新增/删除任何源文件（仍 22 个）。

---

## 2. 新增或修复了哪些服务器功能

1. **会话槽位分配与复用**：删除了无界自增的 `_nextSlot`，改为 `AllocSlot()` 选最小空闲槽位。此前每次 DTLS init 都会 `_nextSlot++` 并新建 `PlayerState` —— 同 peer 重发即泄漏一个槽位与一个玩家实体。
2. **`sv_maxclients` 成为硬上限**：该配置此前只被校验、从未被强制执行（可无限超卖槽位）。现在满员时拒收新会话并计数 `RejectedFull`，不静默超卖。
3. **重发 DTLS init 保护（真实缺陷修复）**：已建立传输的会话重发 init 会被**忽略**。原因：传输密钥以 `cookie` 为 HMAC 盐（`HMAC-SHA1(key24, [0:6] || [14:])`），替换 cookie 会让之后所有数据帧被自己的 HMAC 拒收 —— 即"连上但静默丢包"这一类最难定位的故障。握手未完成时的重发则原地刷新 cookie/tag 并复用槽位。
4. **握手超时 / 静默超时**：`SweepTimeouts()` 每 tick 判定。`state < Connected` 用 `handshake_timeout_ms`，已连接会话用 `sv_timeout_ms`；超时后释放槽位、摘除玩家实体并计数 `Timeouts`。
5. **`cancelConnect` 真实释放**：此前只置 `s.Cancelled = true`（会话、cookie、槽位、玩家实体全部滞留）。现调用 `DropSession()` 完整回收。
6. **优雅停机**：`ServerHost.Dispose()` → `ClientLogic.Shutdown()`，清空全部会话并输出生命周期汇总（`connected/dropped/timeouts/full`）。
7. **玩家实体下线摘除**：`GameWorld.OnPlayerRemoved()` 把 `Connected=false`、清零移动/按键/速度，权威 `Frame()` 按 `Connected` 过滤。
8. **消除魔法数漂移**：`PumpSnapshot` 里硬编码的 `15000.0ms` 静默门限改为 `_cfg.SessionTimeoutMs`，与 `SweepTimeouts` 共用同一配置源。
9. **自测环境缺陷修复**：见 §4。

---

## 3. 哪些构建和测试已经实际执行

| # | 项目 | 命令 | 结果 |
|---|---|---|---|
| B-1 | 可重复构建 (release) | `powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1` | **BUILD OK**（`sources: 22`，`/platform:x86 /warn:4`；1 条既有告警 `ClientCommandReader.cs(213) CS0675`） |
| T-1 | 离线自测（全 9 节） | `build/bin/CODOLCombatServer.exe --selftest` | **通过 137 项，失败 0 项，exit=0** |
| T-2 | 构建来源指纹 | `--fingerprint` | `SOURCE_SHA256=4738710bb2057ed73dc33cfb06eedf2a1aa760154ae3b39cbdac9adab448248f` == `BUILD_MANIFEST.txt` 的 `source_sha256`（证明 exe 由当前源码编译） |
| R-1 | 运行时冒烟 (`--run`) | 后台启动 `--run +set port 28961`，运行约 4s | **成功**：`已监听 UDP 127.0.0.1:28961` → `初始化完成，进入主循环（128 Hz）`，无 stderr |
| R-2 | 新配置键解析 | 同上（读 `config/combat_server.cfg`） | **成功**：`CFG sv_maxclients=1 handshake_timeout_ms=5000 sv_timeout_ms=15000`，无"未知键"告警 |
| R-3 | 主循环持续推进 | `--run +set port 28962` 运行 ~30s | **成功**：`STAT 收包=0 NAT=0 init=0 keyex=0 data=0 会话=0 tick=1301`（128 Hz × 30s ≈ 3840 期望 tick，实际 1301 因 `Thread.Sleep(1)` 粒度；**如实记录，非断言项**） |

**本轮新增的 14 项断言（第 9 节，全部通过）**：
- A1 两个 peer 各占槽位 0/1 · A2 第 3 个 peer 被拒（不超卖） · A3 握手期重发 init 复用原槽位
- B1 已建立传输后重发 init 不改 cookie/状态（保护 HMAC 盐） · B2 connect 计入 Connected · B3 `cancelConnect` 立即回收会话与玩家实体 · B4 释放后新 peer 复用槽位 0
- C1–C3 握手超时（未到阈值不回收 / 到阈值回收） · C4–C6 已连接会话静默超时（14s 不回收 / 16s 回收） · C7–C8 `Shutdown()` 清空全部会话

**NOT_RUN（本轮未执行，明确标注）**
- `NOT_RUN` — 真实 CODOL 客户端与本服的任何端到端握手/进战斗（需授权实机，且本工作区无 `.runtime/` 实机证据）
- `NOT_RUN` — 交互式 Ctrl+C 停机（本机非控制台会话无法投递控制台控制事件；`Shutdown()` 逻辑本身已由 C8 断言覆盖，`Dispose()`→`Shutdown()` 调用链由代码走查确认）
- `NOT_RUN` — ol-mod（L1）插件线与 booking/DedicatedControl 接线（不在本轮改动范围）
- `NOT_RUN` — 任何 2697 客户端侧分派（T-01/T-02/T-03）与快照帧边界（T-04）

---

## 4. 证据与环境记录

### 4.1 本机 .NET Framework 无法在 `%TEMP%` 建目录（自测脆弱性根因）
- **现象**：变更前的自测有 3 项失败，全部为 `UnauthorizedAccessException: 对路径 "C:\Users\…\AppData\Local\Temp\codol_*" 的访问被拒绝`（见 `V0_2_SELFTEST_BEFORE_FIX.txt`）。
- **最小复现**：用 `csc`（.NET Framework 4.0）编译的最小 `Directory.CreateDirectory(Path.GetTempPath()+guid)` 探针，`/platform:x86` 与默认 anycpu **都抛 `UnauthorizedAccessException`**；而同一台机器上 `pwsh`/`cmd` 在同一 `%TEMP%` 建目录/写文件**成功**。→ 判定为 **.NET Framework 进程在本机对 `%TEMP%` 的环境级权限异常**，与被测代码无关。
- **可复算证据**：探针源码见本目录 `V0_2_TEMP_PROBE.cs`（用 `csc /platform:x86` 与默认 anycpu 编译后在本机均复现失败；`pwsh`/`cmd` 同类操作成功）。
- **处置**：自测新增 `ScratchRoot()` —— 优先仓库内 `build/tmp`（可写、随仓库清理），找不到仓库再退回 `%TEMP%`。只改**测试的临时目录位置**，不改变任何被测语义。
- **结论**：修复后自测 3 项失败消失，全绿；该修复同时让自测可重复、不污染用户 `%TEMP%`。

### 4.2 未触碰的证据与基线
- 未修改 `tests/golden_first_snapshot.hex`、`tests/gen_*.py`、`config/firingrange-gamestate.bin`、`build/bin/session_descriptor/*` 原文语义。
- 未修改 `GOLDEN-LOBBY-001`、`REF_LOBBY_KIT`、`_e1_regression/ol-mod-olfinal`、`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001`。
- 未做任何可能影响冻结基线的实验。

---

## 5. 哪些功能仍然阻塞及其具体原因

| # | 阻塞 | 具体原因 | 证据 |
|---|---|---|---|
| BL-1 | **本服从未被真实客户端连接**（`收包=0`） | 结构性：无同 SHA-256 客户端的运行时镜像（`.data` 声明 218MB 仅 0.14% 在文件内，`.tvm0` 未解码），且 ACE 使内存读取失效 | 覆盖审计 BLK-1/2/3/5/6、BQ-33 |
| BL-2 | 客户端 `0x02` / `0x06` / `0x04` 消费链未定位 | `.tvm0`(RVA 0xD958000) 未解码，`.text` 线性扫描 0 命中 → 无法证明"客户端能读" | T-01/T-02/T-03/T-10 |
| BL-3 | snapshot 帧边界与 delta 基准未定 | 无 2697 战斗通道真实字节样本（需授权实机采集） | T-04/T-05 |
| BL-4 | 大厅→战斗 booking/DedicatedControl 应答接线未完成 | 源码已到位但**接线与实机验证仍未发生** | T-07、G-06 |
| BL-5 | 移动/碰撞/弹道/伤害不可用 | 无 BSP/Clip 真实碰撞；`G_Damage` 缺 9 依赖；2697 字段布局未重验 | G-10/G-11/G-18、T-17/T-18 |
| BL-6 | 交互式 Ctrl+C 停机未在非控制台会话验证 | 本机 PTY 无法投递控制台控制事件给 .NET Framework 进程（环境限制，非代码缺陷） | 本轮 §3 NOT_RUN |

> **纪律**：以上阻塞项**不**用静态推断"补圆"，也不把 3.3.3.3/1.1.1.13 的字段当成 2697 已确认。

---

## 6. 下一项可以直接执行的代码修改（无阻塞、可立刻做）

按"能立刻改、且直接推进 M2/M4"排序：

1. **把会话生命周期接入世界状态**（本工程，~30 行）
   - `ServerHost.Run()` 里 `players` 每帧从 `_logic.Sessions` 重建；改为在 `DropSession` 后由 `GameWorld` 维护**权威实体表**，使玩家标识（slot ↔ entity）在重连后保持稳定；`Frame()` 只遍历在册实体。
   - 直接解锁：M5 的"玩家退出与实体清理"、M2 的"玩家身份关联"。
2. **重连状态回滚**（本工程）
   - 目前同 peer 断开后再握手会得到新 `PlayerState`（位置/背包丢失）。实现 `ClientLogic` 复用最近释放的 slot→backup，按 `CancelConnect`/超时原因决定是否保留。
   - 直接解锁：M5 异常/重连回归；`T-24` 剩余部分。
3. **`--run` 的可编程停机**（本工程，~10 行）
   - 除 Ctrl+C 外支持 `--run --max-seconds N`（自测/CI 用），让"端到端启动→清理"可自动化，消除本轮 R-3 只能人工 kill 的限制。
4. **booking/DedicatedControl 最小接线**（副本工程，`T-07`/`G-06`）
   - 源码已在 `_e1_regression/ol-mod-olfinal/src/backend`；在本服侧实现 `booking` 六步离线回归，消费 `SessionExporter` 导出的端点/密钥（不动 Golden）。
   - 直接解锁：M2 "大厅→战斗"第一条闭环路径。

---

## 7. 哈希

- 改动文件与产物的 SHA-256 见 `CHANGED_FILES.tsv`；本目录交付物清单见 `SHA256SUMS.txt`。
- 构建/自测原始输出见 `V0_2_BUILD_AND_TEST_LOG.txt`；修复前失败样张见 `V0_2_SELFTEST_BEFORE_FIX.txt`；`--run` 冒烟输出见 `V0_2_RUN_SMOKE_28961.txt`。
