# T2_RUNTIME_VALIDATION_PREREQUISITES — 真实运行验证的前置条件、方案与回滚

**日期**：2026-10-10
**状态**：**需单独授权。本轮未执行任何真实运行验证。**
**上游**：[T2_ACCEPTANCE_REVIEW.md](T2_ACCEPTANCE_REVIEW.md) 结论为 **③ 暂不进入**，因此本文件是**方案**，不是已执行的记录。

---

## 0. 一句话

在**门槛未满足之前不要启动客户端**。本文件定义：先修什么（§1）、授权后允许做什么（§2）、怎么做才可回滚（§3）、要采到什么才算证据（§4）、以及何时必须中止（§5）。

---

## 1. 进入条件（**必须先满足**）

| # | 条件 | 现状 |
| --- | --- | --- |
| P-1 | T-1 基线复现通过（`REPRODUCE.ps1` 全绿） | ✅ 已满足（本轮实测 exit 0，`checks=124 failures=0`） |
| P-2 | T-2 调用方测试通过（除既有 `-qa` 项） | ✅ 已满足（25 项，1 项预先存在） |
| P-3 | **G1 修复**：PID 在发起附加前二次校验镜像名 | ❌ **未做** |
| P-4 | **G2 修复**：区分"工具自身错误"与"插件拒绝" | ❌ **未做** |
| P-5 | G3：多 PID 聚合规则有单测 | ❌ 未做 |
| P-6 | 显式授权（启动客户端 + Frida 附加） | ❌ 未取得 |

**P-3 与 P-4 是硬门槛**（见验收审查 §7.3）。P-5 建议同批完成。P-6 需用户单独给出。

---

## 2. 授权后允许 / 禁止

| 允许 | 禁止 |
| --- | --- |
| 启动**一个**客户端进程（建议 `dedicated` 角色，最小面） | 启动双客户端 / 房间对局 |
| 让 `CodolGameServerControl.py --disable` 附加该进程并调用导出 | 手工注入、调试器附加、断点 |
| 只读 `Ayria\Logs\*.log` | 读取进程内存（除 Frida 调用导出本身） |
| 只读 `CODOL_GameServerGetTransportStatus` / `GetStatus` 的返回值 | 抓包（可选，需另批） |
| 在**隔离沙箱目录**运行（`E:\CODOL_SANDBOX\RUN001`） | 修改 `config/codol-game-dir.txt` / 部署到正式安装目录 |
| 记录前后哈希与日志 | 提交 Git / 推送 |

**建议的沙箱**：`E:\CODOL_SANDBOX\RUN001`（既有 overlay 44/44；`main\` 已有 `mp_crash_tropical*.ff`）。**不触碰正式安装目录**。

---

## 3. 实验方案（最小、可回滚）

### 3.1 步骤

| 步 | 动作 | 期望观察 | 若不符则 |
| --- | --- | --- | --- |
| 1 | 记录前置：F HEAD、`git status`、`.runtime/` 是否存在、`tasklist` 中无 `codoMP_client_shipRetail.exe`、`28960/28961/28962` 均空闲 | 全部符合 | **中止** |
| 2 | 启动**单个** `dedicated` 客户端（沙箱目录） | 进程出现；`Ayria\Logs\CodolGameServer.log` 出现 | 中止 |
| 3 | 记录**附加前**的端口占用：`28960`（game transport）、`28961`（dedicated control）、`28962`（client bridge） | 记录实际 bound 情况 | — |
| 4 | 只读调用 `GetTransportStatus`（经控制工具 `status` 动作） | `bound=1`、`port≠0` | 中止 |
| 5 | **执行 `CodolGameServerControl.py --disable --pid <pid>`** | 见 §4 的 S1–S4 | 见 §5 |
| 6 | 再次只读 `GetTransportStatus` | `bound=0`、`port=0` | 记为"拒绝" |
| 7 | 只读插件日志 | **不出现** `udp transport stop failed op=close error=`；**不出现** `game server disable failed` | 记为失败 |
| 8 | （可选，见 3.3）从**另一进程**尝试绑定 `28960` | 绑定成功 ⇒ OS 层确实释放 | — |
| 9 | 只读核对 `28961` / `28962` | **仍被占用**（预期：`SetEnabled(false)` 不触碰它们） | 记录差异 |
| 10 | 按预期停止进程（`CodolGame.py stop`），确认进程消失 | 进程消失 | 手动 `taskkill` |
| 11 | 记录后置哈希 / `git status` / `.runtime/` | 与步 1 一致（除 `.runtime/` 可能新增） | 记录 |

### 3.2 关键设计点

- **单进程**：避免双客户端变量，先把"停止是否真的发生"问清楚。
- **不做任何写操作**：除 `--disable` 本身外，全部为只读采样。
- **先附加后停**：`--disable` 会先 `attach` 再调用导出；因此"附加成功"本身也是本轮的验证对象之一。
- **不依赖 `stop` 的退出码作为唯一判据**：必须同时核对插件日志与 `GetTransportStatus`。

### 3.3 可选的 OS 层释放验证（步 8）

用一个独立的小工具进程在 `127.0.0.1` 上尝试 `bind(28960)`：

- 成功 ⇒ **OS 层确实释放**（这是 S4 的最强证据，且与 T-1 探针同一原理）。
- 失败（`WSAEADDRINUSE`）⇒ 传输仍被占用 ⇒ 即使插件返回 `true`，**OS 层也未释放** ⇒ 必须记录为不一致。

**前置**：仅在步 6/7 报告成功后才执行；工具必须在 `--disable` **完成之后**运行；绑定失败不得重试、不得强制。

---

## 4. 必须采集的证据（对应 B1 的五个状态）

| 状态 | 证据 | 采集方式 | 本轮是否已有 |
| --- | --- | --- | --- |
| **S1 API 调用成功** | 控制工具退出码 `0` + JSON `{"ok": true}` | `--disable` 的 stdout/exit code | ❌ 仅 mock + 失败路径实证 |
| **S2 插件状态切换成功** | `CODOL_GameServerGetStatus` 的 `enabled == 0` | 只读调用 | ❌ |
| **S3 `Network.stop()` 完成** | S1 为真即蕴含；佐证：插件日志**无** `game server disable failed` | 日志 | ❌ |
| **S4 UDP socket 关闭成功** | ① `GetTransportStatus` 的 `bound == 0`；② 日志**无** `udp transport stop failed`；③（可选）外部进程能重绑 28960 | 只读调用 + 日志 + 可选绑定 | ❌ |
| **S5 进程退出** | 进程从 `tasklist` 消失 | `tasklist` | ❌ |

**补充证据（验证 B1 的适用范围分析）**：

| 项 | 期望 |
| --- | --- |
| `28961`（dedicated control）在 `--disable` 之后 | **仍被占用** —— 证明 `SetEnabled(false)` 只管 game transport |
| `28962`（client bridge）在 `--disable` 之后 | **仍被占用** —— 同上 |

> 若这两个端口在 `--disable` 后**也被释放**，则说明 B1 的适用范围分析与实现不符，必须回到源码重新核对。

---

## 5. 中止条件与止损

**立即中止并报告**（不做进一步尝试）：

| 条件 | 理由 |
| --- | --- |
| Frida 附加触发反作弊/客户端拒绝启动或崩溃 | 安全边界 |
| 附加后客户端行为异常（卡死、掉线、报错弹窗） | 同上 |
| 步 5 返回非预期退出码（既非 0 也非 2） | 分类未知，需先查清 |
| 步 6 显示 `bound=1` 但步 5 退出码为 0 | **语义矛盾**，说明"成功"语义有误，必须停止 |
| 步 8 绑定 28960 失败而步 5/6 报告成功 | **OS 层未释放**，同上 |
| `28961`/`28962` 被意外释放 | 与源码分析不符 |
| 出现任何内存读取/调试器/抓包需求 | 超出授权 |

**止损动作**：`CodolGame.py stop` → 若失败则 `taskkill /PID <pid> /T /F` → 确认进程消失 → 记录全部日志 → 报告。

---

## 6. 回滚

| 对象 | 回滚方式 | 验证 |
| --- | --- | --- |
| 客户端进程 | `CodolGame.py stop`（或 `taskkill /F`） | `tasklist` 中无目标镜像 |
| `.runtime/frida` | 删除该目录，或用 `tools/runtime/CleanupRuntimeTemp.py` | 目录不存在 |
| 沙箱 overlay | 不修改；如需清理 `Remove-Item E:\CODOL_SANDBOX\RUN001\Ayria -Recurse` | 仅当明确要求 |
| 仓库 | **不产生任何仓库改动**（本轮验证不修改源码） | `git status` 与验证前一致 |
| 正式安装目录 | **从未触碰** | `config/codol-game-dir.txt` 哈希不变 |

---

## 7. 不得声称的内容

- ❌ 不得把 `--disable` 返回 `true` 描述为"UDP socket 被本次调用关闭"——只保证"调用后 transport 不再 bound"（§B1）。
- ❌ 不得把 `--disable` 描述为"插件已完全停止"——`28961`/`28962` 不受影响。
- ❌ 不得把 mock 测试描述为真实客户端验证。
- ❌ 不得在未采集 S4 证据的情况下宣称"UDP 已释放"。
- ❌ 不得用一次成功运行外推到其它角色、其它构建或双客户端场景。

---

## 8. 关联交付

- [T2_ACCEPTANCE_REVIEW.md](T2_ACCEPTANCE_REVIEW.md) — 验收结论与缺口（G1–G5）
- [T2_ACCEPTANCE_SHA256_MANIFEST.txt](T2_ACCEPTANCE_SHA256_MANIFEST.txt)
- [NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md) · [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md)
