# CODOL Historical Server Model — 第一阶段证据报告

日期：2026-09-28
性质：**考古与协议重建第一阶段**。本文只做证据重建，不实现服务器。

---

## 0. 本报告的纪律声明

本报告遵守任务给定的证据纪律：

```text
已有资料 → 重新定位 → 重新分析 → 独立验证 → 建立证据链 → 寻找反证 → 确认/修正/推翻
```

具体执行方式：

* 目录中所有既有 `CODOL_EX*.md` / `ICH*.md` / `RESTORE*.md` / `GDP_*.md` 等
  **只作为线索索引**，不作为证据继承。
* 所有结论都重新回到 **客户端本体的原始字节**（磁盘 EXE / 运行期明文镜像 / 真实运行日志）复核。
* 每一条结论给出原始证据（地址、镜像、SHA-256、xref、数据流），并给出反证与新的置信度。
* `Confidence` 只使用 `CONFIRMED / LIKELY / UNKNOWN / REFUTED`。
* 无法证明的一律进 `UNKNOWN`，不自行补全。

### 本报告新增的可复核产物

```text
分析/00_baseline_module_hashes.csv      客户端模块 SHA-256 基线
分析/01_string_anchors.csv              字符串锚点 + 4 字节引用
分析/02_runtime_xrefs.json              运行期镜像全代码段 xref 结果
分析/baseline_hash.py / pe_probe.py / strdump.py / endpoint_arch.py
分析/xrefs.py / dataflow.py / dis_va.py / constants.py / tdr_parse.py
```

---

## 1. 版本与证据基线（必填项）

### 1.1 客户端主模块

| 项目 | 值 |
|---|---|
| 文件 | `COD OL\codoMP_client_shipRetail.exe` |
| 大小 | 7,841,344 B |
| SHA-256 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |
| 映像基址 | `0x00400000` |
| EntryPoint RVA | `0x0E5DC690` |
| 节区 | 全部名为 `.tp3`（6 个）+ `.tvm0`（1 个） |

关键节区：

```text
.tp3  VA=0x00401000  VS=0x008A689A  RAW=0x00001000  RSize=0x00593000  flags=0x60000020
.tp3  VA=0x00CA8000  VS=0x0016DA70  RAW=0x00594000  RSize=0x0016E000  flags=0x40000040
.tp3  VA=0x00E16000  VS=0x0DBB1CC0  RAW=0x00702000  RSize=0x00062000  flags=0xC0000040
.tvm0 VA=0x0E9D3000  VS=0x00004000  RAW=0x0076F000  RSize=0x00002000  flags=0x60000020
```

### 1.2 磁盘代码是密文（重新验证结果：CONFIRMED）

在磁盘 EXE 上按 VA 取字节：

| VA | 磁盘字节 | 是否可解析为指令 |
|---|---|---|
| `0x004FCEE0` | `43 03 21 d0 7f 7a 00 15 54 ed 43 01 33 01 02 45` | 否 |
| `0x0077EE40` | `17 c8 67 00 10 c8 7c 0e 50 45 a8 d8 65 a0 cb 00` | 否 |
| `0x00808650` | `f4 53 57 8b ce e8 8a 73 fd ff 39 78 68 75 10 8d` | 否 |

对比运行期明文镜像同地址：

| VA | 运行期字节 |
|---|---|
| `0x004FCEE0` | `55 8b ec 81 ec 34 04 00 00 a1 40 f2 e3 00 33 c5` (`push ebp; mov ebp,esp; sub esp,0x434`) |
| `0x0077EE40` | `55 8b ec 83 e4 f8 81 ec 8c 02 00 00` (`push ebp; mov ebp,esp; and esp,-8; sub esp,0x28c`) |
| `0x00808650` | `55 8b ec 83 ec 08 53 56 e8 93 12 fe ff` |

**结论：磁盘 `.tp3` 代码段是密文，任何"直接反汇编磁盘 EXE 代码段"的结论都不成立。**
旧的"运行期镜像"说法本身需要重新验证 —— 见 1.3。

### 1.3 历史"运行期镜像"的重新验证（重要修正：REFUTED 大部分）

目录里存在两份被当作"运行期明文镜像"的全镜像 dump：

| 镜像 | 大小 | 非零字节 | 与磁盘 EXE 的关系 | 判定 |
|---|---|---|---|---|
| `CODOLServer/_fullimage/run1/fullimage/image_best.bin` | 0xA65000 | **0** | — | **无效（全零）** |
| `CODOLServer/_fullimage/run2/fullimage/image_best.bin` | 0xA65000 | 6,439,332 | **与磁盘 EXE 逐字节相同** | **REFUTED：未解密，不能作为代码证据** |
| `CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin` | 0xA65000 | 9,354,801 | 含明文指令（见上表） | **有效：可用于代码复核** |

**这是本次重新验证中最重要的修正之一：**

```text
过去被引用为"明文镜像"的 _fullimage/run2 实际是未解密 dump。
任何基于它的反汇编结论（例如 CODOL_EXE_* / _m8_fullimage_xrefs 的输出）都不成立。
```

有效的明文镜像为：

```text
CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin
size   = 0xA65000
sha256 = 17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045
base   = 0x00400000（换算 offset = VA - 0x400000）
```

> 注意其时间戳早于最后两次真实运行（2026-09-27）；本报告中所有代码结论均来自该镜像，
> 并通过独立的字符串/引用关系复核，不依赖旧报告的转述。

### 1.4 其它模块基线（部分）

| 模块 | 大小 | 备注 |
|---|---|---|
| `codoMP_client_shipRetailBase.dll` | 60,327,992 | VM 宿主 / 平台 bootstrap |
| `GameDataPlatformServer.dll` | 354,808 | 内嵌 `GDPPkg` / `GDPOpenProtocol.tdr` 引用 |
| `GDPLoader.dll` | 291,832 | 基本明文，可静态反汇编 |
| `GDPImpl.dll` | 68,088 | |
| `GameRpcs.dll` | 2,488,888 | |
| `TenProxy.dll` | 167,592 | |
| `TenRpcs.dll` | 17,408,064 | |
| `TenSLX.dll` | 2,675,768 | |
| `TCJ.dll` | 3,158,584 | |
| `TerSafe.dll` | 8,280,328 | |
| `PolicyProbe.dll` | 6,855,224 | |
| `BugTrace.dll` | 1,029,624 | |
| `GbSpy.dll` | 538,584 | |
| `TCLS/Tenio/ProtocalHandler.dll` | 1,556,072 | |

全量 SHA-256 见 `分析/00_baseline_module_hashes.csv`。

### 1.5 本地配置文件现状（注意：已被改写）

```text
COD OL\dwauth.ini   ==>
127.0.0.1 / 0 / 127.0.0.1 / 443 / 0 / 0 / 0      <- 已被本地实验改写

COD OL\stun.ini     ==>
stun1-tub.codol.qq.com / stun2-tub.codol.qq.com / stun3-tub.codol.qq.com   <- 原始

COD OL\iips.ini     ==>
enable_iips=0                                      <- 已被本地实验改写
```

**⇒ `dwauth.ini` 不是原始文件。任何"历史大厅地址"都不能从当前磁盘取值推断，
只能从代码格式和动态观测推断。**

---

## 2. 第一阶段结论总表

| # | 结论 | 置信度 |
|---|---|---|
| C1 | 磁盘 `.tp3` 代码段加密，必须用运行期明文镜像 | **CONFIRMED** |
| C2 | `_fullimage/run2` 镜像是未解密 dump，旧结论需作废 | **REFUTED（旧证据）** |
| C3 | 大厅/DW 状态机为 `0x7F25B0`(取状态) + `0x7F26C0`(泵) + `0x7F28F0`(分派) | **CONFIRMED** |
| C4 | DW 状态取值 0–5，子状态取值 0–9 | **CONFIRMED** |
| C5 | `dwauth.ini` 7 个字段 → `0x81A7F34 / 0x81A9780 / 0x81A76A8 / 0x81A9EC4 / 0x81A9EB8 / 0x81A56A4 / 0x81A76E4` | **CONFIRMED** |
| C6 | 大厅主机 `0x81A76A8`、端口 `0x81A9EC4` 被 DNS 步骤与建连步骤直接引用 | **CONFIRMED** |
| C7 | AUTH 请求为 `POST /auth/`，JSON 含 `auth_task / iv_seed / title_id / identity / extra_data` | **CONFIRMED（动态）** |
| C8 | AUTH 走 TLS，CA 来自同级 `cacert.pem` | **CONFIRMED** |
| C9 | URL 模板 `%s://%s:%d/%s/title/%d/queue/%d/member/%llu` 属于队列/匹配类接口 | **LIKELY**；其**服务归属（LSG 或 Lobby）为 UNKNOWN** |
| C10 | `lsg_server_ticket` 来自 `/auth/` 响应体，被解析进对象偏移 `+0x2e8` | **CONFIRMED** |
| C11 | `GDPOpenProtocol.tdr` 是独立明文 schema（438,856 B） | **CONFIRMED** |
| C12 | EXE 内两处 `0x000B02D6` 只是数据片段，不是完整 TDR | **REFUTED（旧假设）** |
| C13 | `dwauth.ini` 当前值非原始值 | **CONFIRMED** |
| C14 | LSG ticket 与 Lobby 的连接关系 | **UNKNOWN**（本阶段无直接证据） |

---

## 3. 结论卡片（标准格式）

### C1 — 磁盘代码段加密

```text
结论：codoMP_client_shipRetail.exe 的 .tp3 代码段在磁盘上是密文，
      必须在运行期解密后才能反汇编。

原始证据：
- 文件：COD OL\codoMP_client_shipRetail.exe
- SHA-256：36997674b18f2896de5e9d75...（见 00_baseline_module_hashes.csv）
- 地址：0x004FCEE0 / 0x0077EE40 / 0x00808650
- 磁盘字节 vs 运行期字节：见 1.2

支持证据：
1. 三个入口地址在磁盘上均无法构成合法 x86 prologue。
2. 对应运行期镜像上均为标准 push ebp; mov ebp,esp。
3. 全 EXE 的 .tp3 代码节 flags 含 execute/read，但内容为高熵数据。

反证：
1. 旧报告曾声称部分区域"明文可读"（GDPLoader.dll 确实明文，但那不是本 EXE）。
2. 未发现任何 .tp3 代码节内的明文函数体。

重新验证结果：CONFIRMED
```

### C2 — 旧"明文镜像"作废

```text
结论：CODOLServer/_fullimage/run2/.../image_best.bin 不是解密镜像，
      与磁盘 EXE 字节相同。

原始证据：
- 镜像 SHA-256：1b85e28e22556897865d7258a793d12cae4612a50550e61426687944a6a46c63
- 该镜像 0x4FCEE0 处字节 = 43 03 21 d0 ...，与磁盘 EXE 完全一致。

支持证据：
1. 逐地址比对与磁盘 EXE 相同。
2. run1 版本非零字节为 0（完全无效）。

反证：
1. 其 fullimage.log 自称 "nonzero=6439332"，确实读到了内存，
   但读到的是尚未解密的映射内容。

重新验证结果：REFUTED（作为"解密代码证据"）
```

### C3 / C4 — DW 状态机结构

```text
结论：大厅 DW 状态机由以下函数构成：
      0x7F25B0  = 取"对外状态"（对外可见的 DW 状态）
      0x7F26C0  = 状态泵/推进器（switch on [0x84ABA50]）
      0x7F28F0  = 子状态分派器（switch on [0x84ABA60]，分支 0..9）

原始证据：
- 镜像：_dyn100_run_20260925_182324/live/image_best.bin
- 关键全局：0x84ABA50（dw_state）、0x84ABA60（dw_substate）、
            0x84ABA5C（dw_code）、0x84ABA78（dns_ok）、0x84ABA7C（lobby_phase）
- 反汇编：0x7F26C0 处 `cmp eax,5 / dec eax / cmp eax,3 / jmp [eax*4+0x7F2850]`
          0x7F28F0 处 `cmp eax,9 / ja ... / jmp [eax*4+0x7F2994]`

支持证据：
1. 跳转表 0x7F25DC（状态→对外值）、0x7F2850（4 分支）、0x7F2994（10 分支）
   均已逐项 dump（见 分析/constants.py 输出）。
2. 调用者 xref：0x7EF1C8 / 0x7EF387 调 0x7F26C0；
   0x4F8ADB / 0x4F8BD1 / 0x77DB4C / 0x7EF1CD / 0x7EF28A / 0x7EF2A4 / 0x7FB158 调 0x7F25B0。

反证：
1. 之前有结论称 0x7F25B0 = "Lobby 状态机整体"，实际它只是**取状态值的只读函数**，
   真正的泵是 0x7F26C0。旧命名需要收窄。

重新验证结果：CONFIRMED（结构），修正（旧命名过宽）
```

子状态分派（`0x7F28F0` 的 0x7F2994 跳转表）：

| 子状态 | 处理函数 | 观察到的行为 |
|---:|---|---|
| 0 | `0x7F2B90` | 发起大厅建连 |
| 1 | `0x7F29C0` | （未展开） |
| 2 | `0x7F2AB0` → 成功后调 `0x7F2B90` | 中间握手 |
| 3 | `0x7F23??` 分支 → 置子状态 0 | 结束/复位 |
| 5 | `0x7F2B90`（`push 1`） | 另一种建连模式 |
| 6 | `0x7F2DB0` | （未展开） |
| 7 | `0x7F3100` | 关闭/清理（含 CA 校验失败弹窗路径） |
| 8 | `0x7F3190` | 取结果码，`0x22C4` 视为成功 |
| 9 | 直接返回（无操作） | |

### C5 / C6 — `dwauth.ini` 与大厅主机/端口

```text
结论：dwauth.ini 的 7 个字段被读入固定全局，其中字段 3 = 大厅 HOST、
      字段 4 = 大厅 PORT，二者被 DNS 步骤与建连步骤直接引用。

原始证据（0x77EE40 = WinMain，逐条复核）：
- 0x77EF3C: push 0xDDBD9C("dwauth.ini") + fopen(0xDB0048="r") -> FILE*
- 0x77EF64: push 0x81A7F34 + push 0xDDBDA8("%59s")  -> 字段1 字符串
- 0x77EF77: push 0x81A9780 + push 0xDDBDB0          -> 字段2 uint16
- 0x77EF8A: push 0x81A76A8 + push 0xDDBDA8("%59s")  -> 字段3 字符串（HOST）
- 0x77EF9D: push 0x81A9EC4 + push 0xDDBDB0          -> 字段4 uint16（PORT）
- 0x77EFB0: push 0x81A9EB8 + push 0xDDBDB8("%x")    -> 字段5 hex32
- 0x77EFC3: push 0x81A56A4 + push 0xDDBDB8("%x")    -> 字段6 hex32
- 0x77EFD6: push 0x81A76E4 + push 0xDDBDB8("%x")    -> 字段7 hex32
- 0x77EFE9: fclose
- stun.ini：0x77F056 fopen(0xDDBDBC)，随后 0x77F070 起以步长 0x3C 循环到 0x81A9EA8

字段 → 目标全局（xref 复核）：
  字段1 %59s  -> 0x81A7F34   被 0x7F3589 引用（DNS 第二主机）
  字段2 %hu   -> 0x81A9780   被 0x7F38B3 movzx 引用
  字段3 %59s  -> 0x81A76A8   被 0x7F2BDD / 0x7F2C15 / 0x7F306C / 0x7F3533 / 0x77EF8A 引用
  字段4 %hu   -> 0x81A9EC4   被 0x7F2BAF movzx 引用（PORT）
  字段5 %x    -> 0x81A9EB8   被 0x7F2BA8 引用
  字段6 %x    -> 0x81A56A4
  字段7 %x    -> 0x81A76E4

支持证据：
1. DNS 步骤 0x7F3533/0x7F3589 分别 push 0x81A76A8 / 0x81A7F34 进解析器。
2. 建连步骤 0x7F2BDD push 0x81A76A8；0x7F2BAF `movzx edi, word ptr [0x81A9EC4]`。
3. URL 拼接 0x7F306C push 0x81A76A8 + push 0xDE09E4("https://%s/")。

反证：
1. 无法证明字段 2/5/6/7 的业务语义（只知类型：uint16 / 三个 hex32）。
2. 当前磁盘 dwauth.ini 已被改写为 127.0.0.1，不能反推原始值。
3. 字段 1 与字段 3 使用同一格式串 `%59s`，因此"字段 1 是第二个主机"只能由
   0x7F3589 的引用推断，不是格式串本身能证明的。

重新验证结果：CONFIRMED（字段归属与引用）；UNKNOWN（字段 2/5/6/7 语义）
```

### C7 / C8 — AUTH 协议（动态证据）

```text
结论：AUTH 为 HTTPS POST /auth/ + application/json，请求字段为
      auth_task / iv_seed / title_id / identity / extra_data。

原始证据（时间线一致的固化链运行）：
- 运行目录：run_codol_001/runs/IFS1_ELEVATED_20260927_223423
- 服务端探针日志：CODOLServer/logs/FULL_DYNAMIC_20260927_2238/probe.jsonl
- 条目：{"event":"http", ... "request_line":"POST /auth/ HTTP/1.1",
  "headers":["Host: 127.0.0.1","Accept: */*","Content-Type: application/json",
             "X-TransactionID: 2142895319833911715","Content-Length: 187",
             "Expect: 100-continue"], "body_len":187}
- body（已解码）：
  {"auth_task":"10","iv_seed":"2034743188","title_id":"0",
   "identity":"356c4bc3",
   "extra_data":"{\"version\": \"0\", \"user_id\": \"10995207597479878709\",
                  \"extended_data\": true}"}
- TLS：{"event":"tls_ok","tls_version":"TLSv1","cipher":"AES256-SHA"}

支持证据（静态，与动态一致）：
1. 0xD5A2CC 明文格式串 "https://%s:%d/auth/"（磁盘命中）。
2. 0xD5A228 明文 "auth_task"（磁盘命中）。
3. 0xD5A114 明文 "iv_seed"（磁盘命中）。
4. 0xDC9CB0 "CODOL/1.0"、0xDC9CBC "X-TransactionID: %I64u"、
   0xDC9CA4 "cacert.pem"（CA 文件名，磁盘命中）。
5. 运行期 xref：0xB99EBE / 0xB9AC89 push 0xD5A2CC（URL 模板被真实引用）。

反证：
1. 请求是通过本地改写 dwauth.ini 指向 127.0.0.1:443 后观测到的，
   属于"重定向后的真实客户端行为"，不是原始公网流量。
2. 没有原始公网 AUTH 抓包可比对响应体。

重新验证结果：CONFIRMED（请求结构与传输方式）
```

### C10 — ticket 数据流

```text
结论：/auth/ 响应头中的 DW-Server-Ticket / DW-Client-Ticket / DW-Ticket-Seed
      被解析；响应体 JSON 中的 lsg_server_ticket / lsg_server_ticket_size
      被解析进对象，并落到 +0x2e8 区域；ticket 长度上限为 0x80。

原始证据：
- 解析点 0xB984CD push 0xD5A0FC("lsg_server_ticket_size") -> [ebp-0xe8]
- 解析点 0xB984B2 push 0xD5A114("iv_seed")                -> [ebp-0xf4]
- 解析点 0xB9852B push 0xD5A0E8("lsg_server_ticket")      -> [ebp-0xe0]
- 长度校验 0xB98553: cmp edi, 0x80 (128) —— 即 ticket 上限 128 字节
- 写入 0xB98577 起: push edi / lea ecx,[esi+0x2e8] / 复制字符串到对象 +0x2e8
- 响应头解析 0xB987E5 push 0xD5A1AC("DW-Server-Ticket")；
             0xD5A180 "DW-Client-Ticket" 与 0xD5A158 "DW-Ticket-Seed"
             在代码中同样各有一个 immediate 引用（0xB989B8 / 0xB98A3E）

支持证据：
1. 上述五个字符串在磁盘上唯一命中，且在代码中各有 1 个 immediate 引用。
2. 全代码段 xref 扫描（3,239,842 条指令）独立复现了这些引用。
3. 动态运行中，本地 mock 返回的 JSON 恰好包含
   lsg_server_ticket_size=128 与 128 字节的 lsg_server_ticket。

反证：
1. mock 的 ticket 值本身是测试构造的（`3q297x0o...`），不是真实 ticket。
2. 未观测到真实服务器返回的 ticket 样本。

重新验证结果：CONFIRMED（解析位置与长度约束）
               UNKNOWN（ticket 的加密/编码语义）
```

### C9 — URL 模板归属

```text
结论：%s://%s:%d/%s/title/%d/queue/%d/member/%llu 是队列/匹配类 URL 模板。

原始证据（磁盘明文，同一字符串池 0xD5A0E8..0xD5A340）：
  0xD5A11C  "%s://%s:%d/%s/title/%d/queue/%d/member/%llu"
  0xD5A148  "https"
  0xD5A150  "v1.0"
  0xD5A158  "DW-Ticket-Seed"
  0xD5A168  "DW-Client-Ticket-Size"
  0xD5A180  "DW-Client-Ticket"
  0xD5A194  "DW-Server-Ticket-Size"
  0xD5A1AC  "DW-Server-Ticket"
  0xD5A1C0  "Transfer-Encoding"
  0xD5A1D4  "Content-Type"
  0xD5A1E4  "application/json"
  0xD5A228  "auth_task"
  0xD5A290  "extended_data"
  0xD5A2A0  "license_id"
  0xD5A2AC  "user_id"
  0xD5A2B4  "time_to_live"
  0xD5A2C4  "cd_key"
  0xD5A2CC  "https://%s:%d/auth/"

支持证据：
1. 该模板与 ticket/HTTP 头字段同处一个字符串池，语义上属于同一 HTTP 接口族。
2. 模板中的 title/queue/member 与 CODOL 的 title_id + 匹配队列模型吻合。

反证：
1. 未在本阶段直接抓到"该模板被 push 且随后进入 send"的完整链。
2. 因此它到底是 LSG 的还是 Lobby 的 queue 接口，**不能仅凭字符串确定**。

重新验证结果：LIKELY（属于队列类 URL）；具体服务归属 UNKNOWN
```

### C11 / C12 — GDP schema

```text
结论：GDPOpenProtocol.tdr 是**独立的明文** schema 文件（不是从 EXE 解出的），
      EXE 内出现的 0x000B02D6 只是数据片段。

原始证据：
- 文件：COD OL\GDPOpenProtocol.tdr
- 大小：438,856 B
- SHA-256：b0c5d029a582b11d053bcb4069b348ad8abdf4a5b028acd93207a09eec7a52cb
- 头部：d6020b00 20000000 48b20600 ... （magic 0x000B02D6，小端）
- 含字符串："GDP_Open_Protocol"(0x94)、"TGDPCODOLCmd"(0x60372)、
  "GDPPkgHead"(0x607f8)、"GDP_CF_REQ_ENTERSERVER"(0x56da3)、
  "GDP_CF_NOTIFY_GAMESERVERPORTINFO"(0x57e15)、"GDP_PROTOCOL_VERSION"(0x561b0)

支持证据：
1. 独立文件内可定位 CODOL 专用命令与类型名。
2. GameDataPlatformServer.dll 的字符串中同时含 GDPPkg / GDPOpenProtocol.tdr。

反证（重要）：
1. EXE 内 0xE40398 / 0xE44458 两处 0x000B02D6 之后 0x60000 字节窗口内
   找不到上述任何 GDP 名字 —— 说明它们**不是**完整内嵌 schema。
   旧说法"CODOL 的服务器协议 schema 内嵌在 exe"属于过度概括。
2. GDP 通道在运行期是否真正与大厅交互，本阶段未取得直接证据。

重新验证结果：CONFIRMED（独立 TDR 明文存在）
               REFUTED（"EXE 内完整内嵌 schema"）
               UNKNOWN（GDP 与 Lobby 的运行时关系）
```

### C13 / 反证与 AUTH 端点的重要性排序

```text
结论：在当前所有已知端点中，只有 AUTH（/auth/）被真实运行证据证明
      是客户端必经且被服务器响应的阶段。

原始证据：
- IIPS：iips.ini 被置 enable_iips=0 后仍能推进（本轮未作为阻碍）。
- TQoS/ied-tqos.qq.com：旧实验 A 改写到本地并应答后 [100] 依旧出现。
- AUTH：本轮真实观测到 POST /auth/ 到达本地探针并返回 200。

支持证据：
1. probe.jsonl 记录了完整 TLS + HTTP + 响应。
2. socket.jsonl 显示 127.0.0.2:8444 的监听端**没有**收到任何连接，
   说明真实大厅 socket 尚未建立。

反证：
1. 无法排除 IIPS/TQoS 在更完整环境下仍影响后续阶段。
2. AUTH 之后没有任何后续请求，说明链条在 AUTH 之后中断。

重新验证结果：CONFIRMED（AUTH 是必经且可观测阶段）
               大厅 socket 未建立 = CONFIRMED（本轮范围内）
```

---

## 4. 服务端组件模型（当前证据水平）

### A. 组件

| Component | Role | Endpoint | Protocol | Client entry point | Evidence | Confidence |
|---|---|---|---|---|---|---|
| AUTH (dw auth) | 账号/ticket 签发 | `dwauth.ini` 字段3:字段4 | HTTPS + JSON | `0x7F2B90` → `0xB88B80` / `0xB99090` → `0xB9A100`(载入 cacert.pem) | C5/C6/C7/C10 | **CONFIRMED** |
| Lobby (dw lobby) | 大厅连接与登录 | 同 AUTH 主机 | 未捕获（应用层未知） | `0x7F28F0` 子状态 0/2/8 | C3/C4 | **LIKELY** |
| LSG | 队列/匹配（含 queue URL） | 未捕获 | HTTP(S) + JSON | 字符串池 0xD5A11C 等 | C9 | **UNKNOWN**（归属） |
| TQoS | 网络质量上报 | `tqos.gamesafe.qq.com:8080/8081`（GDPLoader 内） | 自定义 `TssQosPkg`（UDP） | `GDPLoader!InitGdp` | GDPLoader 静态 | **LIKELY**（该 DLL 与大厅无引用关系） |
| STUN | NAT 检测 | `stun*.codol.qq.com`（原始 stun.ini） | STUN 风格 | `stun.ini` 读取点 0x77F056 | 配置文件 + 代码 | **LIKELY** |
| IIPS | 下载/加速/地址发现 | `ctrl.iips.qq.com` 等 | `ur`（Tenio） | IIPSHostApp.exe | 抓包 + 策略响应 | **CONFIRMED**（作为独立组件） |
| Game Server (GDP) | 房间/战局（CF 命令族） | 未知 | GDP 包（TDR） | `GDPOpenProtocol.tdr` | C11 | **UNKNOWN**（运行时关系） |

### B. Endpoint

| Host | Port | Protocol | Path | Source | Evidence | Confidence |
|---|---|---|---|---|---|---|
| `dwauth.ini` 字段3 | `dwauth.ini` 字段4 | HTTPS | `/auth/` | 磁盘格式串 0xD5A2CC + 动态 | C5/C7 | **CONFIRMED** |
| 同 HOST | 字段4 | HTTPS | `https://%s/` | 磁盘 0xDE09E4 | xref 0x7F3071 | **CONFIRMED** |
| 字段3 | 字段4 | HTTPS | `%s://%s:%d/%s/title/%d/queue/%d/member/%llu` | 磁盘 0xD5A11C | C9 | **LIKELY** |
| `ied-tqos.qq.com` | 80 | TCP | — | 磁盘 0xDD98A0 | 旧抓包 | **LIKELY** |
| `stun1/2/3-tub.codol.qq.com` | 未定 | UDP | — | `stun.ini` | 配置 | **LIKELY** |
| `tqos.gamesafe.qq.com` | 8080/8081 | UDP | — | GDPLoader 内 | 静态 | **LIKELY**（与大厅无关联证） |

### C. AUTH

```text
Request  : POST /auth/  (HTTP/1.1)
Headers  : Host, Accept: */*, Content-Type: application/json,
           X-TransactionID: <u64 decimal>, Content-Length, Expect: 100-continue
Body     : {"auth_task":"<n>","iv_seed":"<u32 decimal>","title_id":"0",
            "identity":"<8 hex>","extra_data":"{\"version\":\"0\",
            \"user_id\":\"<u64>\",\"extended_data\":true}"}
Response : HTTP 200 + JSON
Fields   : auth_task, code, iv_seed, client_ticket, server_ticket,
           lsg_server_ticket, lsg_server_ticket_size,
           next_poll_after, estimated_wait_time, member_position
Parser   : 0xB983F0（主解析）, 0xBA9BC0（子解析）, 0xB9A470（另一阶段）, 0xB983B0（结果码取值）
State    : 0x7F28F0 子状态机；0x7F3190 用 code==0x22C4 判成功
```

### D. LSG

```text
Connection : UNKNOWN（本阶段未捕获）
Ticket     : lsg_server_ticket / lsg_server_ticket_size，来自 /auth/ 响应体，
             上限 128 字节，落点 +0x2e8
Request    : UNKNOWN
Response   : UNKNOWN
Fields     : 仅知 URL 模板含 title / queue / member
State      : UNKNOWN
```

### E. Lobby

```text
Connection : 使用 dwauth.ini HOST:PORT；两个分支分别构造 0xB88B80 / 0xB99090
             对象，随后都会走到 0xB9A100 加载同级 cacert.pem
Handshake  : 未捕获（socket.jsonl 显示 127.0.0.2:8444 零连接）
Packet     : UNKNOWN
Opcode     : UNKNOWN
State machine : 0x7F28F0 子状态 0..9（已知映射见 §3 C3/C4 表）
```

### F. Session / Room / Queue / Match
```text
UNKNOWN —— 客户端未推进到该阶段，无证据可填。
```

### G. Game Server
```text
UNKNOWN —— 仅知 GDP TDR schema 存在（独立文件），运行期关系未证实。
```

### H. UNKNOWN 汇总

```text
1. 大厅建连之后的应用层协议（无包捕获）
2. lsg_server_ticket 的字节格式（前 4 字节 DE AD BD EF 只是本地 mock 构造）
3. ticket 的实际校验方式（客户端是否本地校验、校验什么）
4. dwauth.ini 字段 2 / 5 / 6 / 7 的业务语义
5. 历史原始 dwauth.ini 取值（HOST / PORT 原始值）
6. GDP 通道在运行期是否被使用
7. auth_task 的完整状态枚举（仅观测到 0/7/10/12/24/26/32）
8. code / result / status 三个返回码字段的取值表
```

---

## 5. 最小 Server Emulator 需求（仅基于 CONFIRMED）

```text
MUST IMPLEMENT
- HTTPS 监听，端口 = dwauth.ini 字段 4
- 证书链能被客户端同级 cacert.pem 接受
- POST /auth/ 的 HTTP/1.1 处理（含 Expect: 100-continue）
- application/json 请求解析（auth_task / iv_seed / title_id / identity / extra_data）
- 返回 JSON，至少含 auth_task 回执与 code
- 返回 lsg_server_ticket / lsg_server_ticket_size（≤128 字节）

PROBABLY REQUIRED
- auth_task 的阶段推进逻辑（观测到 0/7/10/12/24/26/32 数个阶段）
- client_ticket / server_ticket / lsg_server_ticket 的一致性
- code==0x22C4 被 0x7F3190 判为成功的语义对齐
- iv_seed 回显策略

UNKNOWN（不得自行填充）
- 大厅握手首个报文
- opcode / framing（magic / length / type / sequence）
- session / room / queue / match 数据模型
- Game Server 分配
- GDP 通道是否必需
```

---

## 6. 下一阶段建议（按证据价值排序）

```text
1. 取得大厅阶段的真实流量
   现状：socket.jsonl 证明 8444 端口零连接 → AUTH 之后没有进入 Lobby。
   需要：在不改变固化启动链语义的前提下，确认 AUTH 之后客户端下一步读什么全局。
   起点：0x7F3190（结果判定）与 0x7F3100（清理）之间的分支。

2. 追 0x7F2B90 的两个分支差异
   push 0（子状态 0）与 push 1（子状态 5）分别走 0xB88B80 与 0xB99090。
   两者之后都会加载 cacert.pem；需要确认两个对象类型分别是哪条通道。

3. 遍历 0x7F29C0 / 0x7F2AB0 / 0x7F2DB0 / 0x7F3100 四个未展开的子状态处理函数。

4. 校验 +0x2e8 处的 ticket 下游消费者
   已确认写入点 0xB98577，未确认读取点。需要追 {esi+0x2e8} 的所有读取。

5. GDP：确认 GameDataPlatformServer.dll / GDPLoader.dll 是否被 exe 真实引用
   （旧结论称 GDPLoader 不引用，需在明文镜像上重新搜 xref）。
```

---

## 7. 诚实标注的限制

```text
1. 本报告的大多数代码结论基于 2026-09-25 的运行期镜像，
   其 SHA-256 已在 §1.3 给出，可复核。
2. 未捕获大厅阶段流量，因此 Lobby / LSG / Session / Room / Queue / Match
   全部只能标记 UNKNOWN。
3. 当前磁盘 dwauth.ini / iips.ini 均已被本地实验改写，
   不能代表历史原始配置。
4. 本报告不包含任何绕过安全组件、伪造凭据或修改系统网络设置的结论。
```
