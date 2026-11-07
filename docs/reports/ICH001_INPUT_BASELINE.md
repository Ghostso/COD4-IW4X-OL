# ICH-001-00 — IW4X 本地输入盘点基线

- 生成时间：2026-09-20 15:12:52 UTC+08:00
- 输入根目录：`D:\BaiduNetdiskDownload\使命召唤OL\IW4X`
- 范围：仅 IW4X 本地文件；不包含 CODOL、`Base.dll`、`.tvm0` 或运行时行为。
- 执行约束：只做文件枚举、SHA-256、PE 元数据、Git 元数据与源码位置识别；未启动 IW4X/CODOL，未注入、Hook、动态调试或修改输入文件。

## 盘点结果

| 项目 | 结果 |
|---|---:|
| 目录数 | 72 |
| 文件数 | 594 |
| PE 文件数 | 3 |
| 源码/构建脚本文件数 | 541 |
| `iw4x-launcher.exe` | YES |
| `iw4mp.exe` | NO |
| Git repository | YES |

## 身份确认

### A. IW4X Launcher

- 状态：YES
- 路径：`D:\BaiduNetdiskDownload\使命召唤OL\IW4X\启动器\iw4x-launcher.exe`
- 大小：40338259 bytes (38.47 MiB)
- SHA-256：`d1982b7cec260a3d3141f2921c23983a2832aada7d6f419b328d125ac1e5284d`
- PE 类型：`PE64` / machine `0x8664`
- ImageBase / EntryRVA：`0x140000000` / `0x1400`
- PE timestamp：`0x6a3c0871` (2026-06-24T16:40:17Z)
- sections / imports / exports：`19` / `406` / `0`
- 判定依据：路径与文件名是初筛；PE 元数据确认其为 PE64 Windows 可执行文件，且 SHA-256 已固定。内部代码归属与运行逻辑留待后续阶段。

### B. IW4 Multiplayer Host

- 状态：NO
- `iw4mp.exe`：未找到。
- 其他 PE 候选：`premake5.exe` 与 `protoc.exe` 仅是源码仓库中的构建工具，均不是 IW4 Multiplayer Host。

### C. IW4X Client

- 客户端源码：YES
- 源码根：`D:\BaiduNetdiskDownload\使命召唤OL\IW4X\Client核心代码\iw4x-client`
- 预期构建目标：`premake5.lua` 中 `project iw4x` / `kind SharedLib`。
- 已构建 Client DLL：未找到。当前输入不包含成品 `iw4x.dll`。
- 源码中预期的宿主名：`src/STDInclude.hpp` 定义 `BASEGAME_NAME` 为 `iw4mp_ceg.exe`。

### Git 身份

| 字段 | 值 |
|---|---|
| repository root | `D:\BaiduNetdiskDownload\使命召唤OL\IW4X\Client核心代码\iw4x-client` |
| current commit | `0699a7e5716ded53bcfa6748bcb89a535f8f39f0` |
| branch | `main` |
| remote URL | `https://github.com/iw4x/iw4x-client.git` |
| HEAD date | `2026-09-17T19:35:40-04:00` |
| describe | `r5124-18-g0699a7e5` |
| nearest tag | `r5124` |
| worktree status | `clean` |

## 源码结构确认

| 预期路径 | 存在 |
|---|---|
| `src` | YES |
| `src/Components` | YES |
| `src/Game` | YES |
| `src/Steam` | YES |
| `src/Utils` | YES |

| 关键文件/标记 | 存在 | 标记存在 |
|---|---|---|
| `Client核心代码\iw4x-client\src\DllMain.cpp` : `DllMain` | YES | YES |
| `Client核心代码\iw4x-client\src\DllMain.cpp` : `Main::EntryPoint` | YES | YES |
| `Client核心代码\iw4x-client\src\DllMain.cpp` : `Components::Loader` | YES | YES |
| `Client核心代码\iw4x-client\src\Components\Loader.cpp` : `namespace Components` | YES | YES |
| `Client核心代码\iw4x-client\src\Game\Functions.cpp` : `namespace Game` | YES | YES |

重点存在项：`src/DllMain.cpp`、`src/Components/`、`src/Game/Functions.cpp`、`src/Steam/`、`src/Utils/` 均存在。
未发现名为 `src/Main.cpp` 的文件；入口链证据在 `src/DllMain.cpp` 中，其中引用了 `Main::EntryPoint` 并调用 `Components::Loader`。

## PE 文件清单

| filename | size | sha256 | PE | machine | image_base | entry_rva | imports | exports | timestamp |
|---|---:|---|---|---|---|---|---:|---:|---|
| `premake5.exe` | 1567744 | `2301e3e23ff3074cb83a5ea6103d68c7ea81dad56b786807c84b0643cddea31b` | PE64 | `0x8664` | `0x140000000` | `0xa967c` | 293 | 0 | `2026-01-24T18:06:59Z` |
| `protoc.exe` | 3905024 | `85bad46a94aee92c2bd49ee65dbb847d3d039a3d64f995e775f21477d78a8ee3` | PE64 | `0x8664` | `0x140000000` | `0x215c70` | 137 | 0 | `2022-09-29T20:31:04Z` |
| `iw4x-launcher.exe` | 40338259 | `d1982b7cec260a3d3141f2921c23983a2832aada7d6f419b328d125ac1e5284d` | PE64 | `0x8664` | `0x140000000` | `0x1400` | 406 | 0 | `2026-06-24T16:40:17Z` |

完整节区、EntryVA 与 PE timestamp 见 `ich001_pe_inventory.csv`。

## 输出文件

- `ich001_input_inventory.csv`
- `ich001_pe_inventory.csv`
- `ich001_source_inventory.csv`
- `ICH001_INPUT_BASELINE.md`

## 基线判定

- `IW4X_LAUNCHER_FOUND = YES`
- `IW4MP_HOST_FOUND = NO`
- `IW4X_CLIENT_FOUND = YES`（源码形态确认；成品 DLL 未找到）
- `IW4X_SOURCE_FOUND = YES`
- `LAUNCHER_PATH = D:\BaiduNetdiskDownload\使命召唤OL\IW4X\启动器\iw4x-launcher.exe`
- `IW4MP_PATH = NOT_FOUND`
- `CLIENT_PATH = D:\BaiduNetdiskDownload\使命召唤OL\IW4X\Client核心代码\iw4x-client (source; no built client DLL found)`
- `SOURCE_ROOT = D:\BaiduNetdiskDownload\使命召唤OL\IW4X\Client核心代码\iw4x-client`
- `INPUT_BASELINE = COMPLETE`

本阶段到此停止；未进行更深入的逆向、动态验证或代码行为分析。
