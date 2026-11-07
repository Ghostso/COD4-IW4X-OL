# 10 — A：Diff 范围与插桩影响审查（Diff Scope Review）

> 任务：`EARLY-SERVER-TAP-PREFLIGHT-001`，只读审查与实验设计。
> 边界：本轮不启动客户端/服务端/launcher，不执行 `.cmd`/未知脚本/二进制，不应用、改写或试跑 tap diff，不修改原始样本、既有报告或可进入大厅的基线。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

---

## A.0 目录与拼写纠正

用户给出的输出目录写作 `EARY_SERVER_ANALYSIS`，但既有目录实际使用 `EARLY_SERVER_ANALYSIS`。本轮按既有命名约定创建并使用：

`D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\10_TAP_PREFLIGHT_001\`

未创建 `EARY_SERVER_ANALYSIS`，避免维护两个混淆目录。

---

## A.1 一句话裁决

- `wire_interception.md` §4 的目标文件被明确写为 Python `game-server.py`，但全盘只读搜索 `D:\BaiduNetdiskDownload` 的结果是 `game-server.py count=0`、`tap_report.py count=0`。
- 当前服务器启动脚本明确说明它运行原生 `codol_dedrun_next.exe`，且是 “in place of the Python game-server.py”（`dedicated\bin\START-CODOL-SERVER.cmd:4-6`）。
- 因此，**§4 diff 不能按原文应用**；它对当前原生服务端树的适用性为 **REFUTED**。
- 即使假设 Python 目标存在，§4 也只记录 gamestate 元数据和 snapshot `op` 计数，**不记录 gamestate/snapshot 完整载荷**；它不足以完成本任务要求的完整载荷验证。
- 本轮只给出原生栈候选插桩点，未实施任何插桩或运行实验。

---

## A.2 输入与复核位置

| 输入 | 路径 | 复核结果 |
|---|---|---|
| tap diff 文档 | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\lobby\docs\wire_interception.md` | 13,470 B；SHA-256 `BB1F82F118DA9694ECE8ECF679495256A41423ECE50A6DD0BAA11AF279C61375` |
| §4 标题与范围 | 同上，`:122-132` | “Game-server integration — THE DIFF (not applied; apply verbatim when the file is free)” |
| §4 diff 正文 | 同上，`:134-203` | 7 个 hunk：WT-G0 至 WT-G6 |
| 应用说明 | 同上，`:205-215` | 目标 `game-server.py` 为 CRLF；按上下文锚点应用；`tap_report.py` 被假定已存在 |
| 启动脚本 | `...\CODOL_Server\dedicated\bin\START-CODOL-SERVER.cmd` | 12,116 B；SHA-256 `388C7F6F5BC91BD71D5EB039860B8297B826773C3D20D9CF3CBC902E43ECDE96` |
| 原生服务器 | `...\CODOL_Server\dedicated\bin\codol_dedrun_next.exe` | 8,469,493 B；SHA-256 `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| 客户端样本 | `...\CODOL_Client\codoMP_client_shipRetail.exe` | 20,918,752 B；SHA-256 `904436480938632A856B39DEA73FB94C9682B5A0EBF7FA619ECD5DD5475ED3B6` |
| 现有 tap 模块 | `...\CODOL_Server\lobby\demonware\wire_tap.py` | 12,408 B；SHA-256 `5004CF5EB473F0B4C5D0D1256E06C465690983965882A6EDB885F83BF07FBF59` |

全盘只读搜索证据：

```powershell
Get-ChildItem -LiteralPath 'D:\BaiduNetdiskDownload' -Recurse -File -Filter 'game-server.py'
Get-ChildItem -LiteralPath 'D:\BaiduNetdiskDownload' -Recurse -File -Filter 'tap_report.py'
```

结果均为 `count=0`。因此无法从真实文件核验 §4 中引用的行号、上下文和 Python 运行时行为。

---

## A.3 §4 的 7 个 hunk：目标、边界与影响

| Hunk | 文档行 | 文档目标文件/函数/上下文 | 插桩边界 | 预期观察内容 | 对缓冲区/长度/顺序/返回值的影响 |
|---|---:|---|---|---|---|
| WT-G0 | `:137-154` | `game-server.py:65` import 块 | 模块导入阶段，尚未进入网络收发 | 加载 `wire_tap`；失败时使用 no-op stub | 文档声称 log-only；但目标文件缺失，实际导入副作用和名称冲突 **UNKNOWN** |
| WT-G1 | `:155-160` | `note_client_packet`，在 `_apply_relack_seed(addr, st)` 后、`prev_ack` 前 | 入站已解码 netchan packet 后；可靠命令/usercmd 解析之前 | `c2s` 的 `clc_packet` 计数、`cmds` 数与 `move_len` | 不写入线缓冲区；仅计数。是否影响异常路径和时序 **UNKNOWN** |
| WT-G2 | `:161-167` | 可靠命令循环，sanity gate 接受命令后 | 入站可靠命令已被接受并写入 `_ctext` 后 | `clc_cmd` 的 `seq` 与前 200 字符 `text` | 不改线协议；但可能记录聊天/玩家文本，需脱敏；目标缺失故集成影响 **UNKNOWN** |
| WT-G3 | `:168-181` | usercmd decode 成功分支，`_ammo_decode_ok` 之后 | 入站 usercmd 已解码后 | `usercmd` 计数、`weapon`、`buttons` | 新增局部 `_tc` 和 try/except；目标函数变量表未知，变量冲突与行为影响 **UNKNOWN** |
| WT-G4 | `:182-190` | `build_gamestate`，gametype 解析后 | 出站 gamestate 构造阶段，实际发送前 | `map`、`gametype`、`fs_crc`、`seq`、`opcode` 元数据 | 不写入完整 gamestate 载荷；元数据日志本身可能泄露玩家/主机信息；实际影响 **UNKNOWN** |
| WT-G5 | `:191-195` | `_send_snapshot_now`，SENT 日志之后 | 文档上下文显示在实际发送日志之后，属于 post-send 观察；加密前后位置无法确认 | snapshot 的 `op` 计数，1/s 聚合 | **不记录完整 snapshot 载荷**；post-send 观察不能证明发送前字节未被修改；实际影响 **UNKNOWN** |
| WT-G6 | `:196-202` | `_queue_server_cmd`，queued 日志之后 | 出站可靠 server command 入队后、线序列化前 | `server_cmd` 的 `seq` 与前 300 字符 `text` | 不写线缓冲区；但命令文本可能包含敏感内容；实际影响 **UNKNOWN** |

### A.3.1 关键事实：§4 不是完整载荷 tap

`wire_interception.md` 的 §4 描述与实际插入内容表明：

- WT-G4 只记录 gamestate 的结构字段，没有 `payload`、`payload_hex`、`payload_len` 的完整字节记录。
- WT-G5 只调用 `wire_tap.bump(... "snapshot", values={"op": sop})`，没有记录 snapshot 的完整 payload。
- WT-G1、WT-G2、WT-G3、WT-G6 也都不记录完整线载荷。

所以，即使目标 `game-server.py` 存在，**仅应用 §4 仍不能满足“gamestate 完整载荷及长度、snapshot 完整载荷及长度”的捕获要求**。这是独立的阻塞项，与目标文件缺失相互叠加。

### A.3.2 现有 `wire_tap.py` 可证明什么

可核验的模块级事实：

- `tap()` 永不抛出，`CODOL_TAP=0` 时 no-op（`wire_tap.py:120-135`）。
- `bump()` 对高频路径按 key 做 1/s 聚合，distinct values 上限 32（`wire_tap.py:138-177`；上限定义于 `:47`）。
- `safe()` 对 bytes 只保留前 `blob_cap` 字节 hex 和精确长度，默认 256 B（`wire_tap.py:62-81`）。
- 日文件默认上限 256 MB，超过后写 `tap_capped` 并停止追加（`wire_tap.py:90-117`）。

这些只能证明 **tap 模块自身不会主动改线协议**。它们**不能证明**缺失的 `game-server.py` 中各 hunk 的上下文、控制流、变量作用域和异常行为没有变化。故对 §4 集成影响的结论是：

- `wire_tap.py` 模块行为：**CONFIRMED（源码级）**。
- §4 对目标 Python 服务的实际行为影响：**UNKNOWN（目标文件不存在，无法静态核验）**。
- §4 对当前原生服务端树的适用性：**REFUTED（目标、调用链和运行时均不匹配）**。

---

## A.4 当前原生服务端的真实编码/发送边界

以下位置来自既有 `09_A_SERVER_MESSAGE_LEDGER.md` 的源码账本，本轮只读复核了关键行号：

| 位置 | 语义 | 相对网络边界 |
|---|---|---|
| `dedicated\src\sv_main.c:3939-3949` | `SV_WriteGameState` 的 CODOL 分支调用 `CODOL_WriteServerGamestate`，传统 `svc_ops_e` 分支不可达 | 序列化入口 |
| `dedicated\src\codol\snapshot\codol_sv_state.c:141-146` | `CODOL_MsgWriteInit`；`CODOL_WriteGamestate`；`msg->cursize += wire.size` | gamestate 明文序列化后、netchan 编码前 |
| `dedicated\src\codol\snapshot\codol_configstrings.c:269-286` | configstring 子流：首字节 `3`、u16 count、位字段、终止字节 `5` | gamestate 内部子流 |
| `dedicated\src\codol\snapshot\codol_configstrings.c:288-308` | gamestate：首字节 `2`、u32 seq、map、zone_type、u32 crc、configstrings、clientNum、checksumFeed、终止字节 `5` | gamestate 明文序列化 |
| `dedicated\src\sv_snapshot.c:224-283` | `SV_WriteSnapshotToClient`；CODOL 分支调用 `CODOL_PrepareClientSnapshot` | snapshot 序列化入口 |
| `dedicated\src\codol\snapshot\codol_snapshot.c:22-41` | snapshot 段首字节 `0`、u32 serverTime、delta、flags、各段、终止字节 `5` | snapshot 明文序列化 |
| `dedicated\src\sv_snapshot.c:642-696` | `SV_SendMessageToClient`；`msg->overflowed` 检查；`SV_Netchan_Transmit(client, msg->data, msg->cursize)`；失败回滚 frame 记录 | 明文消息交给 netchan 发送 |
| `dedicated\src\sv_net_chan.c:135-149` | `SV_Netchan_Transmit`；CODOL 分支先 memcpy，再 `SV_Netchan_Encode`，再 `CODOL_NetchanSubmit`；保留调用者明文 | 加密前边界，整条 netchan 消息 |
| `dedicated\src\sv_snapshot.c:97-107` | `SV_UpdateServerCommandsToClient` 写 `0x01`、u32 seq、cstring | 可靠 server command |
| `dedicated\src\sv_snapshot.c:827-849` | `SV_EndClientSnapshot`；未 prepared 时写 `SV_WIRE_EOF` | snapshot 收尾 |

结论：

- 原生服务端有可静态定位的明文序列化和发送边界：**CONFIRMED（源码级）**。
- 实际运行时到达这些边界的字节、分支和发送结果：**NOT_OBSERVED**。
- 客户端是否接受这些原生字节：**NOT_OBSERVED**，不能由服务端源码自动推出。

---

## A.5 原生栈候选插桩点（只设计，不应用）

以下仅为后续实验候选，不构成本轮修改。

| 候选点 | 位置 | 可观察内容 | 优点 | 局限/风险 | 状态 |
|---|---|---|---|---|---|
| N-1 gamestate 明文段 | `codol_sv_state.c:141-146`，在 `msg->cursize += wire.size` 后 | 新增 gamestate 区域的起始指针、`wire.size`、首字节、完整明文 | 直接对应 `CODOL_WriteGamestate` 输出 | 需保存调用前 `msg->cursize` 才能精确取段；修改源码需另行授权 | CANDIDATE |
| N-2 snapshot 明文段 | `sv_snapshot.c:260-263`，`CODOL_PrepareClientSnapshot` 返回后 | snapshot 在 `msg` 中的偏移、长度、首字节、完整明文 | 直接对应 snapshot 准备完成点 | 精确偏移需结合调用前 `msg->cursize`/prepared 状态；当前未应用 | CANDIDATE |
| N-3 发送前整包明文 | `sv_snapshot.c:688`，`SV_Netchan_Transmit` 前后 | `msg->data`、`msg->cursize`、`client->netchan.outgoingSequence`、client state、发送返回值 | 不碰加密密钥；能证明调用者交给 netchan 的完整明文 | 是整条 netchan 消息，不自动给出内部 svc 消息边界；需与 N-1/N-2 关联 | CANDIDATE |
| N-4 加密前 netchan 明文 | `sv_net_chan.c:143-144`，`SV_Netchan_Encode` 前 | 调用者明文 `data[0..cursize)`、长度、返回值 | 精确位于加密前；可验证调用者字节未被 netchan 修改 | 仍不提供内部消息边界；高频，需要采样/开关 | CANDIDATE |
| N-5 可靠 server command | `sv_snapshot.c:97-107` | `0x01`、seq、命令字符串、消息内偏移 | 对应 `SV_WIRE_SERVERCOMMAND` | 命令文本可能敏感，需脱敏/白名单 | CANDIDATE |
| N-6 snapshot 段级收尾 | `codol_snapshot.c:22-41` | snapshot 段首字节、serverTime、delta、flags、EOF | 段级语义清楚 | 需要与 `msg` 偏移和消息边界关联；不宜只记录单个字段 | CANDIDATE |

推荐优先级：N-1 与 N-2 用于取得目标消息完整明文；N-3 用于证明实际交给发送函数的完整消息；N-5/N-6 仅作为交叉核验。所有候选都需要在实验副本上单独设计、构建、审查和授权，不得直接改原始二进制或原始目录。

---

## A.6 源码可证明与仅运行时才能验证的边界

### 源码可证明

- 当前原生 CODOL 分支实际调用的编码函数和写入顺序（既有 `09_A`，本轮复核关键行号）。
- gamestate/snapshot 首字节常量及其来源。
- `SV_SendMessageToClient` 到 `SV_Netchan_Transmit` 的调用链。
- `SV_Netchan_Transmit` 在 CODOL 分支中先复制再编码，保留调用者明文。
- `wire_tap.py` 自身 `tap()`/`bump()` 的 no-op、限流和 JSONL 写入行为。

### 仅运行时才能验证

- 实际分支是否走到目标编码路径、是否发生 overflow、是否发送成功。
- 实际发送的消息顺序、时间、长度和完整字节。
- `SV_Netchan_Encode` 后、分片后的线上字节。
- 客户端是否收到、是否进入解析器、是否无错误、是否完成状态转换。
- 插桩是否改变时序、错误处理或触发未预期交互。
- §4 若未来被移植到某个实际存在的目标，其运行时影响。

---

## A.7 本轮未做事项

- 未启动任何客户端、服务端、launcher 或未知程序。
- 未执行 `START-CODOL-SERVER.cmd` 或任何其他 `.cmd`/脚本/二进制。
- 未应用、改写或试跑 §4 diff。
- 未修改原始样本、既有报告或可运行基线。
- 未进行抓包或声称已捕获载荷。