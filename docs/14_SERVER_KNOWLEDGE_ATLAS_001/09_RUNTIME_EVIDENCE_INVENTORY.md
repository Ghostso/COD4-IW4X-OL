# 09 — 运行证据清单 / RUNTIME EVIDENCE INVENTORY

> 本任务**只读**；本档案**未产生任何新运行证据**。下表汇总既有运行/动态/抓包记录。

## 1. 运行 / 动态证据总表

| ID | 对象 | 证据 | 时间 | 等级 |
|---|---|---|---|---|
| RT-01 | OLD 服务端 | `qconsole.log`：`running=1 bots=12 humans=0` | — | VERIFIED |
| RT-02 | OLD 服务端 | 作者自述 “incomplete port, not a playable CoDOL server” | — | VERIFIED |
| RT-03 | C-1113 客户端 | 与 OLD 服务端真实握手 **从未在隔离环境跑通** | — | NOT-OBSERVED |
| RT-04 | C-2697 客户端 | 与 2697 服务端互通 | — | NOT-OBSERVED |
| RT-05 | 2697 服务端 | 任何运行时观测 | — | NOT-OBSERVED |
| RT-06 | C-3333 客户端 | 2026-10-05 16:36 首次进入正式 Online Lobby | 2026-10-05 | VERIFIED（实机） |
| RT-07 | C-3333 客户端 | Battle 通道 | 2026-10-06 监听 28960，`BATTLE_RX=0` | VERIFIED（动态） |
| RT-08 | C-3333 客户端 | usercmd 14 B 真实观测 | 2026-10-06 | VERIFIED |
| RT-09 | 恢复镜像/客户端 | 运行时解包 dump | — | **不存在** |
| RT-10 | 客户端 | 断点 / 注入 / 内存读 | — | **本任务禁止**；历史亦无 |
| RT-11 | TCLS→Client 交接 | 静态 100% 复现；动态受 TenProtect 限制 | 2026-09 | VERIFIED（静态）/ BLOCKED（动态） |
| RT-12 | 客户端共享内存标记 | 未在游戏内存发现 `CODOLBLOCK1-MARKER`（t+6s） | — | VERIFIED（未发现） |
| RT-13 | 客户端句柄枚举 | 未出现 `TCLS_TASMEMORY_<pid>` / `TCLS_SHELLMEMORY_<pid>` | — | VERIFIED（未出现） |
| RT-14 | 反作弊 | ~10s 后内存读取失效（ACE） | — | VERIFIED |
| RT-15 | ol-mod | 自述 two-real-client Nuketown FFA / Factory 通过 | 2026-09/10 | [文档声明] —— `.runtime/natural-match` 目录本地不存在 |
| RT-16 | C# 战斗服 | `--selftest` 通过 111 / 失败 3（临时目录权限） | 2026-10-10 | VERIFIED |
| RT-17 | Codec MVP | `--codec-selftest` | 2026-10-10 | VERIFIED |
| RT-18 | 合成加密对等体 | 握手 INIT/COOKIE 往返 | — | VERIFIED（合成） / 真实 C1 UNKNOWN |

## 2. 运行证据的“独立来源”审计（任务书 §5.2 要求）

任务书规定：**两个模块共享同一个错误的字段定义，即使全部测试通过，也不构成独立验证。**

| 验证对 | 是否独立 | 说明 |
|---|---|---|
| C# Codec ↔ 2697 服务端 E1/E2/E3 | **不独立** | C# 的字段定义来自 E1–E3 的同一份反汇编结论；共享同一错误假设风险高 |
| 合成对等体 ↔ OLD 服务端 | **部分独立** | 合成对等体由 C# 实现；但与源码假设共享 README/注释 |
| C-1113 客户端字符串表 ↔ `codol_network.c` 注释 | **部分独立** | 字符串表为独立读取；但 RVA 来自服务端源码注释 |
| 2697 服务端写入 ↔ C-2697 客户端 `0xA2E50` | **弱** | 字段形状匹配，但无分派、无字节样本、无运行时 |
| GOLDEN-LOBBY-001 实机 ↔ REF_LOBBY_KIT | **独立** | 实机进大厅是第一手运行证据 |

**结论：** 目前**没有任何**一条跨端协议结论同时具备 (a) 两端独立静态证据 与 (b) 真实字节/运行时证据。

## 3. 抓包 / 采集证据

| 证据 | 位置 | 内容 | 等级 |
|---|---|---|---|
| REF_LOBBY_KIT_CAP009 | `REF_LOBBY_KIT_CAP009\` | 21/5 响应、6/14 mmbook 帧（44 条 R2 帧） | VERIFIED |
| booking 动态 | `DEV-BOOKING\runtime_net_001`、`runtime_net_ch003` | 运行时网络记录 | VERIFIED |
| TCLS 交接导出 | `CODOLServer\_write_handoff.py` | TAS/SHELL 二进制 | VERIFIED |
| 2697 注册导出 | `evidence\client-registration2697.txt` | 注册校验输入 | VERIFIED |
| 2697 未采集 | — | 2697 战斗通道抓包 | **不存在** |

## 4. 明确缺失的运行时证据（决定本档案上限）

| 缺失项 | 影响 | 可获取性 |
|---|---|---|
| 同 SHA-256 客户端的**运行时解包内存 dump** | 无法证明恢复镜像 ≡ 运行时映射 | 需受控动态实验（需授权） |
| 客户端 `0xA2E50` **调用栈/回调注册** | 无法闭合 opcode 分派 | 需运行时 |
| **2697 战斗通道抓包** | 无法做字节级双向闭合 | 需真实互通（未发生） |
| **2697 完整黄金向量** | 无法做独立解码交叉测试 | 需抓包或等价运行时 |
| `.rimp` 指针修复格式还原 | 无法恢复 `.rdata` vtable/xref | **静态可尝试** |
| IW4x 两份克隆差异清单 | 无法判断引用的是哪一个 HEAD | 可静态完成 |

## 5. 运行证据清单结论

1. 现有运行证据集中在**大厅层**（REF_LOBBY_KIT / GOLDEN-LOBBY-001）与**OLD 服务端自跑**（bots=12/humans=0）。
2. **游戏战斗通道的端到端运行证据在本项目中不存在**（2697 与 C-2697 均 NOT-OBSERVED）。
3. 客户端恢复镜像的**运行时等价性**是结构性缺口，直接限制了所有客户端侧静态结论的上限。
4. 任务书 §12 优先序（源码/字节 > 离线编解码 > 黄金向量 > 既有日志 > 新动态实验）在本档案中已按此排序（见 `19`）。