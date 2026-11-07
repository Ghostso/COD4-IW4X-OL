# CODOL 静态证据包 — 组件调用、通信链、资源缺口（可直接落地）

**日期**：2026-09-29
**方法**：纯静态、只读。反汇编对象 = 运行期解密镜像
`CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin`
（base `0x400000`，SHA-256 `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`）。
**未运行游戏、未读写游戏内存、未修改任何既有文件**（仅新增下列产物）。

---

## 0. 交付物清单（可复核、可直接落地）

| 文件 | 规模 | 用途 | 复现命令 |
|---|---|---|---|
| `CODOL_STATIC_EVIDENCE_KIT.md` | 本文档 | 组件调用图 + 服务器通信链 + 资源缺口 | — |
| `CODOL_ARCH_COMPONENT_PROTOCOL_MAP.md` | 446 行 / 20 KB | 组件调用图 + 服务器通信链（地址级） | — |
| `arch_modules.csv` | 39 行 | 顶层 39 个模块：架构/大小/保护壳/SHA-256 | `python -X utf8 _arch_scan.py modules` |
| `arch_imports.csv` | 689 行 | 游戏进程实际使用的 Win32 API（已解析 IAT） | `python -X utf8 _arch_scan.py imports` |
| `arch_endpoints.csv` | 813 行 | 端点/协议常量 + **明文镜像真实引用地址** | `python -X utf8 _arch_scan.py endpoints` |
| `arch_zone_requests.csv` | 6,466 行 | 所有被引擎请求的 zone 名、字符串 VA、指令 VA、置信度 | `python -X utf8 _zone_enum.py enq` |
| `arch_zone_ifs_map.csv` | 61 行 | zone 名 ↔ `.ifs` 容器（SHA-256 + size）+ 是否在 main\ | `python -X utf8 _zone_ifs_map.py` |
| `_arch_scan.py` | 8 KB | 只读扫描器（modules/imports/endpoints/xref） | — |
| `_zone_enum.py` | 7 KB | zone 名枚举 + 与 main\ 差集 | — |
| `_zone_ifs_map.py` | 5 KB | zone → .ifs 映射 + 缺口报表 | — |

> 所有脚本 `py_compile` 通过，仅依赖标准库 + capstone/pefile，ASCII 纯文本。

---

## 1. 组件清单（`arch_modules.csv`，顶层 39 项）

| 角色 | 模块 | 大小 | 保护壳 | 关键点 |
|---|---|---|---|---|
| 主模块 | `codoMP_client_shipRetail.exe` | 7.8 MB | `.tp3` + `.tvm0` | **磁盘代码全加密**，唯一静态导入 Base.dll ordinal-1 |
| VM 宿主 | `codoMP_client_shipRetailBase.dll` | 60 MB | `.tvm0` | 真正的 API 面；`ace-ats32.dll` / `tvsd.dll` 等全在其内部被 VM 解开 |
| 大厅协议 | `GameDataPlatformServer.dll` / `GDPLoader.dll` / `GDPImpl.dll` | 354/291/68 KB | `.tvm0` | GDP 协议宿主，内嵌 `GDPPkg`/`GDPOpenProtocol.tdr` |
| RPC | `GameRpcs.dll` / `TenRpcs.dll` | 2.4/17 MB | `.tvm0` | RPC 层 |
| 平台代理 | `TenProxy.dll` | 167 KB | **无壳** | 可静态反汇编，含 `ProtocalHandler` 导出 |
| 安全 | `TCJ.dll` / `PolicyProbe.dll` / `ACE-DRV32.dll` / `VSDDrvDll.dll` | — | **VMProtect** | |
| 安全 | `TerSafe.dll` / `ace-ats32.dll` / `tvsd.dll` / `TenSLX.dll` / `TenSp.dll` | — | `.tvm0` / `.tvm40/41` | |
| 崩溃 | `BugTrace.dll` | 1 MB | 无壳 | 崩溃回传 |
| 语音/浏览/渲染 | `GCloudVoice.dll` / `libcef.dll` / `D3DX9_43.dll` / `bink2w32.dll` | — | 无壳 | |

> **结论**：主 exe 的"自己"的代码在磁盘上是密文；一切代码结论只能来自运行期镜像（本包全部遵守）。