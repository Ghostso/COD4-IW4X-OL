# V0_1_ACCEPTANCE_MATRIX.md

> 交付物 7/8 之二（任务 §四.8）
> 工程: `CODOL-Combat-Server-v0.1/`  ·  git HEAD: 本仓库非 git 仓库（见 §4）
> 配套: [V0_1_IMPLEMENTATION_REPORT.md](V0_1_IMPLEMENTATION_REPORT.md) ·
> [构建与测试证据日志](CODOL-Combat-Server-v0.1/docs/evidence/V0_1_BUILD_AND_TEST_LOG.txt)

---

## 0. 验收结论总表（任务 §三.E 的 7 条）

| # | 验收标准 | 结论 | 方法 | 结果 |
|---|---|---|---|---|
| 1 | 独立服务器目标能够构建 | ✅ **通过** | `build/build.ps1` 可重复构建 | 22 源文件，`BUILD OK`，源码指纹已记录且可断言 |
| 2 | 服务端能初始化真实战斗所需的地图和游戏模式 | ✅ **通过（服务端侧）** | `--selftest` 分节 6 + 启动实测 | 靶场 gamestate 259B 加载，Map/GameType 初始化并校验 |
| 3 | 游戏帧循环持续运行并推进权威状态 | ✅ **通过（服务端侧）** | 启动实测 + `--selftest` (11)(12)(13) | 128 Hz 循环运行；128 tick == 1000ms；move 改变位置、无输入位置不变 |
| 4 | **CODOL 客户端能建立真实战斗会话** | ❌ **未通过** | 需要真实客户端 | 本机从未观测到客户端连入 28960（`收包=0`） |
| 5 | **玩家命令能到达服务端并参与模拟** | ⚠️ **部分通过** | 离线复放真实抓包字节 | 真实 14B usercmd 被解析并驱动权威状态；但**非活体客户端** |
| 6 | **服务端能生成并发送客户端可识别的战斗状态** | ⚠️ **部分通过** | 与实机抓包 / 冻结参考逐字节对齐 | game state 263B、快照 141B、字段序列 29/29、会话描述符逐字节一致；**但"客户端可识别"未经客户端确认** |
| 7 | **最终能进入可玩的战斗** | ❌ **未通过** | 需要真实客户端 | 从未进入战斗 |

**总评：服务端一侧 1/2/3 全部达成；4/7 未达成；5/6 只在"字节级对齐"意义上达成，不得当作实战验证。**

> ★ 任务 §三.E 的硬要求：「不得用日志打印、端口监听或模拟客户端测试替代实战结果」。
> 本矩阵严格遵守：第 4/5/6/7 条凡是依赖活体客户端的，一律标为**未通过或部分通过**，
> 并注明证据强度上限。

---

## 1. 逐项详表

### AC-1 独立服务器目标能够构建

| 项 | 内容 |
|---|---|
| 测试方法 | `powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1` |
| 期望 | 退出码 0，产出 `build/bin/CODOLCombatServer.exe` + `BUILD_MANIFEST.txt` |
| 实测结果 | `sources: 22` / `BUILD OK` / 产物大小恒定 `126464`B / **源码指纹** `61982c961396249f9f5cc9ebef9b11308e990ecd528527ef0d5412910e16bbdd` |
| ★ 可重复的**准确含义** | 本机 csc（.NET Framework 4.0）**不支持 `/deterministic`**，故 exe 的 SHA-256 **每次编译都不同**（连测 3 次 3 个哈希，新 MVID）。因此"可重复构建"以**源码指纹**形式固化并**可断言**：`source_fingerprint = SHA256(每源文件 相对路径+0x00+内容, 按路径序数排序)`，由 `build.ps1` 在编译成功后经 `--fingerprint` 记入 `BUILD_MANIFEST.txt`，自测分节 8 重算并比对。任何源码改动都会让该断言失败 |
| 稳定量对比 | 大小 ✅恒定 126464B · 测试结果 ✅恒定 122/122 · 源码指纹 ✅恒定 · exe SHA-256 ❌每次不同 |
| 证据 | [BUILD_MANIFEST.txt](CODOL-Combat-Server-v0.1/build/bin/BUILD_MANIFEST.txt) §2 · [证据日志](CODOL-Combat-Server-v0.1/docs/evidence/V0_1_BUILD_AND_TEST_LOG.txt) |
| 备注 | ★ 会话开始时构建是**坏的**（`SelfTest.cs` 两处语法错误），仓库里的 exe 无法由源码复现。本轮已修复（见实现报告 §1.1） |

### AC-2 服务端能初始化真实战斗所需的地图和游戏模式

| 项 | 内容 |
|---|---|
| 测试方法 | ① `--selftest` 分节 6 第 (8)(8b) 步；② `--run` 启动实测读取地图/gamestate 日志 |
| 期望 | 地图名与 gametype 进入权威世界；gamestate 来自实机素材且长度 259B/帧 263B |
| 实测结果 | `map=mp_firingrange gametype=coop sv_maxclients=1`；`游戏状态来源: config/firingrange-gamestate.bin (259 字节)`；服务端主动下发 game state 帧长 **263B**（= 4B netchan seq + 259B state） |
| 证据 | 证据日志 §[4] 分节 6 的 `(8) 服务端主动下发 game state`、`(8b) game state 长度 == 基准 263B`；证据日志 §[2] 的 `[1] 分节` 输出 |
| 强度上限 | **服务端侧通过**。gamestate 是实机抓到的靶场素材，但"客户端接受它"从未被活体验证 |
| 未覆盖 | 换其它地图（必须同时提供该图 gamestate 文件，见实现报告 §4 #8） |

### AC-3 游戏帧循环持续运行并推进权威状态

| 项 | 内容 |
|---|---|
| 测试方法 | ① 启动实测（3 秒后仍在运行）；② `--selftest` 第 (11)(12)(13) 步 |
| 期望 | 128 Hz 循环；128 tick == 1000ms；权威位置随 usercmd 改变；无输入时不变 |
| 实测结果 | 启动后 `BOOT 初始化完成，进入主循环（128 Hz）`，3 秒后进程仍 running；`(11) 权威帧循环持续推进（128 tick = 1000ms）` ✅；`(12) yaw=90 度时 move=1 只改变 y` ✅；`(13) 反例: 无移动输入时权威位置不变` ✅ |
| 证据 | 证据日志 §[4] 分节 6；启动实测见 §[2]（`BOOT 初始化完成，进入主循环（128 Hz）`） |
| 强度上限 | 纯服务端行为，可完全离线验证 —— 此条证据强度 = **高** |

### AC-4 CODOL 客户端能建立真实战斗会话 —— ❌ 未通过

| 项 | 内容 |
|---|---|
| 测试方法 | 需要真实 CODOL 客户端发起对局（任务 §二.6 禁止擅自启动/注入客户端进程） |
| 期望 | 服务端日志出现 `RX #1` 16B（DTLS init）→ 握手三阶段 → OOB `connect` |
| 实测结果 | **从未发生。** 全量历史 `battle_srv.log` 里 64 次启动、2499 条 `[stat]` 行中只有 4 条非零，且全部来自 **2026-10-06 21:28 那一次**会话；此后**每次都是 `收包=0`** |
| 已知根因方向 | 客户端把对战流量送到外部腾讯地址 `101.67.36.18:10035`（`gcloudvoice.dll`），**全程 28960 出现 0 次**（`BATTLE_SERVER_PROTOCOL` §8.9）。客户端"消费 endpoint + 建 battle socket"的代码**未定位** |
| 已否证的假设 | 28960 硬编码 ❌ · `mmbook accepted` 含 endpoint ❌ · battle=TCP ❌ · accepted 直接触发 battle ❌ |
| 本轮进展 | 把"战斗地址下发通道"变成服务器侧**可导出、可校验**的产物（`--export-session`），并把"会话端点 == 实际监听端点"变成启动期硬校验 —— 这是从"猜"转向"可定位"的一步 |
| 判定依据 | 任务 §三.E："若 CODOL 专用协议适配尚未完成，必须明确标记缺失环节" → **明确标记为未通过** |

### AC-5 玩家命令能到达服务端并参与模拟 —— ⚠️ 部分通过

| 项 | 内容 |
|---|---|
| 测试方法 | `--selftest` 分节 6 第 (9)(9b)(12) 步：复放**真实抓包里的 14B usercmd**，断言被解析并驱动权威状态 |
| 期望 | 14B usercmd 不得触发 `REJECT_USERCMD`；`ready=true`；move 位驱动权威积分 |
| 实测结果 | `(9) 真实 14B usercmd 被接受（ready=true）` ✅；`(9b) usercmd 处理路径未抛异常` ✅；`(12) yaw=90 度时 move=1 只改变 y（与参考实现同一套运动学）` ✅；分节 4 另有 `真实 14B usercmd 解析通过（不得 REJECT_USERCMD）` ✅ |
| 证据 | 证据日志 §[4] 分节 4 与分节 6；真实字节常量在 `src/Codol/CodolClientReplay.cs` |
| **强度上限（关键）** | 复放的是**真实客户端抓到的字节**，走的是**真实的解析与模拟代码路径** —— 但**发送方不是活体客户端**。因此只能证明"**解析与模拟正确**"，**不能**证明"活体玩家的命令能到达"。按任务要求，此项**不得计为实战通过** |
| 差距 | AC-4 未达成 → 活体命令无条件到达 |

### AC-6 服务端能生成并发送客户端可识别的战斗状态 —— ⚠️ 部分通过

| 项 | 内容 |
|---|---|
| 测试方法 | ① 快照首帧与 Python 参考实现**逐字节**比对；② index-skip 字段序列与实机 trace 比对；③ 会话描述符与冻结参考实现逐字节比对 |
| 期望 | 首帧快照 == 参考实现；字段序列 29/29；描述符 4 组字节 == 参考实现 |
| 实测结果 | `首帧快照与 Python 参考实现逐字节一致` ✅（141B / 1118 bit）· `生成的字段索引序列 == 实录 29/29` ✅ · `index-skip 往返: 实录序列 29/29` ✅ · 描述符：37B/258B/268B/237B **全部逐字节一致** ✅ |
| 证据 | 证据日志 §[4] 分节 5 与分节 7；黄金向量 `src/Codol/SessionGolden.cs`；生成器 `tests/gen_session_golden.py` |
| **强度上限（关键）** | ① 的对照物是**本仓库的 Python 参考实现**（真实抓包已固化其中）；② 的对照物是**实机 trace**（`playerstate-motion-trace.json`）；③ 的对照物是**冻结参考实现**。三者都**不是**"CODOL 客户端接受了我发的字节"的直接证据 —— 后者需要 AC-4 |
| 诚实标注 | 快照的 idx45 / idx219 语义仍是**未知**（已默认不发/不发）；仅**序列与位宽**对齐，**语义**未全部证实 |

### AC-7 最终能进入可玩的战斗 —— ❌ 未通过

| 项 | 内容 |
|---|---|
| 测试方法 | 需要真实客户端进入地图并对战 |
| 期望 | 客户端加载地图、出现玩家、移动/开火同步 |
| 实测结果 | 从未发生。地图碰撞/视线、弹道/伤害/命中判定**完全未实现**（实现报告 §4 #3/#4） |
| 判定 | **未通过** |

---

## 2. 本轮新增的会话描述符验收（任务附录，非 §三.E 原始 7 条但属交付范围）

| ID | 验收点 | 方法 | 结果 | 证据 |
|---|---|---|---|---|
| SD-1 | `bdCommonAddr` 37B 对齐参考实现 | 黄金向量比对 | ✅ | 证据日志 §[4] 分节 7 |
| SD-2 | 258B session 记录对齐参考实现 | 黄金向量比对 | ✅ | 同上 |
| SD-3 | 21/5 靶场对象 268B 对齐 | 黄金向量比对 | ✅ | 同上 |
| SD-4 | 21/5 普通对象 237B 对齐 | 黄金向量比对 | ✅ | 同上 |
| SD-5 | 三条"错了就崩"门槛 | 断言 | ✅ | 分节 7 `门槛1/2/3` |
| SD-6 | 导出与黄金向量的差异**只**落在 securityKey 区段 | 逐字节 diff | ✅ | 分节 7 |
| SD-7 | 6 个导出文件全部落盘且内容一致 | 临时目录落盘 + 回读 | ✅ | 分节 7 |
| SD-8 | `battle_security_key.txt` == 本服实际密钥 | 比对 | ✅ | 分节 7 |
| SD-9 | `endpoint.txt` == 实际监听端点 | 比对 | ✅ | 分节 7 |
| SD-10 | 启动时会话端点 != 实际监听时报 ERROR | 代码路径 +`--run` 实测 | ✅ | `ServerHost.cs` Phase.Config |
| SD-11 | **会话端点/密钥与大厅一致** | 需要大厅侧改造 | ❌ **未达成** | 实测不一致：大厅 `SEC_KEY=16×0x00`，战斗服默认 `16×0x01` |
| SD-12 | 启动时会话端点不一致时明确报 ERROR（不静默） | 代码路径 + 启动实测 | ✅ | `ServerHost` Phase.Config |
| SD-13 | **源码指纹 == 构建时记录**（证明该 exe 由这批源码编译） | `--fingerprint` vs `BUILD_MANIFEST.txt` | ✅ | 分节 8；指纹 `61982c961396249f9f5cc9ebef9b11308e990ecd528527ef0d5412910e16bbdd` |
| SD-14 | 指纹语义：顺序免疫 / 内容敏感 / 路径参与 | 合成目录单元测试 | ✅ | 分节 8 |
| SD-15 | 产物大小 == manifest 记录值 | 比对 | ✅ | 分节 8（126464B） |

> SD-11 是本轮**新发现的结构性风险**：两侧密钥不同 = 即使客户端连上也会静默丢包。
> 修复方向（实现报告 §7 #2）：让大厅直接消费战斗服导出的 `session_descriptor/`。

---

## 3. 回归护栏（防止"改坏了不知道"）

| ID | 护栏 | 说明 |
|---|---|---|
| G-1 | 构建必须成功且黄金向量已重新生成 | `build.ps1` 会编译全部 `src/**/*.cs`；`SessionGolden.cs` 长度不符时生成器**拒绝写出** |
| G-2 | `bdCommonAddr` / 258B / 268B / 237B 四组字节 | 任何描述符回归立刻 FAIL |
| G-3 | 真实 14B usercmd 必须被接受 | 分节 4 + 分节 6 双重断言，防止 netchan 解析器被改坏 |
| G-4 | 首帧快照 == Python 参考实现 | 分节 5 逐字节比对 |
| G-5 | index-skip 字段序列 == 实录 29/29 | 分节 5 + 反向解码复核 |
| G-6 | 服务端必须**主动**下发 game state（不等 `gamestateupdate`） | 分节 6 第 (8) 步 —— 这是历史 bug 的回归护栏 |
| G-7 | 快照必须**自动**开始 | 分节 6 第 (10) 步 —— 同上 |
| G-8 | 反例断言必须失败 | 篡改密文被 HMAC 拒绝 / 错 serverTag 被丢弃 / 截断位流抛异常 / 无输入位置不变 |
| G-9 | 配置行内注释必须正确解析 | 分节 7 —— `session_playlist = # 留空 = 1` 与 `logs/a#b.log` 两种情形都断言 |

**本轮实测：G-1..G-9 全部通过（122/122，退出码 0）。**

```
G-1  构建成功 + 黄金向量长度校验     OK   sources: 22, BUILD OK
G-2  4 组描述符字节 == 参考实现        OK   37B / 258B / 268B / 237B
G-3  真实 14B usercmd 被接受           OK   分节 4 + 分节 6 双重
G-4  首帧快照 == Python 参考实现       OK   141B / 1118 bit
G-5  index-skip 序列 == 实录 29/29     OK   含反向解码复核
G-6  服务端主动下发 game state         OK   263B
G-7  快照自动开始                     OK   >= 3 帧
G-8  反例断言必须失败                  OK   分节 3 / 4 / 5
G-9  配置解析（含行内注释）             OK   4 项
```

---

## 4. 环境与版本记录（任务 §三.A 要求）

| 项 | 值 |
|---|---|
| 工程目录 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\` |
| 编译器 | `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`（.NET Framework 4.0） |
| 目标平台 | Windows，`/platform:x86`，PE32 可执行 |
| 第三方依赖 | **零**（自实现 SHA-1 / HMAC-SHA1 / AES-128 / P-224 大数） |
| 是否联网 | 构建**不联网**、不写仓库外 |
| CoD4x_Server | `https://github.com/callofduty4x/CoD4x_Server` @ `ddd65fc`，**AGPL-3.0**，`git status` 干净 |
| iw4x-client | `https://github.com/IW4x/iw4x-client` @ `d1b175d`（另 `0699a7e5`），**GPL-3.0**，`git status` 干净 |
| 本仓库 | **不是 git 仓库**（`git rev-parse` 失败）→ 无法记录 HEAD；**未提交、未推送**（无仓库可提交） |
| 冻结基线 | `GOLDEN-LOBBY-001` **未修改**；本版全部改动都在 `CODOL-Combat-Server-v0.1/` 内 |
| 客户端进程 | **本轮未启动、未注入、未附加、未读其内存**（任务 §二.6） |

---

## 5. 未能验证的部分（诚实清单）

| 项 | 为什么无法验证 | 需要什么 |
|---|---|---|
| AC-4 客户端建立战斗会话 | 需启动真实客户端；根因未定位 | 运行授权 + 定位 battle 触发链（纯静态可做） |
| AC-5 活体命令到达 | 依赖 AC-4 | 同上 |
| AC-6 客户端**接受**战斗状态 | 依赖 AC-4 | 同上 |
| AC-7 进入可玩战斗 | 依赖 AC-4；且碰撞/弹道未实现 | 运行授权 + 引擎战斗实体表 |
| PvE booking 应答格式 | 无真实样本；ol-mod 源码不在本机 | 官方 pcap 或 ol-mod 源码 |
| 会话描述符被 CODOL 接受 | 只对齐了参考实现字节，未经客户端 | 依赖 AC-4 |

---

## 6. 复现命令（一键验收）

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"

# 1) 重新生成黄金向量（需要本机 python + REF_LOBBY_KIT）
python -X utf8 tests\gen_session_golden.py

# 2) 可重复构建
powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1

# 3) 全部自动化测试（退出码 0 = 全绿）
.\build\bin\CODOLCombatServer.exe --selftest

# 4) 权威会话描述符
.\build\bin\CODOLCombatServer.exe --print-protocol
.\build\bin\CODOLCombatServer.exe --print-session
.\build\bin\CODOLCombatServer.exe --export-session

# 5)（需运行授权）启动战斗服主循环
.\build\bin\CODOLCombatServer.exe --run
```
