# 构建环境探测证据（阶段 A）

探测时间：本次会话。命令与原始输出见 `build/STEP_A_PROBE.txt`。

## 1. 本机编译器可用性（决定第一版实现语言）

| 工具 | 结果 | 证据 |
|---|---|---|
| `cl.exe` (MSVC) | **缺失** | `Get-Command cl` → MISSING |
| `gcc`/`g++` (MinGW) | **缺失** | MISSING |
| `clang`/`clang++` | **不可执行** | 见下 §2 |
| `cmake` | **缺失** | MISSING |
| `rustc`/`cargo` | **缺失** | MISSING |
| `go` | **缺失** | MISSING |
| `xmake` | 存在 | `D:\Program Files\xmake\xmake\xmake.exe`，但无后端编译器 |
| `python` | 存在 | `C:\Users\...\Python311\python.exe` |
| `csc.exe` (.NET Framework 4.0) | **可用且已实测编译成功** | `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`，`/out:_probe_cs.exe` 退出码 0，产物存在 |

## 2. 本机 LLVM 拷贝是损坏的（决定性证据）

路径：`toolchain\llvm18\clang+llvm-18.1.8-x86_64-pc-windows-msvc\bin\clang++.exe`

- 该目录**只有 `bin\`**，没有 `lib\`、`include\`（`Get-ChildItem` 只返回 `bin`）。
- 该目录内**没有 `lld-link.exe` / `llvm-lib.exe` / `clang.exe`**，唯一的 `*.exe` 是 `clang++.exe`。
- 执行它报：`程序“clang++.exe”无法运行: 指定的可执行文件不是此操作系统平台的有效应用程序。`
- PE 头字节实测：
  ```
  4d 5a 78 00 01 00 00 00 04 00 00 00 ...
  ```
  `e_lfanew = 0x78`，但该偏移之后不是合法 `PE\0\0` 签名；`NumberOfSections=4`、`SizeOfOptionalHeader=0` 也与真实 PE32+ 不符。**该文件不是一个完整/有效的 Windows 可执行文件。**

## 3. 系统里没有可用的 MSVC 链接环境

- `C:\Program Files (x86)\Microsoft Visual Studio\` 下只有 `Installer\` 与 `Shared\`，**没有 `VC\Tools\MSVC`**。
- Windows Kits 有 `Lib\10.0.26100.0\ucrt\{x86,x64,arm64}\ucrt.lib`，但**没有 `msvcrt.lib`、没有 `vcruntime*.lib`** → 没有 CRT 起始代码/静态库，即使有编译器也无法链接出 exe。

## 4. 网络不可用

`Invoke-WebRequest -Uri https://github.com -Method Head` → `基础连接已经关闭: 接收时发生错误.`
⇒ 本机无法下载 MinGW-w64 / LLVM / Rust 等工具链，也无法 `git clone` 官方仓库。

## 5. 结论：第一版实现语言选 C#（.NET Framework 4.0）

理由（全部可复核）：

1. 本机**唯一可用的本机代码编译/链接链路**是 `csc.exe`（.NET Framework 4.0）。它产出真实的 PE32 `.exe`。
2. CODOL 战斗协议的服务端侧并不需要引擎 ABI：它是**纯 UDP 字节协议 + 位级快照编码**，与语言无关。
3. 参考实现（`REF_LOBBY_KIT/battle_server.py` + `battle_selftest.py`）已有**全绿**的、可离线复放的字节级基准（见 `build/BASELINE_PYTHON_SELFTEST.txt`）。C# 版可以逐字节对齐它，并把它作为对照 oracle。
4. C# 版写成**纯 BCL、零第三方依赖**（自实现 SHA-1 / HMAC-SHA1 / AES-128 / P-224 大数），因此构建可重复、无网络依赖，`csc.exe` 单命令可编译。

⚠️ 诚实标注：
- 语言选 C# 是**构建环境约束下的工程决策**，不是协议结论。协议适配层与语言无关。
- 未来若获得 MSVC/MinGW，`src/**` 的协议层可以原样改写为 C++（接口已按 `Net/` / `Game/` / `Codol/` 分层）。

## 6. 同时查明的上游源码事实

| 项目 | 路径 | 远端 | HEAD | 许可证 |
|---|---|---|---|---|
| CoD4x_Server | `DEV-BOOKING\_lineage021\CoD4x_Server` | `https://github.com/callofduty4x/CoD4x_Server` | `ddd65fc` (fix: Linux CI job) | **AGPL-3.0**（`License.md`/`copying.md` 全文 = GNU AFFERO GPL v3） |
| iw4x-client | `DEV-BOOKING\_lineage021\iw4x-client` 与 `IW4X\Client核心代码\iw4x-client` | `https://github.com/IW4x/iw4x-client` | `d1b175d` (Add server-side demo recording) | 见其 `LICENSE`；为**客户端**工程 |

工作区状态：`git status --porcelain` 均为空（干净）。本任务**未修改**这两个工作树。

许可证策略见 `docs\LICENSE_POLICY_REUSE.md`。
