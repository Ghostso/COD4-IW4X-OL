# PREFLIGHT_RUN_2026-10-09 — 运行预检执行记录

本文件是**新增的阶段记录**，不覆盖原始审计记录。

## 1. 请求的四个步骤与可行性

| # | 请求的步骤 | 可行性核验结果 |
| --- | --- | --- |
| 1 | `codol-preflight.ps1` 运行预检并生成 preflight.json | **脚本原本不存在**（仓库与全盘 0 命中）→ 本次**实现了它**并实际运行，生成真实报告 |
| 2 | `pktmon start --etw -p 0 -f capture.etl` 抓包 | 工具存在，但**该命令语法在本机不适用**，且**当前进程未提权** → 无法执行（见 §4） |
| 3 | `xmake` 构建服务器 | **xmake 不存在** → 无法执行 |
| 4 | 生成 Golden（定长游戏循环 + 日志/PCAP/哈希） | 依赖 1-3 与可运行客户端/资产 → **无法执行** |

## 2. 步骤 1：preflight 工具与新发现的缺陷

### 2.1 脚本原本不存在
- `codol-preflight.ps1` 在仓库根、仓库内递归、以及 D:/E:/F:（深度 5）搜索均为 **0 命中**。
- 因此本次按任务给出的命令行**实现了该工具**（仓库根 `codol-preflight.ps1`，269 行）。
- 该工具是**非破坏性**的：只读仓库/文件系统，唯一的写入是 `-OutFile` 报告。它**不构建、不启动游戏、不启动抓包、不修改仓库或主机**。

### 2.2 运行中发现的真实缺陷（已修）
首次运行时脚本自身报错：`MaxHashBytes = 2147483648` 超出 `[int]` 上限。
- 现象: `Cannot convert value "2147483648" to type "System.Int32"`
- 修复: 参数类型改为 `[long]`
- 这条记录保留，因为它是“实际执行”而非“仅设计”的证据。

### 2.5 第二个缺陷：报告编码（已修，且是真实完整性问题）
首次生成的报告由 Windows PowerShell 5.1 的 `Set-Content -Encoding UTF8` 写出，实测:
- `preflight.json`: **BOM=true, CRLF=205**
- `preflight.local.json`: **BOM=true, CRLF=367**

两个问题:
1. **BOM** 会使报告不是严格合法的 JSON（严格解析器会拒绝）。
2. **CRLF** 与本审计目录的 `.gitattributes`（`* text eol=lf`）冲突：git 以 LF 归一化存储，而记录下来的 SHA-256 是按 CRLF 字节算的 → **fresh checkout 后哈希必然不匹配**，等于审计完整性记录失效。

修复: 脚本改为显式把 CRLF 替换为 LF，并用 `UTF8Encoding($false)` + `File::WriteAllText` 写出（无 BOM）。
修复后实测: `BOM=false, CRLF=0, validJson=true`。

### 2.3 运行 1 —— 完全按任务给出的命令行
命令: `\codol-preflight.ps1 -RepoPath . -ClientPath D:\path\to\client.exe -GamePath D:\path\to\CODOL -ExpectedClientSha256 E3823FD6...AF37B`

结果: **VERDICT = BLOCKED，9 个阻塞项**

| 检查 | 结果 |
| --- | --- |
| repository path / repo files / git HEAD / git branch | PASS（HEAD `e237e25a`，分支 `OLfinal-live`） |
| client executable exists | **FAIL**（`D:\path\to\client.exe` 是占位符，不存在） |
| game directory exists | **FAIL**（`D:\path\to\CODOL` 是占位符，不存在） |
| toolchain cl / xmake / vcpkg / cmake / ninja | **全部 FAIL**（not found） |
| vswhere / VCPKG_ROOT | **FAIL** |
| pktmon available | PASS（`C:\Windows\system32\PktMon.exe`） |

### 2.4 运行 2 —— 对**本机真实存在的**工件运行（用于量化差距）
命令: `-ClientPath D:\BaiduNetdiskDownload\codoMP_client_shipRetail.exe -GamePath D:\...\sandbox_datafix_20260929 -HashFastfiles`

结果: **VERDICT = BLOCKED，9 个阻塞项**

| 检查 | 结果 | 实际值 |
| --- | --- | --- |
| client SHA-256 匹配 | **FAIL** | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`（期望 `E3823FD6...`） |
| client file version | PASS（信息） | **FileVersion=1649370；ProductVersion=1649370；CompanyName=Activision Blizzard** |
| game main/ 目录 | PASS | present |
| fastfiles 数量 | PASS | **16 个 .ff** |
| **map fastfiles** | **FAIL** | **0 张地图 .ff** |
| fastfile 容器头 | PASS | `magic=IWff0100 version=461` |
| fastfile 总大小 | PASS | 151,330,643 bytes |
| fastfile SHA-256 清单 | PASS | 16 个已哈希 |
| toolchain | **全部 FAIL** | 同运行 1 |

## 3. FileVersion=1649370 线索的静态核验（重要，且**未**通过）

运行 2 发现本机客户端 `FileVersion=1649370`，而 `tools/runtime/CodolGame.py:22-27` 明确写着**两个受支持的构建**:
- 3.3.3.3 → `codoMP_client_shipRetail.exe`
- OLfinal → `out.exe`（build 1649370），是**去掉了 TenProtect/TCLS 的 unpacked 客户端**

因此我**没有**仅凭 FileVersion 就认定匹配，而是做了字节级静态核验。

### 3.1 核验点
`src/game_server/ClientProcessPatches.cpp:207-211` 记录了 build 1649370 的固定字节:

- RVA `0x8371A` 必须为 `83 7C 24 08 01 0F 94 C0`（即 `cmp [esp+8],1 ; sete al`）

### 3.2 本机客户端 PE 分析（直接读取文件）
| 项 | 值 |
| --- | --- |
| SHA-256 | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| 大小 | 7,841,344 bytes |
| Machine | 0x14C（I386 x86） |
| Optional magic | 0x10B（PE32） |
| ImageBase / SizeOfImage | 0x400000 / 0xE659000 |
| TimeDateStamp | 0x6096930A（2021-05-08） |
| 节区 | **`.tp3` ×5、`.tvm0` ×1**（TenProtect/Tencent VM 加壳特征） |

### 3.3 结果: **不匹配**
| RVA | 期望 | 实际 |
| --- | --- | --- |
| `0x8371A` | `837C2408010F94C0` | `00D945108B4D088B` → **MISMATCH** |

(另附探针: `0x0FEA20`→`03C1E006505181C2`、`0x09CF30`→`00B045CC8D560452`、`0x09D3D0`→`019000123C2309D1`、`0x09DA10`→`FFE826270012023E`，均非 OLMod 记录的期望前缀。)

### 3.4 结论与**必须保留的不确定性**
- 本机客户端是**加壳镜像**（`.tp3`/`.tvm0`，第三节点 VSize 0xdbb1cc0 而 RawSize 仅 0x62000），而 OLMod 目标的 `out.exe` 是 **unpacked** 镜像。
- 因此**静态文件字节核验失败**是预期的：加壳镜像不会在文件里保留目标 RVA 的原始字节。
- **关键限定**: 由于插件按**内存镜像**取址（`GetModuleHandleW` + RVA），运行时解壳后是否与 1649370 期望一致，**当前为 UNKNOWN，不能仅凭静态失败就判定 REFUTED**。要判定必须在真实加载后核对内存字节。
- 但就任务要求而言，**必须用 SHA-256 精确匹配确认身份**：本机没有任何文件匹配 `E3823FD6...`（41 份副本、2 个构建），也没有 `out.exe`。
- 因此 B1 结论维持 **`BLOCKED_NO_MATCHING_CLIENT`**，并新增一条精确说明（见 §6）。

## 4. 步骤 2：pktmon 抓包命令在本机不可用（含语法更正）

### 4.1 工具与驱动状态
| 项 | 结果 |
| --- | --- |
| pktmon 可执行 | `C:\Windows\system32\PktMon.exe`（存在） |
| `pktmon.sys` | `C:\Windows\System32\drivers\pktmon.sys`（存在，131,560 bytes） |
| 服务 `PktMon` | 存在，**STATE = STOPPED** |
| `pktmon filter list` | **失败**: “无法与 PktMon 驱动程序通信。系统找不到指定的文件。” |
| 当前进程是否提权 | **False**（不是管理员） |

=> 启动抓包需要管理员权限（并会加载 PktMon 驱动）。**当前会话未提权，无法执行**。

### 4.2 任务给出的命令句法在本机**不适用**（需要更正）
任务给的: `pktmon start --etw -p 0 -f capture.etl`

本机 pktmon 的帮助文本显示:
- **没有 `--etw`**；数据包捕获用 `--capture`（`-c`），事件提供程序用 `--trace`（`-t`）。
- **`-p` 是 `--provider <name>`（事件提供程序）**，不是 packet size。所以 `-p 0` 会被当作 provider 名字 “0”。
- **没有 `-f`**；文件名是 `--file-name <name>`。
- 整包捕获是 `--pkt-size 0`（0 = 记录完整数据包，默认 128 字节）。

**更正后的等效命令**（需管理员 PowerShell）:
```
pktmon filter add CODOL -t UDP -p 28960
pktmon start --capture --pkt-size 0 --file-name capture.etl --comp nics
# ... 运行对局 ...
pktmon stop
pktmon etl2pcap capture.etl --out capture.pcapng
```
说明:
- `--comp nics` 只抓网卡层；回环（loopback）流量在 Windows 上不经 NIC，**若客户端与 dedicated 都在本机回环通信，抓包可能看不到**，这是本方案的一个真实局限，必须在 Golden 记录中如实标注。
- dedicated 的玩法 UDP 端口默认 28960（`sv_network_mp.hpp:43`），实际端口来自 session descriptor，因此筛选器端口应在运行后按实际值修正。

## 5. 步骤 3 / 4：构建与 Golden

- **步骤 3（xmake 构建）**: xmake / cl / vswhere / vcpkg / cmake / ninja **全部不存在** → 无法构建。`BUILD_CONFIRMED` 不成立。
- **步骤 4（生成 Golden）**: 依赖步骤 1-3 与可运行的客户端 + 含地图的资产集。三者均未满足 → **无法执行**。按 GOLDEN_COPY_SPEC.md 的硬要求，**不生成任何伪造的 Golden 或 summary**。

## 6. 最小验收标准的当前达成情况

| 标准 | 状态 | 依据 |
| --- | --- | --- |
| 客户端可通过战斗服务器登录握手 | **未达成 / INSTRUMENTATION_BLOCKED** | 无匹配客户端、无资产、无构建物 |
| gamestate accepted 成功，服务器生成游戏世界 | **未达成 / NOT_OBSERVED** | 同上 |
| 客户端世界加载完成并接收固定频率（≥10Hz）快照 | **未达成 / NOT_OBSERVED** | 同上 |
| （可选）两客户端同局持续交互 | **未达成 / NOT_OBSERVED** | 同上 |

附加说明（避免混淆）: `sv_client_mp.cpp:1424-1426` 的快照节拍是源码内硬编码 50 ms（20 Hz），且 `:1418-1421` 对 **LAN/loopback peer 直接旁路**。因此“≥10Hz”这一标准在本地回环测试下**不能**用来说明已恢复 CODOL 的远程速率契约。

## 7. 本次产生的工件与哈希

| 文件 | SHA-256 |
| --- | --- |
| `preflight/preflight.json` | `CA2AB9DCEE0DAD2F81A69CD58AB5620FCB597C4F7234FFC01B2CDA8348B91D12` |
| `preflight/preflight.local.json` | `C7B3A35E89679D8D0F918A0F938BF9C9B4534F5C8B29DBF7E28C57E2EAC00555` |

说明: 任务给出的命令会在**当前目录**生成 `preflight.json`（脚本默认 `-OutFile preflight.json`）。两次运行的结果已归档到本目录 `preflight/` 下，仓库根不再保留散落副本。

## 8. 结论

四个步骤中，**只有 preflight 这一步是可执行的**，而且它的脚本原本不存在——本次补齐并实际运行，产出的结论是 **BLOCKED**。
pktmon 工具存在但命令句法需更正且需要提权；xmake 与整个工具链不存在；Golden 因此无法生成。
**未产生任何伪造的成功记录。** 所有未达成的项均如实标注为 INSTRUMENTATION_BLOCKED / NOT_OBSERVED。
