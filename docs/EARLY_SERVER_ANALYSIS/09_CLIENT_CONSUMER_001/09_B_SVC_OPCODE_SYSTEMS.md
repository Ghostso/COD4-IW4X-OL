# 09 — B：两套 svc 编号体系的裁决

> 任务：`EARLY-SERVER-CLIENT-CONSUMER-001` 任务 B。
> 边界：**只做静态分析**。不启动客户端/服务端，不执行 `.cmd`/未知脚本，不修改原始样本与既有报告，不输出秘密材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 关键输入：
> - 服务端源码根：`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src`
> - `…\CODOL_Server\lobby\docs\protocol_map.md`（SHA-256 `A0759286DC7852D91FEBACF05E9F57ED11FB101D80BF3E56478075885FB04FE2`，53,619 B，927 行）

---

## B.0 一句话结论

- **存在两套彼此独立的 svc 编号体系**：编译期枚举 `svc_ops_e`（`net_game_conf.h:64-78`）与 CODOL 线上实值（写死在 `#ifdef CODOL_SERVER` 分支的立即数）。二者**数值不同**且**没有任何转换函数**。→ **CONFIRMED**。
- `svc_ops_e` 的全部枚举常量在 CODOL 可达路径中**只出现在 `#else` 死分支**（`sv_main.c:3956/3958/4011`、`sv_client.c:2328/2333`、`sv_snapshot.c:356`、`sv_demo.c:279`），编译时被 `#ifdef CODOL_SERVER` 排除。→ **CONFIRMED（可达性）**。
- CODOL 线上值：`gamestate=0x02`、`configstring 子流=0x03`、`serverCommand=0x01`、`EOF=0x05`、`snapshot=0x00`。→ **CONFIRMED（源码级）**。
- **snapshot 的线上 opcode**：服务端**确认写出 `0x00`**（`codol_snapshot.c:23`）；但文档侧 `protocol_map.md:334` 仍标注 "still unknown"，且**客户端期望值 UNKNOWN**。→ **服务端侧 CONFIRMED / 双端一致 UNKNOWN**。

---

## B.1 编号映射表（任务要求表）

| 编号体系 | 数值 | 定义位置 | 使用位置 | 消息语义 | 证据等级 |
|---|---|---|---|---|---|
| `svc_ops_e` 枚举 | 0 | `net_game_conf.h:65` | （CODOL 可达路径中无使用） | `svc_nop` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 1 | `net_game_conf.h:66` | `sv_main.c:3956`（死分支） | `svc_gamestate` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 2 | `net_game_conf.h:67` | `sv_main.c:3958`（死分支） | `svc_configstring` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 3 | `net_game_conf.h:68` | `sv_main.c:3990`（死分支） | `svc_baseline` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 4 | `net_game_conf.h:69` | `sv_snapshot.c:65`（死分支 `#define`） | `svc_serverCommand` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 5 | `net_game_conf.h:70` | （CODOL 可达路径中无使用） | `svc_download` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 6 | `net_game_conf.h:71` | `sv_snapshot.c:356`（死分支） | `svc_snapshot` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 7 | `net_game_conf.h:72` | `sv_main.c:4011`、`sv_client.c:2328`（死分支） | `svc_EOF` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 8 | `net_game_conf.h:73` | （CODOL 可达路径中无使用） | `svc_steamcommands` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 9 | `net_game_conf.h:74` | （CODOL 可达路径中无使用） | `svc_statscommands` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 10 | `net_game_conf.h:75` | （CODOL 可达路径中无使用） | `svc_configdata` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 11 | `net_game_conf.h:76` | （CODOL 可达路径中无使用） | `svc_configclient` | **CONFIRMED（定义）/ REFUTED（可达）** |
| `svc_ops_e` 枚举 | 12 | `net_game_conf.h:77` | （CODOL 可达路径中无使用） | `svc_acdata` | **CONFIRMED（定义）/ REFUTED（可达）** |
| **CODOL 线上实值** | **0x00** | `codol_snapshot.c:23`（`CODOL_WriteByte(m, 0)`） | `codol_sv_snapshot.c:230` → `codol_snapshot.c:8` | snapshot（每快照首字节） | **CONFIRMED（服务端写出）** |
| **CODOL 线上实值** | **0x01** | `sv_snapshot.c:61`（`#define SV_WIRE_SERVERCOMMAND 1`） | `sv_snapshot.c:103`（`MSG_WriteByte(msg, SV_WIRE_SERVERCOMMAND)`） | serverCommand | **CONFIRMED** |
| **CODOL 线上实值** | **0x02** | `codol_configstrings.c:298`（`WriteByte(2)`） | `codol_configstrings.c:288` `CODOL_WriteGamestate` | gamestate | **CONFIRMED** |
| **CODOL 线上实值** | **0x03** | `codol_configstrings.c:276`（`WriteByte(3)`） | `codol_configstrings.c:269` `CODOL_WriteConfigstrings` | configstring 子流（gamestate 内） | **CONFIRMED** |
| **CODOL 线上实值** | **0x05** | `sv_snapshot.c:62`（`#define SV_WIRE_EOF 5`）、`codol_configstrings.c:284`、`codol_configstrings.c:306`、`codol_snapshot.c:41` | 上述各函数 | EOF / 段终止 | **CONFIRMED** |
| **文档（参考实现）** | `svc_gamestate=2` | `protocol_map.md:330` | lobby kit `probe="play"` 路径 | gamestate | **STRONG_CANDIDATE（[M] 实测，非本仓库源码）** |
| **文档（参考实现）** | `configstring=3` | `protocol_map.md:331`（`CODOL_CS_OP`） | lobby kit | configstring 块 | **STRONG_CANDIDATE** |
| **文档（参考实现）** | `svc_EOF=5` | `protocol_map.md:332` | lobby kit（实测 `0x5D82BB`/`0x5D8354`） | 块终止 | **STRONG_CANDIDATE** |
| **文档（参考实现）** | `serverCommand=1` | `protocol_map.md:333` | lobby kit | serverCommand | **STRONG_CANDIDATE** |
| **文档（参考实现）** | **unknown** | `protocol_map.md:334`（`CODOL_SNAP_OP` / `CODOL_SNAP_LO..HI`） | lobby kit | snapshot | **UNKNOWN** |

> 备注：`protocol_map.md` 的 opcode 值来自 lobby kit 对**真实客户端流量**的实测（标记 `[M]`）；本仓库服务端源码的实值来自**静态阅读**。两者在 `gamestate/configstring/EOF/serverCommand` 上一致，在 `snapshot` 上不一致（源码给出 `0x00`，文档保留 unknown）。

---

## B.2 两套编号并存的证据

### B.2.1 定义位置（枚举）

`net_game_conf.h:46-53`（CODOL 端口/协议版本）与 `:64-78`（`svc_ops_e`）：

```
46: #ifdef CODOL_SERVER
47: #include "codol_wire.h"
48: #define PORT_SERVER CODOL_PORT            // 17733
49: #define PROTOCOL_VERSION ((unsigned int)CODOL_PROTOCOL)   // 187
...
64: enum svc_ops_e {
65:     svc_nop,            // 0
66:     svc_gamestate,      // 1
67:     svc_configstring,   // 2
68:     svc_baseline,       // 3
69:     svc_serverCommand,  // 4
70:     svc_download,       // 5
71:     svc_snapshot,       // 6
72:     svc_EOF,            // 7
...
78: };
```

**注意**：`CODOL_SERVER` 只改写了**端口与协议版本**，**没有改写 `svc_ops_e` 的枚举值**。因此枚举仍然保留 IW4 传统编号，与 CODOL 线上实值不匹配。

### B.2.2 可达性分析（全仓库 token 扫描，1362 个 `.c/.h/.cpp/.hpp`）

对 `svc_gamestate` / `svc_configstring` / `svc_baseline` / `svc_serverCommand` / `svc_snapshot` / `svc_EOF` 逐 token 扫描，命中文件如下（含行号）：

| token | 命中位置 | 是否 CODOL 可达 |
|---|---|---|
| `svc_gamestate` | `net_game_conf.h:66`（定义）、`sv_main.c:3956`、`sv_client.c:2333` | **否**（`#else` 死分支） |
| `svc_configstring` | `net_game_conf.h:67`（定义）、`sv_main.c:3958` | **否** |
| `svc_baseline` | `net_game_conf.h:68`（定义）、`sv_main.c:3990` | **否** |
| `svc_serverCommand` | `net_game_conf.h:69`（定义）、`sv_snapshot.c:65`（`#else` `#define`） | **否** |
| `svc_snapshot` | `net_game_conf.h:71`（定义）、`sv_snapshot.c:77`（**注释**）、`sv_snapshot.c:356`、`codol_snapshot.h:24`（**注释**） | **否**（`:356` 在 `#else` 内） |
| `svc_EOF` | `net_game_conf.h:72`（定义）、`sv_main.c:4011`、`sv_client.c:2328`、`sv_snapshot.c:66`（`#else` `#define`）、`sv_demo.c:279` | **否** |

**证据**：`sv_client.c:2295-2351` 明确以 `#ifdef CODOL_SERVER` / `#else` 分隔——CODOL 分支（`:2298`）调用 `SV_WriteGameState` 后 `return`，`#else` 分支（`:2328-2350`）才写 `svc_EOF`/`svc_gamestate`。同理 `sv_main.c:3939-3950`（CODOL `return`）与 `:3951-4013`（死分支）。

### B.2.3 无转换函数（REFUTED 假设：两套编号存在映射/转换）

对全仓库扫描 "translate/convert/map/opcode" 相关命名与 `svc_*` 交叉引用，**未发现任何把 `svc_ops_e` 常量转换为 CODOL 线上值的函数**（仅有 `db_load.cpp`、`sv_cmds.c` 中与协议无关的 `translated` 命中）。→ **两套编号之间无转换层，CONFIRMED（否定）**。

---

## B.3 自定义 opcode `2/3/5/1` 的来源与语义

`2/3/5/1` 是**任务背景中已有的观察值**（来自 `protocol_map.md` / `console_mp.log` 的实测）。逐项裁决：

| opcode | 语义 | 来源模块 / 发送路径 | 证据等级 |
|---|---|---|---|
| `0x02` | gamestate | `CODOL_WriteGamestate`（`codol_configstrings.c:288-308`，`:298` `WriteByte(2)`）；由 `SV_WriteGameState`→`CODOL_WriteServerGamestate`→`SV_SendClientGameState` 发出 | **CONFIRMED（源码）** |
| `0x03` | configstring 子流 | `CODOL_WriteConfigstrings`（`codol_configstrings.c:269-286`，`:276` `WriteByte(3)`）；**嵌在 gamestate 内**，不是顶层消息 | **CONFIRMED（源码）** |
| `0x05` | EOF / 段终止 | `sv_snapshot.c:62`、`codol_configstrings.c:284/306`、`codol_snapshot.c:41`；用于 gamestate 尾、configstring 尾、snapshot 尾 | **CONFIRMED（源码）** |
| `0x01` | serverCommand | `sv_snapshot.c:61` `#define SV_WIRE_SERVERCOMMAND 1`；写入点 `sv_snapshot.c:103`，经 `SV_UpdateServerCommandsToClient` | **CONFIRMED（源码）** |
| （snapshot） | snapshot | `codol_snapshot.c:23` `WriteByte(0)`——**实值为 `0x00`**；但客户端期望值未证 | **服务端 CONFIRMED / 双端 UNKNOWN** |

**结论**：任务背景里的 `2/3/5/1` **对应 CODOL 线上实值**（不是 `svc_ops_e`），来源为 `dedicated\src\codol\snapshot\*`（gamestate/configstring/snapshot 序列化器）+ `sv_snapshot.c`（serverCommand/EOF 宏）。**`svc_ops_e` 的编号用于编译期枚举层（传统 IW4 语义），在 CODOL 可达路径中被完全旁路。**

---

## B.4 snapshot 线上 opcode 能否由源码确定？

- **服务端侧：CONFIRMED = `0x00`。**
  `codol_snapshot.c:8` `CODOL_WriteSnapshotDeltaNumber` 第一件事是 `:22` `m->bit = 0`、`:23` `CODOL_WriteByte(m, 0)`。该函数由 `codol_sv_snapshot.c:230`（`write_server_snapshot_delta`）在**新位池起始**调用，写入位置 = `msg->data + msg->cursize`（紧跟在 serverCommand 段之后）。→ 每个 snapshot 段的**首字节为 `0x00`**。
- **文档侧：UNKNOWN。** `protocol_map.md:334` 明确写 "`svc_snapshot` = **still unknown** — pinned by `CODOL_SNAP_OP` or swept `CODOL_SNAP_LO..HI`"，且未给出实测值。`codol_snapshot.h:24` 注释虽称 "one `svc_snapshot` + EOF"，但**未给出数值**。
- **客户端期望值：UNKNOWN / INSTRUMENTATION_BLOCKED。** 客户端为 VMProtect 加壳，无符号/字符串可定位 opcode 分派（详见 `09_C`）。→ **不能由服务端源码推断客户端接受 `0x00`**。

> **谨慎结论**：服务端**确实写 `0x00`**（源码 CONFIRMED）；"这就是客户端接受的 snapshot opcode" **仍是 UNKNOWN**。若客户端按 `protocol_map.md:334` 的 `CODOL_SNAP_OP` 扫描，则 `0x00` 是否命中取决于该常量的真实取值——静态材料无法回答。

---

## B.5 哪些编号仅存在于文档 / 哪些有真实源码调用证据

| 分类 | 编号 | 说明 |
|---|---|---|
| **有真实源码调用证据** | `0x01`（serverCommand）、`0x02`（gamestate）、`0x03`（configstring）、`0x05`（EOF）、`0x00`（snapshot，服务端写出） | 均在 `#ifdef CODOL_SERVER` 可达路径中，有明确的 `MSG_WriteByte`/`WriteByte` 调用点 |
| **仅存在于文档** | `svc_gamestate=2`、`configstring=3`、`EOF=5`、`serverCommand=1`（`protocol_map.md:330-333` 的 lobby kit 实测）；`CODOL_SNAP_OP`（`:334`，无值） | 来自 lobby kit 对客户端流量的 `[M]` 实测，**不是本仓库源码**；值恰好与本仓库源码一致（除 snapshot） |
| **仅存在于枚举定义（死代码）** | `svc_ops_e` 全部 0–12 | 定义在 `net_game_conf.h:64-78`，在 CODOL 可达路径中无引用 |

---

## B.6 交叉线索：另一客户端构建（ol-mod）——REFUTED 作为直接证据

`D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\` 是**另一条客户端构建线**：

- `config\codol-game-dir.txt` 指向 `D:\codo_3.19.26.13_fresh\CoD Online`（构建 **3.19.26.13**），**不是**本轮审计客户端（`CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe`，SHA `904436480938632a…`）。
- 其 `sv_gamestate_mp.hpp:30-32` 定义 `ServerCommandSnapshot=0`、`ServerCommandGameState=3`、`ServerCommandConfigString=4`——**gamestate/configstring 与我们的服务端 `2/3` 不同**，证明**不同血缘**。
- 其注释引用的客户端 VA（`CL_ParseSnapshot 0x0046D170`、`CL_FirstSnapshot sub_515C90`、`CL_ParseServerMessage 0x0046E6A0`）**在我们客户端里反汇编为垃圾/非法流**，进一步证明二进制布局不同。

**裁决**：ol-mod **REFUTED** 作为本客户端语义的直接证据；仅可作为**结构蓝图/假设来源**（`STRONG_CANDIDATE` 级别假设，不得引用其 RVA）。

> 值得注意的**跨血缘巧合**：ol-mod `sv_snapshot_mp.cpp:10244-10246` 也写 `MSG_WriteByte(ServerCommandSnapshot)`（=0）——与本仓库 `0x00` 一致。这只是**结构性参照**，不能作为本客户端接受 `0x00` 的证据。

---

## B.7 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| `svc_ops_e` 与 CODOL 线上值数值不同 | **CONFIRMED** | `net_game_conf.h:64-78` vs `codol_configstrings.c:298`/`sv_snapshot.c:61-62` |
| 两套编号之间无转换函数 | **CONFIRMED** | 全仓库 1362 文件 token 扫描，无转换层 |
| `svc_ops_e` 常量在 CODOL 路径中不可达 | **CONFIRMED** | `sv_client.c:2295-2351`、`sv_main.c:3939-3950` 的 `#ifdef`/`#else` 结构 |
| CODOL 线上值 `1/2/3/5` 的语义 | **CONFIRMED** | 各 `MSG_WriteByte` 调用点 |
| snapshot 服务端首字节 = `0x00` | **CONFIRMED（服务端侧）** | `codol_snapshot.c:22-23` |
| 客户端期望的 snapshot opcode | **UNKNOWN** | 客户端 VMProtect；文档亦 unknown |
| ol-mod 可直接作为本客户端证据 | **REFUTED** | 构建号/哈希/反汇编均不同 |

---

## B.8 复算步骤（只读）

```powershell
$src='D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src'
# 1) 枚举定义
Get-Content -LiteralPath "$src\net_game_conf.h" | Select-Object -Skip 45 -First 35
# 2) CODOL 实值
Get-Content -LiteralPath "$src\sv_snapshot.c" | Select-Object -Skip 60 -First 8
Get-Content -LiteralPath "$src\codol\snapshot\codol_snapshot.c" | Select-Object -First 46
Get-Content -LiteralPath "$src\codol\snapshot\codol_configstrings.c" | Select-Object -Skip 268 -First 45
# 3) 可达性（#ifdef/#else）
Get-Content -LiteralPath "$src\sv_client.c" | Select-Object -Skip 2294 -First 58
Get-Content -LiteralPath "$src\sv_main.c"  | Select-Object -Skip 3938 -First 76
# 4) 文档侧
Get-Content -LiteralPath '…\CODOL_Server\lobby\docs\protocol_map.md' | Select-Object -Skip 325 -First 16
```

> 说明：本文件只裁决**编号体系**；每条消息的完整字节布局见 `09_A`，双端对应见 `09_D`。
