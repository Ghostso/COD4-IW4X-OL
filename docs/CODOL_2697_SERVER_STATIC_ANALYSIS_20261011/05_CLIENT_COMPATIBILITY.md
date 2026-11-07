# 05 与已知客户端的兼容性关联 / CLIENT COMPATIBILITY

本报告只使用 **现有静态证据与历史研究报告**，不启动任何进程。
对象：NEW（2697）与 2.6.9.7 客户端 `codoMP_client_shipRetail.exe`。

> 证据等级：**VERIFIED** / **STATIC-INFERENCE** / **NOT-OBSERVED** / **BLOCKED**。
> **核心纪律：** 服务端"能发送" ≠ 客户端"能接收"。没有运行证据时，互通状态一律 = **NOT-OBSERVED**。

---

## 1. 客户端身份关联（VERIFIED）

启动器清单 `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\manifest.json`：

```json
{
  "version": "2.6.9.7",
  "original_exe_sha256": "353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1",
  "inventory_count": 6584,
  "session_seconds": 0,
  "components": {
    "client_room2697.dll":        "120c4cfdd79a9a38d992598c30af3c5cabe754e7b3d17614074b4b8026ffc3a7",
    "client_native_loopback.dll": "53c6fbe264defc06629fef06f43a1ddd82fda716439432c354b5eb2ee4074829"
  },
  "repair_revision": "2026-10-10-chinese-name-boundaries",
  "factory_profile": { "character": 545, "character_name": "尤里" },
  "identity_encoding": {
    "frontend_dw_username": "CP936",
    "native_name": "UTF-8",
    "connect_name": "Base64(CP936)",
    "server_and_clientinfo": "CP936"
  }
}
```

**VERIFIED：** `original_exe_sha256` 与磁盘客户端 **逐字节一致**：

| 项 | 值 |
|---|---|
| 客户端路径 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` |
| 大小 | 9,964,656 字节 |
| SHA-256 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` |
| 与 manifest 声明 | **一致** |

同时 `manifest.json` 声明的两个组件 DLL 哈希与磁盘文件 **一致**（VERIFIED）。

**STATIC-INFERENCE：** NEW 服务端属于 **2.6.9.7 客户端对应的封包**（同一 `CODOL_2697_Launcher` 分发中，服务端与客户端 + 组件 DLL 同源）。这构成"NEW 与当前客户端版本更接近"的 **直接静态关联**，但 **不等于** 二者已联通。

---

## 2. 客户端注册导出（VERIFIED，直接证据）

`_CODOL2697_ReadRegistration`（RVA 0xa3ea0）要求读取一个"已验证客户端注册导出"文件；磁盘上确实存在：

```
D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\evidence\client-registration2697.txt
首行: codol2697-registration 2 6b6fb5d0 180 139 f78302fe
```

- 格式与反汇编中的 `sscanf` 模板（`"codol2697-registration %u %x %u"` / 五字段变体）**匹配**（VERIFIED）。
- 若该文件缺失/校验不过，`_CODOL2697_WriteNativeGamestate` 会 Com_Printf `"CoDOL 2697 gamestate withheld: verified client registration export is required"` 并 **返回 0（扣留 gamestate）**（VERIFIED，见 04 第 4 节）。

**STATIC-INFERENCE：** 2697 进入 gamestate 发布有一个 **硬前置条件** = 存在通过校验的客户端注册导出。这与"进入大厅"强相关：**若注册导出缺失或不匹配，服务端会主动扣留 gamestate，客户端无法收到进入大厅所需的初始状态。** 这是本阶段对"大厅初始化路径"最有解释力的发现。

---

## 3. 发布审计与净约束（NEW-only，VERIFIED）

NEW-only 诊断串（VA 见 04）：

- `"CoDOL 2697 publication dry encode=%d bytes=%u actual_client_crc=%d"`
- `"CoDOL 2697 netconst checksum=%08x seed=%08x"`
- `"Read-only verified client registration export for target gamestate publication"`
- `"CoDOL 2697 map archives mounted: %u (%s)"` / `"CoDOL 2697 map mount failed: %s (asset %u)"`
- `"CoDOL 2697 reliable audit mapped=%u immutable_omitted=%u failures=%u"`
- `"CoDOL2697 bot reliable audit failed: %.1024s"`

**STATIC-INFERENCE：** NEW 引入了一个"**发布审计 / dry-encode**"机制：在发送前对 gamestate 做一次"试编码"，比对字节数与客户端 CRC/净约束（netconst）。这说明 2697 通道 **显式面向某个特定客户端版本的净约束**，进一步支持"与 2.6.9.7 客户端更贴近"的判断——但 **仍是静态推断**。

---

## 4. loopback 守卫（NEW-only，VERIFIED）

NEW 独有 11 个网络守卫（`codol_loopback_win32.c`，符号 RVAs）：

| 符号 | RVA | VA |
|---|---|---|
| `_guard_socket@12` | 0x98920 | 0x498920 |
| `_guard_bind@12` | 0x98e4f | 0x498e4f |
| `_guard_connect@12` | 0x98f03 | 0x498f03 |
| `_guard_send@16` | 0x98dfe | 0x498dfe |
| `_guard_sendto@24` | 0x98d8a | 0x498d8a |
| `_guard_recv@16` | 0x98d39 | 0x498d39 |
| `_guard_recvfrom@24` | 0x98c4e | 0x498c4e |
| `_guard_accept@12` | 0x98b93 | 0x498b93 |
| `_guard_getaddrinfo@16` | 0x98a73 | 0x498a73 |
| `_guard_getnameinfo@28` | 0x989cd | 0x4989cd |
| `_guard_setsockopt@20` | 0x98f50 | 0x498f50 |

配套启动器证据（历史产物，**非本阶段运行**）：

- `evidence\loopback-executable-audit.json`：`executable_sha256 = 80816711…`（与 NEW 一致）、`unguarded_import_thunk_calls: 0`、`unexpected_network_imports: 0`、`engine_started: false`。
- `evidence\client-loopback-guard.json`：`real_client_started: false`、`scope: "udp-127.0.0.1:28969"`、`passed: true`。

**VERIFIED：** 这些是可读的既有 JSON 工件，且其 `executable_sha256` 与 NEW 服务端一致。
**NOT-OBSERVED：** 本阶段 **未运行** 任何 loopback/guard 测试；上述 `engine_started:false` / `real_client_started:false` 表明这些历史证据 **本身也不是真实客户端互通证据**。整体互通仍 = **NOT-OBSERVED**。

---

## 5. 历史研究报告的消息常量对照

任务书列出的旧版静态研究常量（snapshot=0x00 / serverCommand=0x01 / gamestate=0x02 / configstring=0x03 / EOF=0x05）在本阶段 **已用旧包源码与三样本反汇编重新核验**：

| 常量 | 旧版源码依据 | NEW 旧通道 | NEW 2697 通道 |
|---|---|---|---|
| snapshot | 0x00 | 保持 0x00 | 0x00 + 终止 0x06 |
| serverCommand | 0x01（`SV_WIRE_SERVERCOMMAND`） | 0x01 | **0x02**（结构化 payload，见 04§3） |
| gamestate | 0x02 | 保持 0x02 | 起始 **0x03**、终止 **0x06** |
| configstring | 0x03 | 保持 0x03 | 组合进 2697 写路径 |
| EOF | 0x05（`SV_WIRE_EOF`） | 保持 0x05 | **0x06** |

**VERIFIED：** 旧通道常量确实保持；2697 通道在 EOF 处写 `0x06`，在可靠命令处写 `0x02`。
**STATIC-INFERENCE：** 这些字节差异 **可能** 就是 2697 面向新客户端的协议差异，也 **可能** 只是 2697 内部分层；两者都需运行验证。
**NOT-OBSERVED：** 客户端是否接受 `0x06` / 新可靠命令封装——**未验证**。

---

## 6. 兼容性判断（严格分级）

| 问题 | 结论 | 等级 |
|---|---|---|
| NEW 服务端是否与 2.6.9.7 客户端同源封包 | 是（客户端哈希与 manifest 一致） | VERIFIED |
| 是否存在面向客户端的净约束/发布审计机制 | 是（dry-encode / netconst 诊断串） | VERIFIED |
| 是否新增了旧版不存在的注册门控 | 是（gamestate withheld 闸门） | VERIFIED |
| 是否新增了旧版不存在的消息字节（EOF=0x06 / 可靠命令 0x02） | 是 | VERIFIED |
| 这些新字节/封装是否被客户端实际接受 | 未验证 | **NOT-OBSERVED** |
| NEW 服务端 + 该客户端是否已能进入大厅 | 未验证 | **NOT-OBSERVED** |
| 2697 通道是否有运行时启用开关 | 已知存在 CVar 名（`CODOL2697_PROFILE_WIRE` 等），但启用点未追踪 | BLOCKED |

**最终兼容性表述：** NEW 在 **静态层面** 比 OLD 更接近 2.6.9.7 客户端（同源封包 + 面向该客户端的净约束/注册门控/新消息封装），但 **在运行层面，互通与进入大厅均为 NOT-OBSERVED**，不得写成"已兼容"。

未决问题：
- 客户端二进制中是否存在对应接收 `0x06` / 可靠命令 `0x02` 的处理分支（本阶段未反汇编客户端）→ 未解决。
- `client_room2697.dll` / `client_native_loopback.dll` 是否携带与 2697 服务端对称的协议处理（本阶段仅核验哈希，未反汇编）→ 未解决。
