# CODOL 3.19 离线化会话全记录（2026-10-20）

> 本文件是本轮对话的完整工作记录：目标、每一次实验、每一条证据、每一个结论
> （含被推翻的结论）、当前阻塞与后续可执行路线。不做删减式摘要。

---

## 0. 本轮目标

1. 通过外部方式调用 CODOL 3.19 客户端，创建一个**可游玩的本地原生对局**。
2. 彻底移除 ACE / 反作弊保护链。
3. 途中被提出并执行：验证"未加载 ACE 内核驱动时能否进入完整大厅"。
4. 会话后期转向：**深度分析并尝试剥离全部加密/保护链**。

约束（来自 AGENTS.md 与用户指令）：

- 不改 `REF_LOBBY_KIT`、`CODOL_VERIFIED_GOLDEN_20261019` 等受保护基线。
- 单次启动只创建一个客户端，不自动重跑。
- 实验产物只写在 `run_codol_001\runs\<RUN_ID>\`。

---

## 1. 时间线总览（2026-10-20）

| 时间 | 事件 | 结果 |
|---|---|---|
| 17:07–17:20 | `FULL_CHAIN_20261020_170712` 完整链 | **进入完整大厅**（Auth 200 + Lobby 52 条消息），17:20:08 断开 |
| 18:03 | 现场取证 | 确认断开由 `nt10.py --secs 300` 到点 `taskkill` 引起 |
| 18:21–18:50 | 6 轮"外部注入 devmap"实验 | 全部失败，暴露 IIPS 弹窗与投递错误 |
| 20:09–20:13 | `NATIVE_MATCH_PROBE_20261020_1900` | 沙箱路径写错，客户端未拉起 |
| 20:22 | `LOBBY_REPRO_20261020_2015` | 弹窗 `初始化IIPS错误：8189fec`，PID 22136 |
| 20:35 | `LOBBY_REPRO_E236_20261020_2030` | 换 `iips.dll` 为 E2367C48，**仍弹窗**，PID 13944 |
| 20:40–20:42 | 手工启动 `IIPSHostApp.exe` | Host 进程本身可启动，但不写 `HostPid`、不建管道 |
| 21:10 | `IIPS_INIT_PATCH_20261020_2055` | 挂起期打补丁失败（未解壳），PID 8788，TCLS 门禁弹窗 |
| 21:15 | `IIPS_INIT_PATCH_20261020_2120` | 补丁全部命中，**仍弹 8189fec**，PID 19468，退出码 0xFFFFFFFF |
| 21:43 | 原文件备份 | `_BACKUP_ORIGINAL_20261020_214323` |
| 21:45–22:00 | 静态剥离分析 | 推翻"AP32 压缩"结论，确认真实形态 |
| 22:11 | 本文档 | 汇总 |

---

## 2. 完整对话记录（按回合）

### 2.1 接手与"不要推进"

- 用户要求先接手项目、不推进。
- 随后取消"启动链"方向，明确唯一任务是**通过外部方式创建可游玩的原生对局**。

### 2.2 第一次尝试与用户反馈循环

用户逐轮反馈：

"初始化iips错误" → "要随时注意报错弹窗" → "警告码3" → "试试1" →
"我什么都没看到" → "致命错误，你自己不看内存的吗" →
"任务目标是直接调用引擎创建原生对局，这是不需要大厅的"。

此处确立关键原则：**必须全程盯内存与弹窗，报错第一轮就要抓到准确基址**。

### 2.3 参考报告与版本讨论

- 用户提供 `CODOL2697-离线改造工作报告.md`。
- 讨论 3.19 与 2.6.9.7：2.6.9.7 是阉割版、代差过大；3.19 反作弊更敏感。
- 用户要求验证"去除 ACE 的可能性"，并追问"能否彻底移除"。

### 2.4 独立启动客户端构想

- 用户问：能否参考旧版手册提到的客户端，结合 3.19 直接写独立启动客户端。
- 明确要求：完全移除 ACE 组件；1:1 参考启动器但移除整个 ACE；
  目标引擎应为 IW4；双击直接启动。
- 用户提供 IW6 引擎的原生参考：`D:\BaiduNetdiskDownload\使命召唤OL\COD8`。
- 用户提到可参考开源项目 IW4X。

### 2.5 三补丁评估（用户提供）

用户给出的深度评估：

| # | 地址 | 原始字节 | 补丁字节 | 保护模块 | 失败后果 |
|---|---|---|---|---|---|
| 1 | `0x77F6E8` | `80 3D...` 14B | `E9 3A 00 00 00` + 9×`90` | TCLS 启动门禁 | 致命错误弹窗 |
| 2 | `0x64278E` | `0F 84 C6 00 00 00` | `E9 01 00 00 00 90` | TerSafe → ACE | `WIN_ANTIBOT_CREATE_OBJ_ERROR` |
| 3 | `0x65A457` | `74 72` | `EB 72` | IIPS | `WIN_IIPS_DLL_ERROR` |

评估要点：

- TenProxy.dll 加载失败返回 0，游戏继续。
- CrossShell 加载失败只设错误码，58 个 xref 全部 null-check。
- ACE 驱动不是客户端直接加载，是 `TerSafe.dll → ACE-DRV32.dll → 内核驱动` 链式加载。
- `enable_iips` 不控制 DLL 加载；`0x65A761` 无条件调用 IIPS 加载函数。
- 结论：彻底移除 ACE = 3 个运行时补丁 + 文件重命名（共 22 字节）。

### 2.6 完整大厅成功与会话中断

- 用户："看到了完整大厅，但现在闪退了"。
- 前序摘要记录了 `FULL_CHAIN_20261020_170712` 成功进入大厅。

### 2.7 闪退归因（本轮首要纠正）

取证结论：

- `nt10.py` 在 `--secs 300` 到期后记录 `game 仍在运行 (300s)`，
  然后在 `finally` 中执行 `taskkill /F /PID`。
- Lobby 日志 17:20:03 收到最后一条 `service=71 task=20`，
  17:20:08 出现 `ConnectionResetError(10054)`。
- 时间差 5 秒，与强杀时序完全吻合。
- 17:20 前后**没有** WER / Application Error 记录，也没有新 `.dmp`。

结论：**这轮不是引擎崩溃，是监控到期强杀**。`71/20` 只是未映射任务，不能定罪。

### 2.8 "外部注入 devmap"六轮实验

试图在大厅就绪后通过外部线程投递 `devmap mp_firingrange`：

| RUN | PID | 现象 |
|---|---|---|
| `..._1815` | — | 沙箱路径错误，未进入注入块 |
| `..._1816` | — | 同上，PermissionError |
| `..._1817` | — | 脚本缩进错误，跳过注入块 |
| `..._1818` | — | 提权代理离线，ConnectionRefused |
| `..._1819` | 13212 | 进入注入流程，但弹 `8189fec` |
| `..._1821` | 19604 | 同上，弹 `8189fec` |
| `..._1822` | 19736 | 同上，弹 `8189fec` |

共同现象：

- `[0x333A00C] → 0x80FA0DC`，`[+0xC] = 1`
- 窗口标题 `致命错误`，正文 `初始化IIPS错误：8189fec`
- `devmap_queued` 返回线程码 `0xFFFFFFFF`（4294967295）
- 命令缓冲区 `0x7658D80` 内容全 0，未变化
- UDP 28960 上只有本地 `battle_server.py`，不是客户端

结论：`devmap` 从未真正执行；`0x4F6A90` 的调用约定/时机也不成立。

### 2.9 IIPS 复现与单变量实验

**背景存档 `HANDOFF_20260927_IIPS_GATE_RESOLVED.md` 的关键事实：**

- `enable_iips=1` → 启动 `IIPSHostApp.exe` → 载入 `iips.dll` / `ifs2.dll` → 真实 `/auth/`。
- `enable_iips=0` → 不启动 Host，无网络层，多数静默超时。
- 可用组合使用 `iips.dll` 哈希 `E2367C48…`；原始件是 `72DD…`。

**本轮实测：**

| RUN | iips.dll | 结果 |
|---|---|---|
| `LOBBY_REPRO_20261020_2015` | 72DD（原始） | 8189fec，PID 22136 |
| `LOBBY_REPRO_E236_20261020_2030` | E2367C48（已换） | **仍 8189fec**，PID 13944 |

因此：**IIPS 版本不是唯一原因**。

### 2.10 手工验证 IIPSHostApp

- `IIPSHostApp.exe /mode iipslaunch` 可启动，CPU 3.5s，无窗口。
- `IIPS\HostPid` 保持旧值 `20128`，未更新。
- 未创建 IIPS 命名管道。
- `TenioLog` 只产生图片加载错误（路径 `IIPS\\TPFUI` 双反斜杠）。
- 无参数启动时退出码为 0。

结论：Host 程序本身没坏，但"初始化 → 建管道 → 写 HostPid"没有完成。

### 2.11 挂起启动 + 补丁时序实验

**实验 2055（错误时序）：**

- 用 `CreateProcessW(..., CREATE_SUSPENDED)` 创建 PID 8788。
- 在恢复线程前直接写代码段：
  - `0x77F6E8` 读到 `0C CC FF FF …`（与已知 `80 3D…` 不同）
  - `0x65A457` 读到 `FE D9`（与已知 `0F 84` 不同）
  - `0x65A4B5` 读到 `0F 8C 22 00 AA 8B 4D F8`，不匹配
- 恢复后弹窗变为 TCLS 门禁：`请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。`
- 约 59 秒退出，退出码 0。

结论：**代码段在启动时仍是加密态，先写后恢复必然写错位置**。

**实验 2120（正确时序）：**

- 创建 PID 19468，恢复线程。
- t=3.938s 命中解壳门 `0x77F6EF` 并置 `EB`。
- t=3.938s 解壳确认：`0x41CB40` = `55 8B EC 81 EC 64 01 00 00`。
- 随后写补丁并回读：
  - `0x77F6E8` 原 `80 3D 3B 41 49 08 00 EB 36…` → `E9 3A 00 00 00 + 9×90`
  - `0x65A457` 原 `0F 84` → `EB 72`
  - `0x65A4B5` 原 `81 FE 26 00 00 60 74 28` → `E9 2B 00 00 00 90 90 90`
- 结果：**仍然弹 8189fec**，`state_ready=1`，无 3074/28960 连接。
- 116.7 秒后退出，退出码 `0xFFFFFFFF`。

结论：`0x65A4B5` 不是 `8189fec` 的实际分支，或者 IIPS 错误码在别处写入后直接弹窗。

### 2.12 用户判断与立项

- 用户："这证明并未完全剥离加密"。
- 用户："重新进行深度分析，尝试剥离全部加密"。
- 用户："原文件做个备份，然后就去干吧"。
- 用户追问："`.tvm0` 密钥 之前的逆向文件没有嘛？"
- 用户最后要求：记录全部成果与详细对话，汇总成完整文档。

---

## 3. 关键基址与字节（本轮实测）

### 3.1 客户端

```
客户端             codoMP_client_shipRetail.exe
SHA-256            36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
大小               7,841,344 字节
ImageBase          0x00400000
入口 RVA           0x0E5DC690
TimeDateStamp      0x6096930A
SizeOfImage        0x0E659000
```

### 3.2 门禁与补丁点

```
TCLS 门禁          0x0077F6E8   80 3D … 14B            → E9 3A 00 00 00 + 9×90
解壳门             0x0077F6EF   75 → EB（启动窗口内）
TerSafe→ACE        0x0064278E   0F 84 C6 00 00 00      → E9 01 00 00 00 90
IIPS DLL 加载门    0x0065A457   0F 84                  → EB 72
IIPS 初始化比较    0x0065A4B5   81 FE 26 00 00 60 74 28 → E9 2B 00 00 00 90 90 90
IIPS 报错入口      0x0065A5D5   推 0x00DC9408（WIN_IIPS_INIT_ERROR）
解壳探针           0x0041CB40   55 8B EC 81 EC 64 01 00 00
```

### 3.3 运行时状态

```
场景全局           0x08269774
游戏状态指针       0x333A00C → 0x080FA0DC，[+0xC] = 1
命令缓冲区         0x7658D80（本轮始终为 0）
连接状态           0x76446B0
Cbuf 执行入口候选  0x004F6A90（2 参数：char*, int localClient）
Com_Frame          0x004FEA20
```

### 3.4 本轮新增结论：局部函数事实

- `0x4F6A90` 不是"只追加文本"的 Cbuf_AddText，而是包含解析与执行的路径。
- `0x65A457` 之后，`0x65A4A2` 才调用 IIPS 初始化；只有返回 `0x60000026` 被容忍。
- 弹窗路径 `0x65A5CB → 0x65A5D5` 才是 `WIN_IIPS_INIT_ERROR` 的落点。

---

## 4. 静态分析成果（会话后期）

### 4.1 主 EXE 节表（磁盘实测）

| # | 名称 | RVA | VS | Raw | RawSize | 熵 | 判定 |
|---|---|---|---|---|---|---|---|
| 1 | .tp3 | 0x1000 | 0x8A689A | 0x1000 | 0x593000 | 7.14 | 明文 x86（2387 处 `55 8B EC`） |
| 2 | .tp3 | 0x8A8000 | 0x16DA70 | 0x594000 | 0x16E000 | 5.51 | 指针/数据 |
| 3 | .tp3 | 0xA16000 | 0xDBB1CC0 | 0x702000 | 0x62000 | 4.51 | 数据（大 BSS 尾） |
| 4 | .tp3 | 0xE5C8000 | 0x31 | 0x764000 | 0x1000 | 0 | 空 |
| 5 | .tp3 | 0xE5C9000 | 0x9228 | 0x765000 | 0xA000 | 5.71 | 数据 |
| 6 | .tvm0 | 0xE5D3000 | 0x4000 | 0x76F000 | 0x2000 | 6.29 | 小段 |
| 7 | .tp3 | 0xE5D7000 | 0x82000 | 0x771000 | 0x6000 | **7.34** | **高熵壳层，含入口** |

### 4.2 导入/导出/重定位

```
导入表   仅 1 项：codoMP_client_shipRetailBase.dll!ordinal_1
IAT      0x0E9DC665
入口桩   0x0E5DC690: FF 15 65 C6 9D 0E → jmp dword ptr [0x0E9DC665]
导出表   无
重定位   无
TLS      RVA 0x9E8EB8，回调表为空
```

### 4.3 Base.dll

```
文件      codoMP_client_shipRetailBase.dll
SHA-256   EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20
大小      60,327,992 字节
入口 RVA  0x149C  → jmp 0x11AA13B0（.tvm0 内）
导出 1    0x1D6582C → push imm; jmp 0x11F27FDC（.tvm0 内）
导出 2    0x203D4F7
导出 3    0x1AA13B0
```

节表熵值：

```
.text    H=6.994
.rdata   H=4.903
.data    H=2.162
.tls     H=7.532   （磁盘密文，运行时为代码）
.tvm0    H=7.023   （31 MB 高熵）
```

### 4.4 纠正：本客户端不存在 AP32 压缩层

- 全文件中 `AP32` 标记出现 **0** 次。
- 首节 `0x1000` 处直接是明文代码 `55 8B EC 83 EC 50 …`。
- E06 报告（`E06_TVM0_STATIC_DECODE_001`）的 AP32 结论源自另一个版本样本，
  **不能套用到本 3.19 客户端**。

### 4.5 `.tvm0` 密钥问题（用户直接提问）

历史文件 `SUBAGENT_VM_ISA.md` 的原文结论：

> 「AES key 的静态装载点：UNKNOWN。密钥是运行时参数，不在磁盘镜像里；
> `.tvm0` VM ISA：UNKNOWN / 未证实存在。」

同文件还记录：

- `.tls` 磁盘↔运行时是**按块变化的 keystream**，不是固定 XOR。
- 客户端内嵌 OpenSSL 0.9.8zg 与 1.1.0k，含完整 AES 表。
- key-expansion 强候选：`.text` RVA `0x32090E / 0x320A48 / 0x320BAE`（xref rcon 表）。
- AES 轮函数：RVA `0x3218EB` 一带。
- AES key 的装载调用者：`UNKNOWN`。

因此：**没有现成 `.tvm0` 密钥**；密钥只能在运行期抓。

### 4.6 身份门禁（unknown executable image）

源码位置：`_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.hpp`

```
ExpectedTimestamp = 0x6096930A
ExpectedImageSize = 0x0E5D6000
```

`ClientProcessPatches.cpp:550` 与 `EngineBindings.cpp:3663` 都做同样比较；
不匹配时 `backend\Appmain.cpp:28` 记录
`Refused to apply CODOL startup patches to an unknown executable image.`。

本客户端实测：

```
TimeDateStamp = 0x6096930A  （与期望一致）
SizeOfImage   = 0x0E659000  （比期望大 0x80000）
```

差值 `0x80000` 正好等于末节 0x82000 虚拟空间的整数对齐差。

### 4.7 离线候选镜像（已生成，未启用）

| 文件 | 大小 | SHA-256 | 说明 |
|---|---|---|---|
| `work\candidate_no_guard.exe` | 7,802,880 | `05C0A19E…86BB` | 直接截掉末节，`SizeOfImage=0xE5D7000` |
| `work\candidate_stub.exe` | 7,806,976 | `6728AF05…74A8` | 截掉末节 + 空引导节，`SizeOfImage=0xE5D8000` |

两者都**未验证可运行**；`candidate_no_guard.exe` 还会丢失导入桩。

---

## 5. 备份与文件清单

### 5.1 原文件备份

```
D:\BaiduNetdiskDownload\使命召唤OL\_BACKUP_ORIGINAL_20261020_214323\codoMP_client_shipRetail.exe
大小      7,841,344
SHA-256   36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
```

备份与原文件哈希一致；正式文件未被覆盖。

### 5.2 本轮新增脚本

```
STRIP_PROTECTION_001\unpack_msvc.py             枚举 AP32（本版本 0 命中）
STRIP_PROTECTION_001\build_candidate.py         生成截断候选镜像
STRIP_PROTECTION_001\build_stub_candidate.py    生成带空引导节的候选镜像
run_codol_001\runs\...\run_live_match_once.py   外部注入 devmap 的实验脚本
run_codol_001\runs\...\run_probe.py             大厅复现探针
run_codol_001\runs\...\run_suspended_init_patch.py  挂起启动 + 补丁时序实验
```

### 5.3 本轮运行目录

```
FULL_CHAIN_20261020_170712            完整大厅基线
LIVE_MATCH_INJECT_20261020_1815..1822 外部注入实验
NATIVE_MATCH_PROBE_20261020_1900      路径错误，未拉起
LOBBY_REPRO_20261020_2015             iips 72DD 复现
LOBBY_REPRO_E236_20261020_2030        iips E2367C48 复现
IIPS_FALLBACK_TEST_20261020_2050      未执行
IIPS_INIT_PATCH_20261020_2055         错误时序
IIPS_INIT_PATCH_20261020_2120         正确时序
```

---

## 6. 结论汇总（含被推翻的判断）

### 6.1 已被证据推翻的判断

| 原判断 | 实际情况 | 依据 |
|---|---|---|
| 17:20 闪退是引擎崩溃 | 是 `nt10.py` 到期强杀 | 300s 记录 + 5 秒后 10054 + 无 WER |
| `devmap` 已成功投递 | 线程返回 0xFFFFFFFF，缓冲未变 | `events.jsonl` + 命令缓冲区全 0 |
| `0x4F6A90` 是 Cbuf_AddText | 是包含解析与执行的复合路径 | 反汇编 |
| 只要补 `0x65A457` 就能绕过 IIPS | 仍弹 8189fec | 实验 2120 |
| 改 `0x65A4B5` 就能消掉 8189fec | 仍弹，无效果 | 实验 2120 |
| 换 `iips.dll` 到 E2367C48 可修复 | 仍弹 | 实验 2030 |
| 主 EXE 由 AP32 压缩保护 | 本版本 0 处 AP32，首节为明文 | 全文件扫描 + 熵 |
| 改 `SizeOfImage` 即可通过门禁 | 截断后为 0xE5D7000，仍差 0x1000 | 候选镜像实测 |

### 6.2 当前仍然成立的事实

1. 未加载 ACE 内核驱动时，客户端**可以**进入完整大厅（17:07 那轮）。
2. 内核驱动状态：`ACE-BASE`、`ACE-GAME`、`TesSafe` 均为 Stopped。
3. 用户态保护文件仍在：`ACE-DRV32.dll`、`ace-ats32.dll`、`TerSafe.dll`。
4. 3.19 客户端引擎主体在 Base.dll，入口与导出都跳进 `.tvm0`。
5. `.tvm0` 与 `.tls` 是高熵保护区，无法静态线性反汇编。
6. 身份门禁只比较 `TimeDateStamp` 与 `SizeOfImage` 两个值。

### 6.3 精确阻塞点

**大厅/对局线**：

`nt10.py` 那套 4 个大厅补丁 + IIPS 初始化是进大厅的前置；
当前 `8189fec` 说明 IIPS 初始化在 `iips.dll` 内部失败，
而不是游戏侧调用被门禁拦截。

**剥离线**：

Base.dll 的 DllMain 与导出 1 都跳进 `.tvm0`；
`.tvm0` 无静态密钥、无已知 ISA；
因此"剥离全部加密"必须先取得运行期解密后的镜像或密钥。

---

## 7. 后续可执行路线（按可行性排序）

### 路线 A：运行期抓 `.tls` / `.tvm0` 解密材料（推荐）

1. 在 `Base.dll + 0x32090E / 0x320A48 / 0x320BAE` 下断，记录 key-expansion 入参。
2. 在 `.tls` 解密前后做内存差分，取 keystream 或明文页。
3. 用 `engine_dump.py` 的现有能力抓运行时镜像，避免静态猜测。
4. 验收：解出的 `.tls` 页能被 capstone 正常反汇编，且与磁盘字节差异可解释。

### 路线 B：先完成本地原生对局（回到原始目标）

1. 复用 `FULL_CHAIN_20261020_170712` 的已验证大厅链。
2. 只把监控时长拉长（`--secs`），不触发到期强杀。
3. 在大厅就绪后，用**正确的** Cbuf 入口做一次性投递，并记录线程返回码与缓冲区变化。
4. 验收：28960 由客户端 PID 持有，且能产生对局状态。

### 路线 C：镜像级剥离（风险最高，暂缓）

1. 先把 Base.dll 的 `.tvm0` 与 `.tls` 还原为明文。
2. 再把主 EXE 末节替换为最小引导段。
3. 验收：`AlwaysofflineRe` 不再报 `unknown executable image`。

在路线 A 取得密钥/明文之前，路线 C 不可执行。

---

## 8. 复现命令

```powershell
# 1. 校验原文件
Get-FileHash -Algorithm SHA256 `
  'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe'

# 2. 正确时序的 IIPS 补丁实验
python -X utf8 `
  'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\IIPS_INIT_PATCH_20261020_2120\run_suspended_init_patch.py'

# 3. 生成离线候选镜像（不改正式文件）
python -X utf8 'D:\BaiduNetdiskDownload\使命召唤OL\STRIP_PROTECTION_001\build_candidate.py'
```

---

## 9. 证据索引

| 证据 | 路径 |
|---|---|
| 完整大厅基线 | `run_codol_001\runs\FULL_CHAIN_20261020_170712\lobby_evidence.txt` |
| 大厅服务端日志 | `REF_LOBBY_KIT\lobby_srv.log` |
| Auth 日志 | `REF_LOBBY_KIT\auth3074.log` |
| IIPS 原理 | `backup_reverse_engineering\CODOLServer\IIPS_PIPELINE_FULL_REVERSE.md` |
| IIPS 启动闸门 | `backup_reverse_engineering\CODOLServer\HANDOFF_20260927_IIPS_GATE_RESOLVED.md` |
| `.tvm0` 与密钥 | `backup_reverse_engineering\CODOLServer\SUBAGENT_VM_ISA.md` |
| 身份门禁源码 | `_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.hpp` |
| 拒绝补丁日志 | `_e1_regression\ol-mod-olfinal\src\backend\Appmain.cpp:28` |
| 候选镜像清单 | `STRIP_PROTECTION_001\logs\candidate.json` |
| 原文件备份 | `_BACKUP_ORIGINAL_20261020_214323\codoMP_client_shipRetail.exe` |

---

*文档生成时间：2026-10-20 22:11（Asia/Shanghai）*
