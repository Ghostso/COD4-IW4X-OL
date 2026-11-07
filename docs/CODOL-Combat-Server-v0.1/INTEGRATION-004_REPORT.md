# CODOL-BATTLE-SERVER-INTEGRATION-004 — 集成验证报告

对象: `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1`
（`CODOL-Combat-Server-v0.1` 当前正式代码）
验证时间: 2026-10-13（Asia/Shanghai）
验证锚定源码指纹 (SOURCE_SHA256): `d042d83c1af9344014388f67ea3531021d4d61a2243c20b93ed5aef286198698`

> 本报告只证明核心服务器的**实际**状态：能构建、能启动、能监听、能清理、
> 以及"测试结果 ↔ 源码指纹"是否一致。它**不是**游玩可行性证明。

---

## 0. 结论速览

| 项目 | 结果 |
|---|---|
| 构建 (csc, release) | PASS |
| 启动 + 本地 UDP 监听 (127.0.0.1:28960) | PASS（真实 UDP 回环往返） |
| 配置解析 | PASS（含 `+set` / 行内注释 / 未知键 WARN） |
| 连接与初始化阶段机 | PASS（离线复放，章节 [6]/[9]） |
| 实体创建与移除 | PASS（章节 [11]） |
| 超时 / 重连 | PASS（章节 [9]/[10]） |
| 停机清理（会话 / 实体 / 网络） | PASS（运行后自检 + 端口可重绑） |
| 自动化测试 | PASS 228/228（0 失败） |
| 测试结果 ↔ 源码指纹一致 | PASS（自测章节 [8] 断言 exe 由当前源码编译） |
| 真实 CODOL 客户端端到端 | **NOT_RUN**（无可用客户端连接；本机未执行） |

**本轮实际改动（已交付）：**
1. 新增 `--run --max-seconds N` 自动退出能力（原先**不存在**，非重复开发）。
2. 运行结束时新增"停机清理自检"：会话数 / 实体数必须归零，否则退出码 6。
3. README 补充该命令说明。

---

## 1. 源码指纹与一致性

本机 csc (.NET Framework 4.0) 不支持 `/deterministic`，**exe 的 SHA-256 每次编译都会变**
（MVID 变化），所以可重复性锚定在**源码指纹**上：
`SOURCE_SHA256 = SHA256( 每个源文件: 相对路径 + 0x00 + 内容, 按路径序 )`。

本轮验证窗口内 `src/` 处于静止（60s 内无写入），指纹三次采样一致：

```
fp_a / fp_b / fp_c / fp_final = d042d83c1af9344014388f67ea3531021d4d61a2243c20b93ed5aef286198698
SOURCE_FILES = 23
```

自测章节 **[8] 构建来源指纹** 断言：
- 源码指纹可重复计算（同树两次一致） -> OK
- 源码指纹 == BUILD_MANIFEST.txt 记录（证明 exe 由当前源码编译） -> OK
- 指纹对内容敏感、对写入顺序免疫、路径参与哈希 -> OK
- 构建产物大小 == BUILD_MANIFEST 记录 -> OK

即：**本报告的各项测试结果，对应源码指纹 `d042d83c…`。**

构建产物快照（同一源码、可能因编译次数不同而 exe 哈希不同）：

```
size: 168448
sha256: B2E1429288729C5D13BAC36B6F4FF090DCC2107F48AB3CB02140F2004E08BA20
source_sha256: d042d83c1af9344014388f67ea3531021d4d61a2243c20b93ed5aef286198698
```

---

## 2. 构建

命令：

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"
powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1
```

结果：`BUILD OK`，退出码 0，23 个源文件，工具链为本机自带
`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`（不联网、无第三方依赖）。

日志：`docs/evidence/INTEGRATION004_build.log`

唯一编译告警（既有、非本轮引入）：

```
src\Codol\ClientCommandReader.cs(213,45): warning CS0675:
  在整数提升的位上使用了按位或运算符；请先考虑强制转换为较小无符号类型
```

处置：`CS0675` 为告警非错误，不影响构建与行为；本轮不改动该文件以免与
并行修改冲突（见 §8）。

---

## 3. 自动化测试

命令：`.\build\bin\CODOLCombatServer.exe --selftest`

结果：**通过 228 项，失败 0 项，全绿，退出码 0**（日志 `docs/evidence/INTEGRATION004_selftest.log`）。

覆盖章节：

| 章节 | 内容 |
|---|---|
| [1] | 密码学 KAT（AES-128 / SHA-1 / HMAC-SHA1） |
| [2] | 大整数与 P-224 ECDH |
| [3] | 协议阶段编解码往返（NAT / cookie / key exchange / 数据帧篡改检测） |
| [4] | 客户端 usercmd / reliable 命令解析 |
| [5] | 快照位级编码（index-skip，独立位流复核） |
| [6] | 端到端离线复放（真实抓包字节 -> 服务端 -> 客户端） |
| [7] | 权威会话描述符（地址下发通道） |
| [8] | 构建来源指纹一致性 |
| [9] | 连接生命周期（槽位复用 / 上限 / 超时 / 清理） |
| [10] | 重连状态（身份门控 / 会话隔离） |
| [11] | 权威实体表（slot -> PlayerState） |

断言数量在本轮验证窗口内为**确定值 228**（连跑两次同为 228/0）。

---

## 4. `--run --max-seconds N`（本轮新增）

**检查结论：原代码没有该能力**（`grep max-seconds` 零命中），因此是新增实现，不是重复开发。

实现位置：
- `src/Program.cs`：解析 `--max-seconds N` 与 `--max-seconds=N`；非法值退出码 5；`--help` 增列。
- `src/Engine/ServerHost.cs`：新增 `public double RunSecondsLimit`，主循环在 N 秒后 `RequestStop()`。
- `src/Program.cs` `RunServer`：运行结束做**停机清理自检**（会话/实体必须为 0），否则退出码 6。

正向验证（`docs/evidence/INTEGRATION004_run_maxseconds.log`）：

```
[NET] 已监听 UDP 127.0.0.1:28960
[*] 自动退出已启用: max-seconds=3
[BOOT] 自动退出已启用 max-seconds=3
[BOOT] 达到 max-seconds=3 -> 请求停止（自动退出）
[BOOT] 主循环退出 frames=112 ticks=112 用时=3016ms
[CONN] SHUTDOWN 会话已清空 connected=0 dropped=0 timeouts=0 full=0
[BOOT] === 服务端停止 ===
[*] 停机清理自检通过: sessions=0 entities=0
```

退出码 0，实际墙钟 ~3.0s（可重复）。

负向 / 边界验证：

| 输入 | 结果 | 退出码 |
|---|---|---|
| `--run --max-seconds 0` | `[FATAL] --max-seconds 非法: '0'` | 5 |
| `--run --max-seconds abc` | `[FATAL] --max-seconds 非法: 'abc'` | 5 |
| `--run --max-seconds`（缺参） | `[FATAL] --max-seconds 非法: '(缺少参数)'` | 5 |
| `--run --max-seconds=1` | 正常，~1s 自动退出 | 0 |
| `--help` | 列出 `--max-seconds <N>` | 0 |

---

## 5. 本地 UDP 监听（真实回环往返）

不仅验证"端口能 bind"，还验证**真实 UDP 收发**：向正在监听的服务器发送一个
合法 NAT 探针（29B，尾 6B = 发送方自己的 IP:port），要求服务器回 29B、首字节 0x0C。

证据 `docs/evidence/INTEGRATION004_udp_roundtrip.log`：

```
REPLY len=29 first=0x0c from=('127.0.0.1', 28960) localport=64274
NAT_ROUNDTRIP_OK
client_rc=0  server_exit=0
```

即：**监听 -> 收包 -> 协议判定 -> 回包** 全链路在真实 socket 上打通（非仅离线复放）。

---

## 6. 重复绑定 / 无 SO_REUSEADDR

`UdpTransport` 刻意不设 `SO_REUSEADDR` 并置 `ExclusiveAddressUse`。验证
`docs/evidence/INTEGRATION004_bind_conflict.log`：

| 场景 | 结果 | 退出码 |
|---|---|---|
| 后启动实例（同默认日志文件） | 先在 Config 阶段因**日志文件被占用**失败 | 2 |
| 后启动实例（独立日志文件，同 UDP 端口） | `绑定 127.0.0.1:28960 失败 … —— 是否还有旧战斗服占着该端口?` | 2 |

结论：重复绑定**直接失败**（不冗余抢包），符合设计意图。

**发现（minor，未改代码）**：因日志文件被单实例独占，第二个默认实例会先在日志阶段
失败，从而"掩盖"了真实的端口冲突。排查双实例问题时需用 `+set log_file <其他文件>`
才能看到端口绑定失败。属诊断可读性问题，非正确性缺陷。

---

## 7. 停机清理与资源残留

| 资源 | 检查方式 | 结果 |
|---|---|---|
| 会话 / 实体 | 运行结束自检 + 自测 [9][11]（DropSession / Despawn / 超时 / 停机） | sessions=0 entities=0 |
| 网络 socket | 停机后**立即重绑**同一端口 | 成功（`docs/evidence/INTEGRATION004_port_release.log`） |
| 后台循环 | `--run` 在主线程执行 `Run()`，无 `StartBackground` 残留线程 | 无残留 |
| 重连缓存 | 停机清空（自测 [10] J4：shutdown 不登记且清空缓存） | PASS |

停机后重绑验证：

```
first_exit=0
[NET] 已监听 UDP 127.0.0.1:28960
[*] 停机清理自检通过: sessions=0 entities=0
rebind_rc=0
```

---

## 8. 重要过程发现：验证期间源码被并发修改（须复核）

严格说，本轮存在一个**环境级问题**：验证期间 `CODOL-Combat-Server-v0.1/src` 被
**另一进程/会话持续写改**。实测证据：

```
00:36:26  我方构建 OK，源码指纹 b62204a6…
00:36:28  src\Engine\ServerConfig.cs 被外部改写            (mtime)
00:36:28→ 指纹漂移为 62068fff…
00:37:29  构建失败: ServerConfig 缺 Spawn/WalkSpeed/Gravity/JumpVelocity，
          但 GameWorld/SelfTest 仍引用 -> CS1061（外部重构中间态）
00:37:59  GameWorld.cs 被外部改写
00:38:56  SelfTest.cs 被外部改写
00:40:48  GameWorld.cs 再次被外部改写 -> 指纹 d042d83c…
00:40:48 起 src 静止 >=60s -> 进入本轮正式验证
```

期间曾观察到**一次瞬态失败** `C1: 在册实体被权威推进 :: x=555.000`（外部编辑中间态），
该失败在静止指纹 `d042d83c…` 上**不可复现**，228 项全绿。故**不计入本版缺陷**，
但记录留痕。

结论与要求：
- 本报告所有 PASS 结果，仅对应**静止窗口**里的源码指纹 `d042d83c…`。
- **若在验证后源码继续变动，必须对新指纹重跑 build + `--selftest` + 运行自检**，
  否则"测试结果 ↔ 源码指纹"不再成立。
- 建议：同一项目工作区避免多会话并行写 `src/`；如需并行，请先冻结或分工作树。

---

## 9. 其它观测（非阻塞，未改代码）

1. **初始化失败阶段标签恒为 `Shutdown`**：`Initialize()` 在返回 false 前先置
   `Phase=Shutdown`，`Program` 打印 `host.Phase`，故 Config/Transport 阶段失败也显示
   `phase=Shutdown`（`FailReason` 文本仍正确）。属诊断可读性 minor。
2. **主循环 tick 非 128Hz**：`Run()` 用 `Thread.Sleep(1)` 节流，Windows 上实测约
   37–40 Hz（3s 内 frames≈104–121）。`tick_hz=128` 为名义值；因积分按 `dt` 进行，
   模拟时间仍近似正确，只是**分辨率**低于名义值。属既有实现，未在本轮改动。
3. **构建脚本 golden 生成路径瑕疵**：`build.ps1` 中
   `Join-Path $root 'testsgen_session_golden.py'` 缺少路径分隔符（应为
   `tests\gen_session_golden.py`），仅在 `CODOL_REGEN_GOLDEN=1` 时触发；默认不触发。
   README 里手写的正确路径为 `tests\gen_session_golden.py`。属既有瑕疵，未在本轮改动。

---

## 10. NOT_RUN（本机无法执行 / 未执行）

| 项目 | 原因 |
|---|---|
| 真实 CODOL 客户端端到端进服 | 未连接真实客户端；本机未执行。不得据此判定"可进游戏"。 |
| 活体玩家输入 / 命中判定 / 弹道 | 未实现（见 README 已知边界）。 |
| 地图 BSP / Clip 真实碰撞 | 未实现（`AssetsDirectory` 未命中，仅登记）。 |

---

## 11. 证据文件清单

| 文件 | 内容 |
|---|---|
| `docs/evidence/INTEGRATION004_build.log` | 构建输出 |
| `docs/evidence/INTEGRATION004_selftest.log` | 自测全量输出（228/0） |
| `docs/evidence/INTEGRATION004_run_maxseconds.log` | `--run --max-seconds 3` 运行 + 清理 |
| `docs/evidence/INTEGRATION004_udp_roundtrip.log` | 真实 UDP NAT 往返 |
| `docs/evidence/INTEGRATION004_bind_conflict.log` | 重复绑定 / 端口冲突 |
| `docs/evidence/INTEGRATION004_port_release.log` | 停机后端口释放重绑 |
| `build/bin/BUILD_MANIFEST.txt` | 构建清单 + 源码指纹 + 逐文件 SHA-256 |

## 12. 相关代码位置（本轮）

| 主题 | 文件:行 |
|---|---|
| `--max-seconds` 解析 | `src/Program.cs`（参数循环、`TryParseMaxSeconds`、`BadMaxSeconds`） |
| 自动退出 + 清理自检 | `src/Program.cs` `RunServer`；`src/Engine/ServerHost.cs` `RunSecondsLimit`、`Run()` |
| UDP 监听 / 无复用 | `src/Net/UdpTransport.cs` `Bind()` |
| 实体创建/移除 | `src/Engine/GameWorld.cs` `Spawn` / `DespawnPlayer` / `Frame` |
| 会话生命周期/超时/重连 | `src/Engine/ClientLogic.cs` `DropSession` / `SweepTimeouts` / `Shutdown` / `TryRestoreOnConnect` |
| 停机清理自检来源 | `src/Engine/GameWorld.cs` `EntityCount`；`src/Engine/ClientLogic.cs` `SessionCount` |

---

## 附：复现命令

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"
powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1            # 构建
.\build\bin\CODOLCombatServer.exe --fingerprint                                # 源码指纹
.\build\bin\CODOLCombatServer.exe --selftest                                   # 228 项自测
.\build\bin\CODOLCombatServer.exe --run --max-seconds 3                         # 运行 3s 自动退出 + 清理自检
```

---

## 8.1 验证后复核（源码仍在变动）

本报告定稿前，`src/` 仍在被并行写改（外部会话）。补充一次"最新树"快速复核，留痕：

| 时刻 (Asia/Shanghai) | 源码指纹 | build | selftest |
|---|---|---|---|
| 00:44:10 变动后 | `f3aa1f211ec57bcf5bd668602d57accb325b09386a5c37b193770a272802c777` | — | — |
| 复核时 | `c51248095bbbdae68c9b085546be9ec7a20e160e88ccb4e54f205b9ce383f025` | BUILD OK | 228/0 PASS |

日志：`docs/evidence/INTEGRATION004_recheck_build.log`、`docs/evidence/INTEGRATION004_recheck_selftest.log`。

**注意**：`--max-seconds`、停机清理自检等同 §4/§7 所述，在该最新树上依然存在且工作。
但由于源码持续变动，任何一次 PASS 只对"当时那一刻的指纹"有效；合并/定稿前请以
`--fingerprint` + `--selftest` 再确认一次。
