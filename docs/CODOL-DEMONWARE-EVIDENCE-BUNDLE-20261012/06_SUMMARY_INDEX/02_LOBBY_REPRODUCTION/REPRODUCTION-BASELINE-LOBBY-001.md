# CODOL复活：从黑箱到 Lobby 的完整复现基线

## 0. 文档元数据

```text
DOCUMENT_ID        = DEV-REPRO\REPRODUCTION-BASELINE-LOBBY-001
DOCUMENT_VERSION   = 1.0
CREATED            = 2026-10-08 22:58
LAST_VALIDATED     = 2026-10-08 22:58（文件级 / 端口级校验；本文件生成会话**未**做新的实机端到端跑）
STAGE              = LOBBY_REPRODUCTION
STAGE_STATUS       = LOBBY_REPRODUCTION_CONFIRMED
NOT_FULL_PVE       = TRUE
FULL_PVE           = NOT_REPRODUCED
```

### 0.1 本文件的权威来源（按优先级）

本文件**不是**新逆向，而是把已有成果固化成可交接手册。优先级：

1. **`REF_LOBBY_KIT\GOLDEN-LOBBY-001.md`（2026-10-07，STATUS=FROZEN）** —— 唯一权威复现依据；
   `GOLDEN-LOBBY-001\REF_LOBBY_KIT\_golden_hashes.json` 为机器可读哈希基线。
2. `HANDOFF_20261007_TAKEOVER.md`（2026-10-07，总入口交接手册）。
3. `HANDOFF_20261005_LOBBY_REACHED.md`（2026-10-05 16:36，**首次进入大厅的实机记录**）。
4. `HANDOFF_20261005_REFKIT_WORKS.md` / `HANDOFF_20261005_BREAKTHROUGH.md` / `HANDOFF_20261005_PUSH_TO_LOBBY.md`。
5. `DEV-BOOKING\PUBLISHER_FILE_RECOVERY-001.md` / `-002.md`（2026-10-08，Publisher 数据恢复）。
6. 更早的启动链/IIPS 报告：`CODOLServer\HANDOFF_20260927_IIPS_GATE_RESOLVED.md`、
   `CODOLServer\SESSION_APPEND_20260929_STAGE3_SUCCESS.md`、`CODOLServer\CONFIRMED_RESULTS_20260928.md`。
7. `DEV-REVIEW\MASTER-POST-LOBBY-FULL-HISTORY-001.md`（大厅之后的全量工程考古总账）。

### 0.2 证据等级约定

| 等级 | 含义 |
|---|---|
| CONFIRMED | 有实机日志/截图/字节级证据，或冻结基线明确写死 |
| HIGH-CONFIDENCE | 有指令级静态证据，缺逐条动态回放 |
| PARTIAL | 部分成立（本文件会写清哪一半成立） |
| UNRESOLVED | 未解决，**不得当作复现依赖** |
| NOT_FOUND | 在现有材料与磁盘上未找到 |
| SOURCE_CONFLICT | 两份材料冲突，双方都保留（见附录 A） |

### 0.3 客户端版本

```text
CLIENT_EXE        = codoMP_client_shipRetail.exe
CLIENT_FILE_VER   = 1649370
CLIENT_PROD_VER   = 1649370
CLIENT_SIZE       = 7,841,344 B
CLIENT_SHA256     = 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
CLIENT_MAIN_DLL   = codoMP_client_shipRetailBase.dll  (60,327,992 B)
```

---

## 1. 项目阶段定义

### 1.1 本阶段目标（唯一目标）

```text
从"完全黑箱、无法启动 / 无法进入游戏"
   → 到"按固定流程稳定启动客户端并进入 CODOL Lobby（大厅）"
```

**最终交付是"大厅复现"，不是 PvE 对局。**

### 1.2 明确的非目标（本阶段不做）

- 不做新的逆向研究来填充本文档。
- 不解决 Booking / Battle / DTLS / PvE 进图（见 §19）。
- 不绕、不停、不配置、不规避 ACE / TenProtect（硬纪律，见 §7.4）。

### 1.3 什么才算"进入大厅"

判据取自 `HANDOFF_20261005_LOBBY_REACHED.md`（实机截图 + 日志）与 `GOLDEN-LOBBY-001.md` §2/§3：

```text
① lobby_srv.log 出现  === 大厅连接建立 ===   且  [keys] ★ 试解命中
② 首帧             hmac=OK marker=0x86
③ 出现             <- keepalive
④ 收到             8/1 8/2（档案）、10/21（发行方配置）
⑤ 全程             hmac=BAD 计数 = 0
⑥ 客户端窗口       类名 CODO 可见、标题 "使命召唤online"
```

### 1.4 阶段命名说明

历史材料里同时存在两套说法，本文件**不创造新名字**，直接沿用材料中的真实术语：

- 早期（2026-09）用「第一档 / 第二档 / 第三档」描述握手分档，见 `CODOLServer\SESSION_APPEND_20260929_STAGE3_SUCCESS.md`。
- 2026-09-26 起用 `Stage 1 / Stage 2 / Stage 3` 描述会话阶段，见 `CODOLServer\SESSION_RECORD_20260926_LOBBY_*.md`。
- 大厅侧运行期状态用：`uA50`、`sub_state`、`obj_code`、`DWLOBBY_PUMP_SUCCESS`、`lobReq5e8`、`lobReq5ec`。
- 大厅连接状态用：`DW_LOBBY_CONNECTED`、`=== 大厅连接建立 ===`、`hmac=OK`。

本文件 §4 的阶段编号是**为可交接而做的整理编号**，每个编号都标注了它对应的真实材料。

---

## 2. 最初黑箱状态

来源：`REVERSE_ENGINEERING_SUMMARY.md`（2026-09-30）、`CODOLServer\HANDOFF_20260927_IIPS_GATE_RESOLVED.md`、
`CODOLServer\SESSION_RECORD_20260926_C5C0_SWITCH.md`、`DEV-BOOKING\PUBLISHER_FAILURE_SPEC-001.md`（后者是后期补充）。

### 2.1 原始客户端 / 目录

```text
原始客户端目录   COD OL\                      （出厂原件，含 974 个 IIPS .ifs 内容包）
原始 EXE         COD OL\codoMP_client_shipRetail.exe   （Build 1649370）
原始组件         ACE/TP 全套原版：ace-ats32.dll、ACE-DRV32.dll、VSDDrvDll.dll、
                 PolicyProbe.dll、TCJ.dll、tvsd.dll、TerSafe.dll、TenSLX.dll、
                 TenSp.dll、BugTrace.dll、TenProxy.dll、TenRpcs.dll
启动器           TCLS\（腾讯登录器 Client.exe）、WeGameLauncher\、TGuard\、tqm\
```

### 2.2 缺失 / 不完整组件（黑箱的核心）

| 项 | 黑箱状态 | 证据 |
|---|---|---|
| `dwauth.ini`（exe 侧） | **本机完全没有这个文件**；穷尽磁盘+归档搜索 0 命中 | `SESSION_RECORD_20260925_DWAUTH.md`；`HANDOFF_20260927_DYNAMIC_CAPTURE.md` |
| `buildconfig.ini` | 同样缺失 | `SESSION_RECORD_20260925_DWAUTH.md` |
| `iips.ini` | 母沙箱为 `enable_iips=0` | `HANDOFF_20260927_IIPS_GATE_RESOLVED.md` §1 |
| 本地 CA | 不在 `cacert.pem` 内 | `SESSION_RECORD_20260926_LOBBY_STAGE2.md` |
| 本地大厅/认证服务 | 不存在 | 同上 |
| Publisher `.info` 数据（后期才发现） | Golden 冻结副本里数据目录缺失 | `DEV-BOOKING\PUBLISHER_FILE_RECOVERY-001/002.md` |

### 2.3 原始启动方式与原始结果

原始启动方式：直接双击 exe，或走官方腾讯登录器 `TCLS\Client.exe`。

实际观察到的失败（逐条来自历史报告，原文引用）：

```text
无参数启动   →  Win32 对话框 class=#32770，标题「致命错误」
                文本「请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。」
                判据键 WIN_NO_TCLS

-q / -qa 启动 →  绕过 TCLS 闸门，随后
                标题「致命错误」 / 文本「初始化IIPS错误：8189fec。」
                伴随窗口类 iipsinit

过了 IIPS 之后 →  游戏内**渲染**出文本  [100]无法连接大厅服务!
                判据键 @SF_UI_DW_LIVE_CONNECTING_FAILED（不是弹窗，是 ingame 文本）

后期           →  「致命错误 / 与大厅服务失去连接」
                判据键 @SF_UI_DW_LIVE_DISCONNECTED
```

### 2.4 当时无法证明的事（黑箱边界）

- 无法证明客户端能否载入网络层（`enable_iips=0` 时无任何网络层；多数运行静默跑到超时，个别 t=11.4 s 崩溃 `0xc0000005`）。
- 无法证明 TAS/TCLS 共享内存是否被消费（运行期未观测到游戏打开 `TCLS_TASMEMORY_<pid>`）。
- 无法证明任何大厅协议内容（当时连 `/auth/` 请求都收不到）。
- 动态内存读取受 ACE 限制：约 10 s 后内存读取失效。

---

## 3. 最终已达成状态

### 3.1 本阶段成功判据（真实术语）

```text
CLIENT_PROCESS_ALIVE      = CONFIRMED   （codoMP_client_shipRetail 运行中, Responding=True）
IIPS_INIT                 = CONFIRMED   （IIPSHostApp.exe + iips.dll 载入）
IFS2_INIT                 = CONFIRMED   （ifs2.dll 载入, observer 事件 t=9.160）
ONLINE_MODE               = CONFIRMED   （CoD Splash: "使命召唤online Multiplayer"）
AUTH_TLS                  = CONFIRMED   （127.0.0.1:3074, TLSv1/AES256-SHA, POST /auth/ 200）
LOBBY_TCP                 = CONFIRMED   （127.0.0.2:3074, === 大厅连接建立 ===）
LOBBY_HANDSHAKE           = CONFIRMED   （0x81/0x82/0x83 闭合; uA50=5 / sub_state=9 / obj_code=700）
LOBBY_TASK_EXCHANGE       = CONFIRMED   （0x85 任务应答 hmac=OK; golden 基线 235 OK / 0 BAD）
LOBBY_KEEPALIVE           = CONFIRMED   （<- keepalive 出现 15 次）
PUBLISHER_FILES           = CONFIRMED   （10 个 .info 全部下发, 无 "缺"）
LOBBY_UI_LOADED           = CONFIRMED   （窗口类 CODO, 标题 "使命召唤online", 截图 lobby_window.png）
LOBBY_ENTRY               = CONFIRMED
STAGE_STATUS              = LOBBY_REPRODUCTION_CONFIRMED
```

### 3.2 实机证据锚点

```text
首次进入大厅时间   2026-10-05 16:36
证据文档           HANDOFF_20261005_LOBBY_REACHED.md
截图               REF_LOBBY_KIT\lobby_window.png   (1920x1080, mtime 2026-10-05 16:36:51)
                   REF_LOBBY_KIT\lobby_live.png     (mtime 2026-10-05 16:36:34)
判据               窗口类 CODO 可见、标题 "使命召唤online"、
                   任务数 34 → 47、hmac 全 OK、无致命弹窗
冻结基线           2026-10-07, GOLDEN-LOBBY-001.md, STATUS=FROZEN
冻结基线日志指标   lobby_srv.log(134,649 B): 建立 23 / 结束 23 / 异常 0 /
                   keepalive 15 / hmac=OK 235 / hmac=BAD 0
```

### 3.3 诚实声明

- 本文件生成会话**没有**重新做一次完整实机跑（需要人工批准 UAC + 拉起游戏）。
  上述 CONFIRMED 状态来自：冻结基线 + 历史实机证据（`lobby_srv.log` 计数、窗口记录、截图）
  + 本次对磁盘上文件/端口/开关的直接校验。
- ACE 状态诚实记录（来自 `GOLDEN-LOBBY-001.md` §4）：`ACE_REMOVAL = NOT_COMPLETE`。
  客户端 ACE 强依赖靠 `nt10.py` 的 4 个内存补丁绕过（见 §5.5），属"绕过/共存"，不是"移除"。

---

## 4. 从黑箱到 Lobby 的历史演进

> 编号是为可交接整理的；每段标注真实材料来源与日期。

### 4.0 Stage 0 —— 原始黑箱（≤ 2026-09-25）

见 §2。一句话：客户端不会启动、没有网络层、没有 `/auth/`、没有任何大厅协议证据。

### 4.1 Stage 1 —— 认证层打通：`dwauth.ini` + TLS + `/auth/`（2026-09-26）

- 发现 exe 侧 `dwauth.ini` 缺失是"无法连接大厅"的直接原因。
- 关键产物：本地自签 CA 追加进 `cacert.pem` → 客户端首次真的发出 `POST /auth/`。
- 结果：`auth_task 10 → 11`、`code=700`、`DW_DNS_COMPLETE`；卡在 `[obj+0x240]==2`。
- 来源：`CODOLServer\SESSION_RECORD_20260926_LOBBY_HANDSHAKE.md`、`..._LOBBY_STAGE2.md`。

### 4.2 Stage 2 —— 平台/会话上下文：`cfg_applied=1`（2026-09-26）

- CA 正确后首次真实 `POST /auth/`；`TCLS_SHAREDMEMEMORY<pid>` 使 `cfg_applied=1`。
- 出现 `auth_task=32`（DSA 签名路径）与 `obj_code 735`。
- 来源：`SESSION_RECORD_20260926_LOBBY_STAGE2.md`、`SESSION_RECORD_20260926_C5C0_SWITCH.md`。

### 4.3 Stage 3 —— 启动链闸门：`enable_iips=1`（2026-09-27）

单变量对照（沙箱 `sandbox_ifs1_ctl_iips1_20260927` 与母沙箱只差 `iips.ini` 一个字节）：

```text
enable_iips=1  →  IIPSHostApp.exe 启动 → iips.dll 载入 → ifs2.dll 载入
               →  在线模式（CoD Splash: "使命召唤online Multiplayer"）→ 真实 POST /auth/
enable_iips=0  →  不启动 IIPSHostApp → 不载入 iips.dll / ifs2.dll → 无任何网络层
```

强证据：`/auth/` 请求里的 `identity` 三次完全相同（`356c4bc3`），直接来自 `iips.dll`；
这解释了"必须过 IIPS 才会有 `/auth/`"。来源：`CODOLServer\HANDOFF_20260927_IIPS_GATE_RESOLVED.md`。

> ⚠️ 该文档 §3 记的 `dwauth.ini` 是**旧格式**（`127.0.0.1/443`），**已作废**。
> 正式基线用的是 §5.2 的 3074 域名格式。

### 4.4 Stage 4 —— 握手闭合：0x81 / 0x82 / 0x83（2026-09-28 ~ 09-29）

- 第一档①②③闭合：0x81 handler 真执行、收下 0x82、发 0x83 并推进到状态 3。
- 关键更正：不能在 0x81 之前改 `[req+0x5E8]`；0x83 回显值来自运行期 `[req+0x5FC]`，不能从帧尾推断。
- 来源：`CODOLServer\SESSION_APPEND_20260929_STAGE3_SUCCESS.md`、`CONFIRMED_RESULTS_20260928.md`、
  `LOBBY_BREAKTHROUGH_REPRO_20260928.md`（该轮 `uA50=5`、`DWLOBBY_PUMP_SUCCESS`，4/4 复现）。

### 4.5 Stage 5 —— 自研协议栈的最后一段（2026-09-30 ~ 10-05，失败并最终放弃）

自研 `CODOLServer\` 栈在这段时间只解出 4 条任务（`71/4 → 71/3 → 71/7 → 71/9`）就断流，
并与参考实现出现**结构性差异**（`71/4 declared=84 vs 212`、`field1` 全零 vs `nQloP0oCVWR6RDJS`）。
关键修正与卡点：

- 0x85 AES 密钥口径修正为 `[provider+0x9C]` 前 16 字节（`HANDOFF_20261005_KEY_AND_TASK.md`）。
- 根因之一 `auth_template749.on`：启用后客户端**再也不发 `/queue/`**；禁用后 queue 立刻回来，
  链路推进到 `st 4→5 / DWLOBBY_PUMP_SUCCESS`（`HANDOFF_20261005_BREAKTHROUGH.md`）。
- 剩余卡点：弹窗仍在、`Address Fail | result = -3`、客户端不建立大厅连接对象。
- 结论（本项目记录在案）：`CODOLServer\` 只用于**理解与实验**；
  真正能进大厅的是第三方完整实现 `REF_LOBBY_KIT\`（`HANDOFF_20261005_REFKIT_WORKS.md` §6）。

### 4.6 Stage 6 —— 换用 `REF_LOBBY_KIT`：链路全通（2026-10-05 15:55）

- 从外部来源（F 盘 `...\scripts\`）复制整套脚本到 `REF_LOBBY_KIT\`，
  只改 `GAME_ROOT` 指向本机沙箱。
- 结果：大厅连接建立、解出 **34 条**跨 service 任务、hmac 全 OK、连接稳定 ~3 分钟。
- 对照：自研栈只有 4 条。
- 来源：`HANDOFF_20261005_REFKIT_WORKS.md`。

### 4.7 Stage 7 —— 进入大厅（2026-10-05 16:36）

两个真实修复（`HANDOFF_20261005_LOBBY_REACHED.md`）：

1. **握手竞态**：0x83 用了过期 challenge。修复为"用本会话 24B 会话密钥配对，
   最多等 5 秒本会话 KDF 记录"（改了 `lobby_server.py` 的 0x82 分支）。
2. **缺发行方文件**：客户端连续 3 次请求 `mp_playlists_shipRetail_1.0.0.info`，
   套件里只有 `mp_playlists_shipRetail_release.info`。修复为同义名回退 + 实体别名文件。

结果：任务数 **34 → 47**、连接持续 keepalive、无 reset、无致命弹窗，
窗口类 `CODO` 可见、标题 "使命召唤online"、大厅界面渲染完成。

### 4.8 Stage 8 —— 冻结与数据完整性修复（2026-10-07 ~ 10-08）

- **2026-10-07**：`GOLDEN-LOBBY-001.md` 冻结（STATUS=FROZEN），核心文件 SHA-256 入册
  （`_golden_hashes.json`）；4 个内存补丁 + 1 个 KDF hook 定稿；开关终态固定。
- **2026-10-08**：发现 **Golden 冻结副本缺少数据目录**，直接跑会复现
  `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`；在 `DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\`
  补齐 `publisher_files\ / player_profiles\ / user_files\ / mkt_assets\ / sku_arrays\`，
  `PUBLISHER_FAILURE_RESOLVED = CONFIRMED`，客户端正常进大厅并真正发出 `6/14 mmbook`。
  来源：`DEV-BOOKING\PUBLISHER_FILE_RECOVERY-001/002.md`。

---

## 5. 当前可复现环境

### 5.1 目录结构（全部为 Windows 绝对路径）

```text
PROJECT ROOT   D:\BaiduNetdiskDownload\使命召唤OL
GAME ORIGINAL  D:\BaiduNetdiskDownload\使命召唤OL\COD OL\                （出厂原件，读）
GAME ROOT      D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\
SERVER (正式)  D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\          （可跑；含全部数据目录 + mem_* 转储）
SERVER (恢复)  D:\BaiduNetdiskDownload\使命召唤OL\DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\
SERVER (冻结)  D:\BaiduNetdiskDownload\使命召唤OL\GOLDEN-LOBBY-001\REF_LOBBY_KIT\  （只读基线，⚠ 缺数据目录，见 §5.7）
AGENT          D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\  （elevated_agent.py / agent_client.py）
PUBLISHER 数据 D:\...\REF_LOBBY_KIT\publisher_files\
CONFIG         <GAME ROOT>\dwauth.ini、<GAME ROOT>\iips.ini、<GAME ROOT>\cacert.pem、C:\Windows\System32\drivers\etc\hosts
LOG            D:\...\REF_LOBBY_KIT\{lobby_srv.log, auth3074.log, battle_srv.log, n10*.txt, kdf_sessions.txt}
AGENT STATE    D:\...\CODOLServer\logs\elevated_agent.json
BACKUP         各目录内 *.bak_* 文件（改名回滚）
TOOLS          D:\...\REF_LOBBY_KIT\（脚本）；D:\...\REF_LOBBY_KIT\_ref\（第三方 C# 参考实现）
```

### 5.2 客户端

```text
CLIENT_EXE      = <GAME ROOT>\codoMP_client_shipRetail.exe
CLIENT_WORKDIR  = <GAME ROOT>          （= 启动时的 cwd，见 §9）
CLIENT_ARGUMENTS= nt10.py 启动时【无额外命令行参数】：
                  subprocess.Popen([<GAME ROOT>\codoMP_client_shipRetail.exe], cwd=<GAME ROOT>)   (nt10.py:2101)
                  其他历史入口用过 -q 或 -q --disable-gpu --disable-gpu-compositing（AboProbe.cs / launch.ps1）
CLIENT_ENV      = NOT_FOUND（无任何文档记录必需环境变量）
CLIENT_CONFIG   = dwauth.ini、iips.ini、buildconfig.ini、stun.ini、cacert.pem
MUTEX           = Global\{5BD75B76-601A-4b20-80C8-D2317C94BB30}（nt10.py 自行创建；残留实例会阻塞启动）
```

`<GAME ROOT>\dwauth.ini`（当前实测，79 B，即"三方已验证格式"）：

```text
formal-zone-lsg.codol.qq.com 3074
formal-zone-auth.codol.qq.com 3074
0x03EA
```

`<GAME ROOT>\iips.ini`（当前实测，46 B）：

```text
enable_iips=1
iips_url="http://10.231.2.181/"
```

### 5.3 Publisher（服务=10 / 任务=21 的发行方配置下载）

> ⚠️ **"Publisher" 不是独立 EXE/DLL**。磁盘上不存在任何 `*publisher*` 可执行文件
> （glob `**/*publisher*` 为空）。
> 它是客户端 `codoMP_client_shipRetail.exe` 内部的一个下载子系统
> （错误串 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` @ `0x00DC9C6C`），
> 由**本地大厅服务**用协议 `service=10 task=21` 供给。

```text
PUBLISHER_ENDPOINT = 127.0.0.2:3074（与大厅同一条 lsg 明文 TCP；Publisher 自己没有监听端口）
PUBLISHER_DIR      = <lobby_server.py 所在目录>\publisher_files\<名字>.info
PUBLISHER_HANDLER  = lobby_server.py  reply_objects()  第 529-543 行
必需数据文件（10 个 wire 文件 + manifest.json）：
  activities_v1.info   broadcast.info   configs_s.info   daily_challenge_config.info
  market-down.info     market_ui.info   MOTD.info        tlogconfig.info
  whitelist_tester.info
  mp_playlists_shipRetail_1.0.0.info      （= 关键；同义名回退 mp_playlists_shipRetail_release.info）
依赖数据目录： player_profiles\ (public.result, secure.result)、user_files\ (the.json)、
               mkt_assets\、sku_arrays\
```

历史失败文案（Golden 冻结副本直接跑时）：
`GOLDEN-LOBBY-001\REF_LOBBY_KIT\lobby_srv.log` 第 50-102 行有
`[20:02:22]        -> 缺 mp_playlists_shipRetail_1.0.0.info`（及其余 9 条）。

### 5.4 Lobby

```text
服务文件   D:\...\REF_LOBBY_KIT\lobby_server.py        (76,410 B, SHA256 d7eeb4564af05f4c…)
地址端口   TCP 127.0.0.2:3074 （明文 lsg，hosts 别名 formal-zone-lsg.codol.qq.com）
认证文件   D:\...\REF_LOBBY_KIT\fake_auth_tls.py       (10,347 B, 地址 TCP 127.0.0.1:3074, TLS)
启动默认   run_all.py: start_py_service("auth","fake_auth_tls.py",3074, addr="127.0.0.1")
                      start_lobby_server(lobby_bind="127.0.0.2", lobby_port=3074, raw_ports="")
```

### 5.5 Tools

```text
run_all.py      D:\...\REF_LOBBY_KIT\run_all.py         (31,507 B, 一键编排: hosts/dwauth/证书 + auth + lobby + battle + nt10)
nt10.py         D:\...\REF_LOBBY_KIT\nt10.py            (169,491 B, 注入 / 内存补丁 / KDF hook / 拉起客户端 / 观测)
codol_crypto.py D:\...\REF_LOBBY_KIT\codol_crypto.py    (42,853 B, 帧/加密/对象编码/session 构造)
marketplace_store.py / battle_server.py / battle_selftest.py / make_local_ca.ps1 / write_dwauth.py
elevated_agent.py   D:\...\CODOLServer\_mainline\elevated_agent.py   (提权代理, 监听 127.0.0.1:<临时端口>)
agent_client.py     D:\...\CODOLServer\_mainline\agent_client.py     (客户端: ping / run)
```

`nt10.py` 实装的 4 个内存补丁 + 1 个 hook（`GOLDEN-LOBBY-001.md` §1.4）：

```text
补丁1 AuthGate      @0x00B9A78E  74 -> 75        (JE  -> JNE)
补丁2 ClientTicket  @0x00B9A7C5  75 -> EB        (JNE -> JMP)
补丁3 ParseFallback @0x00B9A7C7  E8 -> E9        (call -> jmp 0x00B9A7F1)
补丁4 LsgNonceCheck @0x00BA3C1C  85 C0 75 44 -> 85 C0 90 90  (NOP)
KDF hook            @0x00BA0D20  trampoline（派生会话密钥 -> secrets_kdf.txt / kdf_sessions.txt）
```

> 说明：`nt10.py` 会写客户端的运行时内存（补丁）并挂 hook，这些是**运行期行为**，
> 不是对磁盘文件的改写。Golden 里的 `nt10.py` 哈希（`05863ebafc7d7bb3…`）即为准。

### 5.6 Logs

```text
大厅   D:\...\REF_LOBBY_KIT\lobby_srv.log      （冻结基线 134,649 B；建立23/keepalive15/hmac=OK 235/BAD 0）
认证   D:\...\REF_LOBBY_KIT\auth3074.log       （TLS 就绪 + -> 200 task=10->11）
战斗   D:\...\REF_LOBBY_KIT\battle_srv.log     （大厅阶段: 已监听 28960, 收包=0）
注入   D:\...\REF_LOBBY_KIT\n10*.txt           （每次 run_all --out 指定的文件名）
会话钥 D:\...\REF_LOBBY_KIT\kdf_sessions.txt、secrets_kdf.txt、auth_sessions.txt
代理   D:\...\CODOLServer\logs\elevated_agent.json   （{pid, port, token, debug_privilege}）
截图   D:\...\REF_LOBBY_KIT\{lobby_window.png, lobby_live.png}
```

### 5.7 ★ 副本角色与"不可修改"边界（这是最容易踩的坑）

| 副本 | 角色 | 证据 | 可修改? |
|---|---|---|---|
| `REF_LOBBY_KIT\` | **正式可跑副本**；`GOLDEN-LOBBY-001.md` §2 的复现命令指向它；含全部数据目录 + mem_* 转储 | `GOLDEN-LOBBY-001.md` §2、§3 | 开发副本，实验在此进行 |
| `DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\` | **数据恢复副本**（2026-10-08 从 `REF_LOBBY_KIT\` 复制并排除 mem_*/日志备份），Publisher/Booking 实跑用它 | `PUBLISHER_FILE_RECOVERY-002.md` §1 | 实验副本 |
| `GOLDEN-LOBBY-001\REF_LOBBY_KIT\` | **冻结只读基线** | `GOLDEN-LOBBY-001.md`「Golden 只读；所有实验在开发副本进行」 | **只读** |

> 🚨 **重大坑（本次校验新发现，且有历史实机佐证）**：
> `GOLDEN-LOBBY-001\REF_LOBBY_KIT\` 当前**只有 `__pycache__` 一个目录**，
> `publisher_files\`、`player_profiles\`、`user_files\`、`mkt_assets\`、`sku_arrays\` **全部缺失**。
> 直接跑它会复现 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` ——
> 这正是 `PUBLISHER_FILE_RECOVERY-001/002.md` 记录的现象，
> 也对应 `GOLDEN-LOBBY-001\REF_LOBBY_KIT\lobby_srv.log` 里的 `-> 缺 mp_playlists_shipRetail_1.0.0.info`。
> **复现大厅请用 `REF_LOBBY_KIT\`（或已恢复的 `DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\`），
> 或在运行前把数据目录补齐到 Golden 副本。**
>
> 补充：Golden 副本的 `lobby_srv.log`（31,377 B）**不是** `GOLDEN-LOBBY-001.md` §3 引用的那份基线日志；
> 基线日志（134,649 B）在顶层 `REF_LOBBY_KIT\`。两份的三份核心代码 SHA-256 完全一致，只有日志不同
> （本次已比对）。

`run_codol_001\` 下的沙箱：

| 沙箱 | 角色（证据） |
|---|---|
| `sandbox_ifs1_20260923` | 历史"母沙箱"；`capture_elevated_network.ps1` 的默认沙箱；`iips.ini` 已为 `=1` |
| `sandbox_datafix_20260929` | **当前 GAME_ROOT**：母沙箱副本 + 6 个 zone 解包进 `main\`（2026-09-29 建） |
| `sandbox_ifs1_ctl_iips1_20260927` | 单变量对照克隆（与母沙箱只差 `iips.ini` 一个字节） |
| `sandbox` | `run.ps1` 建，用 junction 指向 `COD OL`；`COD OL` 原件对我们只读 |
| `sandbox_new` | `create_hardlinks.ps1` 的硬链接镜像 |
| `sandbox_ace_stub_20260929` | 目录存在，**用途 NOT_FOUND**（任何文档都没有记录） |

> ⚠️ 除 `REF_LOBBY_KIT` 系列外，**没有任何文档声明某个 `run_codol_001` 沙箱不可修改**（UNRESOLVED）。
> 唯一明确的"原件只读"对象是 `COD OL\`。

---

## 6. 网络拓扑

```text
                    CODOL 客户端进程 (codoMP_client_shipRetail.exe)
                      |                                   |
     TLS POST /auth/  |                                   |  明文 lsg 大厅长连接
                      v                                   v
        127.0.0.1:3074                                127.0.0.2:3074
        fake_auth_tls.py                              lobby_server.py
        (hosts: formal-zone-auth.codol.qq.com)        (hosts: formal-zone-lsg.codol.qq.com)
                                                      |
                                                      +--> publisher_files\*.info  (service=10/task=21)

        [ POST-LOBBY, 大厅阶段不需要 ]
        battle_server.py   UDP 0.0.0.0:28960  <-- 客户端仅在"进对局"时才会连
```

真实 hosts 块（`run_all.py` 用 `# CODOL-LOCAL-BEGIN/END` 包围管理）：

```text
# CODOL-LOCAL-BEGIN
127.0.0.1 formal-zone-auth.codol.qq.com
127.0.0.2 formal-zone-lsg.codol.qq.com
# CODOL-LOCAL-END
```

**明确交还给真实网络的域名**（`run_all.py` 文档头 a 条）：**不劫持** `down.qq.com` / `intldlgs.qq.com`
—— 让 ACE/TP3 走真实网络。设计上 `443 / 80 / 8081` 应当**空闲**。

### 6.1 端口速查（含"是不是大厅必需"）

| 端口 | 协议 | 归属 | 大厅必需? |
|---|---|---|---|
| 3074 | TCP | `127.0.0.1` fake_auth_tls.py（TLS /auth/） | **YES** |
| 3074 | TCP | `127.0.0.2` lobby_server.py（明文 lsg） | **YES** |
| 28960 | UDP | battle_server.py（进对局用） | **NO — POST-LOBBY** |
| 80 / 443 / 8081 | TCP | 应空闲，交还真实网络 | NO |

> ★ **28960 = Battle UDP，属于 POST-LOBBY。**
> 证据链：`GOLDEN-LOBBY-001.md`「服务布局 … battle UDP 0.0.0.0:28960」；
> `GOLDEN-LOBBY-001.md` §3「battle_srv.log … 已监听 28960，**收包=0（未进对局）**」
> —— 即**大厅已经进入、战斗服一个包都没收到**；
> `DEV-BOOKING\MVP-PVE-MATCH-ENTRY-009.md` §8/§11：`GAME_PORT = 28960` 来自 `findSessions(21/5)`
> 会话对象 ① Hostaddress，`BATTLE_ENDPOINT = CONFIRMED（127.0.0.1:28960, UDP）`。
> **大厅复现文档中，28960 / Battle 不是必需条件。**
>
> 说明（诚实标注）：现有材料中**没有**一句"原话"写着"28960 不是进入大厅所必需"（NOT_FOUND）。
> 上面结论是由"大厅进入成功时收包=0"+"28960 只由 21/5 会话对象产出"两条硬证据推出，
> 并非直接引用。最接近的表述：`STAGE_REPORT_BATTLE.md:95`「booking 走的是独立于 3074/28960 的
> '客户端桥'端口」；`BATTLE_SERVER_PROTOCOL.md:606`「PvE 剧情任务的对局流量走的**不是** 28960」。

---

## 7. 权限与 UAC

### 7.1 普通权限启动 vs 管理员启动

```text
非提权进程可见性（CODOLServer\_mainline\_pop3_agent.log:150,153）：
  ADMIN=False ; SeDebugPrivilege=False err=1300 ; OpenProcess failed err=5, retry
提权进程：
  elevated_dbg_privilege=True err=0 ; OpenProcess ok ;
  main_module='…\codoMP_client_shipRetail.exe'
```

固化链脚本**硬拒绝**非管理员（源码级）：

```text
run_codol_001\capture_elevated_network.ps1:80-81
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
      throw 'capture_elevated_network.ps1 must run elevated.'
run_codol_001\run_direct_iips1_elevated.ps1:64-66
  if (-not $isAdmin) { throw 'This runner must be started elevated.' }
```

实际非管理员运行的产物（`run_codol_001\runs\DIRECT_TGP_NONADMIN_20260924_015242\processes_final.json`）：
进程表里只有 `tgp_daemon.exe` 和 `tcls_core.exe`，
**没有游戏进程、没有 `IIPSHostApp.exe`**。

> ⚠️ 诚实边界：**没有**"同一环境下非提权 vs 提权载入 IIPS 的对照实验"（NOT_FOUND）。
> 所有载入 IIPS/IFS 的成功运行都名为 `IFS1_ELEVATED_*`。
> 因此下面"为什么需要管理员"是按**各条独立证据**写的，不是一次单变量对照的结论。

### 7.2 为什么需要管理员（逐条，均有证据）

1. **IIPS 需要创建 Global 命名对象**：`CODOLServer\IIPS_PIPELINE_FULL_REVERSE.md:99-100`
   记录 `SetPrivilege failed` / `IIPSERR_PRIVILEGE_SE_CREATE_GLOBAL_NAME`
   —— 需要 `SeCreateGlobalPrivilege`（涉及 `Global\IIPSShareState_MMF_<key>` 与
   `Global\IIPSShareState_Mutex_<key>`）。
2. **读游戏内存 / 下断点 / dump**：需要进程内显式启用 `SeDebugPrivilege`
   （`CODOLServer\WORKING_HARNESS_NOTES.md:16`：SeDebugPrivilege 必须在提权进程内显式启用，
   High 完整性不算够）。`elevated_agent.py` 启动时正是做这件事。
3. **手工启动 IIPSHostApp 的历史做法都是提权**：
   `IIPS_ROOT_CAUSE.md:37`「手工提权启动 `IIPSHostApp.exe /mode iipslaunch`」；
   `IIPS_POLICY_PROTOCOL.md:32` 同。
4. **杀客户端**：ACE 保护下普通权限 `taskkill` / `Stop-Process` 报 Access denied。
5. **改 hosts**：写 `C:\Windows\System32\drivers\etc\hosts` 需管理员。
6. **写 `cacert.pem` / 安装本地根 CA**：`HANDOFF_20261005_REFKIT_WORKS.md` 明确
   「必须管理员 —— 要写 hosts + 装根证书」。
7. **`netsh interface portproxy`**（仅历史方案需要，见 §16）需管理员；
   普通权限下 `netsh interface portproxy show all` **返回空**。

### 7.3 提权代理：`elevated_agent.py` / `agent_client.py`

```text
文件      D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py   (142 行)
          D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\agent_client.py     (49 行)
状态文件  D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\logs\elevated_agent.json
          { "pid": <代理PID>, "port": <监听端口, 随机>, "token": <随机48位hex>,
            "debug_privilege": true/false, "debug_err": <err> }
监听      127.0.0.1:<随机端口>（端口 0 = 系统分配，只监听本机回环）
协议      一行一个 JSON  {token, action:"ping"} / {token, action:"run", argv, cwd, timeout}
代理 stdout（启动时打印）: elevated_agent pid=<pid> port=<port> debug=<bool>/<err>
```

启动（会弹 UAC，**必须人工点"是"**）：

```powershell
$py = (Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8',
  'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' `
  -Verb RunAs -WindowStyle Hidden
```

历史等价的 `.cmd` 入口（`run_codol_001\run_elevated_agent_admin.cmd` 第 5 行，原文）：

```text
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'python.exe' -Verb RunAs -ArgumentList @('-X','utf8','-u','%HERE%..\CODOLServer\_mainline\elevated_agent.py')"
```

验证（PING）：

```powershell
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping
# 期望: "ok": true, "debug_privilege": true, 并给出 "pid"
```

查看 PID / 端口（读 json，不需要提权）：

```powershell
Get-Content "CODOLServer\logs\elevated_agent.json" -Raw
```

调用方（仓库内，已排除 archive/backups/_lineage）：
`auto_lobby_loop.py:78`、`_auto_attempt.py:20`、`_e57a5c_experiment.py:220,397`、
`_sweep_probe.py:23`（都调 `agent_client.py run`）；`_mk_tldr.py:207` 调 `run_elevated_agent_admin.cmd`。

### 7.4 ★ Golden 纪律：ACE / TenProtect 不绕过

原文（多处一致）：

```text
CODOLServer\HANDOFF_20261002_TLDR.md:19-20
  **始终禁止**：关闭/停止/配置/规避 ACE、TenProtect
  （历史实测会导致蓝屏 0x01010002）。

CODOLServer\HANDOFF_20260929_LOBBY_PROTOCOL.md:721-723
  允许    ReadProcessMemory / WriteProcessMemory / EnumWindows / EnumProcesses
  禁止    绕过或篡改 ACE / 修改 .text 代码段 / Frida 注入

CODOLServer\CONFIRMED_RESULTS_20260928.md:2239-2241
  不再绕过 ACE、不改安全组件 / 不再改客户端 .text 代码 / 不再对游戏/平台进程做 Frida 注入

CODOLServer\HANDOFF_20261005_SESSION_1347.md:410
  **不关、不规避 ACE / TenProtect**；
```

> 说明（冲突保留）：`HANDOFF_20261002_TLDR.md` §二 另记录"用户已明确解锁（2026-10-01）：
> patch `.text` / 下断点 / 调试器"。两处并存，本文件不擅自取舍（见附录 A8）；
> 但 **ACE/TenProtect 本身不绕** 这一点全材料一致，无冲突。
> Golden 里的客户端依赖 DLL 全是**原版** ACE/TP 文件，不是 stub。

### 7.5 UAC 是人工步骤

- 起 `elevated_agent.py` 会弹 UAC → **必须人工批准**。本文件不提供任何免 UAC 方案。
- `HANDOFF_20260927_IIPS_GATE_RESOLVED.md` 也把 443 需要管理员写为已知事实（提权代理由此而来）。
- `UNATTENDED_SESSION_20260925.md:23`：「提权常驻 helper（只需点一次 UAC）」。

---

## 8. 服务启动顺序与"必需性矩阵"

### 8.1 必需性矩阵

| Component | Required for Lobby | Start Order | Port | Verification |
|---|---|---|---|---|
| 环境准备：hosts / dwauth.ini / iips.ini / cacert.pem | **YES** | 0 | — | hosts 含 `# CODOL-LOCAL-BEGIN` 块；dwauth 三行；`enable_iips=1`；cacert 含本地 CA |
| `elevated_agent.py`（提权代理） | **YES** | 0 | TCP 127.0.0.1:<随机> | `agent_client.py ping` → `ok=true, debug_privilege=true` |
| `fake_auth_tls.py` | **YES** | 1 | TCP 127.0.0.1:3074 | auth3074.log：`TLS 就绪` + `-> 200 task=10->11` |
| `lobby_server.py` | **YES** | 2 | TCP 127.0.0.2:3074 | lobby_srv.log：`=== 大厅连接建立 ===` + `★ 试解命中` |
| `publisher_files\*.info` 数据 | **YES**（数据，非进程） | — | 经 3074 | lobby_srv.log：`-> publisher <name>.info` 且**无** `缺` |
| `nt10.py`（注入 + 4 补丁 + KDF hook + 拉起客户端） | **YES** | 3 | — | `n10*.txt`：`game pid=...`；后续出现 KDF/密钥 |
| `codoMP_client_shipRetail.exe` | **YES** | 4（由 nt10 拉起） | 出站→3074 | 窗口类 `CODO`、标题 `使命召唤online` |
| `run_all.py` | **RECOMMENDED**（编排器；也可手工起服务） | — | — | 三个日志同时出现 |
| `battle_server.py` | **NO（POST-LOBBY）** | 5（可选） | UDP 0.0.0.0:28960 | battle_srv.log 已监听；大厅阶段**收包=0** |
| `marketplace_store.py` / `marketplace-*.json` | **NO**（仅商城/仓库功能） | — | — | — |
| `battle_selftest.py` | **NO**（离线自测工具） | — | — | — |

> 分类速记：**LOBBY REQUIRED** = 上表前 7 行；**BATTLE REQUIRED** = `battle_server.py`（POST-LOBBY）；
> **BOOKING REQUIRED** = 目前**无任何已实现服务**（缺控制面，见 §19.2）；**OPTIONAL** = 商城相关。
>
> `run_all.py` 启动 battle 的逻辑（`run_all.py` L718-725）：
> 默认会起，但如果 `firingrange-battle.enabled` 开关存在，则**交给 lobby_server 起**，避免两份抢 28960。
> 想显式跳过战斗服：加 `--no-battle`。

### 8.2 精确启动顺序（一句话版）

```text
0. 提权代理 → 1. auth TLS(127.0.0.1:3074) → 2. lobby(127.0.0.2:3074) → 3. nt10 注入并拉起客户端 → 4.(可选) battle(UDP 28960)
```

---

## 9. 客户端启动顺序

客户端**不是**手工双击，而是由 `nt10.py` 拉起（`run_all.py` → `nt10.py`）。

`nt10.py` 的实际启动逻辑（源码位置已核）：

```text
nt10.py:2093-2101
  1) 若非 --keep-others：taskkill /F /IM codoMP_client_shipRetail.exe 与 TP3Helper.exe
  2) 创建互斥体 Global\{5BD75B76-601A-4b20-80C8-D2317C94BB30}
  3) subprocess.Popen([<GAME ROOT>\codoMP_client_shipRetail.exe], cwd=<GAME ROOT>)   ← 无额外参数
  4) 观察 4 秒；若已退出(坏启动, 常见 0xC0000005)则重试, 最多 6 次
```

`run_all.py` 调 nt10 的参数（`run_all.py:486-488`）：

```text
python <ROOT>\nt10.py --root <GAME ROOT> --secs <secs> --delay 0 --out <out> --apis <apis>
```

**启动前必须做的**：
1. 提权代理在线（`agent_client.py ping` → `debug_privilege=true`）。
2. 无残留 `codoMP_client_shipRetail` / `TP3Helper` / `IIPSHostApp` 进程（残留会占单实例互斥 → 坏启动）。
3. hosts / dwauth.ini / iips.ini / cacert.pem 已就位（`run_all.py` 会自动做）。
4. Publisher 数据目录存在（否则弹 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`）。

**启动后要观察的**：IIPS/IFS2 载入 → `/auth/` TLS → lobby 3074 连接 → 0x81/0x82/0x83 → 0x85 任务 → keepalive → 大厅 UI。

> 历史其他入口（**当前基线不使用**，仅备查）：`run_codol_001\launch.ps1` 用
> `-q --disable-gpu --disable-gpu-compositing`；`AboProbe.cs` 用 `"<exe>" -q`；
> 自研实验驱动 `CODOLServer\_mainline\_e57a5c_experiment.py`（见 §4.5，已不用于复现）。

---

## 10. 完整 SOP（可执行）

> 所有命令均来自历史报告或本次磁盘/源码核对，**未臆造**。
> 唯一权威"一步到位"路径是 `GOLDEN-LOBBY-001.md` §2；下面把它展开成带检查点的 SOP。

### STEP 01 —— 确认工作目录

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
Get-Location
```
期望：输出 `D:\BaiduNetdiskDownload\使命召唤OL`。

### STEP 02 —— 检查客户端/沙箱完整

```powershell
$SB = 'run_codol_001\sandbox_datafix_20260929'
Test-Path "$SB\codoMP_client_shipRetail.exe"
Test-Path "$SB\codoMP_client_shipRetailBase.dll"
Test-Path "$SB\dwauth.ini"; Test-Path "$SB\iips.ini"
```
期望：四个 `True`。

### STEP 03 —— 检查 Publisher 数据目录（★ 最容易漏）

```powershell
$KIT = 'REF_LOBBY_KIT'
foreach ($d in 'publisher_files','player_profiles','user_files','mkt_assets','sku_arrays') {
  $p = Join-Path $KIT $d
  "{0,-16} {1}" -f $d, (Test-Path -LiteralPath $p)
}
```
期望：五个 `True`。若你在 `GOLDEN-LOBBY-001\REF_LOBBY_KIT` 上跑，这里会是 `False`（见 §5.7）。

### STEP 04 —— 检查端口

```powershell
netstat -ano | Select-String ':3074|:28960|:443\s|:80\s|:8081'
```
期望：3074（两个地址）与 28960 在启动前**空闲**；`443 / 80 / 8081` 空闲（设计上交还真实网络）。
若发现历史残留 `127.0.0.1:443` 监听与 `127.0.0.1 443 -> 8443` 的 portproxy（旧方案遗留），见 §15 / §16。

### STEP 05 —— 清残留进程（走提权代理）

```powershell
python -X utf8 "CODOLServer\_mainline\agent_client.py" run powershell -NoProfile `
  -Command "Get-Process codoMP_client_shipRetail,TP3Helper -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue"
```
期望：无残留；`run_all.py` 自己也会在开头自检僵尸进程并提示。

### STEP 06 —— 启动提权代理（会弹 UAC，人工点"是"）

```powershell
$py = (Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8',
  'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' `
  -Verb RunAs -WindowStyle Hidden
```

### STEP 07 —— 确认代理就绪（PING）

```powershell
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping
Get-Content "CODOLServer\logs\elevated_agent.json" -Raw
```
期望：`"ok": true`、`"debug_privilege": true`，并拿到 `pid`。

### STEP 08 —— 一键跑 `run_all.py`（起 auth + lobby + 注入 + 拉起客户端）

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL"
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 600 --out n10_golden.txt
```

> 注意：`--secs 600 --out <name>.txt`，**不要加 `--tas`**（TAS 会把客户端推到 DSA 签名路径而卡住）。
> 想跳过战斗服加 `--no-battle`；只想恢复 hosts 用 `--restore-hosts`。

### STEP 09 —— 确认 auth 在监听

```powershell
netstat -ano | Select-String ':3074'
Get-Content "REF_LOBBY_KIT\auth3074.log" -Tail 20
```
期望：`127.0.0.1:3074 ... LISTENING`；日志有 `TLS 就绪`。

### STEP 10 —— 确认 lobby 在监听

```powershell
netstat -ano | Select-String '127.0.0.2:3074'
Get-Content "REF_LOBBY_KIT\lobby_srv.log" -Tail 30
```
期望：`127.0.0.2:3074 ... LISTENING`；日志首行 `==== lobby_server 启动 lobby=127.0.0.2:3074 raw=[] ====`。

### STEP 11 —— 观察 IIPS / IFS2 初始化

```powershell
Get-Process IIPSHostApp -EA SilentlyContinue | Select-Object Id,ProcessName
Get-Process codoMP_client_shipRetail -EA SilentlyContinue | Select-Object Id,Responding
Get-Content "$SB\IIPS\HostPid" -EA SilentlyContinue
```
期望：`IIPSHostApp.exe` 出现；客户端进程存活；出现 `IIPS\HostPid`。
observer 侧的对应事件（`FULL_DYNAMIC_CAPTURE_REPORT_20260927.md:56`）：
`t=8.094 iips.dll 载入` → `t=9.160 ifs2.dll 载入` → `t=15.245 Splash`。

### STEP 12 —— 观察 Lobby TCP 建立与握手

看 `REF_LOBBY_KIT\lobby_srv.log`：

```text
==== lobby_server 启动 lobby=127.0.0.2:3074 raw=[] ====
=== 大厅连接建立 ('127.0.0.1', <ephemeral>) ===
  [keys] ★ 试解命中: 密钥组 src=kdf-session aes_out=... challenge=...
  ★ 解密成功 #1 seq=1 hmac=OK marker=0x86 service=71 ver=0x03 task=4 declared=84
```

> 备注：服务端 bind 的是 `127.0.0.2:3074`；日志里"大厅连接建立"的对端是客户端（本机回环），
> 因此显示 `'127.0.0.1', <ephemeral>`。

### STEP 13 —— 观察任务交换与 publisher 下发

```powershell
Select-String -Path "REF_LOBBY_KIT\lobby_srv.log" -Pattern '解密成功|keepalive|publisher|缺' |
  Select-Object -Last 40
```
期望：出现 `-> publisher mp_playlists_shipRetail_1.0.0.info (976 字节)` 等 10 条，**且没有 `缺`**。

### STEP 14 —— 等待大厅 UI

```powershell
python -X utf8 "CODOLServer\_mainline\agent_client.py" run powershell -NoProfile `
  -Command "(Get-Process codoMP_client_shipRetail -EA SilentlyContinue | Select-Object Id,Responding,MainWindowTitle) | Format-List"
```
期望：进程存活、`Responding=True`、标题 `使命召唤online`；可另用截图工具确认窗口类 `CODO`。

### STEP 15 —— 验证最终大厅状态

按 §12 的五条判据逐条勾。全部满足 → `LOBBY_REPRODUCTION_STATUS = CONFIRMED`。

---

## 11. 每一步的成功信号

| STEP | ACTION | EXPECTED RESULT | LOG / SIGNAL | FAILURE SIGNAL |
|---|---|---|---|---|
| 01 | 切到项目根 | 路径正确 | `Get-Location` 输出 | 路径不同 → 后续相对路径全错 |
| 02 | 查客户端 | 四个 True | 文件存在 | 缺 exe/dll → 客户端起不来 |
| 03 | 查 Publisher 数据 | 五个 True | 目录存在 | False → `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` |
| 04 | 查端口 | 3074/28960 空闲 | `netstat` | 被占 → 服务起不来或抢端口 |
| 05 | 清残留 | 无残留进程 | `Get-Process` 空 | 残留 → 坏启动 `rc=1 t≈10s` |
| 06 | 起代理 | UAC 弹出 | 代理 stdout: `elevated_agent pid=.. port=.. debug=..` | 拒绝 UAC → STEP 07 失败 |
| 07 | ping 代理 | `ok=true, debug_privilege=true` | `agent_client.py ping` | `elevated_agent.json` 不存在 / 连接被拒 |
| 08 | 跑 run_all | 服务起、客户端起 | `run_all.py` 控制台 `[4/5]`/`[4/4]` | `坏启动` 重试 6 次全失败 |
| 09 | auth 监听 | `127.0.0.1:3074 LISTENING` | `auth3074.log` `TLS 就绪` | 端口没起 → 客户端 `DW_ACCOUNT_ERROR` |
| 10 | lobby 监听 | `127.0.0.2:3074 LISTENING` | `lobby_srv.log` 首行 | 端口没起 → 客户端 `[100]无法连接大厅服务!` |
| 11 | IIPS/IFS2 | `IIPSHostApp.exe` 在 | `iips.dll`/`ifs2.dll` 模块载入 | `初始化IIPS错误：8189fec` / 无网络层 |
| 12 | 握手 | `=== 大厅连接建立 ===` + `★ 试解命中` | 首帧 `hmac=OK marker=0x86` | `hmac_ok=false have_aes_out=false`（观测侧没导出密钥） |
| 13 | 任务/publisher | 多条 `解密成功` + 10 条 `-> publisher` | 无 `缺 xxx` | 有 `缺 <name>` → 弹致命框 |
| 14 | 大厅 UI | 窗口类 `CODO`, 标题 `使命召唤online` | 截图 | 停留启动画面 / 弹窗 |
| 15 | 最终判据 | §12 五条全过 | `hmac=BAD = 0` | 有 BAD / 无 keepalive |

---

## 12. Lobby 成功判据

```text
LOBBY_REPRODUCTION_STATUS = CONFIRMED  当且仅当：
  ① Client process alive（codoMP_client_shipRetail.exe 存活, Responding=True）
  ② required initialization complete（IIPSHostApp + iips.dll + ifs2.dll 载入; /auth/ 200）
  ③ Lobby connection established（lobby_srv.log: === 大厅连接建立 ===, 且 [keys] ★ 试解命中）
  ④ Lobby state/UI loaded（首帧 hmac=OK marker=0x86; keepalive 出现;
     窗口类 CODO, 标题 "使命召唤online"）
  ⑤ hmac=BAD 计数 = 0
```

冻结基线的量化参照（`GOLDEN-LOBBY-001.md` §3，本次已用日志逐项复核）：

```text
lobby_srv.log (134,649 B) : 建立 23 / 结束 23 / 异常 0 / keepalive 15 / hmac=OK 235 / hmac=BAD 0
auth3074.log              : TLS 认证记录
battle_srv.log            : 已监听 28960, 收包=0（未进对局）—— 不影响大厅判定
```

---

## 13. Quick Reproduction — Lobby Only

> 目标：新 Agent **不读任何逆向报告**，只读本节也能完成大厅复现。
> 前提：这台机器上 `REF_LOBBY_KIT\` 与 `run_codol_001\sandbox_datafix_20260929\` 已就位。

### 0) 环境前置

- Windows；`python` 在 PATH；**磁盘空间充足**（`REF_LOBBY_KIT` 含 mem_* 转储，约 26.7 GB）。
- 你能看到 UAC 弹窗并**人工点"是"**。
- 不修改 `COD OL\`（出厂原件）。

### 1) 文件准备

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'

# (a) 客户端/沙箱
Test-Path 'run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe'   # True

# (b) Publisher/Golden 数据目录（★ 必须在 REF_LOBBY_KIT 上）
Test-Path 'REF_LOBBY_KIT\publisher_files'      # True
Test-Path 'REF_LOBBY_KIT\player_profiles'      # True
Test-Path 'REF_LOBBY_KIT\user_files'           # True
```

若你在 `GOLDEN-LOBBY-001\REF_LOBBY_KIT` 上工作，先把数据目录补进去
（**不要**反过来从 Golden 拷代码覆盖正式副本）：

```powershell
# 仅当必须在 Golden 副本上运行时才执行（示例，未在历史报告中出现；推荐直接用 REF_LOBBY_KIT）
# robocopy 'REF_LOBBY_KIT\publisher_files' 'GOLDEN-LOBBY-001\REF_LOBBY_KIT\publisher_files' /E
# robocopy 'REF_LOBBY_KIT\player_profiles' 'GOLDEN-LOBBY-001\REF_LOBBY_KIT\player_profiles' /E
# robocopy 'REF_LOBBY_KIT\user_files'      'GOLDEN-LOBBY-001\REF_LOBBY_KIT\user_files'      /E
# robocopy 'REF_LOBBY_KIT\mkt_assets'      'GOLDEN-LOBBY-001\REF_LOBBY_KIT\mkt_assets'      /E
# robocopy 'REF_LOBBY_KIT\sku_arrays'      'GOLDEN-LOBBY-001\REF_LOBBY_KIT\sku_arrays'      /E
```

### 2) 服务启动（一键）

```powershell
# UAC：启动提权代理（人工点"是"）
$py = (Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8',
  'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' `
  -Verb RunAs -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping    # 期望 ok=true, debug_privilege=true
```

```powershell
# 清残留（ACE 保护，必须走提权代理）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run powershell -NoProfile `
  -Command "Get-Process codoMP_client_shipRetail -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue"
```

```powershell
# 一键：起 auth(127.0.0.1:3074) + lobby(127.0.0.2:3074) + 注入 + 拉起客户端
cd "D:\BaiduNetdiskDownload\使命召唤OL"
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 600 --out n10_golden.txt
```

（只想跳过战斗服，就加上 `--no-battle`。）

### 3) 权限 / UAC

见 §7。要点：起代理会弹 UAC，**人工批准**；`run_all.py` 本身要以管理员权限运行。
**不要**尝试绕过 ACE / TenProtect（纪律，见 §7.4）。

### 4) 客户端启动

由 `run_all.py` → `nt10.py` 自动完成（见 §9）。**不要**手工双击沙箱里的 exe。

### 5) 等待条件

```text
> 等待 auth3074.log 出现 TLS 就绪
> 等待 lobby_srv.log 出现 === 大厅连接建立 ===
> 等待出现 ★ 试解命中 与 首帧 hmac=OK marker=0x86
> 等待出现 <- keepalive
> 等待出现 -> publisher ...（10 条, 无 "缺"）
```

### 6) 验证大厅

```powershell
Select-String -Path "REF_LOBBY_KIT\lobby_srv.log" -Pattern '大厅连接建立|试解命中|keepalive|hmac=OK|hmac=BAD|publisher|缺' |
  Select-Object -Last 40

python -X utf8 "CODOLServer\_mainline\agent_client.py" run powershell -NoProfile `
  -Command "(Get-Process codoMP_client_shipRetail -EA SilentlyContinue | Select Id,Responding,MainWindowTitle) | Format-List"
```

**判成功**：§12 的 ①~⑤ 全部满足，且 `hmac=BAD` 为 0。

---

## 14. 首次复现 Checklist

```text
[ ] 工作目录 = D:\BaiduNetdiskDownload\使命召唤OL
[ ] 客户端文件完整（codoMP_client_shipRetail.exe / Base.dll 存在）
[ ] 使用 REF_LOBBY_KIT\（或已补齐数据的副本），不是裸 Golden
[ ] Publisher 数据目录存在（publisher_files / player_profiles / user_files / mkt_assets / sku_arrays）
[ ] hosts 含 # CODOL-LOCAL-BEGIN 块（127.0.0.1 formal-zone-auth / 127.0.0.2 formal-zone-lsg）
[ ] dwauth.ini = formal-zone-lsg...3074 / formal-zone-auth...3074 / 0x03EA
[ ] iips.ini = enable_iips=1
[ ] cacert.pem 含本地根 CA
[ ] required ports available（3074 ×2、28960 空闲）
[ ] elevated_agent 已启动且 debug_privilege=true
[ ] UAC 已人工批准
[ ] agent_client.py ping OK
[ ] 无残留 codoMP_client_shipRetail / TP3Helper / IIPSHostApp
[ ] client launched（由 nt10 拉起，非手工双击）
[ ] IIPS 初始化（IIPSHostApp.exe + iips.dll）
[ ] IFS2 初始化（ifs2.dll）
[ ] /auth/ 200（auth3074.log: -> 200 task=10->11）
[ ] Lobby TCP established（lobby_srv.log: === 大厅连接建立 ===）
[ ] Lobby service response received（★ 试解命中 / 首帧 hmac=OK marker=0x86）
[ ] publisher 文件下发无 "缺"
[ ] lobby keepalive 出现
[ ] hmac=BAD 计数 = 0
[ ] 客户端窗口类 CODO / 标题 "使命召唤online"
[ ] client is in Lobby
```

---

## 15. Failure Diagnosis

| 症状 | 可能原因 | 确认方法 | 恢复方法 |
|---|---|---|---|
| 客户端完全不启动（坏启动 `rc=1 t≈10s`） | 残留实例占单实例互斥；UAC/提权缺失；Publisher 数据缺 | `Get-Process codoMP_client_shipRetail`；`run_all.py` 开头的僵尸自检；`lobby_srv.log` 有无 `缺` | 走提权代理杀干净残留；确认提权代理在线；补齐 Publisher 数据目录；重跑 |
| 弹 `请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。` | 无参数/无 TCLS 上下文启动 | 该对话框 class=#32770 标题「致命错误」 | 用本 SOP 的 nt10 启动路径（不要手工双击沙箱 exe） |
| 弹 `初始化IIPS错误：8189fec` | `iips.ini` 的 `enable_iips=0`，IIPS 未载入 | 窗口类 `iipsinit`；检查 `<GAME ROOT>\iips.ini` | 设 `enable_iips=1`；确认 `IIPSHostApp.exe` 启动；必要时以管理员启动 |
| 游戏内出现 `[100]无法连接大厅服务!` | 大厅 3074 没起 / 地址被劫持错 / Publisher 缺文件 | `netstat` 看 3074；`lobby_srv.log` 是否启动；有无 `缺` | 起 auth+lobby；确认 hosts 与 dwauth.ini；补齐 Publisher 数据 |
| elevated_agent 不可用 | UAC 被拒；代理未启动；状态文件缺失 | `logs\elevated_agent.json` 是否存在；`agent_client.py ping` 报错 | 重新 `Start-Process -Verb RunAs`；人工批准 UAC；`ping` 直到 `debug_privilege=true` |
| Lobby TCP 未建立 | lobby 服务未起；`127.0.0.2:3074` 被占；hosts/dwauth 错；Publisher/平台上下文未就绪 | `netstat -ano` 查 `127.0.0.2:3074`；`lobby_srv.log` 是否出现"建立" | 按 §8 顺序起服务；修正 hosts/dwauth；处理端口占用 |
| 客户端启动但不进大厅 | IIPS/IFS2 未初始化；`/auth/` 未过；session 上下文缺失；无 lobby 应答 | 查 `IIPSHostApp.exe`、`auth3074.log`、`lobby_srv.log` | 逐层回退到上一个成功阶段（§10 STEP 11→12） |
| 握手出现 `hmac=BAD` 或 `hmac_ok=false have_aes_out=false` | 观测侧没导出会话密钥（KDF hook 没命中）；或 0x83 用了过期 challenge | `secrets_kdf.txt` / `kdf_sessions.txt` 是否更新；日志有无 `[keys] ★ 试解命中` | 确认 nt10 的 KDF hook 生效；确认 lobby_server.py 是 Golden 版本（0x83 用本会话 challenge） |
| 连接建立后客户端约 4-5 分钟后正常关闭并重连 | **当前没有游戏世界（world）**，属预期行为；BAD 是结果不是原因 | 主连接存活时长 + 期间 hmac 全 OK | **不要**把它当主线阻塞去修（历史明确更正过） |
| lobby 服务起了但客户端断开 | 会话密钥/challenge 竞态；Publisher 缺文件 | 同时抓 `lobby_srv.log` 与 `n10*.txt` 的连接生命周期 | 按日志定位：缺文件→补数据；challenge→用 Golden lobby_server.py |
| 任务只解出 4 条就断 | 用错了服务端（自研 `CODOLServer\` 而非 `REF_LOBBY_KIT\`） | 日志特征 `71/3` 错误上报、`declared=212` | 改用 `REF_LOBBY_KIT\lobby_server.py` |
| 内存读取在 ~10s 后失效 | ACE 保护 | 观察器报错 | 通过提权代理在 nt10 早期拿句柄（见 §7.2） |
| `127.0.0.1:443` 被占 / portproxy 残留 | 旧 OfflineServer 方案遗留 | `netsh interface portproxy show v4tov4` | 按 §16 删除该条 portproxy |

> **本表只列有证据的恢复方法。** 没有证据的修复方向一律不写；对应条目见 §19 的 `UNRESOLVED`。

---

## 16. 回滚方法

| 对象 | 回滚动作 | 证据 |
|---|---|---|
| hosts | `python -X utf8 "REF_LOBBY_KIT\run_all.py" --restore-hosts` | `run_all.py` L650-656 |
| `dwauth.ini` | `run_all.py --no-dwauth` 跳过；历史值在 `<GAME ROOT>\dwauth.ini.bak_*` | 磁盘上的 `.bak_*` 文件 |
| `iips.ini` | 备份 `<GAME ROOT>\iips.ini.bak_enable0_20260927`；**不要**改回 0（会失去启动链） | `HANDOFF_20260927_IIPS_GATE_RESOLVED.md` §5 |
| Golden 代码 | 以 `GOLDEN-LOBBY-001\REF_LOBBY_KIT\_golden_hashes.json` 校验 SHA-256 | 该 json |
| 商城目录 | 删开关 `marketplace-catalog-merged.on` 即退回原目录；备份 `marketplace-catalog-merged.json.bak_trusted_37793_20261007` | `HANDOFF_20261007_TAKEOVER.md` §3 |
| SKU 实验开关 | `marketplace-skus.on.rolled_back_*` / `marketplace-skus-allow-unsafe.on.rolled_back_*` / `market-sku-probe.on.tested_ok` / `market-tables.on.paused_*` 都已是关闭态 | 同上 |
| 靶场 booking 推送 | `firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH` —— **实测 9/9 断连，必须保持关闭** | `GOLDEN-LOBBY-001.md` §1.3/§6 |
| 战斗服 | `run_all.py --no-battle`；或 `lobby_server.py` 的 `firingrange-battle.enabled` 开关 | `run_all.py` L718-725 |
| TAS 注入 | 默认已关（`tas_off.flag`）；要注入才加 `--tas` | `run_all.py` L669-679 |
| 旧 portproxy（若存在） | `netsh interface portproxy delete v4tov4 listenport=443 listenaddress=127.0.0.1` | `run_lobby_elevated.bat` 第 [0] 步 |
| 进程 | 通过提权代理 `Stop-Process` | §7.3 |

---

## 17. 已确认事实

```text
[F-01] 大厅主通道 = 127.0.0.2:3074 (明文 lsg, formal-zone-lsg.codol.qq.com)                 CONFIRMED
[F-02] 认证通道   = 127.0.0.1:3074 (TLS, formal-zone-auth.codol.qq.com)                     CONFIRMED
[F-03] 战斗通道   = UDP 0.0.0.0:28960, 大厅阶段收包=0                                        CONFIRMED
[F-04] 启动链闸门 = iips.ini -> enable_iips=1 -> IIPSHostApp + iips.dll + ifs2.dll           CONFIRMED
[F-05] 握手帧     = 0x81(204B) / 0x82(153B) / 0x83(204B) / 0x85(seq+IV+AES-CBC+HMAC-SHA1前8B) CONFIRMED
[F-06] 会话密钥来源 = nt10.py @0x00BA0D20 KDF hook -> secrets_kdf.txt / kdf_sessions.txt      CONFIRMED
[F-07] 4 个内存补丁 @0x00B9A78E / 0x00B9A7C5 / 0x00B9A7C7 / 0x00BA3C1C                       CONFIRMED
[F-08] Publisher = service=10/task=21, 从 <kit>\publisher_files\<name>.info 下发           CONFIRMED
[F-09] 首次进大厅 = 2026-10-05 16:36, 任务 34 -> 47, 窗口类 CODO, 标题 "使命召唤online"       CONFIRMED
[F-10] 冻结基线 = 2026-10-07 GOLDEN-LOBBY-001, lobby_srv.log 235 OK / 0 BAD / 15 keepalive     CONFIRMED
[F-11] 客户端 build = 1649370, exe 7,841,344 B, SHA256 36997674...                           CONFIRMED
[F-12] 客户端启动 = nt10.py Popen([<GAME ROOT>\codoMP_client_shipRetail.exe], cwd=<GAME ROOT>) CONFIRMED
[F-13] Golden 副本缺数据目录（publisher_files 等）→ 直接跑会复现 publisher 失败               CONFIRMED
[F-14] 需要提权：读内存 / 杀客户端 / 改 hosts / 写 cacert / portproxy                          CONFIRMED
[F-15] 纪律：不绕 ACE/TenProtect（历史蓝屏 0x01010002）                                        CONFIRMED
[F-16] IFS = IIPS 的本地归档/VFS 子系统（IFS2.dll: CreateIFSLibDll/DestoryIFSLibDll/
       IFSDllVerifyApiCompatable；另 IIPSVFS.dll + IIPSFileList.ini）                          CONFIRMED
```

---

## 18. 已关闭研究支线（以后不要再研究）

### A. senderId / A-B endian —— 已确认，但有重要更正

```text
CONFIRMED（指令级）：+0x168 = A, +0x16C = B
  0x62F736  mov ecx,[edi+0x168]    ; A = item+0x168
  0x62F73C  mov [esi+0x3a048],ecx
  0x62F742  mov edx,[edi+0x16c]    ; B = item+0x16C
  0x62F748  mov [esi+0x3a04c],edx
CONFIRMED（动态 018 + 019）：A = LOW32, B = HIGH32
```

★ **更正（不得再写错）**：把 A/B 说成"= SessionId"只是**操作上成立**，不是本质要求。
`DEV-BOOKING\PVE-MATCHING-AB-FIELD-IDENTITY-018.md` §0 明确：
`matching+0x3A048 / +0x3A04C` **不是 SessionId**，而是 `21/5 findSessions` 会话对象里 tag=0x0A 的 u64 字段
（字段序 #7）；019 动态把 #7 设成 SessionId 后 `AB_ALIGNMENT = CONFIRMED`。
**本质要求：信封 senderId A/B == 会话对象字段 #7。**
来源：`DEV-BOOKING\PVE-SENDERID-AB-ENDIAN-CONFIRMATION-013.md`、`...-018.md`、`...-019.md`。

### B. Lobby transport ≠ Battle transport —— 已确认

```text
CONFIRMED：0xB81EF0 → 内含 0xB82025 → 0xBA4080  = Lobby 主连接（唯一链）
           Battle 专用 connect = 未发现（无第二个 0xB81EF0 调用者）
           type-2 对象 = Demonware LOBBY TCP 连接
              socket(AF_INET, SOCK_STREAM=1, IPPROTO_TCP=6), 日志 "DW_LOBBY_CONNECTED"
           Battle 传输 = UDP（021: CODOL_BATTLE_TRANSPORT = UDP）
```
来源：`DEV-BOOKING\MVP-PVE-MATCH-ENTRY-009.md` §6、`CLIENT-BOOKING-BATTLE-OBJECT-016.md` §1。

### C. 0x818de0 ≠ Battle —— 属 chat.private

```text
CONFIRMED：STATE_MACHINE_818DE0 = chat.private 私聊状态机（仅 state4 实现）
          WORKER_TO_818DE0 = chat.private
          "006 把该链归为 booking" = REFUTED
```
来源：`DEV-BOOKING\BOOKING-CONNECT-PATH-007.md` §3/§6、`...-014.md` §5。

### D. `[0x849B61C]` ≠ Battle trigger —— consumers 是 UI/progress/telemetry

```text
CONFIRMED：0x849B61C_CONSUMERS = NOT_BATTLE_TRIGGER
  读取者 0x7CB1E2 → call 0x620590   (UI / telemetry, mask 0xdb0000)
  读取者 0x7CFA87 → call 0x7CB210   (UI / progress)
  无 socket / endpoint / UDP
```
来源：`DEV-BOOKING\CLIENT-BOOKING-BATTLE-TRIGGER-014.md` §2。

### E. Battle trigger —— 仍然 UNRESOLVED

```text
BATTLE_TRIGGER_PATH = UNRESOLVED（跨模块间接触发，非直连）
015 进一步证伪"accepted → listener → Battle"：7/7 listener 都不是
  （5× 0x4F7590 ret 8、1× wargod 0x738E70、1× UI/CEF 0x7CAF30）
```
**所以 Battle trigger 不能写成大厅复现的依赖。**
来源：`...-014.md` §0、`CLIENT-BOOKING-LISTENER-BRIDGE-015.md` §0、`...-016.md` §0。

### 附：本项目已作废的假设（大厅相关，不要再试）

`HANDOFF_20261005_TAKEOVER_NO_ADVANCE.md` §6 与 `HANDOFF_20260927_IIPS_GATE_RESOLVED.md` §7 记录：

```text
[x] [req+0x644] 是配置链总开关                       否证
[x] [0x84ABB2F] (g2f) 是卡点                          否证
[x] 只要 0xB7A670 返回 2 就能开 gate                  否证
[x] 用 [obj+0x620][4:20] 当 0x85 密钥                 作废（已修正为 [provider+0x9C][:16]）
[x] 复现 WeGame/TCLS 上下文才能载入 IIPS              证伪（与 IIPS 载入无关）
[x] 把 iips.dll 换回 72DD 当"基线"                    方向反了，当前可用组合已在位
[x] 从 dwauth.ini / portproxy 入手                    三次成功运行都不需要改
[x] 把 enable_iips 当"只读回显"                       已被 0/1 对照推翻
[x] 把 enable_iips 改回 0                             会直接失去启动链
[x] 应答体形状/大小（认证侧，749 模板等）             否证（且 13:28 后 queue 已消失，判据是假的）
[x] 非提权进程读 ExecutablePath 为空 = 进程不存在      证伪（是可见性问题，进程确实在跑）
```

---

## 19. Post-Lobby 未完成事项（POST-LOBBY / FUTURE WORK）

> 本节内容**不属于**大厅复现步骤，**不得**写成大厅的隐含依赖。

### 19.1 Booking / Battle / PvE 现状

```text
mmbook accepted = 已经可以产生
   CONFIRMED：017 ACCEPTED_WIRE（9 次 "mmbook accepted" 实际发出）；023 wire check PASS
A/B = 已确认
   A=LOW32 / B=HIGH32（018 字段身份 + 019 动态）
accepted handler = 已确认（但从未执行）
   handler 0x632680 CONFIRMED（020 分派链；022 的 7 道门）
   ACCEPTED_HANDLER_EXECUTED = NO（017/019）；023 在 G4 就失败，走不到 G6
accepted → Battle UDP = 未解决
   BOOKING_TO_BATTLE_CONNECT = UNRESOLVED（009 §22）
UDP 28960 = 尚未成功
   CLIENT_UDP_28960_SEEN = FAILED（012）；BATTLE_RX_COUNT = 0（017）；
   BATTLE_28960_TRIGGER = NOT_OBSERVED（023）
DTLS = 未完成 / 且不是标准 DTLS
   021：走 UDP(SOCK_DGRAM/IPPROTO_UDP)，但【没有证据】它是标准 DTLS；
   DTLS/ECDH/secp224 字符串只是 OpenSSL 0.9.8p 静态表，不能当证据；
   实际握手是自定义 4 步：NAT(29B) → init(16B)/cookie(38B) → cookie+pubkey(219B)/ack(114B) → data
PvE session = 未完成
   PVE_SESSION_CREATED = NOT_TESTED（009/012）
Map entry = 未完成
   MAP_ENTRY = NOT_TESTED
```

### 19.2 根因定位（材料中已有结论）

```text
大厅 3074: 21/5 / 6/14 / 11/4 全部已响应
     ↓
sharedRoomClient / DedicatedBookingDispatcher: ★ 从未实现
     ↓
分配/启动战斗服 → 客户端进入加载 → 连 UDP 28960
```

缺口是 **booking / room 控制面**，不是大厅里的某个推送字段。
`sharedRoomClient_.connect(...)` 连的是**独立的 DedicatedControl / client bridge 端口**，
不是大厅 3074，也不是战斗服 28960（`HANDOFF_20261007_TAKEOVER.md` §5、`STAGE_REPORT_BATTLE.md:95`）。

### 19.3 其它 Post-Lobby 缺口（P1/P2，非大厅依赖）

```text
P1 商城目录页（80/70 等）回空     -> 商城空白 + 军火箱页面重叠
P1 游玩清单 MP 条目为空           -> MatchMakingStripView #1009
P1 公告 #1125 / 首页挑战 #1010
P2 名片/徽章/称号 拥有与装备（缺 ref↔itemID 映射表）
P2 未映射服务 3/46,48,53 · 9/5,14 · 10/20 · 12/6 · 28/1,4 · 29/10 · 102/1,2,7
```
来源：`GOLDEN-LOBBY-001.md` §5、`HANDOFF_20261007_TAKEOVER.md` §5/§15。

### 19.4 明确声明

```text
"进入大厅" ≠ "进入 PvE"。
大厅复现成功后，客户端在大厅停留、主连接结束后可能正常重连，
那是"没有游戏世界(world)"的预期结果（HANDOFF_20261005_LOBBY_REACHED.md §2.5），
不是大厅复现的失败。
```

---

## 20. 当前阶段结论

```text
STAGE                     = LOBBY_REPRODUCTION
STAGE_STATUS              = LOBBY_REPRODUCTION_CONFIRMED
NOT_FULL_PVE              = TRUE
LOBBY_REPRODUCTION_STATUS = CONFIRMED
QUICK_REPRODUCTION        = READY
AUTHORITY                 = GOLDEN-LOBBY-001.md (2026-10-07, FROZEN)
LAST_LOBBY_ENTRY          = 2026-10-05 16:36 (HANDOFF_20261005_LOBBY_REACHED.md)
BASELINE_LOG_METRICS      = 建立23 / keepalive15 / hmac=OK 235 / hmac=BAD 0
```

本阶段**已完成**：

- 客户端从"完全不能启动"到"稳定启动并载入 IIPS/IFS2"。
- 认证层 + 大厅链路全通，握手密码学闭合。
- Publisher 数据下发完整，无致命弹窗。
- 大厅 UI 渲染并被截图确认。
- 环境被冻结成 `GOLDEN-LOBBY-001`，并补齐了数据目录缺口。

**未完成**（全部隔离在 §19）：

- Booking 控制面、Battle UDP 28960、DTLS/自定义握手、PvE session、Map entry。
- 商城目录页、MP 游玩清单、公告/挑战。

> 关于 CONFIRMED 的口径（避免误读）："CONFIRMED"指**该状态在冻结基线与历史实机中被确认可达**，
> 且本次已在磁盘/端口/日志层面复核；它**不**表示本文件生成会话又跑了一遍实机。

---

## 21. 下一阶段入口

1. **稳定起点**：任何 Booking / Battle / PvE 工作都以本文件的 §13 复现到大厅后为基线，
   **不要**重新经历黑箱逆向、文件恢复、启动机制分析、Lobby 链路定位。
2. **P0（Booking 控制面）**：复刻 `sharedRoomClient` / `DedicatedControl` 控制面
   （ol-mod `src/game_server/` 源码**不在本机**，需先取得），
   或在 `REF_LOBBY_KIT` 新增 `booking_server.py` 接收 `mmbook/mmstart` 并分配 28960。
3. **P0（Battle UDP）**：让客户端真正向 28960 发包（判据：`battle_srv.log` 出现
   `RX #1 ... 16B` 即握手 init）。
4. **P1（商城 / 清单 / 公告）**：继续只读 provider 调用链 dump，严禁再"猜"对象格式
   （历史上猜 SKU 页把整个 marketplace 打挂过两次）。
5. **纪律**：Golden 只读；一切实验在开发副本，带开关 + 单条 + 可回滚；不碰 ACE/TP。

---

## 附录 A：SOURCE_CONFLICT 清单（冲突双留）

| # | 冲突点 | 说法甲（较新/优先） | 说法乙（较旧/被替代） | 处理 |
|---|---|---|---|---|
| A1 | 大厅明文端口 | `127.0.0.2:3074`（2026-10-07 Golden） | `127.0.0.1:8446` / poke 8443（2026-09-28） | 以 3074 为准；8446/8443 为历史方案 |
| A2 | Publisher 缺文件根因 | 数据目录缺失 `GOLDEN_DATA_DIR_INCOMPLETE`（RECOVERY-001/002，2026-10-08） | "本地完全没有"（SPEC-001，较旧，未结论） | 以 RECOVERY 为准 |
| A3 | Golden 里的 `lobby_spec.txt` | 磁盘实际值 `127.0.0.1:3074:3074`（20 B） | `GOLDEN-LOBBY-001.md` §1.3 写 `127.0.0.1:3074:CODOL-LOCAL` | 记录冲突；`lobby_spec` 不参与 Golden 复现路径（不写大厅全局） |
| A4 | 基线日志位置 | 顶层 `REF_LOBBY_KIT\lobby_srv.log`（134,649 B） | `GOLDEN-LOBBY-001\REF_LOBBY_KIT\lobby_srv.log`（31,377 B，含 `缺`） | 以顶层为基线日志；Golden 目录那份是失败复现记录 |
| A5 | `iips.dll` 版本身份 | 原件 `72DD…`（`COD OL`，2026-09-10） | 沙箱用 `E2367C48…`（2026-09-21，本项目 PE 手术产物）；早期报告把二者写反 | 以 IIPS 报告更正版为准；当前可用组合=沙箱 `E2367C48…` |
| A6 | `dwauth.ini` 格式 | 3074 域名版（当前 Golden） | `127.0.0.1/443` 旧版（`HANDOFF_20260927_IIPS_GATE_RESOLVED.md` §3） | 以 3074 域名版为准 |
| A7 | `[req+0x644]` 是否进大厅判据 | 不是必要判据（2026-10-05 更正） | 曾当作判据（更早） | 以更正版为准，644 作废 |
| A8 | 是否允许改 `.text` / 下断点 | 允许（2026-10-01 解锁；`HANDOFF_20261002_TLDR.md` §二） | 禁止修改 `.text`（`HANDOFF_20260929_LOBBY_PROTOCOL.md` §721-723） | 两说并存；**ACE/TP 不绕过**这一点无冲突 |

---

## 附录 B：本文件生成过程中实际执行的校验（可复核）

```text
1. 目录/文件存在性
   - run_codol_001\sandbox_datafix_20260929 存在；
     内含 codoMP_client_shipRetail.exe (7,841,344 B)、
     codoMP_client_shipRetailBase.dll (60,327,992 B)、dwauth.ini、iips.ini。
2. 配置内容
   - dwauth.ini = 三行（3074 域名 + 0x03EA）
   - iips.ini    = enable_iips=1 / iips_url="http://10.231.2.181/"
3. 数据目录
   - REF_LOBBY_KIT: publisher_files=26 文件 / player_profiles=9 / user_files=1 / mkt_assets / sku_arrays 均在
   - DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT: 同上齐全
   - GOLDEN-LOBBY-001\REF_LOBBY_KIT: 只有 __pycache__，
     publisher_files / player_profiles / user_files / mkt_assets / sku_arrays  ★全部 MISSING
4. hosts
   - 当前含 # CODOL-LOCAL-BEGIN 块（127.0.0.1 formal-zone-auth / 127.0.0.2 formal-zone-lsg），
     另有历史遗留的两行同类映射
5. 日志指标（对 REF_LOBBY_KIT\lobby_srv.log 逐行统计）
   - 大厅连接建立 = 23 / <- keepalive = 15 / hmac=OK = 235 / hmac=BAD = 0
     （与 Golden §3 完全一致）
6. 端口快照（生成本文件时）
   - 观察到 127.0.0.1:3074 LISTENING、127.0.0.2:3074 LISTENING、UDP 0.0.0.0:28960 已绑定，
     且有 127.0.0.1:<ephemeral> -> 127.0.0.2:3074 ESTABLISHED（说明当时有大厅会话在位）
   - 另观察到 127.0.0.1:443 LISTENING 与 portproxy「127.0.0.1 443 -> 127.0.0.1 8443」
     —— 这是**旧 OfflineServer 方案的历史遗留**，与 Golden 要求（443/80/8081 空闲）不符，
     建议清理（见 §16）
7. 进程归属（PID 16360/22336/14220/24524）
   - 本次会话为受限上下文，WMI/CIM 查询被拒绝（拒绝访问），**未能确认进程名**；端口快照本身可复核
   - 注：另有一份提权代理状态文件显示 pid=21428 / port=54901 / debug_privilege=true（研究时读取）
8. 源码核对
   - nt10.py:2101  Popen([<root>\<exe>], cwd=root)
   - run_all.py L41 GAME_ROOT / L49-52 hosts 块 / L392 auth / L449-451 lobby /
     L486-488 nt10 参数 / L718-725 battle 起法 / L650-656 --restore-hosts
   - elevated_agent.py L87-88 状态路径 / L104-107 ping 返回 / L127-138 启动打印
   - agent_client.py L13-14 状态路径 / L36-40 ping 与 run
9. 未执行
   - 本会话未启动/未重启客户端，未做新的实机端到端跑（需人工批准 UAC）
```

---

*（本文件为后续所有 Booking / Battle / PvE 工作的稳定起点基线。Golden 只读；实验在开发副本，带开关、单条、可回滚。）*









